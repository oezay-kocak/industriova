import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication,QTabWidget,QLabel,QPushButton
from PySide6.QtCore import QEvent
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.consortium_view import ConsortiumView
from production_zero.ui.theme import APP_STYLESHEET
from production_zero.core.commands import CommandBus
from production_zero.core.contracts import contract_requirements_for_products,contract_reward_quote
from production_zero.core.consortium import ConsortiumMember
from production_zero.data.definitions import load_resource_definitions
from tests.test_phase8_contract_balance import company,D,GOODS


@pytest.fixture
def views():
    app=QApplication.instance() or QApplication([]);_load_qa_fonts();app.setStyleSheet(APP_STYLESHEET)
    s=company();s.company.level=100
    R=load_resource_definitions(Path('src/production_zero/data/resource_definitions.json'))
    tabs=QTabWidget();contracts=ContractsView(s,CommandBus(s),D,R);consortium=ConsortiumView(s,D,R)
    tabs.addTab(contracts,'Contracts');tabs.addTab(consortium,'Consortium')
    yield app,tabs,s,contracts,consortium
    tabs.close();tabs.deleteLater();app.sendPostedEvents(None,QEvent.Type.DeferredDelete)


@pytest.mark.parametrize('size',[(1366,768),(1600,980),(1920,1080)])
@pytest.mark.parametrize('kind',['regular','daily','weekly'])
def test_all_manual_preview_amounts_and_exact_rewards_match_accepted(views,size,kind):
    app,tabs,s,view,_=views
    tabs.resize(*size);tabs.show();app.processEvents()
    offer=s.contracts.offers[kind][0]
    controls=view._selection_controls[kind,offer.contract_id]
    selected=GOODS[:{'regular':2,'daily':3,'weekly':4}[kind]]
    for combo,rid in zip(controls['combos'],selected):combo.setCurrentIndex(combo.findData(rid))
    expected=contract_requirements_for_products(s,offer,D,selected)
    quote=contract_reward_quote(s,offer,D,expected)
    assert [button.amount.property('requiredAmount') for button in controls['buttons']]==list(expected.values())
    assert controls['cash'].property('rewardAmount')==quote[0]
    assert controls['xp'].property('rewardAmount')==quote[1]
    assert f'{quote[0]:,.2f}' in controls['cash'].toolTip()
    controls['accept'].click();app.processEvents()
    active=s.contracts.active[kind]
    assert active.offer.requirements==expected
    assert (active.offer.reward_cash,active.offer.reward_xp)==quote


def test_stale_single_player_button_rejects_changed_capacity_quote(views):
    app,tabs,s,view,_=views
    offer=s.contracts.offers['daily'][0]
    controls=view._selection_controls['daily',offer.contract_id]
    for combo,rid in zip(controls['combos'],GOODS[:3]):combo.setCurrentIndex(combo.findData(rid))
    from dataclasses import replace
    s.cards['truck0']=replace(s.cards['truck0'],mk_level=2)
    controls['accept'].click()
    assert 'daily' not in s.contracts.active
    assert s.contracts.offers['daily'][0].contract_id!=offer.contract_id


def test_stale_consortium_button_uses_rendered_id_and_keeps_new_offer_unaccepted(views):
    app,tabs,s,_,view=views
    guild=view._service.create('Snapshot Cooperative')
    view.refresh()
    view._draft_products['daily']=list(GOODS[:3]);view._refresh_contracts(guild,'chairman')
    button=next(b for b in view.contracts_page.findChildren(QPushButton,'deliverContractButton') if b.isEnabled())
    previous=guild.contracts['daily'].contract_id
    guild.members['new']=ConsortiumMember('new','New',25)
    button.click()
    assert guild.contracts['daily'].status=='available'
    assert guild.contracts['daily'].contract_id!=previous


def test_large_rewards_are_compact_with_exact_accessible_quote(views):
    app,tabs,s,view,_=views
    panel=view._rewards_panel('weekly',1234567890123.45,987654321.25)
    for label in panel.findChildren(QLabel,'contractRewardLabel'):
        if label.property('rewardAmount') is not None:
            assert len(label.text())<=7
            assert f"{label.property('rewardAmount'):,.2f}" in label.toolTip()


def test_large_consortium_quantities_use_normalized_progress_without_int_overflow(views):
    from PySide6.QtWidgets import QProgressBar
    from production_zero.ui.contract_product import ContractProductButton
    app,tabs,s,_,view=views
    guild=view._service.create('Large Quantity Cooperative')
    contract=view._service.start_contract(guild.consortium_id,view._service.current_company_id,'daily',GOODS[:3])
    contract.requirements={rid:4e12 for rid in GOODS[:3]}
    contract.delivered={rid:qty*.42 for rid,qty in contract.requirements.items()}
    view.refresh()
    bars=view.contracts_page.findChildren(QProgressBar,'consortiumRequirementProgress')
    assert len(bars)==3 and all(bar.maximum()==1000 and bar.value()==420 for bar in bars)
    modules=view.contracts_page.findChildren(ContractProductButton)
    active=[m for m in modules if m.property('resourceId') in GOODS[:3] and not m.isEnabled()]
    assert all(len(m.amount.text())<20 and '4,000,000,000,000.00' in m.toolTip() for m in active)


def test_legacy_offer_research_change_cannot_accept_a_different_displayed_quote(views):
    from production_zero.core.contracts import ContractOffer
    app,tabs,s,view,_=views
    offer=ContractOffer('legacy-preview','daily','Legacy',{'iron_ore':10,'coal':20,'copper_ore':30},0,10,s.contracts.daily_period_index)
    s.contracts.offers['daily']=[offer];view.refresh()
    old=view._quoted_rewards['daily',offer.contract_id]
    s.research.unlocked_node_ids.add('company.contracts.s1.major')
    view._accept('daily',offer.contract_id)
    assert 'daily' not in s.contracts.active
    assert view._quoted_rewards['daily',offer.contract_id]!=old


def test_finished_offer_can_be_renewed_from_the_existing_contract_header(views):
    app,tabs,s,_,view=views
    guild=view._service.create('Renewable Cooperative')
    old=guild.contracts['daily'];old.status='expired';view.refresh()
    button=view.findChild(QPushButton,'renewConsortiumContractButton')
    assert button is not None
    button.click()
    assert guild.contracts['daily'].status=='available' and guild.contracts['daily'].contract_id!=old.contract_id


def test_large_and_stale_contribution_dialog_preserves_goods(views):
    from production_zero.persistence.sqlite_store import serialize_game_state
    app,tabs,s,_,view=views
    guild=view._service.create('Dialog Cooperative')
    contract=view._service.start_contract(guild.consortium_id,view._service.current_company_id,'daily',GOODS[:3])
    contract.requirements[GOODS[0]]=4e12;s.ensure_resource(GOODS[0]).amount=4e12
    view.refresh()
    assert not hasattr(view,'_show_contribution')
    contract.status='expired'
    view._service.renew_contract_offer(guild.consortium_id,view._service.current_company_id,'daily')
    before=serialize_game_state(s)
    with pytest.raises(PermissionError):
        view._service.contribute(guild.consortium_id,view._service.current_company_id,'daily',GOODS[0],4e12,expected_contract_id=contract.contract_id)
    assert serialize_game_state(s)==before
