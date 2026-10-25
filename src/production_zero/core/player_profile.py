"""Read-only profile snapshots. Missing remote metrics remain unknown, not zero."""
from dataclasses import dataclass

from production_zero.core.company import title_for_level


@dataclass(frozen=True, slots=True)
class PlayerProfile:
    company_id: str | None
    name: str
    level: int
    title: str
    source: str
    consortium: str | None = None
    role: str | None = None
    earnings: float | None = None
    lifetime_production: float | None = None
    resource_id: str | None = None
    resource_amount: float | None = None
    stock_resource_id: str | None = None
    stock_amount: float | None = None
    inventory_history: tuple[tuple[float, float], ...] = ()
    inventory_history_now: float = 0.0
    contribution: float | None = None


def local_profile(state) -> PlayerProfile:
    membership = state.consortium.membership()
    produced = {key: value for key, value in state.production_progress.lifetime_produced.items() if value > 0}
    strongest = max(sorted(produced), key=produced.get) if produced else None
    stocked = {rid: stock.amount for rid, stock in state.resources.items() if stock.amount > 0}
    leading_stock = max(sorted(stocked), key=stocked.get) if stocked else None
    return PlayerProfile(
        state.consortium.current_company_id, state.consortium.current_company_name,
        state.company.level, state.company.current_title, "LOCAL COMPANY · RECORDED STATISTICS",
        consortium=membership[0].name if membership else "Independent company",
        role=membership[1].role if membership else None,
        earnings=state.statistics.total_earnings,
        lifetime_production=sum(produced.values()), resource_id=strongest,
        resource_amount=produced.get(strongest) if strongest else None,
        stock_resource_id=leading_stock, stock_amount=stocked.get(leading_stock) if leading_stock else 0.0,
        inventory_history=state.inventory_history.values_for(leading_stock) if leading_stock else (),
        inventory_history_now=state.inventory_history.elapsed_seconds,
        contribution=membership[1].lifetime_contribution if membership else None,
    )


def member_profile(state, consortium, member) -> PlayerProfile:
    if member.company_id == state.consortium.current_company_id:
        return local_profile(state)
    return PlayerProfile(member.company_id, member.company_name, member.company_level,
                         title_for_level(member.company_level), "LOCAL CONSORTIUM RECORD · REMOTE STATISTICS UNAVAILABLE",
                         consortium=consortium.name, role=member.role, contribution=member.lifetime_contribution)


def leaderboard_profile(state, entry) -> PlayerProfile:
    if entry.is_current_player:
        return local_profile(state)
    return PlayerProfile(None, entry.player_name, entry.company_level, entry.title,
                         "OFFLINE DEMO COMPANY · SAMPLE RANKING DATA", earnings=entry.total_earnings)
