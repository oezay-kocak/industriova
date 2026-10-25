# Industriova 0.2.0.dev1 – Diagnose der Bedienfehler

Stand: 19.10.2026. **Ausschließlich Untersuchung. Kein Produktivcode geändert, kein neuer Build erstellt.**

## Ergebnis und Einordnung

Nachgewiesen sind ein veraltender Rezeptwähler, ein falsches Klickziel beim Kauf späterer Slots, die beschädigte Aktionsleisten-Anordnung und eine unpräzise Supply-Ablehnung. Freight besitzt außerdem keinen angeschlossenen Drag-and-drop-Pfad. Das Pausieren eines Freight-Fahrzeugs funktioniert; eine bereits laufende Fahrt läuft dabei weiter.

Eine gemeinsame globale Sperre aller Mausereignisse ist **nicht nachgewiesen**. Leere Slots in Resources, Factory und Energy, Installation der Starterkarten, Hallenkauf und Unlock Line 3 funktionieren in den nachfolgend beschriebenen Windows-Qt-Proben. Das erklärt oder widerlegt die menschlich beobachteten intermittierenden Ausfälle nicht vollständig. Diese Beobachtungen bleiben offen; dafür werden keine spekulativen Änderungen empfohlen.

## Sicherung, Vergleichsbasis und Verfahren

- Aktueller Arbeitsstand: `artifacts/release-backups/20261018T214852789617Z/`. **712 Dateien**, einschließlich uncommitteter und ungetrackter Projektdateien; **337 konsistente Save-Kopien** einschließlich vorhandener Prüfstände. Alle Archiv-Dateihashes geprüft. Abgleich gegen sämtliche vorhandenen Git-Dateien einschließlich ungetrackter Dateien: keine fehlende Datei vor Beginn der Untersuchung. Löschungen und Git-Ausgangszustand sind zusätzlich als Status, HEAD und binäre Diffs dokumentiert.
- Vor dem Overhaul: ausschließlich `artifacts/release-backups/20261018T185514851717Z/working-tree.zip`. Relevante Originaldateien wurden separat unter `artifacts/industriova-ui-investigation/baseline/` gelesen. Keine Wiederherstellung über den aktuellen Arbeitsstand. Die Sicherung von `203430...` wurde nicht als Vor-Overhaul-Basis ausgegeben.
- Release-Bericht und Regressionsübersicht vollständig gelesen. Der dortige Status „keine verbleibenden technischen Fehler“ ist angesichts dieser Befunde nicht mehr haltbar.
- Reproduktion mit PySide6/QtTest und **Qt-Windows-Plattform**, 1366×768, ohne SaveStore und ohne Zugriff auf persönliche Spielstände. Mausereignisse wurden über das tatsächliche `QWindow` und sichtbare Positionen gesendet. Ziel-Widget, ausgelöste CommandBus-Befehle und resultierender Zustand wurden aufgezeichnet. Haltezeit im vollständigen Spielpfad: 180ms.
- Das ist eine Prüfung der realen Qt-Oberfläche und ihres Event-Routings. Sie ersetzt keinen Test mit physischer Maus, wechselnden Monitoren oder dem vollständigen nativen OLE-Drag-and-drop der gebauten EXE. Ein versuchter nativer Produktions-Drag ergab keinen abgeschlossenen Nachweis und wurde abgebrochen; daraus wird kein Produktfehler abgeleitet.
- Sieben relevante Module aus dem vorhandenen EXE-Pythonarchiv wurden mit dem aktuellen Quellcode verglichen: normalisierter kompilierter Code stimmt überein (`package-source-comparison.json`). Das prüft die Codebasis, nicht die gesamte Laufzeitumgebung des menschlichen Playtests.
- Prüfsummen sämtlicher bereits gesicherter `src/`-Dateien sind nach der Untersuchung unverändert. Neue Dateien sind Diagnosehelfer und dieser Bericht.

