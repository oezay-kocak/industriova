# INDUSTRIOVA 0.3 – Phase P10: Final UI Consistency und Early-Game-Audit

Stand 23.10.2026. Ausgangspunkt ist der tatsächliche uncommittete/ungetrackte P9-Working-Tree mit 1.938 Tests. P10 ist implementiert und am finalen Quellstand geprüft. Kein neuer Windows-Build, keine Versionsanhebung, keine Events oder Tutorialmechanik.

## 1. Vorbereitung und Sicherung

Die acht beauftragten P0-/Roadmap-/P3-/P5-/P6-/P7-/P8-/P9-Berichte und die tatsächlichen Komponenten wurden geprüft. Neue unabhängige Sicherung `artifacts/phase10/backup-20261022T224910Z`: 958 Quelldateien einschließlich ungetrackter und uncommitteter Inhalte, CRC-/SHA256-geprüft und als `before-tree` extrahiert. Fünf persönliche Saves frisch vor P10 roh und über SQLite read-only konsistent kopiert, integrity_check=ok; die aktuellen Originalhashes sind die Referenz, frühere Spielerfortschritte werden nicht gegen P9 zurückgesetzt. Die vollständige P9→P0-Sicherungskette bleibt gebunden. Originale werden weder geladen/migriert noch beschrieben. Die 4083 vorhandenen Build-Dateien sind einzeln unverändert. Wiederherstellung in einen neuen Ordner anhand Manifest/SHA256; niemals pauschal über aktuelle Saves extrahieren.

Die im Auftrag erwähnten zehn Nutzer-Screenshots waren in der Textanlage nicht vorhanden. Die konkrete Textspezifikation und tatsächliche Industriova-Komponenten waren die verfügbare Referenz. Ein Abgleich mit diesen fehlenden zehn Originalbildern wird nicht behauptet.

## 2. Tatsächlich geänderte Dateien

Alle produktiven Änderungen, angepassten bestehenden Tests und neuen P10-Werkzeuge/Dokumente relativ zum gesicherten tatsächlichen P9-Stand:

- `docs/industriova-03-phase10-final-ui-polish-report.md`
- `docs/industriova-03-phase10-resource-price-audit.md`
- `scripts/phase10_backup.py`
- `scripts/phase10_benchmark.py`
- `scripts/phase10_capture.py`
- `scripts/phase10_cent_final_validation.py`
- `scripts/phase10_click_roundtrip.py`
- `scripts/phase10_complete.py`
- `scripts/phase10_deliver.py`
- `scripts/phase10_evidence.py`
- `scripts/phase10_final_validation.py`
- `scripts/phase10_inventory_benchmark.py`
- `scripts/phase10_migration_audit.py`
- `scripts/phase10_preserve_legacy_outputs.py`
- `scripts/phase10_price_capture.py`
- `scripts/phase10_recheck_validation.py`
- `scripts/phase10_resource_audit.py`
- `scripts/phase10_resource_capture.py`
- `scripts/phase10_verify.py`
- `scripts/phase10_visual_queue.py`
- `scripts/phase10_write_report.py`
- `src/production_zero/core/commands.py`
- `src/production_zero/ui/event_feed.py`
- `src/production_zero/ui/factory_view.py`
- `src/production_zero/ui/factory_view_v2.py`
- `src/production_zero/ui/freight_assignment.py`
- `src/production_zero/ui/freight_lines.py`
- `src/production_zero/ui/freight_view.py`
- `src/production_zero/ui/interaction_polish.py`
- `src/production_zero/ui/inventory_workspace.py`
- `src/production_zero/ui/main_window.py`
- `src/production_zero/ui/market_view.py`
- `src/production_zero/ui/pz_controls.py`
- `src/production_zero/ui/release_board.py`
- `src/production_zero/ui/resource_prices.py`
- `src/production_zero/ui/supply_categories.py`
- `src/production_zero/ui/supply_view.py`
- `tests/test_factory_ui.py`
- `tests/test_final_language_alignment.py`
- `tests/test_live_playtest_polish.py`
- `tests/test_phase10_polish.py`
- `tests/test_phase10_polish_ui.py`
- `tests/test_phase3_inventory_ui.py`
- `tests/test_phase5_freight_ui.py`
- `tests/test_phase6_freight_statistics_ui.py`
- `tests/test_phase7_economy.py`
- `tests/test_phase7_economy_ui.py`
- `tests/test_phase9_navigation_ui.py`
- `tests/test_playtest2_consistency_followup.py`
- `tests/test_production_board_split.py`
- `tests/test_recipe_retirement.py`
- `tests/test_research_interaction_polish.py`
- `tests/test_secondary_modernization.py`
- `tests/test_ui_polish_interactions.py`
- `tests/test_unified_production_ux.py`

