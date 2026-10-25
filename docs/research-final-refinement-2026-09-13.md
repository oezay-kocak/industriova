# Research — abschließende visuelle Verfeinerung

## Typografie: genaue Änderungen

| Element | Vorher | Jetzt |
|---|---|---|
| RESEARCH & DEVELOPMENT | 22 px / 900 | 24 px / 900 |
| COMPANY / INDUSTRIES | 16 px / 900 | 17 px / 900 |
| Kategorien | 13 px / 800 | 13 px / 900 |
| Header-Zusammenfassung | 13 px / 800 | 13 px / 900 |
| Major-Eyebrow | 14 px / 800 | 15 px / 900 |
| Major-Prozent | 29 px / 700 | 30 px / 900 |
| Major-Effekt | 16 px / 800 | 17 px / 900 |
| Major-Status | 12 px / 800 | 13 px / 900 |
| Small-Eyebrow / Effekt / Status | 13 / 14 / 11 px, Gewicht 800 | gleiche Größen, Gewicht 900 |
| Small-Prozent | 25 px / 700 | unverändert |
| Gesperrt: SPECIALIZATION | 13 px / 800 | 14 px / 900 |
| Gesperrt: LOCKED | 12 px / 800 | 13 px / 900 |

Die Schrift bleibt Bahnschrift. Small Nodes behalten ihre hellen Beschriftungen und die bisherigen Zustandstöne auf Graphit; kein Wechsel zu schwarzem Text. Major-Texte bleiben nahe Schwarz. Die vier zusätzlichen Pixel der Sidebar-Überschrift werden durch vier Pixel weniger Abstand zur Kategorienansicht ausgeglichen. Die etwas größeren Abschnittslabels erhalten entsprechend kleinere Padding-Werte. Button-Geometrien und Auswahlmetriken bleiben stabil.

## Sichtbar stärkeres Material

- Shell diagonal: #e9e2d9 → #c6bfb5 bei 38 % → #797976.
- Sidebar vertikal: #eee8df → #d2cbc1 bei 30 % → #95918a.
- Header vertikal: #f5eee4 → #e4dcd1 bei 9 % → #c5bdb2 bei 70 % → #92908a.
- Kategorieflächen vertikal: #ede7de → #d9d2c8 bei 15 % → #aaa69f.
- Major-Flächen vertikal: #f2ece3 → #dcd6cd bei 16 % → #bdb7ae bei 72 % → #85817b.

Die stärkere Hell-Dunkel-Spreizung ist in den normalen 1600×900-Aufnahmen sichtbar, besonders an Header, Sidebar und Major-Unterkante. Warme neutrale Lackmetall-/Betontöne ohne Grün-/Olivstich. Die vorhandenen oberen/linken Lichtkanten, unteren/rechten Schattenkanten und Chamfers bleiben erhalten. Keine Kratzer, Texturdateien oder Grunge-Effekte. Small-Node-Material und Graphit-Arbeitsfläche wurden nicht neu gestaltet.

## Zentrierte gesperrte Spezialisierung

Nur der gesperrte Zustand verwendet einen gemeinsamen, 97 px hohen Block, zentriert in der unveränderten 176×184-Chassisfläche. Sein Mittelpunkt liegt bei (88,92):

- Überschrift: y=43,5, Höhe 18.
- Kanonisches Lock-Gehäuse: y=69,5, Größe 49,6×44,8.
- LOCKED: y=122,5, Höhe 18.

Alle drei Rechtecke sind horizontal auf X=88 zentriert. Rahmenfarbe #df6b2f, GameIcon.LOCK und der Factory-Warnrahmen bleiben erhalten. Available-/Selected-Innenlayouts und exakte Produkticons bleiben unverändert. Slot-Position, Connector und 42-px-Inset bleiben unverändert.

## Controls und Scope

RP und Full Respec benötigen nach Sichtprüfung keine weitere Änderung; sie behalten die bestehende orange/gelbe Raised-PZ-Darstellung. History/Inbox wurden nicht geändert. Keine Änderung an Mechanik, Topologie, Werten, Achsen, Node-Abmessungen, Icons, Speicherpfad oder Performance-Architektur.

## Validierung

21 fokussierte Tests bestanden: 17 Visual-/Research-UI-/Layout-/Specialization-Tests sowie 4 Control-/Interaktionstests. Die Tests verwenden die tatsächlichen neuen Schriftgewichte, prüfen den zentrierten Lock-Block, Text-Fit, die Layoutstabilität aller 21 Bäume bei 1600×900 und 1366×768, fehlendes horizontales Scrollen sowie vorhandene Spezialisierungs- und Control-Zustände. compileall und git diff --check bestanden.

Vier Screenshots erzeugt und visuell geprüft:

1. artifacts/ui/research-final-refinement/01-company.png
2. artifacts/ui/research-final-refinement/02-agriculture.png
3. artifacts/ui/research-final-refinement/03-major-small.png
4. artifacts/ui/research-final-refinement/04-locked-specialization.png

Kein Textüberlauf, keine horizontale Verschiebung und kein Grün-/Olivstich festgestellt. Vollständige Testsuite NICHT ausgeführt. Ausschließlich OFFSCREEN-Qt, keine Live-GUI.

## Schlussurteil

Aus der geprüften Offscreen-Ansicht ist Research jetzt bereit für die finale manuelle Sichtfreigabe: stärkere Typografie und Materialtiefe, weiterhin gut lesbare Small Nodes und ein ausbalancierter Lock-Block. Die tatsächliche manuelle Freigabe bleibt beim Nutzer.
