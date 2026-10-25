# Industriova 0.2.0.dev6 — Final UI Approval Pass

Stand: 19.10.2026. Entwicklungs-Playtest, menschliche Abnahme ausstehend.

## Änderungen

**Contracts:** Der Hinweis auf fehlende geeignete Produkte ist jetzt 20 px groß, kräftig und innerhalb der verfügbaren Fläche horizontal/vertikal zentriert. Cash-, XP- und RP-Kategorie und Wert stehen mit einem festen Abstand als gemeinsame zentrierte Einheit in ihrer jeweiligen Box. Auswahl, Annahme, Angebote und Belohnungsberechnung bleiben unverändert.

**Freight:** Scrollbereich, Viewport, Inhalt und Raster verwenden die transparente Oberflächenbehandlung der vorhandenen Production Boards. Der alte dunkle Hintergrundkasten und dessen sichtbare Ecke hinter Fleet 01 sind entfernt. Ursache war die eigene deckende Hintergrunddarstellung der Scroll-/Inhaltsflächen. Im dev5-Vergleich zeichnen diese am untersuchten Eckpunkt RGBA `(8,13,17,255)`, in dev6 `(0,0,0,0)`; die vorhandene Board-Materialfläche scheint korrekt durch. Karten, acht Positionen je Linie, Freischaltkosten, Pause, Routen und Vorlagen sind unverändert.

**Resources / Factory / Energy:** Alle bereits freigeschalteten Linien bleiben sichtbar. Zusätzlich wird genau die erste noch gesperrte Erweiterung angezeigt. Nach dem Kauf erscheint deren Nachfolger; nach der letzten Freischaltung gibt es keinen weiteren Erweiterungsblock. Die vollständige Linienliste mit allen Kosten bleibt im GameState erhalten. Der einzelne kompakte Block verwendet dieselbe Linienplakette, den neutralen Track-Rahmen, Idle-Indikator und die vorhandenen Unlock-Buttons wie Freight. Die zusätzliche große EXPANSION-Überschrift entfällt.

Es wurden keine Core-, Balancing-, MK-/Rarity-, Contract-, Freight-Simulations-, Research-, Pause- oder Copy/Paste-Befehle geändert. Die bestehenden Karten- und allgemeinen Button-Komponenten bleiben erhalten.

## Sicherung und frischer dev6-Start

Vor den Änderungen wurden **762 Dateien** einschließlich aller vorhandenen uncommitteten Quellen, Tests, Skripte und Dokumentation gesichert:

`artifacts/final-ui-approval/20261019T165458Z/working-tree.zip`

Backup-SHA256: `96a26e9cb9614a6c7d2930b82df90d8bb197f3eb269a7e6ff23c7b6afb2ebd6a`. Die Dateiprüfsummen stehen in `manifest.json` daneben. Die Vergleichsaufnahmen verwenden ausschließlich die daraus extrahierten dev5-Quellen. Vorhandene Änderungen und ältere Builds wurden erhalten.

Auf ausdrücklichen Nutzerwunsch startet dev6 in einem getrennten Testspeicher:

- Autosave: `%LOCALAPPDATA%\Industriova\playtests\dev6\saves\company.sqlite`, Slot `company`.
- Manueller Dev-Save: `%LOCALAPPDATA%\Industriova\playtests\dev6\saves\dev\dev_save.json`.

dev5-Saves sowie ältere Industriova-/Production-Zero-Verzeichnisse werden nicht automatisch geladen. Persönliche Originaldateien wurden weder verändert noch gelöscht. Innerhalb dev6 bleiben Save/Load und New Game erhalten. Serializer, Schema 6, SessionWriter und manuelles Saveformat sind unverändert; nur der Standard-Speicherordner ist für diesen neuen Testbuild getrennt.

## Betroffene Dateien

Produktivcode unter `src/production_zero/`:

