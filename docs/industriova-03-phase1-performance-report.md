# INDUSTRIOVA 0.3 – Phase 1: Performance und UI-Reaktionszeit

Stand: 21.10.2026. Ausgangspunkt: gesicherter Working Tree 0.2.0.dev6 nach Phase 0. Ausschließlich P1; keine spätere Roadmap-Phase umgesetzt.

## Sicherung und Umfang

Vor der ersten produktiven Änderung wurde der vollständige aktuelle Working Tree einschließlich uncommitteter und ungetrackter Dateien gesichert: `artifacts/phase1/backup-20261021T185035Z/`. Das Inventar umfasst 38.087 Dateien. Die inkrementelle Sicherung verwendet das unverändert erhaltene vollständige Phase-0-Archiv, ein Delta mit 649 Dateien und ein SHA-256-Inventar mit eindeutiger Speicherzuordnung je Datei. Wiederherstellung benötigt Basisarchiv und Delta; `manifest.json` beschreibt die Rekonstruktion. Zusätzlich liegt ein unabhängiges `source-baseline.zip` vor. Die Vorher-Quellen wurden daraus unter `artifacts/phase1/before-tree/` wiederhergestellt. Die Sicherung ist ausdrücklich kein Vergleich mit dem veralteten Git-HEAD.

Fünf vorhandene persönliche SQLite-Spielstände wurden separat als Dateien und konsistente SQLite-Backups gesichert; alle Backups bestanden `integrity_check`. Preis-/Rezeptdefinitionen, CommandBus-Wirtschaftslogik, Inventory, Freight und Save-Schema wurden nicht geändert. Kein neuer Windows-Build, kein Überschreiben bestehender Builds oder persönlicher Saves.

## Ursachen und tatsächlich geänderte produktive Dateien

Alle folgenden Pfade liegen unter `src/production_zero/`.

| Datei / Funktionen | Ursache und Änderung |
| --- | --- |
| `ui/unlock_tree_view.py`: `_render_icon`, Node-/Edge-Refresh, `_rebuild_scene`, `refresh_state`, Emphasis | Vollständige Szenenentsorgung und 353 temporäre Icon-Widgets entfielen. Knoten, Kanten und Tiefenmarker werden wiederverwendet; Icons entstehen beim ersten tatsächlichen Zeichnen. Unveränderte Zustands-/Emphasis-Signaturen lösen keine erneuten Updates aus. |
| `ui/resource_art.py`: `_ui_raster_atlas`, `_scaled_resource_raster`, `_cached_scaled_resource_raster` | Der bisherige 64er-Cache verdrängte sich bei 353 Produkten selbst. Jetzt maximal 768 kleine Rastervarianten; große Vorschauen werden nicht darin gehalten. Ein zusätzlicher verlustloser PNG-Atlas liefert die unveränderten Qt-Skalierungen in 32/38/48 Pixeln ohne wiederholte 512-Pixel-Dekodierung. |
| `assets/resources/ui_raster_atlas.png` | Zusätzlicher Darstellungs-Cache, kein Ersatz der 353 Originalbilder. 2.824.847 Byte auf Datenträger, 8.337.408 Byte dekodiert. Katalog, Größen und Original-SHA256 stehen in den PNG-Metadaten. Der vorhandene Packaging-Glob umfasst diese PNG bereits; kein Build ausgeführt oder Buildskript verändert. |
| `ui/factory_view.py`: Guide-Progressionssignatur, `_populate_guide_grid`, Runtime-/Session-Reset | Statt 353 Kacheln beim Öffnen entstehen nur die aktuellen Filterergebnisse. Bestehender Panel-, Rezept-/Reverse-Index- und Kachelcache bleiben erhalten. Requirements und freigeschaltete Outputs werden pro relevanter Progressionssignatur wiederverwendet. |
| `core/progression.py`: `unlock_requirement_lines` | Optionaler bereits berechneter Output-Satz vermeidet dieselbe globale Ableitung pro Kachel. Bestehende Aufrufer und Freischaltregeln behalten ihr Verhalten. |
| `ui/factory_view_v2.py`: `_refresh_content`, `_refresh_existing_board`, Frame-/Liniensignaturen, suspendiertes Board, `_status_text` | Unveränderte Boards bleiben erhalten; Belegungs-/Slotänderungen ersetzen nur betroffene Linien. MK-/Rezept-/Statusänderungen aktualisieren vorhandene Karten. Informative Guide-/Tree-/Chain-Ansichten behalten genau ein verborgenes Board. Nach Änderungen werden Layout und Auswahlgeometrie synchron gültig. Pausenprüfung verwendet einen validierten Gebäude-/Slotkontext. |
| `ui/main_window.py`: `_refresh_views`, `_refresh_entered_view` | Sichtbare Projektion und globale Werte aktualisieren sofort; verborgene Projektionen werden als veraltet markiert und bei Tab-Eintritt aktualisiert. Keine zweite GameState-Kopie. |
| `ui/supply_view.py`: `_notify_and_refresh` | Auch ein programmgesteuerter Kauf aus einem verborgenen Tab aktualisiert seinen eigenen Angebotsstatus sofort. Im sichtbaren Normalfall entsteht kein zusätzlicher doppelter Refresh. |
| `ui/contracts_view.py`: `ContractProductPicker` | Nur der große kumulative Leaderboard-Picker materialisiert gepufferte sichtbare Reihen. Logischer Katalog und Suche umfassen weiterhin 353 Produkte. Bestehende Tile-Klassen, Größen und Styles bleiben erhalten; kleinere Vertrags-/Forschungspicker behalten ihren bisherigen Ablauf. |
| `ui/leaderboard_view.py`: Pickeröffnung, `_refresh_ranking`, `_update_entry_row` | Ein Dialog mit wiederverwendeten Definitionen/Kacheln; eigene angeheftete Row bleibt dieselbe Instanz. Werte und Rang-Properties aktualisieren direkt; PROFILE liest den aktuellen Eintrag. Unveränderte fremde Einträge werden nicht neu gebaut. |
| `persistence/session_writer.py`: `_detach_snapshot`, `snapshot_game_state` | Generisches rekursives `deepcopy` wird für bereits serialisierte Container durch gezieltes vollständiges Ablösen ihrer veränderlichen Inhalte ersetzt. Unbekannte Blatttypen verwenden weiterhin konservativ `deepcopy`. Schreibwarteschlange, Encoder, atomarer SQLite-Commit und Schema bleiben unverändert. |

