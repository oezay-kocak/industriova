"""Coordinate independent evidence jobs, with content-bound reusable results."""
import hashlib,json,os,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def begin(out,name,source):
    digest=hashlib.sha256()
    paths=[p for p in (source.resolve()/'src').rglob('*') if p.is_file() and p.suffix in {'.py','.json'} and '__pycache__' not in p.parts]
    paths += [ROOT/'scripts'/p for p in ('phase8_simulation_checkpoint.py','phase8_contract_simulation.py','phase8_consortium_simulation.py','phase8_offline_work_cache.py')]
    paths += [ROOT/'src/production_zero/core/contract_capacity.py']
    for p in sorted(paths):digest.update(str(p).encode());digest.update(p.read_bytes())
    fingerprint=digest.hexdigest();result=out/name;lock=out/(name+'.running')
    while True:
        if result.is_file() and json.loads(result.read_text(encoding='utf8')).get('evidence_fingerprint')==fingerprint:
            print('REUSING VERIFIED CONTENT-BOUND RESULT',str(result),flush=True);return None
        try:
            with lock.open('x',encoding='utf8') as stream:json.dump(dict(fingerprint=fingerprint,pid=os.getpid()),stream)
            return fingerprint
        except FileExistsError:
            value=json.loads(lock.read_text(encoding='utf8'))
            assert value['fingerprint']==fingerprint,'Different simulation already owns output folder'
            time.sleep(1)
def finish(out,name,result,fingerprint):
    result['evidence_fingerprint']=fingerprint
    path=out/name;temporary=path.with_suffix('.pending.json')
    temporary.write_text(json.dumps(result,indent=2),encoding='utf8');temporary.replace(path)
    (out/(name+'.running')).unlink()
