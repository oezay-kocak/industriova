# Industriova – UI Polish & Interaction Refinement

Stand: 19.10.2026. Umsetzung im Quellstand; kein neuer Windows-Build erstellt. Die vorhandene dev2-ZIP enthält diesen Polish-Pass noch nicht.

## Änderungen

- Der lange Funktionsbalken ist entfernt. Recipe, Pause für die Auswahl, Copy, Paste und Sell sind über das industrielle Kartenmenü per Rechtsklick erreichbar. Mehrfachauswahl und Produktions-Drag bleiben erhalten.
- Direktes Upgrade: größerer grüner Kartenknopf mit zwei gezeichneten Aufwärtspfeilen. Ein Klick auf eine ausgewählte Karte berücksichtigt die geeigneten selektierten Karten; MK99 wird ausgelassen. Bestehende Preis-, MK- und Rarity-Logik bleibt maßgeblich.
- Gebäude- und Sektorheader besitzen kompakte 76×38-Steuerungen: PAUSE rot, RESUME gelb. Freight beendet begonnene Fahrten weiterhin regulär.
- Gebäudenamen lassen sich im Header oder durch Klick auf die erste Namenszeile links ändern. Die Belegungszeile links bleibt zur Navigation verfügbar. Bei leeren Resources-Sites ist die vorhandene Typänderung im Namensdialog erreichbar. Rechtsklick links öffnet den Gebäudeverkauf. Separate Rename-/Sell-Building-Buttons entfallen.
- Belegte Gebäude können nach ausdrücklicher Bestätigung mitsamt Maschinen verkauft werden. Der Dialog nennt Anzahl, Gebäudeerlös, Maschinen-/Fahrzeugerlös und Gesamtbetrag. Letztes Gebäude und Fahrzeuge unterwegs bleiben geschützt. Wiederverwendet werden die bestehenden Verkaufswerte (Gebäude 60% Investition, Maschinen vorhandener Resale-Wert); keine neuen Preise.
- Build Site öffnet drei bebilderte Optionen, Build Facility vier. Keine Vorwahl und keine Buchung beim Öffnen. Der Preis erscheint im Dialog; BUY wird erst nach Typwahl und ausreichendem Cash aktiv. CANCEL oben rechts. Unten links steht nur BUILD SITE beziehungsweise BUILD FACILITY.
- Neue Contracts wählen und akzeptieren keine Produkte mehr automatisch. Der Spieler wählt die erforderlichen unterschiedlichen Produkte selbst. Bestehende aktive Lieferaufträge werden nicht zurückgesetzt. Arbeitswert-/Kategorie-/Level-XP, Cash-Snapshot, Lieferungen und Periodenstruktur bleiben erhalten; Quote jetzt bei manueller Annahme. Nach Abbruch wird die Produktauswahl geleert.
- Verkaufs-/Kaufdialoge verwenden den vorhandenen Production-Guide-Button-Painter: gleiche 48px-Buttons, gelbes JA und rotes NEIN, dunkle kräftige Schrift. Größere industrielle Titel und Textblöcke. Menge und Multiplikatoren bleiben bedienbar.
- MaterialFrame ist transparent und rund maskiert; Transparenzregeln sind auf den Container begrenzt, damit Eingabefelder ihren Hintergrund behalten. Resources-Overlay und neue Dialoge zeigen keine schwarzen rechteckigen Eckflächen. Der obere Resources-Button nutzt dieselbe Reliefgeometrie in Hellblau mit größerem schwarzem Text.

## Geänderte Dateien

Produktivcode:

- `src/production_zero/core/commands.py`
- `src/production_zero/core/contracts.py`
- `src/production_zero/core/infrastructure.py`
- `src/production_zero/ui/contracts_view.py`
- `src/production_zero/ui/factory_view_v2.py`
- `src/production_zero/ui/freight_view.py`
- `src/production_zero/ui/game_ui/widgets.py`
- `src/production_zero/ui/interaction_polish.py`
- `src/production_zero/ui/material_frame.py`
- `src/production_zero/ui/release_board.py`
- `src/production_zero/ui/release_dialogs.py`
- `src/production_zero/ui/release_freight.py`

