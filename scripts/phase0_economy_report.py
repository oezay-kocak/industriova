"""Render measured economic data into the Phase 0 report (no gameplay edits)."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase0'
model=json.loads((OUT/'economy-model.json').read_text());front=json.loads((OUT/'economy-frontier.json').read_text())
sim=json.loads((OUT/'chain-simulation.json').read_text());recipe=json.loads((OUT/'recipe-mk-audit.json').read_text())
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |',*['| '+' | '.join(map(str,row))+' |' for row in rows]])
def num(v):return f'{v:,.2f}'
parts=['''# INDUSTRIOVA 0.3 – Wirtschafts-, Kosten- und Contract-Audit

Stand: 21.10.2026, gesicherter Working Tree 0.2.0.dev6. Sämtliche Vorschläge sind **nur berechnet**, nicht in Produktivdaten geschrieben. 353 Ressourcen/Produkte, Rezeptverhältnisse, feste Basispreise, Rarity und `M(m)=1+0,25(m−1)` für MK1–99 bleiben Grundlage. MK99 = 25,5×, nicht 99×.

## 1. Reproduzierbare Grundlage

Aufrufe aus dem Projektordner mit `.venv/Scripts/python.exe`: `scripts/phase0_benchmark.py economy`, danach `scripts/phase0_chain_simulation.py`, `scripts/phase0_economy_frontier.py`, `scripts/phase0_economy_report.py`. JSON unter `artifacts/phase0`: `economy-model.json`, `chain-simulation.json`, `economy-frontier.json`, `recipe-mk-audit.json`. Kein persönlicher Save wird geladen. Die Engine-Simulationen sind synthetische versorgte Firmen, kein erspielter Start-bis-Endgame-Verlauf. Ihre Walltime wurde unter gleichzeitig laufender Regression gemessen und ist **kein Performancebenchmark**.

Der vorhandene `release_economy_audit.py` wurde mit ausschließlich umgeleitetem Ausgabepfad wiederverwendet: 304 weiterverarbeitende Rezepte, **keine negative Modellmarge**, 20 kontinuierliche Infrastruktur-/MK-Szenarien und vollständige MK-Kostenreihen. Dieses Margenmodell enthält Input-Opportunitätswert, Kohleäquivalent für Energie, 10-Stunden-Kapitalanteil und 2 % Transportpauschale. Es beweist keine tatsächliche Auslastung, Transportfinanzierung oder Startkapital-Erreichbarkeit. Der alte `tools/contract_balance_audit.py` importiert hingegen eine im aktuellen Contractmodul nicht mehr existierende XP-Konstante; er ist für dev6 keine belastbare Quelle und wurde nicht als Ergebnis ausgegeben.

## 2. Istkosten: Ausbau konkurriert mit billigen Neubauten

`core/economy.py`: `B(n)=1000·(1+max(0,n−1))^2,5`, n = vorhandene Gebäude **im gesamten Board**. Bei Resources wird momentan nicht nach Mining/Drilling/Agriculture getrennt. n=0 und n=1 liefern beide 1.000; danach 5.656,85 / 15.588,46 / 32.000. UI und Backend verwenden diese Funktion, bei der Resources-Auswahl ist die Spezialisierung teilweise erst nach dem Kauf gesetzt.

`core/state.py`: Linie l kostet `750+500·max(0,l−3)`; Zusatzslot k in Linie l kostet `120+90·(k−s−1)+35·(l−1)`, s = Anfangsslots pro Linie. Linienkosten sind im Save hinterlegt. Neue Factory startet heute mit zwei Linien à drei Slots; Resources/Energy jeweils eine Linie mit einem Slot.
''']
parts.append(table(['Board','Startkapazität','Maximum','Linienkosten zusätzlich','Kompletter Ausbau zusätzlich','Zweite Facility'],[
    [r['board'],f"{r['start_lines']}×{r['start_slots']}",f"{r['lines']}×{r['slots_per_line']}",', '.join(map(num,r['line_costs'])),num(r['full_expansion']),num(r['next_building'])] for r in model['buildings']]))
parts.append('''
Die ersten vorhandenen Gebäude sind Startausstattung ohne Kaufdebit. Für eine hypothetisch bezahlte erste Facility bei n=0 kommen zu den Ausbauzahlen 1.000 hinzu. Die eigentlichen Maschinen/Energie-/Transportkosten sind in dieser Tabelle noch nicht enthalten.

Factory-Beispiel: Die letzten drei Slots einer bestehenden Linie 1 kosten zusammen 1.710; eine zweite Hall kostet 1.000 und liefert **sechs** Plätze. Auch der Vergleich vollständiger Ausbau 19.850 für 44 zusätzliche Plätze gegen eine neue Halle mit sechs Plätzen erklärt den Neubauanreiz. Bei Energy kostet Linie 1 Slot 5 bereits 390, Linie 3 mit einem Startslot 750, während ein neues Kraftwerksgebäude mit erstem Slot 1.000 kostet. Ein bloß pauschal höherer Slotpreis würde diesen Anreiz verschärfen.

## 3. Factory/Energy: reale Leistung und Kapital

Beispiel Processor → Iron, Common, keine Forschung: 60 Iron/min, 8 MW und 105 Cash/min Marge nach Input-Opportunitätswert, **vor** Energie/Kapital/Transport. Solar: 20 MW, Preis 180. Processor: 275. Alle Raten skalieren bei gleicher Rarity mit M; für 50 Processors werden immer 20 Solar derselben MK-Stufe benötigt. Eine voll ausgebaute Energy-Facility fasst 15 Solar, daher sind zwei bestehende Plants nötig. Keine Brennstoffkosten bei Solar; Fläche/Kapital bleibt ein realer Aufwand.
''')
parts.append(table(['MK','50 Processor Iron/min','MW Bedarf','15 Solar MW','Processorflotte inkl. bezahltem MK','15 Solar inkl. bezahltem MK'],[
    [mk,num(next(r for r in front['full_facility_examples'] if r['definition']=='machine.processor' and r['mk']==mk)['output_iron_per_minute']),
     num(next(r for r in front['full_facility_examples'] if r['definition']=='machine.processor' and r['mk']==mk)['power_mw']),
     num(next(r for r in front['full_facility_examples'] if r['definition']=='energy.solar_array' and r['mk']==mk)['power_mw']),
     num(next(r for r in front['full_facility_examples'] if r['definition']=='machine.processor' and r['mk']==mk)['fleet_capital']),
     num(next(r for r in front['full_facility_examples'] if r['definition']=='energy.solar_array' and r['mk']==mk)['fleet_capital'])] for mk in (1,2,10,50,99)]))
parts.append('''
MK-Flottenkapital summiert exakt `mk_upgrade_cost` für jede Stufe; Qualitätsgewinne werden im Vergleich bewusst ausgeschaltet. Kostenformel: Maximum aus `Commonpreis·MK^1,7` und `0,25·Familien-Maximalgewinn/s·900·((MK+1)/2)^2,3`, auf Cent aufrunden. Der Familien-Maximalgewinn berücksichtigt alle Rezepte, nicht nur Iron. Deshalb sind hohe MK bei einem frühen Rezept nicht aus dessen kurzer Maschinenamortisation ableitbar. Die Stufen bleiben unverändert.

MK1-Kosten eines bestückten ersten Factory-Gebäudes: 19.850 Ausbau + 13.750 Processors = **33.600**, ohne Energie, Inputs, Resources und Freight. Energie-Zusatz bei Nutzung der kostenlosen Start-Plant: erste Plant bis 15 Solar ausbauen (4.980), zweite Plant kaufen (1.000), deren erste Linie von einem auf fünf Plätze erweitern (1.020), 20 Solar kaufen (3.600): **10.600**. Zusammen **44.200**. Bei nur Iron beträgt die rechnerische Amortisation nach Inputwert und vor Logistik 44.200 / 5.250 = **8,42 min**. Das ist ein konditionales Modell, kein erreichbarer Cashflow ohne passende Erzversorgung, Lager und Auslieferung.

Für eine weitere volle Energy-Facility bei heutigem erstem Neukauf: 1.000 Bau + 4.980 Ausbau + 2.700 Solar = **8.680**, 300 MW bei MK1. Bestehende Startplant entsprechend 7.680. Reiner Energiepreis/MW ohne verkäufliches Energieprodukt liefert keine eigene Geldamortisation; sinnvoll ist vermiedener Stromengpass bzw. zusätzlicher Kettengewinn, nicht ein erfundener Stromverkauf.

Geschlossene Iron-Kette für 3.000/min: mindestens 50 Processors + 50 Extractors (je 120 Erz/min, zusammen 6.000 Erz/min) + 700 MW Gesamtbedarf, also 35 MK1-Solar. Drei Plants fassen diese 35; erforderliche Resource-Slots und voll beladene Freight-Kapazität kommen hinzu. Bei 50 Processors kostet die erste Hall unter dem Vorschlag unten 389.025 statt 19.850 Ausbau. Die 20-Solar-Teilversorgung dafür kostet unter denselben Vorschlagsformeln 41.060 statt 10.600; zusammen mit Processors also **443.835**, Amortisationsuntergrenze **84,54 min** vor Erz-/Freightkapital. Das ist eine sehr große Verschiebung und muss als Kandidat gespielt werden, keine stillschweigende Freigabe.

Allgemein: `Qverkauf = min(QKette, QFreight, QLager_abfluss)`. `π/min = Qverkauf·P − ΣInput_opportunität − Brennstoff − sonstige laufende Kosten`. Bei einer vollständig eigenen Kette externe Inputkosten durch tatsächliche Primär-/Energie-/Transportkosten ersetzen; interne Zwischenprodukte nicht nochmals als externe Kosten abziehen. `Amortisation = ΔInvestition / Δπ`, nur für Δπ>0. Für Puffer mindestens Spitzeninputs pro Zyklus plus Transit-/Outputbuffer berücksichtigen. Ein MK-Ausbau ohne zusätzlichen Absatz/Inputs kann Δπ=0 haben.

## 4. Freight: Istzustand und Schiffe

Common MK1, keine Forschung, stets Vollbeladung; `Q=60·Kapazität/Fahrzeit`. Die letzten zwei Spalten beziehen sich auf **nur das Fahrzeug**, nicht Facility, Expansion oder die finanzierte Ware; Iron Ore hat Basiseinzelpreis 1.
''')
parts.append(table(['Typ','Kapazität','Sekunden','Einheiten/min','Fahrzeugpreis','Erste gekaufte Facility','Cash je zusätzliches E/min','Bruttoamortisation Erz/min'],[
    [r['definition'],num(r['capacity']),num(r['seconds']),num(r['per_minute']),num(r['price']),num(r['facility']),num(r['cash_per_added_unit_minute']),num(r['ore_gross_payback_minutes'])] for r in model['freight']]))
parts.append('''
Facilitykosten sind bereits nach **gleichem Freight-Typ** quadratisch: `Base_typ·(1+n_typ)^2`. Basis Garage 500, Rail 1.500, Air 3.500, Sea 2.500. Die erste Garage ist kostenlos vorhanden; eine zweite kostet 2.000. Ausbauten kosten `300·e²` pro zusätzlichem Slot (e=1,2,…), ohne wirksames Drei-Ausbau-Limit; die alten Max-/Stepkonstanten beschreiben nicht den aktiven Pfad. Neue Facility: Garage 3 Startslots, sonst 2. Die aktive `line_capacity` ist **8**: eine Linie mit 8 Positionen, nicht 3/2 Fahrzeuge pro Linie. Das ältere Unified-UX-Dokument beschreibt hier einen überholten Stand. Eine weitere Freight-Linie kauft ihren ersten Slot auf derselben Slotkurve, ohne neue Gebührenart.

Garage von 3 auf 8 Slots kostet 300+1.200+2.700+4.800+7.500 = 16.500. Acht Trucks kosten 1.640; zusammen **18.140** für 320/min. Zwei Züge mit neuem Rail Depot kosten 2.800 für 400/min. Zwei Flugzeuge einschließlich Air Terminal kosten 13.470 für 2.666,67/min. Das ist ein konkreter Anreiz, Garage nicht weitgehend auszubauen und Train möglicherweise direkt zu überspringen.

Schiff derzeit / Flugzeug: Preis 48.200 / 4.985 = **9,669×**, Durchsatz 10.000 / 1.333,33 = **7,5×**. Ziel bei gleichen MK/Rarity/Research: Schiffpreis **14.955** (=3×4.985); bei unveränderten 240 Sekunden Fahrzeit Kapazität **16.000** (=3·4.000·240/180), also **4.000/min**. Preis −68,97 %, Kapazität/Durchsatz −60 %. Flugzeug/Truck/Train-Fahrzeugwerte bleiben unverändert.

Nur die Kapazität in `release_balance.py` zu ändern reicht nicht: `common_card_price` würde dann 19.400 verlangen, nicht 14.955. Für Freight eine explizite Supply-Preisoption analog der vorhandenen Energy-Option im bestehenden Preispfad vorsehen, oder einen klar dokumentierten Ship-Quotezweig; keine zweite Shoplogik. Daily-Uncommon, Templates, MK-Mindestkosten und **neue** Käufe müssen denselben Preis sehen. Bestehende `acquisition_cost`/Upgradeinvestition und unterwegs eingefrorene Kapazität/Zeit nicht neu berechnen. Auch geänderter Basisdurchsatz beeinflusst `base_net_profit_per_second` und damit künftige Ship-MK-Kosten; als Folgeänderung prüfen.

## 5. Konkrete Kostenformeln als prüfbarer Vorschlag

Alle neuen Produktionsfacilities beginnen mit **einer** nutzbaren Linie. Startplätze: Factory 3, Resources/Energy 1. Maxima 5×10 / 3×10 / 3×5 erhalten.

Zusatzslot k, s Anfangsplätze: `S(k)=5·ceil(120·(k−s)^1,35 / 5)`. Kein pauschaler Boardgebäudezähler im Slotpreis. Neue Linie l≥2: `L_b(l)=A_b·(l−1)^2`, A Factory=12.000, Resources=15.000, Energy=3.000. Diese Kandidaten erfüllen `L(2)+ΣS > maximale Slotkosten·Plätze_pro_Linie`; vollständiges Erschließen einer neuen Linie wird dadurch nicht billiger pro Platz als der teuerste Platz einer vorhandenen Linie.

Facility für n bereits vorhandene dieses Typs: n=0 günstiger Erstzugang (Resources je Mining/Drilling/Agriculture **500**, Factory/Energy 1.000, kostenlose Startausstattung gesondert erhalten); für n≥1 `B_b(n)=B2_b·n^2,5`. Resources zählt n **pro Spezialisierung**, nicht pauschal alle Sites.

B2 aus einer vergleichbaren fertig erweiterten neuen ersten Linie ableiten: `B2 = auf100_aufrunden(max(1,25·CletzteLinie·Startplätze/Maxplätze, 1,25·CletzteLinie − Slotausbau_ersteLinie))`. So ist auch ein Neubau mit anschließend billig ausgebauter erster Linie teurer als die teuerste verbleibende Linie des bestehenden Gebäudes. Nur Startplätze zu vergleichen hätte einen Neubau-Exploit über deren günstige Slotkurve offengelassen.
''')
parts.append(table(['Board','Slotpreise je Linie','Neue Linien','Voller Ausbau erste Facility','Zweite Facility B2'],[
    [r['board'],', '.join(map(str,r['slot_prices_per_line'])),', '.join(map(str,r['line_prices'])),num(r['full_first_expansion']),num(r['proposed_second_facility'])] for r in front['production']]))
parts.append('''
Diese Werte sind ein **starker, mathematisch konsistenter Kandidat**, keine bereits abgestimmten Endpreise. Gesamtkapital jeder vollständigen Kette einschließlich Primär-, Energie-, MK-, Speicher- und Freightinvestment muss vor Übernahme in P7 erneut mit den vorgeschlagenen Formeln durchgerechnet werden. Die oben gezeigte rund zehnfache Factory-Amortisationsverschiebung ist ausdrücklich eine offene Designentscheidung. Die Formelbedingungen bleiben brauchbar, auch wenn die Konstanten nach Playtest gesenkt werden.

Typwahl vor Quote/Commit nötig: derzeit kann ein leerer Resources-Standort beim Rename kostenlos umklassifiziert werden. Mit verschiedenen Erst-/Zweitstandortkosten kann das die gewählte Preiskurve umgehen. Anzahl vorhandener Standorte bleibt gemäß Auftrag maßgeblich; eine bezahlte Umklassifizierung mit erneutem Quotevergleich oder eine klar definierte Typbindung ist vor P7 zu entscheiden. Keine heimliche Umstellung auf einen Lebenszeit-Erwerbszähler. Verkäufe erstatten weiterhin historische Investitionen, nicht neue Ersatzpreise.

Freight-Kandidat für Facilitybasis: Garage 500, Rail **30.000**, Air **180.000**, Sea **250.000**, je Typ weiter `(1+n)^2`; heutige Slotkurve zunächst beibehalten. Nur Ship-Fahrzeugwerte wie oben anpassen. Vergleich einer eigenen Facility mit 1–24 Fahrzeugen, voller Beladung, erste Garage als Startbestand, keine MK/Forschung. Für jeden Budgetpunkt wird die höchste leistbare Kapazität gesucht; unterschiedliche Facilities kombiniert, Teilbeladung, mehrere gleiche Facilities und Inputs sind noch nicht optimiert.
''')
def best_label(r):
    b=r['best_single_facility'];return f"{b['type']} ×{b['vehicles']}, {num(b['units_per_minute'])}/min, Kosten {num(b['cash'])}" if b else 'keine'
parts.append(table(['Budget','Heute: beste einzelne Facility','Kandidat: beste einzelne Facility'],[
    [num(budget),best_label(next(r for r in front['freight_frontier'] if not r['proposal'] and r['budget']==budget)),best_label(next(r for r in front['freight_frontier'] if r['proposal'] and r['budget']==budget))] for budget in (1000,3000,10000,20000,50000,100000,200000,300000,500000,1000000)]))
parts.append('''
Die Kurve prüft Anreize, erzwingt keine Kaufreihenfolge. Größerer Kapitaleinsatz und besserer langfristiger Durchsatz sind verschiedene Größen. Insbesondere macht eine preiswertere 3×-Ship-Instanz zusätzliche Airports wirtschaftlich angreifbar. Eine garantierte optimale Truck→Train→Air→Sea-Folge für jeden frei gewählten Warenmix wird aus dieser eingeschränkten Kurve nicht behauptet. Vor endgültigen Basen Mischflotten, Zweitgebäude, MK-Alternativen, tatsächliche Auslastung und vollständige Kapitalamortisation einbeziehen; keine künstlichen Freischaltsperren.

## 6. Contracts: aktive Berechnung statt toter Konstanten

`contract_capacity_estimate` summiert Produktionswert/min der konfigurierten installierten Maschinen, inklusive MK/Rarity. Es prüft dabei weder effektive Pause noch Input-/Energieversorgung noch Freight. Zwischenprodukt- und Endproduktleistung werden beide addiert. Der Schätzer ist daher **nominelle** Leistung und kann eine vollständig ausgelastete Kette oder ungeeignete Konfiguration überschätzen.

Budget: `Keff^0,88 · Zielminuten · Faktor`, begrenzt durch `Keff · Kapazitätscap`, anschließend gerundet. Medium-Zielminuten Daily 45, Weekly 160; Faktoren 1,25 / 1,65, Caps 110 / 520. Eine manuelle Auswahl muss 3 / 4 verschiedene verfügbare Produkte haben. Mengen werden aus Budget / Produktanzahl / rekursivem Produktionswert berechnet und stufenweise gerundet, mindestens 1. Bei teuren Endprodukten kann diese Ganzzahluntergrenze den Sollaufwand merklich erhöhen.

Die konstanten nominellen Cash/PV-Werte 180/220 erzeugen die anfängliche Offerquote. **Bei Annahme überschreibt `contract_cash_quote` diese mit ΣMenge·Festpreis·(1+produktbezogener Wertbonus+Contractbonus).** Ohne Forschung entspricht Cash exakt dem Opportunitätswert eines direkten Verkaufs. XP bei Annahme: `20·sqrt(max(1,ΣMenge·PVproEinheit))·(1+ln(1+Level)/4)·Kategorie`, Kategorie Regular/Daily/Weekly = 1/2/4. Abschluss-RP: Daily 1, Weekly 3, zusätzlich gibt Company-Level-up ohnehin je 1 RP. Vorhandene manuelle Produktauswahl und Snapshotstruktur erhalten.

Szenarien: Früh Level1/MK1, je eine von vier Primärproduktionen; Mitte Level25/MK10, je zwei konfiguriert für Iron/Steel/Copper/Steel Components; Ende Level100/MK99, je fünf für Industrial Equipment/Cargo Aircraft/High Speed Network System/Steel Components. Für Daily werden die ersten drei ausgewählt, für Weekly alle vier. Quotes entstehen aus der nominellen Vierproduktfirma, danach wird eine dedizierte vollständige Lieferkette für den akzeptierten Snapshot dimensioniert. Keine Forschungs-/Rarityboni.
''')
parts.append(table(['Szenario','Typ','PV-Budget','Warenwert = Cash','XP','XP / nächste Levelanforderung','RP','Produktionsuntergrenze min','1 Fahrzeug seriell min'],[
    [r['scenario'],r['kind'],num(r['budget']),num(r['accepted_cash']),num(r['accepted_xp']),f"{r['accepted_xp']/r['next_level_xp']*100:.2f}%",r['rp'],num(r['parallel_output_minutes']),num(r['one_vehicle_serial_minutes'])] for r in model['contracts']]))
parts.append('''
Die Produktionsuntergrenze nimmt parallele Zielproduktion ohne Ramp-up an. Der rekursive DAG-Plan summiert gemeinsamen Inputbedarf, rundet Maschinenzahlen auf, dimensioniert Solar konservativ für alle Maschinen gleichzeitig und enthält die gesamten Vorstufen. Serialle Freightzeit summiert `ceil(Menge/Kapazität)·Fahrzeit` für einen Truck/Train/Aircraft gleicher MK. Sie ist bei anfangs unterfüllten Abfahrten zu optimistisch. Produktions- und Lieferzeit können überlappen; ihre Summe ist eine Planungshilfe, kein Engine-Resultat.

Tatsächliche `SimulationEngine`-Läufe: leere Warenbestände, vollständige Vorstufen, benötigte Solar, ein Fahrzeug; 1-Sekunden-Schritte, Route bevorzugt die am stärksten bevorratete noch benötigte Ware. Keine Dev-Produkteinspeisung. Stop spätestens nach vier simulierten Stunden. Normale First-Production-/Continuity-/Efficiency-XP bleiben aktiv, daher ist Ending-XP nicht gleich Vertrags-XP. Ein nicht abgeschlossener Vertrag erhält **keine** vorweggenommene Belohnung.
''')
parts.append(table(['Szenario','Typ','Simulierte Minuten','Abgeschlossen','Produktionskarten','Solar','Erzeugte MW','Ist-Geld','Liefermengen'],[
    [r['scenario'],r['kind'],num(r['elapsed_seconds']/60),str(r['completed']),r['production_cards'],r['solar_cards'],num(r['power_mw']),num(r['cash']),'; '.join(f'{rid}: {num(a)}' for rid,a in r['delivered'].items())] for r in sim]))
parts.append('''
Alle sechs Läufe behalten nichtnegative Bestände; Daily Mitte und Ende werden vollständig beliefert. Die vier Stunden nicht fertig gewordenen Fälle sind **rechtszensierte Beobachtungen**, keine behaupteten Komplettlaufzeiten. Für Früh-Daily verlangt der Snapshot 22.800 Einheiten, ein Truck bietet nominell nur 40/min; bereits 570 Minuten reine Vollfahrt liegen weit über dem vierstündigen Beobachtungsfenster. Früh-Weekly benötigt mindestens 2.700 Minuten Fahrt. Ende-Weekly verlangt u.a. 1.713.000 Steel Components; die dedizierte Kette und manuelle Produktmischung bestimmen hier den Engpass. Tatsächliche Bedarfe, Counts, Power, Summen und Limits stehen ungekürzt im JSON.

Für die Beurteilung von Unternehmensprogression nicht allein die nominalen Belohnungen vergleichen: Früh-Daily entspricht bereits etwa einer Levelanforderung, Ende-Daily nur rund 13 %; Weekly Ende ca. 57 %. Forschungsfortschritt enthält zusätzlich RP durch sämtliche Produktions-Levelaufstiege. Eine pauschale RP-Erhöhung ohne diese Kopplung wäre nicht evidenzbasiert.

## 7. Empfohlene Rewardformeln und Entscheidungsbedarf

Minimaler Cash-Vorschlag innerhalb der vorhandenen Belohnung: `Cash_k = rundeCent(W · (1+β_k))`, W aus festen Produktpreisen und bestehenden additiven Forschungsboni, β Daily zunächst **0,20**, Weekly **0,40**. Keine neue Rewardmechanik. Gegenprobe für obige Fälle ohne Forschung: 32.832 / 166.320; 320.850 / 1.667.251,42; 22.733.282,65 / 122.420.698,09 (Daily/Weekly je Phase). Diese Konstanten sind ein Startkandidat, keine freigegebenen Zahlen. Angenommene alte Verträge bleiben unverändert.

Kapazitätsbudget künftig aus **erreichbarer** statt nominaler Leistung: `Kreal = min(Knetto_Kette, Kauslieferbar, Kenergieversorgt)`, Zwischenprodukte bei einer gemeinsamen Kette nicht als zusätzliche freie Endkapazität zählen; alle Werte in dieselbe PV/min-Einheit konvertieren. Zeitraum-Fenster und Angebotsgenerierung so wählen, dass kurze Pausen/temporär leeres Lager die Quote nicht manipulierbar absenken. Kein neuer kontinuierlicher Quote-Neuaufbau während aktiver Annahme. Erst die Versorgungs- und Freightsimulation unter P7 korrigieren, dann Target-Minuten/Caps kalibrieren.

XP optional mit begrenztem Zeitfaktor auf bestehender Arbeitswertformel: `XPneu = XPheute · clamp((Tfeasible/Tref)^0,25, 0,8, 1,5)`, Tref Daily 60 min / Weekly 240 min. Tfeasible muss aus validierter erreichbarer Kette/Logistik stammen; Eingabe-/Pausenstillstand darf keine unendliche Prämie erzeugen. Vor Umsetzung gewünschtes Leveltempo festlegen und XP/Level-Anteile über die Phasen neu simulieren. **RP vorerst 1/3 beibehalten**, bis Vertragsabschlussfrequenz und Level-RP gemeinsam quantifiziert sind; keine neue RP-Mechanik empfohlen.

Preview, Annahme und Auszahlung müssen dieselbe zentrale Quote verwenden. Vorhandene aktive Snapshots nicht mit neuen Preisen/Produktmengen/XP nachquotieren; bei variablem RP diesen Wert später ebenfalls im Annahmesnapshot speichern. Research/Respec und UTC-Expiry dürfen angenommene Werte nicht nachträglich verändern.

Vor P7/P8 zu entscheiden: Zielamortisation und Stärke des Kostenkandidaten; Aufwand-/Cashprämie der Contracts; normales gewünschtes Daily-/Weekly-Zeitbudget für typische Flotten; erreichbares XP/RP-Tempo; Umgang mit kostenloser Site-Typänderung. Jede Freigabe benötigt einen erneuten Mischflotten-/Gesamtkapitalvergleich. In Phase 0 wurden **keine Produktions- oder Preisdaten verändert**.
''')
(ROOT/'docs/industriova-03-economy-audit.md').write_text('\n\n'.join(parts)+'\n',encoding='utf8')
print('Wrote economy report')