Nachweise liegen unter `artifacts/industriova-ui-investigation/`: `backup-verification.json`, `baseline-method-comparison.json`, `diff/`, `package-source-comparison.json`, `probe.json`, `gameplay.json`, `actions.json`, `supply.json` und PNGs.

## Bestätigte Fehler

### D01 – Rezeptwähler bleibt nach natürlicher Freischaltung veraltet

**Reproduktion:** Neues Spiel → Energy → erster Build Slot → Solar Array einsetzen. Resources → erster Build Slot → Extractor einsetzen → auswählen → Recipe → Iron Ore. Factory → erster Build Slot → Processor einsetzen → auswählen → Recipe. Wähler geöffnet lassen, während die reguläre Simulation Rohstoffe produziert. Bei 144 lebenslang produzierten Iron Ore enthält der Spielzustand bereits `recipe.processor.iron`; der geöffnete Wähler zeigt weiterhin ausschließlich die gesperrten Aluminum-/Bitumen-Kacheln. Zurück → Maschine → Recipe: Iron erscheint und lässt sich auswählen. Danach wurden tatsächlich sechs Iron produziert.

**Datei/Funktion:** `ui/factory_view.py:2257`, `FactoryViewBase._refresh_runtime_widgets`; `ui/factory_view.py:2127`, `_populate_production_selection_grid`; ergänzend `ui/factory_view_v2.py:1357`.

**Nachgewiesene Ursache:** Die Produktionsfreischaltung aktualisiert den Zustand, aber der Runtime-Refresh aktualisiert den offenen Rezeptwähler nicht. Seine Kacheln werden bei Öffnen/Filter-/Layoutänderungen erzeugt. Das Öffnen vor dem Unlock konserviert den alten Optionsstand. Es fehlt weder Geld noch ein CommandBus-Aufruf bei der späteren erfolgreichen Rezeptwahl.

**Minimale Korrektur:** Beim Ändern der verfügbaren Produktionsoptionen den offenen Wähler gezielt aktualisieren. Suche, Kategorie, Scrollposition und Auswahl erhalten; kein vollständiger Board-Neuaufbau pro Takt.

**UI-Regressionstest:** Unkonfigurierten Processor einsetzen, Recipe über sichtbare Controls öffnen, durch reguläre Produktion die Schwelle überschreiten; Iron muss ohne Schließen erscheinen und anklickbar werden. Anschließend Warenverbrauch und Iron-Ausgabe prüfen.

**Risiko:** Gemeinsamer Rezeptwähler für mehrere Maschinenfamilien; unnötige Raster-Neuaufbauten könnten Scrollposition, Widget-Identitäten und Performance beeinträchtigen. Der Fehler ist im gemeinsamen Runtime-/Picker-Pfad angelegt; seine Entstehung erst im Overhaul ist nicht belegt.

### D02 – Klick auf S05 kauft S04

**Reproduktion:** Neues Spiel → Factory → gesperrtes **S05** in Line 1 anklicken. Anzeige vor Kauf: S05 kostet $210. Tatsächlich werden **$120** abgezogen; Line 1 erhält einen vierten Slot mit internem Index 6. S05 bleibt gesperrt.

**Datei/Funktion:** `ui/factory_view_v2.py:1595`, `ProductionBoardViewV2._build_line_panel`, insbesondere Verbindung bei Zeile 1654; `ui/factory_view.py:2495`, `_unlock_slot`; `core/commands.py:445`, `UnlockProductionSlot.apply`.

**Nachgewiesene Ursache:** Jede gesperrte Slot-Kachel verbindet sich nur mit der `line_id`, unabhängig von der sichtbaren Slotnummer. Der Command kauft immer `len(line.slot_indexes) + 1`. UI zeigt eine konkrete andere Kaufposition samt anderem Preis, übermittelt sie aber nicht. Diese Verbindung war bereits in der Vor-Overhaul-Version vorhanden; kein neu erfundener Overhaul-Defekt.

