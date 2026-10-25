# INDUSTRIOVA 0.3 – Phase 2: Inventory-Backend und atomare Kartenoperationen

Stand: 21.10.2026. **Backend-Zwischenstand vor P3, kein spielbarer Build.** Ausschließlich P2. Keine neue Inventory-Oberfläche, kein Windows-Build und keine Änderung persönlicher Spielstände. Die unveränderte Shop-UI prüft teilweise weiterhin freie Slots und spricht von automatischer Installation; normale Backendkäufe erwerben bereits unplatzierte Karten. Diese bewusst akzeptierte Zwischenphasendifferenz wird erst in P3 aufgelöst.

## 1. Vorbereitung und Sicherung

Die vier verbindlichen P0-/P1-Berichte wurden vollständig gelesen. Arbeitsbasis sind die tatsächlichen gesicherten Quellen nach P1, einschließlich aller uncommitteten und ungetrackten Änderungen, nicht Git-HEAD.

`artifacts/phase2/backup-20261021T195615Z/` erfasst vor produktiven Änderungen **41.058 Dateien / 27.349.362.030 Quelldatei-Bytes**. Das SHA256-Manifest verweist unveränderte Inhalte auf die erhaltene P0-Basis und das P1-Delta; neue/geänderte Inhalte liegen im P2-Delta. Große bereits vorhandene Sicherungsarchive werden mit Pfad und Hash als unveränderliche Abhängigkeiten erhalten. Zur vollständigen Wiederherstellung sind diese im Manifest beschriebenen Komponenten erforderlich; dies ist keine alleinstehende Voll-ZIP. Ein unabhängiges `source-baseline.zip` enthält zusätzlich sämtliche aktuellen Quellen, Tests, Skripte, Dokumentation und Assets. Beide neuen ZIPs wurden per CRC geprüft. Vorher-Messquellen wurden daraus unter `artifacts/phase2/before-tree` wiederhergestellt.

Alle fünf persönlichen SQLite-Dateien wurden nur gelesen, roh kopiert und über SQLite read-only in konsistente Kopien gesichert; fünfmal `integrity_check=ok`. Tests verwenden eigene AppData-/Temp-Verzeichnisse. Wiederherstellung ausschließlich in einen neuen Ordner nach Manifest; keine automatische Rücksetzung oder Überlagerung persönlicher Saves.

## 2. Geänderte produktive Dateien und Wiederverwendung

Alle produktiven Pfade unter `src/production_zero/core/`:

| Datei | Änderung |
| --- | --- |
| `supply.py` | Gemeinsamer vorbereiteter Inventarerwerb für Common, Daily Machine/Energy und Daily Freight; ein Debit, eindeutige IDs und erfasster Anschaffungspreis. Tagesrotation auf einer getrennten Angebotsbuch-Kopie vor dem Commit. Gemeinsame Preisprüfung, Backend-MAX und optionale bestätigte Preisquote. Alter unvollständiger Supply-Kartenerzeuger entfernt. |
| `commands.py` | Bestehende Kaufcommands erhalten optionale Preisquote und Operations-ID. Neuer `ReturnMachinesToInventory`; bestehende Einzel-Remove-Commands delegieren dorthin. Installationen schützen aktive Freight-Referenzen; Freight prüft die erhaltene Route erneut. |
| `machine_operations.py` | Gemeinsame atomare Gruppenrücknahme; Verkauf prüft konkrete Karten und Definitionen vor Mutation, verwendet eine ID-Menge zur Slotbereinigung. Resale verwendet ausschließlich erfasste Investitionen. |
| `inventory.py` | Bestehende Platzierbarkeitsprojektion umfasst Production, Energy und Freight; dangling Slotreferenzen führen in der Anzeige nicht zum Absturz. |
| `state.py` | Ausschließlich flüchtige Operationsquittungen für die laufende Sitzung; keine zweite Bestandsverwaltung. |
| `production_templates.py` | Direkte Platzierung bleibt erhalten. Zusätzlicher Wiederholungsschutz, ID-Kollisions- und endliche Geldprüfung vor Debit. |

