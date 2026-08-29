from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from PySide6.QtCore import QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from production_zero.core.contracts import CONTRACT_KINDS
from production_zero.core.freight import MarketDeliveryResolution
from production_zero.core.state import GameState


AGGREGATION_SECONDS = 1.5
ENTRY_LIFETIME_SECONDS = 3.6


@dataclass(slots=True)
class FeedEvent:
    event_type: str
    label: str
    amount: float = 0.0
    count: int = 1


@dataclass(slots=True)
class _PendingEvent:
    event_type: str
    label: str
    amount: float
    count: int
    created_at: float
    updated_at: float


class EventFeedEntry(QFrame):
    def __init__(self, event: FeedEvent) -> None:
        super().__init__()
        self.setObjectName("eventFeedEntry")
        self.setProperty("eventType", event.event_type)
        self.created_at = monotonic()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(11, 7, 11, 7)
        layout.setSpacing(8)

        icon = QLabel(self._icon(event.event_type))
        icon.setObjectName("eventFeedIcon")
        amount = QLabel(self._amount_text(event))
        amount.setObjectName("eventFeedAmount")
        amount.setProperty("eventType", event.event_type)
        label = QLabel(self._label_text(event))
        label.setObjectName("eventFeedLabel")

        layout.addWidget(icon)
        layout.addWidget(amount)
        layout.addWidget(label, 1)

        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)
        self._fade = QPropertyAnimation(effect, b"opacity", self)
        self._fade.setDuration(240)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def fade_out(self) -> None:
        effect = self.graphicsEffect()
        if effect is None:
            self.deleteLater()
            return
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(260)
        animation.setStartValue(effect.opacity())
        animation.setEndValue(0.0)
        animation.finished.connect(self.deleteLater)
        self._fade = animation
        animation.start()

    def _amount_text(self, event: FeedEvent) -> str:
        if event.event_type == "cash":
            return f"+${event.amount:,.0f}"
        if event.event_type == "xp":
            return f"+{event.amount:,.0f} XP"
        if event.event_type == "pack":
            return f"x{event.count}" if event.count > 1 else "+1"
        return "DONE"

    def _label_text(self, event: FeedEvent) -> str:
        if event.count > 1 and event.event_type == "cash":
            return f"{event.count} {event.label}s"
        if event.count > 1 and event.event_type == "pack":
            return f"{event.label}s received"
        return event.label

    def _icon(self, event_type: str) -> str:
        return {
            "cash": "$",
            "xp": "XP",
            "pack": "PK",
            "contract": "OK",
        }.get(event_type, "!")


