"""Fill the requested engineering report only from completed raw evidence."""
import hashlib,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase1'
read=lambda p:json.loads(p.read_text(encoding='utf8'))
comparison=read(OUT/'comparison.json');summary=read(OUT/'final-test-summary.json');visual=read(OUT/'visual-comparison.json');protected=read(OUT/'protected-verification.json')
assert summary['failures']==summary['skipped']==0 and summary['tests']>=1257
assert len(visual)==18 and all(row['identical'] for row in visual) and protected['ok']
active_before=read(OUT/'before/active/run-1/active-card-baseline.json')['results']
active_after=read(OUT/'after/active/run-1/active-card-baseline.json')['results']
assert [(r['cards'],r['payload_bytes']) for r in active_before]==[(r['cards'],r['payload_bytes']) for r in active_after]
def fmt(row):return f"{row['median_ms']:.2f} / {row['max_ms']:.2f}"
def table(kind,labels):
    lines=['| Messung | n vorher / nachher | Vorher Median / Max ms | Nachher Median / Max ms |','| --- | --- | --- | --- |']
    for label,title in labels:
        b=comparison['before'][kind][label];a=comparison['after'][kind][label]
        if kind not in ('active','rapid_bursts'):b,a=b['total'],a['total']
        lines.append(f"| {title} | {b['n']} / {a['n']} | {fmt(b)} | {fmt(a)} |")
    return '\n'.join(lines)
def cold(stage):
    rows=[read(p)['measurements'] for p in (OUT/stage/'ui').glob('run-*/ui-baseline.json')]
    values=[r['unlock.constructor.cold']['samples_ms'][0]+r['unlock.first_show']['samples_ms'][0] for r in rows]
    return dict(n=len(values),median_ms=statistics.median(values),max_ms=max(values))
before_cold,after_cold=cold('before'),cold('after')
memory={stage:dict(median=statistics.median(comparison[stage]['unlock_memory_mib']),maximum=max(comparison[stage]['unlock_memory_mib'])) for stage in ('before','after')}
ui=[('unlock.constructor.cold','Unlock: Konstruktion'),('unlock.first_show','Unlock: erstes Show/Layout/Paint'),('unlock.rebuild.warm','Unlock: unveränderter Rebuild'),('unlock.refresh','Unlock: unveränderter Statusrefresh'),('unlock.render','Unlock: vollständiges Rendern'),('unlock.zoom_pan','Unlock: Zoomschritt + Pan + Events'),('guide.first_open','Guide: erstes Öffnen'),('guide.close_reopen','Guide: Board zurück / erneut öffnen'),('guide.search','Guide: steel + zurück, zwei Filter'),('guide.filter','Guide: Processing + All, zwei Filter'),('guide.list_graph_roundtrip','Guide: Steel-Chain + zurück'),('guide.render','Guide: Rendern'),('leaderboard.picker_construct','Picker: neue Instanz konstruieren'),('leaderboard.picker_show','Picker: erstes Show/Paint'),('leaderboard.picker_filter','Picker: iron + zurück'),('leaderboard.unchanged_refresh','Leaderboard: unverändert'),('leaderboard.changed_refresh','Leaderboard: Produktionswert geändert')]
metrics='''## Messmethode und Ergebnisse

Windows 11, Python 3.12.14, Qt/PySide6 6.11.1, Offscreen-Qt, `PYTHONHASHSEED=0`, 1366×768 und Qt-Skalierung 1. Gleiche explizite Windowsfont-Registrierung und Stylesheets wie in Phase 0; echte MainWindow-Kaufproben verwenden dessen normalen Anwendungsstil. Vorher-Quellen kommen aus der neuen P1-Sicherung. Die Phase-0-Skripte und ursprünglichen Rohdaten wurden nicht überschrieben. Der Wrapper verändert ausschließlich Ausgabeziel und Wiederholungszahl, keine Datengröße, Fensterfläche oder Wirtschaftswerte.

Jeder Cold-View-Aufbau wurde siebenmal in frischen Prozessen gemessen. Warme UI-Operationen umfassen 7×7 = 49 Stichproben. Core-, aktive Karten-/Save- und zusätzliche UI-Aktionsmessungen haben jeweils mindestens sieben Wiederholungen. Käufe: sieben 20er-Bursts je Firmengröße, 140 einzelne Kaufcallbacks. Kein paralleler Test-/Build-/Benchmarkprozess während der Performance-Messungen. Alle Zeiten in ms, Stichprobenmedian und Maximum; keine p95-Schätzung. Kombinierte Callback-plus-Event-Zeiten sind keine nativen FPS.

Die ursprüngliche Phase-0-Einzelmessung lag bei 2.265,73 ms Unlock-Konstruktion, 406,33 ms warmem Rebuild, 3.854,54 ms Guide und rund 2.549 ms Picker. Die neuen Vorher-Wiederholungen reproduzieren diese Größenordnung. Folgende Tabellen vergleichen die wiederholte Vorher-Messung mit dem endgültigen Stand einschließlich Rasteratlas.

'''+table('ui',ui)+f'''

**Vollständiger Unlock-Cold-Open (Konstruktion + erstes Show/Paint, paarweise je Prozess): {fmt(before_cold)} → {fmt(after_cold)} ms**, jeweils sieben Stichproben. Die bloße Konstruktion wäre bei verzögerten Icons allein irreführend.

**Unlock-Working-Set-Zuwachs beim ersten Öffnen:** Median {memory['before']['median']:.2f} → {memory['after']['median']:.2f} MiB; Maximum {memory['before']['maximum']:.2f} → {memory['after']['maximum']:.2f} MiB, je sieben frische Prozesse. Das umfasst Bilder, Fonts, Qt, Szene und Heap; keine isolierte Cacheallokation oder Langzeit-Leakmessung.

'''

