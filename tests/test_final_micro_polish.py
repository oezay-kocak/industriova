"""Visible interactions for the three final dev5 adjustments."""
import hashlib
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QComboBox, QScrollArea
from test_ui_polish_interactions import app, window, board, click
from production_zero.core.freight import build_freight_facility, FREIGHT_FACILITY_START_SLOTS
from production_zero.ui.game_ui import GameButton
from production_zero.ui.research_hover import ResearchHover, hover_products
from production_zero.ui.resource_icons import ResourceIconWidget
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state


@pytest.mark.parametrize('kind', ['garage_depot', 'rail_station', 'airport', 'harbor'])
def test_eight_freight_positions_unlock_sequentially_then_next_line(window, kind):
    window.resize(1920,1080); f=board(window,'Freight'); state=f._state
    state.cash.amount=1_000_000
    facility=build_freight_facility(state.freight,kind)
    f._selected_facility_id=facility.facility_id; f.refresh(); QTest.qWait(60)
    assert facility.line_capacity==8
    track=f.findChild(QFrame,'freightBayTrack')
    assert len(track.findChildren(QFrame,'freightSlotCard'))==8
    start=FREIGHT_FACILITY_START_SLOTS[kind]; initial=state.cash.amount
    line=f.findChild(GameButton,'unlockFreightLineButton')
    assert not line.isEnabled() and line.property('slotIndex')==8
    assert line.property('unlockCost')==900
    for number in range(1,9-start):
        preview=next(c for c in f.findChildren(QFrame,'freightSlotCard') if c.property('slotIndex')==len(facility.slots))
        assert preview.property('clickEnabled')
        assert preview.property('unlockCost')==60*number
        click(window,preview); QTest.qWait(30)
        assert len(facility.slots)==start+number
    assert len(facility.slots)==8
    button=f.findChild(GameButton,'unlockFreightLineButton')
    assert button.isEnabled() and button.property('unlockCost')==900
    scroll=f.findChild(QScrollArea,'freightSlotsScroll');scroll.ensureWidgetVisible(button);QTest.qWait(40)
    click(window,button)
    assert len(facility.slots)==9 and len(f.findChildren(GameButton,'sectorPauseButton'))==2
    assert state.cash.amount==initial-(sum(60*n for n in range(1,9-start))+900)
    loaded=deserialize_game_state(serialize_game_state(state))
    assert loaded.freight.facilities[facility.facility_id]==facility


@pytest.mark.parametrize('size',[(1366,768),(1600,980),(1920,1080)])
def test_contract_hierarchy_manual_selection_and_accept_remain_usable(window,size):
    window.resize(*size);v=board(window,'Contracts');state=v._state
    state.production_progress.unlocked_production_ids.add('recipe.processor.steel')
    state.ensure_resource('steel').amount=1;v.refresh();QTest.qWait(40)
    for kind in ('regular','daily','weekly'):
        card=next(c for c in v.findChildren(QFrame,'contractCard') if c.property('kind')==kind)
        product=card.findChild(QPushButton,'contractProductSlot');accept=card.findChild(QPushButton,'acceptContractButton')
        assert product is not None and not accept.isEnabled()
        assert product.height()<=card.height()*.55
        assert '22px' in product.amount.styleSheet()
        assert accept.height()>=60 and '20px' in accept.styleSheet()
        assert all(c.height()>=72 for c in card.findChildren(QFrame,'contractRewardChip'))
        used=set()
        for combo in card.findChildren(QComboBox,'contractProductSelect'):
            index=next(i for i in range(1,combo.count()) if combo.itemData(i) not in used)
            used.add(combo.itemData(index));combo.setCurrentIndex(index)
        QTest.qWait(20)
        for product in card.findChildren(QPushButton,'contractProductSlot'):
            assert product.name.width()>=product.width()-20
            assert product.amount.width()>=product.width()-20
        assert accept.isEnabled();click(window,accept)
        assert kind in state.contracts.active and len(state.contracts.offers[kind])==1
    assert v._board_scroll.horizontalScrollBar().maximum()==0


@pytest.mark.parametrize('size',[(1366,768),(1600,980),(1920,1080)])
def test_largest_research_list_icons_match_products_and_fallback_renders(window,size,monkeypatch):
    from production_zero.core.research import research_domains
    window.resize(*size);v=board(window,'Research');domains=research_domains()
    domain=max(set(domains.values()),key=lambda d:list(domains.values()).count(d));tid='industry.'+domain
    popup=ResearchHover(window);popup.display(v.navigation_buttons[tid],window._session_state,tid);QTest.qWait(35)
    expected={rid for rid,_,_ in hover_products(window._session_state,tid)}
    icons=popup.findChildren(ResourceIconWidget,'researchHoverProductIcon')
    assert {i.resource_id for i in icons}==expected
    assert window.rect().contains(popup.geometry())
    for icon in icons:
        label=icon.parentWidget().findChild(QLabel,'researchHoverProduct')
        assert label.property('resourceId')==icon.resource_id
        assert icon.geometry().right()<label.geometry().left()
    scroll=popup.findChild(QScrollArea,'researchHoverProducts')
    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum());QTest.qWait(20)
    monkeypatch.setattr('production_zero.ui.resource_icons.has_resource_raster',lambda rid:False)
    assert all(not i.grab().isNull() for i in icons)
    popup.close();popup.deleteLater()


def test_dev5_default_paths_ignore_both_previous_industriova_and_production_zero(app,tmp_path,monkeypatch):
    from production_zero.persistence.paths import default_company_save_path,default_save_directory
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    old=[]
    for folder in ('Industriova/saves','Production Zero/saves'):
        p=tmp_path/folder/'company.sqlite';p.parent.mkdir(parents=True);p.write_bytes(b'old playtest save must not be opened')
        old.append((p,hashlib.sha256(p.read_bytes()).hexdigest()))
    assert default_save_directory()==tmp_path/'Industriova/playtests/contract-auto-test/saves'
    assert not default_company_save_path().exists()
    from production_zero.ui.main_window import MainWindow
    from production_zero.persistence.sqlite_store import SQLiteSaveStore
    default_save_directory().mkdir(parents=True)
    w=MainWindow(save_store=SQLiteSaveStore(default_company_save_path()),development_mode=False)
    assert w._session_state.cash.amount==1250 and len(w._session_state.cards)==8
    assert w._session_state.freight.facilities['garage-1'].line_capacity==8
    w.close();w.deleteLater()
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==sha for p,sha in old)
