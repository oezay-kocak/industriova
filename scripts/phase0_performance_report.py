"""Summarize the verified raw benchmarks, retaining measurement boundaries."""
import json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase0'
def read(name):return json.loads((OUT/name).read_text(encoding='utf8'))
u=read('ui-baseline.json');a=read('actions-baseline.json');r=read('rapid-ui-baseline.json');active=read('active-card-baseline.json');probe=read('reference-probe.json')
tests=read('regression/results.json')
def table(head,rows):return '\n'.join(['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |',*['| '+' | '.join(map(str,row))+' |' for row in rows]])
def f(x):return f'{x:.2f}'
def med(row,key):return statistics.median(row[key]) if row.get(key) else 0
def timing(key,label):
    v=u['measurements'][key];return [label,f(v['median_ms']),f(v['max_ms']),f(med(v,'callback_samples_ms')),f(med(v,'queued_event_delays_ms'))]
parts=['''# INDUSTRIOVA 0.3 – Reproduzierbare Performance-Baseline

Stand 21.10.2026. Ausschließlich Messung/Analyse des gesicherten Working Tree 0.2.0.dev6. Keine Optimierung oder Gameplayänderung vorgenommen.

## 1. Methode und vollständige Testbaseline

**1.257/1.257 Tests in 80/80 Modulen bestanden**, 0 Fehler, 0 Skips. Ausführung über den vorhandenen `scripts/run_release_tests.py`, je Modul frischer Prozess, `--workers 1 --timeout 600`; Einzel-Text-/JUnit-Nachweise und echte Fallzahlen in `artifacts/phase0/regression/`, Gesamtausgabe `regression-run.log`. Summe der Modul-Prozesszeiten: 727,04 s. Das ist eine neue Messung, keine Übernahme der historischen dev6-Testzahl.

Windows 11 10.0.26200, Python 3.12.14 AMD64, PySide6/Qt 6.11.1, `PYTHONHASHSEED=0`, `QT_QPA_PLATFORM=offscreen`. CPU-Kennung: AMD64 Family 23 Model 113 Stepping 0, AuthenticAMD. Detailumgebung in den JSON-Dateien. Sichtbare Viewgröße 1366×768, DPI 1; keine Windows-Anzeigeeinstellung geändert. Alle Saves/SQLite-Dateien ausschließlich im eigenen `artifacts/phase0`-Bereich. Messläufe nach Abschluss von Regression/Sicherung, keine parallelen Build-/Test-/Simulationsjobs.

Die Sichtkontrolle des ersten Harness-Laufs zeigte fehlende Schriftglyphen im Offscreen-Backend. Deshalb werden die Windowsfonts wie in vorhandenen Capture-Skripten ausdrücklich registriert (Segoe UI/Bold, Bahnschrift, Arial, Agency) und die vorhandenen Industriova-Styles verwendet. Nur die danach erneut gemessenen JSON-Dateien sind Grundlage. Die falschen Font-Proben bleiben unter `initial-unregistered-fonts/` zur Nachvollziehbarkeit erhalten. `MainWindow` im echten Kaufprobe-Lauf verwendet seine eigene normale Stylesheetzuweisung, keine doppelte App-Zuweisung.

`scripts/phase0_benchmark.py ui` misst standardmäßig sieben Wiederholungen, warme Neuaufbauten fünf, Pickerkonstruktion drei, erstes Öffnen einmal. Median und Maximum sind Stichprobenwerte, keine belastbare p95 oder Langzeitgarantie. UI-Tabelle: Gesamt = Callback plus ein `processEvents`, wo im JSON gekennzeichnet; Callback = synchrone Funktionsarbeit; Queue = Wartezeit eines **vorher** eingereihten Zero-Timers. Der Timer kann vor dem nachfolgenden Paint verarbeitet werden. Deshalb ist Queue keine Obergrenze für die gesamte sichtbare Frameunterbrechung; synchrone Renderzeit und Gesamtzeit zusätzlich beachten. In `ui` zählt eine kleine QApplication-notify-Instrumentierung Paint-Events; deren Overhead gehört zu diesen Diagnoselaufzeiten. Keine native FPS-/DWM-/GPU-Abnahme.

Profile (`*.profile.txt`) sind zusätzliche instrumentierte Einzelaufrufe und dürfen nicht mit unprofilierten Medianen addiert werden. Cold bedeutet erster Viewaufbau nach geladenen Definitionen im jeweiligen Prozess, nicht kalter Systemstart oder leerer Betriebssystem-Dateicache. Guide/Pickers werden nach dem Unlock-Test im selben UI-Prozess gemessen; Rasterquelldaten sind teilweise bereits warm.

## 2. Unlock Tree: Graph nicht der dominante Aufbaukostenblock
''']
parts.append(table(['Szenario (353 Knoten, 708 Kanten)','Gesamt Median ms','Maximum ms','Callback Median ms','Queue Median ms'],[
    timing('unlock.graph','Reiner Graphaufbau'),timing('unlock.constructor.cold','Erste Konstruktion, n=1'),timing('unlock.first_show','Erstes Show/Layout/Paint, n=1'),
    timing('unlock.column_order','Spalten-/Reihenfolgeplanung'),timing('unlock.rebuild.warm','Warmer Szenenneuaufbau, n=5'),timing('unlock.refresh','Unveränderter Statusrefresh'),
    timing('unlock.render','Explizites Rendern'),timing('unlock.zoom_pan','Zoomschritt + Pan + Event/Paint')]))
