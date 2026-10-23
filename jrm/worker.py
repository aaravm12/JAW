"""Acquisition, inference, recording and checkpoints run off the Qt UI thread."""
import hashlib
import queue
import time
import traceback
from PySide6.QtCore import QThread, Signal
from .acquisition import Camera, Video
from .assessment import Assessment
from .config import Settings
from .cycles import LiveMovementMetrics
from .telemetry import FrameTelemetry
from .detector import FaceDetector
from .pipeline import Pipeline
from .recorder import Recorder
from .storage import Storage
from .synthetic import synthetic_observation, draw_synthetic

class CaptureWorker(QThread):
    saved = Signal(str)
    error = Signal(str)
    notice = Signal(str)

    def __init__(self, mode, cfg, data_dir, participant, camera_index=0, video_path=None, synthetic_video=False):
        super().__init__()
        self.mode, self.cfg, self.data_dir = mode, cfg, data_dir
        self.participant, self.camera_index, self.video_path = participant, camera_index, video_path
        self.source_kind = "synthetic_video" if synthetic_video and mode == "video" else mode
        self.commands = queue.Queue()
        self.preview = queue.Queue(maxsize=1)
        self.quitting = False

    def command(self, action):
        self.commands.put(action)

    def run(self):
        source = detector = store = recorder = None
        assessment = Assessment(self.cfg)
        pipeline = Pipeline(self.cfg)
        metrics = None
        telemetry = FrameTelemetry()
        last_t = 0.
        last_valid = False
        checkpoint_t = 0.
        try:
            store = Storage(self.data_dir)
            device = {"kind": self.mode, "timestamp_basis": "monotonic_capture"}
            if self.mode == "webcam":
                detector = FaceDetector()
                source = Camera(self.camera_index)
                device["camera_index"] = self.camera_index
            elif self.mode == "video":
                detector, source = FaceDetector(), Video(self.video_path)
                with open(self.video_path, "rb") as f:
                    device["source_sha256"] = hashlib.file_digest(f, "sha256").hexdigest()
                device["timestamp_basis"] = "video_presentation_timestamps"
                pipeline.begin_calibration()
                recorder = Recorder(self.participant, self.source_kind, self.cfg, None, device)
            else:
                device["timestamp_basis"] = "monotonic_synthetic_playback"
            origin, index = time.monotonic(), 0
            while not self.quitting:
                while not self.commands.empty():
                    cmd = self.commands.get_nowait()
                    if cmd == "quit":
                        self.quitting = True
                    elif cmd == "calibrate" and assessment.state in ("idle", "finished", "stopped"):
                        pipeline.begin_calibration()
                    elif cmd == "start" and last_valid and pipeline.reference and not pipeline.repositioned and assessment.state in ("idle", "finished", "stopped"):
                        assessment = Assessment(self.cfg)
                        assessment.start(last_t)
                        recorder = Recorder(self.participant, self.source_kind, self.cfg, pipeline.reference, device)
                        metrics = LiveMovementMetrics(self.cfg, pipeline.reference["opening_raw"])
                    elif cmd == "pause":
                        assessment.pause(last_t)
                        if metrics:
                            metrics.break_sequence()
                    elif cmd == "resume":
                        assessment.resume(last_t)
                        pipeline.last_good = None
                    elif cmd == "skip":
                        try:
                            assessment.skip(last_t)
                            if recorder and assessment.state == "finished":
                                self.saved.emit(store.save(recorder.snapshot(assessment), recorder.rows))
                        except ValueError as exc:
                            self.notice.emit(str(exc))
                    elif cmd == "stop":
                        assessment.stop(last_t)
                        if recorder:
                            self.saved.emit(store.save(recorder.snapshot(assessment), recorder.rows))
                    elif cmd == "restart":
                        assessment.stop(last_t)
                        if recorder:
                            store.save(recorder.snapshot(assessment), recorder.rows)
                        recorder = None
                        assessment = Assessment(self.cfg)
                        pipeline.begin_calibration()
                        metrics = None
                if self.quitting:
                    break
                if self.mode == "synthetic":
                    t = time.monotonic() - origin
                    obs = synthetic_observation(assessment.phase_elapsed, assessment.phase if assessment.state == "running" else "baseline", self.cfg.cadence_hz)
                    frame = draw_synthetic(obs)
                else:
                    item = source.read()
                    if item is None:
                        if assessment.state in ("running", "paused"):
                            assessment.stop(last_t)
                        elif assessment.state == "idle":
                            assessment.state = "calibration_failed"
                        self.notice.emit("Video analysis finished. Incomplete recordings remain labeled as incomplete.")
                        break
                    index, t, frame = item
                    obs = detector.detect(frame, t)
                last_t = t
                previous_state = assessment.state
                assessment.tick(t)
                row = pipeline.process(obs, t, index)
                last_valid = row["valid"]
                if self.mode == "video" and assessment.state == "idle" and row["valid"] and pipeline.reference:
                    assessment.start(t)
                    recorder.metadata["calibration"] = pipeline.reference
                    metrics = LiveMovementMetrics(self.cfg, pipeline.reference["opening_raw"])
                live = (metrics.update(row, assessment.phase, assessment.state) if metrics else
                        {"cycles": 0, "peak_opening": None, "frequency_hz": None})
                if recorder and previous_state not in ("finished", "stopped", "calibration_failed"):
                    recorder.append(row, assessment)
                    if time.monotonic() - checkpoint_t > 2 or assessment.state in ("finished", "stopped"):
                        sid = store.save(recorder.snapshot(assessment), recorder.rows)
                        checkpoint_t = time.monotonic()
                        if assessment.state in ("finished", "stopped"):
                            self.saved.emit(sid)
                packet = {"frame": frame, "row": row, "observation": obs,
                          "phase": assessment.phase, "phase_elapsed": assessment.phase_elapsed,
                          "elapsed": assessment.elapsed, "state": assessment.state,
                          "calibration": pipeline.reference, "calibrating": pipeline.calibrating,
                          "calibration_message": pipeline.calibrator.message,
                          "calibration_progress": pipeline.calibrator.progress,
                          **live, "telemetry": telemetry.update(time.monotonic(), frame),
                          "mode": self.mode}
                try:
                    self.preview.get_nowait()
                except queue.Empty:
                    pass
                self.preview.put_nowait(packet)
                index += 1
                if self.mode == "synthetic":
                    self.msleep(30)
                if self.mode == "video" and assessment.state == "finished":
                    break
        except Exception as exc:
            traceback.print_exc()
            self.error.emit(str(exc))
            if assessment.state in ("running", "paused"):
                assessment.state = "interrupted"
                assessment.events.append({"event": "error", "message": str(exc), "source_t": last_t})
        finally:
            if recorder and store:
                if assessment.state in ("running", "paused"):
                    assessment.stop(last_t)
                try:
                    sid = store.save(recorder.snapshot(assessment), recorder.rows)
                    self.saved.emit(sid)
                except Exception as exc:
                    self.error.emit("Could not save this assessment: " + str(exc))
            for resource in (source, detector, store):
                if resource:
                    resource.close()
