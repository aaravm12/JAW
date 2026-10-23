# Project instructions

Read `docs/ARCHITECTURE.md`, `docs/MEASUREMENTS.md`, and `docs/TESTING.md` before changing acquisition, signal analysis, or recording.

- This is a camera-only engineering prototype, not a diagnostic product.
- Live capture, file replay, and synthetic geometry share `Pipeline`; do not implement a competing metric in UI code.
- Preserve raw observations, source timestamps, validity flags, calibration, source identity, and settings. Never interpolate missing values into valid research data.
- Never mix synthetic sessions with human recordings or imply lip landmarks measure mandibular/TMJ biomechanics.
- Keep acquisition and inference outside the Qt UI thread. Preserve shutdown and partial-session checkpoints.
- Tests: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q` (omit environment prefix on Windows). Run `python -m jrm --download-model` for detector regressions.
- Update the engineering report with observed evidence, distinguishing Linux offscreen execution from untested macOS/hardware behavior.
- Do not commit participant data, face videos, credentials, local databases, virtual environments, or downloaded third-party model binaries. `data/` and `evidence/` may contain clearly labeled original synthetic artifacts.
