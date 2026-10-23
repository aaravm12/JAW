"""Shared streaming geometry and preprocessing for webcam, video, and synthetic input."""
from collections import deque
import math
import numpy as np
from .config import Settings
from .geometry import geometry
from .calibration import Calibrator

class Pipeline:
    def __init__(self, cfg: Settings):
        self.cfg = cfg
        self.calibrator = Calibrator(cfg)
        self.reference = None
        self.calibrating = False
        self.repositioned = False
        self.last_t = None
        self.last_good = None
        self.dts = deque(maxlen=60)

    def begin_calibration(self):
        self.calibrator = Calibrator(self.cfg)
        self.reference = None
        self.calibrating = True
        self.repositioned = False
        self.last_good = None

    def process(self, obs, t: float, index: int):
        if not math.isfinite(t) or t < 0 or (self.last_t is not None and t <= self.last_t):
            raise ValueError("Frame timestamps must be finite, nonnegative, and strictly increasing.")
        raw, flags = geometry(obs, self.cfg)
        dt = None if self.last_t is None else t - self.last_t
        if dt is not None:
            typical = float(np.median(self.dts)) if self.dts else dt
            if dt > self.cfg.max_gap or dt > max(.15, 3 * typical):
                flags.append("frame_gap")
            else:
                self.dts.append(dt)
        self.last_t = t
        if self.calibrating:
            reference = self.calibrator.add(t, raw, flags)
            if reference is not None:
                self.reference = reference
                self.calibrating = False
        if self.reference and "eye_fraction" in raw:
            ref = self.reference
            scale = abs(raw["eye_fraction"] / ref["eye_fraction"] - 1)
            center = math.hypot(raw["center_x"] - ref["center_x"], raw["center_y"] - ref["center_y"])
            pose = max((abs(raw.get(k, ref[k]) - ref[k]) for k in ("yaw", "pitch", "roll")))
            if scale > self.cfg.scale_change or center > self.cfg.center_change or pose > self.cfg.pose_change:
                self.repositioned = True
        if not self.reference:
            flags.append("uncalibrated")
        if self.repositioned:
            flags.append("camera_or_head_repositioned")
        if not flags and self.last_good:
            gt, gr, _ = self.last_good
            if abs(raw["opening_raw"] - gr) / (t - gt) > self.cfg.max_opening_speed:
                flags.append("opening_outlier")
        row = dict(source_t=float(t), frame_index=int(index), dt=dt, **raw)
        row.update(valid=not flags, flags="|".join(flags), opening=None, velocity=None, lateral=None)
        if not flags:
            value = raw["opening_raw"]
            if self.last_good:
                gt, _, gf = self.last_good
                delta = t - gt
                alpha = -math.expm1(-delta / self.cfg.smoothing_tau)
                filtered = gf + alpha * (value - gf)
                row["velocity"] = (filtered - gf) / delta
            else:
                filtered = value
            row["opening"] = float(filtered)
            row["lateral"] = raw["lateral_raw"] - self.reference["lateral_raw"]
            self.last_good = (t, value, filtered)
        else:
            self.last_good = None
        return row
