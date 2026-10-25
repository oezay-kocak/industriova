# INDUSTRIOVA 0.3 – P6: Tatsächliche Freight-Lieferstatistik

Stand: 22.10.2026. Ausschließlich P6 auf der tatsächlichen Arbeitskopie nach P5. Kein neuer Windows-Build, kein P7/P8, keine Preis-, Kapazitäts-, MK-, Rarity-, Research- oder Produktionsformel geändert.

## Sicherung und Erhaltung

Vor produktiven Änderungen: `artifacts/phase6/backup-20261022T105601Z` mit **51,578 Dateien / 30,239,068,604 Bytes**. Vollständiges SHA256-Inventar, inkrementelles Delta mit rekursiv erhaltener P5/P4/P3/P2/P1/P0-Kette und separat unabhängigem source-baseline.zip. Beide ZIPs CRC-geprüft; 855 extrahierte Quell-/Test-/Asset-/Skript-/Dokumentdateien gegen Manifest-SHA geprüft. Große Altarchive bleiben explizite pfad-/hashgebundene Abhängigkeiten. Archiv-/Manifest-/Saveprüfsummen: SHA256SUMS.json im Sicherungsordner.

Alle fünf persönlichen SQLite-Originale wurden nur lesend gesichert: Rohkopie plus konsistentes SQLite-Backup, fünfmal integrity_check=ok. Abschließend **24,374 geschützte Bestandsdateien und fünf persönliche Original-Saves SHA256-unverändert**. Bestehende Builds, Assets, Spieldaten, Preis-/MK-Regeln und P0–P5-Nachweise erhalten. Keine Originalmigration oder automatisches Speichern persönlicher Daten. Tests/AppData/SQLite ausschließlich isoliert unter artifacts/phase6; alte von Tests erneuerte PNG-Referenzen aus der Sicherung wiederhergestellt, frische Bilder unter P6 behalten.

Wiederherstellung ausschließlich in einen neuen Ordner nach Manifest und Prüfsummen, niemals pauschal über persönliche Saves und niemals auf Git-HEAD zurücksetzen.

## Tatsächlich geänderte Komponenten

| Pfad unter src/production_zero | Änderung |
| --- | --- |
| core/freight_statistics.py (neu) | Begrenzte Zeitaggregate, abgeleitete laufende Fahrzeug-/Facility-Indizes, Warm-up und detachter Snapshot. |
| core/freight.py | Herkunft auf Sendungen, kleiner wirtschaftlicher Abschlussmarker, Statistik im FreightState, bounded Feed-Puffer und Vermeidung wiederverwendeter historisch belegter Facility-IDs. |
| core/simulation.py | Statistik nach endgültiger wirtschaftlicher Allokation im bestehenden zentralen Abschluss; monotone Simulationszeit und echte Ankunftszeit bei Zeitsprüngen. |
| persistence/sqlite_store.py | Schema 7, Statistik-Snapshot, sichere leere Migration und eindeutige Herkunftsauflösung für alte aktive Sendungen; separate Vorsicherung beim Laden von Schema 6. |
| ui/freight_statistics.py (neu) | Gemeinsame lesbare Ist-Raten, kompakte Headerzahlen und exakte Hoverwerte. |
| ui/freight_view.py | Statistik im konkreten Facility-Header, Ist-Zeile im vorhandenen Hover, Runtime-Wiederverwendung und direkte Referenz auf den aktuellen Header. |
| ui/freight_lines.py | Nur lokale Breite der vorhandenen Freight-Warnplakette an deren bestehende Schrift/Innenabstände angepasst. |
| ui/event_feed.py | Sequenz-Watermark statt Listenindex, damit der bestehende Feed nach Puffer-Rollover weiterarbeitet. |

Bestandstests: test_phase2_inventory_backend.py erwartet jetzt ausdrücklich Schema 7; test_paid_templates.py prüft zusätzlich die eindeutig migrierte Herkunft und weiterhin alle alten Sendungsfelder; test_recipe_retirement.py ändert ausschließlich das Capture-Ziel auf P6. Zwei neue P6-Testmodule, eigene Audit-/Capture-/Messskripte. Vollständiger tatsächlicher Delta gegen die Vorsicherung: implementation.diff; Dateiliste und SHA256: deliverables-manifest.json.

## Zeitstruktur, Berechnung und begrenzte Retention