for stage,title in (('before','Vorher'),('after','Nachher')):
    guide=comparison[stage]['guide_objects'][0];picker=comparison[stage]['picker_objects'][0]
    metrics+=f"{title}, erster UI-Lauf: Guide {guide['tiles_created']} materialisierte Kacheln / {guide['widgets']} QWidget-Nachfahren der gesamten View; Picker {picker['products']} materialisierte Kacheln / {picker['widgets']} Widgets. "
metrics+='''Der logische Katalog umfasst in beiden Ständen 353 Produkte. Das historische JSON-Feld `picker.products` zählt materialisierte Tiles; es bedeutet im neuen bedarfsgerechten Picker nicht die logische Produktmenge. Die Widgetzählung schließt zurückgehaltene und eventuell noch auf DeferredDelete wartende Kinder ein. Die Regression erreicht alle 353 Guide-Produkte; Caches dürfen sich bei weiteren Besuchen füllen.

### UI-Blockierung und schnelle Aktionen

Die Rohdaten trennen synchrone Callbackdauer, Gesamtzeit einschließlich Event-Drain und den vor dem Callback eingereihten Zero-Timer. Letzterer kann vor Paint laufen und ist daher keine Obergrenze der sichtbaren Unterbrechung. `comparison.json` enthält für jede Reihe Median/Maximum/N dieser drei Größen; `comparison-tables.md` enthält alle Ergebnisse einschließlich sämtlicher Core-Kontrollmessungen.

'''+table('rapid_bursts',[(f'rapid_ui.{n}.20_individual_purchases',f'{n} Karten: kompletter 20er-Kaufburst') for n in (50,500)])+'\n\n'+table('rapid',[(f'rapid_ui.{n}.20_individual_purchases',f'{n} Karten: einzelner Kauf innerhalb des Bursts') for n in (50,500)])+'\n\n'
guide_totals={}
for stage in ('before','after'):
    values=[]
    for file in (OUT/stage/'ui').glob('run-*/ui-baseline.json'):
        measurements=read(file)['measurements']
        values.append(sum(sum(row['samples_ms']) for name,row in measurements.items() if name.startswith('guide.')))
    guide_totals[stage]=dict(median_ms=statistics.median(values),max_ms=max(values))
