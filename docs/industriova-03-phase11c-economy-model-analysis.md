# P11-C – mathematische Wirtschaftsmodelle und Entscheidungsvorlage

Stand 23.10.2026. Ausschließlich Offline-Analyse. Alle 353 Originalpreise und Gameplaywerte unverändert. Factory-Gebäude nach Teil A ohne globales Kaufcap. Quellen: vollständige P11-A/P11-B-Berichte und CSVs plus aktuelle produktive Funktionen. Eingabe-SHA256 und reine Katalogcache-Gleichheitsprüfung in artifacts/phase11c/proof.json.

## 1. Fragestellung und Dominanz

Vergleichbare Strategien haben dasselbe Budget, zulässigen Level-/Unlock-/Researchzustand, Qualitätszugang und Zeithorizont. Pareto-Dominanz bedeutet in allen betrachteten Zielen mindestens gleich gut und in mindestens einem strikt besser. Ein höherer Stückpreis, Lastmaschinenumsatz oder höhere Rendite bei mehr Kapital ist allein kein Dominanzbeweis. Markt bleibt fest; kein Nachfrageabschlag, keine Steuer oder Zufallsmarktmechanik vorgeschlagen.

Die Untersuchung umfasst **4375** dimensionierte Einproduktfirmen über zehn Budgets, Levelkohorten 1/5/25 und Common-MK1/10/50/99, daneben 156 echte Engine-Messpunkte, 105 Genesis-Messpunkte und 9531 statische Qualitäts-/Research-/Contractquotes. Levelkohorten sind vorverdiente Lifetime-Freischaltungen ohne Research; sie sind ausdrücklich keine neu gestarteten Firmen mit kostenlos erspieltem Fortschritt. Echter P10-Neustart wird separat simuliert.

## 2. Drei vollständige Schattenpreislisten

A: produktive BASE_MARKET_PRICES unverändert. B: alle 49 Primäranker=1, danach ausschließlich vorhandenes build_fixed_prices mit allen übrigen Ankern und Rundungen. C: Primärprodukte=1; für jedes Folgeprodukt rekursiv

    pC(output) = Summe(a_i*pC(input_i))/q + 120*t/(60*q) + 0.01*P*t/(60*q)

q=Output/Zyklus, a_i=Inputs/Zyklus, t=Sekunden, P=Rezept-MW. 120 Dollar je Maschinenminute wird aus normiertem Primary-Umsatz 120 U/min × 1 Dollar abgeleitet. 0.01 Dollar je MW-Minute ist ein ausdrücklich gewählter **Bewertungsparameter**, keine reale Stromrechnung und kein nachgewiesener optimaler Energietarif. Alte Mindestanker entfallen vollständig. Die Summe enthält schon bewertete Vorarbeit; hinzu kommen nur eigene Maschinenminute und eigener Leistungseinsatz. Kein Zählen von Zutatenarten und kein erneutes Addieren des gesamten Rohstoffwerts. Parallelität entsteht über echte Inputmengen und dimensionierte Karten, nicht einen pauschalen Mehrzutatenbonus.

C belohnt jede Verarbeitung mit positivem zusätzlichem Warenwert, garantiert aber nicht positiven Cashflow nach zusätzlichen Investitionen. Die Parameter sind eine transparente Testhypothese, keine abschließend identifizierte Preisformel. All-Research- und Rarityänderungen wirken später auf dieselben Basispreise; nicht erneut in die Preisrekursion zählen.

| Produkt | A heute | B Primary=1 mit Ankern | C Arbeit/Energie |
|---|---|---|---|
| iron_ore | 1.0 | 1.0 | 1.0 |
| copper_ore | 1.4 | 1.0 | 1.0 |
| crude_oil | 2.2 | 1.0 | 1.0 |
| platinum_ore | 5.8 | 1.0 | 1.0 |
| wheat | 0.95 | 1.0 | 1.0 |
| iron | 3.75 | 3.75 | 4.001333333333333 |
| steel | 10.0 | 10.0 | 6.753 |
| lumber | 1.8125 | 1.8125 | 5.001666666666667 |
| flour | 1.625 | 1.625 | 7.0025 |
| biodiesel | 29.9119 | 29.4919 | 78.71399999999998 |
| microchip | 147.55 | 147.55 | 138.09333333333333 |
| industrial_equipment | 45.1603 | 44.7403 | 61.64305 |
| ai_server | 299.1375 | 299.1375 | 255.0318 |

B lässt **191/353** heutige Preise exakt unverändert. Das allein widerlegt die Erwartung, dass uniforme Primary-Preise automatisch alle Folgeproduktrelationen reparieren. A-Primärspreizung: Platinum 5.8 gegenüber Wheat 0.95 = 6.105263-facher Preis bei identischer Basisrate/Leistung; Crude Oil 2.2× und Copper 1.4× Iron Ore. Spätere Company-Level und Nutzen als Vorprodukt sind reale unterschiedliche Eigenschaften, beseitigen aber im freigeschalteten Rohstoffverkauf diese nominale Erlösspreizung nicht.

CSV docs/industriova-03-phase11c-price-model-comparison.csv enthält je Produkt alle drei Preise, absolute/prozentuale Deltas, direkte Inputwerte und Wertschöpfung/Zyklus und zusätzlicher Maschinenminute. Die CSV enthält außerdem eine vollständig bepreiste 1-U/min-Zielhülle mit allen Kartenanzahlen, Stromerzeugern und Freight. Diese ist ein nomineller Flussplan; tatsächlicher Betrieb braucht die dokumentierte Steuerung und Unlocks. Rekursive Arbeitszeit und MW-Minuten stammen aus den realen Mengen und Rezeptleistungen; Rohstoffmengen und vollständige Vorproduktion sind ebenfalls je Zeile enthalten.

