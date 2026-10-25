"""Diagnostic only: real Qt gestures on isolated database copies, no product edits."""
import os,sys,json,sqlite3,traceback
from pathlib import Path
from collections import Counter
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import Qt,QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QTabWidget,QPushButton,QMessageBox
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2,FactoryV2BuildSlot,FactoryV2MachineCard
from production_zero.ui.factory_view import FactoryCardSelectionTile
from production_zero.persistence.sqlite_store import SQLiteSaveStore,serialize_game_state

case=sys.argv[1];out=Path('artifacts/industriova-save-state-diagnosis')/case;out.mkdir(parents=True,exist_ok=True)
os.environ['LOCALAPPDATA']=str(out.resolve()/'isolated-localappdata')
app=QApplication([]);errors=[]
sys.excepthook=lambda t,v,tb:errors.append(''.join(traceback.format_exception(t,v,tb)))
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
_load_qa_fonts()
def raw():
    p=out/'company.sqlite'
    if not p.exists():return None
    with sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True) as db:
        r=db.execute("select state_json from saves where slot='company'").fetchone()
    return json.loads(r[0]) if r else None
def summary(p):
    locations=[];locked=[]
    for key in ('halls','resource_sites','energy_plants'):
        for uid,u in p.get(key,{}).items():
            allowed={i for line in u.get('production_lines',[]) if line['unlocked'] for i in line['slot_indexes']}
            for slot in u['slots']:
                if slot.get('card_id'):
                    loc=(key,uid,slot['index'],slot['card_id']);locations.append(loc)
                    if slot['index'] not in allowed:locked.append(loc)
    for uid,u in p.get('freight',{}).get('facilities',{}).items():
        for s in u['slots']:
            if s.get('card_id'):locations.append(('freight',uid,s['index'],s['card_id']))
    counts=Counter(x[3] for x in locations);cards=p['cards']
    return {'schema':p.get('state_schema_version',1),'tick':p['tick'],'cash':p['cash'],'company':p.get('company'),
        'nonzero_resources':{k:v for k,v in p['resources'].items() if v['amount']},'cards':cards,
        'buildings':{k:p.get(k,{}) for k in ('halls','resource_sites','energy_plants')},'locations':locations,
        'unplaced_ids':sorted(set(cards)-set(counts)),'duplicate_placements':{k:v for k,v in counts.items() if v>1},
        'missing_card_references':[x for x in locations if x[3] not in cards],
        'key_id_mismatches':[k for k,v in cards.items() if k!=v['card_id']], 'locked_placements':locked,
        'freight':p.get('freight'), 'history_points':sum(len(v['values']) for v in p.get('history',{}).values())}
