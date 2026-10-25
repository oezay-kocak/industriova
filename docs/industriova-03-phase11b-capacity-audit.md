# INDUSTRIOVA 0.3 – P11-B: Systemkapazitäten und wirtschaftliche Grenzen

Stand: 23.10.2026. Reiner Audit des P10-Quellstands mit vollständigem P11-A-Katalog. Keine persönlichen Spielzustände geladen, keine Simulation, keine produktive Änderung. Dollar und Spielzeit als Einheiten.

## 1. Ergebnis und Geltungsbereich

Factory regulär: **10 Hallen × 5 Linien × 10 Slots = 500 Verarbeitungskarten insgesamt**. Resources/Energy: begrenzte Gebäudegrößen, keine feste Gebäudeanzahl. Freight: kein Gebäude- oder Liniencap im aktuellen Kaufpfad, acht Slots/Linie. Storage: kein Upgradecap. MK99: höchste Kartenstufe, Faktor 25.5. Primary kann weiter über Standorte skalieren; verarbeitete Produkte teilen endliche Factoryplätze.

Die Grenzen gelten für reguläre P10-Neukäufe. Historische Geometrien sind gesondert: FactoryHall hat einen Default von sechs Linien, Neustart und Kaufpfade ausdrücklich fünf. Dies erlaubt keine sechste neu kaufbare Linie. Administrative BuildHall-/Legacy-Pfade sind keine normalen Käufe. Es wurde kein persönlicher Save geöffnet.

## 2. Globale Kapazitäts- und Kaufgrenzen

| Familie | Gebäudeanzahl | Linien/Gebäude | Slots/Linie | Startplätze | Karten/Gebäude voll | Installation |
|---|---|---:|---:|---:|---:|---|
| Mining Complex | kein Anzahlcap | 3 | 10 | 1 | 30 | nur Extractor |
| Drilling Field | kein Anzahlcap | 3 | 10 | 1 | 30 | nur Drilling Rig |
| Agricultural Estate | kein Anzahlcap | 3 | 10 | 1 | 30 | nur Harvester |
| Factory Hall | maximal 10 regulär | 5 | 10 | 3 | 50 | Processor/Fabricator/Assembler mischbar |
| Energy Plant | kein Anzahlcap | 3 | 5 | 1 | 15 | alle Energy-Karten mischbar |
| Garage | kein Anzahlcap | kein Liniencap | 8 | 3 | weiter erweiterbar | nur Trucks |
| Rail Depot | kein Anzahlcap | kein Liniencap | 8 | 2 | weiter erweiterbar | nur Trains |
| Air Terminal | kein Anzahlcap | kein Liniencap | 8 | 2 | weiter erweiterbar | nur Aircraft |
| Seaport | kein Anzahlcap | kein Liniencap | 8 | 2 | weiter erweiterbar | nur Ships |

Eine Karte braucht einen freigeschalteten kompatiblen freien Slot, Doppelinstallation ist verboten. Busy-Freight kann nicht frei verschoben/verkauft werden. Karten, Linien, Gebäude und Routen sind unabhängig pausierbar. Kaufbefehle prüfen Geld, Struktur und Quotes; kein allgemeines Company-Level-Gate für Gebäude oder Common-Karten. Rezepte/Brennstoff bleiben separat durch Progression gesperrt. Common-Supply erlaubt 10000 Karten pro einzelner Kaufoperation, kein globales Besitzlimit. Uncommon Daily Machine/Freight haben getrennte tägliche Kaufrechte; Common bleibt nachkaufbar.

Kein Anzahlcap bezeichnet das Spielmodell, nicht unendlichen realen Speicher: Cash/Quotes müssen endlich sein, riesige Potenzen können numerische Grenzen erreichen. Dies ist keine designte feste Gebäudezahl.

## 3. Kostenkurven für Resources, Factory und Energy

infrastructure_prices.py: s=Startslots, c=Slots/Linie, B=Slotbasis (Resources 90, Factory 40, Energy 100). Slot k kostet B*(k−s). Linie l>=2 kostet A*(l−1)^2, A=ceil((B*(c−s)*s+1)/100)*100, enthält s Plätze.

Gebäude mit n vorhandenen: n=0 Resources 500, Factory/Energy 1000. Sonst E=Summe(B*i,i=1..c−s); D=ceil((1.05*(line_price(letzte Linie)+E)−E)/100)*100; Preis=ceil(D*n^2.5/100)*100. Resources zählt n je Spezialisierung, Energy/Factory jeweils im ganzen Bereich. Die drei kostenlosen Startstandorte zählen bereits für Folgekäufe.

| Bereich | Zusatzslotpreise | zusätzliche Linienpreise | Vollausbau vorhandenes Startgebäude |
|---|---|---|---:|
| factory | 40.0, 80.0, 120.0, 160.0, 200.0, 240.0, 280.0 | 900.0, 3600.0, 8100.0, 14400.0 | 32600.0 |
| resources | 90.0, 180.0, 270.0, 360.0, 450.0, 540.0, 630.0, 720.0, 810.0 | 900.0, 3600.0 | 16650.0 |
| energy | 100.0, 200.0, 300.0, 400.0 | 500.0, 2000.0 | 5500.0 |

| vorhandene Gebäude n | nächstes Resources je Typ | nächste Factory Hall | nächstes Energy Plant |
|---:|---:|---:|---:|
| 0 | 500.0 | 1000.0 | 1000.0 |
| 1 | 4000.0 | 15200.0 | 2200.0 |
| 2 | 22700.0 | 86000.0 | 12500.0 |
| 3 | 62400.0 | 237000.0 | 34300.0 |
| 4 | 128000.0 | 486400.0 | 70400.0 |
| 5 | 223700.0 | 849800.0 | 123000.0 |
| 6 | 352800.0 | 1340400.0 | 194000.0 |
| 7 | 518600.0 | 1970600.0 | 285300.0 |
| 8 | 724100.0 | 2751500.0 | 398300.0 |
| 9 | 972000.0 | 3693600.0 | 534600.0 |

Bei Factory n=10 wird der Kauf abgelehnt; ein hypothetischer weiterer Preis wäre kein verfügbares Angebot. Resources/Energy-Kurven setzen sich fort. Gebäude enthalten Startlinie/-plätze, keine Karten. Typwechsel eines Resources-Gebäudes erfordert leeres Gebäude und Zugangspreis der Zielfamilie, Rename ist kein Typwechsel. Wiederverkauf: 60 % dokumentierter Gebäudeinvestition, auf Cent abgerundet; mindestens ein Gebäude je Produktionsbereich beziehungsweise insgesamt ein Freightgebäude bleibt.

