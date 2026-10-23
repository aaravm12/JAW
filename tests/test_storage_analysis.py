import copy
import csv
import json
import pytest
from jrm.replay import run_synthetic
from jrm.storage import Storage
from jrm.analytics import compare_sessions, analyze
from jrm.charts import plot_data


def test_complete_assessment_reopens_and_exports_exact_data(tmp_path,cfg):
    store=Storage(tmp_path)
    sid=run_synthetic(store,cfg)
    meta,rows=store.load(sid)
    assert meta["status"]=="finished" and meta["simulated"]
    assert len(rows)==601
    assert set(r['phase'] for r in rows)=={'baseline','controlled','activity','post_activity'}
    assert meta['analysis']['phases']['controlled']['complete_cycles']==2
    assert meta['analysis']['phases']['activity']['complete_cycles']==2
    export=store.export(sid,tmp_path/'export.csv')
    exported=list(csv.DictReader(export.open()))
    assert len(exported)==len(rows)
    for r,c in zip(rows,exported):
        assert float(c['source_t'])==r['source_t']
        assert c['flags']==r['flags']
        assert (float(c['opening']) if c['opening'] else None)==r['opening']
    assert json.loads(export.with_suffix('.json').read_text())['session_id']==sid
    store.close()
    reopened=Storage(tmp_path)
    assert reopened.load(sid)==(meta,rows)
    x,y=plot_data(rows)
    assert x==[r['source_t'] for r in rows]
    for value,row in zip(y,rows):
        if row['valid']: assert value==row['opening']
    reopened.close()


def test_synthetic_pipeline_regression_is_reproducible(tmp_path,cfg):
    store=Storage(tmp_path)
    s1,s2=run_synthetic(store,cfg),run_synthetic(store,cfg)
    m1,r1=store.load(s1);m2,r2=store.load(s2)
    assert r1==r2 and m1['analysis']==m2['analysis']
    p=m1['analysis']['phases']['controlled']
    assert p['max_opening']==pytest.approx(.283962,abs=2e-5)
    assert p['mean_amplitude'] > .24
    store.close()


def test_invalid_geometry_does_not_make_summary_values(cfg):
    rows=[{'source_t':i/30,'phase':'controlled','valid':False,'opening':None,'flags':'no_face','recording_state':'running','dt':1/30} for i in range(100)]
    result=analyze(rows,cfg,0.)
    assert result['phases']['controlled']['mean_opening'] is None
    assert result['phases']['controlled']['complete_cycles']==0
    assert result['quality_flags']['no_face']==100


def test_comparison_requires_same_participant_source_settings(tmp_path,cfg):
    store=Storage(tmp_path)
    pid=store.participant()
    a,b=[store.load(run_synthetic(store,cfg,pid))[0] for _ in range(2)]
    assert compare_sessions([a,b])[1]['amplitude_change']==0
    c=copy.deepcopy(b);c['source_kind']='webcam';c['simulated']=False
    with pytest.raises(ValueError,match='separately'):compare_sessions([a,c])
    c=copy.deepcopy(b);c['participant_id']='other'
    with pytest.raises(ValueError,match='same anonymous'):compare_sessions([a,c])
    c=copy.deepcopy(b);c['settings']['cycle_high']=.3
    with pytest.raises(ValueError,match='matching settings'):compare_sessions([a,c])
    c=copy.deepcopy(b);c['runtime']['model_sha256']='different'
    with pytest.raises(ValueError,match='runtime'):compare_sessions([a,c])
    c=copy.deepcopy(b);c['status']='stopped'
    with pytest.raises(ValueError,match='complete'):compare_sessions([a,c])
    store.close()


def test_delete_cascades_and_failed_save_is_atomic(tmp_path,cfg):
    store=Storage(tmp_path)
    sid=run_synthetic(store,cfg)
    meta,rows=store.load(sid)
    broken=copy.deepcopy(rows);broken[0]['opening']=float('nan')
    with pytest.raises(ValueError):store.save(meta,broken)
    assert store.load(sid)==(meta,rows)
    store.delete(sid)
    assert not store.db.execute('SELECT * FROM samples').fetchall()
    assert not store.sessions()
    store.close()
