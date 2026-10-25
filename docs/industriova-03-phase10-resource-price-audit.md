# INDUSTRIOVA 0.3 – P10: Rohstoffpreis- und Weiterverarbeitungs-Audit

Stand 23.10.2026. Reale feste Kataloge: 49 Primärrohstoffe, 353 Produkte, alle unmittelbaren Rezeptinputs und rekursiven Rohstoffbedarfe. Keine Preis-, Rezept-, MK-, Rarity-, Research- oder Freight-Balancingänderung.

## 1. Bewertung

Copper Ore liefert bei gleicher MK1/Common-Maschine, 120 U/min und 6 MW **40 % mehr nominalen Direktverkauf** als Iron Ore: $168.00 statt $120.00/min. Bei demselben einzelnen Startertruck werden im echten 10-Minutenlauf $46.48 statt $33.20/min ausgezahlt. Crude Oil erreicht bei denselben Rohmaschinenkosten von $340.00 nominal $264.00/min und mit derselben knappen Freight $73.04/min. Dieser Vorteil besteht bei unveränderten Routen, MK und Research fort; feste Preise enthalten keinen automatischen zeitlichen Ausgleich. Das ist ein nachgewiesener Anreiz zu profitableren Direktverkaufsbranchen, kein zufälliger Anzeigerundungsfehler.

Für das isolierte Ziel maximaler passiver Cash-Erzeugung aus gleich vielen Rohmaschinen und gleicher Freight ist daher eine höher bewertete, bereits freigeschaltete Rohstoffroute wirtschaftlich überlegen. Im späteren Katalog liegen z.B. Platinum Ore ($5.80/U, Level 20) und Palladium Ore ($5.40/U, Level 20) darüber; Uranium Ore ($3.20/U) benötigt Level 25. Diese sind **keine** sofort verfügbaren Early-Game-Alternativen. Die Tabelle führt die tatsächlichen Voraussetzungen getrennt auf.

Die stärkere Behauptung, es gebe über alle vollständigen Firmen hinweg keinen vernünftigen Grund für andere Branchen, ist damit nicht belegt: Iron Ore wird in 108, Copper Ore in 113, Crude Oil in 175 und Wheat in 9 verschiedenen Folgeprodukten rekursiv benötigt. Processing-/Fabrication-/Assembly-Ketten, Research-Freischaltungen sowie ausgewählte persönliche und Consortium Contracts benötigen konkrete Warenkombinationen. Es gibt keine wirtschaftliche Regel, die diese Rohstoffe einfach gegenseitig ersetzt. Eine spätere Kette neutralisiert einen früheren Preisvorteil nicht automatisch; ihr Bedarf schafft einen eigenständigen Nutzen. Die unten stehenden Mehrwerte und Maschinenzeitkennzahlen machen diesen Unterschied quantitativ sichtbar.

## 2. Rechenbasis und Grenzen

Nominelle Rate = `output_amount_for(definition) × 60 / cycle_seconds_for(definition) × card.output_multiplier`. Maschinenleistung verwendet unverändert `card.power_multiplier`. Common hat 0 % Bonus, Legendary in den Vergleichsfällen den real zulässigen Maximalroll 20 %. MK1/10/99 entsprechen unverändert 1/3.25/25.5; Rarity skaliert Produktion und Energie unterschiedlich. Freight verwendet die reale `freight_stats`-Kapazität und Reisezeit, einschließlich ihres Rarity-Einflusses.

600 one-second real engine ticks; zero initial stock, full recipe/level unlock for capability comparison; Common replacement-capital reference (machines/solar/truck/MK); non-Common acquisition premium excluded, no recurring solar money cost; no Research. One matching-MK vehicle. Finite start/end shipment latency included. Not an organic early-game playthrough; initial unlock status is listed separately. No prices or recipes changed.

