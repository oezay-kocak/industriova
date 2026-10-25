# Industriova 0.2.0.dev3 – Save Reset und Windows-Playtest

Stand: 19.10.2026. Ergebnis: gezielte Speicherstandtrennung und New-Game-Reparatur abgeschlossen; Windows-Playtest-Paket erstellt und die geforderten 16 Bedienpfade an der tatsächlich gebauten EXE erfolgreich geprüft. Vollständige Regression: **1.200 bestanden, 0 Fehler, 0 übersprungen** in 76 ausgeführten Testmodulen. Die menschliche Langzeitabnahme bleibt dem anschließenden Playtest vorbehalten.

## 1. Sicherung und Umfang

Vor Beginn wurde der Arbeitsstand einschließlich der uncommitteten Dateien gesichert: `artifacts/dev3/20261019T121025Z/working-tree.zip`, 737 Dateien, mit SHA256-Manifest daneben. Grundlage ist der vorhandene UI-Polish einschließlich dessen Bericht `docs/industriova-ui-polish-report.md`. Keine Rücksetzung des Overhauls und keine zusätzliche Designentwicklung.

Alle 39 vorhandenen Python-Dateien im Core sowie SQLiteStore und SessionWriter sind gegenüber dieser Sicherung bytegleich. Damit bleiben insbesondere Wirtschaft, MK-/Rarity-Logik, Startervergabe, Simulation und die bestehenden SQLite-Sicherheitsmechanismen unverändert. Nachweis: `artifacts/dev3/final-audit.json` und `source-sha256.json`.

## 2. Verbindlicher Speicherpfad

Normaler Windows-Start und Autosave: **`%LOCALAPPDATA%\Industriova\saves\company.sqlite`**, automatisch geladener SQLite-Slot **`company`**.

Dev SAVE GAME / LOAD GAME: **`%LOCALAPPDATA%\Industriova\saves\dev\dev_save.json`** als getrennte manuelle Sicherung. New Game schreibt den neuen Zustand verbindlich in die normale SQLite-Datei; eine ausdrücklich angelegte manuelle Sicherung bleibt für LOAD GAME erhalten.

Der zentrale neue Helfer `src/production_zero/persistence/paths.py` wird vom App-Einstieg und vom DevSaveStore verwendet. Wenn LOCALAPPDATA fehlt, wird APPDATA, danach das Benutzerverzeichnis verwendet, jeweils ausschließlich mit `Industriova/saves`. Es gibt keinen Production-Zero-Fallback, keinen automatischen Legacy-Import und keine Anzeige alter Slots. EXE und Quellstart verwenden dieselben kompilierten Helfer.

`%LOCALAPPDATA%\Production Zero\saves` wird vollständig ignoriert. Es wurde keine automatische Löschung oder Bereinigung eingebaut. Persönliche Originalspielstände wurden für diese Arbeiten weder überschrieben noch gelöscht. Die Tests liefen ausschließlich mit isolierten Verzeichnissen und synthetischen Saves.

Aktive QA-Pfadhelfer und Build-Dokumentation wurden entsprechend angepasst. Historische Diagnose-/dev2-Skripte dürfen weiterhin historische Pfade als Vergleichsdaten untersuchen; sie sind kein Teil des normalen Spielstarts.

## 3. Nachgewiesene Ursache und New-Game-Reparatur

Neben dem Legacy-Pfad bestand ein tatsächlicher UI-Synchronisationsfehler: Die gemeinsamen GameState-Felder wurden ausgetauscht, während FactoryViewBase in `_units` weiterhin die bisherige Gebäudeliste hielt. Eine sichtbare Aktualisierung allein band diese Referenz nicht neu. Auswahl, Clipboard, verzögerte Scroll-Wiederherstellung und einige Dialog-/Render-Caches konnten ebenfalls zum vorigen Spiel gehören.

Die minimale Reparatur liegt in `ui/main_window.py` (`replace_state`) und gezielten `reset_for_state_change`-Methoden in FactoryViewBase, FreightView und ContractsView. Die bestehende gemeinsame GameState-Referenz bleibt erhalten, damit alle Verbraucher dasselbe Objekt verwenden; sämtliche Felder stammen aus dem frischen beziehungsweise ausdrücklich geladenen Zustand. Die Boards binden anschließend ihre Gebäudelisten neu. Auswahlen, Zwischenablage, Drag-Zustände, Such-/Kategorieauswahlen und relevante Widget-/Render-/Scroll-Caches werden zurückgesetzt. Offene zustandsabhängige Dialoge und Ressourcenansichten werden geschlossen beziehungsweise aktualisiert. Research, Consortium, Supply und Ereignisanzeige erhalten ebenfalls konsistente neue Ansichten. Die CommandBus-Historie wird geleert.

