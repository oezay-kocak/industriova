# Industriova 0.2.0 – technische Regression und Playtest-Freigabe

**Historischer dev1-Bericht.** Die spätere UI-Diagnose hat trotz grüner Suite Bedienfehler nachgewiesen. Aktueller Stand und dev2-Paket: [UI-Reparaturbericht](industriova-ui-repair-report.md). Die damalige technische Freigabe ersetzt keine Bedienabnahme.

Stand: 18.10.2026 23:33. Build **0.2.0.dev1 – Stabilized Playtest**.

**Technische Regression bestanden. Vollständige Release-Abnahme noch offen: Der längere menschliche Gameplay-Playtest steht aus.** Der vorliegende Overhaul bleibt die verbindliche Spielgrundlage. Es wurden Fehler und Tests korrigiert, keine neuen Gameplay-Systeme oder wirtschaftlichen Designs eingeführt.

## Ergebnis

| Prüfung | Verifiziertes Ergebnis |
| --- | --- |
| Vollständige Testsammlung | **73/73 Module, 1.135/1.135 Tests bestanden**, 0 Fehler, 0 Skips, 0 XFAIL, 0 Zeitüberschreitungen. Alle `test_*.py`-Module in getrennten Qt-Prozessen, keine Testauswahl im Abnahmelauf. |
| Unveränderter neuer Referenzlauf | 73 Module, 42 erfolgreich / 31 nicht erfolgreich; 801 bestandene und 108 fehlgeschlagene Tests in abgeschlossenen Modulen, zusätzlich zwei 75s-Abbrüche. |
| Klassifizierung | **167 Ergebnisse** einschließlich der nach dem alten UI-Abbruch erstmals erreichbaren Fehler und beider Zeitlimits: A 121, B 3, C 42, D 1. Einzelbegründungen in `industriova-regression-classification.md`. |
| Testmodernisierung | **160 bestehende Testfunktionen** fachlich/technisch angepasst; Parametrisierungen sind hier nicht mehrfach gezählt. Fünf zusätzliche Integrations-/UI-Testfunktionen prüfen neue Fehlernachweise. |
| Produktfehler | **13 konkrete Korrekturen**, unten einzeln aufgeführt. Die drei B-Ergebnisse der ursprünglichen Fehlerklassifizierung sind nicht die Gesamtzahl später zusätzlich entdeckter Produktfehler. |
| MK / Rarity / Wirtschaft | MK1–99, lineare Skalierung, Input/Output/Power/Fuel, bezahlte Einzel-/Gruppenoperationen, erste permanente Rarity und Save geprüft. 304 Rezeptkalkulationen ohne negative Modellmarge; 20 echte Endausbau-Szenarien erfolgreich; 10.000 reale Rarity-Upgrade-Serien wiederholt. |
| Migration | **16/16 Slots** mit erweiterten Erhaltungs-/Idempotenzprüfungen erfolgreich. Persönliche Saves blieben unberührt. |
| Anwendung / EXE | Drei reguläre Quell-Anwendungsstarts mit Save/Load und drei zusätzliche native Starts der tatsächlich gebauten Windows-EXE mit WM_CLOSE, jeweils Exitcode 0. Native persistierte Ticks: [114, 229, 344]. |
| Visuelle Regression | **57 Ansichten**, 1366×768, 1600×980 und 1920×1080. MK99 mit verschiedenen Rarities, Sechserauswahl, Dialoge, Freight-Konfiguration, Ressourcenübersicht, Research-/Ranglistenbrowser und Suche enthalten. Ausgewählte kritische Ansichten tatsächlich gesichtet; kein vollständiger menschlicher Bedien-Playtest. |
| DPI | Alle **11** Industriova-UI-Prüfungen zusätzlich mit `QT_SCALE_FACTOR=2` bestanden; nicht zur Haupt-Testzahl addiert. |
| Paket | EXE-/Versionsmetadaten geprüft, ZIP-CRC ok, **353/353 Ressourcenbilder**, Qt-Windows-Plattformabhängigkeit und Anleitung vorhanden, keine persönlichen Save-Dateien. Getestete Source-/Test-Prüfsummen stimmen mit dem Build-Ausgangsstand überein. |

