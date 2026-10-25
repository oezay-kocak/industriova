"""Phase 0 only: reproducible local measurements; never opens personal saves.

Run with .venv/Scripts/python.exe scripts/phase0_benchmark.py ui|actions|economy.
All synthetic states and SQLite outputs live under artifacts/phase0.
"""
from __future__ import annotations
import os, sys, json, platform, statistics, time, cProfile, pstats, io, ctypes
from pathlib import Path
from dataclasses import replace
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
OUT = ROOT / 'artifacts/phase0'
OUT.mkdir(parents=True, exist_ok=True)
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['LOCALAPPDATA'] = str(OUT / 'benchmark-appdata')
os.environ['APPDATA'] = os.environ['LOCALAPPDATA']
from importlib.resources import files
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.commands import CommandBus
from production_zero.core.state import FactoryHall, HallSlot, MachineProductionState
from production_zero.ui.main_window import _create_initial_state
D = load_card_definitions(files('production_zero.data') / 'game_definitions.json')
R = load_resource_definitions(files('production_zero.data') / 'resource_definitions.json')
RESULT = {'environment': {'python': sys.version, 'platform': platform.platform(),
                         'processor': platform.processor(), 'qt_platform': 'offscreen',
                         'hashseed': os.environ.get('PYTHONHASHSEED'), 'resource_count': len(R)}, 'measurements': {}}

def save(name):
    (OUT / (name + '.json')).write_text(json.dumps(RESULT, indent=2), encoding='utf8')

def measure(label, action, n=7, events=False):
    values=[];callbacks=[];call_times=[];paint_counts=[]
    for _ in range(n):
        if 'app' in globals():
            from PySide6.QtCore import QTimer
            app.phase0_paints=0
            t=time.perf_counter()
            QTimer.singleShot(0,lambda start=t:callbacks.append((time.perf_counter()-start)*1000))
        else:t=time.perf_counter()
        action();call_times.append((time.perf_counter()-t)*1000)
        if events: app.processEvents()
        values.append((time.perf_counter()-t)*1000)
        if 'app' in globals():
            if not events:app.processEvents()
            paint_counts.append(getattr(app,'phase0_paints',0))
    row={'median_ms': statistics.median(values), 'max_ms':max(values), 'samples_ms':values,
         'includes_event_drain':events,'callback_samples_ms':call_times,
         'queued_event_delays_ms':callbacks,'paint_event_counts':paint_counts}
    RESULT['measurements'][label]=row
    print(label, round(row['median_ms'],3), flush=True)
    return row

def profile(label, action):
    p=cProfile.Profile();p.runcall(action);s=io.StringIO()
    pstats.Stats(p,stream=s).strip_dirs().sort_stats('cumtime').print_stats(35)
    (OUT/(label+'.profile.txt')).write_text(s.getvalue(),encoding='utf8')