`implementation.diff`, `final-source-sha256.json` und `delivery-manifest.json` binden den endgültigen Stand. Keine Änderungen an Datenkatalogen/Rezepten oder bestehenden Preisformeln. Alte Testidentitäten bleiben erhalten; Erwartungen an autorisiert entfernte Controls, neue Genesis und Centformatierung wurden auf den neuen Sollzustand aktualisiert. Diagnosevorläufe sind nicht die finale Regression. Ein bestehender Klicktest wartet nun vor seinem expliziten Scrollen auf die vorhandene verzögerte 0/50/150-ms-Wiederherstellung und nimmt den sichtbaren Slot; alle Gameplayassertions bleiben erhalten. Nach der letzten produktiven Float-/Cent-Korrektur wurden die vollständigen 97 Module und sämtliche elf DPI-Module nochmals frisch auf exakt dem endgültigen Quellstand gerechnet (`accepted-validation.json`). Frühere Teilläufe, Fehler und die zwischenzeitlichen 20er-Timingprüfungen bleiben nachvollziehbar erhalten, ersetzen diesen finalen Gesamtlauf aber nicht. Ein unverändert-logisches Dashboard wurde zuvor auf seine ursprünglichen Zeilenenden zurückgestellt; die endgültige Regression enthält bereits diese Originaldatei.

## 3. Wiederverwendete Komponenten

`IndustrialDialog`, `MaterialFrame`, `GameButton`, `RaisedPZButton`, vorhandene Accent-Paletten, industrielle Fonts, Kartenrenderer, ResourceSelectionTiles, virtuelle Supply-/Inventory-Pools, vorhandene Install-/Return-/Sell-/Route-Commands und persistente Communications. Gelb bestätigt, Rot bricht ab/verkauft, Blau setzt Routen zurück, Grau navigiert. Farbige Aktionsflächen behalten schwarze Beschriftung. Kein neues Iconset, Bitmapmaterial, Dropdown oder eigenes Handels-/Routensystem.

## 4. Rename-Stift und Dialog

`building_title_layout` berechnet sichtbaren Text und Stiftposition gemeinsam aus derselben tatsächlich gezeichneten Schrift über QFontMetricsF. Stiftabstand 8 logische Pixel, 32×32-Klickfläche. Resources/Factory/Energy verwenden dieselbe FactoryStage; Freight dieselbe gemeinsame Messung mit vorab reserviertem Statistikplatz. Lange Namen werden kontrolliert elidiert; vollständiger Name im Hover. Rechts gelegene Statistik-/Pause-/Guide-Controls überlagern den Stift nicht. Titelklick bleibt auf den tatsächlichen Titelbereich begrenzt, vorhandene Rename-Aktion bleibt erhalten.

Rename hat nur Name, Eingabefeld, gelbes YES–SAVE und rotes NO–CANCEL. Typselector, TYPE CHANGE, Investitionshinweis und Zusatzfläche sind entfernt. Der öffentliche RenameHall-Command lehnt jede mitgesendete Spezialisierung vollständig vor Mutation ab, auch dieselbe Spezialisierung. Alte Felder bleiben für Aufrufkompatibilität vorhanden, erlauben aber keine Spielerumklassifizierung. Historische Site-Spezialisierungen und interner kompatibler Legacy-Install-/Migrationspfad bleiben lesbar. Bau wählt den Typ weiterhin vor der Quote. P7-Preis-/Investmentfunktionen werden nicht neu berechnet.

## 5. Preise und Cent-Konsistenz

`resource_prices.price_number` nutzt Decimal aus der dezimalen Darstellung und ROUND_CEILING für positive Einzelpreise, exakt zwei Stellen einschließlich Nullen. Beispiele: 226.1625→226.17, 299.1375→299.14, 497.4→497.40 und 1.8125→1.82. Kleine positive Preise werden sichtbar 0.01; nichtendliche Eingaben sind abgelehnt. Große Beträge behalten exakten Geldtext, bei begrenzter Kachelbreite steht er im Hover. Bei Float-Eingaben werden höchstens zwei binäre ULP Abstand zu einem exakten Cent als Repräsentationsrauschen erkannt; beispielsweise 1.1×1.1 ergibt korrekt 1.21 statt 1.22. Echte gebrochene Cent und hochpräzise Decimal-Eingaben werden weiterhin strikt aufgerundet. Alle 353 Basispreis-Anzeigetexte sind vor/nach dieser Absicherung exakt gleich; `price-display-equivalence.json` belegt die Gültigkeit der endgültigen Bildaufnahmen.