## Cachegrenzen und Invalidierung

Die Graph-Pools enthalten höchstens den vorhandenen Katalog: 353 Knoten, 708 Kanten, acht Tiefenobjekte. Der Icon-Pixmapcache ist auf 512 Einträge à 38×38 begrenzt (unter 2,83 MiB reine Pixeldaten). Der Rastercache hält höchstens 768 Varianten mit jeweils höchstens 128² Pixeln (höchstens 48 MiB reine Pixeldaten, zuzüglich Verwaltungsdaten). Der einmal geladene Rasteratlas benötigt zusätzlich 7,95 MiB. Der vorhandene begrenzte Quellbildcache bleibt für andere Größen bestehen; große Vorschauen können weiterhin dessen PNG-Dekodierspeicher aufbauen.

Der erste Messdurchgang deckte einen echten Nachteil rein verzögerter Icons auf: Erstes Pan/Zoom in unbesuchte Bereiche musste weitere große PNGs dekodieren. Deshalb wurde vor der endgültigen Abnahme der Atlas ergänzt. Er enthält ausschließlich die exakt vorhandene Qt-`SmoothTransformation`, keine neue Grafikgestaltung. Ein Test prüft alle 353 Original-SHA256 und alle 1.059 skalierten Bilder auf Pixelgleichheit. Katalog-/Größenabweichung oder fehlender Atlas führt zum ursprünglichen Rasterpfad zurück. Die reproduzierbare Erzeugung liegt in `scripts/phase1_raster_atlas.py`; nach einer Änderung der Originalgrafiken muss dieser Cache neu erzeugt werden, was der Hash-/Pixeltest erzwingt. Der erste Messdurchgang bleibt unter `artifacts/phase1/after-first-pass/` erhalten.

Guide und Picker behalten höchstens eine Kachel pro logischem Produkt, also 353. Es existieren höchstens ein Guide-Panel, ein Tree-Panel, ein unterlegtes Board und ein Leaderboard-Produktdialog je zugehöriger View. Ein vollständiger Katalogbesuch darf den Cache füllen; das ist keine Zusage dauerhaft minimaler Speichernutzung.

