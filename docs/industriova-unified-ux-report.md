# Industriova 0.2.0.dev4 — Unified Production UX

Stand: 19.10.2026. Entwicklungs-Playtest, menschliche Abnahme ausstehend.

## Ergebnis und Sicherung

Alle Abschnitte A–F sind implementiert und geprüft. Der abschließende vollständige Lauf besteht mit **1.231 Tests in 78 Modulen**, ohne Fehler oder übersprungene Fälle. Die bisherigen **1.200 Fälle in 76 Modulen** bleiben erhalten; 31 Fälle kommen hinzu. Zusätzlich bestehen die 20 neuen UI-Fälle bei 200 % Qt-Skalierung. Die Windows-EXE wurde nach dem erfolgreichen Gesamtlauf gebaut und anschließend nativ mit frischem und gespeichertem Teststand gestartet.

Vor den Änderungen wurden 745 vorhandene Dateien einschließlich uncommitteter Quellen, Tests, Skripte und Dokumentation gesichert:

- `artifacts/unified-ux/20261019T142502Z/working-tree.zip`
- SHA256: `3dc39795e27c4685a6e9e8593f013e08c8d8ed5826dc0e5a5fa8d35b3e2a6bec`
- Dateiprüfsummen: `manifest.json` im selben Verzeichnis.

Die Vergleichsquellen stammen ausschließlich aus dieser Sicherung. Vorhandene Änderungen wurden erhalten. Keine persönlichen AppData-Spielstände wurden verändert oder gelöscht. Die nativen Spieltests verwenden isolierte `LOCALAPPDATA`-Verzeichnisse innerhalb `artifacts/unified-ux`.

Gelesene Grundlagen: `docs/industriova-ui-polish-report.md`, `docs/industriova-dev3-build-report.md`, vorhandene Production-/Freight-Komponenten und akzeptierte Projekt-/Nutzerreferenzen. Die im aktuellen Auftrag erwähnten fünf neuen Screenshots lagen diesem Textanhang nicht zusätzlich bei. Vergleichsbasis sind die bereits vorhandenen Referenzen und echte Vorher-Aufnahmen des gesicherten dev3-Stands.

## A. Scrolling, Sprache und visueller Polish

**Expansion-Scrolling:** Die Qt-Regel für `lockedLinePanel` begrenzte dessen Höhe weiterhin auf 58 Pixel. Die bisherige Aufhebung mit `max-height: none` ist keine gültige Qt-Aufhebung. Zusammen mit einer zu kleinen Content-Geometrie blieb der unterste Unlock-Button selbst am Scrollende teilweise verdeckt. Die Regel verwendet jetzt einen gültigen großen Pixelwert; die tatsächliche Mindesthöhe ergibt sich aus den Kindern, Abständen und 14 Pixeln unterem Innenabstand. Bestehende Scrollpositionserhaltung bleibt aktiv. Resources, Factory und Energy sind jeweils in allen drei Zielgrößen mit vollständig sichtbarem letzten Unlock-Button und unveränderter Scrollposition während Runtime-Updates geprüft.

**Sprache:** Aktive deutsche Dialog-, Kauf-, Verkaufs-, Auswahl- und Bestätigungstexte in den betroffenen UI-Modulen sind Englisch. Interne Kennungen, Speicherpfade und historische Dokumente wurden dafür nicht umbenannt. Die systematische Suche umfasste auch Research, Contracts und Dev-Ansichten.

**Machine Actions:** Rezept, Pause/Fortsetzen, Copy/Paste und gleichartige aktive Aktionen verwenden vorhandene gelbe GameButtons mit kräftiger schwarzer Beschriftung. Nicht verfügbare Aktionen bleiben deaktiviert sichtbar; Sell und Cancel bleiben rot.

**Contracts:** Die drei bestehenden Spalten bleiben erhalten. ContractCards und Produktflächen nutzen die verfügbare Höhe; Belohnungsanzeigen, Produktnamen und Mengen sind größer. Produktbilder werden mit erhaltenem Seitenverhältnis gezeichnet. Manuelle Wahl, genau ein Angebot pro Kategorie, fehlende Vorbelegung und sämtliche Belohnungsformeln bleiben erhalten. Die größere Produktdarstellung ist auf persönliche Contracts beschränkt; gemeinsame Consortium-Komponenten behalten ihre bisherigen Standardgrößen.

