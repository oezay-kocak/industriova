# INDUSTRIOVA 0.3 – Technischer Audit (Phase 0)

Stand: 21.10.2026. Referenz: tatsächlicher Working Tree 0.2.0.dev6, nicht Git-HEAD. Keine Gameplay-, Preis-, Rezept-, Versions- oder Buildänderung. Messungen und neue Hilfsskripte sind ausschließlich Auditwerkzeuge.

## 1. Grundlage und Sicherung

Gelesen: `industriova-final-ui-approval-report.md`, `industriova-unified-ux-report.md`, `industriova-dev3-build-report.md`, `industriova-release-report.md`; historische Aussagen wurden gegen die Quellen geprüft. Insbesondere beschreibt der historische Release-Bericht teilweise automatische Verträge, während dev6 manuelle Produktauswahl verwendet.

Vollständige Sicherung: `artifacts/phase0/backup-20261021T172118Z/working-tree.zip`, **37.447 Dateien, 13.227.402.976 Quelldatei-Bytes**, einschließlich `.git`, `.venv`, ungetrackter Dateien, Tests, Konfiguration, Quellen, Assets, Builds, früherer Auditdaten und projektnaher Saves. ZIP-SHA256: `6c82e381ec2433851c3185d1fa217e8444c7f373fe7632b499255c89910570e5`. Einzeldateien: `manifest.json`; Archiv-/Manifestprüfsummen: `SHA256SUMS.txt`. Der neue Sicherungsordner selbst ist ausgeschlossen, um Rekursion zu vermeiden.

Zusätzliche schnell wiederherstellbare Quellreferenz: `source-baseline.zip` mit `source-manifest.json` (916 Dateien einschließlich Git-Metadaten und Assets; ohne abgeleitete Build-/Cache-/Artefaktordner). Die vollständige Sicherung bleibt maßgeblich. Dateiliste wurde vor neuen Auditdateien aufgenommen. Die zweite Sicherung schließt keine im Original vorhandenen Quelländerungen aus.

Die Ausführungsumgebung setzt LOCALAPPDATA auf ein Sandbox-Verzeichnis. Deshalb wurden die **realen** Ordner `<USER_HOME>/AppData/Local/Industriova` und `Production Zero` zusätzlich explizit gelesen und separat gesichert: fünf SQLite-Dateien, 59.478.016 Bytes, Rohkopien und konsistente SQLite-Backupkopien, fünfmal `integrity_check=ok`. `personal-saves-manifest.json` enthält Originalpfade und SHA256. Kein Original wurde geladen, migriert, überschrieben oder gelöscht. Prüfläufe verwenden ausschließlich eigene Zustände/Verzeichnisse unter `artifacts/phase0`.

Wiederherstellung: Anwendung beenden; gewünschte Sicherung in einen **neuen** Ordner entpacken, SHA256 gegen Manifest prüfen; persönliche Saves gezielt aus der passenden Kopie wiederherstellen, nie pauschal über aktuelle Saves extrahieren. Für einen Quellvergleich `source-baseline.zip` verwenden. Keine Rücksetzung auf den alten Git-HEAD.

Abschlussprüfung (`artifacts/phase0/verification.json`): alle **37.447 Archiveinträge** durch Lesen und SHA256 gegen das Einzeldateimanifest verifiziert; **768 bestehende Quellen/Tests/Assets/Skripte/Dokumente unverändert**, zusätzlich **4.083 Dateien unter build/dist unverändert** und alle fünf persönlichen Datenbanken weiterhin mit Original-SHA256. Vollständiger neuer Modullauf: **1.257 bestanden, 80 Module, 0 Fehler, 0 übersprungen**. Neu hinzugekommen sind ausschließlich vier Auditberichte, zehn Audit-/Messskripte und ihre Artefakte; deren Prüfsummen stehen in `audit-deliverables-manifest.json`. Kein Windows-Build erstellt.

## 2. Bestand und Wiederverwendung

Alle Pfade in folgenden Tabellen relativ zu `src/production_zero/`.

