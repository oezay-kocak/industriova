"""Identical freight fixtures against a selected source tree, no personal saves."""
import argparse, json, os, sys, time, statistics, ctypes, hashlib
from pathlib import Path
from datetime import datetime,timezone
parser=argparse.ArgumentParser();parser.add_argument('stage');parser.add_argument('--source',type=Path,default=Path.cwd());args=parser.parse_args()
ROOT=Path.cwd();OUT=ROOT/'artifacts/phase6'/args.stage;OUT.mkdir(parents=True,exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(OUT/'appdata'),APPDATA=str(OUT/'appdata'))
sys.path.insert(0,str(args.source.resolve()/'src'))
from PySide6.QtWidgets import QApplication,QWidget
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import QEvent
from production_zero.core.state import GameState
from production_zero.core.freight import FreightFacility,FreightAssignment,start_outbound_shipment_for_card
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.commands import CommandBus,BuildFreightFacility,ExpandFreightFacility,InstallFreightCard,BuyCommonSupplyCard
from production_zero.core.simulation import SimulationEngine
from production_zero.data.definitions import load_card_definitions,load_resource_definitions
from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state,SQLiteSaveStore
from production_zero.ui.freight_view import FreightView
app=QApplication([])
for name in ('segoeui.ttf','segoeuib.ttf','bahnschrift.ttf','arial.ttf','agencyr.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
D=load_card_definitions(args.source/'src/production_zero/data/game_definitions.json')
R=load_resource_definitions(args.source/'src/production_zero/data/resource_definitions.json')
records={}
def memory():
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong),*[(name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaNonPagedPoolUsage','PeakPagefileUsage','PagefileUsage','PrivateUsage')]]
    # GetProcessMemoryInfo's first fields through WorkingSetSize are sufficient.
    c=Counters();c.cb=ctypes.sizeof(c);fn=ctypes.windll.kernel32.GetCurrentProcess;fn.restype=ctypes.c_void_p
    query=ctypes.windll.psapi.GetProcessMemoryInfo;query.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong]
    assert query(fn(),ctypes.byref(c),c.cb)
    return c.WorkingSetSize
def measure(action,events=False):
    samples=[]
    for _ in range(7):
        t=time.perf_counter();action();callback=(time.perf_counter()-t)*1000
        if events:app.processEvents()
        samples.append(dict(callback_ms=callback,total_ms=(time.perf_counter()-t)*1000))
    return dict(samples=samples,median_ms=statistics.median(r['total_ms'] for r in samples),max_ms=max(r['total_ms'] for r in samples))
for count in (10,50,100,500,'20-facilities'):
    s=GameState(197);s.cash.amount=1e15;bus=CommandBus(s)
    if count=='20-facilities':
        for _ in range(19):bus.dispatch(BuildFreightFacility('garage_depot'))
        bus.dispatch(BuyCommonSupplyCard('freight.truck',D,quantity=160))
        owned=iter(s.cards)
        for unit in s.freight.facilities.values():
            for _ in range(5):bus.dispatch(ExpandFreightFacility(unit.facility_id))
            for slot in unit.slots:bus.dispatch(InstallFreightCard(unit.facility_id,slot.index,next(owned),D))
    else:
        unit=FreightFacility('bench','Freight Statistics Stress',slot_count=count);s.freight.facilities={unit.facility_id:unit}
        for i,slot in enumerate(unit.slots):
            cid=f'bench-{i}';s.cards[cid]=create_card_instance(cid,'freight.truck',D['freight.truck'].card_kind,Rarity.COMMON);slot.card_id=cid
    owners=[(slot.card_id,unit.facility_id) for unit in s.freight.facilities.values() for slot in unit.slots]
    # Same loaded company's resources, routes and active shipments in both versions.
    s.ensure_resource('iron_ore').amount=1e9
    for cid,_fid in owners:s.freight.assignments[cid]=FreightAssignment('iron_ore','market')
    engine=SimulationEngine(D,utc_now=lambda:datetime(2026,10,22,12,tzinfo=timezone.utc))
    for _ in range(10):engine.advance_time(s,60)
    view=FreightView(s,bus,D,R);view.resize(1366,768);view.show();app.processEvents()
    cid=owners[0][0];source=view._runtime_widgets[cid]['card']
    row=dict(cards=len(s.cards),facilities=len(s.freight.facilities),synthetic=count!='20-facilities',synthetically_accelerated_completion_batches=True)
    row['tick']=measure(lambda:engine.advance_time(s,1))
    samples=[]
    for repetition in range(7):
        # Prepare an equivalent batch of actual arrivals outside the measurement.
        for shipment in s.freight.outbound_shipments.values():shipment.remaining_seconds=1
        t=time.perf_counter();engine.advance_time(s,1);duration=(time.perf_counter()-t)*1000
        samples.append(dict(callback_ms=duration,total_ms=duration))
    row['completion_tick']=dict(samples=samples,median_ms=statistics.median(r['total_ms'] for r in samples),max_ms=max(r['total_ms'] for r in samples))
    row['freight_refresh']=measure(view.refresh_runtime,True)
    stage=view.findChild(QWidget,'freightFacilityHeader')
    row['header_refresh']=measure(getattr(stage,'refresh_statistics',stage.update),True)
    row['tooltip']=measure(lambda:view._show_freight_hover(cid,source),True);view._hide_freight_hover()
    row['snapshot']=measure(lambda:serialize_game_state(s))
    payload=serialize_game_state(s);raw=json.dumps(payload,sort_keys=True)
    row['payload_bytes']=len(raw.encode());row['encoding']=measure(lambda:json.dumps(payload,sort_keys=True))
    store=SQLiteSaveStore(OUT/f'{count}.sqlite');store.initialize()
    row['save']=measure(lambda:store.save('bench',s))
    row['load']=measure(lambda:store.load('bench'))
    row['working_set_bytes']=memory();row['widgets']=len(view.findChildren(QWidget))
    business=json.loads(raw);business['state_schema_version']=6;business['freight'].pop('delivery_statistics',None)
    for shipment in business['freight']['outbound_shipments'].values():
        shipment.pop('source_facility_id',None);shipment.pop('economic_processed',None)
    row['business_payload_sha256']=hashlib.sha256(json.dumps(business,sort_keys=True).encode()).hexdigest()
    if hasattr(s.freight,'delivery_statistics'):
        stats=s.freight.delivery_statistics;row['statistics_bytes']=len(json.dumps(stats.snapshot()).encode());row['occupied_buckets']=len(stats.buckets)
    records[str(count)]=row
    view.close();view.deleteLater();app.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
    print(count,{k:round(v['median_ms'],3) for k,v in row.items() if isinstance(v,dict) and 'median_ms' in v},flush=True)
(OUT/'freight-measurements.json').write_text(json.dumps(dict(method='7 sequential samples; identical seed, commands and 600 simulation seconds of actual engine delivery warm-up, fixed UTC clock. 10/50/100/500 are oversized synthetic single facilities; 20 facilities/160 cards built by real commands. Completion-tick samples shorten remaining time to one second outside the measured call, generating synthetic simultaneous batches; subsequent UI/snapshot/save/load operate on that stressed history. Callback versus event drain recorded. Header before=existing update(), after=statistics refresh plus any repaint; new work is not a speedup claim. Working set is shared warmed process memory, no GPU/FPS or leak claim. Business hashes may differ for legal-command UUID identities.',fixtures=records),indent=2),encoding='utf8')
