# INDUSTRIOVA 0.3 – Phase 3: Inventory UI und Industrial Supply

Stand: 21.10.2026. Ausgangspunkt ist der vollständig gesicherte P2-Working-Tree, einschließlich uncommitteter/ungetrackter Dateien. Ausschließlich P3; kein Windows-Build.

## 1. Sicherung und Bestandsschutz

Sicherung: `artifacts/phase3/backup-20261021T205548Z/`, 42,927 Dateien und 27,950,626,238 Quelldatei-Bytes. SHA256 pro Datei mit Speicherzuordnung im Manifest; unveränderte Dateien verweisen rekursiv auf die erhaltenen P2-/P1-/P0-Sicherungen, neue Dateien auf das Delta. Beide neuen ZIPs sind CRC-geprüft; `SHA256SUMS.json` hält ihre und die Manifest-/Saveprüfsummen fest. Zusätzlich besteht eine unabhängige `source-baseline.zip`; daraus stammt `before-tree/`. Große vorhandene ZIPs bleiben mit Originalpfad und SHA256 als Abhängigkeiten erhalten. Wiederherstellung ausschließlich in einen neuen Ordner, anschließend Hashvergleich; kein Rücksetzen auf Git-HEAD und kein pauschales Überschreiben aktueller Saves.

Alle fünf persönlichen SQLite-Dateien wurden zusätzlich roh und als konsistente SQLite-Backups gesichert, jeweils `integrity_check=ok`. Die abschließende Kontrolle bestätigt 16,103 geschützte Bestandsdateien und alle fünf Original-Saves unverändert. Von Bestands-UI-Tests neu geschriebene alte Previewpfade wurden unter `legacy-test-captures/` erhalten und die alten Referenzen nach Backup-SHA256 wiederhergestellt; `legacy-capture-preservation.json` dokumentiert dies. Originalgrafiken, P1-Atlas/Caches außerhalb der ausdrücklich geänderten UI, Wirtschaftsdaten, Simulation, Template-Domäne, Serializer/Writer und bestehende Builds sind geschützt. Tests, Benchmarks und Captures verwenden eigene AppData-/Tempverzeichnisse unter `artifacts/phase3`; kein Legacy-Import.

## 2. Produktive Änderungen und Wiederverwendung

Alle folgenden Pfade liegen unter `src/production_zero/`.

| Datei | Tatsächliche Änderung |
| --- | --- |
| `ui/inventory_view.py` | Standardmäßig modernes Inventory; vorhandener Header, `InventoryCardFrame`, Kartenrenderer, Hover und Leistungsprojektionen bleiben Grundlage. Expliziter alter Komponentenmodus ausschließlich für erhaltene Legacy-QA; MainWindow erzeugt weder Crafting noch Scrap-/Pack-/Market-/Kapazitätsbedienung. |
| `ui/inventory_workspace.py` (neu) | Begrenzter wiederverwendeter Kartenpool, Available-Stapel, konkrete ID-Auswahl/Menge, Kategorien, Install/Route-Reset/Sell, Tastaturauswahl und Sessionreset. Kein eigener Kartenbestand. |
| `core/inventory.py` | `CardInventoryRow.card_ids` ergänzt die bestehende Projektion um sämtliche konkreten IDs eines Stapels; Available und In Use. Keine neue Ownership-Tabelle. |
| `ui/main_window.py` | Inventory-Haupttab, bestehender sichtbarer Refresh/Dirty-Hook für verborgene Views, gezielter Reset bei Load/New Game. Neue Rücknahme-/Verkaufsaktionen aktualisieren globale Werte und markieren Inventory/Supply. |
| `ui/supply_view.py` | Vier grundlegende Kategorien Resources/Factory/Energy/Freight; Search-/Sort-/×1-/×4-Controls entfernt. P1-Common-Raster und Daily-Bänder erhalten. Einzelpreis, Kaufdialog, feste Quote/Operations-ID, keine Facility-/Slotkaufbedingung; aktuelle Daily-Offer-ID auch bei wiederholter Qualität und gleichem Preis, ohne zusätzliches Cachewachstum. |
| `ui/release_dialogs.py` | `InventoryPurchaseDialog` auf bestehendem IndustrialDialog: Menge, MAX, Cash, Einzel-/Gesamtpreis, eindeutige Bestätigung und MAX=0. Geschlossene Bestätigungs-/Hinweisdialoge werden freigegeben; umgebrochene Texte erhalten nach Layout ihre tatsächlich benötigte Höhe, auch bei 200 %. |
| `ui/release_board.py`, `ui/release_freight.py` | Eigene RETURN TO INVENTORY-Kontextaktion neben SELL, bestehende Mehrfachauswahl, P2-Gruppencommand, Busy-Erklärung; beendete Kontextdialoge freigeben. |
| `core/commands.py` | Kleine zusätzliche `ResetInventoryFreightRoutes(ids)`-Validierung: eindeutig, vorhanden, Freight, unplatziert, nicht busy; gesamte Gruppe vor Mutation prüfen. |

