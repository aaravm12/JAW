"""Measured processing throughput, independent of video/source time."""
from collections import deque
import math


class FrameTelemetry:
    def __init__(self, window_seconds=2.0):
        self.window_seconds = window_seconds
        self.times = deque()

    def update(self, now, frame):
        if not math.isfinite(now) or (self.times and now <= self.times[-1]):
            raise ValueError("Processing timestamps must increase.")
        self.times.append(now)
        while len(self.times) > 1 and self.times[0] < now - self.window_seconds:
            self.times.popleft()
        fps = ((len(self.times) - 1) / (now - self.times[0])
               if len(self.times) > 1 else None)
        height, width = frame.shape[:2]
        return {"processing_fps": fps, "width": width, "height": height}