Die 76 Engine-Strategien starten bei leerem Lager, mit je einem Rohstoffproduzenten und einem Fahrzeug passenden MK/Rarity. Solar wird passend zur tatsächlichen Leistung in ganzen MK1-Generatoren ergänzt. Genannte Ersatzinvestitionen enthalten Rohmaschine, Solar, Truck und die echten MK-Upgradekosten auf Common-Anschaffungsbasis. Die Legendary-Leistungsfixture ist ausdrücklich ein Qualitätsvergleich bereits vorhandener Karten; ein Legendary-Erwerb ist im Common Supply nicht verfügbar, seine Erwerbsprämie wird nicht erfunden. Für Legendary ist diese Kapitalspalte deshalb nur eine Common-Referenz/Untergrenze und kein tatsächlicher Einkaufspreis. Zusätzliche Gebäudelinien/Slots für große spätere Szenarien sind in diesem reinen Maschinenvergleich nicht eingepreist; es ist kein vollständiger ROI- oder organischer Spiellauf. Grundvoraussetzungen für alle Rezepte/Level sind nur in dieser isolierten Kapazitätsfixture freigegeben. Tatsächliche Genesis-Freischaltungen werden separat genannt. Produktions-/Ankunfts- und Tick-Wartezeit ist im 600-Sekunden-Isterlös enthalten; laufende Restsendungen sind am Messende noch kein Cash. Lagerreste sind im JSON erhalten.

Solar verbraucht keinen Brennstoff und erzeugt keinen laufenden Cash-Abzug. Deshalb wäre eine erfundene Stromgebühr falsch. Die Tabelle nennt MW und erforderliches Solarkapital; bei Brennstoffkraftwerken wären zusätzlich reale Fuel-Opportunitätskosten erforderlich. Im JSON stehen alle Eingänge und Annahmen. Der ausschließlich im Offline-Harness verwendete Arbeitswertcache wurde vor Verwendung für alle 353 Werte exakt gegen den Originalrechner verglichen. Engine, Waren, Zeit, Freischaltungen, Freight und Cash werden nicht übersprungen. Performanceprozesse verwenden diesen Harnesscache nicht.

## 3. Alle Primärrohstoffe

