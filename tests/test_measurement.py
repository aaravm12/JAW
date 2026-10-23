from dataclasses import replace
import math
import numpy as np
import pytest
from jrm.geometry import Observation, geometry, rotation_angles
from jrm.synthetic import synthetic_observation
from jrm.pipeline import Pipeline


def test_normalized_geometry_matches_known_gap(cfg):
    raw, flags = geometry(synthetic_observation(1, "controlled"), cfg)
    assert not flags
    assert raw["opening_raw"] == pytest.approx(.15)
    assert raw["lateral_raw"] == pytest.approx(0.)

@pytest.mark.parametrize("width,height", [(640,480), (1280,720), (800,800)])
def test_pixel_aspect_ratio_normalization(cfg, width, height):
    raw, _ = geometry(synthetic_observation(2, "controlled", width=width, height=height), cfg)
    assert raw["opening_raw"] == pytest.approx(.285)


def test_translation_and_uniform_scaling_do_not_change_ratio(cfg):
    obs = synthetic_observation(1, "controlled")
    before, _ = geometry(obs, cfg)
    obs.faces[0][:, :2] = (obs.faces[0][:, :2] - .5) * .8 + .52
    after, _ = geometry(obs, cfg)
    assert after["opening_raw"] == pytest.approx(before["opening_raw"])

@pytest.mark.parametrize("kind,flag", [("none","no_face"),("two","multiple_faces"),("missing","missing_landmarks"),("nan","invalid_landmarks"),("pose","pose_unavailable"),("rotate","head_rotation"),("distance","distance")])
def test_invalid_observations(cfg, kind, flag):
    obs = synthetic_observation(0)
    if kind == "none": obs.faces = []
    if kind == "two": obs.faces *= 2
    if kind == "missing": obs.faces = [np.ones((20,3))]
    if kind == "nan": obs.faces[0][13,0] = np.nan
    if kind == "pose": obs.pose = None
    if kind == "rotate": obs.pose = (30,0,0)
    if kind == "distance": obs.faces[0][:,:2] = (obs.faces[0][:,:2] - .5) * .1 + .5
    _, flags = geometry(obs,cfg)
    assert flag in flags


def test_calibration_requires_contiguous_stable_samples(cfg):
    p = Pipeline(cfg)
    p.begin_calibration()
    for i in range(30): p.process(synthetic_observation(0), i/30, i)
    assert p.reference is None
    p.process(Observation([],640,480),1.,30)
    for i in range(31,90): p.process(synthetic_observation(0),i/30,i)
    assert p.reference is None
    for i in range(90,94): p.process(synthetic_observation(0),i/30,i)
    assert p.reference and p.reference["quality"] == "stable_reference"


def test_moving_jaw_does_not_calibrate(cfg):
    p = Pipeline(cfg)
    p.begin_calibration()
    for i in range(180): p.process(synthetic_observation(i/30, "controlled"),i/30,i)
    assert p.reference is None


def test_reposition_latches_until_recalibration(calibrated):
    obs = synthetic_observation(0)
    obs.faces[0][:,:2] = (obs.faces[0][:,:2]-.5)*1.2+.5
    r = calibrated.process(obs, 2.1, 63)
    assert "camera_or_head_repositioned" in r["flags"] and r["opening"] is None
    r = calibrated.process(synthetic_observation(0),2.14,64)
    assert not r["valid"]
    calibrated.begin_calibration()
    for i in range(65,130): r=calibrated.process(synthetic_observation(0),i/30, i)
    assert r["valid"]


def test_gap_invalidates_and_does_not_interpolate(calibrated):
    r = calibrated.process(synthetic_observation(0),3.,90)
    assert "frame_gap" in r["flags"] and r["opening"] is None
    r = calibrated.process(synthetic_observation(0),3.04,91)
    assert r["valid"] and r["velocity"] is None


def test_outlier_is_preserved_raw_but_excluded(calibrated):
    r = calibrated.process(synthetic_observation(2,"controlled"),62/30,62)
    assert "opening_outlier" in r["flags"]
    assert r["opening_raw"] == pytest.approx(.285)
    assert r["opening"] is None

@pytest.mark.parametrize("t", [float('nan'), -1, 61/30, 0])
def test_bad_timestamps_fail(calibrated,t):
    with pytest.raises(ValueError): calibrated.process(synthetic_observation(0),t,62)


def test_time_aware_filter_matches_equation(calibrated):
    t = 61/30 + .1
    obs = synthetic_observation(.2,"controlled")
    old = calibrated.last_good[2]
    r=calibrated.process(obs,t,62)
    expected=old + (1-math.exp(-.1/calibrated.cfg.smoothing_tau))*(r["opening_raw"]-old)
    assert r["opening"] == pytest.approx(expected)
    assert r["velocity"] == pytest.approx((expected-old)/.1)


def test_rotation_matrix_angles():
    a=math.radians(25)
    m=np.array([[math.cos(a),0,math.sin(a),0],[0,1,0,0],[-math.sin(a),0,math.cos(a),0],[0,0,0,1]])
    yaw,pitch,roll=rotation_angles(m)
    assert (yaw,pitch,roll) == pytest.approx((25,0,0))