def memory():
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong),
                  *[(name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage',
                  'QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]]
    c=Counters();c.cb=ctypes.sizeof(c)
    handle=ctypes.windll.kernel32.GetCurrentProcess
    handle.restype=ctypes.c_void_p
    fn=ctypes.windll.psapi.GetProcessMemoryInfo
    fn.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong]
    if not fn(handle(),ctypes.byref(c),c.cb): raise ctypes.WinError()
    return c.WorkingSetSize

def register_fonts(app, *, stylesheet=True):
    # The offscreen Qt backend does not discover Windows font families here.
    # Use the same explicit registration as existing project capture tools.
    from PySide6.QtGui import QFontDatabase,QFont
    loaded=[]
    for name in ('segoeui.ttf','segoeuib.ttf','bahnschrift.ttf','arial.ttf','agencyr.ttf'):
        p=Path('C:/Windows/Fonts')/name
        if p.exists():loaded.append({'font':name,'id':QFontDatabase.addApplicationFont(str(p))})
    app.setFont(QFont('Segoe UI',9))
    from production_zero.ui.theme import APP_STYLESHEET
    if stylesheet:app.setStyleSheet(APP_STYLESHEET)
    RESULT['environment']['registered_fonts']=loaded
    RESULT['environment']['application_stylesheet']=stylesheet

def state():
    s=_create_initial_state(R,D);s.cash.amount=1e18;return s

def board_fixture(count, *, selected_hall=False):
    s=state();s.cards.clear();s.halls.clear();s.resource_sites.clear();s.energy_plants.clear();s.machine_production.clear()
    # Production UI supports 50 per real hall. A 100/500 selection surface is a
    # synthetic controller stress fixture with extra lines, not a legal save.
    per_hall=count if selected_hall else 50
    for start in range(0,count,per_hall):
        n=min(per_hall,count-start);hid=f'bench-{start}'
        h=FactoryHall(hid,hid,n,max_lines=max(1,(n+9)//10),max_slots_per_line=10,
                      start_unlocked_lines=max(1,(n+9)//10),start_slots_per_line=10)
        s.halls[hid]=h
        for i in range(n):
            cid=f'card-{start+i}';s.cards[cid]=create_card_instance(cid,'machine.processor',CardKind.MACHINE,Rarity.COMMON)
            h.slots[i].card_id=cid
    return s

def ui():
    from PySide6.QtCore import Qt,QPoint,QPointF,QRect,QEvent
    from PySide6.QtGui import QPixmap,QMouseEvent
    from PySide6.QtWidgets import QWidget,QApplication,QRubberBand
    from production_zero.ui.unlock_tree_view import UnlockTreeView,build_unlock_tree_graph
    from production_zero.ui.factory_view_v2 import FactoryViewV2
    from production_zero.ui.contracts_view import ContractProductPicker
    from production_zero.ui.leaderboard_view import LeaderboardView
    from production_zero.services.local import LocalLeaderboardService
    from types import SimpleNamespace
    global app
    class MeasuredApplication(QApplication):
        def notify(self,receiver,event):
            if event.type()==QEvent.Type.Paint:self.phase0_paints=getattr(self,'phase0_paints',0)+1
            return super().notify(receiver,event)
    app=QApplication.instance() or MeasuredApplication([])
    register_fonts(app)
    def drain():
        for _ in range(3):app.processEvents();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    s=state();before=memory(); holder=[]
    measure('unlock.graph',lambda:build_unlock_tree_graph(D))
    measure('unlock.constructor.cold',lambda:holder.append(UnlockTreeView(s,D,lambda:None)),n=1)
    u=holder[-1];u.resize(1366,768)
    measure('unlock.first_show',u.show,n=1,events=True);drain()
    RESULT['unlock']={'nodes':len(u.graph.nodes),'edges':len(u.graph.edges),'scene_items':len(u.canvas.scene().items()),
                      'widgets':len(u.findChildren(QWidget)),'working_set_delta_bytes':memory()-before}
    measure('unlock.column_order',lambda:u._ordered_columns(u._visible_resources()))
    measure('unlock.refresh',u.refresh_state,events=True)
    measure('unlock.rebuild.warm',u._rebuild_scene,n=5,events=True)
    measure('unlock.render',lambda:u.render(QPixmap(u.size())))
    measure('unlock.zoom_pan',lambda:(u.canvas.zoom_by_steps(1),u.canvas.pan_by(QPointF(25,15))),events=True)
    profile('unlock-rebuild',u._rebuild_scene)
    drain()
    u.grab().save(str(OUT/'unlock-tree.png'));u.close();u.deleteLater();drain()
    b=FactoryViewV2(s,CommandBus(s),D);b.pause_simulation();b.resize(1366,768);b.show();drain()
    measure('guide.first_open',b._open_production_guide,n=1,events=True)
    RESULT['guide']={'widgets':len(b.findChildren(QWidget)), 'tiles_created':b._guide_tile_create_count}
    measure('guide.search',lambda:(b._on_guide_search_changed('steel'),b._on_guide_search_changed('')),events=True)
    measure('guide.filter',lambda:(b._on_guide_stage_filter_changed('Processing'),b._on_guide_stage_filter_changed('All')),events=True)
    measure('guide.render',lambda:b.render(QPixmap(b.size())))
    measure('guide.list_graph_roundtrip',lambda:(b._open_chain_from_guide('steel'),b._back_from_chain_inspector()),n=5,events=True)
    measure('guide.close_reopen',lambda:(b._close_drawer(),b._open_production_guide()),n=5,events=True)
    RESULT['guide'].update(tiles_created_after=b._guide_tile_create_count, builds=b._guide_view_build_count,
                           grid_rebuilds=b._guide_grid_rebuild_count)
    profile('guide-filter',lambda:b._on_guide_search_changed('iron'))
    b._on_guide_search_changed('');drain()
    b.grab().save(str(OUT/'production-guide.png'));b.close();b.deleteLater();drain()
    products=[SimpleNamespace(resource_id=rid,name=r.name) for rid,r in R.items()]
    holders=[]
    measure('leaderboard.picker_construct',lambda:holders.append(ContractProductPicker(products,R,set(),'Iron Ore',purpose_label='CUMULATIVE PRODUCTION')),n=3)
    picker=holders[-1];picker.resize(950,650)
    measure('leaderboard.picker_show',picker.show,n=1,events=True)
    RESULT['picker']={'products':len(picker.tiles),'widgets':len(picker.findChildren(QWidget))}
    measure('leaderboard.picker_filter',lambda:(picker.search.setText('iron'),picker.search.clear()),events=True)
    profile('leaderboard-picker',lambda:ContractProductPicker(products,R,set(),'Iron Ore',purpose_label='CUMULATIVE PRODUCTION'))
    for p in holders:p.close();p.deleteLater()
    drain()
    lb=LeaderboardView(LocalLeaderboardService(s));lb.resize(1366,768);lb.show();drain()
    measure('leaderboard.unchanged_refresh',lb.refresh,events=True)
    pinned=lb._production_own_layout.itemAt(0).widget();replaced=[]
    def changed():
        nonlocal pinned
        s.production_progress.lifetime_produced['iron_ore']=s.production_progress.lifetime_produced.get('iron_ore',0)+1
        lb.refresh();new=lb._production_own_layout.itemAt(0).widget();replaced.append(new is not pinned);pinned=new
    measure('leaderboard.changed_refresh',changed,events=True)
    RESULT['leaderboard']={'changed_refresh_replaces_pinned':replaced,'local_production_rows':1,'online_backend':False}
    lb.close();lb.deleteLater();drain()
    for count in (10,50,100,500):
        ss=board_fixture(count,selected_hall=True);bb=FactoryViewV2(ss,CommandBus(ss),D);bb.pause_simulation()
        bb.resize(1366,768);bb.show();drain();ids=tuple(ss.cards);surface=bb._release_selection_surface
        RESULT.setdefault('selection',[]).append({'cards':count,'slot_widgets':len(bb._slot_widgets),'widgets':len(bb.findChildren(QWidget)),
                                                  'synthetic_exceeds_legal_hall':count>50})
        measure(f'selection.{count}.shift',lambda:(bb._select_slot(0,Qt.KeyboardModifier.NoModifier),bb._select_slot(count-1,Qt.KeyboardModifier.ShiftModifier)),events=True)
        measure(f'selection.{count}.redraw',lambda:bb.render(QPixmap(bb.size())))
        measure(f'selection.{count}.group_pause',lambda:bb._command_bus.dispatch(__import__('production_zero.core.commands',fromlist=['PauseMachines']).PauseMachines(ids,True)))
        event=QMouseEvent(QEvent.Type.MouseMove,QPointF(20,20),QPointF(20,20),Qt.MouseButton.NoButton,Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier)
        measure(f'selection.{count}.1000_idle_filter',lambda:[bb.eventFilter(surface,event) for _ in range(1000)])
        def rectangle():
            bb._rubber_origin=QPoint(0,0);bb._rubber_band=QRubberBand(QRubberBand.Shape.Rectangle,surface)
            bb._rubber_band.setGeometry(QRect(QPoint(0,0),surface.size()))
            release=QMouseEvent(QEvent.Type.MouseButtonRelease,QPointF(20,20),QPointF(20,20),Qt.MouseButton.LeftButton,Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier)
            bb.eventFilter(surface,release)
        measure(f'selection.{count}.rectangle_release',rectangle,events=True)
        def move_rectangle():
            bb._rubber_origin=QPoint(0,0);bb._rubber_band=QRubberBand(QRubberBand.Shape.Rectangle,surface)
            for _ in range(100):bb.eventFilter(surface,event)
            bb._rubber_band.deleteLater();bb._rubber_origin=None
        measure(f'selection.{count}.100_rectangle_moves',move_rectangle,events=True)
        bb.close();bb.deleteLater();drain();save('ui-baseline')
    save('ui-baseline')

def actions():
    from PySide6.QtWidgets import QApplication
    from production_zero.core.commands import (BuyCommonSupplyCard,InstallCardInHall,RemoveCardFromHall,
        UpgradeMachines,SellMachines,ConfigureMachines,UnlockProductionSlot)
    from production_zero.core.machine_operations import buy_and_install
    from production_zero.core.production_templates import MachineTemplate,PurchaseTemplates,quote_templates
    from production_zero.persistence.session_writer import snapshot_game_state,encode_snapshot
    from production_zero.persistence.sqlite_store import SQLiteSaveStore
    from production_zero.ui.factory_view_v2 import FactoryViewV2
    global app
    app=QApplication.instance() or QApplication([])
    register_fonts(app)
    for count in (10,50,100,500):
        s=board_fixture(count);bus=CommandBus(s);cid=next(iter(s.cards));hid=next(iter(s.halls))
        # One new hall with 50 real compatible slots for each isolated burst.
        def prepare():
            s.halls['target']=FactoryHall('target','Target',50,max_lines=5,start_unlocked_lines=5,start_slots_per_line=10)
        def burst(use_bus):
            prepare()
            for _ in range(20):
                if use_bus:bus.dispatch(BuyCommonSupplyCard('machine.processor',D))
                else:buy_and_install(s,D['machine.processor'],1,__import__('production_zero.core.supply',fromlist=['common_card_price']).common_card_price(D['machine.processor']))
            ids=tuple(x.card_id for x in s.halls['target'].slots if x.card_id)
            SellMachines(ids,D).apply(s)
            del s.halls['target']
        measure(f'actions.{count}.20_buy_core_plus_cleanup',lambda:burst(False),n=5)
        measure(f'actions.{count}.20_buy_bus_plus_cleanup',lambda:burst(True),n=5)
        # Time purchase and sale independently; fixture setup is outside the clock.
        for action_name in ('purchase20','sale20'):
            samples=[]
            for _ in range(7):
                prepare()
                if action_name=='sale20':BuyCommonSupplyCard('machine.processor',D,20).apply(s)
                start=time.perf_counter()
                if action_name=='purchase20':bus.dispatch(BuyCommonSupplyCard('machine.processor',D,20))
                else:bus.dispatch(SellMachines(tuple(x.card_id for x in s.halls['target'].slots if x.card_id),D))
                samples.append((time.perf_counter()-start)*1000)
                ids=tuple(x.card_id for x in s.halls['target'].slots if x.card_id)
                if ids:SellMachines(ids,D).apply(s)
                del s.halls['target']
            RESULT['measurements'][f'actions.{count}.{action_name}']={'median_ms':statistics.median(samples),'max_ms':max(samples),'samples_ms':samples,'includes_event_drain':False}
        measure(f'actions.{count}.20_install_remove',lambda:[(bus.dispatch(RemoveCardFromHall(hid,0,'factory')),bus.dispatch(InstallCardInHall(hid,0,cid,'factory'))) for _ in range(20)],n=5)
        measure(f'actions.{count}.upgrade',lambda:bus.dispatch(UpgradeMachines((cid,),D)),n=7)
        option=D['machine.processor'].available_production_options[0]
        s.production_progress.unlocked_production_ids.add(option.production_id)
        measure(f'actions.{count}.20_recipe_assign',lambda:[bus.dispatch(ConfigureMachines((cid,),option.production_id,D)) for _ in range(20)],n=5)
        def slots():
            s.halls['slots']=FactoryHall('slots','Slots',6,max_lines=5)
            h=s.halls['slots']
            for line in h.production_lines[:2]:
                for _ in range(7):bus.dispatch(UnlockProductionSlot(h.hall_id,line.line_id,'factory'))
            del s.halls['slots']
        measure(f'actions.{count}.14_slot_unlocks',slots,n=5)
        def paste():
            prepare();templates=(MachineTemplate('machine.processor'),)*10;line=s.halls['target'].production_lines[0].line_id
            total=quote_templates(s,D,templates,'factory','target',line)[2]
            bus.dispatch(PurchaseTemplates(templates,'factory','target',line,D,total))
            ids=tuple(slot.card_id for slot in s.halls['target'].slots if slot.card_id)
            bus.dispatch(SellMachines(ids,D));del s.halls['target']
        measure(f'actions.{count}.paste10_and_sell',paste,n=5)
        b=FactoryViewV2(s,bus,D);b.pause_simulation();b.resize(1366,768);b.show();app.processEvents()
        measure(f'actions.{count}.ui_runtime',b.refresh_runtime,events=True)
        measure(f'actions.{count}.ui_structural',b.refresh_view,n=5,events=True)
        # Fixed 240 history values; no personal history or save is loaded.
        for series in s.history.series.values():series.values=[float(i) for i in range(240)]
        measure(f'actions.{count}.snapshot',lambda:snapshot_game_state(s))
        snap=snapshot_game_state(s)
        measure(f'actions.{count}.encoding',lambda:encode_snapshot(snap),n=3)
        payload=encode_snapshot(snap);store=SQLiteSaveStore(OUT/f'actions-{count}.sqlite');store.initialize()
        measure(f'actions.{count}.sqlite_commit',lambda:store.save_payload('company',payload),n=3)
        if count==500:
            from production_zero.persistence.session_writer import SessionWriter
            writer=SessionWriter(store)
            measure('actions.500.writer_submit',lambda:writer.submit(snap),n=3)
            measure('actions.500.writer_wait_drain',lambda:writer.poll(wait=True),n=1)
            writer.shutdown()
        RESULT.setdefault('fixtures',[]).append({'initial_cards':count,'final_cards':len(s.cards),'halls':len(s.halls),'history_samples':240,'payload_bytes':len(payload)})
        if count==500:profile('snapshot500',lambda:snapshot_game_state(s));profile('board-refresh500',b.refresh_view)
        b.close();b.deleteLater();app.processEvents();save('actions-baseline')
    save('actions-baseline')

def economy():
    from production_zero.core.economy import hall_purchase_price
    from production_zero.core.state import factory_slot_unlock_cost,factory_line_unlock_cost
    from production_zero.core.supply import common_card_price
    from production_zero.core.freight import FREIGHT_FACILITY_BUILD_BASE_COSTS,freight_stats
    from production_zero.core.definitions import FreightDefinition,MachineDefinition,EnergyDefinition
    from production_zero.core.market import BASE_MARKET_PRICES
    from production_zero.core.production_values import ProductionValueCalculator,contract_required_amount
    from production_zero.core.contracts import (contract_production_value_budgets,contract_capacity_estimate,
        generate_contract_offers,accept_contract,contract_requirements_for_products)
    from production_zero.core.company import xp_required_for_next_level
    from production_zero.ui.production_board_views import RESOURCES_BOARD_CONFIG,ENERGY_BOARD_CONFIG
    from production_zero.ui.factory_view import ProductionBoardConfig
    RESULT['buildings']=[]
    for config in (ProductionBoardConfig(),RESOURCES_BOARD_CONFIG,ENERGY_BOARD_CONFIG):
        line_costs=[factory_line_unlock_cost(l) for l in range(config.start_unlocked_lines+1,config.max_lines+1)]
        slot_costs=[[factory_slot_unlock_cost(l,k,start_slots_per_line=config.start_slots_per_line)
                     for k in range(config.start_slots_per_line+1,config.max_slots_per_line+1)] for l in range(1,config.max_lines+1)]
        RESULT['buildings'].append({'board':config.board_kind,'lines':config.max_lines,'slots_per_line':config.max_slots_per_line,
          'start_lines':config.start_unlocked_lines,'start_slots':config.start_slots_per_line,'line_costs':line_costs,'slot_costs':slot_costs,
          'full_expansion':sum(line_costs)+sum(map(sum,slot_costs)),'next_building':hall_purchase_price(1)})
    RESULT['freight']=[]
    for definition in {d.definition_id:d for d in D.values()}.values():
        if not isinstance(definition,FreightDefinition):continue
        c=create_card_instance('probe',definition.definition_id,CardKind.FREIGHT,Rarity.COMMON);stats=freight_stats(c,definition)
        price=common_card_price(definition);q=60*stats.capacity/stats.transport_time_seconds
        RESULT['freight'].append({'definition':definition.definition_id,'capacity':stats.capacity,'seconds':stats.transport_time_seconds,
            'per_minute':q,'price':price,'facility':FREIGHT_FACILITY_BUILD_BASE_COSTS[definition.facility_id],
            'cash_per_added_unit_minute':price/q,'ore_gross_payback_minutes':price/(q*BASE_MARKET_PRICES['iron_ore']),
            'mk_per_minute':{mk:q*(1+.25*(mk-1)) for mk in (1,2,10,50,99)}})
    RESULT['machine_examples']=[]
    for did in ('machine.processor','energy.solar_array'):
        d=D[did];row={'definition':did,'price':common_card_price(d),'mk':{}}
        for mk in (1,2,10,50,99):
            f=1+.25*(mk-1)
            if isinstance(d,MachineDefinition):
                opt=next(o for o in d.available_production_options if o.output_resource=='iron')
                q=opt.output_amount_for(d)*60/opt.cycle_seconds_for(d)*f
                inputs={rid:a*60/opt.cycle_seconds_for(d)*f for rid,a in opt.input_resources.items()}
                row['mk'][mk]={'units_per_minute':q,'power':opt.power_draw_for(d)*f,
                     'margin_per_minute_before_power_and_capital':q*BASE_MARKET_PRICES['iron']-sum(a*BASE_MARKET_PRICES[rid] for rid,a in inputs.items())}
            else:row['mk'][mk]={'power':d.base_power_output*f}
        RESULT['machine_examples'].append(row)
    calc=ProductionValueCalculator(D)
    producer={o.output_resource:(d,o) for d in {d.definition_id:d for d in D.values()}.values() if isinstance(d,MachineDefinition) for o in d.available_production_options}
    scenarios=[('early',1,1,1,('iron_ore','coal','copper_ore','limestone')),
               ('mid',25,10,2,('iron','steel','copper','steel_components')),
               ('end',100,99,5,('industrial_equipment','cargo_aircraft','high_speed_network_system','steel_components'))]
    RESULT['contracts']=[]
    # Analytic steady-state DAG sizing: a dedicated MK fleet per requested output,
    # recursively ceil producer counts, include full upstream chain and power.
    import math
    for name,level,mk,copies,products in scenarios:
        s=state();s.cards.clear();s.halls.clear();s.resource_sites.clear();s.energy_plants.clear();s.machine_production.clear();s.company.level=level
        s.production_progress.unlocked_production_ids.update(o.production_id for _,o in producer.values())
        for rid in products:
            d,o=producer[rid];h=FactoryHall(rid,rid,copies,board_kind='factory');s.halls[rid]=h
            s.resources[rid].amount=1
            for i in range(copies):
                cid=f'{rid}-{i}';s.cards[cid]=replace(create_card_instance(cid,d.definition_id,d.card_kind,Rarity.COMMON),mk_level=mk)
                h.slots[i].card_id=cid;s.machine_production[cid]=MachineProductionState(cid,rid,o.production_id)
        estimate=contract_capacity_estimate(s,D)
        for kind in ('daily','weekly'):
            offer=generate_contract_offers(303,kind,1,state=s,definitions=D)[0]
            selected=products[:3 if kind=='daily' else 4]
            req=contract_requirements_for_products(s,offer,D,selected)
            offer=replace(offer,requirements={});s.contracts.offers[kind]=[offer]
            # Acceptance refresh uses current periods. Set persisted period state first.
            from production_zero.core.contracts import refresh_contracts
            refresh_contracts(s,D);s.contracts.offers[kind]=[offer]
            accept_contract(s,kind,offer.contract_id,D,selected_resource_ids=selected)
            accepted=s.contracts.active[kind].offer
            times={rid:a/(producer[rid][1].output_amount_for(producer[rid][0])*60/producer[rid][1].cycle_seconds_for(producer[rid][0])*(1+.25*(mk-1))*copies) for rid,a in req.items()}
            duration=max(times.values());demands={rid:a/duration for rid,a in req.items()}
            # Accumulate needs in reverse topological order, so shared inputs sum.
            needs=dict(demands);counts={};power=0.;capital=0.
            depth=lambda rid:calc.value_for_resource(rid).depth
            for rid in sorted(producer,key=depth,reverse=True):
                rate=needs.get(rid,0)
                if rate<=0:continue
                d,o=producer[rid];f=1+.25*(mk-1);q=o.output_amount_for(d)*60/o.cycle_seconds_for(d)*f
                n=math.ceil(rate/q-1e-10);counts[rid]=n;capital+=n*common_card_price(d)
                power+=n*o.power_draw_for(d)*f
                # Full fleet utilization would overproduce; required average input
                # rates use requested output, while power conservatively sizes all machines.
                for input_id,a in o.input_resources.items():needs[input_id]=needs.get(input_id,0)+rate*a/o.output_amount_for(d)
            freight=RESULT['freight'][0]
            freight_did={'early':'freight.truck','mid':'freight.train','end':'freight.aircraft'}[name]
            fr=next(x for x in RESULT['freight'] if x['definition']==freight_did)
            trip_count=sum(math.ceil(a/(fr['capacity']*(1+.25*(mk-1)))) for a in req.values())
            freight_minutes=trip_count*fr['seconds']/60
            RESULT['contracts'].append({'scenario':name,'level':level,'mk':mk,'copies_per_selected_product':copies,'kind':kind,
              'capacity_estimate_pv_min':estimate.effective_pv_per_minute,'budget':offer.production_value_budget,
              'requirements':req,'fixed_value':sum(a*BASE_MARKET_PRICES[rid] for rid,a in req.items()),
              'accepted_cash':accepted.reward_cash,'accepted_xp':accepted.reward_xp,'rp':1 if kind=='daily' else 3,
              'next_level_xp':xp_required_for_next_level(level),'parallel_output_minutes':duration,
              'one_vehicle_serial_minutes':freight_minutes,'conservative_sequential_minutes':duration+freight_minutes,
              'freight_type':freight_did,'upstream_machine_counts':counts,'steady_chain_power_mw':power,
              'base_machine_purchase_capital_excludes_mk_buildings_energy_freight':capital,
              'solar_count_at_same_mk':math.ceil(power/(D['energy.solar_array'].base_power_output*(1+.25*(mk-1))))})
    save('economy-model')

if __name__=='__main__':
    {'ui':ui,'actions':actions,'economy':economy}[sys.argv[1]]()
