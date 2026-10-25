import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton
from production_zero.ui.resource_icons import ResourceIconWidget
from production_zero.core.state import GameState
from production_zero.core.commands import CommandBus
from production_zero.core.packs import grant_pack, DAILY_MINI_PACK, FULL_PACK
from production_zero.core.enums import CardKind
from production_zero.data.definitions import load_card_definitions
from production_zero.ui.packs_view import PacksView, BoosterPackTileFrame
from production_zero.ui.theme import APP_STYLESHEET


def _wait_until(predicate, *, timeout_ms=1000, step_ms=10):
    elapsed_ms = 0
    while elapsed_ms < timeout_ms and not predicate():
        QTest.qWait(step_ms)
        elapsed_ms += step_ms
    return predicate()


@pytest.fixture
def view():
    app = QApplication.instance() or QApplication([])
    for font in ('segoeui.ttf', 'segoeuib.ttf', 'bahnschrift.ttf', 'agencyr.ttf', 'agencyb.ttf'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + font)
    app.setStyleSheet(APP_STYLESHEET)
    state = GameState(rng_seed=42)
    definitions = load_card_definitions(Path('src/production_zero/data/game_definitions.json'))
    widget = PacksView(state, CommandBus(state), definitions)
    widget.resize(1180, 690)
    widget.show()
    app.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()

@pytest.mark.parametrize('count', [0, 1, 2, 3, 4, 7])
def test_pack_gallery(view, count):
    for _ in range(count):
        grant_pack(view._state, DAILY_MINI_PACK, 'test')
    view.refresh(force=True)
    QApplication.processEvents()
    tiles = [view._grid.itemAt(i).widget() for i in range(view._grid.count())]
    packs = [t for t in tiles if isinstance(t, BoosterPackTileFrame)]
    assert len(packs) == count
    assert len({t.property('packId') for t in packs}) == count
    assert not view.findChildren(QLabel, 'packsHeaderMetricValue')
    assert not view.findChildren(QLabel, 'packsUnopenedCount')
    assert view.findChild(QFrame, 'packsHeader')._monochrome is False
    assert view.findChild(QFrame, 'packsUnopenedHeader') is None
    if count == 0:
        empty = view.findChild(QLabel, 'emptyStateTitle')
        assert empty.text() == 'NO UNOPENED PACKS'
        assert view.findChild(QLabel, 'emptyStateMessage').text().startswith('Complete contracts')
        icon = view.findChild(ResourceIconWidget, 'emptyStateIcon')
        assert icon is None or icon.isHidden()
    if count <= 4:
        assert view._pack_scroll.verticalScrollBar().maximum() == 0
    Path('artifacts').mkdir(exist_ok=True)
    view.grab().save(f'artifacts/packs_polish_{count}.png')


def test_empty_and_populated_gallery_share_the_light_chassis(view):
    view.refresh(force=True)
    QApplication.processEvents()
    empty_corner = view._pack_scroll.viewport().grab().toImage().pixelColor(4, 4)
    grant_pack(view._state, DAILY_MINI_PACK, 'same-chassis')
    view.refresh(force=True)
    QApplication.processEvents()
    populated_corner = view._pack_scroll.viewport().grab().toImage().pixelColor(4, 4)
    assert empty_corner == populated_corner
    assert view.findChildren(BoosterPackTileFrame)

