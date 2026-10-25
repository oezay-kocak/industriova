# INDUSTRIOVA 0.3 – P5: Freight-Bedienung

Stand: 22.10.2026. Ausschließlich P5, auf der tatsächlichen Arbeitskopie nach P4. Kein Build, kein Balancing und keine P6-Lieferstatistik.

## Sicherung und Grenzen

Vor produktiven Änderungen wurde `artifacts/phase5/backup-20261021T224926Z` erstellt: 47,704 Dateien / 29,343,804,445 Bytes. SHA256-Inventar mit rekursiv erhaltener P4/P3/P2/P1/P0-Kette, Delta und separater unabhängiger source-baseline.zip. Beide ZIPs CRC-geprüft, sämtliche extrahierten Quellinhalte gegen Manifest-Hashes geprüft. Große Altarchive bleiben mit Originalpfad und Hash dokumentierte Abhängigkeiten. Wiederherstellung ausschließlich in einen neuen Ordner nach Manifest; kein Git-HEAD-Reset.

Manifest SHA256: `3abe85a3faec43c24a79a9e6a6750197fed8a6453d32e846529ef60e8ea03232`. Source ZIP SHA256: `cfdc25d58aad7427ea431251a3e348555d4ed684d3c8601a0aad1ec039fe29b4`. Delta SHA256: `747855800b68ef4e9982493a393753fdc1c0089ba101c4f4712b006489f9c28c`. Vollständige Archiv-/Save-Prüfsummen: `artifacts/phase5/backup-20261021T224926Z/SHA256SUMS.json`.

Fünf persönliche SQLite-Dateien zusätzlich roh und konsistent über read-only SQLite gesichert, fünfmal integrity_check=ok. Abschließend 20,648 geschützte bestehende Dateien und alle fünf Original-Saves unverändert. Bestehende Builds, Daten, Assets/Atlas, Simulation, MK-/Preislogik, Templatekäufe, Schema-6-Serializer und P0–P4-Nachweise geschützt. Alte von Tests beschriebene PNG-Referenzen wurden nach Backup-SHA wiederhergestellt; frische Bilder bleiben unter P5 erhalten. Tests/Captures ausschließlich in isolierten AppData-/Tempverzeichnissen.

## Tatsächliche Änderung und Wiederverwendung

| Datei unter src/production_zero | Änderung |
| --- | --- |
| core/commands.py | AssignFreightVehicles erhält optionale Definitionen, Ursprungssnapshot und explizite Zielprüfung. Ein vorbereiteter Gruppencommit; kein zweites Routenmodell. |
| core/freight_routes.py (neu) | Reine gemeinsame Bestätigungsvalidierung für aktuelle Eigentümer/Plätze, Katalog-/Facility-Kompatibilität, Cargo und Vertragsbedarf einschließlich reservierter Mengen. |
| ui/freight_assignment.py (neu) | Flüchtiger Waren-/Zielentwurf, Mixed-Zustand, explizite Bestätigung, Zielbegründungen; vorhandenes Board beim Wechsel erhalten. |
| ui/freight_view.py | Vorhandener Picker an geführten Ablauf gebunden, gezielter Runtime-Refresh, lokale MK-Hitbox, sicherer Durchsatz und vollständige Tooltip-Beschriftung. |
| ui/freight_upgrade.py (neu) | Bestehender GameButton mit identischem grünen ⇈-Renderer, gemeinsame Single-/Group-Bestätigung über UpgradeMachines, Quote-/Sessionprüfung und Doppelklickschutz. |
| ui/release_freight.py | Kontextmenü delegiert an denselben Upgradepfad und friert die Routen-Gruppe vor dem Öffnen ein. |

FreightAssignment, die vorhandenen Ziele market/contract/consortium, AssignFreightVehicles, UpgradeMachines, mk_upgrade_cost, freight_stats, IndustrialDialog/confirm/inform, ResourceBrowser und sekundäre Controls bleiben Grundlage. Kein neues Zielenum, keine zweite Upgrade-/Rarityformel und keine Savefelder. Vollständige geänderte/neue Dateien und SHA256 stehen in deliverables-manifest.json; implementation.diff vergleicht gegen die Vorsicherung.