Keine Änderungen an Preisen, Rezepten, Rarity-/MK-Formeln, Simulation, `PurchaseTemplates`, Save-Schema oder Buildkonfiguration. Die einzige Domain-Erweiterung löscht auf ausdrücklichen Wunsch gespeicherte Routen verfügbarer idle Fahrzeuge.

## 3. Bedienpfad und konkrete Kartenidentität

Industrial Supply → Kategorie/Angebot → Menge oder MAX → PURCHASE TO INVENTORY → Inventory → Karte auswählen → INSTALL → passende Facility und freier freigeschalteter Slot. Der Kauf funktioniert auch ohne passende Facility und bei komplett belegten Boards. Installation dispatcht ausschließlich `InstallCardInHall` beziehungsweise `InstallFreightCard`; kein Kauf, keine neue ID. Die Core-Commands validieren das gewählte Ziel beim Commit erneut. Fehlende/inkompatible Gebäude beziehungsweise Ressourcenspezialisierungen und belegte/gesperrte Plätze werden erklärt.

Inventory zeigt ausschließlich verfügbare Karten. Die Kopfzeile nennt zusätzlich die bereits auf Boards eingesetzte Anzahl. Kategorien, Name, MK/Rarity, Bonus und Anzahl bleiben sichtbar; vollständige Namen und Leistung stehen in Detailzeile/Hover. Sehr lange Kartenbeschriftungen sind ausdrücklich gekürzt, damit der unveränderte Bitmaprenderer seine Mindestzellbreite nicht überschreitet. Vollständige Namen bleiben zugänglich.

Ein normaler Klick wählt genau eine konkrete Karte; das Mengenfeld erweitert diese Auswahl innerhalb desselben Stapels. Ctrl-Klick fügt eine weitere Karte hinzu; SELECT ALL AVAILABLE ist ausdrücklich gruppenbezogen auf die angezeigte Kategorie. Der Verkauf bestätigt stets die tatsächliche Anzahl und Summe. Stapelschlüssel berücksichtigen weiterhin MK, Rarity, individuelle Boni, Anschaffung, bezahlte Upgrades und Pause. Ähnlich aussehende Investitionsvarianten werden nicht zusammengelegt. `GameState.cards` plus Slotreferenzen bleiben allein autoritativ; Global Storage betrifft weiterhin physische Waren.

## 4. Rücknahme, Verkauf und Freight-Routen

Rechtsklick auf eine installierte Karte → RETURN TO INVENTORY, auch für die vorhandene Mehrfachauswahl. Die Aktion nutzt ausschließlich `ReturnMachinesToInventory`; SELL bleibt eine getrennte rote Aktion mit gelb/roter Bestätigung. Bei Rücknahme werden nur Slots geleert. Kartenobjekt/ID, MK, Rarity, Anschaffung/Upgrades, Boni, individuelle Pause, Produktionszuordnung und Teilzyklus bleiben erhalten. Die Simulation bleibt unverändert: unplatziert keine Fortsetzung, nach Installation bei gültigen Inputs/Energie/Storage genau der verbleibende Zyklus, Inputdebit am Abschluss.

