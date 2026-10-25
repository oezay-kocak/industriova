"""Verify migration from backed-up save payloads without touching originals."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import re
import hashlib,sys,argparse
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument("--source",type=Path,default=ROOT);parser.add_argument("--out",type=Path,default=ROOT/"artifacts/phase6/migration-audit.json");args=parser.parse_args()
sys.path.insert(0,str(args.source.resolve()/"src"))
from production_zero.persistence.sqlite_store import deserialize_game_state, serialize_game_state


def run():
    backup = Path("artifacts/release-backups/20261018T185514851717Z").resolve()
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    results = []
    for entry in manifest["saves"]:
        path = backup / entry["backup"]
        if path.suffix not in {".sqlite", ".db"}:
            continue
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
            rows = db.execute("SELECT slot,state_json FROM saves").fetchall()
        for slot, raw in rows:
            try:
                old = json.loads(raw)
                state = deserialize_game_state(old)
                new = serialize_game_state(state)
                expected_cards = {cid for cid, card in old["cards"].items() if card.get("card_kind") != "recipe" and not card.get("definition_id", "").startswith("recipe.")}
                old_units = {key: unit for board in ('halls', 'resource_sites', 'energy_plants') for key, unit in old.get(board, {}).items()}
                new_units = {key: unit for board in ('halls', 'resource_sites', 'energy_plants') for key, unit in new.get(board, {}).items()}
                old_installed = sorted(slot['card_id'] for unit in old_units.values() for slot in unit.get('slots', []) if slot.get('card_id'))
                new_installed = sorted(slot['card_id'] for unit in new_units.values() for slot in unit.get('slots', []) if slot.get('card_id'))
                def legacy_mk(card):
                    match = re.search(r'\.mk(\d+)', card.get('definition_id', ''))
                    return int(card.get('mk_level', match.group(1) if match else 1))
                checks = {
                    "cash": old["cash"] == new["cash"],
                    "cards": expected_cards == set(new["cards"]),
                    "rarities": all(old["cards"][cid]["rarity"] == new["cards"][cid]["rarity"] and old["cards"][cid]["output_bonus_percent"] == new["cards"][cid]["output_bonus_percent"] for cid in expected_cards),
                    "resources": all(float(stock["amount"] if isinstance(stock, dict) else stock) == new["resources"][rid]["amount"] for rid, stock in old.get("resources", {}).items()),
                    "company_level_xp": all(old.get("company", {}).get(key, default) == new["company"][key] for key, default in (("level", 1), ("current_xp", 0.))),
                    "mk": all(new['cards'][cid]['mk_level'] == legacy_mk(old['cards'][cid]) for cid in expected_cards),
                    "recipes_and_progress": all(all(new.get('machine_production', {}).get(cid, {}).get(key) == value for key, value in machine.items()) for cid, machine in old.get('machine_production', {}).items() if cid in expected_cards),
                    "inflight": all(all(new["freight"]["outbound_shipments"].get(sid, {}).get(key) == value for key,value in ship.items()) for sid,ship in old.get("freight", {}).get("outbound_shipments", {}).items()) and set(new["freight"]["outbound_shipments"]) == set(old.get("freight", {}).get("outbound_shipments", {})),
                    "freight_routes": all(new['freight']['assignments'][cid]['resource_id'] == route['resource_id'] and new['freight']['assignments'][cid]['destination_kind'] == route['destination_kind'] for cid, route in old.get('freight', {}).get('assignments', {}).items()),
                    "placements": old_installed == new_installed,
                    "building_structure": all(key in new_units and new_units[key]['max_lines'] >= unit.get('max_lines', 1) and len(new_units[key]['slots']) >= len(unit.get('slots', [])) for key, unit in old_units.items()),
                    "production_line_unlocks_and_schema6_pause_defaults": all(new_units[key]['production_lines'] == [{'paused': False, **line} for line in unit['production_lines']] for key, unit in old_units.items() if 'production_lines' in unit),
                    "freight_facilities": all(key in new['freight']['facilities'] and new['freight']['facilities'][key]['slots'] == facility['slots'] and new['freight']['facilities'][key]['expansion_level'] == facility.get('expansion_level', 0) for key, facility in old.get('freight', {}).get('facilities', {}).items()),
                    "consortium": all(new['consortium'].get(key) == value for key, value in old.get('consortium', {}).items()),
                    "idempotent": new == serialize_game_state(deserialize_game_state(new)),
                    "recorded_investments": all(all(new["cards"][cid].get(key) == value for key,value in old["cards"][cid].items() if key in {"acquisition_cost","upgrade_investment","paused"}) for cid in expected_cards),
                    "specialized_sites": all(len({state.cards[s.card_id].definition_id for s in site.slots if s.card_id}) <= 1 for site in state.resource_sites.values()),
                }
                from copy import deepcopy
                legacy = deepcopy(new)
                legacy['state_schema_version'] = 6
                legacy['freight'].pop('delivery_statistics', None)
                for shipment in legacy['freight']['outbound_shipments'].values():
                    shipment.pop('source_facility_id', None)
                    shipment.pop('economic_processed', None)
                compatible_sha = hashlib.sha256(json.dumps(legacy,sort_keys=True).encode('utf8')).hexdigest()
                p5 = json.loads((ROOT/'artifacts/phase5/migration-after.json').read_text(encoding='utf8'))
                expected = next(r for r in p5['results'] if r['source']==entry['source'] and r['slot']==slot)
                checks['entire_business_payload_matches_p5'] = compatible_sha == expected['payload_sha256']
                checks['schema7_empty_warmup'] = new['freight']['delivery_statistics'] == {'seconds':0.0,'buckets':[]}
                results.append(dict(source=entry["source"], slot=slot, checks=checks, legacy_compatible_sha256=compatible_sha, payload_sha256=hashlib.sha256(json.dumps(new,sort_keys=True).encode("utf8")).hexdigest(), passed=all(checks.values())))
            except Exception as error:
                results.append(dict(source=entry["source"], slot=slot, passed=False, error=str(error)))
    report = {"results": results, "passed": sum(r["passed"] for r in results), "failed": sum(not r["passed"] for r in results)}
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}))
    for result in results:
        if not result["passed"]:
            print(json.dumps(result))
    assert report['failed'] == 0, 'Save migration invariants failed; see migration-audit.json'


if __name__ == "__main__":
    run()
