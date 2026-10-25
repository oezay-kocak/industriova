# INDUSTRIOVA 0.3 – P4: Card swaps and drag interaction

Stand: 22.10.2026. Ausschließlich P4, auf dem gesicherten tatsächlichen P3-Working-Tree. Kein Windows-Build; P5–P9, Preise, Supply/Inventory-Regeln und Save-Schema nicht erweitert.

## 1. Sicherung und Umfang

Vor produktiven Änderungen: `artifacts/phase4/backup-20261021T215803Z` mit 45,231 Dateien und 28,593,692,870 Quelldatei-Bytes. Inkrementelles Working-Tree-Delta mit vollständigem SHA256-Inventar und rekursiven P3/P2/P1/P0-Abhängigkeiten; große Altarchive bleiben pfad-/hashgebundene Abhängigkeiten. Zusätzlich unabhängiges `source-baseline.zip`, CRC-geprüft und jeder extrahierte Quellinhalt gegen Manifest-SHA verifiziert. Archiv-/Manifest-Summen: `SHA256SUMS.json`. Kein Git-HEAD-Reset.

Alle fünf persönlichen SQLite-Dateien sind roh sowie über read-only SQLite-Backup gesichert, jeweils `integrity_check=ok`. Kein Original wurde geladen, migriert oder geschrieben. Wiederherstellung ausschließlich in einen neuen Ordner nach Manifest, nicht über bestehende Spielstände. Alle Tests/Captures verwenden isolierte AppData-/Tempverzeichnisse.

Abschluss: **18,282 geschützte bestehende Dateien und alle fünf persönlichen Saves SHA256-unverändert**, einschließlich vorhandener build/dist-Dateien, Originalassets/Atlas, Spieldaten, Simulation, Templatekauf, Serializer/Writer und P0–P3-Referenzdaten. Die von alten Tests überschriebenen Previewpfade wurden unter P4 erhalten und ihre ursprünglichen Referenzen aus der geprüften Sicherung wiederhergestellt (`legacy-capture-preservation.json`).

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

**1491/1491 bestanden in 85/85 Modulen; 0 Fehler/Skips.** Alle ursprünglichen 1.381 Fälle mit identischen Modulfallzahlen erhalten, dazu 110 P4-Fälle. Vollständige Modulnachweise `final-tests/`, erste Versuche unverändert unter `first-full-tests/`; Herkunft in `provenance.json`. Beide P4-Module zusätzlich bei 200 % geprüft, ohne Doppelzählung.

Neue `test_phase4_slot_permutations.py` und `test_phase4_drag_ui.py`: belegte Einzel-/Gruppenswaps, Überlappung/Zyklen/Leerräume, 36 exhaustive kleine Zuordnungen, volle Boards, 1/2/5/10 Karten, vier Boards und vier Freight-Facilities, Hin-/Rückkompatibilität, komplette Site-Endkonfiguration, doppelte/fehlende/gesperrte Quellen/Ziele, veraltete Sessions/Ursprünge sowie abgebrochene/ersetzte Drag-Intents, aktive Quellen und Gegenkarten mit reservierter Ladung, unveränderte komplette Zustände/History, dreifache echte SQLite-Roundtrips, Hotspot, Ghost-Position/Identität, echte Qt-Wheel-Zustellung, Zielneuberechnung, Randscrollen in beide Richtungen und an Grenzen, Esc/Outside/Deactivate/Tab/Refresh/Reset und echte MainWindow-Load/New-Game-Hooks.

Zwei Bestandsdateien fachlich aktualisiert: `test_industriova_release_ui.py` erzeugt das neue sitzungsgebundene MIME mit dem tatsächlichen Payload-Helfer. `test_ui_interaction_recovery.py` prüft im bisherigen occupied-Fall jetzt den absichtlich erlaubten identitätserhaltenden Swap; falsche Facility, Locked und Busy bleiben atomare Ablehnungen. Zusätzlich schreibt `test_recipe_retirement.py` seine vier PNGs jetzt ausschließlich unter P4; sämtliche Assertions und vier Fälle bleiben erhalten. Die erste Schutzprüfung erkannte genau diese vier erneut geschriebenen P3-Bilder. Neue Captures sind gesichert, ursprüngliche Referenzen SHA-geprüft restauriert; der vollständige betroffene Test wurde erfolgreich wiederholt. Insgesamt 32 alte Previewreferenzen sind erhalten. Ein relativer Pfadfehler beim Zusammenführen der Modulergebnisse wurde im Prüfskript korrigiert; erster Fehlernachweis bleibt erhalten. Keine Fälle entfernt, deaktiviert oder übersprungen.

