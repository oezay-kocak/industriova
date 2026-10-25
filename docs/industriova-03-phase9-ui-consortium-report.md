# INDUSTRIOVA 0.3 – P9: Navigation, UI-Polish und Freight-only Consortium

Stand: 22.10.2026. P9 ist implementiert. Consortium Contracts nehmen ausschließlich abgeschlossene wirtschaftliche Freight-Lieferungen an. Navigation und Informationsdarstellung verwenden die bestehenden Industriova-Komponenten. Kein neuer Windows-Build, kein Tutorial, keine Events und kein zusätzlicher Markt.

**1,938 / 1,938 Tests in 95 vollständigen Modulen bestanden**, 0 Fehler und 0 Skips. Alle **1.869 P8-Fälle** sind mit derselben Testidentität erhalten; 69 neue Fälle. Zusätzlich 218 Fälle in 8 vollständigen Modulen bei 200 %. **16/16 historische Migrationen**, gesamter serialisierter Zustand identisch zu final P8. Schema bleibt **9**.

## 1. Sicherung und tatsächlich geänderte Dateien

Die tatsächliche uncommittete und ungetrackte P8-Arbeitskopie ist maßgeblich, kein Git-HEAD-Reset. Vor produktiven Änderungen: `artifacts/phase9/backup-20261022T174317Z` mit unabhängigem, CRC-geprüftem Quellarchiv und SHA256-geprüfter Extraktion nach `artifacts/phase9/before-tree`. 934 relevante Quellen, Tests, Konfigurationen, Dokumente und Assets; zusätzlich fünf persönliche Saves roh sowie als konsistente read-only SQLite-Backups, jeweils integrity_check=ok. 4.083 vorhandene Build-/Dist-Dateien wurden separat gehasht. Das P8-Manifest und dessen Archivprüfsummen binden die unverändert erhaltene P8→P0-Sicherungskette für frühere Arbeitsstände und Artefakte.

Quellarchiv SHA256: `9259186717c265131b04700639c2f6e6f0c23ce8a3a35a502c289c6c974edf14`. Wiederherstellen ausschließlich in einen neuen Ordner, dann Einzeldatei-Hashes prüfen; persönliche Saves nur gezielt aus passenden Kopien. Ein vorangegangener vollständiger Archivscan wurde beendet; dessen unvollständiges Diagnoseverzeichnis ist **keine** freigegebene Sicherung. `backup-location.txt` benennt ausschließlich die geprüfte Sicherung. Die P9-Sicherung umfasst relevante Arbeitsdateien und Saves; sie behauptet keine erneute Vollarchivierung aller alten Build-/Artefaktarchive.

Produktive Quellen und Tests:

- `src/production_zero/core/consortium.py`
- `src/production_zero/core/simulation.py`
- `src/production_zero/ui/consortium_view.py`
- `src/production_zero/ui/contracts_view.py`
- `src/production_zero/ui/event_feed.py`
- `src/production_zero/ui/factory_view.py`
- `src/production_zero/ui/factory_view_v2.py`
- `src/production_zero/ui/freight_view.py`
- `src/production_zero/ui/interaction_polish.py`
- `src/production_zero/ui/main_tab_header.py`
- `src/production_zero/ui/main_window.py`
- `tests/test_consortium.py`
- `tests/test_consortium_ui.py`
- `tests/test_factory_ui.py`
- `tests/test_factory_view_v2.py`
- `tests/test_industriova_release_integration.py`
- `tests/test_phase8_contract_balance.py`
- `tests/test_phase8_contract_ui.py`
- `src/production_zero/core/freight_settlement.py`
- `src/production_zero/ui/resource_prices.py`
- `tests/consortium_freight_fixture.py`
- `tests/test_phase9_freight_only.py`
- `tests/test_phase9_navigation_ui.py`

Die zwei neuen produktiven Dateien sind `core/freight_settlement.py` und `ui/resource_prices.py`. Die übrigen produktiven Änderungen liegen in elf bestehenden Dateien. Preis-/Rezeptkataloge, Produktionsketten, MK-/Rarityformeln, Infrastrukturpreise, Research-/XP-Regeln und Serializer/Writer bleiben unverändert. Auditwerkzeuge und Bericht stehen zusätzlich unter `scripts/phase9_*.py` und `docs/industriova-03-phase9-ui-consortium-report.md`.

## 2. Entfernte direkte Beitragspfade

`ContributionDialog` und `_show_contribution` sind aus der Consortium-UI entfernt. Es gibt keinen manuellen Mengenpicker, keinen direkten Storage-Spendenhinweis und keinen spielbaren CONTRIBUTE-Button mehr. „YOUR CONTRIBUTION“ bezeichnet weiterhin tatsächlich angenommene Freight-Ware.

