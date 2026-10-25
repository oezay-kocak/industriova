"""Run the existing Phase-0 workloads (P3 validation) against an explicit saved source tree.

Outputs are isolated under artifacts/phase3; Phase-0 evidence is never replaced.
The workload/size/fonts remain identical; warm sample counts are raised to seven.
"""
import argparse,os,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def child(source,out,kind):
    sys.path[:0]=[str(source/'src'),str(source/'scripts')]
    os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
    out.mkdir(parents=True,exist_ok=True)
    import types
    path=source/'scripts/phase0_benchmark.py'
    code=path.read_text(encoding='utf8').replace("OUT = ROOT / 'artifacts/phase0'",f'OUT = Path({str(out)!r})')
    # The original first-open remains one cold sample per fresh process.
    code=code.replace('n=5','n=7').replace('n=3','n=7')
    module=types.ModuleType('phase0_benchmark');module.__file__=str(path);sys.modules[module.__name__]=module
    exec(compile(code,str(path),'exec'),module.__dict__)
    if kind in ('ui','actions'):getattr(module,kind)();return
    if kind=='rapid':
        path=source/'scripts/phase0_rapid_ui.py';exec(compile(path.read_text(encoding='utf8'),str(path),'exec'),{'__name__':'__main__','__file__':str(path)});return
    if kind=='extended':
        path=ROOT/'scripts/phase1_ui_actions.py';exec(compile(path.read_text(encoding='utf8'),str(path),'exec'),{'__name__':'__main__','__file__':str(path)});return
    if kind=='active':
        from PySide6.QtWidgets import QApplication
        import release_benchmark
        app=QApplication([]);module.register_fonts(app)
        import json,statistics,time
        samples=[]
        def measured(action,repetitions=7):
            values=[]
            for _ in range(max(7,repetitions)):
                start=time.perf_counter();action();values.append((time.perf_counter()-start)*1000)
            samples.append(dict(samples_ms=values,median_ms=statistics.median(values),max_ms=max(values)))
            return round(statistics.median(values),3)
        release_benchmark.measure=measured
        release_benchmark.run(out/'active-card-baseline.json')
        path=out/'active-card-baseline.json';data=json.loads(path.read_text(encoding='utf8'))
        data['method']='median; unchanged Phase-0 workloads (P3 validation); offscreen Qt; 240 history samples; all measurements 7 repetitions; raw samples in active-samples.json'
        path.write_text(json.dumps(data,indent=2),encoding='utf8')
        names=('render','refresh','tick','snapshot','encoding','commit','full_save','load')
        (out/'active-samples.json').write_text(json.dumps({f'{count}.{name}':values for (count,name),values in zip(((count,name) for count in (10,50,100,500) for name in names),samples)},indent=2),encoding='utf8')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('before','after'));parser.add_argument('kind',choices=('ui','actions','rapid','active','extended'))
    parser.add_argument('--source',type=Path);parser.add_argument('--repeat',type=int,default=1);parser.add_argument('--child',action='store_true');parser.add_argument('--out',type=Path)
    args=parser.parse_args();source=(args.source or ROOT).resolve()
    if args.child:child(source,args.out.resolve(),args.kind)
    else:
        for index in range(args.repeat):
            out=ROOT/'artifacts/phase3'/args.stage/args.kind/f'run-{index+1}'
            out.mkdir(parents=True,exist_ok=True)
            env=dict(os.environ,PYTHONHASHSEED='0')
            with (out/'run.log').open('w',encoding='utf8') as log:
                result=subprocess.run([sys.executable,__file__,args.stage,args.kind,'--source',str(source),'--child','--out',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT)
            print(f'{args.stage} {args.kind} {index+1}: exit {result.returncode}',flush=True)
            if result.returncode:raise SystemExit(result.returncode)
