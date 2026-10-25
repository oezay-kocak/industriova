import hashlib,json
from pathlib import Path
from PySide6.QtGui import QImage
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase6';rows=[];sizes=set()
for scale in (1,2):
    captures=json.loads((OUT/f'screenshots/dpi{scale}/captures.json').read_text(encoding='utf8'));assert len(captures)==51
    for row in captures:
        path=ROOT/row['file'];image=QImage(str(path));assert not image.isNull()
        assert (image.width(),image.height())==(row['logical_width']*scale,row['logical_height']*scale)==(row['width'],row['height'])
        sizes.add((row['logical_width'],row['logical_height'],scale))
        rows.append(dict(**row,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
assert len(rows)==102 and len(sizes)==6
reviewed=[('dpi1','harbor-high-mixed-paused-mk50-tooltip-1366x768.png'),('dpi1','rail_station-low-warmup-mk1-tooltip-1600x980.png'),('dpi1','airport-empty-warmup-1920x1080.png'),
 ('dpi2','garage_depot-high-mixed-paused-mk50-tooltip-1366x768.png'),('dpi2','rail_station-low-warmup-mk1-tooltip-1600x980.png'),('dpi2','20-facilities-isolated-header-1920x1080.png'),('dpi2','airport-idle-zero-1366x768.png')]
review=[]
for dpi,name in reviewed:
    path=OUT/'screenshots'/dpi/name;review.append(dict(file=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(OUT/'visual-verification.json').write_text(json.dumps(dict(ok=True,captures=102,configurations=sorted(sizes),files=rows),indent=2),encoding='utf8')
(OUT/'visual-review.json').write_text(json.dumps(dict(actually_viewed=review,observations='All six configurations and all four facility types reviewed: legible local targets and values, warm-up, mixed high values, existing tooltip theory/actual separation, idle zero and 20-facility isolation. Long Shipping/Rail plates now fit locally. Sidebar long names retain existing elision. Synthetic amounts intentionally include values above nominal vehicle throughput; these are formatting fixtures, not an economic playtest.',native_windows_hand_acceptance=False),indent=2),encoding='utf8')
print(json.dumps(dict(captures=102,actually_viewed=len(review),configurations=len(sizes))))