**Build Site/Facility:** Titel und Cancel stehen in derselben oberen Zeile, die englische Beschreibung direkt darunter. Vorhandene MaterialFrames verbinden Bild, Auswahlbutton und Preis zu einer silbernen Auswahlkarte. Die erweiterten vorhandenen GameButtons sind silbern; Auswahl ist rot mit schwarzer Schrift. Buy bleibt gelb. Gebäudearten und Preise wurden nicht geändert.

## B. Unabhängige Pausenhierarchie

Neue persistierte Felder:

| Modell | Felder | Bedeutung |
|---|---|---|
| `FactoryHall` für alle drei Produktionsboards | `paused: bool` | gesamtes Gebäude |
| `ProductionLine` | `paused: bool` | einzelne Linie |
| `FreightFacility` | `paused: bool`, `paused_lines: set[int]` | Facility und einzelne Transportlinien |
| `FreightFacility` | `line_capacity: int` | dauerhaft stabile Zuordnung bestehender Slotindizes zu Linien |

Effektive Pause ist Gebäude **oder** Linie **oder** individuelle Karte. Übergeordnete Befehle überschreiben keine untergeordneten Flags. Pause ist rot, Resume gelb; pausierte Linien zeigen Idle, Karten Paused. Energieversorgung und Produktionsvorschau berücksichtigen dieselbe Hierarchie.

`PauseProductionScope` und `PauseFreightScope` validieren ihre Ziele und laufen über den vorhandenen CommandBus. Freight-Pause verhindert neue Abfahrten. Bereits gestartete Sendungen behalten ihre reservierte Menge und schließen regulär ab.

## C. Bezahlte Produktionsvorlagen

`MachineTemplate` speichert Typ und verfügbare Rezept-/Ressourcen- beziehungsweise Routenkonfiguration sowie den individuellen Pausenwunsch. Kopierte Maschinenidentität, hoher MK-Level, Rarity-Boni, Fortschritt, Investitionshistorie und laufende Sendungen werden nicht übertragen. Vorlagen sind eine flüchtige UI-Zwischenablage; gekaufte Maschinen werden normal gespeichert.

- Copy kopiert exakt die markierten Karten in visueller Linienreihenfolge. Ohne Auswahl kann die fokussierte Linie kopiert werden.
- Rechtsklick auf freien Linienhintergrund bietet Copy Line und Paste Machines.
- Ctrl+C/Ctrl+V funktionieren im fokussierten Board. Such-, Namens-, Text- und Zahlenfelder behalten ihre normale Textbearbeitung.
- Paste zeigt Anzahl, Typen, MK1/Common, benötigte und vorhandene freie Slots, Gesamtpreis und fehlende Voraussetzungen. Der Kauf braucht ausdrückliche Bestätigung.
- `PurchaseTemplates` prüft Kompatibilität, Freischaltungen, Preis, Geld und Platz erneut, bevor irgendeine Änderung erfolgt. Anschließend werden neue eindeutige Instanzen gekauft und installiert. Keine Teilkäufe bei Ablehnung.
- Preise kommen aus der bestehenden Common-Direktkaufberechnung. Neue Maschinen starten immer mit MK1/Common, eigener Anschaffungssumme und frischem Produktionszustand.

Die alten internen Konfigurationsbefehle bleiben für bestehende Aufrufer erhalten. Die neue Benutzeroberfläche verwendet die bezahlte Vorlagensemantik.

## D. Freight-Linien und gemeinsame Bedienung

Garage, Rail Depot, Air Terminal und Seaport verwenden gemeinsame Production-TrackPanels und Linienheader: Fleet, Rail Line, Air Route und Shipping Line. Die erste Linie ist verfügbar. Danach wird zuerst die nächste Linie und anschließend deren nächster Slot gekauft. Nur die tatsächlich nächste Freischaltung ist bedienbar; spätere Positionen bleiben sichtbare gesperrte Vorschauen.

