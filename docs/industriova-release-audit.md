# Industriova release overhaul — Bestandsaufnahme und Abhängigkeiten

Stand: 18. Oktober 2026. Grundlage ist der vorhandene, stark vom Git-HEAD abweichende Arbeitsstand, nicht ein neues Projekt. Historische Audit-Dokumente bleiben erhalten.

## Sicherung vor Gameplay-Änderungen

`scripts/backup_release.py` archiviert alle Quellen, Daten, Assets, Tests, Skripte und Dokumente einschließlich unversionierter Dateien. SQLite-Dateien werden über die SQLite-Backup-API aus schreibgeschützten Verbindungen gesichert und mit `integrity_check` geprüft; JSON-Entwicklerspielstände werden unverändert kopiert. Manifest mit Ursprungsorten und SHA256-Prüfsummen. Keine Wiederherstellung über aktuelle Dateien ohne ausdrücklichen Auftrag.

Erste Sicherung: `artifacts/release-backups/20261018T185514851717Z`: 676 Dateien, 29 Datenbanken/Spielstände. Enthält insbesondere den Playtest-Spielstand unter `artifacts/playtest-appdata/Production Zero/saves`. Beim untersuchten lokalen Benutzer war kein Spielstand im normalen LocalAppData-Verzeichnis vorhanden.

## Architektur

| Bereich | Tatsächliche Implementierung | Umbaugrenze |
| --- | --- | --- |
| Definitionen/Rezepte | `data/definitions.py`, `game_definitions.json`, `resource_definitions.json`; primäre Maschinenfamilien werden beim Laden getrennt | Rezept-IDs und Input-/Output-Verhältnisse erhalten |
| Karten | unveränderliche `CardInstance`, individuelle Rarity-Boni; `CardStackKey` fasst gleiche Karten zusammen | Neue MK-Felder gehören an Instanzen, nicht globale Definitionen; Stackschlüssel erweitern |
| Simulation | `core/simulation.py`; gemeinsames Lager, zyklische Produktion, kontinuierlicher Brennstoffverbrauch | MK muss Input, Output, Leistung und Brennstoff gemeinsam skalieren |
| Kartenwirtschaft | `packs.py`, `crafting.py`, `inventory.py`, `supply.py` | Packs/Crafting aus aktiven Einstiegspunkten entfernen; Supply/Daily Offers erhalten |
| Preise | `market.py` lädt zentrale Basispreise; bisher fünfminütige dynamische Marktänderungen; Research-Wertmodifikatoren | Alle Verkaufspfade auf feste Basispreise umstellen |
| Produktionsbereiche | `GameState.halls/resource_sites/energy_plants`, gemeinsame `FactoryHall`-Struktur; Commands für Ausbau/Installation | Ressourcenstandorte bisher gemischt; Hallenlimit bisher nicht zehn |
| Freight | eigene Anlagen/Slots, Karten-Assignments und ausgehende Lieferungen mit bereits gebuchten Waren | Beim Umkonfigurieren bestehende Sendungen erhalten; Ziel erst für nächste Sendung ändern |
| Contracts/XP | drei Schwierigkeiten je Regular/Daily/Weekly, aktive Verträge, Produktwahl; Company-XP zusätzlich aus Produktion | Auto-Aktivierung und neue XP-Quote abstimmen; laufende Lieferziele bewahren |
| Lager | globales Lager; Ausbau derzeit bei Level 10 begrenzt | Begrenzung entfernen, numerische Sicherheit beachten |
| Research/Guide | Metadaten zu Branchen, Produkten, Freischaltungen; vorhandene Such-/Filter- und Produktkacheln | Vorhandene Komponenten weiterverwenden |
| Consortium/Leaderboard | lokale Services/Mock-Rankings, lokale Consortium-Netzwerkstruktur | Kein vorhandener Multiplayer-Server; serverseitige Validierung ist keine bereits testbare Funktion |
| Persistenz | SQLite-Tabelle `saves(slot,state_json)`; State-Schema 4, Board-Schema 3; separater JSON-Dev-Save | Daten vor Deserialisierung sichern; alte Felder mit Defaults lesen, neue Felder serialisieren |
| Speichern | `session_writer.py`: geordneter einzelner Hintergrund-Writer, abgetrennte Snapshots, Abschlusswartung beim Schließen | Nicht durch ungesichertes Caching ersetzen; Snapshot und Commit getrennt messen |
| Oberfläche | PySide6 6.11.1; `factory_view.py` Basis, `factory_view_v2.py` gemalte Karten, `production_board_views.py` Spezialisierung | Bestandspalette, Bahnschrift, GameButton/PZControl und Materialrenderer verwenden |
| Performance | Laufzeit aktualisiert primär sichtbaren Bereich; Karten werden dennoch regelmäßig neu gezeichnet; alte Research-/UI-QA-Skripte | Vorher-/Nachher-Messung mit denselben Fixtures; Freight-Balken erhalten |
| Alte MKs | `core/mk_upgrades.py` bereits im Ausgangsarbeitsstand gelöscht; Loader normalisiert `.mk1`–`.mk3` und verwirft `mk_level` | Noch vorhandene rohe MK-Felder retten; bereits früher verworfene Informationen sind nicht rekonstruierbar |
| Visuelle Referenzen | `artifacts/final_visual_*`, `profile_convergence`, `human_review_followup`, zahlreiche `capture_*`-Skripte | 1366×768, 1600×980, 1920×1080 mit tatsächlichem Rendering prüfen |