Unverändert: `CardInstance`, `CardStackKey`, MK-/Rarity-Berechnung, Simulation, physisches Warenlager, Definitionen/Preise/Rezeptkatalog, Forschungs-/Contract-/Consortium-Regeln, kompletter UI-Code, P1-Atlas/Caches und SQLite-/Snapshotimplementierung. Der bisherige `buy_and_install`-Helfer bleibt für vorhandene explizite Diagnoseaufrufe erhalten; keiner der normalen Supply-Kaufpfade ruft ihn auf. Template-Direktplatzierung verwendet ihren bestehenden Zielplan.

## 3. Commands und Transaktionsgrenzen

`BuyCommonSupplyCard`, `BuyDailyMachineSupplyCard`, `BuyDailyFreightSupplyCard`, `InstallCardInHall`, `InstallFreightCard`, `ReturnMachinesToInventory(card_ids)`, `SellMachines` und `PurchaseTemplates` bleiben synchrone Domain-Commands. Der CommandBus besitzt weiterhin keinen Rollback und protokolliert nur erfolgreiche Anwendungen.

Kauf: Angebot/Definition/Menge/Quote/Geld/Operations-ID prüfen → alle Karten mit IDs und Investition vorbereiten → Kollisionen prüfen → einmal abbuchen → Karten eintragen → Daily-Recht und Quittung übernehmen → Cash-History. Eine Ablehnung verändert weder Cash/Karten/Slots noch Angebote/Tagesrechte/Rezepte/Investitionen/Sendungen/History.

Rücknahme und Verkauf validieren die gesamte konkrete Gruppe vor der ersten Mutation. Doppelte IDs, fehlende Karten und aktive Sendungen lehnen die ganze Gruppe ab. Rücknahme verlangt genau eine bestehende Platzierung pro ID; auch beschädigte Doppelplatzierung wird atomar abgelehnt. Verkauf beseitigt erst nach vollständiger Prüfung die ausgewählten Kartenreferenzen und zahlt einmal aus.

## 4. Regulärer Erwerb und Backend-MAX

Common akzeptiert ausschließlich echte `int`-Mengen von 1 bis 10.000; insbesondere keine Bool-Werte, Float-/String-/Nullmengen, Null oder negativen Mengen. Kein Gebäude, keine freie Linie, kein Slot und kein physischer Lagerplatz sind erforderlich. Alle regulären Kartentypen werden MK1 mit Angebotsrarity/-bonus und individuellem Anschaffungspreis Eigentum in `GameState.cards`.

`common_supply_max_quantity(state, definitions, definition_id)` liefert `min(10000, max(0, floor(cash / common_card_price(definition))))`. Genau dieselbe Preisfunktion bestimmt den Common-Debit. Nicht bezahlbar bedeutet 0. Daily bleibt ein Kauf pro Kategorie und Spieltag; beide Kategorien sind unabhängig. Ungültiger/veralteter Daily-Kauf darf nicht einmal die Live-Angebotsrotation verändern.

`expected_unit_price` ist optional für bestehende Aufrufer; P3 kann die bestätigte Quote mitgeben. Ein veränderter Quote wird vor Debit abgelehnt. Die aktuelle UI wurde ausdrücklich nicht auf diese neue API umgebaut.

## 5. Schutz vor Wiederholungen

Jeder neue Kauf-/Templatecommand erhält eine UUID-Operations-ID. Ein bewusst neu erzeugter Command bedeutet einen neuen Kauf. Derselbe Command, seine vor dem Commit erstellte Kopie oder eine Wiederholung mit derselben ID wird auch über einen anderen Bus derselben Sitzung vor Debit abgelehnt. Fehlgeschlagene Käufe verbrauchen die ID nicht. Verkauf kann nach Entfernen der konkreten IDs keine zweite Auszahlung erzeugen.