metrics+=f"Die erste Processing-Filterauswahl erzeugt erstmals zusätzlich benötigte Kacheln. Deshalb steigt das Filterpaar-Maximum von {comparison['before']['ui']['guide.filter']['total']['max_ms']:.2f} auf {comparison['after']['ui']['guide.filter']['total']['max_ms']:.2f} ms, obwohl der Median sinkt. Dies ist die konkret verbleibende Gegenleistung der bedarfsgerechten Materialisierung; sie wird nicht als Framebudget-Erfolg ausgegeben. Die Summe aller gemessenen Guide-Intervalle pro identischem UI-Lauf (Öffnen und je sieben Such-/Filter-, Render- und Navigationsintervalle, ohne Setup/Profile) beträgt vorher {fmt(guide_totals['before'])}, nachher {fmt(guide_totals['after'])} ms. Der frühere mehrsekündige Komplettaufbau wird vermieden.\n\n"
blocking=['| UI-Pfad | Callback vorher Median / Max | Callback nachher Median / Max | Queue vorher Median / Max | Queue nachher Median / Max |','| --- | --- | --- | --- | --- |']
for label,title in (('unlock.constructor.cold','Unlock-Konstruktion'),('unlock.refresh','Unlock-Status'),('unlock.zoom_pan','Zoom + Pan'),('guide.first_open','Guide erstes Öffnen'),('guide.search','Guide Suchpaar'),('guide.filter','Guide Filterpaar'),('guide.close_reopen','Guide zurück / erneut öffnen'),('leaderboard.changed_refresh','Leaderboard-Wertänderung'),('selection.500.shift','500er Shift-Auswahl')):
    b=comparison['before']['ui'][label];a=comparison['after']['ui'][label]
    blocking.append(f"| {title} | {fmt(b['callback'])} | {fmt(a['callback'])} | {fmt(b['queue'])} | {fmt(a['queue'])} |")
