# Freight geometry correction pass

Stand: 7. September 2026. Grundlage dieses Passes sind die vier bereits genehmigten SVGs. Farben, Konturen, Detailgrad, Schattierungsstil, Perspektivcharakter, ViewBox (`0 0 320 240`) und Größe innerhalb der Karten wurden beibehalten. Es gab keine Änderung am Kartenlayout oder an der Laufzeitintegration.

## Geometrische Korrekturen

### Truck

- Der Containeraufbau besteht jetzt aus drei eindeutig geschlossenen Flächen: Dach, lange Seitenwand und hintere Stirnfläche. Gemeinsame Eckpunkte schließen das Volumen ohne offene oder optisch durchsichtige Oberkante.
- Die Tür folgt als vollständige Kontur der schrägen Kabinenseite. Seitenfenster und Griff liegen innerhalb dieser Kontur.
- Chassis, Aufbauunterkante und Radachsen folgen derselben Flucht. Die sichtbaren Radaufstandspunkte laufen in Blickrichtung von `y=216` über `213` und `207` auf `205`; die Abnahme entspricht der Entfernung im Bildraum.
- Kabine, Radkasten und Chassis überlappen konstruktiv und bilden eine zusammenhängende Silhouette.

### Train

- Hinter der Lok stehen drei getrennte, gekoppelte Waggons. Ihre sichtbaren Aufbauweiten nehmen ungefähr von 51 über 40 auf 20 ViewBox-Einheiten ab.
- Die Waggonunterkanten und alle Fahrwerke folgen derselben Fernflucht. Die Radaufstandspunkte der Lok sinken in Bildrichtung von `209` auf `201`; die Waggons setzen diese Folge mit `199`, `197`, `195`, `193` und `192` fort.
- Die Führerhaustür ist eine geschlossene Fläche innerhalb der schrägen Kabinenseite. Fenster und Griff sind in der Türfläche verankert.
- Kopplung und Überdeckung laufen vom Lokkörper zum ersten, zweiten und dritten Waggon; kein Waggon schwebt unabhängig vom Unterrahmen.

### Ship

- Deck, Wasserlinie, roter Unterwassergürtel und Kiellinie sind durchgehende, geschlossene Flächen. Die Unterkante läuft vom Bug über den tiefsten Mittelbereich zum Heck ohne Sprung.
- Vier Containerpositionen verwenden dasselbe perspektivische Raster. Benachbarte Container teilen Kanten; die beiden Container der zweiten Lage teilen ihre Aufstandskanten exakt mit den Dächern der unteren Lage.
- Alle Container besitzen Dach-, Stirn- und Seitenfläche und bleiben damit als Quader lesbar.
- Die Brücke liegt hinter dem Containerfeld und wurde bis zur Deckebene verlängert. Mast, Reling und Aufbauten sind mit Deck beziehungsweise Brücke verbunden.

### Aircraft

- Silhouette und Flügelgeometrie wurden weitgehend erhalten.
- Beide Gondeln besitzen dieselbe Achsrichtung (`rotate(-27)` für die Intake-Ellipsen), eine klare Einlassöffnung, einen sichtbaren Kern, einen auslaufenden Gondelkörper und einen Pylon zur jeweiligen Tragfläche.
- Das fernere Triebwerk liegt nun unter der fernen Tragfläche und wird vor dem Rumpf gezeichnet; das nähere liegt unter der nahen Tragfläche. Ihre unterschiedliche Größe folgt der Perspektive.
- Die Nase läuft zu einem eindeutigen vorderen Punkt links oben aus. Zwei zurückgestaffelte Cockpitfenster folgen der Rumpfachse und vermeiden den Eindruck eines seitlich gedrehten Gesichts.
- Beide Flügelspitzen bleiben vollständig im ViewBox. Der gerasterte Alpha-Bereich reicht horizontal von `x=15` bis `x=307` und vertikal von `y=46` bis `y=215`.

## Offscreen-Prüfung

Die realen installierten Freight-Karten wurden bei **166 × 264 px** mit `QT_QPA_PLATFORM=offscreen` gerendert. Zusätzlich wurden die Auswahlkarten bei 166 × 224 px geprüft. Kein Widget wurde mit `show()` geöffnet; die reale GUI wurde nicht gestartet.

Der Vergleich verwendet den genehmigten SVG-Stand unmittelbar vor diesem Korrekturpass als „Vorher“. Die Datei `artifacts/freight_geometry_pass/comparison_installed.png` enthält beide Zustände bei 1:1-Pixelmaßstab. `comparison_selection.png` enthält die zusätzliche Prüfung der kleineren Kartenfläche.

Die Sichtprüfung umfasste:

- gemeinsame Boden-/Fahrwerksebenen bei Truck und Train;
- monotone perspektivische Verkleinerung und Anschluss der drei Waggons;
- gemeinsame Kanten und Aufstandsebenen der Container;
- durchgehende Deck-, Wasser- und Kiellinien;
- parallele Gondel-/Rumpfachsen und plausible Pylonanschlüsse;
- eindeutige Flugrichtung sowie vollständige Flügelspitzen;
- Silhouettenlesbarkeit und Erhalt der Hauptdetails bei 166 × 264 px.

Die automatische Qt-Prüfung bestätigt für alle acht Karten **0 geänderte Pixel außerhalb des bestehenden Fahrzeugbereichs**. Alle vier SVGs sind gültig, behalten transparente Hintergründe und besitzen gerasterten Innenabstand zu allen ViewBox-Kanten. Die Messwerte liegen in `artifacts/freight_geometry_pass/verification.json`.

## Artefakte

- `artifacts/freight_geometry_pass/comparison_installed.png` – geforderter Vorher-/Nachher-Vergleich bei 166 × 264 px.
- `artifacts/freight_geometry_pass/comparison_selection.png` – zusätzliche Prüfung bei 166 × 224 px.
- `artifacts/freight_geometry_pass/assets_preview.png` – korrigierte SVGs in voller ViewBox.
- `artifacts/freight_geometry_pass/approved_*.png` – genehmigte Baseline.
- `artifacts/freight_geometry_pass/corrected_*.png` – korrigierter Stand.
- `artifacts/freight_geometry_pass/verification.json` – Clipping-, Padding- und Pixelbereichsprüfung.

Reproduktion:

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m production_zero.tools.freight_asset_sheet approved --output-dir artifacts/freight_geometry_pass
.venv/Scripts/python.exe -m production_zero.tools.freight_asset_sheet corrected --output-dir artifacts/freight_geometry_pass
.venv/Scripts/python.exe -m production_zero.tools.freight_asset_sheet geometry_compare --output-dir artifacts/freight_geometry_pass
.venv/Scripts/python.exe -m production_zero.tools.freight_asset_sheet geometry_verify --output-dir artifacts/freight_geometry_pass
```
