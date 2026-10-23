# Checkpoint 4 stabilization report — 23 October 2026

## Scope and status

The camera-only desktop prototype includes mandatory calibration, shared MediaPipe/geometry processing, complete-cycle detection, guided assessment, pause/resume, transactional local sessions, reopening, graphs, CSV/JSON export, video replay, and explicitly synthetic demonstrations. Checkpoint 4 adds processing FPS, actual frame dimensions, bounded background camera discovery with a manual index fallback, current-phase peak opening, and live measured movement frequency.

**Milestone 5 has not started.** Native Mac launch, camera permissions, real webcam tracking, and physical five-cycle acceptance remain hardware-only checks assigned to the operator in [MACOS_VERIFICATION.md](MACOS_VERIFICATION.md). No physical camera was available in the Linux environment. These software tests do not establish human accuracy or clinical validity.

## Verification evidence

- Baseline suite: 42 tests passed on Linux/Python 3.12, including actual MediaPipe inference on an original cartoon video, deterministic repeat replay, missing-face and variable-frame-rate replay, synthetic Qt assessment, storage/reopen/export, and shutdown.
- Checkpoint 4 regression suite: see final test result below. Tests preserve the baseline coverage and add real-clock throughput/resolution checks, sparse camera discovery and cleanup, unsupported/failed discovery fallback, camera open/read errors, UI discovery and indicator behavior, and controlled cycle acceptance.
- Five-cycle sequences: exactly five complete cycles with leading/trailing partial movements and subthreshold movements; also five with small head motion. A large rotation cancels the in-progress cycle, latches invalidity, and permits further valid counting only after recalibration. Live and saved-analysis cycle counts agree on the controlled sequences.
- Setup and live Qt tabs rendered at 1220 × 880 on Linux's offscreen platform and were visually inspected. These are actual widgets, not native Mac or webcam screenshots.
- Synthetic pixel video fixtures regenerated successfully from the committed generator. Generated fixtures, session data, exports, screenshots, logs, databases, environments, and downloaded model binaries are excluded from git.
- Earlier pinned-dependency resolution succeeded for Apple Silicon, Intel Mac, and Windows targets. Resolution is not execution on those platforms. Intel uses MediaPipe 0.10.21; other supported targets use 0.10.32. No dependency versions were changed in this stabilization.

## Reproduce

```sh
python3.12 scripts/setup.py --setup-only
.venv/bin/python -m jrm --download-model
.venv/bin/python scripts/make_fixtures.py
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Pytest also generates missing fixtures automatically. Detector tests explicitly skip if the model is unavailable; any such skip must be reported. Local logs are under the ignored `evidence/` directory in the development checkout and are not bundled in the source repository. The original synthetic fixture generation code and all automated tests are committed. The GitHub Actions workflow also generates fixtures and runs tests; a workflow file is not proof that hosted CI has passed.

## Remaining limitations

1. Complete the Mac operator handoff before claiming a verified Mac webcam product. Multi-camera selection, physical disconnect handling, and permission denial/recovery require actual devices.
2. Camera discovery briefly opens candidate devices on a background thread. macOS/Windows scan indices 0–9; Linux probes existing video nodes. Busy or permission-blocked devices may be absent. Manual indices 0–99 remain available. Indices can change after reconnecting devices; confirm the preview.
3. Native camera opening/reading can block in the driver. Shutdown waits and reports a delay rather than killing a running acquisition/discovery thread.
4. FPS is measured application processing throughput, not sensor exposure rate. Resolution is the actual frame array size. Video processing throughput is separate from source playback rate.
5. The live peak describes valid frames in the current phase; frequency requires two complete cycles in one uninterrupted segment. It clears on invalidity, pause, phase change, restart, or a long absence of peaks. See [MEASUREMENTS.md](MEASUREMENTS.md).
6. Pose and quality thresholds are engineering heuristics. Lip opening normalized to eye distance is not physical jaw displacement, TMJ biomechanics, force, fatigue, or recovery. No recovery or diagnostic score is calculated.
7. Storage is local and unencrypted. A hard crash can lose the latest checkpoint interval (approximately two seconds). Imported videos require a resting lead-in and known protocol timing. Reproducibility is tested within the same software/model/runtime, not guaranteed across architectures.
8. The development launcher is not a signed/notarized Mac application. Windows hardware remains unverified too.

## Final test result

**55 passed, 0 failed, 0 skipped, 14 upstream Matplotlib/Pyparsing deprecation warnings, in 39.17 seconds** on Linux/Python 3.12. Command: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q`. All 42 baseline tests remain present and pass, with 13 additional regression cases. Generated fixtures were rebuilt immediately before this run.