Eine autoritative Sammlung belegter **Ein-Sekunden-Buckets** enthält je (Fahrzeugkarten-ID, Herkunfts-Facility-ID) die drei Mengen Sell/Contract/Consortium. Die Zielgruppe ist durch die Spalte gegeben; jedes Ereignis trägt damit ID, Herkunft, endgültige Aufteilung und Simulationszeit. Mehrere Abschlüsse desselben Besitzers in derselben Sekunde werden zusammengefasst. Keine vollständige Ereignis-/Sendungsliste und kein neues Set abgeschlossener Sendungs-IDs.

Anzeige: Buckets mit `floor(now)-60 < bucket <= floor(now)`. Retention: `floor(now)-600 < bucket <= floor(now)`, höchstens 600 belegte Sekunden. Zeitauflösung ausdrücklich eine Simulationssekunde; bei Untersekundenaufrufen kann eine Lieferung gegenüber einem kontinuierlich exakten Zeitfenster bis zu knapp einer Sekunde früher herausfallen. An ganzzahligen Simulationsgrenzen ist das 60-Sekunden-Fenster exakt.

Raten: Zielmenge × 60 / min(60, beobachtete Simulationssekunden); Total ist die Summe der drei Zielraten. Bei null Beobachtungszeit ausschließlich MEASURING…, während der ersten Minute normierte Rate mit klarer MEASURING-Kennzeichnung und Beobachtungsdauer. Ab 60 Sekunden voller Nenner. Nach einer Minute ohne Lieferung fällt die Rate auf null. Kein Nenner aus aktiven Fahrzeugen oder deren Fahrzeit.

Die Statistik besitzt ihren eigenen persistierten monotonen Simulationssekundenzähler ab Aktivierung/Migration. Jeder normale Engine-Advance erhöht ihn, auch wenn Karte/Linie/Facility pausiert ist oder keine Ware vorliegt. Stillstand der ganzen Anwendung ohne simulierte Zeit erfindet keine Offline-Lieferungen. Lange Sprünge werden begrenzt verarbeitet; keine Schleife über Milliarden übersprungener Sekunden. Bereits vor dem Schritt laufende Sendungen erhalten als Statistikzeit vorheriger Statistikzeitpunkt + damalige Restfahrzeit, statt einen alten Abschluss fälschlich ins aktuelle Minutenfenster zu schieben. Die vorhandene tickquantisierte Freight-Simulation bleibt unverändert.

Zwei flüchtige Summenindizes werden aus denselben Buckets abgeleitet: je Karten-ID und je Facility-ID. Abschluss-Eintrag und Header-/Tooltipabfrage sind O(1); beim Ablauf wird nur die aus dem Minutenfenster fallende Aggregation abgezogen. Zeitpflege prüft höchstens 600 belegte Bucket-Schlüssel; große Sprünge können die begrenzten noch relevanten Aggregate einmal neu indexieren. Snapshots speichern ausschließlich die Buckets/Zeit, keine zweite Gebäudewahrheit oder UI-Historienlisten. Kleine IEEE-754-Rundungsdifferenzen beim Neuindexieren sind möglich; Tests vergleichen Mengen numerisch und die gespeicherten Buckets exakt.

Karten- oder Gebäude-Verkauf schreibt Vergangenheit nicht um. Ihre Aggregationen bleiben für das begrenzte Mess-/Retentionsfenster bestehen und verschwinden danach samt abgeleiteten Indexeinträgen. Speicher ist bezüglich Sitzungsdauer begrenzt; er skaliert mit den innerhalb dieser zehn Minuten tatsächlich auftretenden Besitzerpaaren und belegten Sekunden. Keine falsche Behauptung eines konstanten Speichers unabhängig von Flottengröße oder Besitzerwechseln.

## Zentraler Abschluss und wirtschaftliche Zuordnung

Einziger Erfassungspunkt: SimulationEngine._complete_outbound_shipments, nachdem die vorhandene Wirtschaft den Abschluss verarbeitet hat. Sell zählt die tatsächlich verkaufte Menge; Contract die tatsächlich angenommene Menge; Consortium den Rückgabewert der bestehenden Annahme. Abgelehnter Rest läuft über den bestehenden Verkaufspfad und zählt ausschließlich Sell. Beispiel 40 Contract + 60 Sell = 100 Total, ohne zusätzliche 100 Contract. Routenwahl, Kauf, Installation, Dispatch, Reservierung, Upgrade, Move und Save/Load zählen nichts.

Ein vorhandener Membership-Fallback hatte ValueError/KeyError abgefangen, während fehlende Mitgliedschaft PermissionError auslöst. Die gleiche beabsichtigte Verkaufskonvertierung fängt jetzt auch diese konkrete Ausnahme ab. Keine neue Fallback- oder Preisregel. Contract-Expiry folgt weiterhin der vorhandenen UTC-Periodenerneuerung, Consortium-Expiry dessen bestehendem Service; angenommene Contract-Snapshots/Rewards werden nicht neu quotiert.