## 4. Resources: alle drei Familien und MK1–99

Alle 49 Primary-Rezepte identisch: 12 Output/6 s, 6 MW, 120 U/min, Common-Karte 340. Extractor 37 Produkte, Drilling Rig Crude Oil/Natural Gas, Harvester zehn Agrar-/Forstprodukte. Unterschiede liegen in Preisen/Freischaltungen. Ein voller Standort kann 30 Karten gleichzeitig betreiben, sofern Strom und Lager reichen.

M=1+0.25*(MK−1), b=Outputbonus in Prozent, S=1+Speed-Research. Output/min=120*M*(1+b/100)*S; MW=6*M*(1+b/200). CSV enthält alle MK1–99 für Common und die beiden Legendary-Bonusendpunkte. Auswahl ohne Research:

| MK | M | Common U/min | Common MW | Legendary 16–20 % U/min | Legendary 16–20 % MW |
|---:|---:|---:|---:|---|---|
| 1 | 1.0 | 120 | 6 | 139.2–144 | 6.48–6.6 |
| 2 | 1.25 | 150 | 7.5 | 174–180 | 8.1–8.25 |
| 10 | 3.25 | 390 | 19.5 | 452.4–468 | 21.06–21.45 |
| 25 | 7.0 | 840 | 42 | 974.4–1008 | 45.36–46.2 |
| 50 | 13.25 | 1590 | 79.5 | 1844.4–1908 | 85.86–87.45 |
| 99 | 25.5 | 3060 | 153 | 3549.6–3672 | 165.24–168.3 |

Voller Standort MK1/Common: 3600 U/min, 180 MW. MK99/Common: 91800 U/min, 4590 MW. MK99/Legendary 20 %: 110160 U/min, 5049 MW; mit vollständigem Speed-Research 118972.8 U/min bei gleicher Leistung. Produktionsobergrenzen sind keine verkauften Mengen. P10-Neustart hat je einen kostenlosen Standort aller drei Typen, aber nur drei Extractor als Starterkarten; Drilling Rig/Harvester müssen beschafft werden. Produkt-Unlocks vollständig in P11-A.

## 5. Factory: gemeinsam begrenzte Plätze und Rezeptunterschiede

Die 500 Plätze sind frei zwischen Processor/Fabricator/Assembler aufteilbar, nicht je 500 pro Stufe. Common-Karten kosten 275/225/240. Alle Zyklen 6 s. Processing Output 1–6 bei 5–15 MW; Fabrication 1–3 bei 10 MW; Assembly 1 bei 12 MW. P11-A führt alle Inputmengen; neue CSV verbindet alle 353 Basisrezepte über product_id.

Für q Output, a Input, P Rezept-MW: Output/Zyklus=q*M*(1+b/100); Input/Zyklus=a*M; Output/min=q*10*M*(1+b/100)*S; Input/min=a*10*M*S; MW=P*M*(1+b/200). Rarity verbessert die Materialeffizienz, MK allein nicht. Speed erhöht Output-/Inputdurchsatz, nicht die angeforderte momentane Leistung.

Der Kern prüft vor Fortschritt und pro Zyklus Material, volle Maschinenleistung und globalen Lagerplatz nach Inputverbrauch. Kein Teilzyklusoutput. Karten-/Standortreihenfolge und gepufferter Fortschritt können den Verlauf ändern. Mittlere Auslastung genügt nicht zum Start einer Maschine, deren ganze Leistung nicht passt. Auch unkonfigurierte, nicht pausierte Karten können Strom reservieren.

Sinnvolle Gleichzeitigkeit hängt neben den 500 Slots von Kapital, freigeschalteten Inputs, Inputraten, Chargenpuffern, Strom und Absatz ab. Ohne Layout/Firmenzustand ist keine feste wirtschaftlich sinnvolle Maschinenzahl je Budget nachweisbar.

Getrennte Slotobergrenzen bei ausschließlich 500 Karten einer Klasse, MK99/Legendary 20 % und vollem Speed-Research: Processing 991440 U/min bei q=6; Fabrication 495720 bei q=3; Assembly 165240. Keine gleichzeitig erreichbaren Kettenmengen: Vorstufen brauchen dieselben 500 Plätze.

### Vollständige Zuordnung aller verarbeitenden Leistungsgruppen

