"""Actual MainWindow P8 scenes; synthetic formatting states, isolated AppData."""
import os,sys,json,runpy,hashlib
from pathlib import Path
from dataclasses import replace,asdict
ROOT=Path.cwd();scale=int(os.environ.get('QT_SCALE_FACTOR','1'))
OUT=ROOT/os.environ.get('PHASE8_CAPTURE_ROOT','artifacts/phase8/screenshots')/f'dpi{scale}';OUT.mkdir(parents=True,exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen',LOCALAPPDATA=str(OUT/'appdata'),APPDATA=str(OUT/'appdata'))
sys.argv=['fixture','--source',str(ROOT),'--stage','visual-fixture']
f=runpy.run_path(str(ROOT/'scripts/phase8_contract_simulation.py'),run_name='fixture')
company=f['company'];PRODUCTS=f['PRODUCTS'];D=f['D']
from PySide6.QtWidgets import QApplication,QTabWidget,QLabel,QProgressBar
from PySide6.QtCore import QTimer,QEvent
from PySide6.QtTest import QTest
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow,_copy_state
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.consortium_view import ConsortiumView
from production_zero.core.consortium import ConsortiumMember,ConsortiumService
app=QApplication([]);_load_qa_fonts()
w=MainWindow(development_mode=False)
for timer in w.findChildren(QTimer):timer.stop()
tabs=w.findChild(QTabWidget,'mainTabs');personal=w.findChild(ContractsView);cooperative=w.findChild(ConsortiumView)
rows=[];terms=[];size=None
def drain():
    for _ in range(3):app.processEvents();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
def shot(name):
    # Let native Qt progress transitions reach the asserted state before grab.
    drain();QTest.qWait(350);drain()
    pix=w.grab();path=OUT/f'{name}-{size[0]}x{size[1]}.png';assert pix.save(str(path))
    bars=[dict(value=b.value(),maximum=b.maximum(),position=[b.mapTo(w,b.rect().topLeft()).x(),b.mapTo(w,b.rect().topLeft()).y()],size=[b.width(),b.height()]) for b in w.findChildren(QProgressBar,'consortiumRequirementProgress') if b.isVisible()]
    rows.append(dict(file=path.relative_to(ROOT).as_posix(),logical_size=[w.width(),w.height()],pixels=[pix.width(),pix.height()],scale=scale,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),visible_requirement_bars=bars))
def reset():
    prepared,info=company('late',10)
    prepared.cash.amount=1234567890123.45
    _copy_state(w._session_state,prepared)
    personal.reset_for_state_change()
    cooperative._workspace_signature=None;cooperative._render_signature=None
    cooperative._draft_products={'daily':[None]*3,'weekly':[None]*4}
    w._global_header.refresh()
    return w._session_state
