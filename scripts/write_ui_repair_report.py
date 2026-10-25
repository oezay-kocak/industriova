"""Assemble the repair evidence without inflating native/manual coverage."""
import json,zipfile,hashlib
from pathlib import Path
root=Path.cwd();out=root/'artifacts/industriova-ui-repair'
def read(name):return json.loads((out/name).read_text(encoding='utf-8'))
tests=read('approved-tests/results.json');package=read('package-verification.json');perf=read('performance-comparison.json');normal=read('normal-play-save.json')
assert sum(r['passed'] for r in tests)==1161 and all(r['exit_code']==0 for r in tests)
changes=[]
with zipfile.ZipFile(root/'artifacts/release-backups/20261018T221255021770Z/working-tree.zip') as z:
    names=set(z.namelist())
    candidates=[p for directory in ('src','tests','scripts','docs') for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts]+[root/'pyproject.toml']
    for p in candidates:
        name=p.relative_to(root).as_posix()
        if name not in names or z.read(name)!=p.read_bytes():changes.append(name)
(out/'all-changed-files.json').write_text(json.dumps(sorted(changes),indent=2),encoding='utf-8')
rows='\n'.join('| '+str(r['cards'])+' | '+' | '.join(f"{r[k][0]:.2f} → {r[k][1]:.2f}" for k in ('render_ms','refresh_ms','tick_ms','snapshot_ms','full_save_ms','load_ms'))+' |' for r in perf)
report=f'''# Industriova 0.2.0.dev2 – UI-Reparatur und Interaktionsprüfung

Stand: 19.10.2026. **Entwicklungs-Playtest für den nächsten menschlichen Test. Keine vollständige menschliche Gameplay-Abnahme.**

## Ergebnis

Die bestätigten Fehler D01–D04 sind gezielt korrigiert. Freight unterstützt jetzt die interne Verschiebung vorhandener Fahrzeuge, eine sichtbare Pause mit unveränderter Liefersemantik und drei begrenzte Ausbauvorschauen. Die technische Suite besteht mit **1.161 Tests in 74 Modulen**, ohne Fehler, Skip oder XFAIL. Alle bisherigen Testfunktionen sind erhalten; 26 neue Prüffälle ergänzen die bisherigen 1.135.

Ein normaler Spielstand wurde mit Windows-Eingaben bedient: Startermaschinen und Energie einsetzen, Iron Ore und Iron produzieren, Slot und Halle kaufen, Supply-Kauf mit automatischem Einbau, Mehrfachauswahl, tatsächlicher Freight-Drag, Lieferung, Pause/Resume und ein aus Spielerlösen bezahltes MK2-Upgrade. Speichern und erneutes Laden wurden geprüft. Der native Produktions-OLE-Drag bleibt separat manuell nachzuprüfen; er wird nicht als behoben oder erfolgreich abgenommen ausgegeben.

## Sicherung und Umfang

Vor der ersten Änderung: `artifacts/release-backups/20261018T221255021770Z/`, **713 Arbeitsdateien und 337 konsistente Save-Kopien**. Vergleichsbasis ist dieser vor der Reparatur gesicherte dev1-Stand. Die Vor-Overhaul-Sicherung bleibt erhalten und wurde nicht über den aktuellen Stand zurückgespielt. Persönliche Spielstände wurden für Gameplay und EXE-Proben nicht verwendet.

Keine Wirtschaftsumstellung, kein Rollback und kein Save-Schemawechsel. Simulation, GameState, SQLite-Speicherung und asynchroner Save-Writer sind unverändert. Die komplette FactoryV2MachineCard-Klasse ist strukturell identisch mit der Reparatur-Ausgangsversion; der Karten-Cache bleibt erhalten.

## Behobene Fehler

| Befund | Gezielte Änderung | Nachweis |
| --- | --- | --- |
| D01: offener Rezeptwähler veraltet | Runtime vergleicht die tatsächlich verfügbaren Produktions-IDs der gewählten Maschinenfamilie. Nur bei Änderung wird das bestehende Raster aktualisiert; Suche, Kategorie, Scrollposition soweit möglich und wiederverwendbare Kacheln bleiben erhalten. Bereits vorhandene gesperrte Kacheln werden korrekt aktiviert. | Natürliches Frühspiel: Wähler bleibt offen, nach **120 Iron Ore / 60s** erscheint Iron, unveränderter Raster-Host; danach **12 Iron** tatsächlich produziert. Kein Zusatzgeld, keine direkte Installation. |
| D02: S05 kauft S04 | Jede Vorschau kennt `isNextUnlock`; nur der unmittelbar nächste Slot ist kaufbar. Runtime-Cash-Refresh respektiert diese Grenze. Preis und sequenzieller Command bleiben unverändert. | Resources/Factory/Energy: späterer Klick ohne Buchung, nächster Slot mit exaktem Preis, erneute Aktivierung und Cash-Grenzen. |
| D03: breite zweizeilige Leiste | Bestehende GameButtons in einer kompakten Reihe; einheitlich 38px, feste Breiten 52–112px, 6px Abstände. Resources-Typfeld 160px. Gebäudeverkauf ebenfalls gleich hoch. | Drei Auflösungen × zwei Skalierungen; echte Screenshots und Vergleich mit akzeptierter Referenz. Leiste 42px statt etwa 80px. |
| D04: unklare/aktive ungültige Käufe | Einheitliche UI-Vorprüfung für Angebot, Tageslimit, Typ, Slots, Menge und Cash; deaktivierte Buttons besitzen einen konkreten Hinweis. Vor Bestätigung und erneut vor Ausführung geprüft. | Getrennte Gründe: **Insufficient Cash**, **No Available Slots**, **Incompatible Facility**, **Purchase Limit Reached**; keine Mutation bei Ablehnung. Normaler Processor-Kauf $275 → genau eine installierte Karte. |
| F01: kein Freight-Drag | Eigener kleiner Freight-Eingabecontroller mit Auswahl, Zielmarkierung und internem Press/Move/Release-Pfad. Separater atomarer MoveFreightVehicle-Command validiert beide Slots vor Änderung. Keine blockierende OLE-Schleife für interne Fahrzeugbewegungen. | Vollständige Qt-Mausgeste ohne ersetzten Handler/Command sowie tatsächliche Windows-SendInput-Geste: Truck Slot 1→2. Identität, MK, Rarity und Route erhalten; ungültige/gesperrte/belegte Ziele, falscher Facility-Typ, laufende Fahrt und Abbruch geprüft. |
| F02: Pause unverständlich | Pause verhindert weiter nur neue Abfahrten. Karte zeigt PAUSED auch während der Restfahrt; Dialog und Tooltip erklären den Abschluss der begonnenen Fahrt. | Laufende Fahrt beendet sich einmal, keine neue Fahrt bis Resume, Route bleibt erhalten. Normaler Windows-Spielpfad und eigener Engine-/UI-Test. |
| F03: nur eine Ausbauvorschau | Genau drei zukünftige Slots mit korrekter Kostenprojektion; nur der nächste ist aktiv. Anzahl bleibt nach Erweiterungen begrenzt. Bestehende Wheel-Navigation ohne horizontale Scrollleiste bleibt erhalten. | Vorschauzahl und Reihenfolge, deaktivierter späterer Klick, nächste Vorschau nach Kauf sowie existierende Rail-/Garage-Layouttests. |
| Zusätzlich bestätigt: Freight-Übersicht nach Ankunft veraltet | Hallenübersicht und Navigationszahlen werden nur bei Änderung ihrer Runtime-Signatur aktualisiert. | Nach Abschluss einer pausierten Lieferung stimmen 0 aktive Sendungen, sichtbare Übersicht und Zustand überein. |

## Tatsächlich geänderte Dateien

Produktivcode: `config.py`, `core/commands.py`, `core/freight.py`, `ui/factory_view.py`, `ui/factory_view_v2.py`, **neu** `ui/freight_drag.py`, `ui/freight_view.py`, `ui/release_board.py`, `ui/release_freight.py`, `ui/supply_view.py`, jeweils unter `src/production_zero/`.

Tests: **neu** `tests/test_ui_interaction_recovery.py`; bestehende `tests/test_factory_ui.py` und `tests/test_playtest2_consistency_followup.py` präzisiert. Fünf vorhandene Freight-Funktionen erwarten jetzt die ausdrücklich gewünschten drei Vorschauen. Der X4-Test stellt vier kompatible Plätze bereit und prüft die exakte Viererkauf-Cash-Grenze sowie X1. Keine Testfunktion entfernt, keine Deaktivierung und keine Anpassung an einen Produktdefekt.

Paket: `pyproject.toml`, `scripts/industriova_version.txt`, `scripts/playtest_LIESMICH.txt`, `scripts/build_windows_alpha.ps1`. Neue Diagnose-/QA-Helfer dokumentieren natürliche Freischaltung, wiederholte Klickpfade, native Testfenster, Screenshots, Performance, Test-Hashes und Paket-/Save-Prüfung. Die vollständige Dateiliste steht in `all-changed-files.json`; der reine Quell-/Test-Diff in `repair-source.diff`.

## Regression und Interaktionstests

| Prüfung | Ergebnis |
| --- | --- |
| Vollständiger abschließender Lauf | **74/74 Module, 1.161 bestanden**, 0 fehlgeschlagen, 0 Fehler, 0 übersprungen. Separater Qt-Prozess je Modul. |
| Bisherige Tests | Alle bisherigen 1.135 enthalten; AST-Abgleich: keine vorhandene Testfunktion entfernt. |
| Neue Prüffälle | 26: Live-Rezeptfreischaltung, drei Boards mit sequenziellen Slotkäufen, neun Toolbar-Konfigurationen, fünf Kauf-Ablehnungen, vier ungültige Freight-Moves, vollständiger Maus-Move mit Save/Load, begrenzte Vorschau, Abbruch und Pause/Lieferabschluss/Resume. |
| 200% DPI | **37 zusätzliche UI-Prüfungen bestanden**; nicht zur Hauptzahl addiert. |
| Wiederholte Bedienpfade | **90/90 erfolgreich**: je drei Wiederholungen, drei Auflösungen, zwei Skalierungen; Resources/Factory/Energy Slot→Starterinstallation, Line 3 und Hallenkauf. Echte normale Startmittel pro frischer Sitzung. |
| Migration | **16/16 ursprüngliche Slots**, einschließlich Erhaltung und Idempotenz; nur Kopien gelesen. |
| Wirtschaft | **304** Rezeptkalkulationen ohne negative Modellmarge; **20** reale Endausbau-Simulationen, kein fehlender Input und kein Stromausfall. |
| Rarity/MK | **10.000** reale Serien mit jeweils 98 Upgrades; erste permanente Rarity weiter geprüft. |
| Regulärer Source-Einstieg | Drei Anwendungsstarts mit Save/Load, geordneter Abschluss und Exitcode 0. |

Frühere Zwischenläufe mit Fehlern bleiben erhalten (`regression/`, `final-regression/`). Dort wurden zunächst veraltete Vorschau-/X4-Erwartungen und ein neuer Testaufbau mit leerem Iron-Bestand sichtbar. Ausschließlich `approved-tests/` ist der abschließende grüne Gesamtlauf. `tested-source.json` hält dessen Quell-/Test-Prüfsummen fest; der Paketcheck verifiziert sie erneut.

## Spielbarkeits-Klickpfad

Der Windows-Spielpfad verwendete ausschließlich den isolierten regulären MainWindow-Spielstand und echte Windows-Eingaben über den computer-use-Skill. Keine direkte Installation und kein Zusatzgeld. Wirtschaftlich notwendige Zwischenschritte wurden vorgezogen: Die erste Freight-Lieferung finanziert den späteren Hallen-/Supply-/MK-Ausbau. Eine Quell-Anwendung mit sichtbarem Qt-Fenster ist als solche dokumentiert; die gebaute EXE wird zusätzlich separat geprüft.

| Schritt | Ergebnis und Methode |
| --- | --- |
| 1 Start | Neues Spiel mit $1.250, leere Produktionsplätze. Windows. |
| 2 Resources | Hauptnavigation über Windows-Maus. |
| 3 Startermaschine | Build Slot → Extractor-Karte; eingesetzt. Windows. |
| 4 Ressource | Maschinen-Control → Iron Ore gewählt. Windows. |
| 5 Energie | Energy → erster Slot → Starter-Solar; 20MW. Windows. |
| 6 Rohstoffproduktion | Reguläre Echtzeitsimulation; keine Engine-Abkürzung im normalen Klickpfad. |
| 7 Factory | Hauptnavigation über Windows-Maus. |
| 8 Processor | Build Slot → Starterkarte eingesetzt. Windows. |
| 9 Produktfreischaltung | Iron durch tatsächliche Produktion erreicht. Offener Wähler separat im normalen zeitgesteuerten Qt-Ablauf nachgewiesen. |
| 10 Rezept | Sichtbare Iron-Kachel gewählt. Windows. |
| 11 Produkt herstellen | Laufender Processor, tatsächlicher Iron-Bestand wächst. |
| 12 Slot | S04 für $120 gekauft, Hallenkapazität 6→7. Windows. |
| 13 Halle | Hall 2 für $1.000 gekauft; erst nach im Spiel verdientem Erlös. Windows. |
| 14 Supply-Kauf | Common Supply → MACHINE → Processor → Kaufdialog, $275 bestätigt. Windows. |
| 15 Automatischer Einbau | Neue Karte in freiem Slot von Hall 1, Hall 1 zeigt 2/7. |
| 16 Markieren | Sichtbare Maschinen markiert. Windows und Qt. |
| 17 Mehrfachauswahl | Native Rechteckgeste markiert beide Processors; Strg/Shift zusätzlich per Qt-Window geprüft. |
| 18 Produktions-Drag | Nativer OLE-Versuch nicht zuverlässig abgeschlossen; Escape erhält Zustand. Bestehende synthetische Drop-/Identitätsprüfungen bestehen. **Weiter manuell prüfen, nicht als erfolgreich abgenommen zählen.** |
| 19 MK-Upgrade | Im normalen Spiel erzielter Erlös bezahlt Freight MK1→MK2 für $205, Kapazität 40→50. Produktions-Gruppenupgrades zusätzlich isoliert über echte Dialoge geprüft. |
| 20 Freight | Hauptnavigation über Windows-Maus. |
| 21 Fahrzeug | Startertruck über Build Slot/Karte eingesetzt. Windows. |
| 22 Fracht | Assign Route → Iron → Sell. Windows. |
| 23 Abschluss | Tatsächliche 60s-Lieferung abgeschlossen, $150 einmal gebucht. |
| 24 Pause/Resume | Während Fahrt pausiert; Restfahrt endet, keine Folgesendung. Resume startet neue Sendung mit erhaltener Route. Windows. |
| 25 Verschieben | Idle-Truck mit vollständiger nativer Press/Move/Release-Geste von Slot 1 nach Slot 2; kein Handler direkt aufgerufen. |
| 26 Speichern | Normale Autosaves und Speichern beim Schließen. |
| 27 Schließen | Native Alt+F4, Source-Prozess Exitcode 0. |
| 28 Erneut laden | Reguläre Source-Neustarts erhalten Fortschritt; Übergabe des isolierten Saves an die gebaute dev2-EXE zusätzlich geprüft. |

Der gespeicherte normale Endstand: **{normal['cash']:,.0f}$**, neun Karten, Hall 1 und Hall 2, **{normal['lifetime_produced']['iron']:,.0f} Iron und {normal['lifetime_produced']['iron_ore']:,.0f} Iron Ore lebenslang produziert**, Truck MK2 auf Slot 2 mit Iron-Sell-Route. Eine laufende Fahrt wurde samt reservierten 40 Einheiten und Restzeit gespeichert. `normal-play-save.json` enthält den überprüften Zustand. Keine menschliche Langzeitabnahme daraus abgeleitet.

## Visuelle Prüfung

`visuals/comparison.html` zeigt akzeptierte Production-Zero-Referenz, dev1 vor Reparatur sowie Reparatur bei 100% und 200% nebeneinander. Zwölf aktuelle Boardansichten pro Skalierung: Resources, Factory, Energy und Freight bei **1366×768, 1600×980, 1920×1080**. Ausgewählte tatsächliche PNGs wurden visuell geprüft, insbesondere Factory 1366/1920 und Resources 1366 bei 200%.

Die GameButton-Designsprache bleibt erhalten. Keine überbreiten Grid-Spalten, keine zweite Action-Reihe, keine neuen Dialog-/Button-Systeme. Die erste Linie gewinnt etwa 38px vertikalen Raum. Die Referenz ohne Massenleiste besitzt naturgemäß noch mehr Platz; die Reparatur behauptet keine identische Spielflächenhöhe. Vergleichsszenen haben unterschiedliche Bestückung, daher werden Anordnung und Control-Geometrie verglichen, nicht identische Karteninhalte. `measurements.json` dokumentiert reale Geometrien.

## Performance

Erste Kurzmessung bei 500 Karten: kompletter Save 313→400ms und Takt 5,32→7,20ms. Dieser Ausschlag wurde **nicht übergangen**. Anschließend vier sequenzielle **A/B/B/A**-Läufe gegen exakt extrahierten Sicherungs-Quellcode, ohne Test-/Build-Worker und ohne laufendes Testspiel. Mittel der beiden Laufmediane je Version; 10/50/100/500 Karten und identische Fixture-/Payloadgrößen.

| Karten | Zeichnen ms | Karten-Refresh ms | Takt ms | Snapshot ms | Kompletter Save ms | Laden ms |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{rows}

Der große erste Save-Ausschlag ließ sich nicht als beständiger Verlust bestätigen. Kurzlaufstreuung bleibt sichtbar, unter anderem beim 100-Karten-Zeichnen; es wird keine allgemeine Beschleunigung behauptet. Simulation, Snapshot-/SQLite-/Save-Writer-Pfad und vollständige Kartenklasse sind gegenüber der Sicherung unverändert (`performance-path-integrity.json`).

Zusätzlich ausgewähltes Supply mit 500 installierten Maschinen: **1,45→2,45ms** je vollständigem Refresh. Die etwa 1ms Mehrarbeit ist die neue erforderliche Prüfung kompatibler Plätze und konkreter Kaufgründe. Keine neue persistente Zustandskopie eingeführt. Offene Rezeptwähler bauen das Raster bei unverändertem Optionssatz nicht neu. Native FPS und längere Autosave-Eindrücke bleiben Teil des menschlichen Playtests.

## Offene Beobachtungen und Abnahmegrenzen

- Allgemeine gelegentliche Ausfälle von Build Slot, Build Hall, Unlock Line und Karteneinsatz wurden auch in den wiederholten Qt-Pfaden und den erfolgreichen nativen Stichproben nicht reproduziert. Keine spekulativen CommandBus-/Mausevent-Umbauten vorgenommen.
- Der bestehende native Produktions-OLE-Drag ließ sich durch die automatisierte Windows-Geste nicht zuverlässig abschließen. Die Ursache ist mit diesen Proben nicht ausreichend eingegrenzt, um sie als Produktfehler oder bloßes Eingabehelfer-Timing festzuschreiben. Der Pfad bleibt ausdrücklich **manuell nachzuprüfen**. Freight verwendet den separat erfolgreich geprüften internen Mauspfad.
- 200%-Prüfungen verwenden Qt-Skalierung. Gemischte physische Monitore, Maustreiber und ein vollständiger menschlicher Langzeit-Spielverlauf sind nicht abgenommen.
- Windows-Eingaben sind automatisierte native Interaktionen, keine menschliche Abnahme. Qt-Tests sind simulierte Ereignisse. Diese Kategorien werden nicht vermischt.

## Windows-Build

**0.2.0.dev2 – Industriova UI Repaired Playtest**

`dist/playtest/Industriova-0.2.0-ui-repaired-playtest-Windows.zip`

- {package['bytes']:,} Bytes, {package['entries']} ZIP-Einträge, CRC ok.
- **353/353 Ressourcenbilder**, Qt-Windows-Plattform, EXE und Anleitung enthalten; keine persönlichen Saves.
- Version/ProductName/Entwicklungs-Playtest-Metadaten geprüft; getesteter Quell-/Teststand unverändert.
- SHA256: `{package['sha256']}`.
- Native EXE-Prüfungen: frischer Start mit Starterinstallation auf drei Boards, späterer Slot ohne Fehlkauf, nächster Slot und Hallenkauf; fortgesetzter normaler Spielstand mit zusätzlichem Supply-Kauf, gesperrtem Move während einer Fahrt, sichtbarem Pause-Abschluss und vollständigem Freight-Mausdrag Slot 2→1. Danach erneut gestartet: MK2, Route, Pause und Slot 1 erhalten, 0 Sendungen, Cash unverändert $875. Letzter regulärer Abschluss mit Exitcode 0; alle drei EXE-Fehlerausgaben leer. Details: `exe-verification.json` und Save-Zusammenfassungen.
- Zwölf zentrale tatsächlich eingebundene Module einschließlich Freight-Eingabecontroller stimmen im kompilierten Code mit dem getesteten Quellstand überein (`compiled-modules.json`).

## Nachweise

Alle unter `artifacts/industriova-ui-repair/`: `approved-tests/`, `tested-source.json`, `dpi2-final.txt`, `repeated-dpi1.json`, `repeated-dpi2.json`, `natural-unlock.json`, `native-actions.json`, `native-freight-drag-events.json`, `normal-play-save.json`, `visuals/`, `benchmark-abba-*.json`, `performance-comparison.json`, `supply-before.json`, `supply-after.json`, `migration-audit.json`, `economy-audit.json`, `endgame-simulation.json`, `rarity-simulation.json`, `application-smoke.txt`, `package-verification.json`, `exe-verification.json`, `all-changed-files.json` und `repair-source.diff`.
'''
(root/'docs/industriova-ui-repair-report.md').write_text(report,encoding='utf-8')
print(json.dumps({'report':'docs/industriova-ui-repair-report.md','tests':1161,'changed_files':len(changes)}))
