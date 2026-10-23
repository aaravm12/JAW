"""Live monotonic acquisition and presentation-timestamp video decoding."""
import sys
import time
import cv2

class Camera:
    def __init__(self, index=0):
        backend = cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY
        self.cap = cv2.VideoCapture(index, backend)
        if not self.cap.isOpened():
            self.cap.release()
            raise RuntimeError("Cannot open camera. Close other camera apps. On macOS allow Terminal/Python under System Settings → Privacy & Security → Camera, then relaunch. Try another camera index.")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.origin = time.monotonic()
        self.index = 0

    def read(self):
        ok, frame = self.cap.read()
        t = time.monotonic() - self.origin
        if not ok:
            raise RuntimeError("Camera stopped providing frames. This assessment will be saved as interrupted.")
        index = self.index
        self.index += 1
        return index, t, frame

    def close(self):
        self.cap.release()

class Video:
    def __init__(self, path):
        import av
        self.container = av.open(str(path))
        if not self.container.streams.video:
            self.container.close()
            raise ValueError("This file has no video stream.")
        self.stream = self.container.streams.video[0]
        self.iterator = iter(self.container.decode(self.stream))
        self.origin = None
        self.last_t = None
        self.index = 0

    def read(self):
        try:
            frame = next(self.iterator)
        except StopIteration:
            return None
        if frame.pts is None or frame.time_base is None:
            raise ValueError("Video lacks frame presentation timestamps. Convert it to a timestamped video before analysis.")
        pts = float(frame.pts * frame.time_base)
        if self.origin is None:
            self.origin = pts
        t = pts - self.origin
        if self.last_t is not None and t <= self.last_t:
            raise ValueError("Video frame timestamps are not strictly increasing; analysis stopped without inventing times.")
        self.last_t = t
        index = self.index
        self.index += 1
        return index, t, frame.to_ndarray(format="bgr24")

    def close(self):
        self.container.close()