`ConsortiumService.contribute` ist ein ausdrücklich ablehnender Kompatibilitätseinstieg: Jeder Aufruf endet vor jeder Änderung mit PermissionError. Der alte Command `ContributeToConsortiumContract` gelangt ausschließlich zu dieser Sperre. Lager, Fortschritt, Ablaufstatus, History und Receipts bleiben bei Ablehnung vollständig identisch; der CommandBus protokolliert keinen erfolgreichen Command. Auch die frühere öffentliche `receive_freight_delivery`-Signatur lehnt ab. Normale lokale und Remote-Serviceaufrufe können damit weder Storage abbuchen noch Fortschritt erzeugen.

## 3. Autorisierte Freight-only-Lieferarchitektur

Der bestehende Engine-Pfad `SimulationEngine._complete_outbound_shipments` bleibt der wirtschaftliche Abschluss. Er verarbeitet nur beendete, noch nicht wirtschaftlich verbuchte Sendungen. Ein kurzlebiges internes Abschlussrecht wird für genau dieses GameState-/Shipment-Paar in `_economic_arrival` ausgestellt. `_accept_freight_arrival` nimmt nur dieses Recht an; `_claim_arrival` konsumiert es einmalig. Es gibt keinen `is_freight=True`-Schalter und keine frei übergebbaren Waren-/Firmenparameter im neuen Annahmeeinstieg. Beliebige Objekte, Boolesche Werte, Request-Payloads und Rechte für andere Zustände werden abgelehnt. Das Recht existiert nur im synchronen internen Abschlusskontext und wird anschließend entfernt; es wird weder gespeichert noch an UI-/Netzwerkrequests ausgegeben.

Der lokale Netzwerkstub bleibt bestehen. Eine autoritative Remote-Firma durchläuft ihre eigene tatsächliche Engine-Abrechnung mit gemeinsamem Consortium-Netzwerk. Ein Client kann die alte Empfangsmethode nicht mehr mit einer behaupteten Sendungs-ID aufrufen. Dies ist eine interne Anwendungsschnittstelle für vertrauenswürdigen Python-Programmcode, keine Sandbox gegen beliebigen im Prozess ausgeführten Fremdcode und kein neu implementierter Multiplayer-Server.

## 4. Effektive Consortium-Kapazität

Neue Angebote summieren je Produkt die belegte Mitgliedsrate `min(nachhaltige vollständige Produktionskette, effektive gesamte Freight-Leistung)`. Die vorhandene zentrale Kapazitätsplanung berücksichtigt konkrete Karten, MK, individuelle Rarity-Boni, Research, bezahlte kompatible Plätze, erreichbare Vorstufen, Strom/Brennstoff und endliche Lagerpuffer. Eigene uninstallierte Karten können nur vorhandene freie bezahlte kompatible Plätze nutzen. Spezialisierte Firmen tragen ausschließlich nachweisbare Produkte bei; unbekannte Firmen erzeugen keine Leistung.

Pause, aktuelle Warenbestände, Routenziel und laufender Tick ändern die Quote nicht. Ein tatsächlicher Besitz-/Ausbau-, Research- oder dauerhafter Konfigurationswechsel invalidiert neue Angebote; aktive Snapshots bleiben eingefroren. Es gibt keine Gratisfahrzeuge und keinen Ersatz durch Direktabgabe.

Mitgliedsbelege tragen im bestehenden Signaturfeld den Präfix `freight-only-v1:`. Alte P8-Belege über reine Produktionsleistung werden für neue Angebote nicht als Freight-Nachweis verwendet. Ihre historische Speicherung und bereits aktive Verträge bleiben unverändert. Remote-Belege müssen wie in P8 aus einem echten Firmenzustand stammen und für neue Angebote höchstens 24 Stunden alt sein. Das bestehende Cache-/Signaturmodell verhindert eine erneute vollständige Kettenanalyse bei jedem Paint.

Die vorhandene Serienformel bleibt: Für Auswahl i, Preis p und Rate r ist `V = T / Σ[1/(r_i × p_i)]`, anschließend `q_i = max(1, floor(V/p_i))`. Daily T=120 und Weekly T=480 Planminuten, drei bzw. vier manuelle Produkte. Diese Kalibrierung ist keine Zeitgarantie; Batches, gemeinsame Vorstufen, Anlauf und Routen beeinflussen die reale Dauer.

## 5. Erhalt der P8-Rewards und alten Snapshots

