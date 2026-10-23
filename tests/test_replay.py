from pathlib import Path
import csv
import numpy as np
import pytest
from jrm.acquisition import Video
from jrm.detector import FaceDetector
from jrm.model import model_path
from jrm.pipeline import Pipeline
from jrm.geometry import Observation, INDICES
from jrm.replay import analyze_video
from jrm.storage import Storage

DATA=Path(__file__).resolve().parents[1]/'data'


def test_variable_rate_presentation_timestamps_are_preserved():
    video=Video(DATA/'no_face_vfr.mkv')
    times=[]
    while (item:=video.read()) is not None:times.append(item[1])
    video.close()
    assert len(times)==45
    assert all(b>a for a,b in zip(times,times[1:]))
    assert len(set(round(b-a,3) for a,b in zip(times,times[1:])))>=2


def test_landmark_fixture_replays_identically(cfg):
    outputs=[]
    for _ in range(2):
        p=Pipeline(cfg);p.begin_calibration();rows=[]
        for i,r in enumerate(csv.DictReader((DATA/'synthetic_landmarks.csv').open())):
            points=np.tile([.5,.5,0.],(478,1))
            for n in INDICES:
                points[n]=[float(r[f'lm_{n}_{a}']) for a in ('x','y','z')]
            rows.append(p.process(Observation([points],640,480,(0,0,0)),float(r['t']),i))
        outputs.append(rows)
    assert outputs[0]==outputs[1]
    assert sum(r['valid'] for r in outputs[0])>550
    assert max(r['opening'] or 0 for r in outputs[0])>.28

@pytest.mark.skipif(not model_path().exists(),reason='Run python -m jrm --download-model for actual MediaPipe regression')
def test_real_detector_video_replay_is_reproducible_and_never_fills_missing_faces(tmp_path,cfg):
    store=Storage(tmp_path)
    first=store.load(analyze_video(DATA/'no_face_vfr.mkv',store,cfg,synthetic=True))
    second=store.load(analyze_video(DATA/'no_face_vfr.mkv',store,cfg,synthetic=True))
    assert first[0]['status']=='calibration_failed'
    assert first[1]==second[1]
    assert first[0]['analysis']==second[0]['analysis']
    assert len(first[1])==45
    assert all(not r['valid'] and r['opening'] is None and 'no_face' in r['flags'] for r in first[1])
    assert first[0]['calibration'] is None
    store.close()

@pytest.mark.skipif(not model_path().exists(),reason='Run model setup first')
def test_positive_synthetic_video_through_actual_mediapipe(tmp_path,cfg):
    store=Storage(tmp_path)
    first=store.load(analyze_video(DATA/'cartoon_assessment.mp4',store,cfg,synthetic=True))
    second=store.load(analyze_video(DATA/'cartoon_assessment.mp4',store,cfg,synthetic=True))
    assert first[0]['status']=='finished'
    assert first[0]['simulated'] and first[0]['source_kind']=='synthetic_video'
    assert first[1]==second[1]
    assert first[0]['analysis']==second[0]['analysis']
    assert first[0]['analysis']['phases']['controlled']['complete_cycles']==2
    assert first[0]['analysis']['phases']['activity']['complete_cycles']==2
    assert first[0]['analysis']['phases']['controlled']['valid_fraction']>.95
    assert first[0]['calibration']['quality']=='stable_reference'
    store.close()
