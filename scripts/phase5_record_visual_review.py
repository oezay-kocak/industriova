"""Record the nine final images actually inspected in the task, without regenerating them."""
import json,hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase5'
names=[('dpi1','route-1-cargo-mixed-group-1366x768.png'),('dpi1','harbor-mk-rarity-99-1600x980.png'),
       ('dpi1','route-target-options-event-disabled-1920x1080.png'),('dpi1','garage_depot-mk-rarity-99-1920x1080.png'),
       ('dpi2','airport-busy-theoretical-tooltip-1366x768.png'),('dpi2','route-2-consortium-valid-1600x980.png'),
       ('dpi2','harbor-last-line-mk-1920x1080.png'),('dpi2','route-target-options-event-disabled-1920x1080.png'),
       ('dpi1','route-2-contract-invalid-1366x768.png')]
metadata=json.loads((OUT/'visual-verification.json').read_text(encoding='utf8'))
known={Path(r['file']).as_posix():r for r in metadata['files']};rows=[];main_configurations=set()
for dpi,name in names:
    path=OUT/'screenshots'/dpi/name;relative=path.relative_to(ROOT).as_posix();row=known[relative]
    assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
    width,height=map(int,re.search(r'(\d+)x(\d+)\.png$',name).groups())
    if row['surface']=='MainWindow':main_configurations.add((width,height,int(dpi[-1])))
    rows.append(dict(file=relative,sha256=row['sha256'],surface=row['surface'],context_width=width,context_height=height,scale=int(dpi[-1]),actually_viewed=True))
assert len(main_configurations)==6
target=OUT/'visual-review.json';assert not target.exists()
target.write_text(json.dumps(dict(images=len(rows),main_window_configurations=sorted(main_configurations),files=rows,
    findings='Final cargo/target/error/MK99/rarity/throughput layouts readable. Separate Qt popup now opaque and legible at both scales. Existing long Shipping/Air line and sidebar clipping remains P9. Native Windows hand acceptance not performed.'),indent=2),encoding='utf8')
print('Nine final images actually reviewed; all six MainWindow configurations included.')