Daily weiterhin ungefähr +15 %, Weekly +25 % auf den eigenen eingebrachten eingefrorenen Sell-Warenwert. Der maximale Cash-/XP-Pool, die persönliche anteilige Quote, Value-Research, vorhandene RP-Schwellen, Mitgliederrechte, Startberechtigung, Verfall bei Austritt/Ausschluss und einmalige Consortium-XP bleiben P8-Regeln. Kein erneutes Verkaufen angenommener Vertragsware und keine neue XP-/RP-Kurve.

Alte aktive Version-0- und P8-Version-1-Verträge behalten Anforderungen, bereits bestätigte Beiträge, persönliche Rewards, XP/RP-Schwellen und Receipts. **Auch diese alten Verträge akzeptieren ab P9 ausschließlich Freight.** Produktionsbasierte alte große Ziele können deshalb mit einer schwachen Flotte schwerer oder vor Ablauf nicht mehr erreichbar sein. Es gibt keine stille Kürzung, Laufzeitverlängerung oder Nachvergütung. Der ursprüngliche Snapshot ist maßgeblich.

## 6. P6-Statistik, Reservierungen und Fallback

Dispatch entnimmt/reserviert wie bisher einmalig Global Storage. Erst die Ankunft bucht den angenommenen Anteil; es gibt keinen zweiten Storage-Abzug. Ungültige/abgelaufene/erneuerte/erfüllte Ziele, ausgeschiedene Mitglieder und Überschüsse verwenden den vorhandenen Sell-Fallback. Die P6-Allokation erhält ausschließlich wirtschaftlich angenommene Mengen: Sell + Contract + Consortium = tatsächliche Sendungsmenge.

Das ausdrücklich nachgestellte Schiffsbeispiel läuft durch einen normal gekauften und installierten Ship, echten Dispatch und eine getrennte vorzeitige Mitgliederlieferung: **10.000 Cargo → 6.000 Consortium + 4.000 Sell = 10.000 Total**. Lager nach Dispatch und nach Ankunft jeweils 0; 4.000 Sell-Cash plus der eingefrorene Altvertragsreward von 123, genau einmal. Originalobjekt-, kopierter Receipt- und Save/Load-Retry ändern danach keine Wirtschaftsdaten. Nachweis `ship-allocation-proof.json`; es ist eine finanzierte Testfirma mit endlichem Lager, kein organischer Progressionslauf.

`economic_processed` verhindert die erneute Verarbeitung desselben Abschlussobjekts. Firmengebundene P8-Receipts unterscheiden identische lokale Freight-IDs verschiedener Firmen. Ein bereits bestätigter Receipt wird außerdem vor Status-/Mitgliedschaftsprüfung in aktuellem Vertrag oder aufbewahrter Historie erkannt: Ein Retry darf nicht als zweiter Sell-Fallback Geld erzeugen. Die vorhandenen Reward- und Consortium-XP-Flags sichern einmalige Auszahlung. Keine neue unbegrenzte Freight-ID-Datenhaltung; die vorhandene Contract-Historie bleibt begrenzt.

Der Rename-Einstieg erhält den bestehenden vollständigen P6-Header-Hovertext. Der sichtbare Stift hat seinen eigenen Rename-Hover. Die vier vorhandenen Istlieferwerte bleiben im Header lesbar.

## 7. Storage und Resources

Der Storage-Kasten bleibt erhalten. EXPAND sitzt als kleiner 98×28-Mindestbutton oben rechts; sein Hover zeigt die zentrale aktuelle Ausbauquote. RESOURCES liegt darunter im selben Storage-Panel und öffnet denselben vorhandenen globalen Drawer. Der Storage-Wert verwendet jetzt die vorhandene passende Metrikschriftanpassung, damit auch unter engem Layout keine Zeichenhöhe abgeschnitten wird. Cash-/Kapazitätsprüfung und Ausbaucommand bleiben unverändert.

## 8. History und Inbox

Die **vorhandenen beiden Buttons** des EventFeedWidget werden in die frei gewordene obere Operationsfläche umgehängt. Kein zweiter Feed, keine zweite Inbox und keine Kopie der Kommunikationsdaten. Unread-Badge, persistente Messages, Mark-read-Verhalten, vorhandene Activity-History und laufender Ticker bleiben erhalten. History und Inbox verwenden dieselbe vorhandene Popup-Geometrie. Geschlossene und bereits freigegebene Popups werden sicher behandelt; wiederholtes Öffnen/Schließen und Load/New Game lassen keine veralteten Qt-Referenzen zurück.

## 9. Frontscreen-Navigation

