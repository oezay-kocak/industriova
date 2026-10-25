"""Write the requested two reports from accepted P10 evidence."""
from pathlib import Path
import json,hashlib
root=Path.cwd();out=root/'artifacts/phase10';docs=root/'docs'
read=lambda name:json.loads((out/name).read_text(encoding='utf8'))
a=read('resource-price-audit.json');summary=read('regression-summary.json');protected=read('protected-verification.json');visual=read('visual-review.json')
before=read('performance/before/results.json');after=read('performance/after/results.json')
def money(n):return f'${n:,.2f}'
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |']+['| '+' | '.join(map(str,row))+' |' for row in rows])
primary=table(['Resource','Produktion U/min','Basispreis/U','Cash/min direkt, nominal','Maschine','Energie','Freight','Weiterverarbeitung (Auswahl)','Vergleich'],[
 [r['name'],f"{r['rate']:g}",money(r['price']),money(r['gross_cash_min']),money(r['machine_cost']),f"{r['power']:g} MW; Solar: $0/min",f"{r['freight_units_min']:g} U/min",', '.join(e['name'] for e in r['consumers'][:4]) or 'keine direkten Folgerezepte',f"Level {r['company_level']}; {'Genesis-unlocked' if r['initially_unlocked'] else 'später'}; {r['descendants']} Folgeprodukte"] for r in a['raws']])
sim=table(['Resource','MK / Rarity','Erlös in 10 min','Ist Cash/min','Nominell Produktion / Freight U/min','Solar','Ersatzkapital'],[
 [r['resource'],f"{r['mk']} / {r['rarity']}",money(r['actual_cash']),money(r['cash_min']),f"{r['theoretical_production_min']:g} / {r['theoretical_freight_min']:g}",r['solar_generators'],money(r['capital'])] for r in a['simulations']])
representatives={'iron_ore','coal','copper_ore','bauxite','limestone','quartz','crude_oil','timber','wheat'}
recipes=[]
for r in a['raws']:
 if r['resource'] not in representatives:continue
 for e in r['consumers'][:4]:
  recipes.append([r['name'],e['name'],', '.join(f'{q:g} {k}' for k,q in e['inputs'].items()),f"{e['output']:g}",money(e['output_price']),money(e['added_value_per_cycle'])])