Die Quittungsmenge lebt ausschließlich im aktuellen GameState und wird nicht gespeichert. Sie ist kein Inventory und keine serverseitige, über Neustarts gültige Transaktionsdatenbank; sie wächst mit erfolgreichen Kaufoperationen dieser Sitzung. New Game/Load beginnen eine neue Sitzung ohne alte Quittungen. P3 muss bei Wiederholung einer bestätigten Aktion deren Operations-ID wiederverwenden; eine zeitbasierte Sperre identischer bewusst neuer Käufe wurde nicht eingeführt.

## 6. Installation und Identität

Die bestehenden Install-Commands prüfen Eigentum, bereits bestehende Platzierung, Typ/Board beziehungsweise Freight-Facility, freie freigeschaltete Ziele sowie Ressourcenspezialisierung. Ungültige Slotindizes werden vor Mutation abgewiesen. Auch eine beschädigt unplatzierte Karte mit aktiver Freight-Sendungsreferenz lässt sich nicht neu installieren.

Installation verschiebt keine Investitionen, belastet kein Geld und erzeugt keine Ersatzkarte. Karten-ID, MK, Rarity, individuelle Boni und Pausenstatus bleiben dieselbe Instanz. Ressourcenspezialisierung folgt weiterhin der vorhandenen kompatiblen Site-Regel.

## 7. Rücknahme und Teilzyklusmodell

Rücknahme leert ausschließlich die zuvor validierten Slots. `cards`, `machine_production` und Freight-Zuweisungen werden nicht gelöscht oder neu erzeugt. Rezept, Zielressource, Fortschrittssekunden, letzte Statusinformation, Anschaffung/Upgrades, Boni und individuelle Pause bleiben erhalten. Gruppen-/Gebäudepause gehört weiter zum Gebäude und wird nicht in die individuelle Pause umgeschrieben.

Das tatsächlich bestehende Simulationsmodell konsumiert Inputs **erst beim Abschluss eines ganzen Zyklus**. Vorher prüft es Inputs, Energie und freien physischen Lagerraum; Teilfortschritt liegt an der Karten-ID. Die Simulation besucht ausschließlich installierte Slots. Unplatziert steigt der Fortschritt daher nicht und es entstehen weder Inputdebit noch Output. Nach Reinstallation wird derselbe Restzyklus bei gültigen Bedingungen fortgesetzt; am Abschluss werden Inputs genau einmal konsumiert und Output genau einmal erzeugt. Kein Inputrefund, keine neue Reservierung, keine Reset-/Gratiszyklusregel und kein neues Savefeld. Der gespeicherte Status ist der letzte Simulationsstatus, keine zusätzliche Inventory-Zustandsmaschine.

Regression: fünf Rücknahme-/Warte-/Installationsrunden bei 40 % Fortschritt erhalten exakt 40 %; anschließend erzeugen die verbleibenden 60 % einen Zyklus mit genau einem Inputverbrauch. Weitere Prüfungen blockieren Fortsetzung ohne Inputs, Energie oder Lagerraum.

## 8. Freight-Routen und Reservierungen

Idle-Freight kann zurückgenommen werden und behält Route, Pause, MK/Rarity und Investitionen. Die Route wird bei Installation gegen verfügbare Ressourcen und die bestehenden Ziele Market/Contract/Consortium validiert. Ein nicht mehr gültiger Eintrag bleibt unverändert gespeichert, blockiert aber die Installation bis zur bewussten Korrektur.

Aktive `outbound_shipments` sind die vorhandenen reservierten Ladungen; sie werden weder entfernt noch umgehängt. Eine betroffene busy Karte blockiert komplette Rücknahme-/Verkaufsgruppen. Bestehender Ankunfts-/Lieferabschluss, Cargo-Accounting und Routewechsel während Fahrt sind unverändert. Kein erzwungenes Entfernen unterwegs.

## 9. Stapel und Verkauf

Inventory ist weiterhin `GameState.cards` abzüglich Slotreferenzen. `inventory_card_stacks()` und `build_card_inventory_rows()` bilden ausschließlich Projektionen. Stapel enthalten alle konkreten Karten; die vorhandenen Schlüssel unterscheiden Definition, Typ, MK, Rarity, Bonuswerte, Anschaffungs-/Upgradeinvestition und Pause. Aktionen verwenden ausschließlich IDs.