| Resource | Produktion U/min | Basispreis/U | Cash/min direkt, nominal | Maschine | Energie | Freight | Weiterverarbeitung (Auswahl) | Vergleich |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Iron Ore | 120 | $1.00 | $120.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Iron, Steel, Stainless Steel, Nickel Alloy | Level 1; Genesis-unlocked; 108 Folgeprodukte |
| Copper Ore | 120 | $1.40 | $168.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Copper | Level 1; Genesis-unlocked; 113 Folgeprodukte |
| Bauxite | 120 | $1.10 | $132.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Aluminum | Level 1; Genesis-unlocked; 80 Folgeprodukte |
| Nickel Ore | 120 | $1.80 | $216.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Stainless Steel, Nickel, Nickel Alloy | Level 11; später; 32 Folgeprodukte |
| Zinc Ore | 120 | $1.25 | $150.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Zinc, Galvanized Metal | Level 9; später; 6 Folgeprodukte |
| Lead Ore | 120 | $1.15 | $138.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Lead, Shielding Material, Nuclear Material | Level 9; später; 9 Folgeprodukte |
| Tin Ore | 120 | $1.45 | $174.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Tin | Level 9; später; 7 Folgeprodukte |
| Manganese Ore | 120 | $1.35 | $162.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Manganese | Level 9; später; 11 Folgeprodukte |
| Chromium Ore | 120 | $1.65 | $198.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Stainless Steel, Chromium | Level 11; später; 14 Folgeprodukte |
| Titanium Ore | 120 | $2.40 | $288.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Titanium, Superconducting Alloy | Level 22; später; 33 Folgeprodukte |
| Tungsten Ore | 120 | $2.80 | $336.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Tungsten | Level 22; später; 22 Folgeprodukte |
| Cobalt Ore | 120 | $2.60 | $312.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Cobalt | Level 15; später; 8 Folgeprodukte |
| Molybdenum Ore | 120 | $2.20 | $264.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Molybdenum, Nickel Alloy | Level 22; später; 21 Folgeprodukte |
| Vanadium Ore | 120 | $2.10 | $252.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Vanadium, Vanadium Alloy | Level 22; später; 7 Folgeprodukte |
| Silver Ore | 120 | $3.60 | $432.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Silver | Level 18; später; 44 Folgeprodukte |
| Gold Ore | 120 | $5.00 | $600.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Gold | Level 18; später; 93 Folgeprodukte |
| Platinum Ore | 120 | $5.80 | $696.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Platinum, Catalyst Metal | Level 20; später; 8 Folgeprodukte |
| Palladium Ore | 120 | $5.40 | $648.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Palladium, Catalyst Metal | Level 20; später; 4 Folgeprodukte |
| Lithium Ore | 120 | $2.30 | $276.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Lithium | Level 15; später; 11 Folgeprodukte |
| Uranium Ore | 120 | $3.20 | $384.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Nuclear Material | Level 25; später; 6 Folgeprodukte |
| Rare Earth Ore | 120 | $2.70 | $324.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Rare Earth Metals, Superconducting Alloy | Level 15; später; 56 Folgeprodukte |
| Niobium Ore | 120 | $2.50 | $300.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Niobium, Superconducting Alloy | Level 22; später; 6 Folgeprodukte |
| Coal | 120 | $1.20 | $144.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Steel, Stainless Steel, Nickel Alloy, Silicon | Level 1; Genesis-unlocked; 98 Folgeprodukte |
| Quartz | 120 | $1.10 | $132.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Silicon, High-Purity Silicon | Level 1; Genesis-unlocked; 99 Folgeprodukte |
| Silica Sand | 120 | $0.90 | $108.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Glass | Level 3; später; 20 Folgeprodukte |
| Limestone | 120 | $0.80 | $96.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Glass, Cement | Level 1; Genesis-unlocked; 40 Folgeprodukte |
| Gypsum | 120 | $0.85 | $102.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Cement, Processed Gypsum | Level 3; später; 29 Folgeprodukte |
| Clay | 120 | $0.70 | $84.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Ceramics | Level 3; später; 8 Folgeprodukte |
| Kaolin | 120 | $1.00 | $120.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Ceramics | Level 3; später; 8 Folgeprodukte |
| Phosphate Rock | 120 | $1.25 | $150.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Phosphoric Acid | Level 7; später; 5 Folgeprodukte |
| Potash | 120 | $1.35 | $162.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Potassium Compound | Level 7; später; 3 Folgeprodukte |
| Salt | 120 | $0.75 | $90.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Chlorine | Level 7; später; 6 Folgeprodukte |
| Sulfur | 120 | $1.15 | $138.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Synthetic Rubber, Sulfuric Acid, Phosphoric Acid, Processed Rubber | Level 7; später; 37 Folgeprodukte |
| Graphite | 120 | $1.75 | $210.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Purified Graphite, Carbon Fiber | Level 13; später; 34 Folgeprodukte |
| Fluorspar | 120 | $1.50 | $180.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | High-Purity Silicon | Level 13; später; 97 Folgeprodukte |
| Magnesite | 120 | $1.30 | $156.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Ceramics | Level 13; später; 8 Folgeprodukte |
| Borate Ore | 120 | $1.45 | $174.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Glass, Shielding Material | Level 13; später; 26 Folgeprodukte |
| Crude Oil | 120 | $2.20 | $264.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | High-Purity Silicon, Carbon Fiber, Wood Pulp, Cellulose | Level 1; Genesis-unlocked; 175 Folgeprodukte |
| Natural Gas | 120 | $1.90 | $228.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | High-Purity Silicon, Carbon Fiber, Wood Pulp, Cellulose | Level 5; später; 183 Folgeprodukte |
| Timber | 120 | $1.10 | $132.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Lumber, Wood Pulp, Cellulose, Treated Lumber | Level 1; Genesis-unlocked; 30 Folgeprodukte |
| Wheat | 120 | $0.95 | $114.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Flour, Organic Feedstock | Level 1; Genesis-unlocked; 9 Folgeprodukte |
| Corn | 120 | $0.90 | $108.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Corn Meal, Starch, Fermentation Feedstock | Level 2; später; 13 Folgeprodukte |
| Soybeans | 120 | $1.05 | $126.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Soy Oil, Soy Protein, Vegetable Oil | Level 2; später; 14 Folgeprodukte |
| Sugarcane | 120 | $0.85 | $102.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Raw Sugar, Refined Sugar, Fruit Concentrate, Fermentation Feedstock | Level 4; später; 19 Folgeprodukte |
| Cotton | 120 | $1.20 | $144.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Cotton Fiber | Level 4; später; 10 Folgeprodukte |
| Rapeseed | 120 | $1.00 | $120.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Vegetable Oil, Bio-Lubricant | Level 4; später; 13 Folgeprodukte |
| Potatoes | 120 | $0.80 | $96.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Starch, Organic Feedstock | Level 2; später; 6 Folgeprodukte |
| Fruit | 120 | $1.10 | $132.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Fruit Concentrate, Organic Feedstock | Level 4; später; 11 Folgeprodukte |
| Natural Rubber | 120 | $1.70 | $204.00 | $340.00 | 6 MW; Solar: $0/min | 120 U/min | Processed Rubber | Level 5; später; 22 Folgeprodukte |

