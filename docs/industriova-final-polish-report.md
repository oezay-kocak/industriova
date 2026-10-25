# Industriova 0.2.0.dev5 — Final Micro Polish

Stand: 19.10.2026. Entwicklungs-Playtest; menschliche Abnahme ausstehend.

## Umfang und Sicherung

Umgesetzt sind die drei beauftragten Anpassungen: acht Positionen pro Freight-Linie, kompaktere Contract-Produktflächen mit stärkeren Mengen/Rewards/Aktionsbuttons sowie Produkticons in Research-Infoboxen. Bestehende Materialien und Komponenten werden weiterverwendet. Keine neue Spielmechanik und kein großes Refactoring.

Nach ausdrücklicher Klarstellung des Nutzers werden ältere Testspielstände für dev5 nicht automatisch berücksichtigt. dev5 verwendet einen getrennten Speicherordner. Auf den anschließenden Wunsch des Nutzers liefen die abschließenden Tests, Screenshots und die Windows-EXE-Startprüfung **headless**; kein sichtbarer nativer Spielpfad wurde für diesen Durchlauf automatisiert.

Vor den Änderungen wurden 756 vorhandene Dateien einschließlich uncommitteter Quellen, Tests, Skripte und Dokumentation gesichert:

`artifacts/final-polish/20261019T162014Z/working-tree.zip`

Backup-SHA256: `079a07cadc25b288ae35c353c8a7ed45380e1d83cff01d35e450369338eed305`. Das zugehörige `manifest.json` enthält die Dateiprüfsummen. Vergleichsaufnahmen verwenden die darin gesicherten dev4-Quellen. Ältere Builds und persönliche Spielstände bleiben erhalten.

## 1. Freight: acht Positionen pro Linie

Alle vier Facility-Typen verwenden nun acht Slotpositionen je Linie: Fleet, Rail Line, Air Route und Shipping Line. Die anfänglich verfügbaren Slots bleiben drei in der Garage und zwei bei den anderen Typen. Die weiteren Positionen sind gesperrte, bepreiste Vorschauen. Nur der nächste Slot ist freischaltbar.

Erst nach Freischaltung aller acht Slotpositionen kann die nächste Linie gekauft werden. Wie bisher kauft deren Unlock den ersten zusätzlichen Slot dieser Linie. Die Vorschau des nächsten Linienbuttons zeigt bereits den Preis dieser zukünftigen Position; sie erhält nicht mehr den Index oder Preis des noch ausstehenden Slots in der aktuellen Linie.

Die Freight-Kostenkurve bleibt unverändert **300 × Erweiterungsnummer²**. Auch Facility-Startkosten, Fahrzeuge, Kapazitäten und Transportzeiten bleiben unverändert. Bestehende Simulation, Pause, Gruppenauswahl und bezahlte Vorlagen wurden nicht neu implementiert.

Die vorhandenen 166×264-Karten bleiben erhalten. Bei 1920×1080 passen acht Karten nebeneinander; bei schmaleren Fenstern bricht das bestehende Raster um und bleibt vertikal scrollbar. Es werden acht Positionen angeboten, ohne Karten zu verzerren oder rechts abzuschneiden. Alle vier Typen sind in sämtlichen Zielgrößen erfasst und funktional bis zur nächsten Linie geprüft.

## 2. Contracts: kompaktere Produkte, stärkere Aktionen

Das Drei-Spalten-Layout und die vollständige manuelle Produktauswahl bleiben erhalten. Die Produkt-/Requirement-Fläche verwendet ungefähr die halbe bisherige Höhe. Icon, Name und Menge stehen als zusammenhängende Gruppe; Textflächen behalten ihre volle verfügbare Breite.

| Logische Fenstergröße | Produktbereich dev4 | Produktbereich dev5 | Anteil |
|---|---:|---:|---:|
| 1366×768 | 302 px | 154 px | 51,0 % |
| 1600×980 | 462 px | 234 px | 50,6 % |
| 1920×1080 | 562 px | 284 px | 50,5 % |

Die benötigten Mengen verwenden 22 px und kräftige Schrift. Die bestehenden Cash-/XP-/RP-Badges nehmen den frei werdenden Bereich ein; Rewardzahlen verwenden 24 px, Kategorien 16 px. Die Aktionsbuttons sind mindestens 60 px hoch und verwenden 20 px kräftige Beschriftung. Das gilt konsistent für Regular, Daily und Weekly sowie deren aktive Karten. Ressourcenbilder behalten ihr Seitenverhältnis.

Die Vorher-/Nachher-Messwerte gelten für denselben isolierten QA-Zustand; bei 200 % Qt-Skalierung bleiben die logischen Proportionen gleich. Keine Contract-Formel, keine Belohnungsberechnung und keine automatische Vorbelegung wurde geändert. Produktauswahl und tatsächliche Annahme aller drei Kategorien werden über Qt-Widgets geprüft.

