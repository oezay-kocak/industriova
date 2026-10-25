# INDUSTRIOVA – vollständiger Wirtschafts- und Rezeptaudit P11-A

Stand: 23.10.2026. Ausschließlich Ist-Daten des aktuellen Working Tree; keine Spielstände geladen, keine Simulation, keine Preisänderung, kein Build. Geldwerte in Dollar, Mengen in Produkteinheiten; Dezimalpunkt bewahrt die internen Werte.

## 1. Executive Summary

Vollständig erfasst: **353 eindeutige Produkte und 353 kanonische Rezepte**, davon 49 Primary Production, 68 Processing, 86 Fabrication, 150 Assembly. Jede Ressource hat genau einen Hersteller im vorhandenen ProductionGuideRecipeIndex.

Die Primärpreise sind Katalogwerte. Folgeproduktpreise werden beim Import rezeptabhängig berechnet und bleiben im Spiel fest. „Fest“ bedeutet daher keine laufende Marktschwankung, aber ausdrücklich keine Unabhängigkeit von Rohstoffpreisen. Die einheitliche Maschinenleistung je Stufe gilt für Primary und Assembly; Processing und Fabrication haben rezeptabhängige Abweichungen.

## 2. Tatsächliche technische Preisarchitektur

Maßgeblich sind `src/production_zero/data/resource_definitions.json`, `game_definitions.json` und `resource_progression.json`; der Loader `data/definitions.py:load_card_definitions` teilt Primary in Extractor, Drilling Rig und Harvester und wendet `core/release_balance.py:balance_definitions` an. Alle Tabellen verwenden diese wirksamen Laufzeitdefinitionen, keine historischen Rohdatenannahmen.

`core/market.py` liest `base_market_price` als `LEGACY_BASE_MARKET_PRICES` und erzeugt mit `core/fixed_prices.py:build_fixed_prices` die tatsächlichen `BASE_MARKET_PRICES`. Für Primary bleibt der Katalogpreis erhalten. Für jedes Produkt mit Inputs wird in Abhängigkeitsreihenfolge gerechnet. Fehlende/zyklische Inputs führen dort zu ValueError.

Bestehende Formel, je Output-Einheit (q = Output/Zyklus, t = Sekunden, P = Rezept-MW, b = Kataloganker, p = bereits ermittelter Basispreis):

```text
I = Summe(p[input] * inputmenge) / q
E = P * t * b[coal] * 0.01 / q
K = (120 + Maschinenbasisoutput * 14 + Maschinenbasisleistung * 9) * t / (36000 * q)
T = b[produkt] * 0.02
p[produkt] = round(max(b[produkt] * 1.25, I * 1.15 + E + K + T), 4)
```

Das sind unverändert vorhandene Formeln, keine vorgeschlagene Neubewertung. Es gibt keinen separaten Aufschlag je Stufe: 15 % auf den direkten monetären Inputwert, eine Untergrenze von 125 % des jeweiligen Produkt-Katalogankers, Energie-, Kapital- und Transportterme. Die Zahl unterschiedlicher Inputs ist kein eigener Faktor; deren Mengen sind es. Rekursive Warenkosten wirken über die bereits abgeleiteten Inputpreise; es gibt in dieser Preisfunktion keine zusätzliche Rohstoff- oder Maschinenkettenoptimierung.

Der Kapitalterm verwendet eine ungerundete Kennzahl aus Maschinenbasiswerten, nicht den tatsächlich gezahlten Kartenpreis, MK-Investitionen oder den gerundeten Supply-Preis. Der Transportterm ist ein Ankeraufschlag, keine Berechnung tatsächlicher Frachtstrecken. Der Energieterm ist ein Kohlepreisäquivalent, keine individuelle Generatorrechnung.

`market_price_for` gibt direkt `BASE_MARKET_PRICES[rid]` zurück. Historische Volatilitäts-/Event-/MarketState-Felder sind kein schwankender Verkaufspreis. Der CSV enthält deshalb sowohl `base_sell_price` als auch den ausdrücklich getrennten `catalog_anchor_price`. Die Cent-Aufrundung der UI wird nirgends für die Originalpreise verwendet.

## 3. Vollständige Maschinen-/Stufenübersicht

| Maschinen-ID / Name | Produkte | Common-Kaufpreis | Basisoutput | Basiszyklus s | Basis-MW | wirksame Rezeptvarianten (Output; s; MW) |
|---|---:|---:|---:|---:|---:|---|
| machine.extractor / Extractor | 37 | 340.0 | 12.0 | 6.0 | 6.0 | 12.0; 6.0; 6.0 (37 Rezepte) |
| machine.processor / Processor | 68 | 275.0 | 6.0 | 6.0 | 8.0 | 1.0; 6.0; 5.0 (2 Rezepte); 1.0; 6.0; 12.0 (2 Rezepte); 2.0; 6.0; 5.0 (8 Rezepte); 2.0; 6.0; 6.0 (3 Rezepte); 2.0; 6.0; 7.0 (4 Rezepte); 2.0; 6.0; 8.0 (5 Rezepte); 2.0; 6.0; 9.0 (4 Rezepte); 2.0; 6.0; 10.0 (2 Rezepte); 2.0; 6.0; 12.0 (3 Rezepte); 2.0; 6.0; 15.0 (1 Rezepte); 3.0; 6.0; 5.0 (1 Rezepte); 3.0; 6.0; 6.0 (2 Rezepte); 3.0; 6.0; 7.0 (4 Rezepte); 3.0; 6.0; 8.0 (3 Rezepte); 3.0; 6.0; 9.0 (1 Rezepte); 3.0; 6.0; 10.0 (2 Rezepte); 3.0; 6.0; 11.0 (1 Rezepte); 3.0; 6.0; 12.0 (1 Rezepte); 3.0; 6.0; 13.0 (2 Rezepte); 4.0; 6.0; 10.0 (5 Rezepte); 4.0; 6.0; 11.0 (2 Rezepte); 4.0; 6.0; 12.0 (1 Rezepte); 5.0; 6.0; 8.0 (4 Rezepte); 5.0; 6.0; 9.0 (3 Rezepte); 6.0; 6.0; 8.0 (2 Rezepte) |
| machine.fabricator / Fabricator | 86 | 225.0 | 1.0 | 6.0 | 10.0 | 1.0; 6.0; 10.0 (63 Rezepte); 2.0; 6.0; 10.0 (22 Rezepte); 3.0; 6.0; 10.0 (1 Rezepte) |
| machine.assembler / Assembler | 150 | 240.0 | 1.0 | 6.0 | 12.0 | 1.0; 6.0; 12.0 (150 Rezepte) |
| machine.drilling / Drilling Rig | 2 | 340.0 | 12.0 | 6.0 | 6.0 | 12.0; 6.0; 6.0 (2 Rezepte) |
| machine.agriculture / Harvester | 10 | 340.0 | 12.0 | 6.0 | 6.0 | 12.0; 6.0; 6.0 (10 Rezepte) |

Alle 49 Primary-Rezepte: 12 Output/6 s, 6 MW, 120 U/min, Common-Maschinenpreis 340.0; keine Ausnahme. Assembly: alle 150 Rezepte 1/6 s, 12 MW, 10 U/min. Processing: 1–6 Output/6 s und 5–15 MW. Fabrication: 1–3 Output/6 s bei 10 MW. Die vollständigen konkreten Produkt-IDs und Werte stehen in Abschnitt 6; Abweichungen von den Maschinenbasiswerten werden dort ausdrücklich markiert.

MK/Rarity (`core/cards.py`, `core/mk_upgrades.py`): MK1–99; M = 1 + 0.25*(MK−1). Outputmultiplikator = M*(1+Outputbonus/100). Maschinenleistungsbedarf = M*(1+Outputbonus*0.5/100). Inputs skalieren im echten Simulationskern nur mit M; der Rarity-Outputbonus erhöht nicht die Rezeptinputs. Die Zykluszeit bleibt durch MK/Rarity unverändert; Research production_speed beschleunigt den Zyklusfortschritt. Common-Bonus 0 %, Uncommon 1–5 %, Rare 6–10 %, Epic 11–15 %, Legendary 16–20 % (Zehntelprozent-Schritte).

Common-Maschinenpreis (`core/supply.py:common_card_price`) = round((120 + Basisoutput*14 + Basis-MW*9)/5)*5. Uncommon-Angebote verwenden common_price*(2.4+bonus_percent*0.28), auf 5 gerundet. Tatsächlicher historischer Kaufpreis und MK-Investition liegen an der Instanz und sind keine Rezeptpreisparameter.

## 4. Exakte Produktanzahlen je Stufe

| Stufe | Anzahl |
|---|---:|
| Primary Production | 49 |
| Processing | 68 |
| Fabrication | 86 |
| Assembly | 150 |
| **Summe** | **353** |

Primary-Unterklassen: Extractor 37, Drilling Rig 2, Harvester 10. Die Normalisierung zu Primary Production im Audit verändert die ursprüngliche Maschinenklasse nicht.

## 5. Alle Primary-Rohstoffe mit Originalpreisen

| Rohstoff / ID | Maschine | Basispreis | Output/Zyklus | Sekunden | MW | U/min | Freischaltung |
|---|---|---:|---:|---:|---:|---:|---|
| bauxite (Bauxite) | machine.extractor | 1.1 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 1 |
| borate_ore (Borate Ore) | machine.extractor | 1.45 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 13 |
| chromium_ore (Chromium Ore) | machine.extractor | 1.65 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 11 |
| clay (Clay) | machine.extractor | 0.7 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 3 |
| coal (Coal) | machine.extractor | 1.2 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 1 |
| cobalt_ore (Cobalt Ore) | machine.extractor | 2.6 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 15 |
| copper_ore (Copper Ore) | machine.extractor | 1.4 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 1 |
| corn (Corn) | machine.agriculture | 0.9 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 2 |
| cotton (Cotton) | machine.agriculture | 1.2 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 4 |
| crude_oil (Crude Oil) | machine.drilling | 2.2 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 1 |
| fluorspar (Fluorspar) | machine.extractor | 1.5 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 13 |
| fruit (Fruit) | machine.agriculture | 1.1 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 4 |
| gold_ore (Gold Ore) | machine.extractor | 5.0 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 18 |
| graphite (Graphite) | machine.extractor | 1.75 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 13 |
| gypsum (Gypsum) | machine.extractor | 0.85 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 3 |
| iron_ore (Iron Ore) | machine.extractor | 1.0 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 1 |
| kaolin (Kaolin) | machine.extractor | 1.0 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 3 |
| lead_ore (Lead Ore) | machine.extractor | 1.15 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 9 |
| limestone (Limestone) | machine.extractor | 0.8 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 1 |
| lithium_ore (Lithium Ore) | machine.extractor | 2.3 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 15 |
| magnesite (Magnesite) | machine.extractor | 1.3 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 13 |
| manganese_ore (Manganese Ore) | machine.extractor | 1.35 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 9 |
| molybdenum_ore (Molybdenum Ore) | machine.extractor | 2.2 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 22 |
| natural_gas (Natural Gas) | machine.drilling | 1.9 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 5 |
| natural_rubber (Natural Rubber) | machine.agriculture | 1.7 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 5 |
| nickel_ore (Nickel Ore) | machine.extractor | 1.8 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 11 |
| niobium_ore (Niobium Ore) | machine.extractor | 2.5 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 22 |
| palladium_ore (Palladium Ore) | machine.extractor | 5.4 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 20 |
| phosphate_rock (Phosphate Rock) | machine.extractor | 1.25 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 7 |
| platinum_ore (Platinum Ore) | machine.extractor | 5.8 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 20 |
| potash (Potash) | machine.extractor | 1.35 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 7 |
| potatoes (Potatoes) | machine.agriculture | 0.8 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 2 |
| quartz (Quartz) | machine.extractor | 1.1 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 1 |
| rapeseed (Rapeseed) | machine.agriculture | 1.0 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 4 |
| rare_earth_ore (Rare Earth Ore) | machine.extractor | 2.7 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 15 |
| salt (Salt) | machine.extractor | 0.75 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 7 |
| silica_sand (Silica Sand) | machine.extractor | 0.9 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 3 |
| silver_ore (Silver Ore) | machine.extractor | 3.6 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 18 |
| soybeans (Soybeans) | machine.agriculture | 1.05 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 2 |
| sugarcane (Sugarcane) | machine.agriculture | 0.85 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 4 |
| sulfur (Sulfur) | machine.extractor | 1.15 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 7 |
| timber (Timber) | machine.agriculture | 1.1 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 1 |
| tin_ore (Tin Ore) | machine.extractor | 1.45 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 9 |
| titanium_ore (Titanium Ore) | machine.extractor | 2.4 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 22 |
| tungsten_ore (Tungsten Ore) | machine.extractor | 2.8 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 22 |
| uranium_ore (Uranium Ore) | machine.extractor | 3.2 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 25 |
| vanadium_ore (Vanadium Ore) | machine.extractor | 2.1 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 22 |
| wheat (Wheat) | machine.agriculture | 0.95 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 1 |
| zinc_ore (Zinc Ore) | machine.extractor | 1.25 | 12.0 | 6.0 | 6.0 | 120.0 | Company-Level >= 9 |

## 6. Vollständiger Katalog aller 353 Produkte

Alle Werte MK1/Common ohne Research und bei ununterbrochener Versorgung. U/min ist die vorhandene GuideRecipeEntry.output_per_minute-Rate, keine simulierte Lieferleistung. Für jedes Produkt gilt: marktfähig, tatsächlicher Verkauf per Market-Fracht; dies bedeutet keine sofortige Lagerverkaufsaktion. Unmittelbare Folgeprodukte stehen je Produkt vollständig darunter.

### Primary Production (49)

#### Bauxite — `bauxite`

Rezept `resource.bauxite`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × bauxite; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.1; Kataloganker: $1.1; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1.
Unmittelbare Folgeprodukte: aluminum (Aluminum).

#### Borate Ore — `borate_ore`

Rezept `resource.borate_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × borate_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.45; Kataloganker: $1.45; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13.
Unmittelbare Folgeprodukte: glass (Glass); shielding_material (Shielding Material).

#### Chromium Ore — `chromium_ore`

Rezept `resource.chromium_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × chromium_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.65; Kataloganker: $1.65; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 11.
Unmittelbare Folgeprodukte: chromium (Chromium); stainless_steel (Stainless Steel).

#### Clay — `clay`

Rezept `resource.clay`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × clay; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $0.7; Kataloganker: $0.7; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 3.
Unmittelbare Folgeprodukte: ceramics (Ceramics).

#### Coal — `coal`

Rezept `resource.coal`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × coal; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.2; Kataloganker: $1.2; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1.
Unmittelbare Folgeprodukte: nickel_alloy (Nickel Alloy); silicon (Silicon); stainless_steel (Stainless Steel); steel (Steel).

#### Cobalt Ore — `cobalt_ore`

Rezept `resource.cobalt_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × cobalt_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $2.6; Kataloganker: $2.6; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15.
Unmittelbare Folgeprodukte: cobalt (Cobalt).

#### Copper Ore — `copper_ore`

Rezept `resource.copper_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × copper_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.4; Kataloganker: $1.4; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1.
Unmittelbare Folgeprodukte: copper (Copper).

#### Corn — `corn`

Rezept `resource.corn`; Maschine `machine.agriculture` (Harvester); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × corn; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $0.9; Kataloganker: $0.9; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 2.
Unmittelbare Folgeprodukte: corn_meal (Corn Meal); fermentation_feedstock (Fermentation Feedstock); starch (Starch).

#### Cotton — `cotton`

Rezept `resource.cotton`; Maschine `machine.agriculture` (Harvester); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × cotton; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.2; Kataloganker: $1.2; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4.
Unmittelbare Folgeprodukte: cotton_fiber (Cotton Fiber).

#### Crude Oil — `crude_oil`

Rezept `resource.crude_oil`; Maschine `machine.drilling` (Drilling Rig); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × crude_oil; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $2.2; Kataloganker: $2.2; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1.
Unmittelbare Folgeprodukte: bitumen (Bitumen); carbon_fiber (Carbon Fiber); cellulose (Cellulose); chemical_feedstock (Chemical Feedstock); high_purity_silicon (High-Purity Silicon); industrial_resin (Industrial Resin); polymer (Polymer); synthetic_rubber (Synthetic Rubber); treated_lumber (Treated Lumber); wood_pulp (Wood Pulp).

#### Fluorspar — `fluorspar`

Rezept `resource.fluorspar`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × fluorspar; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.5; Kataloganker: $1.5; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13.
Unmittelbare Folgeprodukte: high_purity_silicon (High-Purity Silicon).

#### Fruit — `fruit`

Rezept `resource.fruit`; Maschine `machine.agriculture` (Harvester); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × fruit; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.1; Kataloganker: $1.1; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4.
Unmittelbare Folgeprodukte: fruit_concentrate (Fruit Concentrate); organic_feedstock (Organic Feedstock).

#### Gold Ore — `gold_ore`

Rezept `resource.gold_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × gold_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $5.0; Kataloganker: $5.0; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18.
Unmittelbare Folgeprodukte: gold (Gold).

#### Graphite — `graphite`

Rezept `resource.graphite`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × graphite; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.75; Kataloganker: $1.75; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13.
Unmittelbare Folgeprodukte: carbon_fiber (Carbon Fiber); purified_graphite (Purified Graphite).

#### Gypsum — `gypsum`

Rezept `resource.gypsum`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × gypsum; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $0.85; Kataloganker: $0.85; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 3.
Unmittelbare Folgeprodukte: cement (Cement); processed_gypsum (Processed Gypsum).

#### Iron Ore — `iron_ore`

Rezept `resource.iron_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × iron_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.0; Kataloganker: $1.0; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1.
Unmittelbare Folgeprodukte: galvanized_metal (Galvanized Metal); iron (Iron); nickel_alloy (Nickel Alloy); stainless_steel (Stainless Steel); steel (Steel); vanadium_alloy (Vanadium Alloy).

#### Kaolin — `kaolin`

Rezept `resource.kaolin`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × kaolin; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.0; Kataloganker: $1.0; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 3.
Unmittelbare Folgeprodukte: ceramics (Ceramics).

#### Lead Ore — `lead_ore`

Rezept `resource.lead_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × lead_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.15; Kataloganker: $1.15; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9.
Unmittelbare Folgeprodukte: lead (Lead); nuclear_material (Nuclear Material); shielding_material (Shielding Material).

#### Limestone — `limestone`

Rezept `resource.limestone`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × limestone; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $0.8; Kataloganker: $0.8; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1.
Unmittelbare Folgeprodukte: cement (Cement); glass (Glass).

#### Lithium Ore — `lithium_ore`

Rezept `resource.lithium_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × lithium_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $2.3; Kataloganker: $2.3; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15.
Unmittelbare Folgeprodukte: lithium (Lithium).

#### Magnesite — `magnesite`

Rezept `resource.magnesite`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × magnesite; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.3; Kataloganker: $1.3; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13.
Unmittelbare Folgeprodukte: ceramics (Ceramics).

#### Manganese Ore — `manganese_ore`

Rezept `resource.manganese_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × manganese_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.35; Kataloganker: $1.35; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9.
Unmittelbare Folgeprodukte: manganese (Manganese).

#### Molybdenum Ore — `molybdenum_ore`

Rezept `resource.molybdenum_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × molybdenum_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $2.2; Kataloganker: $2.2; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22.
Unmittelbare Folgeprodukte: molybdenum (Molybdenum); nickel_alloy (Nickel Alloy).

#### Natural Gas — `natural_gas`

Rezept `resource.natural_gas`; Maschine `machine.drilling` (Drilling Rig); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × natural_gas; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.9; Kataloganker: $1.9; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5.
Unmittelbare Folgeprodukte: ammonia (Ammonia); bio_lubricant (Bio-Lubricant); carbon_fiber (Carbon Fiber); cellulose (Cellulose); chemical_feedstock (Chemical Feedstock); high_purity_silicon (High-Purity Silicon); hydrogen (Hydrogen); industrial_gas (Industrial Gas); industrial_resin (Industrial Resin); phosphoric_acid (Phosphoric Acid); polymer (Polymer); sulfuric_acid (Sulfuric Acid); synthetic_rubber (Synthetic Rubber); treated_lumber (Treated Lumber); wood_pulp (Wood Pulp).

#### Natural Rubber — `natural_rubber`

Rezept `resource.natural_rubber`; Maschine `machine.agriculture` (Harvester); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × natural_rubber; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.7; Kataloganker: $1.7; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5.
Unmittelbare Folgeprodukte: processed_rubber (Processed Rubber).

#### Nickel Ore — `nickel_ore`

Rezept `resource.nickel_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × nickel_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.8; Kataloganker: $1.8; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 11.
Unmittelbare Folgeprodukte: nickel (Nickel); nickel_alloy (Nickel Alloy); stainless_steel (Stainless Steel).

#### Niobium Ore — `niobium_ore`

Rezept `resource.niobium_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × niobium_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $2.5; Kataloganker: $2.5; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22.
Unmittelbare Folgeprodukte: niobium (Niobium); superconducting_alloy (Superconducting Alloy).

#### Palladium Ore — `palladium_ore`

Rezept `resource.palladium_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × palladium_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $5.4; Kataloganker: $5.4; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 20.
Unmittelbare Folgeprodukte: catalyst_metal (Catalyst Metal); palladium (Palladium).

#### Phosphate Rock — `phosphate_rock`

Rezept `resource.phosphate_rock`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × phosphate_rock; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.25; Kataloganker: $1.25; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7.
Unmittelbare Folgeprodukte: phosphoric_acid (Phosphoric Acid).

#### Platinum Ore — `platinum_ore`

Rezept `resource.platinum_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × platinum_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $5.8; Kataloganker: $5.8; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 20.
Unmittelbare Folgeprodukte: catalyst_metal (Catalyst Metal); platinum (Platinum).

#### Potash — `potash`

Rezept `resource.potash`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × potash; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.35; Kataloganker: $1.35; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7.
Unmittelbare Folgeprodukte: potassium_compound (Potassium Compound).

#### Potatoes — `potatoes`

Rezept `resource.potatoes`; Maschine `machine.agriculture` (Harvester); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × potatoes; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $0.8; Kataloganker: $0.8; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 2.
Unmittelbare Folgeprodukte: organic_feedstock (Organic Feedstock); starch (Starch).

#### Quartz — `quartz`

Rezept `resource.quartz`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × quartz; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.1; Kataloganker: $1.1; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1.
Unmittelbare Folgeprodukte: high_purity_silicon (High-Purity Silicon); silicon (Silicon).

#### Rapeseed — `rapeseed`

Rezept `resource.rapeseed`; Maschine `machine.agriculture` (Harvester); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × rapeseed; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.0; Kataloganker: $1.0; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4.
Unmittelbare Folgeprodukte: bio_lubricant (Bio-Lubricant); vegetable_oil (Vegetable Oil).

#### Rare Earth Ore — `rare_earth_ore`

Rezept `resource.rare_earth_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × rare_earth_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $2.7; Kataloganker: $2.7; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15.
Unmittelbare Folgeprodukte: rare_earth_metals (Rare Earth Metals); superconducting_alloy (Superconducting Alloy).

#### Salt — `salt`

Rezept `resource.salt`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × salt; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $0.75; Kataloganker: $0.75; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7.
Unmittelbare Folgeprodukte: chlorine (Chlorine).

#### Silica Sand — `silica_sand`

Rezept `resource.silica_sand`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × silica_sand; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $0.9; Kataloganker: $0.9; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 3.
Unmittelbare Folgeprodukte: glass (Glass).

#### Silver Ore — `silver_ore`

Rezept `resource.silver_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × silver_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $3.6; Kataloganker: $3.6; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18.
Unmittelbare Folgeprodukte: silver (Silver).

#### Soybeans — `soybeans`

Rezept `resource.soybeans`; Maschine `machine.agriculture` (Harvester); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × soybeans; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.05; Kataloganker: $1.05; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 2.
Unmittelbare Folgeprodukte: soy_oil (Soy Oil); soy_protein (Soy Protein); vegetable_oil (Vegetable Oil).

#### Sugarcane — `sugarcane`

Rezept `resource.sugarcane`; Maschine `machine.agriculture` (Harvester); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × sugarcane; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $0.85; Kataloganker: $0.85; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4.
Unmittelbare Folgeprodukte: fermentation_feedstock (Fermentation Feedstock); fruit_concentrate (Fruit Concentrate); raw_sugar (Raw Sugar); refined_sugar (Refined Sugar).

#### Sulfur — `sulfur`

Rezept `resource.sulfur`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × sulfur; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.15; Kataloganker: $1.15; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7.
Unmittelbare Folgeprodukte: phosphoric_acid (Phosphoric Acid); processed_rubber (Processed Rubber); sulfuric_acid (Sulfuric Acid); synthetic_rubber (Synthetic Rubber).

#### Timber — `timber`

Rezept `resource.timber`; Maschine `machine.agriculture` (Harvester); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × timber; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.1; Kataloganker: $1.1; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1.
Unmittelbare Folgeprodukte: cellulose (Cellulose); lumber (Lumber); treated_lumber (Treated Lumber); wood_pulp (Wood Pulp).

#### Tin Ore — `tin_ore`

Rezept `resource.tin_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × tin_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.45; Kataloganker: $1.45; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9.
Unmittelbare Folgeprodukte: tin (Tin).

#### Titanium Ore — `titanium_ore`

Rezept `resource.titanium_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × titanium_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $2.4; Kataloganker: $2.4; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22.
Unmittelbare Folgeprodukte: superconducting_alloy (Superconducting Alloy); titanium (Titanium).

#### Tungsten Ore — `tungsten_ore`

Rezept `resource.tungsten_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × tungsten_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $2.8; Kataloganker: $2.8; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22.
Unmittelbare Folgeprodukte: tungsten (Tungsten).

#### Uranium Ore — `uranium_ore`

Rezept `resource.uranium_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × uranium_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $3.2; Kataloganker: $3.2; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 25.
Unmittelbare Folgeprodukte: nuclear_material (Nuclear Material).

#### Vanadium Ore — `vanadium_ore`

Rezept `resource.vanadium_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × vanadium_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $2.1; Kataloganker: $2.1; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22.
Unmittelbare Folgeprodukte: vanadium (Vanadium); vanadium_alloy (Vanadium Alloy).

#### Wheat — `wheat`

Rezept `resource.wheat`; Maschine `machine.agriculture` (Harvester); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × wheat; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $0.95; Kataloganker: $0.95; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1.
Unmittelbare Folgeprodukte: flour (Flour); organic_feedstock (Organic Feedstock).

#### Zinc Ore — `zinc_ore`

Rezept `resource.zinc_ore`; Maschine `machine.extractor` (Extractor); Common-Kaufpreis $340.0.
Inputs/Zyklus: keine. Unterschiedliche Inputs: 0; gesamte Inputmenge: 0.
Output: 12.0 × zinc_ore; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 120.0 U/min.
Basisverkaufspreis: $1.25; Kataloganker: $1.25; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9.
Unmittelbare Folgeprodukte: galvanized_metal (Galvanized Metal); zinc (Zinc).

### Processing (68)

#### Aluminum — `aluminum`

Rezept `recipe.processor.aluminum`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 9 x bauxite (Bauxite). Unterschiedliche Inputs: 1; gesamte Inputmenge: 9.
Output: 5.0 × aluminum; Zyklus: 6.0 s; Leistung: 9.0 MW; MK1/Common: 50.0 U/min.
Basisverkaufspreis: $3.1875; Kataloganker: $2.55; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1; bauxite (Bauxite): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: advanced_cell_components (Advanced Cell Components); aerospace_components (Aerospace Components); aluminum_components (Aluminum Components); avionics_components (Avionics Components); battery_components (Battery Components); compressor_components (Compressor Components); electrolyzer_components (Electrolyzer Components); glass_panels (Glass Panels); network_components (Network Components); power_electronics (Power Electronics); precision_components (Precision Components); solar_components (Solar Components); storage_components (Storage Components); vehicle_components (Vehicle Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Ammonia — `ammonia`

Rezept `recipe.processor.ammonia`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 3 x natural_gas (Natural Gas). Unterschiedliche Inputs: 1; gesamte Inputmenge: 3.
Output: 2.0 × ammonia; Zyklus: 6.0 s; Leistung: 8.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $4.0625; Kataloganker: $3.25; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; natural_gas (Natural Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: fertilizer_components (Fertilizer Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Bio-Lubricant — `bio_lubricant`

Rezept `recipe.processor.bio_lubricant`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x rapeseed (Rapeseed); 1 x natural_gas (Natural Gas). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 2.0 × bio_lubricant; Zyklus: 6.0 s; Leistung: 7.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $2.875; Kataloganker: $2.3; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; rapeseed (Rapeseed): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; natural_gas (Natural Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: bio_material_components (Bio-Material Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Bitumen — `bitumen`

Rezept `recipe.processor.bitumen`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 3 x crude_oil (Crude Oil). Unterschiedliche Inputs: 1; gesamte Inputmenge: 3.
Output: 2.0 × bitumen; Zyklus: 6.0 s; Leistung: 8.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $4.7; Kataloganker: $3.76; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1; crude_oil (Crude Oil): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: asphalt_components (Asphalt Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Carbon Fiber — `carbon_fiber`

Rezept `recipe.processor.carbon_fiber`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 3 x crude_oil (Crude Oil); 1 x natural_gas (Natural Gas); 1 x graphite (Graphite). Unterschiedliche Inputs: 3; gesamte Inputmenge: 5.
Output: 1.0 × carbon_fiber; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $16.1; Kataloganker: $12.88; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; crude_oil (Crude Oil): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; natural_gas (Natural Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; graphite (Graphite): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: aerospace_components (Aerospace Components); composite_components (Composite Components); tire_components (Tire Components); wind_components (Wind Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Catalyst Metal — `catalyst_metal`

Rezept `recipe.processor.catalyst_metal`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 3 x palladium_ore (Palladium Ore); 1 x platinum_ore (Platinum Ore). Unterschiedliche Inputs: 2; gesamte Inputmenge: 4.
Output: 2.0 × catalyst_metal; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $16.0125; Kataloganker: $12.81; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 20; palladium_ore (Palladium Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; platinum_ore (Platinum Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: catalyst_components (Catalyst Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Cellulose — `cellulose`

Rezept `recipe.processor.cellulose`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x timber (Timber); 1 x crude_oil (Crude Oil); 1 x natural_gas (Natural Gas). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 2.0 × cellulose; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $3.9091; Kataloganker: $2.38; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; timber (Timber): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; crude_oil (Crude Oil): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; natural_gas (Natural Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: bio_composite (Bio-Composite); bio_material_components (Bio-Material Components); fiber_components (Fiber Components); membrane_components (Membrane Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Cement — `cement`

Rezept `recipe.processor.cement`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 4 x limestone (Limestone); 1 x gypsum (Gypsum). Unterschiedliche Inputs: 2; gesamte Inputmenge: 5.
Output: 3.0 × cement; Zyklus: 6.0 s; Leistung: 7.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $2.125; Kataloganker: $1.7; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 3; limestone (Limestone): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; gypsum (Gypsum): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: asphalt_components (Asphalt Components); concrete_components (Concrete Components); structural_components (Structural Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Ceramics — `ceramics`

Rezept `recipe.processor.ceramics`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 3 x clay (Clay); 1 x kaolin (Kaolin); 1 x magnesite (Magnesite). Unterschiedliche Inputs: 3; gesamte Inputmenge: 5.
Output: 3.0 × ceramics; Zyklus: 6.0 s; Leistung: 7.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $2.275; Kataloganker: $1.82; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; clay (Clay): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; kaolin (Kaolin): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; magnesite (Magnesite): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: ceramic_components (Ceramic Components); filtration_components (Filtration Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Chemical Feedstock — `chemical_feedstock`

Rezept `recipe.processor.chemical_feedstock`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x crude_oil (Crude Oil); 2 x natural_gas (Natural Gas). Unterschiedliche Inputs: 2; gesamte Inputmenge: 4.
Output: 3.0 × chemical_feedstock; Zyklus: 6.0 s; Leistung: 8.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $3.975; Kataloganker: $3.18; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; crude_oil (Crude Oil): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; natural_gas (Natural Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: agricultural_chemicals (Agricultural Chemicals); biodiesel_feedstock (Biodiesel Feedstock); chemical_components (Chemical Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Chlorine — `chlorine`

Rezept `recipe.processor.chlorine`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 3 x salt (Salt). Unterschiedliche Inputs: 1; gesamte Inputmenge: 3.
Output: 2.0 × chlorine; Zyklus: 6.0 s; Leistung: 8.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $1.85; Kataloganker: $1.48; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; salt (Salt): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: agricultural_chemicals (Agricultural Chemicals); membrane_components (Membrane Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Chromium — `chromium`

Rezept `recipe.processor.chromium`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 9 x chromium_ore (Chromium Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 9.
Output: 5.0 × chromium; Zyklus: 6.0 s; Leistung: 9.0 MW; MK1/Common: 50.0 U/min.
Basisverkaufspreis: $4.7; Kataloganker: $3.76; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 11; chromium_ore (Chromium Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: bearing_components (Bearing Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Cobalt — `cobalt`

Rezept `recipe.processor.cobalt`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 8 x cobalt_ore (Cobalt Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 8.
Output: 4.0 × cobalt; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 40.0 U/min.
Basisverkaufspreis: $7.4125; Kataloganker: $5.93; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15; cobalt_ore (Cobalt Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: advanced_cell_components (Advanced Cell Components); battery_components (Battery Components); battery_materials (Battery Materials).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Copper — `copper`

Rezept `recipe.processor.copper`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 12 x copper_ore (Copper Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 12.
Output: 6.0 × copper; Zyklus: 6.0 s; Leistung: 8.0 MW; MK1/Common: 60.0 U/min.
Basisverkaufspreis: $4.375; Kataloganker: $3.5; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1; copper_ore (Copper Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: autonomous_components (Autonomous Components); avionics_components (Avionics Components); computing_components (Computing Components); control_electronics (Control Electronics); copper_wire (Copper Wire); electrical_components (Electrical Components); electrolyzer_components (Electrolyzer Components); insulated_wire (Insulated Wire); memory_components (Memory Components); motor_components (Motor Components); network_components (Network Components); power_electronics (Power Electronics); processor_components (Processor Components); pump_components (Pump Components); semiconductor_components (Semiconductor Components); semiconductor_die (Semiconductor Die); sensor_components (Sensor Components); server_components (Server Components); storage_components (Storage Components); telecom_components (Telecom Components); transformer_components (Transformer Components).

#### Corn Meal — `corn_meal`

Rezept `recipe.processor.corn_meal`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x corn (Corn). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 2.0 × corn_meal; Zyklus: 6.0 s; Leistung: 5.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $1.5625; Kataloganker: $1.25; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 2; corn (Corn): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: food_ingredients (Food Ingredients).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Cotton Fiber — `cotton_fiber`

Rezept `recipe.processor.cotton_fiber`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x cotton (Cotton). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 2.0 × cotton_fiber; Zyklus: 6.0 s; Leistung: 5.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $1.9375; Kataloganker: $1.55; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4; cotton (Cotton): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: industrial_fabric (Industrial Fabric); technical_textile (Technical Textile).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Fermentation Feedstock — `fermentation_feedstock`

Rezept `recipe.processor.fermentation_feedstock`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x corn (Corn); 1 x sugarcane (Sugarcane). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 2.0 × fermentation_feedstock; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $2.0875; Kataloganker: $1.67; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4; corn (Corn): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; sugarcane (Sugarcane): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: biopolymer (Biopolymer); ethanol_components (Ethanol Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Flour — `flour`

Rezept `recipe.processor.flour`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x wheat (Wheat). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 2.0 × flour; Zyklus: 6.0 s; Leistung: 5.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $1.625; Kataloganker: $1.3; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1; wheat (Wheat): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: food_ingredients (Food Ingredients).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Fruit Concentrate — `fruit_concentrate`

Rezept `recipe.processor.fruit_concentrate`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 3 x fruit (Fruit); 1 x sugarcane (Sugarcane). Unterschiedliche Inputs: 2; gesamte Inputmenge: 4.
Output: 2.0 × fruit_concentrate; Zyklus: 6.0 s; Leistung: 5.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $3.0375; Kataloganker: $2.43; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4; fruit (Fruit): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; sugarcane (Sugarcane): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: nutrition_components (Nutrition Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Galvanized Metal — `galvanized_metal`

Rezept `recipe.processor.galvanized_metal`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 4 x zinc_ore (Zinc Ore); 4 x iron_ore (Iron Ore). Unterschiedliche Inputs: 2; gesamte Inputmenge: 8.
Output: 3.0 × galvanized_metal; Zyklus: 6.0 s; Leistung: 8.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $4.3625; Kataloganker: $3.49; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9; zinc_ore (Zinc Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; iron_ore (Iron Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: corrosion_resistant_components (Corrosion Resistant Components); galvanized_components (Galvanized Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Glass — `glass`

Rezept `recipe.processor.glass`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 4 x silica_sand (Silica Sand); 1 x limestone (Limestone); 1 x borate_ore (Borate Ore). Unterschiedliche Inputs: 3; gesamte Inputmenge: 6.
Output: 3.0 × glass; Zyklus: 6.0 s; Leistung: 7.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $2.9; Kataloganker: $2.32; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; silica_sand (Silica Sand): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; limestone (Limestone): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; borate_ore (Borate Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: display_components (Display Components); glass_panels (Glass Panels); medical_components (Medical Components); silicon_substrate (Silicon Substrate); solar_components (Solar Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Gold — `gold`

Rezept `recipe.processor.gold`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 6 x gold_ore (Gold Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 6.
Output: 3.0 × gold; Zyklus: 6.0 s; Leistung: 11.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $14.25; Kataloganker: $11.4; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; gold_ore (Gold Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: ai_compute_components (AI Compute Components); avionics_components (Avionics Components); computing_components (Computing Components); control_electronics (Control Electronics); electrolyzer_components (Electrolyzer Components); memory_components (Memory Components); network_components (Network Components); power_electronics (Power Electronics); processor_components (Processor Components); semiconductor_components (Semiconductor Components); semiconductor_die (Semiconductor Die); sensor_components (Sensor Components); server_components (Server Components); storage_components (Storage Components); telecom_components (Telecom Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### High-Purity Silicon — `high_purity_silicon`

Rezept `recipe.processor.high_purity_silicon`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 4 x quartz (Quartz); 1 x fluorspar (Fluorspar); 1 x crude_oil (Crude Oil); 1 x natural_gas (Natural Gas). Unterschiedliche Inputs: 4; gesamte Inputmenge: 7.
Output: 1.0 × high_purity_silicon; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $13.1375; Kataloganker: $10.51; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; quartz (Quartz): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; fluorspar (Fluorspar): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; crude_oil (Crude Oil): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; natural_gas (Natural Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: ai_compute_components (AI Compute Components); autonomous_components (Autonomous Components); avionics_components (Avionics Components); computing_components (Computing Components); control_electronics (Control Electronics); display_components (Display Components); electrolyzer_components (Electrolyzer Components); memory_components (Memory Components); network_components (Network Components); power_electronics (Power Electronics); processor_components (Processor Components); semiconductor_components (Semiconductor Components); semiconductor_die (Semiconductor Die); sensor_components (Sensor Components); server_components (Server Components); solar_components (Solar Components); storage_components (Storage Components); telecom_components (Telecom Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Hydrogen — `hydrogen`

Rezept `recipe.processor.hydrogen`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 3 x natural_gas (Natural Gas). Unterschiedliche Inputs: 1; gesamte Inputmenge: 3.
Output: 2.0 × hydrogen; Zyklus: 6.0 s; Leistung: 9.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $4.0625; Kataloganker: $3.25; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; natural_gas (Natural Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: gas_handling_components (Gas Handling Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Industrial Gas — `industrial_gas`

Rezept `recipe.processor.industrial_gas`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x natural_gas (Natural Gas). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 2.0 × industrial_gas; Zyklus: 6.0 s; Leistung: 7.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $2.8125; Kataloganker: $2.25; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; natural_gas (Natural Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: gas_handling_components (Gas Handling Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Industrial Resin — `industrial_resin`

Rezept `recipe.processor.industrial_resin`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x crude_oil (Crude Oil); 1 x natural_gas (Natural Gas). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 2.0 × industrial_resin; Zyklus: 6.0 s; Leistung: 9.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $5.2; Kataloganker: $4.16; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; crude_oil (Crude Oil): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; natural_gas (Natural Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: bio_composite (Bio-Composite); composite_components (Composite Components); fiber_components (Fiber Components); hydraulic_components (Hydraulic Components); marine_components (Marine Components); wind_components (Wind Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Iron — `iron`

Rezept `recipe.processor.iron`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 12 x iron_ore (Iron Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 12.
Output: 6.0 × iron; Zyklus: 6.0 s; Leistung: 8.0 MW; MK1/Common: 60.0 U/min.
Basisverkaufspreis: $3.75; Kataloganker: $3.0; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1; iron_ore (Iron Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: iron_components (Iron Components); magnetic_components (Magnetic Components); motor_components (Motor Components).

#### Lead — `lead`

Rezept `recipe.processor.lead`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 9 x lead_ore (Lead Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 9.
Output: 5.0 × lead; Zyklus: 6.0 s; Leistung: 8.0 MW; MK1/Common: 50.0 U/min.
Basisverkaufspreis: $3.3125; Kataloganker: $2.65; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9; lead_ore (Lead Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: shielding_components (Shielding Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Lithium — `lithium`

Rezept `recipe.processor.lithium`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 8 x lithium_ore (Lithium Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 8.
Output: 4.0 × lithium; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 40.0 U/min.
Basisverkaufspreis: $6.55; Kataloganker: $5.24; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15; lithium_ore (Lithium Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: advanced_cell_components (Advanced Cell Components); battery_components (Battery Components); battery_materials (Battery Materials); grid_storage_components (Grid Storage Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Lumber — `lumber`

Rezept `recipe.processor.lumber`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 3 x timber (Timber). Unterschiedliche Inputs: 1; gesamte Inputmenge: 3.
Output: 3.0 × lumber; Zyklus: 6.0 s; Leistung: 5.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $1.8125; Kataloganker: $1.45; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1; timber (Timber): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: wooden_components (Wooden Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Manganese — `manganese`

Rezept `recipe.processor.manganese`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 9 x manganese_ore (Manganese Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 9.
Output: 5.0 × manganese; Zyklus: 6.0 s; Leistung: 8.0 MW; MK1/Common: 50.0 U/min.
Basisverkaufspreis: $3.85; Kataloganker: $3.08; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9; manganese_ore (Manganese Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: gear_components (Gear Components); rail_components (Rail Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Molybdenum — `molybdenum`

Rezept `recipe.processor.molybdenum`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 8 x molybdenum_ore (Molybdenum Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 8.
Output: 4.0 × molybdenum; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 40.0 U/min.
Basisverkaufspreis: $6.275; Kataloganker: $5.02; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; molybdenum_ore (Molybdenum Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: refractory_alloy_components (Refractory Alloy Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Nickel — `nickel`

Rezept `recipe.processor.nickel`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 9 x nickel_ore (Nickel Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 9.
Output: 5.0 × nickel; Zyklus: 6.0 s; Leistung: 9.0 MW; MK1/Common: 50.0 U/min.
Basisverkaufspreis: $5.125; Kataloganker: $4.1; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 11; nickel_ore (Nickel Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: battery_components (Battery Components); battery_materials (Battery Materials).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Nickel Alloy — `nickel_alloy`

Rezept `recipe.processor.nickel_alloy`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 6 x nickel_ore (Nickel Ore); 6 x iron_ore (Iron Ore); 1 x coal (Coal); 2 x molybdenum_ore (Molybdenum Ore). Unterschiedliche Inputs: 4; gesamte Inputmenge: 15.
Output: 3.0 × nickel_alloy; Zyklus: 6.0 s; Leistung: 13.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $11.6375; Kataloganker: $9.31; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; nickel_ore (Nickel Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; iron_ore (Iron Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; coal (Coal): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; molybdenum_ore (Molybdenum Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: turbine_components (Turbine Components); wind_components (Wind Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Niobium — `niobium`

Rezept `recipe.processor.niobium`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 8 x niobium_ore (Niobium Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 8.
Output: 4.0 × niobium; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 40.0 U/min.
Basisverkaufspreis: $7.125; Kataloganker: $5.7; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; niobium_ore (Niobium Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: refractory_alloy_components (Refractory Alloy Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Nuclear Material — `nuclear_material`

Rezept `recipe.processor.nuclear_material`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 3 x uranium_ore (Uranium Ore); 1 x lead_ore (Lead Ore). Unterschiedliche Inputs: 2; gesamte Inputmenge: 4.
Output: 2.0 × nuclear_material; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $7.825; Kataloganker: $6.26; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 25; uranium_ore (Uranium Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; lead_ore (Lead Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: nuclear_fuel_components (Nuclear Fuel Components); reactor_components (Reactor Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Organic Feedstock — `organic_feedstock`

Rezept `recipe.processor.organic_feedstock`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 1 x wheat (Wheat); 1 x fruit (Fruit); 1 x potatoes (Potatoes). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 2.0 × organic_feedstock; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $2.2125; Kataloganker: $1.77; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4; wheat (Wheat): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; fruit (Fruit): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; potatoes (Potatoes): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: sweetener_components (Sweetener Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Palladium — `palladium`

Rezept `recipe.processor.palladium`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 4 x palladium_ore (Palladium Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 4.
Output: 2.0 × palladium; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $19.2375; Kataloganker: $15.39; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 20; palladium_ore (Palladium Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: catalyst_components (Catalyst Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Phosphoric Acid — `phosphoric_acid`

Rezept `recipe.processor.phosphoric_acid`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x phosphate_rock (Phosphate Rock); 1 x sulfur (Sulfur); 1 x natural_gas (Natural Gas). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 2.0 × phosphoric_acid; Zyklus: 6.0 s; Leistung: 8.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $3.557; Kataloganker: $2.74; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; phosphate_rock (Phosphate Rock): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; sulfur (Sulfur): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; natural_gas (Natural Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: agricultural_mineral_components (Agricultural Mineral Components); fertilizer_components (Fertilizer Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Platinum — `platinum`

Rezept `recipe.processor.platinum`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 4 x platinum_ore (Platinum Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 4.
Output: 2.0 × platinum; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $20.6625; Kataloganker: $16.53; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 20; platinum_ore (Platinum Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: medical_components (Medical Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Polymer — `polymer`

Rezept `recipe.processor.polymer`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 3 x crude_oil (Crude Oil); 1 x natural_gas (Natural Gas). Unterschiedliche Inputs: 2; gesamte Inputmenge: 4.
Output: 2.0 × polymer; Zyklus: 6.0 s; Leistung: 9.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $6.1875; Kataloganker: $4.95; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; crude_oil (Crude Oil): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; natural_gas (Natural Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: display_components (Display Components); electrical_components (Electrical Components); filtration_components (Filtration Components); industrial_fabric (Industrial Fabric); insulated_wire (Insulated Wire); insulation_material (Insulation Material); membrane_components (Membrane Components); packaging_components (Packaging Components); technical_textile (Technical Textile).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Potassium Compound — `potassium_compound`

Rezept `recipe.processor.potassium_compound`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 3 x potash (Potash). Unterschiedliche Inputs: 1; gesamte Inputmenge: 3.
Output: 2.0 × potassium_compound; Zyklus: 6.0 s; Leistung: 7.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $2.975; Kataloganker: $2.38; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; potash (Potash): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: agricultural_mineral_components (Agricultural Mineral Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Processed Gypsum — `processed_gypsum`

Rezept `recipe.processor.processed_gypsum`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 3 x gypsum (Gypsum). Unterschiedliche Inputs: 1; gesamte Inputmenge: 3.
Output: 3.0 × processed_gypsum; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $1.5; Kataloganker: $1.2; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 3; gypsum (Gypsum): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: filtration_components (Filtration Components); insulation_material (Insulation Material).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Processed Rubber — `processed_rubber`

Rezept `recipe.processor.processed_rubber`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x natural_rubber (Natural Rubber); 1 x sulfur (Sulfur). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 2.0 × processed_rubber; Zyklus: 6.0 s; Leistung: 7.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $3.3125; Kataloganker: $2.65; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; natural_rubber (Natural Rubber): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; sulfur (Sulfur): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: industrial_fabric (Industrial Fabric); rubber_blend_components (Rubber Blend Components); tire_components (Tire Components); vehicle_components (Vehicle Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Purified Graphite — `purified_graphite`

Rezept `recipe.processor.purified_graphite`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 4 x graphite (Graphite). Unterschiedliche Inputs: 1; gesamte Inputmenge: 4.
Output: 3.0 × purified_graphite; Zyklus: 6.0 s; Leistung: 9.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $3.35; Kataloganker: $2.68; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; graphite (Graphite): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: advanced_cell_components (Advanced Cell Components); grid_storage_components (Grid Storage Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Rare Earth Metals — `rare_earth_metals`

Rezept `recipe.processor.rare_earth_metals`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 8 x rare_earth_ore (Rare Earth Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 8.
Output: 3.0 × rare_earth_metals; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $10.2625; Kataloganker: $8.21; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15; rare_earth_ore (Rare Earth Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: ai_compute_components (AI Compute Components); autonomous_components (Autonomous Components); magnetic_components (Magnetic Components); motor_components (Motor Components); processor_components (Processor Components); sensor_components (Sensor Components); telecom_components (Telecom Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Raw Sugar — `raw_sugar`

Rezept `recipe.processor.raw_sugar`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x sugarcane (Sugarcane). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 2.0 × raw_sugar; Zyklus: 6.0 s; Leistung: 5.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $1.5; Kataloganker: $1.2; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4; sugarcane (Sugarcane): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: sweetener_components (Sweetener Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Refined Sugar — `refined_sugar`

Rezept `recipe.processor.refined_sugar`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x sugarcane (Sugarcane). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 2.0 × refined_sugar; Zyklus: 6.0 s; Leistung: 5.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $1.5; Kataloganker: $1.2; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4; sugarcane (Sugarcane): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: food_ingredients (Food Ingredients).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Shielding Material — `shielding_material`

Rezept `recipe.processor.shielding_material`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 4 x lead_ore (Lead Ore); 1 x borate_ore (Borate Ore). Unterschiedliche Inputs: 2; gesamte Inputmenge: 5.
Output: 3.0 × shielding_material; Zyklus: 6.0 s; Leistung: 8.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $2.9625; Kataloganker: $2.37; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; lead_ore (Lead Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; borate_ore (Borate Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: nuclear_fuel_components (Nuclear Fuel Components); shielding_components (Shielding Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Silicon — `silicon`

Rezept `recipe.processor.silicon`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 4 x quartz (Quartz); 1 x coal (Coal). Unterschiedliche Inputs: 2; gesamte Inputmenge: 5.
Output: 2.0 × silicon; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $4.075; Kataloganker: $3.26; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1; quartz (Quartz): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; coal (Coal): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: silicon_substrate (Silicon Substrate).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Silver — `silver`

Rezept `recipe.processor.silver`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 6 x silver_ore (Silver Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 6.
Output: 3.0 × silver; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $10.2625; Kataloganker: $8.21; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; silver_ore (Silver Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: computing_components (Computing Components); control_electronics (Control Electronics); memory_components (Memory Components); semiconductor_die (Semiconductor Die).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Soy Oil — `soy_oil`

Rezept `recipe.processor.soy_oil`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x soybeans (Soybeans). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 1.0 × soy_oil; Zyklus: 6.0 s; Leistung: 5.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $3.0625; Kataloganker: $2.45; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 2; soybeans (Soybeans): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: sweetener_components (Sweetener Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Soy Protein — `soy_protein`

Rezept `recipe.processor.soy_protein`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x soybeans (Soybeans). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 1.0 × soy_protein; Zyklus: 6.0 s; Leistung: 5.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $3.0625; Kataloganker: $2.45; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 2; soybeans (Soybeans): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: nutrition_components (Nutrition Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Stainless Steel — `stainless_steel`

Rezept `recipe.processor.stainless_steel`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 12 x iron_ore (Iron Ore); 3 x coal (Coal); 2 x chromium_ore (Chromium Ore); 2 x nickel_ore (Nickel Ore). Unterschiedliche Inputs: 4; gesamte Inputmenge: 19.
Output: 3.0 × stainless_steel; Zyklus: 6.0 s; Leistung: 13.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $11.3875; Kataloganker: $9.11; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 11; iron_ore (Iron Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; coal (Coal): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; chromium_ore (Chromium Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; nickel_ore (Nickel Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: corrosion_resistant_components (Corrosion Resistant Components); medical_components (Medical Components); stainless_components (Stainless Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Starch — `starch`

Rezept `recipe.processor.starch`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x corn (Corn); 1 x potatoes (Potatoes). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 2.0 × starch; Zyklus: 6.0 s; Leistung: 5.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $2.0625; Kataloganker: $1.65; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 2; corn (Corn): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; potatoes (Potatoes): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: biopolymer (Biopolymer).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Steel — `steel`

Rezept `recipe.processor.steel`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 12 x iron_ore (Iron Ore); 3 x coal (Coal). Unterschiedliche Inputs: 2; gesamte Inputmenge: 15.
Output: 4.0 × steel; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 40.0 U/min.
Basisverkaufspreis: $10.0; Kataloganker: $8.0; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1; iron_ore (Iron Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; coal (Coal): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: bearing_components (Bearing Components); compressor_components (Compressor Components); concrete_components (Concrete Components); cutting_tooling (Cutting Tooling); gear_components (Gear Components); hydraulic_components (Hydraulic Components); marine_components (Marine Components); mining_components (Mining Components); precision_components (Precision Components); pump_components (Pump Components); rail_components (Rail Components); steel_components (Steel Components); structural_components (Structural Components); transformer_components (Transformer Components); vehicle_components (Vehicle Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Sulfuric Acid — `sulfuric_acid`

Rezept `recipe.processor.sulfuric_acid`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x sulfur (Sulfur); 1 x natural_gas (Natural Gas). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 2.0 × sulfuric_acid; Zyklus: 6.0 s; Leistung: 8.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $3.0625; Kataloganker: $2.45; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; sulfur (Sulfur): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; natural_gas (Natural Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: agricultural_chemicals (Agricultural Chemicals); chemical_components (Chemical Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Superconducting Alloy — `superconducting_alloy`

Rezept `recipe.processor.superconducting_alloy`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 4 x niobium_ore (Niobium Ore); 2 x titanium_ore (Titanium Ore); 3 x rare_earth_ore (Rare Earth Ore). Unterschiedliche Inputs: 3; gesamte Inputmenge: 9.
Output: 2.0 × superconducting_alloy; Zyklus: 6.0 s; Leistung: 15.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $16.375; Kataloganker: $13.1; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; niobium_ore (Niobium Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; titanium_ore (Titanium Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; rare_earth_ore (Rare Earth Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: refractory_alloy_components (Refractory Alloy Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Synthetic Rubber — `synthetic_rubber`

Rezept `recipe.processor.synthetic_rubber`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x crude_oil (Crude Oil); 1 x natural_gas (Natural Gas); 1 x sulfur (Sulfur). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 2.0 × synthetic_rubber; Zyklus: 6.0 s; Leistung: 9.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $5.5375; Kataloganker: $4.43; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; crude_oil (Crude Oil): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; natural_gas (Natural Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; sulfur (Sulfur): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: rubber_blend_components (Rubber Blend Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Tin — `tin`

Rezept `recipe.processor.tin`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 9 x tin_ore (Tin Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 9.
Output: 5.0 × tin; Zyklus: 6.0 s; Leistung: 8.0 MW; MK1/Common: 50.0 U/min.
Basisverkaufspreis: $4.1375; Kataloganker: $3.31; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9; tin_ore (Tin Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: electrical_components (Electrical Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Titanium — `titanium`

Rezept `recipe.processor.titanium`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 8 x titanium_ore (Titanium Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 8.
Output: 4.0 × titanium; Zyklus: 6.0 s; Leistung: 11.0 MW; MK1/Common: 40.0 U/min.
Basisverkaufspreis: $6.8375; Kataloganker: $5.47; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; titanium_ore (Titanium Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: advanced_alloy_components (Advanced Alloy Components); aerospace_components (Aerospace Components); titanium_components (Titanium Components); turbine_components (Turbine Components); wind_components (Wind Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Treated Lumber — `treated_lumber`

Rezept `recipe.processor.treated_lumber`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 3 x timber (Timber); 2 x crude_oil (Crude Oil); 1 x natural_gas (Natural Gas). Unterschiedliche Inputs: 3; gesamte Inputmenge: 6.
Output: 3.0 × treated_lumber; Zyklus: 6.0 s; Leistung: 7.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $3.9177; Kataloganker: $2.72; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; timber (Timber): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; crude_oil (Crude Oil): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; natural_gas (Natural Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: wooden_components (Wooden Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Tungsten — `tungsten`

Rezept `recipe.processor.tungsten`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 8 x tungsten_ore (Tungsten Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 8.
Output: 4.0 × tungsten; Zyklus: 6.0 s; Leistung: 11.0 MW; MK1/Common: 40.0 U/min.
Basisverkaufspreis: $7.975; Kataloganker: $6.38; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; tungsten_ore (Tungsten Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: cutting_tooling (Cutting Tooling); mining_components (Mining Components); precision_components (Precision Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Vanadium — `vanadium`

Rezept `recipe.processor.vanadium`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 8 x vanadium_ore (Vanadium Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 8.
Output: 4.0 × vanadium; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 40.0 U/min.
Basisverkaufspreis: $5.9875; Kataloganker: $4.79; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; vanadium_ore (Vanadium Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: advanced_alloy_components (Advanced Alloy Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Vanadium Alloy — `vanadium_alloy`

Rezept `recipe.processor.vanadium_alloy`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 4 x vanadium_ore (Vanadium Ore); 4 x iron_ore (Iron Ore). Unterschiedliche Inputs: 2; gesamte Inputmenge: 8.
Output: 3.0 × vanadium_alloy; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $6.025; Kataloganker: $4.82; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; vanadium_ore (Vanadium Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; iron_ore (Iron Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: advanced_alloy_components (Advanced Alloy Components); grid_storage_components (Grid Storage Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Vegetable Oil — `vegetable_oil`

Rezept `recipe.processor.vegetable_oil`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 2 x rapeseed (Rapeseed); 2 x soybeans (Soybeans). Unterschiedliche Inputs: 2; gesamte Inputmenge: 4.
Output: 2.0 × vegetable_oil; Zyklus: 6.0 s; Leistung: 5.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $3.0; Kataloganker: $2.4; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4; rapeseed (Rapeseed): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; soybeans (Soybeans): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: biodiesel_feedstock (Biodiesel Feedstock); nutrition_components (Nutrition Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Wood Pulp — `wood_pulp`

Rezept `recipe.processor.wood_pulp`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 3 x timber (Timber); 1 x crude_oil (Crude Oil); 1 x natural_gas (Natural Gas). Unterschiedliche Inputs: 3; gesamte Inputmenge: 5.
Output: 3.0 × wood_pulp; Zyklus: 6.0 s; Leistung: 6.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $3.044; Kataloganker: $2.4; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; timber (Timber): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; crude_oil (Crude Oil): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0; natural_gas (Natural Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: packaging_components (Packaging Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

#### Zinc — `zinc`

Rezept `recipe.processor.zinc`; Maschine `machine.processor` (Processor); Common-Kaufpreis $275.0.
Inputs/Zyklus: 9 x zinc_ore (Zinc Ore). Unterschiedliche Inputs: 1; gesamte Inputmenge: 9.
Output: 5.0 × zinc; Zyklus: 6.0 s; Leistung: 8.0 MW; MK1/Common: 50.0 U/min.
Basisverkaufspreis: $3.5625; Kataloganker: $2.85; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9; zinc_ore (Zinc Ore): Produktion freigeschaltet UND Lifetime-Produktion >= 120.0.
Unmittelbare Folgeprodukte: galvanized_components (Galvanized Components).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 6.0, Basiszyklus 6.0 s, Basisleistung 8.0 MW; wirksame Werte siehe oben.

### Fabrication (86)

#### AI Compute Components — `ai_compute_components`

Rezept `recipe.fabricator.ai_compute_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x high_purity_silicon (High-Purity Silicon); 1 x rare_earth_metals (Rare Earth Metals); 1 x gold (Gold). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × ai_compute_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $61.45; Kataloganker: $49.16; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; rare_earth_metals (Rare Earth Metals): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gold (Gold): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: advanced_industrial_robot (Advanced Industrial Robot); ai_accelerator (AI Accelerator); ai_server (AI Server); autonomous_vehicle (Autonomous Vehicle); supercomputer (Supercomputer).

#### Advanced Alloy Components — `advanced_alloy_components`

Rezept `recipe.fabricator.advanced_alloy_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x vanadium_alloy (Vanadium Alloy); 1 x vanadium (Vanadium); 1 x titanium (Titanium). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × advanced_alloy_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $30.1; Kataloganker: $24.08; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; vanadium_alloy (Vanadium Alloy): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; vanadium (Vanadium): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; titanium (Titanium): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: gas_turbine (Gas Turbine).

#### Advanced Cell Components — `advanced_cell_components`

Rezept `recipe.fabricator.advanced_cell_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x aluminum (Aluminum); 1 x lithium (Lithium); 1 x purified_graphite (Purified Graphite); 1 x cobalt (Cobalt). Unterschiedliche Inputs: 4; gesamte Inputmenge: 4.
Output: 1.0 × advanced_cell_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $24.6641; Kataloganker: $16.59; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15; aluminum (Aluminum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; lithium (Lithium): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; purified_graphite (Purified Graphite): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; cobalt (Cobalt): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: premium_electric_vehicle (Premium Electric Vehicle).

#### Aerospace Components — `aerospace_components`

Rezept `recipe.fabricator.aerospace_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x aluminum (Aluminum); 1 x titanium (Titanium); 1 x carbon_fiber (Carbon Fiber). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × aerospace_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $31.6125; Kataloganker: $25.29; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; aluminum (Aluminum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; titanium (Titanium): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; carbon_fiber (Carbon Fiber): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: advanced_aircraft (Advanced Aircraft); autonomous_aircraft (Autonomous Aircraft); cargo_aircraft (Cargo Aircraft); commercial_aircraft (Commercial Aircraft); communication_satellite (Communication Satellite); high_speed_train (High-Speed Train); industrial_drone (Industrial Drone); launch_vehicle (Launch Vehicle); light_aircraft (Light Aircraft); navigation_satellite (Navigation Satellite); orbital_vehicle (Orbital Vehicle); satellite (Satellite).

#### Agricultural Chemicals — `agricultural_chemicals`

Rezept `recipe.fabricator.agricultural_chemicals`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x chemical_feedstock (Chemical Feedstock); 1 x chlorine (Chlorine); 1 x sulfuric_acid (Sulfuric Acid). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × agricultural_chemicals; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $11.15; Kataloganker: $8.6; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; chemical_feedstock (Chemical Feedstock): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; chlorine (Chlorine): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sulfuric_acid (Sulfuric Acid): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: advanced_fertilizer (Advanced Fertilizer); crop_protection_products (Crop Protection Products).

#### Agricultural Mineral Components — `agricultural_mineral_components`

Rezept `recipe.fabricator.agricultural_mineral_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x potassium_compound (Potassium Compound); 1 x phosphoric_acid (Phosphoric Acid). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × agricultural_mineral_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $11.8682; Kataloganker: $8.89; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; potassium_compound (Potassium Compound): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; phosphoric_acid (Phosphoric Acid): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: fertilizer (Fertilizer).

#### Aluminum Components — `aluminum_components`

Rezept `recipe.fabricator.aluminum_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x aluminum (Aluminum). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 2.0 × aluminum_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $4.1035; Kataloganker: $2.96; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1; aluminum (Aluminum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: industrial_glass_panels (Industrial Glass Panels); power_cable (Power Cable).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Asphalt Components — `asphalt_components`

Rezept `recipe.fabricator.asphalt_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x bitumen (Bitumen); 1 x cement (Cement). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × asphalt_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $14.2297; Kataloganker: $10.93; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 3; bitumen (Bitumen): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; cement (Cement): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: construction_materials (Construction Materials).

#### Autonomous Components — `autonomous_components`

Rezept `recipe.fabricator.autonomous_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x high_purity_silicon (High-Purity Silicon); 1 x rare_earth_metals (Rare Earth Metals); 1 x copper (Copper). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × autonomous_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $33.6125; Kataloganker: $26.89; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; rare_earth_metals (Rare Earth Metals): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: advanced_industrial_robot (Advanced Industrial Robot); autonomous_aircraft (Autonomous Aircraft); autonomous_cargo_ship (Autonomous Cargo Ship); autonomous_freight_train (Autonomous Freight Train); autonomous_vehicle (Autonomous Vehicle).

#### Avionics Components — `avionics_components`

Rezept `recipe.fabricator.avionics_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 4 x high_purity_silicon (High-Purity Silicon); 2 x copper (Copper); 2 x gold (Gold); 1 x aluminum (Aluminum). Unterschiedliche Inputs: 4; gesamte Inputmenge: 9.
Output: 1.0 × avionics_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $118.4625; Kataloganker: $94.77; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gold (Gold): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; aluminum (Aluminum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: advanced_aircraft (Advanced Aircraft); autonomous_aircraft (Autonomous Aircraft); cargo_aircraft (Cargo Aircraft); commercial_aircraft (Commercial Aircraft); light_aircraft (Light Aircraft); orbital_vehicle (Orbital Vehicle).

#### Battery Components — `battery_components`

Rezept `recipe.fabricator.battery_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x lithium (Lithium); 1 x nickel (Nickel); 1 x cobalt (Cobalt); 1 x aluminum (Aluminum). Unterschiedliche Inputs: 4; gesamte Inputmenge: 4.
Output: 1.0 × battery_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $26.6898; Kataloganker: $15.81; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15; lithium (Lithium): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; nickel (Nickel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; cobalt (Cobalt): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; aluminum (Aluminum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: electric_vehicle (Electric Vehicle); grid_battery (Grid Battery); industrial_drone (Industrial Drone).

#### Battery Materials — `battery_materials`

Rezept `recipe.fabricator.battery_materials`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x lithium (Lithium); 1 x nickel (Nickel); 1 x cobalt (Cobalt). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 2.0 × battery_materials; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $15.5125; Kataloganker: $12.41; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15; lithium (Lithium): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; nickel (Nickel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; cobalt (Cobalt): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: grid_battery (Grid Battery).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Bearing Components — `bearing_components`

Rezept `recipe.fabricator.bearing_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x steel (Steel); 1 x chromium (Chromium). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 2.0 × bearing_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $14.8154; Kataloganker: $11.71; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 11; steel (Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; chromium (Chromium): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: gearbox (Gearbox).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Bio-Composite — `bio_composite`

Rezept `recipe.fabricator.bio_composite`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x cellulose (Cellulose); 1 x industrial_resin (Industrial Resin). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × bio_composite; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $11.3878; Kataloganker: $7.75; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; cellulose (Cellulose): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; industrial_resin (Industrial Resin): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: bioplastic (Bioplastic); sustainable_packaging (Sustainable Packaging).

#### Bio-Material Components — `bio_material_components`

Rezept `recipe.fabricator.bio_material_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x bio_lubricant (Bio-Lubricant); 1 x cellulose (Cellulose). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × bio_material_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $8.67; Kataloganker: $5.55; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; bio_lubricant (Bio-Lubricant): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; cellulose (Cellulose): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: bio_based_chemicals (Bio-Based Chemicals).

#### Biodiesel Feedstock — `biodiesel_feedstock`

Rezept `recipe.fabricator.biodiesel_feedstock`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x vegetable_oil (Vegetable Oil); 1 x chemical_feedstock (Chemical Feedstock). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × biodiesel_feedstock; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $12.4178; Kataloganker: $9.46; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; vegetable_oil (Vegetable Oil): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; chemical_feedstock (Chemical Feedstock): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: biodiesel (Biodiesel).

#### Biopolymer — `biopolymer`

Rezept `recipe.fabricator.biopolymer`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x starch (Starch); 1 x fermentation_feedstock (Fermentation Feedstock). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × biopolymer; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $8.0195; Kataloganker: $5.89; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4; starch (Starch): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; fermentation_feedstock (Fermentation Feedstock): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: bioplastic (Bioplastic).

#### Catalyst Components — `catalyst_components`

Rezept `recipe.fabricator.catalyst_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x catalyst_metal (Catalyst Metal); 1 x palladium (Palladium). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × catalyst_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $41.9632; Kataloganker: $33.42; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 20; catalyst_metal (Catalyst Metal): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; palladium (Palladium): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: synthetic_fuel_plant (Synthetic Fuel Plant).

#### Ceramic Components — `ceramic_components`

Rezept `recipe.fabricator.ceramic_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x ceramics (Ceramics). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 2.0 × ceramic_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $3.0383; Kataloganker: $2.17; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; ceramics (Ceramics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: advanced_furnace (Advanced Furnace); advanced_semiconductor_equipment (Advanced Semiconductor Equipment); semiconductor_equipment (Semiconductor Equipment).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Chemical Components — `chemical_components`

Rezept `recipe.fabricator.chemical_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x chemical_feedstock (Chemical Feedstock); 1 x sulfuric_acid (Sulfuric Acid). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × chemical_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $13.6305; Kataloganker: $10.44; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; chemical_feedstock (Chemical Feedstock): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sulfuric_acid (Sulfuric Acid): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: bio_based_chemicals (Bio-Based Chemicals); biofuel (Biofuel); carbon_capture_plant (Carbon Capture Plant); crop_protection_products (Crop Protection Products); industrial_chemicals (Industrial Chemicals); industrial_rubber_products (Industrial Rubber Products); synthetic_fuel_plant (Synthetic Fuel Plant).

#### Composite Components — `composite_components`

Rezept `recipe.fabricator.composite_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x carbon_fiber (Carbon Fiber); 1 x industrial_resin (Industrial Resin). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × composite_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $25.6561; Kataloganker: $20.19; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; carbon_fiber (Carbon Fiber): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; industrial_resin (Industrial Resin): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: advanced_protective_equipment (Advanced Protective Equipment); engineered_structures (Engineered Structures); high_speed_vessel (High-Speed Vessel); industrial_plastics (Industrial Plastics).

#### Compressor Components — `compressor_components`

Rezept `recipe.fabricator.compressor_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x steel (Steel); 1 x aluminum (Aluminum). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × compressor_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $16.173; Kataloganker: $12.5; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1; steel (Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; aluminum (Aluminum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: carbon_capture_plant (Carbon Capture Plant); industrial_compressor (Industrial Compressor).

#### Computing Components — `computing_components`

Rezept `recipe.fabricator.computing_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 4 x high_purity_silicon (High-Purity Silicon); 2 x copper (Copper); 2 x gold (Gold); 2 x silver (Silver). Unterschiedliche Inputs: 4; gesamte Inputmenge: 10.
Output: 1.0 × computing_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $139.875; Kataloganker: $111.9; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gold (Gold): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; silver (Silver): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: diagnostic_system (Diagnostic System); industrial_computer (Industrial Computer); machine_vision_system (Machine Vision System); server (Server).

#### Concrete Components — `concrete_components`

Rezept `recipe.fabricator.concrete_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x cement (Cement); 1 x steel (Steel). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 2.0 × concrete_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $8.7074; Kataloganker: $6.75; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 3; cement (Cement): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; steel (Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: construction_materials (Construction Materials); prefabricated_structures (Prefabricated Structures); reinforced_concrete (Reinforced Concrete); structural_systems (Structural Systems).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Control Electronics — `control_electronics`

Rezept `recipe.fabricator.control_electronics`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x high_purity_silicon (High-Purity Silicon); 1 x copper (Copper); 1 x gold (Gold); 1 x silver (Silver). Unterschiedliche Inputs: 4; gesamte Inputmenge: 5.
Output: 1.0 × control_electronics; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $71.75; Kataloganker: $57.4; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gold (Gold): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; silver (Silver): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: advanced_furnace (Advanced Furnace); advanced_medical_equipment (Advanced Medical Equipment); advanced_semiconductor_equipment (Advanced Semiconductor Equipment); autonomous_control_system (Autonomous Control System); autonomous_mobile_robot (Autonomous Mobile Robot); cnc_machine (CNC Machine); commercial_truck (Commercial Truck); container_ship (Container Ship); heavy_machinery (Heavy Machinery); heavy_mining_drill (Heavy Mining Drill); high_speed_network_system (High-Speed Network System); industrial_controller (Industrial Controller); industrial_cutting_machine (Industrial Cutting Machine); industrial_display (Industrial Display); industrial_inverter (Industrial Inverter); industrial_relay (Industrial Relay); industrial_robot (Industrial Robot); industrial_sensor (Industrial Sensor); laboratory_equipment (Laboratory Equipment); launch_vehicle (Launch Vehicle); memory_module (Memory Module); microcontroller (Microcontroller); network_switch (Network Switch); nuclear_reactor (Nuclear Reactor); orbital_vehicle (Orbital Vehicle); processing_equipment (Processing Equipment); quantum_computing_module (Quantum Computing Module); robotic_arm (Robotic Arm); semiconductor_equipment (Semiconductor Equipment); servo_motor (Servo Motor); switchgear (Switchgear); utility_vehicle (Utility Vehicle).

#### Copper Wire — `copper_wire`

Rezept `recipe.fabricator.copper_wire`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x copper (Copper). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 3.0 × copper_wire; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 30.0 U/min.
Basisverkaufspreis: $3.6608; Kataloganker: $2.71; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: basic_chip (Basic Chip); electrical_cable (Electrical Cable).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Corrosion Resistant Components — `corrosion_resistant_components`

Rezept `recipe.fabricator.corrosion_resistant_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x galvanized_metal (Galvanized Metal); 1 x stainless_steel (Stainless Steel). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × corrosion_resistant_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $24.2681; Kataloganker: $19.07; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 11; galvanized_metal (Galvanized Metal): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; stainless_steel (Stainless Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: tanker (Tanker).

#### Cutting Tooling — `cutting_tooling`

Rezept `recipe.fabricator.cutting_tooling`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x tungsten (Tungsten); 1 x steel (Steel). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × cutting_tooling; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $21.7694; Kataloganker: $17.04; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; tungsten (Tungsten): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; steel (Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: industrial_cutting_machine (Industrial Cutting Machine).

#### Display Components — `display_components`

Rezept `recipe.fabricator.display_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x glass (Glass); 1 x high_purity_silicon (High-Purity Silicon); 1 x polymer (Polymer). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × display_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $26.8875; Kataloganker: $21.51; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; glass (Glass): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; polymer (Polymer): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: industrial_computer (Industrial Computer); medical_monitor (Medical Monitor); premium_electric_vehicle (Premium Electric Vehicle).

#### Electrical Components — `electrical_components`

Rezept `recipe.fabricator.electrical_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x copper (Copper); 1 x polymer (Polymer); 1 x tin (Tin). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 2.0 × electrical_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $8.972; Kataloganker: $7.04; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; polymer (Polymer): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; tin (Tin): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: electric_motor (Electric Motor); industrial_equipment (Industrial Equipment); industrial_relay (Industrial Relay); switchgear (Switchgear); transformer (Transformer).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Electrolyzer Components — `electrolyzer_components`

Rezept `recipe.fabricator.electrolyzer_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x copper (Copper); 2 x high_purity_silicon (High-Purity Silicon); 1 x aluminum (Aluminum); 1 x gold (Gold). Unterschiedliche Inputs: 4; gesamte Inputmenge: 6.
Output: 1.0 × electrolyzer_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $64.7875; Kataloganker: $51.83; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; aluminum (Aluminum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gold (Gold): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: fusion_reactor_module (Fusion Reactor Module); hydrogen_electrolyzer (Hydrogen Electrolyzer); synthetic_fuel_plant (Synthetic Fuel Plant).

#### Ethanol Components — `ethanol_components`

Rezept `recipe.fabricator.ethanol_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x fermentation_feedstock (Fermentation Feedstock). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 1.0 × ethanol_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $5.636; Kataloganker: $3.87; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4; fermentation_feedstock (Fermentation Feedstock): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: biofuel (Biofuel).

#### Fertilizer Components — `fertilizer_components`

Rezept `recipe.fabricator.fertilizer_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x ammonia (Ammonia); 2 x phosphoric_acid (Phosphoric Acid). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 2.0 × fertilizer_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $6.9086; Kataloganker: $5.17; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; ammonia (Ammonia): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; phosphoric_acid (Phosphoric Acid): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: advanced_fertilizer (Advanced Fertilizer); fertilizer (Fertilizer).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Fiber Components — `fiber_components`

Rezept `recipe.fabricator.fiber_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x cellulose (Cellulose); 1 x industrial_resin (Industrial Resin). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × fiber_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $15.9397; Kataloganker: $10.57; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; cellulose (Cellulose): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; industrial_resin (Industrial Resin): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: industrial_insulation (Industrial Insulation).

#### Filtration Components — `filtration_components`

Rezept `recipe.fabricator.filtration_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x ceramics (Ceramics); 1 x processed_gypsum (Processed Gypsum); 1 x polymer (Polymer). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × filtration_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $12.407; Kataloganker: $9.64; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; ceramics (Ceramics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; processed_gypsum (Processed Gypsum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; polymer (Polymer): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: carbon_capture_plant (Carbon Capture Plant); desalination_plant (Desalination Plant).

#### Food Ingredients — `food_ingredients`

Rezept `recipe.fabricator.food_ingredients`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x flour (Flour); 1 x corn_meal (Corn Meal); 1 x refined_sugar (Refined Sugar). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 2.0 × food_ingredients; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $3.1194; Kataloganker: $2.27; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4; flour (Flour): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; corn_meal (Corn Meal): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; refined_sugar (Refined Sugar): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: animal_feed (Animal Feed); bakery_products (Bakery Products); packaged_food (Packaged Food); packaged_meals (Packaged Meals); processed_food (Processed Food).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Galvanized Components — `galvanized_components`

Rezept `recipe.fabricator.galvanized_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x galvanized_metal (Galvanized Metal); 1 x zinc (Zinc). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 2.0 × galvanized_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $7.5604; Kataloganker: $5.82; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9; galvanized_metal (Galvanized Metal): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; zinc (Zinc): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: industrial_hall_modules (Industrial Hall Modules).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Gas Handling Components — `gas_handling_components`

Rezept `recipe.fabricator.gas_handling_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x industrial_gas (Industrial Gas); 1 x hydrogen (Hydrogen). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × gas_handling_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $8.794; Kataloganker: $6.52; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; industrial_gas (Industrial Gas): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; hydrogen (Hydrogen): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: industrial_chemicals (Industrial Chemicals).

#### Gear Components — `gear_components`

Rezept `recipe.fabricator.gear_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x steel (Steel); 1 x manganese (Manganese). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 2.0 × gear_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $14.3184; Kataloganker: $11.3; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9; steel (Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; manganese (Manganese): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: gearbox (Gearbox); industrial_crusher (Industrial Crusher).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Glass Panels — `glass_panels`

Rezept `recipe.fabricator.glass_panels`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x glass (Glass); 1 x aluminum (Aluminum). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 2.0 × glass_panels; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $5.6317; Kataloganker: $4.26; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; glass (Glass): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; aluminum (Aluminum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: industrial_display (Industrial Display); industrial_glass_panels (Industrial Glass Panels); industrial_hall_modules (Industrial Hall Modules); laboratory_equipment (Laboratory Equipment); safety_equipment (Safety Equipment).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Grid Storage Components — `grid_storage_components`

Rezept `recipe.fabricator.grid_storage_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x lithium (Lithium); 1 x vanadium_alloy (Vanadium Alloy); 1 x purified_graphite (Purified Graphite). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × grid_storage_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $19.3795; Kataloganker: $15.42; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; lithium (Lithium): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; vanadium_alloy (Vanadium Alloy): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; purified_graphite (Purified Graphite): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: data_center_module (Data Center Module); supercomputer (Supercomputer).

#### Hydraulic Components — `hydraulic_components`

Rezept `recipe.fabricator.hydraulic_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x steel (Steel); 1 x industrial_resin (Industrial Resin). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × hydraulic_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $18.5255; Kataloganker: $14.41; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; steel (Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; industrial_resin (Industrial Resin): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: excavator (Excavator); heavy_machinery (Heavy Machinery); heavy_mining_drill (Heavy Mining Drill); hydraulic_system (Hydraulic System).

#### Industrial Fabric — `industrial_fabric`

Rezept `recipe.fabricator.industrial_fabric`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x cotton_fiber (Cotton Fiber); 1 x polymer (Polymer); 1 x processed_rubber (Processed Rubber). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × industrial_fabric; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $14.0533; Kataloganker: $7.14; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; cotton_fiber (Cotton Fiber): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; polymer (Polymer): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; processed_rubber (Processed Rubber): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: advanced_protective_equipment (Advanced Protective Equipment); commercial_furniture (Commercial Furniture); industrial_clothing (Industrial Clothing); protective_clothing (Protective Clothing); safety_equipment (Safety Equipment); workwear (Workwear).

#### Insulated Wire — `insulated_wire`

Rezept `recipe.fabricator.insulated_wire`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x copper (Copper); 1 x polymer (Polymer). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 2.0 × insulated_wire; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $7.1125; Kataloganker: $5.69; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; polymer (Polymer): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: communication_cable (Communication Cable); electrical_cable (Electrical Cable); power_cable (Power Cable).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Insulation Material — `insulation_material`

Rezept `recipe.fabricator.insulation_material`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x processed_gypsum (Processed Gypsum); 1 x polymer (Polymer). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 2.0 × insulation_material; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $4.8718; Kataloganker: $3.64; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; processed_gypsum (Processed Gypsum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; polymer (Polymer): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: high_voltage_equipment (High-Voltage Equipment); industrial_hall_modules (Industrial Hall Modules); industrial_insulation (Industrial Insulation); protective_packaging (Protective Packaging).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Iron Components — `iron_components`

Rezept `recipe.fabricator.iron_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x iron (Iron). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 2.0 × iron_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $4.7608; Kataloganker: $3.48; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1; iron (Iron): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: industrial_equipment (Industrial Equipment).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Magnetic Components — `magnetic_components`

Rezept `recipe.fabricator.magnetic_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x rare_earth_metals (Rare Earth Metals); 1 x iron (Iron). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × magnetic_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $17.1373; Kataloganker: $13.28; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15; rare_earth_metals (Rare Earth Metals): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; iron (Iron): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: autonomous_control_system (Autonomous Control System); industrial_laser (Industrial Laser); precision_motor (Precision Motor); radio_transceiver (Radio Transceiver).

#### Marine Components — `marine_components`

Rezept `recipe.fabricator.marine_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x steel (Steel); 1 x industrial_resin (Industrial Resin). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × marine_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $30.2151; Kataloganker: $23.89; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; steel (Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; industrial_resin (Industrial Resin): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: autonomous_cargo_ship (Autonomous Cargo Ship); cargo_vessel (Cargo Vessel); container_ship (Container Ship); high_speed_vessel (High-Speed Vessel); tanker (Tanker); workboat (Workboat).

#### Medical Components — `medical_components`

Rezept `recipe.fabricator.medical_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x stainless_steel (Stainless Steel); 1 x glass (Glass); 1 x platinum (Platinum). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × medical_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $42.2875; Kataloganker: $33.83; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 20; stainless_steel (Stainless Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; glass (Glass): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; platinum (Platinum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: advanced_medical_equipment (Advanced Medical Equipment); diagnostic_system (Diagnostic System); medical_monitor (Medical Monitor).

#### Membrane Components — `membrane_components`

Rezept `recipe.fabricator.membrane_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x polymer (Polymer); 1 x cellulose (Cellulose); 1 x chlorine (Chlorine). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × membrane_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $14.7091; Kataloganker: $10.66; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; polymer (Polymer): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; cellulose (Cellulose): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; chlorine (Chlorine): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: desalination_plant (Desalination Plant).

#### Memory Components — `memory_components`

Rezept `recipe.fabricator.memory_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 3 x high_purity_silicon (High-Purity Silicon); 1 x copper (Copper); 1 x gold (Gold); 1 x silver (Silver). Unterschiedliche Inputs: 4; gesamte Inputmenge: 6.
Output: 1.0 × memory_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $84.35; Kataloganker: $67.48; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gold (Gold): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; silver (Silver): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: compute_node (Compute Node); cpu (CPU); memory_module (Memory Module); server (Server).

#### Mining Components — `mining_components`

Rezept `recipe.fabricator.mining_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x steel (Steel); 1 x tungsten (Tungsten). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × mining_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $21.7694; Kataloganker: $17.04; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; steel (Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; tungsten (Tungsten): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: heavy_mining_drill (Heavy Mining Drill); industrial_crusher (Industrial Crusher); mining_drill (Mining Drill); mining_equipment (Mining Equipment).

#### Motor Components — `motor_components`

Rezept `recipe.fabricator.motor_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x copper (Copper); 1 x rare_earth_metals (Rare Earth Metals); 1 x iron (Iron). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × motor_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $24.0; Kataloganker: $19.2; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; rare_earth_metals (Rare Earth Metals): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; iron (Iron): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: electric_locomotive (Electric Locomotive); electric_motor (Electric Motor); electric_vehicle (Electric Vehicle); industrial_compressor (Industrial Compressor); industrial_generator (Industrial Generator); industrial_pump (Industrial Pump); industrial_robot (Industrial Robot); mining_drill (Mining Drill); precision_motor (Precision Motor); robotic_actuator (Robotic Actuator); robotic_arm (Robotic Arm); servo_motor (Servo Motor).

#### Network Components — `network_components`

Rezept `recipe.fabricator.network_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 4 x copper (Copper); 4 x high_purity_silicon (High-Purity Silicon); 2 x gold (Gold); 1 x aluminum (Aluminum). Unterschiedliche Inputs: 4; gesamte Inputmenge: 11.
Output: 1.0 × network_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $127.425; Kataloganker: $101.94; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gold (Gold): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; aluminum (Aluminum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: ai_server (AI Server); autonomous_cargo_ship (Autonomous Cargo Ship); autonomous_freight_train (Autonomous Freight Train); communication_satellite (Communication Satellite); compute_node (Compute Node); high_speed_network_system (High-Speed Network System); network_switch (Network Switch); router (Router); server_rack (Server Rack); supercomputer (Supercomputer).

#### Nuclear Fuel Components — `nuclear_fuel_components`

Rezept `recipe.fabricator.nuclear_fuel_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x nuclear_material (Nuclear Material); 1 x shielding_material (Shielding Material). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × nuclear_fuel_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $22.5145; Kataloganker: $17.64; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 25; nuclear_material (Nuclear Material): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; shielding_material (Shielding Material): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: fusion_reactor_module (Fusion Reactor Module); nuclear_fuel_assembly (Nuclear Fuel Assembly); nuclear_reactor (Nuclear Reactor).

#### Nutrition Components — `nutrition_components`

Rezept `recipe.fabricator.nutrition_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x soy_protein (Soy Protein); 1 x vegetable_oil (Vegetable Oil); 1 x fruit_concentrate (Fruit Concentrate). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × nutrition_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $11.3985; Kataloganker: $8.81; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4; soy_protein (Soy Protein): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; vegetable_oil (Vegetable Oil): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; fruit_concentrate (Fruit Concentrate): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: animal_feed (Animal Feed); packaged_beverages (Packaged Beverages); packaged_meals (Packaged Meals); packaged_nutrition (Packaged Nutrition); processed_food (Processed Food); soft_drinks (Soft Drinks).

#### Packaging Components — `packaging_components`

Rezept `recipe.fabricator.packaging_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x wood_pulp (Wood Pulp); 1 x polymer (Polymer). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 2.0 × packaging_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $7.5527; Kataloganker: $5.78; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; wood_pulp (Wood Pulp): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; polymer (Polymer): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: bakery_products (Bakery Products); industrial_packaging (Industrial Packaging); industrial_plastics (Industrial Plastics); packaged_beverages (Packaged Beverages); packaged_food (Packaged Food); packaged_meals (Packaged Meals); packaged_nutrition (Packaged Nutrition); packaging_materials (Packaging Materials); protective_packaging (Protective Packaging); soft_drinks (Soft Drinks); sustainable_packaging (Sustainable Packaging).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Power Electronics — `power_electronics`

Rezept `recipe.fabricator.power_electronics`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x high_purity_silicon (High-Purity Silicon); 2 x copper (Copper); 1 x gold (Gold); 1 x aluminum (Aluminum). Unterschiedliche Inputs: 4; gesamte Inputmenge: 6.
Output: 1.0 × power_electronics; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $64.7875; Kataloganker: $51.83; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gold (Gold): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; aluminum (Aluminum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: ai_accelerator (AI Accelerator); autonomous_control_system (Autonomous Control System); cellular_base_station (Cellular Base Station); desalination_plant (Desalination Plant); electric_locomotive (Electric Locomotive); grid_battery (Grid Battery); grid_storage_system (Grid Storage System); high_speed_train (High-Speed Train); high_voltage_equipment (High-Voltage Equipment); hydrogen_electrolyzer (Hydrogen Electrolyzer); industrial_inverter (Industrial Inverter); solar_array (Solar Array); superconducting_magnet_system (Superconducting Magnet System); wind_turbine (Wind Turbine).

#### Precision Components — `precision_components`

Rezept `recipe.fabricator.precision_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x steel (Steel); 1 x aluminum (Aluminum); 1 x tungsten (Tungsten). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × precision_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $25.6125; Kataloganker: $20.49; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; steel (Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; aluminum (Aluminum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; tungsten (Tungsten): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: advanced_medical_equipment (Advanced Medical Equipment); advanced_semiconductor_equipment (Advanced Semiconductor Equipment); cnc_machine (CNC Machine); industrial_cutting_machine (Industrial Cutting Machine); industrial_laser (Industrial Laser); industrial_robot (Industrial Robot); industrial_seals (Industrial Seals); laboratory_equipment (Laboratory Equipment); precision_motor (Precision Motor); robotic_actuator (Robotic Actuator); robotic_arm (Robotic Arm); semiconductor_equipment (Semiconductor Equipment); servo_motor (Servo Motor); surgical_equipment (Surgical Equipment).

#### Processor Components — `processor_components`

Rezept `recipe.fabricator.processor_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x gold (Gold); 2 x high_purity_silicon (High-Purity Silicon); 1 x copper (Copper); 1 x rare_earth_metals (Rare Earth Metals). Unterschiedliche Inputs: 4; gesamte Inputmenge: 6.
Output: 1.0 × processor_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $85.725; Kataloganker: $68.58; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; gold (Gold): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; rare_earth_metals (Rare Earth Metals): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: autonomous_control_system (Autonomous Control System); compute_node (Compute Node); cpu (CPU); quantum_computing_module (Quantum Computing Module).

#### Pump Components — `pump_components`

Rezept `recipe.fabricator.pump_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x steel (Steel); 1 x copper (Copper). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × pump_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $17.5612; Kataloganker: $13.63; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1; steel (Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: carbon_capture_plant (Carbon Capture Plant); desalination_plant (Desalination Plant); industrial_pump (Industrial Pump); processing_equipment (Processing Equipment); tanker (Tanker).

#### Rail Components — `rail_components`

Rezept `recipe.fabricator.rail_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x steel (Steel); 1 x manganese (Manganese). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × rail_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $28.637; Kataloganker: $22.61; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9; steel (Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; manganese (Manganese): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: autonomous_freight_train (Autonomous Freight Train); diesel_locomotive (Diesel Locomotive); electric_locomotive (Electric Locomotive); freight_railcar (Freight Railcar); high_speed_train (High-Speed Train); railway_track (Railway Track).

#### Reactor Components — `reactor_components`

Rezept `recipe.fabricator.reactor_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x nuclear_material (Nuclear Material). Unterschiedliche Inputs: 1; gesamte Inputmenge: 1.
Output: 1.0 × reactor_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $9.9013; Kataloganker: $7.26; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 25; nuclear_material (Nuclear Material): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: fusion_reactor_module (Fusion Reactor Module); nuclear_reactor (Nuclear Reactor).

#### Refractory Alloy Components — `refractory_alloy_components`

Rezept `recipe.fabricator.refractory_alloy_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x molybdenum (Molybdenum); 1 x niobium (Niobium); 1 x superconducting_alloy (Superconducting Alloy). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × refractory_alloy_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $36.025; Kataloganker: $28.82; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; molybdenum (Molybdenum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; niobium (Niobium): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; superconducting_alloy (Superconducting Alloy): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: fusion_reactor_module (Fusion Reactor Module); quantum_computing_module (Quantum Computing Module); superconducting_magnet_system (Superconducting Magnet System).

#### Rubber Blend Components — `rubber_blend_components`

Rezept `recipe.fabricator.rubber_blend_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x synthetic_rubber (Synthetic Rubber); 1 x processed_rubber (Processed Rubber). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × rubber_blend_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $17.5758; Kataloganker: $13.64; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; synthetic_rubber (Synthetic Rubber): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; processed_rubber (Processed Rubber): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: industrial_rubber_products (Industrial Rubber Products).

#### Semiconductor Components — `semiconductor_components`

Rezept `recipe.fabricator.semiconductor_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x high_purity_silicon (High-Purity Silicon); 1 x copper (Copper); 1 x gold (Gold). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × semiconductor_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $54.325; Kataloganker: $43.46; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gold (Gold): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: basic_chip (Basic Chip); industrial_laser (Industrial Laser); microchip (Microchip).

#### Semiconductor Die — `semiconductor_die`

Rezept `recipe.fabricator.semiconductor_die`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x high_purity_silicon (High-Purity Silicon); 1 x copper (Copper); 1 x gold (Gold); 1 x silver (Silver). Unterschiedliche Inputs: 4; gesamte Inputmenge: 5.
Output: 1.0 × semiconductor_die; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $68.125; Kataloganker: $54.5; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gold (Gold): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; silver (Silver): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: microchip (Microchip); microcontroller (Microcontroller).

#### Sensor Components — `sensor_components`

Rezept `recipe.fabricator.sensor_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x high_purity_silicon (High-Purity Silicon); 1 x copper (Copper); 1 x gold (Gold); 1 x rare_earth_metals (Rare Earth Metals). Unterschiedliche Inputs: 4; gesamte Inputmenge: 5.
Output: 1.0 × sensor_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $68.125; Kataloganker: $54.5; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gold (Gold): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; rare_earth_metals (Rare Earth Metals): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: advanced_industrial_robot (Advanced Industrial Robot); advanced_medical_equipment (Advanced Medical Equipment); advanced_protective_equipment (Advanced Protective Equipment); advanced_semiconductor_equipment (Advanced Semiconductor Equipment); autonomous_aircraft (Autonomous Aircraft); autonomous_cargo_ship (Autonomous Cargo Ship); autonomous_mobile_robot (Autonomous Mobile Robot); autonomous_vehicle (Autonomous Vehicle); commercial_truck (Commercial Truck); diagnostic_system (Diagnostic System); industrial_controller (Industrial Controller); industrial_drone (Industrial Drone); industrial_robot (Industrial Robot); industrial_sensor (Industrial Sensor); machine_vision_system (Machine Vision System); medical_monitor (Medical Monitor); navigation_satellite (Navigation Satellite); utility_vehicle (Utility Vehicle).

#### Server Components — `server_components`

Rezept `recipe.fabricator.server_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x high_purity_silicon (High-Purity Silicon); 1 x copper (Copper); 1 x gold (Gold). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × server_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $54.325; Kataloganker: $43.46; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gold (Gold): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: ai_server (AI Server); data_center_module (Data Center Module); server_rack (Server Rack); supercomputer (Supercomputer).

#### Shielding Components — `shielding_components`

Rezept `recipe.fabricator.shielding_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x shielding_material (Shielding Material); 1 x lead (Lead). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 2.0 × shielding_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $5.7778; Kataloganker: $4.38; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; shielding_material (Shielding Material): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; lead (Lead): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: nuclear_fuel_assembly (Nuclear Fuel Assembly).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Silicon Substrate — `silicon_substrate`

Rezept `recipe.fabricator.silicon_substrate`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x silicon (Silicon); 1 x glass (Glass). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × silicon_substrate; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $13.6744; Kataloganker: $10.48; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; silicon (Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; glass (Glass): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: basic_chip (Basic Chip).

#### Solar Components — `solar_components`

Rezept `recipe.fabricator.solar_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x glass (Glass); 1 x aluminum (Aluminum); 1 x high_purity_silicon (High-Purity Silicon). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × solar_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $25.1875; Kataloganker: $20.15; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; glass (Glass): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; aluminum (Aluminum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: communication_satellite (Communication Satellite); satellite (Satellite); solar_array (Solar Array).

#### Stainless Components — `stainless_components`

Rezept `recipe.fabricator.stainless_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x stainless_steel (Stainless Steel). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 2.0 × stainless_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $13.6857; Kataloganker: $10.57; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 11; stainless_steel (Stainless Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: advanced_furnace (Advanced Furnace); steam_turbine (Steam Turbine); surgical_equipment (Surgical Equipment).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Steel Components — `steel_components`

Rezept `recipe.fabricator.steel_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x steel (Steel). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 2.0 × steel_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $12.0643; Kataloganker: $9.28; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1; steel (Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: cargo_vessel (Cargo Vessel); hydraulic_system (Hydraulic System); industrial_equipment (Industrial Equipment); mining_drill (Mining Drill); mining_equipment (Mining Equipment); processing_equipment (Processing Equipment); railway_track (Railway Track); reinforced_concrete (Reinforced Concrete).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Storage Components — `storage_components`

Rezept `recipe.fabricator.storage_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x aluminum (Aluminum); 2 x copper (Copper); 2 x high_purity_silicon (High-Purity Silicon); 1 x gold (Gold). Unterschiedliche Inputs: 4; gesamte Inputmenge: 7.
Output: 1.0 × storage_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $68.725; Kataloganker: $54.98; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; aluminum (Aluminum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gold (Gold): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: grid_storage_system (Grid Storage System).

#### Structural Components — `structural_components`

Rezept `recipe.fabricator.structural_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 3 x steel (Steel); 1 x cement (Cement). Unterschiedliche Inputs: 2; gesamte Inputmenge: 4.
Output: 2.0 × structural_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $19.1551; Kataloganker: $15.23; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 3; steel (Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; cement (Cement): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: cellular_base_station (Cellular Base Station); cnc_machine (CNC Machine); construction_frames (Construction Frames); container_ship (Container Ship); data_center_module (Data Center Module); engineered_structures (Engineered Structures); excavator (Excavator); freight_railcar (Freight Railcar); heavy_machinery (Heavy Machinery); industrial_hall_modules (Industrial Hall Modules); nuclear_reactor (Nuclear Reactor); prefabricated_structures (Prefabricated Structures); server_rack (Server Rack); structural_systems (Structural Systems); wind_turbine (Wind Turbine).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Sweetener Components — `sweetener_components`

Rezept `recipe.fabricator.sweetener_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x raw_sugar (Raw Sugar); 1 x soy_oil (Soy Oil); 1 x organic_feedstock (Organic Feedstock). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × sweetener_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $10.4338; Kataloganker: $8.01; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4; raw_sugar (Raw Sugar): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; soy_oil (Soy Oil): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; organic_feedstock (Organic Feedstock): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: packaged_food (Packaged Food).

#### Technical Textile — `technical_textile`

Rezept `recipe.fabricator.technical_textile`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x cotton_fiber (Cotton Fiber); 1 x polymer (Polymer). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 2.0 × technical_textile; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $5.1275; Kataloganker: $3.85; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; cotton_fiber (Cotton Fiber): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; polymer (Polymer): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: clothing (Clothing); industrial_clothing (Industrial Clothing); workwear (Workwear).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Telecom Components — `telecom_components`

Rezept `recipe.fabricator.telecom_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x copper (Copper); 2 x high_purity_silicon (High-Purity Silicon); 1 x gold (Gold); 1 x rare_earth_metals (Rare Earth Metals). Unterschiedliche Inputs: 4; gesamte Inputmenge: 6.
Output: 1.0 × telecom_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $75.3125; Kataloganker: $60.25; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; high_purity_silicon (High-Purity Silicon): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gold (Gold): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; rare_earth_metals (Rare Earth Metals): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: cellular_base_station (Cellular Base Station); communication_cable (Communication Cable); communication_satellite (Communication Satellite); navigation_satellite (Navigation Satellite); radio_transceiver (Radio Transceiver); router (Router); satellite (Satellite).

#### Tire Components — `tire_components`

Rezept `recipe.fabricator.tire_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x processed_rubber (Processed Rubber); 1 x carbon_fiber (Carbon Fiber). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × tire_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $27.3219; Kataloganker: $21.54; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; processed_rubber (Processed Rubber): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; carbon_fiber (Carbon Fiber): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: commercial_truck (Commercial Truck); industrial_rubber_products (Industrial Rubber Products); industrial_seals (Industrial Seals); industrial_tires (Industrial Tires); protective_clothing (Protective Clothing); safety_equipment (Safety Equipment).

#### Titanium Components — `titanium_components`

Rezept `recipe.fabricator.titanium_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x titanium (Titanium). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 2.0 × titanium_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $8.3688; Kataloganker: $6.35; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; titanium (Titanium): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: rocket_engine (Rocket Engine).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

#### Transformer Components — `transformer_components`

Rezept `recipe.fabricator.transformer_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x copper (Copper); 1 x steel (Steel). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × transformer_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $18.75; Kataloganker: $15.0; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 1; copper (Copper): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; steel (Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: high_voltage_equipment (High-Voltage Equipment); transformer (Transformer).

#### Turbine Components — `turbine_components`

Rezept `recipe.fabricator.turbine_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x nickel_alloy (Nickel Alloy); 1 x titanium (Titanium). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × turbine_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $22.3538; Kataloganker: $17.51; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; nickel_alloy (Nickel Alloy): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; titanium (Titanium): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: advanced_aircraft (Advanced Aircraft); combustion_vehicle (Combustion Vehicle); commercial_aircraft (Commercial Aircraft); diesel_locomotive (Diesel Locomotive); gas_turbine (Gas Turbine); high_speed_vessel (High-Speed Vessel); industrial_generator (Industrial Generator); jet_engine (Jet Engine); launch_vehicle (Launch Vehicle); rocket_engine (Rocket Engine); steam_turbine (Steam Turbine); workboat (Workboat).

#### Vehicle Components — `vehicle_components`

Rezept `recipe.fabricator.vehicle_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x steel (Steel); 1 x aluminum (Aluminum); 1 x processed_rubber (Processed Rubber). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × vehicle_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $20.0517; Kataloganker: $15.97; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; steel (Steel): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; aluminum (Aluminum): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; processed_rubber (Processed Rubber): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: autonomous_mobile_robot (Autonomous Mobile Robot); autonomous_vehicle (Autonomous Vehicle); combustion_vehicle (Combustion Vehicle); commercial_truck (Commercial Truck); electric_vehicle (Electric Vehicle); excavator (Excavator); premium_electric_vehicle (Premium Electric Vehicle); utility_vehicle (Utility Vehicle).

#### Wind Components — `wind_components`

Rezept `recipe.fabricator.wind_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 1 x nickel_alloy (Nickel Alloy); 1 x titanium (Titanium); 1 x carbon_fiber (Carbon Fiber); 1 x industrial_resin (Industrial Resin). Unterschiedliche Inputs: 4; gesamte Inputmenge: 4.
Output: 1.0 × wind_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $49.125; Kataloganker: $39.3; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; nickel_alloy (Nickel Alloy): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; titanium (Titanium): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; carbon_fiber (Carbon Fiber): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; industrial_resin (Industrial Resin): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: wind_turbine (Wind Turbine).

#### Wooden Components — `wooden_components`

Rezept `recipe.fabricator.wooden_components`; Maschine `machine.fabricator` (Fabricator); Common-Kaufpreis $225.0.
Inputs/Zyklus: 2 x lumber (Lumber); 1 x treated_lumber (Treated Lumber). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 2.0 × wooden_components; Zyklus: 6.0 s; Leistung: 10.0 MW; MK1/Common: 20.0 U/min.
Basisverkaufspreis: $4.7823; Kataloganker: $3.33; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; lumber (Lumber): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; treated_lumber (Treated Lumber): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: cargo_pallets (Cargo Pallets); commercial_furniture (Commercial Furniture); construction_frames (Construction Frames); construction_materials (Construction Materials); industrial_packaging (Industrial Packaging); prefabricated_structures (Prefabricated Structures).
**Rezeptabweichung von Maschinenbasis:** Basisoutput 1.0, Basiszyklus 6.0 s, Basisleistung 10.0 MW; wirksame Werte siehe oben.

### Assembly (150)

#### AI Accelerator — `ai_accelerator`

Rezept `recipe.assembler.ai_accelerator`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x ai_compute_components (AI Compute Components); 1 x power_electronics (Power Electronics). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × ai_accelerator; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $226.1625; Kataloganker: $180.93; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; ai_compute_components (AI Compute Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; power_electronics (Power Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### AI Server — `ai_server`

Rezept `recipe.assembler.ai_server`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x ai_compute_components (AI Compute Components); 1 x server_components (Server Components); 1 x network_components (Network Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × ai_server; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $299.1375; Kataloganker: $239.31; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; ai_compute_components (AI Compute Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; server_components (Server Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; network_components (Network Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Advanced Aircraft — `advanced_aircraft`

Rezept `recipe.assembler.advanced_aircraft`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x aerospace_components (Aerospace Components); 1 x turbine_components (Turbine Components); 1 x avionics_components (Avionics Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × advanced_aircraft; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $250.4; Kataloganker: $200.32; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; aerospace_components (Aerospace Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; turbine_components (Turbine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; avionics_components (Avionics Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Advanced Fertilizer — `advanced_fertilizer`

Rezept `recipe.assembler.advanced_fertilizer`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x fertilizer_components (Fertilizer Components); 1 x agricultural_chemicals (Agricultural Chemicals). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × advanced_fertilizer; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $30.073; Kataloganker: $22.82; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; fertilizer_components (Fertilizer Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; agricultural_chemicals (Agricultural Chemicals): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Advanced Furnace — `advanced_furnace`

Rezept `recipe.assembler.advanced_furnace`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x stainless_components (Stainless Components); 1 x ceramic_components (Ceramic Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × advanced_furnace; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $124.0875; Kataloganker: $99.27; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; stainless_components (Stainless Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; ceramic_components (Ceramic Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Advanced Industrial Robot — `advanced_industrial_robot`

Rezept `recipe.assembler.advanced_industrial_robot`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x autonomous_components (Autonomous Components); 1 x sensor_components (Sensor Components); 1 x ai_compute_components (AI Compute Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × advanced_industrial_robot; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $242.0625; Kataloganker: $193.65; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; autonomous_components (Autonomous Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; ai_compute_components (AI Compute Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Advanced Medical Equipment — `advanced_medical_equipment`

Rezept `recipe.assembler.advanced_medical_equipment`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x medical_components (Medical Components); 1 x precision_components (Precision Components); 1 x sensor_components (Sensor Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 4; gesamte Inputmenge: 5.
Output: 1.0 × advanced_medical_equipment; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $313.825; Kataloganker: $251.06; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; medical_components (Medical Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; precision_components (Precision Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Advanced Protective Equipment — `advanced_protective_equipment`

Rezept `recipe.assembler.advanced_protective_equipment`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x industrial_fabric (Industrial Fabric); 1 x sensor_components (Sensor Components); 1 x composite_components (Composite Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × advanced_protective_equipment; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $143.2638; Kataloganker: $109.43; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; industrial_fabric (Industrial Fabric): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; composite_components (Composite Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Advanced Semiconductor Equipment — `advanced_semiconductor_equipment`

Rezept `recipe.assembler.advanced_semiconductor_equipment`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x precision_components (Precision Components); 1 x control_electronics (Control Electronics); 1 x ceramic_components (Ceramic Components); 1 x sensor_components (Sensor Components). Unterschiedliche Inputs: 4; gesamte Inputmenge: 5.
Output: 1.0 × advanced_semiconductor_equipment; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $243.2375; Kataloganker: $194.59; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; precision_components (Precision Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; ceramic_components (Ceramic Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Animal Feed — `animal_feed`

Rezept `recipe.assembler.animal_feed`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x food_ingredients (Food Ingredients); 1 x nutrition_components (Nutrition Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × animal_feed; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $21.509; Kataloganker: $16.09; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4; food_ingredients (Food Ingredients): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; nutrition_components (Nutrition Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Autonomous Aircraft — `autonomous_aircraft`

Rezept `recipe.assembler.autonomous_aircraft`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x aerospace_components (Aerospace Components); 1 x avionics_components (Avionics Components); 1 x autonomous_components (Autonomous Components); 1 x sensor_components (Sensor Components). Unterschiedliche Inputs: 4; gesamte Inputmenge: 5.
Output: 1.0 × autonomous_aircraft; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $355.7; Kataloganker: $284.56; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; aerospace_components (Aerospace Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; avionics_components (Avionics Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; autonomous_components (Autonomous Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Autonomous Cargo Ship — `autonomous_cargo_ship`

Rezept `recipe.assembler.autonomous_cargo_ship`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x marine_components (Marine Components); 1 x autonomous_components (Autonomous Components); 1 x sensor_components (Sensor Components); 1 x network_components (Network Components). Unterschiedliche Inputs: 4; gesamte Inputmenge: 5.
Output: 1.0 × autonomous_cargo_ship; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $362.55; Kataloganker: $290.04; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; marine_components (Marine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; autonomous_components (Autonomous Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; network_components (Network Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Autonomous Control System — `autonomous_control_system`

Rezept `recipe.assembler.autonomous_control_system`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x control_electronics (Control Electronics); 2 x processor_components (Processor Components); 1 x magnetic_components (Magnetic Components); 1 x power_electronics (Power Electronics). Unterschiedliche Inputs: 4; gesamte Inputmenge: 6.
Output: 1.0 × autonomous_control_system; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $497.4; Kataloganker: $397.92; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; processor_components (Processor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; magnetic_components (Magnetic Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; power_electronics (Power Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Autonomous Freight Train — `autonomous_freight_train`

Rezept `recipe.assembler.autonomous_freight_train`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x rail_components (Rail Components); 1 x autonomous_components (Autonomous Components); 1 x network_components (Network Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × autonomous_freight_train; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $267.6; Kataloganker: $214.08; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; rail_components (Rail Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; autonomous_components (Autonomous Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; network_components (Network Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Autonomous Mobile Robot — `autonomous_mobile_robot`

Rezept `recipe.assembler.autonomous_mobile_robot`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x vehicle_components (Vehicle Components); 1 x sensor_components (Sensor Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × autonomous_mobile_robot; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $196.6; Kataloganker: $157.28; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; vehicle_components (Vehicle Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Autonomous Vehicle — `autonomous_vehicle`

Rezept `recipe.assembler.autonomous_vehicle`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x vehicle_components (Vehicle Components); 1 x autonomous_components (Autonomous Components); 1 x sensor_components (Sensor Components); 1 x ai_compute_components (AI Compute Components). Unterschiedliche Inputs: 4; gesamte Inputmenge: 4.
Output: 1.0 × autonomous_vehicle; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $229.85; Kataloganker: $183.88; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; vehicle_components (Vehicle Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; autonomous_components (Autonomous Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; ai_compute_components (AI Compute Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Bakery Products — `bakery_products`

Rezept `recipe.assembler.bakery_products`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x food_ingredients (Food Ingredients); 1 x packaging_components (Packaging Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × bakery_products; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $17.0134; Kataloganker: $12.44; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; food_ingredients (Food Ingredients): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; packaging_components (Packaging Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Basic Chip — `basic_chip`

Rezept `recipe.assembler.basic_chip`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x semiconductor_components (Semiconductor Components); 1 x silicon_substrate (Silicon Substrate); 1 x copper_wire (Copper Wire). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × basic_chip; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $87.1; Kataloganker: $69.68; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; semiconductor_components (Semiconductor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; silicon_substrate (Silicon Substrate): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; copper_wire (Copper Wire): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Bio-Based Chemicals — `bio_based_chemicals`

Rezept `recipe.assembler.bio_based_chemicals`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x bio_material_components (Bio-Material Components); 1 x chemical_components (Chemical Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × bio_based_chemicals; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $37.0396; Kataloganker: $25.96; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; bio_material_components (Bio-Material Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; chemical_components (Chemical Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Biodiesel — `biodiesel`

Rezept `recipe.assembler.biodiesel`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x biodiesel_feedstock (Biodiesel Feedstock). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 1.0 × biodiesel; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $29.9119; Kataloganker: $22.33; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; biodiesel_feedstock (Biodiesel Feedstock): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Biofuel — `biofuel`

Rezept `recipe.assembler.biofuel`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x ethanol_components (Ethanol Components); 1 x chemical_components (Chemical Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × biofuel; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $29.9804; Kataloganker: $21.91; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; ethanol_components (Ethanol Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; chemical_components (Chemical Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Bioplastic — `bioplastic`

Rezept `recipe.assembler.bioplastic`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x biopolymer (Biopolymer); 1 x bio_composite (Bio-Composite). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × bioplastic; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $32.9158; Kataloganker: $23.53; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; biopolymer (Biopolymer): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; bio_composite (Bio-Composite): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### CNC Machine — `cnc_machine`

Rezept `recipe.assembler.cnc_machine`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x precision_components (Precision Components); 1 x control_electronics (Control Electronics); 1 x structural_components (Structural Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × cnc_machine; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $174.675; Kataloganker: $139.74; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; precision_components (Precision Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; structural_components (Structural Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### CPU — `cpu`

Rezept `recipe.assembler.cpu`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x processor_components (Processor Components); 1 x memory_components (Memory Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × cpu; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $308.2375; Kataloganker: $246.59; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; processor_components (Processor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; memory_components (Memory Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Carbon Capture Plant — `carbon_capture_plant`

Rezept `recipe.assembler.carbon_capture_plant`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x pump_components (Pump Components); 1 x compressor_components (Compressor Components); 1 x chemical_components (Chemical Components); 1 x filtration_components (Filtration Components). Unterschiedliche Inputs: 4; gesamte Inputmenge: 4.
Output: 1.0 × carbon_capture_plant; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $72.4875; Kataloganker: $57.99; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; pump_components (Pump Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; compressor_components (Compressor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; chemical_components (Chemical Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; filtration_components (Filtration Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Cargo Aircraft — `cargo_aircraft`

Rezept `recipe.assembler.cargo_aircraft`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 3 x aerospace_components (Aerospace Components); 1 x avionics_components (Avionics Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 4.
Output: 1.0 × cargo_aircraft; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $257.025; Kataloganker: $205.62; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; aerospace_components (Aerospace Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; avionics_components (Avionics Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Cargo Pallets — `cargo_pallets`

Rezept `recipe.assembler.cargo_pallets`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x wooden_components (Wooden Components). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 1.0 × cargo_pallets; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $12.0608; Kataloganker: $7.86; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; wooden_components (Wooden Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Cargo Vessel — `cargo_vessel`

Rezept `recipe.assembler.cargo_vessel`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 3 x marine_components (Marine Components); 1 x steel_components (Steel Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 4.
Output: 1.0 × cargo_vessel; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $121.925; Kataloganker: $97.54; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; marine_components (Marine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; steel_components (Steel Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Cellular Base Station — `cellular_base_station`

Rezept `recipe.assembler.cellular_base_station`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x telecom_components (Telecom Components); 1 x structural_components (Structural Components); 1 x power_electronics (Power Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × cellular_base_station; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $288.375; Kataloganker: $230.7; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; telecom_components (Telecom Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; structural_components (Structural Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; power_electronics (Power Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Clothing — `clothing`

Rezept `recipe.assembler.clothing`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x technical_textile (Technical Textile). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 1.0 × clothing; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $12.8794; Kataloganker: $9.09; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; technical_textile (Technical Textile): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Combustion Vehicle — `combustion_vehicle`

Rezept `recipe.assembler.combustion_vehicle`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x vehicle_components (Vehicle Components); 1 x turbine_components (Turbine Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × combustion_vehicle; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $74.4875; Kataloganker: $59.59; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; vehicle_components (Vehicle Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; turbine_components (Turbine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Commercial Aircraft — `commercial_aircraft`

Rezept `recipe.assembler.commercial_aircraft`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 3 x aerospace_components (Aerospace Components); 1 x avionics_components (Avionics Components); 1 x turbine_components (Turbine Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 5.
Output: 1.0 × commercial_aircraft; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $289.275; Kataloganker: $231.42; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; aerospace_components (Aerospace Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; avionics_components (Avionics Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; turbine_components (Turbine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Commercial Furniture — `commercial_furniture`

Rezept `recipe.assembler.commercial_furniture`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x wooden_components (Wooden Components); 1 x industrial_fabric (Industrial Fabric). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × commercial_furniture; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $28.3975; Kataloganker: $16.63; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; wooden_components (Wooden Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; industrial_fabric (Industrial Fabric): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Commercial Truck — `commercial_truck`

Rezept `recipe.assembler.commercial_truck`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x vehicle_components (Vehicle Components); 3 x tire_components (Tire Components); 2 x control_electronics (Control Electronics); 1 x sensor_components (Sensor Components). Unterschiedliche Inputs: 4; gesamte Inputmenge: 8.
Output: 1.0 × commercial_truck; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $417.0625; Kataloganker: $333.65; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; vehicle_components (Vehicle Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; tire_components (Tire Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Communication Cable — `communication_cable`

Rezept `recipe.assembler.communication_cable`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x insulated_wire (Insulated Wire); 1 x telecom_components (Telecom Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × communication_cable; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $107.8875; Kataloganker: $86.31; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; insulated_wire (Insulated Wire): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; telecom_components (Telecom Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Communication Satellite — `communication_satellite`

Rezept `recipe.assembler.communication_satellite`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x aerospace_components (Aerospace Components); 1 x solar_components (Solar Components); 1 x telecom_components (Telecom Components); 1 x network_components (Network Components). Unterschiedliche Inputs: 4; gesamte Inputmenge: 4.
Output: 1.0 × communication_satellite; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $325.725; Kataloganker: $260.58; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; aerospace_components (Aerospace Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; solar_components (Solar Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; telecom_components (Telecom Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; network_components (Network Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Compute Node — `compute_node`

Rezept `recipe.assembler.compute_node`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x processor_components (Processor Components); 1 x memory_components (Memory Components); 1 x network_components (Network Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × compute_node; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $471.3625; Kataloganker: $377.09; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; processor_components (Processor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; memory_components (Memory Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; network_components (Network Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Construction Frames — `construction_frames`

Rezept `recipe.assembler.construction_frames`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x wooden_components (Wooden Components); 1 x structural_components (Structural Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × construction_frames; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $34.4596; Kataloganker: $26.38; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; wooden_components (Wooden Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; structural_components (Structural Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Construction Materials — `construction_materials`

Rezept `recipe.assembler.construction_materials`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x concrete_components (Concrete Components); 1 x wooden_components (Wooden Components); 1 x asphalt_components (Asphalt Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × construction_materials; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $43.478; Kataloganker: $34.14; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; concrete_components (Concrete Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; wooden_components (Wooden Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; asphalt_components (Asphalt Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Container Ship — `container_ship`

Rezept `recipe.assembler.container_ship`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 3 x marine_components (Marine Components); 1 x structural_components (Structural Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 5.
Output: 1.0 × container_ship; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $221.8625; Kataloganker: $177.49; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; marine_components (Marine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; structural_components (Structural Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Crop Protection Products — `crop_protection_products`

Rezept `recipe.assembler.crop_protection_products`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x agricultural_chemicals (Agricultural Chemicals); 1 x chemical_components (Chemical Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × crop_protection_products; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $42.8906; Kataloganker: $33.31; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; agricultural_chemicals (Agricultural Chemicals): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; chemical_components (Chemical Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Data Center Module — `data_center_module`

Rezept `recipe.assembler.data_center_module`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x server_components (Server Components); 1 x grid_storage_components (Grid Storage Components); 1 x structural_components (Structural Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × data_center_module; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $180.7625; Kataloganker: $144.61; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; server_components (Server Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; grid_storage_components (Grid Storage Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; structural_components (Structural Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Desalination Plant — `desalination_plant`

Rezept `recipe.assembler.desalination_plant`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x filtration_components (Filtration Components); 1 x membrane_components (Membrane Components); 1 x pump_components (Pump Components); 1 x power_electronics (Power Electronics). Unterschiedliche Inputs: 4; gesamte Inputmenge: 4.
Output: 1.0 × desalination_plant; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $134.5375; Kataloganker: $107.63; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; filtration_components (Filtration Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; membrane_components (Membrane Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; pump_components (Pump Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; power_electronics (Power Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Diagnostic System — `diagnostic_system`

Rezept `recipe.assembler.diagnostic_system`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x medical_components (Medical Components); 1 x computing_components (Computing Components); 1 x sensor_components (Sensor Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × diagnostic_system; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $307.85; Kataloganker: $246.28; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 20; medical_components (Medical Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; computing_components (Computing Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Diesel Locomotive — `diesel_locomotive`

Rezept `recipe.assembler.diesel_locomotive`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x rail_components (Rail Components); 1 x turbine_components (Turbine Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × diesel_locomotive; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $94.4875; Kataloganker: $75.59; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; rail_components (Rail Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; turbine_components (Turbine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Electric Locomotive — `electric_locomotive`

Rezept `recipe.assembler.electric_locomotive`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x rail_components (Rail Components); 1 x motor_components (Motor Components); 1 x power_electronics (Power Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × electric_locomotive; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $178.7375; Kataloganker: $142.99; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; rail_components (Rail Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; motor_components (Motor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; power_electronics (Power Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Electric Motor — `electric_motor`

Rezept `recipe.assembler.electric_motor`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x motor_components (Motor Components); 1 x electrical_components (Electrical Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × electric_motor; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $68.45; Kataloganker: $54.76; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15; motor_components (Motor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; electrical_components (Electrical Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Electric Vehicle — `electric_vehicle`

Rezept `recipe.assembler.electric_vehicle`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x vehicle_components (Vehicle Components); 2 x battery_components (Battery Components); 1 x motor_components (Motor Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × electric_vehicle; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $114.5933; Kataloganker: $82.15; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15; vehicle_components (Vehicle Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; battery_components (Battery Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; motor_components (Motor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Electrical Cable — `electrical_cable`

Rezept `recipe.assembler.electrical_cable`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x insulated_wire (Insulated Wire); 1 x copper_wire (Copper Wire). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × electrical_cable; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $21.8126; Kataloganker: $16.98; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; insulated_wire (Insulated Wire): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; copper_wire (Copper Wire): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Engineered Structures — `engineered_structures`

Rezept `recipe.assembler.engineered_structures`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x structural_components (Structural Components); 1 x composite_components (Composite Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × engineered_structures; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $76.2875; Kataloganker: $61.03; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; structural_components (Structural Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; composite_components (Composite Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Excavator — `excavator`

Rezept `recipe.assembler.excavator`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x vehicle_components (Vehicle Components); 1 x hydraulic_components (Hydraulic Components); 1 x structural_components (Structural Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × excavator; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $94.675; Kataloganker: $75.74; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; vehicle_components (Vehicle Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; hydraulic_components (Hydraulic Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; structural_components (Structural Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Fertilizer — `fertilizer`

Rezept `recipe.assembler.fertilizer`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x fertilizer_components (Fertilizer Components); 1 x agricultural_mineral_components (Agricultural Mineral Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × fertilizer; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $30.9059; Kataloganker: $23.17; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; fertilizer_components (Fertilizer Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; agricultural_mineral_components (Agricultural Mineral Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Freight Railcar — `freight_railcar`

Rezept `recipe.assembler.freight_railcar`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x rail_components (Rail Components); 1 x structural_components (Structural Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × freight_railcar; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $91.05; Kataloganker: $72.84; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9; rail_components (Rail Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; structural_components (Structural Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Fusion Reactor Module — `fusion_reactor_module`

Rezept `recipe.assembler.fusion_reactor_module`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x reactor_components (Reactor Components); 1 x nuclear_fuel_components (Nuclear Fuel Components); 1 x electrolyzer_components (Electrolyzer Components); 1 x refractory_alloy_components (Refractory Alloy Components). Unterschiedliche Inputs: 4; gesamte Inputmenge: 4.
Output: 1.0 × fusion_reactor_module; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $165.5875; Kataloganker: $132.47; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 25; reactor_components (Reactor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; nuclear_fuel_components (Nuclear Fuel Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; electrolyzer_components (Electrolyzer Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; refractory_alloy_components (Refractory Alloy Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Gas Turbine — `gas_turbine`

Rezept `recipe.assembler.gas_turbine`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x turbine_components (Turbine Components); 1 x advanced_alloy_components (Advanced Alloy Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × gas_turbine; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $89.025; Kataloganker: $71.22; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; turbine_components (Turbine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; advanced_alloy_components (Advanced Alloy Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Gearbox — `gearbox`

Rezept `recipe.assembler.gearbox`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x gear_components (Gear Components); 1 x bearing_components (Bearing Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × gearbox; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $51.7012; Kataloganker: $41.34; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 11; gear_components (Gear Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; bearing_components (Bearing Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Grid Battery — `grid_battery`

Rezept `recipe.assembler.grid_battery`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x battery_components (Battery Components); 1 x battery_materials (Battery Materials); 1 x power_electronics (Power Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × grid_battery; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $156.9941; Kataloganker: $117.91; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; battery_components (Battery Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; battery_materials (Battery Materials): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; power_electronics (Power Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Grid Storage System — `grid_storage_system`

Rezept `recipe.assembler.grid_storage_system`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x storage_components (Storage Components); 1 x power_electronics (Power Electronics). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × grid_storage_system; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $243.7; Kataloganker: $194.96; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; storage_components (Storage Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; power_electronics (Power Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Heavy Machinery — `heavy_machinery`

Rezept `recipe.assembler.heavy_machinery`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x structural_components (Structural Components); 1 x hydraulic_components (Hydraulic Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × heavy_machinery; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $157.2375; Kataloganker: $125.79; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; structural_components (Structural Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; hydraulic_components (Hydraulic Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Heavy Mining Drill — `heavy_mining_drill`

Rezept `recipe.assembler.heavy_mining_drill`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x mining_components (Mining Components); 1 x hydraulic_components (Hydraulic Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × heavy_mining_drill; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $162.8; Kataloganker: $130.24; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; mining_components (Mining Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; hydraulic_components (Hydraulic Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### High-Speed Network System — `high_speed_network_system`

Rezept `recipe.assembler.high_speed_network_system`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 3 x network_components (Network Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 2; gesamte Inputmenge: 4.
Output: 1.0 × high_speed_network_system; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $547.1; Kataloganker: $437.68; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; network_components (Network Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### High-Speed Train — `high_speed_train`

Rezept `recipe.assembler.high_speed_train`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x rail_components (Rail Components); 1 x aerospace_components (Aerospace Components); 1 x power_electronics (Power Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × high_speed_train; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $188.1; Kataloganker: $150.48; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; rail_components (Rail Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; aerospace_components (Aerospace Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; power_electronics (Power Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### High-Speed Vessel — `high_speed_vessel`

Rezept `recipe.assembler.high_speed_vessel`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x marine_components (Marine Components); 1 x turbine_components (Turbine Components); 1 x composite_components (Composite Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × high_speed_vessel; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $94.7; Kataloganker: $75.76; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; marine_components (Marine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; turbine_components (Turbine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; composite_components (Composite Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### High-Voltage Equipment — `high_voltage_equipment`

Rezept `recipe.assembler.high_voltage_equipment`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x transformer_components (Transformer Components); 1 x power_electronics (Power Electronics); 1 x insulation_material (Insulation Material). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × high_voltage_equipment; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $108.35; Kataloganker: $86.68; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; transformer_components (Transformer Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; power_electronics (Power Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; insulation_material (Insulation Material): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Hydraulic System — `hydraulic_system`

Rezept `recipe.assembler.hydraulic_system`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x hydraulic_components (Hydraulic Components); 1 x steel_components (Steel Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × hydraulic_system; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $58.3051; Kataloganker: $45.91; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; hydraulic_components (Hydraulic Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; steel_components (Steel Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Hydrogen Electrolyzer — `hydrogen_electrolyzer`

Rezept `recipe.assembler.hydrogen_electrolyzer`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x electrolyzer_components (Electrolyzer Components); 1 x power_electronics (Power Electronics). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × hydrogen_electrolyzer; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $234.2125; Kataloganker: $187.37; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; electrolyzer_components (Electrolyzer Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; power_electronics (Power Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Chemicals — `industrial_chemicals`

Rezept `recipe.assembler.industrial_chemicals`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x chemical_components (Chemical Components); 1 x gas_handling_components (Gas Handling Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × industrial_chemicals; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $43.028; Kataloganker: $33.02; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; chemical_components (Chemical Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gas_handling_components (Gas Handling Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Clothing — `industrial_clothing`

Rezept `recipe.assembler.industrial_clothing`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x industrial_fabric (Industrial Fabric); 1 x technical_textile (Technical Textile). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × industrial_clothing; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $39.5605; Kataloganker: $21.85; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; industrial_fabric (Industrial Fabric): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; technical_textile (Technical Textile): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Compressor — `industrial_compressor`

Rezept `recipe.assembler.industrial_compressor`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x compressor_components (Compressor Components); 1 x motor_components (Motor Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × industrial_compressor; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $66.7674; Kataloganker: $53.26; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15; compressor_components (Compressor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; motor_components (Motor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Computer — `industrial_computer`

Rezept `recipe.assembler.industrial_computer`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x computing_components (Computing Components); 1 x display_components (Display Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × industrial_computer; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $369.5; Kataloganker: $295.6; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; computing_components (Computing Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; display_components (Display Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Controller — `industrial_controller`

Rezept `recipe.assembler.industrial_controller`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x control_electronics (Control Electronics); 1 x sensor_components (Sensor Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × industrial_controller; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $255.0125; Kataloganker: $204.01; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Crusher — `industrial_crusher`

Rezept `recipe.assembler.industrial_crusher`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x mining_components (Mining Components); 1 x gear_components (Gear Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × industrial_crusher; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $68.5337; Kataloganker: $54.68; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; mining_components (Mining Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; gear_components (Gear Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Cutting Machine — `industrial_cutting_machine`

Rezept `recipe.assembler.industrial_cutting_machine`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x precision_components (Precision Components); 1 x cutting_tooling (Cutting Tooling); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × industrial_cutting_machine; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $145.95; Kataloganker: $116.76; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; precision_components (Precision Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; cutting_tooling (Cutting Tooling): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Display — `industrial_display`

Rezept `recipe.assembler.industrial_display`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x glass_panels (Glass Panels); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × industrial_display; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $92.875; Kataloganker: $74.3; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; glass_panels (Glass Panels): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Drone — `industrial_drone`

Rezept `recipe.assembler.industrial_drone`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x aerospace_components (Aerospace Components); 1 x sensor_components (Sensor Components); 1 x battery_components (Battery Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × industrial_drone; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $148.6475; Kataloganker: $117.59; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; aerospace_components (Aerospace Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; battery_components (Battery Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Equipment — `industrial_equipment`

Rezept `recipe.assembler.industrial_equipment`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x steel_components (Steel Components); 1 x electrical_components (Electrical Components); 1 x iron_components (Iron Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × industrial_equipment; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $45.1603; Kataloganker: $35.77; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9; steel_components (Steel Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; electrical_components (Electrical Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; iron_components (Iron Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Generator — `industrial_generator`

Rezept `recipe.assembler.industrial_generator`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x motor_components (Motor Components); 1 x turbine_components (Turbine Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × industrial_generator; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $84.2125; Kataloganker: $67.37; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; motor_components (Motor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; turbine_components (Turbine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Glass Panels — `industrial_glass_panels`

Rezept `recipe.assembler.industrial_glass_panels`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x glass_panels (Glass Panels); 1 x aluminum_components (Aluminum Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × industrial_glass_panels; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $18.8529; Kataloganker: $13.83; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; glass_panels (Glass Panels): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; aluminum_components (Aluminum Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Hall Modules — `industrial_hall_modules`

Rezept `recipe.assembler.industrial_hall_modules`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x structural_components (Structural Components); 1 x galvanized_components (Galvanized Components); 1 x insulation_material (Insulation Material); 1 x glass_panels (Glass Panels). Unterschiedliche Inputs: 4; gesamte Inputmenge: 5.
Output: 1.0 × industrial_hall_modules; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $69.3125; Kataloganker: $55.45; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; structural_components (Structural Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; galvanized_components (Galvanized Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; insulation_material (Insulation Material): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; glass_panels (Glass Panels): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Insulation — `industrial_insulation`

Rezept `recipe.assembler.industrial_insulation`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x insulation_material (Insulation Material); 1 x fiber_components (Fiber Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × industrial_insulation; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $30.8703; Kataloganker: $21.51; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; insulation_material (Insulation Material): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; fiber_components (Fiber Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Inverter — `industrial_inverter`

Rezept `recipe.assembler.industrial_inverter`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x power_electronics (Power Electronics); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × industrial_inverter; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $242.6; Kataloganker: $194.08; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; power_electronics (Power Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Laser — `industrial_laser`

Rezept `recipe.assembler.industrial_laser`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x precision_components (Precision Components); 1 x semiconductor_components (Semiconductor Components); 1 x magnetic_components (Magnetic Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × industrial_laser; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $118.7375; Kataloganker: $94.99; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; precision_components (Precision Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; semiconductor_components (Semiconductor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; magnetic_components (Magnetic Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Packaging — `industrial_packaging`

Rezept `recipe.assembler.industrial_packaging`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x packaging_components (Packaging Components); 1 x wooden_components (Wooden Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × industrial_packaging; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $24.134; Kataloganker: $17.94; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; packaging_components (Packaging Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; wooden_components (Wooden Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Plastics — `industrial_plastics`

Rezept `recipe.assembler.industrial_plastics`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x packaging_components (Packaging Components); 1 x composite_components (Composite Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × industrial_plastics; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $48.5453; Kataloganker: $38.26; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; packaging_components (Packaging Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; composite_components (Composite Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Pump — `industrial_pump`

Rezept `recipe.assembler.industrial_pump`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x pump_components (Pump Components); 1 x motor_components (Motor Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × industrial_pump; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $70.0147; Kataloganker: $55.98; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15; pump_components (Pump Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; motor_components (Motor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Relay — `industrial_relay`

Rezept `recipe.assembler.industrial_relay`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x electrical_components (Electrical Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × industrial_relay; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $97.0625; Kataloganker: $77.65; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; electrical_components (Electrical Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Robot — `industrial_robot`

Rezept `recipe.assembler.industrial_robot`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x precision_components (Precision Components); 1 x motor_components (Motor Components); 1 x control_electronics (Control Electronics); 1 x sensor_components (Sensor Components). Unterschiedliche Inputs: 4; gesamte Inputmenge: 5.
Output: 1.0 × industrial_robot; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $269.95; Kataloganker: $215.96; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; precision_components (Precision Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; motor_components (Motor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Rubber Products — `industrial_rubber_products`

Rezept `recipe.assembler.industrial_rubber_products`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x tire_components (Tire Components); 1 x rubber_blend_components (Rubber Blend Components); 1 x chemical_components (Chemical Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × industrial_rubber_products; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $103.2625; Kataloganker: $82.61; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; tire_components (Tire Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; rubber_blend_components (Rubber Blend Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; chemical_components (Chemical Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Seals — `industrial_seals`

Rezept `recipe.assembler.industrial_seals`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x tire_components (Tire Components); 1 x precision_components (Precision Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × industrial_seals; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $63.3125; Kataloganker: $50.65; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; tire_components (Tire Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; precision_components (Precision Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Sensor — `industrial_sensor`

Rezept `recipe.assembler.industrial_sensor`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x sensor_components (Sensor Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × industrial_sensor; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $250.6375; Kataloganker: $200.51; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Industrial Tires — `industrial_tires`

Rezept `recipe.assembler.industrial_tires`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 3 x tire_components (Tire Components). Unterschiedliche Inputs: 1; gesamte Inputmenge: 3.
Output: 1.0 × industrial_tires; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $96.6899; Kataloganker: $76.25; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; tire_components (Tire Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Jet Engine — `jet_engine`

Rezept `recipe.assembler.jet_engine`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 3 x turbine_components (Turbine Components). Unterschiedliche Inputs: 1; gesamte Inputmenge: 3.
Output: 1.0 × jet_engine; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $79.2647; Kataloganker: $61.99; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; turbine_components (Turbine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Laboratory Equipment — `laboratory_equipment`

Rezept `recipe.assembler.laboratory_equipment`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x glass_panels (Glass Panels); 1 x precision_components (Precision Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × laboratory_equipment; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $126.3; Kataloganker: $101.04; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; glass_panels (Glass Panels): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; precision_components (Precision Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Launch Vehicle — `launch_vehicle`

Rezept `recipe.assembler.launch_vehicle`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x aerospace_components (Aerospace Components); 1 x turbine_components (Turbine Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × launch_vehicle; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $192.9375; Kataloganker: $154.35; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; aerospace_components (Aerospace Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; turbine_components (Turbine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Light Aircraft — `light_aircraft`

Rezept `recipe.assembler.light_aircraft`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x aerospace_components (Aerospace Components); 1 x avionics_components (Avionics Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × light_aircraft; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $218.9375; Kataloganker: $175.15; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; aerospace_components (Aerospace Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; avionics_components (Avionics Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Machine Vision System — `machine_vision_system`

Rezept `recipe.assembler.machine_vision_system`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x sensor_components (Sensor Components); 1 x computing_components (Computing Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × machine_vision_system; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $332.725; Kataloganker: $266.18; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; computing_components (Computing Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Medical Monitor — `medical_monitor`

Rezept `recipe.assembler.medical_monitor`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x display_components (Display Components); 1 x sensor_components (Sensor Components); 1 x medical_components (Medical Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × medical_monitor; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $168.875; Kataloganker: $135.1; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 20; display_components (Display Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; medical_components (Medical Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Memory Module — `memory_module`

Rezept `recipe.assembler.memory_module`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x memory_components (Memory Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × memory_module; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $289.7375; Kataloganker: $231.79; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; memory_components (Memory Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Microchip — `microchip`

Rezept `recipe.assembler.microchip`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x semiconductor_die (Semiconductor Die); 1 x semiconductor_components (Semiconductor Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × microchip; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $147.55; Kataloganker: $118.04; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; semiconductor_die (Semiconductor Die): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; semiconductor_components (Semiconductor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Microcontroller — `microcontroller`

Rezept `recipe.assembler.microcontroller`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x semiconductor_die (Semiconductor Die); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × microcontroller; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $168.55; Kataloganker: $134.84; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; semiconductor_die (Semiconductor Die): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Mining Drill — `mining_drill`

Rezept `recipe.assembler.mining_drill`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x mining_components (Mining Components); 1 x motor_components (Motor Components); 1 x steel_components (Steel Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × mining_drill; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $69.9875; Kataloganker: $55.99; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; mining_components (Mining Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; motor_components (Motor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; steel_components (Steel Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Mining Equipment — `mining_equipment`

Rezept `recipe.assembler.mining_equipment`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x mining_components (Mining Components); 1 x steel_components (Steel Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × mining_equipment; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $65.8929; Kataloganker: $52.25; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; mining_components (Mining Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; steel_components (Steel Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Navigation Satellite — `navigation_satellite`

Rezept `recipe.assembler.navigation_satellite`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x aerospace_components (Aerospace Components); 1 x sensor_components (Sensor Components); 1 x telecom_components (Telecom Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × navigation_satellite; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $215.3125; Kataloganker: $172.25; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; aerospace_components (Aerospace Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; telecom_components (Telecom Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Network Switch — `network_switch`

Rezept `recipe.assembler.network_switch`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x network_components (Network Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × network_switch; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $393.55; Kataloganker: $314.84; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; network_components (Network Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Nuclear Fuel Assembly — `nuclear_fuel_assembly`

Rezept `recipe.assembler.nuclear_fuel_assembly`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x nuclear_fuel_components (Nuclear Fuel Components); 1 x shielding_components (Shielding Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × nuclear_fuel_assembly; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $60.288; Kataloganker: $47.79; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 25; nuclear_fuel_components (Nuclear Fuel Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; shielding_components (Shielding Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Nuclear Reactor — `nuclear_reactor`

Rezept `recipe.assembler.nuclear_reactor`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x reactor_components (Reactor Components); 1 x nuclear_fuel_components (Nuclear Fuel Components); 1 x control_electronics (Control Electronics); 1 x structural_components (Structural Components). Unterschiedliche Inputs: 4; gesamte Inputmenge: 5.
Output: 1.0 × nuclear_reactor; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $164.3875; Kataloganker: $131.51; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 25; reactor_components (Reactor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; nuclear_fuel_components (Nuclear Fuel Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; structural_components (Structural Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Orbital Vehicle — `orbital_vehicle`

Rezept `recipe.assembler.orbital_vehicle`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x aerospace_components (Aerospace Components); 1 x avionics_components (Avionics Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × orbital_vehicle; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $311.725; Kataloganker: $249.38; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; aerospace_components (Aerospace Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; avionics_components (Avionics Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Packaged Beverages — `packaged_beverages`

Rezept `recipe.assembler.packaged_beverages`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x nutrition_components (Nutrition Components); 1 x packaging_components (Packaging Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × packaged_beverages; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $23.0498; Kataloganker: $17.58; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; nutrition_components (Nutrition Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; packaging_components (Packaging Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Packaged Food — `packaged_food`

Rezept `recipe.assembler.packaged_food`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x food_ingredients (Food Ingredients); 1 x sweetener_components (Sweetener Components); 1 x packaging_components (Packaging Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × packaged_food; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $29.2144; Kataloganker: $22.55; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; food_ingredients (Food Ingredients): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sweetener_components (Sweetener Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; packaging_components (Packaging Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Packaged Meals — `packaged_meals`

Rezept `recipe.assembler.packaged_meals`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x food_ingredients (Food Ingredients); 2 x nutrition_components (Nutrition Components); 1 x packaging_components (Packaging Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 5.
Output: 1.0 × packaged_meals; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $43.6685; Kataloganker: $34.37; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; food_ingredients (Food Ingredients): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; nutrition_components (Nutrition Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; packaging_components (Packaging Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Packaged Nutrition — `packaged_nutrition`

Rezept `recipe.assembler.packaged_nutrition`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x nutrition_components (Nutrition Components); 1 x packaging_components (Packaging Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × packaged_nutrition; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $36.3705; Kataloganker: $28.2; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; nutrition_components (Nutrition Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; packaging_components (Packaging Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Packaging Materials — `packaging_materials`

Rezept `recipe.assembler.packaging_materials`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x packaging_components (Packaging Components). Unterschiedliche Inputs: 1; gesamte Inputmenge: 2.
Output: 1.0 × packaging_materials; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $18.5483; Kataloganker: $13.64; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; packaging_components (Packaging Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Power Cable — `power_cable`

Rezept `recipe.assembler.power_cable`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x insulated_wire (Insulated Wire); 1 x aluminum_components (Aluminum Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × power_cable; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $22.3277; Kataloganker: $17.28; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; insulated_wire (Insulated Wire): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; aluminum_components (Aluminum Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Precision Motor — `precision_motor`

Rezept `recipe.assembler.precision_motor`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x motor_components (Motor Components); 1 x precision_components (Precision Components); 1 x magnetic_components (Magnetic Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × precision_motor; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $81.4375; Kataloganker: $65.15; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; motor_components (Motor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; precision_components (Precision Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; magnetic_components (Magnetic Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Prefabricated Structures — `prefabricated_structures`

Rezept `recipe.assembler.prefabricated_structures`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x structural_components (Structural Components); 1 x wooden_components (Wooden Components); 1 x concrete_components (Concrete Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × prefabricated_structures; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $39.0685; Kataloganker: $31.13; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; structural_components (Structural Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; wooden_components (Wooden Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; concrete_components (Concrete Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Premium Electric Vehicle — `premium_electric_vehicle`

Rezept `recipe.assembler.premium_electric_vehicle`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x vehicle_components (Vehicle Components); 1 x advanced_cell_components (Advanced Cell Components); 1 x display_components (Display Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × premium_electric_vehicle; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $84.5783; Kataloganker: $66.51; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 15; vehicle_components (Vehicle Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; advanced_cell_components (Advanced Cell Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; display_components (Display Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Processed Food — `processed_food`

Rezept `recipe.assembler.processed_food`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x food_ingredients (Food Ingredients); 1 x nutrition_components (Nutrition Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × processed_food; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $21.509; Kataloganker: $16.09; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 4; food_ingredients (Food Ingredients): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; nutrition_components (Nutrition Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Processing Equipment — `processing_equipment`

Rezept `recipe.assembler.processing_equipment`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x steel_components (Steel Components); 1 x pump_components (Pump Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × processing_equipment; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $137.75; Kataloganker: $110.2; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; steel_components (Steel Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; pump_components (Pump Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Protective Clothing — `protective_clothing`

Rezept `recipe.assembler.protective_clothing`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x industrial_fabric (Industrial Fabric); 1 x tire_components (Tire Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × protective_clothing; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $65.5103; Kataloganker: $43.16; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; industrial_fabric (Industrial Fabric): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; tire_components (Tire Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Protective Packaging — `protective_packaging`

Rezept `recipe.assembler.protective_packaging`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x packaging_components (Packaging Components); 1 x insulation_material (Insulation Material). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × protective_packaging; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $15.4195; Kataloganker: $11.35; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; packaging_components (Packaging Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; insulation_material (Insulation Material): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Quantum Computing Module — `quantum_computing_module`

Rezept `recipe.assembler.quantum_computing_module`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x refractory_alloy_components (Refractory Alloy Components); 1 x processor_components (Processor Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × quantum_computing_module; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $238.0; Kataloganker: $190.4; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; refractory_alloy_components (Refractory Alloy Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; processor_components (Processor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Radio Transceiver — `radio_transceiver`

Rezept `recipe.assembler.radio_transceiver`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x telecom_components (Telecom Components); 1 x magnetic_components (Magnetic Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × radio_transceiver; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $201.5; Kataloganker: $161.2; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; telecom_components (Telecom Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; magnetic_components (Magnetic Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Railway Track — `railway_track`

Rezept `recipe.assembler.railway_track`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x rail_components (Rail Components); 1 x steel_components (Steel Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × railway_track; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $82.0875; Kataloganker: $65.67; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9; rail_components (Rail Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; steel_components (Steel Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Reinforced Concrete — `reinforced_concrete`

Rezept `recipe.assembler.reinforced_concrete`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x concrete_components (Concrete Components); 1 x steel_components (Steel Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × reinforced_concrete; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $35.3543; Kataloganker: $27.45; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 3; concrete_components (Concrete Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; steel_components (Steel Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Robotic Actuator — `robotic_actuator`

Rezept `recipe.assembler.robotic_actuator`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x precision_components (Precision Components); 1 x motor_components (Motor Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × robotic_actuator; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $59.7875; Kataloganker: $47.83; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; precision_components (Precision Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; motor_components (Motor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Robotic Arm — `robotic_arm`

Rezept `recipe.assembler.robotic_arm`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x precision_components (Precision Components); 1 x motor_components (Motor Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × robotic_arm; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $180.775; Kataloganker: $144.62; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; precision_components (Precision Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; motor_components (Motor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Rocket Engine — `rocket_engine`

Rezept `recipe.assembler.rocket_engine`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x turbine_components (Turbine Components); 1 x titanium_components (Titanium Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × rocket_engine; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $62.9392; Kataloganker: $49.85; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; turbine_components (Turbine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; titanium_components (Titanium Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Router — `router`

Rezept `recipe.assembler.router`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x network_components (Network Components); 1 x telecom_components (Telecom Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × router; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $244.3; Kataloganker: $195.44; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; network_components (Network Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; telecom_components (Telecom Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Safety Equipment — `safety_equipment`

Rezept `recipe.assembler.safety_equipment`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x industrial_fabric (Industrial Fabric); 1 x glass_panels (Glass Panels); 1 x tire_components (Tire Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × safety_equipment; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $55.7727; Kataloganker: $40.52; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 13; industrial_fabric (Industrial Fabric): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; glass_panels (Glass Panels): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; tire_components (Tire Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Satellite — `satellite`

Rezept `recipe.assembler.satellite`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x aerospace_components (Aerospace Components); 1 x solar_components (Solar Components); 1 x telecom_components (Telecom Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × satellite; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $162.5; Kataloganker: $130.0; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; aerospace_components (Aerospace Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; solar_components (Solar Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; telecom_components (Telecom Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Semiconductor Equipment — `semiconductor_equipment`

Rezept `recipe.assembler.semiconductor_equipment`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x precision_components (Precision Components); 1 x control_electronics (Control Electronics); 1 x ceramic_components (Ceramic Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × semiconductor_equipment; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $154.6; Kataloganker: $123.68; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; precision_components (Precision Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; ceramic_components (Ceramic Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Server — `server`

Rezept `recipe.assembler.server`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x computing_components (Computing Components); 1 x memory_components (Memory Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × server; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $438.7375; Kataloganker: $350.99; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; computing_components (Computing Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; memory_components (Memory Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Server Rack — `server_rack`

Rezept `recipe.assembler.server_rack`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x server_components (Server Components); 1 x structural_components (Structural Components); 1 x network_components (Network Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × server_rack; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $313.7875; Kataloganker: $251.03; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; server_components (Server Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; structural_components (Structural Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; network_components (Network Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Servo Motor — `servo_motor`

Rezept `recipe.assembler.servo_motor`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x motor_components (Motor Components); 1 x precision_components (Precision Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × servo_motor; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $149.275; Kataloganker: $119.42; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; motor_components (Motor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; precision_components (Precision Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Soft Drinks — `soft_drinks`

Rezept `recipe.assembler.soft_drinks`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x nutrition_components (Nutrition Components); 1 x packaging_components (Packaging Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × soft_drinks; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $36.3705; Kataloganker: $28.2; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; nutrition_components (Nutrition Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; packaging_components (Packaging Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Solar Array — `solar_array`

Rezept `recipe.assembler.solar_array`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x solar_components (Solar Components); 1 x power_electronics (Power Electronics). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × solar_array; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $138.775; Kataloganker: $111.02; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; solar_components (Solar Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; power_electronics (Power Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Steam Turbine — `steam_turbine`

Rezept `recipe.assembler.steam_turbine`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x turbine_components (Turbine Components); 1 x stainless_components (Stainless Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × steam_turbine; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $69.1554; Kataloganker: $54.94; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; turbine_components (Turbine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; stainless_components (Stainless Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Structural Systems — `structural_systems`

Rezept `recipe.assembler.structural_systems`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x structural_components (Structural Components); 1 x concrete_components (Concrete Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × structural_systems; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $56.05; Kataloganker: $44.84; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 3; structural_components (Structural Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; concrete_components (Concrete Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Supercomputer — `supercomputer`

Rezept `recipe.assembler.supercomputer`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x ai_compute_components (AI Compute Components); 1 x server_components (Server Components); 1 x grid_storage_components (Grid Storage Components); 1 x network_components (Network Components). Unterschiedliche Inputs: 4; gesamte Inputmenge: 5.
Output: 1.0 × supercomputer; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $406.525; Kataloganker: $325.22; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; ai_compute_components (AI Compute Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; server_components (Server Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; grid_storage_components (Grid Storage Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; network_components (Network Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Superconducting Magnet System — `superconducting_magnet_system`

Rezept `recipe.assembler.superconducting_magnet_system`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x refractory_alloy_components (Refractory Alloy Components); 1 x power_electronics (Power Electronics). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × superconducting_magnet_system; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $164.8875; Kataloganker: $131.91; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; refractory_alloy_components (Refractory Alloy Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; power_electronics (Power Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Surgical Equipment — `surgical_equipment`

Rezept `recipe.assembler.surgical_equipment`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x precision_components (Precision Components); 1 x stainless_components (Stainless Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × surgical_equipment; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $77.65; Kataloganker: $62.12; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; precision_components (Precision Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; stainless_components (Stainless Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Sustainable Packaging — `sustainable_packaging`

Rezept `recipe.assembler.sustainable_packaging`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x packaging_components (Packaging Components); 1 x bio_composite (Bio-Composite). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × sustainable_packaging; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $23.0119; Kataloganker: $16.3; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 5; packaging_components (Packaging Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; bio_composite (Bio-Composite): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Switchgear — `switchgear`

Rezept `recipe.assembler.switchgear`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x electrical_components (Electrical Components); 1 x control_electronics (Control Electronics). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × switchgear; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $107.6625; Kataloganker: $86.13; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; electrical_components (Electrical Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Synthetic Fuel Plant — `synthetic_fuel_plant`

Rezept `recipe.assembler.synthetic_fuel_plant`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x chemical_components (Chemical Components); 1 x electrolyzer_components (Electrolyzer Components); 1 x catalyst_components (Catalyst Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 3.
Output: 1.0 × synthetic_fuel_plant; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $147.125; Kataloganker: $117.7; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 20; chemical_components (Chemical Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; electrolyzer_components (Electrolyzer Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; catalyst_components (Catalyst Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Tanker — `tanker`

Rezept `recipe.assembler.tanker`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x marine_components (Marine Components); 1 x pump_components (Pump Components); 1 x corrosion_resistant_components (Corrosion Resistant Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × tanker; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $123.7375; Kataloganker: $98.99; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 11; marine_components (Marine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; pump_components (Pump Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; corrosion_resistant_components (Corrosion Resistant Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Transformer — `transformer`

Rezept `recipe.assembler.transformer`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x transformer_components (Transformer Components); 1 x electrical_components (Electrical Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × transformer; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $55.7875; Kataloganker: $44.63; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 9; transformer_components (Transformer Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; electrical_components (Electrical Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Utility Vehicle — `utility_vehicle`

Rezept `recipe.assembler.utility_vehicle`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x vehicle_components (Vehicle Components); 2 x control_electronics (Control Electronics); 1 x sensor_components (Sensor Components). Unterschiedliche Inputs: 3; gesamte Inputmenge: 5.
Output: 1.0 × utility_vehicle; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $309.4125; Kataloganker: $247.53; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 18; vehicle_components (Vehicle Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; control_electronics (Control Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; sensor_components (Sensor Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Wind Turbine — `wind_turbine`

Rezept `recipe.assembler.wind_turbine`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x wind_components (Wind Components); 1 x structural_components (Structural Components); 1 x power_electronics (Power Electronics). Unterschiedliche Inputs: 3; gesamte Inputmenge: 4.
Output: 1.0 × wind_turbine; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $223.95; Kataloganker: $179.16; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; wind_components (Wind Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; structural_components (Structural Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; power_electronics (Power Electronics): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Workboat — `workboat`

Rezept `recipe.assembler.workboat`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 2 x marine_components (Marine Components); 1 x turbine_components (Turbine Components). Unterschiedliche Inputs: 2; gesamte Inputmenge: 3.
Output: 1.0 × workboat; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $98.3375; Kataloganker: $78.67; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 22; marine_components (Marine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; turbine_components (Turbine Components): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

#### Workwear — `workwear`

Rezept `recipe.assembler.workwear`; Maschine `machine.assembler` (Assembler); Common-Kaufpreis $240.0.
Inputs/Zyklus: 1 x technical_textile (Technical Textile); 1 x industrial_fabric (Industrial Fabric). Unterschiedliche Inputs: 2; gesamte Inputmenge: 2.
Output: 1.0 × workwear; Zyklus: 6.0 s; Leistung: 12.0 MW; MK1/Common: 10.0 U/min.
Basisverkaufspreis: $23.2271; Kataloganker: $13.24; Verkauf: ja; Market-Fracht erforderlich.
Freischaltung: Company-Level >= 7; technical_textile (Technical Textile): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0; industrial_fabric (Industrial Fabric): Produktion freigeschaltet UND Lifetime-Produktion >= 60.0.
Unmittelbare Folgeprodukte: —.

## 7. Direkte Rezepte und Mengen

Abschnitt 6 und die CSV führen sämtliche direkten Inputmengen pro abgeschlossenem Zyklus und den zugehörigen Output auf. Kein Input ist zu einem Sammelbegriff zusammengefasst. Primärrezepte haben keine Materialinputs. `direct_input_count` zählt verschiedene Produkte, `total_input_units_per_cycle` summiert deren Einheiten. Letzteres ist keine Gewichtung nach Geldwert oder Masse. Über Produkt-IDs sind alle Rezepte stufenübergreifend eindeutig verknüpft.

## 8. Produktionszeit und Energie

Alle 353 wirksamen Rezepte dauern 6.0 Sekunden. Rezeptüberschreibungen für Output und Leistung werden durch `ProductionOptionDefinition.output_amount_for`, `cycle_seconds_for` und `power_draw_for` aufgelöst. MW sind momentane Leistung bei Betrieb, keine Energiemenge pro Zyklus. Die Rate berücksichtigt keine Lagerblockade, Materialknappheit, fehlende Leistung oder Frachtwartezeit. Generatoren und Brennstoffverbrauch sind eigene Infrastrukturregeln; `release_balance.balance_definitions` passt Brennstoffraten anhand des bestehenden Graphen an, verändert aber die hier erfassten Produktionsrezepte nicht.

## 9. Freischaltvoraussetzungen

`core/progression.py:_option_requirements_met` verlangt Company-Level laut `resource_progression.json` und für jeden direkten Input dessen bereits freigeschaltete Produktion sowie Lifetime-Produktion: Processing jeweils 120, Fabrication und Assembly jeweils 60. Diese Schwellen hängen nicht von der Rezeptmenge ab und werden beim Freischalten nicht verbraucht. Primary benötigt nur das Company-Level. Alle Bedingungen stehen pro Produkt im Katalog und CSV. Familiennamen/Mastery in der UI sind keine zusätzliche Bedingung dieser Funktion. Bereits gewährte Freischaltungen bleiben im Produktionsfortschritt gespeichert; Migration kann historische Berechtigungen übernehmen. Es wurde kein individueller Savezustand ausgewertet.

## 10. Herkunft und Abhängigkeiten sämtlicher Produktionsketten

Quelle der Kanten: `ProductionOptionDefinition.input_resources`; keine separate manuell gepflegte Kettenliste. Für die vollständigen Vorfahren wurde ausschließlich die vorhandene Funktion `ancestors` aus `scripts/phase8_contract_simulation.py` isoliert verwendet, ohne das Simulationsmodul auszuführen. Hersteller und unmittelbare Verbraucher stammen aus `ProductionGuideRecipeIndex`. Tiefe, Rohstoffarten und Arbeitswert stammen aus `ProductionValueCalculator`. Die bestehenden P10-Rohstoffmengen je Einheit wurden übernommen und ihre Produktpreise/Tiefen mit dem aktuellen Katalog abgeglichen. Es wurde kein neues Auditprogramm im Projekt angelegt und keine neue Preis- oder Graphberechnung implementiert.

Definitionen: Tiefe zählt maximale Kanten bis zum Rohstoff (Primary 0). Vorfahren schließen das Ziel selbst aus. Indirekte Inputs schließen direkte Inputs aus. Zwischenprodukte sind alle nicht-primären Vorfahren, einschließlich direkter Zwischenprodukte. Bei Primary bezeichnet die Basisrohstoffmenge das Produkt selbst (1 Art); es gibt dabei keine Inputkante. „Gemeinsam“ bedeutet: dieses Vorprodukt wird innerhalb derselben vollständigen Zielkette von mindestens zwei unterschiedlichen Rezepten verwendet. Mengen gemeinsamer Äste sind im übernommenen raw_inputs_per_output_unit zusammengeführt; keine Annahme über tatsächliche Maschinenbelegung oder gemeinsame Lagerbestände.

### `bauxite` — Bauxite
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: bauxite (Bauxite).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.0}`.

### `borate_ore` — Borate Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: borate_ore (Borate Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"borate_ore": 1.0}`.

### `chromium_ore` — Chromium Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: chromium_ore (Chromium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"chromium_ore": 1.0}`.

### `clay` — Clay
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: clay (Clay).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"clay": 1.0}`.

### `coal` — Coal
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: coal (Coal).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 1.0}`.

### `cobalt_ore` — Cobalt Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: cobalt_ore (Cobalt Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"cobalt_ore": 1.0}`.

### `copper_ore` — Copper Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: copper_ore (Copper Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 1.0}`.

### `corn` — Corn
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: corn (Corn).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"corn": 1.0}`.

### `cotton` — Cotton
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: cotton (Cotton).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"cotton": 1.0}`.

### `crude_oil` — Crude Oil
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: crude_oil (Crude Oil).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 1.0}`.

### `fluorspar` — Fluorspar
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: fluorspar (Fluorspar).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"fluorspar": 1.0}`.

### `fruit` — Fruit
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: fruit (Fruit).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"fruit": 1.0}`.

### `gold_ore` — Gold Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: gold_ore (Gold Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"gold_ore": 1.0}`.

### `graphite` — Graphite
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: graphite (Graphite).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"graphite": 1.0}`.

### `gypsum` — Gypsum
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: gypsum (Gypsum).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"gypsum": 1.0}`.

### `iron_ore` — Iron Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: iron_ore (Iron Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"iron_ore": 1.0}`.

### `kaolin` — Kaolin
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: kaolin (Kaolin).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"kaolin": 1.0}`.

### `lead_ore` — Lead Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: lead_ore (Lead Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"lead_ore": 1.0}`.

### `limestone` — Limestone
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: limestone (Limestone).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"limestone": 1.0}`.

### `lithium_ore` — Lithium Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: lithium_ore (Lithium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"lithium_ore": 1.0}`.

### `magnesite` — Magnesite
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: magnesite (Magnesite).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"magnesite": 1.0}`.

### `manganese_ore` — Manganese Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: manganese_ore (Manganese Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"manganese_ore": 1.0}`.

### `molybdenum_ore` — Molybdenum Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: molybdenum_ore (Molybdenum Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"molybdenum_ore": 1.0}`.

### `natural_gas` — Natural Gas
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: natural_gas (Natural Gas).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"natural_gas": 1.0}`.

### `natural_rubber` — Natural Rubber
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: natural_rubber (Natural Rubber).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"natural_rubber": 1.0}`.

### `nickel_ore` — Nickel Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: nickel_ore (Nickel Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"nickel_ore": 1.0}`.

### `niobium_ore` — Niobium Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: niobium_ore (Niobium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"niobium_ore": 1.0}`.

### `palladium_ore` — Palladium Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: palladium_ore (Palladium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"palladium_ore": 1.0}`.

### `phosphate_rock` — Phosphate Rock
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: phosphate_rock (Phosphate Rock).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"phosphate_rock": 1.0}`.

### `platinum_ore` — Platinum Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: platinum_ore (Platinum Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"platinum_ore": 1.0}`.

### `potash` — Potash
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: potash (Potash).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"potash": 1.0}`.

### `potatoes` — Potatoes
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: potatoes (Potatoes).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"potatoes": 1.0}`.

### `quartz` — Quartz
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: quartz (Quartz).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"quartz": 1.0}`.

### `rapeseed` — Rapeseed
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: rapeseed (Rapeseed).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"rapeseed": 1.0}`.

### `rare_earth_ore` — Rare Earth Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"rare_earth_ore": 1.0}`.

### `salt` — Salt
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: salt (Salt).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"salt": 1.0}`.

### `silica_sand` — Silica Sand
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: silica_sand (Silica Sand).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"silica_sand": 1.0}`.

### `silver_ore` — Silver Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: silver_ore (Silver Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"silver_ore": 1.0}`.

### `soybeans` — Soybeans
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: soybeans (Soybeans).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"soybeans": 1.0}`.

### `sugarcane` — Sugarcane
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: sugarcane (Sugarcane).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"sugarcane": 1.0}`.

### `sulfur` — Sulfur
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: sulfur (Sulfur).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"sulfur": 1.0}`.

### `timber` — Timber
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: timber (Timber).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"timber": 1.0}`.

### `tin_ore` — Tin Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: tin_ore (Tin Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"tin_ore": 1.0}`.

### `titanium_ore` — Titanium Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: titanium_ore (Titanium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"titanium_ore": 1.0}`.

### `tungsten_ore` — Tungsten Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: tungsten_ore (Tungsten Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"tungsten_ore": 1.0}`.

### `uranium_ore` — Uranium Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: uranium_ore (Uranium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"uranium_ore": 1.0}`.

### `vanadium_ore` — Vanadium Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: vanadium_ore (Vanadium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"vanadium_ore": 1.0}`.

### `wheat` — Wheat
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: wheat (Wheat).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"wheat": 1.0}`.

### `zinc_ore` — Zinc Ore
Tiefe 0; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: —.
Nur indirekte Inputs: —.
Basisrohstoffe: zinc_ore (Zinc Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"zinc_ore": 1.0}`.

### `aluminum` — Aluminum
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: bauxite (Bauxite).
Nur indirekte Inputs: —.
Basisrohstoffe: bauxite (Bauxite).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8}`.

### `ammonia` — Ammonia
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: natural_gas (Natural Gas).
Nur indirekte Inputs: —.
Basisrohstoffe: natural_gas (Natural Gas).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"natural_gas": 1.5}`.

### `bio_lubricant` — Bio-Lubricant
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: natural_gas (Natural Gas); rapeseed (Rapeseed).
Nur indirekte Inputs: —.
Basisrohstoffe: natural_gas (Natural Gas); rapeseed (Rapeseed).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"natural_gas": 0.5, "rapeseed": 1.0}`.

### `bitumen` — Bitumen
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: crude_oil (Crude Oil).
Nur indirekte Inputs: —.
Basisrohstoffe: crude_oil (Crude Oil).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 1.5}`.

### `carbon_fiber` — Carbon Fiber
Tiefe 1; Basisrohstoffarten 3; Zwischenprodukte 0.
Alle Vorprodukte: crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas).
Nur indirekte Inputs: —.
Basisrohstoffe: crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 3.0, "graphite": 1.0, "natural_gas": 1.0}`.

### `catalyst_metal` — Catalyst Metal
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: palladium_ore (Palladium Ore); platinum_ore (Platinum Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: palladium_ore (Palladium Ore); platinum_ore (Platinum Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"palladium_ore": 1.5, "platinum_ore": 0.5}`.

### `cellulose` — Cellulose
Tiefe 1; Basisrohstoffarten 3; Zwischenprodukte 0.
Alle Vorprodukte: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Nur indirekte Inputs: —.
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 0.5, "natural_gas": 0.5, "timber": 1.0}`.

### `cement` — Cement
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: gypsum (Gypsum); limestone (Limestone).
Nur indirekte Inputs: —.
Basisrohstoffe: gypsum (Gypsum); limestone (Limestone).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"gypsum": 0.3333333333333333, "limestone": 1.3333333333333333}`.

### `ceramics` — Ceramics
Tiefe 1; Basisrohstoffarten 3; Zwischenprodukte 0.
Alle Vorprodukte: clay (Clay); kaolin (Kaolin); magnesite (Magnesite).
Nur indirekte Inputs: —.
Basisrohstoffe: clay (Clay); kaolin (Kaolin); magnesite (Magnesite).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"clay": 1.0, "kaolin": 0.3333333333333333, "magnesite": 0.3333333333333333}`.

### `chemical_feedstock` — Chemical Feedstock
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: crude_oil (Crude Oil); natural_gas (Natural Gas).
Nur indirekte Inputs: —.
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 0.6666666666666666, "natural_gas": 0.6666666666666666}`.

### `chlorine` — Chlorine
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: salt (Salt).
Nur indirekte Inputs: —.
Basisrohstoffe: salt (Salt).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"salt": 1.5}`.

### `chromium` — Chromium
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: chromium_ore (Chromium Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: chromium_ore (Chromium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"chromium_ore": 1.8}`.

### `cobalt` — Cobalt
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: cobalt_ore (Cobalt Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: cobalt_ore (Cobalt Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"cobalt_ore": 2.0}`.

### `copper` — Copper
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: copper_ore (Copper Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: copper_ore (Copper Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 2.0}`.

### `corn_meal` — Corn Meal
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: corn (Corn).
Nur indirekte Inputs: —.
Basisrohstoffe: corn (Corn).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"corn": 1.0}`.

### `cotton_fiber` — Cotton Fiber
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: cotton (Cotton).
Nur indirekte Inputs: —.
Basisrohstoffe: cotton (Cotton).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"cotton": 1.0}`.

### `fermentation_feedstock` — Fermentation Feedstock
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: corn (Corn); sugarcane (Sugarcane).
Nur indirekte Inputs: —.
Basisrohstoffe: corn (Corn); sugarcane (Sugarcane).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"corn": 1.0, "sugarcane": 0.5}`.

### `flour` — Flour
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: wheat (Wheat).
Nur indirekte Inputs: —.
Basisrohstoffe: wheat (Wheat).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"wheat": 1.0}`.

### `fruit_concentrate` — Fruit Concentrate
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: fruit (Fruit); sugarcane (Sugarcane).
Nur indirekte Inputs: —.
Basisrohstoffe: fruit (Fruit); sugarcane (Sugarcane).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"fruit": 1.5, "sugarcane": 0.5}`.

### `galvanized_metal` — Galvanized Metal
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: iron_ore (Iron Ore); zinc_ore (Zinc Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: iron_ore (Iron Ore); zinc_ore (Zinc Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"iron_ore": 1.3333333333333333, "zinc_ore": 1.3333333333333333}`.

### `glass` — Glass
Tiefe 1; Basisrohstoffarten 3; Zwischenprodukte 0.
Alle Vorprodukte: borate_ore (Borate Ore); limestone (Limestone); silica_sand (Silica Sand).
Nur indirekte Inputs: —.
Basisrohstoffe: borate_ore (Borate Ore); limestone (Limestone); silica_sand (Silica Sand).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"borate_ore": 0.3333333333333333, "limestone": 0.3333333333333333, "silica_sand": 1.3333333333333333}`.

### `gold` — Gold
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: gold_ore (Gold Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: gold_ore (Gold Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"gold_ore": 2.0}`.

### `high_purity_silicon` — High-Purity Silicon
Tiefe 1; Basisrohstoffarten 4; Zwischenprodukte 0.
Alle Vorprodukte: crude_oil (Crude Oil); fluorspar (Fluorspar); natural_gas (Natural Gas); quartz (Quartz).
Nur indirekte Inputs: —.
Basisrohstoffe: crude_oil (Crude Oil); fluorspar (Fluorspar); natural_gas (Natural Gas); quartz (Quartz).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 1.0, "fluorspar": 1.0, "natural_gas": 1.0, "quartz": 4.0}`.

### `hydrogen` — Hydrogen
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: natural_gas (Natural Gas).
Nur indirekte Inputs: —.
Basisrohstoffe: natural_gas (Natural Gas).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"natural_gas": 1.5}`.

### `industrial_gas` — Industrial Gas
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: natural_gas (Natural Gas).
Nur indirekte Inputs: —.
Basisrohstoffe: natural_gas (Natural Gas).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"natural_gas": 1.0}`.

### `industrial_resin` — Industrial Resin
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: crude_oil (Crude Oil); natural_gas (Natural Gas).
Nur indirekte Inputs: —.
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 1.0, "natural_gas": 0.5}`.

### `iron` — Iron
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: iron_ore (Iron Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: iron_ore (Iron Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"iron_ore": 2.0}`.

### `lead` — Lead
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: lead_ore (Lead Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: lead_ore (Lead Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"lead_ore": 1.8}`.

### `lithium` — Lithium
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: lithium_ore (Lithium Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: lithium_ore (Lithium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"lithium_ore": 2.0}`.

### `lumber` — Lumber
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: timber (Timber).
Nur indirekte Inputs: —.
Basisrohstoffe: timber (Timber).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"timber": 1.0}`.

### `manganese` — Manganese
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: manganese_ore (Manganese Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: manganese_ore (Manganese Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"manganese_ore": 1.8}`.

### `molybdenum` — Molybdenum
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: molybdenum_ore (Molybdenum Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: molybdenum_ore (Molybdenum Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"molybdenum_ore": 2.0}`.

### `nickel` — Nickel
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: nickel_ore (Nickel Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: nickel_ore (Nickel Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"nickel_ore": 1.8}`.

### `nickel_alloy` — Nickel Alloy
Tiefe 1; Basisrohstoffarten 4; Zwischenprodukte 0.
Alle Vorprodukte: coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_ore (Nickel Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_ore (Nickel Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.3333333333333333, "iron_ore": 2.0, "molybdenum_ore": 0.6666666666666666, "nickel_ore": 2.0}`.

### `niobium` — Niobium
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: niobium_ore (Niobium Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: niobium_ore (Niobium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"niobium_ore": 2.0}`.

### `nuclear_material` — Nuclear Material
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: lead_ore (Lead Ore); uranium_ore (Uranium Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: lead_ore (Lead Ore); uranium_ore (Uranium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"lead_ore": 0.5, "uranium_ore": 1.5}`.

### `organic_feedstock` — Organic Feedstock
Tiefe 1; Basisrohstoffarten 3; Zwischenprodukte 0.
Alle Vorprodukte: fruit (Fruit); potatoes (Potatoes); wheat (Wheat).
Nur indirekte Inputs: —.
Basisrohstoffe: fruit (Fruit); potatoes (Potatoes); wheat (Wheat).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"fruit": 0.5, "potatoes": 0.5, "wheat": 0.5}`.

### `palladium` — Palladium
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: palladium_ore (Palladium Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: palladium_ore (Palladium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"palladium_ore": 2.0}`.

### `phosphoric_acid` — Phosphoric Acid
Tiefe 1; Basisrohstoffarten 3; Zwischenprodukte 0.
Alle Vorprodukte: natural_gas (Natural Gas); phosphate_rock (Phosphate Rock); sulfur (Sulfur).
Nur indirekte Inputs: —.
Basisrohstoffe: natural_gas (Natural Gas); phosphate_rock (Phosphate Rock); sulfur (Sulfur).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"natural_gas": 0.5, "phosphate_rock": 1.0, "sulfur": 0.5}`.

### `platinum` — Platinum
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: platinum_ore (Platinum Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: platinum_ore (Platinum Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"platinum_ore": 2.0}`.

### `polymer` — Polymer
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: crude_oil (Crude Oil); natural_gas (Natural Gas).
Nur indirekte Inputs: —.
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 1.5, "natural_gas": 0.5}`.

### `potassium_compound` — Potassium Compound
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: potash (Potash).
Nur indirekte Inputs: —.
Basisrohstoffe: potash (Potash).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"potash": 1.5}`.

### `processed_gypsum` — Processed Gypsum
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: gypsum (Gypsum).
Nur indirekte Inputs: —.
Basisrohstoffe: gypsum (Gypsum).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"gypsum": 1.0}`.

### `processed_rubber` — Processed Rubber
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: natural_rubber (Natural Rubber); sulfur (Sulfur).
Nur indirekte Inputs: —.
Basisrohstoffe: natural_rubber (Natural Rubber); sulfur (Sulfur).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"natural_rubber": 1.0, "sulfur": 0.5}`.

### `purified_graphite` — Purified Graphite
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: graphite (Graphite).
Nur indirekte Inputs: —.
Basisrohstoffe: graphite (Graphite).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"graphite": 1.3333333333333333}`.

### `rare_earth_metals` — Rare Earth Metals
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: rare_earth_ore (Rare Earth Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"rare_earth_ore": 2.6666666666666665}`.

### `raw_sugar` — Raw Sugar
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: sugarcane (Sugarcane).
Nur indirekte Inputs: —.
Basisrohstoffe: sugarcane (Sugarcane).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"sugarcane": 1.0}`.

### `refined_sugar` — Refined Sugar
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: sugarcane (Sugarcane).
Nur indirekte Inputs: —.
Basisrohstoffe: sugarcane (Sugarcane).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"sugarcane": 1.0}`.

### `shielding_material` — Shielding Material
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: borate_ore (Borate Ore); lead_ore (Lead Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: borate_ore (Borate Ore); lead_ore (Lead Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"borate_ore": 0.3333333333333333, "lead_ore": 1.3333333333333333}`.

### `silicon` — Silicon
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: coal (Coal); quartz (Quartz).
Nur indirekte Inputs: —.
Basisrohstoffe: coal (Coal); quartz (Quartz).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.5, "quartz": 2.0}`.

### `silver` — Silver
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: silver_ore (Silver Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: silver_ore (Silver Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"silver_ore": 2.0}`.

### `soy_oil` — Soy Oil
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: soybeans (Soybeans).
Nur indirekte Inputs: —.
Basisrohstoffe: soybeans (Soybeans).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"soybeans": 2.0}`.

### `soy_protein` — Soy Protein
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: soybeans (Soybeans).
Nur indirekte Inputs: —.
Basisrohstoffe: soybeans (Soybeans).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"soybeans": 2.0}`.

### `stainless_steel` — Stainless Steel
Tiefe 1; Basisrohstoffarten 4; Zwischenprodukte 0.
Alle Vorprodukte: chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); nickel_ore (Nickel Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); nickel_ore (Nickel Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"chromium_ore": 0.6666666666666666, "coal": 1.0, "iron_ore": 4.0, "nickel_ore": 0.6666666666666666}`.

### `starch` — Starch
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: corn (Corn); potatoes (Potatoes).
Nur indirekte Inputs: —.
Basisrohstoffe: corn (Corn); potatoes (Potatoes).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"corn": 1.0, "potatoes": 0.5}`.

### `steel` — Steel
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: coal (Coal); iron_ore (Iron Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: coal (Coal); iron_ore (Iron Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.75, "iron_ore": 3.0}`.

### `sulfuric_acid` — Sulfuric Acid
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: natural_gas (Natural Gas); sulfur (Sulfur).
Nur indirekte Inputs: —.
Basisrohstoffe: natural_gas (Natural Gas); sulfur (Sulfur).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"natural_gas": 0.5, "sulfur": 1.0}`.

### `superconducting_alloy` — Superconducting Alloy
Tiefe 1; Basisrohstoffarten 3; Zwischenprodukte 0.
Alle Vorprodukte: niobium_ore (Niobium Ore); rare_earth_ore (Rare Earth Ore); titanium_ore (Titanium Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: niobium_ore (Niobium Ore); rare_earth_ore (Rare Earth Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"niobium_ore": 2.0, "rare_earth_ore": 1.5, "titanium_ore": 1.0}`.

### `synthetic_rubber` — Synthetic Rubber
Tiefe 1; Basisrohstoffarten 3; Zwischenprodukte 0.
Alle Vorprodukte: crude_oil (Crude Oil); natural_gas (Natural Gas); sulfur (Sulfur).
Nur indirekte Inputs: —.
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); sulfur (Sulfur).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 1.0, "natural_gas": 0.5, "sulfur": 0.5}`.

### `tin` — Tin
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: tin_ore (Tin Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: tin_ore (Tin Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"tin_ore": 1.8}`.

### `titanium` — Titanium
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: titanium_ore (Titanium Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: titanium_ore (Titanium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"titanium_ore": 2.0}`.

### `treated_lumber` — Treated Lumber
Tiefe 1; Basisrohstoffarten 3; Zwischenprodukte 0.
Alle Vorprodukte: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Nur indirekte Inputs: —.
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 0.6666666666666666, "natural_gas": 0.3333333333333333, "timber": 1.0}`.

### `tungsten` — Tungsten
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: tungsten_ore (Tungsten Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"tungsten_ore": 2.0}`.

### `vanadium` — Vanadium
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: vanadium_ore (Vanadium Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: vanadium_ore (Vanadium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"vanadium_ore": 2.0}`.

### `vanadium_alloy` — Vanadium Alloy
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: iron_ore (Iron Ore); vanadium_ore (Vanadium Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: iron_ore (Iron Ore); vanadium_ore (Vanadium Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"iron_ore": 1.3333333333333333, "vanadium_ore": 1.3333333333333333}`.

### `vegetable_oil` — Vegetable Oil
Tiefe 1; Basisrohstoffarten 2; Zwischenprodukte 0.
Alle Vorprodukte: rapeseed (Rapeseed); soybeans (Soybeans).
Nur indirekte Inputs: —.
Basisrohstoffe: rapeseed (Rapeseed); soybeans (Soybeans).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"rapeseed": 1.0, "soybeans": 1.0}`.

### `wood_pulp` — Wood Pulp
Tiefe 1; Basisrohstoffarten 3; Zwischenprodukte 0.
Alle Vorprodukte: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Nur indirekte Inputs: —.
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 0.3333333333333333, "natural_gas": 0.3333333333333333, "timber": 1.0}`.

### `zinc` — Zinc
Tiefe 1; Basisrohstoffarten 1; Zwischenprodukte 0.
Alle Vorprodukte: zinc_ore (Zinc Ore).
Nur indirekte Inputs: —.
Basisrohstoffe: zinc_ore (Zinc Ore).
Zwischenprodukte: —.
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"zinc_ore": 1.8}`.

### `ai_compute_components` — AI Compute Components
Tiefe 2; Basisrohstoffarten 6; Zwischenprodukte 3.
Alle Vorprodukte: crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore).
Nur indirekte Inputs: crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Basisrohstoffe: crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: gold (Gold); high_purity_silicon (High-Purity Silicon); rare_earth_metals (Rare Earth Metals).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "natural_gas": 2.0, "quartz": 8.0, "rare_earth_ore": 2.6666666666666665}`.

### `advanced_alloy_components` — Advanced Alloy Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 3.
Alle Vorprodukte: iron_ore (Iron Ore); titanium (Titanium); titanium_ore (Titanium Ore); vanadium (Vanadium); vanadium_alloy (Vanadium Alloy); vanadium_ore (Vanadium Ore).
Nur indirekte Inputs: iron_ore (Iron Ore); titanium_ore (Titanium Ore); vanadium_ore (Vanadium Ore).
Basisrohstoffe: iron_ore (Iron Ore); titanium_ore (Titanium Ore); vanadium_ore (Vanadium Ore).
Zwischenprodukte: titanium (Titanium); vanadium (Vanadium); vanadium_alloy (Vanadium Alloy).
Gemeinsam verwendete Vorprodukte in dieser Kette: vanadium_ore (Vanadium Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"iron_ore": 2.6666666666666665, "titanium_ore": 2.0, "vanadium_ore": 4.666666666666666}`.

### `advanced_cell_components` — Advanced Cell Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 4.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); cobalt (Cobalt); cobalt_ore (Cobalt Ore); graphite (Graphite); lithium (Lithium); lithium_ore (Lithium Ore); purified_graphite (Purified Graphite).
Nur indirekte Inputs: bauxite (Bauxite); cobalt_ore (Cobalt Ore); graphite (Graphite); lithium_ore (Lithium Ore).
Basisrohstoffe: bauxite (Bauxite); cobalt_ore (Cobalt Ore); graphite (Graphite); lithium_ore (Lithium Ore).
Zwischenprodukte: aluminum (Aluminum); cobalt (Cobalt); lithium (Lithium); purified_graphite (Purified Graphite).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "cobalt_ore": 2.0, "graphite": 1.3333333333333333, "lithium_ore": 2.0}`.

### `aerospace_components` — Aerospace Components
Tiefe 2; Basisrohstoffarten 5; Zwischenprodukte 3.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas); titanium (Titanium); titanium_ore (Titanium Ore).
Nur indirekte Inputs: bauxite (Bauxite); crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas); titanium_ore (Titanium Ore).
Zwischenprodukte: aluminum (Aluminum); carbon_fiber (Carbon Fiber); titanium (Titanium).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "crude_oil": 3.0, "graphite": 1.0, "natural_gas": 1.0, "titanium_ore": 2.0}`.

### `agricultural_chemicals` — Agricultural Chemicals
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 3.
Alle Vorprodukte: chemical_feedstock (Chemical Feedstock); chlorine (Chlorine); crude_oil (Crude Oil); natural_gas (Natural Gas); salt (Salt); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid).
Nur indirekte Inputs: crude_oil (Crude Oil); natural_gas (Natural Gas); salt (Salt); sulfur (Sulfur).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); salt (Salt); sulfur (Sulfur).
Zwischenprodukte: chemical_feedstock (Chemical Feedstock); chlorine (Chlorine); sulfuric_acid (Sulfuric Acid).
Gemeinsam verwendete Vorprodukte in dieser Kette: natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 0.6666666666666666, "natural_gas": 1.1666666666666665, "salt": 1.5, "sulfur": 1.0}`.

### `agricultural_mineral_components` — Agricultural Mineral Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 2.
Alle Vorprodukte: natural_gas (Natural Gas); phosphate_rock (Phosphate Rock); phosphoric_acid (Phosphoric Acid); potash (Potash); potassium_compound (Potassium Compound); sulfur (Sulfur).
Nur indirekte Inputs: natural_gas (Natural Gas); phosphate_rock (Phosphate Rock); potash (Potash); sulfur (Sulfur).
Basisrohstoffe: natural_gas (Natural Gas); phosphate_rock (Phosphate Rock); potash (Potash); sulfur (Sulfur).
Zwischenprodukte: phosphoric_acid (Phosphoric Acid); potassium_compound (Potassium Compound).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"natural_gas": 0.5, "phosphate_rock": 1.0, "potash": 3.0, "sulfur": 0.5}`.

### `aluminum_components` — Aluminum Components
Tiefe 2; Basisrohstoffarten 1; Zwischenprodukte 1.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite).
Nur indirekte Inputs: bauxite (Bauxite).
Basisrohstoffe: bauxite (Bauxite).
Zwischenprodukte: aluminum (Aluminum).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8}`.

### `asphalt_components` — Asphalt Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: bitumen (Bitumen); cement (Cement); crude_oil (Crude Oil); gypsum (Gypsum); limestone (Limestone).
Nur indirekte Inputs: crude_oil (Crude Oil); gypsum (Gypsum); limestone (Limestone).
Basisrohstoffe: crude_oil (Crude Oil); gypsum (Gypsum); limestone (Limestone).
Zwischenprodukte: bitumen (Bitumen); cement (Cement).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 3.0, "gypsum": 0.3333333333333333, "limestone": 1.3333333333333333}`.

### `autonomous_components` — Autonomous Components
Tiefe 2; Basisrohstoffarten 6; Zwischenprodukte 3.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore).
Nur indirekte Inputs: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: copper (Copper); high_purity_silicon (High-Purity Silicon); rare_earth_metals (Rare Earth Metals).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 2.0, "crude_oil": 1.0, "fluorspar": 1.0, "natural_gas": 1.0, "quartz": 4.0, "rare_earth_ore": 2.6666666666666665}`.

### `avionics_components` — Avionics Components
Tiefe 2; Basisrohstoffarten 7; Zwischenprodukte 4.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz).
Nur indirekte Inputs: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "copper_ore": 4.0, "crude_oil": 4.0, "fluorspar": 4.0, "gold_ore": 4.0, "natural_gas": 4.0, "quartz": 16.0}`.

### `battery_components` — Battery Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 4.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); cobalt (Cobalt); cobalt_ore (Cobalt Ore); lithium (Lithium); lithium_ore (Lithium Ore); nickel (Nickel); nickel_ore (Nickel Ore).
Nur indirekte Inputs: bauxite (Bauxite); cobalt_ore (Cobalt Ore); lithium_ore (Lithium Ore); nickel_ore (Nickel Ore).
Basisrohstoffe: bauxite (Bauxite); cobalt_ore (Cobalt Ore); lithium_ore (Lithium Ore); nickel_ore (Nickel Ore).
Zwischenprodukte: aluminum (Aluminum); cobalt (Cobalt); lithium (Lithium); nickel (Nickel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "cobalt_ore": 2.0, "lithium_ore": 2.0, "nickel_ore": 1.8}`.

### `battery_materials` — Battery Materials
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 3.
Alle Vorprodukte: cobalt (Cobalt); cobalt_ore (Cobalt Ore); lithium (Lithium); lithium_ore (Lithium Ore); nickel (Nickel); nickel_ore (Nickel Ore).
Nur indirekte Inputs: cobalt_ore (Cobalt Ore); lithium_ore (Lithium Ore); nickel_ore (Nickel Ore).
Basisrohstoffe: cobalt_ore (Cobalt Ore); lithium_ore (Lithium Ore); nickel_ore (Nickel Ore).
Zwischenprodukte: cobalt (Cobalt); lithium (Lithium); nickel (Nickel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"cobalt_ore": 1.0, "lithium_ore": 2.0, "nickel_ore": 0.9}`.

### `bearing_components` — Bearing Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: chromium (Chromium); chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); steel (Steel).
Nur indirekte Inputs: chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore).
Basisrohstoffe: chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore).
Zwischenprodukte: chromium (Chromium); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"chromium_ore": 0.9, "coal": 0.75, "iron_ore": 3.0}`.

### `bio_composite` — Bio-Composite
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: cellulose (Cellulose); crude_oil (Crude Oil); industrial_resin (Industrial Resin); natural_gas (Natural Gas); timber (Timber).
Nur indirekte Inputs: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: cellulose (Cellulose); industrial_resin (Industrial Resin).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 1.5, "natural_gas": 1.0, "timber": 1.0}`.

### `bio_material_components` — Bio-Material Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 2.
Alle Vorprodukte: bio_lubricant (Bio-Lubricant); cellulose (Cellulose); crude_oil (Crude Oil); natural_gas (Natural Gas); rapeseed (Rapeseed); timber (Timber).
Nur indirekte Inputs: crude_oil (Crude Oil); natural_gas (Natural Gas); rapeseed (Rapeseed); timber (Timber).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); rapeseed (Rapeseed); timber (Timber).
Zwischenprodukte: bio_lubricant (Bio-Lubricant); cellulose (Cellulose).
Gemeinsam verwendete Vorprodukte in dieser Kette: natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 0.5, "natural_gas": 1.0, "rapeseed": 1.0, "timber": 1.0}`.

### `biodiesel_feedstock` — Biodiesel Feedstock
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 2.
Alle Vorprodukte: chemical_feedstock (Chemical Feedstock); crude_oil (Crude Oil); natural_gas (Natural Gas); rapeseed (Rapeseed); soybeans (Soybeans); vegetable_oil (Vegetable Oil).
Nur indirekte Inputs: crude_oil (Crude Oil); natural_gas (Natural Gas); rapeseed (Rapeseed); soybeans (Soybeans).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); rapeseed (Rapeseed); soybeans (Soybeans).
Zwischenprodukte: chemical_feedstock (Chemical Feedstock); vegetable_oil (Vegetable Oil).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 0.6666666666666666, "natural_gas": 0.6666666666666666, "rapeseed": 2.0, "soybeans": 2.0}`.

### `biopolymer` — Biopolymer
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: corn (Corn); fermentation_feedstock (Fermentation Feedstock); potatoes (Potatoes); starch (Starch); sugarcane (Sugarcane).
Nur indirekte Inputs: corn (Corn); potatoes (Potatoes); sugarcane (Sugarcane).
Basisrohstoffe: corn (Corn); potatoes (Potatoes); sugarcane (Sugarcane).
Zwischenprodukte: fermentation_feedstock (Fermentation Feedstock); starch (Starch).
Gemeinsam verwendete Vorprodukte in dieser Kette: corn (Corn).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"corn": 3.0, "potatoes": 1.0, "sugarcane": 0.5}`.

### `catalyst_components` — Catalyst Components
Tiefe 2; Basisrohstoffarten 2; Zwischenprodukte 2.
Alle Vorprodukte: catalyst_metal (Catalyst Metal); palladium (Palladium); palladium_ore (Palladium Ore); platinum_ore (Platinum Ore).
Nur indirekte Inputs: palladium_ore (Palladium Ore); platinum_ore (Platinum Ore).
Basisrohstoffe: palladium_ore (Palladium Ore); platinum_ore (Platinum Ore).
Zwischenprodukte: catalyst_metal (Catalyst Metal); palladium (Palladium).
Gemeinsam verwendete Vorprodukte in dieser Kette: palladium_ore (Palladium Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"palladium_ore": 3.5, "platinum_ore": 0.5}`.

### `ceramic_components` — Ceramic Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 1.
Alle Vorprodukte: ceramics (Ceramics); clay (Clay); kaolin (Kaolin); magnesite (Magnesite).
Nur indirekte Inputs: clay (Clay); kaolin (Kaolin); magnesite (Magnesite).
Basisrohstoffe: clay (Clay); kaolin (Kaolin); magnesite (Magnesite).
Zwischenprodukte: ceramics (Ceramics).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"clay": 1.0, "kaolin": 0.3333333333333333, "magnesite": 0.3333333333333333}`.

### `chemical_components` — Chemical Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: chemical_feedstock (Chemical Feedstock); crude_oil (Crude Oil); natural_gas (Natural Gas); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid).
Nur indirekte Inputs: crude_oil (Crude Oil); natural_gas (Natural Gas); sulfur (Sulfur).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); sulfur (Sulfur).
Zwischenprodukte: chemical_feedstock (Chemical Feedstock); sulfuric_acid (Sulfuric Acid).
Gemeinsam verwendete Vorprodukte in dieser Kette: natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 1.3333333333333333, "natural_gas": 1.8333333333333333, "sulfur": 1.0}`.

### `composite_components` — Composite Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: carbon_fiber (Carbon Fiber); crude_oil (Crude Oil); graphite (Graphite); industrial_resin (Industrial Resin); natural_gas (Natural Gas).
Nur indirekte Inputs: crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas).
Basisrohstoffe: crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas).
Zwischenprodukte: carbon_fiber (Carbon Fiber); industrial_resin (Industrial Resin).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 4.0, "graphite": 1.0, "natural_gas": 1.5}`.

### `compressor_components` — Compressor Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); iron_ore (Iron Ore); steel (Steel).
Nur indirekte Inputs: bauxite (Bauxite); coal (Coal); iron_ore (Iron Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); iron_ore (Iron Ore).
Zwischenprodukte: aluminum (Aluminum); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 0.75, "iron_ore": 3.0}`.

### `computing_components` — Computing Components
Tiefe 2; Basisrohstoffarten 7; Zwischenprodukte 4.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Zwischenprodukte: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 4.0, "crude_oil": 4.0, "fluorspar": 4.0, "gold_ore": 4.0, "natural_gas": 4.0, "quartz": 16.0, "silver_ore": 4.0}`.

### `concrete_components` — Concrete Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 2.
Alle Vorprodukte: cement (Cement); coal (Coal); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); steel (Steel).
Nur indirekte Inputs: coal (Coal); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone).
Basisrohstoffe: coal (Coal); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone).
Zwischenprodukte: cement (Cement); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.375, "gypsum": 0.3333333333333333, "iron_ore": 1.5, "limestone": 1.3333333333333333}`.

### `control_electronics` — Control Electronics
Tiefe 2; Basisrohstoffarten 7; Zwischenprodukte 4.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Zwischenprodukte: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 2.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "natural_gas": 2.0, "quartz": 8.0, "silver_ore": 2.0}`.

### `copper_wire` — Copper Wire
Tiefe 2; Basisrohstoffarten 1; Zwischenprodukte 1.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore).
Nur indirekte Inputs: copper_ore (Copper Ore).
Basisrohstoffe: copper_ore (Copper Ore).
Zwischenprodukte: copper (Copper).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 1.3333333333333333}`.

### `corrosion_resistant_components` — Corrosion Resistant Components
Tiefe 2; Basisrohstoffarten 5; Zwischenprodukte 2.
Alle Vorprodukte: chromium_ore (Chromium Ore); coal (Coal); galvanized_metal (Galvanized Metal); iron_ore (Iron Ore); nickel_ore (Nickel Ore); stainless_steel (Stainless Steel); zinc_ore (Zinc Ore).
Nur indirekte Inputs: chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); nickel_ore (Nickel Ore); zinc_ore (Zinc Ore).
Basisrohstoffe: chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); nickel_ore (Nickel Ore); zinc_ore (Zinc Ore).
Zwischenprodukte: galvanized_metal (Galvanized Metal); stainless_steel (Stainless Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"chromium_ore": 0.6666666666666666, "coal": 1.0, "iron_ore": 6.666666666666666, "nickel_ore": 0.6666666666666666, "zinc_ore": 2.6666666666666665}`.

### `cutting_tooling` — Cutting Tooling
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: coal (Coal); iron_ore (Iron Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: coal (Coal); iron_ore (Iron Ore); tungsten_ore (Tungsten Ore).
Basisrohstoffe: coal (Coal); iron_ore (Iron Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.75, "iron_ore": 3.0, "tungsten_ore": 2.0}`.

### `display_components` — Display Components
Tiefe 2; Basisrohstoffarten 7; Zwischenprodukte 3.
Alle Vorprodukte: borate_ore (Borate Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); high_purity_silicon (High-Purity Silicon); limestone (Limestone); natural_gas (Natural Gas); polymer (Polymer); quartz (Quartz); silica_sand (Silica Sand).
Nur indirekte Inputs: borate_ore (Borate Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silica_sand (Silica Sand).
Basisrohstoffe: borate_ore (Borate Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silica_sand (Silica Sand).
Zwischenprodukte: glass (Glass); high_purity_silicon (High-Purity Silicon); polymer (Polymer).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"borate_ore": 0.3333333333333333, "crude_oil": 2.5, "fluorspar": 1.0, "limestone": 0.3333333333333333, "natural_gas": 1.5, "quartz": 4.0, "silica_sand": 1.3333333333333333}`.

### `electrical_components` — Electrical Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 3.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); natural_gas (Natural Gas); polymer (Polymer); tin (Tin); tin_ore (Tin Ore).
Nur indirekte Inputs: copper_ore (Copper Ore); crude_oil (Crude Oil); natural_gas (Natural Gas); tin_ore (Tin Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); natural_gas (Natural Gas); tin_ore (Tin Ore).
Zwischenprodukte: copper (Copper); polymer (Polymer); tin (Tin).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 1.0, "crude_oil": 0.75, "natural_gas": 0.25, "tin_ore": 0.9}`.

### `electrolyzer_components` — Electrolyzer Components
Tiefe 2; Basisrohstoffarten 7; Zwischenprodukte 4.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz).
Nur indirekte Inputs: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "copper_ore": 4.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "natural_gas": 2.0, "quartz": 8.0}`.

### `ethanol_components` — Ethanol Components
Tiefe 2; Basisrohstoffarten 2; Zwischenprodukte 1.
Alle Vorprodukte: corn (Corn); fermentation_feedstock (Fermentation Feedstock); sugarcane (Sugarcane).
Nur indirekte Inputs: corn (Corn); sugarcane (Sugarcane).
Basisrohstoffe: corn (Corn); sugarcane (Sugarcane).
Zwischenprodukte: fermentation_feedstock (Fermentation Feedstock).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"corn": 2.0, "sugarcane": 1.0}`.

### `fertilizer_components` — Fertilizer Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: ammonia (Ammonia); natural_gas (Natural Gas); phosphate_rock (Phosphate Rock); phosphoric_acid (Phosphoric Acid); sulfur (Sulfur).
Nur indirekte Inputs: natural_gas (Natural Gas); phosphate_rock (Phosphate Rock); sulfur (Sulfur).
Basisrohstoffe: natural_gas (Natural Gas); phosphate_rock (Phosphate Rock); sulfur (Sulfur).
Zwischenprodukte: ammonia (Ammonia); phosphoric_acid (Phosphoric Acid).
Gemeinsam verwendete Vorprodukte in dieser Kette: natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"natural_gas": 1.25, "phosphate_rock": 1.0, "sulfur": 0.5}`.

### `fiber_components` — Fiber Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: cellulose (Cellulose); crude_oil (Crude Oil); industrial_resin (Industrial Resin); natural_gas (Natural Gas); timber (Timber).
Nur indirekte Inputs: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: cellulose (Cellulose); industrial_resin (Industrial Resin).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 2.0, "natural_gas": 1.5, "timber": 2.0}`.

### `filtration_components` — Filtration Components
Tiefe 2; Basisrohstoffarten 6; Zwischenprodukte 3.
Alle Vorprodukte: ceramics (Ceramics); clay (Clay); crude_oil (Crude Oil); gypsum (Gypsum); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas); polymer (Polymer); processed_gypsum (Processed Gypsum).
Nur indirekte Inputs: clay (Clay); crude_oil (Crude Oil); gypsum (Gypsum); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas).
Basisrohstoffe: clay (Clay); crude_oil (Crude Oil); gypsum (Gypsum); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas).
Zwischenprodukte: ceramics (Ceramics); polymer (Polymer); processed_gypsum (Processed Gypsum).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"clay": 1.0, "crude_oil": 1.5, "gypsum": 1.0, "kaolin": 0.3333333333333333, "magnesite": 0.3333333333333333, "natural_gas": 0.5}`.

### `food_ingredients` — Food Ingredients
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 3.
Alle Vorprodukte: corn (Corn); corn_meal (Corn Meal); flour (Flour); refined_sugar (Refined Sugar); sugarcane (Sugarcane); wheat (Wheat).
Nur indirekte Inputs: corn (Corn); sugarcane (Sugarcane); wheat (Wheat).
Basisrohstoffe: corn (Corn); sugarcane (Sugarcane); wheat (Wheat).
Zwischenprodukte: corn_meal (Corn Meal); flour (Flour); refined_sugar (Refined Sugar).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"corn": 0.5, "sugarcane": 0.5, "wheat": 0.5}`.

### `galvanized_components` — Galvanized Components
Tiefe 2; Basisrohstoffarten 2; Zwischenprodukte 2.
Alle Vorprodukte: galvanized_metal (Galvanized Metal); iron_ore (Iron Ore); zinc (Zinc); zinc_ore (Zinc Ore).
Nur indirekte Inputs: iron_ore (Iron Ore); zinc_ore (Zinc Ore).
Basisrohstoffe: iron_ore (Iron Ore); zinc_ore (Zinc Ore).
Zwischenprodukte: galvanized_metal (Galvanized Metal); zinc (Zinc).
Gemeinsam verwendete Vorprodukte in dieser Kette: zinc_ore (Zinc Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"iron_ore": 1.3333333333333333, "zinc_ore": 2.2333333333333334}`.

### `gas_handling_components` — Gas Handling Components
Tiefe 2; Basisrohstoffarten 1; Zwischenprodukte 2.
Alle Vorprodukte: hydrogen (Hydrogen); industrial_gas (Industrial Gas); natural_gas (Natural Gas).
Nur indirekte Inputs: natural_gas (Natural Gas).
Basisrohstoffe: natural_gas (Natural Gas).
Zwischenprodukte: hydrogen (Hydrogen); industrial_gas (Industrial Gas).
Gemeinsam verwendete Vorprodukte in dieser Kette: natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"natural_gas": 2.5}`.

### `gear_components` — Gear Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: coal (Coal); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); steel (Steel).
Nur indirekte Inputs: coal (Coal); iron_ore (Iron Ore); manganese_ore (Manganese Ore).
Basisrohstoffe: coal (Coal); iron_ore (Iron Ore); manganese_ore (Manganese Ore).
Zwischenprodukte: manganese (Manganese); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.75, "iron_ore": 3.0, "manganese_ore": 0.9}`.

### `glass_panels` — Glass Panels
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 2.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); glass (Glass); limestone (Limestone); silica_sand (Silica Sand).
Nur indirekte Inputs: bauxite (Bauxite); borate_ore (Borate Ore); limestone (Limestone); silica_sand (Silica Sand).
Basisrohstoffe: bauxite (Bauxite); borate_ore (Borate Ore); limestone (Limestone); silica_sand (Silica Sand).
Zwischenprodukte: aluminum (Aluminum); glass (Glass).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 0.9, "borate_ore": 0.3333333333333333, "limestone": 0.3333333333333333, "silica_sand": 1.3333333333333333}`.

### `grid_storage_components` — Grid Storage Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 3.
Alle Vorprodukte: graphite (Graphite); iron_ore (Iron Ore); lithium (Lithium); lithium_ore (Lithium Ore); purified_graphite (Purified Graphite); vanadium_alloy (Vanadium Alloy); vanadium_ore (Vanadium Ore).
Nur indirekte Inputs: graphite (Graphite); iron_ore (Iron Ore); lithium_ore (Lithium Ore); vanadium_ore (Vanadium Ore).
Basisrohstoffe: graphite (Graphite); iron_ore (Iron Ore); lithium_ore (Lithium Ore); vanadium_ore (Vanadium Ore).
Zwischenprodukte: lithium (Lithium); purified_graphite (Purified Graphite); vanadium_alloy (Vanadium Alloy).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"graphite": 1.3333333333333333, "iron_ore": 1.3333333333333333, "lithium_ore": 2.0, "vanadium_ore": 1.3333333333333333}`.

### `hydraulic_components` — Hydraulic Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 2.
Alle Vorprodukte: coal (Coal); crude_oil (Crude Oil); industrial_resin (Industrial Resin); iron_ore (Iron Ore); natural_gas (Natural Gas); steel (Steel).
Nur indirekte Inputs: coal (Coal); crude_oil (Crude Oil); iron_ore (Iron Ore); natural_gas (Natural Gas).
Basisrohstoffe: coal (Coal); crude_oil (Crude Oil); iron_ore (Iron Ore); natural_gas (Natural Gas).
Zwischenprodukte: industrial_resin (Industrial Resin); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.75, "crude_oil": 1.0, "iron_ore": 3.0, "natural_gas": 0.5}`.

### `industrial_fabric` — Industrial Fabric
Tiefe 2; Basisrohstoffarten 5; Zwischenprodukte 3.
Alle Vorprodukte: cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); natural_gas (Natural Gas); natural_rubber (Natural Rubber); polymer (Polymer); processed_rubber (Processed Rubber); sulfur (Sulfur).
Nur indirekte Inputs: cotton (Cotton); crude_oil (Crude Oil); natural_gas (Natural Gas); natural_rubber (Natural Rubber); sulfur (Sulfur).
Basisrohstoffe: cotton (Cotton); crude_oil (Crude Oil); natural_gas (Natural Gas); natural_rubber (Natural Rubber); sulfur (Sulfur).
Zwischenprodukte: cotton_fiber (Cotton Fiber); polymer (Polymer); processed_rubber (Processed Rubber).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"cotton": 1.0, "crude_oil": 1.5, "natural_gas": 0.5, "natural_rubber": 1.0, "sulfur": 0.5}`.

### `insulated_wire` — Insulated Wire
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); natural_gas (Natural Gas); polymer (Polymer).
Nur indirekte Inputs: copper_ore (Copper Ore); crude_oil (Crude Oil); natural_gas (Natural Gas).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); natural_gas (Natural Gas).
Zwischenprodukte: copper (Copper); polymer (Polymer).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 1.0, "crude_oil": 0.75, "natural_gas": 0.25}`.

### `insulation_material` — Insulation Material
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: crude_oil (Crude Oil); gypsum (Gypsum); natural_gas (Natural Gas); polymer (Polymer); processed_gypsum (Processed Gypsum).
Nur indirekte Inputs: crude_oil (Crude Oil); gypsum (Gypsum); natural_gas (Natural Gas).
Basisrohstoffe: crude_oil (Crude Oil); gypsum (Gypsum); natural_gas (Natural Gas).
Zwischenprodukte: polymer (Polymer); processed_gypsum (Processed Gypsum).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 0.75, "gypsum": 0.5, "natural_gas": 0.25}`.

### `iron_components` — Iron Components
Tiefe 2; Basisrohstoffarten 1; Zwischenprodukte 1.
Alle Vorprodukte: iron (Iron); iron_ore (Iron Ore).
Nur indirekte Inputs: iron_ore (Iron Ore).
Basisrohstoffe: iron_ore (Iron Ore).
Zwischenprodukte: iron (Iron).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"iron_ore": 2.0}`.

### `magnetic_components` — Magnetic Components
Tiefe 2; Basisrohstoffarten 2; Zwischenprodukte 2.
Alle Vorprodukte: iron (Iron); iron_ore (Iron Ore); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore).
Nur indirekte Inputs: iron_ore (Iron Ore); rare_earth_ore (Rare Earth Ore).
Basisrohstoffe: iron_ore (Iron Ore); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: iron (Iron); rare_earth_metals (Rare Earth Metals).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"iron_ore": 2.0, "rare_earth_ore": 2.6666666666666665}`.

### `marine_components` — Marine Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 2.
Alle Vorprodukte: coal (Coal); crude_oil (Crude Oil); industrial_resin (Industrial Resin); iron_ore (Iron Ore); natural_gas (Natural Gas); steel (Steel).
Nur indirekte Inputs: coal (Coal); crude_oil (Crude Oil); iron_ore (Iron Ore); natural_gas (Natural Gas).
Basisrohstoffe: coal (Coal); crude_oil (Crude Oil); iron_ore (Iron Ore); natural_gas (Natural Gas).
Zwischenprodukte: industrial_resin (Industrial Resin); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 1.5, "crude_oil": 1.0, "iron_ore": 6.0, "natural_gas": 0.5}`.

### `medical_components` — Medical Components
Tiefe 2; Basisrohstoffarten 8; Zwischenprodukte 3.
Alle Vorprodukte: borate_ore (Borate Ore); chromium_ore (Chromium Ore); coal (Coal); glass (Glass); iron_ore (Iron Ore); limestone (Limestone); nickel_ore (Nickel Ore); platinum (Platinum); platinum_ore (Platinum Ore); silica_sand (Silica Sand); stainless_steel (Stainless Steel).
Nur indirekte Inputs: borate_ore (Borate Ore); chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); limestone (Limestone); nickel_ore (Nickel Ore); platinum_ore (Platinum Ore); silica_sand (Silica Sand).
Basisrohstoffe: borate_ore (Borate Ore); chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); limestone (Limestone); nickel_ore (Nickel Ore); platinum_ore (Platinum Ore); silica_sand (Silica Sand).
Zwischenprodukte: glass (Glass); platinum (Platinum); stainless_steel (Stainless Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"borate_ore": 0.3333333333333333, "chromium_ore": 0.6666666666666666, "coal": 1.0, "iron_ore": 4.0, "limestone": 0.3333333333333333, "nickel_ore": 0.6666666666666666, "platinum_ore": 2.0, "silica_sand": 1.3333333333333333}`.

### `membrane_components` — Membrane Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 3.
Alle Vorprodukte: cellulose (Cellulose); chlorine (Chlorine); crude_oil (Crude Oil); natural_gas (Natural Gas); polymer (Polymer); salt (Salt); timber (Timber).
Nur indirekte Inputs: crude_oil (Crude Oil); natural_gas (Natural Gas); salt (Salt); timber (Timber).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); salt (Salt); timber (Timber).
Zwischenprodukte: cellulose (Cellulose); chlorine (Chlorine); polymer (Polymer).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 2.0, "natural_gas": 1.0, "salt": 1.5, "timber": 1.0}`.

### `memory_components` — Memory Components
Tiefe 2; Basisrohstoffarten 7; Zwischenprodukte 4.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Zwischenprodukte: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 2.0, "crude_oil": 3.0, "fluorspar": 3.0, "gold_ore": 2.0, "natural_gas": 3.0, "quartz": 12.0, "silver_ore": 2.0}`.

### `mining_components` — Mining Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: coal (Coal); iron_ore (Iron Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: coal (Coal); iron_ore (Iron Ore); tungsten_ore (Tungsten Ore).
Basisrohstoffe: coal (Coal); iron_ore (Iron Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.75, "iron_ore": 3.0, "tungsten_ore": 2.0}`.

### `motor_components` — Motor Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 3.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); iron (Iron); iron_ore (Iron Ore); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore).
Nur indirekte Inputs: copper_ore (Copper Ore); iron_ore (Iron Ore); rare_earth_ore (Rare Earth Ore).
Basisrohstoffe: copper_ore (Copper Ore); iron_ore (Iron Ore); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: copper (Copper); iron (Iron); rare_earth_metals (Rare Earth Metals).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 2.0, "iron_ore": 2.0, "rare_earth_ore": 2.6666666666666665}`.

### `network_components` — Network Components
Tiefe 2; Basisrohstoffarten 7; Zwischenprodukte 4.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz).
Nur indirekte Inputs: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "copper_ore": 8.0, "crude_oil": 4.0, "fluorspar": 4.0, "gold_ore": 4.0, "natural_gas": 4.0, "quartz": 16.0}`.

### `nuclear_fuel_components` — Nuclear Fuel Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: borate_ore (Borate Ore); lead_ore (Lead Ore); nuclear_material (Nuclear Material); shielding_material (Shielding Material); uranium_ore (Uranium Ore).
Nur indirekte Inputs: borate_ore (Borate Ore); lead_ore (Lead Ore); uranium_ore (Uranium Ore).
Basisrohstoffe: borate_ore (Borate Ore); lead_ore (Lead Ore); uranium_ore (Uranium Ore).
Zwischenprodukte: nuclear_material (Nuclear Material); shielding_material (Shielding Material).
Gemeinsam verwendete Vorprodukte in dieser Kette: lead_ore (Lead Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"borate_ore": 0.3333333333333333, "lead_ore": 2.333333333333333, "uranium_ore": 3.0}`.

### `nutrition_components` — Nutrition Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 3.
Alle Vorprodukte: fruit (Fruit); fruit_concentrate (Fruit Concentrate); rapeseed (Rapeseed); soy_protein (Soy Protein); soybeans (Soybeans); sugarcane (Sugarcane); vegetable_oil (Vegetable Oil).
Nur indirekte Inputs: fruit (Fruit); rapeseed (Rapeseed); soybeans (Soybeans); sugarcane (Sugarcane).
Basisrohstoffe: fruit (Fruit); rapeseed (Rapeseed); soybeans (Soybeans); sugarcane (Sugarcane).
Zwischenprodukte: fruit_concentrate (Fruit Concentrate); soy_protein (Soy Protein); vegetable_oil (Vegetable Oil).
Gemeinsam verwendete Vorprodukte in dieser Kette: soybeans (Soybeans).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"fruit": 1.5, "rapeseed": 1.0, "soybeans": 3.0, "sugarcane": 0.5}`.

### `packaging_components` — Packaging Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: crude_oil (Crude Oil); natural_gas (Natural Gas); polymer (Polymer); timber (Timber); wood_pulp (Wood Pulp).
Nur indirekte Inputs: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: polymer (Polymer); wood_pulp (Wood Pulp).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 1.0833333333333333, "natural_gas": 0.5833333333333333, "timber": 1.0}`.

### `power_electronics` — Power Electronics
Tiefe 2; Basisrohstoffarten 7; Zwischenprodukte 4.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz).
Nur indirekte Inputs: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "copper_ore": 4.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "natural_gas": 2.0, "quartz": 8.0}`.

### `precision_components` — Precision Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 3.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); iron_ore (Iron Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: bauxite (Bauxite); coal (Coal); iron_ore (Iron Ore); tungsten_ore (Tungsten Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); iron_ore (Iron Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: aluminum (Aluminum); steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 0.75, "iron_ore": 3.0, "tungsten_ore": 2.0}`.

### `processor_components` — Processor Components
Tiefe 2; Basisrohstoffarten 7; Zwischenprodukte 4.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore).
Nur indirekte Inputs: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); rare_earth_metals (Rare Earth Metals).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 2.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 4.0, "natural_gas": 2.0, "quartz": 8.0, "rare_earth_ore": 2.6666666666666665}`.

### `pump_components` — Pump Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: coal (Coal); copper (Copper); copper_ore (Copper Ore); iron_ore (Iron Ore); steel (Steel).
Nur indirekte Inputs: coal (Coal); copper_ore (Copper Ore); iron_ore (Iron Ore).
Basisrohstoffe: coal (Coal); copper_ore (Copper Ore); iron_ore (Iron Ore).
Zwischenprodukte: copper (Copper); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.75, "copper_ore": 2.0, "iron_ore": 3.0}`.

### `rail_components` — Rail Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: coal (Coal); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); steel (Steel).
Nur indirekte Inputs: coal (Coal); iron_ore (Iron Ore); manganese_ore (Manganese Ore).
Basisrohstoffe: coal (Coal); iron_ore (Iron Ore); manganese_ore (Manganese Ore).
Zwischenprodukte: manganese (Manganese); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 1.5, "iron_ore": 6.0, "manganese_ore": 1.8}`.

### `reactor_components` — Reactor Components
Tiefe 2; Basisrohstoffarten 2; Zwischenprodukte 1.
Alle Vorprodukte: lead_ore (Lead Ore); nuclear_material (Nuclear Material); uranium_ore (Uranium Ore).
Nur indirekte Inputs: lead_ore (Lead Ore); uranium_ore (Uranium Ore).
Basisrohstoffe: lead_ore (Lead Ore); uranium_ore (Uranium Ore).
Zwischenprodukte: nuclear_material (Nuclear Material).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"lead_ore": 0.5, "uranium_ore": 1.5}`.

### `refractory_alloy_components` — Refractory Alloy Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 3.
Alle Vorprodukte: molybdenum (Molybdenum); molybdenum_ore (Molybdenum Ore); niobium (Niobium); niobium_ore (Niobium Ore); rare_earth_ore (Rare Earth Ore); superconducting_alloy (Superconducting Alloy); titanium_ore (Titanium Ore).
Nur indirekte Inputs: molybdenum_ore (Molybdenum Ore); niobium_ore (Niobium Ore); rare_earth_ore (Rare Earth Ore); titanium_ore (Titanium Ore).
Basisrohstoffe: molybdenum_ore (Molybdenum Ore); niobium_ore (Niobium Ore); rare_earth_ore (Rare Earth Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: molybdenum (Molybdenum); niobium (Niobium); superconducting_alloy (Superconducting Alloy).
Gemeinsam verwendete Vorprodukte in dieser Kette: niobium_ore (Niobium Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"molybdenum_ore": 2.0, "niobium_ore": 4.0, "rare_earth_ore": 1.5, "titanium_ore": 1.0}`.

### `rubber_blend_components` — Rubber Blend Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 2.
Alle Vorprodukte: crude_oil (Crude Oil); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); sulfur (Sulfur); synthetic_rubber (Synthetic Rubber).
Nur indirekte Inputs: crude_oil (Crude Oil); natural_gas (Natural Gas); natural_rubber (Natural Rubber); sulfur (Sulfur).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); natural_rubber (Natural Rubber); sulfur (Sulfur).
Zwischenprodukte: processed_rubber (Processed Rubber); synthetic_rubber (Synthetic Rubber).
Gemeinsam verwendete Vorprodukte in dieser Kette: sulfur (Sulfur).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 2.0, "natural_gas": 1.0, "natural_rubber": 1.0, "sulfur": 1.5}`.

### `semiconductor_components` — Semiconductor Components
Tiefe 2; Basisrohstoffarten 6; Zwischenprodukte 3.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz).
Nur indirekte Inputs: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Zwischenprodukte: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 2.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "natural_gas": 2.0, "quartz": 8.0}`.

### `semiconductor_die` — Semiconductor Die
Tiefe 2; Basisrohstoffarten 7; Zwischenprodukte 4.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Zwischenprodukte: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 2.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "natural_gas": 2.0, "quartz": 8.0, "silver_ore": 2.0}`.

### `sensor_components` — Sensor Components
Tiefe 2; Basisrohstoffarten 7; Zwischenprodukte 4.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore).
Nur indirekte Inputs: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); rare_earth_metals (Rare Earth Metals).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 2.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "natural_gas": 2.0, "quartz": 8.0, "rare_earth_ore": 2.6666666666666665}`.

### `server_components` — Server Components
Tiefe 2; Basisrohstoffarten 6; Zwischenprodukte 3.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz).
Nur indirekte Inputs: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Zwischenprodukte: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 2.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "natural_gas": 2.0, "quartz": 8.0}`.

### `shielding_components` — Shielding Components
Tiefe 2; Basisrohstoffarten 2; Zwischenprodukte 2.
Alle Vorprodukte: borate_ore (Borate Ore); lead (Lead); lead_ore (Lead Ore); shielding_material (Shielding Material).
Nur indirekte Inputs: borate_ore (Borate Ore); lead_ore (Lead Ore).
Basisrohstoffe: borate_ore (Borate Ore); lead_ore (Lead Ore).
Zwischenprodukte: lead (Lead); shielding_material (Shielding Material).
Gemeinsam verwendete Vorprodukte in dieser Kette: lead_ore (Lead Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"borate_ore": 0.3333333333333333, "lead_ore": 2.2333333333333334}`.

### `silicon_substrate` — Silicon Substrate
Tiefe 2; Basisrohstoffarten 5; Zwischenprodukte 2.
Alle Vorprodukte: borate_ore (Borate Ore); coal (Coal); glass (Glass); limestone (Limestone); quartz (Quartz); silica_sand (Silica Sand); silicon (Silicon).
Nur indirekte Inputs: borate_ore (Borate Ore); coal (Coal); limestone (Limestone); quartz (Quartz); silica_sand (Silica Sand).
Basisrohstoffe: borate_ore (Borate Ore); coal (Coal); limestone (Limestone); quartz (Quartz); silica_sand (Silica Sand).
Zwischenprodukte: glass (Glass); silicon (Silicon).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"borate_ore": 0.3333333333333333, "coal": 1.0, "limestone": 0.3333333333333333, "quartz": 4.0, "silica_sand": 1.3333333333333333}`.

### `solar_components` — Solar Components
Tiefe 2; Basisrohstoffarten 8; Zwischenprodukte 3.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); high_purity_silicon (High-Purity Silicon); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silica_sand (Silica Sand).
Nur indirekte Inputs: bauxite (Bauxite); borate_ore (Borate Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silica_sand (Silica Sand).
Basisrohstoffe: bauxite (Bauxite); borate_ore (Borate Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silica_sand (Silica Sand).
Zwischenprodukte: aluminum (Aluminum); glass (Glass); high_purity_silicon (High-Purity Silicon).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "borate_ore": 0.3333333333333333, "crude_oil": 1.0, "fluorspar": 1.0, "limestone": 0.3333333333333333, "natural_gas": 1.0, "quartz": 4.0, "silica_sand": 1.3333333333333333}`.

### `stainless_components` — Stainless Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 1.
Alle Vorprodukte: chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); nickel_ore (Nickel Ore); stainless_steel (Stainless Steel).
Nur indirekte Inputs: chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); nickel_ore (Nickel Ore).
Basisrohstoffe: chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); nickel_ore (Nickel Ore).
Zwischenprodukte: stainless_steel (Stainless Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"chromium_ore": 0.6666666666666666, "coal": 1.0, "iron_ore": 4.0, "nickel_ore": 0.6666666666666666}`.

### `steel_components` — Steel Components
Tiefe 2; Basisrohstoffarten 2; Zwischenprodukte 1.
Alle Vorprodukte: coal (Coal); iron_ore (Iron Ore); steel (Steel).
Nur indirekte Inputs: coal (Coal); iron_ore (Iron Ore).
Basisrohstoffe: coal (Coal); iron_ore (Iron Ore).
Zwischenprodukte: steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.75, "iron_ore": 3.0}`.

### `storage_components` — Storage Components
Tiefe 2; Basisrohstoffarten 7; Zwischenprodukte 4.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz).
Nur indirekte Inputs: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "copper_ore": 4.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "natural_gas": 2.0, "quartz": 8.0}`.

### `structural_components` — Structural Components
Tiefe 2; Basisrohstoffarten 4; Zwischenprodukte 2.
Alle Vorprodukte: cement (Cement); coal (Coal); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); steel (Steel).
Nur indirekte Inputs: coal (Coal); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone).
Basisrohstoffe: coal (Coal); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone).
Zwischenprodukte: cement (Cement); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 1.125, "gypsum": 0.16666666666666666, "iron_ore": 4.5, "limestone": 0.6666666666666666}`.

### `sweetener_components` — Sweetener Components
Tiefe 2; Basisrohstoffarten 5; Zwischenprodukte 3.
Alle Vorprodukte: fruit (Fruit); organic_feedstock (Organic Feedstock); potatoes (Potatoes); raw_sugar (Raw Sugar); soy_oil (Soy Oil); soybeans (Soybeans); sugarcane (Sugarcane); wheat (Wheat).
Nur indirekte Inputs: fruit (Fruit); potatoes (Potatoes); soybeans (Soybeans); sugarcane (Sugarcane); wheat (Wheat).
Basisrohstoffe: fruit (Fruit); potatoes (Potatoes); soybeans (Soybeans); sugarcane (Sugarcane); wheat (Wheat).
Zwischenprodukte: organic_feedstock (Organic Feedstock); raw_sugar (Raw Sugar); soy_oil (Soy Oil).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"fruit": 0.5, "potatoes": 0.5, "soybeans": 2.0, "sugarcane": 2.0, "wheat": 0.5}`.

### `technical_textile` — Technical Textile
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); natural_gas (Natural Gas); polymer (Polymer).
Nur indirekte Inputs: cotton (Cotton); crude_oil (Crude Oil); natural_gas (Natural Gas).
Basisrohstoffe: cotton (Cotton); crude_oil (Crude Oil); natural_gas (Natural Gas).
Zwischenprodukte: cotton_fiber (Cotton Fiber); polymer (Polymer).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"cotton": 0.5, "crude_oil": 0.75, "natural_gas": 0.25}`.

### `telecom_components` — Telecom Components
Tiefe 2; Basisrohstoffarten 7; Zwischenprodukte 4.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore).
Nur indirekte Inputs: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); rare_earth_metals (Rare Earth Metals).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 4.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "natural_gas": 2.0, "quartz": 8.0, "rare_earth_ore": 2.6666666666666665}`.

### `tire_components` — Tire Components
Tiefe 2; Basisrohstoffarten 5; Zwischenprodukte 2.
Alle Vorprodukte: carbon_fiber (Carbon Fiber); crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); sulfur (Sulfur).
Nur indirekte Inputs: crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas); natural_rubber (Natural Rubber); sulfur (Sulfur).
Basisrohstoffe: crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas); natural_rubber (Natural Rubber); sulfur (Sulfur).
Zwischenprodukte: carbon_fiber (Carbon Fiber); processed_rubber (Processed Rubber).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 3.0, "graphite": 1.0, "natural_gas": 1.0, "natural_rubber": 2.0, "sulfur": 1.0}`.

### `titanium_components` — Titanium Components
Tiefe 2; Basisrohstoffarten 1; Zwischenprodukte 1.
Alle Vorprodukte: titanium (Titanium); titanium_ore (Titanium Ore).
Nur indirekte Inputs: titanium_ore (Titanium Ore).
Basisrohstoffe: titanium_ore (Titanium Ore).
Zwischenprodukte: titanium (Titanium).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"titanium_ore": 2.0}`.

### `transformer_components` — Transformer Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: coal (Coal); copper (Copper); copper_ore (Copper Ore); iron_ore (Iron Ore); steel (Steel).
Nur indirekte Inputs: coal (Coal); copper_ore (Copper Ore); iron_ore (Iron Ore).
Basisrohstoffe: coal (Coal); copper_ore (Copper Ore); iron_ore (Iron Ore).
Zwischenprodukte: copper (Copper); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.75, "copper_ore": 2.0, "iron_ore": 3.0}`.

### `turbine_components` — Turbine Components
Tiefe 2; Basisrohstoffarten 5; Zwischenprodukte 2.
Alle Vorprodukte: coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); titanium (Titanium); titanium_ore (Titanium Ore).
Nur indirekte Inputs: coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_ore (Nickel Ore); titanium_ore (Titanium Ore).
Basisrohstoffe: coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_ore (Nickel Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: nickel_alloy (Nickel Alloy); titanium (Titanium).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.3333333333333333, "iron_ore": 2.0, "molybdenum_ore": 0.6666666666666666, "nickel_ore": 2.0, "titanium_ore": 2.0}`.

### `vehicle_components` — Vehicle Components
Tiefe 2; Basisrohstoffarten 5; Zwischenprodukte 3.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); iron_ore (Iron Ore); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); steel (Steel); sulfur (Sulfur).
Nur indirekte Inputs: bauxite (Bauxite); coal (Coal); iron_ore (Iron Ore); natural_rubber (Natural Rubber); sulfur (Sulfur).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); iron_ore (Iron Ore); natural_rubber (Natural Rubber); sulfur (Sulfur).
Zwischenprodukte: aluminum (Aluminum); processed_rubber (Processed Rubber); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 0.75, "iron_ore": 3.0, "natural_rubber": 1.0, "sulfur": 0.5}`.

### `wind_components` — Wind Components
Tiefe 2; Basisrohstoffarten 8; Zwischenprodukte 4.
Alle Vorprodukte: carbon_fiber (Carbon Fiber); coal (Coal); crude_oil (Crude Oil); graphite (Graphite); industrial_resin (Industrial Resin); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); titanium (Titanium); titanium_ore (Titanium Ore).
Nur indirekte Inputs: coal (Coal); crude_oil (Crude Oil); graphite (Graphite); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_ore (Nickel Ore); titanium_ore (Titanium Ore).
Basisrohstoffe: coal (Coal); crude_oil (Crude Oil); graphite (Graphite); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_ore (Nickel Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: carbon_fiber (Carbon Fiber); industrial_resin (Industrial Resin); nickel_alloy (Nickel Alloy); titanium (Titanium).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.3333333333333333, "crude_oil": 4.0, "graphite": 1.0, "iron_ore": 2.0, "molybdenum_ore": 0.6666666666666666, "natural_gas": 1.5, "nickel_ore": 2.0, "titanium_ore": 2.0}`.

### `wooden_components` — Wooden Components
Tiefe 2; Basisrohstoffarten 3; Zwischenprodukte 2.
Alle Vorprodukte: crude_oil (Crude Oil); lumber (Lumber); natural_gas (Natural Gas); timber (Timber); treated_lumber (Treated Lumber).
Nur indirekte Inputs: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: lumber (Lumber); treated_lumber (Treated Lumber).
Gemeinsam verwendete Vorprodukte in dieser Kette: timber (Timber).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 0.3333333333333333, "natural_gas": 0.16666666666666666, "timber": 1.5}`.

### `ai_accelerator` — AI Accelerator
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 7.
Alle Vorprodukte: ai_compute_components (AI Compute Components); aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); power_electronics (Power Electronics); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: ai_compute_components (AI Compute Components); aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); power_electronics (Power Electronics); rare_earth_metals (Rare Earth Metals).
Gemeinsam verwendete Vorprodukte in dieser Kette: gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "copper_ore": 4.0, "crude_oil": 6.0, "fluorspar": 6.0, "gold_ore": 6.0, "natural_gas": 6.0, "quartz": 24.0, "rare_earth_ore": 5.333333333333333}`.

### `ai_server` — AI Server
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 8.
Alle Vorprodukte: ai_compute_components (AI Compute Components); aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); network_components (Network Components); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); server_components (Server Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: ai_compute_components (AI Compute Components); aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); network_components (Network Components); rare_earth_metals (Rare Earth Metals); server_components (Server Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "copper_ore": 10.0, "crude_oil": 8.0, "fluorspar": 8.0, "gold_ore": 8.0, "natural_gas": 8.0, "quartz": 32.0, "rare_earth_ore": 2.6666666666666665}`.

### `advanced_aircraft` — Advanced Aircraft
Tiefe 3; Basisrohstoffarten 13; Zwischenprodukte 10.
Alle Vorprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); avionics_components (Avionics Components); bauxite (Bauxite); carbon_fiber (Carbon Fiber); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); quartz (Quartz); titanium (Titanium); titanium_ore (Titanium Ore); turbine_components (Turbine Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); quartz (Quartz); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_ore (Nickel Ore); quartz (Quartz); titanium_ore (Titanium Ore).
Zwischenprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); avionics_components (Avionics Components); carbon_fiber (Carbon Fiber); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); nickel_alloy (Nickel Alloy); titanium (Titanium); turbine_components (Turbine Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); crude_oil (Crude Oil); natural_gas (Natural Gas); titanium (Titanium).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 5.4, "coal": 0.3333333333333333, "copper_ore": 4.0, "crude_oil": 10.0, "fluorspar": 4.0, "gold_ore": 4.0, "graphite": 2.0, "iron_ore": 2.0, "molybdenum_ore": 0.6666666666666666, "natural_gas": 6.0, "nickel_ore": 2.0, "quartz": 16.0, "titanium_ore": 6.0}`.

### `advanced_fertilizer` — Advanced Fertilizer
Tiefe 3; Basisrohstoffarten 5; Zwischenprodukte 7.
Alle Vorprodukte: agricultural_chemicals (Agricultural Chemicals); ammonia (Ammonia); chemical_feedstock (Chemical Feedstock); chlorine (Chlorine); crude_oil (Crude Oil); fertilizer_components (Fertilizer Components); natural_gas (Natural Gas); phosphate_rock (Phosphate Rock); phosphoric_acid (Phosphoric Acid); salt (Salt); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid).
Nur indirekte Inputs: ammonia (Ammonia); chemical_feedstock (Chemical Feedstock); chlorine (Chlorine); crude_oil (Crude Oil); natural_gas (Natural Gas); phosphate_rock (Phosphate Rock); phosphoric_acid (Phosphoric Acid); salt (Salt); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); phosphate_rock (Phosphate Rock); salt (Salt); sulfur (Sulfur).
Zwischenprodukte: agricultural_chemicals (Agricultural Chemicals); ammonia (Ammonia); chemical_feedstock (Chemical Feedstock); chlorine (Chlorine); fertilizer_components (Fertilizer Components); phosphoric_acid (Phosphoric Acid); sulfuric_acid (Sulfuric Acid).
Gemeinsam verwendete Vorprodukte in dieser Kette: natural_gas (Natural Gas); sulfur (Sulfur).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 0.6666666666666666, "natural_gas": 3.6666666666666665, "phosphate_rock": 2.0, "salt": 1.5, "sulfur": 2.0}`.

### `advanced_furnace` — Advanced Furnace
Tiefe 3; Basisrohstoffarten 14; Zwischenprodukte 9.
Alle Vorprodukte: ceramic_components (Ceramic Components); ceramics (Ceramics); chromium_ore (Chromium Ore); clay (Clay); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas); nickel_ore (Nickel Ore); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); stainless_components (Stainless Components); stainless_steel (Stainless Steel).
Nur indirekte Inputs: ceramics (Ceramics); chromium_ore (Chromium Ore); clay (Clay); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas); nickel_ore (Nickel Ore); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); stainless_steel (Stainless Steel).
Basisrohstoffe: chromium_ore (Chromium Ore); clay (Clay); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas); nickel_ore (Nickel Ore); quartz (Quartz); silver_ore (Silver Ore).
Zwischenprodukte: ceramic_components (Ceramic Components); ceramics (Ceramics); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); silver (Silver); stainless_components (Stainless Components); stainless_steel (Stainless Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"chromium_ore": 1.3333333333333333, "clay": 1.0, "coal": 2.0, "copper_ore": 2.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "iron_ore": 8.0, "kaolin": 0.3333333333333333, "magnesite": 0.3333333333333333, "natural_gas": 2.0, "nickel_ore": 1.3333333333333333, "quartz": 8.0, "silver_ore": 2.0}`.

### `advanced_industrial_robot` — Advanced Industrial Robot
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 7.
Alle Vorprodukte: ai_compute_components (AI Compute Components); autonomous_components (Autonomous Components); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: ai_compute_components (AI Compute Components); autonomous_components (Autonomous Components); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); rare_earth_metals (Rare Earth Metals).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 6.0, "crude_oil": 6.0, "fluorspar": 6.0, "gold_ore": 4.0, "natural_gas": 6.0, "quartz": 24.0, "rare_earth_ore": 10.666666666666666}`.

### `advanced_medical_equipment` — Advanced Medical Equipment
Tiefe 3; Basisrohstoffarten 18; Zwischenprodukte 15.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); chromium_ore (Chromium Ore); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); medical_components (Medical Components); natural_gas (Natural Gas); nickel_ore (Nickel Ore); platinum (Platinum); platinum_ore (Platinum Ore); precision_components (Precision Components); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); silica_sand (Silica Sand); silver (Silver); silver_ore (Silver Ore); stainless_steel (Stainless Steel); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); chromium_ore (Chromium Ore); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); nickel_ore (Nickel Ore); platinum (Platinum); platinum_ore (Platinum Ore); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silica_sand (Silica Sand); silver (Silver); silver_ore (Silver Ore); stainless_steel (Stainless Steel); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: bauxite (Bauxite); borate_ore (Borate Ore); chromium_ore (Chromium Ore); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); nickel_ore (Nickel Ore); platinum_ore (Platinum Ore); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silica_sand (Silica Sand); silver_ore (Silver Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: aluminum (Aluminum); control_electronics (Control Electronics); copper (Copper); glass (Glass); gold (Gold); high_purity_silicon (High-Purity Silicon); medical_components (Medical Components); platinum (Platinum); precision_components (Precision Components); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); silver (Silver); stainless_steel (Stainless Steel); steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: coal (Coal); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "borate_ore": 0.6666666666666666, "chromium_ore": 1.3333333333333333, "coal": 2.75, "copper_ore": 4.0, "crude_oil": 4.0, "fluorspar": 4.0, "gold_ore": 4.0, "iron_ore": 11.0, "limestone": 0.6666666666666666, "natural_gas": 4.0, "nickel_ore": 1.3333333333333333, "platinum_ore": 4.0, "quartz": 16.0, "rare_earth_ore": 2.6666666666666665, "silica_sand": 2.6666666666666665, "silver_ore": 2.0, "tungsten_ore": 2.0}`.

### `advanced_protective_equipment` — Advanced Protective Equipment
Tiefe 3; Basisrohstoffarten 11; Zwischenprodukte 12.
Alle Vorprodukte: carbon_fiber (Carbon Fiber); composite_components (Composite Components); copper (Copper); copper_ore (Copper Ore); cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); industrial_fabric (Industrial Fabric); industrial_resin (Industrial Resin); natural_gas (Natural Gas); natural_rubber (Natural Rubber); polymer (Polymer); processed_rubber (Processed Rubber); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); sulfur (Sulfur).
Nur indirekte Inputs: carbon_fiber (Carbon Fiber); copper (Copper); copper_ore (Copper Ore); cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); industrial_resin (Industrial Resin); natural_gas (Natural Gas); natural_rubber (Natural Rubber); polymer (Polymer); processed_rubber (Processed Rubber); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sulfur (Sulfur).
Basisrohstoffe: copper_ore (Copper Ore); cotton (Cotton); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); natural_gas (Natural Gas); natural_rubber (Natural Rubber); quartz (Quartz); rare_earth_ore (Rare Earth Ore); sulfur (Sulfur).
Zwischenprodukte: carbon_fiber (Carbon Fiber); composite_components (Composite Components); copper (Copper); cotton_fiber (Cotton Fiber); gold (Gold); high_purity_silicon (High-Purity Silicon); industrial_fabric (Industrial Fabric); industrial_resin (Industrial Resin); polymer (Polymer); processed_rubber (Processed Rubber); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 2.0, "cotton": 2.0, "crude_oil": 9.0, "fluorspar": 2.0, "gold_ore": 2.0, "graphite": 1.0, "natural_gas": 4.5, "natural_rubber": 2.0, "quartz": 8.0, "rare_earth_ore": 2.6666666666666665, "sulfur": 1.0}`.

### `advanced_semiconductor_equipment` — Advanced Semiconductor Equipment
Tiefe 3; Basisrohstoffarten 15; Zwischenprodukte 13.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); ceramic_components (Ceramic Components); ceramics (Ceramics); clay (Clay); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas); precision_components (Precision Components); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); ceramics (Ceramics); clay (Clay); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: bauxite (Bauxite); clay (Clay); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silver_ore (Silver Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: aluminum (Aluminum); ceramic_components (Ceramic Components); ceramics (Ceramics); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); precision_components (Precision Components); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); silver (Silver); steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "clay": 1.0, "coal": 1.5, "copper_ore": 4.0, "crude_oil": 4.0, "fluorspar": 4.0, "gold_ore": 4.0, "iron_ore": 6.0, "kaolin": 0.3333333333333333, "magnesite": 0.3333333333333333, "natural_gas": 4.0, "quartz": 16.0, "rare_earth_ore": 2.6666666666666665, "silver_ore": 2.0, "tungsten_ore": 4.0}`.

### `animal_feed` — Animal Feed
Tiefe 3; Basisrohstoffarten 6; Zwischenprodukte 8.
Alle Vorprodukte: corn (Corn); corn_meal (Corn Meal); flour (Flour); food_ingredients (Food Ingredients); fruit (Fruit); fruit_concentrate (Fruit Concentrate); nutrition_components (Nutrition Components); rapeseed (Rapeseed); refined_sugar (Refined Sugar); soy_protein (Soy Protein); soybeans (Soybeans); sugarcane (Sugarcane); vegetable_oil (Vegetable Oil); wheat (Wheat).
Nur indirekte Inputs: corn (Corn); corn_meal (Corn Meal); flour (Flour); fruit (Fruit); fruit_concentrate (Fruit Concentrate); rapeseed (Rapeseed); refined_sugar (Refined Sugar); soy_protein (Soy Protein); soybeans (Soybeans); sugarcane (Sugarcane); vegetable_oil (Vegetable Oil); wheat (Wheat).
Basisrohstoffe: corn (Corn); fruit (Fruit); rapeseed (Rapeseed); soybeans (Soybeans); sugarcane (Sugarcane); wheat (Wheat).
Zwischenprodukte: corn_meal (Corn Meal); flour (Flour); food_ingredients (Food Ingredients); fruit_concentrate (Fruit Concentrate); nutrition_components (Nutrition Components); refined_sugar (Refined Sugar); soy_protein (Soy Protein); vegetable_oil (Vegetable Oil).
Gemeinsam verwendete Vorprodukte in dieser Kette: soybeans (Soybeans); sugarcane (Sugarcane).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"corn": 1.0, "fruit": 1.5, "rapeseed": 1.0, "soybeans": 3.0, "sugarcane": 1.5, "wheat": 1.0}`.

### `autonomous_aircraft` — Autonomous Aircraft
Tiefe 3; Basisrohstoffarten 10; Zwischenprodukte 11.
Alle Vorprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); autonomous_components (Autonomous Components); avionics_components (Avionics Components); bauxite (Bauxite); carbon_fiber (Carbon Fiber); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); titanium (Titanium); titanium_ore (Titanium Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); autonomous_components (Autonomous Components); avionics_components (Avionics Components); carbon_fiber (Carbon Fiber); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); titanium (Titanium).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); copper (Copper); crude_oil (Crude Oil); gold (Gold); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); rare_earth_metals (Rare Earth Metals).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 5.4, "copper_ore": 8.0, "crude_oil": 13.0, "fluorspar": 7.0, "gold_ore": 6.0, "graphite": 2.0, "natural_gas": 9.0, "quartz": 28.0, "rare_earth_ore": 5.333333333333333, "titanium_ore": 4.0}`.

### `autonomous_cargo_ship` — Autonomous Cargo Ship
Tiefe 3; Basisrohstoffarten 10; Zwischenprodukte 11.
Alle Vorprodukte: aluminum (Aluminum); autonomous_components (Autonomous Components); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); industrial_resin (Industrial Resin); iron_ore (Iron Ore); marine_components (Marine Components); natural_gas (Natural Gas); network_components (Network Components); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); steel (Steel).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); industrial_resin (Industrial Resin); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: aluminum (Aluminum); autonomous_components (Autonomous Components); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); industrial_resin (Industrial Resin); marine_components (Marine Components); network_components (Network Components); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); crude_oil (Crude Oil); gold (Gold); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); rare_earth_metals (Rare Earth Metals).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 3.0, "copper_ore": 12.0, "crude_oil": 9.0, "fluorspar": 7.0, "gold_ore": 6.0, "iron_ore": 12.0, "natural_gas": 8.0, "quartz": 28.0, "rare_earth_ore": 5.333333333333333}`.

### `autonomous_control_system` — Autonomous Control System
Tiefe 3; Basisrohstoffarten 10; Zwischenprodukte 11.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron (Iron); iron_ore (Iron Ore); magnetic_components (Magnetic Components); natural_gas (Natural Gas); power_electronics (Power Electronics); processor_components (Processor Components); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron (Iron); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silver_ore (Silver Ore).
Zwischenprodukte: aluminum (Aluminum); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); iron (Iron); magnetic_components (Magnetic Components); power_electronics (Power Electronics); processor_components (Processor Components); rare_earth_metals (Rare Earth Metals); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); rare_earth_metals (Rare Earth Metals).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "copper_ore": 12.0, "crude_oil": 10.0, "fluorspar": 10.0, "gold_ore": 14.0, "iron_ore": 2.0, "natural_gas": 10.0, "quartz": 40.0, "rare_earth_ore": 8.0, "silver_ore": 4.0}`.

### `autonomous_freight_train` — Autonomous Freight Train
Tiefe 3; Basisrohstoffarten 11; Zwischenprodukte 10.
Alle Vorprodukte: aluminum (Aluminum); autonomous_components (Autonomous Components); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); natural_gas (Natural Gas); network_components (Network Components); quartz (Quartz); rail_components (Rail Components); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); manganese_ore (Manganese Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: aluminum (Aluminum); autonomous_components (Autonomous Components); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); manganese (Manganese); network_components (Network Components); rail_components (Rail Components); rare_earth_metals (Rare Earth Metals); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 3.0, "copper_ore": 10.0, "crude_oil": 5.0, "fluorspar": 5.0, "gold_ore": 4.0, "iron_ore": 12.0, "manganese_ore": 3.6, "natural_gas": 5.0, "quartz": 20.0, "rare_earth_ore": 2.6666666666666665}`.

### `autonomous_mobile_robot` — Autonomous Mobile Robot
Tiefe 3; Basisrohstoffarten 13; Zwischenprodukte 11.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); silver (Silver); silver_ore (Silver Ore); steel (Steel); sulfur (Sulfur); vehicle_components (Vehicle Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore); steel (Steel); sulfur (Sulfur).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silver_ore (Silver Ore); sulfur (Sulfur).
Zwischenprodukte: aluminum (Aluminum); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); processed_rubber (Processed Rubber); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); silver (Silver); steel (Steel); vehicle_components (Vehicle Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 0.75, "copper_ore": 4.0, "crude_oil": 4.0, "fluorspar": 4.0, "gold_ore": 4.0, "iron_ore": 3.0, "natural_gas": 4.0, "natural_rubber": 1.0, "quartz": 16.0, "rare_earth_ore": 2.6666666666666665, "silver_ore": 2.0, "sulfur": 0.5}`.

### `autonomous_vehicle` — Autonomous Vehicle
Tiefe 3; Basisrohstoffarten 12; Zwischenprodukte 11.
Alle Vorprodukte: ai_compute_components (AI Compute Components); aluminum (Aluminum); autonomous_components (Autonomous Components); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); steel (Steel); sulfur (Sulfur); vehicle_components (Vehicle Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel); sulfur (Sulfur).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); quartz (Quartz); rare_earth_ore (Rare Earth Ore); sulfur (Sulfur).
Zwischenprodukte: ai_compute_components (AI Compute Components); aluminum (Aluminum); autonomous_components (Autonomous Components); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); processed_rubber (Processed Rubber); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); steel (Steel); vehicle_components (Vehicle Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); rare_earth_metals (Rare Earth Metals).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 0.75, "copper_ore": 4.0, "crude_oil": 5.0, "fluorspar": 5.0, "gold_ore": 4.0, "iron_ore": 3.0, "natural_gas": 5.0, "natural_rubber": 1.0, "quartz": 20.0, "rare_earth_ore": 8.0, "sulfur": 0.5}`.

### `bakery_products` — Bakery Products
Tiefe 3; Basisrohstoffarten 6; Zwischenprodukte 7.
Alle Vorprodukte: corn (Corn); corn_meal (Corn Meal); crude_oil (Crude Oil); flour (Flour); food_ingredients (Food Ingredients); natural_gas (Natural Gas); packaging_components (Packaging Components); polymer (Polymer); refined_sugar (Refined Sugar); sugarcane (Sugarcane); timber (Timber); wheat (Wheat); wood_pulp (Wood Pulp).
Nur indirekte Inputs: corn (Corn); corn_meal (Corn Meal); crude_oil (Crude Oil); flour (Flour); natural_gas (Natural Gas); polymer (Polymer); refined_sugar (Refined Sugar); sugarcane (Sugarcane); timber (Timber); wheat (Wheat); wood_pulp (Wood Pulp).
Basisrohstoffe: corn (Corn); crude_oil (Crude Oil); natural_gas (Natural Gas); sugarcane (Sugarcane); timber (Timber); wheat (Wheat).
Zwischenprodukte: corn_meal (Corn Meal); flour (Flour); food_ingredients (Food Ingredients); packaging_components (Packaging Components); polymer (Polymer); refined_sugar (Refined Sugar); wood_pulp (Wood Pulp).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"corn": 1.0, "crude_oil": 1.0833333333333333, "natural_gas": 0.5833333333333333, "sugarcane": 1.0, "timber": 1.0, "wheat": 1.0}`.

### `basic_chip` — Basic Chip
Tiefe 3; Basisrohstoffarten 10; Zwischenprodukte 8.
Alle Vorprodukte: borate_ore (Borate Ore); coal (Coal); copper (Copper); copper_ore (Copper Ore); copper_wire (Copper Wire); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); semiconductor_components (Semiconductor Components); silica_sand (Silica Sand); silicon (Silicon); silicon_substrate (Silicon Substrate).
Nur indirekte Inputs: borate_ore (Borate Ore); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silica_sand (Silica Sand); silicon (Silicon).
Basisrohstoffe: borate_ore (Borate Ore); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silica_sand (Silica Sand).
Zwischenprodukte: copper (Copper); copper_wire (Copper Wire); glass (Glass); gold (Gold); high_purity_silicon (High-Purity Silicon); semiconductor_components (Semiconductor Components); silicon (Silicon); silicon_substrate (Silicon Substrate).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); quartz (Quartz).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"borate_ore": 0.3333333333333333, "coal": 1.0, "copper_ore": 3.333333333333333, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "limestone": 0.3333333333333333, "natural_gas": 2.0, "quartz": 12.0, "silica_sand": 1.3333333333333333}`.

### `bio_based_chemicals` — Bio-Based Chemicals
Tiefe 3; Basisrohstoffarten 5; Zwischenprodukte 6.
Alle Vorprodukte: bio_lubricant (Bio-Lubricant); bio_material_components (Bio-Material Components); cellulose (Cellulose); chemical_components (Chemical Components); chemical_feedstock (Chemical Feedstock); crude_oil (Crude Oil); natural_gas (Natural Gas); rapeseed (Rapeseed); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid); timber (Timber).
Nur indirekte Inputs: bio_lubricant (Bio-Lubricant); cellulose (Cellulose); chemical_feedstock (Chemical Feedstock); crude_oil (Crude Oil); natural_gas (Natural Gas); rapeseed (Rapeseed); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid); timber (Timber).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); rapeseed (Rapeseed); sulfur (Sulfur); timber (Timber).
Zwischenprodukte: bio_lubricant (Bio-Lubricant); bio_material_components (Bio-Material Components); cellulose (Cellulose); chemical_components (Chemical Components); chemical_feedstock (Chemical Feedstock); sulfuric_acid (Sulfuric Acid).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 2.333333333333333, "natural_gas": 3.833333333333333, "rapeseed": 2.0, "sulfur": 1.0, "timber": 2.0}`.

### `biodiesel` — Biodiesel
Tiefe 3; Basisrohstoffarten 4; Zwischenprodukte 3.
Alle Vorprodukte: biodiesel_feedstock (Biodiesel Feedstock); chemical_feedstock (Chemical Feedstock); crude_oil (Crude Oil); natural_gas (Natural Gas); rapeseed (Rapeseed); soybeans (Soybeans); vegetable_oil (Vegetable Oil).
Nur indirekte Inputs: chemical_feedstock (Chemical Feedstock); crude_oil (Crude Oil); natural_gas (Natural Gas); rapeseed (Rapeseed); soybeans (Soybeans); vegetable_oil (Vegetable Oil).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); rapeseed (Rapeseed); soybeans (Soybeans).
Zwischenprodukte: biodiesel_feedstock (Biodiesel Feedstock); chemical_feedstock (Chemical Feedstock); vegetable_oil (Vegetable Oil).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 1.3333333333333333, "natural_gas": 1.3333333333333333, "rapeseed": 4.0, "soybeans": 4.0}`.

### `biofuel` — Biofuel
Tiefe 3; Basisrohstoffarten 5; Zwischenprodukte 5.
Alle Vorprodukte: chemical_components (Chemical Components); chemical_feedstock (Chemical Feedstock); corn (Corn); crude_oil (Crude Oil); ethanol_components (Ethanol Components); fermentation_feedstock (Fermentation Feedstock); natural_gas (Natural Gas); sugarcane (Sugarcane); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid).
Nur indirekte Inputs: chemical_feedstock (Chemical Feedstock); corn (Corn); crude_oil (Crude Oil); fermentation_feedstock (Fermentation Feedstock); natural_gas (Natural Gas); sugarcane (Sugarcane); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid).
Basisrohstoffe: corn (Corn); crude_oil (Crude Oil); natural_gas (Natural Gas); sugarcane (Sugarcane); sulfur (Sulfur).
Zwischenprodukte: chemical_components (Chemical Components); chemical_feedstock (Chemical Feedstock); ethanol_components (Ethanol Components); fermentation_feedstock (Fermentation Feedstock); sulfuric_acid (Sulfuric Acid).
Gemeinsam verwendete Vorprodukte in dieser Kette: natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"corn": 4.0, "crude_oil": 1.3333333333333333, "natural_gas": 1.8333333333333333, "sugarcane": 2.0, "sulfur": 1.0}`.

### `bioplastic` — Bioplastic
Tiefe 3; Basisrohstoffarten 6; Zwischenprodukte 6.
Alle Vorprodukte: bio_composite (Bio-Composite); biopolymer (Biopolymer); cellulose (Cellulose); corn (Corn); crude_oil (Crude Oil); fermentation_feedstock (Fermentation Feedstock); industrial_resin (Industrial Resin); natural_gas (Natural Gas); potatoes (Potatoes); starch (Starch); sugarcane (Sugarcane); timber (Timber).
Nur indirekte Inputs: cellulose (Cellulose); corn (Corn); crude_oil (Crude Oil); fermentation_feedstock (Fermentation Feedstock); industrial_resin (Industrial Resin); natural_gas (Natural Gas); potatoes (Potatoes); starch (Starch); sugarcane (Sugarcane); timber (Timber).
Basisrohstoffe: corn (Corn); crude_oil (Crude Oil); natural_gas (Natural Gas); potatoes (Potatoes); sugarcane (Sugarcane); timber (Timber).
Zwischenprodukte: bio_composite (Bio-Composite); biopolymer (Biopolymer); cellulose (Cellulose); fermentation_feedstock (Fermentation Feedstock); industrial_resin (Industrial Resin); starch (Starch).
Gemeinsam verwendete Vorprodukte in dieser Kette: corn (Corn); crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"corn": 6.0, "crude_oil": 1.5, "natural_gas": 1.0, "potatoes": 2.0, "sugarcane": 1.0, "timber": 1.0}`.

### `cnc_machine` — CNC Machine
Tiefe 3; Basisrohstoffarten 13; Zwischenprodukte 11.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); cement (Cement); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); precision_components (Precision Components); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); steel (Steel); structural_components (Structural Components); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); cement (Cement); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: aluminum (Aluminum); cement (Cement); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); precision_components (Precision Components); silver (Silver); steel (Steel); structural_components (Structural Components); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "coal": 2.625, "copper_ore": 2.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "gypsum": 0.16666666666666666, "iron_ore": 10.5, "limestone": 0.6666666666666666, "natural_gas": 2.0, "quartz": 8.0, "silver_ore": 2.0, "tungsten_ore": 4.0}`.

### `cpu` — CPU
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 7.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); memory_components (Memory Components); natural_gas (Natural Gas); processor_components (Processor Components); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silver_ore (Silver Ore).
Zwischenprodukte: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); memory_components (Memory Components); processor_components (Processor Components); rare_earth_metals (Rare Earth Metals); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 6.0, "crude_oil": 7.0, "fluorspar": 7.0, "gold_ore": 10.0, "natural_gas": 7.0, "quartz": 28.0, "rare_earth_ore": 5.333333333333333, "silver_ore": 2.0}`.

### `carbon_capture_plant` — Carbon Capture Plant
Tiefe 3; Basisrohstoffarten 11; Zwischenprodukte 12.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); ceramics (Ceramics); chemical_components (Chemical Components); chemical_feedstock (Chemical Feedstock); clay (Clay); coal (Coal); compressor_components (Compressor Components); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); filtration_components (Filtration Components); gypsum (Gypsum); iron_ore (Iron Ore); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas); polymer (Polymer); processed_gypsum (Processed Gypsum); pump_components (Pump Components); steel (Steel); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); ceramics (Ceramics); chemical_feedstock (Chemical Feedstock); clay (Clay); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); gypsum (Gypsum); iron_ore (Iron Ore); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas); polymer (Polymer); processed_gypsum (Processed Gypsum); steel (Steel); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid).
Basisrohstoffe: bauxite (Bauxite); clay (Clay); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); gypsum (Gypsum); iron_ore (Iron Ore); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas); sulfur (Sulfur).
Zwischenprodukte: aluminum (Aluminum); ceramics (Ceramics); chemical_components (Chemical Components); chemical_feedstock (Chemical Feedstock); compressor_components (Compressor Components); copper (Copper); filtration_components (Filtration Components); polymer (Polymer); processed_gypsum (Processed Gypsum); pump_components (Pump Components); steel (Steel); sulfuric_acid (Sulfuric Acid).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "clay": 1.0, "coal": 1.5, "copper_ore": 2.0, "crude_oil": 2.833333333333333, "gypsum": 1.0, "iron_ore": 6.0, "kaolin": 0.3333333333333333, "magnesite": 0.3333333333333333, "natural_gas": 2.333333333333333, "sulfur": 1.0}`.

### `cargo_aircraft` — Cargo Aircraft
Tiefe 3; Basisrohstoffarten 9; Zwischenprodukte 8.
Alle Vorprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); avionics_components (Avionics Components); bauxite (Bauxite); carbon_fiber (Carbon Fiber); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); titanium (Titanium); titanium_ore (Titanium Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); natural_gas (Natural Gas); quartz (Quartz); titanium_ore (Titanium Ore).
Zwischenprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); avionics_components (Avionics Components); carbon_fiber (Carbon Fiber); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); titanium (Titanium).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 7.2, "copper_ore": 4.0, "crude_oil": 13.0, "fluorspar": 4.0, "gold_ore": 4.0, "graphite": 3.0, "natural_gas": 7.0, "quartz": 16.0, "titanium_ore": 6.0}`.

### `cargo_pallets` — Cargo Pallets
Tiefe 3; Basisrohstoffarten 3; Zwischenprodukte 3.
Alle Vorprodukte: crude_oil (Crude Oil); lumber (Lumber); natural_gas (Natural Gas); timber (Timber); treated_lumber (Treated Lumber); wooden_components (Wooden Components).
Nur indirekte Inputs: crude_oil (Crude Oil); lumber (Lumber); natural_gas (Natural Gas); timber (Timber); treated_lumber (Treated Lumber).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: lumber (Lumber); treated_lumber (Treated Lumber); wooden_components (Wooden Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: timber (Timber).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 0.6666666666666666, "natural_gas": 0.3333333333333333, "timber": 3.0}`.

### `cargo_vessel` — Cargo Vessel
Tiefe 3; Basisrohstoffarten 4; Zwischenprodukte 4.
Alle Vorprodukte: coal (Coal); crude_oil (Crude Oil); industrial_resin (Industrial Resin); iron_ore (Iron Ore); marine_components (Marine Components); natural_gas (Natural Gas); steel (Steel); steel_components (Steel Components).
Nur indirekte Inputs: coal (Coal); crude_oil (Crude Oil); industrial_resin (Industrial Resin); iron_ore (Iron Ore); natural_gas (Natural Gas); steel (Steel).
Basisrohstoffe: coal (Coal); crude_oil (Crude Oil); iron_ore (Iron Ore); natural_gas (Natural Gas).
Zwischenprodukte: industrial_resin (Industrial Resin); marine_components (Marine Components); steel (Steel); steel_components (Steel Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 5.25, "crude_oil": 3.0, "iron_ore": 21.0, "natural_gas": 1.5}`.

### `cellular_base_station` — Cellular Base Station
Tiefe 3; Basisrohstoffarten 12; Zwischenprodukte 10.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); cement (Cement); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); power_electronics (Power Electronics); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel); structural_components (Structural Components); telecom_components (Telecom Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); cement (Cement); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: aluminum (Aluminum); cement (Cement); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); power_electronics (Power Electronics); rare_earth_metals (Rare Earth Metals); steel (Steel); structural_components (Structural Components); telecom_components (Telecom Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 1.125, "copper_ore": 12.0, "crude_oil": 6.0, "fluorspar": 6.0, "gold_ore": 6.0, "gypsum": 0.16666666666666666, "iron_ore": 4.5, "limestone": 0.6666666666666666, "natural_gas": 6.0, "quartz": 24.0, "rare_earth_ore": 5.333333333333333}`.

### `clothing` — Clothing
Tiefe 3; Basisrohstoffarten 3; Zwischenprodukte 3.
Alle Vorprodukte: cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); natural_gas (Natural Gas); polymer (Polymer); technical_textile (Technical Textile).
Nur indirekte Inputs: cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); natural_gas (Natural Gas); polymer (Polymer).
Basisrohstoffe: cotton (Cotton); crude_oil (Crude Oil); natural_gas (Natural Gas).
Zwischenprodukte: cotton_fiber (Cotton Fiber); polymer (Polymer); technical_textile (Technical Textile).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"cotton": 1.0, "crude_oil": 1.5, "natural_gas": 0.5}`.

### `combustion_vehicle` — Combustion Vehicle
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 7.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_rubber (Natural Rubber); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); processed_rubber (Processed Rubber); steel (Steel); sulfur (Sulfur); titanium (Titanium); titanium_ore (Titanium Ore); turbine_components (Turbine Components); vehicle_components (Vehicle Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_rubber (Natural Rubber); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); processed_rubber (Processed Rubber); steel (Steel); sulfur (Sulfur); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_rubber (Natural Rubber); nickel_ore (Nickel Ore); sulfur (Sulfur); titanium_ore (Titanium Ore).
Zwischenprodukte: aluminum (Aluminum); nickel_alloy (Nickel Alloy); processed_rubber (Processed Rubber); steel (Steel); titanium (Titanium); turbine_components (Turbine Components); vehicle_components (Vehicle Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: coal (Coal); iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "coal": 1.8333333333333333, "iron_ore": 8.0, "molybdenum_ore": 0.6666666666666666, "natural_rubber": 2.0, "nickel_ore": 2.0, "sulfur": 1.0, "titanium_ore": 2.0}`.

### `commercial_aircraft` — Commercial Aircraft
Tiefe 3; Basisrohstoffarten 13; Zwischenprodukte 10.
Alle Vorprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); avionics_components (Avionics Components); bauxite (Bauxite); carbon_fiber (Carbon Fiber); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); quartz (Quartz); titanium (Titanium); titanium_ore (Titanium Ore); turbine_components (Turbine Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); quartz (Quartz); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_ore (Nickel Ore); quartz (Quartz); titanium_ore (Titanium Ore).
Zwischenprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); avionics_components (Avionics Components); carbon_fiber (Carbon Fiber); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); nickel_alloy (Nickel Alloy); titanium (Titanium); turbine_components (Turbine Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); crude_oil (Crude Oil); natural_gas (Natural Gas); titanium (Titanium).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 7.2, "coal": 0.3333333333333333, "copper_ore": 4.0, "crude_oil": 13.0, "fluorspar": 4.0, "gold_ore": 4.0, "graphite": 3.0, "iron_ore": 2.0, "molybdenum_ore": 0.6666666666666666, "natural_gas": 7.0, "nickel_ore": 2.0, "quartz": 16.0, "titanium_ore": 8.0}`.

### `commercial_furniture` — Commercial Furniture
Tiefe 3; Basisrohstoffarten 6; Zwischenprodukte 7.
Alle Vorprodukte: cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); industrial_fabric (Industrial Fabric); lumber (Lumber); natural_gas (Natural Gas); natural_rubber (Natural Rubber); polymer (Polymer); processed_rubber (Processed Rubber); sulfur (Sulfur); timber (Timber); treated_lumber (Treated Lumber); wooden_components (Wooden Components).
Nur indirekte Inputs: cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); lumber (Lumber); natural_gas (Natural Gas); natural_rubber (Natural Rubber); polymer (Polymer); processed_rubber (Processed Rubber); sulfur (Sulfur); timber (Timber); treated_lumber (Treated Lumber).
Basisrohstoffe: cotton (Cotton); crude_oil (Crude Oil); natural_gas (Natural Gas); natural_rubber (Natural Rubber); sulfur (Sulfur); timber (Timber).
Zwischenprodukte: cotton_fiber (Cotton Fiber); industrial_fabric (Industrial Fabric); lumber (Lumber); polymer (Polymer); processed_rubber (Processed Rubber); treated_lumber (Treated Lumber); wooden_components (Wooden Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"cotton": 1.0, "crude_oil": 2.1666666666666665, "natural_gas": 0.8333333333333333, "natural_rubber": 1.0, "sulfur": 0.5, "timber": 3.0}`.

### `commercial_truck` — Commercial Truck
Tiefe 3; Basisrohstoffarten 14; Zwischenprodukte 13.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); silver (Silver); silver_ore (Silver Ore); steel (Steel); sulfur (Sulfur); tire_components (Tire Components); vehicle_components (Vehicle Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore); steel (Steel); sulfur (Sulfur).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); iron_ore (Iron Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silver_ore (Silver Ore); sulfur (Sulfur).
Zwischenprodukte: aluminum (Aluminum); carbon_fiber (Carbon Fiber); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); processed_rubber (Processed Rubber); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); silver (Silver); steel (Steel); tire_components (Tire Components); vehicle_components (Vehicle Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); crude_oil (Crude Oil); gold (Gold); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); processed_rubber (Processed Rubber).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "coal": 1.5, "copper_ore": 6.0, "crude_oil": 15.0, "fluorspar": 6.0, "gold_ore": 6.0, "graphite": 3.0, "iron_ore": 6.0, "natural_gas": 9.0, "natural_rubber": 8.0, "quartz": 24.0, "rare_earth_ore": 2.6666666666666665, "silver_ore": 4.0, "sulfur": 4.0}`.

### `communication_cable` — Communication Cable
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 7.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); insulated_wire (Insulated Wire); natural_gas (Natural Gas); polymer (Polymer); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); telecom_components (Telecom Components).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); polymer (Polymer); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); insulated_wire (Insulated Wire); polymer (Polymer); rare_earth_metals (Rare Earth Metals); telecom_components (Telecom Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 6.0, "crude_oil": 3.5, "fluorspar": 2.0, "gold_ore": 2.0, "natural_gas": 2.5, "quartz": 8.0, "rare_earth_ore": 2.6666666666666665}`.

### `communication_satellite` — Communication Satellite
Tiefe 3; Basisrohstoffarten 13; Zwischenprodukte 12.
Alle Vorprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); carbon_fiber (Carbon Fiber); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); limestone (Limestone); natural_gas (Natural Gas); network_components (Network Components); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silica_sand (Silica Sand); solar_components (Solar Components); telecom_components (Telecom Components); titanium (Titanium); titanium_ore (Titanium Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); carbon_fiber (Carbon Fiber); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silica_sand (Silica Sand); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); borate_ore (Borate Ore); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silica_sand (Silica Sand); titanium_ore (Titanium Ore).
Zwischenprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); carbon_fiber (Carbon Fiber); copper (Copper); glass (Glass); gold (Gold); high_purity_silicon (High-Purity Silicon); network_components (Network Components); rare_earth_metals (Rare Earth Metals); solar_components (Solar Components); telecom_components (Telecom Components); titanium (Titanium).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); copper (Copper); crude_oil (Crude Oil); gold (Gold); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 5.4, "borate_ore": 0.3333333333333333, "copper_ore": 12.0, "crude_oil": 10.0, "fluorspar": 7.0, "gold_ore": 6.0, "graphite": 1.0, "limestone": 0.3333333333333333, "natural_gas": 8.0, "quartz": 28.0, "rare_earth_ore": 2.6666666666666665, "silica_sand": 1.3333333333333333, "titanium_ore": 2.0}`.

### `compute_node` — Compute Node
Tiefe 3; Basisrohstoffarten 9; Zwischenprodukte 9.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); memory_components (Memory Components); natural_gas (Natural Gas); network_components (Network Components); processor_components (Processor Components); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silver_ore (Silver Ore).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); memory_components (Memory Components); network_components (Network Components); processor_components (Processor Components); rare_earth_metals (Rare Earth Metals); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "copper_ore": 14.0, "crude_oil": 11.0, "fluorspar": 11.0, "gold_ore": 14.0, "natural_gas": 11.0, "quartz": 44.0, "rare_earth_ore": 5.333333333333333, "silver_ore": 2.0}`.

### `construction_frames` — Construction Frames
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 6.
Alle Vorprodukte: cement (Cement); coal (Coal); crude_oil (Crude Oil); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); lumber (Lumber); natural_gas (Natural Gas); steel (Steel); structural_components (Structural Components); timber (Timber); treated_lumber (Treated Lumber); wooden_components (Wooden Components).
Nur indirekte Inputs: cement (Cement); coal (Coal); crude_oil (Crude Oil); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); lumber (Lumber); natural_gas (Natural Gas); steel (Steel); timber (Timber); treated_lumber (Treated Lumber).
Basisrohstoffe: coal (Coal); crude_oil (Crude Oil); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: cement (Cement); lumber (Lumber); steel (Steel); structural_components (Structural Components); treated_lumber (Treated Lumber); wooden_components (Wooden Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: timber (Timber).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 1.125, "crude_oil": 0.6666666666666666, "gypsum": 0.16666666666666666, "iron_ore": 4.5, "limestone": 0.6666666666666666, "natural_gas": 0.3333333333333333, "timber": 3.0}`.

### `construction_materials` — Construction Materials
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 8.
Alle Vorprodukte: asphalt_components (Asphalt Components); bitumen (Bitumen); cement (Cement); coal (Coal); concrete_components (Concrete Components); crude_oil (Crude Oil); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); lumber (Lumber); natural_gas (Natural Gas); steel (Steel); timber (Timber); treated_lumber (Treated Lumber); wooden_components (Wooden Components).
Nur indirekte Inputs: bitumen (Bitumen); cement (Cement); coal (Coal); crude_oil (Crude Oil); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); lumber (Lumber); natural_gas (Natural Gas); steel (Steel); timber (Timber); treated_lumber (Treated Lumber).
Basisrohstoffe: coal (Coal); crude_oil (Crude Oil); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: asphalt_components (Asphalt Components); bitumen (Bitumen); cement (Cement); concrete_components (Concrete Components); lumber (Lumber); steel (Steel); treated_lumber (Treated Lumber); wooden_components (Wooden Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: cement (Cement); crude_oil (Crude Oil); timber (Timber).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.75, "crude_oil": 3.3333333333333335, "gypsum": 1.0, "iron_ore": 3.0, "limestone": 4.0, "natural_gas": 0.16666666666666666, "timber": 1.5}`.

### `container_ship` — Container Ship
Tiefe 3; Basisrohstoffarten 11; Zwischenprodukte 10.
Alle Vorprodukte: cement (Cement); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); industrial_resin (Industrial Resin); iron_ore (Iron Ore); limestone (Limestone); marine_components (Marine Components); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); steel (Steel); structural_components (Structural Components).
Nur indirekte Inputs: cement (Cement); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); industrial_resin (Industrial Resin); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); steel (Steel).
Basisrohstoffe: coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Zwischenprodukte: cement (Cement); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); industrial_resin (Industrial Resin); marine_components (Marine Components); silver (Silver); steel (Steel); structural_components (Structural Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 5.625, "copper_ore": 2.0, "crude_oil": 5.0, "fluorspar": 2.0, "gold_ore": 2.0, "gypsum": 0.16666666666666666, "iron_ore": 22.5, "limestone": 0.6666666666666666, "natural_gas": 3.5, "quartz": 8.0, "silver_ore": 2.0}`.

### `crop_protection_products` — Crop Protection Products
Tiefe 3; Basisrohstoffarten 4; Zwischenprodukte 5.
Alle Vorprodukte: agricultural_chemicals (Agricultural Chemicals); chemical_components (Chemical Components); chemical_feedstock (Chemical Feedstock); chlorine (Chlorine); crude_oil (Crude Oil); natural_gas (Natural Gas); salt (Salt); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid).
Nur indirekte Inputs: chemical_feedstock (Chemical Feedstock); chlorine (Chlorine); crude_oil (Crude Oil); natural_gas (Natural Gas); salt (Salt); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); salt (Salt); sulfur (Sulfur).
Zwischenprodukte: agricultural_chemicals (Agricultural Chemicals); chemical_components (Chemical Components); chemical_feedstock (Chemical Feedstock); chlorine (Chlorine); sulfuric_acid (Sulfuric Acid).
Gemeinsam verwendete Vorprodukte in dieser Kette: chemical_feedstock (Chemical Feedstock); natural_gas (Natural Gas); sulfuric_acid (Sulfuric Acid).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 2.6666666666666665, "natural_gas": 4.166666666666666, "salt": 3.0, "sulfur": 3.0}`.

### `data_center_module` — Data Center Module
Tiefe 3; Basisrohstoffarten 13; Zwischenprodukte 11.
Alle Vorprodukte: cement (Cement); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); grid_storage_components (Grid Storage Components); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); lithium (Lithium); lithium_ore (Lithium Ore); natural_gas (Natural Gas); purified_graphite (Purified Graphite); quartz (Quartz); server_components (Server Components); steel (Steel); structural_components (Structural Components); vanadium_alloy (Vanadium Alloy); vanadium_ore (Vanadium Ore).
Nur indirekte Inputs: cement (Cement); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); lithium (Lithium); lithium_ore (Lithium Ore); natural_gas (Natural Gas); purified_graphite (Purified Graphite); quartz (Quartz); steel (Steel); vanadium_alloy (Vanadium Alloy); vanadium_ore (Vanadium Ore).
Basisrohstoffe: coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); lithium_ore (Lithium Ore); natural_gas (Natural Gas); quartz (Quartz); vanadium_ore (Vanadium Ore).
Zwischenprodukte: cement (Cement); copper (Copper); gold (Gold); grid_storage_components (Grid Storage Components); high_purity_silicon (High-Purity Silicon); lithium (Lithium); purified_graphite (Purified Graphite); server_components (Server Components); steel (Steel); structural_components (Structural Components); vanadium_alloy (Vanadium Alloy).
Gemeinsam verwendete Vorprodukte in dieser Kette: iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 1.125, "copper_ore": 4.0, "crude_oil": 4.0, "fluorspar": 4.0, "gold_ore": 4.0, "graphite": 1.3333333333333333, "gypsum": 0.16666666666666666, "iron_ore": 5.833333333333333, "limestone": 0.6666666666666666, "lithium_ore": 2.0, "natural_gas": 4.0, "quartz": 16.0, "vanadium_ore": 1.3333333333333333}`.

### `desalination_plant` — Desalination Plant
Tiefe 3; Basisrohstoffarten 15; Zwischenprodukte 14.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); cellulose (Cellulose); ceramics (Ceramics); chlorine (Chlorine); clay (Clay); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); filtration_components (Filtration Components); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); kaolin (Kaolin); magnesite (Magnesite); membrane_components (Membrane Components); natural_gas (Natural Gas); polymer (Polymer); power_electronics (Power Electronics); processed_gypsum (Processed Gypsum); pump_components (Pump Components); quartz (Quartz); salt (Salt); steel (Steel); timber (Timber).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); cellulose (Cellulose); ceramics (Ceramics); chlorine (Chlorine); clay (Clay); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas); polymer (Polymer); processed_gypsum (Processed Gypsum); quartz (Quartz); salt (Salt); steel (Steel); timber (Timber).
Basisrohstoffe: bauxite (Bauxite); clay (Clay); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); gypsum (Gypsum); iron_ore (Iron Ore); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas); quartz (Quartz); salt (Salt); timber (Timber).
Zwischenprodukte: aluminum (Aluminum); cellulose (Cellulose); ceramics (Ceramics); chlorine (Chlorine); copper (Copper); filtration_components (Filtration Components); gold (Gold); high_purity_silicon (High-Purity Silicon); membrane_components (Membrane Components); polymer (Polymer); power_electronics (Power Electronics); processed_gypsum (Processed Gypsum); pump_components (Pump Components); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); crude_oil (Crude Oil); natural_gas (Natural Gas); polymer (Polymer).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "clay": 1.0, "coal": 0.75, "copper_ore": 6.0, "crude_oil": 5.5, "fluorspar": 2.0, "gold_ore": 2.0, "gypsum": 1.0, "iron_ore": 3.0, "kaolin": 0.3333333333333333, "magnesite": 0.3333333333333333, "natural_gas": 3.5, "quartz": 8.0, "salt": 1.5, "timber": 1.0}`.

### `diagnostic_system` — Diagnostic System
Tiefe 3; Basisrohstoffarten 16; Zwischenprodukte 11.
Alle Vorprodukte: borate_ore (Borate Ore); chromium_ore (Chromium Ore); coal (Coal); computing_components (Computing Components); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); medical_components (Medical Components); natural_gas (Natural Gas); nickel_ore (Nickel Ore); platinum (Platinum); platinum_ore (Platinum Ore); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); silica_sand (Silica Sand); silver (Silver); silver_ore (Silver Ore); stainless_steel (Stainless Steel).
Nur indirekte Inputs: borate_ore (Borate Ore); chromium_ore (Chromium Ore); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); nickel_ore (Nickel Ore); platinum (Platinum); platinum_ore (Platinum Ore); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silica_sand (Silica Sand); silver (Silver); silver_ore (Silver Ore); stainless_steel (Stainless Steel).
Basisrohstoffe: borate_ore (Borate Ore); chromium_ore (Chromium Ore); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); nickel_ore (Nickel Ore); platinum_ore (Platinum Ore); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silica_sand (Silica Sand); silver_ore (Silver Ore).
Zwischenprodukte: computing_components (Computing Components); copper (Copper); glass (Glass); gold (Gold); high_purity_silicon (High-Purity Silicon); medical_components (Medical Components); platinum (Platinum); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); silver (Silver); stainless_steel (Stainless Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"borate_ore": 0.3333333333333333, "chromium_ore": 0.6666666666666666, "coal": 1.0, "copper_ore": 6.0, "crude_oil": 6.0, "fluorspar": 6.0, "gold_ore": 6.0, "iron_ore": 4.0, "limestone": 0.3333333333333333, "natural_gas": 6.0, "nickel_ore": 0.6666666666666666, "platinum_ore": 2.0, "quartz": 24.0, "rare_earth_ore": 2.6666666666666665, "silica_sand": 1.3333333333333333, "silver_ore": 4.0}`.

### `diesel_locomotive` — Diesel Locomotive
Tiefe 3; Basisrohstoffarten 6; Zwischenprodukte 6.
Alle Vorprodukte: coal (Coal); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); molybdenum_ore (Molybdenum Ore); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); rail_components (Rail Components); steel (Steel); titanium (Titanium); titanium_ore (Titanium Ore); turbine_components (Turbine Components).
Nur indirekte Inputs: coal (Coal); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); molybdenum_ore (Molybdenum Ore); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); steel (Steel); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: coal (Coal); iron_ore (Iron Ore); manganese_ore (Manganese Ore); molybdenum_ore (Molybdenum Ore); nickel_ore (Nickel Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: manganese (Manganese); nickel_alloy (Nickel Alloy); rail_components (Rail Components); steel (Steel); titanium (Titanium); turbine_components (Turbine Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: coal (Coal); iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 3.3333333333333335, "iron_ore": 14.0, "manganese_ore": 3.6, "molybdenum_ore": 0.6666666666666666, "nickel_ore": 2.0, "titanium_ore": 2.0}`.

### `electric_locomotive` — Electric Locomotive
Tiefe 3; Basisrohstoffarten 11; Zwischenprodukte 11.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron (Iron); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); motor_components (Motor Components); natural_gas (Natural Gas); power_electronics (Power Electronics); quartz (Quartz); rail_components (Rail Components); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron (Iron); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); manganese_ore (Manganese Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); iron (Iron); manganese (Manganese); motor_components (Motor Components); power_electronics (Power Electronics); rail_components (Rail Components); rare_earth_metals (Rare Earth Metals); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 3.0, "copper_ore": 6.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "iron_ore": 14.0, "manganese_ore": 3.6, "natural_gas": 2.0, "quartz": 8.0, "rare_earth_ore": 2.6666666666666665}`.

### `electric_motor` — Electric Motor
Tiefe 3; Basisrohstoffarten 6; Zwischenprodukte 7.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); electrical_components (Electrical Components); iron (Iron); iron_ore (Iron Ore); motor_components (Motor Components); natural_gas (Natural Gas); polymer (Polymer); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); tin (Tin); tin_ore (Tin Ore).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); iron (Iron); iron_ore (Iron Ore); natural_gas (Natural Gas); polymer (Polymer); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); tin (Tin); tin_ore (Tin Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); iron_ore (Iron Ore); natural_gas (Natural Gas); rare_earth_ore (Rare Earth Ore); tin_ore (Tin Ore).
Zwischenprodukte: copper (Copper); electrical_components (Electrical Components); iron (Iron); motor_components (Motor Components); polymer (Polymer); rare_earth_metals (Rare Earth Metals); tin (Tin).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 5.0, "crude_oil": 0.75, "iron_ore": 4.0, "natural_gas": 0.25, "rare_earth_ore": 5.333333333333333, "tin_ore": 0.9}`.

### `electric_vehicle` — Electric Vehicle
Tiefe 3; Basisrohstoffarten 10; Zwischenprodukte 12.
Alle Vorprodukte: aluminum (Aluminum); battery_components (Battery Components); bauxite (Bauxite); coal (Coal); cobalt (Cobalt); cobalt_ore (Cobalt Ore); copper (Copper); copper_ore (Copper Ore); iron (Iron); iron_ore (Iron Ore); lithium (Lithium); lithium_ore (Lithium Ore); motor_components (Motor Components); natural_rubber (Natural Rubber); nickel (Nickel); nickel_ore (Nickel Ore); processed_rubber (Processed Rubber); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel); sulfur (Sulfur); vehicle_components (Vehicle Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); cobalt (Cobalt); cobalt_ore (Cobalt Ore); copper (Copper); copper_ore (Copper Ore); iron (Iron); iron_ore (Iron Ore); lithium (Lithium); lithium_ore (Lithium Ore); natural_rubber (Natural Rubber); nickel (Nickel); nickel_ore (Nickel Ore); processed_rubber (Processed Rubber); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel); sulfur (Sulfur).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); cobalt_ore (Cobalt Ore); copper_ore (Copper Ore); iron_ore (Iron Ore); lithium_ore (Lithium Ore); natural_rubber (Natural Rubber); nickel_ore (Nickel Ore); rare_earth_ore (Rare Earth Ore); sulfur (Sulfur).
Zwischenprodukte: aluminum (Aluminum); battery_components (Battery Components); cobalt (Cobalt); copper (Copper); iron (Iron); lithium (Lithium); motor_components (Motor Components); nickel (Nickel); processed_rubber (Processed Rubber); rare_earth_metals (Rare Earth Metals); steel (Steel); vehicle_components (Vehicle Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 5.4, "coal": 0.75, "cobalt_ore": 4.0, "copper_ore": 2.0, "iron_ore": 5.0, "lithium_ore": 4.0, "natural_rubber": 1.0, "nickel_ore": 3.6, "rare_earth_ore": 2.6666666666666665, "sulfur": 0.5}`.

### `electrical_cable` — Electrical Cable
Tiefe 3; Basisrohstoffarten 3; Zwischenprodukte 4.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); copper_wire (Copper Wire); crude_oil (Crude Oil); insulated_wire (Insulated Wire); natural_gas (Natural Gas); polymer (Polymer).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); natural_gas (Natural Gas); polymer (Polymer).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); natural_gas (Natural Gas).
Zwischenprodukte: copper (Copper); copper_wire (Copper Wire); insulated_wire (Insulated Wire); polymer (Polymer).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 3.333333333333333, "crude_oil": 1.5, "natural_gas": 0.5}`.

### `engineered_structures` — Engineered Structures
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 6.
Alle Vorprodukte: carbon_fiber (Carbon Fiber); cement (Cement); coal (Coal); composite_components (Composite Components); crude_oil (Crude Oil); graphite (Graphite); gypsum (Gypsum); industrial_resin (Industrial Resin); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); steel (Steel); structural_components (Structural Components).
Nur indirekte Inputs: carbon_fiber (Carbon Fiber); cement (Cement); coal (Coal); crude_oil (Crude Oil); graphite (Graphite); gypsum (Gypsum); industrial_resin (Industrial Resin); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); steel (Steel).
Basisrohstoffe: coal (Coal); crude_oil (Crude Oil); graphite (Graphite); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas).
Zwischenprodukte: carbon_fiber (Carbon Fiber); cement (Cement); composite_components (Composite Components); industrial_resin (Industrial Resin); steel (Steel); structural_components (Structural Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 2.25, "crude_oil": 4.0, "graphite": 1.0, "gypsum": 0.3333333333333333, "iron_ore": 9.0, "limestone": 1.3333333333333333, "natural_gas": 1.5}`.

### `excavator` — Excavator
Tiefe 3; Basisrohstoffarten 9; Zwischenprodukte 8.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); cement (Cement); coal (Coal); crude_oil (Crude Oil); gypsum (Gypsum); hydraulic_components (Hydraulic Components); industrial_resin (Industrial Resin); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); steel (Steel); structural_components (Structural Components); sulfur (Sulfur); vehicle_components (Vehicle Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); cement (Cement); coal (Coal); crude_oil (Crude Oil); gypsum (Gypsum); industrial_resin (Industrial Resin); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); steel (Steel); sulfur (Sulfur).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); crude_oil (Crude Oil); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); natural_rubber (Natural Rubber); sulfur (Sulfur).
Zwischenprodukte: aluminum (Aluminum); cement (Cement); hydraulic_components (Hydraulic Components); industrial_resin (Industrial Resin); processed_rubber (Processed Rubber); steel (Steel); structural_components (Structural Components); vehicle_components (Vehicle Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "coal": 3.375, "crude_oil": 1.0, "gypsum": 0.16666666666666666, "iron_ore": 13.5, "limestone": 0.6666666666666666, "natural_gas": 0.5, "natural_rubber": 2.0, "sulfur": 1.0}`.

### `fertilizer` — Fertilizer
Tiefe 3; Basisrohstoffarten 4; Zwischenprodukte 5.
Alle Vorprodukte: agricultural_mineral_components (Agricultural Mineral Components); ammonia (Ammonia); fertilizer_components (Fertilizer Components); natural_gas (Natural Gas); phosphate_rock (Phosphate Rock); phosphoric_acid (Phosphoric Acid); potash (Potash); potassium_compound (Potassium Compound); sulfur (Sulfur).
Nur indirekte Inputs: ammonia (Ammonia); natural_gas (Natural Gas); phosphate_rock (Phosphate Rock); phosphoric_acid (Phosphoric Acid); potash (Potash); potassium_compound (Potassium Compound); sulfur (Sulfur).
Basisrohstoffe: natural_gas (Natural Gas); phosphate_rock (Phosphate Rock); potash (Potash); sulfur (Sulfur).
Zwischenprodukte: agricultural_mineral_components (Agricultural Mineral Components); ammonia (Ammonia); fertilizer_components (Fertilizer Components); phosphoric_acid (Phosphoric Acid); potassium_compound (Potassium Compound).
Gemeinsam verwendete Vorprodukte in dieser Kette: natural_gas (Natural Gas); phosphoric_acid (Phosphoric Acid).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"natural_gas": 3.0, "phosphate_rock": 3.0, "potash": 3.0, "sulfur": 1.5}`.

### `freight_railcar` — Freight Railcar
Tiefe 3; Basisrohstoffarten 5; Zwischenprodukte 5.
Alle Vorprodukte: cement (Cement); coal (Coal); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); manganese (Manganese); manganese_ore (Manganese Ore); rail_components (Rail Components); steel (Steel); structural_components (Structural Components).
Nur indirekte Inputs: cement (Cement); coal (Coal); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); manganese (Manganese); manganese_ore (Manganese Ore); steel (Steel).
Basisrohstoffe: coal (Coal); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); manganese_ore (Manganese Ore).
Zwischenprodukte: cement (Cement); manganese (Manganese); rail_components (Rail Components); steel (Steel); structural_components (Structural Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 4.125, "gypsum": 0.16666666666666666, "iron_ore": 16.5, "limestone": 0.6666666666666666, "manganese_ore": 3.6}`.

### `fusion_reactor_module` — Fusion Reactor Module
Tiefe 3; Basisrohstoffarten 14; Zwischenprodukte 13.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); electrolyzer_components (Electrolyzer Components); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); lead_ore (Lead Ore); molybdenum (Molybdenum); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); niobium (Niobium); niobium_ore (Niobium Ore); nuclear_fuel_components (Nuclear Fuel Components); nuclear_material (Nuclear Material); quartz (Quartz); rare_earth_ore (Rare Earth Ore); reactor_components (Reactor Components); refractory_alloy_components (Refractory Alloy Components); shielding_material (Shielding Material); superconducting_alloy (Superconducting Alloy); titanium_ore (Titanium Ore); uranium_ore (Uranium Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); lead_ore (Lead Ore); molybdenum (Molybdenum); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); niobium (Niobium); niobium_ore (Niobium Ore); nuclear_material (Nuclear Material); quartz (Quartz); rare_earth_ore (Rare Earth Ore); shielding_material (Shielding Material); superconducting_alloy (Superconducting Alloy); titanium_ore (Titanium Ore); uranium_ore (Uranium Ore).
Basisrohstoffe: bauxite (Bauxite); borate_ore (Borate Ore); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); lead_ore (Lead Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); niobium_ore (Niobium Ore); quartz (Quartz); rare_earth_ore (Rare Earth Ore); titanium_ore (Titanium Ore); uranium_ore (Uranium Ore).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); electrolyzer_components (Electrolyzer Components); gold (Gold); high_purity_silicon (High-Purity Silicon); molybdenum (Molybdenum); niobium (Niobium); nuclear_fuel_components (Nuclear Fuel Components); nuclear_material (Nuclear Material); reactor_components (Reactor Components); refractory_alloy_components (Refractory Alloy Components); shielding_material (Shielding Material); superconducting_alloy (Superconducting Alloy).
Gemeinsam verwendete Vorprodukte in dieser Kette: lead_ore (Lead Ore); niobium_ore (Niobium Ore); nuclear_material (Nuclear Material).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "borate_ore": 0.3333333333333333, "copper_ore": 4.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "lead_ore": 2.833333333333333, "molybdenum_ore": 2.0, "natural_gas": 2.0, "niobium_ore": 4.0, "quartz": 8.0, "rare_earth_ore": 1.5, "titanium_ore": 1.0, "uranium_ore": 4.5}`.

### `gas_turbine` — Gas Turbine
Tiefe 3; Basisrohstoffarten 6; Zwischenprodukte 6.
Alle Vorprodukte: advanced_alloy_components (Advanced Alloy Components); coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); titanium (Titanium); titanium_ore (Titanium Ore); turbine_components (Turbine Components); vanadium (Vanadium); vanadium_alloy (Vanadium Alloy); vanadium_ore (Vanadium Ore).
Nur indirekte Inputs: coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); titanium (Titanium); titanium_ore (Titanium Ore); vanadium (Vanadium); vanadium_alloy (Vanadium Alloy); vanadium_ore (Vanadium Ore).
Basisrohstoffe: coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_ore (Nickel Ore); titanium_ore (Titanium Ore); vanadium_ore (Vanadium Ore).
Zwischenprodukte: advanced_alloy_components (Advanced Alloy Components); nickel_alloy (Nickel Alloy); titanium (Titanium); turbine_components (Turbine Components); vanadium (Vanadium); vanadium_alloy (Vanadium Alloy).
Gemeinsam verwendete Vorprodukte in dieser Kette: iron_ore (Iron Ore); titanium (Titanium); vanadium_ore (Vanadium Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.6666666666666666, "iron_ore": 6.666666666666666, "molybdenum_ore": 1.3333333333333333, "nickel_ore": 4.0, "titanium_ore": 6.0, "vanadium_ore": 4.666666666666666}`.

### `gearbox` — Gearbox
Tiefe 3; Basisrohstoffarten 4; Zwischenprodukte 5.
Alle Vorprodukte: bearing_components (Bearing Components); chromium (Chromium); chromium_ore (Chromium Ore); coal (Coal); gear_components (Gear Components); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); steel (Steel).
Nur indirekte Inputs: chromium (Chromium); chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); steel (Steel).
Basisrohstoffe: chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); manganese_ore (Manganese Ore).
Zwischenprodukte: bearing_components (Bearing Components); chromium (Chromium); gear_components (Gear Components); manganese (Manganese); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"chromium_ore": 0.9, "coal": 2.25, "iron_ore": 9.0, "manganese_ore": 1.8}`.

### `grid_battery` — Grid Battery
Tiefe 3; Basisrohstoffarten 10; Zwischenprodukte 10.
Alle Vorprodukte: aluminum (Aluminum); battery_components (Battery Components); battery_materials (Battery Materials); bauxite (Bauxite); cobalt (Cobalt); cobalt_ore (Cobalt Ore); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); lithium (Lithium); lithium_ore (Lithium Ore); natural_gas (Natural Gas); nickel (Nickel); nickel_ore (Nickel Ore); power_electronics (Power Electronics); quartz (Quartz).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); cobalt (Cobalt); cobalt_ore (Cobalt Ore); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); lithium (Lithium); lithium_ore (Lithium Ore); natural_gas (Natural Gas); nickel (Nickel); nickel_ore (Nickel Ore); quartz (Quartz).
Basisrohstoffe: bauxite (Bauxite); cobalt_ore (Cobalt Ore); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); lithium_ore (Lithium Ore); natural_gas (Natural Gas); nickel_ore (Nickel Ore); quartz (Quartz).
Zwischenprodukte: aluminum (Aluminum); battery_components (Battery Components); battery_materials (Battery Materials); cobalt (Cobalt); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); lithium (Lithium); nickel (Nickel); power_electronics (Power Electronics).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); cobalt (Cobalt); lithium (Lithium); nickel (Nickel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 5.4, "cobalt_ore": 5.0, "copper_ore": 4.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "lithium_ore": 6.0, "natural_gas": 2.0, "nickel_ore": 4.5, "quartz": 8.0}`.

### `grid_storage_system` — Grid Storage System
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 6.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); power_electronics (Power Electronics); quartz (Quartz); storage_components (Storage Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); power_electronics (Power Electronics); storage_components (Storage Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 9.0, "copper_ore": 12.0, "crude_oil": 6.0, "fluorspar": 6.0, "gold_ore": 6.0, "natural_gas": 6.0, "quartz": 24.0}`.

### `heavy_machinery` — Heavy Machinery
Tiefe 3; Basisrohstoffarten 11; Zwischenprodukte 10.
Alle Vorprodukte: cement (Cement); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); hydraulic_components (Hydraulic Components); industrial_resin (Industrial Resin); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); steel (Steel); structural_components (Structural Components).
Nur indirekte Inputs: cement (Cement); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); industrial_resin (Industrial Resin); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); steel (Steel).
Basisrohstoffe: coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Zwischenprodukte: cement (Cement); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); hydraulic_components (Hydraulic Components); industrial_resin (Industrial Resin); silver (Silver); steel (Steel); structural_components (Structural Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 3.0, "copper_ore": 2.0, "crude_oil": 3.0, "fluorspar": 2.0, "gold_ore": 2.0, "gypsum": 0.3333333333333333, "iron_ore": 12.0, "limestone": 1.3333333333333333, "natural_gas": 2.5, "quartz": 8.0, "silver_ore": 2.0}`.

### `heavy_mining_drill` — Heavy Mining Drill
Tiefe 3; Basisrohstoffarten 10; Zwischenprodukte 10.
Alle Vorprodukte: coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); hydraulic_components (Hydraulic Components); industrial_resin (Industrial Resin); iron_ore (Iron Ore); mining_components (Mining Components); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); industrial_resin (Industrial Resin); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); hydraulic_components (Hydraulic Components); industrial_resin (Industrial Resin); mining_components (Mining Components); silver (Silver); steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 2.25, "copper_ore": 2.0, "crude_oil": 3.0, "fluorspar": 2.0, "gold_ore": 2.0, "iron_ore": 9.0, "natural_gas": 2.5, "quartz": 8.0, "silver_ore": 2.0, "tungsten_ore": 4.0}`.

### `high_speed_network_system` — High-Speed Network System
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 7.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); network_components (Network Components); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Zwischenprodukte: aluminum (Aluminum); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); network_components (Network Components); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 5.4, "copper_ore": 26.0, "crude_oil": 14.0, "fluorspar": 14.0, "gold_ore": 14.0, "natural_gas": 14.0, "quartz": 56.0, "silver_ore": 2.0}`.

### `high_speed_train` — High-Speed Train
Tiefe 3; Basisrohstoffarten 12; Zwischenprodukte 11.
Alle Vorprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); natural_gas (Natural Gas); power_electronics (Power Electronics); quartz (Quartz); rail_components (Rail Components); steel (Steel); titanium (Titanium); titanium_ore (Titanium Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); natural_gas (Natural Gas); quartz (Quartz); steel (Steel); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); iron_ore (Iron Ore); manganese_ore (Manganese Ore); natural_gas (Natural Gas); quartz (Quartz); titanium_ore (Titanium Ore).
Zwischenprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); carbon_fiber (Carbon Fiber); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); manganese (Manganese); power_electronics (Power Electronics); rail_components (Rail Components); steel (Steel); titanium (Titanium).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "coal": 3.0, "copper_ore": 4.0, "crude_oil": 5.0, "fluorspar": 2.0, "gold_ore": 2.0, "graphite": 1.0, "iron_ore": 12.0, "manganese_ore": 3.6, "natural_gas": 3.0, "quartz": 8.0, "titanium_ore": 2.0}`.

### `high_speed_vessel` — High-Speed Vessel
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 8.
Alle Vorprodukte: carbon_fiber (Carbon Fiber); coal (Coal); composite_components (Composite Components); crude_oil (Crude Oil); graphite (Graphite); industrial_resin (Industrial Resin); iron_ore (Iron Ore); marine_components (Marine Components); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); steel (Steel); titanium (Titanium); titanium_ore (Titanium Ore); turbine_components (Turbine Components).
Nur indirekte Inputs: carbon_fiber (Carbon Fiber); coal (Coal); crude_oil (Crude Oil); graphite (Graphite); industrial_resin (Industrial Resin); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); steel (Steel); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: coal (Coal); crude_oil (Crude Oil); graphite (Graphite); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_ore (Nickel Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: carbon_fiber (Carbon Fiber); composite_components (Composite Components); industrial_resin (Industrial Resin); marine_components (Marine Components); nickel_alloy (Nickel Alloy); steel (Steel); titanium (Titanium); turbine_components (Turbine Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: coal (Coal); crude_oil (Crude Oil); industrial_resin (Industrial Resin); iron_ore (Iron Ore); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 1.8333333333333333, "crude_oil": 5.0, "graphite": 1.0, "iron_ore": 8.0, "molybdenum_ore": 0.6666666666666666, "natural_gas": 2.0, "nickel_ore": 2.0, "titanium_ore": 2.0}`.

### `high_voltage_equipment` — High-Voltage Equipment
Tiefe 3; Basisrohstoffarten 10; Zwischenprodukte 10.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); insulation_material (Insulation Material); iron_ore (Iron Ore); natural_gas (Natural Gas); polymer (Polymer); power_electronics (Power Electronics); processed_gypsum (Processed Gypsum); quartz (Quartz); steel (Steel); transformer_components (Transformer Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); natural_gas (Natural Gas); polymer (Polymer); processed_gypsum (Processed Gypsum); quartz (Quartz); steel (Steel).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); gypsum (Gypsum); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); insulation_material (Insulation Material); polymer (Polymer); power_electronics (Power Electronics); processed_gypsum (Processed Gypsum); steel (Steel); transformer_components (Transformer Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 0.75, "copper_ore": 6.0, "crude_oil": 2.75, "fluorspar": 2.0, "gold_ore": 2.0, "gypsum": 0.5, "iron_ore": 3.0, "natural_gas": 2.25, "quartz": 8.0}`.

### `hydraulic_system` — Hydraulic System
Tiefe 3; Basisrohstoffarten 4; Zwischenprodukte 4.
Alle Vorprodukte: coal (Coal); crude_oil (Crude Oil); hydraulic_components (Hydraulic Components); industrial_resin (Industrial Resin); iron_ore (Iron Ore); natural_gas (Natural Gas); steel (Steel); steel_components (Steel Components).
Nur indirekte Inputs: coal (Coal); crude_oil (Crude Oil); industrial_resin (Industrial Resin); iron_ore (Iron Ore); natural_gas (Natural Gas); steel (Steel).
Basisrohstoffe: coal (Coal); crude_oil (Crude Oil); iron_ore (Iron Ore); natural_gas (Natural Gas).
Zwischenprodukte: hydraulic_components (Hydraulic Components); industrial_resin (Industrial Resin); steel (Steel); steel_components (Steel Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 2.25, "crude_oil": 2.0, "iron_ore": 9.0, "natural_gas": 1.0}`.

### `hydrogen_electrolyzer` — Hydrogen Electrolyzer
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 6.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); electrolyzer_components (Electrolyzer Components); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); power_electronics (Power Electronics); quartz (Quartz).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); electrolyzer_components (Electrolyzer Components); gold (Gold); high_purity_silicon (High-Purity Silicon); power_electronics (Power Electronics).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 5.4, "copper_ore": 12.0, "crude_oil": 6.0, "fluorspar": 6.0, "gold_ore": 6.0, "natural_gas": 6.0, "quartz": 24.0}`.

### `industrial_chemicals` — Industrial Chemicals
Tiefe 3; Basisrohstoffarten 3; Zwischenprodukte 6.
Alle Vorprodukte: chemical_components (Chemical Components); chemical_feedstock (Chemical Feedstock); crude_oil (Crude Oil); gas_handling_components (Gas Handling Components); hydrogen (Hydrogen); industrial_gas (Industrial Gas); natural_gas (Natural Gas); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid).
Nur indirekte Inputs: chemical_feedstock (Chemical Feedstock); crude_oil (Crude Oil); hydrogen (Hydrogen); industrial_gas (Industrial Gas); natural_gas (Natural Gas); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); sulfur (Sulfur).
Zwischenprodukte: chemical_components (Chemical Components); chemical_feedstock (Chemical Feedstock); gas_handling_components (Gas Handling Components); hydrogen (Hydrogen); industrial_gas (Industrial Gas); sulfuric_acid (Sulfuric Acid).
Gemeinsam verwendete Vorprodukte in dieser Kette: natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 2.6666666666666665, "natural_gas": 6.166666666666666, "sulfur": 2.0}`.

### `industrial_clothing` — Industrial Clothing
Tiefe 3; Basisrohstoffarten 5; Zwischenprodukte 5.
Alle Vorprodukte: cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); industrial_fabric (Industrial Fabric); natural_gas (Natural Gas); natural_rubber (Natural Rubber); polymer (Polymer); processed_rubber (Processed Rubber); sulfur (Sulfur); technical_textile (Technical Textile).
Nur indirekte Inputs: cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); natural_gas (Natural Gas); natural_rubber (Natural Rubber); polymer (Polymer); processed_rubber (Processed Rubber); sulfur (Sulfur).
Basisrohstoffe: cotton (Cotton); crude_oil (Crude Oil); natural_gas (Natural Gas); natural_rubber (Natural Rubber); sulfur (Sulfur).
Zwischenprodukte: cotton_fiber (Cotton Fiber); industrial_fabric (Industrial Fabric); polymer (Polymer); processed_rubber (Processed Rubber); technical_textile (Technical Textile).
Gemeinsam verwendete Vorprodukte in dieser Kette: cotton_fiber (Cotton Fiber); polymer (Polymer).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"cotton": 2.5, "crude_oil": 3.75, "natural_gas": 1.25, "natural_rubber": 2.0, "sulfur": 1.0}`.

### `industrial_compressor` — Industrial Compressor
Tiefe 3; Basisrohstoffarten 5; Zwischenprodukte 7.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); compressor_components (Compressor Components); copper (Copper); copper_ore (Copper Ore); iron (Iron); iron_ore (Iron Ore); motor_components (Motor Components); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); iron (Iron); iron_ore (Iron Ore); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); iron_ore (Iron Ore); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: aluminum (Aluminum); compressor_components (Compressor Components); copper (Copper); iron (Iron); motor_components (Motor Components); rare_earth_metals (Rare Earth Metals); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "coal": 1.5, "copper_ore": 2.0, "iron_ore": 8.0, "rare_earth_ore": 2.6666666666666665}`.

### `industrial_computer` — Industrial Computer
Tiefe 3; Basisrohstoffarten 10; Zwischenprodukte 8.
Alle Vorprodukte: borate_ore (Borate Ore); computing_components (Computing Components); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); display_components (Display Components); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); limestone (Limestone); natural_gas (Natural Gas); polymer (Polymer); quartz (Quartz); silica_sand (Silica Sand); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: borate_ore (Borate Ore); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); limestone (Limestone); natural_gas (Natural Gas); polymer (Polymer); quartz (Quartz); silica_sand (Silica Sand); silver (Silver); silver_ore (Silver Ore).
Basisrohstoffe: borate_ore (Borate Ore); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silica_sand (Silica Sand); silver_ore (Silver Ore).
Zwischenprodukte: computing_components (Computing Components); copper (Copper); display_components (Display Components); glass (Glass); gold (Gold); high_purity_silicon (High-Purity Silicon); polymer (Polymer); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"borate_ore": 0.3333333333333333, "copper_ore": 8.0, "crude_oil": 10.5, "fluorspar": 9.0, "gold_ore": 8.0, "limestone": 0.3333333333333333, "natural_gas": 9.5, "quartz": 36.0, "silica_sand": 1.3333333333333333, "silver_ore": 8.0}`.

### `industrial_controller` — Industrial Controller
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 7.
Alle Vorprodukte: control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silver_ore (Silver Ore).
Zwischenprodukte: control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 6.0, "crude_oil": 6.0, "fluorspar": 6.0, "gold_ore": 6.0, "natural_gas": 6.0, "quartz": 24.0, "rare_earth_ore": 2.6666666666666665, "silver_ore": 4.0}`.

### `industrial_crusher` — Industrial Crusher
Tiefe 3; Basisrohstoffarten 4; Zwischenprodukte 5.
Alle Vorprodukte: coal (Coal); gear_components (Gear Components); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); mining_components (Mining Components); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: coal (Coal); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: coal (Coal); iron_ore (Iron Ore); manganese_ore (Manganese Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: gear_components (Gear Components); manganese (Manganese); mining_components (Mining Components); steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 2.25, "iron_ore": 9.0, "manganese_ore": 0.9, "tungsten_ore": 4.0}`.

### `industrial_cutting_machine` — Industrial Cutting Machine
Tiefe 3; Basisrohstoffarten 11; Zwischenprodukte 10.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); cutting_tooling (Cutting Tooling); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); natural_gas (Natural Gas); precision_components (Precision Components); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: aluminum (Aluminum); control_electronics (Control Electronics); copper (Copper); cutting_tooling (Cutting Tooling); gold (Gold); high_purity_silicon (High-Purity Silicon); precision_components (Precision Components); silver (Silver); steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: steel (Steel); tungsten (Tungsten).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 1.5, "copper_ore": 2.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "iron_ore": 6.0, "natural_gas": 2.0, "quartz": 8.0, "silver_ore": 2.0, "tungsten_ore": 4.0}`.

### `industrial_display` — Industrial Display
Tiefe 3; Basisrohstoffarten 11; Zwischenprodukte 8.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); glass_panels (Glass Panels); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silica_sand (Silica Sand); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silica_sand (Silica Sand); silver (Silver); silver_ore (Silver Ore).
Basisrohstoffe: bauxite (Bauxite); borate_ore (Borate Ore); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silica_sand (Silica Sand); silver_ore (Silver Ore).
Zwischenprodukte: aluminum (Aluminum); control_electronics (Control Electronics); copper (Copper); glass (Glass); glass_panels (Glass Panels); gold (Gold); high_purity_silicon (High-Purity Silicon); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 0.9, "borate_ore": 0.3333333333333333, "copper_ore": 2.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "limestone": 0.3333333333333333, "natural_gas": 2.0, "quartz": 8.0, "silica_sand": 1.3333333333333333, "silver_ore": 2.0}`.

### `industrial_drone` — Industrial Drone
Tiefe 3; Basisrohstoffarten 13; Zwischenprodukte 13.
Alle Vorprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); battery_components (Battery Components); bauxite (Bauxite); carbon_fiber (Carbon Fiber); cobalt (Cobalt); cobalt_ore (Cobalt Ore); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); lithium (Lithium); lithium_ore (Lithium Ore); natural_gas (Natural Gas); nickel (Nickel); nickel_ore (Nickel Ore); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); titanium (Titanium); titanium_ore (Titanium Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); cobalt (Cobalt); cobalt_ore (Cobalt Ore); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); lithium (Lithium); lithium_ore (Lithium Ore); natural_gas (Natural Gas); nickel (Nickel); nickel_ore (Nickel Ore); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); cobalt_ore (Cobalt Ore); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); lithium_ore (Lithium Ore); natural_gas (Natural Gas); nickel_ore (Nickel Ore); quartz (Quartz); rare_earth_ore (Rare Earth Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); battery_components (Battery Components); carbon_fiber (Carbon Fiber); cobalt (Cobalt); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); lithium (Lithium); nickel (Nickel); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); titanium (Titanium).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "cobalt_ore": 2.0, "copper_ore": 2.0, "crude_oil": 5.0, "fluorspar": 2.0, "gold_ore": 2.0, "graphite": 1.0, "lithium_ore": 2.0, "natural_gas": 3.0, "nickel_ore": 1.8, "quartz": 8.0, "rare_earth_ore": 2.6666666666666665, "titanium_ore": 2.0}`.

### `industrial_equipment` — Industrial Equipment
Tiefe 3; Basisrohstoffarten 6; Zwischenprodukte 8.
Alle Vorprodukte: coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); electrical_components (Electrical Components); iron (Iron); iron_components (Iron Components); iron_ore (Iron Ore); natural_gas (Natural Gas); polymer (Polymer); steel (Steel); steel_components (Steel Components); tin (Tin); tin_ore (Tin Ore).
Nur indirekte Inputs: coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); iron (Iron); iron_ore (Iron Ore); natural_gas (Natural Gas); polymer (Polymer); steel (Steel); tin (Tin); tin_ore (Tin Ore).
Basisrohstoffe: coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); iron_ore (Iron Ore); natural_gas (Natural Gas); tin_ore (Tin Ore).
Zwischenprodukte: copper (Copper); electrical_components (Electrical Components); iron (Iron); iron_components (Iron Components); polymer (Polymer); steel (Steel); steel_components (Steel Components); tin (Tin).
Gemeinsam verwendete Vorprodukte in dieser Kette: iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 1.5, "copper_ore": 1.0, "crude_oil": 0.75, "iron_ore": 8.0, "natural_gas": 0.25, "tin_ore": 0.9}`.

### `industrial_generator` — Industrial Generator
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 7.
Alle Vorprodukte: coal (Coal); copper (Copper); copper_ore (Copper Ore); iron (Iron); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); motor_components (Motor Components); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); titanium (Titanium); titanium_ore (Titanium Ore); turbine_components (Turbine Components).
Nur indirekte Inputs: coal (Coal); copper (Copper); copper_ore (Copper Ore); iron (Iron); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: coal (Coal); copper_ore (Copper Ore); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_ore (Nickel Ore); rare_earth_ore (Rare Earth Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: copper (Copper); iron (Iron); motor_components (Motor Components); nickel_alloy (Nickel Alloy); rare_earth_metals (Rare Earth Metals); titanium (Titanium); turbine_components (Turbine Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.3333333333333333, "copper_ore": 4.0, "iron_ore": 6.0, "molybdenum_ore": 0.6666666666666666, "nickel_ore": 2.0, "rare_earth_ore": 5.333333333333333, "titanium_ore": 2.0}`.

### `industrial_glass_panels` — Industrial Glass Panels
Tiefe 3; Basisrohstoffarten 4; Zwischenprodukte 4.
Alle Vorprodukte: aluminum (Aluminum); aluminum_components (Aluminum Components); bauxite (Bauxite); borate_ore (Borate Ore); glass (Glass); glass_panels (Glass Panels); limestone (Limestone); silica_sand (Silica Sand).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); glass (Glass); limestone (Limestone); silica_sand (Silica Sand).
Basisrohstoffe: bauxite (Bauxite); borate_ore (Borate Ore); limestone (Limestone); silica_sand (Silica Sand).
Zwischenprodukte: aluminum (Aluminum); aluminum_components (Aluminum Components); glass (Glass); glass_panels (Glass Panels).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "borate_ore": 0.6666666666666666, "limestone": 0.6666666666666666, "silica_sand": 2.6666666666666665}`.

### `industrial_hall_modules` — Industrial Hall Modules
Tiefe 3; Basisrohstoffarten 10; Zwischenprodukte 12.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); cement (Cement); coal (Coal); crude_oil (Crude Oil); galvanized_components (Galvanized Components); galvanized_metal (Galvanized Metal); glass (Glass); glass_panels (Glass Panels); gypsum (Gypsum); insulation_material (Insulation Material); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); polymer (Polymer); processed_gypsum (Processed Gypsum); silica_sand (Silica Sand); steel (Steel); structural_components (Structural Components); zinc (Zinc); zinc_ore (Zinc Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); cement (Cement); coal (Coal); crude_oil (Crude Oil); galvanized_metal (Galvanized Metal); glass (Glass); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); polymer (Polymer); processed_gypsum (Processed Gypsum); silica_sand (Silica Sand); steel (Steel); zinc (Zinc); zinc_ore (Zinc Ore).
Basisrohstoffe: bauxite (Bauxite); borate_ore (Borate Ore); coal (Coal); crude_oil (Crude Oil); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); silica_sand (Silica Sand); zinc_ore (Zinc Ore).
Zwischenprodukte: aluminum (Aluminum); cement (Cement); galvanized_components (Galvanized Components); galvanized_metal (Galvanized Metal); glass (Glass); glass_panels (Glass Panels); insulation_material (Insulation Material); polymer (Polymer); processed_gypsum (Processed Gypsum); steel (Steel); structural_components (Structural Components); zinc (Zinc).
Gemeinsam verwendete Vorprodukte in dieser Kette: gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); zinc_ore (Zinc Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 0.9, "borate_ore": 0.3333333333333333, "coal": 2.25, "crude_oil": 0.75, "gypsum": 0.8333333333333333, "iron_ore": 10.333333333333334, "limestone": 1.6666666666666665, "natural_gas": 0.25, "silica_sand": 1.3333333333333333, "zinc_ore": 2.2333333333333334}`.

### `industrial_insulation` — Industrial Insulation
Tiefe 3; Basisrohstoffarten 4; Zwischenprodukte 6.
Alle Vorprodukte: cellulose (Cellulose); crude_oil (Crude Oil); fiber_components (Fiber Components); gypsum (Gypsum); industrial_resin (Industrial Resin); insulation_material (Insulation Material); natural_gas (Natural Gas); polymer (Polymer); processed_gypsum (Processed Gypsum); timber (Timber).
Nur indirekte Inputs: cellulose (Cellulose); crude_oil (Crude Oil); gypsum (Gypsum); industrial_resin (Industrial Resin); natural_gas (Natural Gas); polymer (Polymer); processed_gypsum (Processed Gypsum); timber (Timber).
Basisrohstoffe: crude_oil (Crude Oil); gypsum (Gypsum); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: cellulose (Cellulose); fiber_components (Fiber Components); industrial_resin (Industrial Resin); insulation_material (Insulation Material); polymer (Polymer); processed_gypsum (Processed Gypsum).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 3.5, "gypsum": 1.0, "natural_gas": 2.0, "timber": 2.0}`.

### `industrial_inverter` — Industrial Inverter
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 7.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); power_electronics (Power Electronics); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Zwischenprodukte: aluminum (Aluminum); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); power_electronics (Power Electronics); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "copper_ore": 10.0, "crude_oil": 6.0, "fluorspar": 6.0, "gold_ore": 6.0, "natural_gas": 6.0, "quartz": 24.0, "silver_ore": 2.0}`.

### `industrial_laser` — Industrial Laser
Tiefe 3; Basisrohstoffarten 11; Zwischenprodukte 11.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron (Iron); iron_ore (Iron Ore); magnetic_components (Magnetic Components); natural_gas (Natural Gas); precision_components (Precision Components); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); semiconductor_components (Semiconductor Components); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron (Iron); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); iron (Iron); magnetic_components (Magnetic Components); precision_components (Precision Components); rare_earth_metals (Rare Earth Metals); semiconductor_components (Semiconductor Components); steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 0.75, "copper_ore": 2.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "iron_ore": 5.0, "natural_gas": 2.0, "quartz": 8.0, "rare_earth_ore": 2.6666666666666665, "tungsten_ore": 2.0}`.

### `industrial_packaging` — Industrial Packaging
Tiefe 3; Basisrohstoffarten 3; Zwischenprodukte 6.
Alle Vorprodukte: crude_oil (Crude Oil); lumber (Lumber); natural_gas (Natural Gas); packaging_components (Packaging Components); polymer (Polymer); timber (Timber); treated_lumber (Treated Lumber); wood_pulp (Wood Pulp); wooden_components (Wooden Components).
Nur indirekte Inputs: crude_oil (Crude Oil); lumber (Lumber); natural_gas (Natural Gas); polymer (Polymer); timber (Timber); treated_lumber (Treated Lumber); wood_pulp (Wood Pulp).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: lumber (Lumber); packaging_components (Packaging Components); polymer (Polymer); treated_lumber (Treated Lumber); wood_pulp (Wood Pulp); wooden_components (Wooden Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 2.5, "natural_gas": 1.3333333333333333, "timber": 3.5}`.

### `industrial_plastics` — Industrial Plastics
Tiefe 3; Basisrohstoffarten 4; Zwischenprodukte 6.
Alle Vorprodukte: carbon_fiber (Carbon Fiber); composite_components (Composite Components); crude_oil (Crude Oil); graphite (Graphite); industrial_resin (Industrial Resin); natural_gas (Natural Gas); packaging_components (Packaging Components); polymer (Polymer); timber (Timber); wood_pulp (Wood Pulp).
Nur indirekte Inputs: carbon_fiber (Carbon Fiber); crude_oil (Crude Oil); graphite (Graphite); industrial_resin (Industrial Resin); natural_gas (Natural Gas); polymer (Polymer); timber (Timber); wood_pulp (Wood Pulp).
Basisrohstoffe: crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: carbon_fiber (Carbon Fiber); composite_components (Composite Components); industrial_resin (Industrial Resin); packaging_components (Packaging Components); polymer (Polymer); wood_pulp (Wood Pulp).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 6.166666666666666, "graphite": 1.0, "natural_gas": 2.6666666666666665, "timber": 2.0}`.

### `industrial_pump` — Industrial Pump
Tiefe 3; Basisrohstoffarten 4; Zwischenprodukte 6.
Alle Vorprodukte: coal (Coal); copper (Copper); copper_ore (Copper Ore); iron (Iron); iron_ore (Iron Ore); motor_components (Motor Components); pump_components (Pump Components); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel).
Nur indirekte Inputs: coal (Coal); copper (Copper); copper_ore (Copper Ore); iron (Iron); iron_ore (Iron Ore); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel).
Basisrohstoffe: coal (Coal); copper_ore (Copper Ore); iron_ore (Iron Ore); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: copper (Copper); iron (Iron); motor_components (Motor Components); pump_components (Pump Components); rare_earth_metals (Rare Earth Metals); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 1.5, "copper_ore": 6.0, "iron_ore": 8.0, "rare_earth_ore": 2.6666666666666665}`.

### `industrial_relay` — Industrial Relay
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 8.
Alle Vorprodukte: control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); electrical_components (Electrical Components); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); polymer (Polymer); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); tin (Tin); tin_ore (Tin Ore).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); polymer (Polymer); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); tin (Tin); tin_ore (Tin Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore); tin_ore (Tin Ore).
Zwischenprodukte: control_electronics (Control Electronics); copper (Copper); electrical_components (Electrical Components); gold (Gold); high_purity_silicon (High-Purity Silicon); polymer (Polymer); silver (Silver); tin (Tin).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 3.0, "crude_oil": 2.75, "fluorspar": 2.0, "gold_ore": 2.0, "natural_gas": 2.25, "quartz": 8.0, "silver_ore": 2.0, "tin_ore": 0.9}`.

### `industrial_robot` — Industrial Robot
Tiefe 3; Basisrohstoffarten 12; Zwischenprodukte 13.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron (Iron); iron_ore (Iron Ore); motor_components (Motor Components); natural_gas (Natural Gas); precision_components (Precision Components); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron (Iron); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silver_ore (Silver Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: aluminum (Aluminum); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); iron (Iron); motor_components (Motor Components); precision_components (Precision Components); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); silver (Silver); steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); rare_earth_metals (Rare Earth Metals).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "coal": 1.5, "copper_ore": 6.0, "crude_oil": 4.0, "fluorspar": 4.0, "gold_ore": 4.0, "iron_ore": 8.0, "natural_gas": 4.0, "quartz": 16.0, "rare_earth_ore": 5.333333333333333, "silver_ore": 2.0, "tungsten_ore": 4.0}`.

### `industrial_rubber_products` — Industrial Rubber Products
Tiefe 3; Basisrohstoffarten 5; Zwischenprodukte 8.
Alle Vorprodukte: carbon_fiber (Carbon Fiber); chemical_components (Chemical Components); chemical_feedstock (Chemical Feedstock); crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); rubber_blend_components (Rubber Blend Components); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid); synthetic_rubber (Synthetic Rubber); tire_components (Tire Components).
Nur indirekte Inputs: carbon_fiber (Carbon Fiber); chemical_feedstock (Chemical Feedstock); crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid); synthetic_rubber (Synthetic Rubber).
Basisrohstoffe: crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas); natural_rubber (Natural Rubber); sulfur (Sulfur).
Zwischenprodukte: carbon_fiber (Carbon Fiber); chemical_components (Chemical Components); chemical_feedstock (Chemical Feedstock); processed_rubber (Processed Rubber); rubber_blend_components (Rubber Blend Components); sulfuric_acid (Sulfuric Acid); synthetic_rubber (Synthetic Rubber); tire_components (Tire Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); processed_rubber (Processed Rubber); sulfur (Sulfur).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 9.333333333333334, "graphite": 2.0, "natural_gas": 4.833333333333333, "natural_rubber": 5.0, "sulfur": 4.5}`.

### `industrial_seals` — Industrial Seals
Tiefe 3; Basisrohstoffarten 9; Zwischenprodukte 7.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); coal (Coal); crude_oil (Crude Oil); graphite (Graphite); iron_ore (Iron Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); precision_components (Precision Components); processed_rubber (Processed Rubber); steel (Steel); sulfur (Sulfur); tire_components (Tire Components); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); coal (Coal); crude_oil (Crude Oil); graphite (Graphite); iron_ore (Iron Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); steel (Steel); sulfur (Sulfur); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); crude_oil (Crude Oil); graphite (Graphite); iron_ore (Iron Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); sulfur (Sulfur); tungsten_ore (Tungsten Ore).
Zwischenprodukte: aluminum (Aluminum); carbon_fiber (Carbon Fiber); precision_components (Precision Components); processed_rubber (Processed Rubber); steel (Steel); tire_components (Tire Components); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 0.75, "crude_oil": 3.0, "graphite": 1.0, "iron_ore": 3.0, "natural_gas": 1.0, "natural_rubber": 2.0, "sulfur": 1.0, "tungsten_ore": 2.0}`.

### `industrial_sensor` — Industrial Sensor
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 7.
Alle Vorprodukte: control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silver_ore (Silver Ore).
Zwischenprodukte: control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 6.0, "crude_oil": 6.0, "fluorspar": 6.0, "gold_ore": 6.0, "natural_gas": 6.0, "quartz": 24.0, "rare_earth_ore": 5.333333333333333, "silver_ore": 2.0}`.

### `industrial_tires` — Industrial Tires
Tiefe 3; Basisrohstoffarten 5; Zwischenprodukte 3.
Alle Vorprodukte: carbon_fiber (Carbon Fiber); crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); sulfur (Sulfur); tire_components (Tire Components).
Nur indirekte Inputs: carbon_fiber (Carbon Fiber); crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); sulfur (Sulfur).
Basisrohstoffe: crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas); natural_rubber (Natural Rubber); sulfur (Sulfur).
Zwischenprodukte: carbon_fiber (Carbon Fiber); processed_rubber (Processed Rubber); tire_components (Tire Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 9.0, "graphite": 3.0, "natural_gas": 3.0, "natural_rubber": 6.0, "sulfur": 3.0}`.

### `jet_engine` — Jet Engine
Tiefe 3; Basisrohstoffarten 5; Zwischenprodukte 3.
Alle Vorprodukte: coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); titanium (Titanium); titanium_ore (Titanium Ore); turbine_components (Turbine Components).
Nur indirekte Inputs: coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_ore (Nickel Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: nickel_alloy (Nickel Alloy); titanium (Titanium); turbine_components (Turbine Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 1.0, "iron_ore": 6.0, "molybdenum_ore": 2.0, "nickel_ore": 6.0, "titanium_ore": 6.0}`.

### `laboratory_equipment` — Laboratory Equipment
Tiefe 3; Basisrohstoffarten 14; Zwischenprodukte 11.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); glass_panels (Glass Panels); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); precision_components (Precision Components); quartz (Quartz); silica_sand (Silica Sand); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silica_sand (Silica Sand); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: bauxite (Bauxite); borate_ore (Borate Ore); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silica_sand (Silica Sand); silver_ore (Silver Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: aluminum (Aluminum); control_electronics (Control Electronics); copper (Copper); glass (Glass); glass_panels (Glass Panels); gold (Gold); high_purity_silicon (High-Purity Silicon); precision_components (Precision Components); silver (Silver); steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 2.7, "borate_ore": 0.3333333333333333, "coal": 0.75, "copper_ore": 2.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "iron_ore": 3.0, "limestone": 0.3333333333333333, "natural_gas": 2.0, "quartz": 8.0, "silica_sand": 1.3333333333333333, "silver_ore": 2.0, "tungsten_ore": 2.0}`.

### `launch_vehicle` — Launch Vehicle
Tiefe 3; Basisrohstoffarten 14; Zwischenprodukte 11.
Alle Vorprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); titanium (Titanium); titanium_ore (Titanium Ore); turbine_components (Turbine Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_ore (Nickel Ore); quartz (Quartz); silver_ore (Silver Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); carbon_fiber (Carbon Fiber); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); nickel_alloy (Nickel Alloy); silver (Silver); titanium (Titanium); turbine_components (Turbine Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); titanium (Titanium).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "coal": 0.3333333333333333, "copper_ore": 2.0, "crude_oil": 8.0, "fluorspar": 2.0, "gold_ore": 2.0, "graphite": 2.0, "iron_ore": 2.0, "molybdenum_ore": 0.6666666666666666, "natural_gas": 4.0, "nickel_ore": 2.0, "quartz": 8.0, "silver_ore": 2.0, "titanium_ore": 6.0}`.

### `light_aircraft` — Light Aircraft
Tiefe 3; Basisrohstoffarten 9; Zwischenprodukte 8.
Alle Vorprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); avionics_components (Avionics Components); bauxite (Bauxite); carbon_fiber (Carbon Fiber); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); titanium (Titanium); titanium_ore (Titanium Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); natural_gas (Natural Gas); quartz (Quartz); titanium_ore (Titanium Ore).
Zwischenprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); avionics_components (Avionics Components); carbon_fiber (Carbon Fiber); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); titanium (Titanium).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 5.4, "copper_ore": 4.0, "crude_oil": 10.0, "fluorspar": 4.0, "gold_ore": 4.0, "graphite": 2.0, "natural_gas": 6.0, "quartz": 16.0, "titanium_ore": 4.0}`.

### `machine_vision_system` — Machine Vision System
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 7.
Alle Vorprodukte: computing_components (Computing Components); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silver_ore (Silver Ore).
Zwischenprodukte: computing_components (Computing Components); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 8.0, "crude_oil": 8.0, "fluorspar": 8.0, "gold_ore": 8.0, "natural_gas": 8.0, "quartz": 32.0, "rare_earth_ore": 5.333333333333333, "silver_ore": 4.0}`.

### `medical_monitor` — Medical Monitor
Tiefe 3; Basisrohstoffarten 15; Zwischenprodukte 11.
Alle Vorprodukte: borate_ore (Borate Ore); chromium_ore (Chromium Ore); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); display_components (Display Components); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); medical_components (Medical Components); natural_gas (Natural Gas); nickel_ore (Nickel Ore); platinum (Platinum); platinum_ore (Platinum Ore); polymer (Polymer); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); silica_sand (Silica Sand); stainless_steel (Stainless Steel).
Nur indirekte Inputs: borate_ore (Borate Ore); chromium_ore (Chromium Ore); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); nickel_ore (Nickel Ore); platinum (Platinum); platinum_ore (Platinum Ore); polymer (Polymer); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silica_sand (Silica Sand); stainless_steel (Stainless Steel).
Basisrohstoffe: borate_ore (Borate Ore); chromium_ore (Chromium Ore); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); nickel_ore (Nickel Ore); platinum_ore (Platinum Ore); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silica_sand (Silica Sand).
Zwischenprodukte: copper (Copper); display_components (Display Components); glass (Glass); gold (Gold); high_purity_silicon (High-Purity Silicon); medical_components (Medical Components); platinum (Platinum); polymer (Polymer); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); stainless_steel (Stainless Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); glass (Glass); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"borate_ore": 0.6666666666666666, "chromium_ore": 0.6666666666666666, "coal": 1.0, "copper_ore": 2.0, "crude_oil": 4.5, "fluorspar": 3.0, "gold_ore": 2.0, "iron_ore": 4.0, "limestone": 0.6666666666666666, "natural_gas": 3.5, "nickel_ore": 0.6666666666666666, "platinum_ore": 2.0, "quartz": 12.0, "rare_earth_ore": 2.6666666666666665, "silica_sand": 2.6666666666666665}`.

### `memory_module` — Memory Module
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 6.
Alle Vorprodukte: control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); memory_components (Memory Components); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Zwischenprodukte: control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); memory_components (Memory Components); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); silver (Silver).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 6.0, "crude_oil": 8.0, "fluorspar": 8.0, "gold_ore": 6.0, "natural_gas": 8.0, "quartz": 32.0, "silver_ore": 6.0}`.

### `microchip` — Microchip
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 6.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); semiconductor_components (Semiconductor Components); semiconductor_die (Semiconductor Die); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Zwischenprodukte: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); semiconductor_components (Semiconductor Components); semiconductor_die (Semiconductor Die); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 4.0, "crude_oil": 4.0, "fluorspar": 4.0, "gold_ore": 4.0, "natural_gas": 4.0, "quartz": 16.0, "silver_ore": 2.0}`.

### `microcontroller` — Microcontroller
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 6.
Alle Vorprodukte: control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); semiconductor_die (Semiconductor Die); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Zwischenprodukte: control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); semiconductor_die (Semiconductor Die); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); silver (Silver).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 4.0, "crude_oil": 4.0, "fluorspar": 4.0, "gold_ore": 4.0, "natural_gas": 4.0, "quartz": 16.0, "silver_ore": 4.0}`.

### `mining_drill` — Mining Drill
Tiefe 3; Basisrohstoffarten 5; Zwischenprodukte 8.
Alle Vorprodukte: coal (Coal); copper (Copper); copper_ore (Copper Ore); iron (Iron); iron_ore (Iron Ore); mining_components (Mining Components); motor_components (Motor Components); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel); steel_components (Steel Components); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: coal (Coal); copper (Copper); copper_ore (Copper Ore); iron (Iron); iron_ore (Iron Ore); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: coal (Coal); copper_ore (Copper Ore); iron_ore (Iron Ore); rare_earth_ore (Rare Earth Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: copper (Copper); iron (Iron); mining_components (Mining Components); motor_components (Motor Components); rare_earth_metals (Rare Earth Metals); steel (Steel); steel_components (Steel Components); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: iron_ore (Iron Ore); steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 1.5, "copper_ore": 2.0, "iron_ore": 8.0, "rare_earth_ore": 2.6666666666666665, "tungsten_ore": 2.0}`.

### `mining_equipment` — Mining Equipment
Tiefe 3; Basisrohstoffarten 3; Zwischenprodukte 4.
Alle Vorprodukte: coal (Coal); iron_ore (Iron Ore); mining_components (Mining Components); steel (Steel); steel_components (Steel Components); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: coal (Coal); iron_ore (Iron Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: coal (Coal); iron_ore (Iron Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: mining_components (Mining Components); steel (Steel); steel_components (Steel Components); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 2.25, "iron_ore": 9.0, "tungsten_ore": 4.0}`.

### `navigation_satellite` — Navigation Satellite
Tiefe 3; Basisrohstoffarten 10; Zwischenprodukte 10.
Alle Vorprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); telecom_components (Telecom Components); titanium (Titanium); titanium_ore (Titanium Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); carbon_fiber (Carbon Fiber); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); telecom_components (Telecom Components); titanium (Titanium).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); crude_oil (Crude Oil); gold (Gold); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); rare_earth_metals (Rare Earth Metals).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "copper_ore": 6.0, "crude_oil": 7.0, "fluorspar": 4.0, "gold_ore": 4.0, "graphite": 1.0, "natural_gas": 5.0, "quartz": 16.0, "rare_earth_ore": 5.333333333333333, "titanium_ore": 2.0}`.

### `network_switch` — Network Switch
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 7.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); network_components (Network Components); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Zwischenprodukte: aluminum (Aluminum); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); network_components (Network Components); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "copper_ore": 18.0, "crude_oil": 10.0, "fluorspar": 10.0, "gold_ore": 10.0, "natural_gas": 10.0, "quartz": 40.0, "silver_ore": 2.0}`.

### `nuclear_fuel_assembly` — Nuclear Fuel Assembly
Tiefe 3; Basisrohstoffarten 3; Zwischenprodukte 5.
Alle Vorprodukte: borate_ore (Borate Ore); lead (Lead); lead_ore (Lead Ore); nuclear_fuel_components (Nuclear Fuel Components); nuclear_material (Nuclear Material); shielding_components (Shielding Components); shielding_material (Shielding Material); uranium_ore (Uranium Ore).
Nur indirekte Inputs: borate_ore (Borate Ore); lead (Lead); lead_ore (Lead Ore); nuclear_material (Nuclear Material); shielding_material (Shielding Material); uranium_ore (Uranium Ore).
Basisrohstoffe: borate_ore (Borate Ore); lead_ore (Lead Ore); uranium_ore (Uranium Ore).
Zwischenprodukte: lead (Lead); nuclear_fuel_components (Nuclear Fuel Components); nuclear_material (Nuclear Material); shielding_components (Shielding Components); shielding_material (Shielding Material).
Gemeinsam verwendete Vorprodukte in dieser Kette: lead_ore (Lead Ore); shielding_material (Shielding Material).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"borate_ore": 1.0, "lead_ore": 6.8999999999999995, "uranium_ore": 6.0}`.

### `nuclear_reactor` — Nuclear Reactor
Tiefe 3; Basisrohstoffarten 14; Zwischenprodukte 12.
Alle Vorprodukte: borate_ore (Borate Ore); cement (Cement); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); lead_ore (Lead Ore); limestone (Limestone); natural_gas (Natural Gas); nuclear_fuel_components (Nuclear Fuel Components); nuclear_material (Nuclear Material); quartz (Quartz); reactor_components (Reactor Components); shielding_material (Shielding Material); silver (Silver); silver_ore (Silver Ore); steel (Steel); structural_components (Structural Components); uranium_ore (Uranium Ore).
Nur indirekte Inputs: borate_ore (Borate Ore); cement (Cement); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); lead_ore (Lead Ore); limestone (Limestone); natural_gas (Natural Gas); nuclear_material (Nuclear Material); quartz (Quartz); shielding_material (Shielding Material); silver (Silver); silver_ore (Silver Ore); steel (Steel); uranium_ore (Uranium Ore).
Basisrohstoffe: borate_ore (Borate Ore); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); gypsum (Gypsum); iron_ore (Iron Ore); lead_ore (Lead Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore); uranium_ore (Uranium Ore).
Zwischenprodukte: cement (Cement); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); nuclear_fuel_components (Nuclear Fuel Components); nuclear_material (Nuclear Material); reactor_components (Reactor Components); shielding_material (Shielding Material); silver (Silver); steel (Steel); structural_components (Structural Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: lead_ore (Lead Ore); nuclear_material (Nuclear Material).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"borate_ore": 0.3333333333333333, "coal": 1.125, "copper_ore": 2.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "gypsum": 0.16666666666666666, "iron_ore": 4.5, "lead_ore": 3.333333333333333, "limestone": 0.6666666666666666, "natural_gas": 2.0, "quartz": 8.0, "silver_ore": 2.0, "uranium_ore": 6.0}`.

### `orbital_vehicle` — Orbital Vehicle
Tiefe 3; Basisrohstoffarten 10; Zwischenprodukte 10.
Alle Vorprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); avionics_components (Avionics Components); bauxite (Bauxite); carbon_fiber (Carbon Fiber); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); titanium (Titanium); titanium_ore (Titanium Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); avionics_components (Avionics Components); carbon_fiber (Carbon Fiber); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); silver (Silver); titanium (Titanium).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); copper (Copper); crude_oil (Crude Oil); gold (Gold); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 5.4, "copper_ore": 6.0, "crude_oil": 12.0, "fluorspar": 6.0, "gold_ore": 6.0, "graphite": 2.0, "natural_gas": 8.0, "quartz": 24.0, "silver_ore": 2.0, "titanium_ore": 4.0}`.

### `packaged_beverages` — Packaged Beverages
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 7.
Alle Vorprodukte: crude_oil (Crude Oil); fruit (Fruit); fruit_concentrate (Fruit Concentrate); natural_gas (Natural Gas); nutrition_components (Nutrition Components); packaging_components (Packaging Components); polymer (Polymer); rapeseed (Rapeseed); soy_protein (Soy Protein); soybeans (Soybeans); sugarcane (Sugarcane); timber (Timber); vegetable_oil (Vegetable Oil); wood_pulp (Wood Pulp).
Nur indirekte Inputs: crude_oil (Crude Oil); fruit (Fruit); fruit_concentrate (Fruit Concentrate); natural_gas (Natural Gas); polymer (Polymer); rapeseed (Rapeseed); soy_protein (Soy Protein); soybeans (Soybeans); sugarcane (Sugarcane); timber (Timber); vegetable_oil (Vegetable Oil); wood_pulp (Wood Pulp).
Basisrohstoffe: crude_oil (Crude Oil); fruit (Fruit); natural_gas (Natural Gas); rapeseed (Rapeseed); soybeans (Soybeans); sugarcane (Sugarcane); timber (Timber).
Zwischenprodukte: fruit_concentrate (Fruit Concentrate); nutrition_components (Nutrition Components); packaging_components (Packaging Components); polymer (Polymer); soy_protein (Soy Protein); vegetable_oil (Vegetable Oil); wood_pulp (Wood Pulp).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); soybeans (Soybeans).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 1.0833333333333333, "fruit": 1.5, "natural_gas": 0.5833333333333333, "rapeseed": 1.0, "soybeans": 3.0, "sugarcane": 0.5, "timber": 1.0}`.

### `packaged_food` — Packaged Food
Tiefe 3; Basisrohstoffarten 9; Zwischenprodukte 11.
Alle Vorprodukte: corn (Corn); corn_meal (Corn Meal); crude_oil (Crude Oil); flour (Flour); food_ingredients (Food Ingredients); fruit (Fruit); natural_gas (Natural Gas); organic_feedstock (Organic Feedstock); packaging_components (Packaging Components); polymer (Polymer); potatoes (Potatoes); raw_sugar (Raw Sugar); refined_sugar (Refined Sugar); soy_oil (Soy Oil); soybeans (Soybeans); sugarcane (Sugarcane); sweetener_components (Sweetener Components); timber (Timber); wheat (Wheat); wood_pulp (Wood Pulp).
Nur indirekte Inputs: corn (Corn); corn_meal (Corn Meal); crude_oil (Crude Oil); flour (Flour); fruit (Fruit); natural_gas (Natural Gas); organic_feedstock (Organic Feedstock); polymer (Polymer); potatoes (Potatoes); raw_sugar (Raw Sugar); refined_sugar (Refined Sugar); soy_oil (Soy Oil); soybeans (Soybeans); sugarcane (Sugarcane); timber (Timber); wheat (Wheat); wood_pulp (Wood Pulp).
Basisrohstoffe: corn (Corn); crude_oil (Crude Oil); fruit (Fruit); natural_gas (Natural Gas); potatoes (Potatoes); soybeans (Soybeans); sugarcane (Sugarcane); timber (Timber); wheat (Wheat).
Zwischenprodukte: corn_meal (Corn Meal); flour (Flour); food_ingredients (Food Ingredients); organic_feedstock (Organic Feedstock); packaging_components (Packaging Components); polymer (Polymer); raw_sugar (Raw Sugar); refined_sugar (Refined Sugar); soy_oil (Soy Oil); sweetener_components (Sweetener Components); wood_pulp (Wood Pulp).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); sugarcane (Sugarcane); wheat (Wheat).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"corn": 1.0, "crude_oil": 1.0833333333333333, "fruit": 0.5, "natural_gas": 0.5833333333333333, "potatoes": 0.5, "soybeans": 2.0, "sugarcane": 3.0, "timber": 1.0, "wheat": 1.5}`.

### `packaged_meals` — Packaged Meals
Tiefe 3; Basisrohstoffarten 9; Zwischenprodukte 11.
Alle Vorprodukte: corn (Corn); corn_meal (Corn Meal); crude_oil (Crude Oil); flour (Flour); food_ingredients (Food Ingredients); fruit (Fruit); fruit_concentrate (Fruit Concentrate); natural_gas (Natural Gas); nutrition_components (Nutrition Components); packaging_components (Packaging Components); polymer (Polymer); rapeseed (Rapeseed); refined_sugar (Refined Sugar); soy_protein (Soy Protein); soybeans (Soybeans); sugarcane (Sugarcane); timber (Timber); vegetable_oil (Vegetable Oil); wheat (Wheat); wood_pulp (Wood Pulp).
Nur indirekte Inputs: corn (Corn); corn_meal (Corn Meal); crude_oil (Crude Oil); flour (Flour); fruit (Fruit); fruit_concentrate (Fruit Concentrate); natural_gas (Natural Gas); polymer (Polymer); rapeseed (Rapeseed); refined_sugar (Refined Sugar); soy_protein (Soy Protein); soybeans (Soybeans); sugarcane (Sugarcane); timber (Timber); vegetable_oil (Vegetable Oil); wheat (Wheat); wood_pulp (Wood Pulp).
Basisrohstoffe: corn (Corn); crude_oil (Crude Oil); fruit (Fruit); natural_gas (Natural Gas); rapeseed (Rapeseed); soybeans (Soybeans); sugarcane (Sugarcane); timber (Timber); wheat (Wheat).
Zwischenprodukte: corn_meal (Corn Meal); flour (Flour); food_ingredients (Food Ingredients); fruit_concentrate (Fruit Concentrate); nutrition_components (Nutrition Components); packaging_components (Packaging Components); polymer (Polymer); refined_sugar (Refined Sugar); soy_protein (Soy Protein); vegetable_oil (Vegetable Oil); wood_pulp (Wood Pulp).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); soybeans (Soybeans); sugarcane (Sugarcane).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"corn": 1.0, "crude_oil": 1.0833333333333333, "fruit": 3.0, "natural_gas": 0.5833333333333333, "rapeseed": 2.0, "soybeans": 6.0, "sugarcane": 2.0, "timber": 1.0, "wheat": 1.0}`.

### `packaged_nutrition` — Packaged Nutrition
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 7.
Alle Vorprodukte: crude_oil (Crude Oil); fruit (Fruit); fruit_concentrate (Fruit Concentrate); natural_gas (Natural Gas); nutrition_components (Nutrition Components); packaging_components (Packaging Components); polymer (Polymer); rapeseed (Rapeseed); soy_protein (Soy Protein); soybeans (Soybeans); sugarcane (Sugarcane); timber (Timber); vegetable_oil (Vegetable Oil); wood_pulp (Wood Pulp).
Nur indirekte Inputs: crude_oil (Crude Oil); fruit (Fruit); fruit_concentrate (Fruit Concentrate); natural_gas (Natural Gas); polymer (Polymer); rapeseed (Rapeseed); soy_protein (Soy Protein); soybeans (Soybeans); sugarcane (Sugarcane); timber (Timber); vegetable_oil (Vegetable Oil); wood_pulp (Wood Pulp).
Basisrohstoffe: crude_oil (Crude Oil); fruit (Fruit); natural_gas (Natural Gas); rapeseed (Rapeseed); soybeans (Soybeans); sugarcane (Sugarcane); timber (Timber).
Zwischenprodukte: fruit_concentrate (Fruit Concentrate); nutrition_components (Nutrition Components); packaging_components (Packaging Components); polymer (Polymer); soy_protein (Soy Protein); vegetable_oil (Vegetable Oil); wood_pulp (Wood Pulp).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); soybeans (Soybeans).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 1.0833333333333333, "fruit": 3.0, "natural_gas": 0.5833333333333333, "rapeseed": 2.0, "soybeans": 6.0, "sugarcane": 1.0, "timber": 1.0}`.

### `packaging_materials` — Packaging Materials
Tiefe 3; Basisrohstoffarten 3; Zwischenprodukte 3.
Alle Vorprodukte: crude_oil (Crude Oil); natural_gas (Natural Gas); packaging_components (Packaging Components); polymer (Polymer); timber (Timber); wood_pulp (Wood Pulp).
Nur indirekte Inputs: crude_oil (Crude Oil); natural_gas (Natural Gas); polymer (Polymer); timber (Timber); wood_pulp (Wood Pulp).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: packaging_components (Packaging Components); polymer (Polymer); wood_pulp (Wood Pulp).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 2.1666666666666665, "natural_gas": 1.1666666666666665, "timber": 2.0}`.

### `power_cable` — Power Cable
Tiefe 3; Basisrohstoffarten 4; Zwischenprodukte 5.
Alle Vorprodukte: aluminum (Aluminum); aluminum_components (Aluminum Components); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); insulated_wire (Insulated Wire); natural_gas (Natural Gas); polymer (Polymer).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); natural_gas (Natural Gas); polymer (Polymer).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); natural_gas (Natural Gas).
Zwischenprodukte: aluminum (Aluminum); aluminum_components (Aluminum Components); copper (Copper); insulated_wire (Insulated Wire); polymer (Polymer).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "copper_ore": 2.0, "crude_oil": 1.5, "natural_gas": 0.5}`.

### `precision_motor` — Precision Motor
Tiefe 3; Basisrohstoffarten 6; Zwischenprodukte 9.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); iron (Iron); iron_ore (Iron Ore); magnetic_components (Magnetic Components); motor_components (Motor Components); precision_components (Precision Components); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); iron (Iron); iron_ore (Iron Ore); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); iron_ore (Iron Ore); rare_earth_ore (Rare Earth Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); iron (Iron); magnetic_components (Magnetic Components); motor_components (Motor Components); precision_components (Precision Components); rare_earth_metals (Rare Earth Metals); steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: iron (Iron); iron_ore (Iron Ore); rare_earth_metals (Rare Earth Metals).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 0.75, "copper_ore": 2.0, "iron_ore": 7.0, "rare_earth_ore": 5.333333333333333, "tungsten_ore": 2.0}`.

### `prefabricated_structures` — Prefabricated Structures
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 7.
Alle Vorprodukte: cement (Cement); coal (Coal); concrete_components (Concrete Components); crude_oil (Crude Oil); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); lumber (Lumber); natural_gas (Natural Gas); steel (Steel); structural_components (Structural Components); timber (Timber); treated_lumber (Treated Lumber); wooden_components (Wooden Components).
Nur indirekte Inputs: cement (Cement); coal (Coal); crude_oil (Crude Oil); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); lumber (Lumber); natural_gas (Natural Gas); steel (Steel); timber (Timber); treated_lumber (Treated Lumber).
Basisrohstoffe: coal (Coal); crude_oil (Crude Oil); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: cement (Cement); concrete_components (Concrete Components); lumber (Lumber); steel (Steel); structural_components (Structural Components); treated_lumber (Treated Lumber); wooden_components (Wooden Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: cement (Cement); steel (Steel); timber (Timber).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 1.5, "crude_oil": 0.3333333333333333, "gypsum": 0.5, "iron_ore": 6.0, "limestone": 2.0, "natural_gas": 0.16666666666666666, "timber": 1.5}`.

### `premium_electric_vehicle` — Premium Electric Vehicle
Tiefe 3; Basisrohstoffarten 15; Zwischenprodukte 12.
Alle Vorprodukte: advanced_cell_components (Advanced Cell Components); aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); coal (Coal); cobalt (Cobalt); cobalt_ore (Cobalt Ore); crude_oil (Crude Oil); display_components (Display Components); fluorspar (Fluorspar); glass (Glass); graphite (Graphite); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); lithium (Lithium); lithium_ore (Lithium Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); polymer (Polymer); processed_rubber (Processed Rubber); purified_graphite (Purified Graphite); quartz (Quartz); silica_sand (Silica Sand); steel (Steel); sulfur (Sulfur); vehicle_components (Vehicle Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); coal (Coal); cobalt (Cobalt); cobalt_ore (Cobalt Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); graphite (Graphite); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); lithium (Lithium); lithium_ore (Lithium Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); polymer (Polymer); processed_rubber (Processed Rubber); purified_graphite (Purified Graphite); quartz (Quartz); silica_sand (Silica Sand); steel (Steel); sulfur (Sulfur).
Basisrohstoffe: bauxite (Bauxite); borate_ore (Borate Ore); coal (Coal); cobalt_ore (Cobalt Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); graphite (Graphite); iron_ore (Iron Ore); limestone (Limestone); lithium_ore (Lithium Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); quartz (Quartz); silica_sand (Silica Sand); sulfur (Sulfur).
Zwischenprodukte: advanced_cell_components (Advanced Cell Components); aluminum (Aluminum); cobalt (Cobalt); display_components (Display Components); glass (Glass); high_purity_silicon (High-Purity Silicon); lithium (Lithium); polymer (Polymer); processed_rubber (Processed Rubber); purified_graphite (Purified Graphite); steel (Steel); vehicle_components (Vehicle Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "borate_ore": 0.3333333333333333, "coal": 0.75, "cobalt_ore": 2.0, "crude_oil": 2.5, "fluorspar": 1.0, "graphite": 1.3333333333333333, "iron_ore": 3.0, "limestone": 0.3333333333333333, "lithium_ore": 2.0, "natural_gas": 1.5, "natural_rubber": 1.0, "quartz": 4.0, "silica_sand": 1.3333333333333333, "sulfur": 0.5}`.

### `processed_food` — Processed Food
Tiefe 3; Basisrohstoffarten 6; Zwischenprodukte 8.
Alle Vorprodukte: corn (Corn); corn_meal (Corn Meal); flour (Flour); food_ingredients (Food Ingredients); fruit (Fruit); fruit_concentrate (Fruit Concentrate); nutrition_components (Nutrition Components); rapeseed (Rapeseed); refined_sugar (Refined Sugar); soy_protein (Soy Protein); soybeans (Soybeans); sugarcane (Sugarcane); vegetable_oil (Vegetable Oil); wheat (Wheat).
Nur indirekte Inputs: corn (Corn); corn_meal (Corn Meal); flour (Flour); fruit (Fruit); fruit_concentrate (Fruit Concentrate); rapeseed (Rapeseed); refined_sugar (Refined Sugar); soy_protein (Soy Protein); soybeans (Soybeans); sugarcane (Sugarcane); vegetable_oil (Vegetable Oil); wheat (Wheat).
Basisrohstoffe: corn (Corn); fruit (Fruit); rapeseed (Rapeseed); soybeans (Soybeans); sugarcane (Sugarcane); wheat (Wheat).
Zwischenprodukte: corn_meal (Corn Meal); flour (Flour); food_ingredients (Food Ingredients); fruit_concentrate (Fruit Concentrate); nutrition_components (Nutrition Components); refined_sugar (Refined Sugar); soy_protein (Soy Protein); vegetable_oil (Vegetable Oil).
Gemeinsam verwendete Vorprodukte in dieser Kette: soybeans (Soybeans); sugarcane (Sugarcane).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"corn": 1.0, "fruit": 1.5, "rapeseed": 1.0, "soybeans": 3.0, "sugarcane": 1.5, "wheat": 1.0}`.

### `processing_equipment` — Processing Equipment
Tiefe 3; Basisrohstoffarten 9; Zwischenprodukte 8.
Alle Vorprodukte: coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); natural_gas (Natural Gas); pump_components (Pump Components); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); steel (Steel); steel_components (Steel Components).
Nur indirekte Inputs: coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); steel (Steel).
Basisrohstoffe: coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Zwischenprodukte: control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); pump_components (Pump Components); silver (Silver); steel (Steel); steel_components (Steel Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 2.25, "copper_ore": 4.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "iron_ore": 9.0, "natural_gas": 2.0, "quartz": 8.0, "silver_ore": 2.0}`.

### `protective_clothing` — Protective Clothing
Tiefe 3; Basisrohstoffarten 6; Zwischenprodukte 6.
Alle Vorprodukte: carbon_fiber (Carbon Fiber); cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); graphite (Graphite); industrial_fabric (Industrial Fabric); natural_gas (Natural Gas); natural_rubber (Natural Rubber); polymer (Polymer); processed_rubber (Processed Rubber); sulfur (Sulfur); tire_components (Tire Components).
Nur indirekte Inputs: carbon_fiber (Carbon Fiber); cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas); natural_rubber (Natural Rubber); polymer (Polymer); processed_rubber (Processed Rubber); sulfur (Sulfur).
Basisrohstoffe: cotton (Cotton); crude_oil (Crude Oil); graphite (Graphite); natural_gas (Natural Gas); natural_rubber (Natural Rubber); sulfur (Sulfur).
Zwischenprodukte: carbon_fiber (Carbon Fiber); cotton_fiber (Cotton Fiber); industrial_fabric (Industrial Fabric); polymer (Polymer); processed_rubber (Processed Rubber); tire_components (Tire Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); processed_rubber (Processed Rubber).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"cotton": 2.0, "crude_oil": 6.0, "graphite": 1.0, "natural_gas": 2.0, "natural_rubber": 4.0, "sulfur": 2.0}`.

### `protective_packaging` — Protective Packaging
Tiefe 3; Basisrohstoffarten 4; Zwischenprodukte 5.
Alle Vorprodukte: crude_oil (Crude Oil); gypsum (Gypsum); insulation_material (Insulation Material); natural_gas (Natural Gas); packaging_components (Packaging Components); polymer (Polymer); processed_gypsum (Processed Gypsum); timber (Timber); wood_pulp (Wood Pulp).
Nur indirekte Inputs: crude_oil (Crude Oil); gypsum (Gypsum); natural_gas (Natural Gas); polymer (Polymer); processed_gypsum (Processed Gypsum); timber (Timber); wood_pulp (Wood Pulp).
Basisrohstoffe: crude_oil (Crude Oil); gypsum (Gypsum); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: insulation_material (Insulation Material); packaging_components (Packaging Components); polymer (Polymer); processed_gypsum (Processed Gypsum); wood_pulp (Wood Pulp).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); polymer (Polymer).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 1.8333333333333333, "gypsum": 0.5, "natural_gas": 0.8333333333333333, "timber": 1.0}`.

### `quantum_computing_module` — Quantum Computing Module
Tiefe 3; Basisrohstoffarten 11; Zwischenprodukte 11.
Alle Vorprodukte: control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); molybdenum (Molybdenum); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); niobium (Niobium); niobium_ore (Niobium Ore); processor_components (Processor Components); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); refractory_alloy_components (Refractory Alloy Components); silver (Silver); silver_ore (Silver Ore); superconducting_alloy (Superconducting Alloy); titanium_ore (Titanium Ore).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); molybdenum (Molybdenum); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); niobium (Niobium); niobium_ore (Niobium Ore); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore); superconducting_alloy (Superconducting Alloy); titanium_ore (Titanium Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); niobium_ore (Niobium Ore); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silver_ore (Silver Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); molybdenum (Molybdenum); niobium (Niobium); processor_components (Processor Components); rare_earth_metals (Rare Earth Metals); refractory_alloy_components (Refractory Alloy Components); silver (Silver); superconducting_alloy (Superconducting Alloy).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); niobium_ore (Niobium Ore); rare_earth_ore (Rare Earth Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 4.0, "crude_oil": 4.0, "fluorspar": 4.0, "gold_ore": 6.0, "molybdenum_ore": 2.0, "natural_gas": 4.0, "niobium_ore": 4.0, "quartz": 16.0, "rare_earth_ore": 4.166666666666666, "silver_ore": 2.0, "titanium_ore": 1.0}`.

### `radio_transceiver` — Radio Transceiver
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 7.
Alle Vorprodukte: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron (Iron); iron_ore (Iron Ore); magnetic_components (Magnetic Components); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); telecom_components (Telecom Components).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron (Iron); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); iron (Iron); magnetic_components (Magnetic Components); rare_earth_metals (Rare Earth Metals); telecom_components (Telecom Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: rare_earth_metals (Rare Earth Metals).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 8.0, "crude_oil": 4.0, "fluorspar": 4.0, "gold_ore": 4.0, "iron_ore": 2.0, "natural_gas": 4.0, "quartz": 16.0, "rare_earth_ore": 8.0}`.

### `railway_track` — Railway Track
Tiefe 3; Basisrohstoffarten 3; Zwischenprodukte 4.
Alle Vorprodukte: coal (Coal); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); rail_components (Rail Components); steel (Steel); steel_components (Steel Components).
Nur indirekte Inputs: coal (Coal); iron_ore (Iron Ore); manganese (Manganese); manganese_ore (Manganese Ore); steel (Steel).
Basisrohstoffe: coal (Coal); iron_ore (Iron Ore); manganese_ore (Manganese Ore).
Zwischenprodukte: manganese (Manganese); rail_components (Rail Components); steel (Steel); steel_components (Steel Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 3.75, "iron_ore": 15.0, "manganese_ore": 3.6}`.

### `reinforced_concrete` — Reinforced Concrete
Tiefe 3; Basisrohstoffarten 4; Zwischenprodukte 4.
Alle Vorprodukte: cement (Cement); coal (Coal); concrete_components (Concrete Components); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); steel (Steel); steel_components (Steel Components).
Nur indirekte Inputs: cement (Cement); coal (Coal); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); steel (Steel).
Basisrohstoffe: coal (Coal); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone).
Zwischenprodukte: cement (Cement); concrete_components (Concrete Components); steel (Steel); steel_components (Steel Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 1.5, "gypsum": 0.6666666666666666, "iron_ore": 6.0, "limestone": 2.6666666666666665}`.

### `robotic_actuator` — Robotic Actuator
Tiefe 3; Basisrohstoffarten 6; Zwischenprodukte 8.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); iron (Iron); iron_ore (Iron Ore); motor_components (Motor Components); precision_components (Precision Components); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); iron (Iron); iron_ore (Iron Ore); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); iron_ore (Iron Ore); rare_earth_ore (Rare Earth Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); iron (Iron); motor_components (Motor Components); precision_components (Precision Components); rare_earth_metals (Rare Earth Metals); steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 0.75, "copper_ore": 2.0, "iron_ore": 5.0, "rare_earth_ore": 2.6666666666666665, "tungsten_ore": 2.0}`.

### `robotic_arm` — Robotic Arm
Tiefe 3; Basisrohstoffarten 12; Zwischenprodukte 12.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron (Iron); iron_ore (Iron Ore); motor_components (Motor Components); natural_gas (Natural Gas); precision_components (Precision Components); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron (Iron); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silver_ore (Silver Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: aluminum (Aluminum); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); iron (Iron); motor_components (Motor Components); precision_components (Precision Components); rare_earth_metals (Rare Earth Metals); silver (Silver); steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "coal": 1.5, "copper_ore": 4.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "iron_ore": 8.0, "natural_gas": 2.0, "quartz": 8.0, "rare_earth_ore": 2.6666666666666665, "silver_ore": 2.0, "tungsten_ore": 4.0}`.

### `rocket_engine` — Rocket Engine
Tiefe 3; Basisrohstoffarten 5; Zwischenprodukte 4.
Alle Vorprodukte: coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); titanium (Titanium); titanium_components (Titanium Components); titanium_ore (Titanium Ore); turbine_components (Turbine Components).
Nur indirekte Inputs: coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_ore (Nickel Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: nickel_alloy (Nickel Alloy); titanium (Titanium); titanium_components (Titanium Components); turbine_components (Turbine Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: titanium (Titanium).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 0.6666666666666666, "iron_ore": 4.0, "molybdenum_ore": 1.3333333333333333, "nickel_ore": 4.0, "titanium_ore": 6.0}`.

### `router` — Router
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 7.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); network_components (Network Components); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); telecom_components (Telecom Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); network_components (Network Components); rare_earth_metals (Rare Earth Metals); telecom_components (Telecom Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "copper_ore": 12.0, "crude_oil": 6.0, "fluorspar": 6.0, "gold_ore": 6.0, "natural_gas": 6.0, "quartz": 24.0, "rare_earth_ore": 2.6666666666666665}`.

### `safety_equipment` — Safety Equipment
Tiefe 3; Basisrohstoffarten 10; Zwischenprodukte 9.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); carbon_fiber (Carbon Fiber); cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); glass (Glass); glass_panels (Glass Panels); graphite (Graphite); industrial_fabric (Industrial Fabric); limestone (Limestone); natural_gas (Natural Gas); natural_rubber (Natural Rubber); polymer (Polymer); processed_rubber (Processed Rubber); silica_sand (Silica Sand); sulfur (Sulfur); tire_components (Tire Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); carbon_fiber (Carbon Fiber); cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); glass (Glass); graphite (Graphite); limestone (Limestone); natural_gas (Natural Gas); natural_rubber (Natural Rubber); polymer (Polymer); processed_rubber (Processed Rubber); silica_sand (Silica Sand); sulfur (Sulfur).
Basisrohstoffe: bauxite (Bauxite); borate_ore (Borate Ore); cotton (Cotton); crude_oil (Crude Oil); graphite (Graphite); limestone (Limestone); natural_gas (Natural Gas); natural_rubber (Natural Rubber); silica_sand (Silica Sand); sulfur (Sulfur).
Zwischenprodukte: aluminum (Aluminum); carbon_fiber (Carbon Fiber); cotton_fiber (Cotton Fiber); glass (Glass); glass_panels (Glass Panels); industrial_fabric (Industrial Fabric); polymer (Polymer); processed_rubber (Processed Rubber); tire_components (Tire Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); processed_rubber (Processed Rubber).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 0.9, "borate_ore": 0.3333333333333333, "cotton": 1.0, "crude_oil": 4.5, "graphite": 1.0, "limestone": 0.3333333333333333, "natural_gas": 1.5, "natural_rubber": 3.0, "silica_sand": 1.3333333333333333, "sulfur": 1.5}`.

### `satellite` — Satellite
Tiefe 3; Basisrohstoffarten 13; Zwischenprodukte 11.
Alle Vorprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); carbon_fiber (Carbon Fiber); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silica_sand (Silica Sand); solar_components (Solar Components); telecom_components (Telecom Components); titanium (Titanium); titanium_ore (Titanium Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); carbon_fiber (Carbon Fiber); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silica_sand (Silica Sand); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); borate_ore (Borate Ore); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silica_sand (Silica Sand); titanium_ore (Titanium Ore).
Zwischenprodukte: aerospace_components (Aerospace Components); aluminum (Aluminum); carbon_fiber (Carbon Fiber); copper (Copper); glass (Glass); gold (Gold); high_purity_silicon (High-Purity Silicon); rare_earth_metals (Rare Earth Metals); solar_components (Solar Components); telecom_components (Telecom Components); titanium (Titanium).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); crude_oil (Crude Oil); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "borate_ore": 0.3333333333333333, "copper_ore": 4.0, "crude_oil": 6.0, "fluorspar": 3.0, "gold_ore": 2.0, "graphite": 1.0, "limestone": 0.3333333333333333, "natural_gas": 4.0, "quartz": 12.0, "rare_earth_ore": 2.6666666666666665, "silica_sand": 1.3333333333333333, "titanium_ore": 2.0}`.

### `semiconductor_equipment` — Semiconductor Equipment
Tiefe 3; Basisrohstoffarten 14; Zwischenprodukte 11.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); ceramic_components (Ceramic Components); ceramics (Ceramics); clay (Clay); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas); precision_components (Precision Components); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); ceramics (Ceramics); clay (Clay); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: bauxite (Bauxite); clay (Clay); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); kaolin (Kaolin); magnesite (Magnesite); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: aluminum (Aluminum); ceramic_components (Ceramic Components); ceramics (Ceramics); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); precision_components (Precision Components); silver (Silver); steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: —.
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "clay": 1.0, "coal": 1.5, "copper_ore": 2.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "iron_ore": 6.0, "kaolin": 0.3333333333333333, "magnesite": 0.3333333333333333, "natural_gas": 2.0, "quartz": 8.0, "silver_ore": 2.0, "tungsten_ore": 4.0}`.

### `server` — Server
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 6.
Alle Vorprodukte: computing_components (Computing Components); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); memory_components (Memory Components); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); quartz (Quartz); silver (Silver); silver_ore (Silver Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore).
Zwischenprodukte: computing_components (Computing Components); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); memory_components (Memory Components); silver (Silver).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); silver (Silver).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 10.0, "crude_oil": 11.0, "fluorspar": 11.0, "gold_ore": 10.0, "natural_gas": 11.0, "quartz": 44.0, "silver_ore": 10.0}`.

### `server_rack` — Server Rack
Tiefe 3; Basisrohstoffarten 11; Zwischenprodukte 9.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); cement (Cement); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); network_components (Network Components); quartz (Quartz); server_components (Server Components); steel (Steel); structural_components (Structural Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); cement (Cement); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); steel (Steel).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz).
Zwischenprodukte: aluminum (Aluminum); cement (Cement); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); network_components (Network Components); server_components (Server Components); steel (Steel); structural_components (Structural Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 1.125, "copper_ore": 12.0, "crude_oil": 8.0, "fluorspar": 8.0, "gold_ore": 8.0, "gypsum": 0.16666666666666666, "iron_ore": 4.5, "limestone": 0.6666666666666666, "natural_gas": 8.0, "quartz": 32.0}`.

### `servo_motor` — Servo Motor
Tiefe 3; Basisrohstoffarten 12; Zwischenprodukte 12.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron (Iron); iron_ore (Iron Ore); motor_components (Motor Components); natural_gas (Natural Gas); precision_components (Precision Components); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron (Iron); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silver_ore (Silver Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: aluminum (Aluminum); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); iron (Iron); motor_components (Motor Components); precision_components (Precision Components); rare_earth_metals (Rare Earth Metals); silver (Silver); steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 0.75, "copper_ore": 4.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "iron_ore": 5.0, "natural_gas": 2.0, "quartz": 8.0, "rare_earth_ore": 2.6666666666666665, "silver_ore": 2.0, "tungsten_ore": 2.0}`.

### `soft_drinks` — Soft Drinks
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 7.
Alle Vorprodukte: crude_oil (Crude Oil); fruit (Fruit); fruit_concentrate (Fruit Concentrate); natural_gas (Natural Gas); nutrition_components (Nutrition Components); packaging_components (Packaging Components); polymer (Polymer); rapeseed (Rapeseed); soy_protein (Soy Protein); soybeans (Soybeans); sugarcane (Sugarcane); timber (Timber); vegetable_oil (Vegetable Oil); wood_pulp (Wood Pulp).
Nur indirekte Inputs: crude_oil (Crude Oil); fruit (Fruit); fruit_concentrate (Fruit Concentrate); natural_gas (Natural Gas); polymer (Polymer); rapeseed (Rapeseed); soy_protein (Soy Protein); soybeans (Soybeans); sugarcane (Sugarcane); timber (Timber); vegetable_oil (Vegetable Oil); wood_pulp (Wood Pulp).
Basisrohstoffe: crude_oil (Crude Oil); fruit (Fruit); natural_gas (Natural Gas); rapeseed (Rapeseed); soybeans (Soybeans); sugarcane (Sugarcane); timber (Timber).
Zwischenprodukte: fruit_concentrate (Fruit Concentrate); nutrition_components (Nutrition Components); packaging_components (Packaging Components); polymer (Polymer); soy_protein (Soy Protein); vegetable_oil (Vegetable Oil); wood_pulp (Wood Pulp).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); soybeans (Soybeans).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 1.0833333333333333, "fruit": 3.0, "natural_gas": 0.5833333333333333, "rapeseed": 2.0, "soybeans": 6.0, "sugarcane": 1.0, "timber": 1.0}`.

### `solar_array` — Solar Array
Tiefe 3; Basisrohstoffarten 10; Zwischenprodukte 7.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); limestone (Limestone); natural_gas (Natural Gas); power_electronics (Power Electronics); quartz (Quartz); silica_sand (Silica Sand); solar_components (Solar Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); borate_ore (Borate Ore); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); glass (Glass); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silica_sand (Silica Sand).
Basisrohstoffe: bauxite (Bauxite); borate_ore (Borate Ore); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); limestone (Limestone); natural_gas (Natural Gas); quartz (Quartz); silica_sand (Silica Sand).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); glass (Glass); gold (Gold); high_purity_silicon (High-Purity Silicon); power_electronics (Power Electronics); solar_components (Solar Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: aluminum (Aluminum); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 5.4, "borate_ore": 0.6666666666666666, "copper_ore": 4.0, "crude_oil": 4.0, "fluorspar": 4.0, "gold_ore": 2.0, "limestone": 0.6666666666666666, "natural_gas": 4.0, "quartz": 16.0, "silica_sand": 2.6666666666666665}`.

### `steam_turbine` — Steam Turbine
Tiefe 3; Basisrohstoffarten 6; Zwischenprodukte 5.
Alle Vorprodukte: chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); stainless_components (Stainless Components); stainless_steel (Stainless Steel); titanium (Titanium); titanium_ore (Titanium Ore); turbine_components (Turbine Components).
Nur indirekte Inputs: chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); stainless_steel (Stainless Steel); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); nickel_ore (Nickel Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: nickel_alloy (Nickel Alloy); stainless_components (Stainless Components); stainless_steel (Stainless Steel); titanium (Titanium); turbine_components (Turbine Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: coal (Coal); iron_ore (Iron Ore); nickel_ore (Nickel Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"chromium_ore": 0.6666666666666666, "coal": 1.6666666666666665, "iron_ore": 8.0, "molybdenum_ore": 1.3333333333333333, "nickel_ore": 4.666666666666667, "titanium_ore": 4.0}`.

### `structural_systems` — Structural Systems
Tiefe 3; Basisrohstoffarten 4; Zwischenprodukte 4.
Alle Vorprodukte: cement (Cement); coal (Coal); concrete_components (Concrete Components); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); steel (Steel); structural_components (Structural Components).
Nur indirekte Inputs: cement (Cement); coal (Coal); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); steel (Steel).
Basisrohstoffe: coal (Coal); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone).
Zwischenprodukte: cement (Cement); concrete_components (Concrete Components); steel (Steel); structural_components (Structural Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: cement (Cement); steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 2.625, "gypsum": 0.6666666666666666, "iron_ore": 10.5, "limestone": 2.6666666666666665}`.

### `supercomputer` — Supercomputer
Tiefe 3; Basisrohstoffarten 12; Zwischenprodukte 12.
Alle Vorprodukte: ai_compute_components (AI Compute Components); aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); grid_storage_components (Grid Storage Components); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); lithium (Lithium); lithium_ore (Lithium Ore); natural_gas (Natural Gas); network_components (Network Components); purified_graphite (Purified Graphite); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); server_components (Server Components); vanadium_alloy (Vanadium Alloy); vanadium_ore (Vanadium Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); lithium (Lithium); lithium_ore (Lithium Ore); natural_gas (Natural Gas); purified_graphite (Purified Graphite); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); vanadium_alloy (Vanadium Alloy); vanadium_ore (Vanadium Ore).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); iron_ore (Iron Ore); lithium_ore (Lithium Ore); natural_gas (Natural Gas); quartz (Quartz); rare_earth_ore (Rare Earth Ore); vanadium_ore (Vanadium Ore).
Zwischenprodukte: ai_compute_components (AI Compute Components); aluminum (Aluminum); copper (Copper); gold (Gold); grid_storage_components (Grid Storage Components); high_purity_silicon (High-Purity Silicon); lithium (Lithium); network_components (Network Components); purified_graphite (Purified Graphite); rare_earth_metals (Rare Earth Metals); server_components (Server Components); vanadium_alloy (Vanadium Alloy).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "copper_ore": 10.0, "crude_oil": 10.0, "fluorspar": 10.0, "gold_ore": 10.0, "graphite": 1.3333333333333333, "iron_ore": 1.3333333333333333, "lithium_ore": 2.0, "natural_gas": 10.0, "quartz": 40.0, "rare_earth_ore": 5.333333333333333, "vanadium_ore": 1.3333333333333333}`.

### `superconducting_magnet_system` — Superconducting Magnet System
Tiefe 3; Basisrohstoffarten 11; Zwischenprodukte 9.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); molybdenum (Molybdenum); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); niobium (Niobium); niobium_ore (Niobium Ore); power_electronics (Power Electronics); quartz (Quartz); rare_earth_ore (Rare Earth Ore); refractory_alloy_components (Refractory Alloy Components); superconducting_alloy (Superconducting Alloy); titanium_ore (Titanium Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); molybdenum (Molybdenum); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); niobium (Niobium); niobium_ore (Niobium Ore); quartz (Quartz); rare_earth_ore (Rare Earth Ore); superconducting_alloy (Superconducting Alloy); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); niobium_ore (Niobium Ore); quartz (Quartz); rare_earth_ore (Rare Earth Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: aluminum (Aluminum); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); molybdenum (Molybdenum); niobium (Niobium); power_electronics (Power Electronics); refractory_alloy_components (Refractory Alloy Components); superconducting_alloy (Superconducting Alloy).
Gemeinsam verwendete Vorprodukte in dieser Kette: niobium_ore (Niobium Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "copper_ore": 4.0, "crude_oil": 2.0, "fluorspar": 2.0, "gold_ore": 2.0, "molybdenum_ore": 4.0, "natural_gas": 2.0, "niobium_ore": 8.0, "quartz": 8.0, "rare_earth_ore": 3.0, "titanium_ore": 2.0}`.

### `surgical_equipment` — Surgical Equipment
Tiefe 3; Basisrohstoffarten 6; Zwischenprodukte 6.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); nickel_ore (Nickel Ore); precision_components (Precision Components); stainless_components (Stainless Components); stainless_steel (Stainless Steel); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); nickel_ore (Nickel Ore); stainless_steel (Stainless Steel); steel (Steel); tungsten (Tungsten); tungsten_ore (Tungsten Ore).
Basisrohstoffe: bauxite (Bauxite); chromium_ore (Chromium Ore); coal (Coal); iron_ore (Iron Ore); nickel_ore (Nickel Ore); tungsten_ore (Tungsten Ore).
Zwischenprodukte: aluminum (Aluminum); precision_components (Precision Components); stainless_components (Stainless Components); stainless_steel (Stainless Steel); steel (Steel); tungsten (Tungsten).
Gemeinsam verwendete Vorprodukte in dieser Kette: coal (Coal); iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "chromium_ore": 0.6666666666666666, "coal": 2.5, "iron_ore": 10.0, "nickel_ore": 0.6666666666666666, "tungsten_ore": 4.0}`.

### `sustainable_packaging` — Sustainable Packaging
Tiefe 3; Basisrohstoffarten 3; Zwischenprodukte 6.
Alle Vorprodukte: bio_composite (Bio-Composite); cellulose (Cellulose); crude_oil (Crude Oil); industrial_resin (Industrial Resin); natural_gas (Natural Gas); packaging_components (Packaging Components); polymer (Polymer); timber (Timber); wood_pulp (Wood Pulp).
Nur indirekte Inputs: cellulose (Cellulose); crude_oil (Crude Oil); industrial_resin (Industrial Resin); natural_gas (Natural Gas); polymer (Polymer); timber (Timber); wood_pulp (Wood Pulp).
Basisrohstoffe: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Zwischenprodukte: bio_composite (Bio-Composite); cellulose (Cellulose); industrial_resin (Industrial Resin); packaging_components (Packaging Components); polymer (Polymer); wood_pulp (Wood Pulp).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); timber (Timber).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"crude_oil": 2.583333333333333, "natural_gas": 1.5833333333333333, "timber": 2.0}`.

### `switchgear` — Switchgear
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 8.
Alle Vorprodukte: control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); electrical_components (Electrical Components); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); polymer (Polymer); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); tin (Tin); tin_ore (Tin Ore).
Nur indirekte Inputs: copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); polymer (Polymer); quartz (Quartz); silver (Silver); silver_ore (Silver Ore); tin (Tin); tin_ore (Tin Ore).
Basisrohstoffe: copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); quartz (Quartz); silver_ore (Silver Ore); tin_ore (Tin Ore).
Zwischenprodukte: control_electronics (Control Electronics); copper (Copper); electrical_components (Electrical Components); gold (Gold); high_purity_silicon (High-Purity Silicon); polymer (Polymer); silver (Silver); tin (Tin).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); crude_oil (Crude Oil); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"copper_ore": 4.0, "crude_oil": 3.5, "fluorspar": 2.0, "gold_ore": 2.0, "natural_gas": 2.5, "quartz": 8.0, "silver_ore": 2.0, "tin_ore": 1.8}`.

### `synthetic_fuel_plant` — Synthetic Fuel Plant
Tiefe 3; Basisrohstoffarten 10; Zwischenprodukte 11.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); catalyst_components (Catalyst Components); catalyst_metal (Catalyst Metal); chemical_components (Chemical Components); chemical_feedstock (Chemical Feedstock); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); electrolyzer_components (Electrolyzer Components); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); palladium (Palladium); palladium_ore (Palladium Ore); platinum_ore (Platinum Ore); quartz (Quartz); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); catalyst_metal (Catalyst Metal); chemical_feedstock (Chemical Feedstock); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); natural_gas (Natural Gas); palladium (Palladium); palladium_ore (Palladium Ore); platinum_ore (Platinum Ore); quartz (Quartz); sulfur (Sulfur); sulfuric_acid (Sulfuric Acid).
Basisrohstoffe: bauxite (Bauxite); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); natural_gas (Natural Gas); palladium_ore (Palladium Ore); platinum_ore (Platinum Ore); quartz (Quartz); sulfur (Sulfur).
Zwischenprodukte: aluminum (Aluminum); catalyst_components (Catalyst Components); catalyst_metal (Catalyst Metal); chemical_components (Chemical Components); chemical_feedstock (Chemical Feedstock); copper (Copper); electrolyzer_components (Electrolyzer Components); gold (Gold); high_purity_silicon (High-Purity Silicon); palladium (Palladium); sulfuric_acid (Sulfuric Acid).
Gemeinsam verwendete Vorprodukte in dieser Kette: crude_oil (Crude Oil); natural_gas (Natural Gas); palladium_ore (Palladium Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "copper_ore": 4.0, "crude_oil": 3.333333333333333, "fluorspar": 2.0, "gold_ore": 2.0, "natural_gas": 3.833333333333333, "palladium_ore": 3.5, "platinum_ore": 0.5, "quartz": 8.0, "sulfur": 1.0}`.

### `tanker` — Tanker
Tiefe 3; Basisrohstoffarten 8; Zwischenprodukte 8.
Alle Vorprodukte: chromium_ore (Chromium Ore); coal (Coal); copper (Copper); copper_ore (Copper Ore); corrosion_resistant_components (Corrosion Resistant Components); crude_oil (Crude Oil); galvanized_metal (Galvanized Metal); industrial_resin (Industrial Resin); iron_ore (Iron Ore); marine_components (Marine Components); natural_gas (Natural Gas); nickel_ore (Nickel Ore); pump_components (Pump Components); stainless_steel (Stainless Steel); steel (Steel); zinc_ore (Zinc Ore).
Nur indirekte Inputs: chromium_ore (Chromium Ore); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); galvanized_metal (Galvanized Metal); industrial_resin (Industrial Resin); iron_ore (Iron Ore); natural_gas (Natural Gas); nickel_ore (Nickel Ore); stainless_steel (Stainless Steel); steel (Steel); zinc_ore (Zinc Ore).
Basisrohstoffe: chromium_ore (Chromium Ore); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); iron_ore (Iron Ore); natural_gas (Natural Gas); nickel_ore (Nickel Ore); zinc_ore (Zinc Ore).
Zwischenprodukte: copper (Copper); corrosion_resistant_components (Corrosion Resistant Components); galvanized_metal (Galvanized Metal); industrial_resin (Industrial Resin); marine_components (Marine Components); pump_components (Pump Components); stainless_steel (Stainless Steel); steel (Steel).
Gemeinsam verwendete Vorprodukte in dieser Kette: coal (Coal); iron_ore (Iron Ore); steel (Steel).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"chromium_ore": 0.6666666666666666, "coal": 4.75, "copper_ore": 2.0, "crude_oil": 2.0, "iron_ore": 21.666666666666664, "natural_gas": 1.0, "nickel_ore": 0.6666666666666666, "zinc_ore": 2.6666666666666665}`.

### `transformer` — Transformer
Tiefe 3; Basisrohstoffarten 6; Zwischenprodukte 6.
Alle Vorprodukte: coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); electrical_components (Electrical Components); iron_ore (Iron Ore); natural_gas (Natural Gas); polymer (Polymer); steel (Steel); tin (Tin); tin_ore (Tin Ore); transformer_components (Transformer Components).
Nur indirekte Inputs: coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); iron_ore (Iron Ore); natural_gas (Natural Gas); polymer (Polymer); steel (Steel); tin (Tin); tin_ore (Tin Ore).
Basisrohstoffe: coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); iron_ore (Iron Ore); natural_gas (Natural Gas); tin_ore (Tin Ore).
Zwischenprodukte: copper (Copper); electrical_components (Electrical Components); polymer (Polymer); steel (Steel); tin (Tin); transformer_components (Transformer Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 1.5, "copper_ore": 5.0, "crude_oil": 0.75, "iron_ore": 6.0, "natural_gas": 0.25, "tin_ore": 0.9}`.

### `utility_vehicle` — Utility Vehicle
Tiefe 3; Basisrohstoffarten 13; Zwischenprodukte 11.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); control_electronics (Control Electronics); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); sensor_components (Sensor Components); silver (Silver); silver_ore (Silver Ore); steel (Steel); sulfur (Sulfur); vehicle_components (Vehicle Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); high_purity_silicon (High-Purity Silicon); iron_ore (Iron Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); processed_rubber (Processed Rubber); quartz (Quartz); rare_earth_metals (Rare Earth Metals); rare_earth_ore (Rare Earth Ore); silver (Silver); silver_ore (Silver Ore); steel (Steel); sulfur (Sulfur).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); iron_ore (Iron Ore); natural_gas (Natural Gas); natural_rubber (Natural Rubber); quartz (Quartz); rare_earth_ore (Rare Earth Ore); silver_ore (Silver Ore); sulfur (Sulfur).
Zwischenprodukte: aluminum (Aluminum); control_electronics (Control Electronics); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); processed_rubber (Processed Rubber); rare_earth_metals (Rare Earth Metals); sensor_components (Sensor Components); silver (Silver); steel (Steel); vehicle_components (Vehicle Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 3.6, "coal": 1.5, "copper_ore": 6.0, "crude_oil": 6.0, "fluorspar": 6.0, "gold_ore": 6.0, "iron_ore": 6.0, "natural_gas": 6.0, "natural_rubber": 2.0, "quartz": 24.0, "rare_earth_ore": 2.6666666666666665, "silver_ore": 4.0, "sulfur": 1.0}`.

### `wind_turbine` — Wind Turbine
Tiefe 3; Basisrohstoffarten 15; Zwischenprodukte 13.
Alle Vorprodukte: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); cement (Cement); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); industrial_resin (Industrial Resin); iron_ore (Iron Ore); limestone (Limestone); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); power_electronics (Power Electronics); quartz (Quartz); steel (Steel); structural_components (Structural Components); titanium (Titanium); titanium_ore (Titanium Ore); wind_components (Wind Components).
Nur indirekte Inputs: aluminum (Aluminum); bauxite (Bauxite); carbon_fiber (Carbon Fiber); cement (Cement); coal (Coal); copper (Copper); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold (Gold); gold_ore (Gold Ore); graphite (Graphite); gypsum (Gypsum); high_purity_silicon (High-Purity Silicon); industrial_resin (Industrial Resin); iron_ore (Iron Ore); limestone (Limestone); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); quartz (Quartz); steel (Steel); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: bauxite (Bauxite); coal (Coal); copper_ore (Copper Ore); crude_oil (Crude Oil); fluorspar (Fluorspar); gold_ore (Gold Ore); graphite (Graphite); gypsum (Gypsum); iron_ore (Iron Ore); limestone (Limestone); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_ore (Nickel Ore); quartz (Quartz); titanium_ore (Titanium Ore).
Zwischenprodukte: aluminum (Aluminum); carbon_fiber (Carbon Fiber); cement (Cement); copper (Copper); gold (Gold); high_purity_silicon (High-Purity Silicon); industrial_resin (Industrial Resin); nickel_alloy (Nickel Alloy); power_electronics (Power Electronics); steel (Steel); structural_components (Structural Components); titanium (Titanium); wind_components (Wind Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: coal (Coal); crude_oil (Crude Oil); iron_ore (Iron Ore); natural_gas (Natural Gas).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"bauxite": 1.8, "coal": 1.7916666666666665, "copper_ore": 4.0, "crude_oil": 10.0, "fluorspar": 2.0, "gold_ore": 2.0, "graphite": 2.0, "gypsum": 0.16666666666666666, "iron_ore": 8.5, "limestone": 0.6666666666666666, "molybdenum_ore": 1.3333333333333333, "natural_gas": 5.0, "nickel_ore": 4.0, "quartz": 8.0, "titanium_ore": 4.0}`.

### `workboat` — Workboat
Tiefe 3; Basisrohstoffarten 7; Zwischenprodukte 6.
Alle Vorprodukte: coal (Coal); crude_oil (Crude Oil); industrial_resin (Industrial Resin); iron_ore (Iron Ore); marine_components (Marine Components); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); steel (Steel); titanium (Titanium); titanium_ore (Titanium Ore); turbine_components (Turbine Components).
Nur indirekte Inputs: coal (Coal); crude_oil (Crude Oil); industrial_resin (Industrial Resin); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_alloy (Nickel Alloy); nickel_ore (Nickel Ore); steel (Steel); titanium (Titanium); titanium_ore (Titanium Ore).
Basisrohstoffe: coal (Coal); crude_oil (Crude Oil); iron_ore (Iron Ore); molybdenum_ore (Molybdenum Ore); natural_gas (Natural Gas); nickel_ore (Nickel Ore); titanium_ore (Titanium Ore).
Zwischenprodukte: industrial_resin (Industrial Resin); marine_components (Marine Components); nickel_alloy (Nickel Alloy); steel (Steel); titanium (Titanium); turbine_components (Turbine Components).
Gemeinsam verwendete Vorprodukte in dieser Kette: coal (Coal); iron_ore (Iron Ore).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"coal": 3.3333333333333335, "crude_oil": 2.0, "iron_ore": 14.0, "molybdenum_ore": 0.6666666666666666, "natural_gas": 1.0, "nickel_ore": 2.0, "titanium_ore": 2.0}`.

### `workwear` — Workwear
Tiefe 3; Basisrohstoffarten 5; Zwischenprodukte 5.
Alle Vorprodukte: cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); industrial_fabric (Industrial Fabric); natural_gas (Natural Gas); natural_rubber (Natural Rubber); polymer (Polymer); processed_rubber (Processed Rubber); sulfur (Sulfur); technical_textile (Technical Textile).
Nur indirekte Inputs: cotton (Cotton); cotton_fiber (Cotton Fiber); crude_oil (Crude Oil); natural_gas (Natural Gas); natural_rubber (Natural Rubber); polymer (Polymer); processed_rubber (Processed Rubber); sulfur (Sulfur).
Basisrohstoffe: cotton (Cotton); crude_oil (Crude Oil); natural_gas (Natural Gas); natural_rubber (Natural Rubber); sulfur (Sulfur).
Zwischenprodukte: cotton_fiber (Cotton Fiber); industrial_fabric (Industrial Fabric); polymer (Polymer); processed_rubber (Processed Rubber); technical_textile (Technical Textile).
Gemeinsam verwendete Vorprodukte in dieser Kette: cotton_fiber (Cotton Fiber); polymer (Polymer).
Rohstoffmengen je 1 Output (bestehende P10-Auswertung): `{"cotton": 1.5, "crude_oil": 2.25, "natural_gas": 0.75, "natural_rubber": 1.0, "sulfur": 0.5}`.

## 11. Vorhandene Preis- und Wertformeln

- Basispreisbildung: exakt Abschnitt 2 (`fixed_prices.build_fixed_prices`).
- Tatsächlicher Marktpreis nach Research (`modifiers.market_sale_price`): Basispreis * (1 + Summe passender value-Modifikatoren). Globale, passende Domain- und Produktspezialisierungsboni werden addiert; keine automatische Weitergabe über Inputrezepte. Research verändert den Basispreiskatalog nicht.
- `ProductionValueCalculator`: eigene Maschinenminuten je Einheit = 1/(Output/min); gesamter Wert = eigene Minuten + Summe(Inputmenge/Outputmenge * Arbeitswert des Inputs). Fraction wird intern für Raten und Teilrechnungen verwendet. Dieses Maß ist kein Dollarpreis, enthält keine Strom-/Fracht-/Kaufkosten und bewertet MK1-Basisrezepte; es dient unter anderem Company-XP und Contract-Arbeitsbudgets. Der CSV enthält den vorhandenen Wert separat.
- `modifiers.contract_cash_quote`: Summe(Basispreis * Menge * (1 + Produkt-value-Bonus + contract_value-Bonus)). Neue Capacity-Contracts frieren unit_cash ein; Regular/Daily/Weekly verwenden Bargeldaufschläge 0/20/40 %. Die Annahme friert den Gesamtquote ein (`contracts.contract_reward_quote`, `accept_contract`). Neue Mengen beruhen auf Kapazität, Ketten-/Energie-/Frachtengpässen und Zeitbudgets (`contract_capacity`); sie sind keine neue Basispreisformel.
- Contract-XP (`contracts.contract_work_xp_quote`): round(20 * sqrt(max(1, Arbeitswert)) * (1+log1p(Level)/4) * Kategorie, 2), Kategorie Regular/Daily/Weekly = 1/2/4. Ältere Angebots-/Fallbackpfade enthalten budgetbasierte Rewards; diese sind nicht die aktuelle Basispreisbildung und können bei historischen Angeboten relevant bleiben.
- Consortium (`consortium._balanced_rewards`): Geldpool = Summe(je Produkt höchster eingefrorener Basis-/Mitgliedspreis * Menge) * 1.15 Daily bzw. 1.25 Weekly, auf Cent gerundet; Consortium-XP = 400 bzw. 1750 + Produktionsarbeitswert, auf Cent gerundet. Persönliche Auszahlung berücksichtigt den eingefrorenen Beitragsschlüssel und Mitgliedspreise (`personal_reward_quote`); nicht jeder Contributor erhält den ganzen Pool. Damit sind Bargeldrewards ausdrücklich nicht unabhängig von Produktpreisen.
- MK-Upgrades (`mk_upgrades`): pro Maschinenfamilie wird das Maximum des Rezept-Nettoertrags je Sekunde abzüglich Kohlepreisäquivalent der Leistung verwendet, Untergrenze 0.01. Amortisationszeit = 900*(nächster MK/2)^2.3. Upgradepreis = ceil(max(Commonpreis*aktueller MK^1.7, 0.25*Basisnettoertrag*Amortisationszeit)*100)/100. Diese Funktion liest Preise für Investitionsquotes; sie erzeugt keine Basisverkaufspreise.

## 12. Technische Abhängigkeiten eines theoretischen $1-Primärpreises

Keine alternativen Preise berechnet. Betroffen wären zunächst die 49 Primary-Felder `base_market_price` in `resource_definitions.json`. Folgeproduktanker sind ebenfalls gespeichert, die tatsächlich verwendeten Folgeproduktpreise aber beim Import abgeleitet: Rohstoffänderungen wirken über Inputpreise, zusätzlich wirkt Kohle als globales Energieäquivalent. Produktanker bleiben Untergrenze und Transportbasis. Ein späteres Modell müsste diese unterschiedlichen Rollen ausdrücklich entscheiden.

Lesekette: Resource-JSON → `market.LEGACY_BASE_MARKET_PRICES` → `fixed_prices.build_fixed_prices` → `market.BASE_MARKET_PRICES` → `market_price_for` / `economy.sell_price_for` → Research-Verkauf, Frachtquotes, Contracts, Consortium und MK-Upgradekosten. Diese Modulkonstanten werden beim Import gebildet; eine Dateieditierung allein ersetzt keine bereits im laufenden Prozess gehaltenen Werte. Guide/UI lesen daraus Preise, stellen sie aber teilweise mit eigener Cent-Anzeige dar.

Weiter zu beachten: Kapazitätspläne verwenden Preise unter anderem für wertgewichtete Mengenauswahl; Research-Boni, aktuelle Angebotsquotes und Mitgliedersnapshots können davon abhängen. Bereits akzeptierte Contract-Rewards, Mitgliedspreise und Fracht-Snapshots sind historische Quotes. `simulation.py` speichert den Versandpreis an der Sendung und löst damit aus; aktuelle Katalogpreise allein beschreiben deshalb nicht jeden offenen Vorgang. Savefelder wie Kaufpreis, Upgradeinvestition, verbuchte Einnahmen und bestehende Belohnungen sind historische Beträge, keine automatisch neu zu bewertenden Rezeptpreise. Es wurde weder ein Preis geändert noch eine Migration ausprobiert.

## 13. Datenqualität und Auffälligkeiten

Vollständigkeitskontrolle: 353 Ressourcen, je eine kanonische Produktion, 353 eindeutige Produkt-IDs, sämtliche direkten Referenzen auf vorhandene Ressourcen; alle Input-/Outputmengen und Zeiten positiv und endlich, sämtliche effektiven Preise vorhanden, positiv und endlich; Leistungswerte nichtnegativ und endlich; alle Rezepte mit ihrer Maschinenklasse kompatibel. Die vorhandene vollständige Preisbildung und Vorfahrenauswertung konnten alle Produkte ohne Zyklus-/Fehlreferenzfehler auflösen. Aliase von Karten/Produktions-IDs werden durch den bestehenden Index normalisiert und nicht als neue Produkte gezählt.

Auffälligkeiten ohne Reparatur: Die Annahme einheitlicher Leistung pro Stufe ist für Processing und Fabrication widerlegt; die Rezeptüberschreibungen mit konkreten IDs stehen vollständig in Abschnitt 6. Unterschiedliche Rohstoffpreise und unterschiedliche Preisrelationen sind beobachtete Daten, kein automatisch festgestellter Fehler. Die Bezeichnung „feste Preise“ darf die Rezeptableitung beim Import nicht verdecken. Ebenso sind Kataloganker, tatsächlicher Basispreis, Research-Erlös und UI-Centanzeige unterschiedliche Größen.

## 14. Offene Fragen für die spätere gemeinsame mathematische Analyse

- Sollen die unterschiedlichen Rohstoffpreisbasen und deren Level-/Kettenrollen bewusst erhalten bleiben?
- Welche Bedeutung sollen Produktanker, Mindestpreis, Energieäquivalent und Transportaufschlag künftig haben?
- Sollen die dokumentierten Rezeptunterschiede bei Processing/Fabrication Teil des Designs bleiben?
- Soll faire Weiterverarbeitung nach Geldmarge, Maschinenzeit, Energie, Fracht oder mehreren getrennten Größen beurteilt werden?
- Wie sollen bei einer später beschlossenen Änderung historische Quotes, laufende Lieferungen und akzeptierte Contracts behandelt werden?

Keine dieser Fragen wird hier durch eine neue Formel, Preisempfehlung oder alternative Preisliste beantwortet.

### Quellen, Datenformat und Prüfung

Produktive Quellen: `src/production_zero/data/{game_definitions,resource_definitions,resource_progression}.json`; `src/production_zero/data/definitions.py`; `src/production_zero/core/{definitions,release_balance,production_guide,production_values,progression,fixed_prices,market,cards,supply,mk_upgrades,modifiers,research,simulation,freight,contracts,contract_capacity,consortium,economy}.py`. Ergänzend unveränderte vorhandene Extraktion: `artifacts/phase10/resource-price-audit.json` (353 Ketten); vorhandener Vorfahrenhelfer: `scripts/phase8_contract_simulation.py:ancestors`. Nur diese einzelne Hilfsfunktion wurde isoliert auf die aktuellen Herstellerdaten angewendet, keine Simulation ausgeführt.

CSV: UTF-8 mit BOM, Komma als Trennzeichen, standardkonform maskierte Felder, eine Zeile pro Produkt. IDs plus Namen machen Listen lesbar und eindeutig. Exakte Rezeptzahlen und Originalpreispräzision bleiben erhalten; keine Anzeige-Cent-Rundung. `raw_inputs_per_output_unit` ist eine JSON-Zelle der bereits vorhandenen P10-Auswertung, alle übrigen Listen sind durch Semikolon getrennt. Für jeden Verarbeitungsweg verweist die Input-ID auf die vollständige Zeile desselben Produkts.

### Abschließende Verifikation

- CSV erneut eingelesen: exakt 353 Zeilen, 353 eindeutige IDs, vollständige Übereinstimmung mit der Ressourcenregistrierung. Alle 353 Katalogeinträge und alle 353 Herkunftsabschnitte im Bericht vorhanden.
- Jede Maschinen-ID, direkte Inputliste einschließlich jeder Menge, Outputmenge, Zykluszeit, Leistungsangabe und jeder Basispreis gegen die aktuellen geladenen Produktionsdefinitionen geprüft.
- 708 direkte Rezeptkanten; maximale Verarbeitungstiefe 3. Inputarten je Rezept: 49 ohne Inputs, 52 mit einem, 133 mit zwei, 86 mit drei und 33 mit vier unterschiedlichen Inputs.
- Alle 353 Ressourcen besitzen explizite positive Katalogpreisfelder. Originalwerte beispielsweise lumber 1.8125, ai_accelerator 226.1625, ai_server 299.1375 und autonomous_control_system 497.4; Natural Gas 1.9.
- Vorher-/Nachher-SHA256-Aggregate über dieselben Pfadlisten: 892 durch das bestehende P10-Delivery-Manifest erfasste Dateien einschließlich Quellen/Spieldaten/Tests unverändert; 4083 geschützte Builddateien unverändert; fünf persönliche Save-Dateien unverändert. Spielstände ausschließlich als Bytes gehasht, nicht mit dem Spiel geladen.

| Prüfgruppe | Dateien | SHA256-Aggregat vorher = nachher |
|---|---:|---|
| P10-Manifestdateien | 892 | c1151a7c70a6d375f53401dbaef6d0478fa569531345a7ad929868233f78dfba |
| Builds | 4083 | 94e38bf43ee71dcd7a4415ead3e9a7e592f16ffd150fec28353c600bbf28aad4 |
| Persönliche Saves | 5 | ab31eafb6f021ab115560c9f3f7b7800ec8d9ac8d4ca2b05ede27fd840e5d581 |

Prüfmethode des Aggregats: SHA256 über alphabetisch sortierte Pfadtexte (UTF-8), jeweils gefolgt vom binären SHA256 des Dateiinhalts. Referenzpfadlisten: vorhandenes `artifacts/phase10/delivery-manifest.json` und `artifacts/phase10/backup-20261022T224910Z/{manifest,personal-saves-manifest}.json`. Die aktuellen Vorher-Werte wurden für diesen Audit frisch gelesen und mit den Nachher-Werten verglichen, nicht mit alten Savezuständen gleichgesetzt.

Ausschließlich die beiden angeforderten Dokumente neu erstellt. Keine produktive Änderung, kein neues Auditprogramm im Projekt, kein Testlauf, keine Simulation, keine alternative Preisberechnung, keine Save-Migration und kein Windows-Build. P11-A endet hier.
