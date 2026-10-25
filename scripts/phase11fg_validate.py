"""Reproducible productive-engine companies and bounded economic comparisons."""
from pathlib import Path
import sys,json,math,csv
from collections import Counter
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'artifacts/phase11e'))
import common as c
import validate as previous
from phase11fg_mk import tables,write,fund_buffer
from production_zero.core.simulation import SimulationEngine
from production_zero.core.freight import FreightAssignment
from production_zero.core.research import research_catalog
from production_zero.core.modifiers import research_multiplier
from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state
from phase8_offline_work_cache import install
OUT=ROOT/'artifacts/phase11fg'
SAMPLES=('iron','copper','flour','lumber','steel','bitumen','silicon','biodiesel','industrial_equipment','microchip','ai_server')

def prepare():
    c.extend_curves();install(c.d.D);c.install_offline_catalog_cache()
    return tables()[:2]

def plan(r,mk,up,n=1):
    return c.choose([fund_buffer(p) for p in c.structure('N1',r,c.counts_for(c.N1,r,n),mk)],up)

def simulate(label,p,price,budget=None,dt=1,horizon=7200,reload_at=None,research=False):
    definitions=c.DEFS['N1'];budget=budget or max(1250,math.ceil(p['cost']*1.1));level=p.get('level',25);s,assignments=previous.state(p,definitions,budget,level)
    speed=1.
    if research:
        s.research.unlocked_node_ids={k for k,n in research_catalog()[1].items() if n.effect_type=='production_speed'}
        s.research.total_earned=len(s.research.unlocked_node_ids)
        speed=research_multiplier(s.research,'production_speed')
        assert math.isclose(speed,1.08)
        # MK22 production * 1.08 = MK24 freight, exact even on surplus routes.
        assert p['mk']==22
        for cid,card in tuple(s.cards.items()):
            if card.definition_id.startswith('freight.'):
                s.cards[cid]=replace(card,mk_level=24)
        extra=sum(n*(UP[did,24]-UP[did,22]) for did,n in p['freight_groups'].items())
        s.cash.spend(extra);p=dict(p,cost=p['cost']+extra)
    clock=[0.];engine=SimulationEngine(definitions,utc_now=lambda:1792756800+clock[0])
    warmup=300;statuses=Counter();gross=Counter();consumed=Counter();tail=Counter();arrivals=Counter();rows=[];cash3600=0.;maxstorage=0.;lastseq=-1
    for second in range(dt,horizon+1,dt):
        clock[0]=second
        if second==warmup:
            for cid,r in assignments:s.freight.assignments[cid]=FreightAssignment(r,'market')
        t=engine.advance_time(s,dt);gross.update(t.outputs);consumed.update(t.inputs);maxstorage=max(maxstorage,s.used_storage)
        if second>horizon/2:
            statuses.update(x.status for x in s.machine_production.values());tail.update(t.outputs)
        for event in s.freight.completed_market_deliveries:
            if event.delivery_id>lastseq:arrivals[event.resource_id]+=event.market_amount
        assert s.freight.next_market_delivery_sequence-lastseq-1<=512,'Arrival trace exceeded deque retention'
        lastseq=s.freight.next_market_delivery_sequence-1
        if second==horizon/2:cash3600=s.statistics.total_earnings
        if reload_at and second==reload_at:
            s=deserialize_game_state(serialize_game_state(s))
            # Recent UI delivery IDs intentionally restart on load; accounting
            # statistics and frozen outbound shipments are persisted separately.
            lastseq=-1
    nominal=c.income(p,price)*speed
    real=(s.statistics.total_earnings-cash3600)/(horizon/120)
    ratios={r:tail[r]/(n*c.N1.recipes[r]['output']*c.upgrades.mk_factor(p['mk'])*speed*(horizon/2)/6) for r,n in p['counts'].items()}
    result=dict(label=label,product_id=p['product_id'],mk=p['mk'],dt=dt,seconds=horizon,budget=budget,level_start=level,investment=p['cost'],cash=s.cash.amount,earnings=s.statistics.total_earnings,tail_cash_min=real,nominal_cash_min=nominal,cash_ratio=real/nominal,production_ratios=json.dumps(ratios),tail_status=json.dumps(dict(statuses)),gross=json.dumps(dict(gross)),consumption=json.dumps(dict(consumed)),stocks=json.dumps({r:stock.amount for r,stock in s.resources.items() if stock.amount}),arrivals=json.dumps(dict(arrivals)),productive_seconds=s.company_xp_progress.productive_event_seconds,xp_by_source=json.dumps(s.company_xp_progress.xp_by_source,sort_keys=True),xp=sum(s.company_xp_progress.xp_by_source.values()),company_level=s.company.level,unlocks=json.dumps(sorted(s.production_progress.unlocked_production_ids)),storage_max=maxstorage,storage_capacity=s.storage_capacity,production_cards=sum(p['counts'].values()),factory_cards=p['factory_cards'],power=p['power'],research_speed=speed,paused_cards=sum(card.paused for card in s.cards.values()))
    return result