Der kleine economic_processed-Marker schützt ein bereits verarbeitetes Sendungsobjekt vor erneutem wirtschaftlichem Abschluss. Normale Abschlüsse werden weiterhin im selben synchronen Engine-Aufruf aus outbound_shipments entfernt, wirtschaftlich verarbeitet und erfasst. Kein persistierter unbeschränkter Receipt-Satz. SessionWriter bekommt wie zuvor einen vollständig detachten Snapshot; zwischen diesen synchronen Teilschritten wird kein Autosave eingereiht. SQLite-Slottransaktion und Writerarchitektur bleiben gleich.

Der vorhandene flüchtige Sell-Feed ist jetzt deque(maxlen=512); er ist kein statistisches Archiv und wird weiterhin nicht gespeichert. Der Consumer verwendet Delivery-Sequenzen statt der nach 512 konstanten Listenlänge. Bei extrem verspätetem Consumer können alte Feed-Details aus dem Puffer fallen; die vollständige Statistik innerhalb ihres Zeitfensters bleibt davon unabhängig. Bestehende Consortium-Service-Receipt-/Contractregeln bleiben unverändert.

## Fahrzeug- und Facility-Attribution

Neue Sendungen frieren die eindeutige Herkunfts-Facility bei Abfahrt ein. Alte Abschlüsse bleiben beim alten Gebäude, neue Abfahrten nach einem zulässigen Move gehören zum neuen. Fahrzeugtooltip summiert die eigene Karten-ID auch über einen Gebäudewechsel hinweg. Ein Facility-Header summiert die dort gestarteten relevanten Abschlüsse, einschließlich kürzlich verkaufter Karten; deshalb darf er nach einem Wechsel nicht einfach aus den heute installierten Karten rekonstruiert werden.

Neue Gebäude-IDs überspringen IDs, die noch in Statistikretention oder aktiven Herkunftssnapshots vorkommen. Dadurch bekommt ein neu gebautes Gebäude innerhalb des Zeitfensters keine alte Statistik eines entfernten Gebäudes. Nach vollständiger Retention ist die Vergangenheit entfernt. Umbenennen ändert die ID nicht.

Bei Migration alter aktiver Sendungen wird Herkunft nur bei genau einer realen Slotplatzierung ermittelt. Fehlt diese oder ist sie korrupt mehrdeutig, bleibt Herkunft unbekannt: Fahrzeugmenge wird erfasst, keine fremde Facility wird geraten. Reguläre alte Saves mit eindeutiger Installation erhalten die richtige Herkunft.

## Schema 7, Migration und Rollback

Schema 6 → 7 ergänzt leere Statistik/Warm-up und Herkunft bestehender aktiver Sendungen. Alle alten Karten, MK/Rarity/Investitionen, Slots, Routes, Contract-Snapshots, Ladung, Kapazität, Restfahrzeit und Preise bleiben erhalten. Laden zählt keinen Abschluss. Eine alte aktive Sendung zählt erst später bei der tatsächlichen Ankunft einmal. Bereits abgeschlossene Sendungen werden nicht rekonstruiert.

Beim SQLite-Laden von Schema 6 erzeugt der bestehende sichere Backupmechanismus eine separate .pre-industriova-v7.sqlite, ohne eine ältere v5-Vorsicherung zu überschreiben. Historische frühere Schemafälle behalten ihren bisherigen v5-Backupnamen. Die persönlichen Originale wurden zu Entwicklungszwecken niemals mit diesem Loader geöffnet.

**Rollbackgrenze:** Ein alter Schema-6-Loader kann neue Schema-7-Saves ablehnen. Für Rückkehr zum alten Programm den vor P6 gesicherten Schema-6-Save verwenden. Kein automatischer Down-Converter oder stilles Zurücksetzen aktueller Wirtschaftsdaten implementiert.

16/16 ursprüngliche historische Migrationsfälle bestanden, wiederholte Migration idempotent. Nach Entfernen ausschließlich der neuen Statistik-/Sendungsfelder und Rücksetzen nur des Schema-Metafelds entsprechen ihre vollständigen serialisierten Wirtschaftspayloads SHA256-genau den finalen P5-Ergebnissen. Nachweise migration-audit.json, einschließlich entire_business_payload_matches_p5. Zusätzliche neue Tests prüfen direkt Schema-6-aktive Sendungen, unbekannte Herkunft und v7-Vorsicherung.