Der vorangegangene Overhaul-Bericht bleibt unter `artifacts/industriova-stabilization/overhaul-report-before-stabilization.md` erhalten. Das Architektur-Audit `industriova-release-audit.md` bleibt historischer Ausgangsstand.

## Behobene Produktfehler

| Nr. | Bereich | Tatsächliche Korrektur |
| --- | --- | --- |
| P01 | Route löschen | Bereits reservierte Freight-Ware wurde vom alten Cancel-Pfad entfernt. Nun bleibt die laufende Fahrt bestehen und zahlt genau einmal aus. |
| P02 | Mehrfacher Lieferbefehl | Bereits unterwegs reservierte Contract-Mengen werden vor einem weiteren Dispatch abgezogen; kein doppeltes Reservieren derselben Anforderung. |
| P03 | Contract-Initialisierung | Fehlende Periodenangebote werden auch am gültigen UTC-Epochengrenzfall angelegt. Vorhandene aktive Snapshots bleiben bei fehlender Angebotsliste erhalten. |
| P04 | Titel-Meilensteine | Der aktive XP-Pfad vergab noch drei Packs bei Titel-Leveln. Diese Restvergabe ist entfernt; Cash-/XP-/Levelprüfungen bleiben erhalten. |
| P05 | Letztes Freight-Gebäude | Backend-Verkauf besitzt nun denselben Mindest-Infrastruktur-Schutz wie die bestehende Oberfläche; Ablehnung vor jeder Buchung. |
| P06 | Supply-Preis | Die globale CSS-Schriftgröße übersteuerte die berechnete kleinere Schrift. Der reale Preis bleibt nun innerhalb des vorhandenen Kartenfußes. |
| P07 | Geldwerte im Header | Werte passen sich der vorhandenen Breite an; unveränderte Werte lösen keine neue Anpassung aus. Cash-Feedback verwendet dieselbe kompakte Formatierung. |
| P08 | Owned-Anzeige | Direkt installierte gekaufte Maschinen zählen als Eigentum; zuvor wurden nur unplatzierte Inventory-Stapel gezählt. |
| P09 | Verkauf mit offener Auswahl | Erfolgreicher Maschinenverkauf räumt einen noch offenen Drawer auf; kein veralteter Installations-/Auswahlzustand bleibt sichtbar. |
| P10 | Navigationsschrift | CSS übersteuerte die im Overhaul gesetzten 12px. Die vorgesehenen 12px gelten nun auch nach dem Polieren; Platz-/Clippingprüfungen bestehen. |
| P11 | Gefiltertes Produktraster | Suchtreffer werden kompakt in Zeilen neu angeordnet statt an alten Rasterpositionen mit großen Lücken stehenzubleiben; Widget-Identitäten bleiben erhalten. |
| P12 | Browser-Kontext | Research-/Ranglistenbrowser verwenden Select Product; die Contract-Beschriftung bleibt dem Contract-Kontext vorbehalten. |
| P13 | Kaufdialog-Gesamtpreis | Gesamtpreis verwendet denselben lesbaren dunklen Text wie der Dialogkörper; tatsächlicher Mengenpreis und Kontrast werden am echten Dialog geprüft. |

Gültige alte Tests bleiben berücksichtigt. Entfernte Inventory-/Market-/Packs-Komponenten werden nur dort ausdrücklich im Testaufbau erzeugt, wo ihre vorhandene Komponentenkompatibilität weiter geprüft wird. Die reale Anwendung und ihre Navigation enthalten diese Haupttabs weiterhin nicht. Wirtschaftliche Tests prüfen weiterhin genaue Buchungen, Waren, installierte Identitäten, Snapshots und Save-Daten. Echte Kauf-/Upgrade-/Verkaufsdialoge werden über Qt-Controls bedient; Kaufcommands werden dafür nicht ersetzt.

## Zeitlimits und Testinfrastruktur

`test_factory_ui.py`: Der isolierte Stacktrace zeigte einen alten Kauf-Test, der im neuen Bestätigungsdialog auf einen Menschen wartete. Der Test bedient jetzt den echten Dialog. Anschließend wurden alle **217 Tests vollständig** ausgeführt. Der vollständige Abnahmelauf benötigt rund vier Minuten; kein einzelner Endlosschleifenbefund. Das neue 360s-Prozesslimit folgt dem gemessenen Umfang. Es ist kein Ersatz für die Dialogkorrektur.

