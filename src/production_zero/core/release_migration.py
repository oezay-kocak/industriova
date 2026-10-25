"""Lossless production-site specialization for pre-release test saves."""
from copy import deepcopy
from production_zero.core.machine_operations import SITE_TYPES


def specialize_resource_sites(state):
    for site in tuple(state.resource_sites.values()):
        families = sorted({state.cards[slot.card_id].definition_id for slot in site.slots if slot.card_id in state.cards})
        if not families:
            site.specialization = site.specialization or "machine.extractor"
            continue
        site.specialization = families[0]
        for family in families[1:]:
            new_site = deepcopy(site)
            new_site.hall_id = f"{site.hall_id}-{family.rsplit('.', 1)[-1]}"
            while new_site.hall_id in state.resource_sites:
                new_site.hall_id += "-migrated"
            new_site.name = f"{site.name} · {SITE_TYPES.get(family, family)}"
            new_site.specialization = family
            for line in new_site.production_lines:
                line.line_id = f"{new_site.hall_id}:{line.line_id}"
            for source, target in zip(site.slots, new_site.slots):
                if source.card_id in state.cards and state.cards[source.card_id].definition_id == family:
                    source.card_id = None
                else:
                    target.card_id = None
            state.resource_sites[new_site.hall_id] = new_site


def migrate_release_state(state):
    specialize_resource_sites(state)
    # Packs are retired without compensation by explicit pre-release instruction.
    state.packs.unopened.clear()
    state.packs.last_opened_cards.clear()
