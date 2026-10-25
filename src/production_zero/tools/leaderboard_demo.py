"""Isolated leaderboard demo. No save loading, persistence, or production wiring.

Offscreen preview (default): python -m production_zero.tools.leaderboard_demo
Optional manual demo: python -m production_zero.tools.leaderboard_demo --interactive
"""
from __future__ import annotations

from production_zero.core.company import title_for_level
from production_zero.core.state import GameState
from production_zero.services.interfaces import LeaderboardEntry
from production_zero.services.local import LocalLeaderboardService


def demo_entries() -> tuple[LeaderboardEntry, ...]:
    prefixes = ('Atlas', 'Northstar', 'Copperline', 'Coal Harbor', 'Founders',
                'Orepath', 'Meridian', 'Blackridge', 'Redline', 'Titan', 'Ironvale')
    suffixes = ('Foundry', 'Steel', 'Works', 'Industries', 'Fabrication',
                'Systems', 'Manufacturing', 'Process Works', 'Engineering')
    names = [f'{prefix} {suffix}' for prefix in prefixes for suffix in suffixes]
    return tuple(LeaderboardEntry(0, name, index + 1, title_for_level(index + 1),
                 ((index * 37) % 99 + 1) * 1000., index * 17.)
                 for index, name in enumerate(names))


def create_demo_provider() -> LocalLeaderboardService:
    # Fresh, disposable state; the real player's state is never accepted here.
    state = GameState(rng_seed=2026)
    state.company.level = 25
    state.company.current_xp = 2500
    state.statistics.total_earnings = 25500
    return LocalLeaderboardService(state, mock_entries=demo_entries())


def main() -> None:
    import argparse
    import os
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interactive', action='store_true', help='Explicitly open the disposable demo window')
    parser.add_argument('--output', default='artifacts/leaderboard_demo.png')
    args = parser.parse_args()
    if not args.interactive:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFontDatabase
    from production_zero.ui.leaderboard_view import LeaderboardView
    from production_zero.ui.theme import APP_STYLESHEET
    app = QApplication.instance() or QApplication([])
    for name in ('segoeui.ttf', 'segoeuib.ttf', 'bahnschrift.ttf', 'agencyr.ttf', 'agencyb.ttf'):
        path = Path('C:/Windows/Fonts') / name
        if path.exists():
            QFontDatabase.addApplicationFont(str(path))
    app.setStyleSheet(APP_STYLESHEET)
    view = LeaderboardView(create_demo_provider())
    view.resize(1180, 720)
    view.show()
    app.processEvents()
    if args.interactive:
        app.exec()
    else:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        view.grab().save(str(path))
        view.close()


if __name__ == '__main__':
    main()
