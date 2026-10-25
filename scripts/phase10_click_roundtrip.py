"""Real pointer path: Supply → Inventory → install → return → reinstall → sell."""
from pathlib import Path
import os,sys,json
root=Path.cwd();scale=int(os.environ.get('QT_SCALE_FACTOR','1'));out=root/f'artifacts/phase10/click-roundtrip-dpi{scale}';out.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(root/'src'),str(root/'tests'),str(root)];os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
from PySide6.QtWidgets import QApplication,QTabWidget
from PySide6.QtCore import QTimer,Qt
from PySide6.QtTest import QTest
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.inventory_view import InventoryView
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.game_ui import GameButton
from production_zero.core.machine_operations import resale_value
from test_phase3_inventory_ui import answer,choose
from test_ui_polish_interactions import click,modal,press_dialog
app=QApplication([]);_load_qa_fonts();w=MainWindow(development_mode=False);w.resize(1366,768);w.show();app.processEvents()
for timer in w.findChildren(QTimer):timer.stop()
s=w._session_state;s.cash.amount=1e6;tabs=w.findChild(QTabWidget,'mainTabs');supply=w.findChild(SupplyView);inv=w.findChild(InventoryView);board=w.findChild(FactoryViewV2);steps=[]
def enter(view):
 index=tabs.indexOf(view);nav=tabs._navigation_bar;click(w,nav,pos=nav.tabRect(index).center());QTest.qWait(220);assert tabs.currentWidget() is view
enter(supply);supply._show_section(1);QTest.mouseClick(supply._type_filter.buttons['Processing'],Qt.MouseButton.LeftButton);app.processEvents()
card=next(c for c in supply._common_card_pool if c.isVisible() and c._supply_data.definition_id=='machine.processor')
before=set(s.cards);cash=s.cash.amount;modal(lambda d:press_dialog(d,d.accept_button));QTest.mouseClick(card._buy_button,Qt.MouseButton.LeftButton)
acquired=set(s.cards)-before;assert len(acquired)==1;cid=acquired.pop();original=s.cards[cid];assert s.cash.amount==cash-original.acquisition_cost;steps.append('actual supply buy button → one paid inventory ID')
def inventory_action(name):
 enter(inv);choose(app,inv,cid);tile=next(c for c in inv._workspace_pool if c.isVisible() and cid in c._inventory_row.card_ids)
 QTest.mouseClick(tile,Qt.MouseButton.RightButton);app.processEvents();menu=inv._workspace_menu;assert menu.isVisible()
 modal(lambda d:press_dialog(d,d.accept_button));press_dialog(menu,menu.findChild(GameButton,'inventoryContext'+name));app.processEvents()
def return_action():
 enter(board);index=next(slot.index for slot in s.halls['hall-1'].slots if slot.card_id==cid)
 def selected(d):
  button=next(b for b in d.findChildren(GameButton,'machineContextAction') if b.text()=='RETURN TO INVENTORY')
  press_dialog(d,button)
 modal(selected);click(w,board._slot_widgets[index],button=Qt.MouseButton.RightButton);app.processEvents()
 assert cid not in s.installed_card_ids() and s.cards[cid] is original
inventory_action('Install');assert cid in s.installed_card_ids() and s.cards[cid] is original;steps.append('actual inventory right-click INSTALL → facility confirm')
return_action();steps.append('actual board right-click RETURN TO INVENTORY')
inventory_action('Install');assert cid in s.installed_card_ids() and s.cards[cid] is original;steps.append('actual inventory right-click INSTALL → same ID reinstalled')
return_action();cash=s.cash.amount;value=resale_value(original,board._definitions[original.definition_id]);inventory_action('Sell')
assert cid not in s.cards and s.cash.amount==cash+value and set(s.cards)==before;steps.append('actual inventory right-click SELL → yellow confirmation → exact 80% proceeds')
assert not inv._workspace_ids();w.close();app.processEvents()
report=dict(ok=True,scale=scale,steps=steps,card_id=cid,acquisition=original.acquisition_cost,resale=value,final_cash=s.cash.amount,original_starter_ids_retained=True,no_original_save=True)
(out/'result.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('FULL POINTER ROUNDTRIP PASSED',scale,flush=True)