## Ware → Ziel → Bestätigen

Vorher stand die Zielcombo vor dem Warenbrowser; der Warenklick schrieb sofort eine Route. Jetzt: Fahrzeug oder bestehende Gruppe → Cargo → Delivery Target → Confirm Route. Ein vorhandener gemeinsamer Waren-/Zielwert wird vorbefüllt. Gemischte oder teilweise unzugewiesene Gruppen zeigen MIXED ROUTES und übernehmen keine zufällige Einzelroute. Ware kann erneut geändert werden; ein dadurch ungültiges Ziel wird abgewählt. Sell, Contract und Consortium Contract bleiben wählbar, ungültige Optionen werden als unavailable gekennzeichnet und begründet. Event ist sichtbar und deaktiviert.

Die bestätigten konkreten IDs bleiben stabil. Vor dem einzigen Command werden die aktuelle Kartenregistrierung, Eigentum, eindeutige Freight-Plätze, Facility/Slotindex, freie Zugänglichkeit, Katalog, positive endliche Cargo-Menge und aktuell verbleibender Zielbedarf erneut geprüft. Aktive Verträge verwenden nur ihre tatsächlich angenommenen/manuell gewählten Anforderungen; abgelaufene/inaktive/falsche Produkte und bereits reservierte Mengen blockieren Confirm. Consortium setzt aktuelle Mitgliedschaft voraus; für die Lieferung ist nach bestehender Engine kein Manager-Rang erforderlich. Managerrechte zur Vertragsannahme werden nicht geändert. Kein automatischer Sell-Ersatz beim Bestätigen.

AssignFreightVehicles validiert die ganze Gruppe vor assignments.update. Die optional strengere require_target-Prüfung wird vom neuen expliziten UI-Commit verwendet. Bestehende nichtinteraktive Aufrufer können wie bisher zukünftige Routen ohne aktuell passenden Vertrag konfigurieren; die alte Aufrufsignatur bleibt gültig. Der tatsächliche Engine-Fallback beim Lieferabschluss ist unverändert.

Cancel, Esc, Tabwechsel/Hide, Close, Load/New Game und erneutes Öffnen verwerfen nur den Entwurf. Das normale Board bleibt verborgen erhalten und wird bei unveränderter Struktur mit denselben Widgets wieder eingesetzt; ausschließlich betroffene Karten werden aktualisiert. Bei Session-/Strukturwechsel wird die alte Darstellung verworfen. Während einer aktiven Fahrt darf die Route wie bisher für zukünftige Abfahrten geändert werden. Aktive shipment-Objekte, Cargo, reservierte Menge, Kapazität und Restfahrzeit werden dabei nicht umgeschrieben.

## MK-Button und Durchsatz

Der grüne ⇈-Button sitzt unten rechts im vorhandenen Fahrzeugbild. Sein eigener Pfad betrifft genau die Karten-ID und erhält die Gruppenauswahl. Das Kontextmenü unterstützt weiter das atomare Gruppenupgrade und überspringt wie bisher MK99. Beide Wege bestätigen über dieselbe zentrale Quote und dispatchen UpgradeMachines. MK99 ist deaktiviert, der Tooltip erklärt das Maximum; sonst stehen nächste Stufe und Preis darin. Geldmangel wird vor der Bestätigung erklärt und im Command nochmals geprüft.

Während der Bestätigung sind Kartenobjekte, Session und Ursprünge eingefroren; Änderungen oder ein anderer Preis lehnen ab. Ein Inflight-/Doppelklickintervall und konsumierte DoubleClick-Ereignisse verhindern die zweite Zahlung derselben UI-Geste. Eine spätere bewusste Aktion benötigt eine neue Bestätigung. Die Hitbox hat einen eigenen immer aktiven Maus-Schutz auch hinter dem deaktivierten MK99-Button; Press/Move/Release propagieren nicht in die P4-Auswahl-/Draglogik. Keine neue globale Eventfilterung.