Guide-Invalidierung berücksichtigt freigeschaltete Produktionen, kumulative Mengen, Company-Level, erstmalig produzierte Ressourcen und gemeisterte Familien. Ein sichtbarer Guide prüft dies auch im Runtime-Refresh, sodass ein laufender Unlock ohne erneutes Öffnen erscheint. Filterwechsel verwenden die aktuelle Signatur. New Game und Load löschen die sitzungsabhängigen Panels, Requirement-/Ergebniscaches, das unterlegte Board und seine Runtime-Referenzen; unveränderliche Definitionen und Assets bleiben wiederverwendbar.

Der Pausenkontext ist keine zweite Belegungsverwaltung: Vor Benutzung werden Karten-ID, Slotidentität und Gebäudeidentität in den aktuellen State-Collections geprüft. Move/Swap, ersetzte Slots, Gebäudeentfernung und Load erzwingen bei ungültigem Kontext eine neue Suche. Einzel-, Linien- und Gebäudepause verwenden weiter dieselbe Core-Hierarchie. Unplatzierte/Freight-Vorschauen behalten den ursprünglichen Fallback.

Die vorhandene Auswahlarchitektur bleibt unverändert. Sie aktualisierte bereits nur geänderte Auswahl-Properties. Der Gewinn entsteht durch weniger strukturelle Boardarbeit; keine Swap-, Drag-Ghost- oder Auto-Scroll-Funktion aus P4 wurde hinzugefügt.

## Messmethode und Ergebnisse

Windows 11, Python 3.12.14, Qt/PySide6 6.11.1, Offscreen-Qt, `PYTHONHASHSEED=0`, 1366×768 und Qt-Skalierung 1. Gleiche explizite Windowsfont-Registrierung und Stylesheets wie in Phase 0; echte MainWindow-Kaufproben verwenden dessen normalen Anwendungsstil. Vorher-Quellen kommen aus der neuen P1-Sicherung. Die Phase-0-Skripte und ursprünglichen Rohdaten wurden nicht überschrieben. Der Wrapper verändert ausschließlich Ausgabeziel und Wiederholungszahl, keine Datengröße, Fensterfläche oder Wirtschaftswerte.

Jeder Cold-View-Aufbau wurde siebenmal in frischen Prozessen gemessen. Warme UI-Operationen umfassen 7×7 = 49 Stichproben. Core-, aktive Karten-/Save- und zusätzliche UI-Aktionsmessungen haben jeweils mindestens sieben Wiederholungen. Käufe: sieben 20er-Bursts je Firmengröße, 140 einzelne Kaufcallbacks. Kein paralleler Test-/Build-/Benchmarkprozess während der Performance-Messungen. Alle Zeiten in ms, Stichprobenmedian und Maximum; keine p95-Schätzung. Kombinierte Callback-plus-Event-Zeiten sind keine nativen FPS.

Die ursprüngliche Phase-0-Einzelmessung lag bei 2.265,73 ms Unlock-Konstruktion, 406,33 ms warmem Rebuild, 3.854,54 ms Guide und rund 2.549 ms Picker. Die neuen Vorher-Wiederholungen reproduzieren diese Größenordnung. Folgende Tabellen vergleichen die wiederholte Vorher-Messung mit dem endgültigen Stand einschließlich Rasteratlas.

| Messung | n vorher / nachher | Vorher Median / Max ms | Nachher Median / Max ms |
| --- | --- | --- | --- |
| Unlock: Konstruktion | 7 / 7 | 2271.96 / 2462.42 | 93.58 / 100.81 |
| Unlock: erstes Show/Layout/Paint | 7 / 7 | 75.11 / 101.58 | 138.07 / 145.66 |
| Unlock: unveränderter Rebuild | 49 / 49 | 397.74 / 492.28 | 0.06 / 0.35 |
| Unlock: unveränderter Statusrefresh | 49 / 49 | 56.36 / 78.45 | 0.04 / 7.34 |
| Unlock: vollständiges Rendern | 49 / 49 | 51.48 / 68.09 | 46.32 / 59.10 |
| Unlock: Zoomschritt + Pan + Events | 49 / 49 | 76.98 / 111.16 | 69.85 / 90.96 |
| Guide: erstes Öffnen | 7 / 7 | 3961.69 / 4338.11 | 480.98 / 528.78 |
| Guide: Board zurück / erneut öffnen | 49 / 49 | 55.16 / 83.39 | 20.21 / 23.09 |
| Guide: steel + zurück, zwei Filter | 49 / 49 | 82.76 / 116.82 | 22.83 / 58.58 |
| Guide: Processing + All, zwei Filter | 49 / 49 | 114.43 / 156.98 | 57.54 / 328.71 |
| Guide: Steel-Chain + zurück | 49 / 49 | 40.25 / 56.76 | 39.47 / 57.25 |
| Guide: Rendern | 49 / 49 | 12.54 / 116.63 | 11.49 / 14.25 |
| Picker: neue Instanz konstruieren | 49 / 49 | 2552.51 / 2888.27 | 161.49 / 215.72 |
| Picker: erstes Show/Paint | 7 / 7 | 167.17 / 204.87 | 32.03 / 44.73 |
| Picker: iron + zurück | 49 / 49 | 95.44 / 135.93 | 16.11 / 26.64 |
| Leaderboard: unverändert | 49 / 49 | 0.98 / 9.92 | 0.16 / 6.94 |
| Leaderboard: Produktionswert geändert | 49 / 49 | 3.20 / 5.07 | 0.20 / 0.55 |