Resources, Factory und Energy verlassen Guide, Chain-/Editansicht und Resource-Drawer beim erneuten Haupttab-Eintritt; das vorhandene unterlegte Board und seine Caches bleiben verwendbar. Freight verwirft den unbestätigten Routenentwurf und zeigt wieder sein Board. Contracts schließt den Produktpicker und verwirft unbestätigte Auswahl; Consortium schließt Picker/Unterdialoge und öffnet OVERVIEW. Research schließt den Spezialisierungspicker und die unbestätigte Full-Respec-Vorschau; der Forschungsbaum bleibt erhalten. Der optionale Charts-Tab öffnet die bestehende Übersicht.

Globale Ressourcen-, History-, Inbox- und Profiloverlays schließen beim Haupttabwechsel. Modale Kauf-/Install-/Rename-/Leaderboarddialoge behalten ihre vorhandenen Bestätigungsregeln; normale Mausklicks navigieren während dieser modalen Entscheidung nicht durch den Hintergrund. Load/New Game verwerfen wie bisher die alten Dialoge und Board-/Pickerreferenzen. Keine der neuen Eintrittsaktionen dispatcht Kauf, Verkauf, Upgrade, Research, Beitrag oder Route.

P1-Dirty-/Entry-Refresh und unveränderte Board-/Kachel-/Graphcaches bleiben Grundlage. Es gibt keinen erzwungenen kompletten Sessionreset bei jedem Tabwechsel.

## 10. Rename-Stiftsymbole

Resources-Sites, Factory Halls, Energy Facilities und Freight Facilities zeigen einen kleinen Vektorstift im vorhandenen Header. Er ist ohne zusätzliche Symbolfont/Bitmapdatei renderbar, hat Tooltip und zugänglichen Namen und ruft dieselbe bestehende Rename-Funktion auf. Titelklick und vorhandene Bauminteraktionen bleiben erhalten. Keine zweite Namensverwaltung, keine neue Gebäudeklasse und kein zusätzlicher wirtschaftlicher Rename-Pfad. Extremnamen verwenden reservierten Stiftplatz und gezielte Elision; der vollständige Name bleibt im Hover.

## 11. Ressourcenpreise

Global Resources sowie vorhandene Resources-/Factory-Resource-Drawer zeigen `BASE SELL PRICE: $… / UNIT`. Die Guide- und Produktionsauswahlkacheln verwenden die platzsparende Form `BASE SELL $…/U`; der vollständige Basispreis steht im Hover. Diese Kürzung verhindert, dass der Preiswert selbst hinter einer langen Beschriftung verschwindet. Bestehende Namen, Unlockhinweise und Kategorien bleiben über Metadaten/Hover erreichbar.

`ui/resource_prices.py` formatiert ausschließlich Ergebnisse von `market_price_for` und `market_sale_price`; es berechnet keine neue Preisökonomie. Im Resource-Drawer-Hover steht getrennt der aktuelle `EFFECTIVE SELL PRICE` einschließlich Research. Basispreis bleibt Basispreis; Research ändert den tatsächlichen Sellwert über die vorhandene zentrale Funktion. Kleine Werte erhalten bei Bedarf wissenschaftliche Darstellung, normale Werte bis vier Nachkommastellen, große kompakte Kachelwerte vier signifikante Stellen; die zugrunde liegenden Preiswerte bleiben unverändert. Kein Market-Tab und keine dynamische Marktmechanik wurden ergänzt.

## 12. Textlayout

Line-Plaketten dimensionieren ihre Breite aus derselben Schrift und den tatsächlichen Innenabständen des vorhandenen Renderers. RAIL LINE und SHIPPING LINE bleiben dadurch vollständig sichtbar. Produktionsgebäude reservieren Platz für den Stift; Freight-Titel nutzen ihren vorhandenen Schriftfit mit zusätzlichem reserviertem Bereich. Main-Tab-Header elidieren lange Titel und zeigen den vollständigen Text im Hover, statt ihn unter Statusmodulen abzuschneiden. Resource-Zeilen haben ausreichend Höhe für die zusätzliche Preiszeile; Name/Preis bleiben mit gezielter Elision und vollständigen Hoverinformationen erreichbar. Kein globaler Stilwechsel.

## 13. Performance und Payload

Identische Vorher-Quellen aus der geprüften P9-Vorsicherung gegen den finalen P9-Stand. Windows / Python 3.12 / Qt offscreen, explizit geladene vorhandene Fonts, 100 %, gleiche Kataloge und Datenmengen. Je sieben **serielle** Stichproben, getrennt von Tests, Simulationen und Hashprüfungen. Zahlen: Median / Maximum in ms, keine native FPS-/p95-Garantie.

