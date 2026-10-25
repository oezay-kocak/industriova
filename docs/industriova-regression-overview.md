# Industriova 0.2.0 – Regressionsübersicht

**Aktueller Stand: 0.2.0.dev2 – UI Repaired Playtest.** 74/74 Module, **1.161 Tests bestanden**, 26 neue Prüffälle; zusätzlich 37 UI-Prüfungen bei 200% und 90 wiederholte Klickpfade. Die bestätigten Bedienfehler sind gezielt korrigiert. Der native Produktions-OLE-Drag und die vollständige menschliche Gameplay-Abnahme bleiben offen. Aktueller Nachweis: [UI-Reparaturbericht](industriova-ui-repair-report.md).

Die folgende Übersicht dokumentiert den früheren dev1-Stand vor der UI-Diagnose und ist keine aktuelle Fehlerfreiheitserklärung.

**Technisch bestanden; bereit für den nächsten menschlichen Playtest.** Eine vollständige menschliche Release-Abnahme steht weiterhin aus.

| Punkt | Ergebnis |
| --- | --- |
| Testmodule | **73 von 73 erfolgreich** |
| Ausgeführte Tests | **1.135 bestanden**, 0 fehlgeschlagen, 0 übersprungen, 0 XFAIL |
| Produktivfehler behoben | **13**, einzeln im Release-Bericht aufgeführt |
| Bestehende Testfunktionen angepasst | **160**; fünf zusätzliche Integrations-/UI-Funktionen |
| Alte Zeitlimits | Beide aufgeklärt: echter Kaufdialog im UI-Test bedient; Pixelprüfung ohne Millionen einzelner Qt-Aufrufe. 217 UI-Tests vollständig, Raster-Modul rund 5,5s statt 149,4s. |
| Fehlerklassifizierung | **167 Ergebnisse** mit Einzelbegründung: 121 A, 3 B, 42 C, 1 D. Zusätzliche Produktfehler aus Integrations-/Sichtprüfung separat dokumentiert. |
| Wirtschaft / Rarity | 304 Rezeptkalkulationen, 20 echte Endausbau-Simulationen, 10.000 Upgrade-Serien erfolgreich wiederholt |
| Migration | **16 von 16 Slots**, erweiterte Daten-/Idempotenzprüfung; Originale nicht überschrieben |
| Oberfläche | 57 gerenderte Ansichten bei drei Auflösungen; elf UI-Prüfungen zusätzlich bei 200% DPI |
| Performance | Cache und Lagerbilanz erhalten; bei 500 Karten kompletter Save **343.0 → 343.3ms**, warmes Zeichnen **198.0 → 172.8ms**. Schwankende Taktmessungen zusätzlich über 500 reale Takte untersucht. |
| Windows-Build | **0.2.0.dev1**, ZIP/Metadaten/353 Ressourcenbilder geprüft, keine persönlichen Saves; drei native EXE-Starts und geordnete Abschlüsse mit fortgesetztem Spielstand |
| Verbleibende technische Fehler / externe Blocker | **Keine in der geprüften lokalen Version** |

Paket: `dist/playtest/Industriova-0.2.0-stabilized-playtest-Windows.zip`.

Einzelheiten: [Release-Bericht](industriova-release-report.md), [vollständige Klassifizierung](industriova-regression-classification.md). Prüfdaten: `artifacts/industriova-stabilization/verified-tests/results.json`.

Noch menschlich zu prüfen: längere wirtschaftliche Spielverläufe, tatsächliche Windows-Bedienung mit Drag-and-drop, verschiedene Bildschirme/DPI sowie subjektive UI- und Autosave-Reaktionszeiten. Automatisierte Startprüfungen sind keine manuelle Gameplay-Abnahme.