**Vollständiger Unlock-Cold-Open (Konstruktion + erstes Show/Paint, paarweise je Prozess): 2347.07 / 2564.00 → 232.10 / 243.80 ms**, jeweils sieben Stichproben. Die bloße Konstruktion wäre bei verzögerten Icons allein irreführend.

**Unlock-Working-Set-Zuwachs beim ersten Öffnen:** Median 386.07 → 33.72 MiB; Maximum 386.46 → 33.88 MiB, je sieben frische Prozesse. Das umfasst Bilder, Fonts, Qt, Szene und Heap; keine isolierte Cacheallokation oder Langzeit-Leakmessung.

Vorher, erster UI-Lauf: Guide 353 materialisierte Kacheln / 2603 QWidget-Nachfahren der gesamten View; Picker 353 materialisierte Kacheln / 2504 Widgets. Nachher, erster UI-Lauf: Guide 35 materialisierte Kacheln / 377 QWidget-Nachfahren der gesamten View; Picker 20 materialisierte Kacheln / 173 Widgets. Der logische Katalog umfasst in beiden Ständen 353 Produkte. Das historische JSON-Feld `picker.products` zählt materialisierte Tiles; es bedeutet im neuen bedarfsgerechten Picker nicht die logische Produktmenge. Die Widgetzählung schließt zurückgehaltene und eventuell noch auf DeferredDelete wartende Kinder ein. Die Regression erreicht alle 353 Guide-Produkte; Caches dürfen sich bei weiteren Besuchen füllen.

### UI-Blockierung und schnelle Aktionen

Die Rohdaten trennen synchrone Callbackdauer, Gesamtzeit einschließlich Event-Drain und den vor dem Callback eingereihten Zero-Timer. Letzterer kann vor Paint laufen und ist daher keine Obergrenze der sichtbaren Unterbrechung. `comparison.json` enthält für jede Reihe Median/Maximum/N dieser drei Größen; `comparison-tables.md` enthält alle Ergebnisse einschließlich sämtlicher Core-Kontrollmessungen.

| Messung | n vorher / nachher | Vorher Median / Max ms | Nachher Median / Max ms |
| --- | --- | --- | --- |
| 50 Karten: kompletter 20er-Kaufburst | 7 / 7 | 2472.88 / 2699.74 | 519.10 / 551.60 |
| 500 Karten: kompletter 20er-Kaufburst | 7 / 7 | 2668.21 / 2820.26 | 636.05 / 714.87 |

| Messung | n vorher / nachher | Vorher Median / Max ms | Nachher Median / Max ms |
| --- | --- | --- | --- |
| 50 Karten: einzelner Kauf innerhalb des Bursts | 140 / 140 | 103.30 / 291.36 | 4.53 / 184.00 |
| 500 Karten: einzelner Kauf innerhalb des Bursts | 140 / 140 | 108.76 / 321.11 | 5.22 / 210.77 |

Die erste Processing-Filterauswahl erzeugt erstmals zusätzlich benötigte Kacheln. Deshalb steigt das Filterpaar-Maximum von 156.98 auf 328.71 ms, obwohl der Median sinkt. Dies ist die konkret verbleibende Gegenleistung der bedarfsgerechten Materialisierung; sie wird nicht als Framebudget-Erfolg ausgegeben. Die Summe aller gemessenen Guide-Intervalle pro identischem UI-Lauf (Öffnen und je sieben Such-/Filter-, Render- und Navigationsintervalle, ohne Setup/Profile) beträgt vorher 6288.65 / 6599.81, nachher 1711.71 / 2027.10 ms. Der frühere mehrsekündige Komplettaufbau wird vermieden.