Nach dem vollständigen Wechsel wird synchron auf das Speichern des neuen SQLite-Snapshots gewartet. Der bestehende SessionWriter verarbeitet seine Queue mit einem Worker in Reihenfolge: Ein bereits wartender alter Snapshot liegt vor dem neuen Snapshot und kann diesen anschließend nicht überschreiben. Das ist mit einem absichtlich blockierten alten Schreibauftrag getestet. Weitere Autosaves lesen den aktuellen gemeinsamen Zustand. Der Dev-Status meldet einen Speicherfehler ausdrücklich, statt einen erfolgreichen New-Game-Save vorzutäuschen.

Offizielle Startwerte bleiben erhalten:

| Merkmal | Frischer Start / New Game |
|---|---|
| Cash, Company | $1.250, Level 1, XP 0 |
| Vorgesehener Bestand | Iron Ore 145, Coal 70, Copper Ore 88; insgesamt 303 |
| Starterkarten | 3 Extractor, 2 Processor, 1 Solar Array, 2 Freight Trucks |
| MK / Rarity | Alle MK1 / Common |
| Installation | Noch keine Starterkarte installiert; Einsetzen über Build Slot |
| Anfangsgebäude | Mining Complex 1, Hall 1, Plant 1, Garage 1 |
| Freie Anfangsplätze | Resources 1, Factory 6, Energy 1, Freight 3 |
| Altzustand | Keine alten Maschinen, Aufträge, Freight-Lieferungen oder Upgrades |

Die 303 Startressourcen sind beabsichtigte bestehende Starterwerte, kein zurückgebliebener Altbestand. Starterkarten und Direktkauf stehen weiterhin nebeneinander: Starter einsetzen kostet keinen Kaufpreis; neu gekaufte Maschinen werden auf passende freie Plätze installiert.

## 4. Save-Tests A–G und Persistenz

Neue Abdeckung: `tests/test_industriova_save_reset.py`, zehn ausgeführte Fälle einschließlich dreier Pfadvarianten.

| Fall | Verfahren und Ergebnis |
|---|---|
| A – Frisch | Tatsächlicher App-Einstieg im isolierten Unterprozess ohne Save; korrekter Start und neue Industriova-SQLite-Datei. Bestanden. |
| B – Nur Legacy | Inkompatible Legacy-SQLite mit Schema 999, hohem Cash und fremden Maschinen; normaler Einstieg ignoriert sie, startet offiziell frisch. Bestanden. |
| C – Beide | Gültiger neuer Industriova-Save neben Legacy; ausschließlich neuer Save geladen. Bestanden. |
| D – New Game | Echte Qt-Fenster/Dev-New-Game: vorher belegte Resources-, Factory- und Energy-Boards, Upgrades, Auswahl/Clipboard, Caches, Vertrag und Lieferungen; danach frische Daten und neu gebundene sichtbare Boards. Zusätzlich in der kompilierten EXE bestätigt. |
| E – Save/Restart | Nach New Game erneut drei Starter installieren, speichern, Fenster schließen und laden; Daten und Karten sichtbar korrekt. Zusätzlich native EXE einschließlich manuellem SAVE/LOAD. |
| F – Wiederholt | A/B/C jeweils drei App-Starts; keine Legacy-Übernahme oder Duplikate. Native EXE ebenfalls dreimal gestartet; New-Game-Zustand über Neustart erhalten. |
| G – Legacy unverändert | Byte-/SHA256-Vergleich der Testdateien vor und nach Starts, Spielaktionen und Neustarts. Keine Änderungen und keine Legacy-Migrationsbackups. |

Weitere gezielte Nachweise: alter blockierter Autosave vor New Game; manuelles SAVE → NEW GAME → LOAD mit korrekter UI-Neubindung; gültiger Schema-4-Save im neuen Verzeichnis wird weiterhin über die bestehende Migration samt Sicherheitsbackup geladen, bei erneutem Start idempotent. Diese Migration betrifft ausschließlich bewusst im neuen Industriova-Verzeichnis vorhandene Daten, niemals die Legacy-Datei.

Gezielter kombinierter Lauf: 48 bestanden (`artifacts/dev3/save-tests-final.txt`). Vollständiger Lauf: 76/76 Module, **1.200 bestanden**, keine Fehlschläge, Fehler oder Skips (`artifacts/dev3/regression/results.json`). Die bisherigen 1.190 Fälle bleiben erhalten; der Audit prüft zusätzlich, dass keine bisherigen Testfunktionen entfernt wurden und keine XFAIL-Abkürzungen hinzugekommen sind.

