import json
import logging
from pathlib import Path
import queue
import time
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QComboBox, QSpinBox, QDoubleSpinBox, QProgressBar,
    QTextEdit, QListWidget, QListWidgetItem, QAbstractItemView, QFileDialog, QMessageBox,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QGroupBox, QFormLayout)
from .config import Settings, PHASES, INSTRUCTIONS
from .storage import Storage
from .worker import CaptureWorker
from .cameras import CameraDiscovery
from .charts import plot_widget, show_session, plot_data
from .geometry import INDICES
from .analytics import compare_sessions

log = logging.getLogger(__name__)
STYLE = """
QMainWindow, QWidget { background: #101C29; color: #EDF3F6; font-family: Arial; font-size: 13px; }
QLabel#brand { font-size: 27px; font-weight: bold; }
QLabel#muted { color: #AABCCC; }
QLabel#value { font-size: 30px; color: #62D9BE; font-weight: bold; }
QPushButton { background: #243B50; border: 1px solid #3B5266; border-radius: 6px; padding: 9px 14px; }
QPushButton:hover { background: #314D64; }
QPushButton:disabled { color: #627486; background: #182735; }
QPushButton#primary { background: #246B5C; border-color: #62D9BE; }
QPushButton#stop { background: #713A40; border-color: #CF8285; }
QTabBar::tab { background: #1B2C3D; padding: 10px 20px; }
QTabBar::tab:selected { background: #31516B; }
QComboBox, QSpinBox, QDoubleSpinBox { background: #203549; padding: 6px; }
QTextEdit, QListWidget, QTableWidget { background: #152535; border: 1px solid #30465A; }
QHeaderView::section { background: #263F55; padding: 6px; }
QProgressBar { border: 1px solid #3A5364; text-align: center; min-height: 18px; }
QProgressBar::chunk { background: #246B5C; }
QGroupBox { border: 1px solid #30465A; border-radius: 6px; margin-top: 16px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; }
"""

def label(text, name=None):
    out = QLabel(text)
    out.setWordWrap(True)
    if name:
        out.setObjectName(name)
    return out


def button(text, callback, name=None):
    b = QPushButton(text)
    b.clicked.connect(callback)
    if name:
        b.setObjectName(name)
    return b

