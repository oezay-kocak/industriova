"""Compare the built Python modules, excluding filenames/line tables only."""
import json,types
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader
root=Path.cwd();reader=CArchiveReader(str(root/'dist/playtest/Industriova/Industriova.exe'))
pyz=reader.open_embedded_archive(next(n for n in reader.toc if n.endswith('.pyz')))
def constant(v):
    if isinstance(v,types.CodeType):return (v.co_name,v.co_code.hex(),v.co_names,v.co_varnames,tuple(constant(c) for c in v.co_consts))
    if isinstance(v,frozenset):return ('set',tuple(sorted(repr(c) for c in v)))
    if isinstance(v,tuple):return tuple(constant(c) for c in v)
    return repr(v)
modules=('config','core.commands','core.freight','core.machine_operations','core.simulation','ui.factory_view','ui.factory_view_v2','ui.freight_drag','ui.freight_view','ui.release_board','ui.release_freight','ui.supply_view')
result={}
for suffix in modules:
    name='production_zero.'+suffix;path=root/'src'/Path(*name.split('.')).with_suffix('.py')
    result[name]=constant(pyz.extract(name))==constant(compile(path.read_bytes(),str(path),'exec',optimize=0))
assert all(result.values()),result
(root/'artifacts/industriova-ui-repair/compiled-modules.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
