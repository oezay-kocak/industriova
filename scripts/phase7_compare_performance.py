"""Summarize completed serial raw samples without replacing earlier evidence."""
import json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase7'
assert json.loads((OUT/'performance-complete.json').read_text(encoding='utf8'))['ok']
def read(path):return json.loads(path.read_text(encoding='utf8'))
data={}
for stage in ('before','after'):
    data[stage]={}
    data[stage].update({'command.'+name:r for name,r in read(OUT/stage/'purchases/results.json')['results'].items()})
    data[stage].update({'active.'+name:r for name,r in read(OUT/stage/'active/run-1/active-samples.json').items()})
    data[stage].update({'ui.'+name:r for name,r in read(OUT/stage/'extended/run-1/ui-actions.json').items()})
    data[stage].update({'ui.'+name:r for name,r in read(OUT/stage/'rapid/run-1/rapid-ui-baseline.json')['measurements'].items() if name.startswith('rapid_ui.')})
rows=[]
for name,before in data['before'].items():
    after=data['after'][name]
    assert len(before['samples_ms'])>=7 and len(after['samples_ms'])>=7
    rows.append(dict(operation=name,before=before,after=after,ratio=after['median_ms']/before['median_ms']))
regressions=[r['operation'] for r in rows if r['ratio']>1.1 and r['after']['median_ms']>1]
(OUT/'performance-comparison.json').write_text(json.dumps(dict(rows=rows,greater_than_ten_percent_and_one_ms=regressions),indent=2),encoding='utf8')
text=['# P7: serielle Laufzeitvergleiche','','Vorher: gesicherter P6-Quellbaum; nachher: finaler P7-Quellbaum. Gleiche Workloads, Qt offscreen 100 %, frische Prozesse je Messart. 21 warme Commandproben, sieben aktive/erweiterte Proben, 20 aufeinanderfolgende Supply-Käufe pro Firma. Keine gleichzeitig laufenden Tests, Captureläufe oder Hashprüfungen.','',
'Die aktiven Firmen enthalten 10/50/100/500 Karten und synthetische einzelne Resources-Sites zur Skalierungsmessung; kein Wirtschaftsspielverlauf. Die UI-Aktionen verwenden die bisherigen 50/500-Karten-Factory-Fixtures. slots7 bedeutet sieben einzelne Slotkäufe, mk4 vier einzelne bestätigte Upgrades. sale20 und rapid_ui messen jeweils 20 einzelne Vorgänge. UI-Zeiten enthalten den Event-Drain, Commands keinen Dialog und keine menschliche Wartezeit.','',
'| Operation | Vorher Median / Max ms | Nachher Median / Max ms | Verhältnis |','| --- | --- | --- | --- |']
for r in rows:
    b,a=r['before'],r['after'];text.append(f"| {r['operation']} | {b['median_ms']:.4f} / {b['max_ms']:.4f} | {a['median_ms']:.4f} / {a['max_ms']:.4f} | {r['ratio']:.3f}× |")
text+=['','Mehr als 10 % höherer Median bei zugleich mehr als 1 ms nachher: '+(', '.join(regressions) if regressions else 'keine Operation in diesen Stichproben')+'. Maximalzeiten und einzelne Ausreißer stehen vollständig in den Rohdaten; keine FPS-Zusage und kein Beweis für statistische Gleichheit. Preisfunktionen führen keine Audits oder Produktionssimulationen aus.']
(OUT/'performance-comparison.md').write_text('\n'.join(text)+'\n',encoding='utf8')
print(json.dumps(dict(operations=len(rows),regressions=regressions)),flush=True)
