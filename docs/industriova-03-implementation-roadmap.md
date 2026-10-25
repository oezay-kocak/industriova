# INDUSTRIOVA 0.3 – Implementierungsroadmap

Stand 21.10.2026. Dies ist ein Plan, keine Implementierung. Alle folgenden Pfade relativ zu `src/production_zero/`. Ausgangsstand ist die gesicherte dev6-Arbeitskopie. Jedes Paket erhält vor Beginn eine neue Quell-/Save-Sicherung und nach Abschluss den bestehenden vollständigen Modultestlauf. Kein Paket darf die 353 Ressourcen, Rezeptrelationen, MK-/Rarity-Grundlogik oder die manuelle Contract-Produktauswahl beiläufig ändern.

## Abhängigkeiten und Reihenfolge

`P0 Messbasis → P1 UI-Kosten → P2 Bestand/Commands → P3 Inventory/Supply-UI → P4 Drag/Swap → P5 Freight-UI → P6 Lieferstatistik → P7 Infrastruktur → P8 Contracts → P9 Navigation/Abnahme`.

P1 kann fachlich unabhängig von P2 erfolgen, wird aber separat gemessen. P4 benötigt die P2-Rücknahme-Invarianten. P5 verwendet vorhandene MK-/Routencommands und benötigt kein neues Wirtschaftsmodell. P6 muss vor Aussagen zur realen Amortisation abgenommen sein. P7 benötigt neue Preisquoten in UI und Backend gleichzeitig; P8 folgt erst nach P7, da erreichbare Leistung von Infrastruktur/Transport abhängt. Navigation P9 darf nach P3 vorbereitet werden, finale DPI-Abnahme erfolgt mit allen Controls. Keine parallelen Ersatzsysteme.

## P0 – Messbasis und Erhaltungsschutz

- **Dateien:** `scripts/phase0_benchmark.py`, `scripts/phase0_chain_simulation.py`, bestehender `scripts/run_release_tests.py`, vier Auditberichte und `artifacts/phase0`.
- **Commands/Persistenz:** keine produktiven Änderungen. Working-Tree-SHA256 und persönliche Savekopien vor jeder Umsetzung.
- **Akzeptanz:** Baseline reproduzierbar; aktuelle Tests vollständig gezählt; keine geänderten Bestandsquellen/Tests/Daten/Builds; Cold/Warm-/Core-/Render-/Savezeiten getrennt; Modellannahmen kenntlich.
- **Test/Performance/Visual:** heutige Rohwerte, Profile und Qt-Referenzbilder. Native Windows-Latenz separat kennzeichnen, Offscreen-Bildzeit nicht als FPS ausgeben.
- **Migration/Rollback:** keine. Quellen aus der Quellreferenz, Original-Saves bleiben unberührt.

## P1 – Nachgewiesene UI-Blockaden reduzieren

- **Dateien:** `ui/unlock_tree_view.py`, `ui/factory_view.py`, `ui/factory_view_v2.py`, `ui/main_window.py`, `ui/supply_view.py`, `ui/leaderboard_view.py`, `core/production_pause.py`, ggf. `ui/contracts_view.py`, bestehende Resource-/Zoom-Komponenten; `persistence/session_writer.py` nur in eigenem Unterpaket bei belegtem Snapshotproblem.
- **Commands/Persistenz:** keine fachlichen Commands, keine Saveformatänderung. Cache ausschließlich Darstellung oder unveränderliche Definitionen, mit Reset bei New Game/Load.
- **Änderung:** nach Profilen Icons/Graphobjekte bei Filterwechsel wiederverwenden; Knotenstatus nur bei relevanter Änderung aktualisieren; Picker behalten oder bedarfsgerecht materialisieren; existierenden Ranking-Snapshotvergleich erhalten und geänderte eigene Zeile direkt aktualisieren. `core/production_pause.py:effective_card_paused` durchsucht im großen Renderprofil für jede Karte erneut alle Standorte; vorhandenen Board-/Slotkontext nutzen oder pro Refresh einmal auflösen. Kein pauschales Entfernen von Refreshes ohne Invalidierungskonzept.
- **Tests:** Such-/Stagewechsel gleicher Trefferbestand und Widgetidentität, 353/708 Graphbestand, Zoom/Pan/Fokus, erste Rezeptfreischaltung sichtbar, New Game/Load ohne fremde Referenzen, Rang/Highlight/Own-Row und Textfokus korrekt. Snapshot: freier Live-State nach Submit beeinflusst gespeicherte Kopie nicht; jüngerer Save gewinnt; Fehler/Close-Verhalten erhalten.
- **Performance-Akzeptanz:** Cold Open/Rebuild/Picker gegen heutige Profile deutlich senken; Warm-Refresh p95 unter 16 ms bei gleicher Fixture anstreben; strukturelle Arbeit bei unverändertem Zustand null. Für jeden betroffenen Pfad mindestens sieben identische Wiederholungen, zusätzlich 500-Karten-Snapshot getrennt. Überschreitungen als offen dokumentieren statt Datenmenge verkleinern.
- **Visuell:** bestehende Szenen/Icons/Selection/Tooltips bei 1366×768, 1600×980, 1920×1080 und 100/200 %; menschliche Pan-/Zoom-Beurteilung.
- **Risiko/Rollback:** veraltete Cacheinhalte. Rein darstellungsbezogener Commit rücksetzbar, keine Savemigration.

