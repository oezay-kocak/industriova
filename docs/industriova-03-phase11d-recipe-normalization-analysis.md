# INDUSTRIOVA 0.3 – P11-D: Rezeptnormierung und Produktionskapazität

Stand: 23.10.2026. **Abgeschlossene Offline-Untersuchung und Entscheidungsvorlage. Keine Freigabe oder Implementierung neuer Rezepte.**

## Executive Summary

Alle 304 Folgeproduktrezepte und alle 353 rekursiven Produktketten wurden unter vier Rezeptmodellen mit derselben Preislogik C verglichen. 49 Primärprodukte, 68 Processing-, 86 Fabrication- und 150 Assembly-Produkte bleiben im Katalog; alle 708 bestehenden Zutatenbeziehungen bleiben erhalten.

**Empfehlung: N1 als konservative Grundlage für einen späteren, separat freizugebenden Entwurf.** Es erhält sämtliche Materialumwandlungsverhältnisse, verändert 178 Rezepte und beseitigt das Flour-Verhältnis 1:6. Bei den 37 einfachen Rezepten mit genau einem Primärinput liegen die Verhältnisse anschließend zwischen 1 und 1,5 Verarbeitungskarten je Rohstoffkarte, statt zwischen 1 und 6. Alle 18 Fälle mit mindestens drei Verarbeitern je Rohstoffkarte verschwinden. Diese Zahl ist eine ausdrücklich definierte Auffälligkeitsschwelle, keine Behauptung, dass alle übrigen Rezepte optimal seien.

N2 vereinheitlicht diese einfachen Verhältnisse vollständig auf 1:1, ändert aber Materialausbeuten. N3 gewinnt eine begrenzte Suche über 54 gemeinsame Vorlagen unter erklärten Gewichten; es beweist weder globale Optimalität noch die größte wirtschaftliche Vielfalt. Kein Modell gewinnt über alle untersuchten Budgets und Spielphasen. Der Preisparameter C allein beseitigt weder Kartenbedarf noch Liefer- und Steuerungsprobleme.

Die 68 gesteuerten MK1-Beispielketten liefern nach dem Hochlauf annähernd die berechnete Rate. Dieselben Karten ununterbrochen laufen zu lassen kann gemeinsame Vorprodukte aushungern oder Lager füllen. Normierung ersetzt keine Produktionsplanung. Im Spiel wurde keine automatische Steuerung ergänzt.

## 1. Daten, Vergleichsbasis und Bedeutung der Kennzahlen

Quellen sind die unveränderten produktiven Definitionen und Kostenfunktionen in `src/production_zero`, der vollständige P11-A-Rezeptkatalog und die P11-C-Vergleichspreise. Berechnung und Engine-Adapter liegen ausschließlich in `artifacts/phase11d`. Zahlen in Tabellen sind für die Lesbarkeit gerundet; CSVs enthalten die berechnete Genauigkeit.

Es werden drei verschiedene Bezugsgrößen ausdrücklich getrennt:

* `own`: eine vollständig ausgelastete finale MK1-Karte; die Zutatenkarten werden pro Ressourcentyp rekursiv summiert und erst danach auf ganze Karten gerundet.
* `standard`: **120 aggregierte Primärwareneinheiten pro Minute** über alle Rohstoffarten zusammen. Bei Mehrinputketten bedeutet dies weder genau eine physische Rohstoffkarte noch 120 Einheiten jeder Zutat. Dies ist ein gemeinsamer Materialdurchsatzvergleich, kein Budgetvergleich.
* `fixed_60`: 60 finale Einheiten pro Minute in jedem Modell. Besonders N0/N1 sind damit bei identischer Materialausbeute direkt vergleichbar. Unter N2/N3 kann dieselbe finale Menge andere Rohstoffmengen verlangen.

`standard_capital` ist zusätzlich erforderliches Geld nach Anrechnung der tatsächlich verwendeten Starterkarten und ersten Gratisgebäude, einschließlich aller bezahlten Karten, Hallen, Linien, Slots, erneuerbarer Energie, Freight und gegebenenfalls Storage. `standard_replacement_capital` bewertet zusätzlich die genutzten geschenkten Vermögenswerte zum Ersatzpreis. Ungenutzte Geschenke werden nicht als Kettenkapital gezählt. Höherer Cashflow ist Bruttoliefererlös ohne erfundene laufende Slotmiete oder Energiekosten. Investitionen sind einmalige Ausgaben.

Modellkapazität, nominaler Erlös und gemessener Engine-Erlös sind verschiedene Größen. Die Budgetsuche ist eine Kapazitätsrechnung; nur Tabellen mit ausdrücklich gemessenen Engine-Werten belegen reale Lieferungen. Als nachhaltig wird hier ein annähernd stabiles letztes 60-Minuten-Fenster einer zweistündigen Gegenprüfung bezeichnet, kein Beweis für beliebig lange Laufzeit.

## 2. Mathematik und tatsächliche Infrastrukturkosten

Für Rezept j mit Output q_j, Zyklus t_j und Input a_ij ist die MK1-Rate r_j=60 q_j/t_j. Eine finale Karte verlangt direkt a_ij/q_i gleichzeitige Vorproduktkarten, da sämtliche untersuchten Zyklen sechs Sekunden dauern. Allgemein gilt (60 a_ij/t_j)/r_i. Die inverse Zahl ist die Zahl von Verbrauchern, die eine Vorproduktkarte versorgen kann. Mehrinputrezepte erhalten für **jede** Ressource eine eigene Zahl.

Rekursiv gilt N_j(j)=1 und N_j(x)=Σ_i (a_ij/q_j) N_i(x). Gemeinsame Vorprodukte werden nach Ressourcen-ID zusammengeführt. Für finale Rate R ist die theoretische Kartenzahl f_x=R N_j(x)/r_x und die installierte Zahl n_x=ceil(f_x), mindestens eins bei positivem Bedarf. Die durchschnittliche Auslastung ist Σf_x/Σn_x. Angeforderte maximale Leistung ist Σn_x P_x, kontinuierliche MW-Minuten pro finaler Einheit sind ΣN_j(x)P_x/r_x. Pausen können den Durchschnitt reduzieren; die Anlage ist auf den gleichzeitigen Vollbetrieb dimensioniert.

Das Zusammenführen entspricht in den Engine-Beispielen tatsächlich einer gemeinsamen Ressourceninventur mit allen Verbrauchern. Es setzt eine passende zeitliche Zuteilung voraus. Rechnerisch genügend geteilte Kapazität garantiert bei der bestehenden Ausführungsreihenfolge keine faire Warenverteilung.

Ein zusätzlicher exakter Bruchrechenweg bestimmt den kleinsten vollständig ausgelasteten ganzzahligen Kartenblock: kgV der Nenner von N_j(x) q_j/q_x. Das ist der Maßstab für gleichzeitig volle Karten ohne Bruchkapazitäten, **nicht** die kleinste baubare Firma. Alternativ kann man pausieren, teilen oder Zwischenprodukte zusätzlich verkaufen. `full_feed_cards_without_input_starvation` propagiert den Bedarf aller aufgerundeten Verbraucher im Vollbetrieb; `full_feed_positive_surplus_min` zeigt dabei verbleibende Überschüsse.

Für Gebäude/Slots verwendet eine diskrete dynamische Optimierung die echten `facility_price`, `line_price`, `slot_price` und Freight-Preise. Sie darf eine weitere Halle kaufen, bevor alle teuren Slots der vorherigen geöffnet sind. Factory: fünf Linien mit je zehn Plätzen, zunächst drei Plätze. Resources: drei Linien mit je zehn Plätzen, zunächst einer; separat je Rohstoffmaschinenklasse. Energy: drei Linien mit je fünf Plätzen, zunächst einer. Freight: acht Plätze pro Linie, drei geschenkte Garageplätze beziehungsweise zwei Startplätze anderer Anlagen. Alle tatsächlich bezahlten Karten und Erweiterungen sind enthalten.

Die Infrastrukturkurven sind für 1–512 Karten je Board/Freight-Typ rekonstruiert und auf monotone Kosten geprüft. **512 ist eine Audit-Suchgrenze, kein Spiellimit.** Die Kostenminimierung ist für diese festen Kartenzahlen und Gebäudeoptionen exakt. Die gesamte Unternehmensplanung ist begrenzt: jeweils reine Solar- oder Windversorgung und eine homogene Flotte aus Truck/Train/Aircraft/Ship werden verglichen. Gemischte Fahrzeuge, Brennstoffkraftwerke und beliebige Mehrproduktfirmen sind nicht global optimiert.

Marginale Factory-Kosten werden gesondert für die Erweiterung nach einer bereits vollständig belegten ersten 50er-Halle berechnet (`marginal_factory_capacity`). Die belegte Halle wird nicht erneut bezahlt oder als nutzbarer Gratisraum angerechnet. Spätere bereits belegte Hallenzahlen ändern den konkreten Gebäudepreis weiter; die Spalte ist ein klarer gemeinsamer Zustand, keine universelle Grenzkostenkonstante.

Die statische Storage-Planung deckt konservativ einen summierten Satz aller Input-/Outputchargen der installierten Maschinen ab; Basis 75 280 Einheiten, je Upgrade +18 820, reale auf Zehner gerundete kubische Kosten. Das ist eine Dimensionierungsheuristik. Exakte Puffer/Versandzeitpunkte werden separat in der Engine geprüft. Positiver dauerhafter Überschuss kann durch **kein endliches Lager** dauerhaft behoben werden; Σpositive Überschüsse × 10 ist nur eine Zehn-Minuten-Obergrenze bei angenommenem Vollbetrieb, keine simulierte Lagerkurve.

## 3. Vier vollständig definierte Rezeptmodelle

**N0:** alle heutigen Rezepte, Mengen, Zeiten und Leistungen unverändert.

