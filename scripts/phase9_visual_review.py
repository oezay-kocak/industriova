"""Validate all capture sizes/hashes and record only actually viewed frames."""
from pathlib import Path
import json,struct,hashlib
root=Path.cwd();out=root/'artifacts/phase9';rows=[]
for kind in ('screenshots','popups'):
 for scale in (1,2):
  values=json.loads((out/kind/f'dpi{scale}/captures.json').read_text(encoding='utf8'))['captures']
  for r in values:
   p=root/r['file'];data=p.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n'
   assert list(struct.unpack('>II',data[16:24]))==r['pixels']
   assert r['pixels']==[n*scale for n in r['logical']]
   assert hashlib.sha256(data).hexdigest()==r['sha256'];rows.append(r)
viewed=[
 'screenshots/dpi1/production-guide-prices-1366x768.png','screenshots/dpi1/freight-rail_station-1366x768.png',
 'screenshots/dpi1/storage-global-resources-1600x980.png','screenshots/dpi1/consortium-deliver-via-freight-1600x980.png',
 'screenshots/dpi1/history-1920x1080.png','screenshots/dpi1/factory-frontscreen-1920x1080.png',
 'screenshots/dpi2/freight-harbor-1366x768.png','popups/dpi2/inbox-filled-popup-1366x768.png',
 'screenshots/dpi2/consortium-freight-required-1600x980.png','screenshots/dpi2/freight-assignment-confirmation-1600x980.png',
 'screenshots/dpi2/resources-frontscreen-1920x1080.png','screenshots/dpi2/energy-frontscreen-1920x1080.png',
 'popups/dpi1/history-popup-1920x1080.png','popups/dpi1/inbox-empty-popup-1600x980.png',
]
assert len(rows)==120
report=dict(main_frames=102,separate_popup_frames=18,total=120,actually_viewed=[next(r for r in rows if r['file']=='artifacts/phase9/'+n) for n in viewed],all_frames=rows,method='Actual Qt MainWindow.grab excludes separate top-level Popup surfaces. Their actual Popup.grab pixels are captured separately, without compositing. History/Inbox main frames show the underlying context only. Six size/scale profiles; synthetic formatting fixtures. Native Windows mouse/DWM/multimonitor acceptance remains open.')
(out/'visual-review.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('120 images verified; 14 actually viewed',flush=True)