Guide, Resource-/Global-Browser, Produktionspicker, Tooltips und bisherige Market-Einzelpreisfelder verwenden die zentrale Preisquelle; Supply-/Bau-/Slot-/Linienpreise zeigen ebenfalls zwei Dezimalstellen. Cash-Kontostände/XP/kompakte Rewardkennzahlen sind keine neu quotierten Einzelpreise. Intern bleiben alle 353 Festpreise unverändert und hochpräzise. Tooltip erklärt ausdrücklich die Cent-Aufrundung und die davon getrennte Abrechnung mit präzisem eingefrorenem Einzelpreis. Gesamtquotes von Käufen/Resale/Ausbau bleiben der tatsächlich gebuchte Centbetrag; es wurde keine ökonomische Rundungsregel ersetzt. Die vier konkreten Preisbeispiele sind in 24 zusätzlichen echten Guide-Aufnahmen und Breitenassertions belegt.

## 6. Rohstoff-Audit

Separater Bericht `industriova-03-phase10-resource-price-audit.md`: 49 Primärrohstoffe, 353 rekursive Kettenkennzahlen, 76 echte Engine-Strategien, MK1/10/99 und Legendary-Vergleiche. Copper bietet bei gleicher nomineller Leistung +40 % gegenüber Iron, Crude Oil +120 %. Freight begrenzt alle verglichenen Einzeltrucks; höherer Preis bleibt trotzdem ein relativer Direktverkaufsvorteil. Downstream-Bedarf schafft weitere Verwendungen, ist kein automatisch bewiesener finanzieller Ausgleich. Das separate Dokument trennt tatsächliche Cash-Buchungen, nominale Raten, Opportunitätsmathematik, Freischaltungen und unbelegte globale Optimierungsannahmen. Keine Balanceänderung in P10.

## 7. Kompakter Freight-Header

Hauptzeile: Gebäudetitel+Stift links; zusammenhängend SELL/CONTRACT/CONSORTIUM/TOTAL rechts; Pause ganz rechts im vorhandenen Overview-Rahmen. Stagehöhe 188→64 logische Pixel, Overview-Abstände reduziert. Slotzahl, aktive Sendungen und Messfenster sind im Hover, keine zusätzlichen sichtbaren Statistikzeilen. Die vier Properties und tatsächlichen P6-Raten bleiben facility-spezifisch und verwenden unverändert das 60-Sekunden-Fenster. Warm-up zeigt kompakte 0/min; der genaue Mess-/Nullzustand steht im Hover. Große Raten werden kompakt, vollständige Zahlen und Beobachtungsfenster im Hover ausgegeben. Statistikgruppe reserviert Platz vor der Titel-Elision.

## 8. Inventory und konkrete Auswahl

Available-/Stacks-/In-Use-Zähler, Select All/Clear-Buttons, permanente Selected-/Sale-Texte, Quantityleiste, Install/Reset/Sell-Fußleiste sind entfernt. Vorhandener Header, Karten und Kategorieauswahl bleiben. Normaler Klick wählt eine konkrete erste Stapel-ID, Ctrl ergänzt/toggelt Stapel, Shift erweitert den Bereich. Ctrl+A erhält die gesamte Auswahlfunktion ohne Toolbar. Rechtsklick auf eine bereits ausgewählte Karte erhält die gültige Mehrfachauswahl.

SELECT QUANTITY öffnet einen kompakten vorhandenen Industriova-Dialog ohne irreführenden Kaufpreis. Die Reihenfolge konkreter IDs steht im Hover, Menge entspricht genau den ersten N IDs des gewählten Stapels, andere ausgewählte Stapel bleiben erhalten. Kartenhover nennt gewählte/verfügbare Menge und gespeicherte Freight-Route einschließlich Invalidzustand. Keine Kartenkapazitätsgrenze, keine neue Eigentumstabelle. Virtuelle Darstellung bleibt begrenzt.

