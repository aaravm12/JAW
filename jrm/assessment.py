"""Monotonic/source-time state machine; wall clock is metadata only."""
from .config import Settings, PHASES

class Assessment:
    def __init__(self, cfg: Settings):
        self.cfg = cfg
        self.state = "idle"
        self.phase_index = 0
        self.phase_elapsed = 0.
        self.elapsed = 0.
        self.last_t = None
        self.events = []
        self.skipped = []

    @property
    def phase(self):
        return PHASES[self.phase_index]

    def start(self, t):
        if self.state != "idle":
            raise ValueError("Create a fresh assessment before restarting.")
        self.state, self.last_t = "running", t
        self.events.append({"event": "start", "source_t": t})

    def tick(self, t):
        if self.last_t is not None and t < self.last_t:
            raise ValueError("Assessment time cannot go backwards.")
        dt = 0 if self.last_t is None else t - self.last_t
        self.last_t = t
        if self.state != "running":
            return
        remaining = dt
        while remaining > 0 and self.state == "running":
            step = min(remaining, self.cfg.durations[self.phase_index] - self.phase_elapsed)
            self.phase_elapsed += step
            self.elapsed += step
            remaining -= step
            if self.phase_elapsed + 1e-9 >= self.cfg.durations[self.phase_index]:
                self._advance(t - remaining)

    def _advance(self, t):
        if self.phase_index == 3:
            self.state = "finished"
            self.events.append({"event": "finish", "source_t": t})
        else:
            self.phase_index += 1
            self.phase_elapsed = 0.
            self.events.append({"event": "phase", "phase": self.phase, "source_t": t})

    def pause(self, t):
        if self.state == "running":
            self.tick(t)
            if self.state == "running":
                self.state = "paused"
                self.events.append({"event": "pause", "source_t": t})

    def resume(self, t):
        if self.state == "paused":
            self.last_t, self.state = t, "running"
            self.events.append({"event": "resume", "source_t": t})

    def skip(self, t):
        if self.state != "running" or self.phase not in ("activity", "post_activity"):
            raise ValueError("Only activity or post-activity may be skipped; it is recorded as incomplete.")
        self.tick(t)
        if self.state == "running":
            self.skipped.append(self.phase)
            self.events.append({"event": "skip", "phase": self.phase, "source_t": t})
            self._advance(t)

    def stop(self, t):
        if self.state in ("running", "paused"):
            self.tick(t)
            if self.state != "finished":
                self.state = "stopped"
                self.events.append({"event": "stop", "source_t": t})
