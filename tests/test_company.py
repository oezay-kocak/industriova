from __future__ import annotations

from production_zero.core.company import CompanyProfile, award_company_xp, title_for_level, unlocked_level_titles, xp_required_for_next_level, xp_reward_for_contract_kind


def test_company_profile_starts_at_level_one_with_founder_title() -> None:
    company = CompanyProfile()

    assert company.level == 1
    assert company.current_xp == 0
    assert company.xp_to_next_level == xp_required_for_next_level(1)
    assert company.current_title == "Founder"


def test_company_xp_levels_up_and_keeps_overflow() -> None:
    company = CompanyProfile()
    required = company.xp_to_next_level

    gained = award_company_xp(company, required + 25)

    assert gained == (2,)
    assert company.level == 2
    assert company.current_xp == 25


def test_company_xp_can_gain_multiple_levels_at_once() -> None:
    company = CompanyProfile()
    gained = award_company_xp(company, 5_000)

    assert gained == (2, 3, 4, 5)
    assert company.level == 5
    assert company.current_xp > 0
    assert len(company.pending_rewards) == 4


def test_company_level_progression_continues_beyond_level_100() -> None:
    company = CompanyProfile(level=100, current_xp=0)
    gained = award_company_xp(company, xp_required_for_next_level(100) + xp_required_for_next_level(101) + 10)

    assert gained == (101, 102)
    assert company.level == 102
    assert company.current_xp == 10
    assert company.current_title == "Magnate"


def test_company_titles_unlock_from_level_milestones() -> None:
    assert title_for_level(1) == "Founder"
    assert title_for_level(10) == "Entrepreneur"
    assert title_for_level(25) == "Industrialist"
    assert title_for_level(50) == "Manufacturer"
    assert title_for_level(75) == "Industry Leader"
    assert title_for_level(100) == "Magnate"
    assert unlocked_level_titles(50) == ("Founder", "Entrepreneur", "Industrialist", "Manufacturer")


def test_contract_xp_rewards_scale_by_contract_type() -> None:
    assert xp_reward_for_contract_kind("regular") < xp_reward_for_contract_kind("daily")
    assert xp_reward_for_contract_kind("daily") < xp_reward_for_contract_kind("weekly")