| System | Tatsächlicher Bestand | Konsequenz für 0.3 |
|---|---|---|
| Instanzmodell | `core/cards.py:CardInstance`: eindeutige ID, Definition, MK1–99, Rarity-/Bonuswerte, Anschaffung, Upgradeinvestition, Pause; immutable Dataclass | Identität erhalten; keine neue Inventory-Kartenklasse |
| Bestand | `core/state.py:GameState.cards` enthält alle Karten; Slotreferenzen bestimmen Installation; `inventory_card_stacks()` bildet die Differenz | Kein zweites Inventarregister oder Kapazitätsfeld |
| Inventory-Projektion | `core/inventory.py`: Available-/In-Use-Zeilen, Stapel und Produktionsplatzierungsfilter; `CardStackKey` berücksichtigt MK, Bonus, Investition und Pause | Stapel nur als Anzeige, Aktionen auf konkreten IDs; Freight gesondert zulassen |
| Legacy-UI | `ui/inventory_view.py:InventoryView`, `InventoryCardFrame`, Filter, Header, Raster | Karten-/Filterkomponenten verwenden. Nicht den ganzen Legacy-Tab unverändert aktivieren: enthält Crafting, Scrap und veraltete Packtexte |
| Regulärer Supply | `core/supply.py`: Common, tägliche Maschinen/Energy- und Freight-Angebote, getrennte Tageskontingente; alle aktiven Käufe rufen `buy_and_install` | Alle drei Kaufpfade auf Bestandserwerb umstellen; Angebots-/Rarity-/Tageslogik erhalten |
| Direktplatzierung | `core/machine_operations.py:buy_and_install`, kompatible Slots; `core/production_templates.py:PurchaseTemplates` eigener Ziel-/Linienplan | Regulären Supply entkoppeln. Template-Direktplatzierung ausdrücklich erhalten |
| Vorlagen | `MachineTemplate`, `copy_templates`, `quote_templates`, `PurchaseTemplates`; `ui/production_templates.py:paste_dialog`, Shortcuts | Zielregel bereits weitgehend erfüllt; Regression vor Supply-Änderung einfrieren |
| MK/Rarity | `core/mk_upgrades.py:upgrade_cards`, `mk_upgrade_cost`; `CardInstance`-Multiplikatoren | Eine gemeinsame Logik; keine neue Freight- oder Inventory-Rarity |
| Verkäufe | `SellMachines`/`sell_machines` funktioniert auch ohne Slots; 80 % der erfassten Anschaffung + Upgrades. `core/infrastructure.py`: 60 % Bauinvestition | Inventory-Verkauf direkt wiederverwenden. Historische Investitionen nie aus neuen Preisen rekonstruieren |
| Production Boards | `ui/factory_view_v2.py`, `ui/production_board_views.py`; gemeinsamer `FactoryViewBase` in `ui/factory_view.py` | Drei vorhandene Boardkonfigurationen, gemeinsame Auswahl/Actions weiterführen |
| Freight Boards | `ui/freight_view.py`, `ui/freight_lines.py`, `ui/release_freight.py` | Linien-/Karten-/Dialogkomponenten erweitern |
| Research / Guide | `core/research.py`, `core/production_guide.py`, `ui/research_view.py`, Guide im `ui/factory_view.py` | Rezept-/Reverse-Index, bestehende Materialien und Research-Boni erhalten |
| Unlock Tree | `ui/unlock_tree_view.py`, `ui/zoom_pan_view.py`, echte Runtime-Voraussetzungen aus `core/progression.py` | 353 Knoten / 708 Kanten / 49 Wurzeln, vier Tiefen; keine neue Graphquelle |
| Leaderboard | `ui/leaderboard_view.py`, `services/local.py:LocalLeaderboardService` | Lokal simulierte Rangliste; keine belastbare Aussage zu Online-Latenz möglich |
| Preise / Contracts | `core/fixed_prices.py`, `market.py`, `production_values.py`, `contracts.py`, `modifiers.py` | Feste Basiseinzelpreise, manuelle 2/3/4-Produktauswahl, Annahmesnapshot erhalten |
| Persistenz | `persistence/sqlite_store.py`: Schema 6, JSON pro SQLite-Slot; `session_writer.py` | Kein neues Saveformat; vorhandenen Serializer erweitern, wo neue Statistikfelder nötig werden |
| Kommunikation | `core/communications.py`, vorhandene HISTORY-/INBOX-Buttons und ActivityPanels in `ui/event_feed.py`; Profil separat in `ui/player_profile.py` und `inventory_history_chart.py` | History/Inbox gegen vorhandene Datenprojektionen anbinden; kein neues Nachrichtensystem |