| Klasse | Output/Zyklus | Sekunden | MW | Produkt-IDs |
|---|---:|---:|---:|---|
| assembler | 1.0 | 6.0 | 12.0 | industrial_equipment, heavy_machinery, mining_equipment, mining_drill, heavy_mining_drill, excavator, industrial_crusher, industrial_pump, industrial_compressor, hydraulic_system, electric_motor, precision_motor, gearbox, cnc_machine, industrial_cutting_machine, processing_equipment, advanced_furnace, construction_materials, reinforced_concrete, structural_systems, industrial_hall_modules, prefabricated_structures, industrial_glass_panels, industrial_insulation, engineered_structures, electrical_cable, power_cable, transformer, switchgear, industrial_relay, high_voltage_equipment, industrial_generator, industrial_inverter, solar_array, wind_turbine, gas_turbine, steam_turbine, grid_battery, grid_storage_system, hydrogen_electrolyzer, nuclear_fuel_assembly, nuclear_reactor, basic_chip, microcontroller, microchip, cpu, memory_module, industrial_sensor, industrial_controller, industrial_display, industrial_computer, server, server_rack, compute_node, ai_accelerator, ai_server, data_center_module, supercomputer, robotic_actuator, servo_motor, robotic_arm, industrial_robot, industrial_drone, autonomous_mobile_robot, advanced_industrial_robot, utility_vehicle, combustion_vehicle, electric_vehicle, premium_electric_vehicle, autonomous_vehicle, commercial_truck, industrial_tires, railway_track, freight_railcar, diesel_locomotive, electric_locomotive, high_speed_train, autonomous_freight_train, workboat, cargo_vessel, container_ship, tanker, autonomous_cargo_ship, high_speed_vessel, light_aircraft, cargo_aircraft, commercial_aircraft, jet_engine, advanced_aircraft, autonomous_aircraft, satellite, communication_satellite, navigation_satellite, rocket_engine, launch_vehicle, orbital_vehicle, packaged_food, processed_food, packaged_nutrition, bakery_products, packaged_meals, packaged_beverages, soft_drinks, animal_feed, fertilizer, advanced_fertilizer, construction_frames, packaging_materials, industrial_packaging, protective_packaging, cargo_pallets, commercial_furniture, sustainable_packaging, clothing, workwear, protective_clothing, industrial_clothing, safety_equipment, advanced_protective_equipment, industrial_plastics, industrial_rubber_products, industrial_seals, industrial_chemicals, bio_based_chemicals, bioplastic, biofuel, biodiesel, crop_protection_products, laboratory_equipment, medical_monitor, surgical_equipment, diagnostic_system, advanced_medical_equipment, communication_cable, network_switch, router, radio_transceiver, cellular_base_station, high_speed_network_system, semiconductor_equipment, industrial_laser, machine_vision_system, autonomous_control_system, advanced_semiconductor_equipment, carbon_capture_plant, desalination_plant, synthetic_fuel_plant, quantum_computing_module, superconducting_magnet_system, fusion_reactor_module |
| fabricator | 1.0 | 6.0 | 10.0 | precision_components, cutting_tooling, hydraulic_components, pump_components, compressor_components, turbine_components, mining_components, vehicle_components, marine_components, rail_components, aerospace_components, transformer_components, motor_components, magnetic_components, power_electronics, display_components, semiconductor_components, semiconductor_die, sensor_components, control_electronics, computing_components, memory_components, processor_components, telecom_components, network_components, avionics_components, battery_components, advanced_cell_components, storage_components, solar_components, wind_components, reactor_components, electrolyzer_components, composite_components, nutrition_components, agricultural_chemicals, industrial_fabric, fiber_components, bio_composite, biopolymer, tire_components, ethanol_components, biodiesel_feedstock, advanced_alloy_components, catalyst_components, gas_handling_components, asphalt_components, agricultural_mineral_components, sweetener_components, silicon_substrate, rubber_blend_components, refractory_alloy_components, filtration_components, membrane_components, medical_components, autonomous_components, server_components, ai_compute_components, chemical_components, bio_material_components, nuclear_fuel_components, grid_storage_components, corrosion_resistant_components |
| fabricator | 2.0 | 6.0 | 10.0 | iron_components, steel_components, stainless_components, aluminum_components, titanium_components, gear_components, bearing_components, structural_components, insulated_wire, electrical_components, battery_materials, concrete_components, glass_panels, ceramic_components, insulation_material, packaging_components, food_ingredients, fertilizer_components, technical_textile, wooden_components, galvanized_components, shielding_components |
| fabricator | 3.0 | 6.0 | 10.0 | copper_wire |
| processor | 1.0 | 6.0 | 5.0 | soy_oil, soy_protein |
| processor | 1.0 | 6.0 | 12.0 | high_purity_silicon, carbon_fiber |
| processor | 2.0 | 6.0 | 5.0 | flour, corn_meal, starch, raw_sugar, refined_sugar, vegetable_oil, cotton_fiber, fruit_concentrate |
| processor | 2.0 | 6.0 | 6.0 | cellulose, fermentation_feedstock, organic_feedstock |
| processor | 2.0 | 6.0 | 7.0 | potassium_compound, industrial_gas, processed_rubber, bio_lubricant |
| processor | 2.0 | 6.0 | 8.0 | sulfuric_acid, chlorine, ammonia, phosphoric_acid, bitumen |
| processor | 2.0 | 6.0 | 9.0 | polymer, synthetic_rubber, industrial_resin, hydrogen |
| processor | 2.0 | 6.0 | 10.0 | silicon, catalyst_metal |
| processor | 2.0 | 6.0 | 12.0 | platinum, palladium, nuclear_material |
| processor | 2.0 | 6.0 | 15.0 | superconducting_alloy |
| processor | 3.0 | 6.0 | 5.0 | lumber |
| processor | 3.0 | 6.0 | 6.0 | processed_gypsum, wood_pulp |
| processor | 3.0 | 6.0 | 7.0 | glass, cement, ceramics, treated_lumber |
| processor | 3.0 | 6.0 | 8.0 | chemical_feedstock, galvanized_metal, shielding_material |
| processor | 3.0 | 6.0 | 9.0 | purified_graphite |
| processor | 3.0 | 6.0 | 10.0 | silver, vanadium_alloy |
| processor | 3.0 | 6.0 | 11.0 | gold |
| processor | 3.0 | 6.0 | 12.0 | rare_earth_metals |
| processor | 3.0 | 6.0 | 13.0 | stainless_steel, nickel_alloy |
| processor | 4.0 | 6.0 | 10.0 | cobalt, molybdenum, vanadium, lithium, niobium |
| processor | 4.0 | 6.0 | 11.0 | titanium, tungsten |
| processor | 4.0 | 6.0 | 12.0 | steel |
| processor | 5.0 | 6.0 | 8.0 | zinc, lead, tin, manganese |
| processor | 5.0 | 6.0 | 9.0 | aluminum, nickel, chromium |
| processor | 6.0 | 6.0 | 8.0 | iron, copper |

## 6. Freight: vier Familien und tatsächlicher Absatz

| Fahrzeug | Common-Karte | Gebäudegrundpreis | Startplätze | Cargo MK1 | Reise s | Lieferungen/min kontinuierlich | U/min kontinuierlich |
|---|---:|---:|---:|---:|---:|---:|---:|
| Freight Truck / freight.truck | 205.0 | 2000.0 | 3 | 40.0 | 60.0 | 1 | 40 |
| Freight Train / freight.train | 650.0 | 8000.0 | 2 | 400.0 | 120.0 | 0.5 | 200 |
| Cargo Ship / freight.ship | 14955.0 | 100000.0 | 2 | 16000.0 | 240.0 | 0.25 | 4000 |
| Cargo Aircraft / freight.aircraft | 4985.0 | 30000.0 | 2 | 4000.0 | 180.0 | 0.333333333333 | 1333.33333333 |

Gebäude mit n vorhandenen desselben Typs: Grundpreis*(n+1)^2. Erste fünf Preise: Garage 2000/8000/18000/32000/50000; Rail 8000/32000/72000/128000/200000; Airport 30000/120000/270000/480000/750000; Harbor 100000/400000/900000/1600000/2500000. Kostenlose Startgarage zählt bereits, nächste Garage 8000.

Slotindex i, nullbasierte Linie j=floor(i/8), Position p=i mod 8. Erste Position neuer Linie j>=1 kostet 900*j^2 mit einem Platz. Sonst 60*(p+1−s), s=3 Garage bzw. 2 andere in erster Linie, s=1 in Folgelinien. Linien 2/3/4/5: 900/3600/8100/14400; Folgelinien-Zusatzplätze 60/120/180/240/300/360/420. Vorgängerlinie und Linienanfang müssen gekauft sein. Kein aktives Liniennummerlimit; alte MAX_FREIGHT_FACILITY_EXPANSIONS=3 und Expansionstupel begrenzen diesen Pfad nicht.