Der zentrale Resale zahlt weiter 80 % der individuell erfassten Anschaffungs- und Upgradeinvestition, mit bestehender Centabrundung je Karte. `acquisition_cost=None` ist kein Nachweis einer Anschaffung und trägt deshalb 0 zur Basis bei; dokumentierte Upgrades bleiben erstattungsfähig. Aktuelle Definition-/Supply-Preise bewerten alte Karten niemals neu. An bestehenden Instanzen wird dabei kein Investitionsfeld verändert.

## 10. Template-Schutz

Copy bleibt eine reine Konfigurationsprojektion. `PurchaseTemplates` prüft Ziellinie, Typ/Ressourcenfamilie, freigeschaltete Rezepte, Route, ganze freie Menge, bestätigten Gesamtpreis und Geld vor Debit. Es kauft neue UUID-/MK1-/Common-Instanzen direkt in genau diese Linie, mit aktuellem dokumentiertem Anschaffungspreis, ohne kopierte Upgrades, Teilfortschritt oder Ladung. Auch MK50/Legendary-Quellen bleiben unverändert.

Kein Inventory-Zwischenschritt und keine Restablage bei zu wenig Platz. Vollständige Ablehnung bei Geld-/Slotmangel, falschem Typ/Rezept oder geänderter Quote. Cancel führt nur eine Quote aus und dispatcht keinen Kauf. Vorhandene echte Dialog-Cancel-/Paste-Regressionen bleiben Teil des vollständigen Laufs.

## 11. Save/Load und Migration

Schema bleibt **6**. Keine neue Migration und kein Eingriff in Serializer, Loader, Writer, Savepfade oder Legacy-Importverhalten. Die bisherigen Felder speichern bereits installierte und unplatzierte Karten samt Konfiguration und Teilfortschritt. P2 prüft einen echten SQLite-/Snapshotroundtrip aller drei Kartentypen in beiden Platzierungszuständen, MK50/Legendary, Pause, Investitionen, Rezept/Teilfortschritt, Routen und aktive reservierte Sendung; anschließender erneuter Roundtrip ist identisch.

Die bisherigen Save-/New-Game-/Load-/Isolations-/Legacytests bleiben erhalten. Zusätzlich werden dieselben ursprünglichen 16 Sicherungs-Slots ausschließlich gelesen und mit P1- und P2-Loader geprüft. Der alte Release-Harness verglich Linien-Dictionaries ohne das bereits bestehende Schema-6-Default `paused=False` und meldete deshalb zunächst 16 Unterschiede. Der P2-Harness ergänzt exakt diesen Default, erhält alle ursprünglichen Linien-/Slot-/Freischaltprüfungen und prüft zusätzlich vorhandene Investitionswerte. Der erste Harness-Bericht bleibt als `migration-audit-first-harness.json` erhalten. Keine produktive Migration wurde geändert. Die vollständigen migrierten P1-/P2-Payloads werden pro Slot per SHA256 verglichen; `migration-before-after-comparison.json` dokumentiert dies. Keine Originaldatenbank wird migriert oder gespeichert.

## 12. Stress- und Performancenachweise

Methode: Windows 11 / Python 3.12.14 / Qt 6.11.1 Offscreen; gleiche Fonts, Styles, Kataloge und Fixtures wie P1. Sieben frische Prozesse für Cold-UI und 20er-Kaufbursts; warme UI-Operationen 49 Stichproben, aktive Firmen/weitere Aktionen mindestens sieben. Alle Messungen seriell nach Testende, keine parallelen Tests/Builds. Vergleich ist der gesicherte **P1-Endstand vor P2** gegen P2. Rohdaten: `before/`, `after/`, `comparison.json`, vollständige Tabellen in `comparison-tables.md`. Median und Maximum sind Stichprobenwerte, keine FPS-/p95-Garantie.