| UI-Pfad | Callback vorher Median / Max | Callback nachher Median / Max | Queue vorher Median / Max | Queue nachher Median / Max |
| --- | --- | --- | --- | --- |
| Unlock-Konstruktion | 2271.96 / 2462.42 | 93.58 / 100.81 | 2272.03 / 2462.53 | 93.67 / 100.91 |
| Unlock-Status | 5.83 / 9.19 | 0.01 / 7.23 | 5.91 / 9.30 | 0.02 / 7.31 |
| Zoom + Pan | 0.12 / 0.23 | 0.13 / 0.41 | 0.29 / 0.46 | 0.19 / 0.49 |
| Guide erstes Öffnen | 3860.15 / 4240.96 | 443.28 / 492.02 | 3860.19 / 4241.03 | 443.32 / 492.06 |
| Guide Suchpaar | 70.99 / 98.65 | 12.73 / 34.43 | 71.95 / 100.00 | 13.07 / 39.90 |
| Guide Filterpaar | 100.45 / 134.07 | 44.43 / 307.90 | 100.79 / 134.76 | 44.83 / 308.49 |
| Guide zurück / erneut öffnen | 40.85 / 60.65 | 8.60 / 10.05 | 41.09 / 60.92 | 8.67 / 10.15 |
| Leaderboard-Wertänderung | 1.73 / 2.70 | 0.15 / 0.38 | 1.84 / 2.90 | 0.18 / 0.40 |
| 500er Shift-Auswahl | 10.17 / 14.15 | 10.55 / 16.04 | 10.23 / 14.24 | 10.60 / 16.20 |

| Messung | n vorher / nachher | Vorher Median / Max ms | Nachher Median / Max ms |
| --- | --- | --- | --- |
| 50 Karten: 20 einzelne Verkäufe | 7 / 7 | 1358.58 / 1380.88 | 227.38 / 251.08 |
| 50 Karten: vier MK-Upgrades | 7 / 7 | 293.28 / 306.75 | 26.29 / 30.09 |
| 50 Karten: sieben Slotfreischaltungen | 7 / 7 | 217.57 / 291.99 | 90.64 / 100.65 |
| 50 Karten: 20 Rezeptzuweisungen | 7 / 7 | 1350.80 / 1361.85 | 47.24 / 52.52 |
| 50 Karten: Copy / Kauf von zehn Templates | 7 / 7 | 137.10 / 146.17 | 28.02 / 29.79 |
| 500 Karten: 20 einzelne Verkäufe | 7 / 7 | 1164.74 / 1261.74 | 233.78 / 273.98 |
| 500 Karten: vier MK-Upgrades | 7 / 7 | 288.20 / 301.61 | 49.02 / 51.25 |
| 500 Karten: sieben Slotfreischaltungen | 7 / 7 | 165.75 / 176.58 | 99.17 / 106.60 |
| 500 Karten: 20 Rezeptzuweisungen | 7 / 7 | 1444.91 / 1759.78 | 72.02 / 85.82 |
| 500 Karten: Copy / Kauf von zehn Templates | 7 / 7 | 145.17 / 153.50 | 30.77 / 49.16 |

Kaufproben verwenden die echte MainWindow-Verkabelung und die vorhandenen Supply-Callbacks. Zusätzliche Aktionsproben messen den bestätigten Arbeitsanteil ohne menschliche Modalwartezeit; Fixtures und Vorbereitungen liegen außerhalb der Uhr. Es sind dieselben legalen Hallen mit 50 Plätzen wie in Phase 0, bei 500 Karten entsprechend mehrere Hallen. Alle sieben Wiederholungen prüfen die erwartete Transaktionszahl und resultierende Karten-/Slot-/MK-/Rezeptdaten. Copy erzeugt weiter keine Wirtschaftsaktion; Paste kauft weiter neue MK1-Common-Maschinen. Die UI-Regression prüft Cash-Text und exakten Cash-Tooltip unmittelbar nach Aktionen, unveränderte Widgetidentitäten sowie den notwendigen Refresh beim Tabwechsel.

### Große aktive Firmen, Rendering und Savekosten