## 3. Inventory: konkreter Umbauplan

**Autoritativer Zustand bleibt `cards` plus Slotreferenzen.** Eine Karte ist entweder in genau einem Produktions-/Freight-Slot oder unplatziert. `installed_card_ids()` und `installed_freight_card_ids()` sind Projektionen, keine zusätzliche Wahrheit. Kartenbestand hat schon heute keine Kapazitätsgrenze. `storage_upgrades.py`, `used_storage` und `ExpandInventoryStorage` betreffen physische Waren im Global Storage; der irreführende Legacy-Name darf nicht als Kartenlimit übernommen werden.

1. Bestehende Kaufcommands `BuyCommonSupplyCard` (auch Mengen), `BuyDailyMachineSupplyCard`, `BuyDailyFreightSupplyCard` behalten. Einen gemeinsamen validierten Erwerbshelfer aus dem heutigen Kaufpfad ableiten: Angebot/Ganzzahl/Geld/Tagesrecht prüfen, Karten samt UUID, Anschaffung und Qualitätswerten vorbereiten, einmal abbuchen, Karten hinzufügen, erst danach Tagesverbrauch/History buchen. Keine Slots prüfen oder belegen. `_create_supply_card` ist ein alter Helfer, aber allein nicht ausreichend: alte sequenzielle IDs, kein vollständiger Transaktionsplan/Anschaffungsschutz.
2. `SupplyView._purchase_problem`, `_confirm_purchase` und Mengenmaximum von freien Slots entkoppeln. MAX = `min(10000, floor(cash / unit_price))`; 10.000 ist ein **bestehendes Limit pro Kaufaktion**, keine Inventory-Kapazität. Daily bleibt ein Kauf. Bei MAX=0 Kauf deaktivieren, nicht künstlich Menge 1 kaufbar machen. Nach Bestätigung Cash/Angebot erneut prüfen.
3. `InstallCardInHall` validiert bereits Eigentum, Board, Ressourcenspezialisierung, freie/freigeschaltete Slots und Doppelinstallation; wiederverwenden. `InstallFreightCard` validiert Facility-Typ und Eigentum. Beide müssen für korrupte Saves/aktive unplatzierte Sendungsreferenzen dieselben Invarianten erzwingen.
4. `RemoveCardFromHall` erhält die CardInstance, löscht aber aktuell `machine_production`. Für Return-to-Inventory ein eindeutiges gemeinsames Command `ReturnMachinesToInventory(ids)` planen, alle IDs/Zustände vorab prüfen und eine ausdrücklich entschiedene Regel für Rezept/Teilzyklus anwenden. Nicht versehentlich die alte Reset-Semantik als Produktentscheidung übernehmen. Freight-Zuweisung getrennt behandeln; aktive Fahrzeuge bis Ankunft blockieren.
5. `SellMachines` für unplatzierte IDs verwenden, inklusive Investitionsschutz und Gruppensumme. Inventory-UI darf nicht versehentlich einen ganzen Stapel verkaufen, wenn nur eine Karte gewählt ist. Mengenauflösung muss konkrete IDs mit unveränderten MK-/Rarity-/Investitionswerten liefern.
6. In `MainWindow` Inventory gezielt wieder montieren. Vorhandene Kartenansicht/MaterialFrames übernehmen, Crafting-/Scrap-/Packs-/Trade-UI nicht wieder aktivieren. Legacy-Metadaten im Save brauchen nicht allein wegen ihrer Existenz gelöscht zu werden.

**Copy/Paste:** `PurchaseTemplates` ruft den heutigen Supply-Erwerbshelfer nicht auf. Es quotiert gezielt die Ziellinie, prüft alle Definitionen, Rezepte, Preise, freie Plätze und Geld vor Commit, erzeugt neue MK1/Common-Instanzen mit UUID/Anschaffung und installiert sie direkt. Route/Pause können als Konfiguration kopiert werden, keine Zyklusfortschritte, Upgrades, Rarity oder reservierte Ladung. Dialog zeigt Preis und Slots, Ablehnung dispatcht keinen Kauf. Beim Umbau diesen unabhängigen **Commandpfad innerhalb derselben Domäne** erhalten; kein Umweg über Inventory und kein zweites Wirtschaftssystem.