Die neue Linienfreischaltung kauft den ersten zusätzlichen Slot der Linie über den bestehenden Erweiterungsbefehl. Sie führt keine zusätzliche Gebührenart ein. Die bestehende Folge **300 × Erweiterungsnummer²** bleibt erhalten: 300, 1.200, 2.700 usw. Garage gruppiert drei Slots pro Fleet, die anderen Facility-Typen zwei pro Linie. Die gespeicherte `line_capacity` schützt diese Zuordnung bei künftig veränderten Defaults. Bereits gekaufte Slots bleiben gekauft; vorhandene Fahrzeuge werden nicht neu indiziert.

Freight unterstützt Einzel-, Ctrl-/Shift- und Rahmenauswahl, sichtbare Gruppenmarkierung, Gruppenverschiebung in freie kompatible Linienplätze und einen gemeinsamen Machine-Actions-Dialog. Route/Delivery Target konfiguriert die ausgewählte Gruppe atomar; Pause, Copy/Paste und Verkauf arbeiten ebenfalls auf der Gruppe. Laufende Lieferungen schützen Fahrzeuge weiterhin vor unzulässigem Verschieben/Verkaufen. Vorlagen erzeugen bezahlte neue Fahrzeuge und kopieren keine Frachtreservierungen oder laufenden Sendungen.

## E. Research-Infoboxen

Die bestehende Maschinen-Hover-Komponente wurde erweitert. Industry-Navigation, Research-Knoten und Spezialisierungen zeigen Name, Erklärung, betroffene Produkte und aktuellen Wertbonus. Daten stammen aus `research_domains`, `research_products`, dem bestehenden Research-Katalog und den vorhandenen Modifikatoren; keine zusätzliche Branchenliste.

Die Infobox begrenzt sich auf die sichtbare Fensterfläche, verwendet je nach Breite ein bis drei Spalten und scrollt lange Listen intern. Verzögertes Ausblenden erlaubt den Wechsel vom Auslöser in die Liste. Die größte Kategorie **Metals & Metallurgy mit 64 Produkten** wurde bei allen drei Zielgrößen geprüft und unter Windows tatsächlich geöffnet und intern gescrollt.

## Zusätzlich bestätigter Darstellungsfehler

Im nativen Spielpfad wurde ein Processor vor der ersten Iron-Freischaltung installiert. Nach Erreichen der normalen Erzschwelle war das Rezept bereits anklickbar, die Karte zeigte aber weiterhin **NO RECIPE**. Ursache war der Cache in `FactoryV2MachineCard`: Verfügbarkeitsänderung und sekundärer Text fehlten in den relevanten Signaturen. `set_data` berücksichtigt jetzt Rezeptverfügbarkeit und effektiven Status; der Zeichen-Cache zusätzlich den sekundären Text.

Der neue Test `test_first_recipe_unlock_repaints_the_existing_machine_card` vergleicht echte Widget-Pixel vor und nach Freischaltung. Er scheiterte vor der Korrektur und besteht danach. Die Korrektur invalidiert die betroffene Karte ohne vollständigen Board-Neuaufbau. Sie berücksichtigt zugleich Statusänderungen durch übergeordnete Pause.

## Betroffene Dateien

| Bereich | Geänderte beziehungsweise neue Dateien unter `src/production_zero/` |
|---|---|
| Modelle/Simulation/Befehle | `core/state.py`, `core/freight.py`, `core/simulation.py`, `core/commands.py`, neu `core/production_pause.py`, neu `core/production_templates.py` |
| Persistenz | `persistence/sqlite_store.py` |
| Production UI | `ui/factory_view.py`, `ui/factory_view_v2.py`, `ui/release_board.py`, neu `ui/production_templates.py` |
| Freight UI | `ui/freight_view.py`, `ui/freight_drag.py`, `ui/release_freight.py`, neu `ui/freight_lines.py` |
| Research UI | `ui/research_view.py`, `ui/research_specialization.py`, neu `ui/research_hover.py` |
| Layout/Sprache | `ui/interaction_polish.py`, `ui/release_dialogs.py`, `ui/game_ui/widgets.py`, `ui/contracts_view.py`, `ui/contract_product.py`, `ui/theme.py`, `ui/supply_view.py` |
| Version | `config.py` |