- `ui/contracts_view.py`: Hinweis- und Reward-Ausrichtung.
- `ui/freight_lines.py`: transparente Scroll-/Inhaltsflächen; keine Änderung an der Linien- oder Kaufberechnung.
- `ui/factory_view_v2.py`: ein nächster Erweiterungsblock und dessen kompakte Darstellung.
- `persistence/paths.py`: separater dev6-Testordner.
- `config.py`: Versionsnummer dev6.

Build-Unterlagen: `pyproject.toml`, `scripts/build_windows_alpha.ps1`, `scripts/industriova_version.txt`, `scripts/playtest_LIESMICH.txt`.

Neue QA-Dateien: `tests/test_final_ui_approval.py`, `scripts/capture_ui_approval.py`, `scripts/audit_ui_approval.py`, `scripts/verify_ui_approval_package.py`, `scripts/smoke_ui_approval_headless.py`.

Bestehende Tests für die frühere EXPANSION-Überschrift beziehungsweise deren Painter wurden an die ausdrücklich gewünschte gemeinsame Linienplakette angepasst. Speicherpfad-Erwartungen verwenden dev6. Keine bestehende Testfunktion wurde entfernt oder deaktiviert.

## Headless-Prüfung

Auf den fortgeltenden Nutzerwunsch liefen alle Prüfungen mit `QT_QPA_PLATFORM=offscreen`. Es wurde kein sichtbares Spiel-/Testfenster automatisiert.

| Prüfung | Ergebnis / Nachweis unter `artifacts/final-ui-approval/` |
|---|---|
| Gesamte bestehende und neue Suite | **1.257 bestanden, 80 Module, 0 Fehler, 0 übersprungen**; `regression-verified/results.json` und einzelne Text-/JUnit-Berichte |
| Gezielter UI-Lauf | **43 bestanden**, einschließlich aller 15 neuen Fälle und bestehender Production-Board-Tests; `targeted-final-tests.txt` |
| Neue UI-Fälle bei 200 % | **15 bestanden**; `dpi2-tests.txt` |
| Hintergrundnachweis | `freight-background-before.json`, `freight-background-after.json`, zusätzliche Pixelassertionen bei drei Auflösungen |
| Quell-/Bestandsvergleich | `source-audit.json`: 431 geschützte Dateien einschließlich sämtlicher 41 Core-Dateien unverändert; vorhandene Karten-/Track-Klassen ebenfalls unverändert; alle bisherigen 1.242 Fälle in 79 Modulen erhalten |
| Windows-Paket | `package-verification.json`: Version, CRC, Ressourcen, keine Saves, kompilierte Module im Vergleich zu den geprüften Quellen |
| Headless Windows-EXE | `headless-exe-verified/verification.json`: frischer dev6-Save, ignorierte synthetische ältere Saves, SQLite-Integrität und stabiler Start |

Die neuen 15 Fälle prüfen:

- Neun echte Qt-Klickpfade: Resources, Factory und Energy jeweils bei drei Größen. Immer genau ein nächster Block, korrekter Preis und Geldabzug, danach korrekter Nachfolger bis zur letzten Freischaltung; alle ursprünglichen Linienkennungen und Kosten bleiben erhalten.
- Drei Contract-Layoutfälle: großer zentrierter Weekly-Hinweis, zusammenhängende mittige Kategorie-/Wert-Paare und erhaltene manuelle Auswahl.
- Drei Freight-Fälle: transparente gerenderte Ecken ohne Alt-Hintergrund, unveränderte acht sichtbare Positionen und drei anfangs verfügbare Garage-Slots.

Auswahl und tatsächliche Annahme aller Contract-Typen, Save/Load, New Game, Produktionsketten, Pause, bezahlte Vorlagen und Freight-Interaktionen laufen zusätzlich in der vollständigen bestehenden Suite mit.

