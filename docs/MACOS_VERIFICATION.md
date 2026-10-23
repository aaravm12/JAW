# Checkpoint 4: macOS operator installation and hardware verification

**Hardware sign-off is pending.** Development and automated verification ran on Linux with offscreen Qt and synthetic inputs. Neither native Mac launch nor real webcam tracking has been verified. Milestone 5 has not begun.

## 1. Get the correct source

1. Open https://github.com/aaravm12/JAW/tree/feat/camera-only-mvp.
2. Confirm the branch selector says `feat/camera-only-mvp`, then choose **Code → Download ZIP**. Extract it into a writable folder. The initial default branch may contain only the repository placeholder until the pull request is merged.
3. Alternatively, if Git is installed, run:

   ```sh
   git clone --branch feat/camera-only-mvp https://github.com/aaravm12/JAW.git
   cd JAW
   git rev-parse HEAD
   ```

4. Record the commit hash, Mac model, processor (Apple Silicon or Intel), and macOS version in the operator record below.

## 2. Install and launch

1. Use macOS 12 or newer and install Python **3.12** from https://www.python.org/downloads/macos/ (3.11 is also supported by the launcher). Use a native/universal installation on Apple Silicon, not an Intel Python running under Rosetta.
2. Double-click `run.command` in the extracted folder. The launcher creates an isolated `.venv`, installs pinned dependencies, verifies/downloads the landmark model, and opens the desktop application. Initial installation requires Internet access. This is not a signed or notarized `.app`.
3. If double-clicking does not launch it, open Terminal, type `cd `, drag the extracted project folder into Terminal, press Return, then run:

   ```sh
   chmod +x run.command
   ./run.command
   ```

4. To retain a local startup log, use `./run.command 2>&1 | tee macos-startup.log`. Do not commit participant data or generated logs.
5. If setup reports a certificate problem, run the `Install Certificates.command` included with the Python installation, then retry. If setup cannot download the model, Demo can still run but webcam detection is not ready; retry setup with network access.

## 3. Check software behavior before the camera

1. In Setup set phase seconds to **2 / 8 / 8 / 2**. Select **Demo • synthetic**, choose **Calibrate**, wait for Calibration ready, then **Start assessment**.
2. Confirm changing numeric opening, scrolling graph, processing FPS and actual frame size. The phase peak should update. Frequency appears only after two complete cycles in the same uninterrupted phase; it is not the displayed target pace.
3. Pause/resume and confirm the frequency is cleared and a cycle cannot span the pause. Complete the session, reopen it from Sessions, export CSV/JSON, close the app, relaunch, and reopen it again.
4. Optional local automated verification from the project directory:

   ```sh
   .venv/bin/python -m jrm --download-model
   .venv/bin/python scripts/make_fixtures.py
   QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
   ```

   Tests generate their missing synthetic fixtures automatically. Offscreen automated tests on a Mac still do not verify its physical webcam.

## 4. Discover and open the camera

1. Close FaceTime, Zoom, and any application using the camera. Close any active input in JRM.
2. Click **Find cameras**. Discovery runs in a background thread and briefly opens candidate devices without recording frames. macOS/Windows scans OpenCV indices **0–9**; Linux probes existing `/dev/video*` nodes. Busy or inaccessible devices may not appear. Discovery is not a guarantee of usable frames or a stable device identity after hot-plugging.
3. Allow camera access if macOS prompts. If denied, open **System Settings → Privacy & Security → Camera**, enable the launching Terminal/Python application shown by macOS, quit JRM, and relaunch. The exact process name can depend on how Python was installed/launched.
4. Select a discovered camera and click **Open webcam**. Confirm the preview belongs to the intended camera. To use a missing device, select **Manual camera index**, enter an index (try 0 for the built-in camera), and open it. The manual control supports 0–99.
5. Confirm displayed frame dimensions match the delivered image and processing FPS updates. The requested size is 640 × 480 but the camera may deliver something else. Processing FPS is measured application throughput, not the camera's nominal sensor rate.
6. Verify controls remain usable while tracking. If discovery or native capture is slow to close, wait for its completion and retry Close; the app does not forcibly destroy a running worker.

## 5. Five-cycle physical acceptance trial

1. Set phases to **5 / 30 / 2 / 2 seconds**, target pace **0.25 cycles/second**, before opening the camera. Use one face, even lighting, and a stable laptop. Follow the alignment guide and calibrate while resting.
2. Start assessment and remain resting through baseline. In the controlled phase perform **exactly five comfortable complete openings and closings**, roughly four seconds per repetition, with a resting start and end. Remain resting for the rest of that phase. Do not continue if uncomfortable.
3. Pass criteria: the controlled-phase Results row reports **5 cycles**; the graph contains five corresponding valid excursions; there are no tracking gaps across them. Live peak is consistent with the recorded peak. Frequency should be near the actual repetition rate once two cycles complete, not necessarily exactly 0.25 Hz.
4. Separate trial: perform an incomplete opening without returning to rest before Stop. It must not add a complete cycle. Small subthreshold lip motion should not add a cycle.
5. Separate trial: begin an opening, rotate or move the head enough to trigger a quality warning, then return to rest. The interrupted movement must not count. Major repositioning must remain invalid until **Stop & save → Calibrate → Start assessment** (or Restart + calibrate). Record the warning, not just the final count.
6. A failed count is a failed hardware acceptance check. Save the measurement export and quality flags locally for investigation; do not relax thresholds simply to obtain five.

## 6. Failure and lifecycle checks

- Leave the frame, briefly cover the mouth, and introduce a second consenting face: unavailable geometry must be flagged rather than fabricated. This checks actual detector behavior, not just synthetic flag handling.
- For an external camera, disconnect it during a session. Expect a clear error and an interrupted saved session. With a built-in camera, mark physical disconnect testing not applicable; use an external device before claiming that behavior verified.
- Close input and verify camera release. Reopen it, then close the application during recording; reopen the partial saved session. Check that no video file was recorded.
- Repeat discovery with multiple cameras if available. Verify each selection's preview and manually entering its index. Mark multi-camera behavior unverified if only one camera is available.

## Operator record (complete locally)

| Field | Observed value |
|---|---|
| Date, operator, commit hash | Pending |
| Mac model / CPU / macOS / Python version | Pending |
| Camera model(s), selected index, delivered dimensions | Pending |
| Processing FPS range | Pending |
| Initial installation and launch | Pending |
| Permission allow and denied/recovery flow | Pending |
| Discovery, manual fallback, multiple cameras | Pending |
| Five-cycle trial expected / observed / valid frames | Pending |
| Partial cycle and head-movement trials | Pending |
| Responsive UI, camera release, disconnect behavior | Pending |
| Save, reopen, export, restart | Pending |
| Local automated tests and skips | Pending |
| Failures and local evidence paths | Pending |

Keep this record and any measurements local until reviewed. These checks establish software behavior on that setup, not clinical validity or direct TMJ measurement.