## 5. Tatsächliche Windows-EXE: Bedienprüfung

Geprüft wurde `dist/playtest/dev3/Industriova/Industriova.exe` unter Windows mit `QT_QPA_PLATFORM=windows`. Die Bedienung erfolgte über Windows-Maus-/Tastatureingaben mit dem Computer-Use-Werkzeug, nach jedem Schritt anhand des tatsächlichen Fensters kontrolliert. Keine direkten Backend-Commands, kein Add Cash, keine künstliche Maschineninstallation und kein Zeitsprung für diese Bedienpfade.

LOCALAPPDATA wurde ausschließlich für den Testprozess auf `artifacts/dev3/native` gesetzt. Darin lag absichtlich `Production Zero/saves/company.sqlite` mit Schema 999, $999.999.999, Level 99 und einer fremden MK99-Karte. Daneben war anfangs kein Industriova-Save vorhanden. Die EXE erzeugte ausschließlich `Industriova/saves/company.sqlite` mit den normalen Startwerten. Die SQLite-Daten wurden zur Beweissicherung ausschließlich lesend geprüft.

| Nr. | Bedienpfad | Beobachtung |
|---|---|---|
| 1 | Frischer Start | $1.250, Level 1, XP 0, Bestand 303, keine installierten Maschinen. |
| 2 | Resources öffnen | Board und vorher sichtbare gesperrte Kaufplätze vorhanden. |
| 3 | Starter einsetzen | Build Slot → Extractor → Iron Ore; Maschine sichtbar, später RUNNING. |
| 4 | Energy-Starter | Solar Array eingesetzt, 20 MW verfügbar; Resources versorgt. |
| 5 | Factory-Starter | Processor eingesetzt, Iron-Rezept gewählt, RUNNING; Overlay zeigt tatsächlich produziertes Iron. |
| 6 | Direktkauf / Auto-Platzierung | Common Supply → Processor für $275; zweiter Processor sichtbar in Hall 1, Belegung 2/6. |
| 7 | Grüner Karten-Upgrade-Button | Solar MK1 → Bestätigung $180 → MK2 sichtbar, Energie erhöht. |
| 8 | Pause / Resume | Plant-Header PAUSE: Solar PAUSED, Versorgung 0; RESUME: wieder ONLINE. |
| 9 | Gebäudewahl / Kauf | Build Site zeigt drei Typen ohne Vorwahl, BUY zunächst inaktiv; Drilling Field ausgewählt und für $1.000 gekauft. |
| 10 | Direktes Umbenennen | Klick auf Headernamen, Name „Dev3 Testfeld“ gespeichert; Header und Liste aktualisiert. |
| 11 | Kauf / Verkauf | Preis- und Mengen-Kaufdialog bestätigt; Extractor über Rechtsklick-Menü und Verkaufsbestätigung für $272 verkauft. |
| 12 | Ressourcen-Overlay | Hellblauen Button geöffnet; Bestände und Produktionsraten sichtbar; am Header verschoben und mit CLOSE geschlossen. |
| 13 | Manuelle Contracts | Regular-Produkt 1 Iron und Produkt 2 Iron Ore einzeln gewählt; erst danach ACCEPT aktiv, Vertrag angenommen. Daily/Weekly nicht automatisch befüllt. |
| 14 | Speichern | Dev SAVE GAME bestätigt Industriova-Unterpfad; SQLite-Snapshot und manuelle JSON vorhanden. |
| 15 | Regulär schließen | Fenster regulär beendet, Exitcode 0, keine stderr-Ausgabe. |
| 16 | Neu starten / Laden | $67, beide Processor, Solar-Upgrade, Gebäude und Name erhalten; sichtbare Factory-Belegung stimmt mit gespeicherten Daten überein. |

Zusätzlich im zweiten EXE-Lauf NEW GAME bestätigt: sofort $1.250, XP 0, Bestand 303, Factory 0/6 und keine alten Karten im Board. Regulär geschlossen und drittes Mal gestartet: gleicher frischer Zustand, kein Zurückschreiben des alten Autosaves. Danach LOAD GAME aus der zuvor manuell angelegten Industriova-JSON: gespielter Zustand samt sichtbaren Processors wiederhergestellt. Auch dritter Lauf regulär mit Exitcode 0 beendet. Alle drei stderr-Dateien leer, SQLite-Integrität jeweils `ok`.

