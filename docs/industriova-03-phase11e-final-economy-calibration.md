# INDUSTRIOVA – P11-E: Finale Wirtschaftskalibrierung N1 + C2

Stand: 23.10.2026. Finale Offline-Entscheidungsvorlage. Keine produktive Preis-, Rezept-, Kosten-, Engine-, Save- oder Buildänderung.

## 1. Entscheidung und Rangfolge

**Empfohlene feste Preisvariante: Primary $1; Processing $120, Fabrication $40, Assembly $120 je Maschinenminute; Energie-Wertparameter $0 je MW-Minute.** N1 ist exakt die P11-D-Rezeptreferenz mit 178 geänderten und 126 unveränderten Folgeproduktrezepten sowie 49 unveränderten Primärrezepten. Materialausbeuten und alle Zutatenidentitäten bleiben erhalten. Keine weitere Rezeptnormierung wurde vorgenommen.

Diese C2-Variante gewinnt den erklärten Kandidatenraum von 1 146 globalen Parameterkombinationen. Die Rangfolge berücksichtigt ausdrücklich Starterfirmen **und** zusätzliche Verarbeitung nach vollständig belegten Factory Halls. Eine nur auf Gratisplätzen bewertete Verarbeitung würde zu niedrige Arbeitszuschläge bevorzugen und spätere Erweiterungssprünge verdecken. Energieparameter null heißt kein separater Energieaufschlag im Warenpreis; reale Generatoren, Slots und Strombedarf bleiben vollständig in den Firmeninvestitionen enthalten. Es ist keine kostenlose Energieinfrastruktur und kein neuer Stromtarif.

**Gegenüber N0 mit aktuellen Preisen wird die Branchenkonkurrenz in den untersuchten Budget-/Levelkohorten deutlich breiter. Eine globale Fairnessgarantie besteht nicht.** Insbesondere kleine Budgets können nicht alle Branchen finanzieren; im sehr späten Endgame bleibt eine erhebliche Spreizung. Auch N1+C-Referenz wird nicht in jedem Einzelmaß und jeder Kohorte übertroffen.

**Freigabeempfehlung:** N1+C2 ist die konkrete Preis-/Rezeptbasis für eine Umsetzung, aber als isolierte Preisänderung noch keine ausreichende Endgame-Kalibrierung. Eine weitere globale Anpassung der MK-Preisformel einschließlich ihres Mindestpreisterms ist begründet. Keine zusätzliche Rezeptänderung und kein allgemeiner Domainbonus sind durch diese Daten notwendig. Für eine zugesagte Gesamtdauer muss außerdem die unten quantifizierte Schrittweitenabhängigkeit der bestehenden XP-Berechnung berücksichtigt werden. Diese Vorlage beendet die Offline-Designkalibrierung; sie implementiert keinen dieser Eingriffe.

## 2. Datenbasis und korrekt versorgte Firmen

Verwendet werden die vollständigen Berichte, CSVs und Berechnungswerkzeuge P11-A bis P11-D, die aktuellen produktiven Kosten-/Progressionsfunktionen und die exakten N1-Datensätze. Quellen samt SHA-256 und Abschnittsverzeichnis stehen in `artifacts/phase11e/source-reports.json`. P11-Bs altes 500-Kartenlimit gilt seit P11-C nicht mehr; die aktuelle unbegrenzte Hallenerweiterung mit je 50 regulären Plätzen ist Grundlage.

Für jede Zielkartenzahl werden **alle gleichzeitig aktiven Verbraucher im Vollbetrieb** gerechnet. Rückwärts durch den Graphen: benötigte Karten einer Ressource = aufgerundete Summe aller tatsächlichen Inputchargen ihrer Verbraucher / Outputcharge. Erst danach werden deren eigene Inputs propagiert. Dieses Verfahren unterscheidet sich vom Aufrunden einer Bruchmaschinenkette bei angenommener Teilzeitauslastung. Pro Ressourcentyp bleiben Supply, interner Verbrauch und positiver Verkaufssaldo getrennt.

Alle Ketten laufen Common, mit einer gemeinsamen MK-Stufe, sechs Sekunden Grundzyklus, ohne Research und ohne Maschinenpausen. Gleichmäßiger MK multipliziert Output und Input mit demselben Faktor, die Vollversorgungsverhältnisse bleiben daher identisch. Alle angeforderten ganzen MW werden durch eine finanzierte Solar- oder Windanlage gedeckt. Brennstoffanlagen werden in den Hauptfirmen nicht eingesetzt; ihre unveränderten Ableitungen und neuen Opportunitätswerte werden separat ausgewiesen.

Positive Zwischenproduktüberschüsse werden real exportiert. Die bestehenden Marktrouten besitzen keinen Produktionsinput-Vorbehalt; eine übergroße Flotte könnte daher notwendige Inputpuffer abziehen. Um ohne Controller dauerhaft auskommen zu können, wird der vollständig versorgte Kartenblock erforderlichenfalls mit 1, 2 oder 4 multipliziert, bis alle intern weiter benötigten Nettoüberschüsse pro Sechs-Sekunden-Zyklus durch vier teilbar sind. Ein MK1-Truck trägt genau vier Einheiten je Sechs-Sekunden-Kapazitätsäquivalent (40/min). Dieselbe gemeinsame MK-Skalierung erhält die Gleichheit.

Transportvorlagen kombinieren Trucks mit Trains (20 Einheiten/Zyklus), Ships (400/Zyklus) oder Dreiergruppen Aircraft (zusammen 400/Zyklus); Restmengen fahren Trucks. Nur finale Waren dürfen zusätzliche ungenutzte Transportkapazität erhalten, weil dort keine weiteren Maschineninputs entzogen werden. Fahrzeuge sind fest den tatsächlichen Nettoverkaufsressourcen zugeordnet. Bei gleicher Vorproduktion werden nicht dieselben notwendigen Inputs nochmals als frei verkäufliche Überschüsse gezählt.

Es gibt keine experimentelle Pausensteuerung. Nach einer festen Anlaufzeit von längster Fahrtzeit +60 Sekunden werden die finanzierten Marktrouten einmalig aktiviert. Bis dahin produzieren die realen Maschinen ihre Startup-Batches und Puffer selbst; anfangs werden keine hypothetischen Waren geschenkt. Danach bleiben Produktion und Routen unverändert. Die Lagerdimensionierung enthält Produktionschargen, Fahrzeugladungen und Anlaufüberschüsse. Ganze Karten und diese bewusst konservative Transportfamilie können mehr Kapital benötigen als eine beliebig zeitgesteuerte optimale Mischfirma.

Die realen Gebäude-, Linien- und Slotkosten werden aus P11-Ds diskreter Optimierung übernommen und auf 4 096 Produktions-/Energiekarten je Board/Spezialisierung erweitert. Freight-Kurven reichen bis 512 Fahrzeuge je Familie. Dies sind Suchgrenzen des Audits, keine neuen Spiellimits. Je Produkt werden finale Kartenzahlen 1,2,4,…,4096 mit den nötigen Vollversorgungsblöcken und MK1/2/5/10/25/50/99 untersucht; zu große Strukturen werden verworfen. Somit entsteht ein begrenzter Kandidatenraum, keine globale Optimierung aller Mischqualitäten, Produktionsprogramme und Fahrzeugfahrpläne.

## 3. Preisformel und Parametersuche

Primary p=1. Für ein Folgeprodukt mit Output q, Inputs a_i, Zyklus t, Leistung P und Stufe s gilt:

`p = Σ(a_i × p_i)/q + (L_s + E × P) × t/(60 × q)`.

Nur eigene zusätzliche Arbeit/Energie wird addiert; Vorarbeit steckt bereits in den Inputpreisen. Für C2 ist L=(120,40,120), E=0. Direkter Mehrwert einer vollständig betriebenen MK1-Karte ist somit $120/min bei Processing, $40/min bei Fabrication und $120/min bei Assembly. Das ist Warenwert gegenüber denselben Inputs, noch kein Beweis gleicher Rendite nach Infrastrukturkosten. Es gibt keine alten Mindestanker, dynamischen Preise oder produkt-/domainspezifischen Aufschläge.

Der Preisvektor ist exakt linear in fünf rekursiven Koeffizienten: Primärmenge, Processing-, Fabrication-, Assembly-Maschinenminuten und verarbeitende MW-Minuten. Alle 353 Preise werden so neu berechnet. N1+C als Kontrolle nutzt unverändert 120/120/120 und E=0,01. N0+A nutzt die tatsächlichen aktuellen Laufzeitpreise, nicht die historischen Kataloganker.

Die Hauptsuche kombiniert Processing {2,5;5;10;20;40;60;90;120;180}, Fabrication {20;40;80;120;180;240}, Assembly {30;60;120;180;240;360}, E {0;0,01;0,05}. Hinzu kommt das feinere lokale Raster Processing {5;7,5;10;12,5;15}, Fabrication {30;40;50;60}, Assembly {90;120;150} bei denselben E-Werten. Nach Entfernung identischer Kombinationen: 1 146 Varianten.

**Zielgewichtung:** 55 % gewichtete Branchenkonkurrenz über Budgets/Level, 15 % schlechteste einzelne Kohorte, 20 % inkrementelle Amortisation, 5 % extreme Beschleunigung/Verlangsamung gegenüber A, 5 % Preisexplosion gegenüber N1+C. Der Branchenverlust ist 0,55×log(stärkste/schwächste finanzierbare Domain) +0,25×Anteil nicht innerhalb 20 % +0,10×Anteil nicht innerhalb 10 % +0,10×Anteil nicht innerhalb 30 % +2×Anteil nicht finanzierbarer, levelzulässiger Domains. Nicht finanzierbare Domains werden also nicht stillschweigend als gleichwertig gezählt.

Die Amortisationsstrafe ist der positive Teil von log(Payback/120 Minuten), gleich gewichtet über die drei Produktionsstufen und über zwei Ausgangszustände: Starterplätze verfügbar beziehungsweise bestehende Factory Halls voll. 120 Minuten sind eine gewählte Designreferenz für diesen Score, keine garantierte Grenze aller Schritte. Die Expansionsstrafe setzt erst bei mehr als Faktor zwei Abstand der besten nominalen Kohortenrate zu A ein. Der Preisexplosionsterm setzt erst oberhalb dreifacher N1+C-Preise ein. Gewichte sind erklärte Designentscheidungen, keine aus Daten identifizierten Naturkonstanten.