`test_resource_raster_assets.py`: Vorher isoliert **149,43s**, davon 147,58s für 353 × 512 × 512 einzelne Python/Qt-Pixelabfragen. Jetzt werden dieselben vollständigen Alpha-Schwellen, Pixelzahlen, quadratischen Abmessungen, PNG-Header und inklusiven Randgrenzen über RGBA-Bytes und native Byteoperationen geprüft. Der komplette Vier-Test-Lauf liegt bei rund **5,5s**. Keine Bilder und keine Prüfaussagen wurden ausgespart.

Der Runner protokolliert jetzt bei Abbrüchen auch stderr/Stacktraces und schreibt JUnit-Daten mit echten Test-/Fehler-/Skip-Zahlen. Temporäre Verzeichnisse liegen im isolierten Artefaktbereich. Zwischenläufe und Fehlschläge bleiben erhalten; die Abnahme stützt sich ausschließlich auf `approved-tests` beziehungsweise die daraus geprüfte Kopie `verified-tests`.

## Performance vor / nach der Stabilisierung

Direkter Vergleich gegen die vor dieser Aufgabe gesicherte Version, wiederhergestellt unter `before-source/src`. Dieselbe Maschine, dieselbe Benchmark-Fixture für 10/50/100/500 aktive Karten, 240 History-Samples, `PYTHONHASHSEED=0`, sequenzielle Prozesse ohne parallelen Build. Median aus sieben Wiederholungen; Encoding/Commit/Save/Load jeweils drei. Zahlen bedeuten **vorher → nachher**.

| Karten | Zeichnen ms | Refresh ms | Takt ms | Snapshot ms | Encoding ms | SQLite-Commit ms | Vollständiger Save ms | Laden ms |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 2.54 → 3.01 | 0.02 → 0.02 | 1.55 → 1.54 | 9.37 → 9.18 | 66.03 → 69.24 | 20.50 → 20.01 | 98.11 → 102.04 | 66.03 → 73.37 |
| 50 | 17.22 → 14.85 | 0.14 → 0.08 | 2.54 → 1.89 | 27.11 → 24.27 | 75.02 → 66.42 | 22.28 → 21.26 | 119.98 → 132.14 | 86.98 → 86.21 |
| 100 | 39.88 → 33.33 | 0.27 → 0.18 | 3.06 → 2.58 | 48.91 → 36.55 | 75.00 → 69.63 | 28.54 → 28.72 | 174.93 → 157.81 | 89.77 → 102.45 |
| 500 | 198.01 → 172.76 | 1.12 → 1.07 | 6.70 → 6.65 | 210.78 → 197.81 | 103.79 → 106.93 | 46.70 → 45.70 | 343.00 → 343.30 | 148.30 → 121.79 |

Der vollständige Save misst den tatsächlichen synchronen Pfad Snapshot → Encoding → SQLite-Commit, keine bloße Summe und keine Messung einer Hintergrund-Queue-Wartezeit. Normales asynchrones Speichern und das Warten beim Schließen sind zusätzlich durch Integrations-/Startprüfungen abgedeckt.

Kurzlaufstreuung wurde untersucht: Eine zusätzliche ABBA-Serie zeigte bei 500 Karten Taktwerte 7,14 → 8,86ms. Eine längere reale Engine-Probe mit jeweils **500 Takten** lag bei **6.24 → 6.58ms** je Takt; die vollständige Fixture-Nachmessung oben bei 6,70 → 6,65ms. Die auffällige Kurzlaufdifferenz ließ sich damit nicht als gleichbleibender Verlust reproduzieren. Rohdaten aller Serien bleiben erhalten. Simulation und Save-Writer sind gegenüber dem gesicherten Ausgangsstand unverändert; die Methoden des Kartenflächen-Caches bleiben ebenfalls erhalten. Kein neuer persistenter Zustands-Cache wurde eingeführt.

