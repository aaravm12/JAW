"""Real Qt event-loop interactions, offscreen where no display is available."""
import time
import pytest
from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from jrm.ui import MainWindow
from jrm.config import Settings

@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def wait_for(app,predicate,timeout=8):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        app.processEvents()
        if predicate():return
        time.sleep(.02)
    raise AssertionError('Timed out waiting for UI condition')


def test_full_demo_ui_pause_save_reopen_export_and_close(app,tmp_path,monkeypatch):
    window=MainWindow(tmp_path,Settings(durations=(2.,4.,4.,2.)))
    window.show();app.processEvents()
    QTest.mouseClick(window.demo_button,Qt.LeftButton)
    wait_for(app,lambda:window.latest is not None)
    assert not window.start_button.isEnabled()
    QTest.mouseClick(window.calibrate_button,Qt.LeftButton)
    wait_for(app,lambda:window.start_button.isEnabled())
    QTest.mouseClick(window.start_button,Qt.LeftButton)
    wait_for(app,lambda:window.latest['state']=='running')
    QTest.mouseClick(window.pause_button,Qt.LeftButton)
    wait_for(app,lambda:window.latest['state']=='paused')
    elapsed=window.latest['elapsed']
    time.sleep(.2);app.processEvents()
    assert window.latest['elapsed']==elapsed
    QTest.mouseClick(window.pause_button,Qt.LeftButton)
    wait_for(app,lambda:window.latest['state']=='running')
    wait_for(app,lambda:window.selected_session is not None,timeout=20)
    sid=window.selected_session
    meta,rows=window.store.load(sid)
    assert meta['status']=='finished' and meta['simulated']
    assert any(r['recording_state']=='paused' for r in rows)
    assert int(window.table.item(1,4).text()) == meta['analysis']['phases']['controlled']['complete_cycles']
    window.tabs.setCurrentIndex(3)
    window.history.item(0).setSelected(True)
    window.reopen_selected()
    assert window.tabs.currentIndex()==2 and window.selected_session==sid
    dest=tmp_path/'ui-export.csv'
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(dest),'CSV'))
    QTest.mouseClick(window.export_button,Qt.LeftButton)
    assert dest.exists() and dest.with_suffix('.json').exists()
    worker=window.worker
    window.close();app.processEvents()
    assert not worker.isRunning()


def test_stop_saves_immediately_and_restart_recalibrates(app,tmp_path):
    window=MainWindow(tmp_path)
    window.show();window.start_input('synthetic')
    wait_for(app,lambda:window.latest is not None)
    window.send('calibrate')
    wait_for(app,lambda:window.start_button.isEnabled())
    window.send('start')
    wait_for(app,lambda:window.latest['state']=='running')
    window.send('stop')
    wait_for(app,lambda:window.selected_session is not None)
    meta,_=window.store.load(window.selected_session)
    assert meta['status']=='stopped'
    window.send('restart')
    wait_for(app,lambda:window.latest['calibrating'])
    assert not window.start_button.isEnabled()
    window.close();app.processEvents()


def test_ui_comparison_shows_stored_amplitudes(app,tmp_path,cfg):
    from jrm.replay import run_synthetic
    window=MainWindow(tmp_path,cfg)
    pid=window.participants.currentText()
    run_synthetic(window.store,cfg,pid)
    run_synthetic(window.store,cfg,pid)
    window.refresh_history()
    for i in range(2):window.history.item(i).setSelected(True)
    window.compare_selected()
    assert 'EXPLORATORY COMPARISON' in window.comparison.toPlainText()
    points=window.comparison_plot.listDataItems()[0]
    x,y=points.getData()
    assert len(x)==2 and y[0]==y[1] and y[0]>.24
    window.close();app.processEvents()


def test_camera_selection_and_empty_discovery_manual_fallback(app,tmp_path):
    window=MainWindow(tmp_path)
    window.on_cameras([{'index':2,'name':'Camera 2'},{'index':7,'name':'Camera 7'}])
    assert window.camera_index.value()==2 and not window.camera_index.isEnabled()
    window.camera_choices.setCurrentIndex(2)
    assert window.camera_index.value()==7
    window.camera_choices.setCurrentIndex(0)
    window.camera_index.setValue(12)
    assert window.camera_index.isEnabled() and window.camera_index.value()==12
    window.on_cameras([])
    assert window.camera_index.isEnabled() and window.camera_index.value()==12
    assert 'No available cameras' in window.discovery_status.text()
    window.close()


def test_ui_live_indicators_are_from_worker_and_clear_on_stop(app,tmp_path):
    window=MainWindow(tmp_path)
    window.start_input('synthetic')
    try:
        wait_for(app,lambda:window.latest is not None and window.latest['telemetry']['processing_fps'] is not None)
        assert '640 × 480' in window.input_stats.text()
        assert 'Processing FPS: —' not in window.input_stats.text()
        assert 'Phase peak: —' in window.movement_stats.text()
        # A controlled packet verifies labels without adding a second signal pipeline.
        packet=dict(window.latest,peak_opening=.281,frequency_hz=.25)
        window.update_live_indicators(packet)
        assert '0.281 ratio' in window.movement_stats.text()
        assert '0.250 Hz' in window.movement_stats.text()
        window.stop_input()
        assert window.input_stats.text()=='Processing FPS: —  •  Frame size: —'
        assert window.movement_stats.text()=='Phase peak: —  •  Movement frequency: —'
    finally:
        window.close()


def test_background_discovery_returns_devices_and_restores_controls(app,tmp_path,monkeypatch):
    from jrm import cameras
    monkeypatch.setattr(cameras,'discover_cameras',lambda cancelled: [{'index':3,'name':'Camera 3'}])
    window=MainWindow(tmp_path)
    try:
        window.find_cameras()
        wait_for(app,lambda: window.camera_choices.count()==2 and window.discover_button.isEnabled())
        assert window.camera_index.value()==3
        assert window.camera_button.isEnabled()
    finally:
        window.close()