| Bestand | Projektion vorher Median / Max ms | Projektion nachher Median / Max ms | Snapshot nachher Median / Max ms | JSON-Bytes vorher = nachher | Python aktuell / Peak MiB nachher |
| --- | --- | --- | --- | --- | --- |
| 500 | 1.37 / 1.56 | 1.38 / 1.46 | 7.03 / 19.01 | 212291 | 0.63 / 0.97 |
| 5000 | 14.65 / 15.81 | 14.23 / 14.84 | 57.21 / 58.71 | 1578791 | 4.05 / 6.47 |
| 10000 | 28.71 / 30.39 | 28.95 / 29.55 | 111.34 / 119.35 | 3097123 | 7.65 / 12.37 |

Gleiche unplatzierte Drei-Typen-Fixture (Production/Energy/Freight), sämtliche konkreten IDs enthalten. Speicher separat mit `tracemalloc` für Zustand plus Projektion plus abgelösten Snapshot gemessen; keine Prozess-/GPU-Messung und kein Langzeit-Leaknachweis. Timing ohne `tracemalloc`. Definitionen sind außerhalb der Speicherprobe bereits geladen. Gleiche Payloadgrößen belegen, dass keine Karten-/Historydaten für schnellere Snapshots ausgelassen wurden.

| Erwerb ohne Gebäude/Slots | P1 | P2 Median / Max ms (n=7) |
| --- | --- | --- |
| 1 Karten | 7× wegen fehlender Slots abgelehnt | 0.03 / 4.94 |
| 10 Karten | 7× wegen fehlender Slots abgelehnt | 0.11 / 0.12 |
| 100 Karten | 7× wegen fehlender Slots abgelehnt | 0.99 / 1.05 |
| 1000 Karten | 7× wegen fehlender Slots abgelehnt | 10.12 / 10.19 |

Dieser Erwerbsvergleich zeigt eine absichtlich geänderte Fachregel, keinen Geschwindigkeitsgewinn eines identischen alten Kaufpfads. Eine einzelne Buchung und der vollständige Kartenbestand werden in den Regressionen geprüft.

| P1-Kontrolle | n vorher / nachher | Vorher Median / Max ms | Nachher Median / Max ms |
| --- | --- | --- | --- |
| Unlock Konstruktion | 7 / 7 | 100.85 / 173.69 | 92.63 / 101.68 |
| Unlock Status | 49 / 49 | 0.04 / 7.39 | 0.03 / 7.26 |
| Unlock Rebuild warm | 49 / 49 | 0.06 / 1.09 | 0.08 / 0.68 |
| Unlock Zoom/Pan | 49 / 49 | 70.02 / 109.48 | 75.88 / 131.59 |
| Guide erstes Öffnen | 7 / 7 | 544.78 / 585.26 | 510.31 / 590.57 |
| Guide schließen/öffnen | 49 / 49 | 21.20 / 30.81 | 20.64 / 26.10 |
| Guide Suche | 49 / 49 | 23.57 / 44.38 | 26.85 / 39.69 |
| Guide Filter | 49 / 49 | 62.93 / 294.99 | 65.21 / 330.64 |
| Picker Konstruktion | 49 / 49 | 179.81 / 281.02 | 159.71 / 281.68 |
| Picker Suche | 49 / 49 | 16.49 / 28.30 | 16.25 / 23.05 |
| Leaderboard eigene Zeile | 49 / 49 | 0.19 / 0.73 | 0.20 / 1.15 |
| 500er Shift-Auswahl | 49 / 49 | 27.31 / 58.36 | 28.71 / 63.38 |
| 50: 20er-Kaufburst | 7 / 7 | 535.36 / 560.52 | 539.76 / 571.41 |
| 500: 20er-Kaufburst | 7 / 7 | 582.93 / 614.52 | 556.62 / 587.86 |
| Aktiv 500.render | 7 / 7 | 165.11 / 178.60 | 157.77 / 171.37 |
| Aktiv 500.refresh | 7 / 7 | 5.90 / 192.45 | 6.64 / 210.85 |
| Aktiv 500.tick | 7 / 7 | 5.27 / 7.88 | 5.23 / 8.53 |
| Aktiv 500.snapshot | 7 / 7 | 125.99 / 167.53 | 94.99 / 148.61 |
| Aktiv 500.encoding | 7 / 7 | 93.26 / 94.94 | 92.25 / 95.22 |
| Aktiv 500.commit | 7 / 7 | 43.07 / 45.82 | 42.62 / 45.16 |
| Aktiv 500.full_save | 7 / 7 | 293.68 / 307.07 | 251.22 / 279.51 |
| Aktiv 500.load | 7 / 7 | 171.48 / 224.02 | 173.12 / 183.42 |
| UI 500.sale20 | 7 / 7 | 253.26 / 301.53 | 243.06 / 264.51 |
| UI 500.mk4 | 7 / 7 | 52.55 / 62.12 | 47.10 / 68.90 |
| UI 500.slots7 | 7 / 7 | 104.87 / 110.55 | 126.95 / 140.60 |
| UI 500.recipe20 | 7 / 7 | 79.03 / 96.32 | 69.54 / 80.39 |
| UI 500.copy_paste10 | 7 / 7 | 37.90 / 71.53 | 38.11 / 60.98 |