Die bestehende Core-Regel erlaubt Upgrades während einer Lieferung. Nur spätere Abfahrten verwenden die neuen Stats. mk_upgrades.py, die lineare MK-Basis +25 % pro Stufe und die bestehende einmalige Rarity-Mechanik bleiben unverändert. Keine neue Würfelchance und kein zusätzlicher Freight-Multiplikator.

Der Tooltip ergänzt THEORETICAL THROUGHPUT mit `60 * effective capacity / effective transport seconds`. Beide Werte stammen direkt aus freight_stats, wie beim Start neuer Sendungen: MK, individueller Rarity-/Outputbonus und Kapazitätsforschung wirken zentral; die bestehende Rarity-Fahrzeitregel bleibt identisch. Alle bisherigen Hoverdaten bleiben erhalten. Die Zahl wird lesbar gerundet, sehr kleine/große Werte wissenschaftlich formatiert; nicht positive/nicht endliche Werte ergeben Unavailable. Pause setzt die theoretische Leistungsfähigkeit nicht auf null. Runtime-Updates aktualisieren den vorhandenen Hover nach MK/Research/Rarity; kein Board-Neuaufbau.

## Tests und Erhaltungsschutz

**1595/1595 Tests in 87 Modulen bestanden; 0 Fehler, 0 Skips.** Alle 1.491 bestehenden Fälle mit gleicher Fallzahl je Bestandsmodul plus 104 P5-Fälle. Vollständige Modulnachweise und Herkunft unter final-tests/; final-test-summary.json. Endgültiger kompletter Modullauf mit zwei getrennten Prozessen und eigenem AppData pro Modul; sämtliche Zeitmessungen separat und seriell ohne parallel laufende Tests. Summierte Modul-Prozesszeiten (keine Wandzeit): 765.69 s. Vorbereitende Läufe während der Implementierung bleiben getrennt erhalten und zählen nicht zusätzlich.

Neue Module test_phase5_freight_core.py und test_phase5_freight_ui.py prüfen Waren-/Ziel-/Confirm-Reihenfolge, Gruppenatomarität, konkrete IDs, Mixed/Common, veraltete/entfernte/verschobene Karten, Ressourcen/Kompatibilität, aktive/abgelaufene/manuell gewählte Contract-Produkte, Consortium-Mitgliedschaft und Bedarf/Reservierungen, Event-Sperre, Cancel/Esc/Tab/Reset/Reopen, Double-submit, Busy-Snapshots und Schema-6-Roundtrips. MK: 1/2/10/98/99, Geldmangel, direkte Fenster-Hitbox und Doppelklick, unveränderte Auswahl, kein Drag beim Button-Ziehen, gleiche Quote/MK/Rarity/Cash/History über Direkt- und echten Kontextdialog, Cancel und Modaländerungen, Busy-Gruppen. Tooltip: alle vier Fahrzeugtypen, MK/Rarity/Research, Pause, kleine/große/ungültige Werte und aktualisierter vorhandener Hover.

Bestandsänderungen an Tests: test_factory_ui.py, test_final_language_alignment.py, test_secondary_modernization.py und test_unified_production_ux.py behalten ihre fachlichen Prüfungen und bestätigen jetzt ausdrücklich den neuen Routenablauf. test_recipe_retirement.py ändert nur das Capture-Ausgabeziel nach P5. Kein Test gelöscht/deaktiviert/übersprungen. P4-Occupied-/Gruppenswaps, Busy-Quellen/Gegenkarten, Ghost/Edge/Wheel und Cleanup sowie P1-Cache-/Snapshot- und P2/P3-Inventory-/Supply-/Templatefälle laufen vollständig weiter. Originale **16/16 Save-Migrationen**, migrierte vollständige Payloads vor/nach P5 exakt gleich. Schema bleibt 6. Zusätzlicher P4/P5-Testlauf bei 200 % in dpi2-tests.xml; nicht doppelt gezählt.

## Getrennte Testnachweise

