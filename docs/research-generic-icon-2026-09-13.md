# Generisches Research-Icon

## Asset und Maske

Kanonischer Pfad: `src/production_zero/assets/ui/research_generic.png`.

Das Original-PNG wurde mit der ausdrücklich freigegebenen deterministischen Pixel-Maske verarbeitet. Die beiden zuvor erzeugten Bildeditor-Ausgaben werden nicht verwendet. Endgültige Methode: ausschließlich vom Bildrand erreichbare helle, nahezu neutrale Hintergrundpixel erhalten Alpha 0. Eingeschlossene Metalllichter werden nicht anhand ihrer Farbe entfernt.

- Originalgröße 1254×1254 unverändert; kein Resampling oder neuer Render.
- Echte RGBA-Datei: 761.048 transparente und 811.468 opake Pixel.
- Alle RGB-Werte wurden nach erneutem Laden des gespeicherten PNG gegen das Original verglichen: **0 geänderte RGB-Pixel**.
- Keine Farbkorrektur. Motivfarben, Gold und Cyan bleiben erhalten.
- Dunkle Kontrollansicht visuell geprüft: keine Checkerboard-Flächen oder breiten grauen/weißen Hintergrundsäume. Feine ursprüngliche Metallkanten bleiben erhalten; sie wurden nicht pauschal erodiert.
- Reproduzierbares Werkzeug: `src/production_zero/tools/research_icon_cutout.py`.
- Audit samt Original-SHA256: `artifacts/ui/research-generic-icon/alpha-audit.json`.

## Einbindung

Ein semantischer Schlüssel `ui.research_generic` ersetzt im Renderer die Resource-Referenz aller gewöhnlichen Small Nodes. Die Definitionen wurden nicht einzeln verändert. Die unveränderte 40×40-Iconbox verwendet weiterhin Seitenverhältniserhaltung und SmoothTransformation im bestehenden Rastercache.

Major Nodes behalten ihre bestehende node.icon_resource-Referenz und 60×60-Box. Produktspezialisierungen behalten die exakte Produktreferenz; ungewählte Slots behalten die bisherigen Platzhalter. Layout, Schrift, Farben, Knotengrößen, Mechanik und Kosten wurden nicht geändert. Das neue assets/ui-Verzeichnis ist in den Paketdaten enthalten.

## Prüfung

9 fokussierte Tests bestanden: test_research_generic_icon.py, test_research_layout_stability.py und test_research_specialization_ui.py. Die zwei Icon-Tests nach Bereinigung des Screenshot-Capture-Ablaufs erneut bestanden.

Alle 21 Bäume auf Icon-Zuordnung geprüft, einschließlich Company, Production, Agriculture, Forestry, Metals und Electronics. Major- und Spezialisation-Referenzen bleiben erhalten. Aufgewärmte Company-/Industry-Bäume zeigen beim Kauf keine neuen Decode-/Scaling-Cache-Misses und keine Geometrieänderung. Die bestehenden Layout-Tests prüfen beide Fenstergrößen 1600×900 und 1366×768.

compileall und git diff --check bestanden. Gesamte Testsuite NICHT ausgeführt. Nur OFFSCREEN-Qt, keine Live-GUI und kein Spielerspielstand.

Drei Spielszenen wurden erfasst und visuell geprüft:

1. `artifacts/ui/research-generic-icon/01-company.png`
2. `artifacts/ui/research-generic-icon/02-industry.png`
3. `artifacts/ui/research-generic-icon/03-selected-product.png`

Zusätzliche Kantenkontrolle: `artifacts/ui/research-generic-icon/cutout-on-dark.png`.

## Ergänzende Abnahme des Folgeauftrags

Die deterministische Bereinigung wurde erneut direkt auf dem Original ausgeführt. Die Produktions-PNG ist byte-identisch zur bereits integrierten Datei (identischer SHA256); es existiert weiterhin nur eine Produktionsversion. PNG-IHDR-Farbtyp 6 (RGBA), Alpha 0 an allen vier Ecken und Alpha 255 im Motivzentrum wurden zusätzlich geprüft. Transparente und opake Flächen sind beide vorhanden.

Kontrollbilder cutout-on-dark.png und cutout-on-light.png wurden visuell geprüft: kein Checkerboard, kein rechteckiger Hintergrund und kein auffälliger heller Hintergrundsaum. Die ursprünglichen Metalllichter wurden erhalten.

Erneut 9 fokussierte Tests bestanden, einschließlich Cache-Miss-Vergleich bei Käufen, aller 21 Baum-Iconzuordnungen, stabiler Layouts bei beiden Fenstergrößen und exakter Produkt-Spezialisierungsicons. Alle drei Spiel-Screenshots wurden erneut erzeugt. compileall und git diff --check bestanden. Keine vollständige Testsuite, keine Live-GUI.
