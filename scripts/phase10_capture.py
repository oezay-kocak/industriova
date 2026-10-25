"""Real window/dialog captures from a selected source tree, with isolated state."""
from pathlib import Path
import argparse, os, sys, json, hashlib
root=Path.cwd();p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=root);p.add_argument('--stage',default='after');args=p.parse_args()
scale=int(os.environ.get('QT_SCALE_FACTOR','1'));out=root/f'artifacts/phase10/screenshots/{args.stage}/dpi{scale}';out.mkdir(parents=True,exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
sys.path[:0]=[str(args.source.resolve()/'src'),str(root/'tests'),str(root)]
from PySide6.QtWidgets import QApplication,QWidget,QTabWidget,QLineEdit
from PySide6.QtCore import QTimer,QEvent
from PySide6.QtTest import QTest
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.inventory_view import InventoryView
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.event_feed import EventFeedWidget
from production_zero.ui.release_dialogs import IndustrialDialog
from production_zero.core.commands import CommandBus,BuyCommonSupplyCard,InstallFreightCard,ReturnMachinesToInventory
from contract_capacity_fixture import provide_capacity
from production_zero.data.definitions import load_card_definitions
D=load_card_definitions(args.source/'src/production_zero/data/game_definitions.json')
app=QApplication([]);_load_qa_fonts();rows=[]
def drain():
 for _ in range(3):app.processEvents();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
for width,height in ((1366,768),(1600,980),(1920,1080)):
 w=MainWindow(development_mode=False)
 for timer in w.findChildren(QTimer):timer.stop()
 tabs=w.findChild(QTabWidget,'mainTabs');s=w._session_state;bus=CommandBus(s)
 boards={v._board_config.board_kind:v for v in w.findChildren(ProductionBoardViewV2)}
 inv=w.findChild(InventoryView);freight=w.findChild(FreightView);supply=w.findChild(SupplyView);feed=w.findChild(EventFeedWidget)
 w.resize(width,height);w.show();drain()
 def shot(name,widget=None):
  drain();pix=(widget or w).grab();path=out/f'{name}-{width}x{height}.png';assert pix.save(str(path))
  rows.append(dict(file=path.relative_to(root).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),logical=[(widget or w).width(),(widget or w).height()],pixels=[pix.width(),pix.height()],scale=scale))
 tabs.setCurrentWidget(boards['resources']);drain();shot('genesis-resources')
 # Empty Inventory fixture contains no extra grants; all starter cards are moved
 # out only in this disposable visual state, before restoring the original map.
 tabs.setCurrentWidget(inv);cards=s.cards;s.cards={};inv.refresh();shot('inventory-empty');s.cards=cards;inv.refresh();shot('inventory-filled')
 row=inv._workspace_rows[0];inv._choose_workspace_card(row);shot('inventory-selected')
 if hasattr(inv,'_show_workspace_menu'):
  inv._show_workspace_menu(row);drain();shot('inventory-context',inv._workspace_menu);inv._workspace_menu.reject();drain()
 def modal_shot(name,action):
  def capture():
   d=app.activeModalWidget();assert isinstance(d,IndustrialDialog);shot(name,d);d.reject_button.click()
  QTimer.singleShot(0,capture);action();drain()
 for kind in ('resources','factory','energy'):
  view=boards[kind];tabs.setCurrentWidget(view);unit=view._units[view._selected_hall_id]
  unit.name={'resources':'Mining Complex 1','factory':'Hall 1','energy':'Plant 1'}[kind];view.refresh_view();shot(kind+'-short-name')
  unit.name='MY VERY LARGE INDUSTRIAL COMPLEX AND PRODUCTION FACILITY '+kind.upper();view.refresh_view();shot(kind+'-long-name')
 tabs.setCurrentWidget(boards['resources']);modal_shot('rename-dialog',boards['resources']._rename_building)
 s.cash.amount=1e9;w._global_header.refresh()
 if args.stage=='after':modal_shot('storage-expansion',w._global_header._expand_resource_storage)
 else:shot('storage-no-confirmation-before')
 feed.refresh_communications();shot('history-inbox-normal');s.communications.add_unlocks(['resource.iron_ore']);feed.refresh_communications();shot('history-inbox-unread');feed._show_inbox();shot('inbox-read-popup',feed._inbox_panel);feed.close_panels()
 tabs.setCurrentWidget(supply);supply.refresh();supply._show_section(0);shot('supply-daily');supply._show_section(1);shot('supply-default')
 for category in ('Assembly','Freight'):
  supply._type_filter.setCurrentText(category);shot('supply-'+category.lower())
 tabs.setCurrentWidget(boards['factory']);boards['factory']._open_production_guide();shot('production-guide-prices');boards['factory'].show_frontscreen()
 w._global_resources.toggle();w._global_resources.drawer._set_inventory_mode(False);shot('resource-browser-prices');w._global_resources.hide()
 provide_capacity(s,D)
 for v in boards.values():v.reset_for_state_change()
 freight.reset_for_state_change();tabs.setCurrentWidget(freight);drain()
 facility=s.freight.facilities['p8-fixture-freight'];freight._select_facility(facility.facility_id);cid=next(slot.card_id for slot in facility.slots if slot.card_id)
 facility.name='Garage 1';freight.refresh();shot('freight-short-name')
 facility.name='MY VERY LARGE INDUSTRIAL FREIGHT TERMINAL AND DISTRIBUTION COMPLEX';freight.refresh()
 stats=s.freight.delivery_statistics;stats.advance(60);stats.record(cid,facility.facility_id,sell=1234567,contract=2345678,consortium=3456789);freight.refresh_runtime();shot('freight-statistics-long-name')
 freight._open_assignment_view(cid);shot('freight-select-resource');freight._select_assignment_resource('iron_ore')
 if hasattr(freight,'_route_dialog') and freight._route_dialog is not None:
  freight._choose_assignment_destination('market');shot('delivery-target-confirm',freight._route_dialog);freight._route_dialog.reject();shot('delivery-target-cancel-back-to-resources')
 else:
  freight._route_combo.setCurrentIndex(freight._route_combo.findData('market'));shot('delivery-target-before')
 freight._close_assignment_view();w.close();drain()
(out/'captures.json').write_text(json.dumps(dict(captures=rows,source=str(args.source.resolve()),assumptions='Actual MainWindow and separate Qt surfaces. Isolated synthetic QA states and large P6 display totals; no personal save loaded. Physical pixel size equals logical size times Qt scale. Native Windows hand acceptance remains open.'),indent=2),encoding='utf8')
print('CAPTURED',len(rows),args.stage,'dpi',scale,flush=True)