def chains():
    rows=[];plans=[]
    for r in SAMPLES:
        for mk in ((1,50,75,90,99) if r in ('iron','flour','steel','ai_server') else (1,)):
            p=plan(r,mk,UP);row=simulate('productive',p,PRICE,dt=1);rows.append(row);plans.append(p)
            write('engine-validation.csv',rows)
            assert all(abs(x-1)<1e-8 for x in json.loads(row['production_ratios']).values()),row
            assert row['cash_ratio']>=.995 and all(json.loads(row['tail_status']).get(k,0)==0 for k in ('missing_input','no_power','storage_full')),row
            print('chain',r,mk,'cash ratio',row['cash_ratio'],flush=True)
    for r in ('flour','steel','ai_server'):
        p=plan(r,22,UP);row=simulate('research',p,PRICE,budget=math.ceil(p['cost']*2),research=True)
        rows.append(row);write('engine-validation.csv',rows)
        assert min(json.loads(row['production_ratios']).values())>.995 and row['cash_ratio']>.99,row
        assert all(json.loads(row['tail_status']).get(k,0)==0 for k in ('missing_input','no_power','storage_full')),row
        print('research chain',r,row['cash_ratio'],flush=True)
    (OUT/'engine-plans.json').write_text(json.dumps(plans,indent=2),encoding='utf-8')

def xp():
    rows=[]
    for r in ('flour','steel','ai_server'):
        p=plan(r,1,UP)
        for dt in (1,2,3,6,30,60):
            row=simulate('xp',p,PRICE,dt=dt,reload_at=3600);rows.append(row);write('xp-comparison.csv',rows)
            if dt==1:reference=row
            else:
                for key in ('gross','consumption','stocks','arrivals','productive_seconds','xp_by_source','xp','company_level','unlocks','cash','earnings'):
                    a,b=row[key],reference[key]
                    if key in ('gross','consumption','stocks','arrivals','xp_by_source','unlocks'):a,b=json.loads(a),json.loads(b)
                    assert a==b,(r,dt,key,a,b)
            print('xp',r,dt,row['xp'],row['earnings'],flush=True)

def progression():
    profiles=[p for p in c.load('profiles.json') if p['model']=='N1']
    # Add missing high-MK choices to the existing funded whole-company search.
    seeds={(p['product_id'],tuple(sorted(p['counts'].items()))):p for p in profiles if p['mk']==99}
    for p in seeds.values():
        for mk in (75,90):profiles.extend(c.structure('N1',p['product_id'],p['counts'],mk))
    profiles=[fund_buffer(p) for p in profiles]
    values=[]
    for p in profiles:
        cost=c.cost(p,UP);income=c.income(p,PRICE);level=max(int(c.d.META[x]['company_level']) for x in p['counts'])
        values.append((p,cost,income,level))
    rows=[];winners=[]
    for budget in (1250,10000,50000,100000,500000,1000000,10000000,100000000,1000000000,10000000000,1000000000000):
        for level in (1,5,25):
            feasible=[x for x in values if x[1]<=budget and x[3]<=level]
            best=max(feasible,key=lambda x:x[2]);domains={}
            for item in feasible:
                domain=c.DOMAIN[item[0]['product_id']]
                if domain not in domains or item[2]>domains[domain][2]:domains[domain]=item
            for domain,(p,cost,income,needed) in domains.items():
                rows.append(dict(budget=budget,level=level,domain=domain,product_id=p['product_id'],mk=p['mk'],investment=cost,cash_min=income,best_cash_min=best[2],fraction_of_best=income/best[2],factory_cards=p['factory_cards'],production_cards=sum(p['counts'].values()),power=p['power'],scope='bounded funded comparison; earned prerequisites; no career claim; factory search bound 4096 is not a game cap'))
            if level==(1 if budget==1250 else 5 if budget<=1000000 else 25):
                p,cost,income,_=best;winners.append(dict(p,cost=cost,budget=budget,level=level))
            print('progression',budget,level,best[0]['product_id'],best[0]['mk'],flush=True)
    write('progression-comparison.csv',rows)
    (OUT/'progression-plans.json').write_text(json.dumps(winners,indent=2),encoding='utf-8')
    engine=[]
    for p in winners:
        row=simulate('budget',p,PRICE,budget=p['budget'],dt=6);engine.append(row);write('progression-engine.csv',engine)
        assert row['cash_ratio']>.99 and min(json.loads(row['production_ratios']).values())>.99,row
        print('budget engine',p['budget'],row['production_cards'],row['cash_ratio'],flush=True)

def progression_low_level():
    # Recheck the six low-level cohorts without repeating five unchanged,
    # already measured level-25 endgame companies (up to 7,024 machines).
    plans=json.loads((OUT/'progression-plans.json').read_text())
    with (OUT/'progression-engine.csv').open(encoding='utf-8-sig') as f:existing=list(csv.DictReader(f))
    rows=[]
    for p in plans:
        if p['level']<25:
            row=simulate('budget',p,PRICE,budget=p['budget'],dt=6)
            assert row['cash_ratio']>.99 and min(json.loads(row['production_ratios']).values())>.99
            print('earned level cohort',p['budget'],p['level'],row['company_level'],flush=True)
        else:
            row=next(x for x in existing if float(x['budget'])==p['budget'])
            assert int(row['company_level'])>=25 and math.isclose(float(row['investment']),p['cost'])
            row=dict(row,level_start=25)
        rows.append(row)
    # Preserve the prior declared-mature run as separate diagnostic evidence.
    (OUT/'progression-engine-mature-diagnostic.csv').write_bytes((OUT/'progression-engine.csv').read_bytes())
    write('progression-engine.csv',rows)

if __name__=='__main__':
    PRICE,TABLES=prepare();UP=TABLES['new']
    {'chains':chains,'xp':xp,'progression':progression,'progression-low-level':progression_low_level}[sys.argv[1]]()