## P2 – Inventory-Domäne und atomare Erwerbs-/Rücknahmepfade

- **Dateien:** `core/supply.py`, `machine_operations.py`, `commands.py`, `inventory.py`, `state.py`; `persistence/sqlite_store.py` nur falls zusätzliche Fortsetzungsfelder beschlossen werden.
- **Commands:** bestehende drei Supply-Käufe auf unplatzierte Karten; `ReturnMachinesToInventory` neu, bestehende Install-/Sell-Commands weiterverwenden. `PurchaseTemplates` unverändert direkt installieren lassen.
- **Persistenz:** `cards` bleibt Eigentum, Slots bleiben Platzierung; reine Wiedereinführung funktioniert im bestehenden Schema. Neue Felder nur mit explizitem Schema-/Defaultplan. Keine Kostenneuberechnung aus Tagespreisen für vorhandene Karten.
- **Tests/Akzeptanz:** Common-Menge, beide Daily-Kategorien und MAX ohne freie Slots kaufen; genau eine Geldbuchung, frische eindeutige IDs, exakte Qualität/Anschaffung. Kein Soll bei Geldmangel/ungültiger Menge/veraltetem Daily-Angebot. Installation und Rücknahme behalten Card-ID/MK/Rarity/Investition. Doppelinstallation ablehnen. Gruppenverkauf mit einer ungültigen/busy ID verändert nichts. Kartenlimit nicht mit Global Storage verbinden.
- **Template-Schutz:** MK50/Legendary kopieren → neue MK1/Common ohne Fortschritt/Reservierung; Zielkompatibilität, geänderter Preis, zu wenig Slots/Geld und Cancel lassen Geld/Karten/Slots unverändert. Kein Inventory-Zwischenschritt.
- **Save/Migration:** Schema-6-Roundtrip für platzierte/unplatzierte Produktions-, Energie- und Freight-Karten; vorhandene 16-Slot-Migrationsfixtures, wiederholtes Laden idempotent, Originaldateien nur als Kopien verwenden. Bestehende aktive Freight-Reservierungen unverändert.
- **Performance/Visual:** Erwerb 1/10/100/1000 Karten, Inventarprojektion 500/5000/10000, Snapshotgröße; in diesem Backendpaket keine neue UI.
- **Rollback:** Supply-Verhalten lässt sich zurücksetzen, aber ein alter UI-Stand könnte neue unplatzierte Käufe verbergen. Daten bleiben erhalten; kein automatischer Verkauf/Neuinstallation beim Downgrade.

## P3 – Inventory sichtbar machen und Supply vereinfachen

- **Dateien:** `ui/inventory_view.py`, `supply_view.py`, `release_dialogs.py`, `main_window.py`, bestehende Kartenrenderer/Filter.
- **Commands/Persistenz:** ausschließlich P2-Commands; keine neuen Bestands-/Raritytabellen. Temporäre Auswahl konkret auf IDs abbilden.
- **Akzeptanz:** Inventory zeigt Available/In Use nachvollziehbar; Install/Return/Sell mit Bestätigung und MK/Rarity-Erhaltung. Keine Crafting-/Packs-/Steam-Market-Bedienung. Supply zeigt drei Grundkategorien, keine Suchzeile/Zusatzfilter/X1-X4; Einzelpreis auf Karte, Menge und explizites MAX im Kaufdialog. MAX berücksichtigt Geld und 10.000 pro Aktion, keine Slots. Nach Bestätigung erneut validieren, bei 0 Cash keine kaufbare Pseudomenge.
- **Tests:** alle drei Typen, Daily-Rechte, Stapelauflösung mit verschiedenen Investitionen, Cancel, doppelte Klicks, leere Suche-/Filterreferenzen nach Entfernung, Fokus/Scroll nach Verkauf, New Game/Load.
- **Performance:** virtuelles Common-Raster behalten; Inventory-Refresh bei 500/5000/10000 Karten und Scrolllatenz messen. Kein kompletter App-Refresh für jedes geänderte Mengenlabel.
- **Visuell:** bestehende Industriova-Karten, Dialoge, grüne MK-Anzeige; drei Größen × zwei DPI; sehr lange Namen, MK99/Legendary, große Geld-/Mengenwerte.
- **Risiko/Rollback:** Legacy-Scrap-/Crafting-/Packtexte versehentlich aktiv. UI rücksetzbar; gekaufte Karten im Save behalten.