Freight in aktiver reservierter Lieferung blockiert die gesamte Rücknahme; die UI erklärt den Grund. Idle-Rücknahme erhält die Route. Im Inventory zeigt die Einzelauswahl gespeicherte Ware/Ziel und kennzeichnet ungültige Einträge. RESET ROUTE fordert eine ausdrückliche Bestätigung, validiert die gesamte verfügbare idle Gruppe und entfernt nur deren Assignment. Aktive Sendungen/Reservierungen werden weder gelöscht noch geändert. Danach kann die Karte installiert und über den bestehenden Freight-Ablauf neu geroutet werden. Kein neuer Routing-Wizard aus P5.

Inventory-Sell verwendet `SellMachines` und die vorhandene Centabrundung je Karte: 80% dokumentierte Anschaffung plus bezahlte Upgrades; unbekannte historische Anschaffung ist 0. Cancel erzeugt keinen Command. Eine vollständig entfernte ID kann nicht nochmals ausgezahlt werden. Gruppenvalidierung und Busy-Schutz bleiben zentral in P2.

## 5. Supply-Quote, MAX und Bestätigung

Die Angebotskarte zeigt den Einzelpreis. Der Kaufdialog zeigt MK1/Rarity, Einzelpreis, verfügbares Cash, gewählte Menge und Gesamtpreis. Common-MAX verwendet `common_supply_max_quantity`, also Cash und das bestehende Limit 10.000 pro Operation, unabhängig von Slots und Warenlager. MAX=0 zeigt 0 und deaktiviert Menge/MAX/Kauf; Daily bleibt genau eine Karte und behält seine getrennten Tagesrechte.

Jeder neu geöffnete Kaufdialog erhält eine neue UUID. Beim ersten bestätigten Commit wird genau ein Command mit Quote (`expected_unit_price`), gewählter Menge und dieser Operations-ID eingefroren. Derselbe bestätigte Vorgang verwendet bei Wiederholung denselben Command. Cash, Preis und Daily-Gültigkeit werden weiterhin im P2-Commit geprüft; Ablehnung belastet weder Geld noch Tagesrecht teilweise. Nach Commit aktualisieren nur die sichtbare Projektion und globale Werte sofort; verborgene Views folgen dem P1-Dirty-/Entry-Hook. Mengenänderungen im Dialog dispatchen und refreshen keine App-Views. Beendete Kauf-/Install-/Kontextdialoge werden abgebaut.

`PurchaseTemplates` bleibt unverändert die unabhängige direkte Zielplatzierung: neue MK1/Common-Instanzen nach vollständiger Quote, Slot-/Typ-/Geldprüfung; kein Inventory-Zwischenschritt. Bestehende Copy/Paste-, MK50/Legendary-, Cancel-/Ablehnungsregressionen und die identischen P1-Aktionsmessungen laufen weiter.

## 6. Inventory-Skalierung und Fokus

Es werden nur Viewport-Reihen plus wenige Pufferreihen als vorhandene InventoryCardFrames materialisiert und neu gebunden. Logische Zeilen/IDs bleiben vollständig. Zusätzlich zur stark stapelbaren Drei-Typen-Fixture wird dieselbe Anzahl unterschiedlicher Investitionen als ebenso viele getrennte Stapel gemessen. Ein 10.000-Karten-Stapel allein wäre kein Nachweis für 10.000 unterschiedliche Zeilen.

Auswahl bleibt auf IDs, Refresh erhält Scrollposition und Poolidentität. Der Mengenwechsel aktualisiert nur Auswahl/Details und sichtbare Karten; keine neue Gesamtprojektion. Space/Return wählen, Pfeiltasten bewegen den Kartenfokus; beim Recycling wird ein unsichtbar gewordenes fokussiertes Item nicht unbemerkt zu einer anderen Karte. New Game/Load löschen Auswahl, aktive Zeile, Hover, sitzungsabhängige Zeilen-/Poolbindungen und Supply-Datenbindungen; geteiltes GameState-Objekt und CommandBus bleiben korrekt verbunden.