## 4. Reale Engine-Strategien

| Resource | MK / Rarity | Erlös in 10 min | Ist Cash/min | Nominell Produktion / Freight U/min | Solar | Ersatzkapital |
| --- | --- | --- | --- | --- | --- | --- |
| iron_ore | 1 / common | $332.00 | $33.20 | 120 / 40 | 1 | $725.00 |
| iron_ore | 10 / common | $1,079.00 | $107.90 | 390 / 130 | 1 | $406,279.62 |
| iron_ore | 99 / common | $8,466.00 | $846.60 | 3060 / 1020 | 8 | $661,142,727.57 |
| iron_ore | 1 / legendary | $398.40 | $39.84 | 144 / 43.6364 | 1 | $725.00 |
| copper_ore | 1 / common | $464.80 | $46.48 | 120 / 40 | 1 | $725.00 |
| copper_ore | 10 / common | $1,510.60 | $151.06 | 390 / 130 | 1 | $406,279.62 |
| copper_ore | 99 / common | $11,852.40 | $1,185.24 | 3060 / 1020 | 8 | $661,142,727.57 |
| copper_ore | 1 / legendary | $557.76 | $55.78 | 144 / 43.6364 | 1 | $725.00 |
| bauxite | 1 / common | $365.20 | $36.52 | 120 / 40 | 1 | $725.00 |
| bauxite | 10 / common | $1,186.90 | $118.69 | 390 / 130 | 1 | $406,279.62 |
| bauxite | 99 / common | $9,312.60 | $931.26 | 3060 / 1020 | 8 | $661,142,727.57 |
| bauxite | 1 / legendary | $438.24 | $43.82 | 144 / 43.6364 | 1 | $725.00 |
| nickel_ore | 1 / common | $597.60 | $59.76 | 120 / 40 | 1 | $725.00 |
| zinc_ore | 1 / common | $415.00 | $41.50 | 120 / 40 | 1 | $725.00 |
| lead_ore | 1 / common | $381.80 | $38.18 | 120 / 40 | 1 | $725.00 |
| tin_ore | 1 / common | $481.40 | $48.14 | 120 / 40 | 1 | $725.00 |
| manganese_ore | 1 / common | $448.20 | $44.82 | 120 / 40 | 1 | $725.00 |
| chromium_ore | 1 / common | $547.80 | $54.78 | 120 / 40 | 1 | $725.00 |
| titanium_ore | 1 / common | $796.80 | $79.68 | 120 / 40 | 1 | $725.00 |
| tungsten_ore | 1 / common | $929.60 | $92.96 | 120 / 40 | 1 | $725.00 |
| cobalt_ore | 1 / common | $863.20 | $86.32 | 120 / 40 | 1 | $725.00 |
| molybdenum_ore | 1 / common | $730.40 | $73.04 | 120 / 40 | 1 | $725.00 |
| vanadium_ore | 1 / common | $697.20 | $69.72 | 120 / 40 | 1 | $725.00 |
| silver_ore | 1 / common | $1,195.20 | $119.52 | 120 / 40 | 1 | $725.00 |
| gold_ore | 1 / common | $1,660.00 | $166.00 | 120 / 40 | 1 | $725.00 |
| platinum_ore | 1 / common | $1,925.60 | $192.56 | 120 / 40 | 1 | $725.00 |
| palladium_ore | 1 / common | $1,792.80 | $179.28 | 120 / 40 | 1 | $725.00 |
| lithium_ore | 1 / common | $763.60 | $76.36 | 120 / 40 | 1 | $725.00 |
| uranium_ore | 1 / common | $1,062.40 | $106.24 | 120 / 40 | 1 | $725.00 |
| rare_earth_ore | 1 / common | $896.40 | $89.64 | 120 / 40 | 1 | $725.00 |
| niobium_ore | 1 / common | $830.00 | $83.00 | 120 / 40 | 1 | $725.00 |
| coal | 1 / common | $398.40 | $39.84 | 120 / 40 | 1 | $725.00 |
| coal | 10 / common | $1,294.80 | $129.48 | 390 / 130 | 1 | $406,279.62 |
| coal | 99 / common | $10,159.20 | $1,015.92 | 3060 / 1020 | 8 | $661,142,727.57 |
| coal | 1 / legendary | $478.08 | $47.81 | 144 / 43.6364 | 1 | $725.00 |
| quartz | 1 / common | $365.20 | $36.52 | 120 / 40 | 1 | $725.00 |
| quartz | 10 / common | $1,186.90 | $118.69 | 390 / 130 | 1 | $406,279.62 |
| quartz | 99 / common | $9,312.60 | $931.26 | 3060 / 1020 | 8 | $661,142,727.57 |
| quartz | 1 / legendary | $438.24 | $43.82 | 144 / 43.6364 | 1 | $725.00 |
| silica_sand | 1 / common | $298.80 | $29.88 | 120 / 40 | 1 | $725.00 |
| limestone | 1 / common | $265.60 | $26.56 | 120 / 40 | 1 | $725.00 |
| limestone | 10 / common | $863.20 | $86.32 | 390 / 130 | 1 | $406,279.62 |
| limestone | 99 / common | $6,772.80 | $677.28 | 3060 / 1020 | 8 | $661,142,727.57 |
| limestone | 1 / legendary | $318.72 | $31.87 | 144 / 43.6364 | 1 | $725.00 |
| gypsum | 1 / common | $282.20 | $28.22 | 120 / 40 | 1 | $725.00 |
| clay | 1 / common | $232.40 | $23.24 | 120 / 40 | 1 | $725.00 |
| kaolin | 1 / common | $332.00 | $33.20 | 120 / 40 | 1 | $725.00 |
| phosphate_rock | 1 / common | $415.00 | $41.50 | 120 / 40 | 1 | $725.00 |
| potash | 1 / common | $448.20 | $44.82 | 120 / 40 | 1 | $725.00 |
| salt | 1 / common | $249.00 | $24.90 | 120 / 40 | 1 | $725.00 |
| sulfur | 1 / common | $381.80 | $38.18 | 120 / 40 | 1 | $725.00 |
| graphite | 1 / common | $581.00 | $58.10 | 120 / 40 | 1 | $725.00 |
| fluorspar | 1 / common | $498.00 | $49.80 | 120 / 40 | 1 | $725.00 |
| magnesite | 1 / common | $431.60 | $43.16 | 120 / 40 | 1 | $725.00 |
| borate_ore | 1 / common | $481.40 | $48.14 | 120 / 40 | 1 | $725.00 |
| crude_oil | 1 / common | $730.40 | $73.04 | 120 / 40 | 1 | $725.00 |
| crude_oil | 10 / common | $2,373.80 | $237.38 | 390 / 130 | 1 | $173,631.41 |
| crude_oil | 99 / common | $18,625.20 | $1,862.52 | 3060 / 1020 | 8 | $270,810,855.61 |
| crude_oil | 1 / legendary | $876.48 | $87.65 | 144 / 43.6364 | 1 | $725.00 |
| natural_gas | 1 / common | $630.80 | $63.08 | 120 / 40 | 1 | $725.00 |
| timber | 1 / common | $365.20 | $36.52 | 120 / 40 | 1 | $725.00 |
| timber | 10 / common | $1,186.90 | $118.69 | 390 / 130 | 1 | $141,319.17 |
| timber | 99 / common | $9,312.60 | $931.26 | 3060 / 1020 | 8 | $216,598,095.69 |
| timber | 1 / legendary | $438.24 | $43.82 | 144 / 43.6364 | 1 | $725.00 |
| wheat | 1 / common | $315.40 | $31.54 | 120 / 40 | 1 | $725.00 |
| wheat | 10 / common | $1,025.05 | $102.50 | 390 / 130 | 1 | $141,319.17 |
| wheat | 99 / common | $8,042.70 | $804.27 | 3060 / 1020 | 8 | $216,598,095.69 |
| wheat | 1 / legendary | $378.48 | $37.85 | 144 / 43.6364 | 1 | $725.00 |
| corn | 1 / common | $298.80 | $29.88 | 120 / 40 | 1 | $725.00 |
| soybeans | 1 / common | $348.60 | $34.86 | 120 / 40 | 1 | $725.00 |
| sugarcane | 1 / common | $282.20 | $28.22 | 120 / 40 | 1 | $725.00 |
| cotton | 1 / common | $398.40 | $39.84 | 120 / 40 | 1 | $725.00 |
| rapeseed | 1 / common | $332.00 | $33.20 | 120 / 40 | 1 | $725.00 |
| potatoes | 1 / common | $265.60 | $26.56 | 120 / 40 | 1 | $725.00 |
| fruit | 1 / common | $365.20 | $36.52 | 120 / 40 | 1 | $725.00 |
| natural_rubber | 1 / common | $564.40 | $56.44 | 120 / 40 | 1 | $725.00 |