## 3. Optimierungsmodell, diskrete Investitionen und Schranken

Netzflussbedingungen: Für jedes Produkt i muss eigener Ausstoß plus Anfangspuffer mindestens internen Verbrauch plus Verkauf erfüllen. Dauerleistung wird ohne Anfangswaren gerechnet. Zyklusfluss f_i <= Karten_i * MK-/Rarity-Outputrate; Karten sind ganzzahlig. Ganze angeforderte MW müssen durch Generatoren passen. Gebäude/Slots sind diskret und verursachen die originalen Kurvenkosten, ohne Factorycap. Freight gilt nur für verkaufte Endwaren, nicht interne Zwischenprodukte. Cargo und Reisezeit folgen den realen Regeln. Global Storage ist ein Batchpuffer, kein Produktionsmultiplikator.

Hier verwendetes nachvollziehbares Näherungsverfahren: vollständige Enumeration aller zulässigen Einprodukt-Zielketten; zusammengeführte gemeinsame Vorprodukte; ganzzahlige Karten durch Aufrundung benötigter Raten; vier uniforme MK-Alternativen; Solar oder Wind, jeweils günstigere vollständige Quote; alle vier reinen Freightflotten, jeweils günstigere Quote, eine erweiterbare Anlage. Kompakte Belegung der vorhandenen und zusätzlichen Gebäude. Startergutschrift: drei Extractor, zwei Processor, ein Solar, zwei Trucks, kostenlose Startgebäude der drei Primary-Typen/Factory/Energy/Garage. Jede zusätzliche Karte, Upgrade, Gebäude-, Linien-, Slot- und Lagererweiterung wird bezahlt. Gepufferter Bedarf konservativ als Summe ganzer gleichzeitig zugeordneter Chargen; Fuelkraftwerke sind nicht Teil dieser statischen Suchfamilie, ihre Mechanik bleibt aus P11-B dokumentiert.

Die beste finanzierbare Rate wird je Familie monoton eingeklammert und zwölfmal halbiert; Rate-Stützraum bis zur letzten Zweierpotenz 1048576 Einheiten/min. Dies ist ein **Analyseraster**, kein neues Spielcap. Nicht global durchsucht: Firmen mit mehreren verkauften Produkten, gemischte MK pro Karte, Fuel-/Generator-/Flottenmixe, anders aufgeteilte Gebäude, beliebige Steuerungs- und Reinvestitionspolitiken. Es wird daher ausdrücklich kein globales Optimum behauptet.

Zusätzliche obere Schranke: Infrastruktur, Strom und Freight kostenfrei relaxieren, Karten bruchzahlig zulassen und je Rezept günstigste Kosten/Ratenrelation aus den vier MK-Stufen verwenden. Einheitenkapital aus der gesamten Vorproduktion addieren; alle Starterkarten mit insgesamt 2160 Common-Ersatzwert großzügig als Kapitalgutschrift ansetzen. Obergrenze=(Budget+2160)*max(p/Einheitenkapital). Das ist für diesen Common-/MK-Zustandsraum eine optimistische Relaxation, nicht ein finanzierbarer Plan. Die ausgewiesenen Lücken umfassen weit mehr als das kleine Ratenraster und erlauben keinen Beweis globaler Branchenfairness.

## 4. Budget-, Stufen- und Branchenvergleich

Budgets 1250/5000/10000/50000/100000/500000/1000000/10000000 sowie 1 Milliarde und 1 Billion. Alle Level-1-/5-Ergebnisse separat in Ergebnisdateien; hier Level 25 mit vorverdienten Unlocks, kein Research. Prozentabweichung=100*(1−Cashrate/zulässige beste gefundene Cashrate). Referenz stets derselbe Budget-/Level-/Modellraum, nicht Level 1 gegen voll freigeschaltete Firma.