**Savebedarf:** Für die reine Wiedereinführung ist keine strukturelle Migration nötig: alle unplatzierten `cards` werden schon in Schema 6 serialisiert. Bei neuen Statistik-/Fortsetzungsfeldern Schema 7 mit Defaults planen. Bestehende Slotreferenzen/IDs/MK/Rarity/Rezeptverhältnisse/Investitionen/Pausen bleiben exakt erhalten. Loader nicht mit einer „Neuinstallation aller Karten“ umgehen. Bereits bestehende Migration `migrate_release_state` entfernt alte Packs und spezialisiert gemischte Sites; weder rückgängig machen noch für Inventory erneut ausführen. Downgrade nach Schema 7 benötigt vorab angelegten Schema-6-Save; alter Loader lehnt zukünftige Schemas ab.

## 4. Drag-and-drop und Auswahl

Production: `ReleaseBoardMixin` in `ui/release_board.py` installiert Filter nur auf beteiligten Widgets. Strg/Shift/Rahmenauswahl vorhanden. Auswahlvisuals setzen Properties und aktualisieren nur geänderte Karten. Rechteckbewegung ändert das RubberBand; Schnittmengentest erfolgt erst bei Release. Production-Drag verwendet `QDrag`, MIME mit Session-ID und geordneten Karten-IDs, Vorschau über `widget.grab()`.

Freight: `FreightSlotInteraction` in `ui/freight_drag.py` verwendet Pointer-Capture statt blockierender OLE-Schleife; auswählbar sind kompatible freie Plätze. Aktuell gibt es **keinen bewegten Karten-Ghost** im Pointerpfad. `FreightLineInput` in `ui/freight_lines.py` ergänzt Rahmen-/Linienmenüs, `TemplateShortcuts` schützt Text-/Zahleneingaben. Nicht pauschal einen globalen QApplication-Filter einführen.

`move_machines` validiert die vollständige Gruppe vor Mutation. Belegte Ziele außerhalb der bewegten Gruppe sind abgelehnt; eine Umordnung innerhalb derselben Gruppe ist möglich. Ressourcenfamilie und freigeschaltete Slotindizes werden geprüft, Instanzen und Produktionszustände bleiben unangetastet. Freight-Einzelmove lehnt belegte Ziele und Fahrzeuge unterwegs ab; Gruppencommand prüft alle Ziele vor dem Leeren der Ursprünge.

Minimale Erweiterungen:

- Gemeinsamer **Plan/Validate/Commit** für eine explizite Slotpermutation, einschließlich Gegenkarte eines Swaps. Board-/Site-/Facility-Kompatibilität für beide Richtungen, eindeutige Origins/Targets und keinerlei Doppelbelegung prüfen. Keine Instanz neu erzeugen. Gemischte Ressourcensites auch bei komplettem Austausch anhand des Endzustands prüfen.
- Einzel-Swap zunächst klar definieren; Gruppen-Swap braucht eine bijektive Zielmenge. Bei unzureichenden/incompatiblen Zielen alles ablehnen, kein Verdrängen unbeteiligter Karten ins Inventory.
- Bestehenden Production-QDrag-Hotspot setzen/prüfen. Freight um ein mausdurchlässiges Ghost-Widget erweitern, Position aus globaler Mausposition ableiten, begrenzte Neuzeichnung. Start weiter an der normalen Dragdistanz, Ghost danach ohne zusätzliche Verzögerung.
- Edge-Scroll-Timer an den bestehenden ScrollAreas: Abstand zum oberen/unteren Viewportrand bestimmt begrenzte Scrollgeschwindigkeit. Wheel während Capture bzw. QDrag an denselben vertikalen Scrollbar leiten. Bei Esc, Drop, Zielwechsel, Fensterdeaktivierung und Statewechsel Timer/Ghost/Capture zuverlässig abbauen.
- Aktive Freight-Sendungen: weder Ursprung noch Gegenkarte eines Swaps darf unterwegs sein. Karten-ID, Route, Pause und laufende Reservierung nicht umschreiben. Übergeordnete Pause stoppt nur neue Abfahrten.
- Produktionszyklus beim reinen Move/Swap erhalten; Return-to-Inventory separat entscheiden. Rückkehr einer Karte darf keinen zweiten Rezeptzyklus oder duplizierte Inputs erzeugen.

