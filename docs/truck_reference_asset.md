# Truck reference SVG

Stand: 7. September 2026. `src/production_zero/assets/freight/truck.svg` wurde als vereinfachte Vektorreproduktion der bereitgestellten Truck-Referenz neu erstellt. Train, Ship und Aircraft sowie Kartenlayout und Kartenintegration wurden in diesem Pass nicht verändert.

## Übernommene Konstruktion

- Cab-over-Silhouette in 3/4-Frontperspektive;
- hohe weiße Kabine mit breiter Frontscheibe und sichtbarer Seitenfläche;
- in die Kabinenseite eingesetzte Tür mit Fensterlinie, A-/B-Begrenzung und kleinem Griff;
- langer dunkler, geschlossener Cargo-Kasten mit Dach-, Seiten- und schmaler Heckfläche;
- durchgehender tragender Unterrahmen unter Kabine und vollständigem Aufbau;
- gelber unterer Cargo-Streifen und gelbes geometrisches Seitenzeichen;
- große Frontpartie mit Kühlergrill, Emblem und zwei vereinfachten Leuchten;
- vier sichtbare Radstationen mit perspektivisch abnehmender Größe;
- Radkästen als sichtbare Verbindung zwischen Rädern, Kabine und Cargo-Struktur.

Die Referenz wurde bewusst vereinfacht. Das SVG verwendet große geschlossene Flächen, dunkle Konturen und wenige feste Helligkeitsstufen. Mikrodetails, Texturen, Text, Filter und fotorealistische Effekte wurden ausgelassen.

## Technischer Aufbau

- ViewBox: `0 0 320 240` mit transparentem Hintergrund;
- ausschließlich SVG-Gruppen, Pfade, Ellipsen und ein Kreis;
- keine Rasterbilder, Base64-Daten, externen Abhängigkeiten oder Texte;
- Rendering über den bestehenden `QSvgRenderer`-Pfad;
- vorhandene proportionale Kartenintegration bleibt unverändert.

Die tragenden Hauptteile besitzen stabile SVG-Kennungen: `truck-cargo-side`, `truck-subframe`, `truck-cab-door` und `truck-road-wheels`. Ein Strukturtest bestätigt eine geschlossene Cargo-Seite, einen eigenen Unterrahmen, eine integrierte Tür und genau vier äußere sichtbare Räder.

## Offscreen-Prüfung

Alle Renderings wurden mit `QT_QPA_PLATFORM=offscreen` erzeugt. Die reale GUI wurde nicht gestartet.

| Rendering | Alpha-Grenzen | Sichtbare Pixel | Ergebnis |
| --- | --- | ---: | --- |
| 512 × 512 | `(20, 122)–(491, 426)` | 105.827 | vollständig, transparenter Rand |
| 128 × 128 | `(5, 30)–(122, 106)` | 6.778 | Front, Aufbau und vier Radstationen lesbar |
| 64 × 64 | `(2, 15)–(61, 53)` | 1.751 | Hauptsilhouette und Farbtrennung erhalten |
| Freight-Karte 166 × 264 | bestehender Artwork-Bereich | – | vollständig, zentriert, nicht geclippt |

Die Radaufstandspunkte liegen im SVG bei `y = 224, 223, 221, 218` und steigen damit entlang der perspektivischen Tiefenrichtung gleichmäßig an. Cargo-Aufbau und Kabine liegen auf demselben durchgehenden Unterrahmen. Es gibt keine frei stehenden oder schwebenden Bauteile.

Der Vorher-/Nachher-Pixelvergleich der echten Freight-Karte enthält 4.411 geänderte Pixel, alle innerhalb des vorhandenen Fahrzeugbereichs. Außerhalb dieses Bereichs wurden null Pixel geändert.

74 relevante Tests bestehen, einschließlich Qt-SVG-Validierung, transparentem Innenabstand, Kleinformat-Rendering, Painter-Zustand, strukturellen Truck-Bauteilen und bestehenden Freight-/Kartenrenderer-Tests.

## Artefakte

- `artifacts/truck_reference_asset/after_truck_512.png`
- `artifacts/truck_reference_asset/after_truck_128.png`
- `artifacts/truck_reference_asset/after_truck_64.png`
- `artifacts/truck_reference_asset/after_truck_card_166x264.png`
- `artifacts/truck_reference_asset/comparison_truck_card_166x264.png`
- `artifacts/truck_reference_asset/truck_scale_contact_sheet.png`
- `artifacts/truck_reference_asset/verification.json`

Reproduktion:

```powershell
$env:PYTHONPATH='src'
$env:QT_QPA_PLATFORM='offscreen'
.venv/Scripts/python.exe -m production_zero.tools.truck_asset_qa after
.venv/Scripts/python.exe -m production_zero.tools.truck_asset_qa compare
.venv/Scripts/python.exe -m production_zero.tools.truck_asset_qa verify
```