Die Contract-Probe enthält 500 Karten, 353 Produkte und zehn belegte Mitglieder. Zusätzlich 500 wirtschaftliche Consortium-Ankünfte bei 40 historischen Verträgen; dies ist ausdrücklich synthetischer bereits reservierter Ankunftsstress. Die reale Reservierung/Produktion wird separat durch Tests und Frachtläufe geprüft. Die MainWindow-Probe umfasst alle regulären Haupttabs, History/Inbox, 353 gelagerte Produkte mit je 0,001 Testbestand und 500 tatsächliche Truck-Karten in einer absichtlich übergroßen Einzelfacility. Die zusätzlichen Preiszeilen ändern die sichtbare Zeilenzahl bei gleicher Fläche; das wird nicht als kleinere Datenmenge oder FPS-Gewinn ausgegeben.

| Messung | P8 vorher Median / Max ms | P9 nachher Median / Max ms |
| --- | --- | --- |
| generation.warm | 7.292 / 9.079 | 6.905 / 7.859 |
| generation.capacity_change | 29.198 / 32.670 | 24.331 / 29.338 |
| quote.selection | 1.161 / 21.615 | 1.261 / 14.634 |
| accept | 35.804 / 42.298 | 36.803 / 48.396 |
| complete | 0.036 / 0.096 | 0.036 / 0.096 |
| tick.first | 26.291 / 63.574 | 22.952 / 55.938 |
| tick.warm | 5.596 / 6.958 | 4.695 / 5.334 |
| complete.500_arrivals | 8.444 / 10.433 | 7.633 / 49.654 |
| consortium.500_arrivals_40_history | 14.082 / 16.159 | 20.324 / 23.897 |
| consortium.candidates.10_members | 1.684 / 6.986 | 1.710 / 5.585 |
| consortium.preview.10_members | 1.768 / 1.837 | 1.779 / 2.110 |
| ui.contracts.unchanged | 5.770 / 7.186 | 6.386 / 7.388 |
| ui.consortium.unchanged | 1.358 / 1.681 | 1.442 / 2.412 |
| ui.20_tab_switches | 987.877 / 1006.870 | 989.074 / 1003.706 |
| snapshot | 16.567 / 17.425 | 17.745 / 19.882 |
| json_encoding | 10.225 / 13.659 | 11.193 / 13.329 |
| save | 44.564 / 45.362 | 50.408 / 53.287 |
| load | 25.082 / 28.685 | 26.873 / 31.661 |
| main.20_tab_switches | 923.599 / 1008.833 | 838.997 / 889.082 |
| main.history_inbox_pair | 15.200 / 17.602 | 15.611 / 18.512 |
| main.global_resources_pair | 241.174 / 498.320 | 294.463 / 730.390 |
| main.global_prices_353_refresh | 241.220 / 276.000 | 238.230 / 259.216 |
| main.energy_runtime | 8.011 / 9.141 | 7.603 / 8.423 |
| main.factory_runtime | 17.909 / 19.853 | 16.674 / 17.165 |
| main.resources_runtime | 41.712 / 44.126 | 38.381 / 39.376 |
| freight.500_runtime | 286.909 / 359.352 | 291.494 / 342.845 |
| freight.route_switch | 277.152 / 311.918 | 295.682 / 316.970 |
| main.header_refresh | 1.860 / 5.615 | 2.082 / 5.593 |
| main.snapshot_large_freight | 9.566 / 11.048 | 11.160 / 13.433 |

Vollständiger Contract-Benchmark-Payload: **836,519 → 836,999 Bytes**, Differenz +480. Neue UI- und Abschlussrechte werden nicht gespeichert. Änderungen entstehen nur in vorhandenen Kapazitätssignaturen/-werten neuer Consortium-Angebote. Kein zusätzliches wachsendes UI-/Preisregister. Bereits bekannte P8-Reward-Receipts bleiben ein dauerhaftes Anspruchsledger und können weiter wachsen; P9 behauptet hierfür keine konstante Größe. Rohreihen stehen unter `performance/before` und `performance/after`.

Konkrete Kosten bleiben sichtbar: 500 Consortium-Ankünfte mit voller 40er-Historie steigen im Median von 14,082 auf 20,324 ms durch den zusätzlichen Annahme-/Retrypfad. Öffnen/Schließen der kompletten 353er-Ressourcenübersicht steigt von 241,174 auf 294,463 ms; ihr laufender Refresh bleibt mit 241,220 → 238,230 ms auf vergleichbarem Niveau. Schnelle Routewechsel im künstlichen 500er-Gebäude liegen bei 277,152 → 295,682 ms. Zwanzig echte MainWindow-Tabwechsel verbessern sich dagegen von 923,599 auf 838,997 ms. Das ist keine pauschale Beschleunigung: Die vollständige Ressourcenliste und übergroße Freight-Flächen bleiben spürbar teuer. Die Preise erzeugen keine neue wiederkehrende Kettenanalyse; zusätzliche UI-Zeilen und die Annahmeprüfung sind dennoch reale Arbeit. Speicher-/Savezeitstreuung wird nicht allein der kleinen Payload-Differenz kausal zugeschrieben.

