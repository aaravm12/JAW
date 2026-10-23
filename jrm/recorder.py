from datetime import datetime, timezone
import copy
import uuid
import platform
from functools import lru_cache
from importlib.metadata import version
from .model import MODEL_SHA256

@lru_cache(maxsize=1)
def runtime_fingerprint():
    return {"python": platform.python_version(), "platform": platform.system(),
            "machine": platform.machine(), "model_sha256": MODEL_SHA256,
            **{name: version(name) for name in ("mediapipe", "numpy", "opencv-contrib-python", "av")}}

from . import __version__
from .analytics import analyze

class Recorder:
    def __init__(self, participant_id, source_kind, cfg, calibration, device):
        self.cfg = cfg
        self.rows = []
        self.metadata = {
            "schema_version": 1, "algorithm_version": __version__, "runtime": runtime_fingerprint(),
            "session_id": str(uuid.uuid4()), "participant_id": participant_id,
            "source_kind": source_kind, "simulated": source_kind in ("synthetic", "synthetic_video"),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "settings": cfg.to_dict(), "calibration": copy.deepcopy(calibration),
            "device": device, "status": "running", "events": [], "skipped": [],
        }
        self.segment = 0
        self.last_state = None
        self.last_phase = None

    def append(self, row, assessment):
        state, phase = assessment.state, assessment.phase if assessment.state != "idle" else "calibration"
        if state != self.last_state or phase != self.last_phase:
            self.segment += 1
        self.last_state, self.last_phase = state, phase
        out = dict(row, elapsed=assessment.elapsed, phase=phase,
                   phase_elapsed=assessment.phase_elapsed, recording_state=state,
                   segment=self.segment, source_kind=self.metadata["source_kind"])
        if state != "running":
            out.update(valid=False, opening=None, velocity=None, lateral=None,
                       flags="|".join(filter(None, [out["flags"], state])))
        self.rows.append(out)

    def snapshot(self, assessment):
        result = dict(self.metadata, status=assessment.state,
                      events=copy.deepcopy(assessment.events), skipped=list(assessment.skipped))
        result["analysis"] = analyze(self.rows, self.cfg, (self.metadata["calibration"] or {}).get("opening_raw", 0.))
        return result
