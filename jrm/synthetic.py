"""Original deterministic synthetic geometry; never claims ML inference."""
import math
import numpy as np
from .geometry import Observation


def synthetic_observation(t, phase="baseline", cadence=.25, width=640, height=480):
    opening = .015
    if phase in ("controlled", "activity"):
        opening += .27 * (1 - math.cos(2 * math.pi * cadence * t)) / 2
    points = np.tile([.5, .5, 0.], (478, 1))
    points[33, :2], points[263, :2] = [.34, .36], [.66, .36]
    points[1, :2], points[10, :2], points[152, :2] = [.5, .49], [.5, .19], [.5, .82]
    points[61, :2], points[291, :2] = [.4, .64], [.6, .64]
    gap = opening * .32 * width / height
    points[13, :2], points[14, :2] = [.5, .64 - gap / 2], [.5, .64 + gap / 2]
    return Observation([points], width, height, (0., 0., 0.))


def draw_synthetic(obs):
    import cv2
    img = np.full((obs.height, obs.width, 3), (34, 28, 21), dtype=np.uint8)
    cv2.ellipse(img, (obs.width // 2, obs.height // 2), (145, 192), 0, 0, 360, (76, 65, 48), 2)
    p = obs.faces[0][:, :2] * [obs.width, obs.height]
    for i in (33, 263):
        cv2.circle(img, tuple(p[i].astype(int)), 9, (205, 215, 223), 2)
    a, b = p[13].astype(int), p[14].astype(int)
    center = tuple(((a + b) / 2).astype(int))
    cv2.ellipse(img, center, (64, max(2, int((b[1] - a[1]) / 2))), 0, 0, 360, (170, 220, 75), 2)
    cv2.putText(img, 'SYNTHETIC / no camera inference', (15, 32), cv2.FONT_HERSHEY_SIMPLEX, .5, (100, 215, 235), 1)
    return img
