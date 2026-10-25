"""Export the live central P7 price schedule, including every Freight MK."""
import csv,json,sys
from pathlib import Path
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from production_zero.core.infrastructure_prices import BOARD_LIMITS,facility_price,line_price,slot_price,FREIGHT_BUILD_BASES
from production_zero.core.freight import FreightFacility,FREIGHT_FACILITY_START_SLOTS,freight_facility_expansion_cost,freight_stats
from production_zero.core.supply import common_card_price,uncommon_card_price
from production_zero.core.mk_upgrades import mk_upgrade_cost
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.data.definitions import load_card_definitions
D=load_card_definitions(ROOT/'src/production_zero/data/game_definitions.json');rows=[];text=['# P7: Infrastruktur- und Freight-Preistabelle','','Cash, Preisversion 1. Werte direkt aus dem produktiven Preispfad. Bereits gekaufte Investitionen bleiben historisch.','',
'| Bereich | Startplätze / eine Linie | Maximum | Zusatzslots je Linie | Weitere Linien | Vollausbau ohne Gebäude/Karten |','| --- | --- | --- | --- | --- | --- |']
for board,(maximum,cap,start) in BOARD_LIMITS.items():
    slots=[slot_price(board,1,k) for k in range(start+1,cap+1)];lines=[line_price(board,l) for l in range(2,maximum+1)]
    text.append(f"| {board} | {start} | {maximum} × {cap} | {', '.join(f'{x:,.0f}' for x in slots)} | {', '.join(f'{x:,.0f}' for x in lines)} | {sum(slots)*maximum+sum(lines):,.0f} |")
    for l in range(1,maximum+1):
        if l>1:rows.append(dict(category='production_line',kind=board,line=l,cash=line_price(board,l),capacity=start))
        for k in range(start+1,cap+1):rows.append(dict(category='production_slot',kind=board,line=l,slot=k,cash=slot_price(board,l,k),capacity=1))
    for n in range(10):rows.append(dict(category='production_facility',kind=board,existing_same_type=n,cash=facility_price(board,n),capacity=start))