## 9. Kontextaktionen und Atomarität

INSTALL, SELL und bei Freight RESET ROUTE sind über echte Kontextklicks erreichbar. Installation verwendet denselben Facility-/Slotdialog und die bestehenden InstallCardInHall/InstallFreightCard-Regeln. Für Mehrfachauswahl werden passende freie Plätze geplant, der erste Platz wird ausgewählt, weitere zuerst in derselben Facility, sonst kompatibel verteilt. `InstallInventoryCards` validiert die gesamte Gruppe mit denselben Commands auf einer isolierten Zustandskopie, bevor der synchrone CommandBus die vorbereiteten Installationen übernimmt. Keine alternative Installationsdomäne. Das Kopieren kostet bei großen Gruppen zusätzlich Zeit und ist kein periodischer Refreshpfad.

SELL zeigt Anzahl, Maschinennamen und Gesamterlös, gelbes YES–SELL und rotes Cancel. Nach Bestätigung werden Session, Existenz, Available-Status und unveränderter Erlös erneut geprüft; bestehendes SellMachines erhält die 80-%-Investitionsregel und Gruppenatomarität. Zweiter Verkauf derselben IDs ist unmöglich. RESET ROUTE verwendet den bestehenden P3-Command und schützt Session/aktive Sendungen. Bestehende Kauf→Install→Return→Reinstall→Sell-Tests bleiben erhalten; neue Fälle klicken die tatsächlichen Kontextaktionen.

## 10. Storage Expand

Der kleine Headerbutton öffnet STORAGE EXPANSION mit tatsächlichem Zuwachs, aktuellem/neuem Global Storage und zentraler Quote. Beispiel Level0: +18,820 U, 75,280→94,100 U, $250.00. Cancel ist mutierungsfrei. ExpandInventoryStorage hat optionale erwartete Stufe/Quote; Wiederholung derselben bestätigten Quote wird vor einer weiteren Abbuchung abgelehnt. Neue Session verwirft alten Dialogintent. Bestehende Aufrufer ohne erwartete Quote bleiben kompatibel. Keine neue Kostenformel oder SessionWriter-/Schemaänderung.

## 11. History/Inbox

Die vorhandenen umgehängten RaisedPZButtons nutzen die Operationsfläche mit mindestens 42 Pixel Höhe und gut lesbarer vorhandener Schrift. Normal Grau, neue persistente Unread-Nachricht gelbe vorhandene Primary-Fläche mit schwarzer Schrift. Ein auf den bestehenden Feed begrenzter 1.2-s-Timer variiert nur dezent den Hoverhelligkeitszustand dieses Buttons. Kein Header-/MainWindow-Neuaufbau pro Phase, keine zweite Unread-Verwaltung. Lesen setzt den persistierten bestehenden Mark-read-Zustand, beendet den Timer und stellt Grau her; Hide/Close stoppt den Timer, Show liest den echten Unreadzustand erneut. Save/Load/New Game und History-/Tickerbestand sind regressionsgeprüft.

## 12. Industrial Supply

Kanonische 15 Common-Maschinenangebote umfassen drei Rohstoffmaschinen, drei verschiedene Fabrikstufen, fünf Energiearten und vier Freightfamilien. Direkte Auswahl: **ALL, RESOURCES, ENERGY, PROCESSING, FABRICATION, ASSEMBLY, FREIGHT**. ALL ist Standard. Die sieben Buttons decken zusammen sämtliche 15 IDs ab; kein Assembler wird in einer undurchsichtigen Factory-Gruppe versteckt. CATEGORY nutzt die vorhandene schwere industrielle Schrift. Bei regulärer Breite eine Zeile, bei kleineren Flächen Umbruch. Keine Suche und kein sichtbarer Kategorie-Dropdown/Flyout.

Daily/Common, beide täglichen Angebotsfamilien, Mengen/MAX, kaufabhängige Zustände und Erwerb ins Inventory bleiben erhalten. Derselbe virtuelle Common-Pool wird wiederverwendet. ALL darf beim kleinen heutigen 15er-Katalog alle 15 Karten materialisieren; das ist keine abgeschaltete Virtualisierung. Vorherige strikt-kleiner-als-Katalog-Assertions wurden auf die korrekte obere Grenze angepasst, eindeutige IDs/keine Duplikate und recycelte Bindungen bleiben geprüft.

## 13. Drei kostenlose erste Sites