| Budget $ | Gewicht % |
| --- | --- |
| 1 250 | 4 |
| 5 000 | 8 |
| 10 000 | 8 |
| 50 000 | 12 |
| 100 000 | 12 |
| 500 000 | 12 |
| 1 000 000 | 12 |
| 10 000 000 | 12 |
| 1 000 000 000 | 12 |
| 1 000 000 000 000 | 8 |

Innerhalb der Budgets werden Level 1/5/25 bis $5 000 mit 70/20/10 %, bis $100 000 mit 30/40/30 %, darüber mit 10/30/60 % gewichtet. Levelkohorten setzen die benötigte frühere Lifetime-Produktion voraus. Sie sind finanzierte Zustandsvergleiche und keine Behauptung, jedes Rezept sei am Anfang ohne Vorgeschichte verfügbar. Der echte Genesis-Start wird unabhängig mit tatsächlich verdienten Unlocks simuliert.

| Rang | Processing | Fabrication | Assembly | Energie | Score | Amortisationsstrafe |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 120 | 40 | 120 | 0.0 | 0.689292 | 0.0613 |
| 2 | 120 | 40 | 120 | 0.01 | 0.689319 | 0.0610 |
| 3 | 120 | 40 | 120 | 0.05 | 0.689428 | 0.0598 |
| 4 | 90 | 40 | 120 | 0.0 | 0.689602 | 0.0909 |
| 5 | 90 | 40 | 120 | 0.01 | 0.689693 | 0.0906 |
| 6 | 90 | 40 | 120 | 0.05 | 0.689822 | 0.0893 |
| 7 | 40 | 40 | 120 | 0.05 | 0.690425 | 0.1872 |
| 8 | 40 | 40 | 120 | 0.0 | 0.690616 | 0.1897 |
| 9 | 40 | 40 | 120 | 0.01 | 0.690640 | 0.1892 |
| 10 | 60 | 40 | 120 | 0.0 | 0.693633 | 0.1366 |
| 11 | 120 | 40 | 60 | 0.05 | 0.693852 | 0.0823 |
| 12 | 60 | 40 | 120 | 0.01 | 0.694616 | 0.1362 |

| Produkt | Heute N0+A $ | N1+C $ | Empfohlen N1+C2 $ |
| --- | --- | --- | --- |
| iron | 3.75000 | 4.00133 | 4.00000 |
| copper | 4.37500 | 4.00133 | 4.00000 |
| steel | 10.00000 | 6.75300 | 6.75000 |
| stainless_steel | 11.38750 | 10.33767 | 10.33333 |
| aluminum | 3.18750 | 4.20180 | 4.20000 |
| platinum | 20.66250 | 4.00200 | 4.00000 |
| flour | 1.62500 | 2.00042 | 2.00000 |
| corn_meal | 1.56250 | 2.00042 | 2.00000 |
| soy_oil | 3.06250 | 4.00083 | 4.00000 |
| lumber | 1.81250 | 2.00042 | 2.00000 |
| bitumen | 4.70000 | 3.00100 | 3.00000 |
| silicon | 4.07500 | 4.50167 | 4.50000 |
| high_purity_silicon | 13.13750 | 11.00400 | 11.00000 |
| industrial_equipment | 45.16030 | 38.57303 | 32.41667 |
| biodiesel | 29.91190 | 24.00989 | 21.33333 |
| microchip | 147.55000 | 100.05600 | 84.00000 |
| ai_server | 299.13750 | 182.96047 | 158.86667 |

Die vollständige Rangfolge enthält auch schlechtere Varianten. Sehr kleine Arbeitszuschläge können Starterkonkurrenz angleichen, werden aber bei bezahlter späterer Hallenerweiterung unattraktiv. Deshalb gewinnt die endgültige gemeinsame Bewertung nicht allein nach niedrigen Anfangspreisen. Energie null ist innerhalb des untersuchten kleinen E-Rasters der Sieger; die kleinen Scoreabstände benachbarter Varianten begründen keine Präzision bis auf den letzten Cent.

| Abweichende Budgetgewichtung | Processing | Fabrication | Assembly | Energie |
| --- | --- | --- | --- | --- |
| early_x2 | 40 | 40 | 120 | 0.05 |
| endgame_x2 | 120 | 40 | 120 | 0.0 |
| middle_x2 | 120 | 40 | 120 | 0.0 |

Diese Sensitivität gewichtet jeweils frühe, mittlere oder Endgamebudgets doppelt und bewertet die bereits berechneten Kandidaten neu. Unterschiedliche Gewinner wären ein Zielkonflikt, kein Anlass für versteckte Domainboni. Empfohlen bleibt die ausdrücklich gewählte gemeinsame Gewichtung.

## 4. Branchenkonkurrenz nach Budget und Company-Level

Die folgende Zahl 10/20/30 zählt **verschiedene Research-Domains**, deren beste finanzierbare Strategie mindestens 90/80/70 % der besten zulässigen Firmenrate erreicht. In einer Branche werden ähnliche Produkte nicht mehrfach als Branchenvielfalt gezählt. Jede zugeordnete Firma muss mindestens 50 % ihres Erlöses in dieser Domain erzielen; übrige Überschussverkäufe werden offengelegt. Stärkste/schwächste vergleicht die besten Strategien finanzierbarer Domains. Der Nenner „finanziert/zulässig“ zeigt fehlenden Budgetzugang separat. Alle Werte dieses Abschnitts sind nominale vollständige Versorgungskapazitäten; gemessene Lieferungen folgen in Abschnitt 6.

### Company-Level 1

| Budget $ | Modell | Beste Strategie | Cashkapazität $/min | Domains 10/20/30 | Finanziert/zulässig | Stärkste / schwächste | Faktor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 250 | N0_A | copper | 525.00 | 1/1/2 | 6/7 | metals / construction | 5.47 |
| 5 000 | N0_A | steel | 1 600.00 | 1/1/1 | 6/7 | metals / construction | 8.33 |
| 10 000 | N0_A | steel_components | 1 930.29 | 1/1/1 | 6/7 | metals / construction | 5.03 |
| 50 000 | N0_A | steel | 6 400.00 | 1/1/1 | 7/7 | metals / construction | 4.17 |
| 100 000 | N0_A | steel | 12 800.00 | 1/1/1 | 7/7 | metals / construction | 4.17 |
| 500 000 | N0_A | crude_oil | 33 792.00 | 2/2/2 | 7/7 | oil_gas / machinery | 4.67 |
| 1 000 000 | N0_A | steel | 51 200.00 | 1/2/2 | 7/7 | metals / construction | 3.33 |
| 10 000 000 | N0_A | steel | 128 000.00 | 1/1/1 | 7/7 | metals / construction | 4.17 |
| 1 000 000 000 | N0_A | steel | 665 600.00 | 1/1/1 | 7/7 | metals / construction | 4.17 |
| 1 000 000 000 000 | N0_A | steel | 10 854 400.00 | 1/1/1 | 7/7 | metals / construction | 13.80 |
| 1 250 | N1_C | iron | 480.16 | 1/1/1 | 6/7 | metals / electronics | 4.00 |
| 5 000 | N1_C | aluminum_components | 1 320.76 | 1/2/2 | 6/7 | metals / construction | 4.40 |
| 10 000 | N1_C | steel_components | 1 680.88 | 1/1/2 | 6/7 | metals / construction | 2.80 |
| 50 000 | N1_C | pump_components | 4 562.24 | 3/6/6 | 7/7 | electronics / construction | 1.90 |
| 100 000 | N1_C | aluminum_components | 10 085.72 | 1/2/5 | 7/7 | metals / construction | 2.10 |
| 500 000 | N1_C | iron_components | 28 814.40 | 1/2/3 | 7/7 | metals / construction | 1.88 |
| 1 000 000 | N1_C | iron | 38 412.80 | 5/5/5 | 7/7 | oil_gas / construction | 2.00 |
| 10 000 000 | N1_C | aluminum | 107 566.08 | 1/3/6 | 7/7 | metals / construction | 1.75 |
| 1 000 000 000 | N1_C | iron | 798 986.24 | 1/1/3 | 7/7 | metals / construction | 3.72 |
| 1 000 000 000 000 | N1_C | steel_components | 10 589 009.92 | 1/1/2 | 7/7 | metals / construction | 6.76 |
| 1 250 | N1_C2 | iron | 480.00 | 1/1/1 | 6/7 | metals / electronics | 4.00 |
| 5 000 | N1_C2 | steel | 1 080.00 | 2/2/2 | 6/7 | electronics / construction | 3.60 |
| 10 000 | N1_C2 | steel_components | 1 360.00 | 1/2/5 | 6/7 | metals / construction | 2.27 |
| 50 000 | N1_C2 | steel | 4 320.00 | 3/6/6 | 7/7 | electronics / construction | 1.80 |
| 100 000 | N1_C2 | steel | 8 640.00 | 2/5/5 | 7/7 | electronics / construction | 1.80 |
| 500 000 | N1_C2 | iron_components | 22 400.00 | 3/6/6 | 7/7 | metals / construction | 1.46 |
| 1 000 000 | N1_C2 | iron | 38 400.00 | 4/5/5 | 7/7 | oil_gas / construction | 2.00 |
| 10 000 000 | N1_C2 | aluminum | 107 520.00 | 1/2/6 | 7/7 | metals / construction | 1.75 |
| 1 000 000 000 | N1_C2 | iron | 798 720.00 | 1/1/1 | 7/7 | metals / construction | 3.71 |
| 1 000 000 000 000 | N1_C2 | steel_components | 8 412 160.00 | 1/1/3 | 7/7 | metals / construction | 5.37 |

### Company-Level 5