**Minimale Korrektur:** Nur den unmittelbar nächsten Slot als kaufbar ausweisen und aktivieren. Spätere Slots dürfen als Vorschau sichtbar bleiben, müssen ihre Voraussetzung eindeutig zeigen. Der bestehende sequenzielle Command kann damit erhalten bleiben. Gleiches Verhalten beim Runtime-Refresh der Aktivierung sicherstellen.

**UI-Regressionstest:** S04/S05/S06 mit ihren Preisen prüfen. Klick auf späteren Slot darf keine unerwartete Buchung auslösen; Klick auf S04 muss exakt dessen Preis und dessen Position freischalten. Auch Resources/Energy und erneute Cash-Änderungen prüfen.

**Risiko:** Gemeinsame Produktionsboards und Erschwinglichkeitsanzeige. Änderungen am Command für beliebige Sprünge würden zusätzlich Wirtschaft und Slotreihenfolge verändern und sind für diese Korrektur nicht erforderlich.

### D03 – Aktionsleiste wird bewusst in zwei ungleich hohe Reihen verteilt

**Reproduktion:** Produktionsboard bei 1366×768 öffnen. Upgrade/Pause/Recipe/Copy stehen oben; Paste/Sell unten links und Sell Building unten rechts, dazwischen freie Zellen. Gemessene Breiten rund **199–200px**, erste Reihe 30px hoch, zweite Reihe 38px.

**Datei/Funktion:** `ui/release_board.py:28`, `ReleaseBoardMixin._release_toolbar`.

**Nachgewiesene Ursache:** Feste Grid-Koordinaten `(index + 1) // 5`, `(index + 1) % 5` erzeugen den Zeilenumbruch unabhängig von verfügbarer Breite. Ohne begrenzte Buttonbreiten verteilt das Grid den Platz auf die Spalten. Unterschiedliche Mindesthöhen von Maschinenaktionen und Gebäudeverkauf bestimmen ungleiche Reihenhöhen. Das ist keine DPI-Vermutung.

**Referenzvergleich:** `artifacts/human_review_followup/factory_reference_1366x768.png` wurde gegen die aktuellen Ansichten geprüft. Die Referenz hat kompakte, gleichmäßig angeordnete Controls und beginnt mit Line 1 unmittelbar unter dem Hallenheader. Die neue Leiste beansprucht etwa 80px zusätzlichen Raum und drückt Linien nach unten. Sie übernimmt weder die kompakte Control-Geometrie noch deren Ausrichtung. Referenzen sind vorhanden; eine ausdrücklich abgenommene neue Massenleiste ist nicht dokumentiert.

**Minimale Korrektur:** Kompakte, einheitlich hohe Actions mit begrenzten Breiten und bewusstem Überlaufverhalten; Gebäudeverkauf und Standorttyp sinnvoll ausrichten. Keine Änderung an den zugehörigen Commands.

**UI-Regressionstest:** Messbare Button-Geometrien und visuelle Referenzen bei 1366/1600/1920 sowie 100/200% Skalierung; keine unkontrollierte Streckung, keine abgeschnittenen Texte und ausreichender Platz für die erste Produktionslinie.

**Risiko:** Gering für Spielzustand; mittleres Layout-Risiko bei langen Beschriftungen und Resources-spezifischem Auswahlfeld.

### D04 – Supply aktiviert Käufe ohne freien Slot und nennt den Ablehnungsgrund nicht eindeutig

**Reproduktion:** Common Supply → MACHINE → Suche „extractor“ → BUY → bestätigen. Mit echten $1.250 Startkapital wird für **$340** ein Extractor automatisch in `site-1`, Slot 0 installiert. Danach ist der Standort voll. In einer getrennt gekennzeichneten Diagnose-Fixture mit **$1.000.000** bleibt BUY aktiv; Klick meldet trotzdem „Insufficient cash or no compatible free slots. Expand the matching production site first.“

**Datei/Funktion:** `ui/supply_view.py:1271`, `_can_buy`; `ui/supply_view.py:1192`, `_buy_offer`; `core/machine_operations.py:19`, `compatible_free_slots`.