| Budget | Level | Modell | bestes Muster | nominal $/min | 2D-Pareto | innerhalb 20% | Relaxationslücke % |
|---|---|---|---|---|---|---|---|
| 1250 | 25 | A | gold | 1282.5 | 4 | 5 | 81.62731317625645 |
| 1250 | 25 | B | gold | 1282.5 | 4 | 3 | 64.65770047527555 |
| 1250 | 25 | C | rare_earth_metals | 600.3599999999999 | 6 | 45 | 63.13053662641737 |
| 5000 | 25 | A | platinum | 2892.75 | 4 | 6 | 80.26361731843575 |
| 5000 | 25 | B | platinum | 2892.75 | 4 | 4 | 62.03445065176909 |
| 5000 | 25 | C | magnetic_components | 1360.9199999999998 | 7 | 91 | 60.19578889960658 |
| 10000 | 25 | A | platinum | 4959.0 | 7 | 3 | 80.078125 |
| 10000 | 25 | B | platinum | 4959.0 | 6 | 3 | 61.67763157894737 |
| 10000 | 25 | C | asphalt_components | 2288.0899999999997 | 14 | 85 | 60.59521386454434 |
| 50000 | 25 | A | platinum_ore | 18560.0 | 7 | 3 | 82.61758691206545 |
| 50000 | 25 | B | platinum | 13224.0 | 7 | 3 | 76.1758691206544 |
| 50000 | 25 | C | marine_components | 6604.099999999999 | 17 | 228 | 73.48537405377334 |
| 100000 | 25 | A | platinum_ore | 34800.0 | 7 | 3 | 83.35943617854346 |
| 100000 | 25 | B | gold | 21375.0 | 7 | 3 | 80.33848189452651 |
| 100000 | 25 | C | bioplastic | 10856.55 | 25 | 224 | 77.74536892119038 |
| 500000 | 25 | A | platinum_ore | 104400.0 | 21 | 3 | 89.84387446232277 |
| 500000 | 25 | B | gold | 64125.0 | 20 | 3 | 88.0001153636978 |
| 500000 | 25 | C | high_purity_silicon | 27377.28 | 19 | 225 | 88.58285205514098 |
| 1000000 | 25 | A | platinum_ore | 125280.0 | 12 | 3 | 93.89319070807056 |
| 1000000 | 25 | B | platinum | 82650.0 | 14 | 3 | 92.25007317527474 |
| 1000000 | 25 | C | high_purity_silicon | 38024.0 | 21 | 175 | 92.05433622820485 |
| 10000000 | 25 | A | platinum_ore | 271440.0 | 14 | 3 | 98.6742863541475 |
| 10000000 | 25 | B | gold | 171000.0 | 14 | 3 | 98.39345046297586 |
| 10000000 | 25 | C | treated_lumber | 81031.5 | 19 | 141 | 98.30343881183296 |
| 1000000000.0 | 25 | A | platinum_ore | 2714214.4 | 15 | 3 | 99.86740935306247 |
| 1000000000.0 | 25 | B | platinum | 1813010.4000000001 | 13 | 4 | 99.82963076799754 |
| 1000000000.0 | 25 | C | treated_lumber | 848393.8026666667 | 5 | 226 | 99.82233331627181 |
| 1000000000000.0 | 25 | A | catalyst_components | 28075730.7392 | 17 | 43 | 99.99862848442088 |
| 1000000000000.0 | 25 | B | catalyst_components | 27995444.0192 | 17 | 44 | 99.9973692524935 |
| 1000000000000.0 | 25 | C | network_components | 21656741.43786667 | 41 | 212 | 99.99546473616118 |

Hohe MK und viele Factory Halls werden tatsächlich bepreist, nicht als Gratisstart gesetzt. In den Endgame-Stützpunkten:

| Budget | Modell | bestes Muster | MK | Factory-Karten | benötigte Hallen | Investition |
|---|---|---|---|---|---|---|
| 1000000000.0 | A | platinum_ore | 10 | 0 | 0 | 995913088.0799999 |
| 1000000000.0 | B | platinum | 10 | 1350 | 27 | 985034976.35 |
| 1000000000.0 | C | treated_lumber | 10 | 1450 | 29 | 947457727.99 |
| 1000000000000.0 | A | catalyst_components | 50 | 10100 | 202 | 996443260066.0999 |
| 1000000000000.0 | B | catalyst_components | 50 | 10100 | 202 | 996443260066.0999 |
| 1000000000000.0 | C | network_components | 50 | 8879 | 178 | 999643931826.4701 |

MK99 wurde mit sämtlichen Übergangskosten untersucht, muss deshalb nicht der Renditesieger sein. Unterschiedliche wirtschaftlich sinnvolle MK-Stufen statt automatisch höchstem MK sind ein Ergebnis, kein ausgelassener Zustand.

Branchenstreuung der jeweils besten gefundenen Endproduktfirma je Research-Domain:

| Budget | Modell | stärkste Domain | schwächste Domain | Faktor best/schwach | schwächste Domain Rückstand % |
|---|---|---|---|---|---|
| 1250 | A | metals | agriculture | 7.286931818181818 | 86.27680311890839 |
| 1250 | B | metals | agriculture | 8.015625 | 87.5243664717349 |
| 1250 | C | metals | rail | 2.020216975798853 | 50.50036644679858 |
| 5000 | A | metals | textiles | 6.049361029379473 | 83.46932849364791 |
| 5000 | B | metals | textiles | 7.053148224003745 | 85.8219341457091 |
| 5000 | C | electronics | aerospace | 1.5110713859426566 | 33.821789671692656 |
| 10000 | A | metals | agriculture | 6.802469135802469 | 85.2994555353902 |
| 10000 | B | metals | agriculture | 6.802469135802469 | 85.2994555353902 |
| 10000 | C | construction | medical | 1.8097016917435211 | 44.74227412383254 |
| 50000 | A | metals | agriculture | 5.2727272727272725 | 81.03448275862068 |
| 50000 | B | metals | forestry | 4.1325 | 75.80157289776164 |
| 50000 | C | maritime | oil_gas | 1.222329572376214 | 18.18900380066927 |
| 100000 | A | metals | agriculture | 5.272727272727272 | 81.03448275862068 |
| 100000 | B | metals | oil_gas | 3.5625 | 71.9298245614035 |
| 100000 | C | chemicals | oil_gas | 1.2917574912427658 | 22.586088582468644 |
| 500000 | A | metals | agriculture | 5.2727272727272725 | 81.03448275862068 |
| 500000 | B | metals | oil_gas | 3.5625 | 71.9298245614035 |
| 500000 | C | electronics | textiles | 1.2845765121549528 | 22.15333298267761 |
| 1000000 | A | metals | agriculture | 5.272727272727272 | 81.03448275862068 |
| 1000000 | B | metals | oil_gas | 3.826388888888889 | 73.86569872958258 |
| 1000000 | C | electronics | textiles | 1.3381005334947427 | 25.26719966337051 |
| 10000000 | A | metals | agriculture | 5.272727272727272 | 81.03448275862068 |
| 10000000 | B | metals | oil_gas | 3.6538461538461537 | 72.63157894736842 |
| 10000000 | C | forestry | textiles | 1.2673667318872202 | 21.096240350974625 |
| 1000000000.0 | A | metals | agriculture | 4.5952540903673205 | 78.23841771674338 |
| 1000000000.0 | B | metals | oil_gas | 3.44375 | 70.96188747731398 |
| 1000000000.0 | C | forestry | textiles | 1.202706527181177 | 16.854196979895576 |
| 1000000000000.0 | A | metals | oil_gas | 5.697525992461887 | 82.44852237053327 |
| 1000000000000.0 | B | metals | oil_gas | 5.681233071066583 | 82.39818737427257 |
| 1000000000000.0 | C | electronics | oil_gas | 2.752665187988672 | 63.67157166939421 |