chain=table(['Primärrohstoff','Folgeprodukt','Inputs je Zyklus','Output U','Basispreis/U','Mehrwert/Zyklus gegenüber Input-Sell'],recipes)
best=sorted(a['chains'],key=lambda r:r['gross_cash_per_total_machine_minute'],reverse=True)
stage=table(['Tiefe','Bestes Produkt nach reinem Maschinenzeitmaß','Cash pro gesamter Maschinenminute'],[[depth,entry['name'],money(entry['gross_cash_per_total_machine_minute'])] for depth in sorted({r['depth'] for r in best}) for entry in [next(r for r in best if r['depth']==depth)]])
audit=f'''# INDUSTRIOVA 0.3 – P10: Rohstoffpreis- und Weiterverarbeitungs-Audit

Stand 23.10.2026. Reale feste Kataloge: 49 Primärrohstoffe, 353 Produkte, alle unmittelbaren Rezeptinputs und rekursiven Rohstoffbedarfe. Keine Preis-, Rezept-, MK-, Rarity-, Research- oder Freight-Balancingänderung.

## 1. Bewertung

Copper Ore liefert bei gleicher MK1/Common-Maschine, 120 U/min und 6 MW **40 % mehr nominalen Direktverkauf** als Iron Ore: $168.00 statt $120.00/min. Bei demselben einzelnen Startertruck werden im echten 10-Minutenlauf $46.48 statt $33.20/min ausgezahlt. Crude Oil erreicht bei denselben Rohmaschinenkosten von $340.00 nominal $264.00/min und mit derselben knappen Freight $73.04/min. Dieser Vorteil besteht bei unveränderten Routen, MK und Research fort; feste Preise enthalten keinen automatischen zeitlichen Ausgleich. Das ist ein nachgewiesener Anreiz zu profitableren Direktverkaufsbranchen, kein zufälliger Anzeigerundungsfehler.

Für das isolierte Ziel maximaler passiver Cash-Erzeugung aus gleich vielen Rohmaschinen und gleicher Freight ist daher eine höher bewertete, bereits freigeschaltete Rohstoffroute wirtschaftlich überlegen. Im späteren Katalog liegen z.B. Platinum Ore ($5.80/U, Level 20) und Palladium Ore ($5.40/U, Level 20) darüber; Uranium Ore ($3.20/U) benötigt Level 25. Diese sind **keine** sofort verfügbaren Early-Game-Alternativen. Die Tabelle führt die tatsächlichen Voraussetzungen getrennt auf.

Die stärkere Behauptung, es gebe über alle vollständigen Firmen hinweg keinen vernünftigen Grund für andere Branchen, ist damit nicht belegt: Iron Ore wird in 108, Copper Ore in 113, Crude Oil in 175 und Wheat in 9 verschiedenen Folgeprodukten rekursiv benötigt. Processing-/Fabrication-/Assembly-Ketten, Research-Freischaltungen sowie ausgewählte persönliche und Consortium Contracts benötigen konkrete Warenkombinationen. Es gibt keine wirtschaftliche Regel, die diese Rohstoffe einfach gegenseitig ersetzt. Eine spätere Kette neutralisiert einen früheren Preisvorteil nicht automatisch; ihr Bedarf schafft einen eigenständigen Nutzen. Die unten stehenden Mehrwerte und Maschinenzeitkennzahlen machen diesen Unterschied quantitativ sichtbar.

## 2. Rechenbasis und Grenzen

Nominelle Rate = `output_amount_for(definition) × 60 / cycle_seconds_for(definition) × card.output_multiplier`. Maschinenleistung verwendet unverändert `card.power_multiplier`. Common hat 0 % Bonus, Legendary in den Vergleichsfällen den real zulässigen Maximalroll 20 %. MK1/10/99 entsprechen unverändert 1/3.25/25.5; Rarity skaliert Produktion und Energie unterschiedlich. Freight verwendet die reale `freight_stats`-Kapazität und Reisezeit, einschließlich ihres Rarity-Einflusses.

{a['assumptions']}

Die 76 Engine-Strategien starten bei leerem Lager, mit je einem Rohstoffproduzenten und einem Fahrzeug passenden MK/Rarity. Solar wird passend zur tatsächlichen Leistung in ganzen MK1-Generatoren ergänzt. Genannte Ersatzinvestitionen enthalten Rohmaschine, Solar, Truck und die echten MK-Upgradekosten auf Common-Anschaffungsbasis. Die Legendary-Leistungsfixture ist ausdrücklich ein Qualitätsvergleich bereits vorhandener Karten; ein Legendary-Erwerb ist im Common Supply nicht verfügbar, seine Erwerbsprämie wird nicht erfunden. Für Legendary ist diese Kapitalspalte deshalb nur eine Common-Referenz/Untergrenze und kein tatsächlicher Einkaufspreis. Zusätzliche Gebäudelinien/Slots für große spätere Szenarien sind in diesem reinen Maschinenvergleich nicht eingepreist; es ist kein vollständiger ROI- oder organischer Spiellauf. Grundvoraussetzungen für alle Rezepte/Level sind nur in dieser isolierten Kapazitätsfixture freigegeben. Tatsächliche Genesis-Freischaltungen werden separat genannt. Produktions-/Ankunfts- und Tick-Wartezeit ist im 600-Sekunden-Isterlös enthalten; laufende Restsendungen sind am Messende noch kein Cash. Lagerreste sind im JSON erhalten.

Solar verbraucht keinen Brennstoff und erzeugt keinen laufenden Cash-Abzug. Deshalb wäre eine erfundene Stromgebühr falsch. Die Tabelle nennt MW und erforderliches Solarkapital; bei Brennstoffkraftwerken wären zusätzlich reale Fuel-Opportunitätskosten erforderlich. Im JSON stehen alle Eingänge und Annahmen. Der ausschließlich im Offline-Harness verwendete Arbeitswertcache wurde vor Verwendung für alle 353 Werte exakt gegen den Originalrechner verglichen. Engine, Waren, Zeit, Freischaltungen, Freight und Cash werden nicht übersprungen. Performanceprozesse verwenden diesen Harnesscache nicht.

## 3. Alle Primärrohstoffe

{primary}

## 4. Reale Engine-Strategien

{sim}

## 5. Direkte Weiterverarbeitung und Input-Opportunität

Mehrwert = `Ausgabemenge × fester Ausgabepreis − Summe(Inputmenge × fester Inputpreis)`, vor zusätzlichem Energie-/Maschinen-/Transportkapital und ohne Vertragsboni. Ein positiver Mehrwert pro Zyklus ist keine Zusage besserer Cash-Rate pro eingesetztem Kapital oder pro MW. Sämtliche unmittelbaren Folgerezepte, nicht nur diese Auswahl, stehen im JSON.

{chain}

## 6. Vollständiger Kettenvergleich

Für alle 353 Produkte sind rekursive Rohstoffmengen pro Einheit, Tiefe, direkte Inputvoraussetzungen, Grundpreis und der vorhandene `ProductionValueCalculator.value_per_unit` erfasst. Das Zeitmaß summiert die Produktionsarbeit der gesamten Kette; die Preis/Zeit-Kennzahl ignoriert parallele Anlagenauslegung, ganzzahlige Maschinen, Strom/Fuel, Storage und Freight. Sie darf deshalb nicht als realer Firmenprofit ausgegeben werden. Sie beantwortet die engere Frage, ob hohe Endproduktpreise allein bereits bessere Arbeitsproduktivität beweisen.

{stage}

Early Game: die neun ursprünglichen Startprodukte sind freigeschaltet; der Direktverkauf bevorzugt höhere Grundpreise. Mid Game: neue Rohstoffe und Mischketten verlangen tatsächliche Produktionshistorie und Company-Level; relative Preisunterschiede bleiben. Late Game: hohe Endpreise und Vertragsbedarf schaffen weitere Ziele, aber die obige reine Arbeitskennzahl zeigt keine automatische vollständige Kompensation des frühen Direktverkaufsvorteils. Eine globale Optimierung jeder zulässigen Fabrik/Flotte wurde nicht behauptet oder simuliert. 353 rekursive Kettenkennzahlen plus 76 echte Rohstoffläufe sind der tatsächlich geprüfte Umfang.

## 7. Drei freie Startstandorte

P9→P10 ändert ausschließlich Genesis um Drilling Field 1 und Agricultural Estate 1. Das Startkapital bleibt $1,250.00, alle acht Starterkarten behalten Definition/MK/Rarity/Investition und bleiben unplatziert; es gibt weder neue Maschinen noch zusätzliche Energie, Produktion, Waren, XP oder Research. Leere Sites erzeugen nichts. Der Spieler spart gegenüber dem früheren Erwerb die beiden ersten $500.00-Sites, erhält aber weiterhin keine Drilling-/Agriculture-Maschine. Erst deren Kauf und ausreichend Energie/Freight erschließen die zusätzliche Produktion. Jeder weitere Standort desselben Typs kostet nach unveränderter P7-Quote $4,000.00. Altspielstände bleiben beim Laden unverändert.

Der vorhandene finite Early-Game-Regressionslauf verwendet nun diese realen freien Erststandorte, kauft Maschinen/Solar weiter regulär und bestätigt nichtnegative Bestände/Cash, positive tatsächliche Verkäufe und Erreichbarkeit beider Branchen binnen der vorhandenen 360-Sekunden-Grenze. Dieser technische Kapital-/Materiallauf gibt wie bereits P7 bestimmte Rezeptfreigaben ausdrücklich vor; er ersetzt keinen menschlichen Spielfluss mit organischem Research.

## 8. Getrennte Empfehlungen

Keine Änderung in P10. Für eine spätere ausdrücklich beauftragte Balancephase zunächst vergleichbare begrenzte Budgets, real freigeschaltete Firmen, zwei Startertrucks, zusätzliche Slots, Fuel und neue P8/P9-Vertragsquoten gegeneinander spielen. Maßgeblich sollten ausgezahlter Cash pro Zeit, gebundenes Gesamtkapital und MW sein. Besonders Crude Oil gegenüber Iron/Copper sowie späte Edelmetall-Direktverkäufe prüfen. Falls ungewollt, zuerst eine kleine Änderung an Erwerbs-/Ausbaukosten oder den nachgewiesenen Ausreißern untersuchen; keine pauschale Gleichsetzung aller 49 Preise. Keine automatische neue Marktwirtschaft, keine Preis-/Rezeptkorrektur als Nebenwirkung dieses Audits.

Vollständige Rohdaten: `artifacts/phase10/resource-price-audit.json`; Reproduktion: `.venv/Scripts/python.exe scripts/phase10_resource_audit.py`.
'''
(docs/'industriova-03-phase10-resource-price-audit.md').write_text(audit,encoding='utf8')
backup=Path((out/'backup-location.txt').read_text(encoding='utf8'));manifest=json.loads((backup/'manifest.json').read_text(encoding='utf8'))
old={e['path']:e['sha256'] for e in manifest['entries']}
changed=[]
for folder in ('src','tests','scripts','docs'):
 for path in (root/folder).rglob('*'):
  if not path.is_file() or '__pycache__' in path.parts:continue
  name=path.relative_to(root).as_posix()
  if hashlib.sha256(path.read_bytes()).hexdigest()!=old.get(name):changed.append(name)
