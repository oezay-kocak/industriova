"""P3 scenes at all requested sizes/scales, using the actual MainWindow."""
import os, sys, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'artifacts/phase3/screenshots'/('dpi'+os.environ.get('QT_SCALE_FACTOR','1'));out.mkdir(parents=True,exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from dataclasses import replace
from PySide6.QtCore import QEvent,QTimer
from PySide6.QtWidgets import QApplication,QTabWidget
from production_zero.ui.main_window import MainWindow
from production_zero.ui.inventory_view import InventoryView
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.release_dialogs import IndustrialDialog
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.supply import common_supply_offers
from phase0_benchmark import register_fonts
app=QApplication([]);register_fonts(app)
window=MainWindow(development_mode=False);window.findChild(FactoryViewV2).pause_simulation()
inv=window.findChild(InventoryView);supply=window.findChild(SupplyView);tabs=window.findChild(QTabWidget,'mainTabs');state=inv._state;defs=inv._definitions
def drain():
 for _ in range(5):app.processEvents();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
captures=[]
def capture(name,widget,size):
 drain();path=out/f'{name}-{size[0]}x{size[1]}.png';pix=widget.grab();assert pix.save(str(path));captures.append(dict(file=str(path.relative_to(ROOT)),width=pix.width(),height=pix.height(),logical_width=widget.width(),logical_height=widget.height()))
def clear_cards():
 for unit in (*state.all_production_units(),*state.freight.facilities.values()):
  for slot in unit.slots:slot.card_id=None
 state.cards.clear();state.machine_production.clear();state.freight.assignments.clear();state.freight.outbound_shipments.clear();inv.reset_for_state_change()
def add(did,cid,**values):
 d=defs[did];state.cards[cid]=replace(create_card_instance(cid,did,d.card_kind,values.pop('rarity',Rarity.COMMON)),**values)
def modal_capture(name,trigger,size,quantity=None):
 def run():
  dialog=app.activeModalWidget();assert isinstance(dialog,IndustrialDialog)
  if quantity is not None and dialog.quantity is not None:dialog.quantity.setValue(quantity)
  drain();capture(name,dialog,size);dialog.reject_button.click()
 QTimer.singleShot(0,run);trigger()
for size in ((1366,768),(1600,980),(1920,1080)):
 window.resize(*size);window.show();tabs.setCurrentWidget(inv);drain();assert (window.width(),window.height())==size
 clear_cards();capture('inventory-empty',window,size)
 for i in range(1200):
  did=tuple(d.definition_id for d in defs.values() if d.definition_id in {'machine.processor','machine.extractor','energy.solar_array','freight.truck'})[i%4]
  add(did,f'full-{i:05}',acquisition_cost=float(i),mk_level=i%99+1,rarity=tuple(Rarity)[i%5])
 inv.refresh();drain();capture('inventory-full',window,size)
 bar=inv._workspace_scroll.verticalScrollBar();bar.setValue(bar.maximum());capture('inventory-full-last',window,size)
 clear_cards()
 for i in range(10000):add('machine.processor',f'stack-{i:05}',acquisition_cost=1234567.89)
 inv.refresh();inv._choose_workspace_card(inv._workspace_rows[0]);inv._workspace_quantity.setValue(10000);capture('inventory-large-stack',window,size)
 modal_capture('inventory-sell',inv._workspace_sell.click,size)
 clear_cards();did='machine.processor';original=defs[did];defs[did]=replace(original,name='Advanced International Industrial Processing Machine With A Very Long Name')
 add(did,'legendary',acquisition_cost=987654321.12,upgrade_investment=123456789.12,mk_level=99,rarity=Rarity.LEGENDARY,output_bonus_percent=49.9,power_bonus_percent=49.9)
 inv.refresh();inv._choose_workspace_card(inv._workspace_rows[0]);capture('inventory-legendary-long-name',window,size)
 modal_capture('inventory-install',inv._workspace_install.click,size)
 defs[did]=original
 tabs.setCurrentWidget(supply);state.cash.amount=1e15;supply.refresh();supply._show_section(1);supply._type_filter.setCurrentText('Factory');capture('supply-common',window,size)
 offer=next(o for o in common_supply_offers(defs) if o.definition_id=='machine.processor')
 modal_capture('supply-purchase',lambda:supply._buy_offer(offer,'common'),size,10000)
 supply._show_section(0);capture('supply-daily',window,size)
 state.cash.amount=0
 dialog=supply._purchase_dialog(offer,'common');dialog.show();capture('supply-max-zero',dialog,size);dialog.close();dialog.deleteLater();drain()
window.close();drain();(out/'captures.json').write_text(json.dumps(captures,indent=2),encoding='utf8');print(json.dumps(dict(captures=len(captures),out=str(out))))