def click(widget):
    QTest.mouseClick(w.windowHandle(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,widget.mapTo(w,widget.rect().center()));QTest.qWait(50)
def switch(name):
    i=next(i for i in range(tabs.count()) if tabs.tabText(i)==name)
    nav=tabs._navigation_bar
    QTest.mouseClick(w.windowHandle(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,nav.mapTo(w,nav.tabRect(i).center()));QTest.qWait(70)
    return tabs.currentWidget()
def inspect(stage):
    data={'state':summary(serialize_game_state(w._session_state)),'boards':{}}
    for name in ('Resources','Factory','Energy'):
        b=switch(name);units=w._session_state.production_units(b._board_config.board_kind)
        widgets=[{'index':i,'widget_class':type(widget).__name__,'card_id':getattr(getattr(widget,'_card',None),'card_id',None),'slot_card_id':getattr(getattr(widget,'_slot',None),'card_id',None),'visible':widget.isVisible()} for i,widget in b._slot_widgets.items()]
        data['boards'][name]={'units_is_current_state':b._units is units,'selected_hall':b._selected_hall_id,
            'selection':sorted(getattr(b,'_selected_machines',set())),
            'cached_unit_ids':list(b._units),'actual_unit_ids':list(units),'cached_locations':[(uid,s.index,s.card_id) for uid,u in b._units.items() for s in u.slots if s.card_id],
            'widgets':widgets,'drawer':b._drawer_mode}
        w.grab().save(str(out/f'{stage}-{name}.png'))
    data['errors']=list(errors)
    (out/f'{stage}.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    return data
before=raw()
if before:(out/'raw-before-summary.json').write_text(json.dumps(summary(before),indent=2),encoding='utf-8')
w=MainWindow(save_store=SQLiteSaveStore(out/'company.sqlite'),development_mode=True,charts_enabled=False)
w.resize(1366,768);w.show();QTest.qWait(100)
tabs=w.findChild(QTabWidget,'mainTabs')
for b in w.findChildren(ProductionBoardViewV2):b.pause_simulation()
inspect('loaded')
if case=='A-fresh':
    for name in ('Resources','Factory','Energy'):
        b=switch(name);slot=next(c for c in b.findChildren(FactoryV2BuildSlot) if c.isVisible())
        click(slot);tile=next(c for c in b.findChildren(FactoryCardSelectionTile) if c.isVisible());click(tile)
        card=next(c for c in b.findChildren(FactoryV2MachineCard) if c.isVisible())
        # Top margin selects the installed card without opening its recipe control.
        QTest.mouseClick(w.windowHandle(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,card.mapTo(w,card.rect().topLeft()+__import__('PySide6.QtCore',fromlist=['QPoint']).QPoint(10,10)));QTest.qWait(30)
    inspect('before-new-game-installed-via-ui')
else:
    for name in ('Resources','Factory','Energy'):
        b=switch(name)
        visible=[c for c in b.findChildren(FactoryV2MachineCard) if c.isVisible()]
        if visible:b._selected_machines={visible[0]._card.card_id} # supplementary selection instrumentation only
# Queue an actual older snapshot, then drive New Game and its real confirmation.
w._save_session()
dev=switch('Dev');button=next(x for x in dev.findChildren(QPushButton) if x.text()=='NEW GAME')
def confirm():
    box=app.activeModalWidget()
    if isinstance(box,QMessageBox):QTest.mouseClick(box.button(QMessageBox.StandardButton.Yes),Qt.MouseButton.LeftButton)
    else:errors.append('New Game confirmation not found')
QTimer.singleShot(100,confirm);click(button)
after=inspect('after-new-game')
# A second visible slot installation exposes commands writing to the NEW state
# while the board still reads the OLD unit mapping.
attempts=[]
for name in ('Resources','Factory','Energy'):
    b=switch(name);empty=[x for x in b.findChildren(FactoryV2BuildSlot) if x.isVisible()]
    if not empty:attempts.append({'board':name,'result':'no visible empty slot'});continue
    index=empty[0]._release_slot_index
    click(empty[0]);tiles=[x for x in b.findChildren(FactoryCardSelectionTile) if x.isVisible()]
    if tiles:
        cid=tiles[0].property('cardId');click(tiles[0]);attempts.append({'board':name,'index':index,'card_id':cid,'result':'UI install gesture completed'})
    else:attempts.append({'board':name,'index':index,'result':'no selection tiles'})
inspect('after-install-attempt');(out/'install-attempts.json').write_text(json.dumps(attempts,indent=2))
w._save_session(wait=True);w.close();w.deleteLater();QTest.qWait(100)
(out/'saved-after-summary.json').write_text(json.dumps(summary(raw()),indent=2),encoding='utf-8')
w=MainWindow(save_store=SQLiteSaveStore(out/'company.sqlite'),development_mode=True,charts_enabled=False);w.resize(1366,768);w.show();QTest.qWait(80)
tabs=w.findChild(QTabWidget,'mainTabs')
for b in w.findChildren(ProductionBoardViewV2):b.pause_simulation()
inspect('restarted');w.close();QTest.qWait(50)
(out/'errors.json').write_text(json.dumps(errors,indent=2))
print(json.dumps({'case':case,'loaded_cards':len(before['cards']) if before else 8,'after_new_game_units_current':{k:v['units_is_current_state'] for k,v in after['boards'].items()},'errors':len(errors)}))
