"""Generate the release decision from retained test, migration and package evidence."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path('artifacts/industriova-stabilization')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    tests = read(ROOT / 'verified-tests/results.json')
    assert tests['modules'] == 73 and tests['passed'] == tests['tests'] == 1135
    assert tests['failures'] == tests['errors'] == tests['skipped'] == tests['xfail'] == 0
    for path, digest in tests['source_sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    classification = read(ROOT / 'classification.json')
    migration = read('artifacts/industriova-release/migration-audit.json')
    assert migration['passed'] == 16 and migration['failed'] == 0
    endgame = read('artifacts/industriova-release/endgame-simulation.json')
    assert len(endgame['results']) == 20 and all(r['missing_input'] == r['no_power'] == 0 for r in endgame['results'])
    economy = read('artifacts/industriova-release/economy-audit.json')
    assert len(economy['recipes']) == 304 and economy['negative_margin_products'] == []
    rarity = read('artifacts/industriova-release/rarity-simulation.json')
    assert rarity['samples'] == 10000 and sum(rarity['observed_counts'].values()) == 10000 and rarity['upgrades_per_machine'] == 98
    package = read(ROOT / 'package-verification.json')
    assert package['crc'] == 'ok' and package['resource_images'] == 353 and package['personal_saves'] == []
    native_path = sorted(ROOT.glob('packaged-smoke-*/results.json'))[-1]
    native = read(native_path)
    assert len(native['launches']) == 3 and all(r['exit_code'] == 0 and r['orderly_close'] for r in native['launches'])
    ticks = [r['save']['tick'] for r in native['launches']]
    assert ticks == sorted(set(ticks)) and ticks[0] > 0
    source_smoke = read('artifacts/industriova-release/application-smoke/results.json')
    assert source_smoke['integrity'] == 'ok' and source_smoke['final_cash'] == 7780
    before = read(ROOT / 'benchmark-save-before.json')['results']
    after = read(ROOT / 'benchmark-save-after.json')['results']
    tick_before = read(ROOT / 'tick-profile-before.json')
    tick_after = read(ROOT / 'tick-profile-after.json')
    reference = read(ROOT / 'reference/results.json')
    passed = failed = 0
    for row in reference:
        match = re.search(r'(\d+) passed', row['summary'])
        passed += int(match[1]) if match else 0
        match = re.search(r'(\d+) failed', row['summary'])
        failed += int(match[1]) if match else 0
    performance = ['| Karten | Zeichnen ms | Refresh ms | Takt ms | Snapshot ms | Encoding ms | SQLite-Commit ms | Vollständiger Save ms | Laden ms |',
                   '| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for old, new in zip(before, after):
        assert old['cards'] == new['cards']
        values = [f"{old[key]:.2f} → {new[key]:.2f}" for key in ('render_ms', 'refresh_ms', 'tick_ms', 'snapshot_ms', 'encoding_ms', 'commit_ms', 'full_save_ms', 'load_ms')]
        performance.append('| ' + str(old['cards']) + ' | ' + ' | '.join(values) + ' |')
    fixes = [
        ('P01', 'Route löschen', 'Bereits reservierte Freight-Ware wurde vom alten Cancel-Pfad entfernt. Nun bleibt die laufende Fahrt bestehen und zahlt genau einmal aus.'),
        ('P02', 'Mehrfacher Lieferbefehl', 'Bereits unterwegs reservierte Contract-Mengen werden vor einem weiteren Dispatch abgezogen; kein doppeltes Reservieren derselben Anforderung.'),
        ('P03', 'Contract-Initialisierung', 'Fehlende Periodenangebote werden auch am gültigen UTC-Epochengrenzfall angelegt. Vorhandene aktive Snapshots bleiben bei fehlender Angebotsliste erhalten.'),
        ('P04', 'Titel-Meilensteine', 'Der aktive XP-Pfad vergab noch drei Packs bei Titel-Leveln. Diese Restvergabe ist entfernt; Cash-/XP-/Levelprüfungen bleiben erhalten.'),
        ('P05', 'Letztes Freight-Gebäude', 'Backend-Verkauf besitzt nun denselben Mindest-Infrastruktur-Schutz wie die bestehende Oberfläche; Ablehnung vor jeder Buchung.'),
        ('P06', 'Supply-Preis', 'Die globale CSS-Schriftgröße übersteuerte die berechnete kleinere Schrift. Der reale Preis bleibt nun innerhalb des vorhandenen Kartenfußes.'),
        ('P07', 'Geldwerte im Header', 'Werte passen sich der vorhandenen Breite an; unveränderte Werte lösen keine neue Anpassung aus. Cash-Feedback verwendet dieselbe kompakte Formatierung.'),
        ('P08', 'Owned-Anzeige', 'Direkt installierte gekaufte Maschinen zählen als Eigentum; zuvor wurden nur unplatzierte Inventory-Stapel gezählt.'),
        ('P09', 'Verkauf mit offener Auswahl', 'Erfolgreicher Maschinenverkauf räumt einen noch offenen Drawer auf; kein veralteter Installations-/Auswahlzustand bleibt sichtbar.'),
        ('P10', 'Navigationsschrift', 'CSS übersteuerte die im Overhaul gesetzten 12px. Die vorgesehenen 12px gelten nun auch nach dem Polieren; Platz-/Clippingprüfungen bestehen.'),
        ('P11', 'Gefiltertes Produktraster', 'Suchtreffer werden kompakt in Zeilen neu angeordnet statt an alten Rasterpositionen mit großen Lücken stehenzubleiben; Widget-Identitäten bleiben erhalten.'),
        ('P12', 'Browser-Kontext', 'Research-/Ranglistenbrowser verwenden Select Product; die Contract-Beschriftung bleibt dem Contract-Kontext vorbehalten.'),
        ('P13', 'Kaufdialog-Gesamtpreis', 'Gesamtpreis verwendet denselben lesbaren dunklen Text wie der Dialogkörper; tatsächlicher Mengenpreis und Kontrast werden am echten Dialog geprüft.'),
    ]
    fix_table = ['| Nr. | Bereich | Tatsächliche Korrektur |', '| --- | --- | --- |']
    fix_table += [f'| {number} | {area} | {description} |' for number, area, description in fixes]
    previous_report = ROOT / 'overhaul-report-before-stabilization.md'
    if not previous_report.exists():
        shutil.copy2('docs/industriova-release-report.md', previous_report)
    report = f'''# Industriova 0.2.0 – technische Regression und Playtest-Freigabe

Stand: {datetime.now():%d.%m.%Y %H:%M}. Build **0.2.0.dev1 – Stabilized Playtest**.

**Technische Regression bestanden. Vollständige Release-Abnahme noch offen: Der längere menschliche Gameplay-Playtest steht aus.** Der vorliegende Overhaul bleibt die verbindliche Spielgrundlage. Es wurden Fehler und Tests korrigiert, keine neuen Gameplay-Systeme oder wirtschaftlichen Designs eingeführt.

## Ergebnis

| Prüfung | Verifiziertes Ergebnis |
| --- | --- |
| Vollständige Testsammlung | **73/73 Module, 1.135/1.135 Tests bestanden**, 0 Fehler, 0 Skips, 0 XFAIL, 0 Zeitüberschreitungen. Alle `test_*.py`-Module in getrennten Qt-Prozessen, keine Testauswahl im Abnahmelauf. |
| Unveränderter neuer Referenzlauf | 73 Module, 42 erfolgreich / 31 nicht erfolgreich; {passed} bestandene und {failed} fehlgeschlagene Tests in abgeschlossenen Modulen, zusätzlich zwei 75s-Abbrüche. |
| Klassifizierung | **{classification['classified_results']} Ergebnisse** einschließlich der nach dem alten UI-Abbruch erstmals erreichbaren Fehler und beider Zeitlimits: A {classification['classification_counts']['A']}, B {classification['classification_counts']['B']}, C {classification['classification_counts']['C']}, D {classification['classification_counts']['D']}. Einzelbegründungen in `industriova-regression-classification.md`. |
| Testmodernisierung | **{classification['updated_test_functions']} bestehende Testfunktionen** fachlich/technisch angepasst; Parametrisierungen sind hier nicht mehrfach gezählt. Fünf zusätzliche Integrations-/UI-Testfunktionen prüfen neue Fehlernachweise. |
| Produktfehler | **13 konkrete Korrekturen**, unten einzeln aufgeführt. Die drei B-Ergebnisse der ursprünglichen Fehlerklassifizierung sind nicht die Gesamtzahl später zusätzlich entdeckter Produktfehler. |
| MK / Rarity / Wirtschaft | MK1–99, lineare Skalierung, Input/Output/Power/Fuel, bezahlte Einzel-/Gruppenoperationen, erste permanente Rarity und Save geprüft. 304 Rezeptkalkulationen ohne negative Modellmarge; 20 echte Endausbau-Szenarien erfolgreich; 10.000 reale Rarity-Upgrade-Serien wiederholt. |
| Migration | **16/16 Slots** mit erweiterten Erhaltungs-/Idempotenzprüfungen erfolgreich. Persönliche Saves blieben unberührt. |
| Anwendung / EXE | Drei reguläre Quell-Anwendungsstarts mit Save/Load und drei zusätzliche native Starts der tatsächlich gebauten Windows-EXE mit WM_CLOSE, jeweils Exitcode 0. Native persistierte Ticks: {ticks}. |
| Visuelle Regression | **57 Ansichten**, 1366×768, 1600×980 und 1920×1080. MK99 mit verschiedenen Rarities, Sechserauswahl, Dialoge, Freight-Konfiguration, Ressourcenübersicht, Research-/Ranglistenbrowser und Suche enthalten. Ausgewählte kritische Ansichten tatsächlich gesichtet; kein vollständiger menschlicher Bedien-Playtest. |
| DPI | Alle **11** Industriova-UI-Prüfungen zusätzlich mit `QT_SCALE_FACTOR=2` bestanden; nicht zur Haupt-Testzahl addiert. |
| Paket | EXE-/Versionsmetadaten geprüft, ZIP-CRC ok, **353/353 Ressourcenbilder**, Qt-Windows-Plattformabhängigkeit und Anleitung vorhanden, keine persönlichen Save-Dateien. Getestete Source-/Test-Prüfsummen stimmen mit dem Build-Ausgangsstand überein. |

Der vorangegangene Overhaul-Bericht bleibt unter `artifacts/industriova-stabilization/overhaul-report-before-stabilization.md` erhalten. Das Architektur-Audit `industriova-release-audit.md` bleibt historischer Ausgangsstand.

## Behobene Produktfehler

{chr(10).join(fix_table)}

Gültige alte Tests bleiben berücksichtigt. Entfernte Inventory-/Market-/Packs-Komponenten werden nur dort ausdrücklich im Testaufbau erzeugt, wo ihre vorhandene Komponentenkompatibilität weiter geprüft wird. Die reale Anwendung und ihre Navigation enthalten diese Haupttabs weiterhin nicht. Wirtschaftliche Tests prüfen weiterhin genaue Buchungen, Waren, installierte Identitäten, Snapshots und Save-Daten. Echte Kauf-/Upgrade-/Verkaufsdialoge werden über Qt-Controls bedient; Kaufcommands werden dafür nicht ersetzt.

## Zeitlimits und Testinfrastruktur

`test_factory_ui.py`: Der isolierte Stacktrace zeigte einen alten Kauf-Test, der im neuen Bestätigungsdialog auf einen Menschen wartete. Der Test bedient jetzt den echten Dialog. Anschließend wurden alle **217 Tests vollständig** ausgeführt. Der vollständige Abnahmelauf benötigt rund vier Minuten; kein einzelner Endlosschleifenbefund. Das neue 360s-Prozesslimit folgt dem gemessenen Umfang. Es ist kein Ersatz für die Dialogkorrektur.

`test_resource_raster_assets.py`: Vorher isoliert **149,43s**, davon 147,58s für 353 × 512 × 512 einzelne Python/Qt-Pixelabfragen. Jetzt werden dieselben vollständigen Alpha-Schwellen, Pixelzahlen, quadratischen Abmessungen, PNG-Header und inklusiven Randgrenzen über RGBA-Bytes und native Byteoperationen geprüft. Der komplette Vier-Test-Lauf liegt bei rund **5,5s**. Keine Bilder und keine Prüfaussagen wurden ausgespart.

Der Runner protokolliert jetzt bei Abbrüchen auch stderr/Stacktraces und schreibt JUnit-Daten mit echten Test-/Fehler-/Skip-Zahlen. Temporäre Verzeichnisse liegen im isolierten Artefaktbereich. Zwischenläufe und Fehlschläge bleiben erhalten; die Abnahme stützt sich ausschließlich auf `approved-tests` beziehungsweise die daraus geprüfte Kopie `verified-tests`.

## Performance vor / nach der Stabilisierung

Direkter Vergleich gegen die vor dieser Aufgabe gesicherte Version, wiederhergestellt unter `before-source/src`. Dieselbe Maschine, dieselbe Benchmark-Fixture für 10/50/100/500 aktive Karten, 240 History-Samples, `PYTHONHASHSEED=0`, sequenzielle Prozesse ohne parallelen Build. Median aus sieben Wiederholungen; Encoding/Commit/Save/Load jeweils drei. Zahlen bedeuten **vorher → nachher**.

{chr(10).join(performance)}

Der vollständige Save misst den tatsächlichen synchronen Pfad Snapshot → Encoding → SQLite-Commit, keine bloße Summe und keine Messung einer Hintergrund-Queue-Wartezeit. Normales asynchrones Speichern und das Warten beim Schließen sind zusätzlich durch Integrations-/Startprüfungen abgedeckt.

Kurzlaufstreuung wurde untersucht: Eine zusätzliche ABBA-Serie zeigte bei 500 Karten Taktwerte 7,14 → 8,86ms. Eine längere reale Engine-Probe mit jeweils **500 Takten** lag bei **{tick_before['wall_ms']:.2f} → {tick_after['wall_ms']:.2f}ms** je Takt; die vollständige Fixture-Nachmessung oben bei 6,70 → 6,65ms. Die auffällige Kurzlaufdifferenz ließ sich damit nicht als gleichbleibender Verlust reproduzieren. Rohdaten aller Serien bleiben erhalten. Simulation und Save-Writer sind gegenüber dem gesicherten Ausgangsstand unverändert; die Methoden des Kartenflächen-Caches bleiben ebenfalls erhalten. Kein neuer persistenter Zustands-Cache wurde eingeführt.

Die bekannte Hauptthread-Kostenposition des vollständigen Snapshots bei 500 synthetischen Standorten bleibt sichtbar (hier rund 198ms). Sie wurde nicht versteckt oder als behoben ausgegeben. Native FPS, lange Spielsessions und subjektive Autosave-Unterbrechungen gehören in den menschlichen Playtest.

## Spielstände und Sicherungen

Vor Änderungen wurde der komplette vorhandene Arbeitsstand samt uncommitteter Dateien und konsistenten SQLite-Kopien gesichert: `artifacts/release-backups/20261018T203430454897Z/` mit SHA256-Manifest. Die ursprüngliche Overhaul-Sicherung `20261018T185514851717Z` bleibt ebenfalls erhalten.

Alle 16 ursprünglichen Slots wurden erneut ausschließlich aus Sicherungskopien migriert. Geprüft: Geld, Waren, Level/XP, Kartenidentitäten, Rarity, MK, vorhandene Rezeptfelder und Produktionsfortschritt, vollständige aktive Sendungen, Ressourcen-/Zielrouten, Platzierungen, vorhandene Gebäudestruktur, vorhandene Consortium-Daten und identischer zweiter Load. Fehlende alte Consortium-Daten erhalten lediglich die vorhandenen Loader-Defaults. Packs verschwinden entsprechend der ausdrücklichen Vorabversionsentscheidung. Schema bleibt 5.

Die drei nativen EXE-Läufe verwendeten ausschließlich `{native['isolated_appdata']}`. SQLite-Integrität, Schema 5, nichtnegative Waren, leere Pack-Bestände und strikt fortgesetzte gespeicherte Simulationstakte wurden nach jedem Lauf überprüft. Der erste Prüfhelfer-Versuch wurde nicht als Erfolg gezählt; der endgültige Helfer hält den Prozesshandle und protokolliert Close-Meldung, Exitcode und Save-Probe je Lauf.

## Windows-Playtest

`dist/playtest/Industriova-0.2.0-stabilized-playtest-Windows.zip`

- Version: **0.2.0.dev1**, EXE-Beschreibung **Industriova Stabilized Playtest**.
- Größe: **{package['bytes']:,} Bytes**; ZIP-Einträge: {package['entries']}; CRC: ok.
- SHA256: `{package['sha256']}`.
- Komplett entpacken und `Industriova.exe` zusammen mit `_internal` belassen. Anleitung liegt im Paket; der Dev-Tab bleibt wie bisher für den Playtest verfügbar.

**Technische Regression bestanden** bedeutet hier eine grüne vollständige Suite, bestandene Simulationen/Migrationen, geprüfte Visuals und einen tatsächlich startenden/geordnet schließenden Build. **Vollständige Release-Abnahme bestanden** wird ausdrücklich nicht behauptet.

Für den menschlichen Playtest bleiben: längere Früh-/Mittel-/Spätspiel-Verläufe, Kapitalbindung und MK-Amortisation im echten Spieltempo, native Drag-and-drop-Bedienung einschließlich Hallenwechsel während gehaltenem Drag, reale DPI-/Mehrmonitor-Konfigurationen, häufige Route-/Pause-/Vertragswechsel und subjektive Save-/UI-Reaktionszeiten. Ein produktiver Online-Server ist im bestehenden Projekt nicht vorhanden; lokale Consortium-/Ranglistenlogik wurde geprüft, keine Online-Abnahme erfunden.

## Nachweise

Alle unter `artifacts/industriova-stabilization/`: `reference/results.json`, `classification.json`, `approved-tests/results.json`, `verified-tests/results.json` samt 73 vollständigen JUnit-/Textberichten, `dpi2.txt`, `benchmark-save-before.json`, `benchmark-save-after.json`, `benchmark-abba-*.json`, `tick-profile-*.json`, `migration-final.txt`, `endgame.txt`, `rarity.txt`, `application-smoke.txt`, `{native_path.relative_to(ROOT).as_posix()}`, `package-verification.json`, `build.txt` und `visuals/`. Die auftragsbezogene Dateiliste und der reine Produktivcode-Diff stehen in `changed-files.json` und `source-changes.diff`; Vergleichsbasis ist die Sicherung vor dieser Stabilisierung, nicht der deutlich ältere Git-HEAD.
'''
    Path('docs/industriova-release-report.md').write_text(report, encoding='utf-8')
    overview = f'''# Industriova 0.2.0 – Regressionsübersicht

**Technisch bestanden; bereit für den nächsten menschlichen Playtest.** Eine vollständige menschliche Release-Abnahme steht weiterhin aus.

| Punkt | Ergebnis |
| --- | --- |
| Testmodule | **73 von 73 erfolgreich** |
| Ausgeführte Tests | **1.135 bestanden**, 0 fehlgeschlagen, 0 übersprungen, 0 XFAIL |
| Produktivfehler behoben | **13**, einzeln im Release-Bericht aufgeführt |
| Bestehende Testfunktionen angepasst | **160**; fünf zusätzliche Integrations-/UI-Funktionen |
| Alte Zeitlimits | Beide aufgeklärt: echter Kaufdialog im UI-Test bedient; Pixelprüfung ohne Millionen einzelner Qt-Aufrufe. 217 UI-Tests vollständig, Raster-Modul rund 5,5s statt 149,4s. |
| Fehlerklassifizierung | **167 Ergebnisse** mit Einzelbegründung: 121 A, 3 B, 42 C, 1 D. Zusätzliche Produktfehler aus Integrations-/Sichtprüfung separat dokumentiert. |
| Wirtschaft / Rarity | 304 Rezeptkalkulationen, 20 echte Endausbau-Simulationen, 10.000 Upgrade-Serien erfolgreich wiederholt |
| Migration | **16 von 16 Slots**, erweiterte Daten-/Idempotenzprüfung; Originale nicht überschrieben |
| Oberfläche | 57 gerenderte Ansichten bei drei Auflösungen; elf UI-Prüfungen zusätzlich bei 200% DPI |
| Performance | Cache und Lagerbilanz erhalten; bei 500 Karten kompletter Save **{before[-1]['full_save_ms']:.1f} → {after[-1]['full_save_ms']:.1f}ms**, warmes Zeichnen **{before[-1]['render_ms']:.1f} → {after[-1]['render_ms']:.1f}ms**. Schwankende Taktmessungen zusätzlich über 500 reale Takte untersucht. |
| Windows-Build | **0.2.0.dev1**, ZIP/Metadaten/353 Ressourcenbilder geprüft, keine persönlichen Saves; drei native EXE-Starts und geordnete Abschlüsse mit fortgesetztem Spielstand |
| Verbleibende technische Fehler / externe Blocker | **Keine in der geprüften lokalen Version** |

Paket: `dist/playtest/Industriova-0.2.0-stabilized-playtest-Windows.zip`.

Einzelheiten: [Release-Bericht](industriova-release-report.md), [vollständige Klassifizierung](industriova-regression-classification.md). Prüfdaten: `artifacts/industriova-stabilization/verified-tests/results.json`.

Noch menschlich zu prüfen: längere wirtschaftliche Spielverläufe, tatsächliche Windows-Bedienung mit Drag-and-drop, verschiedene Bildschirme/DPI sowie subjektive UI- und Autosave-Reaktionszeiten. Automatisierte Startprüfungen sind keine manuelle Gameplay-Abnahme.
'''
    Path('docs/industriova-regression-overview.md').write_text(overview, encoding='utf-8')
    print(json.dumps(dict(report='docs/industriova-release-report.md', overview='docs/industriova-regression-overview.md', product_fixes=len(fixes), tests=tests['passed'], native_ticks=ticks)))


if __name__ == '__main__':
    main()
