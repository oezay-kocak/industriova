"""Start the packaged Windows EXE offscreen using isolated synthetic save folders."""
import hashlib,json,os,sqlite3,subprocess,time
from pathlib import Path
root=Path.cwd();out=root/'artifacts/final-polish/headless-exe-verified';out.mkdir(parents=True,exist_ok=True)
legacy=out/'Industriova/saves/company.sqlite';legacy.parent.mkdir(parents=True,exist_ok=True)
legacy.write_bytes(b'Synthetic dev4 save. Dev5 must ignore this file.')
old_hash=hashlib.sha256(legacy.read_bytes()).hexdigest()
save=out/'Industriova/playtests/dev5/saves/company.sqlite'
assert not save.exists(),'Use a fresh test directory; preserve prior evidence.'
environment=dict(os.environ,LOCALAPPDATA=str(out),QT_QPA_PLATFORM='offscreen',QT_SCALE_FACTOR='1')
exe=root/'dist/playtest/dev5/Industriova/Industriova.exe'
flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
with (out/'stdout.txt').open('wb') as stdout,(out/'stderr.txt').open('wb') as stderr:
 process=subprocess.Popen([str(exe)],env=environment,stdout=stdout,stderr=stderr,creationflags=flags)
 try:
  payload=None
  for _ in range(100):
   assert process.poll() is None,f'Unexpected startup exit {process.returncode}'
   if save.exists():
    try:
     with sqlite3.connect(save.as_uri()+'?mode=ro',uri=True) as db:
      row=db.execute("select state_json from saves where slot='company'").fetchone()
      if row:payload=json.loads(row[0]);integrity=db.execute('pragma integrity_check').fetchone()[0];break
    except sqlite3.Error:pass
   time.sleep(.5)
  assert payload is not None,'No initial company save after 50 seconds'
  time.sleep(3);assert process.poll() is None,'EXE exited after initialization'
  assert payload['cash']['amount']==1250 and len(payload['cards'])==8 and payload['state_schema_version']==6
  assert payload['freight']['facilities']['garage-1']['line_capacity']==8
  assert not any(s['card_id'] for u in payload['halls'].values() for s in u['slots'])
  assert integrity=='ok' and hashlib.sha256(legacy.read_bytes()).hexdigest()==old_hash
 finally:
  if process.poll() is None:process.terminate()
  process.wait(timeout=15)
errors=(out/'stderr.txt').read_text(encoding='utf-8',errors='replace')
assert 'Traceback' not in errors and 'Failed to execute script' not in errors,errors
result={'mode':'Windows EXE with QT_QPA_PLATFORM=offscreen; no visible window or native UI automation',
 'save_path':str(save),'initial_cash':payload['cash']['amount'],'starter_cards':len(payload['cards']),
 'schema':payload['state_schema_version'],'freight_line_capacity':8,'sqlite_integrity':integrity,
 'synthetic_dev4_save_ignored_and_unchanged':True,'startup_survived':True,
 'shutdown':'Test process deliberately terminated after headless startup checks; this is not a normal UI-close test.',
 'stderr':errors}
(out/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
