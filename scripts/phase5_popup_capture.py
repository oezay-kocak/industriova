"""Retain the failed popup visuals and capture the corrected final surfaces."""
import os,json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase5'
for name in ('screenshots','visual-verification.json'):
    source=OUT/name;target=OUT/('before-popup-fix-'+name)
    assert source.resolve().is_relative_to(OUT.resolve()) and target.resolve().is_relative_to(OUT.resolve())
    assert not target.exists()
    source.rename(target)
for scale in ('1','2'):
    env=dict(os.environ,QT_SCALE_FACTOR=scale)
    with (OUT/f'popup-fixed-capture-dpi{scale}.log').open('w',encoding='utf8') as log:
        result=subprocess.run([sys.executable,'scripts/phase5_capture.py'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    print('popup-fixed capture',scale,result.returncode,flush=True);assert result.returncode==0
result=subprocess.run([sys.executable,'scripts/phase5_verify_visual.py'],cwd=ROOT)
assert result.returncode==0
