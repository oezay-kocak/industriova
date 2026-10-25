"""Capture the same three existing views at three sizes and two Qt scales."""
import os,sys,argparse,json
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('stage');parser.add_argument('--source',type=Path);args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[1];source=(args.source or ROOT).resolve();out=ROOT/'artifacts/phase1'/args.stage/('dpi'+os.environ.get('QT_SCALE_FACTOR','1'))
out.mkdir(parents=True,exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(out/'appdata'),APPDATA=str(out/'appdata'))
sys.path[:0]=[str(source/'src'),str(source/'scripts')]
from phase0_benchmark import D,register_fonts,state
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEvent
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.unlock_tree_view import UnlockTreeView
from production_zero.ui.leaderboard_view import LeaderboardView
from production_zero.core.commands import CommandBus
from production_zero.services.local import LocalLeaderboardService
app=QApplication([]);register_fonts(app)
def drain():
    for _ in range(8):app.processEvents();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
s=state();b=FactoryViewV2(s,CommandBus(s),D);b.pause_simulation()
u=UnlockTreeView(s,D,lambda:None);lb=LeaderboardView(LocalLeaderboardService(s));lb._set_ranking_index(2)
for width,height in ((1366,768),(1600,980),(1920,1080)):
    for name,view in (('guide',b),('unlock',u),('leaderboard',lb)):
        view.resize(width,height);view.show()
        if name=='guide':b._open_production_guide()
        drain();view.grab().save(str(out/f'{name}-{width}x{height}.png'));view.hide()
for view in (b,u,lb):view.close();view.deleteLater()
drain();print('Captured',out)
