# Freight structural geometry rebuild

Stand: 7. September 2026. Dieser Pass ersetzt die beanstandeten Teilgeometrien konstruktiv. Die genehmigte Palette, Konturstärke, flächige Schattierung, Detaildichte, allgemeine Dreiviertelperspektive, ViewBox und Kartenintegration bleiben erhalten. Kartenlayout, Texte, Buttons, Rahmen, Farben und Interaktionslogik wurden nicht geändert.

## Neu aufgebaute Fahrzeugstrukturen

### Truck

Der Cargo-Aufbau besteht aus einem geschlossenen Dach, einer langen Seitenwand und einer hinteren Stirnwand. Alle drei Flächen teilen ihre Eckpunkte; Vorderkante, Dachkante und hintere Kante sind dadurch eindeutig geschlossen.

Ein durchgehender Unterrahmen läuft unter Kabine und vollständigem Cargo-Aufbau. Die vordere Aufbaukante endet direkt auf diesem Rahmen, sodass der Kasten nicht mehr schwebt. Vorder-, Mittel- und Hinterräder berühren eine gemeinsame, in die Tiefe ansteigende Bodenflucht.

Die Kabine wurde als zusammenhängende Front- und Seitenfläche neu aufgebaut. Die Tür liegt als eingesetztes Panel vollständig innerhalb der Seitenfläche. Türkontur, obere Fensterkante, A-Säule, B-Säule, unteres Panel und kleiner Griff gehören zu derselben Türstruktur.

### Train

Eine sichtbare, durchgehende Schienenlinie definiert die gemeinsame Fahrwerksebene für Lok und Waggons. Die Lok besitzt einen eigenen durchgehenden Unterrahmen; alle Radsätze enden auf der Schienenflucht.

Hinter der Lok stehen zwei vollständig geschlossene Freight-Waggons. Jeder besitzt Dach, Seitenwand, Stirnwand, Unterrahmen und eigenes Fahrwerk. Der zweite Waggon wird perspektivisch kleiner. Kupplungen verbinden Lok, ersten Waggon und zweiten Waggon entlang derselben Unterrahmenflucht.

Die Seitenwand des Führerhauses und ihre Tür wurden neu konstruiert. Die Tür ist ein eingesetztes Panel mit Fenster, A-/B-Begrenzung, unterer Fuge und kleinem Griff; sie schwebt nicht vor der Seitenwand.

### Ship

Deckkante, Rumpfseiten, Wasserlinie, roter Unterwassergürtel und Kiellinie bilden weiterhin durchgehende geschlossene Flächen.

Der Containerbereich besitzt jetzt eine eigene sichtbare Cargo-Deckplattform. Drei Container stehen in einer geraden unteren Reihe auf dieser Plattform. Zwei weitere Container stehen exakt auf den Dachflächen der unteren Reihe. Alle Container sind geschlossene Quader mit Dach-, Stirn- und Seitenfläche und teilen innerhalb der Reihen ihre perspektivischen Kanten.

Der Vorderdeckbereich ist frei von Containern. Der Mast steht vollständig vor dem Cargo-Bereich auf diesem freien Deck und überlappt keinen Container. Zwischen Containerfeld und Brücke bleibt ein eigener Abstand; die Brücke reicht bis zur Deckebene und bildet einen getrennten Aufbau.

### Aircraft

Die vorherige Triebwerksgeometrie wurde vollständig ersetzt. Das Flugzeug besitzt exakt zwei semantisch getrennte Engine-Baugruppen: `engine-near` und `engine-far`.

Jede Baugruppe enthält einen sichtbaren Pylon, eine geschlossene Gondel, einen dunklen runden Intake, einen inneren Kern, einen gelben Konstruktionsakzent und einen nach hinten auslaufenden Abgasbereich. Beide Gondelachsen verwenden dieselbe Ausrichtung von 27 Grad parallel zur Rumpflängsachse. Die Einlässe liegen jeweils auf der nasenseitigen linken/vorderen Seite; Gondelkörper und Abgasbereich laufen nach rechts/hinten zum Leitwerk. Das nähere Triebwerk ist perspektivisch größer.

