import pytest
from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QTabWidget, QFrame, QPushButton, QLabel, QScrollArea
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow
from production_zero.ui.consortium_view import ConsortiumView, ConfirmConsortiumDialog
from production_zero.ui.contract_product import ContractProductButton
from production_zero.ui.material_frame import MaterialFrame
from production_zero.core.consortium import OPEN, MEMBER, CHAIRMAN, BOARD_MEMBER, ConsortiumMember
from production_zero.core.progression import production_options

@pytest.fixture
def scene():
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    window = MainWindow(development_mode=False)
    view = window.findChild(ConsortiumView)
    window.findChild(QTabWidget, 'mainTabs').setCurrentWidget(view)
    for option in production_options(view._definitions):
        view._state.production_progress.unlocked_production_ids.add(option.production_id)
        view._state.ensure_resource(option.output_resource).amount = 25
    guild = view._service.create('Final UX Industries', OPEN, 1)
    view.refresh()
    window.resize(1366,768); window.show()
    yield app, window, view, guild
    window.close(); window.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

def settle(app):
    for _ in range(5): app.processEvents()

@pytest.mark.parametrize('size', [(1366,768),(1600,980),(1920,1080)])
def test_two_contract_sections_fit_and_route_independently(scene, size):
    app, window, view, guild = scene
    window.resize(*size)
    view.member_tabs.setCurrentWidget(view.contracts_page)
    for kind in ('daily','weekly'):
        view._draft_products[kind] = list(view._service.contract_candidates(guild.consortium_id, kind)[:3 if kind=='daily' else 4])
    view._refresh_contracts(guild, CHAIRMAN); settle(app)
    assert (window.width(), window.height()) == size
    assert view.contracts_layout.count() == 2
    daily, weekly = [view.contracts_layout.itemAt(i).widget() for i in range(2)]
    assert daily.geometry().bottom() < weekly.geometry().top()
    assert all(isinstance(page.widget(), MaterialFrame) for page in (view.overview_page, view.contracts_page,view.members_page,view.progression_page))
    assert view.contracts_page.horizontalScrollBar().maximum() == 0
    if size[1] >= 980: assert view.contracts_page.verticalScrollBar().maximum() == 0
    for section, count in ((daily,3),(weekly,4)):
        modules = section.findChildren(ContractProductButton)
        assert len(modules) == count
        for module in modules:
            assert module.rect().contains(module.amount.mapTo(module,module.amount.rect().bottomRight()))
    weekly.findChildren(ContractProductButton)[0].click()
    assert view._selected_contract_kind == 'weekly' and view._product_picker is not None
    view._close_product_picker()
    # Starting Weekly cannot accidentally start Daily due to loop callbacks.
    next(b for b in weekly.findChildren(QPushButton) if b.text() == 'START CONTRACT').click()
    assert guild.contracts['weekly'].status == 'active' and guild.contracts['daily'].status == 'available'
    settle(app)
    active = view.contracts_layout.itemAt(1).widget()
    modules = active.findChildren(ContractProductButton)
    assert len(modules) == 4 and len({m.mapTo(active,QPoint(0,0)).y() for m in modules}) == 1
    assert view.contracts_page.horizontalScrollBar().maximum() == 0

@pytest.mark.parametrize('count',[1,2,10,25,50])
def test_roster_is_compact_scrollable_and_management_reachable(scene,count):
    app, window, view, guild = scene
    guild.member_capacity = max(10,count)
    for i in range(1,count): guild.members[str(i)] = ConsortiumMember(str(i),f'Company {i}',i+1)
    view.refresh(); view.member_tabs.setCurrentWidget(view.members_page); settle(app)
    housing = next(h for h in view.members_page.findChildren(QFrame,'consortiumRosterHousing') if h.isVisible())
    heading = housing.findChild(QFrame,'consortiumRosterHeader')
    roster = housing.findChild(QScrollArea,'consortiumRosterScroll')
    assert heading.height() == 32
    assert len(view._member_rows) == count
    assert all(row.height()==48 for row in view._member_rows.values())
    assert view.members_page.verticalScrollBar().maximum() == 0
    assert (roster.verticalScrollBar().maximum()>0) == (count*49-1>roster.viewport().height())
    assert not view.members_page.findChildren(QFrame,'consortiumMemberActions')
    assert not any('PERMANENT ACTION' in label.text() for label in view.members_page.findChildren(QLabel))
    view.members_page.verticalScrollBar().setValue(view.members_page.verticalScrollBar().maximum()); settle(app)
    button = next(b for b in view.members_page.findChildren(QPushButton) if b.isVisible() and b.text()=='DISBAND CONSORTIUM')
    assert view.members_page.viewport().rect().contains(button.mapTo(view.members_page.viewport(),button.rect().center()))

def test_context_menu_permissions_profile_and_promotion(scene):
    app, window, view, guild = scene
    guild.members['peer'] = ConsortiumMember('peer','Peer Company',5)
    view.refresh(); view.member_tabs.setCurrentWidget(view.members_page); settle(app)
    profile = []
    view.profile_requested.connect(lambda group, member: profile.append(member.company_id))
    row = view._member_rows['peer']
    row.findChild(QPushButton,'consortiumProfileLink').click()
    assert profile == ['peer']
    window._profile_view.close()
    event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(5,5),row.mapToGlobal(QPoint(5,5)))
    QApplication.sendEvent(row,event); settle(app)
    menu = view._context_menu
    actions = {a.text():a for a in menu.actions()}
    assert 'TRANSFER LEADERSHIP' in actions and 'PROMOTE TO BOARD MEMBER' in actions
    menu.hide()
    actions['PROMOTE TO BOARD MEMBER'].trigger()
    assert guild.members['peer'].role == BOARD_MEMBER
    menu = view._member_menu(guild, MEMBER, guild.chairman())
    assert [a.text() for a in menu.actions()] == ['OPEN PLAYER PROFILE']
    menu.deleteLater()

def test_disband_cancel_and_confirm_and_leave_consequences(scene):
    app, window, view, guild = scene
    view._confirm_disband(guild); settle(app)
    dialog = next(d for d in window.centralWidget().findChildren(ConfirmConsortiumDialog) if d.isVisible())
    body = dialog.findChild(QLabel,'consortiumConfirmMessage')
    assert body.height() >= body.heightForWidth(body.width())
    assert 'not returned' in body.text() and 'XP' in body.text()
    dialog.reject()
    assert guild.consortium_id in view._state.consortium.consortiums
    guild.members['peer'] = ConsortiumMember('peer','Peer Company',5)
    view._state.consortium.current_company_id = 'peer'; view.refresh()
    view._confirm_leave(guild); settle(app)
    dialog = next(d for d in window.centralWidget().findChildren(ConfirmConsortiumDialog) if d.isVisible())
    assert 'ends immediately' in dialog.findChild(QLabel,'consortiumConfirmMessage').text()
    next(b for b in dialog.findChildren(QPushButton) if b.text()=='LEAVE CONSORTIUM').click()
    assert 'peer' not in guild.members
    view._state.consortium.current_company_id = guild.chairman().company_id; view.refresh()
    view._confirm_disband(guild); settle(app)
    dialog = next(d for d in window.centralWidget().findChildren(ConfirmConsortiumDialog) if d.isVisible())
    next(b for b in dialog.findChildren(QPushButton) if b.text()=='DISBAND').click()
    assert guild.consortium_id not in view._state.consortium.consortiums
