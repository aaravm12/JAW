import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from jrm.config import Settings
from jrm.pipeline import Pipeline
from jrm.synthetic import synthetic_observation

@pytest.fixture
def cfg():
    return Settings(durations=(2., 8., 8., 2.))

@pytest.fixture
def calibrated(cfg):
    p = Pipeline(cfg)
    p.begin_calibration()
    for i in range(62):
        r = p.process(synthetic_observation(i / 30), i / 30, i)
    assert p.reference is not None and r["valid"]
    return p


@pytest.fixture(scope="session", autouse=True)
def ensure_generated_fixtures():
    """Keep generated data out of git; a fresh checkout regenerates the fixtures."""
    from pathlib import Path
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[1]
    names = ('cartoon_assessment.mp4', 'no_face_vfr.mkv', 'synthetic_landmarks.csv')
    if not all((root / 'data' / name).exists() for name in names):
        subprocess.run([sys.executable, str(root / 'scripts/make_fixtures.py')], cwd=root, check=True)
