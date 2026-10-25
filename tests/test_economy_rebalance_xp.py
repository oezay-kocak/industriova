from importlib.resources import files
from dataclasses import replace
import pytest
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.state import GameState, FactoryHall, MachineProductionState
from production_zero.core.simulation import SimulationEngine
from production_zero.core.progression import initialize_production_progress
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state

DEFS=load_card_definitions(files('production_zero.data')/'game_definitions.json')

def firm():
    s=GameState(351);s.warehouse_capacity=1e8
    d=DEFS['machine.processor'];o=next(o for o in d.available_production_options if o.output_resource=='flour')
    for rid in o.input_resources:s.ensure_resource(rid).amount=1e6
    for cid,did,board in (('p','machine.processor',s.halls),('e','energy.solar_array',s.energy_plants)):
        card=create_card_instance(cid,did,DEFS[did].card_kind,Rarity.COMMON)
        s.cards[cid]=card;hall=FactoryHall(cid,cid,3);hall.slots[0].card_id=cid;board[cid]=hall
    s.machine_production['p']=MachineProductionState('p','flour',o.production_id)
    s.production_progress.lifetime_produced['wheat']=120
    s.production_progress.first_produced_resource_ids.add('wheat')
    initialize_production_progress(s,DEFS)
    return s

def run(dt, *, reload=False, speed=False, paused=False, power=True, supplied=True, horizon=7200, start=1792756800):
    s=firm()
    if speed:
        from production_zero.core.research import research_catalog
        s.research.unlocked_node_ids=set(research_catalog()[1])
    if paused:s.cards['p']=replace(s.cards['p'],paused=True)
    if not power:s.energy_plants.clear()
    if not supplied:s.ensure_resource('wheat').amount=0
    clock=[0.];engine=SimulationEngine(DEFS,utc_now=lambda:start+clock[0])
    outputs={};inputs={}
    while clock[0]<horizon-1e-7:
        step=min(dt,horizon-clock[0]);clock[0]+=step;t=engine.advance_time(s,step)
        for rid,q in t.outputs.items():outputs[rid]=outputs.get(rid,0)+q
        for rid,q in t.inputs.items():inputs[rid]=inputs.get(rid,0)+q
        if reload and abs(clock[0]-horizon/2)<1e-6:s=deserialize_game_state(serialize_game_state(s))
    return dict(outputs=outputs,inputs=inputs,stocks={r:v.amount for r,v in s.resources.items() if v.amount},cash=s.cash.amount,productive_seconds=s.company_xp_progress.productive_event_seconds,xp=s.company_xp_progress.xp_by_source,level=s.company.level,current_xp=s.company.current_xp,unlocks=sorted(s.production_progress.unlocked_production_ids))

@pytest.mark.parametrize('dt',(2,3,6,30,60,300,7200))
def test_accepted_work_has_same_xp_at_every_tick_size(dt):
    assert run(dt)==run(1)

@pytest.mark.parametrize('dt',(1,2,3,6,60))
def test_save_load_preserves_productive_event_watermark(dt):
    assert run(dt,reload=True)==run(dt)

@pytest.mark.parametrize('setting',('paused','power','supplied'))
def test_unproductive_time_never_grants_production_xp(setting):
    kwargs={setting:False} if setting!='paused' else {setting:True}
    result=run(300,**kwargs,horizon=600)
    assert not result['xp'] and result['productive_seconds']==0

def test_fractional_ticks_do_not_multiply_completion_continuity():
    a=run(.25,horizon=600);b=run(1,horizon=600)
    assert a==b

@pytest.mark.parametrize('dt',(2,3,6,60,600))
def test_research_speed_events_preserve_continuity_and_work(dt):
    a=run(dt,speed=True,horizon=3600);b=run(1,speed=True,horizon=3600)
    assert a['outputs']==pytest.approx(b['outputs'])
    assert a['inputs']==pytest.approx(b['inputs'])
    assert a['productive_seconds']==b['productive_seconds']
    assert a['xp']==pytest.approx(b['xp'])
    assert a['level']==b['level'] and a['unlocks']==b['unlocks']

@pytest.mark.parametrize('dt',(2,3,6,60,600))
def test_offline_catchup_assigns_events_to_the_correct_utc_day(dt):
    assert run(dt,horizon=600,start=1792799980)==run(1,horizon=600,start=1792799980)

def test_zero_time_pause_resume_cannot_replay_an_xp_event():
    s=firm();engine=SimulationEngine(DEFS,utc_now=lambda:1792756800)
    engine.advance_time(s,6)
    before=dict(s.company_xp_progress.xp_by_source)
    seconds=s.company_xp_progress.productive_event_seconds
    for _ in range(100):
        s.cards['p']=replace(s.cards['p'],paused=True);engine.advance_time(s,0)
        s.cards['p']=replace(s.cards['p'],paused=False);engine.advance_time(s,0)
    assert s.company_xp_progress.xp_by_source==before
    assert s.company_xp_progress.productive_event_seconds==seconds