Nur `_create_initial_state` ergänzt Drilling Field 1 und Agricultural Estate 1 zum bisherigen Mining Complex 1. Je eine freie Linie/ein freier Slot und festgelegte Spezialisierung. Genesis behält $1,250.00, acht unplatzierte Starterkarten, vorhandene Rohwaren, XP/RP/Research und Energy-Voraussetzungen. Kein zusätzlicher Gratisproduzent. Zweite Site jedes Typs wird korrekt als zweiter Standort quotiert ($4,000.00); erste zusätzliche Slots nach P7. Laden alter Saves ruft Genesis nicht auf, es gibt keinen doppelten kostenlosen Effekt. Der vorhandene finite Starttest nutzt nun die bereits vorhandenen Erststandorte und besteht mit realen Maschinen-/Solar-/Transportkäufen.

## 14. Freight-Ressource und Delivery Target

Die bestehende Ressourcenauswahl zeigt SELECT A RESOURCE, Browser und Cancel. Große Prozessüberschrift, zusätzliche Fahrzeugtitelzeile und zweiter großflächiger Zielscreen sind entfernt. Ressourcenwahl öffnet unmittelbar den kleinen modal geführten IndustrialDialog SELECT DELIVERY TARGET. MARKET/SELL, CONTRACT, CONSORTIUM CONTRACT und EVENT stehen nebeneinander; schmalere Dialoge verwenden zwei Spalten. Bestehende neutrale Auswahlflächen, gelbe Auswahl/CONFIRM, rotes CANCEL; keine großen Warenkarten und kein Dropdown.

Verfügbarkeit stammt aus dem bestehenden `target_problem`/`validate_route`. Nicht benötigte/abgelaufene persönliche Contracts, fehlende Mitgliedschaft/Consortium-Ziele und Event bleiben sichtbar deaktiviert mit Grund im Hover. Normale Route setzt keinen neuen Versand in Gang, solange nicht bestätigt. Auswahl und Bestätigung nutzen unverändert AssignFreightVehicles mit Sessionidentität, vollständigen konkreten IDs, Ursprungs-Snapshot und erneuter Waren-/Zielprüfung.

## 15. Rückkehr, Session und Save

Erfolg schließt Dialog und zeigt das vorhandene gecachte Board; nur betroffene Karten/KPIs werden aktualisiert, kein unnötiger MainWindow-Rebuild. Cancel/Esc im Zieldialog führt zur unveränderten Ressourcenwahl; Cancel im Ressourcenbrowser zurück zum Board. Haupttabwechsel, View-Hide, Load/New Game/Reset verwerfen Dialoge und alte IDs. Doppelte Confirm-Geste kann den abgeschlossenen Intent nicht erneut anwenden. Bestehende aktive Sendungen behalten Cargo-/Preis-/Zielsnapshots. P4-Auswahl, Busy-/MK-/Routenregeln, P9-Freight-only und P6-Buchungen bleiben erhalten.

Schema **9** unverändert. Alle **16/16** historischen Migrationen liefern vollständig SHA256-identische normalisierte Payloads zum akzeptierten Vorzustand und sind idempotent. Kein neues persistentes UI-Register, Save-/SessionWriter unverändert. Nach Abschluss 5 persönliche Originale und 4083 Build-Dateien unverändert.

## 16. Performance

Seven serial samples, real Qt offscreen widgets at 1366x768/100%, same exact card IDs/counts/stock and one-site fixture. Synthetic 500-slot Freight stress. Supply category cycle explicitly includes seven P10 versus four P9 categories; not normalized as equal work. No FPS/native latency claim.