## Ausdrückliche Präzisierung des Auftraggebers

Es gibt noch keine öffentlichen Spieler. Packs sollen ersatzlos aus dem aktiven Spiel entfernt werden; keine Entschädigungswirtschaft nötig. Gesicherte Testspielstände bleiben zum Vergleich verfügbar. Andere Karten, Produktionskonfigurationen, Ressourcen und Fortschrittsdaten sind weiterhin zu schützen.

## Abhängigkeitsplan / überprüfbare Pakete

1. Bestandssicherung, unveränderte Regression und reproduzierbare Benchmarks.
2. Branding und Build-Metadaten; interne Imports und bisheriger Save-Ordner bleiben kompatibel.
3. Release-Datenmodell: individuelle MKs, Investitionsbasis, Pausezustand, sichere Migration. Darauf bauen Kauf/Upgrade/Verkauf auf.
4. Zentrale Festpreise und Wirtschaftsmodell; Produktions- und Brennstoffskalierung, Rarity-Simulationen; erst danach Kosten und Infrastruktur freigeben.
5. Direkter Slotkauf und atomare Massenaktionen; spezialisierte Standorte, Hallen-/Lagerausbau.
6. Auswahl, Drag-and-drop, Bestätigungsdialoge und Konfigurationsoperationen auf bestehenden Boards.
7. Freight-Ziele und laufende Sendungen, automatische Contracts/XP; gemeinsame Tests gegen Doppelbuchungen.
8. Navigation, globales Ressourcenoverlay, Research-Zuordnung und Produktstatistiken.
9. Performanceoptimierung mit Vorher-/Nachher-Vergleich, vollständige Regression, Save/Load und mehrere reguläre Starts, Build und visuelle Abnahme.

## Migrationen

Keine SQL-Tabellenänderung für zusätzliche JSON-Felder erforderlich. Neue State-Version erst mit implementierter Migration erhöhen. Legacy-Save-Verzeichnis und interne Python-Paketnamen nicht umbenennen. MKs aus explizitem Feld oder Legacy-ID lesen, Defaults MK1. Keine vorhandene seltene Karte neu würfeln. Gemischte Ressourcenstandorte verlustfrei nach Maschinenfamilien aufteilen; vorhandene Karten-IDs/Rezepte/Fortschritt bewahren. Mengen, Geld, XP, Research, Contract- und Sendungsfortschritt durch Vergleichstests prüfen.

## Drive

Authentifizierter Zugriff auf den bestehenden Projektordner wurde geprüft. Aktive Roadmap, Current Status, Produktliste und Architekturunterlagen sind von datierten Playtest-/Progress-Protokollen zu unterscheiden. IDs, Verknüpfungen und historische Protokolle erhalten. Änderungen und Verifikation werden im Abschlussbericht protokolliert.