Die gepackte EXE wird auf Windows headless mit einem isolierten `LOCALAPPDATA` gestartet. Die Prüfung wartet auf den regulären ersten 30-Sekunden-Autosave und kontrolliert 1.250 Cash, acht unplatzierte Starterkarten, Schema 6 und acht Freight-Positionen je Linie. Anschließend wird ausschließlich der eigene Testprozess gezielt beendet. Dies ersetzt auf Nutzerwunsch einen sichtbaren nativen Start; es ist kein Test des normalen Schließens über das Windows-Fenster.

## Screenshots und visueller Vergleich

Echte Qt-Widget-Aufnahmen wurden für **1366×768, 1600×980 und 1920×1080** bei **100 % und 200 % Qt-Skalierung** erstellt. Bei 200 % verdoppeln sich die Rasterabmessungen. Persönliche Windows-Anzeigeeinstellungen wurden nicht geändert.

Vorher-/Nachher-Dateien: `artifacts/final-ui-approval/before/dpi1`, `before/dpi2`, `after/dpi1`, `after/dpi2`. Die neuen Aufnahmen umfassen alle fünf angefragten Bereiche bei allen Kombinationen sowie die drei Produktionsboards jeweils am Scrollende: insgesamt **48 Nachher-Aufnahmen** und entsprechende Vergleichsaufnahmen.

- [Contracts vorher/nachher](../artifacts/final-ui-approval/comparison-contracts.png)
- [Freight vorher/nachher](../artifacts/final-ui-approval/comparison-freight.png)
- [Expansion vorher/nachher](../artifacts/final-ui-approval/comparison-expansion.png)
- [Contracts bei 1366×768](../artifacts/final-ui-approval/after/dpi1/contracts-1366x768.png)
- [Freight bei 1920×1080](../artifacts/final-ui-approval/after/dpi1/freight-1920x1080.png)
- [Factory: nächste Erweiterung bei 1366×768](../artifacts/final-ui-approval/after/dpi1/factory-expansion-1366x768.png)
- [Resources: nächste Erweiterung](../artifacts/final-ui-approval/after/dpi1/resources-expansion-1366x768.png)
- [Energy: nächste Erweiterung](../artifacts/final-ui-approval/after/dpi1/energy-expansion-1366x768.png)
- [Contracts bei 200 %](../artifacts/final-ui-approval/after/dpi2/contracts-1366x768.png)

Die Aufnahmen verwenden isolierte QA-Zustände und die vorhandenen Schriftarten. Sie sind headless gerenderte echte Widgets, keine behaupteten nativen Spielsitzungen.

## Build und Restpunkte

Finale Ausgabe nach erfolgreicher Prüfung:

- Version: **0.2.0.dev6 — Industriova Development Playtest**.
- EXE: `dist/playtest/dev6/Industriova/Industriova.exe`.
- ZIP: `dist/playtest/Industriova-0.2.0-dev6-Windows-Playtest.zip`.
- ZIP-Größe: **174,255,833 Bytes**.
- SHA256: `04d4d0171250d56f11d7767cefbecaa4a097b0f79d44952c2945cf5b4b0ba50b`.
- Paketprüfung: ZIP-CRC ok, 594 Einträge, 353 Ressourcenbilder, 0 persönliche Saves.
- 37 geprüfte kompilierte Module einschließlich Einstieg stimmen mit den getesteten Quellen überein.
- Windows-EXE-Start headless bestanden: frischer dev6-Autosave, SQLite-Integrität ok, ältere synthetische Saves ignoriert, stderr leer.

dev5 bleibt erhalten, dessen ZIP-SHA256 weiterhin `e11772de275ca0b83e97491104efdbee74ccfffff39dbde29a7caf8670920d5f`.

Die menschliche Gameplay-/Designabnahme und reale Windows-Monitor-/DPI-Wechsel bleiben ausstehend. Der Build bleibt ausdrücklich ein Entwicklungs-Playtest. Über den beauftragten UI-Umfang und die ausdrücklich gewünschte Save-Isolation hinaus wurden keine Systeme umgebaut.