**Nachgewiesene Ursache:** `_can_buy` berücksichtigt Cash und Tageskaufstatus, aber keine kompatiblen freien Slots. `_buy_offer` fasst fehlendes Geld und fehlenden Platz in einer Meldung zusammen. Im nachgewiesenen Fall fehlt ausschließlich Platz. Die Ablehnung selbst ist korrekt und atomar; ein allgemeiner Fehler der automatischen Platzierung wurde nicht reproduziert.

**Minimale Korrektur:** Fehlenden Platz und fehlendes Geld getrennt anzeigen, inklusive benötigtem Gebäudetyp beziehungsweise Preis. Verfügbarkeit im Kaufbutton verständlich ausweisen. Die bestehende atomare Kauf-/Installationsoperation erhalten.

**UI-Regressionstest:** Gleicher sichtbarer Kauf mit (a) Geld+Platz, (b) Geld ohne Platz, (c) Platz ohne Geld, (d) falscher Resources-Spezialisierung und (e) Mengen oberhalb der freien Kapazität. Bei Ablehnung keinerlei Buchung/Karte/Installation.

**Risiko:** Niedrig bei reiner Anzeigeänderung; mittleres Risiko für Virtualisierung/Verfügbarkeitsaktualisierung bei vielen Angeboten.

## Bestätigte Funktionslücken und Verhaltensunterschiede

### F01 – Freight hat keinen Drag-and-drop-Anschluss

**Reproduktion:** Startertruck über Freight-Build-Slot einsetzen; im Leerlauf von der Fahrzeugkarte zum benachbarten leeren Slot ziehen. Belegung bleibt unverändert. Quell- und Zielkarte haben `acceptDrops() == False`; `mouseMoveEvent` stammt direkt von QWidget.

**Datei/Funktion:** `ui/freight_view.py:675`, `_build_slot_card` und `ClickableFreightSlotCard`; zum Vergleich `ui/release_board.py:199`, `_release_bind_widget`, `eventFilter`, `_begin_machine_drag`.

**Ursache:** Freight ist kein Produktionsboard mit ReleaseBoardMixin. Es besitzt weder den Maschinen-MIME-/Drop-Filter noch einen eigenen Drag-Start-/Move-Pfad. `core/machine_operations.py:115`, `move_machines`, durchsucht ausschließlich Produktionsgebäude und ist kein geeigneter unverändert wiederverwendbarer Freight-Move-Command.

**Empfehlung:** Freight-Verschiebung gesondert und eng begrenzt an vorhandene Slot-Controls anschließen, sofern Drag-and-drop auch hier das Sollverhalten ist. Passender Facility-Typ, Identität, beschäftigte Fahrzeuge und laufende Sendungen müssen vor jeder Mutation geprüft werden. Keine Neuimplementierung der gesamten Freight-Ansicht.

**UI-Test:** Idle-Truck per vollständiger Mausgeste zwischen zwei gültigen Slots bewegen; danach falschen Facility-Typ, belegtes Ziel und laufende Sendung prüfen. Kein Kartenverlust und keine doppelte Sendung.

**Risiko:** Hoch bei ungeprüfter Wiederverwendung der Produktions-Move-Logik; insbesondere laufende Sendungen und Fahrzeugreferenzen. Das ist eine nachgewiesene fehlende UI-Anbindung, kein nachgewiesener Defekt eines bereits implementierten Freight-Drag-Pfads.

### F02 – Freight-Pause stoppt neue Fahrten, friert eine laufende Fahrt nicht ein

**Reproduktion:** Truck einsetzen → Assign Route → Iron Ore → reguläre Simulation startet eine Fahrt. Fahrzeug-Kontextmenü → Pause. `card.paused` wird true. Die Restzeit fällt trotzdem während weiterer drei Sekunden Wartezeit von **58,26 auf 55,49 Sekunden** (letzter protokollierter Lauf).

**Datei/Funktion:** `ui/release_freight.py:11`, `vehicle_actions`; `core/freight.py:339`, `advance_outbound_shipments`; `core/simulation.py`, `_available_assigned_freight_cards`.