## 7. Messmethode und Ergebnisse

Windows 11 / Python 3.12.14 / Qt 6.11.1 offscreen, gleiche Fonts/Kataloge und ursprüngliche P1/P2-Workloads. Vorher stammt aus der neuen P3-Quellsicherung. Sieben frische Prozesse für Cold-UI und Kaufbursts, warme UI-Reihen 49 Werte; aktive und weitere Aktionen mindestens sieben. Nachher-Messungen erfolgen seriell nach den Tests. Zeiten sind Median / Maximum in ms, keine FPS-/p95-Garantie. Python-Speicher wird getrennt mit tracemalloc gemessen und umfasst die Fixture plus neue UI; Qt-/GPU-Speicher ist darin nicht vollständig enthalten. Zusätzlich wird das tatsächliche Windows-Prozess-Working-Set am Messpunkt erfasst; es enthält Qt, Assets, Fonts und zuvor erwärmte Caches desselben Prozesses, ist also kein isolierter UI-Zuwachs.

Die neue Inventory-Probe erzeugt sieben frische View-Instanzen im selben Prozess; Fonts und gemeinsame Assets können nach der ersten Instanz warm sein. Aufbau plus Show/Paint ist deshalb kein siebenfacher kalter Prozessstart. Im P2-Hauptfenster gab es keine verfügbare Inventory-UI. Daher wird kein erfundener UI-Beschleunigungsfaktor angegeben: Core-Projektion und Snapshot haben eine identische Vorher-Fixture, neue UI-Werte werden separat ausgewiesen.

| Karten / Stapelart | Zeilen | Projektion vorher ms | Projektion nachher ms | Neuer Aufbau + Show ms | Neuer Refresh ms | Scrollpaar ms | Kartenwidgets / alle Widgets | Prozess-Working-Set MiB | Python aktuell / Peak MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 500-stacked | 3 | 1.43 / 1.54 | 1.42 / 1.47 | 19.25 / 162.70 | 7.82 / 8.54 | 0.03 / 0.04 | 3 / 34 | 97.70 | 0.21 / 0.24 |
| 500-distinct | 500 | 2.31 / 15.89 | 2.52 / 2.66 | 103.40 / 107.30 | 40.26 / 49.53 | 67.70 / 69.84 | 42 / 73 | 100.29 | 0.42 / 0.43 |
| 5000-stacked | 3 | 14.41 / 14.79 | 13.44 / 13.56 | 30.32 / 34.77 | 20.36 / 22.99 | 0.02 / 0.03 | 3 / 34 | 109.07 | 1.36 / 1.90 |
| 5000-distinct | 5000 | 22.19 / 37.07 | 31.59 / 47.91 | 133.01 / 150.97 | 67.46 / 85.43 | 66.62 / 71.71 | 42 / 73 | 110.13 | 2.38 / 2.98 |
| 10000-stacked | 3 | 26.85 / 27.40 | 35.14 / 38.05 | 47.08 / 49.35 | 34.57 / 39.67 | 0.03 / 0.08 | 3 / 34 | 117.04 | 2.64 / 3.23 |
| 10000-distinct | 10000 | 58.19 / 59.96 | 73.26 / 74.06 | 187.37 / 201.21 | 125.87 / 136.96 | 72.07 / 77.13 | 42 / 73 | 119.58 | 4.39 / 5.79 |

Alle konkreten Karten-IDs sind erreichbar. Die sechs vollständigen Snapshot-Payloads stimmen vor/nach P3 jeweils in Bytes und SHA256 überein; kein Weglassen von Daten. Rohwerte: `before/inventory-ui-benchmark.json`, `after/inventory-ui-benchmark.json`.

### P1-Kontrollen mit unveränderten Workloads