| Messung | n vorher / nachher | Vorher Median / Max ms | Nachher Median / Max ms |
| --- | --- | --- | --- |
| 10 aktive Karten: vollständige Kartenfläche rendern | 7 / 7 | 2.99 / 3.55 | 3.17 / 3.81 |
| 10 aktive Karten: Runtime-Refresh | 7 / 7 | 0.20 / 3.20 | 0.11 / 3.25 |
| 10 aktive Karten: Snapshot Hauptthread | 7 / 7 | 9.66 / 28.10 | 6.02 / 22.14 |
| 50 aktive Karten: vollständige Kartenfläche rendern | 7 / 7 | 19.49 / 20.36 | 15.11 / 16.75 |
| 50 aktive Karten: Runtime-Refresh | 7 / 7 | 3.99 / 23.37 | 0.65 / 17.65 |
| 50 aktive Karten: Snapshot Hauptthread | 7 / 7 | 32.82 / 68.48 | 13.65 / 35.86 |
| 100 aktive Karten: vollständige Kartenfläche rendern | 7 / 7 | 43.85 / 47.44 | 30.55 / 33.27 |
| 100 aktive Karten: Runtime-Refresh | 7 / 7 | 12.36 / 60.02 | 1.19 / 35.11 |
| 100 aktive Karten: Snapshot Hauptthread | 7 / 7 | 35.40 / 60.52 | 21.64 / 47.73 |
| 500 aktive Karten: vollständige Kartenfläche rendern | 7 / 7 | 472.26 / 509.50 | 188.82 / 198.45 |
| 500 aktive Karten: Runtime-Refresh | 7 / 7 | 301.37 / 779.13 | 6.43 / 212.29 |
| 500 aktive Karten: Snapshot Hauptthread | 7 / 7 | 181.76 / 267.98 | 159.01 / 208.20 |

| Messung | n vorher / nachher | Vorher Median / Max ms | Nachher Median / Max ms |
| --- | --- | --- | --- |
| 500 aktive Karten: Simulationstick | 7 / 7 | 5.39 / 8.43 | 7.64 / 12.04 |
| 500 aktive Karten: Snapshot-Encoding | 7 / 7 | 93.05 / 113.98 | 100.27 / 131.68 |
| 500 aktive Karten: SQLite-Commit | 7 / 7 | 42.50 / 45.18 | 45.21 / 56.03 |
| 500 aktive Karten: Snapshot + Encoding + Commit | 7 / 7 | 340.51 / 400.07 | 233.27 / 277.36 |
| 500 aktive Karten: Load | 7 / 7 | 173.96 / 220.86 | 175.47 / 208.07 |

Die aktive Phase-0-Fixture bleibt vollständig erhalten: ein aktiver Extraktor pro Standort, dieselbe große vollständige Renderfläche, dieselben Slotstrukturen und 240 Historywerte pro Serie. Der umfangreiche Standort-/Slotbestand erklärt einen Teil der verbleibenden Serialisierungskosten. Payloadgrößen bleiben gleich; es werden keine Daten oder Historien zur Beschleunigung weggelassen. Encoding/Commit/Load laufen im echten SessionWriter weiter außerhalb des Hauptthreads; die Tabelle misst ihre Einzelkosten separat synchron. Der Snapshot selbst bleibt Hauptthreadarbeit.

### Auswahl-Stresstest

| Messung | n vorher / nachher | Vorher Median / Max ms | Nachher Median / Max ms |
| --- | --- | --- | --- |
| 10 Karten: Shift-Auswahl inklusive Paint | 49 / 49 | 7.25 / 26.68 | 6.91 / 24.82 |
| 10 Karten: Rechteckauswahl abschließen | 49 / 49 | 0.35 / 3.04 | 0.38 / 1.53 |
| 10 Karten: 100 Rechteckbewegungen | 49 / 49 | 1.49 / 2.69 | 1.63 / 3.46 |
| 10 Karten: vollständige Boardfläche rendern | 49 / 49 | 20.08 / 24.56 | 18.29 / 26.25 |
| 50 Karten: Shift-Auswahl inklusive Paint | 49 / 49 | 15.70 / 51.07 | 14.88 / 47.07 |
| 50 Karten: Rechteckauswahl abschließen | 49 / 49 | 0.56 / 1.10 | 0.60 / 1.21 |
| 50 Karten: 100 Rechteckbewegungen | 49 / 49 | 1.45 / 1.92 | 1.61 / 2.13 |
| 50 Karten: vollständige Boardfläche rendern | 49 / 49 | 29.29 / 36.49 | 26.74 / 36.50 |
| 100 Karten: Shift-Auswahl inklusive Paint | 49 / 49 | 16.36 / 54.88 | 17.20 / 50.81 |
| 100 Karten: Rechteckauswahl abschließen | 49 / 49 | 0.80 / 1.44 | 0.86 / 1.28 |
| 100 Karten: 100 Rechteckbewegungen | 49 / 49 | 1.47 / 2.18 | 1.53 / 2.58 |
| 100 Karten: vollständige Boardfläche rendern | 49 / 49 | 28.99 / 38.38 | 28.38 / 34.98 |
| 500 Karten: Shift-Auswahl inklusive Paint | 49 / 49 | 25.59 / 58.47 | 25.72 / 80.70 |
| 500 Karten: Rechteckauswahl abschließen | 49 / 49 | 3.36 / 5.78 | 3.06 / 4.68 |
| 500 Karten: 100 Rechteckbewegungen | 49 / 49 | 1.60 / 2.79 | 1.54 / 2.40 |
| 500 Karten: vollständige Boardfläche rendern | 49 / 49 | 29.57 / 34.71 | 27.68 / 43.03 |

