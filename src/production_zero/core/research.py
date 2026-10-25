"""Research definitions and allocation transitions, independent of Qt and recipes."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from importlib.resources import files
import json
import math
import time
from types import MappingProxyType

RESPEC_SECONDS = 86_400
EFFECT_TYPES = {"value", "production_speed", "energy_output", "freight_capacity", "storage_capacity", "contract_value"}


@dataclass(frozen=True, slots=True)
class ResearchTree:
    id: str
    name: str
    family: str
    icon_resource: str
    order: int


@dataclass(frozen=True, slots=True)
class ResearchNode:
    id: str
    tree_id: str
    name: str
    description: str
    node_type: str
    cost: int
    icon_resource: str
    prerequisites: tuple[str, ...]
    effect_type: str
    effect_scope: str
    effect_target: str
    effect_value: float
    bonus_label: str
    row: int
    position: int

    @property
    def bonus_text(self) -> str:
        return f"+{self.effect_value * 100:g}% {self.bonus_label}"


@dataclass(frozen=True, slots=True)
class SpecializationSlot:
    id: str
    tree_id: str
    major_node_id: str
    cost: int
    value_bonus: float


@lru_cache(maxsize=1)
def specialization_catalog():
    config = json.loads(files("production_zero.data").joinpath("research_definitions.json").read_text(encoding="utf-8"))["specialization"]
    bonus = config["value_bonus"]
    if not math.isfinite(bonus) or bonus <= 0:
        raise ValueError("Invalid specialization value bonus")
    slots = {s["id"]: SpecializationSlot(**s, value_bonus=bonus) for s in config["slots"]}
    trees, nodes = research_catalog()
    if len(slots) != len(config["slots"]):
        raise ValueError("Duplicate specialization IDs")
    for slot in slots.values():
        major = nodes.get(slot.major_node_id)
        if (slot.id in nodes or slot.cost != 1 or slot.tree_id not in trees
                or trees[slot.tree_id].family != "industry" or major is None
                or major.tree_id != slot.tree_id or major.node_type != "major" or major.row == 0):
            raise ValueError(f"Invalid specialization slot: {slot.id}")
    return MappingProxyType(slots)


@lru_cache(maxsize=1)
def research_products():
    """Canonical resource metadata for selection and Activity labels, never membership."""
    data = json.loads(files("production_zero.data").joinpath("resource_definitions.json").read_text(encoding="utf-8"))
    return MappingProxyType({r["id"]: MappingProxyType(r) for r in data["resources"]})


@lru_cache(maxsize=1)
def research_domains():
    return MappingProxyType(json.loads(files("production_zero.data").joinpath("research_domains.json").read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def research_catalog():
    data = json.loads(files("production_zero.data").joinpath("research_definitions.json").read_text(encoding="utf-8"))
    trees = {t["id"]: ResearchTree(**t) for t in data["trees"]}
    nodes = {n["id"]: ResearchNode(**{**n, "prerequisites": tuple(n["prerequisites"])}) for n in data["nodes"]}
    if len(trees) != len(data["trees"]) or len(nodes) != len(data["nodes"]):
        raise ValueError("Duplicate Research IDs")
    validate_catalog(trees, nodes, research_domains())
    return MappingProxyType(trees), MappingProxyType(nodes)


def validate_catalog(trees, nodes, domains):
    resources = json.loads(files("production_zero.data").joinpath("resource_definitions.json").read_text(encoding="utf-8"))["resources"]
    if set(domains) != {r["id"] for r in resources}:
        raise ValueError("Every resource must have exactly one Research domain")
    if {f"industry.{domain}" for domain in domains.values()} != {t.id for t in trees.values() if t.family == "industry"}:
        raise ValueError("Industry domain/tree mismatch")
    for tree in trees.values():
        if tree.icon_resource not in domains or tree.family not in {"company", "industry"}:
            raise ValueError(f"Invalid Research tree: {tree.id}")
    for node in nodes.values():
        if node.tree_id not in trees or node.cost != 1 or node.node_type not in {"small", "major"} or node.icon_resource not in domains:
            raise ValueError(f"Invalid Research node: {node.id}")
        if node.effect_type not in EFFECT_TYPES or not math.isfinite(node.effect_value) or node.effect_value <= 0:
            raise ValueError(f"Invalid Research effect: {node.id}")
        if node.effect_scope == "global":
            valid = node.effect_target == "*"
        elif node.effect_scope == "domain":
            valid = node.effect_type == "value" and node.effect_target in domains.values()
        elif node.effect_scope == "product":
            valid = node.effect_type == "value" and node.effect_target in domains
        else:
            valid = False
        if not valid:
            raise ValueError(f"Invalid Research target: {node.id}")
        for prerequisite in node.prerequisites:
            previous = nodes.get(prerequisite)
            if previous is None or previous.tree_id != node.tree_id or previous.row >= node.row:
                raise ValueError(f"Invalid/cyclic prerequisite: {node.id}")


@dataclass(slots=True)
class ResearchState:
    total_earned: int = 0
    unlocked_node_ids: set[str] = field(default_factory=set)
    respec_available_at: float = 0.0
    utc_high_water_timestamp: float = 0.0
    cooldown_notified: bool = True
    # Allocation snapshots are stable ID tuples; template-management UX is deferred.
    saved_allocations: dict[str, tuple[str, ...]] = field(default_factory=dict)
    # Paid V1 second-row nodes retain ownership across the strict-lane migration.
    legacy_lane_node_ids: set[str] = field(default_factory=set)
    # Stable slot ID -> canonical product ID. Repeated product IDs are intentional.
    specializations: dict[str, str] = field(default_factory=dict)

    @property
    def spent(self) -> int:
        return len(self.unlocked_node_ids) + len(self.specializations)

    @property
    def available(self) -> int:
        return self.total_earned - self.spent


def grant_research_points(state, amount: int, source: str) -> None:
    if type(amount) is not int or amount <= 0:
        raise ValueError("Research grant must be a positive integer")
    state.research.total_earned += amount
    state.communications.add_activity("research", f"+{amount} RP · {source}")


def node_state(research: ResearchState, node: ResearchNode) -> str:
    if node.id in research.unlocked_node_ids:
        return "unlocked"
    if not set(node.prerequisites) <= research.unlocked_node_ids:
        return "locked"
    return "available" if research.available >= node.cost else "unfunded"


def purchase_research(state, node_id: str) -> None:
    _, nodes = research_catalog()
    node = nodes.get(node_id)
    if node is None:
        raise ValueError("Unknown Research node")
    if node_state(state.research, node) != "available":
        raise ValueError("Research requires an unowned node, its prerequisites, and 1 RP")
    state.research.unlocked_node_ids.add(node.id)
    if node.node_type == "major":
        tree = research_catalog()[0][node.tree_id]
        state.communications.add_activity("research", f"{tree.name} · {node.name} researched")
    for candidate in nodes.values():
        if candidate.node_type == "major" and node.id in candidate.prerequisites and set(candidate.prerequisites) <= state.research.unlocked_node_ids:
            state.communications.add_activity("research", f"{research_catalog()[0][candidate.tree_id].name} · {candidate.name} ready")


def specialization_state(research: ResearchState, slot: SpecializationSlot) -> str:
    if slot.id in research.specializations:
        return "unlocked"
    if slot.major_node_id not in research.unlocked_node_ids:
        return "locked"
    return "available" if research.available >= slot.cost else "unfunded"


def purchase_specialization(state, slot_id: str, product_id: str) -> None:
    slot = specialization_catalog().get(slot_id)
    if slot is None:
        raise ValueError("Unknown specialization slot")
    if specialization_state(state.research, slot) != "available":
        raise ValueError("Specialization requires an unselected slot, its Major, and 1 RP; changing it requires Full Respec")
    if research_domains().get(product_id) != slot.tree_id.removeprefix("industry."):
        raise ValueError("Choose a product from this Industry domain")
    state.research.specializations[slot.id] = product_id
    state.communications.add_activity("research", f"{research_products()[product_id]['name']} specialization researched")


def sync_research_clock(state, now: float | None = None) -> float:
    requested = time.time() if now is None else float(now)
    if not math.isfinite(requested) or requested < 0:
        raise ValueError("Research timestamp must be finite and nonnegative")
    research = state.research
    research.utc_high_water_timestamp = max(requested, research.utc_high_water_timestamp)
    if not research.cooldown_notified and research.utc_high_water_timestamp >= research.respec_available_at:
        research.cooldown_notified = True
        state.communications.add_activity("research", "Research respec cooldown finished")
    return research.utc_high_water_timestamp


def cooldown_remaining(research: ResearchState, now: float | None = None) -> float:
    return max(0.0, research.respec_available_at - max(time.time() if now is None else now, research.utc_high_water_timestamp))


def respec_research(state, now: float | None = None) -> int:
    timestamp = sync_research_clock(state, now)
    if cooldown_remaining(state.research, timestamp) > 0:
        raise ValueError("Research respec is cooling down")
    returned = state.research.spent
    if returned == 0:
        raise ValueError("No Research allocation to reset")
    state.research.unlocked_node_ids.clear()
    state.research.legacy_lane_node_ids.clear()
    state.research.specializations.clear()
    state.research.respec_available_at = timestamp + RESPEC_SECONDS
    state.research.cooldown_notified = False
    state.communications.add_activity("research", f"Respec completed · {returned} RP returned · 24h cooldown")
    return returned


def research_to_dict(research: ResearchState) -> dict:
    return dict(version=3, total_earned=research.total_earned, available=research.available,
                specializations=dict(sorted(research.specializations.items())),
                legacy_lane_node_ids=sorted(research.legacy_lane_node_ids & research.unlocked_node_ids),
                spent=research.spent, unlocked_node_ids=sorted(research.unlocked_node_ids),
                respec_available_at=research.respec_available_at,
                utc_high_water_timestamp=research.utc_high_water_timestamp,
                cooldown_notified=research.cooldown_notified,
                saved_allocations={k: list(v) for k, v in research.saved_allocations.items()})


def research_from_dict(data: dict | None) -> ResearchState:
    if data is None:
        return ResearchState()
    if not isinstance(data, dict):
        raise ValueError("Research save must be an object")
    version = data.get("version", 1)
    if version not in (1, 2, 3):
        raise ValueError("Unsupported Research save version")
    total = data.get("total_earned", 0)
    if type(total) is not int or total < 0:
        raise ValueError("Invalid Research point total")
    raw_ids = data.get("unlocked_node_ids", [])
    if not isinstance(raw_ids, list) or not all(isinstance(nid, str) for nid in raw_ids) or len(set(raw_ids)) != len(raw_ids) or len(raw_ids) > total:
        raise ValueError("Invalid Research allocation")
    selections = data.get("specializations", {})
    if not isinstance(selections, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in selections.items()):
        raise ValueError("Invalid Research specializations")
    if len(raw_ids) + len(selections) > total:
        raise ValueError("Research allocation exceeds earned RP")
    nodes = research_catalog()[1]
    # Validate V1 allocations against the topology they were actually purchased in.
    # Never grant free ancestors or refund a valid paid node merely because its
    # prerequisites changed. Exemptions persist until full respec, not new purchases.
    allocation = {nid for nid in raw_ids if nid in nodes}
    legacy = data.get("legacy_lane_node_ids", []) if version >= 2 else []
    if not isinstance(legacy, list) or not all(isinstance(nid, str) for nid in legacy):
        raise ValueError("Invalid legacy Research allocation")
    legacy = set(legacy) & allocation

    def prerequisites(nid):
        node = nodes[nid]
        prefix = nid.rsplit(".", 1)[0]
        if version == 1:
            if node.node_type == "small":
                return {prefix + ".major"}
            section = node.row // 3 + 1
            return {f"{node.tree_id}.s{section - 1}.n{i}" for i in range(1, 7)} if section > 1 else set()
        if nid in legacy and node.node_type == "small" and node.row % 3 == 2:
            return {prefix + ".major"}
        return set(node.prerequisites)

    # Unknown content and genuinely broken allocations are still refunded.
    while any(not prerequisites(nid) <= allocation for nid in allocation):
        allocation = {nid for nid in allocation if prerequisites(nid) <= allocation}
    legacy = {nid for nid in allocation if nodes[nid].node_type == "small"
              and nodes[nid].row % 3 == 2 and not set(nodes[nid].prerequisites) <= allocation
              and (version == 1 or nid in legacy)}
    slots = specialization_catalog()
    # Invalid/retired products or slots are refunded, as are slots whose Major
    # no longer survives allocation validation. Earned RP never changes.
    selections = {sid: rid for sid, rid in selections.items() if sid in slots
                  and slots[sid].major_node_id in allocation
                  and research_domains().get(rid) == slots[sid].tree_id.removeprefix("industry.")}
    timestamps = [float(data.get(key, 0)) for key in ("respec_available_at", "utc_high_water_timestamp")]
    if any(not math.isfinite(t) or t < 0 for t in timestamps):
        raise ValueError("Invalid Research cooldown")
    snapshots = data.get("saved_allocations", {})
    if not isinstance(snapshots, dict) or any(not isinstance(ids, (list, tuple)) or not all(isinstance(nid, str) for nid in ids) for ids in snapshots.values()):
        raise ValueError("Invalid saved Research allocations")
    return ResearchState(total_earned=total, unlocked_node_ids=allocation,
                         specializations=selections,
                         legacy_lane_node_ids=legacy,
                         respec_available_at=timestamps[0], utc_high_water_timestamp=timestamps[1],
                         cooldown_notified=bool(data.get("cooldown_notified", True)),
                         saved_allocations={str(k): tuple(v) for k, v in snapshots.items()})