Alle 15 Domains einschließlich Metalle/Edelmetalle, Oil/Gas/Chemie, Landwirtschaft/Food/Biodiesel, Elektronik/Semiconductors, Maschinenbau, Energie-/Erneuerbarentechnik und komplexe Assembly sind in artifacts/phase11c/industry-comparison.csv einzeln ausgewiesen. Keine Preisrelation wird als vollständiger Unternehmensvergleich ausgegeben. Processing/Fabrication-Rezeptabweichungen gehen durch q/t/P direkt ein. Zusätzliche Gebäudezahlen und MK können den Gewinner ändern; frontiers.csv enthält die Gewinner je Kohorte, nicht eine universelle Meta.

Pareto: frontiers.csv ist die zweidimensionale Kosten-/Cashratenfront. pareto-multidimensional.csv betrachtet zusätzlich MW, Factory-Karten, erforderlichen Level und Basisreisezeit; damit wird bloße höhere Rendite bei anderen Nachteilen nicht pauschal als Dominanz bezeichnet. Dies sind vollständige Fronten des genannten Kandidatenraums, nicht aller im Spiel denkbaren Unternehmen. Lifetime-Erspielzeit bleibt dort eine nicht quantifizierte Voraussetzung.

## 5. Echte Engine-Gegenprüfung

Reale SimulationEngine bei 1-s-Schritten, vollständige unveränderte Input-/Output-/Fuel-/Storage-/Dispatch-/Arrival-Transitions. Ein vorhandener Offlinecache ersetzt ausschließlich wiederholte reine Katalogarbeitswerte nach 353 Gleichheitsprüfungen. Keine GameState-Ergebnisse werden gecacht. Shadowpreise werden nur im isolierten Python-Prozess für die Marktlesefunktion eingesetzt und im finally zurückgesetzt; keine Preisdatei oder Spielsave wird geändert. Verschiedene Modelle erhalten dieselben Anfangsbedingungen.

Bei diesen Maturity-Firmen sind Inputs anfangs leer und benötigte Unlocks vorverdient. Tabellenrate ist eine kontinuierliche **Obergrenze**, nicht ein verkaufter Output. Es gibt kein automatisches Lastfolgemanagement; überschüssige Zwischenprodukte können Lagerblockaden erzeugen. Das ist gerade ein Gegenbeispiel zur Gleichsetzung von Netzflusskapazität und nachhaltiger realer Steuerung. Für sehr große Suchfirmen wird die Engine-Stichprobe ausdrücklich auf die separat bepreiste 1-U/min-Zielhülle verkleinert, statt ungemessenes Budgetwachstum zu behaupten.

| Produkt | Modell | Minuten | Nominal $/min | real $/min seit Start | Cash minus Investition |
|---|---|---|---|---|---|
| iron_ore | A | 120.0 | 40.0 | 39.43333333333333 | 4732.0 |
| iron_ore | B | 120.0 | 40.0 | 39.43333333333333 | 4732.0 |
| iron_ore | C | 120.0 | 40.0 | 39.43333333333333 | 4732.0 |
| copper_ore | A | 120.0 | 56.0 | 55.20666666666667 | 6624.8 |
| copper_ore | B | 120.0 | 40.0 | 39.43333333333333 | 4732.0 |
| copper_ore | C | 120.0 | 40.0 | 39.43333333333333 | 4732.0 |
| crude_oil | A | 120.0 | 88.0 | 86.75333333333333 | 10070.4 |
| crude_oil | B | 120.0 | 40.0 | 39.43333333333333 | 4392.0 |
| crude_oil | C | 120.0 | 40.0 | 39.43333333333333 | 4392.0 |
| platinum_ore | A | 120.0 | 232.0 | 228.7133333333333 | 27445.6 |
| platinum_ore | B | 120.0 | 40.0 | 39.43333333333333 | 4732.0 |
| platinum_ore | C | 120.0 | 40.0 | 39.43333333333333 | 4732.0 |
| wheat | A | 120.0 | 38.0 | 37.461666666666666 | 4155.4 |
| wheat | B | 120.0 | 40.0 | 39.43333333333333 | 4392.0 |
| wheat | C | 120.0 | 40.0 | 39.43333333333333 | 4392.0 |
| iron | A | 120.0 | 150.0 | 147.6875 | 17722.5 |
| iron | B | 120.0 | 150.0 | 147.6875 | 17722.5 |
| iron | C | 120.0 | 160.05333333333334 | 157.5858444444444 | 18910.30133333333 |
| steel | A | 120.0 | 400.0 | 393.6666666666667 | 46870.0 |
| steel | B | 120.0 | 400.0 | 393.6666666666667 | 46870.0 |
| steel | C | 120.0 | 270.12 | 265.8430999999997 | 31531.171999999962 |
| lumber | A | 120.0 | 54.375 | 53.5140625 | 6081.6875 |
| lumber | B | 120.0 | 54.375 | 53.5140625 | 6081.6875 |
| lumber | C | 120.0 | 150.05 | 147.674208333333 | 17380.904999999962 |
| flour | A | 120.0 | 32.5 | 31.985416666666666 | 3498.25 |
| flour | B | 120.0 | 32.5 | 31.985416666666666 | 3498.25 |
| flour | C | 120.0 | 140.05 | 137.83254166666637 | 16199.904999999966 |
| biodiesel | A | 120.0 | 149.55949999999999 | 147.31610749999973 | 14972.932899999967 |
| biodiesel | B | 120.0 | 147.4595 | 145.2476075000004 | 14724.71290000005 |
| biodiesel | C | 120.0 | 393.56999999999994 | 387.66644999999977 | 43814.97399999997 |
| microchip | A | 120.0 | 368.875 | 330.75791666666635 | 33660.94999999996 |
| microchip | B | 120.0 | 368.875 | 330.75791666666635 | 33660.94999999996 |
| microchip | C | 120.0 | 345.23333333333335 | 309.5592222222227 | 31117.106666666718 |
| industrial_equipment | A | 120.0 | 451.603 | 444.4526191666674 | 47064.314300000085 |
| industrial_equipment | B | 120.0 | 447.40299999999996 | 440.31911916666564 | 46568.29429999988 |
| industrial_equipment | C | 120.0 | 616.4305 | 606.6703504166676 | 66530.44205000011 |
| ai_server | A | 120.0 | 373.921875 | 0.0 | -8520.0 |
| ai_server | B | 120.0 | 373.921875 | 0.0 | -8520.0 |
| ai_server | C | 120.0 | 318.78975 | 0.0 | -8520.0 |

