import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from dataclasses import asdict, replace
from pathlib import Path
import pytest
from PySide6.QtCore import QEvent, QRectF
from PySide6.QtGui import QFontMetrics, QFontDatabase
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QLabel
from production_zero.core.cards import create_card_instance
from production_zero.core.commands import CommandBus
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.inventory import build_card_inventory_rows
from production_zero.core.packs import PACK_CATEGORIES, FULL_PACK, DAILY_MINI_PACK, grant_pack, open_pack
from production_zero.core.state import GameState
from production_zero.core.definitions import MachineDefinition
from production_zero.core.supply import buy_common_supply_card, common_supply_offers, refresh_supply
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state
from production_zero.ui.supply_view import SupplyView, SupplyOfferCardFrame
from production_zero.ui.theme import APP_STYLESHEET, Theme


def test_all_card_sources_exclude_recipes_and_legacy_save_is_clean():
    definitions = load_card_definitions(Path('src/production_zero/data/game_definitions.json'))
    state = GameState(rng_seed=42)
    assert {kind.value for kind in CardKind} == {'energy', 'freight', 'machine'}
    assert all(not key.startswith('recipe.') for key in definitions)
    assert 'recipes' not in {category.category_id for category in PACK_CATEGORIES}
    refresh_supply(state, definitions)
    assert not hasattr(state.supply, 'daily_offers')
    assert len(state.supply.freight_daily_offers) == len(state.supply.machine_daily_offers) == 4
    for offer in common_supply_offers(definitions):
        assert offer.card_kind in CardKind
    for category in PACK_CATEGORIES:
        for pack_type in (FULL_PACK, DAILY_MINI_PACK):
            pack_id = grant_pack(state, pack_type, 'polish-test')
            assert all(card.card_kind in CardKind for card in open_pack(state, definitions, pack_id, category.category_id))
    payload = serialize_game_state(state)
    legacy = dict(asdict(next(iter(state.cards.values()))), card_id='legacy-recipe', card_kind='recipe', definition_id='recipe.processor.iron')
    payload['cards']['legacy-recipe'] = legacy
    payload['halls']['legacy-hall'] = dict(hall_id='legacy-hall', name='Legacy', slot_count=1, specialization=None, slots=[dict(index=0, card_id='legacy-recipe')])
    payload['packs']['last_opened_cards'].append(legacy)
    payload['supply']['daily_offers'] = [{'card_kind': 'recipe', 'definition_id': 'recipe.processor.iron'}]
    payload['supply']['daily_period_index'] = 0
    cleaned = deserialize_game_state(payload)
    assert 'legacy-recipe' not in cleaned.cards
    assert cleaned.halls['legacy-hall'].slots[0].card_id is None
    with pytest.raises(ValueError):
        create_card_instance('retired', 'recipe.processor.iron', 'recipe', Rarity.COMMON)
    assert all(card.card_kind in CardKind for card in cleaned.packs.last_opened_cards)
    assert len(build_card_inventory_rows(cleaned, definitions)) > 0
    rewritten = serialize_game_state(cleaned)
    assert 'daily_offers' not in rewritten['supply']
    assert payload['cards']['legacy-recipe'] == legacy  # Loading does not edit its input.


def test_common_supply_exposes_and_sells_canonical_machine_families():
    definitions = load_card_definitions(Path('src/production_zero/data/game_definitions.json'))
    machine_ids = {
        definition.definition_id
        for definition in definitions.values()
        if isinstance(definition, MachineDefinition)
    }
    offers = common_supply_offers(definitions)
    offered_machine_ids = {offer.definition_id for offer in offers if offer.card_kind is CardKind.MACHINE}
    assert offered_machine_ids == machine_ids
    assert machine_ids == {
        'machine.extractor', 'machine.drilling', 'machine.agriculture',
        'machine.processor', 'machine.fabricator', 'machine.assembler',
    }