metrics+='\n'.join(blocking)+'\n\n'
metrics+=table('extended',[(f'{n}.{action}',f'{n} Karten: {title}') for n in (50,500) for action,title in (('sale20','20 einzelne Verkäufe'),('mk4','vier MK-Upgrades'),('slots7','sieben Slotfreischaltungen'),('recipe20','20 Rezeptzuweisungen'),('copy_paste10','Copy / Kauf von zehn Templates'))])
metrics+='''

Kaufproben verwenden die echte MainWindow-Verkabelung und die vorhandenen Supply-Callbacks. Zusätzliche Aktionsproben messen den bestätigten Arbeitsanteil ohne menschliche Modalwartezeit; Fixtures und Vorbereitungen liegen außerhalb der Uhr. Es sind dieselben legalen Hallen mit 50 Plätzen wie in Phase 0, bei 500 Karten entsprechend mehrere Hallen. Alle sieben Wiederholungen prüfen die erwartete Transaktionszahl und resultierende Karten-/Slot-/MK-/Rezeptdaten. Copy erzeugt weiter keine Wirtschaftsaktion; Paste kauft weiter neue MK1-Common-Maschinen. Die UI-Regression prüft Cash-Text und exakten Cash-Tooltip unmittelbar nach Aktionen, unveränderte Widgetidentitäten sowie den notwendigen Refresh beim Tabwechsel.

### Große aktive Firmen, Rendering und Savekosten

'''+table('active',[(f'{n}.{name}',f'{n} aktive Karten: {title}') for n in (10,50,100,500) for name,title in (('render','vollständige Kartenfläche rendern'),('refresh','Runtime-Refresh'),('snapshot','Snapshot Hauptthread'))])+'\n\n'
metrics+=table('active',[(f'500.{name}',f'500 aktive Karten: {title}') for name,title in (('tick','Simulationstick'),('encoding','Snapshot-Encoding'),('commit','SQLite-Commit'),('full_save','Snapshot + Encoding + Commit'),('load','Load'))])
metrics+='''

Die aktive Phase-0-Fixture bleibt vollständig erhalten: ein aktiver Extraktor pro Standort, dieselbe große vollständige Renderfläche, dieselben Slotstrukturen und 240 Historywerte pro Serie. Der umfangreiche Standort-/Slotbestand erklärt einen Teil der verbleibenden Serialisierungskosten. Payloadgrößen bleiben gleich; es werden keine Daten oder Historien zur Beschleunigung weggelassen. Encoding/Commit/Load laufen im echten SessionWriter weiter außerhalb des Hauptthreads; die Tabelle misst ihre Einzelkosten separat synchron. Der Snapshot selbst bleibt Hauptthreadarbeit.

### Auswahl-Stresstest

'''+table('ui',[(f'selection.{n}.{key}',f'{n} Karten: {title}') for n in (10,50,100,500) for key,title in (('shift','Shift-Auswahl inklusive Paint'),('rectangle_release','Rechteckauswahl abschließen'),('100_rectangle_moves','100 Rechteckbewegungen'),('redraw','vollständige Boardfläche rendern'))])
metrics+='''

100 und 500 Karten auf **einem** Auswahlboard sind die unveränderten synthetischen Phase-0-Stressfixtures oberhalb der realen Hallengrenze; die Aktionen mit einer 500-Karten-Firma verwenden dagegen mehrere normale Hallen. Das Auswahlboard bleibt 1366×768 mit derselben Scrollfläche; sein Rendern zeichnet den Viewport, während die separate aktive Kartenprobe die große vollständige Kartenfläche zeichnet. Die Auswahlfilter werden nicht als Engpass neu erfunden. Paint und Geometriearbeit sind getrennt von den kleinen Filter-/Auswahlcallbacks zu betrachten.

Reproduktion: `scripts/phase1_validate.py --after-only --test-output final-atlas-tests` führt vollständige Regression, alle Nachher-Messungen, sechs Capture-Konfigurationen, Vergleiche und Schutzprüfung seriell aus. Einzelmessungen: `phase1_measure.py before|after ui|actions|rapid|active|extended`; für Vorher `--source artifacts/phase1/before-tree`, für Cold-UI und Kaufbursts zusätzlich `--repeat 7`. Bestehende Ausgaben vor einer erneuten Messung in ein eigenes Versuchsverzeichnis sichern.

'''
tail=f'''## Tests, visuelle Regression und verbleibende Grenzen

**{summary['tests']}/{summary['tests']} Tests in {summary['modules']}/{summary['modules']} Modulen bestanden, 0 Fehler, 0 Skips.** Alle ursprünglichen 1.257 Fälle und ihre Modul-Fallzahlen sind erhalten; 13 neue Regressionen einschließlich Parameterfällen ergänzen sie. Der abschließende vollständige, serielle Lauf des endgültigen Atlas-Stands liegt unter `artifacts/phase1/final-atlas-tests/`; `final-test-summary.json` fasst ihn zusammen. Frühere fehlgeschlagene/korrigierte Versuche bleiben zur Nachvollziehbarkeit erhalten.

Gezielte neue Nachweise: Graphbestand und Poolidentität, kein eager Iconaufbau, Mengenlabel-Repaint bei tatsächlicher Änderung, pixelgleiche Icons mit/ohne Stylesheet, sämtliche 1.059 Rastervarianten und Original-SHA256, alle 353 Guide-Produkte, sofortige Progressionsaktualisierung, Reset und Boardwiederverwendung, Picker-Suche/Scroll/Identität, eigene Leaderboard-Row/Highlight/aktuelles Profil mit großen Zahlen, Pausenhierarchie inklusive Move/Gruppenpermutation und Load, echte 20er-Aktionen bei 50/500 Karten, Slotänderungen ohne fremden Linienaufbau sowie Snapshot-/Schreibfehler-/New-Game-Reihenfolge.

Zwei bestehende Testdateien wurden fachlich angepasst: `tests/test_factory_ui.py` erreicht noch nicht erzeugte Guide-Produkte über die vorhandene Suche, prüft verborgene wiederverwendete Boards statt deren erzwungener Löschung und fordert Runtime-Rekonnektion nach einer echten Strukturänderung. Suchtext-/Scroll-Erhalt bleibt geprüft. `tests/test_secondary_modernization.py` unterscheidet neu erreichte Tiles von bereits erzeugten und prüft deren Identität beim erneuten gleichen Filter. Keine Fälle wurden entfernt, deaktiviert oder übersprungen. Der bestehende Rechteckauswahltest blieb fachlich unverändert und deckte den korrigierten synchronen Layoutabschluss nach Linienersatz auf.

**36 Vergleichsscreenshots, 18 Paare, alle pixelgleich:** Unlock Tree, Guide und Leaderboard bei 1366×768, 1600×980 und 1920×1080, jeweils 100 % und 200 % Qt-Skalierung. Dateien unter `artifacts/phase1/before/dpi1|dpi2/` und `after/dpi1|dpi2/`; sämtliche Pixelvergleiche einschließlich tatsächlicher Bildgrößen in `visual-comparison.json`. Die Fonts wurden ausdrücklich registriert. Der statische Vergleich und erhaltene Row-/Kachelidentitäten sichern Darstellung und beseitigte strukturelle Flackerursachen; native DWM-/GPU-Bewegungsqualität und menschlich bewertetes Pan-/Zoom-Gefühl sind damit nicht als geprüft behauptet.

Die abschließende SHA-256-Schutzprüfung bestätigt {len(protected['protected'])} unveränderte Bestandsdateien aus Builds, Phase-0-Nachweisen, Originalgrafiken, Styles, Spieldaten, unveränderter Core-Wirtschaftslogik und SQLite-Serializer sowie alle fünf persönlichen Saves. Details: `protected-verification.json`. Der einzige Core-Eingriff ist der optionale vorberechnete Darstellungs-Kontext für Requirementtexte; Formeln, Preise und Freischaltregeln bleiben identisch.

Das 16-ms-Ziel ist **kein pauschaler Erfolg**: Unveränderte Status-/Ranking-Updates und die große aktive Runtime-Probe sind anhand der Tabellen zu bewerten; komplette Szenen-/Board-Paints, Filterpaare mit Layoutarbeit, erste bedarfsgerechte Materialisierung, Chain-Roundtrips und große Snapshots können darüber liegen. Ein erstmaliger Filter kann neue Kacheln anlegen; sein Maximum darf nicht mit einem bereits warmen Cache verwechselt werden. Alle Maxima bleiben im Bericht sichtbar. Der begrenzte globale Quellbildcache kann bei großen Vorschauen weiterhin bis zum vollständigen Originalkatalog wachsen. Native Framerate und stundenlange Speichernutzung wurden nicht gemessen.

Snapshotkosten oberhalb eines Frames bleiben wegen vollständiger Datenerfassung und Containerablösung bestehen; es wurde keine Integrität zugunsten einer kleineren Messfixture aufgegeben. Weitere Rendering-/Serialisierungsarbeit ist als verbleibender Aufwand dokumentiert und eröffnet keine spätere Roadmap-Phase. Keine Gameplay-/Balancing-/Inventoryänderung und kein Windows-Build.

Zusätzliche Dateien zur Reproduktion: `scripts/phase1_measure.py`, `phase1_capture.py`, `phase1_compare.py`, `phase1_ui_actions.py`, `phase1_validate.py`, `phase1_visual_compare.py`, `phase1_verify_protected.py`, `phase1_rerun.py`, `phase1_raster_atlas.py`, `phase1_finish_report.py` und `tests/test_phase1_performance.py`. Produktive Änderungen sind vollständig in der Dateitabelle oben aufgeführt.
'''
path=ROOT/'docs/industriova-03-phase1-performance-report.md';document=path.read_text(encoding='utf8')
start=document.index('## Messmethode und Ergebnisse');end=document.index('## Getrennte Snapshot-/Save-Prüfung')
document=document[:start]+metrics+document[end:]
document=document[:document.index('## Tests, visuelle Regression und verbleibende Grenzen')]+tail
path.write_text(document,encoding='utf8')
print(path,summary, 'cold open',fmt(before_cold),'->',fmt(after_cold),'memory',memory)