| Budget $ | Modell | Beste Strategie | Cashkapazität $/min | Domains 10/20/30 | Finanziert/zulässig | Stärkste / schwächste | Faktor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 250 | N0_A | copper | 525.00 | 1/1/2 | 8/11 | metals / electronics | 3.98 |
| 5 000 | N0_A | steel | 1 600.00 | 1/1/1 | 8/11 | metals / construction | 4.13 |
| 10 000 | N0_A | steel_components | 1 930.29 | 1/1/2 | 8/11 | metals / construction | 3.35 |
| 50 000 | N0_A | steel | 6 400.00 | 1/1/4 | 11/11 | metals / energy | 2.94 |
| 100 000 | N0_A | steel | 12 800.00 | 1/1/2 | 11/11 | metals / energy | 4.71 |
| 500 000 | N0_A | crude_oil | 33 792.00 | 2/2/3 | 11/11 | oil_gas / energy | 4.11 |
| 1 000 000 | N0_A | steel | 51 200.00 | 1/2/2 | 11/11 | metals / energy | 6.22 |
| 10 000 000 | N0_A | steel | 128 000.00 | 1/2/2 | 11/11 | metals / energy | 5.05 |
| 1 000 000 000 | N0_A | steel | 665 600.00 | 2/2/4 | 11/11 | metals / energy | 4.21 |
| 1 000 000 000 000 | N0_A | steel | 10 854 400.00 | 1/1/2 | 11/11 | metals / energy | 5.39 |
| 1 250 | N1_C | iron | 480.16 | 1/1/2 | 8/11 | metals / electronics | 4.00 |
| 5 000 | N1_C | aluminum_components | 1 320.76 | 1/2/5 | 9/11 | metals / textiles | 2.75 |
| 10 000 | N1_C | hydraulic_components | 2 161.06 | 1/3/5 | 10/11 | machinery / oil_gas | 2.25 |
| 50 000 | N1_C | packaging_materials | 6 242.78 | 3/5/8 | 11/11 | forestry / oil_gas | 1.63 |
| 100 000 | N1_C | biodiesel | 11 764.80 | 3/7/10 | 11/11 | energy / oil_gas | 1.53 |
| 500 000 | N1_C | packaged_food | 33 612.78 | 3/6/6 | 11/11 | agriculture / energy | 2.29 |
| 1 000 000 | N1_C | biodiesel_feedstock | 48 314.20 | 2/6/10 | 11/11 | chemicals / energy | 3.29 |
| 10 000 000 | N1_C | asphalt_components | 124 854.48 | 7/9/10 | 11/11 | construction / oil_gas | 1.63 |
| 1 000 000 000 | N1_C | fiber_components | 1 048 661.12 | 1/3/7 | 11/11 | textiles / oil_gas | 2.13 |
| 1 000 000 000 000 | N1_C | construction_materials | 18 478 985.04 | 1/2/3 | 11/11 | construction / oil_gas | 5.37 |
| 1 250 | N1_C2 | iron | 480.00 | 1/1/2 | 8/11 | metals / electronics | 4.00 |
| 5 000 | N1_C2 | steel | 1 080.00 | 2/4/5 | 9/11 | electronics / textiles | 2.25 |
| 10 000 | N1_C2 | hydraulic_components | 1 840.00 | 1/4/5 | 10/11 | machinery / oil_gas | 1.92 |
| 50 000 | N1_C2 | packaging_materials | 5 600.00 | 3/6/9 | 11/11 | forestry / energy | 1.60 |
| 100 000 | N1_C2 | biodiesel | 10 480.00 | 3/8/10 | 11/11 | energy / maritime | 1.46 |
| 500 000 | N1_C2 | packaged_food | 29 600.00 | 3/5/7 | 11/11 | agriculture / energy | 2.26 |
| 1 000 000 | N1_C2 | biodiesel_feedstock | 41 900.00 | 7/7/10 | 11/11 | chemicals / energy | 2.00 |
| 10 000 000 | N1_C2 | packaged_nutrition | 119 680.00 | 2/6/9 | 11/11 | agriculture / oil_gas | 1.56 |
| 1 000 000 000 | N1_C2 | fiber_components | 915 200.00 | 1/4/7 | 11/11 | textiles / oil_gas | 1.86 |
| 1 000 000 000 000 | N1_C2 | construction_materials | 16 030 320.00 | 2/2/3 | 11/11 | construction / oil_gas | 4.66 |

### Company-Level 25

| Budget $ | Modell | Beste Strategie | Cashkapazität $/min | Domains 10/20/30 | Finanziert/zulässig | Stärkste / schwächste | Faktor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 250 | N0_A | gold | 1 455.00 | 1/1/1 | 8/15 | metals / electronics | 11.02 |
| 5 000 | N0_A | catalyst_metal | 2 794.00 | 1/1/1 | 8/15 | metals / textiles | 6.88 |
| 10 000 | N0_A | platinum | 3 538.00 | 1/1/1 | 10/15 | metals / textiles | 6.14 |
| 50 000 | N0_A | platinum | 13 456.00 | 1/1/1 | 15/15 | metals / agriculture | 5.10 |
| 100 000 | N0_A | platinum_ore | 22 272.00 | 1/1/1 | 15/15 | metals / agriculture | 4.05 |
| 500 000 | N0_A | platinum_ore | 89 088.00 | 1/1/1 | 15/15 | metals / agriculture | 5.27 |
| 1 000 000 | N0_A | platinum_ore | 111 360.00 | 1/1/1 | 15/15 | metals / agriculture | 5.27 |
| 10 000 000 | N0_A | platinum_ore | 222 720.00 | 1/1/1 | 15/15 | metals / construction | 3.62 |
| 1 000 000 000 | N0_A | gold | 1 422 720.00 | 1/1/1 | 15/15 | metals / agriculture | 6.48 |
| 1 000 000 000 000 | N0_A | platinum | 22 434 052.00 | 1/1/1 | 15/15 | metals / agriculture | 6.80 |
| 1 250 | N1_C | platinum | 480.24 | 2/2/3 | 8/15 | metals / electronics | 4.00 |
| 5 000 | N1_C | titanium_components | 1 320.84 | 3/3/7 | 10/15 | metals / textiles | 2.75 |
| 10 000 | N1_C | industrial_tires | 2 401.28 | 1/3/6 | 11/15 | automotive / oil_gas | 2.50 |
| 50 000 | N1_C | grid_storage_system | 6 843.54 | 6/11/13 | 14/15 | energy / oil_gas | 1.78 |
| 100 000 | N1_C | biodiesel | 11 764.80 | 5/10/14 | 15/15 | energy / oil_gas | 1.53 |
| 500 000 | N1_C | packaged_food | 33 612.78 | 6/14/14 | 15/15 | agriculture / oil_gas | 1.75 |
| 1 000 000 | N1_C | biodiesel_feedstock | 48 314.20 | 4/12/15 | 15/15 | chemicals / aerospace | 1.30 |
| 10 000 000 | N1_C | wind_components | 133 497.64 | 8/14/14 | 15/15 | energy / oil_gas | 1.74 |
| 1 000 000 000 | N1_C | rubber_blend_components | 1 048 694.40 | 3/10/13 | 15/15 | chemicals / oil_gas | 2.13 |
| 1 000 000 000 000 | N1_C | commercial_aircraft | 21 504 392.76 | 5/8/10 | 15/15 | aerospace / oil_gas | 6.25 |
| 1 250 | N1_C2 | iron | 480.00 | 2/2/3 | 8/15 | chemicals / electronics | 4.00 |
| 5 000 | N1_C2 | high_purity_silicon | 1 320.00 | 1/2/5 | 10/15 | electronics / textiles | 2.75 |
| 10 000 | N1_C2 | industrial_tires | 2 160.00 | 1/3/7 | 11/15 | automotive / oil_gas | 2.25 |
| 50 000 | N1_C2 | industrial_clothing | 6 040.00 | 6/11/13 | 14/15 | textiles / oil_gas | 1.57 |
| 100 000 | N1_C2 | high_purity_silicon | 10 560.00 | 8/10/15 | 15/15 | electronics / maritime | 1.43 |
| 500 000 | N1_C2 | packaged_food | 29 600.00 | 10/14/14 | 15/15 | agriculture / oil_gas | 1.54 |
| 1 000 000 | N1_C2 | protective_clothing | 42 400.00 | 10/14/15 | 15/15 | chemicals / aerospace | 1.28 |
| 10 000 000 | N1_C2 | wind_components | 123 200.00 | 4/13/14 | 15/15 | energy / oil_gas | 1.60 |
| 1 000 000 000 | N1_C2 | fiber_components | 915 200.00 | 2/11/13 | 15/15 | chemicals / oil_gas | 1.86 |
| 1 000 000 000 000 | N1_C2 | commercial_aircraft | 19 404 480.00 | 5/8/11 | 15/15 | aerospace / oil_gas | 5.64 |

Bei Level 25/$1 Mio. wächst die Zahl der Domains innerhalb 20 % von **1 unter A auf 14 unter C2**; der Faktor stärkste/schwächste sinkt von 5,273 auf 1,277. Bei $1 Mrd. sind es 1→11 Domains und 6,477→1,862. Bei $1 Billion bleiben dagegen nur 8 von 15 Domains innerhalb 20 %, Faktor 5,640. In kleinen Budgets fehlen teilweise ganze finanzierbare Branchen. Diese negativen Ergebnisse verhindern die Aussage, Preise allein stellten in jeder Phase Gleichheit her.

### Verbleibende Nachteile unter C2 – Level 25

| Budget $ | Schwächste Domain | Beste dortige Strategie | Rückstand % | Anteil Erlös in Domain % |
| --- | --- | --- | --- | --- |
| 1 250 | electronics | quartz | 75.00 | 100.00 |
| 5 000 | textiles | cotton_fiber | 63.64 | 100.00 |
| 10 000 | oil_gas | bitumen | 55.56 | 100.00 |
| 50 000 | oil_gas | bitumen | 36.42 | 100.00 |
| 100 000 | maritime | workboat | 29.92 | 82.43 |
| 500 000 | oil_gas | bitumen | 35.14 | 100.00 |
| 1 000 000 | aerospace | orbital_vehicle | 21.70 | 93.13 |
| 10 000 000 | oil_gas | bitumen | 37.66 | 100.00 |
| 1 000 000 000 | oil_gas | bitumen | 46.29 | 100.00 |
| 1 000 000 000 000 | oil_gas | bitumen | 82.27 | 100.00 |