Die Tabellen zeigen kumulierte reale Cashrate seit Start, nicht allein den letzten idealisierten Zyklus. Beobachtungszeitpunkte 10/30/60/120 Minuten, inklusive erster Lieferverzögerung. Negative Werte Cash minus Investition bedeuten im beobachteten Horizont keine Amortisation. Eine behauptete ewige Amortisation aus einem kurzen Lauf wäre unzulässig.

### Zusätzlicher Steuerungs-Gegenversuch

Mit unverändertem PauseMachines-Command hält ein isolierter Offlinecontroller jedes Vorprodukt bei ungefähr drei Inputchargen, prüft sekündlich und pausiert/resumiert die vorhandenen Karten. Dies ist eine untersuchte Betriebsstrategie, keine neue Spielfunktion oder behauptete normale Anfängerbedienung. Bei gleicher 1-U/min-Zielhülle liefert die echte Engine nach 120 Minuten:

| Produkt | Modell | gelieferte Einheiten/min | Lagerbestand am Ende |
|---|---|---|---|
| biodiesel | A | 4.924999999999991 | 162.0 |
| biodiesel | B | 4.924999999999991 | 162.0 |
| biodiesel | C | 4.924999999999991 | 162.0 |
| microchip | A | 2.4583333333333335 | 313.0 |
| microchip | B | 2.4583333333333335 | 313.0 |
| microchip | C | 2.4583333333333335 | 313.0 |
| industrial_equipment | A | 9.841666666666681 | 352.0 |
| industrial_equipment | B | 9.841666666666681 | 352.0 |
| industrial_equipment | C | 9.841666666666681 | 352.0 |
| ai_server | A | 1.225 | 368.0 |
| ai_server | B | 1.225 | 368.0 |
| ai_server | C | 1.225 | 368.0 |

Die nominelle Zielrate 1 ist eine Dimensionierungsvorgabe, nicht die volle Kapazität der aufgerundeten ganzen Karten. Tatsächlicher Durchsatz darf sie deshalb überschreiten. Die vorherigen Nominalobergrenzen wurden aus allen real installierten Karten, Vorproduktmengen und Freight separat berechnet. Vergleich ohne Steuerung: AI Server verkauft im beobachteten Horizont null bei nahezu vollem Lager; mit bedarfsgerechter Steuerung wird Output geliefert. Das kann eine Preisänderung allein nicht reparieren. Für alle drei Schattenpreise werden dieselben realen Ankünfte bei festen Preisen exakt umbewertet; keine drei unterschiedlichen Materialflüsse vorgetäuscht.

## 6. Echter P10-Neustart und dynamische Investition

Original _create_initial_state mit 1250 Cash, drei Primary-Startstandorten, unplatzierten acht Starterkarten, echten Anfangswaren und Initialunlocks. Installation, Zukäufe, Freightslots, Routing und Verarbeitung über vorhandene Commands. Wenn Lifetime-Unlocks tatsächlich verdient werden, kann ein vorhandener Processor eingesetzt werden. Vergleich direkte Rohstofflieferung gegen Iron/Copper/Flour-Verarbeitung, zusätzlich Crude-Oil-Start ohne geschenkte Drilling-Karte. Reinvestitionsregel: jede Minute bei ausreichendem Cash Truck und nötigen Slot kaufen, höchstens vier Trucks in dieser bewusst begrenzten Politik. Das ist kein Spielcap und keine optimale Politik. Alle Ausgabenzeitpunkte stehen in investment-events.csv. Keine vorab geschenkte Research-/Legendary-/MK99-Firma.

