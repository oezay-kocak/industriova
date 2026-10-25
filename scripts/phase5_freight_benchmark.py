"""New P5 work only: seven explicit route/upgrade intents, without modal wait."""
import json, os, sys, time, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase5/after/freight-ui';OUT.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(OUT/'appdata'),APPDATA=str(OUT/'appdata'))
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication,QWidget
from production_zero.core.state import GameState
from production_zero.core.freight import FreightFacility
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.commands import CommandBus,BuildFreightFacility,ExpandFreightFacility,InstallFreightCard,BuyCommonSupplyCard
from production_zero.data.definitions import load_card_definitions
from production_zero.ui.freight_view import FreightView
from production_zero.ui import freight_upgrade
from phase0_benchmark import register_fonts,memory
os.environ.update(LOCALAPPDATA=str(OUT/'appdata'),APPDATA=str(OUT/'appdata'))
app=QApplication([]);register_fonts(app)
D=load_card_definitions(ROOT/'src/production_zero/data/game_definitions.json')
# Use the same complete resource catalog as MainWindow.
from phase0_benchmark import R
freight_upgrade.confirm=lambda *a:True
records={}
def timed(action):
    start=time.perf_counter();action();callback=(time.perf_counter()-start)*1000
    app.processEvents()
    app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    return dict(callback_ms=callback,total_ms=(time.perf_counter()-start)*1000)
for count in ('20-facilities',10,50,100,500):
    state=GameState(197);state.cash.amount=1e15;state.ensure_resource('steel').amount=1e8
    state.ensure_resource('copper_ore').amount=1e8
    legal=count=='20-facilities'
    if legal:
        bus=CommandBus(state)
        for _ in range(19):bus.dispatch(BuildFreightFacility('garage_depot'))
        bus.dispatch(BuyCommonSupplyCard('freight.truck',D,quantity=160))
        owned=iter(state.cards)
        for facility in state.freight.facilities.values():
            for _ in range(5):bus.dispatch(ExpandFreightFacility(facility.facility_id))
            for slot in facility.slots:bus.dispatch(InstallFreightCard(facility.facility_id,slot.index,next(owned),D))
        unit=next(iter(state.freight.facilities.values()))
        assert len(state.freight.facilities)==20 and len(state.installed_freight_card_ids())==160
    else:
        unit=FreightFacility('p5','P5 Freight synthetic stress',slot_count=count)
        state.freight.facilities={unit.facility_id:unit}
        for i,slot in enumerate(unit.slots):
            cid=f'p5-{i}';state.cards[cid]=create_card_instance(cid,'freight.truck',D['freight.truck'].card_kind,Rarity.COMMON);slot.card_id=cid
    view=FreightView(state,CommandBus(state),D,R);view.resize(1366,768);view.show();app.processEvents()
    ids=tuple(slot.card_id for slot in unit.slots)[:5];samples={k:[] for k in ('open','cargo','target','confirm_return','single_upgrade','tooltip')}
    for repetition in range(7):
        samples['open'].append(timed(lambda:view._open_assignment_view(ids[0],ids)))
        cargo='steel' if repetition%2==0 else 'copper_ore'
        samples['cargo'].append(timed(lambda:view._select_assignment_resource(cargo)))
        view._route_combo.setCurrentIndex(0);app.processEvents()  # prepare an explicit target choice outside its clock
        samples['target'].append(timed(lambda:view._route_combo.setCurrentIndex(view._route_combo.findData('market'))))
        samples['confirm_return'].append(timed(view._confirm_assignment))
        view._freight_upgrade_pending=False  # a new, distinct confirmed intent; no physical double-click here
        source=view._runtime_widgets[ids[0]]['card']
        samples['single_upgrade'].append(timed(lambda:freight_upgrade.upgrade_vehicles(view,(ids[0],))))
        assert view._runtime_widgets[ids[0]]['card'] is source
        samples['tooltip'].append(timed(lambda:view._show_freight_hover(ids[0],source)))
        view._hide_freight_hover()
    records[str(count)]=dict(synthetic=not legal,legal_command_fixture=legal,facilities=len(state.freight.facilities),cards=len(state.cards),visible_facility_cards=len(unit.slots),widgets=len(view.findChildren(QWidget)),working_set_bytes=memory(),samples=samples,
                            medians_ms={k:statistics.median(r['total_ms'] for r in rows) for k,rows in samples.items()},
                            maxima_ms={k:max(r['total_ms'] for r in rows) for k,rows in samples.items()})
    view.close();view.deleteLater();app.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
(OUT/'measurements.json').write_text(json.dumps(dict(method='New P5 work, no comparable old flow claimed. Standalone FreightView; global MainWindow hooks not included. Seven serial intents, alternating two cargo resources; target placeholder reset/drained outside clock for an explicit measured Sell choice. Callback and drain separated. 10/50/100/500 oversized stress facilities synthetic; 20-facilities is an isolated legal company built through existing purchase/build/expand/install paths, 160 vehicles, 8 per garage. Modal construction and human wait excluded by confirmed-action stub. Working set includes shared warmed Qt/assets, not an isolated allocation or leak proof.',fixtures=records),indent=2),encoding='utf8')
print(json.dumps({k:v['medians_ms'] for k,v in records.items()}),flush=True)