Die Ursachen sind keine ausgelassenen Rohstoffkosten: Unterschiede bleiben durch ganze Kettenblöcke, Spezialstandorte ohne Extractor-Startergeschenke, benötigte Mischinputs, Diskretheit der Fahrzeuge, Familie der Preisquote beim MK-Upgrade, unterschiedliche Unlocks und konvex steigende Hallenkosten. Bei hohen Budgets kommen die begrenzte uniforme MK-Auswahl und die nicht global optimierte Firmenfamilie hinzu. Verglichen werden ihre besten gefundenen Punkte; es wird kein beweisbar weltweit bestes Unternehmen behauptet.

Am Billionenpunkt erreicht der gefundene A-Sieger genau die Auditgrenze von 4 096 Factory-Karten; die N1-Sieger benötigen 3 960. Gerade dieser Endgamepunkt darf deshalb nicht als vollständig ausgeschöpfter Vergleich aller theoretisch kaufbaren Firmen gelesen werden. Das Spiel besitzt dort weiterhin kein Factory-Anzahlcap. Die positiven Ergebnisse bei mittleren Budgets sind von dieser speziellen Grenze getrennt zu beurteilen.

## 5. Zusätzliche Verarbeitung statt alternativem Inputverkauf

Für jedes der 304 Folgeprodukte besitzt B die bereits notwendige, voll arbeitende vorgelagerte Kette und verkauft ihre tatsächlichen Nettooutputs. A besitzt exakt dieselben vorgelagerten Maschinen und verarbeitet zusätzlich die beabsichtigten Inputs. Somit werden notwendige Ressourcen- und Zwischenproduktkarten nicht ein zweites Mal gekauft. A behält Bs Energie- und Fahrzeugvermögen; Fahrzeuge dürfen neu zugeordnet werden. Unnötig gewordene Fahrzeuge werden nicht als optimistischer Verkaufsgewinn gutgeschrieben.

Neue Factory-/Energy-Kapazität wird aus dem tatsächlichen B-Layout erweitert. Der realisierbare Erweiterungsweg öffnet jeweils den günstigsten angebotenen Slot-/Linien-/Gebäudeschritt je gewonnenem Platz. Das ist eine konkret bezahlbare, erhaltene Geometrie, keine behauptete globale optimale Umbauplanung. A vergleicht die unterschiedlichen Transportvorlagen nach **zusätzlichen** Kosten unter Wiederverwendung von Bs Flotte. Selbständig billigstes A plus selbständig billigstes B wäre hierfür falsch, weil schon bezahlte Fahrzeuge dann erneut ersetzt würden.

ΔInvestition umfasst neue Karten inklusive passender Schattenquotes, konkrete Slots/Hallen/Linien, zusätzliche Energie, zusätzliche Fahrzeuge/Freight-Plätze und gegebenenfalls Lager. Es gibt keine laufende Slotmiete. ΔErlös ist A-Lieferung minus B-Lieferung, nicht A-Gesamtumsatz. Ein Schritt ist bei positiver ΔRate amortisiert, wenn diese zusätzlichen Erlöse seine zusätzlichen Ausgaben decken.

Zweiter Zustand für alle 304 Schritte: sämtliche bestehenden Factory Halls sind belegt, Starter-Processors anderweitig gebunden. Es werden alle neuen Verarbeitungskarten bezahlt sowie eine weitere Halle zum aktuellen Gebäudeindex und die nötigen Slots. Andere vorgelagerte und Supportanlagen bleiben dieselben. Dies ist eine **zusätzliche Erweiterungsquote**, kein mit Gratisvermögen neu erzeugtes Budgetunternehmen. Die alten Hallen werden nicht nochmals belastet. Gerade die ersten ein bis vier Maschinen einer neuen Halle amortisieren sich anders als eine Erweiterung in vorhandenen freien Plätzen.

| Stufe | Schritte | Starter: Payback min, Median / Max. | Volle Hallen: Median / Max. | Zusätzlicher Warenwert je volle Karte $/min |
| --- | --- | --- | --- | --- |
| Processing | 68 | 0.00 / 15.31 | 128.96 / 131.29 | 120 |
| Fabrication | 86 | 16.38 / 110.12 | 115.62 / 392.62 | 40 |
| Assembly | 150 | 7.50 / 47.33 | 38.67 / 209.62 | 120 |

Ein Median null im Starterzustand bedeutet verfügbare geschenkte Processors/Slots/Generatorleistung, nicht dauerhaft kostenlose Folgeverarbeitung. Alle 608 Schritt-/Kontextquotes stehen in der Wirtschaftstabelle; Fälle mit langen Amortisationszeiten sind enthalten. Nominale Paybacks sind Quotienten bei voller nachhaltiger Rate, keine beobachteten 304 Engine-Amortisationen.

| Modell | Schritt | Zusatz-$ | Inputverkauf gem. $/min | Verarbeitung gem. $/min | Zusatz gem. $/min | Payback-Schätzer min | Im 120-min-Trace amortisiert ab min | Zusätzliches Netto nach 120 min $ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0_A | flour | 280.00 | 228.00 | 255.00 | 27.00 | 10.37 | 13.00 | 2 906.00 |
| N0_A | steel | 3 310.00 | 1 056.00 | 2 032.00 | 976.00 | 3.39 | 6.00 | 111 522.00 |
| N0_A | bitumen | 970.00 | 1 056.00 | 1 168.00 | 112.00 | 8.66 | 11.00 | 12 246.00 |
| N0_A | copper_wire | 1 135.00 | 525.00 | 569.65 | 44.65 | 25.42 | 24.00 | 4 309.18 |
| N0_A | industrial_equipment | 2 580.00 | 7 482.27 | 7 774.22 | 291.96 | 8.84 | 12.00 | 31 578.85 |
| N0_A | microchip | 2 840.00 | 11 197.00 | 12 201.00 | 1 004.00 | 2.83 | 6.00 | 114 628.00 |
| N0_A | ai_server | 2 840.00 | 14 010.00 | 16 247.50 | 2 237.50 | 1.27 | 4.00 | 261 185.00 |
| N0_A | iron | 0.00 | 120.00 | 225.00 | 105.00 | 0.00 | 0.02 | 12 592.50 |
| N1_C | flour | 0.00 | 120.00 | 240.05 | 120.05 | 0.00 | 0.02 | 14 165.90 |
| N1_C | steel | 3 310.00 | 960.00 | 1 440.48 | 480.48 | 6.89 | 10.00 | 53 506.16 |
| N1_C | bitumen | 0.00 | 120.00 | 240.08 | 120.08 | 0.00 | 0.02 | 14 169.44 |
| N1_C | copper_wire | 1 460.00 | 480.16 | 720.36 | 240.20 | 6.08 | 7.00 | 27 459.89 |
| N1_C | industrial_equipment | 4 480.00 | 7 203.00 | 7 683.48 | 480.48 | 9.32 | 12.00 | 54 347.37 |
| N1_C | microchip | 10 940.00 | 7 202.92 | 7 683.40 | 480.48 | 22.77 | 26.00 | 45 276.16 |
| N1_C | ai_server | 18 520.00 | 9 604.24 | 10 084.72 | 480.48 | 38.54 | 41.00 | 38 176.64 |
| N1_C | iron | 0.00 | 120.00 | 240.08 | 120.08 | 0.00 | 0.02 | 14 385.51 |
| N1_C2 | flour | 0.00 | 120.00 | 240.00 | 120.00 | 0.00 | 0.02 | 14 160.00 |
| N1_C2 | steel | 3 310.00 | 960.00 | 1 440.00 | 480.00 | 6.90 | 10.00 | 53 450.00 |
| N1_C2 | bitumen | 0.00 | 120.00 | 240.00 | 120.00 | 0.00 | 0.02 | 14 160.00 |
| N1_C2 | copper_wire | 1 460.00 | 480.00 | 560.00 | 80.00 | 18.25 | 15.00 | 8 428.00 |
| N1_C2 | industrial_equipment | 4 480.00 | 6 240.00 | 6 720.00 | 480.00 | 9.33 | 12.00 | 53 863.33 |
| N1_C2 | microchip | 10 940.00 | 6 560.00 | 7 040.00 | 480.00 | 22.79 | 26.00 | 45 220.00 |
| N1_C2 | ai_server | 18 520.00 | 8 640.00 | 9 120.00 | 480.00 | 38.58 | 41.00 | 38 120.00 |
| N1_C2 | iron | 0.00 | 120.00 | 240.00 | 120.00 | 0.00 | 0.02 | 14 376.00 |

„Amortisiert ab“ ist der erste Zeitpunkt nach dem letzten negativen A−B−Investitionssaldo innerhalb des beobachteten Horizonts; es garantiert keinen beliebig langen Verlauf. Durch unterschiedliche Anlauf- und Ankunftszeiten kann die beobachtete Amortisation vom Quotienten des letzten stabilen Fensters abweichen. Das Inputverkaufsszenario hat seine eigenen realen Frachten; ein reiner Inputpreisvergleich wird nicht als tatsächliche Auszahlung ausgegeben.

## 6. Echte Engine-Lieferungen und vollständig finanzierte Testfirmen

Die unveränderte `SimulationEngine` erhält nur isolierte Kopien der N0/N1-Definitionen und eine private Preistabelle. Die originale Release-Balancingfunktion wird auf die Kopien angewandt. Keine produktive Definition wird überschrieben. Hauptnachweis: acht Paare aus Landwirtschaft (Flour), Stahl, Petrochemie (Bitumen), Fabrication (Copper Wire), Maschinenbau (Industrial Equipment), Elektronik (Microchip) und komplexer Assembly (AI Server), ergänzt um Iron; jeweils N0+A, N1+C und N1+C2, A und B, zwei Stunden bei einer Sekunde pro Schritt. Dazu werden die besten gefundenen Progressionsfirmen bei zehn Budgets für alle drei Modelle tatsächlich betrieben.

