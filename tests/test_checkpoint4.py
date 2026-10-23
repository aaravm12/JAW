"""Checkpoint 4: hardware-independent regression and controlled cycle acceptance."""
import math
import numpy as np
import pytest
from jrm.cycles import LiveMovementMetrics
from jrm.telemetry import FrameTelemetry
from jrm.synthetic import synthetic_observation
from jrm.analytics import analyze
from jrm import cameras


def test_fps_uses_elapsed_processing_time_and_actual_frame_shape():
    meter = FrameTelemetry()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    assert meter.update(100., frame) == {'processing_fps': None, 'width': 1280, 'height': 720}
    assert meter.update(100.1, frame)['processing_fps'] == pytest.approx(10)
    assert meter.update(100.3, frame)['processing_fps'] == pytest.approx(2 / .3)
    # A long stall clears the stale estimate; changed frame dimensions are observed.
    result = meter.update(104., np.zeros((480, 640, 3)))
    assert result == {'processing_fps': None, 'width': 640, 'height': 480}
    with pytest.raises(ValueError):
        meter.update(104., frame)


@pytest.mark.parametrize('platform', ['darwin', 'win32'])
def test_camera_discovery_sparse_indices_releases_every_probe(monkeypatch, platform):
    monkeypatch.setattr(cameras.sys, 'platform', platform)
    released, backends = [], []
    class Capture:
        def __init__(self, index, backend):
            self.index = index
            backends.append(backend)
        def isOpened(self):
            return self.index in (1, 4)
        def release(self):
            released.append(self.index)
    monkeypatch.setattr(cameras.cv2, 'VideoCapture', Capture)
    assert [c['index'] for c in cameras.discover_cameras()] == [1, 4]
    assert released == list(range(10))
    expected = cameras.cv2.CAP_AVFOUNDATION if platform == 'darwin' else cameras.cv2.CAP_ANY
    assert set(backends) == {expected}
    assert cameras.discover_cameras(lambda: True) == []


def test_discovery_failure_and_unsupported_platform_preserve_manual_fallback(monkeypatch):
    monkeypatch.setattr(cameras.sys, 'platform', 'darwin')
    def fail(*args):
        raise OSError('Camera access unavailable')
    monkeypatch.setattr(cameras.cv2, 'VideoCapture', fail)
    assert cameras.discover_cameras() == []
    monkeypatch.setattr(cameras.sys, 'platform', 'unknown')
    assert cameras.discover_cameras() == []


def feed(calibrated, metrics, opening, pose=(0, 0, 0), state='running', phase='controlled'):
    obs = synthetic_observation(0)
    eye_px = np.linalg.norm((obs.faces[0][263, :2] - obs.faces[0][33, :2]) * [640, 480])
    obs.faces[0][14, 1] = obs.faces[0][13, 1] + opening * eye_px / 480
    obs.pose = pose
    t = calibrated.last_t + 1 / 30
    row = calibrated.process(obs, t, round(t * 30))
    row.update(phase=phase, recording_state=state, segment=0)
    return metrics.update(row, phase, state), row


@pytest.mark.parametrize('pose', [(0, 0, 0), (5, 2, 1)])
def test_five_cycles_with_partial_cycles_and_small_head_movement(calibrated, cfg, pose):
    metrics = LiveMovementMetrics(cfg, calibrated.reference['opening_raw'])
    rows = []
    # Leading initially-open half-cycle must not count.
    for i in range(61):
        out, row = feed(calibrated, metrics, .015 + .27 * (1 + math.cos(math.pi * i / 60)) / 2, pose)
        rows.append(row)
    assert out['cycles'] == 0
    # Five full, comfortable-range synthetic excursions at 0.25 Hz.
    for i in range(601):
        value = .015 + .27 * (1 - math.cos(2 * math.pi * i / 120)) / 2
        out, row = feed(calibrated, metrics, value, pose)
        rows.append(row)
    assert out['cycles'] == 5
    assert out['frequency_hz'] == pytest.approx(.25, abs=.003)
    assert .28 < out['peak_opening'] < .286
    # Subthreshold excursion followed by unfinished large excursion: still five.
    for amplitude, samples in ((.04, 121), (.27, 61)):
        for i in range(samples):
            out, row = feed(calibrated, metrics, .015 + amplitude * (1 - math.cos(2 * math.pi * i / 120)) / 2, pose)
            rows.append(row)
    assert out['cycles'] == 5
    summary = analyze(rows, cfg, calibrated.reference['opening_raw'])
    assert summary['phases']['controlled']['complete_cycles'] == 5
    assert summary['phases']['controlled']['max_opening'] == out['peak_opening']