## 14. Save-Schema und Migration

**Schema 9 bleibt bestehen.** Es ist kein neues persistentes Feld erforderlich: Lieferregel ist Verhalten, neue Quote verwendet bestehende Kapazitätsfelder, Rechte und UI-Entwürfe sind transient. `phase9_migration_audit.py` öffnet ausschließlich die 16 ursprünglichen historischen Sicherungsfälle read-only/immutable. Sämtliche vollständig normalisierten P9-Payloads sind SHA256-genau gleich zu den finalen P8-Ergebnissen, wiederholtes Laden idempotent. Damit bleiben Karten/Inventory, bezahlte Gebäude/Slots, MK/Rarity/Investitionen, Produktions-Teilzyklen, aktive Sendungen, Snapshot-Rewards, individuelle Beiträge, Receipts, Cash/XP/RP erhalten. Zusätzliche P9-Tests prüfen aktive Sendungen vor/nach Ankunft und den Lieferregelwechsel für alte aktive Snapshots.

Originale persönliche Saves wurden nicht mit dem Loader geöffnet oder migriert. Abschließende Original-SHA256 für alle fünf Saves und alle 4.083 vorhandenen Build-Dateien unverändert. P8-Archivkette und 438 gepinnte P8-Artefaktdateien sind ebenfalls unverändert; Nachweise `protected-verification.json` und Backupmanifeste.

## 15. Tests und echte Freight-Simulationen

Finale vollständige Regression: **1,938 Fälle / 95 Module**, 0 Fehler/Skips. `regression-summary.json` vergleicht die Multimenge `(classname, testcase-name)` gegen alle 93 finalen P8-Module: sämtliche 1.869 Identitäten erhalten. Die bisherigen Direktbeitragsfälle nutzen jetzt echte endliche Freight-Dispatch-/Advance-/Abschlussfixtures; ihre Storage-, Reward-, Rollen-, Snapshot- und Retry-Assertions bleiben erhalten. Neue Sperrtests prüfen die produktiven alten API-/Commandpfade ausdrücklich als vollständig mutierungsfreie Ablehnung. Der erste Lauf fand überholte Text-/Tooltip-Erwartungen und Layoutfehler; Diagnoseergebnisse bleiben erhalten. Nach den letzten produktiven Korrekturen läuft die vollständige Suite erneut auf dem eingefrorenen finalen Quellstand; keine Teilmenge ersetzt diesen letzten Gesamtlauf.

Neu: 38 Freight-only-Corefälle und 31 UI-/Navigationsfälle. Abgedeckt sind alte/neue Vertragsversionen, öffentliche und gefälschte Abschlussaufrufe, Dispatch/Ankunft, zwei getrennte Firmen mit identischen lokalen IDs, Mitgliedschaftsverlust, Ablauf, erfülltes/erneuertes/aufgelöstes Ziel, Teilannahme/Sell, P6-Allokation, doppelte Original-/kopierte Receipts, Save/Load, eingefrorene Rewards und RP, ungleiche Mitglieder, fehlende Flotte, Pause und Routenwechsel. UI: Storage-Ausbau, Resources, History/Inbox/Unread/Ticker, Profil, alle drei Produktionsboards, Freight-Entwurf, persönliche/Consortium-Picker, Research-Spezialisierung/Respec, optionale Charts, New Game/Load, vier Rename-Bereiche, Line-Texte, Preise/Research sowie kleine/große Zahlen. Zusätzlich 218 Fälle bei 200 %, nicht doppelt zur Gesamtfallzahl gezählt.

26 gepaarte Freight-Szenarien je Version: dieselben Firmenstände, feste UTC-Uhr, echte Engine je Firma, 30-Sekunden-Raster, endliches bezahltes Lager, keine Warennachfüllung. Die unveränderte externe Laboroptimierung cached nur die reine unveränderliche Arbeitswertmathematik; keine Waren, Zeit, Kapazität oder Zustandsmutation wird übersprungen. Sie ist in Performanceprozessen ausdrücklich nicht aktiv. P8 schließt 21/26 ab. P9 schließt alle 24 mit geeigneter Transportinfrastruktur ab; die beiden reinen No-Freight-Fälle erzeugen ausdrücklich kein startbares Angebot. Keine direkte Beitragsvariante wird als P9-Lieferweg simuliert. Nichtnegative Lagerbestände, Lagergrenzen, vollständiger Snapshot-Roundtrip und abgeräumte Restflüge sind für alle 24 gültigen P9-Läufe geprüft.

