"""Pin the explicitly inspected final offscreen images and verify all 66 PNGs."""
import hashlib,json
from pathlib import Path
from PySide6.QtGui import QImage
R=Path(__file__).resolve().parents[1];O=R/'artifacts/phase8'
selected={
1:{'1366x768':('contracts-large-numbers','consortium-large-numbers'),
   '1600x980':('contracts-preview','consortium-partial'),
   '1920x1080':('contracts-large-numbers','consortium-completed')},
2:{'1366x768':('contracts-large-numbers','consortium-preview'),
   '1600x980':('contracts-accepted','consortium-large-numbers'),
   '1920x1080':('contracts-completed','consortium-expired')}}
viewed=[];verified=[]
for scale in (1,2):
    captures=json.loads((O/f'screenshots-accepted/dpi{scale}/captures.json').read_text(encoding='utf8'))
    assert len(captures['captures'])==33
    for row in captures['captures']:
        path=R/row['file'];image=QImage(str(path));digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert not image.isNull() and digest==row['sha256']
        assert [image.width(),image.height()]==row['pixels']==[v*scale for v in row['logical_size']]
        verified.append(dict(file=row['file'],sha256=digest,pixels=row['pixels']))
    for size,names in selected[scale].items():
        for name in names:
            path=O/f'screenshots-accepted/dpi{scale}/{name}-{size}.png'
            viewed.append(dict(file=path.relative_to(R).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),logical_size=size,scale=scale,review='Actually opened with view_image: amounts/rewards legible, ellipsized names stay within tiles, preview/accept/completion states consistent, scroll access retained.'))
diagnostic=O/'visual-bar-diagnostic/dpi1/captures.json'
barcheck={}
if diagnostic.is_file():
    rows=json.loads(diagnostic.read_text(encoding='utf8'))['captures']
    row=next(r for r in rows if 'consortium-partial-1600' in r['file'])
    bars=row['visible_requirement_bars'];assert len(bars)==7 and all(b['value']==420 and b['maximum']==1000 for b in bars)
    image=QImage(str(R/row['file']))
    colors=[image.pixelColor(b['position'][0]+8,b['position'][1]+8).name() for b in bars]
    assert all(color=='#46a66e' for color in colors)
    barcheck=dict(file=row['file'],sha256=hashlib.sha256((R/row['file']).read_bytes()).hexdigest(),visible_bars=bars,left_chunk_colors=colors)
result=dict(verified_captures=len(verified),profiles_actually_viewed=len({(r['logical_size'],r['scale']) for r in viewed}),actually_viewed=viewed,verified_files=verified,progress_pixel_check=barcheck,limitations='Representative 12 final frames actually viewed across all six profiles; not every one of the 66 frames is claimed individually viewed. Qt offscreen; native Windows/DPI-switch/mouse acceptance remains open. Huge numbers and status changes are isolated presentation fixtures. Accepted screenshots are retained independently of later reproduction captures.')
(O/'visual-review.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(dict(verified=len(verified),actually_viewed=len(viewed),profiles=result['profiles_actually_viewed'])))