parts.append(f'''
**Objekte/Speicher:** {u['unlock']['scene_items']} Scene-Items (353 Knoten, 708 Kanten, 8 Tiefentexte/-trennlinien), nur {u['unlock']['widgets']} dauerhafte QWidget-Nachfahren der View. Dennoch entstehen beim Aufbau zusätzlich **353 temporäre ResourceIconWidgets**, die als Pixmap gerendert und per deleteLater entsorgt werden. Windows-Working-Set-Zuwachs beim ersten Aufbau/Anzeigen: **{f(u['unlock']['working_set_delta_bytes']/1024**2)} MiB**. Dies enthält dekodierte PNG-Quellbilder, Qt-/Font-/Rastercaches und Scene-/Heapallokationen; kein ausschließlich dem Graphen zurechenbarer Speicher. Es ist kein Beweis eines Leaks.

Nach zehn zusätzlichen Statusrefreshes mit Entsorgung geposteter Delete-Events: Working Set {f(probe['unlock_ten_refreshes']['working_set_before']/1024**2)} → {f(probe['unlock_ten_refreshes']['working_set_after']/1024**2)} MiB; Knoten/Scene-Items bleiben {probe['unlock_ten_refreshes']['nodes']}/{probe['unlock_ten_refreshes']['scene_items']}. Das prüft wiederholte Updates, kein stundenlanges Speichermonitoring.

**Nachgewiesene Ursache:** `ui/unlock_tree_view.py:_rebuild_scene` verwirft sämtliche Items. Profil: 353 Aufrufe `_render_icon` ca. 298 ms von 376 ms profiliertem Neuaufbau; darin 353 Smooth-Scalings ca. 184 ms. Der gemeinsame `_scaled_resource_raster` in `ui/resource_art.py` hält nur 64 Einträge. Eine vollständige Serie von 353 Icons verdrängt die vorherigen Einträge. Graphaufbau und `_ordered_columns` bleiben dagegen im kleinen Millisekundenbereich. Kein Beleg, dass eine andere Graphlayoutbibliothek erforderlich wäre.

**Minimale Strategie:** bereits erzeugte Knoten-/Iconpixmaps bei Filter-/Fokuswechsel behalten, Visibility/Emphasis ändern; Iconcache mit Resource-ID, Größe und DPR begrenzt auf die tatsächlich benötigte Menge dimensionieren. Original-PNG-Cache (353×512²) und verkleinerte Anzeigevarianten getrennt budgetieren, nicht blind alle Bildgrößen unbegrenzt cachen. `refresh_state` soll unveränderte Status-/Textsignaturen nicht erneut `update()`n; Kanten nur bei relevanter Status-/Traceänderung. Das erklärt auch die Differenz zwischen kurzem Callback und teurem nachfolgendem Paint. Zoom/Pan transformiert bereits die bestehende Szene; dort zunächst Paint/Cache profilen statt Graph neu erfinden.

Verantwortlich: `ui/unlock_tree_view.py`, `ui/resource_art.py`, `ui/resource_icons.py`, `ui/zoom_pan_view.py`; keine Core-Preis-/Rezeptänderung nötig.

## 3. Production Guide: vorhandene Caches helfen, Erstmaterialisierung bleibt teuer
''')
parts.append(table(['Szenario','Gesamt Median ms','Maximum ms','Callback Median ms','Queue Median ms'],[
    timing('guide.first_open','Erstes Guide-Öffnen (Quellbilder warm), n=1'),timing('guide.search','Suche steel + zurück, zwei Filter'),timing('guide.filter','Processing + All, zwei Filter'),
    timing('guide.render','Explizites Rendering'),timing('guide.list_graph_roundtrip','Steel-Kettengraph + zurück, n=5'),timing('guide.close_reopen','Board schließen/Guide wieder öffnen, n=5')]))
