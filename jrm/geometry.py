"""Image-plane geometry, with pixel aspect ratio handled before normalization."""
from dataclasses import dataclass
import math
import numpy as np
from .config import Settings

INDICES = (1, 10, 13, 14, 33, 61, 152, 263, 291)

@dataclass
class Observation:
    faces: list[np.ndarray]
    width: int
    height: int
    # approximate yaw, pitch, roll from the detector's face transformation matrix
    pose: tuple[float, float, float] | None = None


def rotation_angles(matrix):
    r = np.asarray(matrix, float)[:3, :3]
    u, _, vt = np.linalg.svd(r)
    r = u @ vt
    if np.linalg.det(r) < 0:
        u[:, -1] *= -1
        r = u @ vt
    yaw = math.atan2(-r[2, 0], math.hypot(r[0, 0], r[1, 0]))
    pitch = math.atan2(r[2, 1], r[2, 2])
    roll = math.atan2(r[1, 0], r[0, 0])
    return tuple(float(math.degrees(x)) for x in (yaw, pitch, roll))


def geometry(obs: Observation, cfg: Settings):
    flags = []
    result = {"face_count": len(obs.faces)}
    if not obs.faces:
        return result, ["no_face"]
    if len(obs.faces) != 1:
        return result, ["multiple_faces"]
    points = np.asarray(obs.faces[0], float)
    if points.ndim != 2 or points.shape[0] <= max(INDICES) or points.shape[1] < 2:
        return result, ["missing_landmarks"]
    p = points[list(INDICES), :2]
    if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        return result, ["invalid_landmarks"]
    xy = points[:, :2] * [obs.width, obs.height]
    eye = xy[263] - xy[33]
    ref = float(np.linalg.norm(eye))
    if ref < 1 or obs.width <= 0 or obs.height <= 0:
        return result, ["invalid_reference"]
    axis = eye / ref
    eye_center = (xy[33] + xy[263]) / 2
    mouth_center = (xy[61] + xy[291]) / 2
    opening = float(np.linalg.norm(xy[14] - xy[13]) / ref)
    lateral = float(np.dot(mouth_center - eye_center, axis) / ref)
    result.update(opening_raw=opening, lateral_raw=lateral, eye_px=ref,
                  eye_fraction=ref / obs.width,
                  center_x=float(eye_center[0] / obs.width),
                  center_y=float(eye_center[1] / obs.height))
    for i in INDICES:
        result[f"lm_{i}_x"] = float(points[i, 0])
        result[f"lm_{i}_y"] = float(points[i, 1])
    if not cfg.min_eye_fraction <= ref / obs.width <= cfg.max_eye_fraction:
        flags.append("distance")
    if not .25 <= result["center_x"] <= .75 or not .18 <= result["center_y"] <= .6:
        flags.append("position")
    if opening > 1.2:
        flags.append("implausible_opening")
    if obs.pose is None or not np.isfinite(obs.pose).all():
        flags.append("pose_unavailable")
    else:
        yaw, pitch, roll = obs.pose
        result.update(yaw=float(yaw), pitch=float(pitch), roll=float(roll))
        if abs(yaw) > cfg.max_yaw or abs(pitch) > cfg.max_pitch or abs(roll) > cfg.max_roll:
            flags.append("head_rotation")
    return result, flags
