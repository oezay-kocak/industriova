"""Generate P4 report only from completed checks and raw measurements."""
import json,hashlib,difflib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase4'
def read(p):return json.loads(p.read_text(encoding='utf8'))
summary=read(OUT/'final-test-summary.json');protected=read(OUT/'protected-verification.json')
assert protected['ok'] and summary['original_cases']==1381 and summary['failures']==summary['errors']==summary['skipped']==0
backup=Path((OUT/'backup-location.txt').read_text(encoding='utf8'));manifest=read(backup/'manifest.json')
assert read(OUT/'migration-comparison.json')['passed']==16
comparisons=read(OUT/'comparison.json')
drag={stage:read(OUT/stage/'drag/measurements.json') for stage in ('before','after')}
inventory={stage:read(OUT/stage/'inventory-ui-benchmark.json')['fixtures'] for stage in ('before','after')}
captures=[r for scale in ('1','2') for r in read(OUT/'screenshots'/('dpi'+scale)/'captures.json')]
assert len(captures)==90
from PySide6.QtGui import QImage
for row in captures:
    image=QImage(str(ROOT/row['file']))
    assert not image.isNull() and image.width()==row['width'] and image.height()==row['height']
    assert row['width']==round(row['logical_width']*row['scale']) and row['height']==round(row['logical_height']*row['scale'])
(OUT/'visual-verification.json').write_text(json.dumps(dict(captures=len(captures),dimensions_verified=True,native_hand_acceptance=False),indent=2),encoding='utf8')
def ms(row):return f"{row['median_ms']:.2f} / {row['max_ms']:.2f}"
dragtable=['| Surface / operation | Before median / max ms | After median / max ms |','| --- | --- | --- |']
for name,row in drag['after'].items():
    if 'median_ms' not in row:continue
    previous=drag['before'].get(name)
    dragtable.append(f"| {name} | {ms(previous) if previous else 'new work'} | {ms(row)} |")
invtable=['| Cards / stacks | Open before → after ms | Refresh before → after ms | Scroll before → after ms | Card widgets |', '| --- | --- | --- | --- | --- |']
for name,a in inventory['after'].items():
    b=inventory['before'][name]
    assert (a['payload_sha256'],a['payload_bytes'])==(b['payload_sha256'],b['payload_bytes'])
    invtable.append(f"| {name} | {ms(b['cold_open'])} → {ms(a['cold_open'])} | {ms(b['refresh'])} → {ms(a['refresh'])} | {ms(b['scroll_pair'])} → {ms(a['scroll_pair'])} | {a['card_widgets']} |")
controls=['| P1 control | n before / after | Before median / max ms | After median / max ms |', '| --- | --- | --- | --- |']
regressions=[]
for kind in ('ui','rapid_bursts','active','extended'):
    for name,b in comparisons['before'][kind].items():
        a=comparisons['after'][kind].get(name)
        if not a:continue
        if 'total' in b:b=b['total'];a=a['total']
        if not b or not a:continue
        controls.append(f"| {kind}: {name} | {b['n']} / {a['n']} | {ms(b)} | {ms(a)} |")
        if a['median_ms']>b['median_ms']*1.1 and a['median_ms']>1:
            regressions.append(f"{kind}:{name} {b['median_ms']:.2f} → {a['median_ms']:.2f} ms")
