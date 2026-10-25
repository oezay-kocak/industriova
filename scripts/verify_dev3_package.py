"""Gate dev3 ZIP integrity, resources, metadata and included Python code."""
import json,hashlib,zipfile,subprocess,types
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader
from production_zero.ui.resource_art import RESOURCE_RASTER_ASSETS
root=Path.cwd();out=root/'artifacts/dev3'
app=root/'dist/playtest/dev3/Industriova';package=root/'dist/playtest/Industriova-0.2.0-dev3-Windows-Playtest.zip'
with zipfile.ZipFile(package) as z:
    assert z.testzip() is None
    names=set(z.namelist())
    needed={'Industriova/Industriova.exe','Industriova/LIESMICH.txt','Industriova/_internal/PySide6/Qt6Core.dll','Industriova/_internal/PySide6/plugins/platforms/qwindows.dll'}
    assert needed<=names
    assets={'Industriova/_internal/'+p.relative_to(root/'src').as_posix() for p in RESOURCE_RASTER_ASSETS.values()}
    assert len(assets)==353 and assets<=names
    assert not [n for n in names if Path(n).suffix.lower() in {'.sqlite','.db','.sqlite3'} or '/saves/' in n.lower() or n.endswith('dev_save.json')]
    readme=z.read('Industriova/LIESMICH.txt').decode('utf-8')
    assert '0.2.0.dev3' in readme and r'%LOCALAPPDATA%\Industriova\saves' in readme
    assert r'%LOCALAPPDATA%\Production Zero' not in readme
    assert z.read('Industriova/Industriova.exe')==(app/'Industriova.exe').read_bytes()
command="(Get-Item -LiteralPath 'dist/playtest/dev3/Industriova/Industriova.exe').VersionInfo | Select-Object ProductName,ProductVersion,FileVersion,FileDescription,OriginalFilename | ConvertTo-Json"
version=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',command],text=True,encoding='utf-8-sig'))
assert version['ProductName']=='Industriova' and version['ProductVersion']==version['FileVersion']=='0.2.0.dev3'
assert 'Playtest' in version['FileDescription']
reader=CArchiveReader(str(app/'Industriova.exe'));pyz=reader.open_embedded_archive(next(n for n in reader.toc if n.endswith('.pyz')))
def constant(v):
    if isinstance(v,types.CodeType):return (v.co_name,v.co_code.hex(),v.co_names,v.co_varnames,tuple(constant(c) for c in v.co_consts))
    if isinstance(v,frozenset):return ('set',tuple(sorted(repr(c) for c in v)))
    if isinstance(v,tuple):return tuple(constant(c) for c in v)
    return repr(v)
modules=['config','persistence.paths','persistence.dev_save_store','persistence.sqlite_store','persistence.session_writer',
         'ui.main_window','ui.dev_tools_view','ui.factory_view','ui.factory_view_v2','ui.freight_view','ui.contracts_view',
         'ui.release_board','ui.release_dialogs','ui.release_freight','ui.interaction_polish','ui.global_resources','ui.material_frame','ui.game_ui.widgets',
         'core.contracts','core.infrastructure','core.commands','core.simulation','core.mk_upgrades','core.machine_operations']
compiled={}
for suffix in modules:
    name='production_zero.'+suffix;p=root/'src'/Path(*name.split('.')).with_suffix('.py')
    compiled[name]=constant(pyz.extract(name))==constant(compile(p.read_bytes(),str(p),'exec',optimize=0))
assert all(compiled.values()),compiled
entry_code=next(reader.extract(n) for n in reader.toc if n=='__main__')
import marshal
assert constant(marshal.loads(entry_code))==constant(compile((root/'src/production_zero/app/__main__.py').read_bytes(),'__main__.py','exec',optimize=0))
compiled['production_zero.app.__main__']=True
result={'path':str(package),'bytes':package.stat().st_size,'sha256':hashlib.sha256(package.read_bytes()).hexdigest(),
        'entries':len(names),'resource_images':len(assets),'zip_crc':'ok','personal_saves':0,'version':version,'compiled_modules_match':compiled}
(out/'package-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
