# Freight SVG Asset-Pass

Stand: 7. September 2026. Die Bildreferenz wurde ausschließlich für die Fahrzeuge verwendet. Kartenlayout, Rahmen, Rarity-/Familienfarben, Texte, Buttons und Interaktionscode wurden nicht verändert. Die reale GUI wurde nicht gestartet.

## Ausgangspunkt und Integration

Die sichtbaren Freight-Piktogramme lagen in `src/production_zero/ui/game_ui/rendering/factory.py`, Funktion `_draw_prototype_pictogram()`. `draw_machine_card_prototype()` ruft diese Funktion im bestehenden farbigen Bildbereich auf. Sowohl `ClickableFreightSlotCard` als auch die Inventar-/Auswahlkarten nutzen diesen Renderer. Die versteckten Kompatibilitätswidgets und kleinen Resource-/Hover-Icons sind davon unabhängig und bleiben unverändert.

`src/production_zero/ui/freight_art.py` ordnet die vier Familien ihren SVG-Dateien zu, lädt sie mit `QSvgRenderer` und hält maximal vier Renderer im Cache. Der vollständige ViewBox wird proportional und zentriert in das unveränderte Zielrechteck eingepasst. Es gibt keine Zuschneidung und keine Verzerrung. Disabled-Darstellung reduziert ausschließlich die Zeichen-Deckkraft; der Painter-Zustand wird danach wiederhergestellt. Fehlende oder ungültige Assets werden explizit gemeldet.

Im Kartenrenderer werden nur die vier Freight-Familien an diesen Asset-Renderer weitergeleitet. Die ersetzten Train-/Ship-/Aircraft-Zeichenblöcke wurden entfernt. Das bisher gemeinsam mit Truck verwendete generische Transport-Piktogramm bleibt für die Familie `transport` erhalten.

## Neue Assets

Alle Dateien liegen in `src/production_zero/assets/freight/` und besitzen einen ViewBox von `0 0 320 240`, transparenten Hintergrund, dunkle Konturen und flächige Licht-/Schattenstufen. Ausschließlich native SVG-Gruppen, Pfade, Kreise und Ellipsen; keine Texte, Filter, Rasterbilder oder externen Abhängigkeiten.

| Datei | Gestaltung |
| --- | --- |
| `truck.svg` | Helle moderne Kabine, dunkler gerippter Container, gelbe Sicherheitsmarkierung, Mehrfachachsen, Spiegel, Kühlergrill und Leuchten |
| `train.svg` | Blaue Freight-Lok mit erhöhter Kabine, Frontscheinwerfern, Handläufen, Drehgestellen und zwei angedeuteten Güterwagen |
| `ship.svg` | Dunkler Bug, gestufter Rumpf, farbige Container, helle Brücke, Masten und Reling; ohne Wasser/Hintergrund |
| `aircraft.svg` | Heller Cargo-Rumpf, dunkle Unterseite, zwei vollständige Tragflächen, zwei Turbofans, Cockpit und markantes Leitwerk |

`pyproject.toml` enthält die SVGs als Paketdaten. `ProductionZero.spec` sammelt sie auch für PyInstaller. Die Datensammlung wurde geprüft und enthält genau die vier SVG-Dateien; ein vollständiger EXE-Neubau war nicht Teil dieses Passes.

## Offscreen-Prüfung

Die Original-Widgets wurden über ihren tatsächlichen Builder erstellt und ohne `show()` gerendert. Die Baseline stammt aus dem Arbeitsstand unmittelbar vor diesem Pass, nicht aus Git HEAD. Dadurch bleiben bereits vorhandene Projektänderungen im Vergleich berücksichtigt.

| Kartenoberfläche | Originalgröße | Bestehender Fahrzeug-Zielbereich |
| --- | --- | --- |
| Installierte Freight-Karte | 166 × 264 px | 98 × 79,64 px |
| Freight-Auswahlkarte | 166 × 224 px | 104 × 69,56 px |

Visuell geprüft: Silhouette und Fahrzeugtyp klar erkennbar; gemeinsame Konturstärke und Schattierung; konsistente Größenwirkung; Cockpit/Kabine, Ladung und Hauptbaugruppen bleiben lesbar. Feinere Rippen und Technikdetails sind bewusst nachrangig. Beim Schiff wurde eine überstehende Deckfläche während der Prüfung korrigiert. Das gesamte Flugzeug einschließlich beider Flügelspitzen liegt innerhalb des SVGs. Alle vier Assets besitzen auch nach Qt-Rasterisierung mindestens zehn transparente Pixel Abstand zum ViewBox-Rand bei 320 × 240.

Pixelvergleich aller acht Vorher-/Nachher-Karten: **0 geänderte Pixel außerhalb des bestehenden Fahrzeug-Zielbereichs**. Die vollständigen Messwerte stehen in `artifacts/freight_asset_pass/verification.json`.

72 Tests erfolgreich:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.venv/Scripts/python.exe -m pytest tests/test_freight_assets.py tests/test_freight.py tests/test_card_rendering_audit.py tests/test_game_ui_foundation.py -q
```

Die neuen Tests prüfen reine SVG-Geometrie, transparenten Rand, kleine Darstellung in beiden Disabled-Zuständen und Wiederherstellung des Painter-Zustands. Die bestehenden Tests decken Freight-Verhalten und Kartenrenderer ab.

## Vergleich und Reproduktion

- `artifacts/freight_asset_pass/comparison_installed.png`: vier installierte Karten, oben vorher / unten nachher, 1:1.
- `artifacts/freight_asset_pass/comparison_selection.png`: gleicher Vergleich für Auswahlkarten, 1:1.
- `artifacts/freight_asset_pass/assets_preview.png`: Vektorassets als Qt-gerenderte Übersicht.
- `artifacts/freight_asset_pass/before_*.png` und `after_*.png`: Einzelkarten.
- `artifacts/freight_asset_pass/factory_before.py`: unveränderter Renderer-Arbeitsstand vor dem Pass, ausschließlich QA-Baseline.
- `artifacts/freight_asset_pass/renderer_change.diff`: isolierte Änderungen dieses Passes am Kartenrenderer.

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m production_zero.tools.freight_asset_sheet before
.venv/Scripts/python.exe -m production_zero.tools.freight_asset_sheet after
.venv/Scripts/python.exe -m production_zero.tools.freight_asset_sheet compare
.venv/Scripts/python.exe -m production_zero.tools.freight_asset_sheet verify
```

Das QA-Werkzeug erzwingt `QT_QPA_PLATFORM=offscreen`; der Before-Lauf benötigt die mitgelieferte lokale Baseline in `artifacts/freight_asset_pass/`. Die Baseline und PNGs sind QA-Artefakte und werden nicht vom Spiel geladen.