**N1:** topologisch, von Primary nach Assembly: k=max(1,min(6,floor(min_i(q'_i/a_ij)))); alle Inputs und der Output des bisherigen Rezepts werden gemeinsam mit dem ganzzahligen Faktor k multipliziert. Zyklus und Leistung bleiben unverändert. Pro Rezept höchstens Faktor sechs, keine Zutat verschwindet, jede Umwandlungsrelation a/q bleibt exakt erhalten. Nachgelagerte Rezepte berücksichtigen bereits normierte Vorgänger. Dies ist eine nachvollziehbare konservative Regel, kein individuell handoptimiertes Optimum.

**N2:** gemeinsame Outputs je sechs Sekunden: Processor 6, Fabricator 3, Assembler 1. Für jede Zutat wird die ursprüngliche Kartenlast a_ij/q_i berechnet, auf die größte Last desselben Rezepts normiert und dem nächsten Anteil aus {1, 1/2, 1/4} zugeordnet (bei Gleichstand entscheidet die Reihenfolge 1, 1/2, 1/4). Neuer Input=max(1,floor(q'_i × Anteil × alpha+0,5)), alpha=1. Zutatenidentitäten bleiben erhalten, Materialausbeuten ändern sich. So entsteht für einfache Primärverarbeitung 12→6; für komplexe Rezepte bleiben dominante und ergänzende Zutaten unterscheidbar. Ganzzahlrundung kann besonders bei kleinen Outputs von idealen Viertelanteilen abweichen. Physische Plausibilität/Einheitensemantik ist vor einer Umsetzung separat zu prüfen; das Verfahren behauptet keine echte Massenbilanz über abstrakte Warenarten.

**N3:** dieselben Lastanteile, aber Auswahl einer gemeinsamen Vorlage aus Processor {6,12}, Fabricator {2,3,6}, Assembler {1,2,3}, alpha {0,5;1;2}: 54 Kandidaten. Gewählt wurde **6/6/3 bei alpha=1**. Keine 304 individuellen Sonderregeln.

Zielfunktion, gleich gewichtet über alle 304 Folgeprodukte bei 120 aggregierten Rohstoffeinheiten/min: 0,30 × mittleres Ersatzkapital/N0 + 0,20 × mittlere Factory-Karten/N0 + 0,15 × mittlere angeforderte MW/N0 + 0,15 × mittlerer Leerlaufanteil + 0,10 × Variationskoeffizient der Branchenmittelwerte (Erlös/Ersatzkapital) + 0,05 × mittlere absolute logarithmische Ausbeuteänderung + 0,05 × |log2(alpha)|. Gewichte sind Designannahmen. Output allein erhält keinen Bonus. Score 0,696681; Ergebnis gilt nur innerhalb dieser Kandidatenmenge und dieses Querschnitts. Die vollständigen 54 Ergebnisse stehen in `n3-candidates.csv`.

## 4. Gesamtvergleich und Rezeptauffälligkeiten

| Modell | Geänderte Rezepte | Factory Ø | MW Ø | Ersatzkapital Ø $ | Leerlauf Ø % | Einfach: Verarbeiter/Rohstoffkarte |
| --- | --- | --- | --- | --- | --- | --- |
| N0 | 0 | 7.48 | 105.99 | 12 273.95 | 52.31 | 1.00–6.00 |
| N1 | 178 | 5.74 | 90.35 | 11 369.21 | 65.22 | 1.00–1.50 |
| N2 | 294 | 5.67 | 89.75 | 11 305.43 | 65.38 | 1.00–1.00 |
| N3 | 302 | 5.67 | 89.75 | 11 310.15 | 65.34 | 1.00–1.00 |

Alle Mittelwerte: 304 Folgeprodukte, identischer aggregierter Rohstoffdurchsatz, Common MK1 ohne Research. **Die mittlere Unterauslastung steigt** von 52,31 % auf etwa 65 %: leistungsfähigere ganze Karten werden bei kleinen, festgehaltenen Rohstoffmengen seltener voll genutzt. Weniger bezahlte Karten und weniger Leerlauf sind hier unterschiedliche Ziele. N1 wird deshalb wegen erhaltener Materialausbeuten und niedrigerem Kapital-/Platzbedarf empfohlen, nicht wegen einer Verbesserung jedes Effizienzkriteriums. Auch N3 erreicht unter den gewählten Gewichten keine Verbesserung dieses Einzelziels gegenüber N0. Größere ganzzahlige Vollauslastungsblöcke oder passend gemischte Firmen können dies ändern, sind aber nicht dieselbe Einzelkette bei 120 Rohstoffeinheiten/min. N2 und N3 haben hier dieselben Kartenzahlen, weil größere Outputs auf den oberen Stufen zugleich die dort benötigten Zutatenmengen verändern; ihre finalen Mengen, Preise und Freight-Kosten sind trotzdem verschieden.

| Einfaches N0-Rezept | Input→Output / 6 s | Verarbeiter je Rohstoffkarte | N1 | N2 / N3 |
| --- | --- | --- | --- | --- |
| industrial_gas | 2 natural_gas → 2 / 6 s | 6.00 | 12 natural_gas → 12 / 6 s | 12 natural_gas → 6 / 6 s |
| flour | 2 wheat → 2 / 6 s | 6.00 | 12 wheat → 12 / 6 s | 12 wheat → 6 / 6 s |
| corn_meal | 2 corn → 2 / 6 s | 6.00 | 12 corn → 12 / 6 s | 12 corn → 6 / 6 s |
| raw_sugar | 2 sugarcane → 2 / 6 s | 6.00 | 12 sugarcane → 12 / 6 s | 12 sugarcane → 6 / 6 s |
| refined_sugar | 2 sugarcane → 2 / 6 s | 6.00 | 12 sugarcane → 12 / 6 s | 12 sugarcane → 6 / 6 s |
| soy_oil | 2 soybeans → 1 / 6 s | 6.00 | 12 soybeans → 6 / 6 s | 12 soybeans → 6 / 6 s |
| soy_protein | 2 soybeans → 1 / 6 s | 6.00 | 12 soybeans → 6 / 6 s | 12 soybeans → 6 / 6 s |
| cotton_fiber | 2 cotton → 2 / 6 s | 6.00 | 12 cotton → 12 / 6 s | 12 cotton → 6 / 6 s |
| processed_gypsum | 3 gypsum → 3 / 6 s | 4.00 | 12 gypsum → 12 / 6 s | 12 gypsum → 6 / 6 s |
| lumber | 3 timber → 3 / 6 s | 4.00 | 12 timber → 12 / 6 s | 12 timber → 6 / 6 s |
| chlorine | 3 salt → 2 / 6 s | 4.00 | 12 salt → 8 / 6 s | 12 salt → 6 / 6 s |
| ammonia | 3 natural_gas → 2 / 6 s | 4.00 | 12 natural_gas → 8 / 6 s | 12 natural_gas → 6 / 6 s |
| potassium_compound | 3 potash → 2 / 6 s | 4.00 | 12 potash → 8 / 6 s | 12 potash → 6 / 6 s |
| hydrogen | 3 natural_gas → 2 / 6 s | 4.00 | 12 natural_gas → 8 / 6 s | 12 natural_gas → 6 / 6 s |
| bitumen | 3 crude_oil → 2 / 6 s | 4.00 | 12 crude_oil → 8 / 6 s | 12 crude_oil → 6 / 6 s |
| platinum | 4 platinum_ore → 2 / 6 s | 3.00 | 12 platinum_ore → 6 / 6 s | 12 platinum_ore → 6 / 6 s |
| palladium | 4 palladium_ore → 2 / 6 s | 3.00 | 12 palladium_ore → 6 / 6 s | 12 palladium_ore → 6 / 6 s |
| purified_graphite | 4 graphite → 3 / 6 s | 3.00 | 12 graphite → 9 / 6 s | 12 graphite → 6 / 6 s |

Die folgende wirtschaftliche Priorisierung verwendet eingespartes zusätzliches Kapital bei **60 finalen Einheiten/min zwischen N0 und N1**, damit der Materialbedarf gleich bleibt. Sie bewertet den gesamten rekursiven Effekt. Ein weit oben stehendes komplexes Produkt ist dadurch nicht als falsches Rezept klassifiziert; häufig erbt es mehrere kleine vorgelagerte Kapazitäten. Energie pro Einheit, Leerlauf und Überschüsse sind für alle 304 Produkte in den CSVs gesondert ausgewiesen.

| Produkt | N0 Zusatzkapital $ | N1 Zusatzkapital $ | Ersparnis $ | Factory N0→N1 | MW N0→N1 |
| --- | --- | --- | --- | --- | --- |
| commercial_truck | 570 655.00 | 120 155.00 | 450 500.00 | 153→69 | 1 897.00→1 040.00 |
| high_speed_network_system | 394 195.00 | 189 835.00 | 204 360.00 | 147→83 | 2 072.00→1 313.00 |
| server | 307 165.00 | 121 495.00 | 185 670.00 | 115→61 | 1 624.00→991.00 |
| autonomous_control_system | 350 055.00 | 167 760.00 | 182 295.00 | 135→82 | 1 828.00→1 211.00 |
| compute_node | 333 595.00 | 151 655.00 | 181 940.00 | 125→73 | 1 754.00→1 139.00 |
| supercomputer | 323 665.00 | 144 240.00 | 179 425.00 | 123→72 | 1 684.00→1 090.00 |
| autonomous_aircraft | 260 365.00 | 101 200.00 | 159 165.00 | 111→58 | 1 511.00→904.00 |
| industrial_computer | 251 455.00 | 99 970.00 | 151 485.00 | 103→52 | 1 435.00→854.00 |
| network_switch | 260 140.00 | 118 610.00 | 141 530.00 | 108→62 | 1 513.00→968.00 |
| autonomous_cargo_ship | 254 050.00 | 114 540.00 | 139 510.00 | 108→62 | 1 470.00→956.00 |
| commercial_aircraft | 173 805.00 | 83 100.00 | 90 705.00 | 97→48 | 1 307.00→754.00 |
| orbital_vehicle | 172 000.00 | 83 320.00 | 88 680.00 | 96→50 | 1 295.00→766.00 |
| communication_satellite | 185 070.00 | 99 370.00 | 85 700.00 | 100→56 | 1 374.00→870.00 |
| utility_vehicle | 175 635.00 | 91 300.00 | 84 335.00 | 99→56 | 1 297.00→831.00 |
| machine_vision_system | 173 620.00 | 92 370.00 | 81 250.00 | 92→54 | 1 282.00→834.00 |
| server_rack | 180 225.00 | 101 845.00 | 78 380.00 | 95→59 | 1 325.00→897.00 |
| cargo_aircraft | 148 040.00 | 74 190.00 | 73 850.00 | 88→44 | 1 180.00→680.00 |
| advanced_aircraft | 143 225.00 | 71 880.00 | 71 345.00 | 83→42 | 1 119.00→654.00 |
| memory_module | 151 635.00 | 82 185.00 | 69 450.00 | 87→49 | 1 200.00→753.00 |
| ai_server | 157 415.00 | 90 795.00 | 66 620.00 | 89→53 | 1 238.00→810.00 |

## 5. Iron und Flour: physischer Nachteil und Preiseffekt getrennt

Iron: ein Extractor erzeugt 120 Ore/min; ein Processor verarbeitet genau diese Menge zu 60 Iron/min. Flour N0: ein Harvester erzeugt 120 Wheat/min; ein Processor verarbeitet nur 20 Wheat/min. Ein einzelner Flour-Processor funktioniert, nutzt aber nur ein Sechstel des Harvesters. Für die vollständige Verarbeitung werden sechs Processors benötigt.

Damit benötigt N0-Flour fünf zusätzliche Processor-Karten, fünf weitere Factory-Plätze und insgesamt 36 statt 14 MW. Die fünf zusätzlichen Karten kosten zum Ersatzpreis $1 375. Im anfänglichen Hallenzustand kosten die Plätze bis sechs zusammen $240. Zwei statt einer Solar-Karte benötigen weitere $180 und einen Energy-Slot für $100. Drei statt zwei Trucks verursachen weitere $205. Reine eingesetzte Karten samt zusätzlich gekauften Slots kosten Iron $1 205, Flour $3 305: **$2 100 Unterschied**, einschließlich des unterschiedlichen Freight-Bedarfs. Einschließlich verwendeter geschenkter Gebäude beträgt das Ersatzkapital $5 705 bzw. $7 805.

Der tatsächliche Genesis-Zahlungsbedarf ist wegen Starterkarten anders: Iron $0, Flour $2 165, davon Harvester $340, vier bezahlte Processors $1 100, Factory-Slots $240, Solar $180, Energy-Slot $100 und Truck $205. Die geschenkten zwei Processors sind keine später kostenlos nachkaufbaren Karten.

N1 setzt Flour auf 12 Wheat→12 Flour: ein Harvester versorgt einen Processor, weiter 120 Flour/min. N2/N3 setzen 12→6: ebenfalls 1:1, aber nur 60 Flour/min. In beiden Fällen benötigt die Produktion 11 MW und eine Solar-Karte. N1 benötigt weiterhin drei Trucks; N2/N3 zwei. Zusätzlicher Genesis-Kapitalbedarf ist $545 bzw. $340. N1 erhält die Warenumwandlung 1:1; N2/N3 halbieren die Ausbeute.

Der heutige A-Preis liefert nominal Iron $225/min und Flour $195/min. Diese Referenz ist **keine Engine-Messung**. Bei identischer C-Logik ergibt sich dagegen Iron $240,08/min, N0-Flour $840,30/min und normiertes Flour rund $240,05/min. C honoriert jede zusätzliche Maschinenminute; sechs ineffizient verteilte Processors erhalten sechs Arbeitszuschläge. Flour ist daher physisch benachteiligt, unter C jedoch im nominalen Erlös überkompensiert. Ein reiner Preisvergleich würde das Strukturproblem verdecken.

## 6. Rekursive Preisbildung C und Verarbeitungsanreiz

Primary p=1. Für Folgeprodukt j gilt:

`p_j = (Σ a_ij p_i)/q_j + (120 + 0,01 P_j) t_j/(60 q_j)`.

Alle direkten Inputwerte sind enthalten. Rekursive Expansion zählt Arbeit nur einmal; überprüft wurde die Identität `p_j = 120 × gesamte rekursive Maschinenminuten + 0,01 × rekursive MW-Minuten der Folgeverarbeitung`, wobei Primary wegen 120 Einheiten/min und Preis 1 bereits genau $120 Maschinenminute repräsentiert. Primärenergie wird nicht zusätzlich in den festen Primary-Preis eingerechnet. N0 reproduziert alle 353 C-Preise aus P11-C.

Die zusätzliche Verarbeitung eines eigenen Batches erzeugt gegenüber dem Verkauf seiner Inputs exakt `(120+0,01 P_j)t_j/60` Wert. Ein voll arbeitender MK1-Verarbeiter erhält daher $120+0,01P_j pro Minute zusätzliche Wertschöpfung. Das ist ein transparenter Anreiz, aber keine garantierte bessere Kapitalrendite: notwendige ganze Vorproduktkarten, Slots, Freighter, Startergeschenke und Wartezeiten sind nicht vollständig im Arbeitspreis enthalten.

Alle Varianten werden neu bepreist. Den alten Flour-C-Preis $7,0025 unverändert auf N1s sechsfach schnellere Karte anzuwenden wäre eine künstliche Windfall-Rechnung. Tatsächlich ist N1-Flour C=$2,0004167, N2/N3=$4,0008333; Iron bleibt $4,0013333. Wert pro Freight-Einheit ist derselbe C-Stückpreis, solange kein gesonderter Research-Verkaufsbonus aktiv ist. Keine dynamischen Preise wurden entworfen.

## 7. Die 17 verbindlichen Beispielketten

Je Produkt folgen vier komplette Rezepte und die Kettenbewertung bei 120 aggregierten Primäreinheiten/min. Produktionskarten schließen Primary und sämtliche Zwischenstufen ein; Total enthält zusätzlich Energie und Fahrzeuge. Leistung ist der volle gleichzeitige Bedarf, nicht ein aus Teilmaschinen geschätzter Durchschnitt. Freight zeigt Anzahl, Typ und nominale Einheiten/min.

`Cash gem.` ist der wirklich ausgelieferte Erlös im letzten 60-Minuten-Fenster der gesteuerten Zweistundensimulation. `Payback ≤` ist der erste erfasste Zeitpunkt 10/30/60/120 min, an dem kumulative Verkäufe die vollständig vorfinanzierten Zusatzinvestitionen decken; sonst `>120`. Dies ist eine grobe beobachtete Obergrenze für **Gesamtketteninvestitionen**, keine exakte marginale Amortisation eines einzelnen Slots. Ohne inkrementellen Alt-/Neubetriebsversuch ist `ΔKapital/ΔCash` nur eine theoretische Sensitivität. Die vollständigen markierten Zeitpunkte liegen im Engine-CSV.

### Iron (`iron`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 12 iron_ore → 6 / 6 s |
| N1 | 12 iron_ore → 6 / 6 s |
| N2 | 12 iron_ore → 6 / 6 s |
| N3 | 12 iron_ore → 6 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 2 / 5 | 1 | 0.00 | 5 705.00 | 60.000 | 14.00 | 2 truck / 80.00 | 4.00133 | 240.08 | ≤10 |
| N1 | 2 / 5 | 1 | 0.00 | 5 705.00 | 60.000 | 14.00 | 2 truck / 80.00 | 4.00133 | 240.08 | ≤10 |
| N2 | 2 / 5 | 1 | 0.00 | 5 705.00 | 60.000 | 14.00 | 2 truck / 80.00 | 4.00133 | 240.08 | ≤10 |
| N3 | 2 / 5 | 1 | 0.00 | 5 705.00 | 60.000 | 14.00 | 2 truck / 80.00 | 4.00133 | 240.08 | ≤10 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $0.00 und den Factory-Bedarf von 1 auf 1. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### Copper (`copper`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 12 copper_ore → 6 / 6 s |
| N1 | 12 copper_ore → 6 / 6 s |
| N2 | 12 copper_ore → 6 / 6 s |
| N3 | 12 copper_ore → 6 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 2 / 5 | 1 | 0.00 | 5 705.00 | 60.000 | 14.00 | 2 truck / 80.00 | 4.00133 | 240.08 | ≤10 |
| N1 | 2 / 5 | 1 | 0.00 | 5 705.00 | 60.000 | 14.00 | 2 truck / 80.00 | 4.00133 | 240.08 | ≤10 |
| N2 | 2 / 5 | 1 | 0.00 | 5 705.00 | 60.000 | 14.00 | 2 truck / 80.00 | 4.00133 | 240.08 | ≤10 |
| N3 | 2 / 5 | 1 | 0.00 | 5 705.00 | 60.000 | 14.00 | 2 truck / 80.00 | 4.00133 | 240.08 | ≤10 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $0.00 und den Factory-Bedarf von 1 auf 1. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### Steel (`steel`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 12 iron_ore + 3 coal → 4 / 6 s |
| N1 | 12 iron_ore + 3 coal → 4 / 6 s |
| N2 | 12 iron_ore + 3 coal → 6 / 6 s |
| N3 | 12 iron_ore + 3 coal → 6 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 3 / 6 | 1 | 370.00 | 6 210.00 | 32.000 | 24.00 | 1 truck / 40.00 | 6.75300 | 216.10 | ≤10 |
| N1 | 3 / 6 | 1 | 370.00 | 6 210.00 | 32.000 | 24.00 | 1 truck / 40.00 | 6.75300 | 216.10 | ≤10 |
| N2 | 3 / 7 | 1 | 370.00 | 6 415.00 | 48.000 | 24.00 | 2 truck / 80.00 | 4.50200 | 216.10 | ≤10 |
| N3 | 3 / 7 | 1 | 370.00 | 6 415.00 | 48.000 | 24.00 | 2 truck / 80.00 | 4.50200 | 216.10 | ≤10 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $0.00 und den Factory-Bedarf von 2 auf 2. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### Stainless Steel (`stainless_steel`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 12 iron_ore + 3 coal + 2 chromium_ore + 2 nickel_ore → 3 / 6 s |
| N1 | 12 iron_ore + 3 coal + 2 chromium_ore + 2 nickel_ore → 3 / 6 s |
| N2 | 12 iron_ore + 3 coal + 3 chromium_ore + 3 nickel_ore → 6 / 6 s |
| N3 | 12 iron_ore + 3 coal + 3 chromium_ore + 3 nickel_ore → 6 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 5 / 8 | 1 | 1 160.00 | 7 340.00 | 18.947 | 37.00 | 1 truck / 40.00 | 10.33767 | 195.90 | ≤10 |
| N1 | 5 / 8 | 1 | 1 160.00 | 7 340.00 | 18.947 | 37.00 | 1 truck / 40.00 | 10.33767 | 195.90 | ≤10 |
| N2 | 5 / 8 | 1 | 1 160.00 | 7 340.00 | 34.286 | 37.00 | 1 truck / 40.00 | 5.50217 | 188.72 | ≤10 |
| N3 | 5 / 8 | 1 | 1 160.00 | 7 340.00 | 34.286 | 37.00 | 1 truck / 40.00 | 5.50217 | 188.72 | ≤10 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $0.00 und den Factory-Bedarf von 2 auf 2. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### Aluminum (`aluminum`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 9 bauxite → 5 / 6 s |
| N1 | 9 bauxite → 5 / 6 s |
| N2 | 12 bauxite → 6 / 6 s |
| N3 | 12 bauxite → 6 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 3 / 7 | 2 | 280.00 | 6 260.00 | 66.667 | 24.00 | 2 truck / 80.00 | 4.20180 | 280.12 | ≤10 |
| N1 | 3 / 7 | 2 | 280.00 | 6 260.00 | 66.667 | 24.00 | 2 truck / 80.00 | 4.20180 | 280.12 | ≤10 |
| N2 | 2 / 5 | 1 | 0.00 | 5 705.00 | 60.000 | 15.00 | 2 truck / 80.00 | 4.00150 | 240.09 | ≤10 |
| N3 | 2 / 5 | 1 | 0.00 | 5 705.00 | 60.000 | 15.00 | 2 truck / 80.00 | 4.00150 | 240.09 | ≤10 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $0.00 und den Factory-Bedarf von 2 auf 2. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### Platinum (`platinum`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 4 platinum_ore → 2 / 6 s |
| N1 | 12 platinum_ore → 6 / 6 s |
| N2 | 12 platinum_ore → 6 / 6 s |
| N3 | 12 platinum_ore → 6 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 4 / 9 | 3 | 935.00 | 6 915.00 | 60.000 | 42.00 | 2 truck / 80.00 | 8.00600 | 480.36 | ≤10 |
| N1 | 2 / 5 | 1 | 0.00 | 5 705.00 | 60.000 | 18.00 | 2 truck / 80.00 | 4.00200 | 240.12 | ≤10 |
| N2 | 2 / 5 | 1 | 0.00 | 5 705.00 | 60.000 | 18.00 | 2 truck / 80.00 | 4.00200 | 240.12 | ≤10 |
| N3 | 2 / 5 | 1 | 0.00 | 5 705.00 | 60.000 | 18.00 | 2 truck / 80.00 | 4.00200 | 240.12 | ≤10 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $-935.00 und den Factory-Bedarf von 3 auf 1. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### Flour (`flour`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 2 wheat → 2 / 6 s |
| N1 | 12 wheat → 12 / 6 s |
| N2 | 12 wheat → 6 / 6 s |
| N3 | 12 wheat → 6 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 7 / 12 | 6 | 2 165.00 | 7 805.00 | 120.000 | 36.00 | 3 truck / 120.00 | 7.00250 | 840.30 | ≤10 |
| N1 | 2 / 6 | 1 | 545.00 | 5 910.00 | 120.000 | 11.00 | 3 truck / 120.00 | 2.00042 | 240.05 | ≤10 |
| N2 | 2 / 5 | 1 | 340.00 | 5 705.00 | 60.000 | 11.00 | 2 truck / 80.00 | 4.00083 | 240.05 | ≤10 |
| N3 | 2 / 5 | 1 | 340.00 | 5 705.00 | 60.000 | 11.00 | 2 truck / 80.00 | 4.00083 | 240.05 | ≤10 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $-555.00 und den Factory-Bedarf von 3 auf 1. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### Corn Meal (`corn_meal`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 2 corn → 2 / 6 s |
| N1 | 12 corn → 12 / 6 s |
| N2 | 12 corn → 6 / 6 s |
| N3 | 12 corn → 6 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 7 / 12 | 6 | 2 165.00 | 7 805.00 | 120.000 | 36.00 | 3 truck / 120.00 | 7.00250 | 840.30 | ≤10 |
| N1 | 2 / 6 | 1 | 545.00 | 5 910.00 | 120.000 | 11.00 | 3 truck / 120.00 | 2.00042 | 240.05 | ≤10 |
| N2 | 2 / 5 | 1 | 340.00 | 5 705.00 | 60.000 | 11.00 | 2 truck / 80.00 | 4.00083 | 240.05 | ≤10 |
| N3 | 2 / 5 | 1 | 340.00 | 5 705.00 | 60.000 | 11.00 | 2 truck / 80.00 | 4.00083 | 240.05 | ≤10 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $-555.00 und den Factory-Bedarf von 3 auf 1. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### Soy Oil (`soy_oil`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 2 soybeans → 1 / 6 s |
| N1 | 12 soybeans → 6 / 6 s |
| N2 | 12 soybeans → 6 / 6 s |
| N3 | 12 soybeans → 6 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 7 / 11 | 6 | 1 960.00 | 7 600.00 | 60.000 | 36.00 | 2 truck / 80.00 | 14.00500 | 840.30 | ≤10 |
| N1 | 2 / 5 | 1 | 340.00 | 5 705.00 | 60.000 | 11.00 | 2 truck / 80.00 | 4.00083 | 240.05 | ≤10 |
| N2 | 2 / 5 | 1 | 340.00 | 5 705.00 | 60.000 | 11.00 | 2 truck / 80.00 | 4.00083 | 240.05 | ≤10 |
| N3 | 2 / 5 | 1 | 340.00 | 5 705.00 | 60.000 | 11.00 | 2 truck / 80.00 | 4.00083 | 240.05 | ≤10 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $-1 620.00 und den Factory-Bedarf von 6 auf 1. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### Lumber (`lumber`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 3 timber → 3 / 6 s |
| N1 | 12 timber → 12 / 6 s |
| N2 | 12 timber → 6 / 6 s |
| N3 | 12 timber → 6 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 5 / 10 | 4 | 1 415.00 | 7 055.00 | 120.000 | 26.00 | 3 truck / 120.00 | 5.00167 | 600.20 | ≤10 |
| N1 | 2 / 6 | 1 | 545.00 | 5 910.00 | 120.000 | 11.00 | 3 truck / 120.00 | 2.00042 | 240.05 | ≤10 |
| N2 | 2 / 5 | 1 | 340.00 | 5 705.00 | 60.000 | 11.00 | 2 truck / 80.00 | 4.00083 | 240.05 | ≤10 |
| N3 | 2 / 5 | 1 | 340.00 | 5 705.00 | 60.000 | 11.00 | 2 truck / 80.00 | 4.00083 | 240.05 | ≤10 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $0.00 und den Factory-Bedarf von 2 auf 1. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### Bitumen (`bitumen`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 3 crude_oil → 2 / 6 s |
| N1 | 12 crude_oil → 8 / 6 s |
| N2 | 12 crude_oil → 6 / 6 s |
| N3 | 12 crude_oil → 6 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 5 / 9 | 4 | 1 210.00 | 6 850.00 | 80.000 | 38.00 | 2 truck / 80.00 | 7.50400 | 600.32 | ≤10 |
| N1 | 2 / 5 | 1 | 340.00 | 5 705.00 | 80.000 | 14.00 | 2 truck / 80.00 | 3.00100 | 240.08 | ≤10 |
| N2 | 2 / 5 | 1 | 340.00 | 5 705.00 | 60.000 | 14.00 | 2 truck / 80.00 | 4.00133 | 240.08 | ≤10 |
| N3 | 2 / 5 | 1 | 340.00 | 5 705.00 | 60.000 | 14.00 | 2 truck / 80.00 | 4.00133 | 240.08 | ≤10 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $-555.00 und den Factory-Bedarf von 3 auf 1. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### Silicon (`silicon`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 4 quartz + 1 coal → 2 / 6 s |
| N1 | 12 quartz + 3 coal → 6 / 6 s |
| N2 | 12 quartz + 3 coal → 6 / 6 s |
| N3 | 12 quartz + 3 coal → 6 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 5 / 10 | 3 | 1 025.00 | 7 345.00 | 48.000 | 42.00 | 2 truck / 80.00 | 8.50500 | 408.24 | ≤10 |
| N1 | 3 / 7 | 1 | 370.00 | 6 415.00 | 48.000 | 22.00 | 2 truck / 80.00 | 4.50167 | 216.08 | ≤10 |
| N2 | 3 / 7 | 1 | 370.00 | 6 415.00 | 48.000 | 22.00 | 2 truck / 80.00 | 4.50167 | 216.08 | ≤10 |
| N3 | 3 / 7 | 1 | 370.00 | 6 415.00 | 48.000 | 22.00 | 2 truck / 80.00 | 4.50167 | 216.08 | ≤10 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $-655.00 und den Factory-Bedarf von 3 auf 1. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### High-Purity Silicon (`high_purity_silicon`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 4 quartz + 1 fluorspar + 1 crude_oil + 1 natural_gas → 1 / 6 s |
| N1 | 12 quartz + 3 fluorspar + 3 crude_oil + 3 natural_gas → 3 / 6 s |
| N2 | 12 quartz + 3 fluorspar + 3 crude_oil + 3 natural_gas → 6 / 6 s |
| N3 | 12 quartz + 3 fluorspar + 3 crude_oil + 3 natural_gas → 6 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 6 / 10 | 2 | 1 520.00 | 8 135.00 | 17.143 | 48.00 | 1 truck / 40.00 | 19.01200 | 326.06 | ≤10 |
| N1 | 5 / 8 | 1 | 1 140.00 | 7 480.00 | 17.143 | 36.00 | 1 truck / 40.00 | 11.00400 | 188.72 | ≤10 |
| N2 | 5 / 8 | 1 | 1 140.00 | 7 480.00 | 34.286 | 36.00 | 1 truck / 40.00 | 5.50200 | 188.72 | ≤10 |
| N3 | 5 / 8 | 1 | 1 140.00 | 7 480.00 | 34.286 | 36.00 | 1 truck / 40.00 | 5.50200 | 188.72 | ≤10 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $-2 060.00 und den Factory-Bedarf von 6 auf 2. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### Industrial Equipment (`industrial_equipment`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 2 steel_components + 1 electrical_components + 1 iron_components → 1 / 6 s |
| N1 | 4 steel_components + 2 electrical_components + 2 iron_components → 2 / 6 s |
| N2 | 3 steel_components + 2 electrical_components + 2 iron_components → 1 / 6 s |
| N3 | 6 steel_components + 3 electrical_components + 3 iron_components → 3 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 15 / 20 | 9 | 6 270.00 | 13 045.00 | 9.677 | 123.00 | 1 truck / 40.00 | 61.64305 | 595.88 | ≤30 |
| N1 | 15 / 20 | 9 | 6 270.00 | 13 045.00 | 9.677 | 123.00 | 1 truck / 40.00 | 38.57303 | 372.87 | ≤30 |
| N2 | 15 / 20 | 9 | 6 270.00 | 13 045.00 | 3.025 | 123.00 | 1 truck / 40.00 | 114.39644 | 347.00 | ≤30 |
| N3 | 15 / 20 | 9 | 6 270.00 | 13 045.00 | 10.746 | 123.00 | 1 truck / 40.00 | 32.85194 | 353.16 | ≤30 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $-10 290.00 und den Factory-Bedarf von 26 auf 15. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### Biodiesel (`biodiesel`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 2 biodiesel_feedstock → 1 / 6 s |
| N1 | 6 biodiesel_feedstock → 3 / 6 s |
| N2 | 3 biodiesel_feedstock → 1 / 6 s |
| N3 | 6 biodiesel_feedstock → 3 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 13 / 17 | 9 | 5 465.00 | 11 220.00 | 11.250 | 101.00 | 1 truck / 40.00 | 78.71400 | 885.53 | ≤10 |
| N1 | 8 / 12 | 4 | 2 705.00 | 8 640.00 | 11.250 | 59.00 | 1 truck / 40.00 | 24.00989 | 270.11 | ≤30 |
| N2 | 8 / 12 | 4 | 2 705.00 | 8 640.00 | 3.750 | 59.00 | 1 truck / 40.00 | 72.02967 | 270.11 | ≤30 |
| N3 | 8 / 12 | 4 | 2 705.00 | 8 640.00 | 11.250 | 59.00 | 1 truck / 40.00 | 24.00989 | 270.11 | ≤30 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $-26 585.00 und den Factory-Bedarf von 34 auf 7. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### Microchip (`microchip`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 1 semiconductor_die + 1 semiconductor_components → 1 / 6 s |
| N1 | 1 semiconductor_die + 1 semiconductor_components → 1 / 6 s |
| N2 | 3 semiconductor_die + 3 semiconductor_components → 1 / 6 s |
| N3 | 6 semiconductor_die + 6 semiconductor_components → 3 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 15 / 20 | 8 | 6 505.00 | 13 280.00 | 3.158 | 127.00 | 1 truck / 40.00 | 138.09333 | 434.99 | ≤30 |
| N1 | 14 / 21 | 7 | 5 990.00 | 12 945.00 | 3.158 | 115.00 | 1 truck / 40.00 | 100.05600 | 315.18 | ≤30 |
| N2 | 14 / 21 | 7 | 5 990.00 | 12 945.00 | 1.935 | 115.00 | 1 truck / 40.00 | 142.07200 | 274.67 | ≤30 |
| N3 | 14 / 21 | 7 | 5 990.00 | 12 945.00 | 5.806 | 115.00 | 1 truck / 40.00 | 47.35733 | 274.67 | ≤30 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $-21 645.00 und den Factory-Bedarf von 50 auf 31. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

### AI Server (`ai_server`)

| Modell | Rezept alle 6 s |
| --- | --- |
| N0 | 1 ai_compute_components + 1 server_components + 1 network_components → 1 / 6 s |
| N1 | 1 ai_compute_components + 1 server_components + 1 network_components → 1 / 6 s |
| N2 | 3 ai_compute_components + 3 server_components + 3 network_components → 1 / 6 s |
| N3 | 6 ai_compute_components + 6 server_components + 6 network_components → 3 / 6 s |

| Modell | Produktions-/Totalkarten | Factory | Zusatz-$ | Ersatz-$ | Ziel/min | MW | Freight Karten / Kap./min | C $/Einheit | Cash gem. $/min | Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | 18 / 24 | 10 | 8 975.00 | 15 750.00 | 1.529 | 154.00 | 1 truck / 40.00 | 255.03180 | 391.05 | ≤30 |
| N1 | 17 / 23 | 9 | 8 420.00 | 15 195.00 | 1.529 | 142.00 | 1 truck / 40.00 | 182.96047 | 280.54 | ≤60 |
| N2 | 17 / 23 | 9 | 8 420.00 | 15 195.00 | 1.319 | 142.00 | 1 truck / 40.00 | 203.10133 | 267.42 | ≤60 |
| N3 | 17 / 23 | 9 | 8 420.00 | 15 195.00 | 3.956 | 142.00 | 1 truck / 40.00 | 67.70044 | 267.42 | ≤60 |

Bei gleichen 60 finalen Einheiten/min verändert N1 das Zusatzkapital um $-66 620.00 und den Factory-Bedarf von 89 auf 53. N2/N3 sind wegen geänderter Ausbeuten zusätzlich nach Materialeinsatz zu beurteilen. Vollständige Kartenlisten, Teilkapazitäten, Rohstoffmengen, Überschüsse und Engpässe stehen in der Produktzeile der Ketten-CSV.

## 8. Budget- und Branchenvergleich

**Zwei verschiedene Zustände:** Abschnitt 9 simuliert den echten Genesis-Start. Die folgenden Budgets sind Firmen mit bereits ehrlich vorausgesetzter, früher verdienter Produktionsfreischaltung und Company-Level 1, 5 oder 25. Es werden nur Produkte gewählt, deren komplette Kette zum jeweiligen Level zugänglich ist. Es wird nicht behauptet, dass eine neue $1 250-Firma sofort diese Freischaltungen besitzt. Es sind keine kostenlosen Research-, Rarity- oder MK99-Firmen.

Je Produkt werden Common MK1/10/50/99 mit vollständig bezahlten aktuellen Upgradepreisen durchsucht; alle Karten einer Firma erhalten denselben MK. Research bleibt null. Verfügbare Geschenke werden angerechnet. Die Rate wird monoton bis zur Budgetgrenze gesucht, neun Binärschritte je Intervall, Rate höchstens 65 536/min, Infrastruktur höchstens 512 je Typ. Gemischte MKs, Produkte, Qualitäten und Kraftwerksportfolios sind nicht durchsucht. Die produktiven heutigen Upgradequotes werden eingefroren, um Rezeptänderungen isoliert zu vergleichen; eine zusätzliche Schatten-Neubepreisung ist separat dokumentiert.

Die folgenden Erlöse sind **nominale Kapazitätsobergrenzen**, keine gemessenen Lieferungen aller Budgetfirmen. `10/20/30` zählt finale Produktstrategien mit mindestens 90/80/70 % des besten zulässigen Erlöses, einschließlich des Bestplatzierten. Das sind keine unabhängigen Industriezweige. Eine Branche wird hier durch die vorhandene Research-Domain bestimmt. Stärkste/schwächste Branche vergleicht jeweils deren beste zulässige Produktstrategie; der Faktor ist deren Quotient, nicht der Durchschnitt aller Produkte.

### Company-Level 1 – vorausgesetzte verdiente Unlocks, kein Research

| Budget $ | Modell | Bester Output | Kapazität $/min | Zulässig | 10/20/30 | Stärkste / schwächste Branche | Faktor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 250 | N0 | bitumen | 600.32 | 24 | 3/6/9 | oil_gas / construction | 3.00 |
| 5 000 | N0 | silicon | 1 360.80 | 24 | 3/13/15 | electronics / construction | 3.09 |
| 10 000 | N0 | iron_components | 2 201.39 | 24 | 4/12/14 | metals / construction | 3.44 |
| 50 000 | N0 | pump_components | 6 374.01 | 24 | 5/15/15 | electronics / construction | 1.99 |
| 100 000 | N0 | compressor_components | 11 023.10 | 24 | 12/15/15 | machinery / construction | 1.78 |
| 500 000 | N0 | iron | 26 888.96 | 24 | 6/14/15 | metals / construction | 1.50 |
| 1 000 000 | N0 | iron | 35 979.99 | 24 | 6/14/15 | metals / construction | 1.67 |
| 10 000 000 | N0 | iron | 79 130.37 | 24 | 4/12/15 | metals / construction | 1.69 |
| 1 000 000 000 | N0 | steel | 358 719.36 | 24 | 1/1/9 | metals / construction | 5.48 |
| 1 250 | N1 | aluminum_components | 576.34 | 24 | 7/10/10 | metals / construction | 2.88 |
| 5 000 | N1 | aluminum_components | 1 440.86 | 24 | 1/2/12 | metals / construction | 3.27 |
| 10 000 | N1 | steel_components | 1 951.10 | 24 | 5/9/12 | metals / construction | 3.05 |
| 50 000 | N1 | pump_components | 6 053.01 | 24 | 8/13/15 | electronics / construction | 1.89 |
| 100 000 | N1 | compressor_components | 10 467.97 | 24 | 13/15/15 | machinery / construction | 1.69 |
| 500 000 | N1 | pump_components | 28 614.21 | 24 | 14/15/15 | electronics / construction | 1.59 |
| 1 000 000 | N1 | pump_components | 36 318.04 | 24 | 14/15/15 | electronics / construction | 1.68 |
| 10 000 000 | N1 | bitumen | 79 226.40 | 24 | 14/15/15 | oil_gas / construction | 1.69 |
| 1 000 000 000 | N1 | steel | 358 719.36 | 24 | 5/7/12 | metals / construction | 5.48 |
| 1 250 | N2 | aluminum_components | 720.38 | 24 | 3/4/8 | metals / construction | 3.60 |
| 5 000 | N2 | aluminum_components | 1 440.76 | 24 | 3/5/11 | metals / construction | 3.27 |
| 10 000 | N2 | aluminum_components | 2 161.14 | 24 | 6/7/10 | metals / construction | 3.38 |
| 50 000 | N2 | compressor_components | 6 303.10 | 24 | 7/15/15 | machinery / construction | 1.97 |
| 100 000 | N2 | aluminum_components | 10 805.70 | 24 | 10/15/15 | metals / construction | 1.74 |
| 500 000 | N2 | lumber | 28 806.00 | 24 | 15/15/15 | forestry / construction | 1.60 |
| 1 000 000 | N2 | compressor_components | 36 557.98 | 24 | 15/15/15 | machinery / construction | 1.69 |
| 10 000 000 | N2 | aluminum | 79 133.66 | 24 | 15/15/15 | metals / construction | 1.69 |
| 1 000 000 000 | N2 | compressor_components | 347 594.95 | 24 | 4/9/15 | machinery / construction | 5.31 |
| 1 250 | N3 | compressor_components | 630.31 | 24 | 1/5/11 | machinery / construction | 3.15 |
| 5 000 | N3 | compressor_components | 1 260.62 | 24 | 2/11/15 | machinery / construction | 2.87 |
| 10 000 | N3 | compressor_components | 1 890.93 | 24 | 4/10/15 | machinery / construction | 2.95 |
| 50 000 | N3 | compressor_components | 6 303.10 | 24 | 2/15/15 | machinery / construction | 1.97 |
| 100 000 | N3 | aluminum_components | 10 445.51 | 24 | 15/15/15 | metals / construction | 1.68 |
| 500 000 | N3 | lumber | 28 806.00 | 24 | 15/15/15 | forestry / construction | 1.60 |
| 1 000 000 | N3 | aluminum_components | 36 019.00 | 24 | 15/15/15 | metals / construction | 1.67 |
| 10 000 000 | N3 | aluminum | 79 133.66 | 24 | 15/15/15 | metals / construction | 1.69 |
| 1 000 000 000 | N3 | compressor_components | 347 594.95 | 24 | 4/9/15 | machinery / construction | 5.31 |

### Company-Level 5 – vorausgesetzte verdiente Unlocks, kein Research

| Budget $ | Modell | Bester Output | Kapazität $/min | Zulässig | 10/20/30 | Stärkste / schwächste Branche | Faktor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 250 | N0 | ammonia | 600.32 | 57 | 12/16/21 | oil_gas / machinery | 2.61 |
| 5 000 | N0 | silicon | 1 360.80 | 94 | 11/40/55 | electronics / energy | 1.73 |
| 10 000 | N0 | soy_oil | 2 380.85 | 104 | 9/40/69 | agriculture / oil_gas | 1.32 |
| 50 000 | N0 | marine_components | 6 604.10 | 106 | 29/81/84 | maritime / oil_gas | 1.22 |
| 100 000 | N0 | fiber_components | 11 366.56 | 106 | 60/84/84 | textiles / oil_gas | 1.10 |
| 500 000 | N0 | structural_components | 27 315.36 | 106 | 10/36/84 | construction / energy | 1.33 |
| 1 000 000 | N0 | treated_lumber | 36 014.00 | 106 | 11/41/84 | forestry / energy | 1.31 |
| 10 000 000 | N0 | treated_lumber | 80 959.47 | 106 | 6/28/84 | forestry / energy | 1.30 |
| 1 000 000 000 | N0 | steel | 358 719.36 | 106 | 1/3/22 | metals / energy | 1.56 |
| 1 250 | N1 | aluminum_components | 576.34 | 57 | 7/11/11 | metals / forestry | 2.40 |
| 5 000 | N1 | aluminum_components | 1 440.86 | 94 | 1/5/21 | metals / energy | 2.00 |
| 10 000 | N1 | biodiesel | 2 160.89 | 104 | 6/24/42 | energy / oil_gas | 1.64 |
| 50 000 | N1 | cargo_vessel | 6 519.35 | 106 | 32/66/84 | maritime / oil_gas | 1.29 |
| 100 000 | N1 | industrial_insulation | 12 005.22 | 106 | 18/60/84 | construction / oil_gas | 1.25 |
| 500 000 | N1 | bio_material_components | 33 012.10 | 106 | 20/66/83 | chemicals / oil_gas | 1.23 |
| 1 000 000 | N1 | bio_lubricant | 44 970.49 | 106 | 13/57/84 | chemicals / oil_gas | 1.25 |
| 10 000 000 | N1 | treated_lumber | 97 170.89 | 106 | 8/50/82 | forestry / maritime | 1.25 |
| 1 000 000 000 | N1 | biodiesel_feedstock | 427 005.69 | 106 | 2/20/43 | chemicals / oil_gas | 2.17 |
| 1 250 | N2 | aluminum_components | 720.38 | 57 | 3/4/9 | metals / forestry | 2.25 |
| 5 000 | N2 | aluminum_components | 1 440.76 | 94 | 5/14/32 | metals / energy | 2.00 |
| 10 000 | N2 | clothing | 2 251.08 | 104 | 16/27/50 | textiles / oil_gas | 1.56 |
| 50 000 | N2 | biodiesel_feedstock | 7 202.12 | 106 | 23/56/84 | chemicals / oil_gas | 1.30 |
| 100 000 | N2 | industrial_insulation | 12 605.45 | 106 | 26/62/84 | construction / oil_gas | 1.31 |
| 500 000 | N2 | packaging_components | 34 512.50 | 106 | 12/61/83 | forestry / oil_gas | 1.28 |
| 1 000 000 | N2 | treated_lumber | 47 178.01 | 106 | 7/37/81 | forestry / oil_gas | 1.31 |
| 10 000 000 | N2 | treated_lumber | 98 932.98 | 106 | 8/34/83 | forestry / oil_gas | 1.25 |
| 1 000 000 000 | N2 | bio_composite | 430 281.87 | 106 | 6/25/55 | chemicals / oil_gas | 1.64 |
| 1 250 | N3 | compressor_components | 630.31 | 57 | 1/6/13 | machinery / forestry | 1.97 |
| 5 000 | N3 | marine_components | 1 380.62 | 94 | 5/15/33 | maritime / energy | 1.92 |
| 10 000 | N3 | clothing | 2 251.08 | 104 | 6/21/49 | textiles / oil_gas | 1.56 |
| 50 000 | N3 | construction_frames | 7 263.46 | 106 | 13/47/84 | construction / oil_gas | 1.32 |
| 100 000 | N3 | industrial_insulation | 12 605.45 | 106 | 15/60/84 | construction / oil_gas | 1.31 |
| 500 000 | N3 | packaging_components | 33 822.25 | 106 | 17/62/84 | forestry / oil_gas | 1.26 |
| 1 000 000 | N3 | treated_lumber | 47 178.01 | 106 | 7/37/81 | forestry / oil_gas | 1.31 |
| 10 000 000 | N3 | treated_lumber | 98 932.98 | 106 | 8/34/83 | forestry / oil_gas | 1.25 |
| 1 000 000 000 | N3 | bio_composite | 430 281.87 | 106 | 6/24/55 | chemicals / oil_gas | 1.64 |

### Company-Level 25 – vorausgesetzte verdiente Unlocks, kein Research

| Budget $ | Modell | Bester Output | Kapazität $/min | Zulässig | 10/20/30 | Stärkste / schwächste Branche | Faktor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 250 | N0 | rare_earth_metals | 600.36 | 134 | 33/45/56 | metals / rail | 2.02 |
| 5 000 | N0 | magnetic_components | 1 360.92 | 237 | 21/91/126 | electronics / aerospace | 1.51 |
| 10 000 | N0 | soy_oil | 2 380.85 | 298 | 16/85/166 | agriculture / medical | 1.41 |
| 50 000 | N0 | avionics_components | 6 736.19 | 353 | 81/266/303 | aerospace / oil_gas | 1.25 |
| 100 000 | N0 | industrial_tires | 11 527.92 | 353 | 194/303/304 | automotive / oil_gas | 1.11 |
| 500 000 | N0 | galvanized_metal | 28 011.20 | 353 | 70/203/301 | metals / textiles | 1.31 |
| 1 000 000 | N0 | high_purity_silicon | 38 024.00 | 353 | 44/175/289 | electronics / textiles | 1.34 |
| 10 000 000 | N0 | treated_lumber | 80 959.47 | 353 | 24/145/304 | forestry / textiles | 1.27 |
| 1 000 000 000 | N0 | steel | 358 719.36 | 353 | 15/40/194 | metals / textiles | 1.52 |
| 1 250 | N1 | titanium_components | 640.42 | 134 | 12/29/44 | metals / forestry | 2.67 |
| 5 000 | N1 | aluminum_components | 1 440.86 | 237 | 3/29/67 | metals / oil_gas | 1.71 |
| 10 000 | N1 | industrial_tires | 2 401.28 | 298 | 2/19/84 | automotive / oil_gas | 1.82 |
| 50 000 | N1 | industrial_tires | 7 203.84 | 353 | 24/154/274 | automotive / oil_gas | 1.43 |
| 100 000 | N1 | industrial_rubber_products | 12 160.86 | 353 | 97/265/304 | chemicals / oil_gas | 1.27 |
| 500 000 | N1 | membrane_components | 33 822.62 | 353 | 23/210/302 | machinery / oil_gas | 1.26 |
| 1 000 000 | N1 | sulfuric_acid | 44 971.99 | 353 | 26/191/302 | chemicals / oil_gas | 1.25 |
| 10 000 000 | N1 | treated_lumber | 97 170.89 | 353 | 17/138/298 | forestry / rail | 1.26 |
| 1 000 000 000 | N1 | high_purity_silicon | 438 751.49 | 353 | 9/51/206 | electronics / oil_gas | 2.23 |
| 1 250 | N2 | titanium_components | 720.42 | 134 | 5/10/22 | metals / forestry | 2.25 |
| 5 000 | N2 | aluminum_components | 1 440.76 | 237 | 11/40/84 | metals / agriculture | 1.50 |
| 10 000 | N2 | clothing | 2 251.08 | 298 | 39/79/149 | textiles / medical | 1.67 |
| 50 000 | N2 | rubber_blend_components | 7 562.70 | 353 | 20/143/266 | chemicals / oil_gas | 1.37 |
| 100 000 | N2 | biofuel | 12 725.44 | 353 | 52/238/304 | energy / oil_gas | 1.33 |
| 500 000 | N2 | membrane_components | 34 991.66 | 353 | 25/192/300 | machinery / oil_gas | 1.30 |
| 1 000 000 | N2 | treated_lumber | 47 178.01 | 353 | 17/105/297 | forestry / oil_gas | 1.31 |
| 10 000 000 | N2 | treated_lumber | 98 932.98 | 353 | 21/126/299 | forestry / medical | 1.28 |
| 1 000 000 000 | N2 | chemical_components | 430 287.38 | 353 | 21/157/245 | chemicals / oil_gas | 1.64 |
| 1 250 | N3 | phosphoric_acid | 720.16 | 134 | 1/6/18 | chemicals / forestry | 2.25 |
| 5 000 | N3 | tire_components | 1 440.58 | 237 | 5/31/76 | automotive / agriculture | 1.50 |
| 10 000 | N3 | clothing | 2 251.08 | 298 | 24/68/144 | textiles / medical | 1.67 |
| 50 000 | N3 | construction_frames | 7 263.46 | 353 | 29/165/287 | construction / oil_gas | 1.32 |
| 100 000 | N3 | industrial_insulation | 12 605.45 | 353 | 52/237/304 | construction / oil_gas | 1.31 |
| 500 000 | N3 | membrane_components | 34 661.55 | 353 | 27/189/301 | machinery / oil_gas | 1.29 |
| 1 000 000 | N3 | treated_lumber | 47 178.01 | 353 | 14/85/297 | forestry / rail | 1.32 |
| 10 000 000 | N3 | treated_lumber | 98 932.98 | 353 | 21/122/299 | forestry / medical | 1.28 |
| 1 000 000 000 | N3 | chemical_components | 430 287.38 | 353 | 20/148/245 | chemicals / oil_gas | 1.64 |

Für die Level-25-Sieger werden zusätzlich die tatsächlich eingepreisten Baumaßnahmen zusammengefasst; die volle Auswahl aller zulässigen Produkte findet sich in `budget-search.csv`. Die theoretische Amortisationszahl Zusatzkapital/nominaler Erlös setzt sofort volle Lieferung voraus und ist nur eine untere Idealgrenze gegenüber einem Start mit leeren Lagern.

| Budget $ | Modell | Produkt | MK bezahlt | Investiert $ | Factory | MW | Zielmenge/min | Freight/min | Ideale Payback min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 250 | N0 | rare_earth_metals | 1 | 1 230.00 | 3 | 48.00 | 90.00 | 120.00 | 2.05 |
| 5 000 | N0 | magnetic_components | 1 | 4 735.00 | 9 | 110.00 | 60.00 | 80.00 | 3.48 |
| 10 000 | N0 | soy_oil | 1 | 9 930.00 | 17 | 103.00 | 170.00 | 200.00 | 4.17 |
| 50 000 | N0 | avionics_components | 1 | 48 770.00 | 38 | 540.00 | 60.00 | 80.00 | 7.24 |
| 100 000 | N0 | industrial_tires | 1 | 97 770.00 | 80 | 888.00 | 80.00 | 80.00 | 8.48 |
| 500 000 | N0 | galvanized_metal | 1 | 499 840.00 | 140 | 1 684.00 | 4 200.00 | 4 200.00 | 17.84 |
| 1 000 000 | N0 | high_purity_silicon | 1 | 975 020.00 | 200 | 3 108.00 | 2 000.00 | 2 000.00 | 25.64 |
| 10 000 000 | N0 | treated_lumber | 1 | 9 830 115.00 | 450 | 4 506.00 | 13 488.00 | 14 666.67 | 121.42 |
| 1 000 000 000 | N0 | steel | 10 | 308 492 932.81 | 409 | 25 935.00 | 53 120.00 | 53 300.00 | 859.98 |
| 1 250 | N1 | titanium_components | 1 | 1 240.00 | 4 | 54.00 | 80.00 | 80.00 | 1.94 |
| 5 000 | N1 | aluminum_components | 1 | 4 960.00 | 9 | 104.00 | 200.00 | 200.00 | 3.44 |
| 10 000 | N1 | industrial_tires | 1 | 9 860.00 | 12 | 176.00 | 40.00 | 40.00 | 4.11 |
| 50 000 | N1 | industrial_tires | 1 | 49 445.00 | 36 | 528.00 | 120.00 | 120.00 | 6.86 |
| 100 000 | N1 | industrial_rubber_products | 1 | 98 540.00 | 59 | 875.00 | 213.25 | 240.00 | 8.10 |
| 500 000 | N1 | membrane_components | 1 | 490 580.00 | 148 | 2 085.00 | 2 940.00 | 3 000.00 | 14.50 |
| 1 000 000 | N1 | sulfuric_acid | 1 | 955 710.00 | 150 | 2 550.00 | 17 984.00 | 18 666.67 | 21.25 |
| 10 000 000 | N1 | treated_lumber | 1 | 8 386 205.00 | 270 | 5 130.00 | 32 384.00 | 33 333.33 | 86.30 |
| 1 000 000 000 | N1 | high_purity_silicon | 10 | 343 001 039.47 | 409 | 29 952.00 | 39 872.00 | 40 300.00 | 781.77 |
| 1 250 | N2 | titanium_components | 1 | 1 240.00 | 4 | 54.00 | 60.00 | 80.00 | 1.72 |
| 5 000 | N2 | aluminum_components | 1 | 4 515.00 | 8 | 100.00 | 120.00 | 120.00 | 3.13 |
| 10 000 | N2 | clothing | 1 | 9 765.00 | 12 | 150.00 | 30.00 | 40.00 | 4.34 |
| 50 000 | N2 | rubber_blend_components | 1 | 49 505.00 | 30 | 468.00 | 360.00 | 360.00 | 6.55 |
| 100 000 | N2 | biofuel | 1 | 97 075.00 | 60 | 820.00 | 120.00 | 120.00 | 7.63 |
| 500 000 | N2 | membrane_components | 1 | 496 490.00 | 144 | 2 100.00 | 1 060.00 | 1 200.00 | 14.19 |
| 1 000 000 | N2 | treated_lumber | 1 | 999 230.00 | 143 | 2 507.00 | 8 576.00 | 9 333.33 | 21.18 |
| 10 000 000 | N2 | treated_lumber | 1 | 8 604 950.00 | 300 | 5 250.00 | 17 984.00 | 18 666.67 | 86.98 |
| 1 000 000 000 | N2 | chemical_components | 10 | 248 686 174.61 | 510 | 25 967.50 | 16 544.00 | 16 900.00 | 577.95 |
| 1 250 | N3 | phosphoric_acid | 1 | 1 095.00 | 2 | 40.00 | 120.00 | 120.00 | 1.52 |
| 5 000 | N3 | tire_components | 1 | 4 975.00 | 6 | 100.00 | 120.00 | 120.00 | 3.45 |
| 10 000 | N3 | clothing | 1 | 9 970.00 | 12 | 150.00 | 90.00 | 120.00 | 4.43 |
| 50 000 | N3 | construction_frames | 1 | 49 410.00 | 38 | 484.00 | 240.00 | 240.00 | 6.80 |
| 100 000 | N3 | industrial_insulation | 1 | 98 590.00 | 60 | 815.00 | 300.00 | 320.00 | 7.82 |
| 500 000 | N3 | membrane_components | 1 | 483 710.00 | 140 | 2 055.00 | 2 100.00 | 2 200.00 | 13.96 |
| 1 000 000 | N3 | treated_lumber | 1 | 999 230.00 | 143 | 2 507.00 | 8 576.00 | 9 333.33 | 21.18 |
| 10 000 000 | N3 | treated_lumber | 1 | 8 604 950.00 | 300 | 5 250.00 | 17 984.00 | 18 666.67 | 86.98 |
| 1 000 000 000 | N3 | chemical_components | 10 | 251 494 591.36 | 510 | 25 967.50 | 33 088.00 | 33 150.00 | 584.48 |

Die Diversitätsverbesserung ist nicht durchgehend: bei Level 25 und $1 Mio. liegen N0 175, N1 191, N2 105 und N3 85 Produktstrategien innerhalb von 20 %. Bei $1 Mrd. sind es 40/51/157/148. Bei $1 250 mit vorausgesetzten Level-25-Unlocks sind es 45/29/10/6. Die ungleichen zugelassenen Produktzahlen in kleinen Budgets resultieren aus Finanzierbarkeit. Ein N3-Sieg im gewichteten Querschnitt rechtfertigt daher keine Aussage über allgemeine Meta-Freiheit. Auch Startergeschenke können eine frühe Strategie begünstigen; Ersatzkapital und Cashbudget beantworten verschiedene Fragen.

## 9. Echter Genesis-Start mit $1 250

Alle acht Gegenprüfungen starten mit dem unveränderten tatsächlichen Anfangszustand: $1 250, den vorhandenen Anfangswaren (145 Iron Ore, 70 Coal, 88 Copper Ore), geschenkten Gebäuden und acht Starterkarten, den neun Anfangsproduktionen. Keine fertige Firma wird kostenlos eingesetzt. Ein Flour-Harvester wird bezahlt. Processor-Rezepte werden erst nach tatsächlich produzierter Lifetime-Menge freigeschaltet. Karten, Slots und Zusatzenergie werden mit den bestehenden Spielkommandos gekauft und nur bei ausreichendem Geld installiert. Kein RP, keine seltenen Karten, keine Upgrades. Zeitschritt eine Sekunde.

Deterministische Vergleichspolitik: Ziel ist die Verarbeitung der vollen 120 Rohstoffeinheiten/min; vorhandene freie Processors zuerst verwenden, notwendige Energie und Freight finanzieren; überschüssige Rohstoffproduktion ab 600 Lagereinheiten pausieren. Es wird nur der Zielverkauf exportiert, nach dem ersten Rohstoffverkauf auf das Zielprodukt umgestellt. Das ist ein nachvollziehbarer Vergleichspfad, keine bewiesene optimale Genesis-Strategie. Einnahmen enthalten anfängliche echte Rohstoffverkäufe.

| Modell | Produkt | Min | Kasse $ | Verdient $ | Investiert $ | Letztes Fenster $/min | Processors | Trucks | Company-Level |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | iron | 10 | 3 058.58 | 1 808.58 | 0.00 | 180.86 | 1 | 2 | 1 |
| N0 | iron | 30 | 7 860.18 | 6 610.18 | 0.00 | 240.08 | 1 | 2 | 2 |
| N0 | iron | 60 | 15 062.58 | 13 812.58 | 0.00 | 240.08 | 1 | 2 | 2 |
| N0 | iron | 120 | 29 467.38 | 28 217.38 | 0.00 | 240.08 | 1 | 2 | 3 |
| N0 | flour | 10 | 4 204.81 | 5 119.82 | 2 165.00 | 511.98 | 6 | 3 | 2 |
| N0 | flour | 30 | 21 010.81 | 21 925.81 | 2 165.00 | 840.30 | 6 | 3 | 3 |
| N0 | flour | 60 | 46 219.81 | 47 134.81 | 2 165.00 | 840.30 | 6 | 3 | 3 |
| N0 | flour | 120 | 96 637.82 | 97 552.82 | 2 165.00 | 840.30 | 6 | 3 | 4 |
| N1 | iron | 10 | 3 058.58 | 1 808.58 | 0.00 | 180.86 | 1 | 2 | 1 |
| N1 | iron | 30 | 7 860.18 | 6 610.18 | 0.00 | 240.08 | 1 | 2 | 2 |
| N1 | iron | 60 | 15 062.58 | 13 812.58 | 0.00 | 240.08 | 1 | 2 | 2 |
| N1 | iron | 120 | 29 467.38 | 28 217.38 | 0.00 | 240.08 | 1 | 2 | 3 |
| N1 | flour | 10 | 2 493.36 | 1 788.36 | 545.00 | 178.84 | 1 | 3 | 2 |
| N1 | flour | 30 | 7 294.36 | 6 589.36 | 545.00 | 240.05 | 1 | 3 | 2 |
| N1 | flour | 60 | 14 495.86 | 13 790.86 | 545.00 | 240.05 | 1 | 3 | 3 |
| N1 | flour | 120 | 28 898.86 | 28 193.86 | 545.00 | 240.05 | 1 | 3 | 4 |
| N2 | iron | 10 | 3 058.58 | 1 808.58 | 0.00 | 180.86 | 1 | 2 | 1 |
| N2 | iron | 30 | 7 860.18 | 6 610.18 | 0.00 | 240.08 | 1 | 2 | 2 |
| N2 | iron | 60 | 15 062.58 | 13 812.58 | 0.00 | 240.08 | 1 | 2 | 2 |
| N2 | iron | 120 | 29 467.38 | 28 217.38 | 0.00 | 240.08 | 1 | 2 | 3 |
| N2 | flour | 10 | 2 662.36 | 1 752.36 | 340.00 | 175.24 | 1 | 2 | 2 |
| N2 | flour | 30 | 7 463.36 | 6 553.36 | 340.00 | 240.05 | 1 | 2 | 2 |
| N2 | flour | 60 | 14 664.86 | 13 754.86 | 340.00 | 240.05 | 1 | 2 | 3 |
| N2 | flour | 120 | 29 067.86 | 28 157.86 | 340.00 | 240.05 | 1 | 2 | 4 |
| N3 | iron | 10 | 3 058.58 | 1 808.58 | 0.00 | 180.86 | 1 | 2 | 1 |
| N3 | iron | 30 | 7 860.18 | 6 610.18 | 0.00 | 240.08 | 1 | 2 | 2 |
| N3 | iron | 60 | 15 062.58 | 13 812.58 | 0.00 | 240.08 | 1 | 2 | 2 |
| N3 | iron | 120 | 29 467.38 | 28 217.38 | 0.00 | 240.08 | 1 | 2 | 3 |
| N3 | flour | 10 | 2 662.36 | 1 752.36 | 340.00 | 175.24 | 1 | 2 | 2 |
| N3 | flour | 30 | 7 463.36 | 6 553.36 | 340.00 | 240.05 | 1 | 2 | 2 |
| N3 | flour | 60 | 14 664.86 | 13 754.86 | 340.00 | 240.05 | 1 | 2 | 3 |
| N3 | flour | 120 | 29 067.86 | 28 157.86 | 340.00 | 240.05 | 1 | 2 | 4 |

Für jeden Messpunkt wurde `Kasse=1250+verdiente Erlöse−Investitionen` geprüft. Iron richtet den ersten Processor nach 60 Sekunden ein; normiertes Flour ebenfalls. N0-Flour erreicht alle sechs Processors erst bei Sekunde 252 und finanziert zwischenzeitlich aus echten Einnahmen nach. Der Genesis-Unterschied zeigt außerdem, weshalb gratis Harvester oder sechs gratis Processors den Early-Game-Vergleich verfälschen würden. Ereignisse und Zahlungsstände stehen in `genesis-events.csv`. Die sehr hohen N0-Flour-C-Erlöse sind der Arbeitswertüberkompensation aus Abschnitt 5 geschuldet, keine Empfehlung, die aktuellen Livepreise zu ersetzen.

## 10. Engine-Gegenprüfungen, Puffer und Produktionsstabilität

Verwendet wird die vorhandene `SimulationEngine` mit unveränderlichen Offline-Kopien der Maschinendefinitionen. Nur Inputs/Outputs der Kopien und der Marktpreistabelle im privaten Analyseprozess werden gesetzt und anschließend zurückgesetzt. Energie- und Freight-Definitionen bleiben identisch. Der Adapter erzeugt valide, nach der diskreten Optimierung bezahlte Gebäude-/Linien-/Slotzustände; mature Unlocks sind ausdrücklich vorausgesetzt, Lager starten leer. Kein persönlicher Save wird geladen.

Je N0–N3 und 17 Beispielen wurden zwei Stunden bei sechs Sekunden Schrittweite gemessen, mit Marken nach 10/30/60/120 Minuten: 544 Datensätze, jeweils mit und ohne Versuchssteuerung. Die Steuerung benutzt existierende Pause-Kommandos, eine kumulative Sollproduktionsmenge sowie Zwischenpuffer von mindestens drei summierten Verbraucherchargen. Für Endware muss zusätzlich ein Versandpuffer mindestens `(Fahrzeugzahl+1) × Fahrzeugladung` bestehen. Ein Puffer von bloß drei kleinen Produktionschargen kann die Flotte unterversorgen, obwohl deren nominale Kapazität genügt.

Diese Steuerung ist **nur ein experimenteller Kommandotrace**, keine im Spiel implementierte Automatik. Für gemischte Produktionsketten müsste der Spieler entsprechend disponieren; eine spätere automatische Warenzuteilung wäre eine gesonderte Entwicklungsentscheidung. Die bestehende Engine stellt gemeinsame Inputs nicht automatisch fair zwischen konkurrierenden Maschinen zu.

Die reine katalogabhängige Arbeitswertberechnung wird im Offline-Harness wiederverwendet; unabhängig wurde sie für jedes Modell und alle 353 Produkte gegen den vorhandenen `ProductionValueCalculator` geprüft. Kein Spielzustand oder Engine-Übergang wird dabei ersetzt. Zwölf zusätzliche 600-Sekunden-Paare mit Schritten von 1 und 6 Sekunden (Iron, Flour, AI Server je Modell) ergeben identische Verkaufserlöse; Lagerstände können sich aufgrund des Kontrollzeitpunkts unterscheiden. Dies kalibriert die physische Lieferrechnung, **nicht** identische XP- oder Progressionszeitverläufe. Genesis benutzt deshalb dt=1.

| Modell | Kontrollierte Ketten | Min./Max. Ist/Ziel letzte Stunde | Storage-full-Statuszählungen | Unkontrolliert ohne Verkauf nach 120 min |
| --- | --- | --- | --- | --- |
| N0 | 17 | 0.9975 / 1.0026 | 0 | industrial_equipment, microchip, ai_server |
| N1 | 17 | 0.9975 / 1.0026 | 0 | industrial_equipment, ai_server |
| N2 | 17 | 0.9985 / 1.0027 | 0 | industrial_equipment, microchip, ai_server |
| N3 | 17 | 0.9985 / 1.0004 | 0 | industrial_equipment, microchip, ai_server |

Statuszählungen summieren Maschinenzustände je Zeitschritt; sie sind weder Zahl unterschiedlicher Stoppepisoden noch Sekunden. Ein fehlender Verkauf kann durch Input-Starvation vor einem vollen Lager entstehen. Besonders Iron-Verarbeiter können gemeinsames Ore konsumieren, bevor Steel-/Folgerezept-Verbraucher ihre Charge erhalten. Mathematisch zusammengeführte Teilkapazitäten brauchen daher Scheduling. Das vollständige Vollkarten-Versorgungsszenario in der CSV weist zusätzliche vorgelagerte Karten aus, kann aber danach andere positive Überschüsse erzeugen.

| Modell | Produkt ohne Steuerung | Liefermenge 120 min | Lager / Kapazität | Storage-full-Zähler | Missing-input-Zähler |
| --- | --- | --- | --- | --- | --- |
| N0 | industrial_equipment | 0.00 | 57 625 / 75 280 | 0 | 3608 |
| N0 | microchip | 0.00 | 67 232 / 75 280 | 0 | 2407 |
| N0 | ai_server | 0.00 | 75 270 / 75 280 | 39 | 3613 |
| N1 | industrial_equipment | 0.00 | 45 639 / 75 280 | 0 | 3608 |
| N1 | microchip | 591.00 | 49 853 / 75 280 | 0 | 1209 |
| N1 | ai_server | 0.00 | 63 048 / 75 280 | 0 | 3008 |
| N2 | industrial_equipment | 0.00 | 37 252 / 75 280 | 0 | 3608 |
| N2 | microchip | 0.00 | 50 451 / 75 280 | 0 | 2406 |
| N2 | ai_server | 0.00 | 60 053 / 75 280 | 0 | 3607 |
| N3 | industrial_equipment | 0.00 | 44 440 / 75 280 | 0 | 3608 |
| N3 | microchip | 0.00 | 54 045 / 75 280 | 0 | 2406 |
| N3 | ai_server | 0.00 | 63 647 / 75 280 | 0 | 3607 |

Auch für alle übrigen Beispiele enthalten die Engine-Daten volle Liefermengen, ersten Verkauf, Lager, Statuszählungen, Investitionen und Nettoerlös zu jedem Zeitpunkt. Die Nachweise gelten für diese 17 Ketten je Variante und zwei Stunden, nicht für sämtliche 353 Produkte, beliebige gemischte Firmen, manuelle Eingriffe oder Offline-Catchup. Insbesondere Brennstoffketten, historisch gespeicherte laufende Batches und Contract-/Consortium-Zahlungswege wurden nicht unter neuen Rezepten simuliert.

## 11. MK1–MK99, Rarity, Research und Preisempfindlichkeit

Bestehende Skalierung: MK-Faktor `M=1+(MK−1)/4`, also MK99=25,5. Produktionsoutput q×M×(1+b/100), Input a×M, angeforderte Leistung P×M×(1+b/200). Gleichmäßiger MK aller Stufen erhält damit die Kartenverhältnisse; Rarity erhöht die Materialeffizienz und verändert die nachgelagerten Verhältnisse. Beispielsweise ist Rare +10 % und Legendary +20 % hier eine konkret untersuchte Bonusausprägung, keine pauschale Definition aller Karten dieser Seltenheit.

`mk-rarity-research.csv` enthält 15 Kartenfamilien × 99 MK × drei konkrete Bonuswerte × zwei Researchzustände = 8 910 Skalierungsfälle. Der volle Katalogzustand besitzt 645 freigeschaltete Nodes ohne Produktspezialisierungen: Produktionsgeschwindigkeit 1,08, Energieoutput 1,11, Freightkapazität 1,11, Lagerkapazität 1,25. Es ist ein isolierter Mechaniktest mit gesetzter Research-Allokation, **kein finanziertes oder durchgespieltes Unternehmen**. Alle Budget- und Genesisvergleiche nutzen null Research. Produktionsgeschwindigkeit verkürzt Zyklen, erhöht damit Materialdurchsatz und verlangte Versandrate; sie erhöht nicht automatisch die installierte Nennleistung. Werteffekte und Produktspezialisierungen müssten in einem darauf gerichteten Budgetvergleich zusätzlich bepreist werden.

Die Formeln gelten auf unveränderte Basismengen aller vier Modelle; Rarity-Vorprodukteffizienz wird bei der rekursiven Rechnung je Stufe berücksichtigt. Nur die unten genannten Common-MK99-Ketten wurden zusätzlich wirklich simuliert. Für gemischte Qualitäten/MKs, Spezialresearch, fractional Inputs und extreme Speicherfüllungen ist dies kein vollständiger Engine-Beweis.

Die drei MK99-Beispiele je Modell erhalten vollständig **vorfinanzierte** aktuelle Upgradequotes. Erklärung des Kapitalzustands: mature Company-Level 25, alle nötigen Lifetime-Unlocks zuvor verdient, verfügbares Endgame-Kapital $1 Billion (10^12), keine geschenkten Upgrades, keine Research-/Rarityboni. Die Investitionen liegen tatsächlich darunter; es wird nicht behauptet, diese Firma aus Genesis erreicht zu haben. Rohstoffdurchsatz 3 060/min, also dieselbe Basis ×25,5.

| Modell | Common MK99 | Bezahlt $ | Factory | MW | Ziel/min | Gemessen $/min | Ist/Ziel |
| --- | --- | --- | --- | --- | --- | --- | --- |
| N0 | iron | 926 051 372.96 | 1 | 357.00 | 1 530.00 | 6 122.04 | 1.0000 |
| N0 | flour | 1 597 053 884.55 | 6 | 918.00 | 3 060.00 | 21 427.65 | 1.0000 |
| N0 | ai_server | 7 341 760 349.60 | 10 | 3 927.00 | 39.00 | 9 971.74 | 1.0026 |
| N1 | iron | 926 051 372.96 | 1 | 357.00 | 1 530.00 | 6 122.04 | 1.0000 |
| N1 | flour | 517 683 331.02 | 1 | 280.50 | 3 060.00 | 6 121.28 | 1.0000 |
| N1 | ai_server | 7 129 101 207.58 | 9 | 3 621.00 | 39.00 | 7 153.75 | 1.0026 |
| N2 | iron | 926 051 372.96 | 1 | 357.00 | 1 530.00 | 6 122.04 | 1.0000 |
| N2 | flour | 481 507 081.08 | 1 | 280.50 | 1 530.00 | 6 121.27 | 1.0000 |
| N2 | ai_server | 7 129 101 207.58 | 9 | 3 621.00 | 33.63 | 6 819.13 | 0.9985 |
| N3 | iron | 926 051 372.96 | 1 | 357.00 | 1 530.00 | 6 122.04 | 1.0000 |
| N3 | flour | 481 507 081.08 | 1 | 280.50 | 1 530.00 | 6 121.27 | 1.0000 |
| N3 | ai_server | 7 129 101 207.58 | 9 | 3 621.00 | 100.88 | 6 819.13 | 0.9985 |

Alle MK99-Firmen liefern im letzten Fenster ungefähr ihre Zielrate; leichte Überschreitungen stammen aus in diesem Fenster abgebauten Puffern und diskreten Frachten. Keine Rate wird deshalb künstlich oberhalb der langfristigen Kapazität angesetzt. Die zweite Stunde allein amortisiert die hohen Endgame-Upgrades nicht.

**Upgrade-Neuquotierung:** 5 880 Schattenquotes (4 Modelle × 15 Familien × 98 Übergänge) wenden die unveränderte Upgradeformel auf hypothetische Definitionen und die jeweiligen C-Preise an. Sie stehen in `mk-requote-sensitivity.csv`. Das ist ausdrücklich ein anderer Vergleich als die Budgetsuche mit heutigen, eingefrorenen Quotes. Eine spätere tatsächliche Rezept-/Preisumstellung könnte dadurch Upgradepreise und Budgetrangfolgen zusätzlich verändern; diese Kombination wurde nicht als neue optimale Budgetsuche ausgegeben.

**Arbeitswertsensitivität:** Primary bleibt $1; nur verarbeitende Maschinenarbeit wird mit $90/$120/$150 bewertet, Energie weiterhin $0,01/MW-Minute. 4 236 Produktpreise und zwölf Querschnittszusammenfassungen wurden berechnet. Folgende Zahlen bewerten die Rendite auf **Ersatzkapital bei gleichem Rohstoffdurchsatz**, nicht dasselbe Kriterium wie die Cashbudgetsuche. Branchenfaktor hier: höchster/niedrigster Branchenmittelwert der Rendite.

| Modell | Arbeit $/min | Innerhalb 10/20/30 % | Branchenmittel-Renditefaktor |
| --- | --- | --- | --- |
| N0 | 90 | 8/16/38 | 3.48 |
| N0 | 120 | 5/16/33 | 3.64 |
| N0 | 150 | 5/16/27 | 3.76 |
| N1 | 90 | 2/5/25 | 2.59 |
| N1 | 120 | 2/4/17 | 2.53 |
| N1 | 150 | 2/4/8 | 2.52 |
| N2 | 90 | 4/7/50 | 2.75 |
| N2 | 120 | 4/6/49 | 2.70 |
| N2 | 150 | 4/4/12 | 2.67 |
| N3 | 90 | 4/7/53 | 2.75 |
| N3 | 120 | 4/7/51 | 2.70 |
| N3 | 150 | 4/7/13 | 2.66 |

Für Iron bei 120 Rohstoffeinheiten/min gilt Cash_C=120+L+0,08; für N0-Flour 120+6L+0,30, für normiertes Flour 120+L+0,05. Arbeitswertänderungen können Renditen und Branchenspreizung verändern, aber kein physisches Kartenverhältnis korrigieren. Der Preisparameter sollte daher erst **nach** der Rezeptentscheidung final kalibriert werden; $120/$0,01 bleiben Untersuchungsparameter.

## 12. Auswirkungen und Umstellungsaufwand

**Factory/Energie:** N1 reduziert im gemeinsamen Rohstoffquerschnitt den mittleren Factory-Bedarf um etwa 23 % und die angeforderte Leistung um etwa 15 %. N2/N3 reduzieren Factory um etwa 24 %, Leistung ebenfalls etwa 15 %. Bei späteren höheren Mengen wirken aufgerundete Slots und teurer werdende Gebäude nicht linear. Kein Hallenlimit wurde für diese Analyse wieder eingeführt.

**Freight:** N1 erhält finalen Materialoutput bei gleicher Rohstoffzufuhr, verschiebt jedoch die Produktionskonzentration auf weniger Karten. Flour benötigt bei voller Harvesterverarbeitung weiterhin 120 Versandplätze/min und drei Trucks. N2/N3-Flour braucht 60/min und zwei Trucks, erzielt unter C aber ungefähr dieselben $240/min; der Wert je transportierter Einheit verdoppelt sich gegenüber N1. Auf oberen Stufen wirken die Templates mehrfach. Eine pauschale Aussage, standardisierte Outputs machten Freight überall fair, ist daher falsch; diskrete Cargo- und Reisezeiten, Wertdichte und Versandpuffer bleiben relevant.

**Fabrication/Assembly:** Alle rekursiven Folgen sind neu gerechnet. N1 erhält die Rohstoffmengen pro Endware, senkt aber Maschinenarbeit und deshalb C-Werte. N2/N3 verändern Inputanteile, Ausbeuten und Wertdichten über mehrere Stufen. N3 6/6/3 erhöht nicht bloß losgelöst finale Outputs: die Inputmengen nachgelagerter Rezepte werden aus den neuen Vorgängeroutputs gebildet. Das verhindert einen kostenlosen isolierten Outputbonus, garantiert aber keine semantische Plausibilität oder Branchenfairness.

**Steuerung:** Die normierten Modelle entfernen einfache Kapazitätsanomalien, nicht Ressourcenpriorität, volle Lager oder unpassende Versandpuffer. Alle drei komplexen Beispielketten Industrial Equipment, Microchip und AI Server sind unter den getesteten gerundeten Layouts besonders steuerungssensitiv; die Tabellen zeigen tatsächliche Ausfälle und keine bloße Vermutung. Größere vollständig versorgte ganzzahlige Anlagen sind eine Alternative mit höheren Kosten, bleiben bei Überschuss aber ohne Pause oder Zwischenverkauf nicht beliebig lange stabil.

**Eine spätere Migration müsste gesondert entscheiden:** laufende Produktionsfortschritte und bereits reservierte/verzehrte Batchinputs; neue Outputmengen laufender Batches; alte Warenbestände und deren sofortige Neubewertung; eingefrorene Freight-/Contract-/Consortium-Angebote; Lifetime-Unlocks, Mastery, XP und Zeit bis zum nächsten Unlock; heutige Factory-Layouts und vorhandene Karten; MK-Upgradequotes und Research-Spezialisierungen. Sechs bestehende Flour-Processors würden unter N1 den Bedarf eines alten Harvesters weit übersteigen; einfach Mengen auszutauschen kann alte Unternehmen blockieren. Eine kontrollierte Pause/Übernahme laufender Chargen wäre ein Migrationsentwurf, der in dieser Phase ausdrücklich nicht implementiert wurde.

Die produktive Datenladepipeline leitet außerdem Brennstoff-/Nuclear-Balancing aus Vorproduktdefinitionen ab. Der Offlinevergleich hält die bestehenden Energy-Definitionen bewusst fest, damit nur Rezepte verglichen werden. Eine spätere Änderung der Quelldaten samt erneutem Release-Balancing kann daraus zusätzliche Uranium-/Fuel-Ratenfolgen erzeugen. Diese Kombination ist vor einer Umsetzung gesondert zu prüfen; die erneuerbaren Engine-Beispiele belegen sie nicht.

## 13. Ausdrückliche Antworten auf die 18 Entscheidungsfragen

1. **Wie viele auffällige aktuelle Verhältnisse?** Unter 37 eindeutigen Ein-Primärinput-Rezepten verlangen 18 mindestens drei Verarbeiter je Rohstoffkarte; Maximum sechs. Das ist die belastbare einfache Auffälligkeitszahl. Alle 304 Rezepte wurden zusätzlich nach Leerlauf, Slots, Energie, Kapital und Überschuss bewertet, ohne unterschiedliche komplexe Zutaten pauschal als Fehler zu zählen.
2. **Welche Produkte besonders?** Die vollständige einfache Liste und die wirtschaftlich priorisierten 20 Ketten stehen in Abschnitt 4. Flour, Corn Meal und andere kleine Primärverarbeitungsbatches sind anschauliche Strukturbeispiele; komplexe Endwaren erben solche Effekte rekursiv. Die Rangliste misst Kapitalwirkung bei gleicher finaler Menge und erhaltener Materialausbeute.
3. **Tatsächlicher Flour-Nachteil?** Sechs statt einem Processor, fünf zusätzliche Factory-Plätze und 22 MW mehr gegenüber Iron bei voller Verarbeitung von 120 Rohstoffeinheiten/min; $2 100 zusätzliche eingesetzte Karten-/Slotkosten einschließlich Freight, Genesis $2 165 statt $0. Kein technischer Zwang, sechs zu bauen: ein Processor verarbeitet lediglich ein Sechstel des Harvesters. C kann den Nachteil in Erlösen überkompensieren.
4. **Sinnvolle Mengenverhältnisse?** Für einfache Primärverarbeitung eine Rohstoffkarte zu ungefähr einer Verarbeitungskarte bei sechs Sekunden. 12→12 erhält Flour-Ausbeute, 12→6 senkt Versandmenge und verdoppelt Stückwert unter C. Die Wahl ist eine Material-/Frachtentscheidung; beide benötigen passende Preise.
5. **Alle einfachen Rezepte vereinheitlichbar?** Ja: N1 erreicht 1–1,5 ohne Ausbeuteänderung; N2/N3 genau 1:1 für alle 37. Strikte Gleichheit unter Erhalt jedes ursprünglichen Bruchverhältnisses und kleiner Ganzzahlen ist nicht überall gleichzeitig erreichbar.
6. **Mehrinputrezepte?** Jede Zutat separat dimensionieren, gemeinsame Vorprodukte erst nach Ressourcen-ID aggregieren, dann ganze Karten runden. N2/N3 erhalten Zutaten und unterscheiden Haupt-/Nebenlasten; kein Teilen der Gesamtzutatenmenge pauschal durch 120. Plausibilität der Rohstoffrelationen bleibt ein zusätzlicher Designentscheid.
7. **Gemeinsame Vorlagen?** N1 ganzzahlige gemeinsame Durchsatzskalierung bis Faktor sechs; N2 Outputs 6/3/1, Lastanteile 1/½/¼; N3 unter denselben Regeln 6/6/3. Alle Mengen stehen vollständig in den CSVs.
8. **Wie stark unterscheiden sie sich?** N1 178, N2 294, N3 302 veränderte Rezepte. Nur N1 erhält alle Materialausbeuten. N2/N3 haben im 120-Rohstoffquerschnitt dieselben mittleren Factory-/MW-Anforderungen, aber unterschiedliche Endmengen, Stückpreise und Freightkosten.
9. **Welches reduziert Factory-Platz?** Alle drei. Mittel N0 7,477, N1 5,737, N2/N3 5,674 Karten je Folgeproduktkette im gemeinsamen Querschnitt. N1 erreicht den Großteil der Einsparung bei kleinerem Eingriff; Einzelfallvergleich und spätere Erweiterungszustände bleiben nötig.
10. **Größte Branchenvielfalt?** Kein durchgehender Gewinner. Level 25/$1 Mio. gewinnt N1 nach 20-%-Produktkonkurrenz, $1 Mrd. N2; kleine Budgets können N0 bevorzugen. Das sind begrenzte Kapazitätssuchen, keine globale Fairnessbeweise. Die N3-Zielfunktion ist nicht gleichbedeutend mit allen späteren Diversitätsmaßen.
11. **Freight?** N1-Flour weiter 120/min, drei Trucks; N2/N3 60/min, zwei Trucks. C-Stückwert N1 rund $2, N2/N3 rund $4. Wertdichte, ganzzahlige Flotten und reale Fahrtzyklen verhindern eine allgemeine Freight-Fairnessgarantie.
12. **Energie?** Flour 36→11 MW, Iron bleibt 14. Gesamtmittel N0 105,99, N1 90,35, N2/N3 89,75 MW im deklarierten Querschnitt. Erzeugerkarten, Slots, Gebäude und konkrete Ausgangsgeschenke sind eingepreist.
13. **Höhere Stufen?** Alle 353 Ketten neu bewertet; N1 senkt Arbeit pro Einheit bei erhaltener Materialmenge. N2/N3 verändern zusätzlich Ausbeuten rekursiv. Voll ausgelastete ganzzahlige Blöcke, überlappende Inputs und Scheduling bleiben gerade bei Assembly relevant.
14. **Was löst C?** Einheitliche rekursive Bewertung von Rohstoffbasis, tatsächlichen Inputwerten, eigener Arbeit und Energie; transparente positive zusätzliche Verarbeitungswertschöpfung ohne willkürliche alte Preisanker. Arbeitswertsensitivität zeigt, dass Renditespreizung beeinflussbar ist.
15. **Was braucht Rezeptänderungen?** Unintuitive Verhältnisse, überflüssige Parallelkarten, physischer Slot-/Leistungsbedarf und Batch-/Transportmengen. Ein höherer Verkaufspreis schafft weder Platz noch weniger zu bedienende Karten und kann ineffiziente Struktur sogar honorieren.
16. **Welche brauchen zusätzliche Steuerung?** In den getesteten minimal gerundeten Layouts besonders Industrial Equipment, Microchip und AI Server; geteilte Vorprodukte, ungleiche Auslastung und Flottenpuffer sind die Ursachen. Die bestehenden Pause-Kommandos reichen im Offlineversuch aus. Eine produktive Automatik wäre eine separate Voraussetzung für dieselbe Bedienungsfreiheit, keine bereits vorhandene Funktion dieser Analyse.
17. **Empfehlung?** N1 als nächste konservative Designbasis prüfen: alle Materialrelationen bleiben erhalten, die 18 einfachen Extreme verschwinden, Flour 6→1 und ein großer Teil der Karten-/MW-Einsparung wird erreicht. Anschließend C-Arbeitswert und Freight anhand ausgewählter realer Spielfirmen kalibrieren. Wenn ausdrücklich einheitliche Ausbeuten gewünscht sind, N2 als bewussten weitergehenden Entwurf verwenden. N3 wegen seines begrenzten Zielfunktionssieges nicht automatisch übernehmen.
18. **Implementierungsrisiken?** Laufende Chargen, Bestandswerte, bestehende überdimensionierte Layouts, Upgradequotes, Lifetime-/XP-Progression, Research, eingefrorene Verträge, Brennstoffableitungen und fehlende automatische faire Inputverteilung. Die Zweistunden-Gegenproben ersetzen weder Save-Migration noch vollständige Langzeit-/Portfolio-/Contracttests.

## 14. Verifikation, Artefakte und Reproduzierbarkeit

Vor Abschluss wurden **5,077 zuvor bestehende Dateien per SHA-256 unverändert bestätigt**: produktiver Code/Daten, Tests, vorhandene Skripte und Dokumentation, die fünf persönlichen Spielstände sowie 4 083 Dateien bestehender Windows-Builds. Persönliche Saves wurden ausschließlich byteweise gehasht, nicht geladen. Es wurde kein Build erstellt und kein vorhandener Test verändert. Der vorherige Stand von 1 998 Tests und 16/16 Migrationen ist ein übernommener Projektbaselinewert, **kein neu ausgeführter Testlauf dieser reinen Offlinephase**. Neu geprüft wurden die hier beschriebenen Katalog-, Graph-, Rechen-, Infrastruktur- und Engine-Invarianten.

| Nachweis | Ergebnis |
| --- | --- |
| Produkte / Folgeprodukte | 353 / 304 eindeutige IDs in beiden geforderten CSVs |
| Graph | 708 Zutatenkanten in jedem Modell, identische Zutatenidentitäten; topologisch berechenbar, kein Zyklus/fehlender Input |
| Mengen/Preise | positive endliche Outputs, Inputs und Zeiten; endliche positive C-Preise; Primary unverändert |
| Preis-/Work-Gegenprobe | N0: 353 C-Preise wie P11-C; alle Modelle: 353 Engine-Work-Werte stimmen |
| Infrastruktur | alle Kurven 1–512 rekonstruiert und monoton, echte Kostenfunktionen |
| Budgetsuche | 15,576 finanzierbare Produktfälle in 108 Budget-/Level-/Modellkohorten |
| Engine | 544 MK1-Zeitpunkte, 12 dt-Kalibrierungen, 32 echte Genesis-Zeitpunkte, 48 bezahlte MK99-Zeitpunkte |
| Skalierung | 8 910 MK/Rarity/Research-Fälle; 5 880 Schatten-Upgradequotes; 4 236 Arbeitswertpreise |
| Bestandsschutz | 5,077 identische SHA-256; null veränderte geschützte Dateien |

Die beiden geforderten CSVs enthalten JSON-Zellen für Rezepte, direkte Inputraten, Kartenverhältnisse, rekursive Kartenlisten, Leerlauf, Überschüsse, Bottlenecks und voll ausgelastete Blöcke. Die Ketten-CSV besitzt zusätzlich vollständige finanzierte Pläne und Rohstoff-/Zwischenproduktmengen. `all_integer_cards`/`all_fractional_cards` und `capacity-detail` beziehen sich auf eine finale Vollkarte; `standard_*` und `standard_plan` auf 120 aggregierte Rohstoffeinheiten/min. Diese Bezugsgrößen dürfen nicht ungeprüft vermischt werden. `current_price_A` ist nur die heutige Referenz; Vergleichserlöse verwenden konsequent neu berechnetes C.

Die marginale Factory-Erweiterung, Cash pro Factory-Platz und Cash pro investiertem Dollar stehen in der Ketten-CSV; per Beispiel wurde die reale gesamte Payback-Obergrenze angegeben. Große vollständige Kartenblöcke sind exakte Bruchrechenresultate und können weit außerhalb der Budgetsuchgrenze liegen; sie sind kein behaupteter optimierter Bauplan.

Weitere Daten liegen ausschließlich in `artifacts/phase11d`: `models.json`, `chain-long.csv`, `capacity-detail.csv`, `n3-candidates.csv`, `n3-selection.json`, `budget-search.csv`, `budget-summary.csv`, `engine-validation.csv`, `step-calibration.csv`, `genesis.csv`, `genesis-events.csv`, `mk99-engine.csv`, `labour-sensitivity.csv`, `labour-summary.csv`, `mk-rarity-research.csv`, `mk-requote-sensitivity.csv`, `baseline.json`, `static-proof.json`, `engine-proof.json`, `completion-proof.json`. Zwei ältere lokale Pufferdiagnosen bleiben als Diagnoseartefakte erhalten; sie sind nicht die finalen Messergebnisse.

Reproduktion aus dem Projektordner mit vorhandener Python-Umgebung (NumPy wird aus dem bereits vorhandenen P11-C-Auditpfad eingebunden; keine neue produktive Abhängigkeit):

```powershell
.\.venv\Scripts\python.exe -B artifacts/phase11d/analysis.py prepare
.\.venv\Scripts\python.exe -B artifacts/phase11d/analysis.py search
.\.venv\Scripts\python.exe -B artifacts/phase11d/engine.py
.\.venv\Scripts\python.exe -B artifacts/phase11d/genesis.py
.\.venv\Scripts\python.exe -B artifacts/phase11d/audit.py
.\.venv\Scripts\python.exe -B artifacts/phase11d/mk99.py
.\.venv\Scripts\python.exe -B artifacts/phase11d/report.py
```

Die Infrastruktur-/Portfoliosuche kann gegenüber einer echten globalen Optimierung konservative Grenzen besitzen; die Engine-Ergebnisse sind dagegen konkrete beobachtete Lieferungen der gewählten Layouts. Bei später geänderten produktiven Dateien schlägt die Bestandsschutzprüfung gegen die gespeicherte Baseline absichtlich fehl. Nicht erneuern, um Abweichungen zu verdecken.

## 15. Stopp und anstehende Entscheidung

Die Offline-Untersuchung ist beendet. N0 bleibt das produktive Spiel. Es wurden keine Rezepte, Preise, Maschinenkosten, Save-Schemata, Produktionsfunktionen oder automatischen Steuerungen implementiert und keine Windows-Builds erzeugt. Die Entscheidungsvorlage empfiehlt N1 zur fachlichen Prüfung; erst eine gesondert freigegebene Folgephase dürfte daraus eine produktive Umsetzung mit Migration und finalem Preisbalancing machen.