57 protokollierte native Eingabeaktionen: `artifacts/dev3/native/actions.json`; Zustandsnachweise: `fresh-start.json`, `played-before-close.json`, `restarted-2.json`, `new-game-exe.json`, `fresh-restarted-3.json`, `manual-loaded-3.json`, `final-closed.json`. Legacy-SHA256 vor und nach sämtlichen Schritten unverändert: `ad42b8820306e840ac36f5f4e4d4cca7980e60af0fc67a71dde120752a4a7b2d`.

## 6. Übernommener UI-Polish

Der vollständige bestehende Polish-Stand ist enthalten: keine lange Massenaktionsleiste; grüner MK-Kartenknopf; kompakte PAUSE/RESUME-Header; Umbenennen per Namen und Gebäudeverkauf per Rechtsklick links; industrielle Kauf-/Verkaufsdialoge und Typografie; runde Masken gegen schwarze Eckflächen; hellblauer Resources-Button und verschiebbares Overlay; manuelle Contract-Produkte; drei Build-Site- und vier Build-Facility-Typen.

Die obige native Prüfung bestätigt die dort konkret bedienten Funktionen. Gebäudeverkauf und vier Freight-Typen wurden in diesem EXE-Durchlauf nicht zusätzlich gekauft; sie sind durch die bestehenden UI-Regressionstests und den Vergleich des tatsächlich eingebetteten Codes abgesichert. Es wird keine zusätzliche native Einzelabnahme dieser beiden Pfade behauptet.

Der Paketprüfer vergleicht die normalisierten kompilierten Codeobjekte von **25 relevanten Modulen einschließlich App-Einstieg** mit dem aktuellen Quellstand: Pfade, Save-/New-Game-Ansichten, Boards, Dialoge, MaterialFrame, Resources, UI-Polish und relevante Core-Module stimmen überein. Dadurch ist insbesondere ausgeschlossen, dass wieder nur ein älterer dev2-Stand verteilt wird.

## 7. Paket und Prüfsumme

**Exakter ZIP-Pfad:**

`dist\playtest\Industriova-0.2.0-dev3-Windows-Playtest.zip`

**SHA256:** `f6fda211eb8c99f1e27ff25ef313dd30430a24b94dfe1c7567b4a981473b14d7`

Größe: **172.689.305 Bytes**. ZIP: 594 Einträge, vollständige CRC-Prüfung bestanden. Enthält Windows-EXE, erforderliche Python-/Qt-Bibliotheken einschließlich Windows-Plattformplugin, LIESMICH und **alle 353 Ressourcenbilder**. Keine SQLite-Dateien, Save-Verzeichnisse oder persönlichen Spielstände im Paket. ProductName Industriova, ProductVersion und FileVersion **0.2.0.dev3**, FileDescription „Industriova Development Playtest“.

Build-Log: `artifacts/dev3/build.txt`; Paketnachweis: `artifacts/dev3/package-verification.json`; erneuter Abschlussaudit erfolgreich. Die alte dev2-ZIP und alte EXE sind anhand ihrer bisherigen SHA256-Werte unverändert. Die Buildroutine verwendet einen getrennten dev3-Ausgabeordner und verweigert unbeabsichtigtes Überschreiben bereits vorhandener dev3-Ausgaben.

## 8. Sicherer frischer Playtest

ZIP vollständig in einen eigenen Ordner entpacken und `Industriova/Industriova.exe` starten. Vorhandene Production-Zero-Saves müssen nicht gelöscht werden und werden nicht übernommen. Ohne Industriova-Save startet automatisch die neue Firma mit den oben dokumentierten Werten. Bei einem bereits vorhandenen gültigen Industriova-Save wird dieser bewusst weitergeladen. Für einen erneuten frischen Start bietet der Dev-Tab NEW GAME mit Bestätigung; eine gewünschte manuelle Sicherung vorher über SAVE GAME anlegen.

## 9. Offene Punkte / Grenzen der Abnahme

Kein offener kritischer Save- oder New-Game-Fehler in den ausgeführten Prüfungen. Ein menschlicher Langzeitplaytest und weitere Windows-Auflösungs-/DPI-Konfigurationen sind damit nicht vorweggenommen. Der native Ablauf erfolgte überwiegend maximiert; bei der bisherigen kleinen Standardfensterbreite ist der lange Mining-Headername weiterhin gekürzt. Das ist dokumentiertes vorhandenes Layoutverhalten, keine Save-Abweichung und wurde im gezielten Auftrag nicht umgestaltet.

Die native Bedienprüfung wurde mit der Computer-Use-Skill durchgeführt: `<USER_HOME>/.codex/plugins/cache/openai-bundled/computer-use/26.1013.40934/skills/computer-use/SKILL.md`.
