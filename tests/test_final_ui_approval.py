"""Headless rendered layout and real Qt unlock interactions for dev6."""
import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QWidget
from test_ui_polish_interactions import app, window, board, click
from production_zero.ui.factory_view_v2 import FactoryV2LockedLine, FactoryV2LinePlate


@pytest.mark.parametrize('size',[(1366,768),(1600,980),(1920,1080)])
@pytest.mark.parametrize('name',['Resources','Factory','Energy'])
def test_only_next_expansion_is_visible_and_clicks_reveal_successors(window,size,name):
    window.resize(*size);b=board(window,name);unit=b._units[b._selected_hall_id]
    b._state.cash.amount=100000;b.refresh_runtime()
    original=[(line.line_id,line.unlock_cost) for line in unit.production_lines]
    for expected in [line for line in unit.production_lines if not line.unlocked]:
        QTest.qWait(90)
        panels=b.findChildren(FactoryV2LockedLine)
        assert len(panels)==1 and panels[0].property('lineId')==expected.line_id
        assert isinstance(panels[0].findChild(QLabel,'expansionTrackIdentifier'),FactoryV2LinePlate)
        button=panels[0]._unlock_button;assert button.property('unlockCost')==expected.unlock_cost
        scroll=b.findChild(QScrollArea,'factoryV2Scroll');scroll.ensureWidgetVisible(button);QTest.qWait(25)
        before=b._state.cash.amount;click(window,button)
        assert expected.unlocked and b._state.cash.amount==before-expected.unlock_cost
    assert not b.findChildren(FactoryV2LockedLine)
    assert [(line.line_id,line.unlock_cost) for line in unit.production_lines]==original


@pytest.mark.parametrize('size',[(1366,768),(1600,980),(1920,1080)])
def test_weekly_hint_and_reward_pairs_are_centered_without_affecting_selection(window,size):
    window.resize(*size);v=board(window,'Contracts');QTest.qWait(30)
    weekly=next(c for c in v.findChildren(QFrame,'contractCard') if c.property('kind')=='weekly')
    hint=weekly.findChild(QLabel,'contractRequirementLabel')
    assert hint is not None and '4 eligible unique products' in hint.text()
    assert hint.alignment() & Qt.AlignmentFlag.AlignHCenter
    assert hint.alignment() & Qt.AlignmentFlag.AlignVCenter
    assert '20px' in hint.styleSheet() and '900' in hint.styleSheet()
    for chip in v.findChildren(QFrame,'contractRewardChip'):
        icon=chip.findChild(QLabel,'contractRewardIcon');value=chip.findChild(QLabel,'contractRewardLabel')
        assert abs((icon.x()+value.geometry().right()+1)/2-chip.width()/2)<=2
        assert value.x()-icon.geometry().right()-1==6
        assert abs(icon.geometry().center().y()-chip.rect().center().y())<=2
    assert not v._state.contracts.active


@pytest.mark.parametrize('size',[(1366,768),(1600,980),(1920,1080)])
def test_freight_uses_transparent_board_layers_and_preserves_eight_slots(window,size):
    window.resize(*size);v=board(window,'Freight');QTest.qWait(60)
    scroll=v.findChild(QScrollArea,'freightSlotsScroll')
    layers=[scroll,scroll.viewport(),scroll.widget(),*v.findChildren(QWidget,'freightSlotGridHost')]
    assert scroll.frameShape()==QFrame.Shape.NoFrame
    for layer in layers:
        assert not layer.autoFillBackground()
        assert layer.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert layer.grab().toImage().pixelColor(0,0).alpha()==0
    assert len(v.findChildren(QFrame,'freightSlotCard'))==8
    assert len(v._state.freight.facilities['garage-1'].slots)==3
    image=scroll.viewport().grab().toImage()
    assert image.pixelColor(0,0).alpha()==0