Reife Vergleichsfirmen starten ohne Waren. Ihr Kapital wird explizit um die gesamte Installation reduziert; die gewählte Budgetstufe deckt alle Karten und Upgradequotes. Company-Level 5 beziehungsweise 25 und vorausgesetzte frühere Lifetime-Produktion sind erklärt. Progressionssieger werden bei Level 1 bis $5 000, Level 5 bis $1 Mio. und Level 25 darüber geprüft; Company-Level-Unlocks sämtlicher Zutaten sind in der Auswahl enthalten. Diese bedingten Firmen sind kein kostenlos bis MK99 gespielter Genesis-Start.

Die produktiven MK-Quotes werden mit den jeweiligen neuen Preisen und Rezeptdefinitionen neu berechnet. Die Untersuchung setzt Common als klaren mechanischen Vergleichszustand; zufällige Rarity-Aufwertungen während echter Upgradehistorien wurden nicht kostenlos hinzugerechnet und nicht als optimale Beschaffungspolitik simuliert. Reife Karten werden als vollständig bezahlter Schattenzustand installiert, nicht durch 98 UI-Klicks je Karte erspielt.

Es werden ausschließlich wiederholte reine Katalogberechnungen und das Mapping einer vollständigen unveränderlichen Unlock-ID-Menge memoisiert; Inputs, Output, Lager, Leistung, Ankünfte, Geld, Lifetime- und XP-Übergänge bleiben die originalen Engine-Funktionen. Die Definitions-/Anforderungswerte sind gegen die nicht gecachten Katalogfunktionen geprüft. Es wird kein Simulationsergebnis ersetzt oder hochgerechnet.

| Modell | Testtyp | Firmen | Min. Istproduktion / Vollbedarf | Min./Max. Cash Ist/Soll letzte Stunde | Tail Storage-full / No-power / Missing-input |
| --- | --- | --- | --- | --- | --- |
| N0_A | A/B | 16 | 1.00000 | 1.00000 / 1.00000 | 0 / 0 / 0 |
| N0_A | Progression | 10 | 1.00000 | 1.00000 / 1.00000 | 0 / 0 / 0 |
| N1_C | A/B | 16 | 1.00000 | 1.00000 / 1.00000 | 0 / 0 / 0 |
| N1_C | Progression | 10 | 1.00000 | 1.00000 / 1.00000 | 0 / 0 / 0 |
| N1_C2 | A/B | 16 | 1.00000 | 1.00000 / 1.00000 | 0 / 0 / 0 |
| N1_C2 | Progression | 10 | 1.00000 | 1.00000 / 1.00000 | 0 / 0 / 0 |

Die Produktionsquote verwendet **jede aktive Ressource**, nicht nur den finalen Warenverkauf: tatsächlich produzierte Einheiten in der zweiten Stunde / gleichzeitig finanzierte volle Kartenrate. Die detaillierten Ressourcen-, Ankunfts-, Lager- und Statuszählungen stehen in den CSVs. Statuszähler sind Maschinenzustände pro Tick, keine Anzahl unabhängiger Fehlerfälle. Eine Unterversorgung eines kleineren P11-D-Layouts wird hier ausdrücklich nicht als grundsätzlicher Enginefehler bewertet.

| Modell | Budget $ | Level | Produkt | MK bezahlt | Kapital $ | Factory | MW | Flotte | Nominal $/min | Gemessen letzte Stunde $/min | Cash nach Investition und 120 min $ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N0_A | 1 250 | 1 | copper | 1 | 575.00 | 2 | 28.00 | {"freight.truck": 3} | 525.00 | 525.00 | 62 625.00 |
| N0_A | 5 000 | 1 | steel | 1 | 3 780.00 | 4 | 78.00 | {"freight.truck": 4} | 1 600.00 | 1 600.00 | 190 020.00 |
| N0_A | 10 000 | 5 | steel_components | 1 | 8 480.00 | 12 | 158.00 | {"freight.truck": 4} | 1 930.29 | 1 930.29 | 229 293.98 |
| N0_A | 50 000 | 5 | steel | 1 | 32 420.00 | 16 | 312.00 | {"freight.truck": 16} | 6 400.00 | 6 400.00 | 772 780.00 |
| N0_A | 100 000 | 5 | steel | 1 | 83 210.00 | 32 | 624.00 | {"freight.train": 6, "freight.truck": 2} | 12 800.00 | 12 800.00 | 1 502 390.00 |
| N0_A | 500 000 | 5 | crude_oil | 1 | 443 405.00 | 0 | 768.00 | {"freight.aircraft": 9, "freight.train": 16, "freight.truck": 4} | 33 792.00 | 33 792.00 | 3 923 667.00 |
| N0_A | 1 000 000 | 5 | steel | 1 | 993 405.00 | 128 | 2 496.00 | {"freight.train": 25, "freight.truck": 3} | 51 200.00 | 51 200.00 | 5 946 995.00 |
| N0_A | 10 000 000 | 25 | platinum_ore | 2 | 3 460 830.36 | 0 | 1 920.00 | {"freight.aircraft": 21, "freight.train": 13, "freight.truck": 3} | 222 720.00 | 222 720.00 | 31 968 689.64 |
| N0_A | 1 000 000 000 | 25 | gold | 10 | 637 774 781.83 | 1024 | 46 592.00 | {"freight.train": 153, "freight.truck": 3} | 1 422 720.00 | 1 422 720.00 | 527 266 295.67 |
| N0_A | 1 000 000 000 000 | 25 | platinum | 50 | 501 216 248 732.16 | 4096 | 759 861.00 | {"freight.train": 409, "freight.truck": 5} | 22 434 052.00 | 22 434 052.00 | 501 386 140 301.21 |
| N1_C | 1 250 | 1 | iron | 1 | 575.00 | 2 | 28.00 | {"freight.truck": 3} | 480.16 | 480.16 | 57 333.88 |
| N1_C | 5 000 | 1 | aluminum_components | 1 | 4 495.00 | 8 | 94.00 | {"freight.truck": 5} | 1 320.76 | 1 320.76 | 156 354.68 |
| N1_C | 10 000 | 5 | hydraulic_components | 1 | 9 870.00 | 10 | 154.00 | {"freight.truck": 6} | 2 161.06 | 2 161.06 | 255 135.08 |
| N1_C | 50 000 | 5 | packaging_materials | 1 | 42 800.00 | 30 | 410.00 | {"freight.truck": 14} | 6 242.78 | 6 242.78 | 743 848.04 |
| N1_C | 100 000 | 5 | biodiesel | 1 | 99 265.00 | 54 | 744.00 | {"freight.truck": 15} | 11 764.80 | 11 764.80 | 1 388 981.40 |
| N1_C | 500 000 | 5 | packaged_food | 2 | 493 782.88 | 134 | 1 952.50 | {"freight.train": 4, "freight.truck": 6} | 33 612.78 | 33 612.78 | 3 910 984.48 |
| N1_C | 1 000 000 | 5 | biodiesel_feedstock | 2 | 970 901.16 | 150 | 2 710.00 | {"freight.train": 19, "freight.truck": 4} | 48 314.20 | 48 314.20 | 5 634 346.25 |
| N1_C | 10 000 000 | 25 | wind_components | 5 | 9 277 366.69 | 258 | 9 340.00 | {"freight.train": 13, "freight.truck": 20} | 133 497.64 | 133 497.64 | 16 219 003.59 |
| N1_C | 1 000 000 000 | 25 | rubber_blend_components | 10 | 948 775 187.79 | 1280 | 64 896.00 | {"freight.train": 153, "freight.truck": 3} | 1 048 694.40 | 1 048 694.40 | 172 877 459.07 |
| N1_C | 1 000 000 000 000 | 25 | commercial_aircraft | 99 | 875 959 520 972.48 | 3960 | 1 564 068.00 | {"freight.truck": 178} | 21 504 392.76 | 21 504 392.76 | 126 577 997 373.09 |
| N1_C2 | 1 250 | 1 | iron | 1 | 575.00 | 2 | 28.00 | {"freight.truck": 3} | 480.00 | 480.00 | 57 315.00 |
| N1_C2 | 5 000 | 1 | steel | 1 | 3 780.00 | 4 | 78.00 | {"freight.truck": 4} | 1 080.00 | 1 080.00 | 128 660.00 |
| N1_C2 | 10 000 | 5 | hydraulic_components | 1 | 9 870.00 | 10 | 154.00 | {"freight.truck": 6} | 1 840.00 | 1 840.00 | 217 250.00 |
| N1_C2 | 50 000 | 5 | packaging_materials | 1 | 42 800.00 | 30 | 410.00 | {"freight.truck": 14} | 5 600.00 | 5 600.00 | 668 000.00 |
| N1_C2 | 100 000 | 5 | biodiesel | 1 | 99 265.00 | 54 | 744.00 | {"freight.truck": 15} | 10 480.00 | 10 480.00 | 1 237 375.00 |
| N1_C2 | 500 000 | 5 | packaged_food | 2 | 485 645.66 | 134 | 1 952.50 | {"freight.train": 4, "freight.truck": 6} | 29 600.00 | 29 600.00 | 3 452 971.01 |
| N1_C2 | 1 000 000 | 5 | biodiesel_feedstock | 2 | 957 900.50 | 150 | 2 710.00 | {"freight.train": 19, "freight.truck": 4} | 41 900.00 | 41 900.00 | 4 903 232.83 |
| N1_C2 | 10 000 000 | 25 | wind_components | 5 | 9 126 040.09 | 258 | 9 340.00 | {"freight.train": 13, "freight.truck": 20} | 123 200.00 | 123 200.00 | 15 175 159.91 |
| N1_C2 | 1 000 000 000 | 25 | fiber_components | 10 | 975 596 551.75 | 1280 | 61 568.00 | {"freight.train": 153, "freight.truck": 3} | 915 200.00 | 915 200.00 | 130 570 223.25 |
| N1_C2 | 1 000 000 000 000 | 25 | commercial_aircraft | 99 | 801 848 322 370.72 | 3960 | 1 564 068.00 | {"freight.truck": 178} | 19 404 480.00 | 19 404 480.00 | 200 441 406 269.28 |