Das entfernte Triebwerk wird unter der entfernten Tragfläche und hinter dem Rumpf geführt; das nähere Triebwerk hängt über einen längeren sichtbaren Pylon unter der nahen Tragfläche. Es existieren keine weiteren Triebwerksformen.

Nase und Cockpit wurden neu aufgebaut. Die Rumpfachse beginnt an einem eindeutigen vorderen Nasenpunkt und läuft ohne Richtungswechsel zum Leitwerk. Zwei zurückgestaffelte Cockpitfenster folgen der oberen Rumpfperspektive. Beide Tragflächenspitzen bleiben vollständig innerhalb der ViewBox.

## Prüfung bei echter Kartengröße

Die vier installierten Freight-Karten wurden mit den realen Widgets bei **166 × 264 px** und `QT_QPA_PLATFORM=offscreen` gerendert. Kein Fenster wurde angezeigt und die reale GUI wurde nicht gestartet. Zusätzlich wurden die kleineren Auswahlkarten bei 166 × 224 px geprüft.

Explizit geprüft wurden:

- tragende Verbindung zwischen Truck-Aufbau, Rahmen, Kabine und Achsen;
- gemeinsame Schienen-/Radaufstandsebene von Lok und beiden Waggons;
- geschlossene Wagenkästen und durchgängige Kupplungsfolge;
- sichtbare Deckfläche unter jedem Containerstapel;
- kollisionsfreie Trennung von Vorderdeckmast, Cargo-Bereich und Brücke;
- durchgehende Deck-, Wasser- und Kiellinie;
- exakt zwei Aircraft-Gondeln, jeweils mit Pylon;
- parallele Triebwerks- und Rumpfachsen;
- Intake zur Nase und Abgasbereich zum Leitwerk;
- eindeutige Cockpit-/Nasenrichtung und vollständige Flügelspitzen;
- Silhouetten- und Detailerhalt bei tatsächlicher Kartengröße.

Die Qt-Pixelprüfung bestätigt für installierte Karten und Auswahlkarten **null Änderungen außerhalb des bestehenden Fahrzeugbereichs**. Alle SVGs bleiben transparent, vektorbasiert, Qt-kompatibel und besitzen Innenabstand zu allen ViewBox-Rändern.

73 relevante Tests bestehen. Ein zusätzlicher Strukturtest prüft den Truck-Unterrahmen, beide integrierten Türen, die Train-Schienenebene, exakt zwei Freight-Waggons, Ship-Cargo-Deck und Vorderdeckmast sowie exakt zwei Aircraft-Engine-Gruppen mit identischer Achse, eigenem Pylon und eigenem Intake.

## Vergleichsartefakte

- `artifacts/freight_structural_rebuild/comparison_installed.png` – geforderter Vergleich bei 166 × 264 px, oben vorher und unten nachher.
- `artifacts/freight_structural_rebuild/comparison_selection.png` – zusätzliche Prüfung bei 166 × 224 px.
- `artifacts/freight_structural_rebuild/assets_preview.png` – korrigierte Assets in voller ViewBox.
- `artifacts/freight_structural_rebuild/approved_*.png` – Stand unmittelbar vor diesem Rebuild.
- `artifacts/freight_structural_rebuild/corrected_*.png` – finaler Rebuild-Stand.
- `artifacts/freight_structural_rebuild/verification.json` – Pixelgrenzen, Änderungsbereiche und Qt-Validierung.

Reproduktion ohne GUI:

```powershell
$env:PYTHONPATH='src'
$env:QT_QPA_PLATFORM='offscreen'
.venv/Scripts/python.exe -m production_zero.tools.freight_asset_sheet approved --output-dir artifacts/freight_structural_rebuild
.venv/Scripts/python.exe -m production_zero.tools.freight_asset_sheet corrected --output-dir artifacts/freight_structural_rebuild
.venv/Scripts/python.exe -m production_zero.tools.freight_asset_sheet geometry_compare --output-dir artifacts/freight_structural_rebuild
.venv/Scripts/python.exe -m production_zero.tools.freight_asset_sheet geometry_verify --output-dir artifacts/freight_structural_rebuild
```