| Lauf | Fälle | Bestanden | Fehlerfälle | Skips |
| --- | --- | --- | --- | --- |
| targeted-first.xml | 98 | 98 | 0 | 0 |
| targeted-second.xml | 124 | 124 | 0 | 0 |
| reuse-check.xml | 57 | 57 | 0 | 0 |
| route-reuse-regression.xml | 3 | 3 | 0 | 0 |
| before-popup-fix-dpi2-tests.xml | 213 | 213 | 0 | 0 |
| popup-fix-targeted.xml | 1 | 1 | 0 | 0 |
| dpi2-tests.xml | 214 | 214 | 0 | 0 |
| Vorbereitender Gesamtlauf, 87 Module | 1594 | 1590 | 4 | 0 |
| Gesamtlauf vor Popup-Farbkorrektur, 87 Module | 1594 | 1594 | 0 | 0 |

Im vorbereitenden Gesamtlauf scheiterten vier ältere Sofortzuweisungs-Erwartungen in test_factory_ui.py und test_unified_production_ux.py. Sie bestätigen jetzt das Lieferziel ausdrücklich; alle bisherigen Fachassertions und Fallzahlen bleiben erhalten. Die gezielte Dreierwiederholung ist als Teilmenge erkennbar (214 andere Fälle dieses Moduls wurden dafür nicht ausgewählt); der abschließende Gesamtlauf enthält alle 217. Alle ursprünglichen Nachweise bleiben erhalten.

Im vorbereitenden zweiten Gesamtlauf wurde der Gruppentest vor dem Start seines vollständigen 20-Fälle-Moduls angepasst; before-popup-fix-test-source-reconciliation.json hält Zeit-/SHA-Nachweis fest. Danach wurde beim tatsächlichen Betrachten des separaten Qt-Popups helle Schrift auf weißem Grund erkannt. Nur die lokale Popupfläche erhielt ein deckendes vorhandenes dunkles Material; ein echter Render-/Palette-Kontrasttest ergänzt den Schutz. Alle 87 Module wurden anschließend erneut vollständig ausgeführt. Sämtlicher produktiver Code und alle Tests blieben während dieser endgültigen Suite und ihrer abschließenden Prüfungen unverändert. Die zusätzlichen 200%- und Teilmengenläufe zählen nicht erneut zur Gesamtfallzahl.

Nach der vollständig grünen endgültigen Suite verhinderte ein doppelter DPI-Parameter im bereits gestarteten Prüfharness den nächsten Aufruf. Die Umgebungsansteuerung wurde korrigiert; ausschließlich die ausstehenden Kontrollen wurden fortgesetzt. Keine fehlgeschlagenen Softwaretests und keine Änderung produktiver Quellen. Nachweis: post-suite-harness-recovery.json.

## Zeiten und Speicher

Windows / Python 3.12.14 / Qt 6.11.1 offscreen. Identische P0–P4-Workloads und vollständige Fixtures aus der neuen Vorsicherung gegen den endgültigen Stand. Sieben frische Cold-UI-/Kaufprozesse, warme UI-Reihen 49 Werte, aktive Firmen/weitere Aktionen mindestens sieben. Messungen seriell ohne parallel laufende Test-/Build-/Benchmarkprozesse, Callback/Event-Drain/Queue getrennt. Median / Maximum in ms; keine FPS- oder p95-Zusage. Ausgaben before/, after/, comparison.json und comparison-tables.md.

| P1-Kontrolle | Vorher Median / Max ms | Nachher Median / Max ms |
| --- | --- | --- |
| ui: unlock.constructor.cold | 95.05 / 116.20 | 88.95 / 101.09 |
| ui: unlock.rebuild.warm | 0.05 / 0.43 | 0.05 / 0.19 |
| ui: guide.first_open | 525.18 / 601.85 | 466.31 / 515.05 |
| ui: guide.filter | 66.14 / 380.33 | 56.82 / 255.41 |
| ui: leaderboard.changed_refresh | 0.18 / 0.71 | 0.20 / 0.64 |
| active: 10.render | 2.78 / 3.17 | 2.25 / 2.64 |
| active: 50.render | 13.99 / 14.73 | 12.61 / 13.95 |
| active: 100.render | 30.35 / 32.92 | 25.62 / 26.10 |
| active: 500.render | 161.25 / 178.61 | 141.62 / 143.91 |
| active: 500.refresh | 6.91 / 188.99 | 5.61 / 169.06 |
| active: 500.snapshot | 145.92 / 213.85 | 130.94 / 141.54 |
| active: 500.full_save | 226.98 / 295.53 | 221.31 / 268.10 |
| rapid_bursts: rapid_ui.50.20_individual_purchases | 497.62 / 526.60 | 476.57 / 483.02 |
| rapid_bursts: rapid_ui.500.20_individual_purchases | 497.04 / 547.37 | 471.99 / 481.48 |

