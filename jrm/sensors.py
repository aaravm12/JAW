"""Future hardware contract only. No implemented BLE device or synthetic EMG UI."""
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class EMGSample:
    sensor_time_s: float
    host_monotonic_s: float
    left_volts: float
    right_volts: float
    sample_rate_hz: float
    quality_flags: tuple[str, ...]

@dataclass(frozen=True)
class ClockMapping:
    offset_s: float
    drift: float
    uncertainty_s: float
    # Fit and validate from real synchronization observations before use.
    def host_time(self, sensor_time_s):
        return self.offset_s + self.drift * sensor_time_s

class EMGBackend(Protocol):
    @property
    def connected(self) -> bool: ...
    def read(self) -> list[EMGSample]: ...
    def close(self) -> None: ...
