"""Deterministic batch runner, using the same detector, pipeline and recorder as the UI."""
import hashlib
from pathlib import Path
from .acquisition import Video
from .assessment import Assessment
from .config import Settings
from .detector import FaceDetector
from .pipeline import Pipeline
from .recorder import Recorder
from .storage import Storage
from .synthetic import synthetic_observation


def run_synthetic(store, cfg=None, participant=None, fps=30.):
    cfg = cfg or Settings()
    pid = participant or store.participant()
    pipeline = Pipeline(cfg)
    pipeline.begin_calibration()
    a = Assessment(cfg)
    rec = None
    for i in range(int((sum(cfg.durations) + cfg.calibration_seconds + 2) * fps) + 1):
        t = i / fps
        a.tick(t)
        obs = synthetic_observation(a.phase_elapsed, a.phase, cfg.cadence_hz)
        row = pipeline.process(obs, t, i)
        if a.state == "idle" and row["valid"]:
            a.start(t)
            rec = Recorder(pid, "synthetic", cfg, pipeline.reference,
                           {"kind": "synthetic", "fps": fps, "timestamp_basis": "synthetic_frame_clock"})
        if rec:
            rec.append(row, a)
        if a.state == "finished":
            return store.save(rec.snapshot(a), rec.rows)
    raise RuntimeError("Synthetic assessment failed to complete.")


def analyze_video(path, store, cfg=None, participant=None, synthetic=False):
    cfg = cfg or Settings()
    pid = participant or store.participant()
    pipeline = Pipeline(cfg)
    pipeline.begin_calibration()
    a = Assessment(cfg)
    with Path(path).open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    rec = Recorder(pid, "synthetic_video" if synthetic else "video", cfg, None,
                   {"kind": "video", "source_sha256": digest, "timestamp_basis": "video_presentation_timestamps"})
    source = detector = None
    last_t = 0.
    try:
        source, detector = Video(path), FaceDetector()
        while (item := source.read()) is not None:
            index, t, image = item
            last_t = t
            a.tick(t)
            row = pipeline.process(detector.detect(image, t), t, index)
            if a.state == "idle" and row["valid"]:
                a.start(t)
                rec.metadata["calibration"] = pipeline.reference
            rec.append(row, a)
            if a.state == "finished":
                break
        if a.state == "idle":
            a.state = "calibration_failed"
        else:
            a.stop(last_t)
    except Exception as exc:
        a.state = "interrupted"
        a.events.append({"event": "error", "message": str(exc), "source_t": last_t})
        store.save(rec.snapshot(a), rec.rows)
        raise
    finally:
        for resource in (source, detector):
            if resource:
                resource.close()
    return store.save(rec.snapshot(a), rec.rows)