## P4 – Bestehendes Drag-and-drop erweitern

- **Dateien:** `core/machine_operations.py`, `freight.py`, `commands.py`; `ui/release_board.py`, `freight_drag.py`, `freight_lines.py`, `factory_view_v2.py`.
- **Commands:** bestehenden Move-Pfad um validierten Permutations-/Swap-Plan erweitern; nur wenn Signatur sonst uneindeutig eigenes `SwapMachines`/`SwapFreightVehicles` auf derselben Validierung. P2-Return-Command für Kontextaktion.
- **Persistenz:** keine neuen Karten/Slotidentitäten. Bestehender Produktionszustand folgt ID; aktive Sendung bleibt eingefroren.
- **Akzeptanz/Tests:** kompatibler belegter Einzelswap in beide Richtungen, freie Gruppenziele, überlappende Gruppen, gesperrte Slots, Site-/Facility-Mismatch, doppelte IDs/Targets und veraltete Session vollständig ablehnen. Ursprungs-/Zielzustände und Geld nach Ablehnung exakt gleich. Busy-Fahrzeug in Ursprung **oder Gegenposition** blockiert gesamte Aktion.
- **Interaktion:** sofortiger mausfolgender Ghost nach normalem Dragstart, beide Scrollränder, Wheel bei gehaltenem Drag, Auswahl bleibt erhalten; Esc/Drop außerhalb/Deaktivierung/Load räumen Capture/Ghost/Timer auf. Keine Fachmutation während Hover.
- **Performance:** 10/50 reale, 100/500 synthetische Auswahlflächen; Mausmove-/Filter-/Release-/Redrawzeiten einzeln. Größere Auswahl nicht durch abgeschnittene Fixture vortäuschen.
- **Visuell:** native Windows-Gesten über Hallenwechsel und Scrollrand, Auswahlrahmen, Hoch-DPI-Hotspot; Offscreen-Coretests allein reichen nicht.
- **Rollback:** ohne Formatänderung rücksetzbar; bereits umsortierte Slots bleiben gültig. Unklare Gruppenswap-Semantik vor Umsetzung entscheiden.

## P5 – Freight-Bedienung und theoretischer Durchsatz

- **Dateien:** `ui/freight_view.py`, `release_freight.py`, `freight_lines.py`, Kartenrenderer und Hover.
- **Commands:** vorhandene `AssignFreightVehicles`, `UpgradeMachines`, Scope-/Kartenpause; keine zweite Upgrade- oder Raritylogik.
- **Akzeptanz:** Ware wählen, danach Sell/Contract/Consortium Contract; Event sichtbar deaktiviert. Gruppe atomar konfigurieren. Sichtbarer grüner MK-Button wie Production, gleiche Bestätigung/Kosten, MK99-Sperre. Tooltip zeigt `60*C/T` und Kapazität/Fahrzeit mit realen Modifikatoren.
- **Tests:** Rechtsklick- und Direktbutton führen zu identischem Resultat; Gruppenquote und Ablehnung, Routewechsel unterwegs verändert existierende Sendung nicht; identisches MK/Rarity/Research ergibt identische Tooltip-/Corewerte.
- **Persistenz/Migration:** Routen und aktive Sendungssnapshots bereits vorhanden; keine Änderung erforderlich. Keine Umwandlung laufender Sendung durch UI-Wechsel.
- **Performance/Visuell:** Upgrade-/Route-Burst mit UI-Refresh, Buttons ohne Drag-/Klickkonflikt; 100/200 %, lange Rail-/Shipping-Line-Labels.
- **Rollback:** rein UI-bezogen möglich; Routen bleiben interpretierbar.

## P6 – Echte Liefermengen begrenzt erfassen

