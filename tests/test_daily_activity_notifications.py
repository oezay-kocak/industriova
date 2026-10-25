from pathlib import Path
from PySide6.QtWidgets import QApplication
from production_zero.core import company_xp as xp
from production_zero.core.state import GameState
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state
from production_zero.ui.event_feed import EventFeedController, EventFeedWidget

DEFINITIONS = load_card_definitions(Path('src/production_zero/data/game_definitions.json'))

def test_time_xp_and_daily_activity_are_gone_but_sale_and_contract_xp_are_visible():
    app = QApplication.instance() or QApplication([])
    state = GameState(rng_seed=1)
    feed = EventFeedWidget()
    controller = EventFeedController(state, feed, definitions=DEFINITIONS)
    for i in range(60):
        xp.record_accepted_production_xp(state, {'qa_unknown':1}, 60, DEFINITIONS, 100000)
        controller.observe(); feed.flush_pending()
    assert not feed.history and not state.company_xp_progress.xp_by_source
    xp.award_market_sale_xp(state, 750, DEFINITIONS)
    controller.observe(); feed.flush_pending()
    assert any(e.event_type == 'xp' and e.amount == 75 for e in feed.history)
    xp.award_contract_company_xp(state, 75, DEFINITIONS, source='meaningful_fixture')
    controller.observe(); feed.flush_pending()
    assert state.company_xp_progress.xp_by_source == {'market_sales': 75, 'meaningful_fixture': 75}
    assert all(e.event_type != 'daily_activity' for e in feed.history)
    feed.close()

def test_save_load_and_day_changes_never_recreate_time_xp_or_daily_activity():
    state = GameState(rng_seed=2)
    xp.award_market_sale_xp(state, 400, DEFINITIONS)
    restored = deserialize_game_state(serialize_game_state(state))
    for day in (100000, 200000, 100000, 1000000):
        xp.record_accepted_production_xp(restored, {'qa_unknown':1}, 86400, DEFINITIONS, day)
    assert restored.company_xp_progress.xp_by_source == {'market_sales': 40}
    assert restored.company.current_xp == 40
    assert not restored.communications.pending_activity
    saved = serialize_game_state(restored)['company_xp_progress']
    assert 'continuity_bank_xp' not in saved and 'continuity_daily_xp' not in saved