Cargo=C*M*(1+b/100)*(1+Research-freight_capacity); Reisezeit=T*(1+b/200). Die Zeit wird multipliziert, nicht dividiert. MK erhöht Cargo ohne Zeitänderung. Legendary 20 %: Cargo 1.20, Zeit 1.10, kontinuierlicher Raritybonus 1.20/1.10. MK99/Common: Cargo 25.5*C, Zeit T. Research erhöht Cargo, nicht Geschwindigkeit. Vollständige MK-/Raritywerte in CSV.

Vier getrennte Größen: nominelles Cargo je Sendung; kontinuierliche Vollastobergrenze Cargo*60/Reisezeit; tatsächlich wirtschaftlich anerkannte Ankunftsmenge; real verfügbare Waren/Produktion. Fahrzeugobergrenzen sind nominell additiv, teilen reale Bestände. Ein Fahrzeug ist einem Produkt/Zieltyp zugeordnet und hat höchstens eine aktive Sendung.

Dispatch nimmt min(Bestand,Cargo), wartet nicht automatisch auf volle Ladung und entnimmt Waren sofort physisch dem Lager. Kein zweiter Lagerabzug für dieselbe Reservierung. Contractbedarf wird um schon unterwegs befindliche Waren vermindert. Cash entsteht bei Ankunft/Abrechnung. Market nutzt Versandquote; überzählige/ungültige Contract-/Consortiumladung kann bei Ankunft verkauft werden. Statistiken unterscheiden tatsächlich anerkanntes Sell/Contract/Consortium.

Tickreihenfolge: alte Sendungen merken, produzieren, alte Sendungen bewegen/abrechnen, neue Exporte starten. Neue Fahrten verlieren nicht rückwirkend die Tickdauer. Wiederstarts sind schrittweitenquantisiert. tick() nutzt 1 s, normale UI advance_time mit gemessener Zeit aus 250-ms-Timer. Große Einzelzeitsprünge beweisen keine kontinuierlichen Mehrfachfahrten. capacity_per_cycle mit 6 s ist rechnerischer Durchsatzanteil, nicht Cargo je Fahrt. total_facility_capacity ignoriert Research/Busy-Auslastung, ist keine Ist-Lieferstatistik.

Freight kann auf jeder Entwicklungsstufe begrenzen, muss es aber nicht. Weitere Fahrzeuge/Linien/Gebäude skalieren, während Factoryplätze, Produktion, Energie, Kapital oder Puffer vorher enden können.

## 7. Energie: vollständiger Kraftwerkskatalog

| Karte | Common-Kosten | Basis-MW | Brennstoff/min MK1 | MK99/Common MW | MK99 Brennstoff/min |
|---|---:|---:|---|---:|---:|
| energy.solar_array | 180.0 | 20.0 | 0.0 × keiner | 510.0 | 0.0 |
| energy.wind_turbine | 360.0 | 35.0 | 0.0 × keiner | 892.5 | 0.0 |
| energy.coal_power_plant | 520.0 | 60.0 | 60.0 × coal | 1530.0 | 1530.0 |
| energy.gas_power_plant | 1200.0 | 180.0 | 60.0 × natural_gas | 4590.0 | 1530.0 |
| energy.nuclear_power_plant | 6000.0 | 500.0 | 10.0 × nuclear_fuel_assembly | 12750.0 | 255.0 |

Energy-Plant: 3×5=15 Generatorplätze, ein Startplatz. Zusatzslots 100/200/300/400 je Linie, Linien 2/3 kosten 500/2000 mit je einem Platz. Vollausbau vorhandenes Plant 5500, Karten separat. Solar/Wind sind brennstofffrei und verlässlich im Kern: keine Wetter-/Tag-Nacht-Ausfälle oder laufenden Cashkosten hinzufügen.

Leistung=B*M*(1+b/100)*(1+Research-energy_output). Brennstoff=f*M/min, unabhängig von Rarity/Energy-Research. Kern verlangt Fuel für den ganzen Simulationsschritt vor Produktion; zu wenig Fuel bedeutet keine anteilige Generatorlaufzeit. Auch ungenutzte angebotene Leistung kostet Fuel. Preview elapsed=0 beweist keinen nachhaltigen Betrieb.

P7 release_balance.balance_definitions setzt Verbrauch aus halber Rohstoffkartenrate, Nuclear zusätzlich über rekursiven Uranbedarf je Fuel. Wirksam MK1: Coal 60/min, Gas 60/min, Nuclear Fuel Assembly 10/min. Coal braucht einen Coal-Extractor und 6 MW Vorproduktion; Gas Drilling Rig für Natural Gas und 6 MW. Solar kann bootstrappen. Generatorkauf und Brennstoff-Rezeptfreischaltung sind getrennt.
Natural Gas benötigt Level 5, Uranium Ore/Nuclear Fuel Assembly Level 25; vorgelagerte Lifetime-Unlocks stehen in P11-A.

Nuclear-Kette je 10 Fuel/min, MK1/Common, ideal gemittelt: 60 Uranium Ore, 69 Lead Ore, 10 Borate Ore; 40 Nuclear Material, 30 Shielding Material, 5 Lead; 20 Nuclear Fuel Components, 10 Shielding Components; 10 Nuclear Fuel Assembly. Kapazitätsmäßig mindestens: 2 Nuclear-Material-Processor, 1 Shielding-Material-Processor, 1 Lead-Processor, 2 Fuel-Component-Fabricator, 1 Shielding-Component-Fabricator, 1 Assembler = 8 Factory-Karten, dazu 3 Primary-Extractor. Überschüssige Vorproduktion erfordert bedarfsgerechtes Pausieren.

Ausreichende, nicht optimierte Investitionshülle: 3 Extractor 1020; 4 Processor 1100; 3 Fabricator 675; 1 Assembler 240; Nuclear 6000; Factory-Slots 4–8 zusammen 600; Mining-Slots 2/3 zusammen 270; bezahltes Bootstrap-Solar 180 plus Energy-Slot 2 für 100. Summe 10185 ohne Starterkarten-Gutschrift, kostenlose Startgebäude vorausgesetzt. Keine externe Fracht für interne Waren nötig. Zusätzlich Level 25, Lifetime-Unlocks, Aufbauzeit und Fuel-Startpuffer. Volle Leistung der acht Fabrikkarten plus drei Rohstoffkarten: 100 MW. Nuclear liefert danach 500 MW; Solar kann die Vorproduktion zeitlich gestaffelt bootstrappen. Kein Engine-Nachweis stationären Durchsatzes.

## 8. Global Storage