@pytest.mark.parametrize('pack_type,category,count', [(DAILY_MINI_PACK,'general',3),(FULL_PACK,'freight',6)])
def test_manual_reveal_and_exactly_once(view, pack_type, category, count):
    pack_id = grant_pack(view._state, pack_type, 'test')
    other_id = grant_pack(view._state, DAILY_MINI_PACK, 'test')
    view.refresh()
    QApplication.processEvents()
    tile = next(t for t in view.findChildren(BoosterPackTileFrame) if t.property('packId') == pack_id)
    tile._category_select.setCurrentIndex(tile._category_select.findData(category))
    assert tile._selected_category_id == category
    baseline = len(view._state.cards)
    tile._open_button.click()
    tile._open_button.click()
    view._open_pack(other_id, 'general')
    assert view._flow_state == 'opening'
    assert view.findChild(QLabel, 'packResultsLabel') is None
    assert len(view._state.cards) == baseline + count
    assert len(view._state.packs.unopened) == 1
    assert view._state.packs.opened_count == 1
    assert not view._confirm.isVisible()
    assert all(not c.is_revealed and not c.front.isVisible() for c in view._reveal_cards)
    if category == 'freight':
        assert all(c.card_kind == CardKind.FREIGHT for c in view._active_cards)
    view._confirm_collect()
    assert view._stack.currentIndex() == 1
    first = view._reveal_cards[0]
    first.reveal()
    assert not first._flipping  # cannot reveal an undealt card
    QTest.qWait(1900)
    assert all(c.is_dealt and not c.is_revealed for c in view._reveal_cards)
    assert view._flow_state == 'cards_dealt'
    view.grab().save(f'artifacts/packs_polish_backs_{count}.png')
    QTest.mouseClick(first, Qt.MouseButton.LeftButton)
    QTest.mouseClick(first, Qt.MouseButton.LeftButton)
    assert first._flip.duration() == 220
    assert first._flipping
    assert not first.is_revealed
    assert _wait_until(lambda: first.is_revealed, timeout_ms=750)
    assert sum(c.is_revealed for c in view._reveal_cards) == 1
    assert not view._confirm.isVisible()
    ids = [id(c) for c in view._reveal_cards]
    view.resize(800, 690)
    view.refresh(force=True)
    QApplication.processEvents()
    assert ids == [id(c) for c in view._reveal_cards]
    assert first.is_revealed
    view.resize(1180, 690)
    QApplication.processEvents()
    for card in view._reveal_cards[1:]:
        QTest.mouseClick(card, Qt.MouseButton.LeftButton)
    assert not view._confirm.isVisible()
    assert _wait_until(
        lambda: (
            view._flow_state == 'ready_to_confirm'
            and view._confirm.isVisible()
            and all(card.front.isVisible() for card in view._reveal_cards)
        ),
        timeout_ms=1500,
    )
    assert view._flow_state == 'ready_to_confirm'
    assert view._confirm.isVisible()
    assert all(c.front.isVisible() for c in view._reveal_cards)
    assert len({c.y() for c in view._reveal_cards}) == 1
    assert all(c.width() == 166 and c.height() == 224 for c in view._reveal_cards)
    left = min(c.x() for c in view._reveal_cards)
    right = max(c.x()+c.width() for c in view._reveal_cards)
    assert abs(left - (view._result_container.width()-right)) < 25
    view.grab().save(f'artifacts/packs_polish_fronts_{count}.png')
    view._confirm.click()
    view._confirm_collect()
    view._open_pack(pack_id, category)
    assert view._stack.currentIndex() == 0
    assert len(view._state.cards) == baseline + count
    assert view._state.packs.opened_count == 1
    assert not view._reveal_cards
    # A subsequent pack gets a fresh reveal, without inheriting earlier cards.
    view._open_pack(other_id, 'general')
    assert len(view._reveal_cards) == 3
    assert not any(c.is_revealed for c in view._reveal_cards)
    assert len(view._state.cards) == baseline + count + 3


def test_navigation_and_disposal(view):
    pack_id = grant_pack(view._state, DAILY_MINI_PACK, 'test')
    view._open_pack(pack_id, 'general')
    QTest.keyClick(view, Qt.Key.Key_Escape)
    view.hide()
    QTest.qWait(800)
    view.show()
    assert view._stack.currentIndex() == 1
    assert len(view._reveal_cards) == 3
    assert not view._confirm.isVisible()
    view.close()



@pytest.mark.parametrize('category', ['general', 'extraction', 'energy', 'processing', 'freight'])
def test_category_survives_grid_rebuild(view, category):
    pack_id = grant_pack(view._state, FULL_PACK, 'test')
    view.refresh()
    tile = view._grid.itemAt(0).widget()
    tile._choose_category(tile._category_select.findData(category))
    view.resize(800, 690)
    view.refresh(force=True)
    QApplication.processEvents()
    tile = view._grid.itemAt(0).widget()
    assert tile._selected_category_id == category
    tile._open_button.click()
    assert view._state.packs.opened_count == 1
    from production_zero.core.packs import _candidate_definitions
    allowed = {d.definition_id for d in _candidate_definitions(view._definitions, category)}
    assert all(c.definition_id in allowed for c in view._active_cards)


def test_destroy_during_deal_cancels_owned_work(view):
    from PySide6.QtCore import QEvent
    from shiboken6 import isValid
    # A separate child-owned view allows explicit destruction inside the fixture.
    child = PacksView(view._state, view._bus, view._definitions)
    child.setParent(view)
    pack_id = grant_pack(view._state, FULL_PACK, 'test')
    child._open_pack(pack_id, 'general')
    timer = child._deal_timer
    card = child._reveal_cards[0]
    child.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert not isValid(timer)
    assert not isValid(card)
    QTest.qWait(500)
    assert view._state.packs.opened_count == 1