Die bekannte Hauptthread-Kostenposition des vollständigen Snapshots bei 500 synthetischen Standorten bleibt sichtbar (hier rund 198ms). Sie wurde nicht versteckt oder als behoben ausgegeben. Native FPS, lange Spielsessions und subjektive Autosave-Unterbrechungen gehören in den menschlichen Playtest.

## Spielstände und Sicherungen

Vor Änderungen wurde der komplette vorhandene Arbeitsstand samt uncommitteter Dateien und konsistenten SQLite-Kopien gesichert: `artifacts/release-backups/20261018T203430454897Z/` mit SHA256-Manifest. Die ursprüngliche Overhaul-Sicherung `20261018T185514851717Z` bleibt ebenfalls erhalten.

Alle 16 ursprünglichen Slots wurden erneut ausschließlich aus Sicherungskopien migriert. Geprüft: Geld, Waren, Level/XP, Kartenidentitäten, Rarity, MK, vorhandene Rezeptfelder und Produktionsfortschritt, vollständige aktive Sendungen, Ressourcen-/Zielrouten, Platzierungen, vorhandene Gebäudestruktur, vorhandene Consortium-Daten und identischer zweiter Load. Fehlende alte Consortium-Daten erhalten lediglich die vorhandenen Loader-Defaults. Packs verschwinden entsprechend der ausdrücklichen Vorabversionsentscheidung. Schema bleibt 5.

Die drei nativen EXE-Läufe verwendeten ausschließlich `artifacts\industriova-stabilization\packaged-smoke-20261018T232507`. SQLite-Integrität, Schema 5, nichtnegative Waren, leere Pack-Bestände und strikt fortgesetzte gespeicherte Simulationstakte wurden nach jedem Lauf überprüft. Der erste Prüfhelfer-Versuch wurde nicht als Erfolg gezählt; der endgültige Helfer hält den Prozesshandle und protokolliert Close-Meldung, Exitcode und Save-Probe je Lauf.

## Windows-Playtest

`dist/playtest/Industriova-0.2.0-stabilized-playtest-Windows.zip`

- Version: **0.2.0.dev1**, EXE-Beschreibung **Industriova Stabilized Playtest**.
- Größe: **172,659,679 Bytes**; ZIP-Einträge: 594; CRC: ok.
- SHA256: `0fc6f4fbde4de691e273cb007efc50ab7f1e21582d665128a8b8803f4f38d8db`.
- Komplett entpacken und `Industriova.exe` zusammen mit `_internal` belassen. Anleitung liegt im Paket; der Dev-Tab bleibt wie bisher für den Playtest verfügbar.

**Technische Regression bestanden** bedeutet hier eine grüne vollständige Suite, bestandene Simulationen/Migrationen, geprüfte Visuals und einen tatsächlich startenden/geordnet schließenden Build. **Vollständige Release-Abnahme bestanden** wird ausdrücklich nicht behauptet.

Für den menschlichen Playtest bleiben: längere Früh-/Mittel-/Spätspiel-Verläufe, Kapitalbindung und MK-Amortisation im echten Spieltempo, native Drag-and-drop-Bedienung einschließlich Hallenwechsel während gehaltenem Drag, reale DPI-/Mehrmonitor-Konfigurationen, häufige Route-/Pause-/Vertragswechsel und subjektive Save-/UI-Reaktionszeiten. Ein produktiver Online-Server ist im bestehenden Projekt nicht vorhanden; lokale Consortium-/Ranglistenlogik wurde geprüft, keine Online-Abnahme erfunden.

## Nachweise

Alle unter `artifacts/industriova-stabilization/`: `reference/results.json`, `classification.json`, `approved-tests/results.json`, `verified-tests/results.json` samt 73 vollständigen JUnit-/Textberichten, `dpi2.txt`, `benchmark-save-before.json`, `benchmark-save-after.json`, `benchmark-abba-*.json`, `tick-profile-*.json`, `migration-final.txt`, `endgame.txt`, `rarity.txt`, `application-smoke.txt`, `packaged-smoke-20261018T232507/results.json`, `package-verification.json`, `build.txt` und `visuals/`. Die auftragsbezogene Dateiliste und der reine Produktivcode-Diff stehen in `changed-files.json` und `source-changes.diff`; Vergleichsbasis ist die Sicherung vor dieser Stabilisierung, nicht der deutlich ältere Git-HEAD.
