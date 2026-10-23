# Jaw Recovery Monitor

A local research prototype for recording **observable mouth movements** with a laptop webcam. It includes guided calibration, four assessment phases, live plots, complete movement-cycle detection, local sessions, CSV/JSON export, deterministic video replay, and a clearly labeled synthetic demo.

**This is not a diagnostic or treatment device.** Lip landmarks are not direct mandibular/TMJ measurements. The application does not calculate muscle fatigue, force, neurological abnormalities, a recovery score, or a pain prediction. Stop if movement is uncomfortable. Systematic human-subject research requires institutional review/determination and appropriate supervision.

## Start on macOS

1. Download this project's ZIP from the **feat/camera-only-mvp** branch on GitHub (**Code → Download ZIP**) and extract it into a folder you can write to.
2. Install **Python 3.12** (or 3.11) from [python.org](https://www.python.org/downloads/macos/). On an Apple Silicon Mac use a native arm64/universal Python, not an Intel-only Rosetta environment.
3. Double-click **`run.command`**. The first launch creates `.venv`, installs the pinned dependencies, retrieves and checks the face model, then opens the app. Internet access is needed for initial setup only.
4. If Finder says the script cannot run, open Terminal in the extracted folder and run:

   ```sh
   chmod +x run.command
   ./run.command
   ```

5. Select **Demo • synthetic** first, then **Calibrate**, hold the synthetic reference until ready, and **Start assessment**. The default protocol takes 3.5 minutes. For a shorter demo choose durations **2 / 8 / 8 / 2** before opening the input.
6. For your webcam choose **Find cameras**, select a discovered index, then **Open webcam**. If discovery finds none, select **Manual camera index** and try index 0 (or the index for your device). Grant camera access to the launching Terminal/Python application when macOS asks. If denied: **System Settings → Privacy & Security → Camera**, enable the relevant app, close JRM, and relaunch.
7. With one face visible, align with the positioning guide, face forward with your jaw relaxed, and click **Calibrate**. Start becomes available only with a usable reference and tracking.
8. Results save automatically. Use **Results → Export CSV + metadata JSON**, or **Sessions → Reopen**. **Stop & save** retains a partial assessment. Close the window normally to release the camera and save an in-progress checkpoint.

This is a development launcher, not a signed/notarized macOS `.app`. macOS 12+ is the practical Qt target. Apple Silicon and Intel dependency paths are supplied; **neither physical macOS launch nor webcam permission flow was executed in the Linux build environment**. Intel uses MediaPipe 0.10.21 because the newer pinned wheel is arm64-only on macOS; it still uses the Tasks API. See [verification](docs/ENGINEERING_REPORT.md).

## Windows

Install Python 3.12 x64 from [python.org](https://www.python.org/downloads/windows/) with the Python launcher (`py`). Extract the project and double-click `run.bat`. Enable camera access for desktop apps in **Settings → Privacy & security → Camera**. The Windows launcher and dependency path are provided but not hardware-tested here.

## Terminal usage

Initial isolated setup and launch:

```sh
python3.12 scripts/setup.py
```

After setup:

```sh
.venv/bin/python -m jrm
.venv/bin/python -m jrm --simulate --export demo.csv
.venv/bin/python scripts/make_fixtures.py
.venv/bin/python -m jrm --config data/short_assessment.json --analyze-video data/cartoon_assessment.mp4 --synthetic-video --export cartoon.csv
```

Windows: replace `.venv/bin/python` with `.venv\Scripts\python.exe`.

Use `--data-dir PATH` for a separate local data folder and `--config config.example.json` for advanced thresholds. UI duration/cadence edits apply when opening an input. `--download-model` retries only model retrieval. `JRM_MODEL_PATH` can point to the official, checksum-matching model if it was downloaded separately.

## Workflow and data

- Four configurable phases: baseline (30 s), controlled movement (30 s), gentle activity (30 s), and post-activity rest (120 s). No clenching or fatigue challenge.
- Pause/resume preserves explicit source timing and excludes paused samples. Only the optional activity/post-activity phases can be skipped; skipped/incomplete sessions are labeled and excluded from comparisons.
- Major repositioning invalidates measurements until a fresh calibration. Missing, implausible or low-quality observations are not filled in.
- **Imported video** must begin with a stable resting reference and follow the selected phase durations. Calibration and phases are assigned from source time, not inferred from activities in an arbitrary video. Processing stops at protocol completion; a shorter video saves a partial session. A failed calibration preserves an invalid debug session.
- Mark synthetic imported videos using the checkbox or CLI flag. Demo, synthetic-video, webcam and human-video sessions have separate source labels and cannot be combined in comparisons.
- The app creates random anonymous participant IDs. Choose the same ID to compare repeat sessions. Select multiple sessions using Command-click (Mac) or Ctrl-click (Windows), then Compare.
- Records are stored locally in SQLite. Default macOS location: `~/Library/Application Support/JawRecoveryMonitor`; Windows: the user's Local AppData `JawRecoveryMonitor` folder; Linux: `~/.local/share/JawRecoveryMonitor`.
- No images/video are saved by default, no cloud processing, and no telemetry. Landmark data can still be sensitive. Local SQLite is not encrypted; access depends on your computer account. Deleting a session/participant removes the app's copy; exported files and backups remain.
- CSV includes original source timestamps, phase, active elapsed time, raw coordinates/geometry, processed values and flags. Blank values mean unavailable, never zero. Companion JSON retains settings, source hash (video), calibration, events and summaries.

## Verification and documentation

- [Engineering report and current limitations](docs/ENGINEERING_REPORT.md)
- [Measurement equations, categories and threshold assumptions](docs/MEASUREMENTS.md)
- [Architecture and first-release scope](docs/ARCHITECTURE.md)
- [Tests and hardware acceptance procedure](docs/TESTING.md)
- [Synthetic fixtures and provenance](data/README.md)
- [Third-party dependencies/model notices](docs/THIRD_PARTY.md)
- Generated logs, screenshots, test videos, and sample exports are excluded from git. The scripts in `scripts/` regenerate them locally.
- [Checkpoint 4 macOS operator verification](docs/MACOS_VERIFICATION.md)

```sh
.venv/bin/python -m jrm --download-model
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

On Windows set `QT_QPA_PLATFORM=offscreen` separately or omit it with an available desktop. Tests requiring the actual model skip with an explicit reason when the model is absent; this must not be interpreted as verified detection.

## Troubleshooting

- **Python not found:** install Python 3.11/3.12, restart Terminal, then run again. Python 3.13+ is intentionally not supported by this lock.
- **Package installation fails:** ensure Internet access and a supported Python/architecture. Error output is retained in Terminal. Delete only this project's `.venv` to retry a clean setup; your sessions are in a different user data folder.
- **macOS certificate error retrieving the model:** run the `Install Certificates.command` supplied in your Python installation, then rerun setup.
- **Model missing:** Demo remains available; rerun setup with Internet access. The checksum is verified; the app does not silently substitute another model.
- **Camera unavailable:** close FaceTime/Zoom/other camera clients, grant permission, or try another camera index. The application retains the error text and remains usable in Demo mode.
- **Calibration will not complete:** use even lighting, one face, a forward orientation and resting jaw. Get closer/farther until the eye-spacing check passes. If performance is very low, close other applications; do not relax quality criteria merely to force a result.
- **No cycles:** only complete, quality-valid low–high–low excursions count. Small movements, an initially open mouth, tracking gaps or a phase boundary can prevent counting. Check Engineering and the CSV flags.
- **Closing input takes time:** a native capture call may take several seconds to return. The window reports a delayed shutdown rather than destroying a running worker. Retry Close input once it returns.

EMG acquisition, clinical validation, recovery modeling, and polished dashboards are deferred. The future sensor contract is explicitly unimplemented.
