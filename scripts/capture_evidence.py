"""Exercise a real Qt window and capture synthetic-only evidence, no camera required."""
import json
import logging
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from jrm.ui import MainWindow
from jrm.config import Settings

root=Path(__file__).resolve().parents[1]/'evidence'
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.FileHandler(root/'application-startup.log',mode='w'),logging.StreamHandler()])
app=QApplication([])
w=MainWindow(tempfile.mkdtemp(prefix='jrm-evidence-'),Settings(durations=(2.,8.,8.,2.)))
w.show()
logging.info('Actual Qt window shown; platform=%s',app.platformName())
stage=0
origin=time.monotonic()
report={'platform':app.platformName(),'completed':False}

def step():
    global stage
    if time.monotonic()-origin>50:
        logging.error('Evidence workflow timed out')
        w.close();app.exit(1);return
    if stage==0:
        w.grab().save(str(root/'01-setup.png'))
        w.start_input('synthetic');stage=1
    elif stage==1 and w.latest:
        w.send('calibrate');stage=2
    elif stage==2 and w.start_button.isEnabled():
        logging.info('Stable synthetic calibration accepted')
        w.send('start');stage=3
    elif stage==3 and w.latest['phase']=='controlled' and w.latest['phase_elapsed']>2:
        w.grab().save(str(root/'02-live-synthetic.png'));stage=4
    elif stage==4 and w.selected_session:
        sid=w.selected_session
        w.stop_input()
        w.load_result(sid)
        w.tabs.setCurrentIndex(2)
        stage=5
    elif stage==5:
        w.grab().save(str(root/'03-results.png'))
        sid=w.selected_session
        meta,rows=w.store.load(sid)
        w.store.export(sid,root/'ui-synthetic.csv')
        report.update(completed=meta['status']=='finished',source_kind=meta['source_kind'],
            rows=len(rows),session_reopened=sid,phases=meta['analysis']['phases'])
        w.tabs.setCurrentIndex(4);stage=6
    elif stage==6:
        w.grab().save(str(root/'04-engineering.png'))
        (root/'ui-verification.json').write_text(json.dumps(report,indent=2))
        logging.info('Completed UI assessment, reopened SQLite session, exported CSV/JSON, captured screenshots')
        w.close();app.exit(0)

timer=QTimer();timer.timeout.connect(step);timer.start(100)
raise SystemExit(app.exec())
