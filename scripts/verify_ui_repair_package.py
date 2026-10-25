"""Release gate for the UI repair package; no personal save directory access."""
import json,hashlib,zipfile,subprocess
from pathlib import Path
from production_zero.ui.resource_art import RESOURCE_RASTER_ASSETS
root=Path.cwd();out=root/'artifacts/industriova-ui-repair';package=root/'dist/playtest/Industriova-0.2.0-ui-repaired-playtest-Windows.zip'
tested=json.loads((out/'tested-source.json').read_text())
for name,digest in tested['source_sha256'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
with zipfile.ZipFile(package) as z:
    assert z.testzip() is None
    names=set(z.namelist())
    needed={'Industriova/Industriova.exe','Industriova/LIESMICH.txt','Industriova/_internal/PySide6/Qt6Core.dll','Industriova/_internal/PySide6/plugins/platforms/qwindows.dll'}
    assert needed<=names,needed-names
    assets={'Industriova/_internal/'+p.relative_to(root/'src').as_posix() for p in RESOURCE_RASTER_ASSETS.values()}
    assert len(assets)==353 and assets<=names
    assert not [n for n in names if Path(n).suffix.lower() in {'.sqlite','.db','.sqlite3'} or '/saves/' in n.lower() or n.endswith('dev_save.json')]
    assert b'0.2.0.dev2' in z.read('Industriova/LIESMICH.txt')
    assert z.read('Industriova/Industriova.exe')==(root/'dist/playtest/Industriova/Industriova.exe').read_bytes()
command="(Get-Item -LiteralPath 'dist/playtest/Industriova/Industriova.exe').VersionInfo | Select-Object ProductName,ProductVersion,FileVersion,FileDescription,OriginalFilename | ConvertTo-Json"
version=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',command],text=True,encoding='utf-8-sig'))
assert version['ProductName']=='Industriova' and version['ProductVersion']==version['FileVersion']=='0.2.0.dev2'
assert 'Playtest' in version['FileDescription'] and version['OriginalFilename']=='Industriova.exe'
result={'path':str(package),'bytes':package.stat().st_size,'sha256':hashlib.sha256(package.read_bytes()).hexdigest(),'entries':len(names),'resource_images':353,'zip_crc':'ok','personal_saves':0,'tested_source_unchanged':True,'version':version}
(out/'package-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