**16/16 ursprüngliche Migrationen**, identische vollständige Payload-SHA256 vor/nach P4. Schema bleibt 6, Loader/Serializer unverändert; nur gesicherte Alt-Payloads gelesen. Nachweise `migration-before.json`, `migration-after.json`, `migration-comparison.json`.

## 7. Performance

Windows/Python 3.12/Qt 6.11 offscreen, identische P0/P1-/P3-Fixtures und Fonts, serielle Messungen ohne parallele Testprozesse. Sieben Wiederholungen; UI/Cold und Kaufbursts sieben frische Prozesse, warme Reihen 49 Werte. Median/Maximum in ms, keine FPS-/p95-Garantie. 10/50-Production-Karten sind reguläre Boards; 100/500 sind unveränderte synthetische große Auswahlflächen. Zusätzliche Freight-Flächen oberhalb des normalen Startbestands sind ausdrücklich synthetisch.

Callbacks, Event-Drain und Paint-Anzahl stehen getrennt in den Rohreihen. Ein Burst coalesziert Qt-Paints; das ist keine gemessene native Framefolge. `drop_commit_cycle` misst ausschließlich den Domain-Commit; `100_move_burst` hundert solche zulässigen Zyklen. Diese beiden Workloads sind vor/nach identisch. Neue belegte Swaps/Production-Feedback haben keinen alten erfolgreich arbeitenden Vergleich. Freight-Pointerbewegung hatte vorher keinen Ghost; zusätzliche Darstellungsarbeit wird nicht als vergleichbarer Speedup verkauft.

| Surface / operation | Before median / max ms | After median / max ms |
| --- | --- | --- |
| 10.shift | 7.13 / 24.52 | 6.05 / 20.55 |
| 10.1000_idle_filter | 8.04 / 8.61 | 8.16 / 8.62 |
| 10.render | 19.04 / 19.95 | 16.36 / 17.23 |
| 10.drop_commit_cycle | 0.01 / 0.08 | 0.03 / 0.11 |
| 10.100_move_burst | 1.18 / 1.40 | 3.20 / 3.50 |
| 10.100_drag_moves | new work | 1.15 / 4.22 |
| 10.100_occupied_swaps | new work | 2.30 / 2.42 |
| 50.shift | 15.34 / 45.38 | 13.99 / 39.84 |
| 50.1000_idle_filter | 8.09 / 8.47 | 9.49 / 9.64 |
| 50.render | 28.12 / 28.66 | 26.12 / 28.90 |
| 50.drop_commit_cycle | 0.02 / 0.07 | 0.05 / 0.13 |
| 50.100_move_burst | 1.89 / 2.14 | 4.88 / 5.26 |
| 50.100_drag_moves | new work | 1.14 / 3.59 |
| 50.100_occupied_swaps | new work | 3.80 / 18.30 |
| 100.shift | 15.84 / 44.67 | 17.63 / 49.26 |
| 100.1000_idle_filter | 8.15 / 8.72 | 7.50 / 7.61 |
| 100.render | 28.19 / 30.16 | 26.71 / 28.82 |
| 100.drop_commit_cycle | 0.03 / 0.12 | 0.08 / 0.17 |
| 100.100_move_burst | 2.67 / 18.41 | 7.37 / 7.67 |
| 100.100_drag_moves | new work | 0.95 / 3.97 |
| 100.100_occupied_swaps | new work | 5.82 / 6.66 |
| 500.shift | 26.33 / 52.42 | 24.47 / 47.18 |
| 500.1000_idle_filter | 8.28 / 8.53 | 8.20 / 8.41 |
| 500.render | 27.95 / 28.43 | 25.50 / 28.68 |
| 500.drop_commit_cycle | 0.12 / 0.22 | 0.30 / 0.55 |
| 500.100_move_burst | 10.13 / 10.65 | 28.94 / 29.59 |
| 500.100_drag_moves | new work | 1.35 / 4.69 |
| 500.100_occupied_swaps | new work | 21.01 / 24.05 |
| freight.10.100_pointer_moves | 1.75 / 69.97 | 11.48 / 41.67 |
| freight.50.100_pointer_moves | 2.11 / 38.84 | 12.39 / 67.40 |
| freight.100.100_pointer_moves | 1.77 / 88.44 | 13.05 / 94.00 |
| freight.500.100_pointer_moves | 3.15 / 449.56 | 12.58 / 380.11 |