| Messung | n vorher / nachher | Vorher Median / Max ms | Nachher Median / Max ms |
| --- | --- | --- | --- |
| ui: unlock.constructor.cold | 7 / 7 | 91.25 / 156.27 | 88.32 / 102.88 |
| ui: unlock.first_show | 7 / 7 | 139.76 / 178.15 | 132.53 / 157.01 |
| ui: unlock.rebuild.warm | 49 / 49 | 0.06 / 0.17 | 0.06 / 0.13 |
| ui: guide.first_open | 7 / 7 | 506.43 / 545.50 | 478.98 / 506.30 |
| ui: guide.search | 49 / 49 | 24.45 / 36.82 | 23.76 / 38.65 |
| ui: guide.filter | 49 / 49 | 58.00 / 253.80 | 58.00 / 224.26 |
| ui: leaderboard.picker_construct | 49 / 49 | 151.96 / 191.74 | 149.74 / 177.24 |
| ui: leaderboard.picker_filter | 49 / 49 | 16.01 / 24.14 | 15.57 / 20.15 |
| ui: leaderboard.changed_refresh | 49 / 49 | 0.18 / 0.66 | 0.17 / 0.54 |
| ui: selection.500.shift | 49 / 49 | 27.08 / 56.03 | 24.73 / 52.14 |
| rapid_bursts: rapid_ui.50.20_individual_purchases | 7 / 7 | 516.54 / 579.57 | 470.29 / 482.96 |
| rapid_bursts: rapid_ui.500.20_individual_purchases | 7 / 7 | 581.53 / 672.18 | 480.75 / 507.10 |
| active: 500.render | 7 / 7 | 150.36 / 171.80 | 135.48 / 145.39 |
| active: 500.refresh | 7 / 7 | 6.50 / 199.28 | 7.10 / 179.38 |
| active: 500.tick | 7 / 7 | 6.19 / 9.07 | 6.44 / 10.39 |
| active: 500.snapshot | 7 / 7 | 105.16 / 164.01 | 137.75 / 166.48 |
| active: 500.encoding | 7 / 7 | 94.29 / 96.00 | 90.84 / 94.74 |
| active: 500.commit | 7 / 7 | 44.03 / 47.20 | 41.64 / 45.12 |
| active: 500.full_save | 7 / 7 | 243.56 / 305.97 | 238.77 / 274.83 |
| active: 500.load | 7 / 7 | 169.76 / 229.43 | 165.80 / 173.69 |
| extended: 50.sale20 | 7 / 7 | 225.83 / 235.28 | 218.77 / 255.35 |
| extended: 50.mk4 | 7 / 7 | 25.45 / 26.31 | 25.49 / 28.77 |
| extended: 50.slots7 | 7 / 7 | 89.28 / 107.10 | 93.60 / 100.78 |
| extended: 50.recipe20 | 7 / 7 | 49.44 / 51.31 | 49.86 / 51.06 |
| extended: 50.copy_paste10 | 7 / 7 | 26.05 / 28.86 | 23.95 / 25.54 |
| extended: 500.sale20 | 7 / 7 | 227.32 / 234.21 | 225.10 / 243.37 |
| extended: 500.mk4 | 7 / 7 | 48.87 / 49.98 | 44.76 / 47.85 |
| extended: 500.slots7 | 7 / 7 | 105.22 / 121.67 | 90.53 / 106.98 |
| extended: 500.recipe20 | 7 / 7 | 70.62 / 73.47 | 66.85 / 74.30 |
| extended: 500.copy_paste10 | 7 / 7 | 31.00 / 55.10 | 27.74 / 49.06 |

Die Kontrollen belegen keine pauschale Beschleunigung. Insbesondere steigt die 500-Karten-Snapshot-Medianzeit von 105.16 auf 137.75 ms, obwohl Serializer und Snapshotquelle unverändert sind. Der vollständige Inventory-Refresh mit 10.000 getrennten Zeilen liegt ebenfalls über einem 16-ms-Framebudget. Diese Kosten werden ausgewiesen; die begrenzte Materialisierung ist keine Zusage nativer Framerate.