## 3. Research: Produkticons

Jeder Eintrag der bestehenden kanonischen Produktliste erhält links ein 28×28-Icon aus `ResourceIconWidget`. Der vorhandene Vektor-Fallback greift, wenn ein Rasterbild fehlt. Icon und Text stehen in einer gemeinsamen horizontalen Zeile; die bestehenden Spalten und der interne Scrollbereich bleiben erhalten.

Die größte Kategorie Metals & Metallurgy mit 64 Produkten ist weiterhin innerhalb der Fenstergrenzen. Geprüft sind die Zuordnung aller Icons zu ihren Produktkennungen, Trennung von Bild und Text, internes Scrollen und das Rendern bei absichtlich deaktivierten Rasterbildern. Research-Daten, Boni und Zuordnungen sind unverändert.

## Frischer dev5-Testspeicher

Automatischer Save:

`%LOCALAPPDATA%\Industriova\playtests\dev5\saves\company.sqlite`, Slot `company`.

Manueller Dev-Save:

`%LOCALAPPDATA%\Industriova\playtests\dev5\saves\dev\dev_save.json`.

Der normale Start übernimmt weder `%LOCALAPPDATA%\Industriova\saves` aus dev3/dev4 noch Production-Zero-Altpfade. Alte Dateien werden nicht gelöscht. Innerhalb von dev5 funktionieren Autosave, manueller Save, Load und New Game weiterhin. Ein erster dev5-Start benötigt deshalb keine vorherige manuelle Spielstandlöschung.

Das bestehende State-Schema bleibt **6**. Die schon vorhandene `line_capacity` speichert bei neuen Facilities den Wert 8; kein neues Persistenzmodell ist erforderlich. Serializer, SessionWriter und Dev-SaveStore bleiben unverändert. Die automatische Übernahme alter Spielstände ist ausdrücklich kein Ziel dieses Testbuilds.

## Betroffene Dateien

Produktivcode unter `src/production_zero/`:

- `core/freight.py`: Standardkapazität der Linien auf acht Positionen.
- `ui/freight_view.py`: Vorschauen für sämtliche noch ausstehenden Positionen der aktuellen Linie.
- `ui/freight_lines.py`: korrekter Index und Preis der zukünftigen Linienfreischaltung.
- `ui/contracts_view.py`: Gewichtung von Produkten und Rewards, größere Badges und Aktionsbuttons.
- `ui/contract_product.py`: größere Mengenanzeige und zusammenhängende vertikale Anordnung mit voller Textbreite.
- `ui/research_hover.py`: Icons aus der vorhandenen Ressourcenkomponente.
- `persistence/paths.py`: getrennter dev5-Testspeicher gemäß Nutzerklarstellung.
- `config.py`: Version `0.2.0.dev5`.

Build-/QA-Dateien: `pyproject.toml`, `scripts/build_windows_alpha.ps1`, `scripts/industriova_version.txt`, `scripts/playtest_LIESMICH.txt`; neue Skripte `capture_final_polish.py`, `audit_final_polish.py`, `verify_final_polish_package.py` und `smoke_final_polish_headless.py`.

Neue Tests: `tests/test_final_micro_polish.py`. Bestehende Erwartungen in `test_factory_ui.py`, `test_paid_templates.py`, `test_unified_production_ux.py`, `test_ui_interaction_recovery.py`, `test_dev_save_store.py` und `test_industriova_save_reset.py` berücksichtigen acht Positionen beziehungsweise den ausdrücklich neuen Speicherpfad. Keine Testfunktion wurde entfernt oder deaktiviert.

## Headless-Prüfung und Nachweise

Alle Qt-Läufe verwenden `QT_QPA_PLATFORM=offscreen`.

| Prüfung | Ergebnis / Nachweis unter `artifacts/final-polish/` |
|---|---|
| Gesamte Testsuite | **1.242 bestanden, 79 Module, 0 Fehler, 0 übersprungen**; `regression-verified/results.json` und einzelne JUnit-/Textdateien |
| Neue Regressionen | 11 Fälle: vier Facility-Typen, drei Contract-Größen, drei Research-Größen, Isolation alter Saves |
| Gezielte funktionale Regression | 68 Fälle bestanden: neue Micro-Tests, bezahlte Vorlagen, Interaktionswiederherstellung und Unified UX |
| 200-%-Prüfung | 11 neue Fälle bestanden; `dpi2-verified-tests.txt` |
| Bestands-/Wirtschaftsvergleich | `source-audit.json`: alle bisherigen 1.231 Fälle in 78 Modulen erhalten; 22 geschützte Quelldateien sowie 376 Asset-/Datendateien unverändert; Freight-Preis- und Simulationsfunktionen ebenfalls unverändert |
| Windows-Paket | `package-verification.json`: ZIP-CRC, Ressourcen, Version, keine persönlichen Saves und geprüfte kompilierte Module |
| Gepackte Windows-EXE headless | `headless-exe-verified/verification.json`: Initialisierung des frischen dev5-Saves, acht Starterkarten, acht Freight-Positionen pro Linie, SQLite-Integrität und ignorierter synthetischer dev4-Save |

