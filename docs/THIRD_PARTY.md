# Third-party components and model

The project retrieves Google's versioned MediaPipe Face Landmarker task during setup; it does not redistribute the model binary. URL and SHA-256 are pinned in `jrm/model.py`:

`64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`

Source: https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task

Review [MediaPipe documentation/model information](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker) and upstream terms before redistributing model binaries or a packaged product. Model/library attribution is not a clinical endorsement.

Dependencies are obtained from PyPI, not vendored. MediaPipe and OpenCV use Apache-2.0 licensing; NumPy and PyQtGraph use permissive upstream licenses; PySide6/Qt has LGPLv3/GPLv3/commercial licensing options; PyAV and its FFmpeg components have their own distribution obligations. Review installed distributions' license files before packaging or commercial distribution. This source delivery does not assert compliance for a future bundled binary.

Original synthetic fixture content is CC0-1.0 as stated in `data/README.md`. No project-wide source-code license has been selected on the repository owner's behalf.
