"""Generate original synthetic fixtures. All fixture content is CC0-1.0."""
from fractions import Fraction
from pathlib import Path
import csv
import sys
import numpy as np
import av
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jrm.synthetic import synthetic_observation, draw_synthetic
from jrm.geometry import INDICES

root=Path(__file__).resolve().parents[1]/'data'
root.mkdir(exist_ok=True)
rows=[]
for i in range(660):
    t=i/30
    phase='baseline' if t<4 or t>=20 else 'controlled'
    obs=synthetic_observation(max(0,t-4),phase)
    r={'t':t,'phase':phase}
    for n in INDICES:
        for j,axis in enumerate(('x','y','z')):r[f'lm_{n}_{axis}']=obs.faces[0][n,j]
    rows.append(r)
with (root/'synthetic_landmarks.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
# Blank/counter clip intentionally contains no face. Tests must return missing data.
with av.open(str(root/'no_face_vfr.mkv'),'w') as output:
    stream=output.add_stream('ffv1',rate=30)
    stream.width=320;stream.height=240;stream.pix_fmt='yuv420p';stream.time_base=Fraction(1,1000)
    pts=0
    for i in range(45):
        img=np.full((240,320,3),int(i%20)*4,dtype=np.uint8)
        frame=av.VideoFrame.from_ndarray(img,format='rgb24')
        frame.pts=pts;frame.time_base=Fraction(1,1000)
        pts += 33 if i%2==0 else 67
        for packet in stream.encode(frame):output.mux(packet)
    for packet in stream.encode():output.mux(packet)
print('Created synthetic landmarks and no-face variable-rate video fixtures.')

from jrm.synthetic_face import cartoon_frame
with av.open(str(root/'cartoon_assessment.mp4'),'w') as output:
    stream=output.add_stream('mpeg4',rate=30)
    stream.width=480;stream.height=640;stream.pix_fmt='yuv420p'
    stream.bit_rate=1500000
    for i in range(672):
        t=i/30
        moving=4<=t<20
        frame=av.VideoFrame.from_ndarray(cartoon_frame(max(0,t-4),moving),format='bgr24')
        frame.pts=i;frame.time_base=Fraction(1,30)
        for packet in stream.encode(frame):output.mux(packet)
    for packet in stream.encode():output.mux(packet)
print('Created original 22.4 s synthetic cartoon assessment video.')
