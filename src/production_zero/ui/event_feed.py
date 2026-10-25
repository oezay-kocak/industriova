from __future__ import annotations

from dataclasses import dataclass, replace
from time import monotonic

from PySide6.QtCore import QSize, Qt, QTimer, Signal, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from production_zero.core.company import xp_required_for_next_level
from production_zero.core.contracts import CONTRACT_KINDS, ActiveContract
from production_zero.core.definitions import CardDefinition
from production_zero.core.freight import MarketDeliveryResolution
from production_zero.core.packs import PACK_TYPE_LABELS
from production_zero.core.progression import production_option_for_id
from production_zero.core.state import GameState
from production_zero.ui.resource_icons import ResourceIconWidget, resource_accent_key, resource_icon_key
from production_zero.ui.theme import Theme


AGGREGATION_SECONDS = 3.0
DISPLAY_INTERVAL_SECONDS = 2.5
SLIDE_DURATION_MS = 400
LIVE_ENTRY_LIMIT = 3
HISTORY_LIMIT = 40
PENDING_LIMIT = 24
ACTIVITY_PANEL_SIZE = QSize(470, 540)
ACTIVITY_PANEL_HEADER_HEIGHT = 54


@dataclass(slots=True)
class FeedEvent:
    event_type: str
    label: str
    amount: float = 0.0
    count: int = 1
    group_key: str = ""
    resource_id: str = ""


@dataclass(slots=True)
class _PendingEvent:
    event_type: str
    label: str
    amount: float
    count: int
    group_key: str
    resource_id: str
    created_at: float
    updated_at: float


@dataclass(frozen=True, slots=True)
class _ContractSnapshot:
    contract_id: str
    status: str
    reward_cash: float
    reward_xp: float
    active: ActiveContract
    delivered: tuple[tuple[str, float], ...]


class EventFeedEntry(QFrame):
    def __init__(self, event: FeedEvent) -> None:
        super().__init__()
        self.setObjectName("eventFeedEntry")
        self.setProperty("eventType", event.event_type)
        self.event = replace(event)
        self.created_at = monotonic()
        self.setFixedHeight(28)
        self.setMinimumWidth(0)
        self.setStyleSheet('QFrame#eventFeedEntry {background: #20292d; border: 1px solid #59676b; border-radius: 4px;}')
        self._slide = QPropertyAnimation(self, b'pos', self)
        self._slide.setDuration(SLIDE_DURATION_MS)
        self._slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 1, 6, 1)
        layout.setSpacing(0)
        from production_zero.ui.resource_tiles import ElidedResourceLabel
        amount = ElidedResourceLabel(self._amount_text(event))
        amount.setObjectName("eventFeedAmount")
        amount.setProperty("eventType", event.event_type)
        label = ElidedResourceLabel(self._label_text(event))
        label.setObjectName("eventFeedLabel")
        label.setStyleSheet('color: #eff8f4; font-size: 10px; border: 0; background: transparent;')
        accent = {'cash': Theme.CASH, 'xp': Theme.RESOURCE, 'research': Theme.SAFETY_YELLOW,
                  'contract': Theme.GOOD, 'delivery': Theme.GOOD}.get(event.event_type, Theme.SAFETY_YELLOW)
        amount.setStyleSheet(f'color: {accent}; font-size: 11px; font-weight: 900; border: 0; background: transparent;')

        amount.setFixedHeight(13)
        label.setFixedHeight(11)
        layout.addWidget(amount)
        layout.addWidget(label)
        self.setToolTip(self._amount_text(event) + " · " + self._label_text(event))

    def slide_to(self, target):
        if self.pos() == target:
            return
        if self._slide.state() == QPropertyAnimation.State.Running and self._slide.endValue() == target:
            return
        self._slide.stop()
        self._slide.setStartValue(self.pos())
        self._slide.setEndValue(target)
        self._slide.start()

    def _amount_text(self, event: FeedEvent) -> str:
        if event.event_type == "daily_activity":
            return ""
        if event.event_type == "research":
            return "RESEARCH"
        if event.event_type == "cash":
            return f"+${event.amount:,.0f}"
        if event.event_type == "xp":
            value = f'{event.amount:,.2f}'.rstrip('0').rstrip('.')
            return f'+{value} XP'
        if event.event_type == 'rp':
            return f'+{event.amount:,.0f} RP'
        if event.event_type == "pack":
            return f"+{event.count} {'PACKS' if event.count != 1 else 'PACK'}"
        if event.event_type == "unlock":
            return "NEW"
        if event.event_type == "delivery":
            return f"{event.amount:g}"
        return "DONE"

    def _label_text(self, event: FeedEvent) -> str:
        if event.count > 1 and event.event_type != "pack":
            return f"{event.label} ×{event.count}"
        if event.count > 1 and event.event_type == "pack":
            return event.label
        return event.label