class EventFeedWidget(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("eventFeed")
        self._pending: dict[tuple[str, str], _PendingEvent] = {}
        self._entries: list[EventFeedEntry] = []
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self.hide()

    def push(self, event: FeedEvent) -> None:
        key = (event.event_type, event.label)
        now = monotonic()
        pending = self._pending.get(key)
        if pending is None:
            self._pending[key] = _PendingEvent(event.event_type, event.label, event.amount, event.count, now, now)
            return
        pending.amount += event.amount
        pending.count += event.count
        pending.updated_at = now

    def flush_pending(self) -> None:
        for key in list(self._pending):
            pending = self._pending.pop(key)
            self._add_entry(FeedEvent(pending.event_type, pending.label, pending.amount, pending.count))

    def entry_texts(self) -> tuple[str, ...]:
        return tuple(" ".join(label.text() for label in entry.findChildren(QLabel)) for entry in self._entries if entry.parent() is not None)

    def _tick(self) -> None:
        now = monotonic()
        for key, pending in list(self._pending.items()):
            if now - pending.updated_at >= AGGREGATION_SECONDS:
                self._pending.pop(key)
                self._add_entry(FeedEvent(pending.event_type, pending.label, pending.amount, pending.count))
        for entry in list(self._entries):
            if entry.parent() is None:
                self._entries.remove(entry)
            elif now - entry.created_at >= ENTRY_LIFETIME_SECONDS:
                self._entries.remove(entry)
                entry.fade_out()
        self.setVisible(bool(self._entries or self._pending))

    def _add_entry(self, event: FeedEvent) -> None:
        entry = EventFeedEntry(event)
        self._entries.insert(0, entry)
        self._layout.insertWidget(0, entry)
        while len(self._entries) > 5:
            old = self._entries.pop()
            old.fade_out()
        self.show()


class EventFeedController:
    def __init__(self, state: GameState, feed: EventFeedWidget, cash_highlight_callback=None) -> None:
        self._state = state
        self._feed = feed
        self._cash_highlight_callback = cash_highlight_callback
        self._cash = state.cash.amount
        self._xp_total = self._company_xp_total()
        self._pack_count = len(state.packs.unopened)
        self._contracts = self._contract_snapshot()
        self._market_delivery_count = len(state.freight.completed_market_deliveries)

    def observe(self) -> None:
        previous_cash = self._cash
        previous_xp = self._xp_total
        previous_pack_count = self._pack_count
        previous_contracts = self._contracts
        previous_market_delivery_count = self._market_delivery_count

        self._cash = self._state.cash.amount
        self._xp_total = self._company_xp_total()
        self._pack_count = len(self._state.packs.unopened)
        self._contracts = self._contract_snapshot()
        self._market_delivery_count = len(self._state.freight.completed_market_deliveries)

        completed_shipments = self._completed_market_deliveries(previous_market_delivery_count)
        shipment_cash = 0.0
        for delivery in completed_shipments:
            amount = delivery.market_earnings
            shipment_cash += amount
            resource = delivery.resource_id.replace("_", " ").title() or "Resource"
            if delivery.contract_amount > 0:
                self._feed.push(FeedEvent("contract", f"{delivery.contract_amount:g} {resource} to Contract"))
            if delivery.market_amount > 0 and amount > 0:
                self._feed.push(FeedEvent("cash", f"{resource} Shipment", amount))

        contract_cash = 0.0
        contract_xp = 0.0
        for kind, contract in previous_contracts.items():
            if contract[1] != "active":
                continue
            current = self._contracts.get(kind)
            completed = current is None or current[1] == "completed"
            if not completed:
                continue
            contract_cash += contract[2]
            contract_xp += contract[3]
            self._feed.push(FeedEvent("contract", "Contract completed"))
            if contract[2] > 0:
                self._feed.push(FeedEvent("cash", "Contract Reward", contract[2]))
            if contract[3] > 0:
                self._feed.push(FeedEvent("xp", f"{kind.title()} Contract", contract[3]))

        cash_delta = self._cash - previous_cash
        known_cash = shipment_cash + contract_cash
        if cash_delta > 0.01 and self._cash_highlight_callback is not None:
            self._cash_highlight_callback(previous_cash, self._state.cash.amount)
        if cash_delta > known_cash + 0.01:
            self._feed.push(FeedEvent("cash", "Income", cash_delta - known_cash))

        xp_delta = self._xp_total - previous_xp
        if xp_delta > contract_xp + 0.01:
            self._feed.push(FeedEvent("xp", "Company Progress", xp_delta - contract_xp))

        pack_delta = self._pack_count - previous_pack_count
        if pack_delta > 0:
            self._feed.push(FeedEvent("pack", "Pack", count=pack_delta))

    def _company_xp_total(self) -> float:
        return self._state.company.level * 1_000_000_000 + self._state.company.current_xp

    def _contract_snapshot(self) -> dict[str, tuple[str, str, float, float]]:
        snapshot = {}
        for kind in CONTRACT_KINDS:
            active = self._state.contracts.active.get(kind)
            if active is not None:
                snapshot[kind] = (active.offer.contract_id, active.status, active.offer.reward_cash, active.offer.reward_xp)
        return snapshot

    def _completed_market_deliveries(self, previous_count: int) -> tuple[MarketDeliveryResolution, ...]:
        return tuple(self._state.freight.completed_market_deliveries[previous_count:])