| Rohstoff | Verarbeitung | Modell | Sekunden | Cash | verbuchte Einnahmen | Investitionen | Trucks |
|---|---|---|---|---|---|---|---|
| iron_ore | False | A | 7200 | 15097.0 | 14317.0 | 470.0 | 4 |
| iron_ore | False | A | 28800 | 58297.0 | 57517.0 | 470.0 | 4 |
| iron_ore | True | A | 7200 | 27252.5 | 26472.5 | 470.0 | 4 |
| iron_ore | True | A | 28800 | 108252.5 | 107472.5 | 470.0 | 4 |
| copper_ore | False | A | 7200 | 20744.0 | 19964.0 | 470.0 | 4 |
| copper_ore | False | A | 28800 | 81224.0 | 80444.0 | 470.0 | 4 |
| copper_ore | True | A | 7200 | 31683.25 | 30903.25 | 470.0 | 4 |
| copper_ore | True | A | 28800 | 126183.25 | 125403.25 | 470.0 | 4 |
| crude_oil | False | A | 7200 | 31644.8 | 31204.8 | 810.0 | 4 |
| crude_oil | False | A | 28800 | 126684.8 | 126244.79999999999 | 810.0 | 4 |
| wheat | False | A | 7200 | 13914.8 | 13474.8 | 810.0 | 4 |
| wheat | False | A | 28800 | 54954.8 | 54514.8 | 810.0 | 4 |
| wheat | True | A | 7200 | 4275.05 | 3835.05 | 810.0 | 4 |
| wheat | True | A | 28800 | 15975.05 | 15535.05 | 810.0 | 4 |
| iron_ore | False | B | 7200 | 15097.0 | 14317.0 | 470.0 | 4 |
| iron_ore | False | B | 28800 | 58297.0 | 57517.0 | 470.0 | 4 |
| iron_ore | True | B | 7200 | 27252.5 | 26472.5 | 470.0 | 4 |
| iron_ore | True | B | 28800 | 108252.5 | 107472.5 | 470.0 | 4 |
| copper_ore | False | B | 7200 | 15040.0 | 14260.0 | 470.0 | 4 |
| copper_ore | False | B | 28800 | 58240.0 | 57460.0 | 470.0 | 4 |
| copper_ore | True | B | 7200 | 31651.25 | 30871.25 | 470.0 | 4 |
| copper_ore | True | B | 28800 | 126151.25 | 125371.25 | 470.0 | 4 |
| crude_oil | False | B | 7200 | 14624.0 | 14184.0 | 810.0 | 4 |
| crude_oil | False | B | 28800 | 57824.0 | 57384.0 | 810.0 | 4 |
| wheat | False | B | 7200 | 14624.0 | 14184.0 | 810.0 | 4 |
| wheat | False | B | 28800 | 57824.0 | 57384.0 | 810.0 | 4 |
| wheat | True | B | 7200 | 4276.25 | 3836.25 | 810.0 | 4 |
| wheat | True | B | 28800 | 15976.25 | 15536.25 | 810.0 | 4 |
| iron_ore | False | C | 7200 | 15097.0 | 14317.0 | 470.0 | 4 |
| iron_ore | False | C | 28800 | 58297.0 | 57517.0 | 470.0 | 4 |
| iron_ore | True | C | 7200 | 29021.384000000086 | 28241.384000000082 | 470.0 | 4 |
| iron_ore | True | C | 28800 | 115450.18400000171 | 114670.1840000017 | 470.0 | 4 |
| copper_ore | False | C | 7200 | 15040.0 | 14260.0 | 470.0 | 4 |
| copper_ore | False | C | 28800 | 58240.0 | 57460.0 | 470.0 | 4 |
| copper_ore | True | C | 7200 | 29021.384000000086 | 28241.384000000082 | 470.0 | 4 |
| copper_ore | True | C | 28800 | 115450.18400000171 | 114670.1840000017 | 470.0 | 4 |
| crude_oil | False | C | 7200 | 14624.0 | 14184.0 | 810.0 | 4 |
| crude_oil | False | C | 28800 | 57824.0 | 57384.0 | 810.0 | 4 |
| wheat | False | C | 7200 | 14624.0 | 14184.0 | 810.0 | 4 |
| wheat | False | C | 28800 | 57824.0 | 57384.0 | 810.0 | 4 |
| wheat | True | C | 7200 | 16891.864999999874 | 16451.864999999867 | 810.0 | 4 |
| wheat | True | C | 28800 | 67309.86499999941 | 66869.86499999935 | 810.0 | 4 |

Die Tabelle verwendet zur eindeutigen Verknüpfung Simulationssekunden (7200=120 Minuten, 28800=480 Minuten). Anfangswaren bleiben als einmalige Ausstattung gekennzeichnet und werden nicht auf Dauer hochgerechnet. Produktpreise und Starterkartenasymmetrie sind getrennte Einflüsse.

## 7. Verarbeitung, Opportunitätskosten und Investitionshorizonte

Pro Zyklus zusätzlicher Warenwert=q*pOutput−Summe(a*pInput). Dieser Delta ist kein automatisch vereinnahmter Cashbetrag: unverkaufte Inputs, ungenutzte Freightplätze und zusätzliche Kartenkosten zählen. Für einen definierten Vergleich ist zusätzlicher Cashflow=vollständiger Kettenverkauf minus alternativ tatsächlich lieferbare Inputverkäufe; Payback=zusätzliche reale Investition / nachhaltig gemessener zusätzlicher Cashfluss, nur bei positivem Nenner. Gebäude-/Slot-Sprünge und benötigte Ganzkarten verhindern eine universelle Paybackzahl allein aus dem Rezept. Die realen Reinvestitions-/Verarbeitungswechsel oben liefern konkrete endliche Horizontvergleiche; sie sind kein Beweis optimaler Erweiterung jeder der 353 Ketten.

