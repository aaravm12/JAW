from pathlib import Path
import hashlib
import urllib.request
import os
from .storage import default_data_dir

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
# Filled from the downloaded versioned official asset; setup verifies it.
MODEL_SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"


def model_path():
    override = os.environ.get("JRM_MODEL_PATH")
    return Path(override) if override else default_data_dir() / "models" / "face_landmarker.task"


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ensure_model():
    path = model_path()
    if path.exists() and (MODEL_SHA256 == "PENDING" or checksum(path) == MODEL_SHA256):
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".download")
    try:
        with urllib.request.urlopen(MODEL_URL, timeout=45) as response, temp.open("wb") as out:
            while block := response.read(1024 * 1024):
                out.write(block)
        if MODEL_SHA256 != "PENDING" and checksum(temp) != MODEL_SHA256:
            raise RuntimeError("Downloaded Face Landmarker model failed its checksum.")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    return path
