from dataclasses import dataclass, asdict, field
import json
from pathlib import Path

PHASES = ("baseline", "controlled", "activity", "post_activity")
INSTRUCTIONS = {
    "baseline": "Sit comfortably, face the camera, and let your jaw rest naturally.",
    "controlled": "Slowly open and close within a comfortable range. Do not force movement.",
    "activity": "Follow the gentle pace if comfortable. Stop immediately if you feel discomfort.",
    "post_activity": "Relax your jaw. Remain facing the camera. No recovery claim is calculated.",
}

@dataclass(frozen=True)
class Settings:
    durations: tuple[float, ...] = (30., 30., 30., 120.)
    cadence_hz: float = 0.25
    calibration_seconds: float = 2.0
    calibration_frames: int = 30
    min_eye_fraction: float = 0.15
    max_eye_fraction: float = 0.55
    max_yaw: float = 20.0
    max_pitch: float = 20.0
    max_roll: float = 15.0
    scale_change: float = 0.15
    center_change: float = 0.10
    pose_change: float = 12.0
    smoothing_tau: float = 0.08
    max_gap: float = 0.25
    max_opening_speed: float = 4.0
    cycle_low: float = 0.025
    cycle_high: float = 0.08
    min_cycle_seconds: float = 0.5
    max_cycle_seconds: float = 15.0

    def __post_init__(self):
        import math
        values = [*self.durations, *[v for k, v in asdict(self).items() if k != 'durations']]
        if len(self.durations) != 4 or any(not math.isfinite(v) or v <= 0 for v in values):
            raise ValueError("All settings must be finite and positive; exactly four phase durations are required.")
        if self.cycle_high <= self.cycle_low or self.max_eye_fraction <= self.min_eye_fraction:
            raise ValueError("Upper thresholds must exceed lower thresholds.")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def read(cls, path: str | Path):
        data = json.loads(Path(path).read_text())
        if "durations" in data:
            data["durations"] = tuple(data["durations"])
        return cls(**data)