100 und 500 Karten auf **einem** Auswahlboard sind die unveränderten synthetischen Phase-0-Stressfixtures oberhalb der realen Hallengrenze; die Aktionen mit einer 500-Karten-Firma verwenden dagegen mehrere normale Hallen. Das Auswahlboard bleibt 1366×768 mit derselben Scrollfläche; sein Rendern zeichnet den Viewport, während die separate aktive Kartenprobe die große vollständige Kartenfläche zeichnet. Die Auswahlfilter werden nicht als Engpass neu erfunden. Paint und Geometriearbeit sind getrennt von den kleinen Filter-/Auswahlcallbacks zu betrachten.

Reproduktion: `scripts/phase1_validate.py --after-only --test-output final-atlas-tests` führt vollständige Regression, alle Nachher-Messungen, sechs Capture-Konfigurationen, Vergleiche und Schutzprüfung seriell aus. Einzelmessungen: `phase1_measure.py before|after ui|actions|rapid|active|extended`; für Vorher `--source artifacts/phase1/before-tree`, für Cold-UI und Kaufbursts zusätzlich `--repeat 7`. Bestehende Ausgaben vor einer erneuten Messung in ein eigenes Versuchsverzeichnis sichern.

## Getrennte Snapshot-/Save-Prüfung

Der Serializer liefert teilweise Referenzen auf lebende Dictionaries/Listen. Deshalb darf seine Ausgabe nicht direkt zum Worker gehen. Der neue Kopierer löst weiterhin alle nicht-historischen Container rekursiv ab. Eine gezielte Regression vergleicht alle veränderlichen Objektidentitäten von GameState und Snapshot, prüft identisches JSON zur ursprünglichen Serialisierung und verändert anschließend unter anderem Company-, Produktions-, Karten-, Hallen-, Vertrags- und Consortium-Daten. Der Snapshot bleibt unverändert.

Die bereits vorhandenen `HistoryPrefix`-Objekte bleiben unverändert: Sie halten die beim Snapshot erfasste Länge eines append-only Präfixes; History-Trim ersetzt die zugrunde liegende Liste. Vorhandene Tests prüfen Append und Trim sowie eine Million Werte ohne erneute Vollkopie. Dies ist derselbe bestehende Invariantenvertrag, keine neue lebende GameState-Referenz für den Worker.

Weitere Regressionen prüfen einen fehlgeschlagenen Schreibversuch mit anschließender erfolgreicher Wiederherstellung, genau geordnete Writes, SQLite-Integrität sowie einen blockierten alten Autosave vor einem neueren New-Game-Snapshot. `shutdown` wartet auf beide; der geladene Endstand ist das neue Spiel. Die bestehenden Save-/Load-/Reset-/Integrationsprüfungen bleiben Teil der vollständigen Suite.

## Tests, visuelle Regression und verbleibende Grenzen

**1270/1270 Tests in 81/81 Modulen bestanden, 0 Fehler, 0 Skips.** Alle ursprünglichen 1.257 Fälle und ihre Modul-Fallzahlen sind erhalten; 13 neue Regressionen einschließlich Parameterfällen ergänzen sie. Der abschließende vollständige, serielle Lauf des endgültigen Atlas-Stands liegt unter `artifacts/phase1/final-atlas-tests/`; `final-test-summary.json` fasst ihn zusammen. Frühere fehlgeschlagene/korrigierte Versuche bleiben zur Nachvollziehbarkeit erhalten.