## Header und Tooltip

Jeder ausgewählte Freight-Facility-Header zeigt SELL / CONTRACT / CONSORTIUM / TOTAL pro Minute. Keine globale Unternehmensstatistik ergänzt. Der vorhandene Header ist lokal von 140 auf 188 logische Pixel Mindesthöhe gewachsen; die zusätzlichen vier Werte werden direkt auf demselben vorhandenen Material gezeichnet. Keine vier zusätzlichen Kartenwidgets und kein großes Statistikfenster.

K/M/B/T-Kürzungen und wissenschaftliche Kleinstwerte verhindern lange Zahlentexte. Header-Hover enthält die ungekürzten Werte mit zwölf signifikanten Stellen, Beobachtungsdauer und Zeitfenster. Lange Titel werden mit passender vorhandener Schrift eingepasst beziehungsweise bei Extremnamen elidiert; voller Name im Hover. Lokale Freight-Line-Plaketten berücksichtigen Schriftbreite plus vorhandene Innenabstände, einschließlich SHIPPING LINE und RAIL LINE. Bestehende Sidebar-Elision bleibt erhalten; kein P9-Navigationsumbau.

Der vorhandene P5-Fahrzeughover behält THEORETICAL THROUGHPUT aus freight_stats und ergänzt getrennt ACTUAL THROUGHPUT. MK/Rarity/Research ändern weiterhin nur die vorhandene Theorieformel, bis wirklich neue Lieferungen abgeschlossen werden. Die Ist-Zeile aktualisiert sich im normalen Runtime-Refresh auf demselben Popup und denselben Kartenwidgets. Der Header verwendet eine direkte Referenz auf den aktuellen Header, damit ausstehend gelöschte Vorgänger nach einem Boardwechsel nicht versehentlich aktualisiert werden. Signaturgleiche Statistikupdates fordern kein neues Header-Repaint an.

## Tests und Regression

**1670/1670 Fälle in 89 Modulen bestanden; 0 Fehler, 0 Skips.** Alle 1.595 P5-Bestandsfälle mit derselben Fallzahl je bisherigem Modul erhalten, dazu 59 neue Core- und 16 neue UI-Fälle. Frischer Prozess und eigenes AppData je Modul; zwei Worker nur für die Regression. Summierte berichtete Modulzeiten 836.65 s, keine Wandzeit oder Performancezahl.

Erster vollständiger Lauf: 1.669 bestanden, ein alter Schema-5-Test verglich eine migrierte Sendung noch ohne das neue Herkunftsfeld. Ausschließlich dessen Erwartung ergänzt: Herkunft explizit garage-1, alle bisherigen Sendungswerte weiterhin identisch. Das vollständige 11-Fälle-Modul wurde danach grün wiederholt. Alle produktiven Quellen und die übrigen 88 Testmodule waren unverändert. final-tests/provenance.json benennt die Herkunft jedes vollständigen Modulergebnisses; full-tests/ und paid-template-rerun.* behalten den ursprünglichen Fehler und die vollständige Wiederholung. Kein Test entfernt oder übersprungen, keine Teilmengen als Gesamtfallzahl ausgegeben.

Neue Fälle: volle/teilweise Sell-Ladung, Contract/Consortium und partielle Restverkäufe, abgelaufene/abgebrochene Ziele, Membershipverlust, genau einmalige Verarbeitung, simultane Abschlüsse, Eigentümer-/Gebäudewechsel, Verkauf, vier Fahrzeugtypen, Pause/Busy-Upgrade, echte Engine-Zeitsprünge, Warm-up 0/10/30/60 Sekunden, zehn Minuten, Untersekunden-/Bucketgrenzen, alte aktive Sendungen und wiederholte SQLite-Roundtrips vor/nach Abschluss sowie pausiert/abgelaufen, detachter Snapshot und Schreibfehler, Feed-Rollover, fehlende/mehrdeutige Alt-Herkunft, winzige Mengen, lokale Headerwerte, Buildingwechsel, Theorie/Ist-Trennung und Widgetidentität. P1–P5 laufen vollständig weiter, einschließlich Inventory/Supply/Templates, P4 Swaps/Ghost/Scroll/Cleanup und P5 Routen/MK.