parts.append(f'''
Erster Guide: **{u['guide']['tiles_created']} Produktkacheln**, {u['guide']['widgets']} QWidget-Nachfahren der gesamten Boardview. Nach Suche/Filtern/Wechsel weiterhin exakt {u['guide']['tiles_created_after']} erzeugte Kacheln und {u['guide']['builds']} Guide-Panelaufbau. Im Lauf {u['guide']['grid_rebuilds']} Rasteraktualisierungen. Es existieren also bereits ein Rezept-/Reverse-Index, gecachter Guidepanel und Tile-Reuse; die Behauptung „bei jeder Suche 353 neue Kacheln“ wäre falsch.

**Profilbefund:** Ein einzelner Suchwechsel kostet profiliert etwa 71 ms. `_populate_guide_grid` aktualisiert Metadaten für alle 353 Optionen, obwohl nur wenige Treffer sichtbar sind. 353 `unlock_requirement_lines` kosten zusammen etwa 44 ms; `_unlocked_output_resources` wird 368-mal aufgerufen und benötigt etwa 33 ms. Hinzu kommen Hide/Show, Tooltip-/Textupdates und Neuordnung. Das vorhandene Tile-Caching verhindert die wiederholte Erstellung, nicht diese vollständige Statusarbeit. Erstes Öffnen erzeugt trotzdem alle 353 Kacheln samt Label-/Iconhierarchie.

**Minimale Strategie:** unveränderliche Browserdaten/Rezepte erhalten; freigeschaltete Outputs und Requirementtexte einmal pro Progressionsrevision berechnen; Suche filtert Trefferlisten statt vollständiger Metadatenaktualisierung. Nur aktuell benötigte Kacheln materialisieren beziehungsweise vorhandene behalten; keine unabhängige Guidearchitektur. Bei Öffnen/Schließen Board-Neuaufbau vermeiden, wenn nur das gecachte Panel wechseln muss. New Game/Load müssen Caches explizit invalidieren.

Verantwortlich: `ui/factory_view.py`, `core/progression.py`, `ui/resource_tiles.py`, vorhandener `ProductionGuideRecipeIndex`. Gegenprobe: manuelle Search-/Stage-/Chainnavigation liefert denselben Bestand und dieselben Unlocktexte.

## 4. Mehrfachauswahl: Filter sind nicht der größte Kostenblock

10/50 Karten verwenden eine regulär dimensionierbare Halle; 100/500 in einer einzigen Auswahlfläche sind **synthetische Controller-Stresstests** mit zusätzlichen Linien. Eine reguläre Factory erlaubt maximal 50 Karten pro Halle; 500 in einem echten Unternehmen sind auf zehn Hallen verteilt. Keine Produktdaten-/Maximaänderung, kein neuer Save aus den übergroßen Auswahlflächen. Rendern misst nur die 1366×768-View, nicht alle außerhalb des Viewports liegenden Kartenpixel.
''')
selection=[]
for count in (10,50,100,500):
    m=u['measurements'];key=lambda suffix:m[f'selection.{count}.{suffix}']['median_ms']
    selection.append([count,f(key('shift')),f(key('rectangle_release')),f(key('100_rectangle_moves')),f(key('1000_idle_filter')),f(key('group_pause')),f(key('redraw'))])
