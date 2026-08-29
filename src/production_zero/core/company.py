from __future__ import annotations

from dataclasses import dataclass, field


TITLE_MILESTONES: tuple[tuple[int, str], ...] = (
    (1, "Founder"),
    (10, "Entrepreneur"),
    (25, "Industrialist"),
    (50, "Manufacturer"),
    (75, "Industry Leader"),
    (100, "Magnate"),
)


@dataclass(frozen=True, slots=True)
class LevelUpRewardDefinition:
    level: int
    cash: float = 0.0
    packs: int = 0
    cosmetic_id: str | None = None
    unlock_ids: tuple[str, ...] = ()


@dataclass(slots=True)
class CompanyProfile:
    level: int = 1
    current_xp: float = 0.0
    selected_title: str | None = None
    achievement_titles: list[str] = field(default_factory=list)
    pending_rewards: list[LevelUpRewardDefinition] = field(default_factory=list)

    @property
    def xp_to_next_level(self) -> float:
        return xp_required_for_next_level(self.level)

    @property
    def current_title(self) -> str:
        if self.selected_title is not None:
            return self.selected_title
        return title_for_level(self.level)


def xp_required_for_next_level(level: int) -> float:
    if level < 1:
        raise ValueError("Company level must be positive.")
    if level < 100:
        return float(500 + level * 125 + level * level * 18)
    prestige_level = level - 99
    return float(250_000 + prestige_level * 9_000 + prestige_level * prestige_level * 450)


def title_for_level(level: int) -> str:
    title = TITLE_MILESTONES[0][1]
    for required_level, milestone_title in TITLE_MILESTONES:
        if level >= required_level:
            title = milestone_title
    return title


def unlocked_level_titles(level: int) -> tuple[str, ...]:
    return tuple(title for required_level, title in TITLE_MILESTONES if level >= required_level)


def xp_reward_for_contract_kind(kind: str) -> float:
    rewards = {
        "regular": 90.0,
        "daily": 450.0,
        "weekly": 2_400.0,
    }
    return rewards.get(kind, 0.0)


def award_company_xp(company: CompanyProfile, amount: float) -> tuple[int, ...]:
    if amount < 0:
        raise ValueError("Company XP cannot be negative.")
    if amount == 0:
        return ()

    company.current_xp += amount
    gained_levels: list[int] = []
    while company.current_xp >= company.xp_to_next_level:
        company.current_xp -= company.xp_to_next_level
        company.level += 1
        gained_levels.append(company.level)
        reward = level_up_reward_for_level(company.level)
        if reward is not None:
            company.pending_rewards.append(reward)
    return tuple(gained_levels)


def level_up_reward_for_level(level: int) -> LevelUpRewardDefinition | None:
    if level <= 1:
        return None
    if level <= 100:
        return LevelUpRewardDefinition(level=level)
    if level % 10 == 0:
        return LevelUpRewardDefinition(level=level)
    return None