Alle weiteren Kontrollen, Callback-/Queuewerte und Rohreihen stehen in `comparison.json` und `comparison-tables.md`. Kaufbursts verwenden weiterhin die echte MainWindow-Verkabelung bei gleicher 50/500-Karten-Firma; normale Käufe bleiben wie in P2 unplatziert. Die 500-Karten-Aktivprobe behält alle Sites/Slots, 240 Historywerte und die gesamte Renderfläche. Keine kleinere Fixture zur Beschleunigung. Überschreitungen von 16 ms, erstmalige Materialisierung und große Snapshots bleiben aus den Maxima erkennbar; keine native Framerate- oder Langzeit-Leakgarantie.

## 8. Funktionale Tests und Save-Migration

**1381/1381 Tests in 83/83 Modulen bestanden, 0 Fehler, 0 Skips.** Alle ursprünglichen 1.336 Fälle mit gleicher Fallzahl in allen 82 Bestandsmodulen plus 45 neue P3-Fälle. Serielle Ausführung; vollständige Modulnachweise unter `final-tests/`, Zählung `final-test-summary.json`, Herkunft `final-tests/provenance.json`. Ein vor der abschließenden Dialogbereinigung gestarteter Modullauf und erforderliche vollständige Wiederholungen bleiben getrennt erhalten. Kein Test entfernt oder übersprungen.

Neue UI-Regressionsfälle: Common 1/n bei vollen/fehlenden Facilities, MAX 0/1/n/10.000, unveränderter Einzelpreis, sichtbare Daily Machine/Energy/Freight-Käufe und Tagesrechte, Cancel/Cash-/Preis-/Tageswechsel, wiederholter identischer Commit, vier Installationstypen mit identischer MK99/Legendary-Instanz, vier Board-Kontextpfade einschließlich Gruppe, atomare Busy-Freight-Rücknahme, ungültige Route sichtbar zurücksetzen und installieren, vollständige Route-Gruppenabweisungen, konkrete Stapelmenge und bestätigter/abgebrochener Verkauf, 500/5.000/10.000 unterschiedliche Zeilen mit Pool-/Scroll-/ID-Nachweis, Load/New Game, Fokus ohne App-Refresh und Freigabe geschlossener Dialoge. Ein vollständiger MainWindow-Klickpfad kauft zwei Karten, installiert eine, nimmt sie bei 40% Teilzyklus zurück, wartet unplatziert, installiert erneut, prüft genau einen Abschluss mit einmaligen Inputs und verkauft anschließend genau eine Karte ohne zweite Auszahlung.

Fachlich angepasste Bestandsdateien: `test_factory_ui.py`, `test_industriova_release_ui.py`, `test_live_playtest_polish.py`, `test_ui_interaction_recovery.py`, `test_playtest2_consistency_followup.py`, `test_recipe_retirement.py`. Die alten Search-/×1-/×4-/Slotlimit-Erwartungen werden durch Kategorie-/Dialog-/unplatzierten Erwerb ersetzt, einschließlich erhaltener Empty-/Sparse-/Pool-/Fenstersturmprüfungen. `release_test_support.py`, `test_card_rendering_audit.py` und `test_inventory_workspaces.py` mounten den alten Komponentenmodus jetzt ausdrücklich; dessen Tests bleiben erhalten, ohne ihn im Produkt wieder zu aktivieren. Der synthetische Empty-/Sparse-Katalogtest stoppt seinen Live-Simulationstimer, damit dieser nicht während der Fixtureprüfung wieder den vollständigen Katalog erzeugt.

**16/16 ursprüngliche Save-Migrationsfälle bestanden.** Gegen dieselben ursprünglichen gesicherten Payloads laufen P2- und P3-Loader; jedes vollständig migrierte JSON stimmt per SHA256 überein. Der bewährte P2-Harness erhält alle Strukturprüfungen und berücksichtigt ausschließlich das bereits vorhandene Schema-6-Pausendefault. Keine Migration am Original und kein neues Saveformat. Bestehende P2-Roundtrips/Snapshot-/Schreibfehler-/Reservierungs- und Template-Regressionsfälle laufen weiter. Nachweise: `migration-before.json`, `migration-after.json`, `migration-before-after-comparison.json`.

## 9. Visuelle Abnahme und ausdrückliche Grenze

