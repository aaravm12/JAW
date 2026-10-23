# Architecture and acceptance boundary

## First release

A local Python 3.11/3.12 desktop application records observable mouth movements: input selection → guided calibration → four timed phases → transactional save → graphs → reopen → CSV/JSON export. A complete synthetic path and positive/negative pixel-video replay provide independent verification. A real webcam and macOS must be acceptance-tested on their actual hardware.

PySide6 provides native controls without a browser permission/server layer. OpenCV captures frames, MediaPipe Tasks detects landmarks on CPU, PyAV decodes presentation timestamps, NumPy handles geometry/filtering, PyQtGraph plots, and SQLite stores sessions. No server or telemetry is included. SciPy and Pandas are unnecessary for the implemented calculations and storage, reducing the core surface.

## Data flow

`Camera` (monotonic) / `Video` (PTS) → `FaceDetector` → `Observation` → `Pipeline` (geometry, calibration, quality, filter) → `Assessment` + `Recorder` → `Storage` → `analytics` / UI graphs / export.

The deterministic `synthetic_observation` supplies the same Observation type. The cartoon pixel video exercises the real detector separately. Demo geometry is never described as ML output.

## Modules

| Concern | Module |
|---|---|
| CLI and Qt startup | `__main__.py` |
| Native interface / acquisition worker | `ui.py`, `worker.py` |
| Webcam / presentation timestamp decoding | `acquisition.py` |
| MediaPipe Tasks wrapper / model retrieval | `detector.py`, `model.py` |
| Landmark geometry / reference calibration | `geometry.py`, `calibration.py` |
| Quality-aware preprocessing | `pipeline.py` |
| Timed phases and controls | `assessment.py` |
| Cycle segmentation / summaries / comparisons | `cycles.py`, `analytics.py` |
| Recording and transactional storage | `recorder.py`, `storage.py` |
| Plots | `charts.py` |
| Synthetic fixtures and batch replay | `synthetic.py`, `synthetic_face.py`, `replay.py` |
| Future sensor contract | `sensors.py` |

## Threads and lifecycle

A QThread owns capture, inference, the pipeline, recorder, and its own SQLite connection. The main thread owns Qt widgets and a separate connection. Commands are queued. A single-slot preview queue drops only outdated previews; every processed measurement is recorded. Camera frames that never reach processing are not invented; temporal gaps are flagged.

Save checkpoints occur about every two real seconds. Each database transaction contains both metadata and its complete current sample set. Closing input or the application stops acquisition and saves the partial session. Forced termination can lose up to the latest checkpoint interval. An old `running`/`paused` checkpoint is incomplete and never eligible for a complete-session comparison. The UI does not resume an interrupted assessment from the middle; it can reopen/export the checkpoint and begin a fresh assessment.

SQLite stores sample rows as JSON in an indexed child table, not just metadata. This avoids dangling external CSVs after interrupted saves. Portable CSV plus metadata JSON is generated on export. There is no default video storage.

## Scope deliberately deferred

No EMG signal generator, BLE driver, predictive model, recovery index, fatigue estimate, biometric identity, physical-unit calibration, institutional study workflow, advanced dashboard, or time-to-baseline algorithm. `sensors.py` defines timestamped bilateral samples and an explicit offset/drift/uncertainty contract only. Real hardware needs a documented device protocol, acquisition implementation, synchronization tests, signal units, electrical safety review, and validation before use.

## Core verification areas (not product milestone advancement)

1. Geometry/quality/calibration tests; exact numeric and missing-data behavior.
2. State machine and full synthetic assessment; all phases, cycle metrics, storage/reopen/export.
3. Native UI start, pause/resume, finish/save, reopen, export, stop/restart, shutdown.
4. Pixel-video replay; positive cartoon detection, negative missing-face, variable timestamps, repeated identical outputs.
5. Deliver reproducible setup, macOS launcher, documentation and CI; actual macOS/webcam acceptance remains explicit.
