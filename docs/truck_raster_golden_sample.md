# Truck raster Golden Sample

Stand: 7. September 2026. Das bereitgestellte Truck-Bild ist das finale Production-Zero-Truck-Asset und der Golden Sample für den zukünftigen Freight-Artstyle. Diese Integration ersetzt alle früheren Truck-SVG-Pässe.

## Finales Asset

- Pfad: `src/production_zero/assets/freight/truck.png`
- Originalformat: PNG
- Abmessungen: 1721 × 914 Pixel
- Seitenverhältnis: 1,8829321663
- Alpha-Kanal: vorhanden
- Transparente Pixel: vorhanden
- SHA-256: `ef243c4bf902e28c2522fa4847bf3fdfb1637e0da6d1415cb89027ed3d5aa39e`
- Dateigröße: 1.263.401 Byte

Die Datei wurde ohne Beschneiden, Retusche, Neugenerierung, Vektorisierung oder Formatkonvertierung kopiert. SHA-256 von Anhang und eingebettetem Asset stimmen überein. Damit sind beide Dateien byteidentisch.

Das frühere `src/production_zero/assets/freight/truck.svg` wurde entfernt. Train, Ship und Aircraft verbleiben unverändert als SVG-Assets.

## Codeänderungen

`src/production_zero/ui/freight_art.py` trennt jetzt Raster- und SVG-Assets:

- `truck` wird aus `FREIGHT_RASTER_ASSETS` als gecachtes `QImage` geladen;
- `train`, `ship` und `aircraft` werden weiterhin unverändert über `QSvgRenderer` geladen;
- der Truck wird proportional mit `KeepAspectRatio` eingepasst;
- 3,5 Prozent Innenabstand verhindern Berührung oder Clipping an den Grenzen des bestehenden Fahrzeugbereichs;
- `QImage.scaled(..., SmoothTransformation)` erzeugt vor dem Zeichnen ein hochwertig heruntergerechnetes Zielbild;
- `SmoothPixmapTransform` bleibt auch beim finalen Painter-Schritt aktiv;
- die Disabled-Deckkraft und der Painter-Zustand verhalten sich wie bei den bestehenden Freight-Assets.

`pyproject.toml` und `ProductionZero.spec` sammeln jetzt neben den drei Freight-SVGs auch Freight-PNGs. Die PyInstaller-Datensammlung wurde geprüft und enthält genau:

- `truck.png`
- `train.svg`
- `ship.svg`
- `aircraft.svg`

Das Kartenlayout und die Geometrie des bestehenden Artwork-Bereichs wurden nicht verändert.

## Offscreen-QA

Alle Renderings wurden mit `QT_QPA_PLATFORM=offscreen` erzeugt. Die reale GUI wurde nicht gestartet.

| Rendering | Alpha-Grenzen | Sichtbare Pixel | Ergebnis |
| --- | --- | ---: | --- |
| 512 × 512 | `(37, 141)–(470, 377)` | 81.765 | vollständig, transparent, proportional |
| 128 × 128 | `(9, 35)–(117, 94)` | 5.205 | sauberes Downsampling |
| 64 × 64 | `(4, 17)–(58, 47)` | 1.369 | klare Silhouette und Farbakzente |
| Freight-Karte 166 × 264 | bestehender Artwork-Bereich | – | mittig, vollständig, ohne Stretching |

Der direkte Kartenvergleich verwendet den letzten Truck-SVG-Stand als Vorher-Bild und das Golden-Sample-PNG als Nachher-Bild. 4.093 Pixel wurden geändert. Alle Änderungen liegen innerhalb des bestehenden Fahrzeugbereichs; außerhalb wurden null Pixel verändert. Rahmen, Hintergrundfarbe, Titel, Rarity-Zeile, Capacity, Assign Route, Status und Remove bleiben pixelidentisch.

Die Quell-PNG berührt innerhalb ihrer eigenen Datei am unteren Rand einzelne Alpha-Pixel. Sie wird deshalb als vollständiges Originalbild mit Innenabstand in den Kartenbereich eingepasst. Kein Quellpixel wird abgeschnitten.

73 relevante Tests bestehen. Sie prüfen unter anderem den exakten Golden-Sample-Hash, Abmessungen, Alpha-Kanal, das Fehlen von `truck.svg`, Seitenverhältnistreue, Qt-Rasterdarstellung, transparentes Padding, Painter-Zustand, bestehende Freight-Logik und den Kartenrenderer.

## Artefakte

- `artifacts/truck_raster_golden_sample/comparison_truck_card_166x264.png` – SVG vorher / finales PNG nachher in echter Kartengröße.
- `artifacts/truck_raster_golden_sample/truck_scale_contact_sheet.png` – 512, 128 und 64 Pixel.
- `artifacts/truck_raster_golden_sample/after_truck_512.png`
- `artifacts/truck_raster_golden_sample/after_truck_128.png`
- `artifacts/truck_raster_golden_sample/after_truck_64.png`
- `artifacts/truck_raster_golden_sample/after_truck_card_166x264.png`
- `artifacts/truck_raster_golden_sample/verification.json`

Reproduktion ohne GUI:

```powershell
$env:PYTHONPATH='src'
$env:QT_QPA_PLATFORM='offscreen'
.venv/Scripts/python.exe -m production_zero.tools.truck_asset_qa after --output-dir artifacts/truck_raster_golden_sample
.venv/Scripts/python.exe -m production_zero.tools.truck_asset_qa compare --output-dir artifacts/truck_raster_golden_sample
.venv/Scripts/python.exe -m production_zero.tools.truck_asset_qa verify --output-dir artifacts/truck_raster_golden_sample
```