| Szenario | Art | P8 Minuten | P9 Minuten | P9 gesamte Warenmenge | P9 Reward-Receipts Cash |
| --- | --- | --- | --- | --- | --- |
| one-small | daily | 121.5 | 121.5 | 14,399 | 19,499.17 |
| one-small | weekly | 568.0 | 568.0 | 57,599 | 83,314.75 |
| two-small | daily | 122.0 | 122.0 | 28,798 | 38,998.34 |
| two-small | weekly | 590.0 | 590.0 | 115,198 | 166,629.49 |
| five-mid | daily | 114.0 | 114.0 | 127,548 | 172,726.09 |
| five-mid | weekly | 364.0 | 364.0 | 446,019 | 645,149.48 |
| ten-advanced | daily | 160.0 | 160.0 | 544,303 | 737,098.02 |
| ten-advanced | weekly | 568.0 | 568.0 | 2,087,697 | 3,019,774.48 |
| mixed | daily | 384.0 | 143.0 | 69,662 | 94,336.57 |
| mixed | weekly | 1440.0 (nicht abgeschlossen) | 573.0 | 268,873 | 388,914.49 |
| some-no-freight | daily | 241.5 | 121.5 | 14,399 | 19,499.17 |
| some-no-freight | weekly | 1214.5 | 568.0 | 57,599 | 83,314.75 |
| one-no-power | daily | 121.5 | 121.5 | 14,399 | 19,499.16 |
| one-no-power | weekly | 568.0 | 568.0 | 57,599 | 83,314.74 |
| strong-poor-freight | daily | 1440.0 (nicht abgeschlossen) | 122.5 | 9,599 | 12,998.91 |
| strong-poor-freight | weekly | 1440.0 (nicht abgeschlossen) | 483.0 | 38,397 | 55,539.75 |
| specialized | daily | 103.5 | 103.5 | 14,399 | 19,499.17 |
| specialized | weekly | 302.5 | 302.5 | 57,599 | 83,314.75 |
| member-leaves | daily | 232.5 | 232.5 | 28,798 | 37,507.94 |
| member-leaves | weekly | 1205.5 | 1205.5 | 115,198 | 165,009.50 |
| advanced-products | daily | 197.0 | 197.0 | 17,425 | 2,157,517.42 |
| advanced-products | weekly | 620.0 | 620.0 | 118,949 | 5,369,807.95 |
| mixed-products | daily | 132.5 | 132.5 | 53,905 | 184,149.37 |
| mixed-products | weekly | 775.5 | 775.5 | 148,698 | 682,370.21 |

Fristen und Zielzeiten bleiben verschieden: etwa 121,5 Minuten kleines Daily, 568 Minuten kleines Weekly, 197/620 Minuten komplexe Advanced-Products und bis 1.205,5 Minuten beim Mitgliederaustritt. Diese Laborläufe sind keine organisch erspielte Firma und keine Zusage optimaler menschlicher Routen. Reale entnommene Waren und zentrale Ankunftsabrechnung sind maßgeblich. Remote-Cash wird als bestehender Receipt-Anspruch ausgewiesen; der lokale Stub implementiert keine neue Online-Wallet-Abholung. Einzelne Wallets und Receipts stehen getrennt im JSON.

## 16. Visuelle Prüfung

**102 tatsächliche MainWindow-Aufnahmen** über 1366×768, 1600×980 und 1920×1080 jeweils bei Qt-Skalierung 100/200 %. Je Profil 17 Zustände: drei Produktionsboards, Guide-Preise, Storage/Global Resources, History-Kontext, leere/ungelesene/gefüllte Inbox, vier Freight-Facilities, Consortium-Übersicht, aktiver Freight-Lieferhinweis, bestehende Freight-Zuweisung und fehlende Freight-Kapazität.

`MainWindow.grab()` enthält separate Qt-Popups nicht. Deshalb gibt es zusätzlich **18 tatsächliche einzelne Popup-Aufnahmen** für History und leere/gefüllte Inbox, jeweils in allen sechs Konfigurationen. Keine erfundene Bildschirmkomposition. Main-History-/Inbox-Aufnahmen zeigen den darunterliegenden Kontext; die zugehörigen eigentlichen Popup-Pixel stehen unter `popups/`.

