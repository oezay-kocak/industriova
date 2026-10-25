# P11-C – unbegrenzte Factory-Erweiterung

Stand 23.10.2026. Produktiv ausschließlich die globale Kaufgrenze entfernt und unmittelbar nötige Quote-/Navigationsbehandlung ergänzt. Keine Preis-/Rezept-/Produktionsänderung, kein Build.

## Implementierung

Beide regulären Kaufpfade in core/commands.py (PurchaseHall und PurchaseProductionUnit) akzeptieren nun Halle 11, 12 und weitere. Kein Ersatzcap. Neue Hallen bleiben 5 Linien × 10 Plätze, Startlinie mit 3 Plätzen; maximal 50 Verarbeitungskarten je neuer Halle. Processor/Fabricator/Assembler bleiben mischbar. Die Gesamtplatzzahl ist deshalb 50*N bei N regulären voll ausgebauten Hallen. Historische Geometrien bleiben unverändert lesbar.

core/infrastructure_prices.py behält alle Parameter und Rundungsschritte von facility_price bei. Nur Overflow/ungültige numerische Ergebnisse werden in ValueError umgewandelt. Der Kauf validiert den Quote vor Cashabbuchung/Mutation. ui/factory_view.py deaktiviert einen numerisch nicht darstellbaren Kaufquote. Kein kostenloser Fallback. Finite Floats haben bei extremen Summen nicht mehr Centpräzision; dies ist eine Zahlendarstellungsgrenze, kein zusätzlicher Gebäudehöchstwert.

Die vorhandene scrollbare QTreeWidget-Navigation enthält dynamische Einträge. ui/factory_view_v2.py erzeugt sie nur bei geänderter ID-Liste neu, aktualisiert sonst bestehende Labels/Selektion. Die aktive Halle wird angezeigt, nicht die gesamte Firma als Kartenwidgetbaum gerendert. Listenaktualisierung bleibt linear; keine behauptete konstante Laufzeit für beliebig große Firmen. 1000 synthetische Hallen werden durch den UI-Test geprüft. Keine zehn festen UI-Gebäudeplätze gefunden.

## Unveränderte Kaufkurve

n bezeichnet bereits vorhandene Hallen. Erste Halle kostet 1000, weitere nach der vorhandenen Funktion mit effektivem zweiten Basiswert 15200 und Wachstum n^2.5, auf 100 aufgerundet. Startgebäude im echten Neustart ist geschenkt; kumulierte Modellkosten und tatsächliche Zukaufkosten werden getrennt.

| Hallennummer | Einzelpreis | Summe inklusive bezahlter erster Halle | Zukäufe bei geschenkter erster Halle |
|---|---|---|---|
| 10 | 3693600.0 | 11431500.0 | 11430500.0 |
| 11 | 4806700.0 | 16238200.0 | 16237200.0 |
| 12 | 6100000.0 | 22338200.0 | 22337200.0 |
| 15 | 11147200.0 | 50329700.0 | 50328700.0 |
| 20 | 23918200.0 | 142064600.0 | 142063600.0 |
| 25 | 42891600.0 | 315933700.0 | 315932700.0 |
| 50 | 255466400.0 | 3705352300.0 | 3705351300.0 |
| 100 | 1482284600.0 | 42671744000.0 | 42671743000.0 |
| 250 | 14871061100.0 | 1065417756000.0 | 1065417755000.0 |
| 500 | 84546367300.0 | 12096204872500.0 | 12096204871500.0 |
| 1000 | 479465440000.0 | 137092968327300.0 | 137092968326300.0 |

Quotes bis zu diesen Hallenzahlen sind endlich und positiv. Tests prüfen zudem die unveränderten ersten Preise, monotones Wachstum bis 1000 sowie kontrollierte Ablehnung bei counts 10^124 und 10^1000. Diese Zahlen sind Testpunkte, keine eingeführten Limits.

## Verifikation

98 Testmodule vollständig und einzeln in isolierten Qt-Prozessen: **1998 Tests bestanden**, keine Filter und keine übersprungenen Tests. Die erste gemeinsame Ausführung wurde nach Fixture-/Tempfehlern abgebrochen; alle Module wurden anschließend mit eigenen temporären Verzeichnissen ausgeführt. Der alte Cap-Integrationstest wurde erhalten und passend auf erlaubten Hallenkauf sowie weiterhin atomare Cashprüfung umgestellt. Im neuen SQLite-Test wurde die explizite Datenbankinitialisierung ergänzt. Beide betroffenen Module anschließend erneut vollständig grün; ursprüngliche und korrigierte Logs bleiben erhalten. Vollständige Logs und Exitcodes: artifacts/phase11c/regression/results.json. Neue Tests: beide Kaufpfade über 10→11→12 bis 25; volle lokale 50 Plätze; Gesamtzahl >500 und tatsächliche Installation von 501 Processor-Karten; Cashatomizität; SQLite Save/Load; Legacy-Sechs-Linien-Halle; 1000 Hallen und Navigationseintragsidentität.

Alle **16 historischen Migrationen** gegen unveränderliche Archivkopien erneut geprüft, volle serialisierte Payloads identisch zum bisherigen P8/P10-Referenzstand und idempotent; Schema bleibt 9. Kein persönlicher Save migriert.

SHA256-Bestandsschutz: 5066 Ausgangsdateien erfasst. Exakt die vier genannten produktiven Dateien sowie der an das neue Design angepasste bestehende Integrationstest verändert; alle übrigen erfassten Dateien einschließlich P11-A/P11-B, sämtlicher Spieldaten/Preis-/Researchdefinitionen, fünf persönlicher Saves und 4083 Builddateien unverändert. Neue Test-/Offlinewerkzeuge und Ergebnisse separat. Nachweis: artifacts/phase11c/protected-verification.json, Ausgangsmanifest baseline.json, Quellenbackup source-before.zip.