Zusätzlich sind alle 304 Verarbeitungsschritte in allen drei Modellen als vollständiger Kettenverkauf gegen Verkauf der direkten Vorprodukte bei gleichem rekursivem Inputfluss gerechnet: 912 Zeilen in processing-transitions.csv. Bezahlt werden jeweils diskrete Karten, Energie, vorhandene/nötige Plätze, homogene Freightflotten und Puffer. Dieselben schon vorhandenen Vorprodukte werden nicht doppelt gekauft. Gegenübergestellt werden zusätzliche Investition, Karten, angeforderte MW, realer externer Freight-Mengenbedarf und bedingte Mehrerlöse/Paybacks über 10/30/60/120/480 Minuten. Das ist ein kontinuierlicher, gesteuerter Flussvergleich, kein behaupteter tatsächlicher Contract- oder Engine-Ertrag jeder Kette.

| Produkt | Modell | zusätzliches Kapital | zusätzliche MW | Inputverkauf Freight U/min | bedingter Mehrerlös $/min | bedingter Payback min |
|---|---|---|---|---|---|---|
| iron | A | 0.0 | 8.0 | 2.0 | 1.75 | 0.0 |
| iron | B | 0.0 | 8.0 | 2.0 | 1.75 | 0.0 |
| iron | C | 0.0 | 8.0 | 2.0 | 2.001333333333333 | 0.0 |
| steel | A | 280.0 | 12.0 | 3.75 | 6.1 | 45.9016393442623 |
| steel | B | 280.0 | 12.0 | 3.75 | 6.25 | 44.8 |
| steel | C | 280.0 | 12.0 | 3.75 | 3.003 | 93.24009324009323 |
| lumber | A | 0.0 | 5.0 | 1.0 | 0.7124999999999999 | 0.0 |
| lumber | B | 0.0 | 5.0 | 1.0 | 0.8125 | 0.0 |
| lumber | C | 0.0 | 5.0 | 1.0 | 4.001666666666667 | 0.0 |
| flour | A | 0.0 | 5.0 | 1.0 | 0.675 | 0.0 |
| flour | B | 0.0 | 5.0 | 1.0 | 0.625 | 0.0 |
| flour | C | 0.0 | 5.0 | 1.0 | 6.0025 | 0.0 |
| microchip | A | 1060.0 | 12.0 | 2.0 | 25.10000000000001 | 42.23107569721114 |
| microchip | B | 1060.0 | 12.0 | 2.0 | 25.10000000000001 | 42.23107569721114 |
| microchip | C | 1060.0 | 12.0 | 2.0 | 12.012 | 88.24508824508824 |
| ai_server | A | 1035.0 | 12.0 | 3.0 | 55.9375 | 18.502793296089386 |
| ai_server | B | 1035.0 | 12.0 | 3.0 | 55.9375 | 18.502793296089386 |
| ai_server | C | 1035.0 | 12.0 | 3.0 | 12.012 | 86.16383616383617 |
| biodiesel | A | 280.0 | 12.0 | 2.0 | 5.0763 | 55.15828457734965 |
| biodiesel | B | 280.0 | 12.0 | 2.0 | 4.8963 | 57.186038437187264 |
| biodiesel | C | 280.0 | 12.0 | 2.0 | 12.012 | 23.310023310023308 |

Geringste aktuelle direkte Wertschöpfung je zusätzlicher Maschinenminute:

| Produkt | Stufe | A zusätzlicher $/Maschinenminute |
|---|---|---|
| soy_oil | Processing | 9.624999999999998 |
| soy_protein | Processing | 9.624999999999998 |
| raw_sugar | Processing | 13.0 |
| refined_sugar | Processing | 13.0 |
| corn_meal | Processing | 13.25 |
| flour | Processing | 13.5 |
| chlorine | Processing | 14.500000000000002 |
| ethanol_components | Fabrication | 14.610000000000005 |
| cotton_fiber | Processing | 14.75 |
| cellulose | Processing | 15.181999999999993 |
| starch | Processing | 15.25 |
| fermentation_feedstock | Processing | 15.25 |

C macht den direkten Arbeitszuschlag unabhängig von der Zahl verschiedener Zutaten. Das begrenzt rekursive Preisexplosion auf mengenmäßig erforderliche Maschinenarbeit plus bewertete Energiearbeit statt wiederholter willkürlicher Mindestanker. Hoher Preis komplexer Produkte ist trotzdem möglich, wenn viele reale Inputeinheiten pro Output benötigt werden. Ob das eingesetzte Kapital gerechtfertigt ist, entscheiden vollständige Firmen und Freight-/Zeithorizonte, nicht die positive Rezeptmarge allein.

## 8. Robustheit, Research, Rarity und Contracts

9531 Zeilen in sensitivity-contract-quotes.csv: alle Produkte/Modelle bei Common MK1/10/50/99, zulässigen Uncommon5/Rare10/Legendary20 und allen 645 Researchknoten ohne Produktspezialisierung. Das ist ein klar definierter reifer Researchzustand, kein normaler Anfänger. Quality-Investment unbekannt: kein garantierter Legendarypreis und keine faire Renditebehauptung ohne Qualitätsbeschaffung. Speed erhöht Output/Inputs, nicht MW; Rarity erhöht Output ohne entsprechenden Inputbonus. Freight-Rarity erhöht auch Reisezeit. Diese Asymmetrien können Rankings verschieben. Vier Produktspezialisierungen könnten zusätzlich 4 % je passendem Produkt geben, sind alternative Allokationen mit Respecbedingungen, kein Gratisbonus aller Produkte zugleich.

Persönliche Contractquotes werden über vorhandenes contract_cash_quote separat aus Basispreis und passenden value-/contract_value-Boni berechnet, Kategorieaufschläge 0/20/40 %. Consortium-Poolbeispiele benutzen höchstes berechtigtes Mitgliedspreisniveau und 15/25 %, ausdrücklich nicht voller Pool pro Contributor. Mengen/Angebote hängen von tatsächlicher Kapazität ab; Annahme/Beitrags-/Ablaufregeln und eingefrorene Quotes bleiben relevant. Diese Daten sind bedingte Quotes, keine simulierten Contract-Abschlüsse. Das Basissystem wird anhand Market bewertet; Contracts sind kein Reparaturmechanismus für Preisfehler.

