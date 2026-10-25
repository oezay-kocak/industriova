# Final Truck mechanical correction

Stand: 7. September 2026. Dieser letzte Truck-Pass behält Designsprache, Farben, Konturen, Detailgrad und 3/4-Frontperspektive des akzeptierten `truck.svg`. Geändert wurden ausschließlich Spiegel-, Rad-/Reifen-, Cargo- und Rahmengeometrien innerhalb des Fahrzeugassets. Kartenlayout, Kartenrenderer und die anderen drei Freight-Fahrzeuge blieben unverändert.

## Außenspiegel

Beide Spiegel besitzen jetzt sichtbare Arme, die aus den Kabinen-/Fenstersäulen austreten. Der nähere Spiegel auf der sichtbaren Kabinenseite verwendet einen stärkeren Arm und ein größeres Gehäuse. Der gegenüberliegende Spiegel ist kleiner und perspektivisch zurückgesetzt. Beide Gehäuse enthalten eine eigene reflektierende Fläche und berühren ihren Spiegelarm; es gibt keine frei schwebenden Rechtecke.

## Achspaare und Reifenbreite

Das Fahrwerk enthält vier Achspositionen. Jede Achse besitzt ein hell lesbares Rad auf der nahen Fahrzeugseite und ein kleineres, nach links/oben zurückgesetztes Rad auf der gegenüberliegenden Seite. Sichtbare Achsstummel verbinden die jeweiligen Positionen. Die entfernten Räder werden vor Karosserie und Rahmen gezeichnet und dadurch korrekt teilweise verdeckt.

Jeder nahe Reifen besteht aus vier getrennten räumlichen Schichten:

- einer zurückgesetzten dunklen Reifenlippe;
- einem verbindenden Laufflächenkörper;
- einer vorderen Außenflanke;
- einer inneren hellen Felge mit dunkler Nabe.

Die freiliegende Lauffläche besitzt eigene Konturlinien. Die Reifen lesen sich dadurch als kurze Zylinder statt als einzelne Ellipsenscheiben. Die entfernten Reifen verwenden dieselbe Konstruktion mit geringerer Breite und kleinerer Felge.

Die nahen Radaufstandspunkte liegen bei `y = 225, 223, 221, 218` und steigen entlang der nach rechts hinten laufenden Fahrzeugachse monoton an. Gegenräder, Achsstummel und nahe Räder bleiben je Achse parallel versetzt.

## Cargo-Aufbau und Chassis

Der Kastenaufbau besteht aus vier geschlossenen, gemeinsam verbundenen Flächen:

- eigener Vorderwand direkt hinter der Kabine;
- großer Seitenwand;
- durchgehender Dachfläche;
- schmaler Rückwand.

Die Flächen teilen Vorder-, Dach-, Unter- und Rückkanten. Der Aufbau besitzt keine offene oder durchsichtige Stelle. Seine durchgehende Unterkante endet unmittelbar auf dem Chassis.

Der vorhandene Unterrahmen läuft von unterhalb der Kabine bis zur hinteren Aufbaukante. Zwei sichtbare Rahmenauflagen verbinden den Cargo-Kasten zusätzlich mit diesem Träger. Kabinenseite, Vorderwand des Kastens und Rahmen überlappen konstruktiv ohne schwebende Lücke.

## Offscreen-QA

Alle Renderings wurden mit `QT_QPA_PLATFORM=offscreen` erzeugt; die reale GUI wurde nicht gestartet.

| Rendering | Alpha-Grenzen | Sichtbare Pixel | Ergebnis |
| --- | --- | ---: | --- |
| 512 × 512 | `(18, 122)–(491, 427)` | 107.753 | vollständig, Reifenbreite und Spiegelarme klar sichtbar |
| 128 × 128 | `(4, 30)–(122, 106)` | 6.906 | Achspaare, Kasten und Kabine getrennt lesbar |
| 64 × 64 | `(1, 15)–(61, 53)` | 1.777 | Silhouette, gelber Streifen und Radfolge erhalten |
| Freight-Karte 166 × 264 | bestehender Artwork-Bereich | – | zentriert, vollständig, kein Clipping |

Der Karten-Pixelvergleich enthält 1.643 geänderte Pixel. Alle liegen innerhalb des bestehenden Fahrzeugbereichs; außerhalb wurden null Pixel geändert.

Die automatische Strukturprüfung bestätigt:

- zwei befestigte Spiegelgehäuse;
- vier nahe und vier entfernte Räder;
- vier Achspaare;
- vier eigene Laufflächenkörper;
- geschlossene Cargo-Vorder- und Seitenwand;
- durchgehenden Cargo-/Kabinen-Unterrahmen;
- weiterhin integrierte Kabinentür.

74 relevante Qt-, SVG-, Freight- und Rendering-Tests bestehen.

## Artefakte

- `artifacts/truck_final_mechanical_pass/after_truck_512.png`
- `artifacts/truck_final_mechanical_pass/after_truck_128.png`
- `artifacts/truck_final_mechanical_pass/after_truck_64.png`
- `artifacts/truck_final_mechanical_pass/after_truck_card_166x264.png`
- `artifacts/truck_final_mechanical_pass/comparison_truck_card_166x264.png`
- `artifacts/truck_final_mechanical_pass/truck_scale_contact_sheet.png`
- `artifacts/truck_final_mechanical_pass/verification.json`

Reproduktion:

```powershell
$env:PYTHONPATH='src'
$env:QT_QPA_PLATFORM='offscreen'
.venv/Scripts/python.exe -m production_zero.tools.truck_asset_qa after --output-dir artifacts/truck_final_mechanical_pass
.venv/Scripts/python.exe -m production_zero.tools.truck_asset_qa compare --output-dir artifacts/truck_final_mechanical_pass
.venv/Scripts/python.exe -m production_zero.tools.truck_asset_qa verify --output-dir artifacts/truck_final_mechanical_pass
```