report=f'''# INDUSTRIOVA 0.3 – P4: Card swaps and drag interaction

Stand: 22.10.2026. Ausschließlich P4, auf dem gesicherten tatsächlichen P3-Working-Tree. Kein Windows-Build; P5–P9, Preise, Supply/Inventory-Regeln und Save-Schema nicht erweitert.

## 1. Sicherung und Umfang

Vor produktiven Änderungen: `{backup.relative_to(ROOT).as_posix()}` mit {len(manifest['entries']):,} Dateien und {sum(e['bytes'] for e in manifest['entries']):,} Quelldatei-Bytes. Inkrementelles Working-Tree-Delta mit vollständigem SHA256-Inventar und rekursiven P3/P2/P1/P0-Abhängigkeiten; große Altarchive bleiben pfad-/hashgebundene Abhängigkeiten. Zusätzlich unabhängiges `source-baseline.zip`, CRC-geprüft und jeder extrahierte Quellinhalt gegen Manifest-SHA verifiziert. Archiv-/Manifest-Summen: `SHA256SUMS.json`. Kein Git-HEAD-Reset.

Alle fünf persönlichen SQLite-Dateien sind roh sowie über read-only SQLite-Backup gesichert, jeweils `integrity_check=ok`. Kein Original wurde geladen, migriert oder geschrieben. Wiederherstellung ausschließlich in einen neuen Ordner nach Manifest, nicht über bestehende Spielstände. Alle Tests/Captures verwenden isolierte AppData-/Tempverzeichnisse.

Abschluss: **{len(protected['protected']):,} geschützte bestehende Dateien und alle fünf persönlichen Saves SHA256-unverändert**, einschließlich vorhandener build/dist-Dateien, Originalassets/Atlas, Spieldaten, Simulation, Templatekauf, Serializer/Writer und P0–P3-Referenzdaten. Die von alten Tests überschriebenen Previewpfade wurden unter P4 erhalten und ihre ursprünglichen Referenzen aus der geprüften Sicherung wiederhergestellt (`legacy-capture-preservation.json`).

## 2. Geänderte Komponenten

Produktive Pfade unter `src/production_zero/`:

| Datei | Änderung |
| --- | --- |
| `core/machine_operations.py` | Gemeinsamer reiner `plan_slot_permutation`, unveränderliche Ursprungssnapshots, vorbereiteter Commit; bestehender `move_machines` verwendet denselben Plan. |
| `core/freight.py` | `plan_freight_moves` delegiert an denselben Plan; vorhandene Einzelmove-/Validierungs-API erhalten, beide Richtungen und Busy-Gegenkarten validiert. |
| `core/commands.py` | `MoveMachines` und `MoveFreightVehicles` optional mit erwarteten Ursprüngen; Gruppencommand committed den vollständigen Plan. `MoveFreightVehicle` nutzt denselben Einzelpfad. |
| `ui/release_board.py` | Session-/Kartenregistertoken und eigene UUID je Drag-Geste, konkrete Ursprünge im vorhandenen MIME, vollständig validierter Hover/Drop, korrekter Hotspot, Auswahl bleibt auf IDs, Cleanup in `finally`. |
| `ui/factory_view_v2.py` | Original-Greifpunkt bei Press speichern; bei vollständigem Boardersatz laufenden Drag aufräumen. Bestehende Linien-/Karten-Caches erhalten. |
| `ui/factory_view.py` | Reset invalidiert Drag-Token und temporäre Daten; Runtime prüft nur bei aktivem Drag die Ursprungsgültigkeit. |
| `ui/freight_drag.py` | Bestehender lokaler Pointer-Capture-Pfad erweitert: stabile Gruppenauswahl, Maus-Ghost, Swap-Hover, frische Commitprüfung, Wheel und vollständiges Cleanup. Keine neue OS-Drag-Schleife. |
| `ui/freight_view.py` | Vor Neumaterialisierung Capture/Ghost beenden; Runtime prüft aktive Quellen; Tooltips beschreiben Move/Swap. |
| `ui/drag_feedback.py` (neu) | Kleine gemeinsame Darstellungshilfe: ein Timer, lokaler Filter auf beteiligten Widgets, mausdurchlässiger Ghost, gezielte Zielkontur und nächstgelegene ScrollArea. Keine eigene fachliche Zustandsverwaltung. |

Inventory-Kauf/Install/Return/Sell, unbegrenzter Kartenbestand und direkte MK1/Common-Templatekäufe bleiben dieselben P2/P3-Pfade. Verschieben ruft keinen Return-Command auf und schreibt weder Kartenobjekte noch Produktionskonfigurationen um.

## 3. Exakte Gruppenabbildung

Production-Auswahl: sichtbare freigeschaltete Linienreihenfolge, darin Slotreihenfolge. Freight-Auswahl: bestehende Reihenfolge der Facility-Slots. Das erste ausgewählte Element geht auf den Slot unter dem Drop-Punkt; die weiteren folgen den **unmittelbar folgenden freigeschalteten Slots**, einschließlich belegter Plätze. Production kann dabei in die nächste freigeschaltete Linie laufen; Freight ebenso in die nächste vorhandene Linie. Gesperrte oder nicht vorhandene Plätze werden nicht erzeugt; reicht der restliche Bereich nicht, wird die ganze Aktion abgelehnt. Es gibt keine Suche nach freien Löchern. Auswahlabstände werden kompakt gepackt; keine implizite zweidimensionale Rasterverschiebung. Die Preview zeigt die gegriffene Karte und die Gruppengröße; die Reihenfolge stammt immer aus der Auswahl, nicht aus Set-Iteration.

Für jede ausgewählte Karte entsteht eine gerichtete Kante Ursprung → Ziel. Eindeutige Ursprünge und Ziele ergeben disjunkte Pfade oder bereits geschlossene Zyklen. Bei jedem offenen Pfad kommt der ursprüngliche Inhalt des Endplatzes zurück an den Pfadanfang. Dieser Inhalt darf auch leer sein. Bereits geschlossene Zyklen benötigen keine Gegenkarte. Dadurch wird die Vereinigung aller betroffenen Plätze vollständig und genau einmal neu belegt.

| Ausgangsplätze | Auswahl / Ziele | Ergebnis |
| --- | --- | --- |
| `[A, B]` | A → 1 | `[B, A]` |
| `[A, B, C, D]` | A,B → 2,3 | `[C, D, A, B]` |
| `[A, B, C]` | A,B → 1,2 | `[C, A, B]` |
| `[A, B, C, D, leer]` | A,B → 1,4 | `[leer, A, C, D, B]` |
| `[A, B, leer, leer]` | A,B → 2,3 | `[leer, leer, A, B]` |
| `[A, B]` | A,B → 1,0 | `[B, A]` |

Ein Drop auf dieselben Ursprünge ist ein gültiger No-op. Selbstüberlappung ist erlaubt, sofern die eindeutige vollständige Zuordnung validiert. Gruppen aus 2/5/10 und volle Boards ohne Hilfsslot sind abgedeckt. Gebäudeübergreifende Pläne sind über dieselben bestehenden Commands möglich, sofern jede Hin- und Rückrichtung passt. Die UI behält die bisherige Auswahl-/Navigationsstruktur; es gibt keine neue Hover-Navigation zwischen Tabs oder Gebäudebäumen. Ein Gebäude-/Boardersatz während einer Geste beendet die alte Geste sicher.

## 4. Atomarität, Ressourcen und Freight

Planung liest Karten/Slots nur. Vor dem ersten Write: IDs/Mengen/Indexarten, eindeutige reale Slotidentitäten, genau eine Eigentums-/Installationsreferenz pro Quelle und Gegenkarte, aktuelle Ursprungssnapshots, freigeschaltete Quellen/Ziele und Board-/Facility-Kompatibilität für alle resultierenden Karten prüfen. Erst danach folgen einfache Slotzuweisungen und gegebenenfalls vorbereitete Ressourcenspezialisierungen. Kein CommandBus-Rollback wird vorausgesetzt.

Ressourcensites werden nach ihrer **vollständigen endgültigen Belegung** geprüft, einschließlich nicht bewegter Karten. Gemischte Familien sind ungültig; feste Spezialisierung bleibt bindend. Eine bisher untypisierte Site darf nach vollständigem Austausch genau eine neue Familie erhalten. Eine bereits fest Mining-spezialisierte Site wird nicht automatisch zu Drilling umklassifiziert.

Jedes aktive Freight-Shipment blockiert die Quelle **oder verdrängte Gegenkarte**, auch bei Restzeit 0 oder nur reservierter Menge. Keine Umhängung/Neuberechnung von Shipments, Ladung, Reservierungen, Routes oder Pausen. Karteninstanzen, MK/Rarity, Investition, Produktion/Rezept/Teilfortschritt und Cash bleiben identisch. Linien-/Gebäudepause bleibt weiterhin an ihrem jeweiligen Ort. Fehlgeschlagene Gruppenaktionen lassen vollständige Serialisierung und CommandBus-History unverändert.

## 5. Pointer, Scrollen und Lebensdauer

Production verwendet weiter QDrag nach der normalen Qt-Dragdistanz. Der Hotspot entspricht der ursprünglichen lokalen Pressposition in logischen Qt-Pixeln, auch bei 200 %. Gruppen erhalten eine einmalig gerenderte Zählmarke. Freight behält Pointer-Capture: genau ein mausdurchlässiges QLabel mit einmaligem Kartensnapshot; Positionsänderung über globale Pointerkoordinaten und Greifpunkt, ohne Karten-Neubau pro Bewegung.

Nur das aktuell berührte Ziel erhält eine eigene leichte Kontur: grün MOVE, gelb SWAP, rot UNAVAILABLE. Hover verändert keine Domain-Daten. Wiederholte Pointerbewegungen über dasselbe Ziel bauen keinen neuen Plan oder Zielrahmen auf; beim Drop wird die komplette Prüfung frisch ausgeführt. Quellwidgets und vorhandene P1-Caches bleiben erhalten, solange ihre Struktur nicht geändert wird.

Auto-Scroll: nächstgelegene tatsächliche Board-QScrollArea der Quelle, maximal 64 logische Pixel Randzone (bei kleinem Viewport höchstens ein Drittel), ein 16-ms-Timer. Geschwindigkeit `max(1, round(26 × (1 − Abstand/Randzone)^1.4))` Pixel je Tick, nach oben negativ. Am Rand etwa 1.600 logische Pixel/s, zum Inneren sanft abfallend. Außerhalb des Viewports, am Scrolllimit oder beim Abbruch stoppt der Timer. Nach jedem Scroll-/Wheel-Schritt wird das Ziel unter derselben globalen Pointerposition neu ermittelt; der Freight-Ghost bleibt am Pointer. Normales Scrollen bleibt außerhalb der Geste bei Qt.

Wheel-Ereignisse auf beteiligten Karten/Viewports werden an genau diese Scrollbar geleitet (PixelDelta oder 96 Pixel pro 120 AngleDelta). **Offscreen-Qt-Ereigniszuleitung ist geprüft; Windows-OLE kann während QDrag Wheel selbst konsumieren. Eine native Windows-Wheel-Zustellung und subjektiv flüssiges Draggefühl sind nicht als bestanden behauptet.** Randscrollen bleibt unabhängig von Wheel-Ereignissen verfügbar.

Erfolgreicher Drop, ungültiger Drop, Release außerhalb, Esc, Hide/Tabwechsel, Close, WindowDeactivate, Quellwidget-Hide/Entfernung, vollständiger Boardersatz, Freight-Refresh und New Game/Load lösen Cleanup aus. Ghost/Outline/Timer, Mausfang, Cursor und temporäre Quellen/Ziele werden freigegeben. Jede Geste hat eine eigene UUID, die bei Cancel, erfolgreichem Drop, Ende der nativen Schleife oder einer neuen Geste ungültig wird. Sessionreset invalidiert zusätzlich Token und das konkrete Kartenregister; eine alte MIME-Nachricht kann nicht in eine neue Sitzung passen. Runtime prüft verschwindende/veränderte Quellen nur während einer aktiven Geste. Weitere normale Klicks und ein erneuter Drag sind getestet.

## 6. Tests und Migration

**{summary['passed']}/{summary['tests']} bestanden in {summary['modules']}/85 Modulen; 0 Fehler/Skips.** Alle ursprünglichen 1.381 Fälle mit identischen Modulfallzahlen erhalten, dazu {summary['new_cases']} P4-Fälle. Vollständige Modulnachweise `final-tests/`, erste Versuche unverändert unter `first-full-tests/`; Herkunft in `provenance.json`. Beide P4-Module zusätzlich bei 200 % geprüft, ohne Doppelzählung.

Neue `test_phase4_slot_permutations.py` und `test_phase4_drag_ui.py`: belegte Einzel-/Gruppenswaps, Überlappung/Zyklen/Leerräume, 36 exhaustive kleine Zuordnungen, volle Boards, 1/2/5/10 Karten, vier Boards und vier Freight-Facilities, Hin-/Rückkompatibilität, komplette Site-Endkonfiguration, doppelte/fehlende/gesperrte Quellen/Ziele, veraltete Sessions/Ursprünge sowie abgebrochene/ersetzte Drag-Intents, aktive Quellen und Gegenkarten mit reservierter Ladung, unveränderte komplette Zustände/History, dreifache echte SQLite-Roundtrips, Hotspot, Ghost-Position/Identität, echte Qt-Wheel-Zustellung, Zielneuberechnung, Randscrollen in beide Richtungen und an Grenzen, Esc/Outside/Deactivate/Tab/Refresh/Reset und echte MainWindow-Load/New-Game-Hooks.

Zwei Bestandsdateien fachlich aktualisiert: `test_industriova_release_ui.py` erzeugt das neue sitzungsgebundene MIME mit dem tatsächlichen Payload-Helfer. `test_ui_interaction_recovery.py` prüft im bisherigen occupied-Fall jetzt den absichtlich erlaubten identitätserhaltenden Swap; falsche Facility, Locked und Busy bleiben atomare Ablehnungen. Zusätzlich schreibt `test_recipe_retirement.py` seine vier PNGs jetzt ausschließlich unter P4; sämtliche Assertions und vier Fälle bleiben erhalten. Die erste Schutzprüfung erkannte genau diese vier erneut geschriebenen P3-Bilder. Neue Captures sind gesichert, ursprüngliche Referenzen SHA-geprüft restauriert; der vollständige betroffene Test wurde erfolgreich wiederholt. Insgesamt 32 alte Previewreferenzen sind erhalten. Ein relativer Pfadfehler beim Zusammenführen der Modulergebnisse wurde im Prüfskript korrigiert; erster Fehlernachweis bleibt erhalten. Keine Fälle entfernt, deaktiviert oder übersprungen.

**16/16 ursprüngliche Migrationen**, identische vollständige Payload-SHA256 vor/nach P4. Schema bleibt 6, Loader/Serializer unverändert; nur gesicherte Alt-Payloads gelesen. Nachweise `migration-before.json`, `migration-after.json`, `migration-comparison.json`.

## 7. Performance

Windows/Python 3.12/Qt 6.11 offscreen, identische P0/P1-/P3-Fixtures und Fonts, serielle Messungen ohne parallele Testprozesse. Sieben Wiederholungen; UI/Cold und Kaufbursts sieben frische Prozesse, warme Reihen 49 Werte. Median/Maximum in ms, keine FPS-/p95-Garantie. 10/50-Production-Karten sind reguläre Boards; 100/500 sind unveränderte synthetische große Auswahlflächen. Zusätzliche Freight-Flächen oberhalb des normalen Startbestands sind ausdrücklich synthetisch.

Callbacks, Event-Drain und Paint-Anzahl stehen getrennt in den Rohreihen. Ein Burst coalesziert Qt-Paints; das ist keine gemessene native Framefolge. `drop_commit_cycle` misst ausschließlich den Domain-Commit; `100_move_burst` hundert solche zulässigen Zyklen. Diese beiden Workloads sind vor/nach identisch. Neue belegte Swaps/Production-Feedback haben keinen alten erfolgreich arbeitenden Vergleich. Freight-Pointerbewegung hatte vorher keinen Ghost; zusätzliche Darstellungsarbeit wird nicht als vergleichbarer Speedup verkauft.

{chr(10).join(dragtable)}

P3-Inventory mit exakt denselben sechs vollständigen Payloads/Hashes, Zeilen und UI vor/nach P4. Open = neue View im selben Prozess mit teilweise warmen geteilten Assets; Refresh/Scroll einschließlich Event-Drain. Kein kalter Prozessstart und keine Behauptung, dass ein 10.000-Zeilen-Refresh ein 16-ms-Budget erfüllt.

{chr(10).join(invtable)}

P1-Kontrollen, unveränderte vollständige Katalog-/Firmen-/Snapshot-Workloads:

{chr(10).join(controls)}

Messreihen mit mehr als 10 % höherem Median und über 1 ms nachher: {('; '.join(regressions)) or 'keine in diesen Kontrollen'}. Kleine Stichproben, Caches/Timer und Scheduling können schwanken; daraus folgt keine pauschale Framerate-Zusage. Zusätzliche vollständige Permutationsvalidierung kostet Domain-Zeit; die Tabellen zeigen das offen. Warm-Refresh, Erstmaterialisierung, große Paints/Snapshots und große Inventory-Projektionen können weiter ruckeln. Speicherproben erfassen Python und Prozess-Working-Set, keine GPU- oder stundenlange Leakabnahme. Alle Rohwerte: `before/`, `after/`, `comparison.json` und `comparison-tables.md`.

## 8. Visuelle Prüfung und offene Handabnahme

{len(captures)} MainWindow-Captures: 1366×768, 1600×980, 1920×1080 bei 100/200 %. Je Konfiguration drei Production-Boards mit Auswahl/Swapziel und letztem langen Bereich; vier Freight-Facilities mit Ghost und letztem Bereich sowie aktives ungültiges Freight-Gegenziel. Zusätzliche Production-Preview-Pixmaps zeigen die Zählmarke. Pixel-/logische Größen sind automatisch verifiziert (`visual-verification.json`); sieben finale Bilder wurden tatsächlich über alle sechs Größen-/DPI-Kombinationen betrachtet (`visual-review.json`). Erste Captures bleiben unter `screenshots-first-pass/`; die finale synthetische Fixture nennt die tatsächlich freigeschaltete Slotkapazität. Die Capture-Fixtures sind isolierte synthetische Zustände; kein persönliches Save geladen.

Sichtbare bestehende Layoutgrenzen: lange Freight-Linienplaketten schneiden AIR ROUTE/SHIPPING LINE teilweise ab; lange Sidebar-Namen werden gekürzt. Production-Zeilen können horizontal über den schmalen Ausschnitt reichen und behalten ihren vorhandenen Weiterführungshinweis. P4 ergänzt vertikales Randscrollen; eine neue horizontale Navigation und die spätere P9-Labelkorrektur sind nicht umgesetzt. Der undurchsichtige Ghost verdeckt naturgemäß einen Teil der Zielkarte, die Zielkontur bleibt sichtbar.

**Native Windows-Handabnahme offen.** In dieser Sitzung steht keine native Maussteuerung zur Verfügung. QTest/offscreen prüft Domain-/Qt-Ereignisse, Hotspot-Geometrie, Zuleitung und Screenshots; keine echte OLE-/DWM-/GPU-Geste, kein menschliches Gefühl. Keine native Wheel-/Scrollfreigabe behauptet.

Manueller Testablauf für den nächsten Windows-Playtest:

1. Bei 100 % und 200 % sowie allen drei Fenstergrößen Factory/Resources/Energy und Garage/Rail/Air/Harbor öffnen; genug Plätze für mehrere sichtbare und untere Linien belegen.
2. Eine Karte an unterschiedlichen Stellen greifen, nach Dragdistanz über freie und belegte kompatible Ziele ziehen. Preview muss exakt am Greifpunkt bleiben; MOVE grün, SWAP gelb, gesperrtes/inkompatibles Ziel rot oder nicht annehmbar.
3. Zwei/fünf Karten einschließlich nicht benachbarter Auswahl ziehen; volle, überlappende und gemischt leere/belegte Ziele mit den Beispielen oben vergleichen. IDs, MK/Rarity, Pause/Rezept/Teilfortschritt und Cash vor/nach prüfen.
4. Beim Drag oben/unten an den Viewportrand halten; langsam an den Rand annähern, lange Linien erreichen, Grenzen prüfen. Gleichzeitig Mausrad testen, insbesondere Production-QDrag unter Windows; Framework-Einschränkung bei fehlender Wheel-Zustellung protokollieren.
5. Gegenkarte mit aktiver reservierter Fahrt treffen: ganze Gruppe muss unverändert bleiben. Danach dieselbe Geste nach Ankunft erfolgreich ausführen; Route/Ladungsabrechnung unverändert.
6. Jeweils Esc, Release außerhalb, Alt-Tab, Tabwechsel, View-Schließen und Load/New Game ausführen; keine Vorschau, Kontur, Scrollbewegung oder Mausfang darf bleiben. Sofort normal klicken und erneut ziehen.
7. Nach mehreren schnellen Swaps speichern, schließen und erneut laden; Slots und alle individuellen Zustände müssen gleich sein. Auf abgeschnittene Labels, DPI-Sprünge und subjektive Verzögerungen achten.

## 9. Reproduktion und Stopp

`run_release_tests.py . artifacts/phase4/<neuer-ordner> --workers 1 --timeout 600`; `phase4_finalize_tests.py`; `phase4_validate.py` führt anschließend DPI2-Tests, Vorher-/Nachhermessungen, Migration, Captures und Schutzprüfung seriell aus. `phase4_drag_benchmark.py before --source artifacts/phase4/before-tree` / `after`; vorhandene P1-Workloads über `phase4_measure.py`; Inventory über `phase4_inventory_benchmark.py`; `phase4_capture.py` mit QT_SCALE_FACTOR=1/2; `phase4_preserve_legacy_outputs.py`, `phase4_verify_protected.py`, `phase4_finish_report.py`. Bereits vorhandene Evidenz vor erneuten Ausgaben erhalten.

Vollständiger Delta gegen die tatsächliche Vorsicherung: `artifacts/phase4/implementation.diff`; Dateien/Hashes in `deliverables-manifest.json`. Vorbereitungsentwürfe/fehlgeschlagene erste Testläufe bleiben getrennt unter P4 erhalten. **P4 stoppt hier; kein P5 und kein Windows-Build.**
'''
report_path=ROOT/'docs/industriova-03-phase4-drag-swap-report.md';report_path.write_text(report,encoding='utf8')
entries={e['path']:e for e in manifest['entries']};diff=[];deliverables=[]
for folder in ('src','tests','scripts','docs'):
    for path in sorted((ROOT/folder).rglob('*')):
        if not path.is_file() or path.suffix not in {'.py','.md'} or '__pycache__' in path.parts:continue
        name=path.relative_to(ROOT).as_posix();digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if name in entries and entries[name]['sha256']==digest:continue
        deliverables.append(dict(path=name,sha256=digest,bytes=path.stat().st_size))
        before=OUT/'before-tree'/name
        diff.extend(difflib.unified_diff(before.read_text(encoding='utf8').splitlines(True) if before.is_file() else [],path.read_text(encoding='utf8').splitlines(True),fromfile='before/'+name if before.is_file() else '/dev/null',tofile='after/'+name))
(OUT/'deliverables-manifest.json').write_text(json.dumps(deliverables,indent=2),encoding='utf8');(OUT/'implementation.diff').write_text(''.join(diff),encoding='utf8')
print(json.dumps(dict(report=str(report_path),deliverables=len(deliverables),tests=summary['passed'],captures=len(captures))),flush=True)