P3-Inventory mit exakt denselben sechs vollständigen Payloads/Hashes, Zeilen und UI vor/nach P4. Open = neue View im selben Prozess mit teilweise warmen geteilten Assets; Refresh/Scroll einschließlich Event-Drain. Kein kalter Prozessstart und keine Behauptung, dass ein 10.000-Zeilen-Refresh ein 16-ms-Budget erfüllt.

| Cards / stacks | Open before → after ms | Refresh before → after ms | Scroll before → after ms | Card widgets |
| --- | --- | --- | --- | --- |
| 500-stacked | 20.47 / 170.39 → 19.16 / 172.82 | 8.82 / 9.22 → 8.07 / 8.50 | 0.03 / 0.06 → 0.02 / 0.04 | 3 |
| 500-distinct | 116.06 / 126.18 → 110.41 / 112.44 | 49.35 / 58.34 → 43.27 / 47.74 | 76.65 / 77.35 → 71.57 / 74.24 | 42 |
| 5000-stacked | 34.19 / 35.39 → 32.82 / 35.82 | 23.09 / 23.79 → 21.82 / 24.28 | 0.02 / 0.03 → 0.03 / 0.07 | 3 |
| 5000-distinct | 159.10 / 183.15 → 159.71 / 191.98 | 81.14 / 105.36 → 78.34 / 104.48 | 76.48 / 80.41 → 76.39 / 80.61 | 42 |
| 10000-stacked | 49.36 / 53.11 → 58.58 / 62.09 | 36.71 / 39.58 → 39.28 / 40.57 | 0.02 / 0.40 → 0.03 / 0.04 | 3 |
| 10000-distinct | 196.63 / 222.43 → 199.17 / 215.72 | 132.93 / 161.16 → 118.87 / 125.11 | 78.49 / 84.34 → 72.01 / 75.10 | 42 |

P1-Kontrollen, unveränderte vollständige Katalog-/Firmen-/Snapshot-Workloads:

