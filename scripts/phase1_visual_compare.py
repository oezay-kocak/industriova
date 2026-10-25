"""Pixel comparison of all 18 paired screenshots; no image transformation."""
import json
from pathlib import Path
from PySide6.QtGui import QImage
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase1'
rows=[]
for scale in ('1','2'):
    for before in sorted((OUT/'before'/('dpi'+scale)).glob('*.png')):
        after=OUT/'after'/('dpi'+scale)/before.name
        left,right=QImage(str(before)).convertToFormat(QImage.Format.Format_ARGB32),QImage(str(after)).convertToFormat(QImage.Format.Format_ARGB32)
        assert not left.isNull() and left.size()==right.size()
        changed=0 if left==right else sum(a!=b for a,b in zip(left.constBits().cast('I'),right.constBits().cast('I')))
        rows.append(dict(scale=int(scale),file=before.name,pixels=[left.width(),left.height()],identical=changed==0,changed_pixels=changed,changed_percent=100*changed/(left.width()*left.height())))
assert len(rows)==18
(OUT/'visual-comparison.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
for row in rows:print(row['scale'],row['file'],'same' if row['identical'] else f"{row['changed_percent']:.3f}% changed")
