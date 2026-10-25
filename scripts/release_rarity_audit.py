"""Sample the real first-hit MK upgrade implementation against exact hazards."""
from collections import Counter
import json
from pathlib import Path
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.mk_upgrades import upgraded_card, rarity_distribution


def main():
    counts = Counter({rarity.value: 0 for rarity in Rarity})
    first_hit = Counter()
    samples = 10000
    for seed in range(samples):
        card = create_card_instance("quality-simulation", "machine.extractor", CardKind.MACHINE, Rarity.COMMON)
        for _ in range(98):
            card = upgraded_card(card, 0., seed)
            if card.rarity is not Rarity.COMMON:
                first_hit[card.mk_level] += 1
                break
        counts[card.rarity.value] += 1
    report = {"samples": samples, "upgrades_per_machine": 98, "observed_counts": dict(counts), "observed_rates": {key: value / samples for key, value in counts.items()}, "exact_probabilities": rarity_distribution(), "first_hit_mk": dict(sorted(first_hit.items()))}
    Path("artifacts/industriova-release/rarity-simulation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "first_hit_mk"}))


if __name__ == "__main__":
    main()