66 automatische Captures: 1366×768, 1600×980 und 1920×1080, jeweils Qt-Skalierung 1 und 2. Je Konfiguration leeres Inventory, 1.200 unterschiedliche Zeilen oben/unten, 10.000er-Stapel, Legendary/MK99 mit langem Namen, Install-/Sell-Dialog, Common/Daily Supply, Kaufdialog und MAX=0. Tatsächliche Pixel-/logische Größen sind geprüft; Rohdateien unter `screenshots/dpi1/` und `dpi2/`, Metadaten `captures.json`/`visual-verification.json`. Erste Referenzen vor der Titelkorrektur bleiben unter `screenshots-first-pass/` erhalten; `screenshots-before-dpi-fix/` dokumentiert den anschließend gefundenen abgeschnittenen Install-Text bei 200 %. Dieser Höhenfehler ist korrigiert; betroffene UI-Module und alle 45 P3-Fälle bei 200 % wurden danach erneut geprüft. Diese Zusatzwiederholung wird nicht doppelt in die Fallzahl gerechnet. Die vorherigen Nachher-Messungen bleiben unter `after-before-dpi-fix/` erhalten; finale Messungen wurden nach den letzten UI-Korrekturen wiederholt. Die endgültigen Screens wurden tatsächlich in Stichproben über alle sechs Konfigurationen betrachtet.

Die Darstellung ist offscreen geprüft. Eine native Windows-Handabnahme von DWM/GPU, subjektivem Scroll-/Hovergefühl, langen Spielsitzungen und realen Mausgesten wurde nicht durchgeführt und wird nicht als bestanden behauptet. Diese Grenze ist ausdrücklich offen; Screenshots ersetzen die funktionalen UI-Tests nicht.

## 10. Reproduktion, Risiken für P4 und Stopp

Neue Testdatei: `tests/test_phase3_inventory_ui.py`. Neue Reproduktions-/Prüfskripte: `scripts/phase3_capture.py`, `scripts/phase3_compare.py`, `scripts/phase3_dialog_recheck.py`, `scripts/phase3_finalize_after_dialog_fix.py`, `scripts/phase3_finalize_tests.py`, `scripts/phase3_finish_report.py`, `scripts/phase3_inventory_benchmark.py`, `scripts/phase3_measure.py`, `scripts/phase3_preserve_legacy_outputs.py`, `scripts/phase3_validate_after.py`, `scripts/phase3_verify_protected.py`. Vollständige Dateiliste und aktuelle SHA256: `artifacts/phase3/deliverables-manifest.json`; Delta zur gesicherten Arbeitskopie: `implementation.diff`.

`run_release_tests.py . artifacts/phase3/<neuer-ordner> --workers 1 --timeout 600` mit isolierten LOCALAPPDATA/APPDATA-Pfaden; `phase3_measure.py before|after ui|rapid|active|extended`, für Vorher `--source artifacts/phase3/before-tree`, Cold-UI/Kaufbursts zusätzlich `--repeat 7`; `phase3_inventory_benchmark.py before|after`; `phase3_capture.py` separat mit QT_SCALE_FACTOR=1/2; bestehender `phase2_migration_audit.py --source ... --out ...`; `phase3_compare.py`, `phase3_verify_protected.py`, `phase3_finish_report.py`. Tests und Zeitmessungen seriell. Ausgaben in neue Ordner schreiben beziehungsweise vorhandene Evidenz vorher erhalten.

Verbleibend: Metadatenprojektion und Snapshots wachsen weiter linear mit dem vollständigen Bestand; nur die sichtbaren Qt-Karten sind begrenzt. P4 muss vorhandene Gruppen-/Busy-/Slotinvarianten, ID-Auswahl und Sessionreset bei Ghost/Swap/Autoscroll erhalten. P5-Routing/Statistiken, P6-Liefermessungen, P7/P8-Preise, P9-Topbar, Tutorial, Packs und Market sind nicht erweitert.

**Nach P3 gestoppt. Kein Windows-Build erstellt; persönliche Saves und bestehende Builds unverändert.**
