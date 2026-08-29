from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QTabWidget, QVBoxLayout, QWidget

from production_zero.services.interfaces import LeaderboardEntry, LeaderboardService
from production_zero.ui.widget_lifecycle import clear_layout_safely


RANKINGS = (("company_level", "COMPANY LEVEL"), ("total_earnings", "TOTAL EARNINGS"))


class LeaderboardView(QWidget):
    def __init__(self, provider: LeaderboardService, limit: int = 10) -> None:
        super().__init__()
        self._provider = provider
        self._limit = limit
        self.setObjectName("leaderboardView")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._header = self._build_header()
        layout.addWidget(self._header)

        switch_deck = QFrame()
        switch_deck.setObjectName("leaderboardSwitchDeck")
        switch_layout = QHBoxLayout(switch_deck)
        switch_layout.setContentsMargins(12, 10, 12, 10)
        switch_layout.setSpacing(8)
        label = QLabel("RANKING METRIC")
        label.setObjectName("leaderboardSwitchLabel")
        switch_layout.addWidget(label)
        self._metric_buttons: list[QPushButton] = []
        for index, (ranking_id, text) in enumerate(RANKINGS):
            button = QPushButton(text)
            button.setObjectName("leaderboardMetricChip")
            button.setProperty("rankingId", ranking_id)
            button.setProperty("active", index == 0)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, target=index: self._set_ranking_index(target))
            self._metric_buttons.append(button)
            switch_layout.addWidget(button)
        switch_layout.addStretch(1)
        layout.addWidget(switch_deck)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("leaderboardTabs")
        self._tabs.tabBar().hide()
        self._tabs.setDocumentMode(True)
        self._tabs.currentChanged.connect(self._refresh_metric_state)
        self._tabs.addTab(self._build_ranking_page("company_level"), "Company Level")
        self._tabs.addTab(self._build_ranking_page("total_earnings"), "Total Earnings")
        layout.addWidget(self._tabs, 1)
        self.refresh()

    def refresh(self) -> None:
        for ranking_id, list_layout, own_layout in (
            ("company_level", self._level_list_layout, self._level_own_layout),
            ("total_earnings", self._earnings_list_layout, self._earnings_own_layout),
        ):
            self._refresh_ranking(ranking_id, list_layout, own_layout)
        self._refresh_metric_state()

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("leaderboardPageHeader")
        header.setMinimumHeight(116)
        header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(32, 25, 32, 24)
        layout.setSpacing(18)

        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(1)
        title = QLabel("LEADERBOARD")
        title.setObjectName("leaderboardHeroTitle")
        subtitle = QLabel("GLOBAL RANKINGS / COMPANY DOMINANCE")
        subtitle.setObjectName("leaderboardHeroSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        layout.addLayout(title_column, 1)

        self._rank_metric = self._header_metric("YOUR RANK", "-")
        self._level_metric = self._header_metric("YOUR LEVEL", "-")
        self._tracked_metric = self._header_metric("ENTRIES", str(self._limit))
        layout.addWidget(self._rank_metric[0])
        layout.addWidget(self._level_metric[0])
        layout.addWidget(self._tracked_metric[0])
        return header

    def _header_metric(self, label_text: str, value_text: str) -> tuple[QFrame, QLabel]:
        tile = QFrame()
        tile.setObjectName("leaderboardHeaderMetric")
        tile.setMinimumSize(138, 58)
        tile.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(1)
        label = QLabel(label_text)
        label.setObjectName("leaderboardMetricLabel")
        value = QLabel(value_text)
        value.setObjectName("leaderboardMetricValue")
        layout.addWidget(label)
        layout.addWidget(value)
        return tile, value

    def _build_ranking_page(self, ranking_id: str) -> QWidget:
        page = QWidget()
        page.setObjectName("leaderboardRankingPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setObjectName(f"{ranking_id}LeaderboardScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName(f"{ranking_id}LeaderboardContent")
        list_layout = QVBoxLayout(content)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(8)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        own_frame = QFrame()
        own_frame.setObjectName("ownLeaderboardPanel")
        own_layout = QHBoxLayout(own_frame)
        own_layout.setContentsMargins(12, 9, 12, 9)
        own_layout.setSpacing(10)
        layout.addWidget(own_frame)

        if ranking_id == "company_level":
            self._level_list_layout = list_layout
            self._level_own_layout = own_layout
        else:
            self._earnings_list_layout = list_layout
            self._earnings_own_layout = own_layout
        return page

    def _refresh_ranking(self, ranking_id: str, list_layout: QVBoxLayout, own_layout: QVBoxLayout) -> None:
        self._clear_layout(list_layout)
        self._clear_layout(own_layout)
        entries = self._provider.ranking(ranking_id, self._limit)
        own = self._provider.own_entry(ranking_id)
        for entry in entries:
            list_layout.addWidget(self._entry_row(ranking_id, entry))
        list_layout.addStretch(1)

        self._add_footer_summary(ranking_id, own_layout, own)
        if ranking_id == self._current_ranking_id():
            self._rank_metric[1].setText(f"#{own.rank}")
            self._level_metric[1].setText(f"LEVEL {own.company_level}")
            self._tracked_metric[1].setText(str(len(entries)))

    def _add_footer_summary(self, ranking_id: str, own_layout: QHBoxLayout, own: LeaderboardEntry) -> None:
        items = (
            ("YOUR RANK", f"#{own.rank}"),
            ("YOUR COMPANY", own.player_name.upper()),
            ("CURRENT METRIC", self._ranking_name(ranking_id)),
        )
        for label_text, value_text in items:
            block = QFrame()
            block.setObjectName("leaderboardFooterMetric")
            block_layout = QVBoxLayout(block)
            block_layout.setContentsMargins(0, 0, 0, 0)
            block_layout.setSpacing(1)
            label = QLabel(label_text)
            label.setObjectName("leaderboardFooterLabel")
            value = QLabel(value_text)
            value.setObjectName("leaderboardFooterValue")
            block_layout.addWidget(label)
            block_layout.addWidget(value)
            own_layout.addWidget(block, 1)
        if own.rank > self._limit:
            own_layout.addWidget(self._entry_row(ranking_id, own))

    def _entry_row(self, ranking_id: str, entry: LeaderboardEntry) -> QFrame:
        row = QFrame()
        row.setObjectName("leaderboardRow")
        row.setProperty("ownPlayer", entry.is_current_player)
        row.setProperty("topRank", entry.rank <= 3)
        row.setProperty("rankTier", self._rank_tier(entry.rank))
        layout = QHBoxLayout(row)
        layout.setContentsMargins(13, 9, 13, 9)
        layout.setSpacing(12)
        row.setMinimumHeight(68)

        rank = QLabel(f"#{entry.rank}")
        rank.setObjectName("leaderboardRank")
        rank.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rank.setFixedWidth(52)

        identity = QVBoxLayout()
        identity.setContentsMargins(0, 0, 0, 0)
        identity.setSpacing(3)
        player = QLabel(entry.player_name)
        player.setObjectName("leaderboardPlayer")
        player.setWordWrap(False)
        meta = QHBoxLayout()
        meta.setContentsMargins(0, 0, 0, 0)
        meta.setSpacing(6)
        title = QLabel(entry.title.upper())
        title.setObjectName("leaderboardTitle")
        level = QLabel(f"LEVEL {entry.company_level}")
        level.setObjectName("leaderboardLevel")
        meta.addWidget(title)
        meta.addWidget(level)
        if entry.is_current_player:
            badge = QLabel("YOU")
            badge.setObjectName("leaderboardYouBadge")
            meta.addWidget(badge)
        meta.addStretch(1)
        identity.addWidget(player)
        identity.addLayout(meta)

        value_block = QVBoxLayout()
        value_block.setContentsMargins(0, 0, 0, 0)
        value_block.setSpacing(2)
        value = QLabel(self._value_text(ranking_id, entry))
        value.setObjectName("leaderboardValue")
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        secondary = QLabel(self._secondary_value_text(ranking_id, entry))
        secondary.setObjectName("leaderboardSecondaryValue")
        secondary.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value_block.addWidget(value)
        value_block.addWidget(secondary)

        layout.addWidget(rank)
        layout.addLayout(identity, 1)
        layout.addLayout(value_block)
        return row

    def _value_text(self, ranking_id: str, entry: LeaderboardEntry) -> str:
        if ranking_id == "total_earnings":
            return f"${entry.total_earnings:,.0f}"
        return f"Level {entry.company_level}"

    def _secondary_value_text(self, ranking_id: str, entry: LeaderboardEntry) -> str:
        if ranking_id == "total_earnings":
            return f"LEVEL {entry.company_level} · {entry.title.upper()}"
        return f"${entry.total_earnings:,.0f} TOTAL"

    def _set_ranking_index(self, index: int) -> None:
        self._tabs.setCurrentIndex(index)
        self._refresh_metric_state()

    def _refresh_metric_state(self, *_args) -> None:
        current = self._tabs.currentIndex() if hasattr(self, "_tabs") else 0
        for index, button in enumerate(getattr(self, "_metric_buttons", [])):
            button.setProperty("active", index == current)
            button.style().unpolish(button)
            button.style().polish(button)
        if hasattr(self, "_rank_metric"):
            own = self._provider.own_entry(self._current_ranking_id())
            entries = self._provider.ranking(self._current_ranking_id(), self._limit)
            self._rank_metric[1].setText(f"#{own.rank}")
            self._level_metric[1].setText(f"LEVEL {own.company_level}")
            self._tracked_metric[1].setText(str(len(entries)))

    def _current_ranking_id(self) -> str:
        if not hasattr(self, "_tabs"):
            return RANKINGS[0][0]
        index = max(0, min(self._tabs.currentIndex(), len(RANKINGS) - 1))
        return RANKINGS[index][0]

    def _ranking_name(self, ranking_id: str) -> str:
        return next((name for rid, name in RANKINGS if rid == ranking_id), ranking_id.upper())

    def _rank_tier(self, rank: int) -> str:
        if rank == 1:
            return "gold"
        if rank == 2:
            return "silver"
        if rank == 3:
            return "bronze"
        return "standard"

    def _clear_layout(self, layout) -> None:
        clear_layout_safely(layout)