Die Budgettabellen besitzen 30 Level-/Budgetpunkte je Modell, die echte Progressionsgegenprobe dagegen zehn bewusst ausgewählte Zustände je Modell. Die übrigen Kohorten werden nicht als enginegemessen ausgegeben. Die genauen Karten-/Slot-/Linienpläne und festen Routen liegen in `engine-plans.json`. Die zwei Stunden belegen diese konkreten Firmen, keine beliebigen Portfolios oder jahrelange Catchup-Läufe.

## 7. Echter Genesis-Start und Spielzeit

18 neue Firmen: tatsächlicher Neustart mit $1 250, den ursprünglichen Anfangswaren, acht Starterkarten und neun Anfangsproduktionen. Harvester/Drilling, nötige Trucks, zusätzliche Processors, Energie und Slots werden über existierende Kaufkommandos aus echtem Geld bezahlt. Rohstoffdirektverkauf (Iron Ore, Wheat, Crude Oil) wird jeweils mit späterer voller Verarbeitung zu Iron, Flour beziehungsweise Bitumen verglichen. Jede Firma läuft vier Stunden mit dt=1, ohne Pause-Controller, MK-Upgrade oder ausgegebenes RP. Die Politik baut die gewählte vollständige Anfangskette aus und expandiert danach nicht weiter; sie ist ein Vergleichspfad, keine optimale Karriere.

| Modell | Strategie | Investiert $ | Kasse nach 4 h $ | Gemessen letzte 2 h $/min | Processors / Trucks | Company-Level / Unlocks | Neue XP |
| --- | --- | --- | --- | --- | --- | --- | --- |
| N0_A | iron_ore | 205.00 | 29 725.00 | 120.00 | 0 / 3 | 3 / 17 | 2 225.00 |
| N0_A | wheat | 545.00 | 27 871.20 | 114.00 | 0 / 3 | 3 / 17 | 2 475.00 |
| N0_A | crude_oil | 545.00 | 63 616.20 | 264.00 | 0 / 3 | 3 / 17 | 2 475.00 |
| N0_A | iron | 0.00 | 54 700.00 | 225.00 | 1 / 2 | 4 / 22 | 2 765.00 |
| N0_A | flour | 2 165.00 | 44 823.95 | 195.00 | 6 / 3 | 4 / 21 | 3 515.00 |
| N0_A | bitumen | 1 210.00 | 89 280.00 | 376.00 | 4 / 2 | 4 / 21 | 3 515.00 |
| N1_C | iron_ore | 205.00 | 29 725.00 | 120.00 | 0 / 3 | 3 / 17 | 2 225.00 |
| N1_C | wheat | 545.00 | 29 301.00 | 120.00 | 0 / 3 | 3 / 17 | 2 475.00 |
| N1_C | crude_oil | 545.00 | 29 301.00 | 120.00 | 0 / 3 | 3 / 17 | 2 475.00 |
| N1_C | iron | 0.00 | 58 276.98 | 240.08 | 1 / 2 | 4 / 22 | 2 765.00 |
| N1_C | flour | 545.00 | 57 704.87 | 240.05 | 1 / 3 | 4 / 21 | 3 015.00 |
| N1_C | bitumen | 340.00 | 57 880.98 | 240.08 | 1 / 2 | 4 / 21 | 3 015.00 |
| N1_C2 | iron_ore | 205.00 | 29 725.00 | 120.00 | 0 / 3 | 3 / 17 | 2 225.00 |
| N1_C2 | wheat | 545.00 | 29 301.00 | 120.00 | 0 / 3 | 3 / 17 | 2 475.00 |
| N1_C2 | crude_oil | 545.00 | 29 301.00 | 120.00 | 0 / 3 | 3 / 17 | 2 475.00 |
| N1_C2 | iron | 0.00 | 58 258.00 | 240.00 | 1 / 2 | 4 / 22 | 2 765.00 |
| N1_C2 | flour | 545.00 | 57 693.00 | 240.00 | 1 / 3 | 4 / 21 | 3 015.00 |
| N1_C2 | bitumen | 340.00 | 57 862.00 | 240.00 | 1 / 2 | 4 / 21 | 3 015.00 |

Jeder Genesis-Messpunkt erfüllt Kasse =1250+verdiente Erlöse−bezahlte Investitionen. Die Wirtschaftstabelle enthält außerdem die Messpunkte 10/30/60/120/240 Minuten, Unlock-IDs und Geldschwellen. Die Rohstoffbasis C2 lässt direkten Verkauf im Early Game bei $120/min sinnvoll; freie Starter-Processors erlauben anschließend etwa $240/min bei voller Rohstoffverarbeitung. N0s Preisvorteile bei Crude Oil/Metallen werden nicht unverändert übernommen. Deshalb beschleunigt C2 nicht pauschal jede heutige Startstrategie.

N1 ändert die Lifetime-Schwellen 120 pro Processing-Input und 60 pro Fabrication-/Assembly-Input nicht. Höherer Output einer einzelnen normierten Karte kann die benötigten Mengen früher erreichen. Der rekursive Arbeitswert pro Einheit sinkt dagegen bei höherem Durchsatz; XP-Wert und Effizienzmeilensteine skalieren nicht einfach mit dem neuen Verkaufspreis. C2 selbst verändert keine XP-Formel. Beispiel Flour: bei vollständiger 120-Wheat-Verarbeitung benötigt N0 sechs Processors, N1 einen; der nominale pro Minute auf allen produzierten Gütern erfasste rekursive Work-Wert ist daher unterschiedlich. Die oben tatsächlich gemessenen Level/Unlocks haben Vorrang vor einer pauschalen Aussage über beschleunigten Fortschritt.

### Schrittweite und belastbare Progressionsaussagen

| Modell | Vollversorgte Firma | Verkauf dt1 / dt6 $ | Abweichung % | Neue XP dt1 / dt6 |
| --- | --- | --- | --- | --- |
| N0_A | flour | 30 090.00 / 30 090.00 | 0.00000 | 2 340.00 / 2 740.00 |
| N0_A | steel | 237 504.00 / 237 504.00 | 0.00000 | 2 840.00 / 3 240.00 |
| N0_A | ai_server | 1 917 205.00 / 1 917 205.00 | 0.00000 | 3 300.00 / 3 300.00 |
| N1_C | flour | 28 325.90 / 28 325.90 | 0.00000 | 2 340.00 / 2 740.00 |
| N1_C | steel | 168 336.16 / 168 336.16 | 0.00000 | 2 840.00 / 3 240.00 |
| N1_C | ai_server | 1 189 996.96 / 1 189 996.96 | 0.00000 | 3 300.00 / 3 300.00 |
| N1_C2 | flour | 28 320.00 / 28 320.00 | 0.00000 | 2 340.00 / 2 740.00 |
| N1_C2 | steel | 168 280.00 / 168 280.00 | 0.00000 | 2 840.00 / 3 240.00 |
| N1_C2 | ai_server | 1 076 160.00 / 1 076 160.00 | 0.00000 | 3 300.00 / 3 300.00 |

Dieselben finanzierten Firmen werden hier nur mit anderer Zeitauflösung betrieben. Die Produktionsversorgung ist identisch. Unterschiede im XP-Verlauf stammen aus der bestehenden Ermittlung `productive_seconds` je `advance_time`-Aufruf und der Vergabe von Continuity-/Effizienz-XP. Diese Reproduktion ist ein technischer Progressionshinweis; sie ist **kein** Beleg für ein nicht funktionierendes Lieferlayout. Für Aussagen zum normalen Start wird ausschließlich dt=1 verwendet. Die dt=6-Budgetläufe kalibrieren physische Waren/Geld, ihre XP-Spalten sind keine gleichwertige Echtzeit-Karriereprognose. Eine verlässliche Zusage für Online-/Catchup-Gesamtdauer braucht eine einheitliche Behandlung dieses vorhandenen Zeitauflösungseffekts.

Reproduzierbarer technischer Fall: vollständig versorgtes N1+C2-Flour, identischer bezahlter Plan und zwei Stunden Laufzeit: dt1 verkauft für $28 320.00, dt6 für $28 320.00; dennoch 2 340.00 gegenüber 2 740.00 neue XP. Bei vollständig beschäftigten Maschinen erfasst dt1 am Abschluss eines Sechs-Sekunden-Batches höchstens eine produktive Sekunde, dt6 bis sechs. Bei zeitlich versetzten komplexen Batches kann der Unterschied geringer sein. Die Reproduktion nutzt `validate.simulate` mit ausschließlich unterschiedlichem dt und keinen Pausen. Dies sollte bei einer späteren Umsetzung als zweite, eng begrenzte technische Korrektur neben der wirtschaftlichen MK-Regel behandelt werden.

## 8. MK-Schattenpreise und Endgamegrenze

Die heutige Quote lautet: auf Cent aufgerundetes Maximum aus `Common-Kartenpreis × MK^1,7` und `0,25 × maximales Nettowertpotenzial der Familie pro Sekunde × 900 × ((MK+1)/2)^2,3`. Das Familienmaximum berücksichtigt weiterhin alle Rezepte dieser Maschinenklasse, auch später freischaltbare. Energiekarten verwenden Kohleäquivalent, Freight Kapazität/Fahrtzeit. Unter C2 werden diese Potenziale aus den neuen Preisen berechnet; die alten Upgradepreise werden ausdrücklich nicht eingefroren. Alle 4 410 Übergangsquotes für drei Modelle, 15 Familien und 98 Schritte sind separat gespeichert.

