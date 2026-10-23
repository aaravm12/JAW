from collections import deque
import numpy as np
from .config import Settings

class Calibrator:
    """A contiguous stable resting window, never interpolated across missing data."""
    def __init__(self, cfg: Settings):
        self.cfg = cfg
        self.samples = deque()
        self.reference = None
        self.message = "Face forward with your jaw resting; hold still for calibration."
        self.progress = 0.0

    def add(self, t, raw, flags):
        if flags:
            self.samples.clear()
            self.progress = 0.0
            self.message = "Adjust position: " + ", ".join(flags)
            return None
        if self.samples and (t <= self.samples[-1][0] or t - self.samples[-1][0] > self.cfg.max_gap):
            self.samples.clear()
        self.samples.append((t, raw))
        while len(self.samples) > 1 and t - self.samples[1][0] >= self.cfg.calibration_seconds:
            self.samples.popleft()
        elapsed = t - self.samples[0][0]
        self.progress = min(1., elapsed / self.cfg.calibration_seconds)
        if elapsed + 1e-8 < self.cfg.calibration_seconds or len(self.samples) < self.cfg.calibration_frames:
            self.message = "Hold still with your jaw resting…"
            return None
        keys = ("eye_fraction", "center_x", "center_y", "yaw", "pitch", "roll", "opening_raw", "lateral_raw")
        a = np.array([[s[1][k] for k in keys] for s in self.samples])
        cv = float(a[:, 0].std() / a[:, 0].mean())
        opening_sd = float(a[:, 6].std())
        center_sd = float(np.max(a[:, 1:3].std(axis=0)))
        pose_sd = float(np.max(a[:, 3:6].std(axis=0)))
        if cv > .03 or center_sd > .012 or pose_sd > 3 or opening_sd > .015:
            self.message = "Unstable reference. Keep your head and relaxed jaw still."
            return None
        self.reference = dict(zip(keys, [float(x) for x in np.median(a, axis=0)]))
        self.reference.update(quality="stable_reference", scale_cv=cv, opening_sd=opening_sd,
                              center_sd=center_sd, pose_sd=pose_sd, frames=len(a),
                              duration_s=float(elapsed), source_t=float(t))
        self.message = "Calibration ready. Stay in this position."
        return self.reference
