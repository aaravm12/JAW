import math
import pytest
from jrm.assessment import Assessment
from jrm.cycles import CycleDetector


def test_complete_cycles_and_timing(cfg):
    d=CycleDetector(cfg,.015)
    found=[]
    for i in range(1201):
        t=i/100
        c=d.add(t,.015+.27*(1-math.cos(2*math.pi*.25*t))/2)
        if c: found.append(c)
    assert len(found)==3
    assert all(3.0 < c["duration"] < 4 for c in found)
    assert all(c["opening_duration"]+c["closing_duration"]==pytest.approx(c["duration"]) for c in found)


def test_missing_data_cancels_unfinished_cycle(cfg):
    d=CycleDetector(cfg,.015)
    assert d.add(0,.015) is None
    assert d.add(1,.2) is None
    d.add(1.2,None,False)
    assert d.add(2,.015) is None


def test_initially_open_or_incomplete_not_counted(cfg):
    d=CycleDetector(cfg,0)
    assert d.add(0,.2) is None
    assert d.add(1,0) is None
    assert d.add(2,.2) is None


def test_pause_resume_excludes_paused_time(cfg):
    a=Assessment(cfg)
    a.start(100)
    a.tick(101)
    a.pause(101)
    a.tick(111)
    assert a.elapsed==1 and a.state=="paused"
    a.resume(112)
    a.tick(113)
    assert a.elapsed==2 and a.phase=="controlled"
    a.tick(131)
    assert a.state=="finished" and a.elapsed==20


def test_jump_advances_multiple_phases(cfg):
    a=Assessment(cfg)
    a.start(0)
    a.tick(19)
    assert a.phase=="post_activity" and a.phase_elapsed==1
    a.tick(22)
    assert a.state=="finished" and a.elapsed==20


def test_skip_rules_and_metadata(cfg):
    a=Assessment(cfg)
    a.start(0)
    with pytest.raises(ValueError): a.skip(1)
    a.tick(10)
    a.skip(10)
    assert a.phase=="post_activity" and a.skipped==["activity"]


def test_stop_from_pause(cfg):
    a=Assessment(cfg)
    a.start(10)
    a.pause(11)
    a.stop(100)
    assert a.state=="stopped" and a.elapsed==1