Die vollständige Liste einschließlich angepasster Tests, QA-Helfer und Bericht steht in `artifacts/ui-polish/changed-files.json`. Vor Änderungen wurden 722 Arbeitsdateien einschließlich des bestehenden uncommitteten Stands nach `artifacts/ui-polish/20261019T112903Z/working-tree.zip` gesichert. Persönliche AppData-Saves wurden nicht als Testbasis geladen oder verändert. App-Einstieg, Save-Pfade, Migration und New-Game-Logik bleiben unverändert.

## Prüfung

- Vollständige modulweise Regression: **75 Module, 1190 bestanden; 0 Module mit Fehlern**. Nachweise: `artifacts/ui-polish/final-verification/`. Frühere Zwischenläufe bleiben erhalten; ausschließlich dieser abschließende Lauf ist für die Ergebniszahl maßgeblich.
- Neue Qt-Interaktionstests: 29 Fälle in `tests/test_ui_polish_interactions.py`. Sie bedienen sichtbare Fenster mit Maus-Press/Release, echte Modaldialoge und Bestätigungen. Enthalten sind alle sieben Bautypen, Abbruch, Umbenennen im Header und links auf vier Boards, Typänderung leerer Sites, Einzel-/Gruppenaktionen, Pause/Resume, Overlay, manueller Contract, belegter Gebäudeverkauf und atomare Ablehnungen.
- Zusätzlich 200%: 55 Interaktionsprüfungen (neue 29 + vorhandene 26); separater Lauf, nicht zur Gesamtsuite addiert. Bestehende Tests für automatische Contracts und direkte Freight-Käufe wurden auf die ausdrücklich gewünschte manuelle Auswahl umgestellt. Die fachlichen Liefer-, Preis-, Snapshot-, XP- und Save-Prüfungen bleiben erhalten.
- Native Windows-Stichprobe über computer-use: Resources öffnen/schließen, PAUSE→RESUME→PAUSE, Bauauswahl öffnen/abbrechen, Rechtsklick auf Karte→Verkaufsdialog→Verkauf, freie Slotdarstellung, leere Contract-Auswahl, reguläres Speichern/Schließen mit Exitcode 0. Isolierter ergänzender Teststand mit $20.000 und vorbereiteten Karten; kein normaler Frühspiel-Nachweis. Verkauf einer Extractor-Karte buchte $272 genau einmal und entfernte ihre Slotbelegung. `native/actions.json`, `native/company.sqlite` und `native/observed-state.json` dokumentieren den Ablauf. Die globale Kopfleiste blieb in diesem bewusst angehaltenen QA-Aufbau teilweise auf den Anfangsanzeigen; die Buchung wurde zusätzlich am gespeicherten Zustand geprüft.
- Visuelle Qt-Aufnahmen: Resources, Factory, Energy, Freight und Contracts bei 1366×768, 1600×980 und 1920×1080, jeweils 100% und 200%. Dazu Dialoge, Overlay, Kartenknopf und Bauauswahl. Tatsächliche PNGs visuell geprüft und anhand der zehn bereitgestellten Screenshots verglichen: `artifacts/ui-polish/comparison.html`.

## Hinweise zum nächsten Playtest

Die automatisierten Qt-Mausereignisse und die zusätzlichen nativen Windows-Eingaben sind getrennte Nachweise; eine vollständige menschliche Abnahme wird nicht behauptet. Den finalen optischen Eindruck auf physischen 200%-Monitoren und den längeren Spielfluss bitte im nächsten menschlichen Playtest prüfen. Bereits aktive gespeicherte Contracts behalten ihre bisherigen Produkte; neue Angebote und abgebrochene Angebote beginnen mit manueller Auswahl. Die bestehende dev2-EXE wurde nicht neu gebaut oder ersetzt.