| Modell | Firma | Voll finanziertes MK99-Kapital $ | Nur Kartenquotes MK98→99 $ | Zusätzlicher Cash/min bei gleichem Layout | Untere Payback-Schätzung Tage |
| --- | --- | --- | --- | --- | --- |
| N0_A | iron | 926 051 372.96 | 30 268 021.26 | 56.25 | 373.68 |
| N0_A | flour | 1 035 206 591.71 | 33 757 208.98 | 63.75 | 367.73 |
| N0_A | steel | 6 400 868 495.16 | 209 390 929.90 | 508.00 | 286.24 |
| N0_A | bitumen | 2 235 174 440.06 | 73 002 064.02 | 292.00 | 173.62 |
| N0_A | copper_wire | 1 202 620 188.57 | 39 245 092.49 | 71.21 | 382.74 |
| N0_A | microchip | 30 912 300 822.90 | 1 010 504 750.36 | 3 050.25 | 230.06 |
| N0_A | industrial_equipment | 27 620 331 769.75 | 903 126 127.54 | 1 943.56 | 322.69 |
| N0_A | ai_server | 41 659 846 196.00 | 1 361 258 423.66 | 4 061.88 | 232.73 |
| N1_C | iron | 299 360 954.28 | 9 722 079.71 | 60.02 | 112.49 |
| N1_C | flour | 335 537 544.22 | 10 906 983.85 | 60.01 | 126.21 |
| N1_C | steel | 1 814 939 254.40 | 59 041 998.38 | 360.12 | 113.85 |
| N1_C | bitumen | 299 361 294.28 | 9 722 079.71 | 60.02 | 112.49 |
| N1_C | copper_wire | 454 708 306.76 | 14 723 797.55 | 90.05 | 113.55 |
| N1_C | microchip | 8 377 238 579.09 | 272 186 594.48 | 1 920.85 | 98.40 |
| N1_C | industrial_equipment | 8 497 727 047.71 | 276 216 808.44 | 1 920.87 | 99.86 |
| N1_C | ai_server | 10 369 057 860.90 | 336 667 067.82 | 2 521.18 | 92.73 |
| N1_C2 | iron | 299 315 776.94 | 9 720 598.58 | 60.00 | 112.51 |
| N1_C2 | flour | 335 492 366.88 | 10 905 502.72 | 60.00 | 126.22 |
| N1_C2 | steel | 1 814 758 545.04 | 59 036 073.86 | 360.00 | 113.88 |
| N1_C2 | bitumen | 299 316 116.94 | 9 720 598.58 | 60.00 | 112.51 |
| N1_C2 | copper_wire | 382 450 068.02 | 12 349 545.88 | 70.00 | 122.52 |
| N1_C2 | microchip | 7 798 196 839.09 | 253 160 588.72 | 1 760.00 | 99.89 |
| N1_C2 | industrial_equipment | 7 629 833 062.11 | 247 699 720.52 | 1 680.00 | 102.39 |
| N1_C2 | ai_server | 9 500 802 456.58 | 308 138 130.86 | 2 280.00 | 93.85 |

Dies ist ein marginaler Vergleich desselben vollständig versorgten Layouts, uniform MK98→MK99. Die zusätzliche Rate beträgt nur 0,25 des MK1-Flusses. Zusätzliche Storage-Käufe, Umbau und erneuter Anlauf sind noch nicht bezahlt; die Zeiten sind daher optimistische Untergrenzen, keine simulierten monatelangen Amortisationen. Schon der bestehende Paybackterm wächst bei MK99 auf rund 82 Spieltage; zusätzlich kann der preisunabhängige Kartenpreis-Mindestterm dominieren. Ein Preisaufschlag erhöht oft zugleich die Quote. Genau deshalb lässt sich dieses Zeitproblem nicht zuverlässig mit C2-Stückpreisen allein lösen.

Empfohlen ist **eine globale Überarbeitung dieser MK-Preisregel**, die sowohl den Paybackterm als auch den Mindestterm umfasst. Nur den Arbeitswert hochzusetzen oder nur den Paybackterm zu deckeln reicht nicht, wenn der Kartenpreisfloor weiter dominiert. Als konkrete Designentscheidung für die Umsetzung empfehle ich einen maximalen marginalen Amortisationshorizont von einer aktiven Spielsitzung bis höchstens einem Spieltag statt Monaten; das ist eine Zielvorgabe, keine hier freigegebene neue Kostenkurve. Keine weiteren Rezeptänderungen sind dafür nötig. Infrastrukturcliffs sind dagegen echte, sichtbare Investitionssprünge und bereits Teil der C2-Kalibrierung; eine pauschale Kostensenkung aller Hallen ist aus diesen Daten nicht zwingend.

Eine Gesamtdauer „Genesis bis MK99/Level100“ wird nicht erfunden: die Untersuchung enthält echte vierstündige Starts, vollständig finanzierte höhere Zustände und marginale Zeituntergrenzen, aber keine optimale durchgespielte Reinvestitions-/Contract-/Research-/Rarity-Karriere. Ohne eine Zielspielzeit und wegen der belegten MK- sowie XP-Effekte wäre eine einzelne Stundenzahl unbegründet. Die Empfehlung lautet deshalb klar: Preis-/Rezeptbasis ja, unveränderte gesamte Endgameökonomie noch nicht freigeben.

## 9. Contracts, Research und Brennstoffableitungen

| Modell | Kraftwerk | Fuel | Einheiten/min | Warenwert $/min | $/MW-Minute |
| --- | --- | --- | --- | --- | --- |
| N0_A | energy.coal_power_plant | coal | 60.00 | 72.00 | 1.2000 |
| N0_A | energy.gas_power_plant | natural_gas | 60.00 | 114.00 | 0.6333 |
| N0_A | energy.nuclear_power_plant | nuclear_fuel_assembly | 10.00 | 602.88 | 1.2058 |
| N1_C | energy.coal_power_plant | coal | 60.00 | 60.00 | 1.0000 |
| N1_C | energy.gas_power_plant | natural_gas | 60.00 | 60.00 | 0.3333 |
| N1_C | energy.nuclear_power_plant | nuclear_fuel_assembly | 10.00 | 386.22 | 0.7724 |
| N1_C2 | energy.coal_power_plant | coal | 60.00 | 60.00 | 1.0000 |
| N1_C2 | energy.gas_power_plant | natural_gas | 60.00 | 60.00 | 0.3333 |
| N1_C2 | energy.nuclear_power_plant | nuclear_fuel_assembly | 10.00 | 336.00 | 0.6720 |

Die echte Release-Balancingfunktion wird erneut auf die N1-Kopie angewandt. Weil N1 sämtliche Materialausbeuten erhält, bleiben Primärbedarf pro Fuel und damit die abgeleiteten Verbrauchsmengen gleich: Coal/Gas jeweils 60/min, Nuclear Fuel Assembly 10/min. Der Warenwert des verbrauchten Fuels ändert sich mit C2. Dies ist ein Opportunitätswert gegenüber Verkauf, keine zusätzliche doppelte Abbuchung durch die Engine. Wer Fuelkraftwerke statt der hier finanzierten Erneuerbaren baut, benötigt eine eigene vollständig finanzierte Brennstoffkette; ein separater Vorteil aller Fuelportfolios wurde nicht global optimiert oder simuliert.

Die tatsächlichen Angebots-, Kapazitäts-, Mengen- und Belohnungsfunktionen erzeugen `contract-quotes.csv`. Die Produktauswahl wird auf tatsächlich aktive, freigeschaltete Produktionen der finanzierten Firma begrenzt. Persönliche Angebote frieren die neuen Stückpreise bei Annahme ein; Kategorieaufschläge bleiben 0/20/40 %. Die Consortium-Poolformel 15/25 % wird separat ausgewiesen und ist nicht der volle Betrag je Mitglied. Keine dieser Quotes wird zusätzlich als abgeschlossener Vertragserlös zu den Marktlieferungen gezählt.

| Modell | Firma | Contract | Ziel min | Marktwert $ | Quote $ | XP | Cash/Markt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| N0_A | steel | daily | 60.0 | 40 500.00 | 48 600.00 | 1 219.25 | 1.200 |
| N0_A | steel | regular | 8.0 | 6 767.60 | 6 767.60 | 236.69 | 1.000 |
| N0_A | ai_server | daily | 60.0 | 87 280.57 | 104 736.69 | 2 018.59 | 1.200 |
| N0_A | ai_server | weekly | 240.0 | 242 564.09 | 339 589.72 | 6 606.98 | 1.400 |
| N0_A | ai_server | regular | 8.0 | 32 437.67 | 32 437.67 | 577.33 | 1.000 |
| N1_C | steel | daily | 60.0 | 35 341.23 | 42 409.48 | 1 245.49 | 1.200 |
| N1_C | steel | regular | 8.0 | 5 311.93 | 5 311.93 | 241.42 | 1.000 |
| N1_C | ai_server | daily | 60.0 | 95 238.93 | 114 286.72 | 2 044.24 | 1.200 |
| N1_C | ai_server | weekly | 240.0 | 241 721.21 | 338 409.69 | 6 513.88 | 1.400 |
| N1_C | ai_server | regular | 8.0 | 22 829.01 | 22 829.01 | 500.42 | 1.000 |
| N1_C2 | steel | daily | 60.0 | 35 340.75 | 42 408.90 | 1 245.58 | 1.200 |
| N1_C2 | steel | regular | 8.0 | 5 310.75 | 5 310.75 | 241.42 | 1.000 |
| N1_C2 | ai_server | daily | 60.0 | 88 662.13 | 106 394.56 | 2 090.77 | 1.200 |
| N1_C2 | ai_server | weekly | 240.0 | 233 342.33 | 326 679.27 | 6 690.04 | 1.400 |
| N1_C2 | ai_server | regular | 8.0 | 19 028.67 | 19 028.67 | 497.38 | 1.000 |

Preisänderungen beeinflussen bei mehreren ausgewählten Produkten auch die wertgewichtete Mengenverteilung eines Angebots. N1 senkt bei einigen Gütern den rekursiven Work-Wert, was Mengen-/Work-XP-Quotes ebenfalls beeinflusst. Akzeptierte alte Angebote, eingefrorene Mitgliedspreise und bereits fahrende Frachten müssten bei einer späteren Migration bewusst erhalten oder umgestellt werden; diese Phase ändert sie nicht.

Research ist in allen Budget-/Engine-/Genesis-Hauptvergleichen null. Die zusätzliche Sensitivität nutzt einmal den vollständig verdienten gesamten Node-Katalog ohne Produktspezialisierung und einmal keinen Research: 2 118 Preis-/Mechanikzeilen. Das ist ein mechanischer Zustandstest, keine kostenlose Researchfirma. Speed erhöht Durchsatz/Inputs, Energie-Research Erzeugung, Freight-Research Kapazität und Storage-Research Lager. Wert-/Contractboni werden über die bestehenden Resolver auf die C2-Basis angewandt. Neue Produktspezialisierungen, eine optimale RP-Allokation und zufällige Rarity-Beschaffung sind kein Bestandteil der finanzierten Gewinnerbehauptung.