Gezielte neue Nachweise: Graphbestand und Poolidentität, kein eager Iconaufbau, Mengenlabel-Repaint bei tatsächlicher Änderung, pixelgleiche Icons mit/ohne Stylesheet, sämtliche 1.059 Rastervarianten und Original-SHA256, alle 353 Guide-Produkte, sofortige Progressionsaktualisierung, Reset und Boardwiederverwendung, Picker-Suche/Scroll/Identität, eigene Leaderboard-Row/Highlight/aktuelles Profil mit großen Zahlen, Pausenhierarchie inklusive Move/Gruppenpermutation und Load, echte 20er-Aktionen bei 50/500 Karten, Slotänderungen ohne fremden Linienaufbau sowie Snapshot-/Schreibfehler-/New-Game-Reihenfolge.

Zwei bestehende Testdateien wurden fachlich angepasst: `tests/test_factory_ui.py` erreicht noch nicht erzeugte Guide-Produkte über die vorhandene Suche, prüft verborgene wiederverwendete Boards statt deren erzwungener Löschung und fordert Runtime-Rekonnektion nach einer echten Strukturänderung. Suchtext-/Scroll-Erhalt bleibt geprüft. `tests/test_secondary_modernization.py` unterscheidet neu erreichte Tiles von bereits erzeugten und prüft deren Identität beim erneuten gleichen Filter. Keine Fälle wurden entfernt, deaktiviert oder übersprungen. Der bestehende Rechteckauswahltest blieb fachlich unverändert und deckte den korrigierten synchronen Layoutabschluss nach Linienersatz auf.

**36 Vergleichsscreenshots, 18 Paare, alle pixelgleich:** Unlock Tree, Guide und Leaderboard bei 1366×768, 1600×980 und 1920×1080, jeweils 100 % und 200 % Qt-Skalierung. Dateien unter `artifacts/phase1/before/dpi1|dpi2/` und `after/dpi1|dpi2/`; sämtliche Pixelvergleiche einschließlich tatsächlicher Bildgrößen in `visual-comparison.json`. Die Fonts wurden ausdrücklich registriert. Der statische Vergleich und erhaltene Row-/Kachelidentitäten sichern Darstellung und beseitigte strukturelle Flackerursachen; native DWM-/GPU-Bewegungsqualität und menschlich bewertetes Pan-/Zoom-Gefühl sind damit nicht als geprüft behauptet.

Die abschließende SHA-256-Schutzprüfung bestätigt 5124 unveränderte Bestandsdateien aus Builds, Phase-0-Nachweisen, Originalgrafiken, Styles, Spieldaten, unveränderter Core-Wirtschaftslogik und SQLite-Serializer sowie alle fünf persönlichen Saves. Details: `protected-verification.json`. Der einzige Core-Eingriff ist der optionale vorberechnete Darstellungs-Kontext für Requirementtexte; Formeln, Preise und Freischaltregeln bleiben identisch.

Das 16-ms-Ziel ist **kein pauschaler Erfolg**: Unveränderte Status-/Ranking-Updates und die große aktive Runtime-Probe sind anhand der Tabellen zu bewerten; komplette Szenen-/Board-Paints, Filterpaare mit Layoutarbeit, erste bedarfsgerechte Materialisierung, Chain-Roundtrips und große Snapshots können darüber liegen. Ein erstmaliger Filter kann neue Kacheln anlegen; sein Maximum darf nicht mit einem bereits warmen Cache verwechselt werden. Alle Maxima bleiben im Bericht sichtbar. Der begrenzte globale Quellbildcache kann bei großen Vorschauen weiterhin bis zum vollständigen Originalkatalog wachsen. Native Framerate und stundenlange Speichernutzung wurden nicht gemessen.

Snapshotkosten oberhalb eines Frames bleiben wegen vollständiger Datenerfassung und Containerablösung bestehen; es wurde keine Integrität zugunsten einer kleineren Messfixture aufgegeben. Weitere Rendering-/Serialisierungsarbeit ist als verbleibender Aufwand dokumentiert und eröffnet keine spätere Roadmap-Phase. Keine Gameplay-/Balancing-/Inventoryänderung und kein Windows-Build.

Zusätzliche Dateien zur Reproduktion: `scripts/phase1_measure.py`, `phase1_capture.py`, `phase1_compare.py`, `phase1_ui_actions.py`, `phase1_validate.py`, `phase1_visual_compare.py`, `phase1_verify_protected.py`, `phase1_rerun.py`, `phase1_raster_atlas.py`, `phase1_finish_report.py` und `tests/test_phase1_performance.py`. Produktive Änderungen sind vollständig in der Dateitabelle oben aufgeführt.