| P1 control | n before / after | Before median / max ms | After median / max ms |
| --- | --- | --- | --- |
| ui: guide.close_reopen | 49 / 49 | 22.92 / 36.43 | 20.94 / 25.81 |
| ui: guide.filter | 49 / 49 | 75.20 / 347.28 | 59.69 / 242.92 |
| ui: guide.first_open | 7 / 7 | 542.62 / 564.18 | 470.08 / 508.88 |
| ui: guide.list_graph_roundtrip | 49 / 49 | 43.92 / 71.05 | 40.54 / 47.69 |
| ui: guide.render | 49 / 49 | 12.86 / 20.71 | 12.01 / 15.26 |
| ui: guide.search | 49 / 49 | 26.55 / 47.79 | 24.54 / 36.33 |
| ui: leaderboard.changed_refresh | 49 / 49 | 0.21 / 1.00 | 0.19 / 0.56 |
| ui: leaderboard.picker_construct | 49 / 49 | 173.74 / 246.91 | 165.43 / 177.92 |
| ui: leaderboard.picker_filter | 49 / 49 | 17.39 / 28.96 | 16.11 / 21.42 |
| ui: leaderboard.picker_show | 7 / 7 | 36.35 / 50.09 | 31.57 / 34.14 |
| ui: leaderboard.unchanged_refresh | 49 / 49 | 0.21 / 9.48 | 0.21 / 7.40 |
| ui: selection.10.1000_idle_filter | 49 / 49 | 8.35 / 11.75 | 8.42 / 9.25 |
| ui: selection.10.100_rectangle_moves | 49 / 49 | 1.58 / 2.41 | 1.60 / 1.93 |
| ui: selection.10.group_pause | 49 / 49 | 0.10 / 0.42 | 0.10 / 0.35 |
| ui: selection.10.rectangle_release | 49 / 49 | 0.35 / 0.92 | 0.32 / 0.79 |
| ui: selection.10.redraw | 49 / 49 | 21.34 / 25.36 | 19.72 / 21.70 |
| ui: selection.10.shift | 49 / 49 | 8.09 / 28.22 | 7.40 / 24.74 |
| ui: selection.100.1000_idle_filter | 49 / 49 | 8.09 / 12.39 | 8.43 / 11.37 |
| ui: selection.100.100_rectangle_moves | 49 / 49 | 1.51 / 2.56 | 1.46 / 1.92 |
| ui: selection.100.group_pause | 49 / 49 | 0.77 / 1.38 | 0.76 / 1.18 |
| ui: selection.100.rectangle_release | 49 / 49 | 0.89 / 2.01 | 0.87 / 1.56 |
| ui: selection.100.redraw | 49 / 49 | 30.37 / 42.12 | 28.62 / 31.53 |
| ui: selection.100.shift | 49 / 49 | 18.23 / 59.60 | 16.73 / 48.97 |
| ui: selection.50.1000_idle_filter | 49 / 49 | 8.34 / 11.06 | 7.59 / 9.35 |
| ui: selection.50.100_rectangle_moves | 49 / 49 | 1.52 / 2.23 | 1.58 / 2.13 |
| ui: selection.50.group_pause | 49 / 49 | 0.39 / 0.70 | 0.36 / 0.58 |
| ui: selection.50.rectangle_release | 49 / 49 | 0.70 / 1.22 | 0.65 / 1.41 |
| ui: selection.50.redraw | 49 / 49 | 30.74 / 45.13 | 29.22 / 32.56 |
| ui: selection.50.shift | 49 / 49 | 17.19 / 50.05 | 15.62 / 46.89 |
| ui: selection.500.1000_idle_filter | 49 / 49 | 10.26 / 14.40 | 8.71 / 9.48 |
| ui: selection.500.100_rectangle_moves | 49 / 49 | 1.74 / 3.42 | 1.63 / 2.00 |
| ui: selection.500.group_pause | 49 / 49 | 4.96 / 8.01 | 4.09 / 6.45 |
| ui: selection.500.rectangle_release | 49 / 49 | 4.54 / 6.80 | 3.44 / 4.72 |
| ui: selection.500.redraw | 49 / 49 | 34.33 / 45.00 | 29.66 / 39.85 |
| ui: selection.500.shift | 49 / 49 | 28.89 / 64.01 | 27.08 / 60.56 |
| ui: unlock.column_order | 49 / 49 | 0.41 / 0.68 | 0.44 / 0.83 |
| ui: unlock.constructor.cold | 7 / 7 | 92.10 / 107.13 | 98.17 / 102.72 |
| ui: unlock.first_show | 7 / 7 | 138.51 / 148.97 | 146.16 / 155.28 |
| ui: unlock.graph | 49 / 49 | 2.79 / 3.89 | 3.03 / 4.44 |
| ui: unlock.rebuild.warm | 49 / 49 | 0.06 / 0.90 | 0.06 / 0.22 |
| ui: unlock.refresh | 49 / 49 | 0.04 / 7.25 | 0.04 / 7.15 |
| ui: unlock.render | 49 / 49 | 48.97 / 61.61 | 49.79 / 58.92 |
| ui: unlock.zoom_pan | 49 / 49 | 70.07 / 121.96 | 76.67 / 92.11 |
| rapid_bursts: rapid_ui.50.20_individual_purchases | 7 / 7 | 509.43 / 543.99 | 484.35 / 514.75 |
| rapid_bursts: rapid_ui.500.20_individual_purchases | 7 / 7 | 582.90 / 622.41 | 483.04 / 534.22 |
| active: 10.render | 7 / 7 | 2.84 / 3.71 | 2.89 / 3.25 |
| active: 10.refresh | 7 / 7 | 0.14 / 3.65 | 0.11 / 3.17 |
| active: 10.tick | 7 / 7 | 1.41 / 2.43 | 1.35 / 2.32 |
| active: 10.snapshot | 7 / 7 | 6.75 / 25.59 | 6.65 / 23.87 |
| active: 10.encoding | 7 / 7 | 71.73 / 72.31 | 69.50 / 70.30 |
| active: 10.commit | 7 / 7 | 23.10 / 23.53 | 22.05 / 23.68 |
| active: 10.full_save | 7 / 7 | 104.74 / 111.58 | 100.37 / 107.66 |
| active: 10.load | 7 / 7 | 68.45 / 82.49 | 70.35 / 87.28 |
| active: 50.render | 7 / 7 | 15.19 / 16.18 | 23.47 / 25.55 |
| active: 50.refresh | 7 / 7 | 0.59 / 17.22 | 0.61 / 22.93 |
| active: 50.tick | 7 / 7 | 1.59 / 2.63 | 1.71 / 3.33 |
| active: 50.snapshot | 7 / 7 | 12.84 / 32.28 | 14.62 / 69.88 |
| active: 50.encoding | 7 / 7 | 68.08 / 72.10 | 67.95 / 76.76 |
| active: 50.commit | 7 / 7 | 28.60 / 29.74 | 24.16 / 25.53 |
| active: 50.full_save | 7 / 7 | 111.87 / 142.32 | 105.24 / 131.49 |
| active: 50.load | 7 / 7 | 72.84 / 96.39 | 83.16 / 118.70 |
| active: 100.render | 7 / 7 | 27.54 / 29.86 | 30.35 / 31.51 |
| active: 100.refresh | 7 / 7 | 1.13 / 30.01 | 1.20 / 35.33 |
| active: 100.tick | 7 / 7 | 2.06 / 3.21 | 2.04 / 3.24 |
| active: 100.snapshot | 7 / 7 | 21.89 / 52.83 | 22.23 / 51.06 |
| active: 100.encoding | 7 / 7 | 73.30 / 76.81 | 72.83 / 73.87 |
| active: 100.commit | 7 / 7 | 26.23 / 31.17 | 26.11 / 30.80 |
| active: 100.full_save | 7 / 7 | 127.76 / 169.46 | 124.69 / 155.49 |
| active: 100.load | 7 / 7 | 85.81 / 125.16 | 78.74 / 115.31 |
| active: 500.render | 7 / 7 | 152.94 / 161.18 | 155.12 / 163.97 |
| active: 500.refresh | 7 / 7 | 5.64 / 194.65 | 5.75 / 175.06 |
| active: 500.tick | 7 / 7 | 5.26 / 9.11 | 5.18 / 7.81 |
| active: 500.snapshot | 7 / 7 | 144.57 / 149.69 | 137.16 / 151.73 |
| active: 500.encoding | 7 / 7 | 95.17 / 97.59 | 92.98 / 95.35 |
| active: 500.commit | 7 / 7 | 44.52 / 46.15 | 43.65 / 45.30 |
| active: 500.full_save | 7 / 7 | 256.79 / 293.49 | 235.93 / 282.80 |
| active: 500.load | 7 / 7 | 179.05 / 195.67 | 176.12 / 191.97 |
| extended: 50.sale20 | 7 / 7 | 243.89 / 260.72 | 247.43 / 273.54 |
| extended: 50.mk4 | 7 / 7 | 27.11 / 27.87 | 26.79 / 28.20 |
| extended: 50.slots7 | 7 / 7 | 95.06 / 100.00 | 94.31 / 105.90 |
| extended: 50.recipe20 | 7 / 7 | 51.46 / 54.41 | 49.31 / 53.44 |
| extended: 50.copy_paste10 | 7 / 7 | 30.13 / 31.71 | 29.64 / 31.63 |
| extended: 500.sale20 | 7 / 7 | 269.34 / 273.37 | 277.18 / 281.10 |
| extended: 500.mk4 | 7 / 7 | 50.60 / 55.57 | 51.06 / 56.44 |
| extended: 500.slots7 | 7 / 7 | 96.43 / 102.48 | 99.36 / 102.61 |
| extended: 500.recipe20 | 7 / 7 | 72.83 / 77.74 | 72.67 / 79.65 |
| extended: 500.copy_paste10 | 7 / 7 | 32.24 / 50.44 | 33.16 / 51.67 |