Neue Testmodule: `tests/test_paid_templates.py` und `tests/test_unified_production_ux.py`. Bestehende UI-Erwartungen wurden in vier Modulen an die ausdrücklich neue Semantik angepasst: `test_factory_ui.py`, `test_industriova_release_ui.py`, `test_ui_interaction_recovery.py`, `test_ui_polish_interactions.py`. Keine Testfunktion entfernt, keine Fälle deaktiviert oder übersprungen. Build-/QA-Unterlagen: `pyproject.toml`, Versionsressource, Build-Skript und Playtest-Liesmich; neue Capture-, Audit- und Paketprüfungsskripte unter `scripts/`.

## F. Regression, Save/Load und Migration

| Prüfung | Ergebnis | Nachweis unter `artifacts/unified-ux/` |
|---|---|---|
| Gesamtsuite | 1.231 bestanden, 78 Module, 0 übersprungen | `regression-verified/results.json`, einzelne Text-/JUnit-Berichte |
| Bisheriger Bestand | alle 1.200 Fälle erhalten und bestanden | `source-audit.json` |
| Neue bezahlte Vorlagen/Migration | 11 Fälle bestanden | `regression-verified/test_paid_templates.txt` |
| Neue sichtbare UI-Interaktionen | 20 Fälle bestanden | `regression-verified/test_unified_production_ux.txt` |
| Dieselben UI-Fälle bei 200 % | 20 bestanden | `dpi2-final-tests.txt` |
| Native Windows-Quellversion | 53 protokollierte Schritte, echte Produktion und Käufe | `native-source/actions.json`, Screenshots |
| Gepackte EXE | frischer Start, gespeicherten Spielpfad laden, beide regulär beendet | `native-exe-visible/`, `native-source/exe-exit.txt` |
| Tatsächlicher Save nach EXE-Neustart | SQLite-Integrität ok, 10 Kartenidentitäten/MK/Rarity/Kosten unverändert, alle Slots/Linien/Pausen und Freight-Routen erhalten | `native-save-load-verification.json` |
| Paket | ZIP-CRC ok, Version dev4, 353 Ressourcenbilder, keine Spielstände, 37 geprüfte Module einschließlich Einstieg stimmen mit Quellen überein | `package-verification.json` |

Der State-Serializer steigt von Schema 5 auf **6**. Fehlende neue Pausenfelder alter Saves erhalten False beziehungsweise eine leere Menge; fehlende Freight-Linienkapazität erhält den bestehenden Facility-Startwert. Schema-5-Regression mit acht vorhandenen MK17/Rare-Fahrzeugen erhält Identitäten, Slotfolge, Routen, Geld, Bauinvestition und eine aktive Lieferung mit Menge 31 und Restzeit 47 exakt. Wiederholte Serialisierung/Deserialisierung ist stabil. Vorlagen-Save/Load und unabhängige Pausen sind separat getestet.

Die Tests decken außerdem MK50/Legendary-Vorlagen → MK1/Common, mehrere Kaufmengen, Preisänderung, fehlendes Geld/Slots, inkompatible Typen, gesperrte Rezepte, atomare Ablehnung, Kontextmenü- und Tastaturpfade, Textfeldschutz, Freight-Gruppenroute, tatsächliche Maus-Gruppenverschiebung und Research-Grenzen ab. Bestehende Produktionsketten-, Wirtschaft-, Persistenz- und Stressprüfungen liefen im Gesamtlauf mit.

Speicherpfade und Hintergrund-SaveWriter sind bytegleich zur Sicherung. Automatischer Slot bleibt `company` in `%LOCALAPPDATA%\Industriova\saves\company.sqlite`; manueller Dev-Save bleibt `saves\dev\dev_save.json`. Production-Zero-Altpfade werden durch diesen Durchlauf nicht wieder eingeführt.

## Nativer Windows-Spielpfad

Die native Bedienung erfolgte mit der Computer-Use-Skill über echte Fenster und Zeiger-/Tastaturereignisse. Für diesen Spielpfad wurden weder Geld noch Forschung, Lager oder Karten über Dev-Cheats erzeugt.

