"""Official entry point, isolated legacy folders and actual New Game UI resets."""
import os,json,sqlite3,hashlib,subprocess,sys,threading,time
from pathlib import Path
from dataclasses import replace
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtCore import Qt,QTimer,QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QMessageBox,QPushButton,QTabWidget,QWidget
from production_zero.persistence.paths import default_save_directory,default_company_save_path
from production_zero.persistence.dev_save_store import DevJsonSaveStore,default_dev_save_directory
from production_zero.persistence.sqlite_store import SQLiteSaveStore,serialize_game_state
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2,FactoryV2BuildSlot
from production_zero.ui.factory_view import FactoryCardSelectionTile
from production_zero.ui.dev_tools_view import DevToolsView
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.freight_view import FreightView

@pytest.fixture(scope='module')
def app():return QApplication.instance() or QApplication([])

@pytest.fixture
def window(app,tmp_path,monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path));monkeypatch.setenv('APPDATA',str(tmp_path/'roaming'))
    path=default_company_save_path();path.parent.mkdir(parents=True)
    w=MainWindow(save_store=SQLiteSaveStore(path),development_mode=True,charts_enabled=False)
    w.resize(1366,768);w.show();QTest.qWait(40)
    for b in w.findChildren(ProductionBoardViewV2):b.pause_simulation()
    yield w
    if w.isVisible():w.close()
    w.deleteLater();QTest.qWait(25)

def signature(state):
    return {'cash':state.cash.amount,'level':state.company.level,'xp':state.company.current_xp,
        'resources':{k:v.amount for k,v in state.resources.items() if v.amount},
        'cards':{cid:(c.definition_id,c.mk_level,c.rarity.value) for cid,c in state.cards.items()},
        'buildings':{kind:{uid:(u.slot_count,[(s.index,s.card_id) for s in u.slots]) for uid,u in state.production_units(kind).items()} for kind in ('factory','resources','energy')},
        'freight_slots':{uid:[s.card_id for s in u.slots] for uid,u in state.freight.facilities.items()},
        'shipments':list(state.freight.outbound_shipments),'active_contracts':list(state.contracts.active)}