class ActivityMessageCard(QFrame):
    activated = Signal(str)

    def __init__(
        self,
        title: str,
        secondary: str,
        icon: ResourceIconWidget,
        *,
        status: str = "",
        resource_id: str = "",
    ) -> None:
        super().__init__()
        self.setObjectName("activityMessageCard")
        self.setProperty("interactive", bool(resource_id))
        self.setProperty("resourceId", resource_id)
        self._resource_id = resource_id
        if resource_id:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(11)
        icon.setObjectName("activityMessageIcon")
        layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        copy = QVBoxLayout()
        copy.setSpacing(3)
        title_label = QLabel(title.upper())
        title_label.setObjectName("activityMessageTitle")
        title_label.setWordWrap(True)
        secondary_label = QLabel(secondary)
        secondary_label.setObjectName("activityMessageSecondary")
        secondary_label.setWordWrap(True)
        copy.addWidget(title_label)
        copy.addWidget(secondary_label)
        if status:
            status_label = QLabel(status.upper())
            status_label.setObjectName("activityMessageStatus")
            copy.addWidget(status_label)
        layout.addLayout(copy, 1)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._resource_id and event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.activated.emit(self._resource_id)
        super().mouseReleaseEvent(event)


class ActivityPanel(QFrame):
    def __init__(self, parent: QWidget, *, title: str, subtitle: str, object_name: str) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName(object_name)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setFixedSize(ACTIVITY_PANEL_SIZE)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        frame = QFrame()
        frame.setObjectName("activityPanelFrame")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(12, 10, 12, 12)
        frame_layout.setSpacing(10)
        header_frame = QFrame()
        header_frame.setObjectName("activityPanelHeader")
        header_frame.setFixedHeight(ACTIVITY_PANEL_HEADER_HEIGHT)
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        copy = QVBoxLayout()
        copy.setSpacing(1)
        heading = QLabel(title.upper())
        heading.setObjectName("activityPanelTitle")
        caption = QLabel(subtitle.upper())
        caption.setObjectName("activityPanelSubtitle")
        copy.addWidget(heading)
        copy.addWidget(caption)
        close = QPushButton("CLOSE")
        close.setObjectName("activityPanelClose")
        close.clicked.connect(self.close)
        header.addLayout(copy, 1)
        header.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        frame_layout.addWidget(header_frame)
        scroll = QScrollArea()
        scroll.setObjectName("activityPanelScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("activityPanelContent")
        self.cards = QVBoxLayout(content)
        self.cards.setContentsMargins(5, 5, 5, 5)
        self.cards.setSpacing(7)
        self.cards.addStretch(1)
        scroll.setWidget(content)
        frame_layout.addWidget(scroll, 1)
        outer.addWidget(frame)

    def add_card(self, card: ActivityMessageCard) -> None:
        self.cards.insertWidget(self.cards.count() - 1, card)

    def show_for(self, anchor: QWidget) -> None:
        pos = anchor.mapToGlobal(anchor.rect().bottomRight())
        pos.setX(pos.x() - self.width())
        screen = anchor.screen()
        if screen is not None:
            bounds = screen.availableGeometry().adjusted(8, 8, -8, -8)
            pos.setX(max(bounds.left(), min(pos.x(), bounds.right() - self.width())))
            pos.setY(max(bounds.top(), min(pos.y(), bounds.bottom() - self.height())))
        self.move(pos)
        self.show()
        self.raise_()


class EventFeedWidget(QFrame):
    navigate_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None, *, state: GameState | None = None, definitions=None) -> None:
        super().__init__(parent)
        self.setObjectName("eventFeed")
        self._state = state
        self._definitions = definitions or {}
        self._pending: dict[str, _PendingEvent] = {}
        self._ready: dict[str, FeedEvent] = {}
        self._next_display_at = 0.0
        self._entries: list[EventFeedEntry] = []
        self._departing: list[EventFeedEntry] = []
        self._history: list[FeedEvent] = []
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(7, 2, 5, 2)
        self._layout.setSpacing(5)
        self._live_panel = QFrame(self)
        self._live_panel.setObjectName('activityFeedBand')
        self._live_panel.setStyleSheet('QFrame#activityFeedBand {background: #0d1416; border: 0;}')
        self._layout.addWidget(self._live_panel, 1)
        from production_zero.ui.pz_controls import RaisedPZButton
        self._history_button = RaisedPZButton("HISTORY", variant="secondary")
        self._history_button.setObjectName("eventFeedHistoryButton")
        self._history_button.clicked.connect(self._show_history)
        self._inbox_button = RaisedPZButton(variant="secondary")
        self._inbox_button.setObjectName("companyInboxButton")
        self._inbox_button.clicked.connect(self._show_inbox)
        self._inbox_attention = QTimer(self)
        self._inbox_attention.setInterval(700)
        self._inbox_attention.timeout.connect(self._pulse_inbox)
        self._layout.addWidget(self._history_button)
        self._layout.addWidget(self._inbox_button)
        self.setFixedHeight(34)
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self.refresh_communications()

    def move_communication_buttons(self, layout):
        for button in (self._history_button, self._inbox_button):
            self._layout.removeWidget(button)
            button.setMinimumHeight(42)
            button.setMinimumWidth(96)
            from production_zero.ui.game_ui.tokens import GAME_UI_TOKENS
            font = GAME_UI_TOKENS.typography.industrial_label()
            button.setStyleSheet(f"font-family: '{font.family()}'; font-size: 16px; font-weight: 700;")
            layout.addWidget(button)

    def _pulse_inbox(self):
        # Repaint only this existing button, never the command deck or window.
        if not self._inbox_button.isVisible() or not self._inbox_button.property('unread'):
            return
        self._inbox_button.setProperty('attentionPhase', not self._inbox_button.property('attentionPhase'))
        self._inbox_button.update()

    def hideEvent(self, event):
        self._inbox_attention.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_communications()
        self._position_live_panel()

    def close_panels(self):
        for name in ("_history_panel", "_inbox_panel"):
            panel = getattr(self, name, None)
            setattr(self, name, None)
            from shiboken6 import isValid
            if panel is not None and isValid(panel):
                panel.close()

    @staticmethod
    def _merge_events(first: FeedEvent, second: FeedEvent) -> FeedEvent:
        same_source = (first.label, first.group_key, first.resource_id) == (second.label, second.group_key, second.resource_id)
        label = first.label if same_source else {
            'cash': 'Income', 'xp': 'Company Progress', 'rp': 'Research rewards',
            'delivery': 'Freight deliveries', 'unlock': 'Production unlocked',
            'pack': 'Packs received', 'contract': 'Contracts completed',
            'level_up': 'Company levels', 'research': 'Research updates',
            'daily_activity': 'Daily activity',
        }.get(first.event_type, 'Activity')
        return FeedEvent(first.event_type, label, first.amount + second.amount,
                         first.count + second.count, first.group_key if same_source else '',
                         first.resource_id if same_source else '')

    def push(self, event: FeedEvent) -> None:
        if event.event_type == 'xp' and event.amount <= 0:
            return
        now = monotonic()
        # Finish due windows before adding a boundary arrival to the next window.
        self._flush_due(now)
        kind = event.event_type
        if kind not in self._pending and len(self._pending) >= PENDING_LIMIT - 1:
            kind = '__other__'
            event = replace(event, event_type=kind, label='Other activity', group_key='', resource_id='')
        pending = self._pending.get(kind)
        if pending is None:
            self._pending[kind] = _PendingEvent(event.event_type, event.label, event.amount,
                event.count, event.group_key, event.resource_id, now, now)
        else:
            merged = self._merge_events(self._pending_event(pending), event)
            pending.label, pending.amount, pending.count = merged.label, merged.amount, merged.count
            pending.group_key, pending.resource_id = merged.group_key, merged.resource_id
            pending.updated_at = now

    @staticmethod
    def _pending_event(pending):
        return FeedEvent(pending.event_type, pending.label, pending.amount, pending.count,
                         pending.group_key, pending.resource_id)

    def _flush_due(self, now, *, force=False):
        for kind, pending in tuple(self._pending.items()):
            if force or now - pending.created_at >= AGGREGATION_SECONDS:
                del self._pending[kind]
                event = self._pending_event(pending)
                self._history.insert(0, replace(event))
                del self._history[HISTORY_LIMIT:]
                if kind not in self._ready and len(self._ready) >= PENDING_LIMIT - 1:
                    kind = '__other__'
                    event = replace(event, event_type=kind, label='Other activity', group_key='', resource_id='')
                if kind in self._ready:
                    self._ready[kind] = self._merge_events(self._ready[kind], event)
                else:
                    self._ready[kind] = event

    def flush_pending(self) -> None:
        self._flush_due(monotonic(), force=True)
        self._present_next(monotonic())

    def entry_texts(self) -> tuple[str, ...]:
        return tuple(' '.join(label.text() for label in entry.findChildren(QLabel)) for entry in self._entries)

    def _tick(self) -> None:
        now = monotonic()
        self._flush_due(now)
        self._present_next(now)

    def _present_next(self, now):
        if not self._ready or now < self._next_display_at:
            return
        # The queue stores one summary per type, rather than one item per truck.
        kind = next(iter(self._ready))
        event = self._ready.pop(kind)
        entry = EventFeedEntry(event)
        entry.setParent(self._live_panel)
        self._entries.insert(0, entry)
        self._position_live_panel(animate=True, incoming=entry)
        if len(self._entries) > LIVE_ENTRY_LIMIT:
            old = self._entries.pop()
            self._departing.append(old)
            def finished():
                if old in self._departing:
                    self._departing.remove(old)
                old.hide()
                old.deleteLater()
            old._slide.finished.connect(finished)
            old.slide_to(QPoint(self._live_panel.width() + 6, 0))
        self._next_display_at = now + DISPLAY_INTERVAL_SECONDS

    @property
    def history(self) -> tuple[FeedEvent, ...]:
        return tuple(self._history)

    def clear_events(self) -> None:
        self._pending.clear()
        self._ready.clear()
        self._history.clear()
        self._next_display_at = 0.0
        for entry in self._entries + self._departing:
            entry._slide.stop()
            entry.hide()
            entry.deleteLater()
        self._entries.clear()
        self._departing.clear()
        self.close_panels()
        self.refresh_communications()

    def refresh_communications(self) -> None:
        unread = self._state.communications.unread_count if self._state is not None else 0
        text = f"INBOX  {unread}" if unread else "INBOX"
        if self._inbox_button.text() != text:
            self._inbox_button.setText(text)
        if bool(self._inbox_button.property('unread')) != (unread > 0):
            self._inbox_button.setProperty('unread', unread > 0)
            self._inbox_button.setProperty('attentionPhase', unread > 0)
            self._inbox_button.update()
        if unread and not self._inbox_attention.isActive():
            self._inbox_attention.start()
        elif not unread:
            self._inbox_attention.stop()

    def _event_text(self, event: FeedEvent) -> str:
        if event.event_type == "daily_activity":
            return event.label
        probe = EventFeedEntry(event)
        text = " ".join(label.text() for label in probe.findChildren(QLabel))
        probe.deleteLater()
        return text

    def _position_live_panel(self, *, animate=False, incoming=None):
        width = max(1, (self._live_panel.width() - 12) // LIVE_ENTRY_LIMIT)
        height = max(1, self._live_panel.height())
        for index, entry in enumerate(self._entries):
            entry.setFixedSize(width, height)
            target = QPoint(index * (width + 6), 0)
            if entry is incoming:
                entry.move(-width - 6, 0)
            entry.show()
            if animate:
                entry.slide_to(target)
            else:
                entry._slide.stop()
                entry.move(target)
        if not animate:
            for entry in self._departing:
                entry._slide.stop()
                entry.hide()
                entry.deleteLater()
            self._departing.clear()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, '_live_panel'):
            self._layout.activate()
            self._position_live_panel()

    def _show_history(self) -> None:
        self.close_panels()
        panel = ActivityPanel(
            self,
            title="Activity History",
            subtitle="Recent industrial activity",
            object_name="eventFeedHistoryPanel",
        )
        if not self._history:
            panel.add_card(ActivityMessageCard(
                "No recent activity",
                "Completed production and company events will appear here.",
                self._semantic_icon("history", ""),
            ))
        for event in self._history:
            panel.add_card(ActivityMessageCard(
                self._event_text(event),
                self._history_secondary(event),
                self._semantic_icon(event.event_type, event.resource_id),
                status="Recent",
            ))
        panel.show_for(self._inbox_button)
        self._history_panel = panel

    def _show_inbox(self) -> None:
        self.close_panels()
        panel = ActivityPanel(
            self,
            title="Company Inbox",
            subtitle="Persistent company communications",
            object_name="companyInboxPanel",
        )
        if self._state is None or not self._state.communications.messages:
            panel.add_card(ActivityMessageCard(
                "No company communications",
                "Important progression messages will appear here.",
                self._semantic_icon("inbox", ""),
            ))
        else:
            for message in reversed(self._state.communications.messages):
                was_unread = not message.read
                self._state.communications.mark_read(message.message_id)
                for production_id in message.item_ids:
                    option = production_option_for_id(self._definitions, production_id)
                    resource_id = option.output_resource if option is not None else production_id.rsplit(".", 1)[-1]
                    stage = option.stage.value.replace("_", " ").title() if option is not None else "Production"
                    icon = ResourceIconWidget(resource_id, resource_icon_key(resource_id), resource_accent_key(resource_id), size=42)
                    card = ActivityMessageCard(
                        f"{self._production_name(production_id)} unlocked",
                        stage,
                        icon,
                        status="New · View in Unlock Tree" if was_unread else "View in Unlock Tree",
                        resource_id=resource_id,
                    )
                    card.activated.connect(self._navigate_from_inbox)
                    panel.add_card(card)
        self.refresh_communications()
        panel.show_for(self._inbox_button)
        self._inbox_panel = panel

    def _navigate_from_inbox(self, resource_id: str) -> None:
        panel = getattr(self, "_inbox_panel", None)
        if panel is not None:
            panel.close()
        self.navigate_requested.emit(resource_id)

    def _semantic_icon(self, event_type: str, resource_id: str = "") -> ResourceIconWidget:
        if resource_id:
            return ResourceIconWidget(
                resource_id,
                resource_icon_key(resource_id),
                resource_accent_key(resource_id),
                size=42,
            )
        fallbacks = {
            "cash": ("cash", "package", "crop"),
            "xp": ("company_progress", "gear", "battery"),
            "rp": ("research_points", "gear", "battery"),
            "daily_activity": ("company_progress", "gear", "battery"),
            "pack": ("pack", "package", "component"),
            "contract": ("contract", "package", "default"),
            "delivery": ("delivery", "rail", "rail"),
            "unlock": ("unlock", "gear", "battery"),
            "inbox": ("inbox", "package", "component"),
            "history": ("history", "rail", "rail"),
        }
        resource_id, icon_key, accent_key = fallbacks.get(event_type, (event_type, "hex", "default"))
        return ResourceIconWidget(resource_id, icon_key, accent_key, size=42)

    def _history_secondary(self, event: FeedEvent) -> str:
        return {
            "cash": "Economy / delivery",
            "xp": "Company progression",
            "rp": "Research points earned",
            "daily_activity": "Daily Activity allowance completed",
            "pack": "Pack inventory",
            "contract": "Contract operations",
            "delivery": "Logistics / shipment",
            "unlock": "Production progression",
        }.get(event.event_type, "Industrial activity")

    def _production_name(self, production_id: str) -> str:
        option = production_option_for_id(self._definitions, production_id)
        return option.name if option is not None else production_id.rsplit(".", 1)[-1].replace("_", " ").title()