parts.append(table(['Karten','Einzel+Shift inkl. Events ms','Rahmen-Release ms','100 Rahmen-Moves ms','1.000 idle Filteraufrufe ms','Gruppenpause Core ms','Viewport rendern ms'],selection))
parts.append('''
Mausprobe: direkte synthetische MouseMove-Ereignisse an den bestehenden Filter; gleiche Koordinate, Event-/RubberBand-Verarbeitung 100×, Paint nach dem Batch. Das ist eine reproduzierbare Untergrenze für Controller-Overhead, **kein** Maus-zu-Monitor-Latenztest und keine 100 separat gerenderten Frames. Idle-Filter: direkte gleiche Ereignisse ohne aktiven Rahmen, keine globale OS-Hookmessung. Für die native P4-Abnahme zusätzlich variierende Zeigerpositionen, einzelne dargestellte Frames, Wheel/Edgescroll und Pointer-Capture testen.

Das aktuelle Verfahren berechnet die Widget-/Rahmenschnittmenge erst beim Release; pro Move wird lediglich das RubberBand gesetzt. `ReleaseBoardMixin._update_selection_visuals` aktualisiert nur geänderte Selection-Properties, aber prüft sämtliche Slotwidgets. Bei 500 Karten ist die Gruppenpauseberechnung weiterhin niedrig einstellig; der sichtbare Shift-Auswahlaufruf enthält die nachfolgenden Repaints. Pro idle Filteraufruf liegt der gemessene Aufwand im Mikrosekundenbereich. Kein Beleg, dass der Filter pauschal die gemeldeten Sekundenhänger verursacht.

**Minimale Strategie:** existierende lokale Filter behalten; geometrische Kartenzuordnung nur bei Layoutänderung erneuern, markierte Unterschiede aktualisieren, teure Kartenraster pro Statusrevision wiederverwenden. Keine neue zentrale Auswahlarchitektur. Geplante Swap-/Ghost-/Autoscrollfunktionen existieren noch nicht vollständig und wurden nicht als bereits vorhandene Performanz gemessen.

Verantwortlich: `ui/release_board.py`, `ui/factory_view_v2.py`, für Freight `ui/freight_drag.py`/`freight_lines.py`. Paint-Eventcounts pro Messung stehen im UI-JSON; z.B. Shift vs. Rectangle können unterschiedliche sichtbare Karten und Coalescing haben. Widgetzahl ist nicht gleich Paintzahl.

## 5. Schnelle wirtschaftliche Aktionen: Core vs. Neuaufbau

Kompakte Firma: 10/50/100/500 vorhandene Processors in 1/1/2/10 Hallen. Sie sind für diesen isolierten Command-/Savevergleich überwiegend unkonfiguriert; eine zusätzliche echte aktive Simulation folgt in Abschnitt 7. Alle Kaufmengen/Preis-/Slotprüfungen laufen regulär. 20er-Purchase kauft einmal Menge 20; „20 buy Core/Bus“ in den Rohdaten sind dagegen zwanzig Einzelkäufe samt identischer Aufräumverkäufe. Sie sind keine subtrahierbare reine CommandBus-Latenz. Keine sichtbare Dialog-Wartezeit in den Timings.
''')
parts.append(table(['Vorhandene Karten','Kauf Menge20 ms','Verkauf Menge20 ms','20 Install/Remove-Paare ms','Ein MK-Schritt ms','14 Slotunlock ms','10 Templates+Verkauf ms','20 Rezeptzuweisungen ms'],[
    [count,*[f(a['measurements'][f'actions.{count}.{suffix}']['median_ms']) for suffix in ('purchase20','sale20','20_install_remove','upgrade','14_slot_unlocks','paste10_and_sell','20_recipe_assign')]] for count in (10,50,100,500)]))
parts.append(table(['Karten','20 Einzelkäufe+Cleanup Core ms','Dasselbe über Bus ms','Runtime-UI inkl. Events ms','Struktureller Boardrefresh inkl. Events ms'],[
    [count,*[f(a['measurements'][f'actions.{count}.{suffix}']['median_ms']) for suffix in ('20_buy_core_plus_cleanup','20_buy_bus_plus_cleanup','ui_runtime','ui_structural')]] for count in (10,50,100,500)]))