P4/P5/P6-Module zusätzlich bei Qt-Skalierung 200 % geprüft; diese zusätzlichen Fälle zählen nicht doppelt. Nachweise dpi2-tests.xml. Produktive Quellen sind gegenüber dem Start der ursprünglichen Gesamtsuite unverändert; endgültige Testquellen und Nachprüfungen gegen tested-source-sha256.json eingefroren. Frühe gezielte Entwicklungsversuche bleiben unter targeted-*.xml erhalten.

## Vorher/Nachher: Freight

Identischer P5-Quellstand aus der Vorsicherung gegen P6, gleicher Seed, gleicher Katalog, feste UTC-Uhr und gleiche Firmenformen. Sieben serielle Werte je Operation, ohne parallel laufende Tests/Builds/Messungen. 10/50/100/500 sind synthetisch übergroße Einzelfacilities. 20 Facilities/160 Fahrzeuge wurden über die vorhandenen regulären Build/Expand/Buy/Install-Commands aufgebaut. Nach 600 Simulationssekunden Engine-Warm-up werden sieben synchrone Ankunftsbatches vorbereitet, indem Restfahrzeit außerhalb der Messung auf eine Sekunde gesetzt wird. Das ist ausdrücklich synthetischer Abschlussstress; nachfolgende UI-/Saveproben enthalten diese belastete Historie.

Callback und Event-Drain stehen getrennt in den Rohwerten. Header vorher misst den bisherigen update()-Pfad, nachher die neue Statistikprüfung samt gegebenenfalls Paint; neue Arbeit ist keine behauptete Beschleunigung. Speicher enthält gemeinsame warme Qt-/Asset-Caches, keine isolierte GPU-/Leakmessung. Initiale Vorprobe ohne Abschlussbatches unter before/ erhalten, maßgeblich sind before-final/ und after-final/.

| Fahrzeuge / Firma | Operation | Vorher Median / Max ms | Nachher Median / Max ms |
| --- | --- | --- | --- |
| 10 | tick | 0.805 / 0.941 | 0.820 / 1.007 |
| 10 | completion_tick | 0.976 / 0.995 | 1.125 / 1.160 |
| 10 | freight_refresh | 29.112 / 101.014 | 23.633 / 89.467 |
| 10 | header_refresh | 2.680 / 3.488 | 0.014 / 0.093 |
| 10 | tooltip | 9.088 / 39.791 | 8.021 / 34.347 |
| 10 | snapshot | 1.308 / 1.899 | 1.138 / 1.667 |
| 10 | encoding | 1.220 / 1.397 | 1.288 / 1.384 |
| 10 | save | 22.538 / 38.884 | 9.249 / 9.792 |
| 10 | load | 7.763 / 21.146 | 7.539 / 21.172 |
| 50 | tick | 0.810 / 1.106 | 0.790 / 0.980 |
| 50 | completion_tick | 1.944 / 2.019 | 2.261 / 2.452 |
| 50 | freight_refresh | 41.123 / 46.149 | 33.271 / 41.865 |
| 50 | header_refresh | 2.388 / 2.562 | 0.014 / 0.090 |
| 50 | tooltip | 8.603 / 11.048 | 8.556 / 9.695 |
| 50 | snapshot | 1.938 / 2.201 | 2.217 / 3.099 |
| 50 | encoding | 1.729 / 1.884 | 2.647 / 2.799 |
| 50 | save | 22.567 / 53.536 | 11.457 / 13.603 |
| 50 | load | 8.539 / 10.720 | 10.081 / 11.172 |
| 100 | tick | 1.083 / 1.415 | 0.814 / 1.095 |
| 100 | completion_tick | 4.945 / 5.257 | 4.331 / 4.407 |
| 100 | freight_refresh | 59.111 / 118.105 | 46.170 / 80.251 |
| 100 | header_refresh | 2.369 / 2.647 | 0.016 / 0.090 |
| 100 | tooltip | 8.548 / 11.027 | 8.248 / 9.134 |
| 100 | snapshot | 2.466 / 2.940 | 2.694 / 17.920 |
| 100 | encoding | 2.393 / 2.448 | 3.303 / 3.483 |
| 100 | save | 22.359 / 44.656 | 16.991 / 17.528 |
| 100 | load | 11.677 / 14.899 | 14.199 / 15.793 |
| 500 | tick | 1.254 / 1.454 | 1.097 / 1.478 |
| 500 | completion_tick | 37.182 / 119.575 | 42.130 / 43.451 |
| 500 | freight_refresh | 215.870 / 677.850 | 157.698 / 497.676 |
| 500 | header_refresh | 3.147 / 3.457 | 0.020 / 0.076 |
| 500 | tooltip | 9.274 / 11.157 | 7.527 / 8.536 |
| 500 | snapshot | 8.592 / 9.509 | 10.102 / 44.260 |
| 500 | encoding | 8.608 / 9.024 | 13.253 / 13.590 |
| 500 | save | 40.532 / 78.242 | 39.298 / 86.300 |
| 500 | load | 26.933 / 42.002 | 51.049 / 89.466 |
| 20-facilities | tick | 0.936 / 1.549 | 0.946 / 1.218 |
| 20-facilities | completion_tick | 8.689 / 8.867 | 7.979 / 8.592 |
| 20-facilities | freight_refresh | 30.758 / 47.366 | 26.431 / 36.077 |
| 20-facilities | header_refresh | 2.853 / 3.014 | 0.020 / 0.094 |
| 20-facilities | tooltip | 10.979 / 12.188 | 9.291 / 10.037 |
| 20-facilities | snapshot | 3.465 / 4.254 | 4.346 / 5.332 |
| 20-facilities | encoding | 3.444 / 3.653 | 5.513 / 5.731 |
| 20-facilities | save | 17.412 / 123.450 | 22.427 / 22.826 |
| 20-facilities | load | 12.984 / 16.157 | 26.821 / 56.389 |