Messreihen mit mehr als 10 % höherem Median und über 1 ms nachher: active:50.render 15.19 → 23.47 ms; active:50.snapshot 12.84 → 14.62 ms; active:50.load 72.84 → 83.16 ms; active:100.render 27.54 → 30.35 ms. Kleine Stichproben, Caches/Timer und Scheduling können schwanken; daraus folgt keine pauschale Framerate-Zusage. Zusätzliche vollständige Permutationsvalidierung kostet Domain-Zeit; die Tabellen zeigen das offen. Warm-Refresh, Erstmaterialisierung, große Paints/Snapshots und große Inventory-Projektionen können weiter ruckeln. Speicherproben erfassen Python und Prozess-Working-Set, keine GPU- oder stundenlange Leakabnahme. Alle Rohwerte: `before/`, `after/`, `comparison.json` und `comparison-tables.md`.

## 8. Visuelle Prüfung und offene Handabnahme

90 MainWindow-Captures: 1366×768, 1600×980, 1920×1080 bei 100/200 %. Je Konfiguration drei Production-Boards mit Auswahl/Swapziel und letztem langen Bereich; vier Freight-Facilities mit Ghost und letztem Bereich sowie aktives ungültiges Freight-Gegenziel. Zusätzliche Production-Preview-Pixmaps zeigen die Zählmarke. Pixel-/logische Größen sind automatisch verifiziert (`visual-verification.json`); sieben finale Bilder wurden tatsächlich über alle sechs Größen-/DPI-Kombinationen betrachtet (`visual-review.json`). Erste Captures bleiben unter `screenshots-first-pass/`; die finale synthetische Fixture nennt die tatsächlich freigeschaltete Slotkapazität. Die Capture-Fixtures sind isolierte synthetische Zustände; kein persönliches Save geladen.

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
