"""Separate the larger P10 Inventory viewport from per-card refresh work."""
from pathlib import Path
from dataclasses import replace
import argparse,os,sys,time,json,statistics
root=Path.cwd();p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=root);p.add_argument('--stage',required=True);args=p.parse_args()
out=root/'artifacts/phase10/performance'/args.stage;out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(args.source.resolve()/'src'));os.environ.update(QT_QPA_PLATFORM='offscreen',QT_SCALE_FACTOR='1',LOCALAPPDATA=str(out/'matched-appdata'),APPDATA=str(out/'matched-appdata'))
from PySide6.QtWidgets import QApplication
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.inventory_view import InventoryView
from production_zero.core.state import GameState
from production_zero.core.commands import CommandBus,BuyCommonSupplyCard
from production_zero.data.definitions import load_card_definitions
D=load_card_definitions(args.source/'src/production_zero/data/game_definitions.json');app=QApplication([]);_load_qa_fonts();rows={}
for count in (500,5000,10000):
 s=GameState(1);s.cash.amount=1e12;bus=CommandBus(s);bus.dispatch(BuyCommonSupplyCard('machine.processor',D,count))
 s.cards={f'inventory-{index}':replace(card,card_id=f'inventory-{index}',acquisition_cost=1000+index*.01) for index,card in enumerate(s.cards.values())}
 inv=InventoryView(s,D,command_bus=bus,release_mode=True);inv.resize(1100,760);inv._workspace_scroll.setFixedHeight(400);inv.show();app.processEvents()
 for operation in ('refresh','scroll'):
  samples=[]
  for _ in range(7):
   start=time.perf_counter()
   if operation=='refresh':inv.refresh()
   else:
    bar=inv._workspace_scroll.verticalScrollBar();bar.setValue(bar.maximum() if bar.value()==0 else 0)
   app.processEvents();samples.append((time.perf_counter()-start)*1000)
  rows[f'inventory.{count}.matched_{operation}']=dict(median_ms=statistics.median(samples),max_ms=max(samples),samples_ms=samples,pool=len(inv._workspace_pool),viewport=[inv._workspace_scroll.viewport().width(),inv._workspace_scroll.viewport().height()])
 inv.close();inv.deleteLater();app.processEvents()
(out/'inventory-matched.json').write_text(json.dumps(rows,indent=2),encoding='utf8');print('MATCHED VIEWPORT',args.stage,flush=True)