## 5. Direkte Weiterverarbeitung und Input-Opportunität

Mehrwert = `Ausgabemenge × fester Ausgabepreis − Summe(Inputmenge × fester Inputpreis)`, vor zusätzlichem Energie-/Maschinen-/Transportkapital und ohne Vertragsboni. Ein positiver Mehrwert pro Zyklus ist keine Zusage besserer Cash-Rate pro eingesetztem Kapital oder pro MW. Sämtliche unmittelbaren Folgerezepte, nicht nur diese Auswahl, stehen im JSON.

| Primärrohstoff | Folgeprodukt | Inputs je Zyklus | Output U | Basispreis/U | Mehrwert/Zyklus gegenüber Input-Sell |
| --- | --- | --- | --- | --- | --- |
| Iron Ore | Iron | 12 iron_ore | 6 | $3.75 | $10.50 |
| Iron Ore | Steel | 12 iron_ore, 3 coal | 4 | $10.00 | $24.40 |
| Iron Ore | Stainless Steel | 12 iron_ore, 3 coal, 2 chromium_ore, 2 nickel_ore | 3 | $11.39 | $11.66 |
| Iron Ore | Nickel Alloy | 6 nickel_ore, 6 iron_ore, 1 coal, 2 molybdenum_ore | 3 | $11.64 | $12.51 |
| Copper Ore | Copper | 12 copper_ore | 6 | $4.38 | $9.45 |
| Bauxite | Aluminum | 9 bauxite | 5 | $3.19 | $6.04 |
| Coal | Steel | 12 iron_ore, 3 coal | 4 | $10.00 | $24.40 |
| Coal | Stainless Steel | 12 iron_ore, 3 coal, 2 chromium_ore, 2 nickel_ore | 3 | $11.39 | $11.66 |
| Coal | Nickel Alloy | 6 nickel_ore, 6 iron_ore, 1 coal, 2 molybdenum_ore | 3 | $11.64 | $12.51 |
| Coal | Silicon | 4 quartz, 1 coal | 2 | $4.08 | $2.55 |
| Quartz | Silicon | 4 quartz, 1 coal | 2 | $4.08 | $2.55 |
| Quartz | High-Purity Silicon | 4 quartz, 1 fluorspar, 1 crude_oil, 1 natural_gas | 1 | $13.14 | $3.14 |
| Limestone | Glass | 4 silica_sand, 1 limestone, 1 borate_ore | 3 | $2.90 | $2.85 |
| Limestone | Cement | 4 limestone, 1 gypsum | 3 | $2.12 | $2.33 |
| Crude Oil | High-Purity Silicon | 4 quartz, 1 fluorspar, 1 crude_oil, 1 natural_gas | 1 | $13.14 | $3.14 |
| Crude Oil | Carbon Fiber | 3 crude_oil, 1 natural_gas, 1 graphite | 1 | $16.10 | $5.85 |
| Crude Oil | Wood Pulp | 3 timber, 1 crude_oil, 1 natural_gas | 3 | $3.04 | $1.73 |
| Crude Oil | Cellulose | 2 timber, 1 crude_oil, 1 natural_gas | 2 | $3.91 | $1.52 |
| Timber | Lumber | 3 timber | 3 | $1.81 | $2.14 |
| Timber | Wood Pulp | 3 timber, 1 crude_oil, 1 natural_gas | 3 | $3.04 | $1.73 |
| Timber | Cellulose | 2 timber, 1 crude_oil, 1 natural_gas | 2 | $3.91 | $1.52 |
| Timber | Treated Lumber | 3 timber, 2 crude_oil, 1 natural_gas | 3 | $3.92 | $2.15 |
| Wheat | Flour | 2 wheat | 2 | $1.62 | $1.35 |
| Wheat | Organic Feedstock | 1 wheat, 1 fruit, 1 potatoes | 2 | $2.21 | $1.57 |

