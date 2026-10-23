from .config import Settings

class CycleDetector:
    """A complete low→high→low excursion. A gap cancels the unfinished cycle."""
    def __init__(self, cfg: Settings, resting: float):
        self.cfg = cfg
        self.low = resting + cfg.cycle_low
        self.high = resting + cfg.cycle_high
        self.reset()

    def reset(self):
        self.last_low = None
        self.start = None
        self.peak = None
        self.peak_t = None
        self.reached_high = False

    def add(self, t, value, valid=True):
        if not valid or value is None:
            self.reset()
            return None
        if self.start is not None and t - self.start > self.cfg.max_cycle_seconds:
            self.reset()
        if value <= self.low:
            completed = None
            if self.start is not None and self.reached_high:
                duration = t - self.start
                if self.cfg.min_cycle_seconds <= duration <= self.cfg.max_cycle_seconds:
                    completed = {"start": self.start, "peak_t": self.peak_t, "end": t,
                                 "duration": duration, "opening_duration": self.peak_t - self.start,
                                 "closing_duration": t - self.peak_t,
                                 "peak": self.peak, "amplitude": self.peak - self.start_value}
            self.reset()
            self.last_low = (t, value)
            return completed
        if self.start is None and self.last_low is not None:
            self.start, self.start_value = self.last_low
            self.peak, self.peak_t = value, t
        if self.start is not None:
            if value > self.peak:
                self.peak, self.peak_t = value, t
            if value >= self.high:
                self.reached_high = True
        return None


class LiveMovementMetrics:
    """Session count and current-phase peak/frequency, using the shared detector."""
    def __init__(self, cfg, resting):
        self.detector = CycleDetector(cfg, resting)
        self.cfg = cfg
        self.cycles = 0
        self.phase = None
        self.peak = None
        self.previous_peak_t = None
        self.period_sum = 0.
        self.period_count = 0

    def break_sequence(self):
        self.detector.reset()
        self.previous_peak_t = None
        self.period_sum = 0.
        self.period_count = 0

    def update(self, row, phase, state):
        if phase != self.phase:
            self.phase, self.peak = phase, None
            self.break_sequence()
        valid = row['valid'] and row.get('opening') is not None and state == 'running'
        t = row['source_t']
        if not valid:
            self.break_sequence()
        else:
            if self.previous_peak_t is not None and t - self.previous_peak_t > self.cfg.max_cycle_seconds:
                self.break_sequence()
            self.peak = max(self.peak, row['opening']) if self.peak is not None else row['opening']
            cycle = self.detector.add(t, row['opening'])
            if cycle:
                self.cycles += 1
                if self.previous_peak_t is not None:
                    self.period_sum += cycle['peak_t'] - self.previous_peak_t
                    self.period_count += 1
                self.previous_peak_t = cycle['peak_t']
        return {"cycles": self.cycles, "peak_opening": self.peak,
                "frequency_hz": self.period_count / self.period_sum if self.period_count else None}
