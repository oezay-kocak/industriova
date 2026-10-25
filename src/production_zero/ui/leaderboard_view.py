from __future__ import annotations

import re

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget

from production_zero.services.interfaces import LeaderboardEntry, LeaderboardService
from production_zero.ui.game_ui import Accent
from production_zero.ui.main_tab_header import MainTabHeader
from production_zero.ui.widget_lifecycle import clear_layout_safely


RANKINGS = (("company_level", "COMPANY LEVEL"), ("total_earnings", "TOTAL EARNINGS"), ("production", "PRODUCTION"))


class LeaderboardView(QWidget):
    profile_requested = Signal(object)

    def __init__(self, provider: LeaderboardService, limit: int = 1000) -> None:
        super().__init__()
        self._provider = provider
        self._limit = limit
        self._selected_product_id = "iron_ore"
        self._snapshots = {}
        self._rows_by_rank = {}
        self._scrolls = {}
        self._located_row = None
        self._highlight_timer = QTimer(self)
        self._highlight_timer.setSingleShot(True)
        self._highlight_timer.setInterval(2200)
        self._highlight_timer.timeout.connect(self._clear_highlight)
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
        self._search = QLineEdit()
        self._search.setObjectName("leaderboardSearch")
        self._search.setPlaceholderText("SEARCH COMPANY OR RANK")
        self._search.setAccessibleName("Search company or rank")
        self._search.setClearButtonEnabled(True)
        self._search.setMaxLength(256)
        self._search.setMinimumWidth(240)
        self._search.setMaximumWidth(330)
        self._search.returnPressed.connect(self._search_jump)
        self._search.textEdited.connect(lambda _text: self._search_status.clear())
        self._search_status = QLabel()
        self._search_status.setObjectName("leaderboardSearchStatus")
        self._search_status.setFixedWidth(125)
        switch_layout.addWidget(self._search, 1)
        switch_layout.addWidget(self._search_status)
        layout.addWidget(switch_deck)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("leaderboardTabs")
        self._tabs.tabBar().hide()
        self._tabs.setDocumentMode(True)
        self._tabs.currentChanged.connect(self._refresh_metric_state)
        self._tabs.addTab(self._build_ranking_page("company_level"), "Company Level")
        self._tabs.addTab(self._build_ranking_page("total_earnings"), "Total Earnings")
        product_page = self._build_ranking_page("production")
        self._product_button = QPushButton("SELECT PRODUCT / INDUSTRY")
        self._product_button.setObjectName("leaderboardProductPickerButton")
        self._product_button.clicked.connect(self._open_product_picker)
        product_page.layout().insertWidget(0, self._product_button)
        self._tabs.addTab(product_page, "Product Production")
        layout.addWidget(self._tabs, 1)
        self.refresh()

    def refresh(self) -> None:
        for ranking_id, list_layout, own_layout in (
            ("company_level", self._level_list_layout, self._level_own_layout),
            ("total_earnings", self._earnings_list_layout, self._earnings_own_layout),
            ("production", self._production_list_layout, self._production_own_layout),
        ):
            self._refresh_ranking(ranking_id, list_layout, own_layout)
        self._refresh_metric_state()

    def _open_product_picker(self):
        from types import SimpleNamespace
        from importlib.resources import files
        from production_zero.data.definitions import load_resource_definitions
        from production_zero.ui.contracts_view import ContractProductPicker
        from production_zero.ui.release_dialogs import IndustrialDialog
        cached = getattr(self, "_product_dialog", None)
        if cached is not None:
            self._product_picker.findChild(QLabel, "productionCurrentLabel").setText(
                f"Current: {self._product_resources[self._selected_product_id].name}")
            cached.exec()
            return
        resources = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
        self._product_resources = resources
        dialog = IndustrialDialog("Product production rankings", "Cumulative accepted production. Local company data until a server is connected.", self)
        dialog.resize(950, 650)
        picker = ContractProductPicker([SimpleNamespace(resource_id=rid, name=r.name) for rid, r in resources.items()], resources, set(), resources[self._selected_product_id].name, purpose_label="CUMULATIVE PRODUCTION")
        self._product_dialog = dialog
        self._product_picker = picker
        dialog.layout().itemAt(0).widget().layout().insertWidget(2, picker)
        def select(rid):
            self._selected_product_id = rid
            self._product_button.setText(f"{resources[rid].name} · SELECT PRODUCT / INDUSTRY")
            self.refresh()
            dialog.accept()
        picker.product_selected.connect(select)
        picker.back_requested.connect(dialog.reject)
        dialog.accept_button.hide()
        dialog.reject_button.hide()
        dialog.exec()

    def _build_header(self) -> QFrame:
        header = MainTabHeader(
            object_name="leaderboardPageHeader",
            title="LEADERBOARD",
            subtitle="GLOBAL RANKINGS / COMPANY DOMINANCE",
            title_object_name="leaderboardHeroTitle",
            subtitle_object_name="leaderboardHeroSubtitle",
            accent=Accent.NEUTRAL,
        )

        return header

    def _build_ranking_page(self, ranking_id: str) -> QWidget:
        page = QWidget()
        page.setObjectName("leaderboardRankingPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setObjectName(f"{ranking_id}LeaderboardScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scrolls[ranking_id] = scroll
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName(f"{ranking_id}LeaderboardContent")
        list_layout = QVBoxLayout(content)
        list_layout.setContentsMargins(0, 0, 6, 0)
        list_layout.setSpacing(8)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        own_frame = QFrame()
        own_frame.setObjectName("leaderboardPinnedContainer")
        own_layout = QHBoxLayout(own_frame)
        own_layout.setContentsMargins(0, 0, 6, 0)
        own_layout.setSpacing(10)
        layout.addWidget(own_frame)

        if ranking_id == "company_level":
            self._level_list_layout = list_layout
            self._level_own_layout = own_layout
        elif ranking_id == "total_earnings":
            self._earnings_list_layout = list_layout
            self._earnings_own_layout = own_layout
        else:
            self._production_list_layout = list_layout
            self._production_own_layout = own_layout
        return page

    def _refresh_ranking(self, ranking_id: str, list_layout: QVBoxLayout, own_layout: QHBoxLayout) -> None:
        provider_id = f"production.{self._selected_product_id}" if ranking_id == "production" else ranking_id
        entries = self._provider.ranking(provider_id, self._limit)
        own = self._provider.own_entry(provider_id)
        snapshot = (entries, own)
        if self._snapshots.get(ranking_id) == snapshot:
            return
        previous = self._snapshots.get(ranking_id)
        others = tuple(entry for entry in entries if not entry.is_current_player)
        old_others = tuple(entry for entry in previous[0] if not entry.is_current_player) if previous else None
        rows = self._rows_by_rank.get(ranking_id, {}).copy()
        if others != old_others:
            self._clear_highlight()
            self._clear_layout(list_layout)
            rows = {}
            for entry in others:
                row = self._entry_row(ranking_id, entry)
                list_layout.addWidget(row)
                rows[entry.rank] = row
            list_layout.addStretch(1)
        if previous is None or previous[1] != own:
            if previous is None:
                pinned = self._entry_row(ranking_id, own)
                pinned.setProperty("pinnedPlayer", True)
                own_layout.addWidget(pinned)
            else:
                pinned = own_layout.itemAt(0).widget()
                self._update_entry_row(pinned, ranking_id, own)
            if previous and previous[1].rank != own.rank and previous[1].rank not in {e.rank for e in others}:
                rows.pop(previous[1].rank, None)
        else:
            pinned = own_layout.itemAt(0).widget()
        rows[own.rank] = pinned
        self._snapshots[ranking_id] = snapshot
        self._rows_by_rank[ranking_id] = rows

    def _clear_highlight(self) -> None:
        self._highlight_timer.stop()
        if self._located_row is not None:
            self._located_row.setProperty("located", False)
            self._located_row.style().unpolish(self._located_row)
            self._located_row.style().polish(self._located_row)
            self._located_row = None

    def _search_jump(self) -> None:
        query = self._search.text().strip().casefold()
        self._clear_highlight()
        self._search_status.clear()
        if not query:
            return
        ranking_id = self._current_ranking_id()
        entries, own = self._snapshots[ranking_id]
        candidates = tuple(e for e in entries if not e.is_current_player) + (own,)
        rank_match = re.fullmatch(r"(?:#\s*|rank\s+)?([0-9]+)", query)
        target = None
        if rank_match:
            digits = rank_match.group(1)
            rank = int(digits) if len(digits) <= 9 else -1
            target = next((e for e in candidates if e.rank == rank), None)
        else:
            matches = [e for e in candidates if query in e.player_name.casefold()]
            if matches:
                target = min(matches, key=lambda e: (e.player_name.casefold() != query,
                    not e.player_name.casefold().startswith(query), e.rank))
        if target is None:
            self._search_status.setText("NO MATCH / RANK")
            return
        row = self._rows_by_rank[ranking_id][target.rank]
        if not target.is_current_player:
            scroll = self._scrolls[ranking_id]
            scroll.widget().layout().activate()
            scroll.verticalScrollBar().setValue(row.y() + row.height() // 2 - scroll.viewport().height() // 2)
        row.setProperty("located", True)
        row.style().unpolish(row)
        row.style().polish(row)
        self._located_row = row
        self._search_status.setText("YOUR COMPANY" if target.is_current_player else f"FOUND #{target.rank}")
        self._highlight_timer.start()

    def _entry_row(self, ranking_id: str, entry: LeaderboardEntry) -> QFrame:
        row = QFrame()
        row.setObjectName("leaderboardRow")
        row.setProperty("ownPlayer", entry.is_current_player)
        row.setProperty("rank", entry.rank)
        row.setProperty("alternating", entry.rank % 2 == 0)
        row.setProperty("topRank", entry.rank <= 3)
        row.setProperty("rankTier", self._rank_tier(entry.rank))
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(10)
        row.setMinimumHeight(46)
        row.setMaximumHeight(48)

        rank = QLabel(f"#{entry.rank}")
        rank.setObjectName("leaderboardRank")
        rank.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rank.setFixedWidth(46)

        identity = QVBoxLayout()
        identity.setContentsMargins(0, 0, 0, 0)
        identity.setSpacing(1)
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
        value_block.setSpacing(1)
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
        from production_zero.ui.pz_controls import RaisedPZButton
        profile = RaisedPZButton("PROFILE", variant="secondary")
        profile.setFixedSize(72, 28)
        profile.setAccessibleName(f"Open profile for {entry.player_name}")
        row._leaderboard_entry = entry
        row._profile_button = profile
        row._entry_labels = dict(rank=rank, player=player, title=title, level=level, value=value, secondary=secondary)
        profile.clicked.connect(lambda: self.profile_requested.emit(row._leaderboard_entry))
        layout.addWidget(profile)
        return row

    def _update_entry_row(self, row, ranking_id, entry):
        row._leaderboard_entry = entry
        row._profile_button.setAccessibleName(f"Open profile for {entry.player_name}")
        labels = row._entry_labels
        for key, value in dict(rank=f"#{entry.rank}", player=entry.player_name,
                               title=entry.title.upper(), level=f"LEVEL {entry.company_level}",
                               value=self._value_text(ranking_id, entry),
                               secondary=self._secondary_value_text(ranking_id, entry)).items():
            if labels[key].text() != value:
                labels[key].setText(value)
        changed = False
        for key, value in dict(rank=entry.rank, alternating=entry.rank % 2 == 0,
                               topRank=entry.rank <= 3, rankTier=self._rank_tier(entry.rank)).items():
            if row.property(key) != value:
                row.setProperty(key, value)
                changed = True
        if changed:
            row.style().unpolish(row)
            row.style().polish(row)

    def _value_text(self, ranking_id: str, entry: LeaderboardEntry) -> str:
        if ranking_id == "production":
            return f"{entry.production_amount:,.1f} produced"
        if ranking_id == "total_earnings":
            return f"${entry.total_earnings:,.0f}"
        return f"Level {entry.company_level}"

    def _secondary_value_text(self, ranking_id: str, entry: LeaderboardEntry) -> str:
        if ranking_id == "total_earnings":
            return f"LEVEL {entry.company_level} · {entry.title.upper()}"
        return f"${entry.total_earnings:,.0f} TOTAL"

    def _set_ranking_index(self, index: int) -> None:
        self._tabs.setCurrentIndex(index)
        self._clear_highlight()
        self._search_status.clear()
        self._scrolls[self._current_ranking_id()].verticalScrollBar().setValue(0)
        self.refresh()

    def _refresh_metric_state(self, *_args) -> None:
        current = self._tabs.currentIndex() if hasattr(self, "_tabs") else 0
        for index, button in enumerate(getattr(self, "_metric_buttons", [])):
            if bool(button.property("active")) != (index == current):
                button.setProperty("active", index == current)
                button.style().unpolish(button)
                button.style().polish(button)

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