## 6. Vollständiger Kettenvergleich

Für alle 353 Produkte sind rekursive Rohstoffmengen pro Einheit, Tiefe, direkte Inputvoraussetzungen, Grundpreis und der vorhandene `ProductionValueCalculator.value_per_unit` erfasst. Das Zeitmaß summiert die Produktionsarbeit der gesamten Kette; die Preis/Zeit-Kennzahl ignoriert parallele Anlagenauslegung, ganzzahlige Maschinen, Strom/Fuel, Storage und Freight. Sie darf deshalb nicht als realer Firmenprofit ausgegeben werden. Sie beantwortet die engere Frage, ob hohe Endproduktpreise allein bereits bessere Arbeitsproduktivität beweisen.

| Tiefe | Bestes Produkt nach reinem Maschinenzeitmaß | Cash pro gesamter Maschinenminute |
| --- | --- | --- |
| 0 | Platinum Ore | $696.00 |
| 1 | Platinum | $309.94 |
| 2 | Catalyst Components | $179.84 |
| 3 | Diagnostic System | $157.20 |

Early Game: die neun ursprünglichen Startprodukte sind freigeschaltet; der Direktverkauf bevorzugt höhere Grundpreise. Mid Game: neue Rohstoffe und Mischketten verlangen tatsächliche Produktionshistorie und Company-Level; relative Preisunterschiede bleiben. Late Game: hohe Endpreise und Vertragsbedarf schaffen weitere Ziele, aber die obige reine Arbeitskennzahl zeigt keine automatische vollständige Kompensation des frühen Direktverkaufsvorteils. Eine globale Optimierung jeder zulässigen Fabrik/Flotte wurde nicht behauptet oder simuliert. 353 rekursive Kettenkennzahlen plus 76 echte Rohstoffläufe sind der tatsächlich geprüfte Umfang.