parts.append('''
Die aufeinanderfolgenden MK-Schritte gehen von MK1 bis MK8 und messen daher tatsächliche steigende Stufen, keinen festgehaltenen identischen Kostenquotezustand. Rezeptzuweisung verwendet denselben freigeschalteten Produktionspfad wiederholt; ein wechselndes Rezept mit Ressourcenumbruch gehört in P8/P4-Simulation. Templateprobe prüft Quote, direkten Kauf/Installation und danach Verkauf; Copy selbst kopiert vorhandene Konfiguration ohne eine zweite Wirtschaftsbuchung.

**Bestätigter Kaufpfad mit echter MainWindow-Verkabelung:** Nach einer vorausgesetzten menschlichen Bestätigung ruft der Harness zwanzigmal den echten `SupplyView._buy_common` auf. Jeder Aufruf dispatcht den Command und durchläuft `_notify_and_refresh` → `MainWindow._refresh_views`. Alle normalen View-Abonnenten sind vorhanden (optionales Charts deaktiviert), Simulationstimer gestoppt, kein SaveStore angeschlossen. 50/500 vorhandene Karten, davon vorab 20 regulär unplatziert, um freie kompatible Plätze zu erhalten. Es werden exakt 20 neue Karten nachgewiesen. Danach wird nur im synthetischen Zustand aufgeräumt.
''')
parts.append(table(['Karten','Pro Kauf Median ms','Maximum ms','20 Käufe Summe ms','Queue Median ms'],[
    [count,f(r['measurements'][f'rapid_ui.{count}.20_individual_purchases']['median_ms']),f(r['measurements'][f'rapid_ui.{count}.20_individual_purchases']['max_ms']),f(r['measurements'][f'rapid_ui.{count}.20_individual_purchases']['total_ms']),f(med(r['measurements'][f'rapid_ui.{count}.20_individual_purchases'],'queued_event_delays_ms'))] for count in (50,500)]))
parts.append('''
**Ursache belegt:** `rapid-ui-500.profile.txt` zeigt fast die ganze profiliert gemessene Callbackzeit im Notify-/Full-Views-Pfad; drei Production-Boardrefreshes bauen Inhalte neu auf, dazu Freight. Im ersten Profil 82 von 105 ms allein in den drei Boardrefreshes. Neuere profilspezifische Zeiten stehen in der finalen Datei; Profilzeiten sind keine addierbaren Medianwerte. Der Core-Kauf selbst liegt weit darunter. Da dieser Lauf **ohne SaveStore** dieselbe UI-Unterbrechung zeigt, erklärt SQLite diese Kaufhänger nicht.

Production-Slotunlock, Upgrade, Verkauf, Templatepaste und Rezeptzuweisung rufen im tatsächlichen UI ebenfalls `_refresh_content`/`refresh_view` auf; die gemessene generische strukturelle Refreshzeit ist deren gemeinsamer Kostenblock. Es wurde nicht behauptet, sämtliche Dialoge dieser sieben Aktionen als native komplette Klickpfade zeitlich abzunehmen. Die Commandbursts und vorhandenen Regressionstests decken ihre fachlichen Pfade separat ab.

**Minimale Strategie:** nach wirtschaftlichem Commit betroffene Karten/Slot/Tree-/Cashanzeigen aktualisieren; versteckte Boards als dirty markieren und erst beim Betreten einmal strukturell aktualisieren. Keine Ersetzung des CommandBus, der nur synchron `apply` und History-Append ausführt. Käufe/Verkäufe nicht einzeln über Eventloops verteilen, falls dadurch atomare Gruppensemantik verloren geht. Bestehende Thumbnail-/Kartenrenderer und Viewcaches verwenden.

Verantwortlich: `ui/main_window.py:_refresh_views`, `ui/supply_view.py:_notify_and_refresh`, `ui/factory_view_v2.py:_refresh_content`, `ui/factory_view.py`, `ui/release_board.py`. Datenänderung und UI-Invalidierung voneinander trennen, ohne eine zweite Zustandshaltung einzuführen.

## 6. Nischen-Leaderboard: langsamer Picker und ersetzte eigene Zeile
''')
parts.append(table(['Szenario','Gesamt Median ms','Maximum ms','Callback Median ms','Queue Median ms'],[
    timing('leaderboard.picker_construct','353-Produkte-Picker konstruieren, n=3'),timing('leaderboard.picker_show','Picker erstes Show/Layout/Paint'),timing('leaderboard.picker_filter','Suche iron und leeren, zwei Filter'),
    timing('leaderboard.unchanged_refresh','Rankingrefresh unverändert'),timing('leaderboard.changed_refresh','Eigene Produktion geändert (Identitätsprobe)')]))
