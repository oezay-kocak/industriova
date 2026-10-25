import json
from production_zero.core.inventory_history import InventoryHistory, MAX_SAMPLES, RETENTION_SECONDS
from production_zero.core.player_profile import local_profile
from production_zero.core.state import GameState
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state, SQLiteSaveStore
from production_zero.persistence.session_writer import snapshot_game_state, encode_snapshot


def test_interval_retention_sparse_gaps_and_no_backfill():
    history = InventoryHistory()
    history.advance(0, {"iron_ore": 3})
    assert not history.samples
    history.advance(1, {"iron_ore": 3})
    for _ in range(299):
        history.advance(1, {"iron_ore": 6})
    assert history.values_for("iron_ore") == ((1, 3),)
    history.advance(1, {"iron_ore": 5})
    assert history.values_for("iron_ore") == ((1, 3), (301, 5))
    for i in range(2000):
        history.advance(300, {"iron_ore": i, "copper_ore": 0})
    assert len(history.values_for("iron_ore")) == MAX_SAMPLES
    assert history.values_for("iron_ore")[-1][0] - history.values_for("iron_ore")[0][0] == RETENTION_SECONDS
    history.advance(RETENTION_SECONDS * 2, {"iron_ore": 19})
    assert history.values_for("iron_ore") == ((history.elapsed_seconds, 19),)
    assert history.values_for("copper_ore")[-1][1] == 0


def test_sqlite_round_trip_legacy_and_save_snapshot(tmp_path):
    state = GameState(rng_seed=1)
    state.ensure_resource("iron_ore").amount = 50
    state.inventory_history.advance(200, {"iron_ore": 50})
    store = SQLiteSaveStore(tmp_path / "profile.sqlite")
    store.initialize()
    store.save("test", state)
    restored = store.load("test")
    assert restored.inventory_history == state.inventory_history
    restored.inventory_history.advance(100, {"iron_ore": 40})
    assert len(restored.inventory_history.values_for("iron_ore")) == 1
    restored.inventory_history.advance(200, {"iron_ore": 30})
    assert restored.inventory_history.values_for("iron_ore")[-1] == (500, 30)
    snapshot = snapshot_game_state(state)
    state.inventory_history.advance(300, {"iron_ore": 60})
    frozen = deserialize_game_state(json.loads(encode_snapshot(snapshot)))
    assert frozen.inventory_history.values_for("iron_ore") == ((200, 50),)
    legacy = serialize_game_state(state)
    legacy.pop("inventory_history")
    legacy["history"] = {"resource.iron_ore": {"metric_id": "resource.iron_ore", "values": [5, 10], "max_points": 86400}}
    assert not deserialize_game_state(legacy).inventory_history.samples


def test_inventory_leader_changes_independently_of_lifetime_production():
    state = GameState(rng_seed=1)
    state.production_progress.lifetime_produced["iron_ore"] = 10000
    state.ensure_resource("copper_ore").amount = 100
    state.ensure_resource("iron_ore").amount = 20
    state.inventory_history.advance(1, {"copper_ore": 100, "iron_ore": 20})
    profile = local_profile(state)
    assert profile.resource_id == "iron_ore" and profile.stock_resource_id == "copper_ore"
    state.resources["copper_ore"].amount = 0
    assert local_profile(state).stock_resource_id == "iron_ore"
    state.resources["iron_ore"].amount = 0
    assert local_profile(state).stock_resource_id is None
    assert local_profile(state).stock_amount == 0


def test_simulation_records_final_global_stock_at_sampling_boundary():
    from production_zero.core.simulation import SimulationEngine
    state = GameState(rng_seed=3)
    state.ensure_resource("iron_ore").amount = 40
    from pathlib import Path
    from production_zero.data.definitions import load_card_definitions
    engine = SimulationEngine(load_card_definitions(Path("src/production_zero/data/game_definitions.json")))
    engine.advance_time(state, 1)
    assert state.inventory_history.values_for("iron_ore") == ((1, state.resources["iron_ore"].amount),)
    state.resources["iron_ore"].amount = 12
    engine.advance_time(state, 299)
    assert len(state.inventory_history.values_for("iron_ore")) == 1
    engine.advance_time(state, 1)
    assert state.inventory_history.values_for("iron_ore")[-1] == (301, 12)