## 7. Drei freie Startstandorte

P9→P10 ändert ausschließlich Genesis um Drilling Field 1 und Agricultural Estate 1. Das Startkapital bleibt $1,250.00, alle acht Starterkarten behalten Definition/MK/Rarity/Investition und bleiben unplatziert; es gibt weder neue Maschinen noch zusätzliche Energie, Produktion, Waren, XP oder Research. Leere Sites erzeugen nichts. Der Spieler spart gegenüber dem früheren Erwerb die beiden ersten $500.00-Sites, erhält aber weiterhin keine Drilling-/Agriculture-Maschine. Erst deren Kauf und ausreichend Energie/Freight erschließen die zusätzliche Produktion. Jeder weitere Standort desselben Typs kostet nach unveränderter P7-Quote $4,000.00. Altspielstände bleiben beim Laden unverändert.

Der vorhandene finite Early-Game-Regressionslauf verwendet nun diese realen freien Erststandorte, kauft Maschinen/Solar weiter regulär und bestätigt nichtnegative Bestände/Cash, positive tatsächliche Verkäufe und Erreichbarkeit beider Branchen binnen der vorhandenen 360-Sekunden-Grenze. Dieser technische Kapital-/Materiallauf gibt wie bereits P7 bestimmte Rezeptfreigaben ausdrücklich vor; er ersetzt keinen menschlichen Spielfluss mit organischem Research.

## 8. Getrennte Empfehlungen

Keine Änderung in P10. Für eine spätere ausdrücklich beauftragte Balancephase zunächst vergleichbare begrenzte Budgets, real freigeschaltete Firmen, zwei Startertrucks, zusätzliche Slots, Fuel und neue P8/P9-Vertragsquoten gegeneinander spielen. Maßgeblich sollten ausgezahlter Cash pro Zeit, gebundenes Gesamtkapital und MW sein. Besonders Crude Oil gegenüber Iron/Copper sowie späte Edelmetall-Direktverkäufe prüfen. Falls ungewollt, zuerst eine kleine Änderung an Erwerbs-/Ausbaukosten oder den nachgewiesenen Ausreißern untersuchen; keine pauschale Gleichsetzung aller 49 Preise. Keine automatische neue Marktwirtschaft, keine Preis-/Rezeptkorrektur als Nebenwirkung dieses Audits.

Vollständige Rohdaten: `artifacts/phase10/resource-price-audit.json`; Reproduktion: `.venv/Scripts/python.exe scripts/phase10_resource_audit.py`.