@pytest.mark.parametrize('pack_type,count', [(DAILY_MINI_PACK, 3), (FULL_PACK, 6)])
def test_reveal_canvas_stays_stable_through_confirmation(view, pack_type, count):
    from PySide6.QtCore import QPoint, QRect
    pack_id = grant_pack(view._state, pack_type, 'test')
    view.refresh()
    QApplication.processEvents()

    def canvas_rect(scroll):
        return QRect(scroll.mapTo(view, QPoint()), scroll.size())

    before = canvas_rect(view._pack_scroll)
    view._open_pack(pack_id, 'general')
    # Synchronous return already exposes final geometry and the activation layer.
    assert view._focus.isVisible()
    result = canvas_rect(view._result_scroll)
    assert (result.left(), result.right(), result.bottom()) == (before.left(), before.right(), before.bottom())
    assert result.top() > before.top()
    assert view._focus.geometry() == view._result_scroll.viewport().rect()
    assert view._confirm.parentWidget() is view._result_container
    assert view._stack.widget(1).layout().indexOf(view._confirm) == -1
    reference = (canvas_rect(view._result_scroll), view._result_scroll.viewport().geometry())
    def verify_stable():
        QApplication.processEvents()
        assert (canvas_rect(view._result_scroll), view._result_scroll.viewport().geometry()) == reference

    verify_stable()
    QTest.qWait(1900)
    verify_stable()
    positions = [card.geometry() for card in view._reveal_cards]
    view._reveal_cards[0].reveal()
    QTest.qWait(800)
    verify_stable()
    assert not view._confirm.isVisible()
    for card in view._reveal_cards[1:]:
        card.reveal()
    QTest.qWait(800)
    verify_stable()
    assert [card.geometry() for card in view._reveal_cards] == positions
    assert view._confirm.isVisible()
    button = view._confirm.geometry()
    bottom = max(card.geometry().bottom() for card in view._reveal_cards)
    assert 20 <= button.top() - bottom <= 30
    assert abs(button.center().x() - view._result_container.rect().center().x()) <= 1
    assert view._result_container.rect().contains(button)
    assert view._result_scroll.verticalScrollBar().maximum() == 0
    # Also preserve visibility-independent geometry when a narrow viewport wraps.
    view.resize(800, 690)
    QApplication.processEvents()
    narrow = canvas_rect(view._result_scroll)
    maximum = view._result_scroll.verticalScrollBar().maximum()
    view._confirm.hide()
    QApplication.processEvents()
    assert canvas_rect(view._result_scroll) == narrow
    assert view._result_scroll.verticalScrollBar().maximum() == maximum
    view._confirm.show()
    assert view._confirm.y() > max(card.geometry().bottom() for card in view._reveal_cards)


def test_unsealed_has_readable_hold_before_dealing(view):
    from production_zero.ui.pack_reveal import OPENING_TOTAL_MS
    pack_id = grant_pack(view._state, DAILY_MINI_PACK, 'test')
    view._open_pack(pack_id, 'general')
    assert OPENING_TOTAL_MS == 1200
    assert view._deal_timer.interval() == OPENING_TOTAL_MS
    animation = view._focus._animation
    assert animation.duration() == OPENING_TOTAL_MS
    view._deal_timer.stop()
    animation.pause()
    for time, opacity in [(0, 0), (125, .5), (250, 1), (600, 1), (950, 1), (1075, .5)]:
        animation.setCurrentTime(time)
        assert view._focus._progress == pytest.approx(opacity)
        assert not any(card.is_dealt for card in view._reveal_cards)
    animation.setCurrentTime(600)
    view.grab().save('artifacts/packs_micro_unsealed_hold.png')
    animation.setCurrentTime(1200)
    assert view._focus._progress == 0


def test_rarity_feedback_is_intentionally_ordered():
    from production_zero.ui.pack_reveal import RARITY_FEEDBACK
    values = [RARITY_FEEDBACK[r] for r in ('common', 'uncommon', 'rare', 'epic', 'legendary')]
    for field in ('duration_ms', 'border_alpha', 'glow_alpha', 'border_width'):
        assert all(getattr(a, field) < getattr(b, field) for a, b in zip(values, values[1:]))
    assert [v.lift_px for v in values] == [0, 0, 1, 2, 3]


@pytest.mark.parametrize('rarity', ['common', 'uncommon', 'rare', 'epic', 'legendary'])
def test_rarity_feedback_uses_existing_animation_and_preserves_geometry(view, rarity):
    from production_zero.core.cards import create_card_instance
    from production_zero.core.enums import Rarity
    from production_zero.ui.pack_reveal import RevealCard, RARITY_FEEDBACK
    card = create_card_instance('feedback-test', 'machine.extractor', CardKind.MACHINE, Rarity(rarity))
    wrapper = RevealCard(view._result_card_tile(card), rarity, view)
    wrapper.move(50, 180)
    wrapper.show()
    wrapper.deal()
    wrapper._deal.setCurrentTime(wrapper._deal.duration())
    geometry = wrapper.geometry()
    wrapper.reveal()
    wrapper._flip.setCurrentTime(220)
    assert wrapper.is_revealed
    assert wrapper._feedback.duration() == RARITY_FEEDBACK[rarity].duration_ms
    if rarity != 'common':
        wrapper._feedback.pause()
        wrapper._feedback.setCurrentTime(wrapper._feedback.duration() // 2)
        assert wrapper._pulse == pytest.approx(.5)
        assert not wrapper.front.isVisible()
        wrapper.grab().save(f'artifacts/packs_micro_{rarity}_pulse.png')
        wrapper._feedback.setCurrentTime(wrapper._feedback.duration())
    assert wrapper.front.isVisible()
    assert wrapper.geometry() == geometry
    assert wrapper._snapshot is None