- **Dateien:** `core/freight.py`, `simulation.py`, ggf. `history.py`; `persistence/sqlite_store.py`; Freight-Header und Event-Feed-Consumer.
- **Commands/Persistenz:** keine Benutzeraktion nötig; Abschlussallokation im vorhandenen Simulationspfad. Schema 7 mit begrenzten Buckets/Messbeginn/Watermark und optional Herkunfts-Facility in Sendung. Fehlende Daten = Warm-up, keine erfundene historische Rate.
- **Akzeptanz:** Teilbeladung zählt tatsächliche Menge; aus Contract/Consortium abgelehnte Restmenge zählt nur Sell. Summe der drei Zielallokationen ist Sendungsmenge. Dispatch, Pause, Load und wiederholter Refresh zählen nichts zusätzlich. Aktive Schema-6-Lieferung wird beim späteren Abschluss einmal gezählt. Kein unendlicher Liefer-ID-Satz oder Historywachstum.
- **Tests:** Grenze Zeitbucket/Fenster, Zeitsprung, Pause, null Beobachtungszeit, Reload unmittelbar vor/nach Abschluss, Vertragsabbruch/Expiry/Membershipverlust, Savefehler und Neustart, Facilityverkauf nach Abschluss.
- **Performance:** Memory-/Payloadgröße nach 1.000/100.000/1.000.000 synthetischen Abschlussallokationen konstant bzgl. Zeit; Verarbeitung pro Abschluss O(1) bei gegebener Facilityzahl. Snapshot und Save neu messen.
- **Visuell:** Theorie und gemessene Rate getrennt beschriftet; Sell/Contract/Consortium und Warm-up lesbar.
- **Risiko/Rollback:** alter Loader lehnt Schema 7 ab. Rollback nur mit Schema-6-Vorsicherung oder getestetem Export, der ausschließlich neue Statistikfelder entfernt; keine stillschweigende Vollrücksetzung.

## P7 – Infrastrukturkosten und Schiffrelation

- **Dateien:** `core/economy.py`, `state.py`, `commands.py`, `freight.py`, `release_balance.py`, `supply.py`, `definitions.py`; `data/game_definitions.json` erst in diesem Paket; UI-Quoteeinstiege `release_board.py`, `factory_view.py`, `freight_view.py`.
- **Commands:** bestehende Purchase/Unlock/Expand; zentrale Kostenfunktionen und erwartete bestätigte Quote prüfen. Ressourcensite-Typ vor Kauf festlegen statt nach Debit umklassifizieren. Keine neuen harten Freischaltsperren.
- **Persistenz:** bestehende gekaufte Linien/Slots erhalten. Neue Defaults: eine nutzbare Linie, keine Reduktion alter Kapazität. Persistierte `ProductionLine.unlock_cost` für **noch gesperrte** Linien benötigt eine versionierte Preisregel; Investition und bereits bezahlte Kosten unberührt. Bei Bedarf `pricing_version`/Schema 7 mit P6 abstimmen, keine pauschale Loaderrekalkulation.
- **Akzeptanz/Tests:** erste Mining/Drilling/Agriculture jeweils günstig und nur nach gleichem Typ zählen. Rename/Typwechsel/Verkauf erlaubt keinen günstigeren Zweitstandort-Exploit; gemäß Auftrag vorhandene Standorte gleichen Typs zählen und eine Typänderung separat quotieren. UI-/Backendquote identisch; Ablehnung atomar. Kosten-/Durchsatzvergleich Slot→Linie→Facility und Truck→Train→Aircraft→Ship ohne Gate in Zahlen belegen. Schiff bei gleichem MK/Rarity ungefähr 3× Flugzeugpreis und 3× effektiver Durchsatz.
- **Simulation:** vollständige Ketten bei MK1/2/10/50/99, Energie/Fuel, physisches Storage, reale Transportbegrenzung; keine neuen negativen Rezeptmargen. Neue Facility ist größerer Kapitaleinsatz, aber alle Ketten bleiben innerhalb bestehender Hallengrenzen machbar.
- **Performance/Visuell:** Kauf-/Unlock-Burst und Neuaufbau messen; Preise in bestehendem Dialog/Board; Alt-Save zeigt alle gekauften Plätze.
- **Rollback:** neue Ökonomie hat bereits bezahlte Investitionen erzeugt; Rücksetzen von Code darf diese nicht neu bewerten. Voller wirtschaftlicher Rollback benötigt Vorsave, nicht nur alte Formel.

## P8 – Daily/Weekly-Belohnungen an tatsächlichen Aufwand binden

