"""Serial, matched 353-product / 500-card contract and UI measurements."""
import argparse,sys,os,json,runpy,statistics,time,platform
from pathlib import Path
from dataclasses import replace
root=Path.cwd()
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=root);p.add_argument('--stage',required=True);args=p.parse_args()
out=root/'artifacts/phase9/performance'/args.stage;out.mkdir(parents=True,exist_ok=True)
os.environ.update(PHASE8_FORCE_CLOCK='1',QT_QPA_PLATFORM='offscreen',QT_SCALE_FACTOR='1',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
sys.argv=['fixture','--source',str(args.source),'--stage','../phase9/'+args.stage]
f=runpy.run_path(str(root/'scripts/phase8_contract_simulation.py'),run_name='fixture')
D=f['D'];company=f['company'];GOODS=f['PRODUCTS']['late'];NOW=f['NOW']
from production_zero.core.state import FactoryHall,MachineProductionState
from production_zero.core.contracts import generate_contract_offers,initialize_contracts,contract_requirements_for_products,accept_contract,receive_contract_delivery,ActiveContract,ContractOffer
from production_zero.core.consortium import ConsortiumService,ConsortiumMember
from production_zero.core.commands import CommandBus
from production_zero.core.freight import OutboundFreightShipment
from production_zero.core.simulation import SimulationEngine
import inspect,production_zero.core.company_xp as company_xp_module
assert inspect.isclass(company_xp_module.ProductionValueCalculator),'Offline simulation helper must be absent from performance measurements'
from production_zero.core.progression import production_options
from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state,SQLiteSaveStore
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.consortium_view import ConsortiumView
from production_zero.data.definitions import load_resource_definitions
from PySide6.QtWidgets import QApplication,QTabWidget
from PySide6.QtCore import QEvent
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
app=QApplication([]);_load_qa_fonts()
s,info=company('late',10)
# Same 500 concrete cards, placements and selected productions in both versions.
extra=500-len(s.cards);sample=next(cid for cid,c in s.cards.items() if c.definition_id=='machine.processor')
hall=FactoryHall('stress','Stress',extra,max_lines=1,max_slots_per_line=extra,start_unlocked_lines=1,start_slots_per_line=extra)
s.halls['stress']=hall
for i in range(extra):
    cid=f'extra-{i}';s.cards[cid]=replace(s.cards[sample],card_id=cid)
    s.machine_production[cid]=replace(s.machine_production[sample],card_id=cid)
    hall.slots[i].card_id=cid
for option in production_options(D):
    s.ensure_resource(option.output_resource).amount=.001
    s.production_progress.unlocked_production_ids.add(option.production_id)
initialize_contracts(s,D,now_utc=NOW)
offer=s.contracts.offers['daily'][0]
selected=GOODS[:3]
results={}
def measure(name,fn,count=7):
    samples=[]
    for i in range(count):
        begin=time.perf_counter_ns();fn(i);samples.append((time.perf_counter_ns()-begin)/1e6)
    results[name]=dict(samples_ms=samples,median_ms=statistics.median(samples),max_ms=max(samples))
measure('generation.warm',lambda i:generate_contract_offers(s.rng_seed,'daily',i,state=s,definitions=D))
def cold(i):
    if hasattr(s.contracts,'_capacity_signature'):s.contracts._capacity_signature=''
    generate_contract_offers(s.rng_seed,'daily',i,state=s,definitions=D)
measure('generation.capacity_change',cold)
measure('quote.selection',lambda i:contract_requirements_for_products(s,offer,D,selected))
payload=serialize_game_state(s)
copies=[deserialize_game_state(payload) for _ in range(7)]
measure('accept',lambda i:accept_contract(copies[i],'daily',offer.contract_id,D,selected_resource_ids=selected))
def complete(i):
    active=copies[i].contracts.active['daily']
    for rid,qty in active.offer.requirements.items():receive_contract_delivery(copies[i],active.offer.contract_id,rid,qty,D)
measure('complete',complete)
tick_states=[deserialize_game_state(payload) for _ in range(7)]
measure('tick.first',lambda i:SimulationEngine(D,utc_now=lambda:NOW).advance_time(tick_states[i],6))
for state in tick_states:
    for _ in range(10):SimulationEngine(D,utc_now=lambda:NOW).advance_time(state,6)
measure('tick.warm',lambda i:SimulationEngine(D,utc_now=lambda:NOW).advance_time(tick_states[i],6))
stress=[deserialize_game_state(payload) for _ in range(7)]
ships=[]
for state in stress:
    state.contracts.active['daily']=ActiveContract(ContractOffer('batch','daily','Batch',{'iron_ore':250},250,50,0))
    ships.append([OutboundFreightShipment(f'ship-{i}','contract',target_id='batch',resource_id='iron_ore',quantity=1,active=False,freight_card_id=f'car-{i}',source_facility_id='garage') for i in range(500)])
engine=SimulationEngine(D,utc_now=lambda:NOW)
measure('complete.500_arrivals',lambda i:engine._complete_outbound_shipments(stress[i],ships[i]))
assert all(state.cash.amount==500 for state in stress)
api=ConsortiumService(s,D,clock=lambda:NOW);guild=api.create('Benchmark Cooperative')
for i in range(1,10):guild.members[str(i)]=ConsortiumMember(str(i),str(i),100)
if hasattr(api,'update_capacity_snapshot'):
    for i in range(1,10):
        remote=deserialize_game_state(payload);remote.consortium.current_company_id=str(i)
        api.update_capacity_snapshot(str(i),remote)
else:
    for m in guild.members.values():m.capable_resource_ids=tuple(o.output_resource for o in production_options(D))
# Identical synthetic economic-arrival stress, with the retained history full.
from production_zero.core.consortium import ConsortiumContract,ConsortiumPersonalReward
arrival_states=[];arrival_batches=[]
for i in range(7):
    state=deserialize_game_state(serialize_game_state(s));group=state.consortium.consortiums[guild.consortium_id]
    group.contracts['daily']=ConsortiumContract('arrival-stress','daily','active',NOW,NOW+86400,{'iron_ore':1000},ConsortiumPersonalReward(1,1),1)
    group.contract_history=[ConsortiumContract('history-'+str(j),'daily','completed',NOW-100,NOW-1,{'iron_ore':1},ConsortiumPersonalReward(),0) for j in range(40)]
    arrival_states.append(state)
    arrival_batches.append([OutboundFreightShipment('conso-arrival-'+str(j),'consortium',target_id=guild.consortium_id+'|daily|arrival-stress',resource_id='iron_ore',quantity=1,active=False,freight_card_id='synthetic-arrival-'+str(j),source_facility_id='garage') for j in range(500)])
measure('consortium.500_arrivals_40_history',lambda i:engine._complete_outbound_shipments(arrival_states[i],arrival_batches[i]))
assert all(state.consortium.consortiums[guild.consortium_id].contracts['daily'].delivered=={'iron_ore':500} for state in arrival_states)
measure('consortium.candidates.10_members',lambda i:api.contract_candidates(guild.consortium_id,'daily'))
measure('consortium.preview.10_members',lambda i:(api.preview_contract(guild.consortium_id,'daily',selected),api.preview_contract_rewards(guild.consortium_id,'daily')))
R=load_resource_definitions(args.source/'src/production_zero/data/resource_definitions.json')
tabs=QTabWidget();view=ContractsView(s,CommandBus(s),D,R);group_view=ConsortiumView(s,D,R)
tabs.addTab(view,'Contracts');tabs.addTab(group_view,'Consortium');tabs.resize(1600,980);tabs.show()
def drain():
    app.processEvents();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
drain();view.refresh();group_view.refresh();drain()
measure('ui.contracts.unchanged',lambda i:view.refresh())
measure('ui.consortium.unchanged',lambda i:group_view.refresh())
def burst(i):
    for j in range(20):
        tabs.setCurrentIndex(j%2)
        (view if j%2==0 else group_view).refresh()
        drain()
measure('ui.20_tab_switches',burst)
measure('snapshot',lambda i:serialize_game_state(s))
detached=serialize_game_state(s)
measure('json_encoding',lambda i:json.dumps(detached))
store=SQLiteSaveStore(out/'benchmark.sqlite');store.initialize()
measure('save',lambda i:store.save('company',s))
measure('load',lambda i:store.load('company'))
tabs.close();drain()
report=dict(source=str(args.source.resolve()),python=platform.python_version(),catalog_products=len(production_options(D)),cards=len(s.cards),members=len(guild.members),payload_bytes=len(json.dumps(detached).encode()),metadata=info,results=results,assumptions='Qt offscreen 100%, same fonts and fixture. 500-card stress uses a deliberately oversized synthetic Hall; 353 existing unlocked products with tiny eligibility stock. Seven serial raw samples per operation, no parallel tests/hash/simulation jobs. Cold generation forces capacity invalidation; warm generation reuses lasting state. UI uses actual ContractsView/ConsortiumView with paint/event drain, not human response or native FPS.')
(out/'results.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:{m:round(v,4) for m,v in r.items() if m!='samples_ms'} for k,r in results.items()},indent=2),flush=True)
