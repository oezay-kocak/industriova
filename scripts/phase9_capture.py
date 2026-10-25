"""P9 actual release-window captures, isolated synthetic presentation states."""
from pathlib import Path
import os,sys,json,runpy,hashlib
root=Path.cwd();scale=int(os.environ.get('QT_SCALE_FACTOR','1'));out=root/f'artifacts/phase9/screenshots/dpi{scale}';out.mkdir(parents=True,exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
sys.argv=['fixture','--source',str(root),'--stage','../phase9/capture-fixture']
f=runpy.run_path(str(root/'scripts/phase8_contract_simulation.py'),run_name='fixture')
from PySide6.QtWidgets import QApplication,QTabWidget,QWidget,QLabel,QToolButton
from PySide6.QtCore import QTimer,QEvent
from PySide6.QtTest import QTest
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow,_copy_state
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.consortium_view import ConsortiumView
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.event_feed import EventFeedWidget,FeedEvent
from production_zero.core.commands import CommandBus,BuildFreightFacility,BuyCommonSupplyCard,InstallFreightCard
from production_zero.core.freight import FreightFacility
app=QApplication([]);_load_qa_fonts();rows=[]
def drain():
 for _ in range(3):app.processEvents();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
for width,height in ((1366,768),(1600,980),(1920,1080)):
 w=MainWindow(development_mode=False)
 for timer in w.findChildren(QTimer):timer.stop()
 s,info=f['company']('late',10);s.cash.amount=1234567890123.45
 _copy_state(w._session_state,s);s=w._session_state
 # Long names are formatting fixtures, using the existing objects and identity.
 for u in s.all_production_units():u.name='NORTHERN INDUSTRIAL PRODUCTION AND PROCESSING FACILITY '+u.hall_id
 bus=CommandBus(s);D=f['D'];facilities={}
 for kind,did in (('garage_depot','freight.truck'),('rail_station','freight.train'),('airport','freight.aircraft'),('harbor','freight.ship')):
  facility=next((u for u in s.freight.facilities.values() if u.facility_type==kind),None)
  if facility is None:
   bus.dispatch(BuildFreightFacility(kind));facility=next(u for u in s.freight.facilities.values() if u.facility_type==kind)
  facility.name='NORTHERN INDUSTRIAL FREIGHT TERMINAL AND DISTRIBUTION '+kind.upper()
  if not any(slot.card_id for slot in facility.slots):
   old=set(s.cards);bus.dispatch(BuyCommonSupplyCard(did,D));cid=next(iter(set(s.cards)-old));bus.dispatch(InstallFreightCard(facility.facility_id,0,cid,D))
  facilities[kind]=facility
 boards={v._board_config.board_kind:v for v in w.findChildren(ProductionBoardViewV2)}
 for v in boards.values():v.reset_for_state_change()
 freight=w.findChild(FreightView);freight.reset_for_state_change()
 personal=w.findChild(ContractsView);personal.reset_for_state_change()
 conso=w.findChild(ConsortiumView);conso._workspace_signature=None;conso._render_signature=None;conso.refresh()
 feed=w.findChild(EventFeedWidget);feed.clear_events();w._global_header.refresh()
 t=w.findChild(QTabWidget,'mainTabs');w.resize(width,height);w.show();drain()
 def shot(name):
  drain();QTest.qWait(100);drain();pix=w.grab();p=out/f'{name}-{width}x{height}.png';assert pix.save(str(p))
  rows.append(dict(file=p.relative_to(root).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),logical=[w.width(),w.height()],pixels=[pix.width(),pix.height()],scale=scale,pencils=sum(b.isVisible() for b in w.findChildren(QToolButton,'renameBuildingButton'))))
 for kind in ('resources','factory','energy'):
  t.setCurrentWidget(boards[kind]);drain();shot(kind+'-frontscreen')
 t.setCurrentWidget(boards['factory']);boards['factory']._open_production_guide();shot('production-guide-prices');boards['factory'].show_frontscreen()
 w._global_resources.toggle();w._global_resources.drawer._set_inventory_mode(True);shot('storage-global-resources');w._global_resources.hide()
 feed.push(FeedEvent('contract','CONSORTIUM FREIGHT DELIVERY COMPLETED',12345));feed.flush_pending();feed._show_history();shot('history');feed.close_panels()
 s.communications.messages.clear();feed.refresh_communications();feed._show_inbox();shot('inbox-empty');feed.close_panels()
 s.communications.add_unlocks(['resource.iron_ore','production.steel']);feed.refresh_communications();shot('inbox-unread');feed._show_inbox();shot('inbox-filled');feed.close_panels()
 t.setCurrentWidget(freight)
 for kind,facility in facilities.items():
  freight._select_facility(facility.facility_id)
  # Actual P6 aggregation, synthetic accepted amounts for display stress.
  cid=next(slot.card_id for slot in facility.slots if slot.card_id)
  s.freight.delivery_statistics.advance(60)
  s.freight.delivery_statistics.record(cid,facility.facility_id,sell=1234567,contract=2000000,consortium=3000000)
  freight.refresh_runtime();shot('freight-'+kind)
 guild=conso._service.create('Northern Freight Cooperative')
 t.setCurrentWidget(conso);conso.refresh();shot('consortium-overview')
 contract=conso._service.start_contract(guild.consortium_id,conso._service.current_company_id,'daily',f['PRODUCTS']['late'][:3])
 conso._open_contract('daily');conso.refresh();shot('consortium-deliver-via-freight')
 button=conso.findChild(QWidget,'deliverViaFreightButton');assert button is not None;button.click();drain();assert t.currentWidget() is freight
 facility=facilities['harbor'];freight._select_facility(facility.facility_id);cid=next(slot.card_id for slot in facility.slots if slot.card_id)
 freight._open_assignment_view(cid);freight._select_assignment_resource(next(iter(contract.requirements)))
 freight._route_combo.setCurrentIndex(freight._route_combo.findData('consortium'));shot('freight-assignment-confirmation')
 freight._close_assignment_view()
 # New quotes without a fleet expose the capacity requirement; accepted terms
 # above are untouched. Remove the fleet only in this final presentation fixture.
 contract.status='expired';other=guild.contracts['weekly'];other.status='expired'
 for facility in s.freight.facilities.values():
  for slot in facility.slots:
   if slot.card_id:s.cards.pop(slot.card_id);slot.card_id=None
 conso._service.renew_contract_offer(guild.consortium_id,conso._service.current_company_id,'daily')
 t.setCurrentWidget(conso);conso._open_contract('daily');conso.refresh();shot('consortium-freight-required')
 w.close();drain()
(out/'captures.json').write_text(json.dumps(dict(captures=rows,assumptions='Actual MainWindow, synthetic mature company and long names; P6 large totals are display fixtures. No personal save. Paid extra facilities/vehicles use normal Commands. No native mouse/DWM acceptance.'),indent=2),encoding='utf8')
print('CAPTURED',len(rows),'scale',scale,flush=True)