- **Dateien:** `core/contracts.py`, `production_values.py`, `modifiers.py`, `company_xp.py`, `research.py`; `ui/contracts_view.py` für identische Vorschau.
- **Commands:** `AcceptContract` erhält manuelle Produktauswahl und speichert unveränderliche Menge/Cash/XP/RP-Quote; Lieferung/Abschluss bleiben bestehende Mechaniken.
- **Persistenz:** bereits aktive Angebote/Snapshots nicht neu quotieren. Falls RP künftig variabel wird, explizit im Annahmesnapshot speichern; heutige festen 1/3 RP bei alten Snapshots per versioniertem Default erhalten.
- **Akzeptanz:** Preview = Annahmesnapshot = Auszahlung. Opportunitätswert, Energie/Fuel/Transport und erreichbare Nettoleistung aus P7 berücksichtigen. Keine Prämie allein auf nominell installierte, pausierte oder inputlose Outputkapazität. Keine Auswahl-Automatisierung, neuen Rewardtypen oder Packvergaben.
- **Tests:** Früh-/Mittel-/Endgame mit knapper Energie/Transport, Pausen, alternativer manueller Produktwahl, Produktionswechsel nach Annahme, Forschung/Respec, UTC-Grenzen/Expiry, Save/Load und doppelte Lieferung. Geld/XP/RP exakt einmal; Begrenzungen und Levelwechsel prüfen.
- **Performance:** Quote für 353 Produkte und große Firmen, keine rekursive Neuerstellung des vollen Graphen pro Mausereignis; identische Ergebnisse gegen Referenzrechner.
- **Visuell:** angezeigte Werte und Accept-Voraussetzungen bei 3/4 Produkten, große Werte, 100/200 %; keine versteckten neuen Mechaniken.
- **Risiko/Rollback:** Belohnungsänderung wirkt auf XP/RP/Forschung und kann nicht durch bloßes Zurücksetzen der Geldquote rückgängig gemacht werden. Vorher definierte aktive Snapshotkompatibilität Pflicht.

## P9 – Navigation, Feinabnahme und späterer Build

- **Dateien:** `ui/main_window.py`, `factory_view_v2.py`, `global_resources.py`, `interaction_polish.py`, `event_feed.py` und bestehende Profilviews, `theme.py` nur für vorhandene Komponenten.
- **Commands/Persistenz:** bestehende Rename-/Storagecommands; Frontscreen-Einstieg darf keine Wirtschaftsaktion auslösen. History/Inbox nur Projektionen vorhandener Daten.
- **Akzeptanz:** Tabwechsel startet regulären Screen, Expand oben rechts im Storagepanel, Resources dort integriert, History/Inbox am frei werdenden Platz, sichtbare Stifte und ungekürzte Rail-Line-Beschriftung; feste Preise ausdrücklich erkennbar. Keine neuen UI-Designs.
- **Prüfung:** komplette Suite, Save-Migrationsmatrix, alle Phase-0-Benchmarks, drei Auflösungen × zwei DPI, langer nativer Playtest mit Autosave/Drag/Route/mehrfachen schnellen Aktionen. Native UI-Latenz und subjektives Flackern tatsächlich abnehmen; Offscreen-Referenzen allein sind keine menschliche Freigabe.
- **Rollback/Build:** Quell-/Save-Sicherung je abgeschlossener Version; Build erst in einer ausdrücklich später beauftragten Releasephase. **Phase 0 erzeugt keinen Windows-Build.**

## Übergreifende Releasekriterien

Kein Paket ist fertig, solange eine wirtschaftliche Ablehnung Geld, Karten, Slots, Route oder Reservierung teilweise verändert. CommandBus besitzt keinen automatischen Undo. Jede neue Aktion muss deshalb alle ablehnbaren Prüfungen vor dem Commit abschließen. Vergleichszustände sind mindestens Cash, alle Karten samt Investitionen, Platzierungen, Produktionszustände und aktive Sendungen; History/Kommunikation bei fachlicher Ablehnung ebenfalls kontrollieren.

Alle unveränderten Bestandsfälle weiter ausführen. Neue Tests nur für neue Regeln, Transaktionsgrenzen und konkrete Fehlerbeweise; keine Tests entfernen, um einen neuen Sollzustand künstlich grün zu machen. Performance darf nicht durch kleinere Fixtures oder stilles Weglassen versteckter Views scheinbar verbessert werden. Grenzen und noch ausstehende menschliche Abnahmen ausdrücklich benennen.