class EventFeedController:
    def __init__(
        self,
        state: GameState,
        feed: EventFeedWidget,
        cash_highlight_callback=None,
        definitions: dict[str, CardDefinition] | None = None,
    ) -> None:
        self._state = state
        self._feed = feed
        self._cash_highlight_callback = cash_highlight_callback
        self._definitions = definitions or {}
        self.reset_baseline()

    def reset_baseline(self) -> None:
        state = self._state
        self._cash = state.cash.amount
        self._earnings = state.statistics.total_earnings
        self._xp_total = self._company_xp_total()
        self._continuity_xp = state.company_xp_progress.xp_by_source.get("continuity", 0.0)
        self._packs = self._pack_snapshot()
        self._contracts = self._contract_snapshot()
        self._market_delivery_count = self._market_delivery_watermark()

    def observe(self) -> None:
        from production_zero.core.research import sync_research_clock
        sync_research_clock(self._state)
        for event_type, label in self._state.communications.pending_activity:
            if event_type == 'research' and label.startswith('+') and ' RP · ' in label:
                value, source = label.split(' RP · ', 1)
                self._feed.push(FeedEvent('rp', source, float(value), group_key=source))
            else:
                self._feed.push(FeedEvent(event_type, label, group_key=label))
        self._state.communications.pending_activity.clear()
        previous_cash = self._cash
        previous_earnings = self._earnings
        previous_xp = self._xp_total
        previous_packs = self._packs
        previous_contracts = self._contracts
        previous_market_delivery_count = self._market_delivery_count

        self._cash = self._state.cash.amount
        self._earnings = self._state.statistics.total_earnings
        self._xp_total = self._company_xp_total()
        self._packs = self._pack_snapshot()
        self._contracts = self._contract_snapshot()
        self._market_delivery_count = self._market_delivery_watermark()

        completed_shipments = self._completed_market_deliveries(previous_market_delivery_count)
        shipment_cash = 0.0
        for delivery in completed_shipments:
            amount = delivery.market_earnings
            shipment_cash += amount
            resource = delivery.resource_id.replace("_", " ").title() or "Resource"
            if delivery.market_amount > 0 and amount > 0:
                self._feed.push(
                    FeedEvent(
                        "cash",
                        f"{resource} Shipment",
                        amount,
                        group_key=f"market:{delivery.resource_id}",
                        resource_id=delivery.resource_id,
                    )
                )

        self._push_contract_deliveries(previous_contracts)

        contract_cash = 0.0
        contract_xp = 0.0
        for kind, contract in previous_contracts.items():
            if contract.status != "active":
                continue
            # Keep the observed instance: regular completion removes it from state,
            # while cancellation/expiry must never be inferred as success.
            completed = contract.active.status == "completed"
            if not completed:
                continue
            contract_cash += contract.reward_cash
            contract_xp += contract.reward_xp
            completion_resource_id = (
                next(iter(contract.active.offer.requirements))
                if len(contract.active.offer.requirements) == 1
                else ""
            )
            self._feed.push(
                FeedEvent(
                    "contract",
                    "Contract completed",
                    resource_id=completion_resource_id,
                )
            )
            if contract.reward_cash > 0:
                self._feed.push(FeedEvent("cash", "Contract Reward", contract.reward_cash))
            if contract.reward_xp > 0:
                self._feed.push(FeedEvent("xp", f"{kind.title()} Contract", contract.reward_xp))

        cash_delta = max(self._cash - previous_cash, self._earnings - previous_earnings)
        known_cash = shipment_cash + contract_cash
        if cash_delta > 0.01 and self._cash_highlight_callback is not None:
            self._cash_highlight_callback(previous_cash, self._state.cash.amount)
        if cash_delta > known_cash + 0.01:
            self._feed.push(FeedEvent("cash", "Income", cash_delta - known_cash))

        continuity_xp = self._state.company_xp_progress.xp_by_source.get("continuity", 0.0)
        xp_delta = self._xp_total - previous_xp - max(0.0, continuity_xp - self._continuity_xp)
        self._continuity_xp = continuity_xp
        if xp_delta > contract_xp + 0.01:
            self._feed.push(FeedEvent("xp", "Company Progress", xp_delta - contract_xp))

        new_pack_types: dict[str, int] = {}
        for pack_id, (pack_type, _source) in self._packs.items():
            if pack_id not in previous_packs:
                new_pack_types[pack_type] = new_pack_types.get(pack_type, 0) + 1
        for pack_type, count in new_pack_types.items():
            self._feed.push(FeedEvent("pack", PACK_TYPE_LABELS.get(pack_type, "Pack"), count=count))

        pending_unlock_ids = list(self._state.production_progress.pending_unlock_ids)
        self._state.production_progress.pending_unlock_ids.clear()
        if pending_unlock_ids:
            self._state.communications.add_unlocks(pending_unlock_ids)
            self._feed.refresh_communications()
        roots = [production_id for production_id in pending_unlock_ids if production_id.startswith("resource.")]
        downstream = [production_id for production_id in pending_unlock_ids if production_id not in roots]
        if len(roots) <= 1 and len(pending_unlock_ids) <= 4:
            for production_id in pending_unlock_ids:
                self._feed.push(
                    FeedEvent(
                        "unlock",
                        f"{self._production_name(production_id)} unlocked",
                        resource_id=self._production_resource_id(production_id),
                    )
                )
        else:
            if roots:
                self._feed.push(FeedEvent("unlock", f"New resource family · {len(roots)} primary-production resources"))
            if downstream:
                self._feed.push(FeedEvent("unlock", f"Production expanded · {len(downstream)} recipes"))

    def _production_name(self, production_id: str) -> str:
        option = production_option_for_id(self._definitions, production_id)
        if option is not None:
            return option.name
        return production_id.rsplit(".", 1)[-1].replace("_", " ").title()

    def _production_resource_id(self, production_id: str) -> str:
        option = production_option_for_id(self._definitions, production_id)
        if option is not None:
            return option.output_resource
        if production_id.startswith("resource."):
            return production_id.rsplit(".", 1)[-1]
        return ""

    def _company_xp_total(self) -> float:
        return sum(xp_required_for_next_level(level) for level in range(1, self._state.company.level)) + self._state.company.current_xp

    def _push_contract_deliveries(self, previous: dict[str, _ContractSnapshot]) -> None:
        for contract in previous.values():
            if contract.status != "active":
                continue
            delivered_before = dict(contract.delivered)
            for resource_id, delivered_now in contract.active.delivered.items():
                amount = delivered_now - delivered_before.get(resource_id, 0.0)
                if amount <= 0:
                    continue
                resource = resource_id.replace("_", " ").title() or "Resource"
                self._feed.push(
                    FeedEvent(
                        "delivery",
                        f"{resource} Delivered to {contract.active.offer.name} Contract",
                        amount,
                        group_key=f"contract:{contract.contract_id}:{resource_id}",
                        resource_id=resource_id,
                    )
                )

    def _contract_snapshot(self) -> dict[str, _ContractSnapshot]:
        snapshot = {}
        for kind in CONTRACT_KINDS:
            active = self._state.contracts.active.get(kind)
            if active is not None:
                snapshot[kind] = _ContractSnapshot(
                    active.offer.contract_id,
                    active.status,
                    active.offer.reward_cash,
                    active.offer.reward_xp,
                    active,
                    tuple(sorted(active.delivered.items())),
                )
        return snapshot

    def _completed_market_deliveries(self, previous_count: int) -> tuple[MarketDeliveryResolution, ...]:
        return tuple(delivery for delivery in self._state.freight.completed_market_deliveries if delivery.delivery_id >= previous_count)

    def _market_delivery_watermark(self) -> int:
        freight = self._state.freight
        return max(freight.next_market_delivery_sequence,
                   freight.completed_market_deliveries[-1].delivery_id + 1 if freight.completed_market_deliveries else 0)

    def _pack_snapshot(self) -> dict[str, tuple[str, str]]:
        return {pack.pack_id: (pack.pack_type, pack.source) for pack in self._state.packs.unopened}