Alle **120 PNG-Größen und SHA256** geprüft; **14 finale Bilder tatsächlich betrachtet**, einschließlich sämtlicher sechs Größen-/DPI-Profile und aller drei Popup-Zustände. `visual-review.json` nennt genau diese Dateien. Die Bilder verwenden künstlich lange Namen, einen reifen Firmenstand und große P6-Anzeigemengen als Formatierungsfixtures. Die letzten rein transienten Navigationsergänzungen und die Header-Hoverkorrektur ändern die gezeigten Board-/Popup-Layouts nicht; sie sind zusätzlich am finalen MainWindow getestet. Erste Bilder mit zu langer Guide-Preisbeschriftung bleiben unter `screenshots-initial` erhalten, finale sichtbare Preise unter `screenshots`.

Bildbeispiele: [Guide mit lesbaren Preisen](<artifacts/phase9/screenshots/dpi1/production-guide-prices-1366x768.png>), [Shipping Line und P6 bei 200 %](<artifacts/phase9/screenshots/dpi2/freight-harbor-1366x768.png>), [Freight-Confirm](<artifacts/phase9/screenshots/dpi2/freight-assignment-confirmation-1600x980.png>), [tatsächliche Inbox](<artifacts/phase9/popups/dpi2/inbox-filled-popup-1366x768.png>).

## 17. Native Windows-Handabnahme

Offen bleibt die menschliche Abnahme mit nativer Windows-Maus, DWM/GPU, Mehrmonitor-/DPI-Wechsel, subjektivem Scroll-/Hovergefühl und langen Spielsitzungen. Qt-Offscreen/QTest, Pixelprüfung und gemessene Callbackzeiten werden nicht als native Handfreigabe ausgegeben. Der nächste Playtest sollte Tab-Rückkehr aus offenen Unteransichten, reale Ship-/Rail-Routen, P6-Header-Hover, 100/200-%-Drag/Wheel sowie Speichern unmittelbar vor/nach einer Ankunft abnehmen.

## 18. Risiken, Reproduktion und Stopp

Alte produktionsbasierte aktive Consortium-Ziele können durch Freight-only mehr Zeit oder Flottenausbau erfordern; ihre eingefrorenen Bedingungen bleiben bewusst erhalten. Konservative Planraten sind keine optimale globale Fabrik-/Routenlösung. Die gemessenen langen Weekly-/Mitgliederaustrittsfälle und die persönlichen XP-/RP-Anteile ungleicher Gruppen bleiben Playtestpunkte. Das vorhandene lokale Remote-Receiptmodell ersetzt keinen Onlineserver. Große Boards und vollständige Ressourcenlisten können weiterhin sichtbare Refreshkosten über einem 16-ms-Framebudget haben; die Tabelle zeigt tatsächliche Grenzen.

Reproduktion: `.venv/Scripts/python.exe scripts/phase8_run_tests.py . artifacts/phase9/<neuer-testordner> --workers 2 --timeout 600` für alle finalen Module. `phase9_final_validation.py` und `phase9_postchecks.py` dokumentieren die abschließende Reihenfolge; alte Evidenz nicht unbesehen überschreiben. Migration, Simulation, Main-/Popup-Captures je QT_SCALE_FACTOR=1/2 und Benchmarks stehen in den folgenden Werkzeugen. Nach Prüfungen alte Test-Previewpfade wiederherstellen, unveränderte Originale prüfen, Bericht und Delivery-Manifest erzeugen.

- `scripts/phase9_backup.py`
- `scripts/phase9_capture.py`
- `scripts/phase9_complete.py`
- `scripts/phase9_consortium_simulation.py`
- `scripts/phase9_contract_benchmark.py`
- `scripts/phase9_delivery_manifest.py`
- `scripts/phase9_evidence_summary.py`
- `scripts/phase9_final_validation.py`
- `scripts/phase9_finalize_tests.py`
- `scripts/phase9_migration_audit.py`
- `scripts/phase9_popup_capture.py`
- `scripts/phase9_postchecks.py`
- `scripts/phase9_preserve_legacy_outputs.py`
- `scripts/phase9_ship_allocation_proof.py`
- `scripts/phase9_ui_benchmark.py`
- `scripts/phase9_verify.py`
- `scripts/phase9_visual_review.py`
- `scripts/phase9_write_report.py`

`phase9_finalize_tests.py` dokumentiert ausschließlich eine frühere vollständige Modulergebnis-Reconciliation vor den letzten Nachkorrekturen; der finale vollständige 95-Modul-Lauf benötigt diese Reconciliation nicht. `final-source-sha256.json`, `implementation.diff`, `postchecks.json`, `regression-summary.json`, `visual-review.json` und `delivery-manifest.json` binden die endgültigen Ergebnisse und Dateien.

**Nach P9 gestoppt. Persönliche Saves und vorhandene Builds unverändert. Kein neuer Windows-Build und keine Folgefunktionen implementiert.**