P4-Größen: Production 10/50 reguläre Auswahlboards und explizit synthetische 100/500-Boards; volle Gruppenzyklen, Occupied-Swaps und 100 Mausbewegungen mit Event-Drain. Freight-Stressflächen sind bei allen Größen synthetisch. Keine Behauptung eines nativen Mausgefühls.

| P4-Workload | Vorher Median / Max ms | Nachher Median / Max ms |
| --- | --- | --- |
| 10.drop_commit_cycle | 0.04 / 0.15 | 0.03 / 0.10 |
| 10.100_occupied_swaps | 2.12 / 2.29 | 2.28 / 2.38 |
| 10.100_drag_moves | 1.14 / 4.92 | 0.98 / 4.24 |
| freight.10.100_pointer_moves | 13.34 / 45.72 | 11.15 / 45.25 |
| 50.drop_commit_cycle | 0.05 / 0.18 | 0.07 / 0.14 |
| 50.100_occupied_swaps | 3.98 / 19.49 | 4.51 / 18.85 |
| 50.100_drag_moves | 1.00 / 3.71 | 1.18 / 4.72 |
| freight.50.100_pointer_moves | 11.89 / 73.21 | 11.88 / 75.01 |
| 100.drop_commit_cycle | 0.07 / 0.18 | 0.08 / 0.17 |
| 100.100_occupied_swaps | 5.54 / 6.07 | 6.07 / 6.19 |
| 100.100_drag_moves | 0.94 / 3.91 | 0.99 / 4.56 |
| freight.100.100_pointer_moves | 16.14 / 98.89 | 12.13 / 104.28 |
| 500.drop_commit_cycle | 0.34 / 0.68 | 0.25 / 0.56 |
| 500.100_occupied_swaps | 19.51 / 19.60 | 20.06 / 21.27 |
| 500.100_drag_moves | 0.92 / 4.03 | 0.99 / 3.29 |
| freight.500.100_pointer_moves | 14.54 / 453.12 | 11.71 / 433.02 |

Freight-Widgetzahlen vor → nach P5: 10 Karten: 189 → 209; 50 Karten: 774 → 874; 100 Karten: 1502 → 1702; 500 Karten: 7352 → 8352. Die sichtbare MK-Aktion plus Eingabeschutz benötigen zwei zusätzliche Widgets pro Fahrzeug; dieser Aufwand wird nicht als kostenlose Optimierung ausgegeben.

Identische P3-Inventory-Fixtures: alle Karten/Zeilen und vollständigen Payloads, gestapelt und getrennte Investitionen. Neue P5-Controls betreffen nicht den Inventory-Pool. Python-/Prozessspeicher steht getrennt in den Rohwerten; Working Set enthält erwärmte Qt-/Asset-Caches und ist kein isolierter Zuwachs oder Langzeit-Leaktest.