Startkapazität aus allen 353 default_capacity-Werten: **75280 Einheiten insgesamt**, nicht pro Produkt. Zusammensetzung: 49×500, 67×300, 1×200, 86×180, 150×100. Normale Kapazität auf Upgradelevel L=75280*(1+0.25*L), also +18820 je Upgrade vor Research. Preis von L nach L+1=round(250*(1+L)^3/10)*10. Alte Konstante 1.65 für Wachstum wird von dieser aktuellen Funktion nicht benutzt; wirksam ist kubisches Wachstum.

| aktueller L | Lager ohne Research | nächster Upgradepreis |
|---:|---:|---:|
| 0 | 75280.0 | 250.0 |
| 1 | 94100.0 | 2000.0 |
| 2 | 112920.0 | 6750.0 |
| 3 | 131740.0 | 16000.0 |
| 5 | 169380.0 | 54000.0 |
| 10 | 263480.0 | 332750.0 |
| 20 | 451680.0 | 2315250.0 |

MAX_INVENTORY_STORAGE_LEVEL=infinity, kein Levelcap im Kaufbefehl. Research-storage_capacity multipliziert global, maximal 1.25. apply_inventory_storage_level respektiert in Sonder-/Migrierzuständen eine schon größere warehouse_capacity; Tabelle beschreibt die normale Basiskurve. Alte ResourceStock.capacity ist Metadatum; Kern nutzt Global Storage.

Lager zählt alle positiven Warenmengen, nicht Cash/Karten/Strom. Produktion verlangt Platz für ganze Charge nach Verbrauch ihrer Inputs; Primäroutput braucht nur zusätzlichen Platz. Dispatch schafft durch Entnahme Platz, obwohl Cargo weiter unterwegs ist. Mehr Lager puffert Batches/Stillstände, schafft keine dauerhafte zusätzliche Produktionsrate.

## 9. MK, Rarity und Research: Kosten und Obergrenzen

MK1–99: M=1+0.25*(MK−1), maximal 25.5. Common 0 %, Uncommon 1–5 %, Rare 6–10 %, Epic 11–15 %, Legendary 16–20 %, Zehntelprozentschritte. Legendary hat keinen festen Common-Kaufpreis. Daily bietet Uncommon; Qualität kann durch bestehende Upgrade-/Packmechanismen entstehen. Kein erfundener garantierter Legendary-Anschaffungspreis wird geplant.

MK-Upgradepreis=ceil(max(Commonpreis*aktuellerMK^1.7, 0.25*Basisnettoertrag*900*(nächsterMK/2)^2.3)*100)/100. Basisnettoertrag einer Maschinenfamilie ist das Maximum aller Rezeptmargen/Sekunde nach Kohlepreisäquivalent der Leistung, mindestens 0.01, nicht nur das gerade ausgewählte Rezept. Energy: Basis-MW*Coalpreis*0.01, mindestens 0.01; Freight: max(0.01,Cargo/Basisreisezeit). CSV enthält alle 98 Übergänge je 15 Familien. Gesamtes MK99-Investment=Summe der Übergänge zusätzlich zum Kartenkauf. Rarity ändert diese Kostenfunktion nicht.

Nur noch Common-Karten würfeln bei Upgrades Qualität; ein Qualitätsfund beendet weitere Common-Rolls. Wahrscheinlichkeiten je Roll: Legendary 0.000005, Epic 0.00015, Rare 0.0015, Uncommon 0.012 (keine Prozentzahlen). Keine Zufallsqualität als garantierte Ausbauleistung behandeln. Upgrades/Research sind einmalige Investitionen, keine Minutenmiete; wiederkehrend verbraucht werden Rezeptmaterialien und gegebenenfalls Fuel.

Research addiert gegen vorhandene MK-/Raritybasis. 645 Knoten in 21 Bäumen und 60 Spezialisierungsslots je 1 RP, komplett 705 RP. Je Industry-Domain vier Slots; gleiches Produkt darf wiederholt gewählt werden. Keine unendlichen Bonusstufen pro Knoten. RP unter anderem je Company-Levelaufstieg und aus Daily-/Weeklyabschlüssen, nicht aus bloßem Cash. Kauf braucht Prerequisites/Major und passende Domain. Full Respec gibt Punkte zurück, Cooldown 86400 Sekunden.

| Effekt | maximale passende Katalogsumme | wirksam |
|---|---:|---|
| production_speed global | 0.08 | Multiplikator 1.08 |
| energy_output global | 0.11 | Multiplikator 1.11 |
| freight_capacity global | 0.11 | Multiplikator 1.11 |
| storage_capacity global | 0.25 | Multiplikator 1.25 |
| contract_value global | 0.08 | Multiplikator 1.08 |
| value global | 0.08 | Multiplikator 1.08 |
| value passende Industry-Domain | 0.098 | zusätzlich zu global |
| value je passendem Produktspezialisierungsslot | 0.01 | vier passende Slots maximal 0.04 |

Ein Produkt maximal Marktwertmultiplikator 1+0.08+0.098+0.04=**1.218**. Zuordnung anhand Outputdomain/-produkt, keine rekursive Bonusweitergabe auf Inputs. Contract-cash addiert contract_value=0.08 im selben Researchterm, maximal 1.298 vor Kategorieaufschlag. Regular/Daily/Weekly verwenden 0/20/40 % Kategorieaufschlag. Quotes werden eingefroren, angenommene Rewards nicht nachträglich neu berechnet. Research senkt weder Inputs noch MW direkt; Speed erhöht Inputverbrauch pro Minute.

## 10. Acht Kapitalbudgets: nachvollziehbare Ausbau-Beispiele

Jede Zeile ist ein unabhängiges Szenario ab P10-Neustart mit genanntem Cashbudget: Level 1, kein Research, Common MK1, Iron Ore. Drei kostenlose Primary-Standorte, eine Factory Hall, ein Energy Plant, Startgarage, drei Extractor, ein Solar, zwei Processor und zwei Trucks sind vorhanden; Karten starten unplatziert. Anfangswaren 145 Ore, 70 Coal, 88 Copper Ore werden nicht als dauerhafte Produktion oder zusätzliches Cash gezählt.

Bewusst einfaches Schema: n Iron-Ore-Extractor, ceil(6n/20) Solar, 3n Trucks. Mining-/Energy-Gebäude nacheinander bis 30/15 Karten füllen, eine Garage mit genug Linien/Slots. Echte Kaufquotes, Startergeräte angerechnet. Feste Stützlayouts n=1,2,3,4,5,8,10,15,20,30,40,50,60,80,100,150,200; je Budget ist ein bezahlbares ausgewiesen. Keine Suche nach optimaler Strategie, keine Engine-Simulation, kein Vollauslastungsversprechen. Andere Freight-/MK-Kombinationen können günstiger sein.