| Operation | P9 Median / Maximum ms | P10 Median / Maximum ms |
| --- | --- | --- |
| inventory.500.refresh | 28.688 / 29.698 | 36.990 / 39.947 |
| inventory.500.scroll | 18.712 / 27.919 | 27.544 / 36.552 |
| inventory.5000.refresh | 59.335 / 75.701 | 69.462 / 88.501 |
| inventory.5000.scroll | 20.774 / 30.793 | 26.675 / 34.580 |
| inventory.10000.refresh | 102.044 / 109.709 | 113.129 / 117.732 |
| inventory.10000.scroll | 21.317 / 24.132 | 29.937 / 34.608 |
| main.20_tab_switches | 699.814 / 1012.360 | 749.074 / 1033.991 |
| supply.all_categories_cycle | 188.434 / 363.514 | 339.785 / 497.325 |
| supply.three_shared_categories | 161.546 / 167.591 | 172.672 / 197.464 |
| resources.353_open_close | 313.570 / 790.495 | 342.309 / 798.034 |
| history_inbox.open_close | 11.526 / 13.834 | 10.787 / 13.234 |
| header.refresh | 0.131 / 0.369 | 0.139 / 0.368 |
| storage_dialog.open_cancel | 3.965 / 13.951 | 4.065 / 15.074 |
| freight.500_runtime | 193.330 / 234.266 | 182.156 / 212.776 |
| freight.resource_target_cancel | 1568.396 / 1914.445 | 1579.813 / 1759.795 |
| snapshot.500 | 11.329 / 11.947 | 9.299 / 11.322 |
| serialize.500 | 6.783 / 7.107 | 5.551 / 5.749 |
| save.500 | 18.583 / 19.852 | 19.011 / 20.315 |
| load.500 | 15.376 / 18.913 | 15.248 / 19.287 |
| inventory.500.matched_refresh | 27.934 / 30.943 | 29.639 / 32.785 |
| inventory.500.matched_scroll | 18.274 / 27.411 | 18.724 / 27.067 |
| inventory.5000.matched_refresh | 58.847 / 77.242 | 57.364 / 79.027 |
| inventory.5000.matched_scroll | 19.361 / 28.007 | 18.434 / 27.569 |
| inventory.10000.matched_refresh | 113.353 / 119.806 | 111.431 / 114.239 |
| inventory.10000.matched_scroll | 26.873 / 31.090 | 23.302 / 26.781 |

Inventorypool-Geometrie P9→P10: {'500': {'rows': 500, 'pool': 30}, '5000': {'rows': 5000, 'pool': 30}, '10000': {'rows': 10000, 'pool': 30}} → {'500': {'rows': 500, 'pool': 36}, '5000': {'rows': 5000, 'pool': 36}, '10000': {'rows': 10000, 'pool': 36}}. Serialisiertes 500er-Payload: 286,413→286,413 Bytes. Gleiche Messfixture mit einer Site für beide Quellen; die autorisierte Genesis-Erweiterung wird separat geprüft. Der komplette Supply-Kategoriezyklus umfasst P10 sieben statt P9 vier Kategorien und ist daher ausdrücklich mehr Arbeit; die drei gemeinsamen Kategorien sind zusätzlich identisch gemessen. Durch entfernte Toolbars zeigt das gleich große Inventoryfenster mehr Karten: Pool 30→36. Vollflächen-Refresh/Scroll haben damit mehr echte Zeichenarbeit. Die zusätzlich ausgewiesenen matched-Werte begrenzen ausschließlich die sichtbare Scrollhöhe in beiden Quellen identisch auf 400 Pixel; Kartenanzahlen 500/5.000/10.000 bleiben unverändert, ebenso konkreter Karteninhalt und Breite. Diese Probe trennt die Layoutdichte von den Kosten derselben sichtbaren Datenmenge. Größere Maxima und einzelne kalte Zustandswechsel sind kein Nachweis konstanter nativer FPS. Rohwerte stehen im Performanceordner.

## 17. Tests

Final **1,994 Tests / 97 Module**, 0 Fehler/Skips, alle **1,938** bisherigen Testidentitäten erhalten, **56** zusätzliche Fälle. Zusätzlich **518 Fälle / 11 vollständige relevante Module bei 200 %**. `regression-summary.json` prüft die Multimenge der XML-Testidentitäten gegen final P9, nicht bloß eine behauptete Gesamtzahl.

Neue Fälle betreffen sichere Cent-Aufrundung/Extremwerte, drei kostenlose Sites und unveränderte Altloads, Rename-only und atomare Umklassifizierungssperre, erwartete Storagequote/Doppelbestätigung/Sessionwechsel, ganze Installgruppen, wirkliche Kontextklicks einschließlich Menge/Reset, mehrfache Stapel, veraltete Salequotes/Installation während Dialog, dynamische Stifte, alle Kategorien, persistente Inbox, Freight-Zielverfügbarkeit und Cancel/Esc/Tab/Reset. Bestehende umfassende Busy-/aktiven Sendungs-/Contract-/Consortium-/Load-/New-Game-/Drag- und Roundtriptests sind erhalten und erneut ausgeführt. Zusätzlich läuft bei 100 und 200 % jeweils ein vollständig durch tatsächliche Zeigerklicks geführter Pfad: Supply-Kaufbutton → Inventory-Rechtsklick INSTALL → Facility-Bestätigung → Board-Rechtsklick RETURN TO INVENTORY → erneute Kontextinstallation → Rücknahme → Inventory-Rechtsklick SELL und gelbe Bestätigung. Dieselbe Karten-ID/Instanz bleibt bis zum Verkauf erhalten, alle acht Starter-IDs bleiben vorhanden; $275.00 Kauf und $220.00 Resale werden exakt gebucht. Die beiden zusätzlichen Ablaufbelege stehen unter `click-roundtrip-dpi1/result.json` und `click-roundtrip-dpi2/result.json` und sind nicht doppelt als pytest-Fälle gezählt.