| Inventory-Fixture | Refresh vorher → nachher Median / Max ms | Kartenwidgets / alle | Working Set vorher → nachher MiB | Python nachher aktuell / Peak MiB | Payload unverändert |
| --- | --- | --- | --- | --- | --- |
| 500-stacked | 9.19 / 9.49 → 9.13 / 9.94 | 3 / 34 | 97.66 → 97.70 | 0.21 / 0.24 | SHA256 und Bytes identisch |
| 500-distinct | 49.05 / 55.12 → 43.07 / 46.63 | 42 / 73 | 100.33 → 100.28 | 0.42 / 0.42 | SHA256 und Bytes identisch |
| 5000-stacked | 22.26 / 26.84 → 21.53 / 21.87 | 3 / 34 | 109.03 → 108.52 | 1.36 / 1.90 | SHA256 und Bytes identisch |
| 5000-distinct | 79.54 / 115.58 → 72.90 / 89.12 | 42 / 73 | 109.77 → 109.54 | 2.38 / 2.98 | SHA256 und Bytes identisch |
| 10000-stacked | 36.39 / 47.93 → 35.96 / 37.51 | 3 / 34 | 118.14 → 118.07 | 2.64 / 3.23 | SHA256 und Bytes identisch |
| 10000-distinct | 138.97 / 155.84 → 123.11 / 138.58 | 42 / 73 | 118.87 → 119.21 | 4.38 / 5.80 | SHA256 und Bytes identisch |

Zusätzliche unveränderte P2-Backend-Reihe: unplatzierter Common-Erwerb ohne Facility-/Slotbedingung, sieben Wiederholungen je Menge. Alle Erwerbe erfolgreich, volle Kartenanzahl und keine automatische Installation. Core-Projektion/Snapshot für 500/5.000/10.000 ebenfalls vollständig in inventory-benchmark.json; gleiche Payload-Bytes vor/nach P5.

| Karten pro Kauf | Vorher Median / Max ms | Nachher Median / Max ms |
| --- | --- | --- |
| 1 | 0.03 / 4.93 | 0.03 / 5.12 |
| 10 | 0.11 / 0.13 | 0.12 / 0.14 |
| 100 | 1.00 / 1.08 | 0.98 / 0.99 |
| 1000 | 10.22 / 10.39 | 10.22 / 10.50 |

Neue P5-Arbeit ohne erfundenen Vorhervergleich: eigenständige FreightView, ohne globale MainWindow-Hooks, sieben explizite Gruppenrouten mit wechselnder Ware und Einzelupgrades. Für die gemessene explizite Sell-Wahl wird der Platzhalter außerhalb der Uhr zurückgesetzt. Bestätigter Callback plus Events; Dialogaufbau und menschliche Modalwartezeit sind durch den Bestätigungsstub ausgeschlossen. 10/50/100/500 sind übergroße synthetische Freight-Stressflächen. Zusätzlich 20 Garagen mit 160 Fahrzeugen, acht pro Garage, über vorhandene Build-/Expand-/Supply-/Install-Commands in einem isolierten Zustand aufgebaut; kein persönliches Save geladen. Bestehende Kartenwidgets bleiben nach Return/Upgrade identisch. Working Set umfasst den gemeinsamen Prozess und frühere erwärmte Fixtures.

| Freight-Fixture | Open | Cargo | Target | Confirm/Return | Single MK | Tooltip | Working Set MiB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 20-facilities | 69.75 / 80.37 | 7.17 / 17.28 | 0.98 / 1.33 | 36.55 / 95.92 | 28.94 / 31.71 | 0.81 / 38.17 | 103.36 |
| 10 | 68.17 / 77.29 | 5.22 / 6.43 | 1.01 / 3.47 | 38.43 / 41.19 | 31.18 / 33.10 | 0.67 / 6.01 | 104.17 |
| 50 | 73.02 / 115.95 | 5.30 / 6.40 | 1.03 / 1.30 | 39.34 / 51.54 | 30.59 / 31.58 | 0.76 / 4.97 | 124.57 |
| 100 | 75.14 / 124.70 | 5.33 / 5.60 | 1.04 / 1.31 | 43.60 / 57.05 | 29.84 / 30.79 | 0.83 / 4.96 | 147.56 |
| 500 | 80.95 / 321.35 | 5.28 / 6.11 | 1.05 / 1.20 | 65.84 / 145.49 | 31.55 / 32.46 | 0.80 / 5.64 | 315.27 |

Kontrollen mit über 10 % höherem Median und über 1 ms nachher: keine in den ausgewerteten P1-Kontrollen. Keine pauschale Beschleunigungsbehauptung. Große vollständige Paints, Inventory-Projektionen und Snapshots bleiben teilweise über einem 16-ms-Budget. Zusätzliche Freight-Buttons benötigen Widgets und Quote-/Darstellungsarbeit; Ergebnisse sind offscreen, zeitlich begrenzt und keine GPU-/DWM-/Langzeitmessung.