| Firma | Payload Bytes vorher → nachher | Statistik Bytes nachher | Working Set MiB vorher → nachher | Widgets vorher → nachher |
| --- | --- | --- | --- | --- |
| 10 | 81,550 → 88,430 | 6,255 | 91.09 → 89.21 | 248 → 250 |
| 50 | 125,751 → 159,991 | 31,215 | 110.77 → 110.13 | 993 → 995 |
| 100 | 181,203 → 249,643 | 62,415 | 135.17 → 135.06 | 1921 → 1923 |
| 500 | 626,404 → 974,844 | 318,415 | 307.11 → 309.43 | 9371 → 9373 |
| 20-facilities | 277,438 → 478,654 | 191,023 | 181.34 → 175.07 | 201 → 203 |

Die größere Headerhöhe verändert bei gleicher Fenstergröße den sichtbaren Boardausschnitt. Geringere Paintzeiten sind deshalb kein Beweis einer schnelleren Kartensimulation. Die zusätzlichen gespeicherten Aggregate erzeugen messbare Lade-/Encodingkosten, insbesondere bei 500 Fahrzeugen und den künstlich beschleunigten Ankunftsbatches.

## P1–P5-Kontrollen

Unveränderte P0/P1-Workloads mit sieben frischen UI-/Kaufprozessen, warmen UI-Reihen bis 49 Werten, aktiven 10/50/100/500-Firmen und sieben erweiterten Commandaktionen; P2-Erwerb 1/10/100/1000 und Projektionen 500/5000/10000; P3 alle sechs vollständigen Inventory-Fixtures; P4 Gruppen-/Swap-/Pointerflächen; P5 explizite Routen und sichtbarer Einzel-MK-Pfad. Gleiche Definitionen, keine verkleinerten Fixtures. Sämtliche Rohreihen unter before/ und after/, aggregierte P1-Tabelle comparison-tables.md.

| P1-Kontrolle | Vorher Median / Max ms | Nachher Median / Max ms |
| --- | --- | --- |
| ui:guide.first_open | 583.92 / 648.29 | 473.52 / 495.20 |
| ui:leaderboard.changed_refresh | 0.26 / 0.97 | 0.20 / 0.46 |
| ui:unlock.constructor.cold | 95.63 / 116.22 | 92.23 / 108.09 |
| rapid_bursts:rapid_ui.50.20_individual_purchases | 473.20 / 483.19 | 480.91 / 490.71 |
| rapid_bursts:rapid_ui.500.20_individual_purchases | 521.47 / 630.96 | 478.03 / 517.22 |
| active:500.tick | 5.27 / 7.76 | 5.90 / 9.30 |
| active:500.snapshot | 132.30 / 142.90 | 129.85 / 142.77 |
| active:500.full_save | 224.88 / 269.52 | 218.05 / 266.10 |

P1-Kontrollen mit >10 % höherem Median und >1 ms nachher: active:10.tick 1.30 → 1.57 ms; active:500.refresh 5.68 → 6.67 ms; active:500.tick 5.27 → 5.90 ms; active:500.load 162.38 → 183.00 ms; extended:500.slots7 91.47 → 119.03 ms. Keine pauschale FPS- oder Beschleunigungszusage.