1. Isolierter frischer Start: 1.250 Cash, Level 1, XP 0, vorgesehener Bestand 303 und acht unplatzierte MK1/Common-Starterkarten.
2. Resources: Starter-Extractor einsetzen und Iron Ore wählen. Energy: Starter-Solar einsetzen. Factory: Starter-Processor einsetzen; erste Iron-Freischaltung durch reguläre Erzproduktion erreichen und Iron wählen.
3. Freight: zwei Starter-Trucks einsetzen; beide per Auswahlrahmen markieren; gemeinsamer Aktionsdialog; Iron-Ore-Market-Route auf beide anwenden. Zwei reale Sendungen starten.
4. Fleet 01 pausieren; Facility pausieren und fortsetzen. Fleet 01 bleibt pausiert; gestartete Sendungen schließen trotzdem ab.
5. Fleet 02 für 300 freischalten. Einen Truck kopieren, Ziel-Linienmenü öffnen, Quote über 205 bestätigen. Genau ein neuer MK1/Common-Truck entsteht, erhält die Route und startet seine eigene spätere Lieferung.
6. Processor auswählen, Ctrl+C/Ctrl+V: Quote über 275 bestätigen. Zweiter neuer MK1/Common-Processor erscheint mit Iron-Konfiguration; Original bleibt erhalten. Solar regulär für 180 auf MK2 ausbauen; 25 MW decken die gemeinsame Produktion.
7. Factory Line 02 separat pausieren, Halle pausieren und fortsetzen: Line 01 läuft wieder, Line 02 bleibt pausiert.
8. Contracts bleiben zunächst ohne automatische Produktwahl; Iron wird über den echten Produktpicker manuell gewählt. Research-Metals-Infobox mit 64 Produkten öffnen und intern scrollen.
9. Dev Save Game auslösen, Anwendung schließen. Der gespeicherte Teststand enthält bereits 816 regulär produzierte Iron-Einheiten.
10. Fertige dev4-EXE getrennt frisch starten: 1.250 Cash, acht Starterkarten, leere Boards, gesperrte Fleet 02 korrekt Idle. Danach die EXE mit dem zuvor durchgespielten isolierten Save starten: beide Processor sichtbar, Line-02-Pause erhalten, drei Trucks mit Routen und Fleet-01-Pause erhalten. Regulär schließen; Exitcodes jeweils 0, keine Fehlermeldungen in stderr.

## Visuelle Vergleiche und Skalierung

Echte Qt-Widget-Aufnahmen liegen unter `artifacts/unified-ux/before/dpi1`, `before/dpi2`, `after/dpi1` und `after/dpi2`. Vorher nutzt die archivierten Quellen, Nachher den abschließend getesteten Stand. Es sind gerenderte Widgets mit isolierten QA-Fixtures; diese Aufnahmen ersetzen nicht den oben separat dokumentierten nativen Spielpfad.

Jeder Satz enthält Resources, Factory, Energy, Freight und Contracts in **1366×768, 1600×980 und 1920×1080 logischer Fenstergröße**. Qt-Skalierung 2 erzeugt entsprechend doppelte Rasterabmessungen. Dialoge und Research-Hover wurden zusätzlich erfasst. Der native Windows-Spielpfad lief auf dem vorhandenen 100-%-Desktop; 200 % wurden über Qt-Skalierung geprüft, ohne die persönliche Windows-Anzeigekonfiguration zu verändern.

| Vergleich | Beobachtung |
|---|---|
| [Factory vorher/nachher](../artifacts/unified-ux/comparison-factory.png) | Vorher letzter Unlock am Scrollende verdeckt; danach vollständig sichtbar mit unterem Abstand. |
| [Freight vorher/nachher](../artifacts/unified-ux/comparison-freight.png) | Gemeinsame Linienrahmen, Fleet-Header und kompakte unabhängige Pause statt flacher Facility-Fläche. Weitere Linien sind durch Scrollen erreichbar. |
| [Contracts vorher/nachher](../artifacts/unified-ux/comparison-contracts.png) | Produkt-/Requirement-Flächen verwenden die Höhe; drei Spalten und manuelle Auswahl erhalten. |
| [Build Facility](../artifacts/unified-ux/after/dpi1/build-facility-selected.png) | Titel/Cancel ausgerichtet, zusammengehörige silberne Karten, rote Auswahl und gelber Buy. |
| [Factory bei 1366×768](../artifacts/unified-ux/after/dpi1/factory-1366x768.png) | Unterster Expansion-Button vollständig erreichbar. |
| [Contracts bei 200 %](../artifacts/unified-ux/after/dpi2/contracts-1366x768.png) | Vergrößerte Controls ohne verzerrte Ressourcenbilder. |
| [Research größte Kategorie](../artifacts/unified-ux/after/dpi1/research-largest-hover.png) | Begrenzte Infobox mit Spalten und internem Scrollen. |