## Visuelle Prüfung und native Grenze

114 finale Captures über 1366×768, 1600×980 und 1920×1080 bei 100/200 %. MainWindow-Captures und separate tatsächliche Qt-Ziel-Popup-Captures sind in den Metadaten unterschieden. MK1–99/Rarity/Busy-Tooltip für Truck/Train/Aircraft/Ship, Ware, Mixed-Gruppe, Ziel-unselected, gültiger/ungültiger Contract, Sell, Consortium und sichtbare deaktivierte Event-Option. Tatsächliche Pixel- und logische Größen geprüft. Tatsächlich betrachtete finale Stichproben mit SHA256: visual-review.json. Frühere Captures vor Position/Kontrast/Tooltip-Wrap bleiben getrennt erhalten.

Lange bestehende Freight-Facility-/Sidebar- und Linienbeschriftungen können weiterhin abgeschnitten sein; P9-Navigation/Labelpolish wurde nicht vorgezogen. Der neue MK-Button sitzt im Kartenbild, ohne Kapazität/Route/Utility zu überdecken. Neue Erklärungen haben auf dem bestehenden hellen Secondary-Canvas dunklen Text, die lange Theorie-Beschriftung wird vollständig umgebrochen.

**Native Windows-Handabnahme bleibt offen.** QTest/offscreen prüft Qt-Hitboxen, Zustandsübergänge und Ereignisse; keine echte OLE-/GPU-/DWM-Geste, kein subjektives Wheel-/Scrollgefühl und kein menschlicher Langzeitplaytest. Für die nächste native Abnahme: direkte MK- und deaktivierte MK99-Hitbox bei beiden DPI prüfen; Gruppen-/Busy-Routen und Cancel/Alt-Tab/Load testen; belegte P4-Swaps über Scrollränder mit Wheel, Outside-Drop und Cleanup wiederholen.

## Reproduktion und Stopp

Vollständiger frischer Modullauf: scripts/phase5_run_tests.py . artifacts/phase5/neuer-testordner --workers 2 --timeout 600; der Runner isoliert AppData pro Modul. phase5_validate.py enthält die Originalmigrationen, identischen Vorher-/Nachher-Workloads und P4-Stress. phase5_popup_capture.py und phase5_verify_visual.py prüfen die separaten endgültigen Popup-/MainWindow-Captures. phase5_final_validation.py führt den vollständigen endgültigen Lauf und die anschließenden Kontrollen aus; phase5_finish_validation.py kann ausschließlich die Kontrollen nach einer bereits grünen, SHA-geprüften Gesamtsuite fortsetzen. Bestehende Ausgaben vor Wiederholung separat erhalten; diese versionsgebundenen Proof-Skripte dürfen alte Evidenz nicht überlagern. phase5_finish_report.py erzeugt diesen Bericht aus den abgeschlossenen Nachweisen. Source-/Test-SHA der endgültigen Suite: tested-source-sha256.json.

Die unveränderten P0/P1/P2/P3/P4-Nachherkontrollen wurden vor der letzten lokalen Popup-Farbkorrektur erhoben; diese Pfade bauen das Freight-Zuweisungspopup nicht auf. Die direkt betroffenen neuen Freight-Zeitreihen wurden nach der Farbkorrektur und dem endgültigen vollständigen Testlauf erneut erhoben. Die zusätzliche P2-Backend-Kontrollreihe lief ebenfalls seriell. final-method.json und sämtliche ersten Rohreihen halten diese Grenze fest.

**P5 abgeschlossen; danach gestoppt. Kein P6, kein Balancing, kein Windows-Build.** P6 darf ausschließlich tatsächlich abgeschlossene Liefermengen einmalig in einer begrenzten Zeitstatistik zählen. Dispatch, nominelle Kapazität, Pause oder Load sind keine Ist-Lieferung; der P5-Theoriewert darf dafür nicht verwendet werden.