class MainWindow(QMainWindow):
    def __init__(self, data_dir=None, cfg=None):
        super().__init__()
        self.setWindowTitle("Jaw Recovery Monitor • Research prototype")
        self.resize(1220, 880)
        self.setMinimumSize(980, 740)
        self.setStyleSheet(STYLE)
        self.store = Storage(data_dir)
        self.cfg = cfg or Settings()
        self.worker = None
        self.discovery = None
        self.latest = None
        self.live_rows = []
        self.selected_session = None
        self.last_packet_wall = 0.
        self.started_wall = 0.
        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(24, 20, 24, 16)
        root.addWidget(label("Jaw Recovery Monitor", "brand"))
        root.addWidget(label("CAMERA-ONLY RESEARCH PROTOTYPE  •  Observable mouth movement, locally recorded", "muted"))
        self.banner = label("Experimental, not diagnostic. Lip geometry is not direct jaw-joint motion. Stop if uncomfortable.")
        root.addWidget(self.banner)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self.build_setup()
        self.build_live()
        self.build_results()
        self.build_history()
        self.build_engineering()
        self.setCentralWidget(container)
        self.refresh_participants()
        self.refresh_history()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(40)
        log.info("Main interface initialized")

    def build_setup(self):
        page, layout = QWidget(), QVBoxLayout()
        page.setLayout(layout)
        layout.addWidget(label("1. Choose a participant and input", "brand"))
        row = QHBoxLayout()
        self.participants = QComboBox()
        row.addWidget(label("Anonymous participant"))
        row.addWidget(self.participants, 1)
        row.addWidget(button("New participant", self.new_participant))
        layout.addLayout(row)
        inputs = QHBoxLayout()
        self.camera_choices = QComboBox()
        self.camera_choices.addItem("Manual camera index", None)
        self.camera_choices.currentIndexChanged.connect(self.select_camera)
        inputs.addWidget(self.camera_choices)
        self.camera_index = QSpinBox()
        self.camera_index.setRange(0, 99)
        inputs.addWidget(label("Camera index"))
        inputs.addWidget(self.camera_index)
        self.discover_button = button("Find cameras", self.find_cameras)
        inputs.addWidget(self.discover_button)
        self.camera_button = button("Open webcam", lambda: self.start_input("webcam"), "primary")
        self.demo_button = button("Demo • synthetic", lambda: self.start_input("synthetic"))
        self.video_button = button("Analyze video…", self.open_video)
        inputs.addWidget(self.camera_button)
        inputs.addWidget(self.demo_button)
        inputs.addWidget(self.video_button)
        layout.addLayout(inputs)
        self.discovery_status = label("Find cameras briefly opens candidate devices; permission may be requested. Manual index is always available.", "muted")
        layout.addWidget(self.discovery_status)
        self.synthetic_video = QCheckBox("Imported video is synthetic (enable for the bundled cartoon fixture)")
        layout.addWidget(self.synthetic_video)
        layout.addWidget(label("Webcam: only measurements are stored, never video. Video replay: the first stable 2 seconds are used for calibration, then the configured phases begin automatically. Use a resting lead-in and matching phase timing.", "muted"))
        box = QGroupBox("Assessment settings • seconds")
        form = QFormLayout(box)
        self.duration_inputs = []
        for name, seconds in zip(PHASES, self.cfg.durations):
            spin = QSpinBox()
            spin.setRange(2, 600)
            spin.setValue(int(seconds))
            form.addRow(name.replace("_", " ").title(), spin)
            self.duration_inputs.append(spin)
        self.cadence = QDoubleSpinBox()
        self.cadence.setRange(.05, .5)
        self.cadence.setSingleStep(.05)
        self.cadence.setValue(self.cfg.cadence_hz)
        form.addRow("Movement pace (cycles / second)", self.cadence)
        layout.addWidget(box)
        layout.addWidget(label("2. Calibrate before recording\nUse even front lighting and one visible face. Keep your eyes near the guide line, face forward, and hold your relaxed jaw still. Calibration checks distance, position, rotation, and reference stability."))
        layout.addWidget(label("A different camera position can change the measurement. If the reference shifts substantially, stop, reposition, and recalibrate. A completed cycle must return to the calibrated resting range."))
        layout.addStretch()
        self.tabs.addTab(page, "Setup")

    def build_live(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        top = QHBoxLayout()
        self.mode_label = label("No input selected", "brand")
        self.value = label("—", "value")
        top.addWidget(self.mode_label, 1)
        top.addWidget(self.value)
        layout.addLayout(top)
        self.input_stats = label("Processing FPS: —  •  Frame size: —")
        self.movement_stats = label("Phase peak: —  •  Movement frequency: —")
        layout.addWidget(self.input_stats)
        layout.addWidget(self.movement_stats)
        self.video = QLabel("Choose Webcam, Demo, or Video in Setup.")
        self.video.setAlignment(Qt.AlignCenter)
        self.video.setMinimumSize(480, 260)
        self.video.setMaximumHeight(340)
        layout.addWidget(self.video)
        self.quality = label("Waiting for input")
        layout.addWidget(self.quality)
        self.calibration_bar = QProgressBar()
        layout.addWidget(self.calibration_bar)
        controls = QHBoxLayout()
        self.calibrate_button = button("Calibrate", lambda: self.send("calibrate"))
        self.start_button = button("Start assessment", lambda: self.send("start"), "primary")
        self.pause_button = button("Pause", self.pause_resume)
        self.skip_button = button("Skip optional phase", lambda: self.send("skip"))
        self.stop_button = button("Stop & save", lambda: self.send("stop"), "stop")
        self.restart_button = button("Restart + calibrate", lambda: self.send("restart"))
        self.close_input_button = button("Close input", self.stop_input)
        for b in (self.calibrate_button, self.start_button, self.pause_button, self.skip_button, self.stop_button, self.restart_button, self.close_input_button):
            controls.addWidget(b)
        layout.addLayout(controls)
        self.phase_label = label("Calibration required")
        self.instructions = label("Remain comfortable; do not continue through pain.")
        layout.addWidget(self.phase_label)
        layout.addWidget(self.instructions)
        self.phase_bar = QProgressBar()
        layout.addWidget(self.phase_bar)
        self.live_plot = plot_widget()
        self.live_plot.setMinimumHeight(140)
        self.live_curve = self.live_plot.plot(pen="#62D9BE", connect="finite")
        layout.addWidget(self.live_plot, 1)
        self.tabs.addTab(page, "Live assessment")
        self.enable_controls(None)

    def build_results(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.results_title = label("No session selected", "brand")
        layout.addWidget(self.results_title)
        self.results_info = label("Complete an assessment, or reopen one from Sessions.", "muted")
        layout.addWidget(self.results_info)
        self.result_plot = plot_widget("Recorded mouth opening • gaps are invalid data")
        layout.addWidget(self.result_plot, 2)
        self.table = QTableWidget(4, 6)
        self.table.setHorizontalHeaderLabels(["Phase", "Valid frames", "Mean opening", "Peak opening", "Cycles", "Mean excursion (s)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table, 1)
        layout.addWidget(label("Mean and peak opening are lip-gap / outer-eye-distance ratios. Cycle timing is derived from complete threshold crossings. These are engineering measurements, not clinical scores."))
        layout.addWidget(label("Recovery time not established from this measurement.\nNo muscle fatigue, force, neurological status, or clinical recovery is inferred."))
        self.export_button = button("Export CSV + metadata JSON…", self.export_selected)
        layout.addWidget(self.export_button)
        self.tabs.addTab(page, "Results")

    def build_history(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(label("Saved assessments", "brand"))
        layout.addWidget(label("Select one to reopen. Select multiple for a same-participant comparison. Synthetic, webcam, and replay data stay separate.", "muted"))
        self.history = QListWidget()
        self.history.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.history.itemDoubleClicked.connect(lambda _: self.reopen_selected())
        layout.addWidget(self.history, 2)
        actions = QHBoxLayout()
        for text, fn in (("Refresh", self.refresh_history), ("Reopen", self.reopen_selected),
                         ("Compare", self.compare_selected), ("Delete selected…", self.delete_selected),
                         ("Delete participant…", self.delete_participant)):
            actions.addWidget(button(text, fn))
        layout.addLayout(actions)
        self.comparison = QTextEdit()
        self.comparison.setReadOnly(True)
        self.comparison.setPlaceholderText("Select at least two complete assessments with matching settings to compare observed movement amplitudes and cycle timing.")
        layout.addWidget(self.comparison, 1)
        self.comparison_plot = plot_widget("Selected sessions • observed movement amplitude")
        self.comparison_plot.setLabel("left", "Mean excursion amplitude", units="ratio")
        self.comparison_plot.setLabel("bottom", "Session date")
        layout.addWidget(self.comparison_plot, 1)
        self.tabs.addTab(page, "Sessions / compare")

    def build_engineering(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(label("Engineering view", "brand"))
        self.engineering = QTextEdit()
        self.engineering.setReadOnly(True)
        layout.addWidget(self.engineering)
        layout.addWidget(label("Quality flags invalidate filtered values but retain available raw geometry for inspection. Missing detections remain blank. Detector confidence thresholds are configuration, not per-frame confidence estimates.\n\nEMG: no device connected; hardware acquisition is not implemented."))
        self.tabs.addTab(page, "Engineering")

    def refresh_participants(self):
        old = self.participants.currentText()
        ids = self.store.participants()
        if not ids:
            ids = [self.store.participant()]
        self.participants.clear()
        self.participants.addItems(ids)
        if old in ids:
            self.participants.setCurrentText(old)

    def new_participant(self):
        pid = self.store.participant()
        self.refresh_participants()
        self.participants.setCurrentText(pid)

    def read_settings(self):
        values = self.cfg.to_dict()
        values.update(durations=tuple(float(s.value()) for s in self.duration_inputs), cadence_hz=self.cadence.value())
        return Settings(**values)

    def select_camera(self):
        index = self.camera_choices.currentData()
        self.camera_index.setEnabled(index is None)
        if index is not None:
            self.camera_index.setValue(index)

    def find_cameras(self):
        if (self.worker and self.worker.isRunning()) or (self.discovery and self.discovery.isRunning()):
            return
        self.discovery = CameraDiscovery()
        self.discovery.discovered.connect(self.on_cameras)
        self.discovery.error.connect(self.discovery_status.setText)
        self.discovery.finished.connect(lambda: self.enable_controls(self.latest))
        self.discovery_status.setText("Looking for cameras… Manual selection remains available after the scan.")
        self.discovery.start()
        self.enable_controls(self.latest)

    def on_cameras(self, cameras):
        previous = self.camera_index.value()
        self.camera_choices.clear()
        self.camera_choices.addItem("Manual camera index", None)
        for camera in cameras:
            self.camera_choices.addItem(camera['name'], camera['index'])
        match = self.camera_choices.findData(previous)
        if cameras:
            self.camera_choices.setCurrentIndex(match if match > 0 else 1)
        self.discovery_status.setText(
            f"Found {len(cameras)} camera(s). Confirm the preview after opening. Choose Manual for another index."
            if cameras else "No available cameras found. Check permission, close other camera apps, or enter an index manually.")

    def clear_live_indicators(self):
        self.input_stats.setText("Processing FPS: —  •  Frame size: —")
        self.movement_stats.setText("Phase peak: —  •  Movement frequency: —")
        self.value.setText("— ratio")

    def open_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open video with resting calibration lead-in", "", "Videos (*.mp4 *.mov *.mkv *.avi);;All files (*)")
        if path:
            self.start_input("video", path)

    def start_input(self, mode, path=None):
        if self.discovery and self.discovery.isRunning():
            self.statusBar().showMessage("Wait for camera discovery to finish before opening an input.")
            return
        if not self.stop_input():
            return
        self.cfg = self.read_settings()
        self.live_rows, self.latest = [], None
        self.clear_live_indicators()
        self.started_wall = self.last_packet_wall = time.monotonic()
        self.worker = CaptureWorker(mode, self.cfg, self.store.root, self.participants.currentText(), self.camera_index.value(), path, self.synthetic_video.isChecked())
        self.worker.error.connect(self.show_error)
        self.worker.notice.connect(self.statusBar().showMessage)
        self.worker.saved.connect(self.on_saved)
        self.worker.finished.connect(self.input_finished)
        self.worker.start()
        self.enable_controls(None)
        self.tabs.setCurrentIndex(1)
        self.mode_label.setText({"synthetic": "SYNTHETIC DEMO", "webcam": "LIVE WEBCAM", "video": "OFFLINE VIDEO"}[mode] + (" • SYNTHETIC" if mode == "video" and self.synthetic_video.isChecked() else ""))
        self.banner.setText("SIMULATED DATA • Software demonstration only. No webcam or human measurements." if mode == "synthetic" or (mode == "video" and self.synthetic_video.isChecked()) else "Experimental, not diagnostic. Lip geometry is not direct jaw-joint motion. Stop if uncomfortable.")
        self.quality.setText("Initializing input and detector…")
        log.info("Input requested: %s", mode)

    def stop_input(self):
        if self.worker and self.worker.isRunning():
            self.worker.command("quit")
            if not self.worker.wait(5000):
                self.show_error("Camera/decoder is still shutting down. Wait and try Close input again.")
                return False
        self.enable_controls(None)
        self.clear_live_indicators()
        return True

    def input_finished(self):
        self.enable_controls(None)
        self.clear_live_indicators()

    def send(self, action):
        if self.worker and self.worker.isRunning():
            if action in ("start", "restart"):
                self.live_rows = []
            self.worker.command(action)

    def pause_resume(self):
        self.send("resume" if self.latest and self.latest["state"] == "paused" else "pause")

    def enable_controls(self, packet):
        scanning = bool(self.discovery and self.discovery.isRunning())
        capturing = bool(self.worker and self.worker.isRunning())
        self.discover_button.setEnabled(not scanning and not capturing)
        self.camera_choices.setEnabled(not scanning and not capturing)
        self.camera_index.setEnabled(not scanning and not capturing and self.camera_choices.currentData() is None)
        for b in (self.camera_button, self.demo_button, self.video_button):
            b.setEnabled(not scanning)
        active = bool(packet and self.worker and self.worker.isRunning())
        state = packet["state"] if packet else "idle"
        self.calibrate_button.setEnabled(active and state in ("idle", "finished", "stopped"))
        self.start_button.setEnabled(active and state in ("idle", "finished", "stopped") and packet["row"]["valid"])
        self.pause_button.setEnabled(active and state in ("running", "paused"))
        self.pause_button.setText("Resume" if state == "paused" else "Pause")
        self.stop_button.setEnabled(active and state in ("running", "paused"))
        self.skip_button.setEnabled(active and state == "running" and packet["phase"] in ("activity", "post_activity"))
        self.restart_button.setEnabled(active)
        self.close_input_button.setEnabled(bool(self.worker and self.worker.isRunning()))

    def poll(self):
        if not self.worker or not self.worker.isRunning():
            return
        try:
            packet = self.worker.preview.get_nowait()
        except queue.Empty:
            if self.worker.isRunning() and time.monotonic() - self.last_packet_wall > 3:
                self.quality.setText("No recent frames. Measurements are unavailable; check camera/input.")
                self.start_button.setEnabled(False)
                self.clear_live_indicators()
            return
        self.latest = packet
        self.last_packet_wall = time.monotonic()
        row = packet["row"]
        self.enable_controls(packet)
        v = row.get("opening")
        self.value.setText(f"{v:.3f} ratio" if v is not None else "— ratio")
        self.update_live_indicators(packet)
        quality = "Tracking usable" if row["valid"] else "Measurements unavailable: " + row["flags"].replace("|", ", ")
        if packet["calibrating"] or not packet["calibration"]:
            quality += " • " + packet["calibration_message"]
        self.quality.setText(quality)
        self.calibration_bar.setValue(round(100 * packet["calibration_progress"]))
        self.calibration_bar.setFormat("Calibration ready" if packet["calibration"] else "Calibration %p%")
        duration = self.cfg.durations[PHASES.index(packet["phase"])]
        self.phase_label.setText(f"{packet['state'].upper()}  •  {packet['phase'].replace('_',' ').title()}  •  {max(0,duration-packet['phase_elapsed']):.1f} s remaining  •  {packet['cycles']} complete cycles")
        instruction = INSTRUCTIONS[packet["phase"]]
        if packet["state"] == "running" and packet["phase"] in ("controlled", "activity"):
            instruction += "   Pace: " + ("gently OPEN" if (packet["phase_elapsed"] * self.cfg.cadence_hz) % 1 < .5 else "gently CLOSE")
        self.instructions.setText(instruction)
        self.phase_bar.setValue(round(100 * packet["phase_elapsed"] / duration))
        self.render_frame(packet)
        # Preview may drop frames; the recorder owns the complete processed stream.
        self.live_rows.append(row)
        self.live_rows = self.live_rows[-900:]
        self.live_curve.setData(*plot_data(self.live_rows), connect="finite")
        diagnostics = {"source": packet["mode"], "state": packet["state"],
                       "last_frame": row, "calibration": packet["calibration"],
                       "filter": {"type": "time-aware EMA", "tau_s": self.cfg.smoothing_tau},
                       "EMG": "not implemented"}
        self.engineering.setPlainText(json.dumps(diagnostics, indent=2))

    def update_live_indicators(self, packet):
        stats = packet['telemetry']
        fps = '—' if stats['processing_fps'] is None else f"{stats['processing_fps']:.1f}"
        self.input_stats.setText(f"Processing FPS: {fps}  •  Frame size: {stats['width']} × {stats['height']} px")
        peak, frequency = packet['peak_opening'], packet['frequency_hz']
        peak_text = '—' if peak is None else f'{peak:.3f} ratio'
        hz_text = '— (needs 2 complete cycles)' if frequency is None else f'{frequency:.3f} Hz'
        self.movement_stats.setText(f'Phase peak: {peak_text}  •  Movement frequency: {hz_text}')

    def render_frame(self, packet):
        import cv2
        frame = packet["frame"].copy()
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (int(.23*w), int(.12*h)), (int(.77*w), int(.92*h)), (142, 160, 173), 1)
        cv2.line(frame, (int(.3*w), int(.36*h)), (int(.7*w), int(.36*h)), (142, 160, 173), 1)
        for face in packet["observation"].faces:
            for i in INDICES:
                if i < len(face) and np.isfinite(face[i, :2]).all():
                    p = tuple((face[i, :2] * [w, h]).astype(int))
                    cv2.circle(frame, p, 3, (160, 225, 100), -1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888).copy()
        pix = QPixmap.fromImage(qimg).scaled(self.video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video.setPixmap(pix)

    def on_saved(self, sid):
        self.selected_session = sid
        self.refresh_history()
        self.load_result(sid)
        self.statusBar().showMessage("Assessment saved locally. Open Results or Sessions to review/export.")
        log.info("Session saved and reopened: %s", sid)

    def load_result(self, sid):
        meta, rows = self.store.load(sid)
        self.selected_session = sid
        kind = "SYNTHETIC" if meta["simulated"] else meta["source_kind"].upper()
        self.results_title.setText(f"{kind} • {meta['status'].replace('_', ' ').title()}")
        self.results_info.setText(f"{meta['participant_id']}  |  {meta['started_at']}  |  {len(rows)} recorded frames\nSession {sid}")
        show_session(self.result_plot, rows)
        for i, phase in enumerate(PHASES):
            s = meta["analysis"]["phases"][phase]
            fmt = lambda n: "—" if n is None else f"{n:.3f}"
            values = [phase.replace("_", " ").title(), f"{s['valid_frames']} / {s['frames']}", fmt(s["mean_opening"]), fmt(s["max_opening"]), str(s["complete_cycles"]), ("—" if s["mean_cycle_s"] is None else f"{s['mean_cycle_s']:.2f}")]
            for j, value in enumerate(values):
                self.table.setItem(i, j, QTableWidgetItem(value))
        self.engineering.setPlainText(json.dumps(meta, indent=2))

    def refresh_history(self):
        self.history.clear()
        for meta in self.store.sessions():
            kind = "SYNTHETIC" if meta["simulated"] else meta["source_kind"].upper()
            item = QListWidgetItem(f"{kind} | {meta['started_at'][:19]} | {meta['participant_id']} | {meta['status']} | {meta['session_id'][:8]}")
            item.setData(Qt.UserRole, meta["session_id"])
            self.history.addItem(item)

    def selected_ids(self):
        return [i.data(Qt.UserRole) for i in self.history.selectedItems()]

    def reopen_selected(self):
        ids = self.selected_ids()
        if len(ids) == 1:
            self.load_result(ids[0])
            self.tabs.setCurrentIndex(2)
        else:
            self.statusBar().showMessage("Select exactly one session to reopen.")

    def compare_selected(self):
        try:
            values = compare_sessions([self.store.load(sid)[0] for sid in self.selected_ids()])
            text = ["EXPLORATORY COMPARISON • no clinical interpretation", "Absolute changes relative to the first selected assessment:\n"]
            for r in values:
                text.append(f"{r['date'][:19]} | amplitude {r['mean_amplitude']:.3f} | change {r['amplitude_change']:+.3f} | cycle {r['mean_cycle_s']:.2f} s")
            self.comparison.setPlainText("\n".join(text))
            self.comparison_plot.clear()
            self.comparison_plot.plot(list(range(len(values))), [r["mean_amplitude"] for r in values], pen="#62D9BE", symbol="o")
            self.comparison_plot.getAxis("bottom").setTicks([[(i, r["date"][:10]) for i, r in enumerate(values)]])
        except ValueError as exc:
            self.comparison.setPlainText(str(exc))
            self.comparison_plot.clear()

    def export_selected(self):
        if not self.selected_session:
            self.statusBar().showMessage("Open a saved assessment first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export measurements and metadata", "assessment.csv", "CSV (*.csv)")
        if path:
            try:
                self.store.export(self.selected_session, path)
                self.statusBar().showMessage("Exported CSV and companion JSON metadata.")
            except Exception as exc:
                self.show_error(str(exc))

    def delete_selected(self):
        ids = self.selected_ids()
        if ids and QMessageBox.question(self, "Delete assessments", f"Delete {len(ids)} saved assessment(s)? Exported copies will remain.") == QMessageBox.Yes:
            if not self.stop_input():
                return
            for sid in ids:
                self.store.delete(sid)
            if self.selected_session in ids:
                self.selected_session = None
                self.result_plot.clear()
                self.results_title.setText("Assessment deleted")
            self.refresh_history()

    def delete_participant(self):
        pid = self.participants.currentText()
        if QMessageBox.question(self, "Delete participant", f"Delete {pid} and all associated local assessments? Exported copies will remain.") == QMessageBox.Yes:
            if not self.stop_input():
                return
            self.store.delete_participant(pid)
            self.selected_session = None
            self.refresh_participants()
            self.refresh_history()

    def show_error(self, text):
        log.error(text)
        self.quality.setText(text)
        self.statusBar().showMessage(text)
        self.enable_controls(None)
        self.clear_live_indicators()

    def closeEvent(self, event):
        if self.discovery and self.discovery.isRunning():
            self.discovery.requestInterruption()
            if not self.discovery.wait(5000):
                self.discovery_status.setText("Camera discovery is still closing. Wait, then close again.")
                event.ignore()
                return
        if not self.stop_input():
            event.ignore()
            return
        self.timer.stop()
        self.store.close()
        log.info("Application closed; acquisition resources released")
        event.accept()