Kaufbursts verwenden die echten Supply-/MainWindow-Callbacks mit unveränderter 50/500-Karten-Ausgangsfixture. P2 verändert jedoch absichtlich die resultierende Platzierung; neue Käufe erzeugen keine belegten Boardlinien mehr. Diese Messungen sind deshalb keine isolierte UI-Optimierungsbehauptung. Die vorhandene P1-Auswahl-/Aktionsregression installiert die neuen Karten ausdrücklich und behält ihren ursprünglichen vollständigen Boardumfang. Die zusätzliche aktive 500-Karten-Probe behält sämtliche 500 Sites, ihre Slotstrukturen, 240 Historywerte und die vollständige Renderfläche. Die 100/500-Auswahlboards bleiben dieselben synthetischen Stressflächen oberhalb regulärer Hallengrenzen.

Alle P1-UI-/Atlas-/Snapshotquellen sind gegen die P2-Sicherung unverändert. Pixel-/Cache-/Widgetidentitätsregressionen laufen weiterhin. Verbleibende Frameüberschreitungen großer Paints, erstmaliger Filtermaterialisierung und Snapshots werden nicht als gelöst bezeichnet; native Windows-Gesten/FPS wurden in P2 nicht neu abgenommen.

Die Kontrollen sind kein pauschaler Latenz-Erfolg: Das Guide-Suchpaar steigt im Median von 23,57 auf 26,85 ms; sieben Slotfreischaltungen bei 500 Karten von 104,87 auf 126,95 ms. Andere unveränderte Pfade fallen günstiger aus. Die Messwerte bleiben vollständig sichtbar; aus identischen UI-Quellen allein folgt keine Garantie identischer Laufzeit. P2 führt keine zusätzliche UI-Optimierung ein.

Zusätzliche vollständige JSON-Prüfung der aktiven 10/50/100/500-Karten-Saves: Genau ein Blatt unterscheidet sich jeweils, der vom initialen Spielstand erzeugte `company_xp_progress.utc_high_water_timestamp`. Die 100er-/500er-Payloads weichen dadurch um ein Zeichen ab; alle Karten, Slotstrukturen, Konfigurationen und Historywerte sind gleich. Nachweis: `active-payload-comparison.json`. Die separat fest datierte Inventarprobe hat exakt identische Payloadgrößen.

## 13. Vollständiger Testlauf und Bestandsschutz

**1336/1336 Tests in 82/82 Modulen bestanden; 0 Fehler, 0 Skips.** Alle 1270 vorhandenen Fälle mit unveränderter Fallzahl je Bestandsmodul plus 66 neue P2-Fälle. Vollständiger serieller Modullauf mit erforderlichen Modulwiederholungen: `artifacts/phase2/final-tests/`, Einzeltext/JUnit/`results.json`; `final-test-summary.json` enthält die Zählung. Summierte Modul-Prozesszeiten 912.61 s.