## 9. Verbindliche Entscheidungsfragen

1. Rohstoffspreizung: identische 120 U/min, 6 MW, 340 Common-Kosten, aber A 0.95 Wheat bis 5.8 Platinum; nominal 114 bis 696 Dollar/min je Rohstoffkarte vor kompletter Infrastruktur/Fracht. Späteres Unlock ist ein Nachteil, keine Gleichheit nach verdienter Freischaltung.
2. Spätere Nachteile: unterschiedliche Inputmengen, Level/Lifetime-Gates, preisbedingt teure MK-Familien und konkreter zusätzlicher Kettenmix. Rohstoffverkauf und Nutzung als Input sind verschiedene Entscheidungen; sämtliche Mengen stehen je Produkt in CSV.
3. A kann nicht als bereits nachgewiesen fair gelten: obige Branchenfaktoren und Primärspreizung widersprechen einer pauschalen 10–20-%-Gleichheit. Dies ist keine Behauptung, jedes teure Produkt sei ein Fehler.
4. Über-/Unterbewertung ist zielabhängig. Die vollständige Vergleichstabelle zeigt auch Steel 10 gegenüber C 6.753, Lumber 1.8125 gegenüber C 5.001666666666667 und AI Server 299.1375 gegenüber C 255.0318. Anlagekosten-/Engine-Daten müssen zur Wertung dazugehören.
5. B löst die reine Rohstoffpreis-Asymmetrie, nicht die Ankerproblematik: 191 Preise bleiben exakt gleich.
6. Ein konsistentes Modell braucht mengen-/outputnormierte Inputwerte, inkrementelle Arbeit und getrennte wirtschaftliche Bewertung von Kapital, Energie und Liefereffekten; nicht nochmal komplette Vorarbeit addieren.
7. Arbeitszuschlag 120 Dollar/Maschinenminute ist eine normierte Testgröße aus 1-Dollar-Primary, kein empirisch als optimal bewiesener Satz.
8. Rekursion nur eigener Zusatzarbeit und Energie verhindert doppelte Vorarbeitszählung; feste manuelle Mindestanker in C entfallen. Die Inputmengen selbst können Preise weiterhin stark wachsen lassen.
9. Aus den Suchfirmen und Engine-Raten sichtbar: Ganzkarten/MW, teure Gebäude/Slots, Frachtreisezeit und Lager können Rendite stärker verändern als ein Stückpreis. Es gibt kein absolutes Firmenmaximum nach A.
10. MK99 bedeutet Faktor 25.5, aber tatsächliche Upgradeinvestitionen bis zu Milliarden je Familie. Die vier MK-Zustände wurden separat bezahlt; Gewinner können bei großem Kapital und Flächenkosten wechseln. Kein kostenloses MK99 angenommen.
11. Vergleichbar attraktive Branchen werden pro Budget/Kohorte mit Rückstand ≤20 % gezählt; Zahlen stehen in frontiers.csv und den Tabellen, nicht eine blanket Zusage für alle Domains.
12. Sinnvoll als nächste Designprüfung: normierte Primarybasis und ankerfreie, inkrementelle Wertbildung in C; danach gezielte Kalibrierung an tatsächlichen Anlagen-/Lieferpfaden. Keine automatische produktive Änderung empfohlen.
13. Bei festen Preisen und deterministischen Zuständen bleiben Optima möglich. Gleiche Arbeitsrendite, gleiches Anfangskapital, seltene Freischaltungen, Flächen-/Freightkosten und Spielvielfalt können nicht ohne weitere Zielgewichtung gleichzeitig identisch sein.
14. Empfehlung: **Modell C als nächste gemeinsam zu kalibrierende Schattenvariante; keine produktive Übernahme. Die Daten beweisen keine globale 10–20-%-Fairness.** B ist eine Kontrollvariante, A die nötige Referenz. Kein Modell D als vermeintliche Fairnessgarantie hinzugefügt.

## 10. Reproduzierbarkeit und Grenzen

Aus Projektwurzel mit der vorhandenen venv und -B: scripts/phase11c_economy.py, scripts/phase11c_sensitivity.py, scripts/phase11c_genesis.py, scripts/phase11c_controlled.py und scripts/phase11c_transitions.py; danach scripts/phase11c_reports.py. Regression: scripts/phase11c_regression.py. Resultate ausschließlich artifacts/phase11c und die drei geforderten Dokumente. Unterstützender SciPy/NumPy-Runtime liegt ausschließlich im Auditordner; das ausgeführte Verfahren benötigt ihn nicht und verändert keine Spielabhängigkeit.

Die Entscheidungsvorlage trennt vollständige 353-Produktdaten, begrenzte mathematische Kapazitätssuche, statische Sensitivitäten und tatsächliche Engine-Stichproben. Keine globale optimale Mischfirma, keine optimale dynamische Reinvestitionspolitik für alle Produkte und keine lückenlose langfristige Fairnessgarantie bewiesen. Die Relaxationslücken machen diesen Umfang sichtbar. Die Ergebnisse liefern konkrete Schattenpreise und überprüfbare Gegenbeispiele, keine verbindliche finale Preisentscheidung.

Produktiver Bestandsschutz und sämtliche Tests siehe separater Factory-Bericht. Alle fünf persönlichen Saves und bestehenden Builds unverändert. Nach den Berichten keine weitere Phase, keine Preisübernahme und kein Windows-Build.