Kein generelles CommandBus-Rollback vorhanden: `dispatch()` ruft synchron `apply()` auf und protokolliert erst nach Erfolg. Atomarität entsteht durch Vorprüfung und vorbereitete Ersetzungen, **nicht** durch eine automatische Datenbanktransaktion um jeden Command. Spätere Mutationen deshalb vollständig vorbereiten; Fehler nach Debit nicht durch UI-Refresh „reparieren“.

## 5. Freight: bereits vorhanden und tatsächlich fehlend

Delivery Target existiert bereits in `FreightView._build_assignment_view`: Sell (`market`), Contract, Consortium Contract und deaktiviertes Event. Derzeit steht der Ziel-Combo **vor** dem Warenbrowser; Auswahl einer Ware dispatcht `AssignFreightVehicles` und verlässt die Ansicht. Zielregel benötigt somit einen zweistufigen Waren→Ziel-Ablauf mit bestehendem Dialog/Combo, keine neue Routendomäne. Ausgewählte Gruppe bis Commit stabil halten und Annahme erneut validieren.

MK ist über Rechtsklick → Machine actions → MK UPGRADE erreichbar (`ui/release_freight.py:vehicle_actions`), verwendet `UpgradeMachines` und dieselbe `mk_upgrades.py`. Es fehlt der direkt sichtbare grüne Kartenbutton. Diesen in den vorhandenen Freight-Kartenrenderer einfügen, Hitbox vor Auswahl/Drag behandeln, MK99 deaktivieren. Kein zweites Upgradeverfahren. Busy-Upgrade-Regel gesondert entscheiden: laufende Sendungen besitzen bereits eingefrorene Kapazität/Zeit, sodass ein Upgrade nur kommende Sendungen beeinflussen kann.

`freight_stats` enthält MK/Rarity/Research-Kapazität und Rarity-bedingte Zeit. Der Hover zeigt bereits Capacity, Travel Time und Full-load capacity **pro Economic Cycle**. Zusätzlich `60 * capacity / transport_time_seconds` pro Minute anzeigen; keine Veränderung der Statsskalierung. Fahrzeit skaliert derzeit mit `1 + bonus_percent/200`, MK mit der Kapazität. Für 3×-Vergleiche stets gleiches MK, gleiche Rarity und Research verwenden.

**Ist-Statistiken:** Abgeschlossene Sendungen werden aus `outbound_shipments` entfernt. `completed_market_deliveries` enthält flüchtige Sell-Abrechnungen, keine vollständige Contract-/Consortium-Historie und wird nicht als solcher Bestand serialisiert. Es besitzt derzeit keine Begrenzung. `AccountStatistics`/History ersetzen keine auf drei Lieferziele getrennte, zeitlich datierte Mengenstatistik. Daher lassen sich aktuelle Liefermengen/min aus einem alten Save nicht rückwirkend exakt berechnen.

**Vorgeschlagene bounded Berechnung:** Am bestehenden zentralen Abschluss in `SimulationEngine._complete_outbound_shipments` genau die endgültige Allokation zählen: Sell-Menge + tatsächlich angenommene Contract-Menge + tatsächlich angenommene Consortium-Menge = Sendungsmenge; bei Fallback nur den final verkauften Rest zu Sell. Nicht bei Dispatch zählen. Je Facility und Ziel 60 Zehnsekunden-Buckets speichern (10-Minuten-Fenster), mit monotonem Simulationszeitindex, Mengen und Messbeginn. Aktuelle Anzeige: Summe der letzten 60 Sekunden / tatsächliche beobachtete Minuten, Warm-up kennzeichnen; optional 5-Minuten-Auswahl ohne neue Historie. Während Pause läuft die Messzeit weiter; kein Nenner aus Zahl aktiver Fahrzeuge.

Pro Sendung entweder Abschluss vor Entfernen + Save als ein gemeinsamer Zustandsübergang oder persistierter Watermark/Idempotenzschlüssel. Kein unbeschränktes Set abgeschlossener IDs. Facility-ID der Abfahrt auf der Sendung speichern, falls Zuordnung später fehlt; Umzug ist während Fahrt ohnehin gesperrt. Schema-6-Saves beginnen mit leeren Buckets/Warm-up, bestehende aktive Sendungen zählen einmal beim späteren Abschluss. Nicht vorhandene Vergangenheit als null Ertrag verkaufen. Begrenzung/Consumer-Watermark für `completed_market_deliveries` prüfen, damit Feed keine neue unendliche Liste erhält.