**Ursache:** Das Pause-Command funktioniert. Dispatch überspringt pausierte Fahrzeuge; die Fortschreibung bereits laufender Sendungen prüft die Fahrzeugpause nicht. Die UI zeigt bei beschäftigtem Fahrzeug weiter den Transportstatus, weil `_build_slot_card` PAUSED nur bei `not busy` verwendet.

**Einordnung/Empfehlung:** Beobachtetes Verhalten bestätigt; ob die bestehende Fahrt einfrieren soll, ist aus „Pause funktioniert nicht wie vorgesehen“ allein nicht eindeutig. Minimal ist zunächst eine eindeutige Beschriftung „Keine neuen Fahrten“ samt sichtbarer Pause-Markierung. Falls Einfrieren das verbindliche Soll ist, Sendungsfortschritt gezielt anhalten und vorhandene Reservierung erhalten; nicht ungeprüft umstellen.

**UI-Test/Risiko:** Pause im Leerlauf und während einer Fahrt getrennt prüfen, einschließlich Resume und genau einmaliger Lieferung/Auszahlung. Semantikänderung betrifft Markt, Contracts, Consortium und reservierte Waren; daher mittleres bis hohes Risiko.

### F03 – Freight zeigt nur noch die unmittelbar nächste Erweiterung

**Datei/Funktion:** `ui/freight_view.py:798`, `_locked_slot_specs`.

Die Vor-Overhaul-Version erzeugte alle verbleibenden begrenzten Erweiterungs-Vorschauen und aktivierte nur die nächste. Die neue Version liefert genau eine Vorschau für `len(facility.slots)`. Damit erscheint etwa die Vorschau für S05 erst nach Kauf von S04. Dieser Unterschied ist im Code bestätigt. Dass bereits die **unmittelbar kaufbare nächste** Vorschau generell fehlt, ist nicht nachgewiesen. Produktionsboards erzeugen weiterhin die gesperrten Slots ihrer offenen Linien; geschlossene Linien zeigen eine Expansion statt einzelner Slotkacheln.

**Empfehlung:** Nächsten kaufbaren Slot immer sichtbar und als solchen eindeutig halten. Falls weitere Vorschauen gewünscht sind, ein begrenztes Vorschaufenster für die jetzt unbegrenzten Freight-Erweiterungen anzeigen; nicht die frühere feste Maximalzahl wieder einführen.

**UI-Test/Risiko:** Vor/nach Kauf nächste Vorschau, Preis und Sichtbarkeit prüfen, einschließlich schmaler Fenster und Scrollposition. Risiko hauptsächlich Layout und Kostenanzeige, nicht Save-Format.

## Vollständiger Klickpfad und offene Beobachtungen

Der Spielpfad in `gameplay.json` beginnt ohne installierte Maschinen und ohne zusätzliches Kapital. Nur vorhandene Starterkarten wurden über die sichtbare Auswahl eingesetzt. Energy-Solar liefert Energie; Resources-Extractor erhält Iron-Ore-Rezept; tatsächliche Simulation produziert zunächst 24 Iron Ore innerhalb 15 Sekunden. Nach weiterer regulärer Laufzeit beträgt die lebenslange Menge 144 und Iron ist freigeschaltet. Der offene Wähler bleibt veraltet (D01). Nach Zurück/erneutem Öffnen wird Iron per sichtbarer Kachel gewählt; reguläre Simulation produziert sechs Iron. Damit ist die erste erfolgreiche Rohstoff- **und** Factory-Produktion über UI-Ereignisse nachgewiesen, einschließlich des konkret notwendigen Workarounds.