| P3 Inventory | Refresh vorher → nachher Median / Max ms | Kartenwidgets vorher → nachher | Payload Bytes vorher → nachher |
| --- | --- | --- | --- |
| 500-stacked | 8.54/8.76 → 7.77/8.38 | 3 → 3 | 207291 → 207342 |
| 500-distinct | 45.94/48.61 → 44.89/46.96 | 42 → 42 | 207181 → 207232 |
| 5000-stacked | 31.73/33.01 → 21.74/22.86 | 3 → 3 | 1528791 → 1528842 |
| 5000-distinct | 94.16/121.60 → 73.75/97.67 | 42 → 42 | 1532681 → 1532732 |
| 10000-stacked | 37.76/39.97 → 37.62/39.31 | 3 → 3 | 2997123 → 2997174 |
| 10000-distinct | 122.52/130.84 → 152.76/164.51 | 42 → 42 | 3006013 → 3006064 |

Inventory-Payloads unterscheiden sich erwartungsgemäß um Schema 7 und leere Statistikfelder; keine Behauptung identischer vollständiger Save-Hashes. Zeilen-/Kartenanzahl und begrenzter Widgetpool erhalten. P2-Core-/Speicherwerte separat in inventory-benchmark.json.

| P4-Kontrolle | Vorher Median / Max ms | Nachher Median / Max ms |
| --- | --- | --- |
| 10.100_occupied_swaps | 2.19 / 2.34 | 2.09 / 2.24 |
| freight.10.100_pointer_moves | 11.38 / 45.76 | 13.06 / 52.47 |
| 50.100_occupied_swaps | 4.30 / 4.96 | 3.59 / 3.74 |
| freight.50.100_pointer_moves | 11.18 / 68.98 | 13.30 / 81.41 |
| 100.100_occupied_swaps | 5.55 / 5.64 | 5.58 / 5.79 |
| freight.100.100_pointer_moves | 11.22 / 104.28 | 14.50 / 112.14 |
| 500.100_occupied_swaps | 19.51 / 19.88 | 19.61 / 19.86 |
| freight.500.100_pointer_moves | 12.25 / 486.72 | 13.54 / 561.61 |

100 Pointerbewegungen werden als Qt-Burst mit anschließendem Event-Drain gemessen; keine 100 separat dargestellten nativen Frames. Production 10/50 regulär, 100/500 und alle übergroßen Freight-Flächen synthetisch.

| P5-Freight | Confirm/Return vorher → nachher Median / Max ms | MK vorher → nachher Median / Max ms | Tooltip vorher → nachher Median / Max ms |
| --- | --- | --- | --- |
| 20-facilities | 33.74/90.01 → 40.06/93.37 | 26.33/27.15 → 30.62/33.09 | 0.77/38.10 → 0.95/39.58 |
| 10 | 33.45/37.57 → 39.05/42.06 | 25.69/27.17 → 31.16/31.40 | 0.68/4.49 → 0.97/5.91 |
| 50 | 35.37/42.16 → 39.92/50.43 | 26.28/27.20 → 29.67/30.70 | 0.67/4.61 → 0.81/5.94 |
| 100 | 41.36/59.91 → 47.00/60.90 | 27.67/31.27 → 31.65/32.89 | 0.66/4.58 → 0.82/5.47 |
| 500 | 67.07/135.19 → 69.38/149.12 | 31.03/33.38 → 31.15/39.86 | 0.81/5.55 → 0.82/5.73 |

P5-Probe ist eine eigenständige FreightView ohne globale MainWindow-Hooks; sieben explizite wechselnde Routen/Upgrades, bestätigter Callback plus Events, Modalaufbau und menschliche Wartezeit durch Bestätigungsstub ausgeschlossen. 20-Facility-Variante regulär aufgebaut, übergroße einzelne Freight-Flächen synthetisch.

## Langzeit-/Speicherkosten

Eine Million synthetische Abschlussallokationen für 500 Fahrzeug-IDs in 20 Facilities, alle 500 Abschlüsse 60 Simulationssekunden weiter. Dieser separate Test prüft die begrenzte Aggregationsstruktur, keine Million vollständiger Wirtschafts-/UI-Abschlüsse. Tatsächliche zentrale Abschlüsse sind durch Engine-/Savefälle und completion_tick-Proben separat geprüft. tracemalloc nur in dieser Speicherprobe aktiv; instrumentierte Wandzeit nicht mit normalen Timingreihen vergleichen.

