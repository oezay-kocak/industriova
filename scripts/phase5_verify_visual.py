"""Verify actual Qt PNG dimensions and distinguish the native Qt popup surface."""
import json,hashlib
from pathlib import Path
from PySide6.QtGui import QImage
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase5'
rows=[];sizes=set()
for scale in (1,2):
    captures=json.loads((OUT/f'screenshots/dpi{scale}/captures.json').read_text(encoding='utf8'))
    assert len(captures)==57,len(captures)
    for row in captures:
        path=ROOT/row['file'];picture=QImage(str(path));assert not picture.isNull(),path
        assert (picture.width(),picture.height())==(row['width'],row['height'])
        assert (row['width'],row['height'])==(round(row['logical_width']*scale),round(row['logical_height']*scale))
        if row['surface']=='MainWindow':
            size=(row['logical_width'],row['logical_height']);assert size in {(1366,768),(1600,980),(1920,1080)}
            sizes.add((*size,scale))
        else:assert row['surface']=='QtPopup'
        rows.append(dict(**row,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
assert len(sizes)==6 and len(rows)==114
record=dict(ok=True,captures=len(rows),main_window=sum(r['surface']=='MainWindow' for r in rows),separate_qt_popups=sum(r['surface']=='QtPopup' for r in rows),configurations=sorted(sizes),native_windows_hand_acceptance=False,files=rows)
(OUT/'visual-verification.json').write_text(json.dumps(record,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in record.items() if k!='files'}),flush=True)
