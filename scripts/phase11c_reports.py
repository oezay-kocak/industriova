"""Render reproducible P11-C results after all runners have completed."""
from pathlib import Path
import csv,json,sys,hashlib,math
root=Path.cwd();sys.path.insert(0,str(root/'src'));out=root/'artifacts/phase11c'
from production_zero.core.infrastructure_prices import facility_price
def read(name):return list(csv.DictReader((out/name).open(encoding='utf-8-sig')))
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'---|'*len(headers),*['| '+' | '.join(str(x) for x in row)+' |' for row in rows]])
def write(name,text):(root/'docs'/name).write_text(text,encoding='utf8')
tests=json.loads((out/'regression/results.json').read_text(encoding='utf8'))
assert len(tests)>=98 and all(t['exit_code']==0 for t in tests)
migrations=json.loads((out/'migration-audit.json').read_text(encoding='utf8'));assert migrations['passed']==16
baseline=json.loads((out/'baseline.json').read_text(encoding='utf8'))
changed=[p for p,h in baseline.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
allowed=['src\\production_zero\\core\\commands.py','src\\production_zero\\core\\infrastructure_prices.py','src\\production_zero\\ui\\factory_view.py','src\\production_zero\\ui\\factory_view_v2.py']
allowed.append('tests\\test_industriova_release_integration.py')
assert set(changed)==set(allowed),changed
(out/'protected-verification.json').write_text(json.dumps(dict(baseline_files=len(baseline),changed=changed,other_files_unchanged=True,personal_saves=5,build_files=4083),indent=2),encoding='utf8')
prices=list(csv.DictReader((root/'docs/industriova-03-phase11c-price-model-comparison.csv').open(encoding='utf-8-sig')));by={r['product_id']:r for r in prices}
assert len(prices)==353 and len(by)==353
assert all(math.isfinite(float(r['price_'+m])) and float(r['price_'+m])>0 for r in prices for m in ('A','B','C'))
companies=read('company-search.csv');front=read('frontiers.csv');multi=read('pareto-multidimensional.csv');branches=read('industry-comparison.csv');engine=read('engine-validation.csv');genesis=read('genesis.csv');events=read('investment-events.csv');controlled=read('controlled-engine.csv');transitions=read('processing-transitions.csv')
curve=[]
for n in (10,11,12,15,20,25,50,100,250,500,1000):curve.append([n,facility_price('factory',n-1),math.fsum(facility_price('factory',k) for k in range(n)),math.fsum(facility_price('factory',k) for k in range(1,n))])
write('industriova-03-phase11c-factory-unlimited-report.md',f'''# P11-C – unbegrenzte Factory-Erweiterung

Stand 23.10.2026. Produktiv ausschließlich die globale Kaufgrenze entfernt und unmittelbar nötige Quote-/Navigationsbehandlung ergänzt. Keine Preis-/Rezept-/Produktionsänderung, kein Build.

## Implementierung

Beide regulären Kaufpfade in core/commands.py (PurchaseHall und PurchaseProductionUnit) akzeptieren nun Halle 11, 12 und weitere. Kein Ersatzcap. Neue Hallen bleiben 5 Linien × 10 Plätze, Startlinie mit 3 Plätzen; maximal 50 Verarbeitungskarten je neuer Halle. Processor/Fabricator/Assembler bleiben mischbar. Die Gesamtplatzzahl ist deshalb 50*N bei N regulären voll ausgebauten Hallen. Historische Geometrien bleiben unverändert lesbar.

core/infrastructure_prices.py behält alle Parameter und Rundungsschritte von facility_price bei. Nur Overflow/ungültige numerische Ergebnisse werden in ValueError umgewandelt. Der Kauf validiert den Quote vor Cashabbuchung/Mutation. ui/factory_view.py deaktiviert einen numerisch nicht darstellbaren Kaufquote. Kein kostenloser Fallback. Finite Floats haben bei extremen Summen nicht mehr Centpräzision; dies ist eine Zahlendarstellungsgrenze, kein zusätzlicher Gebäudehöchstwert.

Die vorhandene scrollbare QTreeWidget-Navigation enthält dynamische Einträge. ui/factory_view_v2.py erzeugt sie nur bei geänderter ID-Liste neu, aktualisiert sonst bestehende Labels/Selektion. Die aktive Halle wird angezeigt, nicht die gesamte Firma als Kartenwidgetbaum gerendert. Listenaktualisierung bleibt linear; keine behauptete konstante Laufzeit für beliebig große Firmen. 1000 synthetische Hallen werden durch den UI-Test geprüft. Keine zehn festen UI-Gebäudeplätze gefunden.

## Unveränderte Kaufkurve

n bezeichnet bereits vorhandene Hallen. Erste Halle kostet 1000, weitere nach der vorhandenen Funktion mit effektivem zweiten Basiswert 15200 und Wachstum n^2.5, auf 100 aufgerundet. Startgebäude im echten Neustart ist geschenkt; kumulierte Modellkosten und tatsächliche Zukaufkosten werden getrennt.

{table(['Hallennummer','Einzelpreis','Summe inklusive bezahlter erster Halle','Zukäufe bei geschenkter erster Halle'],curve)}

Quotes bis zu diesen Hallenzahlen sind endlich und positiv. Tests prüfen zudem die unveränderten ersten Preise, monotones Wachstum bis 1000 sowie kontrollierte Ablehnung bei counts 10^124 und 10^1000. Diese Zahlen sind Testpunkte, keine eingeführten Limits.

## Verifikation

{len(tests)} Testmodule vollständig und einzeln in isolierten Qt-Prozessen: **{sum(t['passed'] for t in tests)} Tests bestanden**, keine Filter und keine übersprungenen Tests. Die erste gemeinsame Ausführung wurde nach Fixture-/Tempfehlern abgebrochen; alle Module wurden anschließend mit eigenen temporären Verzeichnissen ausgeführt. Der alte Cap-Integrationstest wurde erhalten und passend auf erlaubten Hallenkauf sowie weiterhin atomare Cashprüfung umgestellt. Im neuen SQLite-Test wurde die explizite Datenbankinitialisierung ergänzt. Beide betroffenen Module anschließend erneut vollständig grün; ursprüngliche und korrigierte Logs bleiben erhalten. Vollständige Logs und Exitcodes: artifacts/phase11c/regression/results.json. Neue Tests: beide Kaufpfade über 10→11→12 bis 25; volle lokale 50 Plätze; Gesamtzahl >500 und tatsächliche Installation von 501 Processor-Karten; Cashatomizität; SQLite Save/Load; Legacy-Sechs-Linien-Halle; 1000 Hallen und Navigationseintragsidentität.

Alle **16 historischen Migrationen** gegen unveränderliche Archivkopien erneut geprüft, volle serialisierte Payloads identisch zum bisherigen P8/P10-Referenzstand und idempotent; Schema bleibt 9. Kein persönlicher Save migriert.

SHA256-Bestandsschutz: {len(baseline)} Ausgangsdateien erfasst. Exakt die vier genannten produktiven Dateien sowie der an das neue Design angepasste bestehende Integrationstest verändert; alle übrigen erfassten Dateien einschließlich P11-A/P11-B, sämtlicher Spieldaten/Preis-/Researchdefinitionen, fünf persönlicher Saves und 4083 Builddateien unverändert. Neue Test-/Offlinewerkzeuge und Ergebnisse separat. Nachweis: artifacts/phase11c/protected-verification.json, Ausgangsmanifest baseline.json, Quellenbackup source-before.zip.
''')

unchanged=sum(float(r['price_A'])==float(r['price_B']) for r in prices)
primary=[r for r in prices if r['stage']=='Primary Production']
weak=sorted(prices,key=lambda r:float(r['added_value_machine_minute_A']))[:12]
sample=['iron_ore','copper_ore','crude_oil','platinum_ore','wheat','iron','steel','lumber','flour','biodiesel','microchip','industrial_equipment','ai_server']
models_table=table(['Produkt','A heute','B Primary=1 mit Ankern','C Arbeit/Energie'],[[r,*[by[r]['price_'+m] for m in ('A','B','C')]] for r in sample])
endgame_rows=[]
for r in front:
 if float(r['budget'])>=1e9 and r['level']=='25':
  c=next(x for x in companies if x['budget']==r['budget'] and x['level']==r['level'] and x['product_id']==r['best_product'])
  endgame_rows.append([r['budget'],r['model'],c['product_id'],c['mk'],c['factory_cards'],math.ceil(int(c['factory_cards'])/50),c['cost']])
summary_table=table(['Budget','Level','Modell','bestes Muster','nominal $/min','2D-Pareto','innerhalb 20%','Relaxationslücke %'],[[r[k] for k in ('budget','level','model','best_product','best_continuous_cash_min','frontier_count','within_20_percent','upper_gap_percent')] for r in front if r['level']=='25'])
engine_table=table(['Produkt','Modell','Minuten','Nominal $/min','real $/min seit Start','Cash minus Investition'],[[r['product_id'],r['model'],float(r['seconds'])/60,r['nominal_cash_min'],r['realized_cash_min'],r['net_after_investment']] for r in engine if r['seconds']=='7200'])
genesis_table=table(['Rohstoff','Verarbeitung','Modell','Sekunden','Cash','verbuchte Einnahmen','Investitionen','Trucks'],[[r[k] for k in ('raw_product','processing','model','seconds','cash','earnings','additional_investment','truck_count')] for r in genesis if r['seconds'] in ('7200','28800')])
# Per-budget domain dispersion: concrete industry comparisons, not product price ratios.
domain_summary=[]
for budget in sorted({r['budget'] for r in branches},key=float):
 for model in ('A','B','C'):
  group=[r for r in branches if r['budget']==budget and r['model']==model and r['level']=='25']
  best=max(group,key=lambda r:float(r['continuous_cash_min']));worst=min(group,key=lambda r:float(r['continuous_cash_min']))
  domain_summary.append([budget,model,best['domain'],worst['domain'],float(best['continuous_cash_min'])/float(worst['continuous_cash_min']),worst['lag_to_best_percent']])
reco='Modell C als nächste gemeinsam zu kalibrierende Schattenvariante; keine produktive Übernahme. Die Daten beweisen keine globale 10–20-%-Fairness.'
text=f'''# P11-C – mathematische Wirtschaftsmodelle und Entscheidungsvorlage

Stand 23.10.2026. Ausschließlich Offline-Analyse. Alle 353 Originalpreise und Gameplaywerte unverändert. Factory-Gebäude nach Teil A ohne globales Kaufcap. Quellen: vollständige P11-A/P11-B-Berichte und CSVs plus aktuelle produktive Funktionen. Eingabe-SHA256 und reine Katalogcache-Gleichheitsprüfung in artifacts/phase11c/proof.json.

## 1. Fragestellung und Dominanz

Vergleichbare Strategien haben dasselbe Budget, zulässigen Level-/Unlock-/Researchzustand, Qualitätszugang und Zeithorizont. Pareto-Dominanz bedeutet in allen betrachteten Zielen mindestens gleich gut und in mindestens einem strikt besser. Ein höherer Stückpreis, Lastmaschinenumsatz oder höhere Rendite bei mehr Kapital ist allein kein Dominanzbeweis. Markt bleibt fest; kein Nachfrageabschlag, keine Steuer oder Zufallsmarktmechanik vorgeschlagen.

Die Untersuchung umfasst **{len(companies)}** dimensionierte Einproduktfirmen über zehn Budgets, Levelkohorten 1/5/25 und Common-MK1/10/50/99, daneben {len(engine)} echte Engine-Messpunkte, {len(genesis)} Genesis-Messpunkte und 9531 statische Qualitäts-/Research-/Contractquotes. Levelkohorten sind vorverdiente Lifetime-Freischaltungen ohne Research; sie sind ausdrücklich keine neu gestarteten Firmen mit kostenlos erspieltem Fortschritt. Echter P10-Neustart wird separat simuliert.

## 2. Drei vollständige Schattenpreislisten

A: produktive BASE_MARKET_PRICES unverändert. B: alle 49 Primäranker=1, danach ausschließlich vorhandenes build_fixed_prices mit allen übrigen Ankern und Rundungen. C: Primärprodukte=1; für jedes Folgeprodukt rekursiv

    pC(output) = Summe(a_i*pC(input_i))/q + 120*t/(60*q) + 0.01*P*t/(60*q)

q=Output/Zyklus, a_i=Inputs/Zyklus, t=Sekunden, P=Rezept-MW. 120 Dollar je Maschinenminute wird aus normiertem Primary-Umsatz 120 U/min × 1 Dollar abgeleitet. 0.01 Dollar je MW-Minute ist ein ausdrücklich gewählter **Bewertungsparameter**, keine reale Stromrechnung und kein nachgewiesener optimaler Energietarif. Alte Mindestanker entfallen vollständig. Die Summe enthält schon bewertete Vorarbeit; hinzu kommen nur eigene Maschinenminute und eigener Leistungseinsatz. Kein Zählen von Zutatenarten und kein erneutes Addieren des gesamten Rohstoffwerts. Parallelität entsteht über echte Inputmengen und dimensionierte Karten, nicht einen pauschalen Mehrzutatenbonus.

C belohnt jede Verarbeitung mit positivem zusätzlichem Warenwert, garantiert aber nicht positiven Cashflow nach zusätzlichen Investitionen. Die Parameter sind eine transparente Testhypothese, keine abschließend identifizierte Preisformel. All-Research- und Rarityänderungen wirken später auf dieselben Basispreise; nicht erneut in die Preisrekursion zählen.

{models_table}

B lässt **{unchanged}/353** heutige Preise exakt unverändert. Das allein widerlegt die Erwartung, dass uniforme Primary-Preise automatisch alle Folgeproduktrelationen reparieren. A-Primärspreizung: Platinum 5.8 gegenüber Wheat 0.95 = 6.105263-facher Preis bei identischer Basisrate/Leistung; Crude Oil 2.2× und Copper 1.4× Iron Ore. Spätere Company-Level und Nutzen als Vorprodukt sind reale unterschiedliche Eigenschaften, beseitigen aber im freigeschalteten Rohstoffverkauf diese nominale Erlösspreizung nicht.

CSV docs/industriova-03-phase11c-price-model-comparison.csv enthält je Produkt alle drei Preise, absolute/prozentuale Deltas, direkte Inputwerte und Wertschöpfung/Zyklus und zusätzlicher Maschinenminute. Die CSV enthält außerdem eine vollständig bepreiste 1-U/min-Zielhülle mit allen Kartenanzahlen, Stromerzeugern und Freight. Diese ist ein nomineller Flussplan; tatsächlicher Betrieb braucht die dokumentierte Steuerung und Unlocks. Rekursive Arbeitszeit und MW-Minuten stammen aus den realen Mengen und Rezeptleistungen; Rohstoffmengen und vollständige Vorproduktion sind ebenfalls je Zeile enthalten.

## 3. Optimierungsmodell, diskrete Investitionen und Schranken

Netzflussbedingungen: Für jedes Produkt i muss eigener Ausstoß plus Anfangspuffer mindestens internen Verbrauch plus Verkauf erfüllen. Dauerleistung wird ohne Anfangswaren gerechnet. Zyklusfluss f_i <= Karten_i * MK-/Rarity-Outputrate; Karten sind ganzzahlig. Ganze angeforderte MW müssen durch Generatoren passen. Gebäude/Slots sind diskret und verursachen die originalen Kurvenkosten, ohne Factorycap. Freight gilt nur für verkaufte Endwaren, nicht interne Zwischenprodukte. Cargo und Reisezeit folgen den realen Regeln. Global Storage ist ein Batchpuffer, kein Produktionsmultiplikator.

Hier verwendetes nachvollziehbares Näherungsverfahren: vollständige Enumeration aller zulässigen Einprodukt-Zielketten; zusammengeführte gemeinsame Vorprodukte; ganzzahlige Karten durch Aufrundung benötigter Raten; vier uniforme MK-Alternativen; Solar oder Wind, jeweils günstigere vollständige Quote; alle vier reinen Freightflotten, jeweils günstigere Quote, eine erweiterbare Anlage. Kompakte Belegung der vorhandenen und zusätzlichen Gebäude. Startergutschrift: drei Extractor, zwei Processor, ein Solar, zwei Trucks, kostenlose Startgebäude der drei Primary-Typen/Factory/Energy/Garage. Jede zusätzliche Karte, Upgrade, Gebäude-, Linien-, Slot- und Lagererweiterung wird bezahlt. Gepufferter Bedarf konservativ als Summe ganzer gleichzeitig zugeordneter Chargen; Fuelkraftwerke sind nicht Teil dieser statischen Suchfamilie, ihre Mechanik bleibt aus P11-B dokumentiert.

Die beste finanzierbare Rate wird je Familie monoton eingeklammert und zwölfmal halbiert; Rate-Stützraum bis zur letzten Zweierpotenz 1048576 Einheiten/min. Dies ist ein **Analyseraster**, kein neues Spielcap. Nicht global durchsucht: Firmen mit mehreren verkauften Produkten, gemischte MK pro Karte, Fuel-/Generator-/Flottenmixe, anders aufgeteilte Gebäude, beliebige Steuerungs- und Reinvestitionspolitiken. Es wird daher ausdrücklich kein globales Optimum behauptet.

Zusätzliche obere Schranke: Infrastruktur, Strom und Freight kostenfrei relaxieren, Karten bruchzahlig zulassen und je Rezept günstigste Kosten/Ratenrelation aus den vier MK-Stufen verwenden. Einheitenkapital aus der gesamten Vorproduktion addieren; alle Starterkarten mit insgesamt 2160 Common-Ersatzwert großzügig als Kapitalgutschrift ansetzen. Obergrenze=(Budget+2160)*max(p/Einheitenkapital). Das ist für diesen Common-/MK-Zustandsraum eine optimistische Relaxation, nicht ein finanzierbarer Plan. Die ausgewiesenen Lücken umfassen weit mehr als das kleine Ratenraster und erlauben keinen Beweis globaler Branchenfairness.

## 4. Budget-, Stufen- und Branchenvergleich

Budgets 1250/5000/10000/50000/100000/500000/1000000/10000000 sowie 1 Milliarde und 1 Billion. Alle Level-1-/5-Ergebnisse separat in Ergebnisdateien; hier Level 25 mit vorverdienten Unlocks, kein Research. Prozentabweichung=100*(1−Cashrate/zulässige beste gefundene Cashrate). Referenz stets derselbe Budget-/Level-/Modellraum, nicht Level 1 gegen voll freigeschaltete Firma.

{summary_table}

Hohe MK und viele Factory Halls werden tatsächlich bepreist, nicht als Gratisstart gesetzt. In den Endgame-Stützpunkten:

{table(['Budget','Modell','bestes Muster','MK','Factory-Karten','benötigte Hallen','Investition'],endgame_rows)}

MK99 wurde mit sämtlichen Übergangskosten untersucht, muss deshalb nicht der Renditesieger sein. Unterschiedliche wirtschaftlich sinnvolle MK-Stufen statt automatisch höchstem MK sind ein Ergebnis, kein ausgelassener Zustand.

Branchenstreuung der jeweils besten gefundenen Endproduktfirma je Research-Domain:

{table(['Budget','Modell','stärkste Domain','schwächste Domain','Faktor best/schwach','schwächste Domain Rückstand %'],domain_summary)}

Alle 15 Domains einschließlich Metalle/Edelmetalle, Oil/Gas/Chemie, Landwirtschaft/Food/Biodiesel, Elektronik/Semiconductors, Maschinenbau, Energie-/Erneuerbarentechnik und komplexe Assembly sind in artifacts/phase11c/industry-comparison.csv einzeln ausgewiesen. Keine Preisrelation wird als vollständiger Unternehmensvergleich ausgegeben. Processing/Fabrication-Rezeptabweichungen gehen durch q/t/P direkt ein. Zusätzliche Gebäudezahlen und MK können den Gewinner ändern; frontiers.csv enthält die Gewinner je Kohorte, nicht eine universelle Meta.

Pareto: frontiers.csv ist die zweidimensionale Kosten-/Cashratenfront. pareto-multidimensional.csv betrachtet zusätzlich MW, Factory-Karten, erforderlichen Level und Basisreisezeit; damit wird bloße höhere Rendite bei anderen Nachteilen nicht pauschal als Dominanz bezeichnet. Dies sind vollständige Fronten des genannten Kandidatenraums, nicht aller im Spiel denkbaren Unternehmen. Lifetime-Erspielzeit bleibt dort eine nicht quantifizierte Voraussetzung.

## 5. Echte Engine-Gegenprüfung

Reale SimulationEngine bei 1-s-Schritten, vollständige unveränderte Input-/Output-/Fuel-/Storage-/Dispatch-/Arrival-Transitions. Ein vorhandener Offlinecache ersetzt ausschließlich wiederholte reine Katalogarbeitswerte nach 353 Gleichheitsprüfungen. Keine GameState-Ergebnisse werden gecacht. Shadowpreise werden nur im isolierten Python-Prozess für die Marktlesefunktion eingesetzt und im finally zurückgesetzt; keine Preisdatei oder Spielsave wird geändert. Verschiedene Modelle erhalten dieselben Anfangsbedingungen.

Bei diesen Maturity-Firmen sind Inputs anfangs leer und benötigte Unlocks vorverdient. Tabellenrate ist eine kontinuierliche **Obergrenze**, nicht ein verkaufter Output. Es gibt kein automatisches Lastfolgemanagement; überschüssige Zwischenprodukte können Lagerblockaden erzeugen. Das ist gerade ein Gegenbeispiel zur Gleichsetzung von Netzflusskapazität und nachhaltiger realer Steuerung. Für sehr große Suchfirmen wird die Engine-Stichprobe ausdrücklich auf die separat bepreiste 1-U/min-Zielhülle verkleinert, statt ungemessenes Budgetwachstum zu behaupten.

{engine_table}

Die Tabellen zeigen kumulierte reale Cashrate seit Start, nicht allein den letzten idealisierten Zyklus. Beobachtungszeitpunkte 10/30/60/120 Minuten, inklusive erster Lieferverzögerung. Negative Werte Cash minus Investition bedeuten im beobachteten Horizont keine Amortisation. Eine behauptete ewige Amortisation aus einem kurzen Lauf wäre unzulässig.

### Zusätzlicher Steuerungs-Gegenversuch

Mit unverändertem PauseMachines-Command hält ein isolierter Offlinecontroller jedes Vorprodukt bei ungefähr drei Inputchargen, prüft sekündlich und pausiert/resumiert die vorhandenen Karten. Dies ist eine untersuchte Betriebsstrategie, keine neue Spielfunktion oder behauptete normale Anfängerbedienung. Bei gleicher 1-U/min-Zielhülle liefert die echte Engine nach 120 Minuten:

{table(['Produkt','Modell','gelieferte Einheiten/min','Lagerbestand am Ende'],[[r['product_id'],r['model'],r['actual_units_min'],r['remaining_stock']] for r in controlled if r['seconds']=='7200'])}

Die nominelle Zielrate 1 ist eine Dimensionierungsvorgabe, nicht die volle Kapazität der aufgerundeten ganzen Karten. Tatsächlicher Durchsatz darf sie deshalb überschreiten. Die vorherigen Nominalobergrenzen wurden aus allen real installierten Karten, Vorproduktmengen und Freight separat berechnet. Vergleich ohne Steuerung: AI Server verkauft im beobachteten Horizont null bei nahezu vollem Lager; mit bedarfsgerechter Steuerung wird Output geliefert. Das kann eine Preisänderung allein nicht reparieren. Für alle drei Schattenpreise werden dieselben realen Ankünfte bei festen Preisen exakt umbewertet; keine drei unterschiedlichen Materialflüsse vorgetäuscht.

## 6. Echter P10-Neustart und dynamische Investition

Original _create_initial_state mit 1250 Cash, drei Primary-Startstandorten, unplatzierten acht Starterkarten, echten Anfangswaren und Initialunlocks. Installation, Zukäufe, Freightslots, Routing und Verarbeitung über vorhandene Commands. Wenn Lifetime-Unlocks tatsächlich verdient werden, kann ein vorhandener Processor eingesetzt werden. Vergleich direkte Rohstofflieferung gegen Iron/Copper/Flour-Verarbeitung, zusätzlich Crude-Oil-Start ohne geschenkte Drilling-Karte. Reinvestitionsregel: jede Minute bei ausreichendem Cash Truck und nötigen Slot kaufen, höchstens vier Trucks in dieser bewusst begrenzten Politik. Das ist kein Spielcap und keine optimale Politik. Alle Ausgabenzeitpunkte stehen in investment-events.csv. Keine vorab geschenkte Research-/Legendary-/MK99-Firma.

{genesis_table}

Die Tabelle verwendet zur eindeutigen Verknüpfung Simulationssekunden (7200=120 Minuten, 28800=480 Minuten). Anfangswaren bleiben als einmalige Ausstattung gekennzeichnet und werden nicht auf Dauer hochgerechnet. Produktpreise und Starterkartenasymmetrie sind getrennte Einflüsse.

## 7. Verarbeitung, Opportunitätskosten und Investitionshorizonte

Pro Zyklus zusätzlicher Warenwert=q*pOutput−Summe(a*pInput). Dieser Delta ist kein automatisch vereinnahmter Cashbetrag: unverkaufte Inputs, ungenutzte Freightplätze und zusätzliche Kartenkosten zählen. Für einen definierten Vergleich ist zusätzlicher Cashflow=vollständiger Kettenverkauf minus alternativ tatsächlich lieferbare Inputverkäufe; Payback=zusätzliche reale Investition / nachhaltig gemessener zusätzlicher Cashfluss, nur bei positivem Nenner. Gebäude-/Slot-Sprünge und benötigte Ganzkarten verhindern eine universelle Paybackzahl allein aus dem Rezept. Die realen Reinvestitions-/Verarbeitungswechsel oben liefern konkrete endliche Horizontvergleiche; sie sind kein Beweis optimaler Erweiterung jeder der 353 Ketten.

Zusätzlich sind alle 304 Verarbeitungsschritte in allen drei Modellen als vollständiger Kettenverkauf gegen Verkauf der direkten Vorprodukte bei gleichem rekursivem Inputfluss gerechnet: 912 Zeilen in processing-transitions.csv. Bezahlt werden jeweils diskrete Karten, Energie, vorhandene/nötige Plätze, homogene Freightflotten und Puffer. Dieselben schon vorhandenen Vorprodukte werden nicht doppelt gekauft. Gegenübergestellt werden zusätzliche Investition, Karten, angeforderte MW, realer externer Freight-Mengenbedarf und bedingte Mehrerlöse/Paybacks über 10/30/60/120/480 Minuten. Das ist ein kontinuierlicher, gesteuerter Flussvergleich, kein behaupteter tatsächlicher Contract- oder Engine-Ertrag jeder Kette.

{table(['Produkt','Modell','zusätzliches Kapital','zusätzliche MW','Inputverkauf Freight U/min','bedingter Mehrerlös $/min','bedingter Payback min'],[[r[k] for k in ('product_id','model','additional_capital','additional_requested_mw','cut_freight_units_min','nominal_additional_cash_min','conditional_payback_minutes')] for r in transitions if r['product_id'] in ('iron','steel','lumber','flour','biodiesel','microchip','ai_server')])}

Geringste aktuelle direkte Wertschöpfung je zusätzlicher Maschinenminute:

{table(['Produkt','Stufe','A zusätzlicher $/Maschinenminute'],[[r['product_id'],r['stage'],r['added_value_machine_minute_A']] for r in weak])}

C macht den direkten Arbeitszuschlag unabhängig von der Zahl verschiedener Zutaten. Das begrenzt rekursive Preisexplosion auf mengenmäßig erforderliche Maschinenarbeit plus bewertete Energiearbeit statt wiederholter willkürlicher Mindestanker. Hoher Preis komplexer Produkte ist trotzdem möglich, wenn viele reale Inputeinheiten pro Output benötigt werden. Ob das eingesetzte Kapital gerechtfertigt ist, entscheiden vollständige Firmen und Freight-/Zeithorizonte, nicht die positive Rezeptmarge allein.

## 8. Robustheit, Research, Rarity und Contracts

9531 Zeilen in sensitivity-contract-quotes.csv: alle Produkte/Modelle bei Common MK1/10/50/99, zulässigen Uncommon5/Rare10/Legendary20 und allen 645 Researchknoten ohne Produktspezialisierung. Das ist ein klar definierter reifer Researchzustand, kein normaler Anfänger. Quality-Investment unbekannt: kein garantierter Legendarypreis und keine faire Renditebehauptung ohne Qualitätsbeschaffung. Speed erhöht Output/Inputs, nicht MW; Rarity erhöht Output ohne entsprechenden Inputbonus. Freight-Rarity erhöht auch Reisezeit. Diese Asymmetrien können Rankings verschieben. Vier Produktspezialisierungen könnten zusätzlich 4 % je passendem Produkt geben, sind alternative Allokationen mit Respecbedingungen, kein Gratisbonus aller Produkte zugleich.

Persönliche Contractquotes werden über vorhandenes contract_cash_quote separat aus Basispreis und passenden value-/contract_value-Boni berechnet, Kategorieaufschläge 0/20/40 %. Consortium-Poolbeispiele benutzen höchstes berechtigtes Mitgliedspreisniveau und 15/25 %, ausdrücklich nicht voller Pool pro Contributor. Mengen/Angebote hängen von tatsächlicher Kapazität ab; Annahme/Beitrags-/Ablaufregeln und eingefrorene Quotes bleiben relevant. Diese Daten sind bedingte Quotes, keine simulierten Contract-Abschlüsse. Das Basissystem wird anhand Market bewertet; Contracts sind kein Reparaturmechanismus für Preisfehler.

## 9. Verbindliche Entscheidungsfragen

1. Rohstoffspreizung: identische 120 U/min, 6 MW, 340 Common-Kosten, aber A 0.95 Wheat bis 5.8 Platinum; nominal 114 bis 696 Dollar/min je Rohstoffkarte vor kompletter Infrastruktur/Fracht. Späteres Unlock ist ein Nachteil, keine Gleichheit nach verdienter Freischaltung.
2. Spätere Nachteile: unterschiedliche Inputmengen, Level/Lifetime-Gates, preisbedingt teure MK-Familien und konkreter zusätzlicher Kettenmix. Rohstoffverkauf und Nutzung als Input sind verschiedene Entscheidungen; sämtliche Mengen stehen je Produkt in CSV.
3. A kann nicht als bereits nachgewiesen fair gelten: obige Branchenfaktoren und Primärspreizung widersprechen einer pauschalen 10–20-%-Gleichheit. Dies ist keine Behauptung, jedes teure Produkt sei ein Fehler.
4. Über-/Unterbewertung ist zielabhängig. Die vollständige Vergleichstabelle zeigt auch Steel 10 gegenüber C {by['steel']['price_C']}, Lumber {by['lumber']['price_A']} gegenüber C {by['lumber']['price_C']} und AI Server {by['ai_server']['price_A']} gegenüber C {by['ai_server']['price_C']}. Anlagekosten-/Engine-Daten müssen zur Wertung dazugehören.
5. B löst die reine Rohstoffpreis-Asymmetrie, nicht die Ankerproblematik: {unchanged} Preise bleiben exakt gleich.
6. Ein konsistentes Modell braucht mengen-/outputnormierte Inputwerte, inkrementelle Arbeit und getrennte wirtschaftliche Bewertung von Kapital, Energie und Liefereffekten; nicht nochmal komplette Vorarbeit addieren.
7. Arbeitszuschlag 120 Dollar/Maschinenminute ist eine normierte Testgröße aus 1-Dollar-Primary, kein empirisch als optimal bewiesener Satz.
8. Rekursion nur eigener Zusatzarbeit und Energie verhindert doppelte Vorarbeitszählung; feste manuelle Mindestanker in C entfallen. Die Inputmengen selbst können Preise weiterhin stark wachsen lassen.
9. Aus den Suchfirmen und Engine-Raten sichtbar: Ganzkarten/MW, teure Gebäude/Slots, Frachtreisezeit und Lager können Rendite stärker verändern als ein Stückpreis. Es gibt kein absolutes Firmenmaximum nach A.
10. MK99 bedeutet Faktor 25.5, aber tatsächliche Upgradeinvestitionen bis zu Milliarden je Familie. Die vier MK-Zustände wurden separat bezahlt; Gewinner können bei großem Kapital und Flächenkosten wechseln. Kein kostenloses MK99 angenommen.
11. Vergleichbar attraktive Branchen werden pro Budget/Kohorte mit Rückstand ≤20 % gezählt; Zahlen stehen in frontiers.csv und den Tabellen, nicht eine blanket Zusage für alle Domains.
12. Sinnvoll als nächste Designprüfung: normierte Primarybasis und ankerfreie, inkrementelle Wertbildung in C; danach gezielte Kalibrierung an tatsächlichen Anlagen-/Lieferpfaden. Keine automatische produktive Änderung empfohlen.
13. Bei festen Preisen und deterministischen Zuständen bleiben Optima möglich. Gleiche Arbeitsrendite, gleiches Anfangskapital, seltene Freischaltungen, Flächen-/Freightkosten und Spielvielfalt können nicht ohne weitere Zielgewichtung gleichzeitig identisch sein.
14. Empfehlung: **{reco}** B ist eine Kontrollvariante, A die nötige Referenz. Kein Modell D als vermeintliche Fairnessgarantie hinzugefügt.

## 10. Reproduzierbarkeit und Grenzen

Aus Projektwurzel mit der vorhandenen venv und -B: scripts/phase11c_economy.py, scripts/phase11c_sensitivity.py, scripts/phase11c_genesis.py, scripts/phase11c_controlled.py und scripts/phase11c_transitions.py; danach scripts/phase11c_reports.py. Regression: scripts/phase11c_regression.py. Resultate ausschließlich artifacts/phase11c und die drei geforderten Dokumente. Unterstützender SciPy/NumPy-Runtime liegt ausschließlich im Auditordner; das ausgeführte Verfahren benötigt ihn nicht und verändert keine Spielabhängigkeit.

Die Entscheidungsvorlage trennt vollständige 353-Produktdaten, begrenzte mathematische Kapazitätssuche, statische Sensitivitäten und tatsächliche Engine-Stichproben. Keine globale optimale Mischfirma, keine optimale dynamische Reinvestitionspolitik für alle Produkte und keine lückenlose langfristige Fairnessgarantie bewiesen. Die Relaxationslücken machen diesen Umfang sichtbar. Die Ergebnisse liefern konkrete Schattenpreise und überprüfbare Gegenbeispiele, keine verbindliche finale Preisentscheidung.

Produktiver Bestandsschutz und sämtliche Tests siehe separater Factory-Bericht. Alle fünf persönlichen Saves und bestehenden Builds unverändert. Nach den Berichten keine weitere Phase, keine Preisübernahme und kein Windows-Build.
'''
write('industriova-03-phase11c-economy-model-analysis.md',text)
print('reports complete; protected files verified')