parts.append(f'''
Picker: **{u['picker']['products']} Kacheln / {u['picker']['widgets']} QWidget-Nachfahren**. `LeaderboardView._open_product_picker` lädt beim Öffnen Definitionen neu und erzeugt jedes Mal `ContractProductPicker` samt allen Kacheln. Das Profil zeigt vor allem Widget-/Layout-/Style-/Fontarbeit: 2.129 addWidget-Aufrufe, >31.000 Elision-/Tooltipberechnungen und Container-Reparenting/StyleChange; kein Serverrequest. Der verwendete LocalLeaderboardService liefert in der Produktionsnische derzeit genau eine lokale Zeile.

Die Rangliste selbst besitzt bereits Snapshotvergleiche; ein unveränderter Refresh baut die Zeilen **nicht** vollständig neu auf. Bei geänderter eigener Produktionszahl ersetzt `_refresh_ranking` aber die eigene angeheftete Zeile per Clear/Delete/Create. Erste Identitätsprobe 7/7 Ersetzungen, zusätzliche Probe bei **sichtbar ausgewähltem Production-Tab** {sum(x['replaced'] for x in probe['changed_production_refresh'])}/{len(probe['changed_production_refresh'])}; Median inkl. mehrfacher Evententsorgung {f(statistics.median(x['including_events_ms'] for x in probe['changed_production_refresh']))} ms. Damit ist unnötiger eigener Zeilenersatz reproduziert. Ein kompletter Aufbau sämtlicher fremder Rankingzeilen bei unverändertem Snapshot ist dagegen nicht belegt. Eine Netzwerkursache wäre bei diesem lokalen Provider eine falsche Diagnose.

**Minimale Strategie:** denselben vorhandenen Produktpicker beim erneuten Öffnen behalten oder Kacheln bedarfsweise erstellen, unveränderliche Produktdefinitionen gemeinsam beziehen. Erst gewählten Produktdatensatz/Zeilenwerte ändern; eigene Rankingspalten auf derselben Rowinstanz aktualisieren. Vorhandenen Snapshot-/Others-Vergleich, Suche, eigene Position und Highlight erhalten. Ein bereits geplantes virtuelles Produktmodell aus dem vorhandenen Supply-Raster kann als Muster dienen; keine neue Ranglistenarchitektur. Subjektives Flackern auf dem echten Windows-Desktop abschließend prüfen – Row-Identitätswechsel ist ein technischer Beweis des Neuaufbaus, keine Videoabnahme des Flackerempfindens.

Verantwortlich: `ui/leaderboard_view.py`, `ui/contracts_view.py:ContractProductPicker`, `ui/resource_tiles.py`, `ui/secondary_views.py`, `services/local.py`.

## 7. Core-Tick, Snapshot, Encoding und SQLite getrennt

Kompakte überwiegend unkonfigurierte 10–500-Kartenfirma, 240 Historywerte je vorhandener Serie; Snapshot siebenmal, Encoding/Commit dreimal. UI-Callback wird während Snapshot/Encoding/Commit ebenfalls separat im JSON erfasst. Diese Datenmenge besitzt erheblich weniger Metrikserien als die aktive Fixture darunter.
''')
parts.append(table(['Karten','Snapshot Mainthread ms','Encoding ms','SQLite-Commit ms','Payload Bytes'],[
    [count,*[f(a['measurements'][f'actions.{count}.{suffix}']['median_ms']) for suffix in ('snapshot','encoding','sqlite_commit')],next(x['payload_bytes'] for x in a['fixtures'] if x['initial_cards']==count)] for count in (10,50,100,500)]))