@pytest.mark.parametrize('size', [(1366,768),(1920,1080)])
def test_supply_polish_geometry_prices_and_sparsity(size):
    app = QApplication.instance() or QApplication([])
    fonts = [QFontDatabase.addApplicationFont(f"C:/Windows/Fonts/{name}") for name in ("segoeui.ttf", "segoeuib.ttf", "bahnschrift.ttf")]
    old = app.styleSheet()
    app.setStyleSheet(APP_STYLESHEET)
    definitions = load_card_definitions(Path('src/production_zero/data/game_definitions.json'))
    state = GameState(rng_seed=42)
    state.cash.add(1_000_000)
    view = SupplyView(state, CommandBus(state), definitions)
    try:
        view.resize(*size)
        view.show()
        for _ in range(4): app.processEvents()
        assert [label.text() for label in view.findChildren(QLabel,'supplyHeaderMetricLabel')] == ['DAILY RESET']
        assert [label.text() for label in view.findChildren(QLabel,'supplyDailySectionTitle')] == ['DAILY FREIGHT','DAILY MACHINES']
        assert view._daily_module_columns_used == 2
        assert abs(view._daily_sections[0].width()-view._daily_sections[1].width()) <= 1
        for label in view.findChildren(QLabel,'supplyDailySectionSubtitle'):
            assert label.palette().color(label.foregroundRole()).name() == Theme.HEADER_SUBTITLE_RED
        daily_price_typography = set()
        for card in view.findChildren(SupplyOfferCardFrame):
            if card.isVisible():
                for price in ('$99999', '$1234567', '$999999999'):
                    card._price_label.setText(price)
                    card._position_footer()
                    footer = card._footer_rect(QRectF(card.rect()).adjusted(3, 3, -3, -3))
                    assert QFontMetrics(card._price_label.font()).horizontalAdvance(price) <= card._price_label.width()
                    assert not card._price_label.geometry().intersects(card._buy_button.geometry())
                    assert card._buy_button.geometry().left() > card._price_label.geometry().right()
                    assert footer.contains(QRectF(card._price_label.geometry()))
                    assert footer.contains(QRectF(card._buy_button.geometry()))
                assert card._buy_button.font().pixelSize() >= 12
                card._price_label.setText('$1234')
                card._position_footer()
                daily_price_typography.add((
                    card._price_label.font().pixelSize(),
                    card._price_label.font().weight(),
                    card._price_label.alignment(),
                ))
        assert len(daily_price_typography) == 1
        view.refresh()
        folder = Path('artifacts/phase7/recipe-retirement-captures/supply-polish');folder.mkdir(parents=True,exist_ok=True)
        view.grab().save(str(folder/f'daily-{size[0]}.png'))
        view._show_section(1)
        view._type_filter.setCurrentText('Processing')
        assert not hasattr(view, '_search')
        view._apply_common_filter()
        app.processEvents()
        assert view._filtered_common_data
        assert all(
            isinstance(item.definition, MachineDefinition)
            for item in view._filtered_common_data
        )
        for card in [card for card in view._common_card_pool if card.isVisible()]:
            footer = card._footer_rect(QRectF(card.rect()).adjusted(3, 3, -3, -3))
            assert footer.contains(QRectF(card._price_label.geometry()))
            assert footer.contains(QRectF(card._buy_button.geometry()))
            assert not card._price_label.geometry().intersects(card._buy_button.geometry())
            assert card._buy_button.font().pixelSize() >= 12
            card._price_label.setText('$1234')
            card._position_footer()
            assert (
                card._price_label.font().pixelSize(),
                card._price_label.font().weight(),
                card._price_label.alignment(),
            ) in daily_price_typography
        view.refresh()
        app.processEvents()
        view.grab().save(str(folder/f'common-machines-{size[0]}.png'))
        view._type_filter.setCurrentText('Freight')
        # A sparse current catalog, rather than a removed search control.
        view._common_display_data=[item for item in view._common_display_data if item.definition_id=='freight.truck']
        view._apply_common_filter()
        app.processEvents()
        visible = [card for card in view._common_card_pool if card.isVisible()]
        assert len(visible) == 1
        assert visible[0].x() == view._common_sparse_x_offset(1, view._common_grid_columns_used)
        assert 'Recipe' not in [view._type_filter.itemText(i) for i in range(view._type_filter.count())]
        view.grab().save(str(folder/f'common-freight-{size[0]}.png'))
    finally:
        view.close();view.deleteLater()
        app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        app.setStyleSheet(old)
        for font in fonts:
            if font >= 0: QFontDatabase.removeApplicationFont(font)