| Budget | Beispielkosten | Restcash | Extractor | Solar | Trucks | Mining/Energy-Gebäude | Garagenlinien | Produktions-/kontinuierliches Frachtmaximum U/min |
|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 1250 | 205 | 1045 | 1 | 1 | 3 | 1/1 | 1 | 120 |
| 5000 | 3505.0 | 1495.0 | 3 | 1 | 9 | 1/1 | 2 | 360 |
| 10000 | 7585.0 | 2415.0 | 5 | 2 | 15 | 1/1 | 2 | 600 |
| 50000 | 30590.0 | 19410.0 | 10 | 3 | 30 | 1/1 | 4 | 1200 |
| 100000 | 78185.0 | 21815.0 | 15 | 5 | 45 | 1/1 | 6 | 1800 |
| 500000 | 166410.0 | 333590.0 | 20 | 6 | 60 | 1/1 | 8 | 2400 |
| 1000000 | 520570.0 | 479430.0 | 30 | 9 | 90 | 1/1 | 12 | 3600 |
| 10000000 | 7907030.0 | 2092970.0 | 80 | 24 | 240 | 3/2 | 30 | 9600 |

Geräte dieses Schemas brauchen kein höheres Level, Iron Ore ist freigeschaltet. Produktions- und Frachtobergrenzen stimmen im Schema numerisch überein; realer Absatz ist trotzdem nicht nachgewiesen: Teilladungen, Reihenfolge und Zeitquantisierung bleiben wirksam. Weil Iron Ore derzeit 1 Dollar kostet, entspricht die U/min-Obergrenze numerisch der Brutto-Dollar/min-Obergrenze; kein garantierter Gewinn oder Payback. Ein hohes Cashbudget schaltet Uran oder Assembly-Rezepte nicht automatisch frei. Einzelne Kostenbestandteile stehen je Budget in der CSV.

Weitere jeweils alternative Ausbauoptionen: bestehendes Mining auf 30 Plätze 16650 ohne Karten, Energy auf 15 Plätze 5500, Factory auf 50 Plätze 32600. Bei 5000 passt isoliert eine zweite Mining-Anlage desselben Typs für 4000, bei 10000 ein weiterer Energy Plant für 2200 oder eine zweite Garage für 8000; Karten/Betrieb separat. Zweite Factory Hall 15200 passt nicht isoliert in 10000. Rail/Trains, Airport/Aircraft, Harbor/Ships sind nach ihren Tabellenpreisen kaufbar, brauchen passende Gebäude; verfügbare Waren/Unlocks separat. Diese Alternativen dürfen nicht stillschweigend zusätzlich zu bereits ausgegebenen Kosten einer Budgetzeile gekauft werden.

### Kostenbestandteile der Budgetbeispiele

| Budget | Mining-Gebäude/-plätze | Energy-Gebäude/-plätze | Freight-Plätze | zusätzliche Karten |
|---:|---:|---:|---:|---:|
| 1250 | 0 | 0 | 0 | 205 |
| 5000 | 270.0 | 0 | 1800.0 | 1435 |
| 10000 | 900.0 | 100.0 | 3060.0 | 3525 |
| 50000 | 4050.0 | 300.0 | 17760.0 | 8480 |
| 100000 | 5850.0 | 1000.0 | 57720.0 | 13615 |
| 500000 | 9000.0 | 1500.0 | 137340.0 | 18570 |
| 1000000 | 16650.0 | 2100.0 | 473160.0 | 28660 |
| 10000000 | 69000.0 | 9800.0 | 7749120.0 | 79110 |

## 11. Gesamtkapital vollständiger Produktionsketten

Einmalig: nötige Rohstoff-/Verarbeitungskarten aller Stufen, zusätzliche Gebäude/Linien/Slots, Generatoren, Freightfahrzeuge/-gebäude, nötige Lagerupgrades und Summe gewählter MK-Upgrades. Startergeschenke/vorhandene bezahlte Infrastruktur nicht nochmals als Cashbedarf zählen. Rarity-spezifische historische Anschaffungspreise sind nicht durch Common-Ersatzpreise zu ersetzen.

Wiederkehrend: tatsächliche Inputs je Zyklus und Fuel. Warenwert zum Verkaufspreis ist Opportunitätswert, keine automatische Cashabbuchung. Es gibt keine Pflichtgebühren für Strom, Fahrtlohn, Gebäudemiete oder Abschreibung im Kern. Anlauf-/Pipelinewaren und Fuelpuffer sind gebundene Güter. Amortisation braucht eine benannte zusätzliche Investition und zusätzlich nachhaltig erzielte Cashrate gegenüber einem Referenzfall.

### A: Iron MK1/Common

1 Extractor 120 Ore/min; 1 Processor 120 Ore → 60 Iron/min. Leistung 6+8=14 MW, 1 Solar 20 MW. 2 Trucks kontinuierlich 80 U/min. Ein Mining-, ein Factory-, ein Energy- und zwei Garageplätze sind schon vorhanden. Common-Geräteersatz=340+275+180+2*205=1205; ab Startergeschenken zusätzlicher Cashbedarf für diese Geräte 0. Das ist kein neu frei kaufbares kostenloses Unternehmen: Gebäude/Karten sind Startgeschenke. Iron verlangt Level 1 und 120 Lifetime-Ore bei freigeschaltetem Input; Anfangsbestand zählt nicht als Lifetime-Produktion. Keine realen 60 Ironverkäufe/min behauptet.

### B: Steel MK1/Common

1 Iron-Ore- und 1 Coal-Extractor, 1 Processor: 120 Ore + 30 Coal/min → 40 Steel/min. Leistung 6+6+12=24 MW, 2 Solar 40 MW, 1 Truck theoretisch 40 U/min. Common-Geräteersatz=2*340+275+2*180+205=1520; vorhandene Startgebäude mit Mining-Slot 2 für 90 und Energy-Slot 2 für 100 ergeben Hülle 1710 ohne Startergutschriften. Ab Starterbestand fehlen nur zweiter Solar 180 und diese Zusatzplätze 190: **370 zusätzlicher Cashbedarf**. Level 1 und jeweils 120 Lifetime Ore/Coal erforderlich. Coalüberschuss braucht Puffer, anderweitigen Abfluss oder zeitweises Pausieren.

### C: Lumber MK1/Common

