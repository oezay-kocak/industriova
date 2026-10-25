"""Uninstrumented packaged startup, using only a fresh isolated save folder."""
from pathlib import Path
from contextlib import closing
import os,json,sqlite3,subprocess,tempfile,time
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase11fg'
folder=Path(tempfile.mkdtemp(prefix='normal-exe-start-',dir=OUT))
exe=ROOT/'dist/economy-rebalance-test/Industriova_0.3_Economy_Rebalance_Test/Industriova_0.3_Economy_Rebalance_Test.exe'
env={k:v for k,v in os.environ.items() if not k.startswith('INDUSTRIOVA_ECONOMY_SMOKE')}
env.update(LOCALAPPDATA=str(folder),QT_QPA_PLATFORM='offscreen')
save=folder/'Industriova/playtests/economy-rebalance-test/saves/company.sqlite'
with (folder/'stdout.txt').open('wb') as stdout,(folder/'stderr.txt').open('wb') as stderr:
    process=subprocess.Popen([str(exe)],cwd=ROOT,env=env,stdout=stdout,stderr=stderr,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        payload=None
        # Normal autosave runs every 30 seconds after window construction.
        # Allow startup time as well, without instrumenting the application.
        for _ in range(100):
            assert process.poll() is None,process.returncode
            if save.exists():
                try:
                    with closing(sqlite3.connect(save.as_uri()+'?mode=ro',uri=True)) as db:
                        row=db.execute("SELECT state_json FROM saves WHERE slot='company'").fetchone()
                        if row:payload=json.loads(row[0]);integrity=db.execute('pragma integrity_check').fetchone()[0];break
                except sqlite3.Error:pass
            time.sleep(.5)
        assert payload is not None and integrity=='ok'
        assert payload['cash']['amount']==1250 and len(payload['cards'])==8 and payload['economy_version']==2
        assert len(payload['halls'])==1 and all(slot['card_id'] is None for hall in payload['halls'].values() for slot in hall['slots'])
        time.sleep(2);assert process.poll() is None
    finally:
        if process.poll() is None:process.terminate()
        process.wait(timeout=15)
errors=(folder/'stderr.txt').read_text(encoding='utf-8',errors='replace')
assert 'Traceback' not in errors and 'Failed to execute script' not in errors,errors
report=dict(folder=str(folder),save_path=str(save),normal_uninstrumented_exe=True,initial_cash=1250,cards=8,economy_version=2,integrity=integrity,startup_exceptions=False,shutdown='Only this isolated test process was deliberately terminated; the instrumented two-launch smoke separately checked graceful close/save/load.')
(OUT/'normal-startup-proof.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
