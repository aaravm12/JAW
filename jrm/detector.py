import numpy as np
from .geometry import Observation, rotation_angles
from .model import model_path, checksum, MODEL_SHA256

class FaceDetector:
    def __init__(self):
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode
        path = model_path()
        if not path.exists():
            raise RuntimeError("Face model is missing. Run setup again, or use Demo mode while offline.")
        if MODEL_SHA256 != "PENDING" and checksum(path) != MODEL_SHA256:
            raise RuntimeError("Face model checksum mismatch. Run setup to retrieve the verified model.")
        self.mp = mp
        self.last_ms = -1
        self.landmarker = FaceLandmarker.create_from_options(FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(path), delegate=BaseOptions.Delegate.CPU),
            running_mode=RunningMode.VIDEO, num_faces=2,
            min_face_detection_confidence=.65, min_face_presence_confidence=.65,
            min_tracking_confidence=.65, output_facial_transformation_matrixes=True))

    def detect(self, bgr, t):
        import cv2
        # MediaPipe requires strictly increasing integer milliseconds; original times remain unchanged.
        ms = max(self.last_ms + 1, int(round(t * 1000)))
        self.last_ms = ms
        rgb = np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        result = self.landmarker.detect_for_video(self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb), ms)
        faces = [np.array([[p.x, p.y, p.z] for p in face]) for face in result.face_landmarks]
        pose = rotation_angles(result.facial_transformation_matrixes[0]) if len(faces) == 1 and len(result.facial_transformation_matrixes) else None
        return Observation(faces, bgr.shape[1], bgr.shape[0], pose)

    def close(self):
        self.landmarker.close()
