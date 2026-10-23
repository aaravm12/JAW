# Verification

Use Python 3.11/3.12 and the pinned `requirements.lock`. The submitted evidence was generated on Linux x86_64 with Python 3.12 and Qt's `offscreen` platform. Offscreen screenshots are images of actual Qt widgets; they do not demonstrate a macOS window or camera permission prompt.

## Automated suite

```sh
python3.12 scripts/setup.py --setup-only
.venv/bin/python -m jrm --download-model
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

The suite covers image-aspect normalization and scaling, invalid/missing/multiple faces, pose, stable calibration, reposition latching, temporal gaps/outliers/filtering, bad timestamps, cycle completeness, pause/resume/skip/stop, transactions, deletion, exact CSV values, reopened SQLite sessions, synthetic/real separation, matched comparisons, variable-rate video timestamps, deterministic landmark fixtures, real-model positive/negative video replay, and actual Qt UI interactions.

Detector tests explicitly skip if the model is missing. A successful run with skips does not verify those paths. The positive detector fixture is a cartoon, not a human accuracy validation. Repeat-run regression requires identical exported sample rows and analysis outputs on the same installed environment. Cross-architecture numerical identity is not guaranteed; algorithm version, settings, model checksum and runtime versions must be retained when studying reproducibility.

## Regenerate evidence

```sh
.venv/bin/python scripts/make_fixtures.py
.venv/bin/python -m jrm --data-dir /tmp/jrm-check --simulate --export evidence/full-synthetic.csv
.venv/bin/python -m jrm --data-dir /tmp/jrm-check --config data/short_assessment.json --analyze-video data/cartoon_assessment.mp4 --synthetic-video --export evidence/cartoon-replay.csv
QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/capture_evidence.py
```

For screenshots, `capture_evidence.py` opens the actual UI, selects synthetic input, calibrates, completes a timed assessment, reopens its SQLite record, exports it and closes acquisition. Preview sampling depends on host performance. Results plots use saved data; tests compare plotted y values with stored numeric values. Do not alter evidence files to make results look better.

## Manual macOS/webcam acceptance — still required

1. Freshly extract the ZIP on an Apple Silicon Mac (macOS 12+) with Python 3.12; open `run.command`. Confirm the isolated install and initial model retrieval.
2. Complete a Demo assessment, reopen it after relaunch, and compare exported CSV/JSON with displayed results.
3. Open the actual camera and grant permissions. Confirm one-face landmarks and visibly changing normalized opening.
4. Verify that no face, a second face, strong rotation, poor positioning and occluded lips prevent usable recording. Detector limitations may require improvements; do not merely widen thresholds.
5. Calibrate while resting. Move the camera significantly and verify invalidation requires recalibration.
6. Record comfortable movements with a resting start/end. Inspect cycles in the graph and raw timestamps. Pause/resume; confirm no cycle spans the pause.
7. Stop mid-assessment, reopen the partial session and export. Close the app while recording; confirm camera release and retained partial data.
8. Process a locally authorized video following the configured protocol. Run twice with the same environment/settings; compare measurements and quality flags.
9. Repeat across lighting, frame rates, skin tones, facial hair and camera models before any claim of reliable human use. A university study needs the appropriate institutional review/determination and supervision.

The repository's GitHub Actions configuration runs model and UI tests on Linux, macOS, and Windows when permitted by the repository's Actions settings. An included workflow is not evidence that those hosted runs have passed; consult the actual run status.

## Checkpoint 4 additions

Use [MACOS_VERIFICATION.md](MACOS_VERIFICATION.md) for the exact installation and physical camera acceptance protocol. `tests/test_checkpoint4.py` covers processing FPS and delivered dimensions, supported/unsupported discovery, cleanup/error paths, five full cycles with partial movements and head motion, peak/frequency resets, and agreement with saved analysis. `tests/test_ui.py` also verifies discovery selection/manual fallback and indicator rendering/reset.

Generated files are not committed. The session fixture in `tests/conftest.py` generates missing replay fixtures; CI explicitly runs `scripts/make_fixtures.py`. For local screenshot evidence, create `evidence/` and run `scripts/capture_evidence.py`; its outputs are ignored by git.