Die EXE-Startprüfung verwendet eine isolierte Testumgebung mit einem absichtlich ungültigen synthetischen dev4-Save. Der neue Save muss mit 1.250 Cash, acht unplatzierten Starterkarten und Schema 6 initialisiert werden. Die Startprüfung wartet auf den regulären ersten 30-Sekunden-Autosave; sie verlangt keine sofortige Speicherung während der Initialisierung. Nach der Startprüfung wird der eigene headless Testprozess gezielt beendet. Dies ist ausdrücklich kein Test des normalen Schließens über ein sichtbares Windows-Fenster. Reguläres Save/Load und New Game werden durch die Qt-Regressionsfälle abgedeckt.

## Visuelle Prüfung

Die Aufnahmen stammen aus echten Qt-Widgets, headless mit geladenen vorhandenen Windows-Schriftarten. Es sind isolierte QA-Fixtures, keine vorgetäuschten nativen Spielsitzungen.

Geprüft: **1366×768, 1600×980 und 1920×1080**, jeweils **100 % und 200 % Qt-Skalierung**. Die Rasterabmessungen bei 200 % sind entsprechend doppelt so groß. Persönliche Windows-Anzeigeeinstellungen wurden nicht verändert.

Vorher-/Nachher-Verzeichnisse: `artifacts/final-polish/before/dpi1`, `before/dpi2`, `after/dpi1`, `after/dpi2`. Jeder Satz enthält alle vier Freight-Typen, Contracts und die größte Research-Infobox in allen drei Größen; zusätzlich ausgewählte und aktive Contract-Karten.

- [Freight vorher/nachher](../artifacts/final-polish/comparison-freight.png)
- [Contracts vorher/nachher](../artifacts/final-polish/comparison-contracts.png)
- [Research vorher/nachher](../artifacts/final-polish/comparison-research.png)
- [Acht Freight-Positionen bei 1920×1080](../artifacts/final-polish/after/dpi1/freight-garage_depot-1920x1080.png)
- [Contracts mit gewählten Produkten](../artifacts/final-polish/after/dpi1/contracts-selected-1920x1080.png)
- [Aktive Contracts](../artifacts/final-polish/after/dpi1/contracts-active-1920x1080.png)
- [Research-Icons bei 1366×768](../artifacts/final-polish/after/dpi1/research-panel-1366x768.png)
- [Research-Icons bei 200 %](../artifacts/final-polish/after/dpi2/research-panel-1366x768.png)

Bei der Prüfung wurde eine durch Zentrierung zu schmale Textgruppe erkannt und vor Abschluss korrigiert. Die zusätzliche Regression prüft jetzt ausdrücklich die volle verfügbare Breite der Namens- und Mengenlabels nach Produktauswahl. Die finalen Screenshots stammen aus dem korrigierten Stand.

## Build und offene Punkte

Geprüfte finale Ausgabe nach erfolgreicher Gesamtprüfung:

- Version: **0.2.0.dev5 — Industriova Development Playtest**.
- EXE: `dist/playtest/dev5/Industriova/Industriova.exe`.
- ZIP: `dist/playtest/Industriova-0.2.0-dev5-Windows-Playtest.zip`.
- ZIP-Größe: **174,255,928 Bytes**.
- SHA256: `e11772de275ca0b83e97491104efdbee74ccfffff39dbde29a7caf8670920d5f`.
- ZIP-CRC: ok; 594 Einträge, 353 Ressourcenbilder, 0 enthaltene persönliche Spielstände.
- 37 geprüfte kompilierte Module einschließlich Programmeinstieg stimmen mit den getesteten Quellen überein.
- Headless-EXE-Start: bestanden; erster regulärer Autosave und SQLite-Integrität geprüft, stderr leer.

dev4 bleibt unverändert erhalten; dessen ZIP-SHA256 ist weiterhin `883eeb2abd509087c2ebb8399513c4574f5c7bc7d7ba4af643309877bb801fee`.

Offen bleibt die menschliche Gameplay-/Designabnahme, einschließlich realer Monitor-/Windows-DPI-Wechsel. Ein sichtbarer nativer Start wurde auf ausdrücklichen Wunsch durch den headless Windows-EXE-Start ersetzt. Es wurden keine weitergehenden Systeme oder Balancing-Anpassungen vorgenommen.