1 Harvester 340, 1 Processor 275, 1 Solar 180, 1 Truck 205: 30 Timber/min → 30 Lumber/min bei 6+5=11 MW, Geräteersatzwert 1000. Passende kostenlose Startgebäude reichen. Ab Starterbestand nur Harvester zusätzlich für 340. Timber ab Level 1, Lumber zusätzlich 120 Lifetime Timber. Ein durchlaufender Harvester liefert 120 Timber/min und Überschuss; für die angegebene Kettenrate ist zeitweises Pausieren oder separater Abfluss nötig.

Nuclear als vollständiges mehrstufiges Beispiel siehe Abschnitt 7. Beliebige Assemblyketten müssen sämtliche Zwischenstufen gemeinsam in die 500 Factory-Slots einpassen. Geldwert direkter Inputs ersetzt keine Vorproduktionsgeräte.

## 12. Messgrößen für Preis-/Dominanzanalyse

| Messgröße | Mit heutigen Daten exakt formulierbar | zusätzlich nötig |
|---|---|---|
| Cash je transportierter Einheit | Basispreis bzw. Research-Verkaufsquote | Versandquote; Vertrags-/Poolbedingungen |
| nominelles Cash/min | kontinuierlicher Absatz * Quote | realer Absatz, Teilladungen, Anlauf, Arrival/Dispatch erfordern Engine-Beobachtung |
| zusätzlicher Warenwert je Schritt | q*pOutput − Summe(a*pInput) pro Basiszyklus | klare Opportunitätsbasis; Rarity/Research auf reale Mengen beziehen |
| Maschinenminuten | P11-A ProductionValueCalculator | konkrete MK-/Rarity-/Researchbelegung und ganzzahlige Parallelmaschinen |
| Gesamtkapital | vorhandene Quotes bei festem vollständigem Layout | Zielrate, Vorbesitz, Unlocks, Steuerung, Puffer |
| gebundene Kartenplätze | ein kompatibler Platz je Karte; Factory regulär 500 | konkrete Kette einschließlich Energie/Rohstoff/Freight |
| MW | Summe aktiver ganzer Kartenleistungen | Fuel, Priorität und tatsächliche Laufzeit |
| Amortisation | zusätzliche Investition / zusätzliche nachhaltige Cashrate | Referenzportfolio, Anlauf und tatsächliche Liefer-/Warenflüsse |
| Freischalthürde | P11-A Level und Lifetime-Schwellen | realer Fortschritt; Budget beweist keine Freischaltung |

P11-A deckt alle Rezepte, Originalpreise, direkten/rekursiven Inputs, Basisraten, Rezept-MW, Maschinen und Unlocks ab. P11-B ergänzt Limits, Kostenkurven, alle 15 Familien über MK1–99, Freight-/Energy-/Storage-Mechanik, Research und Kapitalbeispiele. Für Optimierung fehlen insbesondere die gemeinsam festzulegende Zielfunktion, Zeithorizont und zulässigen Firmenzustände: Level/RP, Kartenqualität, Vorbesitz, Bestände, bezahlte Infrastruktur, Puffer, Steuerung, Ziele und Investitions-/Wiederverkaufsannahmen. Fehlende Daten werden nicht mit Vollfreischaltung ersetzt.

Kontinuierliche Flussgrenzen und Quotes sind Datenanalyse. Nachhaltige Ist-Liefer-/Cashraten bei Chargen, Reservierung, Reihenfolge und wechselnden Engpässen brauchen kontrollierte Engine-Messungen an konkreten Zuständen. Hier keine Engine-Simulation durchgeführt.

### Leaderboard- und Progressionsanreize

services/local.py: Company-Level-Ranking nach Level/aktuellen XP. Total Earnings nach kumulierten verbuchten Einnahmen, nicht Nettovermögen oder Gewinn nach Investitionen. Produktproduktion: kumulierte akzeptierte Lifetime-Produktion, einschließlich später intern verbrauchter Waren; Versand allein zählt nicht als Produktion. Lokaler Service/Demo-Gegner, kein bewiesener globaler Wettbewerb. Höhere Verkäufe/Contractgelder erhöhen Earnings; Reinvestition senkt diese kumulierte Kennzahl nicht.

Company-XP: Kontinuität 40 XP je produktiver Minute, Tagescap 1200, Bankcap 3600. Tägliche Arbeitswertschwellen 25/100/300/750 geben je 500 XP. Einmalige Erstproduktion Primary/Processing/Fabrication/Assembly 25/40/60/100 XP, Familienmastery je 250. Damit bestehen Anreize für Dauerbetrieb, Arbeitswert und Vielfalt zusätzlich zu Cash. Level endet nicht bei 100, danach gilt höhere XP-Kurve. Aufstiege gewähren RP; weitere Anreize über Contracts/Consortium. Hohe Preise allein bilden dies nicht ab.

## 13. Besondere Prüfungen und Grenzen

- Primary-Gesamtdurchsatz ohne designte endliche Gesamtgrenze über Gebäudeanzahl; bei endlichem Kapital/Platz und pro Karte endlich. Verarbeiteter Durchsatz regulär durch gemeinsame 500 Factory-Slots und endliche Karten-/Researchfaktoren begrenzt.
- MK99 ist höchster regulärer MK. Company-Level ist unabhängig und läuft über 100 weiter.
- Nicht alle Gebäude sind beliebig erweiterbar: Resources 30, Energy 15, Factory 50 Plätze und 10 Hallen. Freightlinien sowie zusätzliche Resources-/Energygebäude besitzen keinen festen Anzahlcap.
- Freight kann auf jeder Stufe begrenzen, muss es nicht. Energie, Produktion, Freight, Lagerpuffer und Kapital können wechselweise limitieren.
- Processing/Fabrication haben unterschiedliche Leistungen, vollständig mit Produkt-IDs in Abschnitt 5 und P11-A erfasst.
- Budgetbeispiele ohne höheren Level/Research; All-Research-Werte gesonderte Katalogobergrenzen.
- Keine Preisfunktion, Balancingempfehlung oder Produktänderung eingeführt.

### MK-Kostenkurve und kumulierte MK99-Investition

Kosten sind reine Upgradequotes ohne Kartenkauf/Gebäude. Zeilen gelten für die ganze Kartenfamilie, nicht nur ein gewähltes Rezept. Exakte Kosten aller Zwischenstufen in CSV.