## 18. Visuelle Vorher-/Nachher-Prüfung

**342 tatsächliche PNG-Aufnahmen**: 150 P9-Vorherbilder, 162 P10-MainWindow-/Dialogbilder sowie 24 zusätzliche Guide-Preisbeispiele und sechs gefüllte Global-Resources-Ansichten. Je 1366×768,1600×980,1920×1080 bei Qt100/200 %. Alle tatsächlichen Pixelmaße, DPR-Zuordnung und SHA256 geprüft. Separate Dialog-/Inboxfenster werden als eigene reale Qt-Surfaces aufgenommen, nicht in MainWindow-Pixel hineinmontiert. Die logischen Fenstermaße bleiben die genannten Auflösungen, die PNG-Pixel bei 200 % jeweils doppelt; das wird nicht als Test eines 683-Pixel-Fensters ausgegeben.

Separater finaler Sichtungspass: **17 konkrete Bilder tatsächlich betrachtet**, alle sechs Größen-/DPI-Profile vertreten. Dateiliste/Hashes/Befunde in `visual-review.json`. Gefunden und vor finalen Captures behoben: abgeschnittene Zieldialogoptionen durch unzureichende Dialogbreite, zu kleine per Theme überschriebene CATEGORY-Schrift sowie verdeckter erster Buy-Footer durch unnötige zweite Kategoriezeile. Finale Bilder zeigen kompakte Dialoge, lesbare Preise, direkt anschließende Stifte und erhaltene Industriova-Materialien. Kein Anspruch, alle 342 Bilder einzeln visuell abgenommen zu haben.

Beispiele: `screenshots/after/dpi1/supply-default-1366x768.png`, `screenshots/after/dpi1/inventory-filled-1366x768.png`, `screenshots/after/dpi2/delivery-target-confirm-1366x768.png`, `price-screenshots/dpi2/ai_accelerator-1366x768.png` unter `artifacts/phase10`.

## 19. Native Windows-Handabnahme

Offen bleibt die persönliche Windows-Maus-/DWM-/GPU-Abnahme mit Mehrmonitor-/DPI-Wechsel, subjektivem Hover-/Scrollgefühl, langen Sessions und tatsächlich physisch kleinen HiDPI-Arbeitsflächen. Offscreen/QTest/PNG-Sichtung sind keine menschliche Freigabe. Insbesondere echte Rechtsklick-Mengenwahl, mehrere gemischte Installziele, pulsierende Inbox und Routenwechsel bei laufenden Sendungen im Playtest prüfen.

## 20. Grenzen und Stopp

Der Kettenaudit ist keine globale Gewinnoptimierung aller Firmen und 76 synthetische Rohstoffläufe sind keine organisch gespielten Strategien. Höherpreisige Direktverkaufsrohstoffe bleiben ein separater Balancepunkt; keine stillschweigende Preisänderung. Gruppeninstallation kopiert den Zustand für vollständige Vorprüfung und kann bei sehr großen Gruppen zusätzlichen Aufwand verursachen. Sehr große Resource-/Freightboards bleiben wie zuvor nicht kostenlos; gemessene Maxima bleiben im Rohbericht. Die zehn im Prompt referenzierten Original-Screenshots fehlen weiterhin.

Nach P10 gestoppt. Kein Windows-Build, keine Events, kein Tutorial, keine neue Marktmechanik, keine zusätzlichen Consortium-Systeme. Persönliche Saves/Builds unverändert. Start aus aktuellem Quellstand weiterhin `.venv/Scripts/python.exe -m production_zero.app`; sichtbare Versionskennung bleibt absichtlich 0.2.0.dev6.