parts.append(f'''
Bei 500 Karten beträgt reines SessionWriter-Submit {f(a['measurements']['actions.500.writer_submit']['median_ms'])} ms; das einmalige synchrone Warten auf drei abgeschickte Writes {f(a['measurements']['actions.500.writer_wait_drain']['median_ms'])} ms. Letzteres ist ein Queue-Drain, kein einzelner Commit. Normales Autosave erstellt den Snapshot auf dem UI-Thread und reicht ihn weiter; Encoding/SQLite laufen auf dem einzigen Writerthread. `wait=True` beim expliziten Speichern/Schließen kann zusätzlich bis Queue-Ende blockieren. Keine normale Autosave-UI-Latenz aus der Summe dieser Workerzeiten erfinden.

**Aktive Vergleichsfixture:** vorhandener `scripts/release_benchmark.py` über `phase0_active_benchmark.py`, mit korrekten Windowsfonts/Styles. 10/50/100/500 aktive Extractors, ausreichend synthetische Solarleistung, tatsächliche Simulation/Historyserien und je 240 Werte. Je Extractor eine eigene Site, deren FactoryHall-Modell standardmäßig zusätzliche leere Slots anlegt; 500 ist somit eine strukturell große 500-Sites-Firma, keine kompakte 10-Hallen-Firma. Vollständiges Rendern der gesamten 10-Spalten-Kartenfläche, nicht nur ein üblicher Bildschirmviewport. Die Definition der Solarleistung wird ausschließlich in einer privaten Dataclass-Kopie für die Fixture verändert; keine Quelldatei/Produktivdefinition geändert.
''')
parts.append(table(['Aktive Karten','Alle Karten rendern ms','Alle Karten refreshen ms','Engine-Tick ms','Snapshot ms','Encoding ms','Commit ms','Voller synchroner Save ms','Load ms'],[
    [x['cards'],*[f(x[k]) for k in ('render_ms','refresh_ms','tick_ms','snapshot_ms','encoding_ms','commit_ms','full_save_ms','load_ms')]] for x in active['results']]))
