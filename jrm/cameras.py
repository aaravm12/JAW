"""Bounded, cancellable OpenCV discovery; no frames or images are stored."""
from pathlib import Path
import sys
import cv2
from PySide6.QtCore import QThread, Signal


def discover_cameras(cancelled=lambda: False):
    # Linux device nodes can be sparse. Other backends expose integer indices.
    if sys.platform.startswith("linux"):
        candidates = sorted(int(p.name[5:]) for p in Path('/dev').glob('video*')
                            if p.name[5:].isdigit())
    elif sys.platform in ('darwin', 'win32'):
        candidates = range(10)
    else:
        return []
    backend = cv2.CAP_AVFOUNDATION if sys.platform == 'darwin' else cv2.CAP_ANY
    found = []
    for index in candidates:
        if cancelled():
            break
        cap = None
        try:
            cap = cv2.VideoCapture(index, backend)
            if cap.isOpened():
                found.append({"index": index, "name": f"Camera {index}"})
        except (cv2.error, OSError):
            continue
        finally:
            if cap is not None:
                cap.release()
    return found


class CameraDiscovery(QThread):
    discovered = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            self.discovered.emit(discover_cameras(self.isInterruptionRequested))
        except Exception as exc:
            self.error.emit(f"Camera discovery unavailable: {exc}. Enter an index manually.")