| Menschliche Beobachtung | Stand dieser Untersuchung |
| --- | --- |
| Resources-Slot/Platzierung unzuverlässig | Erster Slot, Starterinstallation und Rezeptwahl erfolgreich. Intermittierende Ausfälle nicht reproduziert. |
| Factory-Karten einsetzen geht nicht | Zwei Starterkarten über Auswahl installiert. Rezeptwähler-Problem D01 bestätigt. |
| Build Hall reagiert nicht | Echter QPushButton löst PurchaseProductionUnit aus; Hallen 1→2, Cash $1.130→$130. Allgemeiner Ausfall nicht reproduziert. |
| Energy: erster Slot unbedienbar | Build Slot öffnet Auswahl; Solar wird über die Kachel installiert. Ausfall nicht reproduziert. |
| Freight-DnD/Pause | Fehlender Drag-Pfad F01 bestätigt. Pause-Flag funktioniert; laufende Fahrt läuft weiter, F02. |
| Unlock Line 3 reagiert nicht | In `actions.json` trifft sichtbarer Klick GameButton; dritte Linie wird freigeschaltet, $750 abgezogen. Allgemeiner Ausfall nicht reproduziert. D02 betrifft spätere Slotkacheln. |
| Gesperrte Slots erst nach Kauf sichtbar | Geänderte Freight-Vorschau F03 bestätigt. Fehlende unmittelbar nächste Vorschau nicht nachgewiesen. |
| Massenaktionsleiste beschädigt | D03 bestätigt und mit Referenz verglichen. |
| Supply/automatische Platzierung | Erfolgreicher realer $340-Kauf; D04 bestätigt. Unzureichendes Geld bleibt als Ablehnungsgrund grundsätzlich korrekt. |
| Mehrfachauswahl unzuverlässig | Einzel-, Strg-, Shift- und Rechteckauswahl über QWindow erfolgreich; gemeinsame Pause funktioniert. Intermittierender Ausfall offen. |
| Produktions-DnD unzuverlässig | Vollständiger nativer Windows-Drop nicht abgeschlossen; offen. Frühere synthetische Drop-Tests beweisen diesen Weg nicht. |

Methodische Anmerkung: Ein früher Klickversuch im langen Gameplay-Trace traf beim Scrollen nur QWidget statt des Unlock-Buttons. Er ist **kein** Beleg für einen fehlerhaften Line-3-Command. Die separate sichtbare Button-Probe in `actions.json` prüft den gültigen Klickpfad erfolgreich. Ebenso wurden anfängliche Diagnosehelfer-Probleme bei versteckter interner Tabbar und beim Zugriff auf bereits neu aufgebaute Freight-Widgets korrigiert; sie wurden nicht als Produktfehler gezählt.

## Gemeinsame Ursache: was belegt ist und was nicht

Die Produktionsboards teilen Slot-/Kauf-/Freischaltpfade. Der Vergleich zeigt unveränderte ASTs für `_InteractivePaintWidget.mousePressEvent/mouseReleaseEvent`, `ClickableCapacityPanel.mousePressEvent`, `FactoryCardSelectionTile.mousePressEvent`, `FactoryViewBase._on_slot_clicked`, `_purchase_hall`, `_unlock_line` und `_unlock_slot`. Neue Event-Filter behandeln Drag/Drop und Auswahl auf Linienhintergründen. Sie verschlucken in den erfolgreichen Proben die Build-Slot-Klicks nicht.

**Belegt:** D01 erklärt eine konkret nicht verfügbare Recipe-Aktion trotz bereits erfolgtem Unlock. D02 erklärt scheinbar wirkungslose spätere Slotkäufe bei tatsächlicher Buchung an anderer Stelle. D03 verringert den sichtbaren Produktionsraum. Freight hat einen anderen, unvollständigen Eingabepfad. Es sind mehrere Ursachen, nicht eine belegte globale CommandBus-Störung.

**Ungeprüfte Vermutungen:** Physische Maus-/Treiberereignisse, gemischte Monitor-DPI, ein bestimmter geladener Spielstand, verdeckte Fenster/Overlays und Unterschiede zwischen tatsächlichem Playtest-Paket und untersuchtem Paket könnten zusätzliche Ausfälle erklären. Für keine dieser Möglichkeiten liegt hier ein Nachweis vor; sie rechtfertigen derzeit keine Produktivänderung. Der untersuchte Quellstand und die untersuchten EXE-Module passen zusammen.