report_name='docs/industriova-03-phase10-final-ui-polish-report.md'
changed=sorted(set(changed+[report_name]+[p.relative_to(root).as_posix() for p in (root/'scripts').glob('phase10_*.py')]));perf=[]
for name,values in after['results'].items():
 prior=before['results'][name]
 perf.append([name,f"{prior['median_ms']:.3f} / {prior['max_ms']:.3f}",f"{values['median_ms']:.3f} / {values['max_ms']:.3f}"])
for name,values in read('performance/after/inventory-matched.json').items():
 prior=read('performance/before/inventory-matched.json')[name]
 assert values['pool']==prior['pool'] and values['viewport']==prior['viewport']
 perf.append([name,f"{prior['median_ms']:.3f} / {prior['max_ms']:.3f}",f"{values['median_ms']:.3f} / {values['max_ms']:.3f}"])
performance=table(['Operation','P9 Median / Maximum ms','P10 Median / Maximum ms'],perf)
report=f'''# INDUSTRIOVA 0.3 – Phase P10: Final UI Consistency und Early-Game-Audit

Stand 23.10.2026. Ausgangspunkt ist der tatsächliche uncommittete/ungetrackte P9-Working-Tree mit 1.938 Tests. P10 ist implementiert und am finalen Quellstand geprüft. Kein neuer Windows-Build, keine Versionsanhebung, keine Events oder Tutorialmechanik.

## 1. Vorbereitung und Sicherung

Die acht beauftragten P0-/Roadmap-/P3-/P5-/P6-/P7-/P8-/P9-Berichte und die tatsächlichen Komponenten wurden geprüft. Neue unabhängige Sicherung `{backup.relative_to(root).as_posix()}`: 958 Quelldateien einschließlich ungetrackter und uncommitteter Inhalte, CRC-/SHA256-geprüft und als `before-tree` extrahiert. Fünf persönliche Saves frisch vor P10 roh und über SQLite read-only konsistent kopiert, integrity_check=ok; die aktuellen Originalhashes sind die Referenz, frühere Spielerfortschritte werden nicht gegen P9 zurückgesetzt. Die vollständige P9→P0-Sicherungskette bleibt gebunden. Originale werden weder geladen/migriert noch beschrieben. Die {protected['protected_build_files']} vorhandenen Build-Dateien sind einzeln unverändert. Wiederherstellung in einen neuen Ordner anhand Manifest/SHA256; niemals pauschal über aktuelle Saves extrahieren.

Die im Auftrag erwähnten zehn Nutzer-Screenshots waren in der Textanlage nicht vorhanden. Die konkrete Textspezifikation und tatsächliche Industriova-Komponenten waren die verfügbare Referenz. Ein Abgleich mit diesen fehlenden zehn Originalbildern wird nicht behauptet.

## 2. Tatsächlich geänderte Dateien

Alle produktiven Änderungen, angepassten bestehenden Tests und neuen P10-Werkzeuge/Dokumente relativ zum gesicherten tatsächlichen P9-Stand:

{chr(10).join('- `'+name+'`' for name in changed)}

`implementation.diff`, `final-source-sha256.json` und `delivery-manifest.json` binden den endgültigen Stand. Keine Änderungen an Datenkatalogen/Rezepten oder bestehenden Preisformeln. Alte Testidentitäten bleiben erhalten; Erwartungen an autorisiert entfernte Controls, neue Genesis und Centformatierung wurden auf den neuen Sollzustand aktualisiert. Diagnosevorläufe sind nicht die finale Regression. Ein bestehender Klicktest wartet nun vor seinem expliziten Scrollen auf die vorhandene verzögerte 0/50/150-ms-Wiederherstellung und nimmt den sichtbaren Slot; alle Gameplayassertions bleiben erhalten. Nach der letzten produktiven Float-/Cent-Korrektur wurden die vollständigen 97 Module und sämtliche elf DPI-Module nochmals frisch auf exakt dem endgültigen Quellstand gerechnet (`accepted-validation.json`). Frühere Teilläufe, Fehler und die zwischenzeitlichen 20er-Timingprüfungen bleiben nachvollziehbar erhalten, ersetzen diesen finalen Gesamtlauf aber nicht. Ein unverändert-logisches Dashboard wurde zuvor auf seine ursprünglichen Zeilenenden zurückgestellt; die endgültige Regression enthält bereits diese Originaldatei.

## 3. Wiederverwendete Komponenten

`IndustrialDialog`, `MaterialFrame`, `GameButton`, `RaisedPZButton`, vorhandene Accent-Paletten, industrielle Fonts, Kartenrenderer, ResourceSelectionTiles, virtuelle Supply-/Inventory-Pools, vorhandene Install-/Return-/Sell-/Route-Commands und persistente Communications. Gelb bestätigt, Rot bricht ab/verkauft, Blau setzt Routen zurück, Grau navigiert. Farbige Aktionsflächen behalten schwarze Beschriftung. Kein neues Iconset, Bitmapmaterial, Dropdown oder eigenes Handels-/Routensystem.

## 4. Rename-Stift und Dialog

`building_title_layout` berechnet sichtbaren Text und Stiftposition gemeinsam aus derselben tatsächlich gezeichneten Schrift über QFontMetricsF. Stiftabstand 8 logische Pixel, 32×32-Klickfläche. Resources/Factory/Energy verwenden dieselbe FactoryStage; Freight dieselbe gemeinsame Messung mit vorab reserviertem Statistikplatz. Lange Namen werden kontrolliert elidiert; vollständiger Name im Hover. Rechts gelegene Statistik-/Pause-/Guide-Controls überlagern den Stift nicht. Titelklick bleibt auf den tatsächlichen Titelbereich begrenzt, vorhandene Rename-Aktion bleibt erhalten.

Rename hat nur Name, Eingabefeld, gelbes YES–SAVE und rotes NO–CANCEL. Typselector, TYPE CHANGE, Investitionshinweis und Zusatzfläche sind entfernt. Der öffentliche RenameHall-Command lehnt jede mitgesendete Spezialisierung vollständig vor Mutation ab, auch dieselbe Spezialisierung. Alte Felder bleiben für Aufrufkompatibilität vorhanden, erlauben aber keine Spielerumklassifizierung. Historische Site-Spezialisierungen und interner kompatibler Legacy-Install-/Migrationspfad bleiben lesbar. Bau wählt den Typ weiterhin vor der Quote. P7-Preis-/Investmentfunktionen werden nicht neu berechnet.

## 5. Preise und Cent-Konsistenz

`resource_prices.price_number` nutzt Decimal aus der dezimalen Darstellung und ROUND_CEILING für positive Einzelpreise, exakt zwei Stellen einschließlich Nullen. Beispiele: 226.1625→226.17, 299.1375→299.14, 497.4→497.40 und 1.8125→1.82. Kleine positive Preise werden sichtbar 0.01; nichtendliche Eingaben sind abgelehnt. Große Beträge behalten exakten Geldtext, bei begrenzter Kachelbreite steht er im Hover. Bei Float-Eingaben werden höchstens zwei binäre ULP Abstand zu einem exakten Cent als Repräsentationsrauschen erkannt; beispielsweise 1.1×1.1 ergibt korrekt 1.21 statt 1.22. Echte gebrochene Cent und hochpräzise Decimal-Eingaben werden weiterhin strikt aufgerundet. Alle 353 Basispreis-Anzeigetexte sind vor/nach dieser Absicherung exakt gleich; `price-display-equivalence.json` belegt die Gültigkeit der endgültigen Bildaufnahmen.

Guide, Resource-/Global-Browser, Produktionspicker, Tooltips und bisherige Market-Einzelpreisfelder verwenden die zentrale Preisquelle; Supply-/Bau-/Slot-/Linienpreise zeigen ebenfalls zwei Dezimalstellen. Cash-Kontostände/XP/kompakte Rewardkennzahlen sind keine neu quotierten Einzelpreise. Intern bleiben alle 353 Festpreise unverändert und hochpräzise. Tooltip erklärt ausdrücklich die Cent-Aufrundung und die davon getrennte Abrechnung mit präzisem eingefrorenem Einzelpreis. Gesamtquotes von Käufen/Resale/Ausbau bleiben der tatsächlich gebuchte Centbetrag; es wurde keine ökonomische Rundungsregel ersetzt. Die vier konkreten Preisbeispiele sind in 24 zusätzlichen echten Guide-Aufnahmen und Breitenassertions belegt.

## 6. Rohstoff-Audit

Separater Bericht `industriova-03-phase10-resource-price-audit.md`: 49 Primärrohstoffe, 353 rekursive Kettenkennzahlen, 76 echte Engine-Strategien, MK1/10/99 und Legendary-Vergleiche. Copper bietet bei gleicher nomineller Leistung +40 % gegenüber Iron, Crude Oil +120 %. Freight begrenzt alle verglichenen Einzeltrucks; höherer Preis bleibt trotzdem ein relativer Direktverkaufsvorteil. Downstream-Bedarf schafft weitere Verwendungen, ist kein automatisch bewiesener finanzieller Ausgleich. Das separate Dokument trennt tatsächliche Cash-Buchungen, nominale Raten, Opportunitätsmathematik, Freischaltungen und unbelegte globale Optimierungsannahmen. Keine Balanceänderung in P10.

## 7. Kompakter Freight-Header

Hauptzeile: Gebäudetitel+Stift links; zusammenhängend SELL/CONTRACT/CONSORTIUM/TOTAL rechts; Pause ganz rechts im vorhandenen Overview-Rahmen. Stagehöhe 188→64 logische Pixel, Overview-Abstände reduziert. Slotzahl, aktive Sendungen und Messfenster sind im Hover, keine zusätzlichen sichtbaren Statistikzeilen. Die vier Properties und tatsächlichen P6-Raten bleiben facility-spezifisch und verwenden unverändert das 60-Sekunden-Fenster. Warm-up zeigt kompakte 0/min; der genaue Mess-/Nullzustand steht im Hover. Große Raten werden kompakt, vollständige Zahlen und Beobachtungsfenster im Hover ausgegeben. Statistikgruppe reserviert Platz vor der Titel-Elision.

## 8. Inventory und konkrete Auswahl

Available-/Stacks-/In-Use-Zähler, Select All/Clear-Buttons, permanente Selected-/Sale-Texte, Quantityleiste, Install/Reset/Sell-Fußleiste sind entfernt. Vorhandener Header, Karten und Kategorieauswahl bleiben. Normaler Klick wählt eine konkrete erste Stapel-ID, Ctrl ergänzt/toggelt Stapel, Shift erweitert den Bereich. Ctrl+A erhält die gesamte Auswahlfunktion ohne Toolbar. Rechtsklick auf eine bereits ausgewählte Karte erhält die gültige Mehrfachauswahl.

SELECT QUANTITY öffnet einen kompakten vorhandenen Industriova-Dialog ohne irreführenden Kaufpreis. Die Reihenfolge konkreter IDs steht im Hover, Menge entspricht genau den ersten N IDs des gewählten Stapels, andere ausgewählte Stapel bleiben erhalten. Kartenhover nennt gewählte/verfügbare Menge und gespeicherte Freight-Route einschließlich Invalidzustand. Keine Kartenkapazitätsgrenze, keine neue Eigentumstabelle. Virtuelle Darstellung bleibt begrenzt.

## 9. Kontextaktionen und Atomarität

INSTALL, SELL und bei Freight RESET ROUTE sind über echte Kontextklicks erreichbar. Installation verwendet denselben Facility-/Slotdialog und die bestehenden InstallCardInHall/InstallFreightCard-Regeln. Für Mehrfachauswahl werden passende freie Plätze geplant, der erste Platz wird ausgewählt, weitere zuerst in derselben Facility, sonst kompatibel verteilt. `InstallInventoryCards` validiert die gesamte Gruppe mit denselben Commands auf einer isolierten Zustandskopie, bevor der synchrone CommandBus die vorbereiteten Installationen übernimmt. Keine alternative Installationsdomäne. Das Kopieren kostet bei großen Gruppen zusätzlich Zeit und ist kein periodischer Refreshpfad.

SELL zeigt Anzahl, Maschinennamen und Gesamterlös, gelbes YES–SELL und rotes Cancel. Nach Bestätigung werden Session, Existenz, Available-Status und unveränderter Erlös erneut geprüft; bestehendes SellMachines erhält die 80-%-Investitionsregel und Gruppenatomarität. Zweiter Verkauf derselben IDs ist unmöglich. RESET ROUTE verwendet den bestehenden P3-Command und schützt Session/aktive Sendungen. Bestehende Kauf→Install→Return→Reinstall→Sell-Tests bleiben erhalten; neue Fälle klicken die tatsächlichen Kontextaktionen.

## 10. Storage Expand

Der kleine Headerbutton öffnet STORAGE EXPANSION mit tatsächlichem Zuwachs, aktuellem/neuem Global Storage und zentraler Quote. Beispiel Level0: +18,820 U, 75,280→94,100 U, $250.00. Cancel ist mutierungsfrei. ExpandInventoryStorage hat optionale erwartete Stufe/Quote; Wiederholung derselben bestätigten Quote wird vor einer weiteren Abbuchung abgelehnt. Neue Session verwirft alten Dialogintent. Bestehende Aufrufer ohne erwartete Quote bleiben kompatibel. Keine neue Kostenformel oder SessionWriter-/Schemaänderung.

## 11. History/Inbox

Die vorhandenen umgehängten RaisedPZButtons nutzen die Operationsfläche mit mindestens 42 Pixel Höhe und gut lesbarer vorhandener Schrift. Normal Grau, neue persistente Unread-Nachricht gelbe vorhandene Primary-Fläche mit schwarzer Schrift. Ein auf den bestehenden Feed begrenzter 1.2-s-Timer variiert nur dezent den Hoverhelligkeitszustand dieses Buttons. Kein Header-/MainWindow-Neuaufbau pro Phase, keine zweite Unread-Verwaltung. Lesen setzt den persistierten bestehenden Mark-read-Zustand, beendet den Timer und stellt Grau her; Hide/Close stoppt den Timer, Show liest den echten Unreadzustand erneut. Save/Load/New Game und History-/Tickerbestand sind regressionsgeprüft.

## 12. Industrial Supply

Kanonische 15 Common-Maschinenangebote umfassen drei Rohstoffmaschinen, drei verschiedene Fabrikstufen, fünf Energiearten und vier Freightfamilien. Direkte Auswahl: **ALL, RESOURCES, ENERGY, PROCESSING, FABRICATION, ASSEMBLY, FREIGHT**. ALL ist Standard. Die sieben Buttons decken zusammen sämtliche 15 IDs ab; kein Assembler wird in einer undurchsichtigen Factory-Gruppe versteckt. CATEGORY nutzt die vorhandene schwere industrielle Schrift. Bei regulärer Breite eine Zeile, bei kleineren Flächen Umbruch. Keine Suche und kein sichtbarer Kategorie-Dropdown/Flyout.

Daily/Common, beide täglichen Angebotsfamilien, Mengen/MAX, kaufabhängige Zustände und Erwerb ins Inventory bleiben erhalten. Derselbe virtuelle Common-Pool wird wiederverwendet. ALL darf beim kleinen heutigen 15er-Katalog alle 15 Karten materialisieren; das ist keine abgeschaltete Virtualisierung. Vorherige strikt-kleiner-als-Katalog-Assertions wurden auf die korrekte obere Grenze angepasst, eindeutige IDs/keine Duplikate und recycelte Bindungen bleiben geprüft.

## 13. Drei kostenlose erste Sites

Nur `_create_initial_state` ergänzt Drilling Field 1 und Agricultural Estate 1 zum bisherigen Mining Complex 1. Je eine freie Linie/ein freier Slot und festgelegte Spezialisierung. Genesis behält $1,250.00, acht unplatzierte Starterkarten, vorhandene Rohwaren, XP/RP/Research und Energy-Voraussetzungen. Kein zusätzlicher Gratisproduzent. Zweite Site jedes Typs wird korrekt als zweiter Standort quotiert ($4,000.00); erste zusätzliche Slots nach P7. Laden alter Saves ruft Genesis nicht auf, es gibt keinen doppelten kostenlosen Effekt. Der vorhandene finite Starttest nutzt nun die bereits vorhandenen Erststandorte und besteht mit realen Maschinen-/Solar-/Transportkäufen.

## 14. Freight-Ressource und Delivery Target

Die bestehende Ressourcenauswahl zeigt SELECT A RESOURCE, Browser und Cancel. Große Prozessüberschrift, zusätzliche Fahrzeugtitelzeile und zweiter großflächiger Zielscreen sind entfernt. Ressourcenwahl öffnet unmittelbar den kleinen modal geführten IndustrialDialog SELECT DELIVERY TARGET. MARKET/SELL, CONTRACT, CONSORTIUM CONTRACT und EVENT stehen nebeneinander; schmalere Dialoge verwenden zwei Spalten. Bestehende neutrale Auswahlflächen, gelbe Auswahl/CONFIRM, rotes CANCEL; keine großen Warenkarten und kein Dropdown.

Verfügbarkeit stammt aus dem bestehenden `target_problem`/`validate_route`. Nicht benötigte/abgelaufene persönliche Contracts, fehlende Mitgliedschaft/Consortium-Ziele und Event bleiben sichtbar deaktiviert mit Grund im Hover. Normale Route setzt keinen neuen Versand in Gang, solange nicht bestätigt. Auswahl und Bestätigung nutzen unverändert AssignFreightVehicles mit Sessionidentität, vollständigen konkreten IDs, Ursprungs-Snapshot und erneuter Waren-/Zielprüfung.

## 15. Rückkehr, Session und Save

Erfolg schließt Dialog und zeigt das vorhandene gecachte Board; nur betroffene Karten/KPIs werden aktualisiert, kein unnötiger MainWindow-Rebuild. Cancel/Esc im Zieldialog führt zur unveränderten Ressourcenwahl; Cancel im Ressourcenbrowser zurück zum Board. Haupttabwechsel, View-Hide, Load/New Game/Reset verwerfen Dialoge und alte IDs. Doppelte Confirm-Geste kann den abgeschlossenen Intent nicht erneut anwenden. Bestehende aktive Sendungen behalten Cargo-/Preis-/Zielsnapshots. P4-Auswahl, Busy-/MK-/Routenregeln, P9-Freight-only und P6-Buchungen bleiben erhalten.

Schema **9** unverändert. Alle **16/16** historischen Migrationen liefern vollständig SHA256-identische normalisierte Payloads zum akzeptierten Vorzustand und sind idempotent. Kein neues persistentes UI-Register, Save-/SessionWriter unverändert. Nach Abschluss {protected['original_saves']} persönliche Originale und {protected['protected_build_files']} Build-Dateien unverändert.

## 16. Performance

{after['assumptions']}

{performance}

Inventorypool-Geometrie P9→P10: {before['inventory']} → {after['inventory']}. Serialisiertes 500er-Payload: {before['payload_bytes']:,}→{after['payload_bytes']:,} Bytes. Gleiche Messfixture mit einer Site für beide Quellen; die autorisierte Genesis-Erweiterung wird separat geprüft. Der komplette Supply-Kategoriezyklus umfasst P10 sieben statt P9 vier Kategorien und ist daher ausdrücklich mehr Arbeit; die drei gemeinsamen Kategorien sind zusätzlich identisch gemessen. Durch entfernte Toolbars zeigt das gleich große Inventoryfenster mehr Karten: Pool 30→36. Vollflächen-Refresh/Scroll haben damit mehr echte Zeichenarbeit. Die zusätzlich ausgewiesenen matched-Werte begrenzen ausschließlich die sichtbare Scrollhöhe in beiden Quellen identisch auf 400 Pixel; Kartenanzahlen 500/5.000/10.000 bleiben unverändert, ebenso konkreter Karteninhalt und Breite. Diese Probe trennt die Layoutdichte von den Kosten derselben sichtbaren Datenmenge. Größere Maxima und einzelne kalte Zustandswechsel sind kein Nachweis konstanter nativer FPS. Rohwerte stehen im Performanceordner.

## 17. Tests

Final **{summary['regression_tests']:,} Tests / {summary['modules']} Module**, 0 Fehler/Skips, alle **{summary['old_test_identities_retained']:,}** bisherigen Testidentitäten erhalten, **{summary['new_test_identities']}** zusätzliche Fälle. Zusätzlich **{summary['dpi2_tests']} Fälle / {summary['dpi2_modules']} vollständige relevante Module bei 200 %**. `regression-summary.json` prüft die Multimenge der XML-Testidentitäten gegen final P9, nicht bloß eine behauptete Gesamtzahl.

Neue Fälle betreffen sichere Cent-Aufrundung/Extremwerte, drei kostenlose Sites und unveränderte Altloads, Rename-only und atomare Umklassifizierungssperre, erwartete Storagequote/Doppelbestätigung/Sessionwechsel, ganze Installgruppen, wirkliche Kontextklicks einschließlich Menge/Reset, mehrfache Stapel, veraltete Salequotes/Installation während Dialog, dynamische Stifte, alle Kategorien, persistente Inbox, Freight-Zielverfügbarkeit und Cancel/Esc/Tab/Reset. Bestehende umfassende Busy-/aktiven Sendungs-/Contract-/Consortium-/Load-/New-Game-/Drag- und Roundtriptests sind erhalten und erneut ausgeführt. Zusätzlich läuft bei 100 und 200 % jeweils ein vollständig durch tatsächliche Zeigerklicks geführter Pfad: Supply-Kaufbutton → Inventory-Rechtsklick INSTALL → Facility-Bestätigung → Board-Rechtsklick RETURN TO INVENTORY → erneute Kontextinstallation → Rücknahme → Inventory-Rechtsklick SELL und gelbe Bestätigung. Dieselbe Karten-ID/Instanz bleibt bis zum Verkauf erhalten, alle acht Starter-IDs bleiben vorhanden; $275.00 Kauf und $220.00 Resale werden exakt gebucht. Die beiden zusätzlichen Ablaufbelege stehen unter `click-roundtrip-dpi1/result.json` und `click-roundtrip-dpi2/result.json` und sind nicht doppelt als pytest-Fälle gezählt.

## 18. Visuelle Vorher-/Nachher-Prüfung

**{summary['captured_images']} tatsächliche PNG-Aufnahmen**: 150 P9-Vorherbilder, 162 P10-MainWindow-/Dialogbilder sowie 24 zusätzliche Guide-Preisbeispiele und sechs gefüllte Global-Resources-Ansichten. Je 1366×768,1600×980,1920×1080 bei Qt100/200 %. Alle tatsächlichen Pixelmaße, DPR-Zuordnung und SHA256 geprüft. Separate Dialog-/Inboxfenster werden als eigene reale Qt-Surfaces aufgenommen, nicht in MainWindow-Pixel hineinmontiert. Die logischen Fenstermaße bleiben die genannten Auflösungen, die PNG-Pixel bei 200 % jeweils doppelt; das wird nicht als Test eines 683-Pixel-Fensters ausgegeben.

Separater finaler Sichtungspass: **{len(visual['files'])} konkrete Bilder tatsächlich betrachtet**, alle sechs Größen-/DPI-Profile vertreten. Dateiliste/Hashes/Befunde in `visual-review.json`. Gefunden und vor finalen Captures behoben: abgeschnittene Zieldialogoptionen durch unzureichende Dialogbreite, zu kleine per Theme überschriebene CATEGORY-Schrift sowie verdeckter erster Buy-Footer durch unnötige zweite Kategoriezeile. Finale Bilder zeigen kompakte Dialoge, lesbare Preise, direkt anschließende Stifte und erhaltene Industriova-Materialien. Kein Anspruch, alle 342 Bilder einzeln visuell abgenommen zu haben.

Beispiele: `screenshots/after/dpi1/supply-default-1366x768.png`, `screenshots/after/dpi1/inventory-filled-1366x768.png`, `screenshots/after/dpi2/delivery-target-confirm-1366x768.png`, `price-screenshots/dpi2/ai_accelerator-1366x768.png` unter `artifacts/phase10`.

## 19. Native Windows-Handabnahme

Offen bleibt die persönliche Windows-Maus-/DWM-/GPU-Abnahme mit Mehrmonitor-/DPI-Wechsel, subjektivem Hover-/Scrollgefühl, langen Sessions und tatsächlich physisch kleinen HiDPI-Arbeitsflächen. Offscreen/QTest/PNG-Sichtung sind keine menschliche Freigabe. Insbesondere echte Rechtsklick-Mengenwahl, mehrere gemischte Installziele, pulsierende Inbox und Routenwechsel bei laufenden Sendungen im Playtest prüfen.

## 20. Grenzen und Stopp

Der Kettenaudit ist keine globale Gewinnoptimierung aller Firmen und 76 synthetische Rohstoffläufe sind keine organisch gespielten Strategien. Höherpreisige Direktverkaufsrohstoffe bleiben ein separater Balancepunkt; keine stillschweigende Preisänderung. Gruppeninstallation kopiert den Zustand für vollständige Vorprüfung und kann bei sehr großen Gruppen zusätzlichen Aufwand verursachen. Sehr große Resource-/Freightboards bleiben wie zuvor nicht kostenlos; gemessene Maxima bleiben im Rohbericht. Die zehn im Prompt referenzierten Original-Screenshots fehlen weiterhin.

Nach P10 gestoppt. Kein Windows-Build, keine Events, kein Tutorial, keine neue Marktmechanik, keine zusätzlichen Consortium-Systeme. Persönliche Saves/Builds unverändert. Start aus aktuellem Quellstand weiterhin `.venv/Scripts/python.exe -m production_zero.app`; sichtbare Versionskennung bleibt absichtlich 0.2.0.dev6.
'''
(docs/'industriova-03-phase10-final-ui-polish-report.md').write_text(report,encoding='utf8')
print('WROTE BOTH REPORTS',len(report),len(audit),flush=True)