def click(w,widget,pos=None):
    QTest.mouseClick(w.windowHandle(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,widget.mapTo(w,pos or widget.rect().center()));QTest.qWait(25)

def board(w,name):
    tabs=w.findChild(QTabWidget,'mainTabs');tabs.setCurrentIndex(next(i for i in range(tabs.count()) if tabs.tabText(i)==name));QTest.qWait(25)
    return tabs.currentWidget()

def install(w,b,index=0):
    slot=next(c for c in b.findChildren(FactoryV2BuildSlot) if c.isVisible() and c._release_slot_index==index)
    click(w,slot);tile=next(c for c in b.findChildren(FactoryCardSelectionTile) if c.isVisible());cid=tile.property('cardId');click(w,tile);return cid

def new_game(w):
    dev=board(w,'Dev')
    def answer():
        box=QApplication.activeModalWidget();assert isinstance(box,QMessageBox)
        QTest.mouseClick(box.button(QMessageBox.StandardButton.Yes),Qt.MouseButton.LeftButton)
    QTimer.singleShot(60,answer)
    click(w,next(b for b in dev.findChildren(QPushButton) if b.text()=='NEW GAME'))
    for b in w.findChildren(ProductionBoardViewV2):b.pause_simulation()

@pytest.mark.parametrize('local,roaming',[(True,True),(False,True),(False,False)])
def test_all_default_save_paths_share_industriova_root(tmp_path,monkeypatch,local,roaming):
    for key,enabled,path in [('LOCALAPPDATA',local,tmp_path/'local'),('APPDATA',roaming,tmp_path/'roaming')]:
        if enabled:monkeypatch.setenv(key,str(path))
        else:monkeypatch.delenv(key,raising=False)
    expected=(tmp_path/'local' if local else tmp_path/'roaming' if roaming else Path.home())/'Industriova/playtests/contract-auto-test/saves'
    assert default_save_directory()==expected
    assert default_company_save_path()==expected/'company.sqlite'
    assert default_dev_save_directory()==expected/'dev'

ENTRY_CHILD=r'''
import json,os
from pathlib import Path
from PySide6.QtCore import QTimer
import production_zero.app.__main__ as entry
from production_zero.ui.main_window import MainWindow
from production_zero.persistence.sqlite_store import serialize_game_state
class Observed(MainWindow):
    def __init__(self,**kwargs):
        super().__init__(development_mode=True,charts_enabled=False,**kwargs)
        Path(os.environ['DIAG_RESULT']).write_text(json.dumps({'path':str(self._save_store._path),'state':serialize_game_state(self._session_state)}))
        QTimer.singleShot(80,self.close)
entry.MainWindow=Observed
assert entry.main()==0
'''

@pytest.mark.parametrize('case',['A-fresh','B-legacy-only','C-both'])
def test_real_entrypoint_ignores_legacy_and_repeated_restarts_preserve_only_own_save(tmp_path,case):
    legacy=tmp_path/'Production Zero/saves/company.sqlite';legacy.parent.mkdir(parents=True)
    if case!='A-fresh':
        payload={'state_schema_version':999,'cash':{'amount':999999999},'resources':{'coal':{'amount':88888}},'cards':{'legacy-machine':{'mk_level':99,'rarity':'legendary'}}}
        with sqlite3.connect(legacy) as db:
            db.execute('create table saves(slot text primary key,state_json text not null)');db.execute('insert into saves values (?,?)',('company',json.dumps(payload)))
    old_hash=hashlib.sha256(legacy.read_bytes()).hexdigest() if legacy.exists() else None
    expected_cash=4321 if case=='C-both' else 1250
    own=tmp_path/'Industriova/playtests/contract-auto-test/saves/company.sqlite'
    if case=='C-both':
        from importlib.resources import files
        from production_zero.data.definitions import load_card_definitions,load_resource_definitions
        from production_zero.ui.main_window import _create_initial_state
        state=_create_initial_state(load_resource_definitions(files('production_zero.data').joinpath('resource_definitions.json')),load_card_definitions(files('production_zero.data').joinpath('game_definitions.json')))
        state.cash.amount=4321;own.parent.mkdir(parents=True)
        store=SQLiteSaveStore(own);store.initialize();store.save('company',state)
    for launch in range(3):
        result_path=tmp_path/f'observed-{launch}.json'
        env=dict(os.environ,LOCALAPPDATA=str(tmp_path),APPDATA=str(tmp_path/'roaming'),PYTHONPATH=str(Path.cwd()/'src'),QT_QPA_PLATFORM='offscreen',DIAG_RESULT=str(result_path))
        result=subprocess.run([sys.executable,'-c',ENTRY_CHILD],env=env,capture_output=True,text=True,timeout=35)
        assert result.returncode==0,result.stderr
        p=json.loads(result_path.read_text());s=p['state']
        assert Path(p['path'])==own and s['cash']['amount']==expected_cash
        assert len(s['cards'])==8 and 'legacy-machine' not in s['cards']
        assert not s['freight']['outbound_shipments'] and s['company']['level']==1 and s['company']['current_xp']==0
        assert {k:v['amount'] for k,v in s['resources'].items() if v['amount']}=={'iron_ore':145,'coal':70,'copper_ore':88}
        assert not s['contracts']['active']
        assert all(c['mk_level']==1 and c['rarity']=='common' for c in s['cards'].values())
        if old_hash:assert hashlib.sha256(legacy.read_bytes()).hexdigest()==old_hash
        else:assert not legacy.exists()
    with sqlite3.connect(own) as db:assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
    assert not list(legacy.parent.glob('*pre-industriova*'))

def test_new_game_clears_old_state_rebinds_all_boards_and_post_reset_install_is_visible(window):
    w=window;expected=signature(w._session_state)
    for name in ('Resources','Factory','Energy'):
        b=board(w,name);cid=install(w,b)
        b._selected_machines={cid};b._selection_anchor=0;b._configuration_clipboard=(('old',),)
        b._state.cards[cid]=replace(b._state.cards[cid],mk_level=7)
    state=w._session_state;state.cash.amount=999999;state.resources['coal'].amount=8888
    state.company.current_xp=500
    state.cards['old-card-only']=replace(next(iter(state.cards.values())),card_id='old-card-only',mk_level=99)
    from tests.contract_acceptance_fixture import accept_fixture
    accept_fixture(state,w.findChild(ContractsView)._definitions,'regular')
    from production_zero.core.freight import OutboundFreightShipment
    state.freight.outbound_shipments['old-shipment']=OutboundFreightShipment('old-shipment','market',None,'coal',40)
    contracts=w.findChild(ContractsView);contracts._selected_products[('regular',state.contracts.offers['regular'][0].contract_id)]=['coal','iron_ore']
    factory=board(w,'Factory');factory._open_production_guide();guide=factory._cached_guide_panel
    w._global_resources.toggle();w._global_resources.search.setText('old filter')
    new_game(w)
    assert signature(state)==expected
    assert not w._global_resources.isVisible() and w._global_resources.search.text()==''
    assert all(all(v is None for v in values) for values in contracts._selected_products.values())
    for b in w.findChildren(ProductionBoardViewV2):
        assert b._units is state.production_units(b._board_config.board_kind)
        assert not b._selected_machines and not b._configuration_clipboard and b._drawer_mode is None
        assert b._cached_guide_panel is None and b._cached_unlock_tree_panel is None
    for name in ('Resources','Factory','Energy'):
        b=board(w,name);cid=install(w,b)
        assert b._slot_widgets[0]._card is state.cards[cid]
        assert b._units[b._selected_hall_id].slots[0].card_id==cid
    assert w._save_session(wait=True)
    saved=SQLiteSaveStore(default_company_save_path()).load('company')
    assert signature(saved)==signature(state)
    checkpoint=signature(state);w.close()
    restarted=MainWindow(save_store=SQLiteSaveStore(default_company_save_path()),development_mode=True,charts_enabled=False)
    restarted.resize(1366,768);restarted.show();QTest.qWait(40)
    for b in restarted.findChildren(ProductionBoardViewV2):b.pause_simulation()
    assert signature(restarted._session_state)==checkpoint
    for name in ('Resources','Factory','Energy'):
        b=board(restarted,name);assert b._slot_widgets[0]._card is restarted._session_state.cards[b._slot_widgets[0]._card.card_id]
    restarted.close();restarted.deleteLater();QTest.qWait(20)

def test_old_queued_autosave_cannot_overwrite_new_game(window):
    w=window;expected=signature(w._session_state);store=w._save_store
    original=store.save_snapshot;started=threading.Event();release=threading.Event();writes=[]
    def delayed(slot,payload):
        p=payload;writes.append(p['cash']['amount'])
        if p['cash']['amount']==98765:
            started.set();assert release.wait(3)
        original(slot,payload)
    store.save_snapshot=delayed
    w._session_state.cash.amount=98765;w._save_session();assert started.wait(2)
    unlock=threading.Timer(.3,release.set);unlock.start()
    try:new_game(w)
    finally:release.set();unlock.join()
    assert writes[0]==98765 and writes[-1]==1250
    assert signature(SQLiteSaveStore(default_company_save_path()).load('company'))==expected

def test_manual_backup_load_and_reset_stay_in_official_tree(window):
    w=window;dev=w.findChild(DevToolsView);state=w._session_state
    factory=board(w,'Factory');cid=install(w,factory)
    state.cash.amount=2468;dev._save_game()
    assert dev._save_store.path==default_save_directory()/'dev/dev_save.json'
    assert dev._save_store.path.exists()
    new_game(w);assert state.cash.amount==1250
    dev._load_game()
    for b in w.findChildren(ProductionBoardViewV2):b.pause_simulation()
    assert state.cash.amount==2468
    factory=board(w,'Factory');assert factory._slot_widgets[0]._card.card_id==cid
    assert factory._units is state.halls
    assert SQLiteSaveStore(default_company_save_path()).load('company').cash.amount==2468

def test_existing_own_schema_upgrade_keeps_integrity_and_backup_in_new_directory(window):
    w=window;path=default_company_save_path();store=w._save_store
    expected=signature(w._session_state)
    payload=serialize_game_state(w._session_state);payload['state_schema_version']=4
    store.save_payload('company',json.dumps(payload))
    restored=store.load('company');assert signature(restored)==expected
    backup=path.with_name('company.pre-industriova-v5.sqlite')
    assert backup.exists() and backup.parent==default_save_directory()
    backup_hash=hashlib.sha256(backup.read_bytes()).hexdigest()
    store.save('company',restored)
    for _ in range(2):assert signature(store.load('company'))==expected
    assert hashlib.sha256(backup.read_bytes()).hexdigest()==backup_hash