text+=['','Für k zusätzliche Plätze: Factory 40k, Resources 90k, Energy 100k. Linienpreis B(l−1)² mit B=900/900/500. Bei historischen abweichenden Linienmaßen wird B aus genau deren Start- und Maximalplätzen abgeleitet: auf 100 aufrunden von (letzter Zusatzslot × Startplätze + 1). Bereits bezahlte Linien bleiben unverändert.','',
'| Bereits vorhandene Facilities | Factory | Resources je Spezialisierung | Energy |','| --- | --- | --- | --- |']
for n in range(10):text.append(f"| {n} | {facility_price('factory',n):,.0f} | {facility_price('resources',n):,.0f} | {facility_price('energy',n):,.0f} |")
text+=['','Bei n≥1: auf 100 aufrunden von C × n^2.5; C=15.200 / 4.000 / 2.200. Factory maximal zehn Gebäude; Resources zählt Mining/Agriculture/Drilling getrennt. Erste Facility ohne vorhandenen Typ 500, Factory/Energy ohne Bestand 1.000. Die gegebenen Startergebäude bleiben kostenlos. Typwechsel eines leeren Standorts zahlt den aktuellen Zieltyp-Neubaupreis ohne Gutschrift alter Ausbauinvestitionen.','',
'| Freight | Startslots | Grundpreis bei 0 Bestand | Kauf bei 1 Bestand | Kauf bei 2 Bestand | Erste Linie zusätzlich bis 8 |','| --- | --- | --- | --- | --- | --- |']
for kind,base in FREIGHT_BUILD_BASES.items():
    start=FREIGHT_FACILITY_START_SLOTS[kind];u=FreightFacility('quote','quote',kind,slot_count=start)
    extras=[freight_facility_expansion_cost(u,slot_index=i) for i in range(start,8)]
    text.append(f"| {kind} | {start} | {base:,.0f} | {base*4:,.0f} | {base*9:,.0f} | {', '.join(f'{x:,.0f}' for x in extras)} |")
    for n in range(10):rows.append(dict(category='freight_facility',kind=kind,existing_same_type=n,cash=base*(n+1)**2,capacity=start))
    for i in range(start,80):rows.append(dict(category='freight_expansion',kind=kind,line=i//8+1,slot=i%8+1,cash=freight_facility_expansion_cost(u,slot_index=i),capacity=1))
text+=['','Freight-Facility bei n gleichen Anlagen: Grundpreis × (n+1)². Die erste Garage wird beim Spielstart gestellt; die nächste Garage kostet deshalb 8.000. Alle Freight-Linien haben acht Positionen. Linien 2–10 kosten für ihren ersten Platz: 900, 3.600, 8.100, 14.400, 22.500, 32.400, 44.100, 57.600, 72.900. Allgemein Linie l: 900(l−1)². Weitere sieben Plätze jeder zusätzlichen Linie kosten 60, 120, 180, 240, 300, 360, 420. Eine neue Linie kann vor vollständigem Ausbau der vorherigen gekauft werden; Lücken bleiben gesperrt. Späte weitere Gebäude können bei sehr vielen Linien wieder günstiger sein.','',
'| Fahrzeug Common MK1 | Preis | Kapazität | Sekunden | Voll beladen Einheiten/min |','| --- | --- | --- | --- | --- |']
vehicles=[]
for did in ('freight.truck','freight.train','freight.aircraft','freight.ship'):
    d=D[did];card=create_card_instance('quote',did,d.card_kind,Rarity.COMMON);base=common_card_price(d);paid=base
    text.append(f"| {d.name} | {base:,.2f} | {d.base_capacity:,.0f} | {d.base_transport_time_seconds:g} | {d.base_capacity*60/d.base_transport_time_seconds:,.2f} |")
    for mk in range(1,100):
        c=replace(card,mk_level=mk);stats=freight_stats(c,d);upgrade=mk_upgrade_cost(c,d) if mk<99 else None
        rows.append(dict(category='freight_vehicle',kind=did,mk=mk,cash=base,capacity=stats.capacity,seconds=stats.transport_time_seconds,total_common_mk_investment=paid,next_mk_cash=upgrade))
        if upgrade:paid+=upgrade
    vehicles.append(dict(definition=did,common=base,capacity=d.base_capacity,seconds=d.base_transport_time_seconds,daily_example_bonus_tenths=160,daily_example_quote=uncommon_card_price(d,160)))
text+=['','Die CSV enthält alle vier Fahrzeuge für MK1–99: Common-Basispreis, kumulierte Common-MK-Investition, nächste Upgradequote und effektive Kapazität/Zeit ohne Research. Die bestehende MK-Formel M=1+0,25(MK−1) bleibt erhalten. Rarity wirkt über den individuellen Bonus; identische Rarity-Namen allein garantieren keinen identischen zufälligen Bonus. Für Aircraft/Ship bei gleichem MK, Bonus und Research beträgt die Vollauslastungsrelation 3×. Cent-Rundungen bei MK-Kosten bleiben bestehen. Daily-Uncommon-Preise hängen vom Bonus ab; Common, Daily, Templates und MK beziehen ihren Basiswert aus common_card_price.','',
'Common Ship: 14.955; Aircraft: 4.985. Ship MK1→2 kostet 15.000,01, Aircraft 5.000,00. Historische Käufe/Upgrades werden daraus nicht neu berechnet.','',
'[Vollständige tabellarische Werte inklusive aller Freight-MK-Stufen](industriova-03-phase7-price-table.csv).']
(ROOT/'docs/industriova-03-phase7-price-table.md').write_text('\n'.join(text)+'\n',encoding='utf8')
keys=['category','kind','existing_same_type','line','slot','mk','cash','capacity','seconds','total_common_mk_investment','next_mk_cash']
with (ROOT/'docs/industriova-03-phase7-price-table.csv').open('w',encoding='utf8',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)
(ROOT/'artifacts/phase7/live-price-table.json').write_text(json.dumps(dict(rows=rows,vehicles=vehicles),indent=2),encoding='utf8')
print(json.dumps(dict(rows=len(rows))),flush=True)