def test_large_head_movement_cancels_cycle_until_recalibration(calibrated, cfg):
    metrics = LiveMovementMetrics(cfg, calibrated.reference['opening_raw'])
    for i in range(301):
        pose = (30, 0, 0) if i == 300 else (0, 0, 0)
        out, row = feed(calibrated, metrics, .015 + .27 * (1 - math.cos(2 * math.pi * i / 120)) / 2, pose)
    assert out['cycles'] == 2
    assert out['frequency_hz'] is None
    assert 'head_rotation' in row['flags']
    for i in range(121):
        out, row = feed(calibrated, metrics, .015)
    assert not row['valid'] and out['cycles'] == 2
    calibrated.begin_calibration()
    for _ in range(65):
        out, row = feed(calibrated, metrics, .015)
    assert row['valid']
    for i in range(361):
        out, row = feed(calibrated, metrics, .015 + .27 * (1 - math.cos(2 * math.pi * i / 120)) / 2)
    assert out['cycles'] == 5
    assert out['frequency_hz'] == pytest.approx(.25, abs=.003)


def test_frequency_peak_and_count_reset_rules(cfg):
    m = LiveMovementMetrics(cfg, .015)
    def sample(t, value=.015, valid=True, state='running', phase='controlled'):
        return m.update({'source_t': t, 'opening': value, 'valid': valid}, phase, state)
    for t, value in [(0,.015),(1,.25),(2,.015),(4,.015),(5,.25),(6,.015)]:
        out = sample(t, value)
    assert out == {'cycles': 2, 'peak_opening': .25, 'frequency_hz': .25}
    out = sample(7, None, False)
    assert out['frequency_hz'] is None and out['peak_opening'] == .25
    assert sample(8, state='paused')['frequency_hz'] is None
    out = sample(9, phase='activity')
    assert out == {'cycles': 2, 'peak_opening': .015, 'frequency_hz': None}
    for t, value in [(10,.25),(11,.015),(13,.015),(14,.25),(15,.015)]:
        out = sample(t, value, phase='activity')
    assert out['frequency_hz'] == .25
    assert sample(31, phase='activity')['frequency_hz'] is None
    assert LiveMovementMetrics(cfg, .015).cycles == 0


def test_linux_discovery_uses_sparse_device_nodes(monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(cameras.sys, 'platform', 'linux')
    monkeypatch.setattr(cameras.Path, 'glob', lambda *args: [Path('/dev/video2'), Path('/dev/video8'), Path('/dev/video-invalid')])
    opened, released = [], []
    class Capture:
        def __init__(self, index, backend):
            self.index = index
            opened.append(index)
        def isOpened(self):
            return True
        def release(self):
            released.append(self.index)
    monkeypatch.setattr(cameras.cv2, 'VideoCapture', Capture)
    assert [c['index'] for c in cameras.discover_cameras()] == [2, 8]
    assert opened == released == [2, 8]


def test_camera_open_and_disconnect_errors_release_resources(monkeypatch):
    from jrm import acquisition
    instances = []
    class Capture:
        available = False
        def __init__(self, *args):
            self.released = False
            instances.append(self)
        def isOpened(self):
            return self.available
        def set(self, *args):
            pass
        def read(self):
            return False, None
        def release(self):
            self.released = True
    monkeypatch.setattr(acquisition.cv2, 'VideoCapture', Capture)
    with pytest.raises(RuntimeError, match='Cannot open camera'):
        acquisition.Camera(0)
    assert instances[-1].released
    Capture.available = True
    source = acquisition.Camera(0)
    try:
        with pytest.raises(RuntimeError, match='stopped providing frames'):
            source.read()
    finally:
        source.close()
    assert instances[-1].released