## Warum 1.135 Tests das nicht erkannten

Die Zahl bezeichnet bestandene Einzelprüfungen, keine 1.135 vollständigen Bedienabläufe. Konkrete Lücken:

1. `tests/test_industriova_release_ui.py:51`, `populated_factory`, setzt $1e12 und installiert Maschinen direkt über `buy_common_supply_cards`. Das umgeht den Einstieg über Build Slot und Kartenauswahl sowie echte finanzielle Einschränkungen.
2. `test_group_drop_preserves_identities_and_mk` ruft `board.eventFilter(target, drop)` direkt auf. Es prüft den synthetischen Drop und die Mutation, nicht Drag-Start, gehaltene Taste, Native-MIME-Übertragung, Ziel-Hit-Test oder Windows-OLE. Freight kommt in diesem Ablauf gar nicht vor.
3. `test_ui_configuration_copy_pause_and_rectangle_selection` setzt Auswahl/Rezeptfreigabe direkt und ruft Pause/Copy/Paste als Methoden auf. Es wartet nicht mit geöffnetem Picker auf eine natürliche Freischaltung.
4. `test_purchase_dialog_quantity_installs_and_counts_owned_machines` startet über `_buy_offer` und hohe Geldbestände. Der reale Weg Navigation → Kategorie → Karte → BUY sowie getrennte Ablehnungsgründe fehlen.
5. Zahlreiche Factory-Tests rufen `_on_slot_clicked(...)` auf oder emittieren Signale. Der alte Testbestand hat viele fachlich sinnvolle Backend- und Komponentenprüfungen, aber kein ausreichendes Coverage für den echten Klickpfad ab leerer Installation.
6. Die allgemeine Factory-Testfixture beantwortet sichtbare IndustrialDialogs automatisch. Ohne zusätzliche Erwartung des konkreten Dialogtitels/-textes kann dadurch auch eine Fehlermeldung geschlossen werden, ohne dass der Test die Ablehnungsursache bewertet.
7. Auflösungs-/Rasterprüfungen prüfen überwiegend Grenzen, Sichtbarkeit und Cache-Verhalten. Eine zweizeilige Leiste kann alle Geometriegrenzen einhalten und trotzdem die akzeptierte Gestaltung verfehlen. Die 57 Screenshots waren keine vollständige vergleichende UI-Abnahme.
8. Native EXE-Smokes prüften Start, Save-Fortsetzung und Schließen. Sie enthalten keine Gameplay-Klickfolge und keinen tatsächlichen Drag-and-drop.

Zusätzlich erforderlich: dauerhaft automatisierter Windows-Qt-Spielpfad vom leeren Produktionsstand bis Iron, offener Picker während Progressionswechsel, jedes sichtbare Kaufziel mit exakter Cash-/Slotprüfung, Freight-Verschiebung und Pause in beiden Betriebszuständen sowie native Produktions-Drags inklusive Abbruch/Fehlziel/Gruppenauswahl. Unterstützte Auflösungen/DPI dabei als unterschiedliche Ausführungsumgebungen behandeln; Layout-Abnahme nicht durch bloßes „kein Clipping“ ersetzen.

## Empfohlene Reparaturreihenfolge

1. D01: offenen Rezeptwähler bei tatsächlichem Optionswechsel aktualisieren.
2. D02: sichtbares Slot-Kaufziel und tatsächlich gekauften nächsten Slot in Übereinstimmung bringen.
3. D03/D04: kompakte Aktionsleiste und eindeutige Kauf-Ablehnungsgründe.
4. F01/F02/F03: Freight-Eingabepfad und gewünschte Pause-/Vorschausemantik gezielt bearbeiten; native Drag-Fragen separat reproduzieren.

Diese Empfehlungen wurden **nicht implementiert**. Kein Rollback, keine Save-Migration, kein Neubau und keine Änderung funktionierender wirtschaftlicher Systeme. Die offenen menschlichen Beobachtungen bleiben als offene Befunde bestehen.