parts.append('''
**Befund:** Das tatsächliche Core-Ticken liegt selbst in der großen Fixture im einstelligen Millisekundenbereich. Dagegen ist der große Snapshot eine sichtbare synchrone Hauptthread-Kostenposition. `snapshot500.profile.txt` für die kompakte Fixture zeigt `asdict`/Serialisierung und anschließendes Deepcopy als Hauptarbeit. Der Unterschied zwischen kompakter und 500-Sites-Firma ist durch unterschiedliche strukturelle und historische Datenmengen erklärbar; nicht pauschal behaupten, „500 Karten kosten immer 200 ms Save“. Der alte Release-Benchmark kann mit demselben Skript reproduziert werden, ist aber keine direkte Vorher/Nachher-Messung einer hier implementierten Optimierung.

Die sehr große Vollflächen-Render-/Refreshzeit ist zusätzlich profiliert in `active-render500.profile.txt` und `active-refresh500.profile.txt`; sie dient als Controller-/Renderer-Stressgrenze. Keine normale 500-Karten-Auswahl oder native Framerate daraus ableiten. Die 50-Karten-Viewportmessung ist der passendere normale Hallenvergleich.

**Zusätzliche tatsächlich nachgewiesene Ursache:** In der 500-Sites-Vollflächenprobe entfallen im Renderprofil 326 von 538 ms auf 500 Aufrufe `production_pause.py:effective_card_paused`; im separaten Refreshprofil 723 von 980 ms auf 1.000 Aufrufe (set_data und Paint). Diese Funktion sucht je Karte erneut durch sämtliche Produktionsgebäude und Slots nach deren Standort. Die profilierten Zeiten enthalten Profiloverhead, die Aufrufstruktur ist eindeutig. Die Skalierung hängt somit nicht nur von gezeichneten Pixeln, sondern von Kartenanzahl × Suchraum der Standorte ab. Minimal: vorhandenen Standort/Slotkontext der Boardwidgets an die Pauseberechnung weiterreichen oder einen **pro Refresh berechneten**, bei Move/Load/Pause korrekt erneuerten Standortindex verwenden. Hierfür ist kein zweites Produktionssystem und kein dauerhaft duplizierter GameState nötig. Die Pausenhierarchie muss identisch bleiben.

**Minimale Save-Strategie:** zuerst serialisierte, mehrfach kopierte Felder identifizieren und einen detachten DTO-Snapshot in einem Durchgang vorbereiten; bestehende HistoryPrefix-Semantik erhalten. Nicht einfach einen lebenden GameState an den Worker geben – dann wären Reservations-/Karten-/Historydaten nicht atomar. Queue ältere noch nicht gestartete Snapshots allenfalls durch einen jüngeren vollständigen Snapshot ersetzen, Fehler-/Close-Reihenfolge testen. Bounded Deliveryhistorie aus dem Freightpaket verhindert später unkontrollierte Snapshotvergrößerung. SQLite-Transaktion pro Slot bleibt erhalten; kein zweites Savesystem.

## 8. Priorisierte, durch Messungen begründete Umsetzung

| Priorität | Engpass | Minimaler nächster Eingriff | Abnahme |
|---|---|---|---|
| 1 | Guide/Picker Erstmaterialisierung vieler Widgets | bestehende Panels/Definitionen behalten, nur benötigte Kacheln erzeugen | gleiche 353 Produkte/Filter/Fokus; Cold/Warmzeiten separat |
| 1 | Jeder Kauf baut mehrere Boards auf | gezielte Dirty-/Runtimeaktualisierung statt Full-Views-Refresh | gleiche Geld-/Karten-/Slotbuchung; Kaufburst und verdeckte Views prüfen |
| 1 | Unlock Icons/Scene bei Filter neu | vorhandene Items/Pixmaps wiederverwenden, skalierte Cachegrößen budgetieren | 353/708 Graph, Zoom/Pan/Fokus, Speicher nach Wechseln |
| 1 | Pause-Standortsuche pro Karte in großen Firmen | vorhandenen Board-/Slotkontext nutzen, pro Refresh einmalige Standortprojektion | gleiche Gebäude-/Linien-/Kartenpause nach Move und Load |
| 2 | Guide-Anforderungstexte pro Filter vollständig neu | Progressionsprojektion einmal je relevanter Revision | erste Rezeptfreischaltung sofort sichtbar, Load/New Game invalidiert |
| 2 | Große Snapshotserialisierung im UI-Thread | einmaliges sicheres Detachen, HistoryPrefix/Commitordnung erhalten | Werte/Reservierungen nach Submit exakt eingefroren, Autosave/Close messen |
| 2 | Ranking eigene Zeile ersetzt | Werte auf gleicher Rowinstanz ändern | Rang/Highlight/Pin/Produktauswahl und sichtbarer Paint |
| 3 | Große Auswahl/volle Kartenfläche zeichnet viel | nur veränderte Kartensignaturen, bestehende Rastercaches prüfen | gleiche Auswahl, sichtbare Frames und native Zeigergesten |

Keine Optimierung ist in Phase 0 implementiert. Wiederholung gegen **diese** Quellsicherung, gleiche Fixtures/Styles/Fontregistrierung und gleiche Renderfläche ist Voraussetzung für einen belastbaren späteren Vorher/Nachher-Vergleich.

## 9. Reproduktion und Grenzen

Aus Projektroot, einzeln/sequenziell, keine parallele Regression/Builds:

```powershell
$env:PYTHONHASHSEED = '0'
.venv/Scripts/python.exe scripts/phase0_benchmark.py ui
.venv/Scripts/python.exe scripts/phase0_benchmark.py actions
.venv/Scripts/python.exe scripts/phase0_rapid_ui.py
.venv/Scripts/python.exe scripts/phase0_active_benchmark.py
.venv/Scripts/python.exe scripts/phase0_active_profile.py
.venv/Scripts/python.exe scripts/phase0_reference_probe.py
```

Rohwerte: `ui-baseline.json`, `actions-baseline.json`, `rapid-ui-baseline.json`, `active-card-baseline.json`, `reference-probe.json`. Finale Logs: `ui-run-fonts-verified.log`, `actions-run-fonts-verified.log`, `rapid-ui-run-final.log`, `active-card-run-fonts-verified.log`, `reference-run.log`. Abgebrochene Harness-Entwicklungsversuche bleiben als alte Logs erhalten; nur vollständige JSON-/finale Läufe werden berichtet. Der Aufruf erzeugt synthetische Artefakte und ersetzt die jeweiligen Benchmark-Ausgabedateien, niemals persönliche Saves.

Referenzbilder wurden nach wiederholtem Eventdrain tatsächlich gesichtet: `production-guide.png`, `unlock-tree.png`, `leaderboard-production.png`. Sie dienen zur Kontrolle der gemessenen Inhalte, nicht als neue UI-Freigabe. Keine neuen Designs, keine umfassende 100/200-%-Visual-Abnahme in Phase 0. Native Pointer-/Scrollgefühl, Hardware-DPI, mehrere Monitore, Langzeitspeicher und produktiver Onlineprovider bleiben spätere Abnahmepunkte; die hier berichteten konkreten Ursachen sind lokal mit Quellen und Profilen nachgewiesen.
''')
(ROOT/'docs/industriova-03-performance-baseline.md').write_text('\n\n'.join(parts)+'\n',encoding='utf8')
print('Wrote performance baseline')
