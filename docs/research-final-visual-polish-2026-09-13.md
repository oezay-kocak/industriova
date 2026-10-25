# Research: finaler visueller Feinschliff

## Visueller Audit und Wiederverwendung

Die vorhandenen RaisedPZButton/RaisedRPBadge-Control-Painter wurden weiterverwendet. Ihre Palette stammt bereits von Storage Expand; die gelbe Primäraktion und die stahlfarbenen Sekundäraktionen behalten diese Rollen. Für den gesperrten Spezialisierungszustand werden draw_lock_warning_frame aus game_ui/rendering/factory.py sowie GameIcon.LOCK mit Accent.LOCKED verwendet. Derselbe Warnrahmen wird von den Factory-/Freight-Locked-Slot-Chassis aufgerufen. Kein neues Schlossbild und keine neue Bildgenerierung.

Der neue kleine paint_module_surface-Helfer adaptiert die vorhandene Materialtechnik: vertikaler Verlauf, dunkle untere/rechte Kante, schmale obere/linke Lichtkante und gezeichneter Schatten. Major-, Small- und Spezialisierungsmodule nutzen denselben Helfer mit ihren bestehenden Silhouetten. Keine Blur-Effekte, Timer, Texturdateien oder neuen Asset-Ladevorgänge.

## Hintergrund und Header

Die bisherigen flachen Shell-, Header- und Sidebar-Flächen verwenden nun warme, neutrale Verläufe mit dunkleren Unterkanten. Die Category-Buttons erhalten ebenfalls einen zurückhaltenden Metallverlauf; ausgewählte Einträge bleiben Graphit mit gelber Kante. Abstände, Border-Breiten, Sidebar-Breite und Header-Höhe wurden nicht geändert. Kein Grün-/Olivstich hinzugefügt.

## Knoten

Major Nodes: warmer heller Lackmetallverlauf, stärkerer unterer Abschluss, seitliche Schattierung und schmale Lichtkante. Small Nodes: Graphitverlauf mit dunkler Basis und zurückhaltender innerer Kantenzeichnung. Bestehende Chamfers, Abmessungen, Icons und Textpositionen bleiben erhalten.

Eyebrows sind nun 14 px bei Majors bzw. 13 px bei Small Nodes statt 13/12 px. Eyebrows, Statuszeilen und Effektzeilen erhalten ExtraBold; die Major-Beschriftung ist dunkler und die Small-Node-Beschriftung heller. Prozentgrößen, Effektgrößen und Textrechtecke bleiben unverändert. Text-Fit wurde auch mit dem tatsächlich verwendeten Gewicht geprüft.

## Spezialisierungen

Gesperrte Module verwenden einen Graphitkörper, die vorhandene PZ-Warnfarbe #df6b2f für Rahmen und Beschriftung sowie einen skalierten kanonischen, abgeschrägten Lock-Warnrahmen. Das echte GameIcon.LOCK wird darin gezeichnet. SPECIALIZATION ist 13 px ExtraBold statt 12 px Bold. Die Modulgröße bleibt 176×184 und die Position bleibt unverändert.

Available bleibt safety-yellow. Selected bleibt cyan mit exakt ausgewähltem Produktbild, Produktname und +1.0%. Unfunded bleibt ein neutraler sekundärer Zustand. Keine Mechanikänderung.

## Controls

RP-Badge, Full Respec und die vorhandenen History-/Inbox-Sekundärbuttons erhalten über ihren bestehenden gemeinsamen Painter einen zusätzlichen inneren Licht-/Bevel-Rahmen. Palette, Geometrie, Hover-, Pressed-, Disabled- und Fokuszustände bleiben erhalten. History/Inbox bleiben Graphit/Stahl, nicht gelbe Primäraktionen.

Verbindungslinien, Routing, Achsen und reservierte Spezialisierungsspalte wurden nicht geändert. Keine Änderung an Kosten, Boni, Topologie, Persistence oder Performance-Architektur.

## Validierung

**21 fokussierte Tests bestanden:**

- 17 Tests: test_research_final_visual.py, test_research_layout_stability.py, test_research_ui.py, test_research_specialization_ui.py.
- 4 Tests: test_research_interaction_polish.py in einem separaten Prozess.

Der erste gemeinsame Testlauf hatte einen einzelnen Timing-Ausreißer: 104,2 ms gegenüber einer 100-ms-Grenze im Kauf-Test. Derselbe Test bestand isoliert; anschließend bestanden alle vier Control-/Interaktionstests im separaten Lauf. Die Grenze wurde nicht gelockert und der Kaufpfad nicht verändert. Daraus wird keine neue Performance-Garantie abgeleitet.

compileall und git diff --check bestanden. Tests prüfen unter anderem identische Geometrie über alle 21 Bäume bei 1600×900 und 1366×768, kein horizontales Scrollen, Text-Fit, kanonischen Lock-Painter, Produkt-Spezialisierungen und Control-Zustände. Die vollständige Testsuite wurde NICHT ausgeführt. Nur OFFSCREEN-Qt, keine Live-GUI, kein Spielerspielstand.

## Fünf geprüfte Screenshots

1. artifacts/ui/research-final-visual/01-company.png
2. artifacts/ui/research-final-visual/02-agriculture.png
3. artifacts/ui/research-final-visual/03-major-small.png
4. artifacts/ui/research-final-visual/04-locked-specialization.png
5. artifacts/ui/research-final-visual/05-header-controls.png

Alle fünf Ansichten wurden visuell geprüft: Materialtiefe statt flacher Weißflächen, kräftigere Schrift, orangefarbener gesperrter Spezialisierungsrahmen, keine Textüberläufe oder horizontale Verschiebung. Am Scrollviewport abgeschnittene weiterführende Knoten sind normales vertikales Scrolling.

## Urteil

Research entspricht aus der geprüften Offscreen-Ansicht jetzt ausreichend eng der etablierten PZ-Materialsprache und ist bereit für die abschließende manuelle Sichtfreigabe. Diese manuelle Freigabe wird nicht vorweggenommen.

Geänderte Dateien dieser Runde: ui/research_view.py, ui/research_specialization.py, ui/pz_controls.py, tests/test_research_final_visual.py und dieser Bericht. Unabhängige bestehende Workspace-Änderungen wurden erhalten.