| Kartenfamilie | MK1→2 | MK10→11 | MK50→51 | MK98→99 | Summe MK1→99 |
|---|---:|---:|---:|---:|---:|
| machine.extractor | 2593.81 | 130849.08 | 4456345.98 | 20489362.38 | 624964697.63 |
| machine.processor | 882.6 | 44524.41 | 1516374.04 | 6971975.96 | 212658587.02 |
| machine.fabricator | 1081.13 | 54539.37 | 1857455.11 | 8540196.59 | 260492312.18 |
| machine.assembler | 3737.3 | 188534.82 | 6420957.5 | 29522242.11 | 900484786.44 |
| energy.solar_array | 180.0 | 9021.38 | 139162.28 | 436874.64 | 16075998.43 |
| energy.wind_turbine | 360.0 | 18042.75 | 278324.55 | 873749.28 | 32151996.36 |
| energy.coal_power_plant | 520.0 | 26061.74 | 402024.35 | 1279696.48 | 46471686.2 |
| energy.gas_power_plant | 1200.0 | 60142.47 | 927748.49 | 3839089.42 | 121909363.11 |
| energy.nuclear_power_plant | 6000.0 | 300712.35 | 4638742.43 | 14562487.96 | 535866598.19 |
| freight.truck | 205.0 | 10274.34 | 257711.43 | 1184904.14 | 36176044.94 |
| freight.train | 750.0 | 37835.15 | 1288557.14 | 5924520.7 | 180711544.37 |
| freight.ship | 15000.01 | 756702.99 | 25771142.61 | 118490413.93 | 3614441583.89 |
| freight.aircraft | 5000.0 | 252234.33 | 8590380.87 | 39496804.65 | 1204813861.58 |
| machine.drilling | 973.8 | 49125.16 | 1673062.58 | 7692397.68 | 234632825.67 |
| machine.agriculture | 748.8 | 37774.62 | 1286495.44 | 5915041.47 | 180420065.75 |

### Zusätzliche Energie-Kapazitätswerte

| Generator | voller Plant 15 Karten MK1/Common MW | MK99/Legendary20+volles Energy-Research MW je Karte | Brennstoff/min dabei |
|---|---:|---:|---:|
| energy.solar_array | 300.0 | 679.32 | 0 |
| energy.wind_turbine | 525.0 | 1188.81 | 0 |
| energy.coal_power_plant | 900.0 | 2037.96 | 1530 |
| energy.gas_power_plant | 2700.0 | 6113.88 | 1530 |
| energy.nuclear_power_plant | 7500.0 | 16983 | 255 |

## 14. Quellen, CSV-Format und Verifikation

Produktive Quellen: src/production_zero/core/{infrastructure_prices,commands,state,freight,simulation,release_balance,definitions,cards,supply,mk_upgrades,storage_upgrades,research,modifiers,progression,company,company_xp,infrastructure,machine_operations,production_pause,statistics,contract_capacity,contracts,consortium}.py; src/production_zero/data/{definitions.py,game_definitions.json,resource_definitions.json,resource_progression.json,research_definitions.json,research_domains.json}; src/production_zero/ui/{main_window,factory_view,production_board_views,leaderboard_view}.py; src/production_zero/services/local.py; beide vollständigen P11-A-Dokumente.

CSV: UTF-8 mit BOM und Komma, eine Zeile je Kategorie/Entität/Messgröße/Bedingung. product_id verbindet alle 353 Rezeptgruppen mit P11-A, machine_id verbindet die Karten-/MK-Daten. mk_level, rarity, bonus_percent, research_state, budget_usd, unit, conditions, existing_formula, source kennzeichnen Grundlage und Voraussetzungen. unbounded bedeutet kein Spiel-Anzahlcap; leere Felder nicht anwendbar. Legendary-Datensätze zeigen gültige Bonusendpunkte 16/20, alle Zwischenrolls folgen der vorhandenen Formel. Originalzahlen ohne UI-Cent-Aufrundung; Quellverweise auf relative Modulnamen sind unter den hier angegebenen Verzeichnissen aufzulösen.

Alle 353 Rezeptbasisdaten wurden mit aktuellen geladenen Definitionen verglichen. Erfasst: sechs Produktionskartenfamilien, fünf Energiearten, vier Freightfamilien; alle drei Primary-Gebäudetypen, Factory, Energy, vier Freightgebäude. Alle MK1–99, alle 98 Upgradeübergänge pro Familie, alle 645 Researchknoten und 60 Slots einzeln. Kein Testlauf, keine Simulation oder produktive Implementierung.


### Abschließender Bestandsschutz-Nachweis

CSV erneut eingelesen: **20819 Datenzeilen**, neun Gebäudefamilien und 15 Karten-/Installationsfamilien. Alle acht angeforderten Kapitalbudgets vorhanden. Alle 353 Originalpreise stimmen exakt mit dem aktuellen BASE_MARKET_PRICES-Katalog überein, Produkt-IDs vollständig mit P11-A verknüpft. Alle 1470 MK-Übergangsquotes, sämtliche MK1–99 und Research-Katalogobergrenzen geprüft; Research-Multiplikatoren zusätzlich mit dem bestehenden research_multiplier-Resolver abgeglichen. Budgetkosten bleiben jeweils innerhalb des Budgets, gekaufte Plätze und nominelle Stromleistung reichen für das ausdrücklich beschriebene Layout. Daraus wird keine gemessene nachhaltige Cashrate abgeleitet.

Vorher-/Nachher-SHA256-Vergleich über identische Pfadlisten:

| Prüfgruppe | Dateien | SHA256-Aggregat vorher = nachher |
|---|---:|---|
| Bestehendes Projekt unter src, tests, scripts und docs einschließlich beider P11-A-Dateien | 976 | 4ed7a70abbd271447faca8810b109c1533889770da74ccd91594e8bb094af04c |
| Bestehende geschützte Builddateien | 4083 | 94e38bf43ee71dcd7a4415ead3e9a7e592f16ffd150fec28353c600bbf28aad4 |
| Persönliche Save-Dateien | 5 | ab31eafb6f021ab115560c9f3f7b7800ec8d9ac8d4ca2b05ede27fd840e5d581 |

Projektgruppe: alle Dateien der genannten vier Verzeichnisse außer Python-Bytecode und den beiden neu angeforderten P11-B-Dokumenten. Builds-/Save-Pfadlisten stammen aus dem vorhandenen P10-Backupmanifest unter artifacts/phase10/backup-20261022T224910Z. Für jeden sortierten Pfad wurde dessen UTF-8-Text und binärer SHA256-Inhaltshash in den Gruppenhash aufgenommen. Ausgangswerte wurden für diesen Auftrag frisch erfasst, nicht mit einem älteren Spielstand gleichgesetzt. Spielstände ausschließlich als Bytes gelesen und gehasht; keine Datenbank geöffnet oder migriert.

Nur die beiden angeforderten Dokumente erstellt. Keine Änderung an Quellen, Tests, Rezepten, Preisen, MK, Energie, Freight, Gebäuden, Storage, Research oder Progression. Keine neue Programmdatei, kein Engine-Lauf, kein Build. P11-B endet hier.