Weitere echte Windows-Aufnahmen liegen in `native-source/` und `native-exe-visible/`, insbesondere Gruppenaktionen, beide Kaufbestätigungen, unabhängige Pausen und Zustand nach EXE-Neustart. Vorhandene Industriova-Materialien, Kartenrahmen, Fonts und Buttonformen wurden weiterverwendet. Keine generischen GroupBoxes oder neues Designsystem eingeführt.

## Wirtschaft und Performance

Der SHA256-Vergleich bestätigt unveränderte Dateien für Karten, Enums/Rarity, Wirtschaft, Festpreise, MK-Upgrades, Modifikatoren, Direktkauf/Supply, Progression, Produktionswerte, Release-Balance, Contracts, Infrastruktur, Research und kanonische Definitionen. Details: `source-audit.json`. Geänderte Simulation berücksichtigt zusätzliche Pausebedingungen; Freight erweitert die Scope-/Dispatch-Prüfung. Bezahlte Vorlagen und Freischaltungen verwenden vorhandene Preisfunktionen.

50 wiederholte Factory-Runtime-Refreshes pro Größe ergaben im abschließenden Capture-Lauf bei 100 % durchschnittlich **1,84 / 3,37 / 3,05 ms** (1366 / 1600 / 1920). Die archivierte Vergleichsversion lag bei **1,73 / 1,84 / 1,72 ms**. Bei 200 % liegt Nachher bei **3,14 / 2,53 / 2,79 ms**. Dies sind lokale indikative Messungen unter wechselnder paralleler Last, kein isolierter Leistungsvergleich und keine FPS-Aussage. Die zusätzlichen Scope-/Verfügbarkeitsprüfungen kosten Arbeit; die beobachteten Refreshes bleiben im einstelligen Millisekundenbereich. Messrohwerte liegen in den jeweiligen `metrics.json`.

Runtime-Updates bauen die Boards nicht vollständig neu auf; Freight ordnet Reihen bei veränderter Spaltenzahl neu an. Geprüfte Runtime-Updates bewegen die Produktions-Scrollposition nicht. Die Tastaturfilter hängen an den jeweiligen Views statt global an QApplication.

## Build und verbleibende Abnahme

- ZIP: `dist/playtest/Industriova-0.2.0-dev4-Windows-Playtest.zip`
- EXE: `dist/playtest/dev4/Industriova/Industriova.exe`
- ZIP-Größe: **174.254.951 Bytes**
- SHA256: `883eeb2abd509087c2ebb8399513c4574f5c7bc7d7ba4af643309877bb801fee`
- Metadaten: `0.2.0.dev4`, `Industriova Development Playtest`; 594 ZIP-Einträge, 353 Ressourcenbilder, 0 enthaltene persönliche Spielstände.
- dev3-ZIP unverändert, SHA256 weiterhin `f6fda211eb8c99f1e27ff25ef313dd30430a24b94dfe1c7567b4a981473b14d7`. Ältere Ausgaben wurden nicht überschrieben.

Für die menschliche Abnahme bleiben längere freie Spielsitzungen, persönliches Bediengefühl und reale Windows-Monitorwechsel/DPI-Wechsel einschließlich mehrerer Monitore offen. Der vollständige native Ablauf prüft einen realistischen frühen Spielpfad; späte Produktionsketten und alle vier Freight-Typen sind durch Regression/Qt-Prüfungen abgedeckt, nicht jeweils über eine vollständige native Wirtschaftspartie erspielt. Kein Anspruch auf eine abgeschlossene menschliche Release-Abnahme.

Ein frischer manueller Playtest ist über New Game möglich. Vorhandene Saves müssen dafür nicht gelöscht werden. Bei eigenständigen QA-Läufen ein separates `LOCALAPPDATA`-Verzeichnis verwenden; der normale Start lädt weiterhin den eigenen Industriova-Save.