for size in ((1366,768),(1600,980),(1920,1080)):
    w.resize(*size);w.show();drain()
    s=reset();tabs.setCurrentWidget(personal);drain()
    previews={}
    for kind in ('regular','daily','weekly'):
        offer=s.contracts.offers[kind][0]
        controls=personal._selection_controls[kind,offer.contract_id]
        selected=PRODUCTS['late'][:{'regular':2,'daily':3,'weekly':4}[kind]]
        for combo,rid in zip(controls['combos'],selected):combo.setCurrentIndex(combo.findData(rid))
        previews[kind]=dict(requirements={rid:button.amount.property('requiredAmount') for rid,button in zip(selected,controls['buttons'])},cash=controls['cash'].property('rewardAmount'),xp=controls['xp'].property('rewardAmount'))
    shot('contracts-preview')
    for kind in ('regular','daily','weekly'):
        offer=s.contracts.offers[kind][0]
        personal._selection_controls[kind,offer.contract_id]['accept'].click()
        accepted=s.contracts.active[kind].offer
        assert accepted.requirements==previews[kind]['requirements']
        assert (accepted.reward_cash,accepted.reward_xp)==(previews[kind]['cash'],previews[kind]['xp'])
    shot('contracts-accepted')
    for active in s.contracts.active.values():active.delivered={rid:qty*.42 for rid,qty in active.offer.requirements.items()}
    personal.refresh();shot('contracts-partial')
    for active in s.contracts.active.values():
        active.offer=replace(active.offer,requirements={rid:qty*1e8 for rid,qty in active.offer.requirements.items()},reward_cash=active.offer.reward_cash*1e8,reward_xp=active.offer.reward_xp*1e8)
        active.delivered={rid:qty*.42 for rid,qty in active.offer.requirements.items()}
    personal.refresh();shot('contracts-large-numbers')
    for active in s.contracts.active.values():active.delivered=dict(active.offer.requirements);active.status='completed'
    personal.refresh();shot('contracts-completed')
    terms.append(dict(size=size,scale=scale,personal_previews=previews))
    s=reset();tabs.setCurrentWidget(cooperative)
    guild=cooperative._service.create('International Heavy Industry Cooperative')
    for i in range(1,5):
        cid=f'visual-member-{i}';guild.members[cid]=ConsortiumMember(cid,f'Specialized Industry Partner {i}',100)
        remote,_=company('late',2);remote.consortium.current_company_id=cid
        cooperative._service.update_capacity_snapshot(cid,remote)
    cooperative.refresh();cooperative.member_tabs.setCurrentWidget(cooperative.contracts_page)
    for kind in ('daily','weekly'):cooperative._draft_products[kind]=list(PRODUCTS['late'][:3 if kind=='daily' else 4])
    cooperative._refresh_contracts(guild,'chairman');shot('consortium-preview')
    for kind in ('daily','weekly'):
        cooperative._service.start_contract(guild.consortium_id,cooperative._service.current_company_id,kind,tuple(cooperative._draft_products[kind]))
    cooperative.refresh();shot('consortium-accepted')
    for contract in guild.contracts.values():
        contract.delivered={rid:qty*.42 for rid,qty in contract.requirements.items()}
        contract.contributions={s.consortium.current_company_id:{rid:qty*.28 for rid,qty in contract.requirements.items()},'visual-member-1':{rid:qty*.14 for rid,qty in contract.requirements.items()}}
    cooperative.refresh();shot('consortium-partial')
    for contract in guild.contracts.values():
        contract.requirements={rid:qty*1e8 for rid,qty in contract.requirements.items()}
        contract.delivered={rid:qty*.42 for rid,qty in contract.requirements.items()}
        contract.personal_reward=replace(contract.personal_reward,cash=contract.personal_reward.cash*1e8,company_xp=contract.personal_reward.company_xp*1e8)
        contract.contributions={s.consortium.current_company_id:{rid:qty*.28 for rid,qty in contract.requirements.items()},'visual-member-1':{rid:qty*.14 for rid,qty in contract.requirements.items()}}
    cooperative._render_signature=None;cooperative.refresh();shot('consortium-large-numbers')
    for contract in guild.contracts.values():
        contract.status='completed';contract.delivered=dict(contract.requirements)
        contract.contributions={s.consortium.current_company_id:{rid:qty*.7 for rid,qty in contract.requirements.items()},'visual-member-1':{rid:qty*.3 for rid,qty in contract.requirements.items()}}
        contract.reward_delivered_member_ids={s.consortium.current_company_id,'visual-member-1'}
    cooperative.refresh();shot('consortium-completed')
    for contract in guild.contracts.values():contract.status='expired'
    cooperative.refresh();shot('consortium-expired')
(OUT/'captures.json').write_text(json.dumps(dict(captures=rows,terms=terms,assumptions='Actual MainWindow and controls, all timers stopped. Preview/accept values asserted. Progress/status and 100-million-fold huge values are deliberate isolated presentation fixtures, not economically earned results. No personal save/store.'),indent=2),encoding='utf8')
w.close();drain();print(json.dumps(dict(scale=scale,captures=len(rows))),flush=True)