| Abschlüsse | Simulationssekunden | Buckets / Besitzerpaare | Python aktuell / Peak MiB | Statistik-Snapshot Bytes |
| --- | --- | --- | --- |
| 1,000 | 120 | 2 / 1000 | 0.43 / 0.43 | 43,328 |
| 100,000 | 12,000 | 10 / 5000 | 2.06 / 2.06 | 216,543 |
| 500,000 | 60,000 | 10 / 5000 | 3.21 / 3.21 | 216,543 |
| 1,000,000 | 120,000 | 10 / 5000 | 3.22 / 3.83 | 216,554 |

Nach weiteren 600 Sekunden sind Buckets und beide Besitzerindizes vollständig leer. Keine wachsende Sendungs-ID-Liste. Die Speicherprobe hält zusätzlich den jeweils letzten detachten Snapshot; Python-Zahlen enthalten diese Diagnosekopie und kurzfristige Allokationen, nicht ausschließlich die autoritative Statistik. Ein Zeitfenster begrenzt die Sitzungsdauerabhängigkeit; große Flotten verursachen weiterhin reale zusätzliche Snapshot-/Encoding-/Ladekosten. Die gemessenen großen Freight-Refreshes/Snapshots können über 16 ms liegen. Kleine Stichproben, Qt-Caches und Scheduling schwanken; die ausgewiesenen Kontrollregressionen bleiben als Beobachtung erhalten, unveränderte geschützte Teilpfade werden deswegen nicht stillschweigend umgebaut. Keine Aussage zu nativen Windows-FPS, DWM-/GPU-Latenz oder stundenlangem Betriebssystem-Working-Set.

## Visuelle Abnahme und offene Punkte

**102 tatsächliche MainWindow-Captures**, 51 je Skalierung, alle drei Größen 1366×768 / 1600×980 / 1920×1080 und Qt-Skalierung 100/200 %. Alle vier Facility-/Fahrzeugtypen, leeres Warm-up, kleine Menge mit MK1-Hover, hohe gemischte Ziele mit pausiertem MK50/Legendary-Hover, Null nach Fensterablauf sowie 20-Facility-Unternehmen. Tatsächliche PNG-Pixelgrößen und alle SHA256 geprüft. **7 Bilder tatsächlich betrachtet**, über alle sechs Größen-/DPI-Konfigurationen und alle vier Facility-Typen; visual-review.json nennt Dateien und Hashes.

Die Capture-Zustände sind isolierte Formatierungsfixtures. Absichtlich eingespeiste hohe Mengen können oberhalb der nominellen Fahrzeugleistung liegen; die Bilder belegen Lesbarkeit und Attribution, keine erspielte Leistung. Keine neuen Zahlenüberlagerungen oder abgeschnittenen Headerwerte in den betrachteten Proben. Lange Sidebar-Namen werden weiterhin wie bisher gekürzt. Der größere Header verringert den sichtbaren Boardausschnitt um 48 logische Pixel; vorhandenes Scrollen bleibt erhalten.

**Native Windows-Handabnahme offen.** Offscreen/QTest und betrachtete Bilder prüfen Qt-Zustände, Geometrie, Ereignisse und Lesbarkeit. Keine menschliche OLE-/Wheel-/DWM-/GPU- oder Mehrmonitor-Abnahme. Nächster nativer Playtest: jede Facility mehrfach wechseln, aktuelle Ist-Werte und exakten Header-Hover prüfen; Pause/fehlende Ware mindestens eine Minute beobachten; Busy-Upgrade und Move nach Ankunft; Speichern vor/nach Ankunft und neu laden; P4-Drag mit Randscrollen und Wheel bei beiden DPI weiter abnehmen.

## Reproduktion und Stopp

Neue Ausgabeverzeichnisse verwenden, vorhandene Nachweise nicht überschreiben. Vollständige Module: phase6_run_tests.py mit zwei Workern, je Modul eigenes AppData. phase6_finalize_tests.py dokumentiert die einmalige Bestands-Testreconciliation; phase6_postchecks.py prüft die finalen Quellen und führt DPI-/Visuell-/Vorher-/Nachher-/Stressproben seriell aus. phase6_migration_audit.py liest nur die 16 bereits gesicherten historischen Payloads. phase6_capture.py mit QT_SCALE_FACTOR=1/2; phase6_verify_visual.py dokumentiert die tatsächlich betrachteten Bilder. phase6_verify_protected.py prüft den tatsächlichen Working-Tree-Delta gegen Backup, nicht Git-HEAD. Bericht/Dateimanifest werden erst nach abgeschlossenen Nachweisen erzeugt; produktive Quellen/Tests bleiben dabei eingefroren.

**P6 abgeschlossen und hier gestoppt. Kein P7/P8, kein Balancing, kein neuer Windows-Build.**