## 6. Supply und Navigation

| Wunsch | Bestehender Einstieg / Abhängigkeit | Minimaler Eingriff |
|---|---|---|
| Supply-Suche/Zusatzfilter weg | `ui/supply_view.py`: Suchdebounce, Chipgruppen, virtuelle Common-Rasterdaten | Such-/Zusatzcontrols und ihre Signalverbindungen entfernen; vorhandenen virtuellen Rasterpfad behalten |
| Drei Kategorien | bestehender Type-Filter / Angebotsklassen | Machines / Energy / Freight; Daily-Purchase-Rechte unabhängig erhalten |
| X1/X4 weg, Menge im Dialog | `_buy_quantity`, `_quantity_priced_data`, `_common_buy_quantity`; `IndustrialDialog` | Einzelpreis auf Karte, Menge erst im Kaufdialog. Aktuell existiert schon ein letzter Schnellbutton ×Maximum, aber kein explizites MAX-Label; sein Maximum hängt noch von freien Slots ab |
| Tab öffnet Frontscreen | `MainWindow` / `ResponsiveMainTabWidget`, Board-`_drawer_mode`, Freight-Assignment, Guide-Caches | Zentraler Entry-Hook schließt Unteransichten/Drawer kontrolliert; wertvolle Cache-/Scrollzustände separat erhalten. Keine Zustandsänderung beim bloßen Navigieren |
| Expand klein oben rechts / Resources im Storage | `FactoryCommandDeckWidget` in `factory_view_v2.py`, `expandResourceStorageButton`, `resources_requested` | Bestehenden Button/Signal umhängen, Layoutbreite und Fokus prüfen |
| History / Inbox | frei werdendes `factoryV2ResourceStrip`, `EventFeedWidget._show_history/_show_inbox` | Vorhandene HISTORY/INBOX-Aktionen aus dem Ticker umhängen; Popup-Anker mitverschieben, persistente Inbox/Unread und begrenzte Activity-History behalten |
| Stift | `TitleRenameFilter`, `bind_building_tree`, Rename-Dialoge | Bestehende Rename-Aktion mit kleinem Icon erreichbar machen; keine zweite Namensspeicherung |
| Rail Line nicht abschneiden | `FactoryV2LinePlate`/Freight-Linienheader | Breite/Schrift anhand tatsächlicher Labels messen, 1366/1600/1920 und 100/200 % abnehmen |
| Feste Verkaufspreise | `core/market.py:BASE_MARKET_PRICES`, `modifiers.py:market_sale_price`, `ResourceSelectionTile`/GlobalResources/Guide | Basiseinzelpreis ausdrücklich als solchen kennzeichnen; ggf. Forschungsbonus separat. Keine dynamische Börsenmechanik |

## 7. Grenzen und offene Produktentscheidungen

Vor Umsetzung zu entscheiden: Rezept/Pause/Teilzyklus bei Return-to-Inventory; Einzel- versus Gruppenswap-Semantik; Zeitfenster und Warm-up-Text der echten Freight-Rate; Bindung angenommener Vertragsquoten an künftiges Balancing; gewünschte Vertragsprämie gegenüber bloßem Sell und XP/RP-Tempo; endgültige Wirtschaftskonstanten nach den im Wirtschaftsbericht beschriebenen Vergleichen.

Fest vorgegeben, keine Rückfrage nötig: normale Supply-Käufe ins unbegrenzte Inventory; manuelle Installation/Rücknahme/Verkauf; MK/Rarity erhalten; Templates kaufen direkt in Zielslots; keine Packs/Steam-Market; 353 Produkte, Rezeptrelationen, Forschungs-/Consortium-Grundstruktur, lineares MK1–99 und bestehende Designkomponenten erhalten. Tutorial, Events, Badges und neue Tiers sind nicht Bestandteil.

Performance-Messwerte/Belege: [Baseline](industriova-03-performance-baseline.md). Kosten/Simulationen: [Wirtschaft](industriova-03-economy-audit.md). Sichere Pakete und Abnahme: [Roadmap](industriova-03-implementation-roadmap.md).