## 10. Zehn ausdrückliche Entscheidungsantworten

1. **N1+C2 nachweisbar fairer als N0+A?** Im erklärten vollständigen Versorgungskandidatenraum ja: bei Level25/$1 Mio. 14 statt einer Domain innerhalb 20 %, Rendite-/Ratenfaktor 1,277 statt 5,273; bei $1 Mrd. 11 statt einer, Faktor 1,862 statt 6,477. Nicht jede Phase ist gleich und im Billionen-Endgame bleibt Faktor 5,640. Keine globale Fairnessbehauptung.
2. **Sinnvollste Parameter?** Primary $1, Processing $120, Fabrication $40, Assembly $120 pro Maschinenminute; E=$0/MW-Minute. Das ist der Sieger der 1 146 Varianten mit transparenter Branchen-, Budget-, Level- und inkrementeller Erweiterungsgewichtung. Energie-Infrastruktur wird real bezahlt, nicht über einen erfundenen laufenden Tarif.
3. **Profitabilität jedes Verarbeitungsschritts?** Alle 304 Schritte haben positive zusätzliche nominale Warenwertschöpfung; pro volle MK1-Karte 120/40/120 Dollar je Stufe. Die 608 Kapital-/Kontextquotes zeigen die wirklichen unterschiedlichen Amortisationen, die 24 A/B-Enginevergleiche die gemessenen Mehrerlöse und beobachtete Amortisation. Free-Starter-Median null ist keine Aussage über bezahlte Expansion.
4. **Welche Branchen bleiben benachteiligt?** Die stärkste/schwächste Domain und ihr Rückstand sind für jeden Budget-/Levelzustand ausgewiesen. Besonders kleine Budgets können fortgeschrittene Domains noch nicht finanzieren; sehr hohe Budgets zeigen trotz C2 große Abstände. Die Level25-Liste in Abschnitt 4 benennt konkrete schwächste Strategien, statt einen Domainnamen für alle Phasen zu verallgemeinern.
5. **Warum?** Ganze vollversorgte Blöcke, Zutatenmix, Starterkarten je Klasse, Transportwertdichte, Fahrtzyklen, erweiterbare aber konvex teure Slots/Hallen und familienweit berechnete Upgradequotes. Aufgerundete, dauerhaft gleichzeitig aktive Verbraucher erfordern tatsächlich zusätzliche Vorproduktion. Das ist eine Layout-/Investitionsfrage und kein grundsätzlicher Enginefehler.
6. **Weitere Rezeptänderungen erforderlich?** Keine ist durch diese Ergebnisse als notwendig nachgewiesen. Exaktes N1 bleibt erhalten; alle getesteten vollversorgten Ketten werden anhand ihrer realen Lieferdaten beurteilt. Reste der Branchenstreuung rechtfertigen keine weiteren 353 Spezialkorrekturen.
7. **MK-/Infrastrukturkosten anpassen?** Für ein Endgame mit Fortschritt über Stunden/Tage statt monatelanger marginaler Amortisation: ja, eine globale Revision der MK-Preisregel einschließlich Floor ist begründet. Eine zusätzliche allgemeine Infrastrukturpreisänderung ist nicht zwingend; ihre Sprünge sind in den zwei Erweiterungskontexten transparent eingepreist.
8. **Alle vollversorgten Testketten lauffähig?** Der Nachweis steht in den Ressourcen-/Status- und Lieferquoten in Abschnitt 6 sowie `stability-proof.csv`. Die Firmen besitzen alle gleichzeitig benötigten Inputs, Energie und tatsächlich finanzierte Routen. Kleinere unterversorgte P11-D-Layouts werden nicht als Enginebug bezeichnet. Die separate XP-Zeitauflösung ist ein Fortschrittsproblem, kein Lieferausfall.
9. **Gesamtdauer der Progression?** Vier Stunden Genesis wurden tatsächlich gemessen, inklusive Level/Unlocks. Höhere Budgets sind deklarierte finanzierte Zustände. Die bestehenden späten MK-Quotes ergeben bereits marginale Untergrenzen von vielen Spieltagen/Monaten, deshalb kann eine vernünftige gesamte MK99-Karriere nicht allein durch neue Preise zugesagt werden. C2 schafft keine direkten neuen XP; N1 verändert Mengen-/Work-Verhältnisse, die vorhandene XP-Schrittweitenabhängigkeit bleibt zu beachten.
10. **Bereit für produktive Implementierung?** N1+C2 als klar ausgewählte Preis-/Rezeptbasis ja; unveränderte Gesamtkosten und verbindliches Endgame-Pacing nein. Das kleinste begründete zusätzliche wirtschaftliche Eingriffsfeld ist **eine globale MK-Preisformel**, nicht weitere Rezepte oder Domainboni. Zusätzlich muss die technische XP-Zeitauflösung bei der späteren Fortschrittsumsetzung konsistent behandelt werden, bevor eine einheitliche Online-/Catchup-Dauer versprochen wird. Diese Offlinephase nimmt keine Freigabe vor und implementiert nichts.

## 11. Dateien, Reproduktion, Bestandsschutz und Stopp

Erstellt wurden der Bericht, die vollständige Preisvergleichstabelle mit 353 Produkten und die Wirtschaftstabelle mit 1124 eindeutig gekennzeichneten Nominal-/Engine-/Genesis-/Inkrementalzeilen. Alle weiteren Daten und Werkzeuge liegen ausschließlich in `artifacts/phase11e`. **5,116 zuvor vorhandene Dateien haben identische SHA-256**, einschließlich produktivem Code/Daten, bestehenden Tests/Skripten/Berichten, sämtlichen P11-D-Artefakten, den fünf persönlichen Spielständen und 4 083 Dateien bestehender Windows-Builds. Persönliche Saves wurden nur gehasht, nicht geladen. Kein Build erstellt; kein vorhandener Test verändert. Die frühere Zahl 1 998 bestandener Tests/16 Migrationen wurde nicht als neuer Testlauf ausgegeben.

| Prüfung | Abdeckung |
| --- | --- |
| Produkte / N1-Änderungen | 353 / 178 geändert, 126 weitere unverändert, 49 Primärrezepte unverändert |
| Graph | 708 identische Zutatenkanten; keine fehlenden Inputs, keine neuen Zyklen, positive Mengen |
| Finanzierte Profilsuche | 49,385 Vollversorgungsprofile; Schattenquotes für jede Parameterkombination |
| Parameter-/Kohortenraster | 1 146 Kombinationen × 30 Budget-/Levelkohorten; 90 finale Vergleichskohorten |
| Reale Engine | 78 Firmenzustände × 4 Zeitpunkte =312 Datensätze; davon24 A/B-Paare |
| Echter Genesis | 18 Firmen ×5 Zeitpunkte =90 Datensätze; Käufe/Unlocks wirklich erspielt |
| Kalibrierung | 9 identische Firmen dt1 gegen dt6, inklusive XP-Abweichung |
| Inkrementelle Schritte | 304 Starter- und 304 volle-Hallen-Quotes |
| Upgradequotes / Research | 4 410 Übergangsquotes; 2 118 Researchfälle |
| Geschützter Bestand | 5,116 identische Prüfsummen; keine produktive Änderung |

Wesentliche Rohdaten: `profiles.json` (vollständige finanzierte Karten-/Supportfamilien), `parameter-ranking.csv`, `candidate-cohorts.json`, `cohort-comparison.csv`, `domain-winners.csv`, `prices.csv`, `incremental-all-products.csv`, `incremental-templates.json`, `engine-validation.csv`, `engine-plans.json`, `incremental-engine.csv`, `paired-cash-traces.csv`, `stability-proof.csv`, `step-calibration.csv`, `genesis.csv`, `genesis-events.csv`, `genesis-milestones.csv`, `upgrade-quotes.csv`, `endgame-upgrade-payback.csv`, `fuel-consequences.csv`, `contract-quotes.csv`, `research-sensitivity.csv`, `progression-work.csv`, `weight-sensitivity.csv`, `audit-proof.json`, `completion-proof.json` und `baseline.json`.

Reproduktion mit der vorhandenen Umgebung, aus dem Projektordner; NumPy stammt ausschließlich aus dem bereits vorhandenen P11-C-Auditordner:

```powershell
# baseline.json stammt vom Phasenbeginn und darf nicht ersetzt werden.
.\.venv\Scripts\python.exe -B artifacts/phase11e/search.py prepare
.\.venv\Scripts\python.exe -B artifacts/phase11e/search.py optimize
.\.venv\Scripts\python.exe -B artifacts/phase11e/validate.py
.\.venv\Scripts\python.exe -B artifacts/phase11e/genesis.py
.\.venv\Scripts\python.exe -B artifacts/phase11e/audit.py
.\.venv\Scripts\python.exe -B artifacts/phase11e/report.py
```

Verbleibende Grenzen: kein global optimales gemischtes Unternehmen; keine vollständig durchgespielte Endgame-Karriere; keine optimierte zufällige Rarity-Beschaffung oder Researchallokation; keine simulierten abgeschlossenen Contracts/Consortium-Verträge; keine vollständige Optimierung von Fuelkraftwerksportfolios; keine Save-Migration unter neuen Preisen. Erweiterungsquotes voller Hallen sind Kapital-/Rateberechnungen, keine 304 zusätzlichen Langzeitsimulationen. Sehr hohe Budgets bleiben durch das deklarierte Karten-/Transport-/MK-Raster begrenzt.

**Stopp:** Die finale Offlinekalibrierung ist abgeschlossen. Produktives Industriova bleibt N0 mit heutigen Preisen und Kosten. Keine weiteren Rezepte, Kosten, Produktionsfunktionen oder automatischen Controller wurden geändert. Es wurde kein persönlicher Spielstand verändert und kein Windows-Build erzeugt. Die konkrete Empfehlung und ihre begrenzten zusätzlichen Umsetzungspunkte liegen zur Freigabe vor.