Ursprüngliche Migrationsmatrix: **16 Slots bestanden**, 0 Fehler. Abschließender SHA256-Schutz: **8056 geschützte Bestandsdateien und alle fünf persönlichen Saves unverändert**, einschließlich aller UI-/P1-Assets, Daten, Builddateien und ursprünglichen P0-/P1-Nachweise (große ZIP-Abhängigkeiten wurden bereits bei der Sicherung vollständig gehasht). `protected-verification.json` und `implementation.diff` dokumentieren Grenzen und den tatsächlichen P2-Delta gegen die Arbeitskopie.

Der erste vollständige Lauf bleibt unter `first-full-tests/` erhalten. Ein vorhandener Dialogtest erwartete noch automatische Kaufplatzierung; ausschließlich dieser Sollwert wurde fachlich auf unplatzierten Besitz aktualisiert. Das ganze betroffene Modul wurde erneut ausgeführt. `final-tests/provenance.json` ordnet jeden endgültigen Modulnachweis seinem ursprünglichen oder wiederholten Lauf zu; kein fehlgeschlagener Nachweis wurde überschrieben.



Fachlich angepasste bestehende Tests bleiben erhalten: Supply erwartet nun unplatzierte Karten; die zwei Energie-Simulationsfälle installieren ausdrücklich. Der frühere Bulk-Slotlimitfall prüft die gültige Operationsgrenze statt eines abgeschafften Platzierungslimits. Release-Simulations-/Move-/Migrations- und UI-Auswahlfixtures installieren ihre gekauften Maschinen ausdrücklich. Der vorhandene P1-Aktionstest behält sein vollständig belegtes 50/500-Karten-Board durch ausdrückliche Installation außerhalb der Kaufcallbacks. Stack-Erwartung nach Common-Kauf lautet Available statt In Use. Kein Test wurde entfernt oder übersprungen.

Angepasste Bestandsdateien: `tests/test_supply.py`, `test_industriova_release.py`, `test_industriova_release_ui.py`, `test_playtest_fix_pass.py` und `test_phase1_performance.py`.

Neue P2-Fälle stehen in `tests/test_phase2_inventory_backend.py`; Rohbelege, JUnit und Einzellogs liegen unter `artifacts/phase2`. Reproduktion: `scripts/run_release_tests.py . artifacts/phase2/<neuer-testordner> --timeout 600 --workers 1`; `phase2_measure.py before|after ui|rapid|active|extended` mit eigener Ausgabe unter P2; `phase2_inventory_benchmark.py before --source artifacts/phase2/before-tree` beziehungsweise `after`; `phase2_migration_audit.py`, `phase2_compare.py`, `phase2_verify_protected.py`. `phase2_finalize_tests.py` erhält Erstlauf und vollständige Modulwiederholungen mit Herkunftsnachweis; `phase2_finish_report.py` füllt die Tabellen ausschließlich aus den fertigen Nachweisen. Tests und zeitliche Messungen seriell ausführen, eigene AppData-Pfade verwenden.

## 14. Offen für P3 und ausdrücklicher Stopp

P3 muss Inventory sichtbar machen, konkrete ID-Auswahl/Install/Return/Sell und Bestätigungen anbinden, Shop-Text und Slotprüfungen auf Inventarerwerb umstellen, Mengen/MAX im Dialog anzeigen und Quote/Operations-ID bei Bestätigungswiederholung erhalten. Die vorhandene virtuelle Supply-Darstellung und P1-Caches bleiben Grundlage. Bis dahin können erworbene Karten in der alten Oberfläche verborgen bleiben; der Backendbestand und Saves behalten sie.

Keine neue Navigation, keine UI-Reaktivierung, keine sichtbare MAX-Anzeige, kein Drag-and-drop/Swap aus P4, keine Freight-UI/-Statistik aus P5/P6, keine Infrastruktur-/Contractpreise aus P7/P8, kein Tutorial und kein Build. **P2 endet als geprüfter Backend-Zwischenstand.**
