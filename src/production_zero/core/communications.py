from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CompanyMessage:
    message_id: str
    event_type: str
    title: str
    item_ids: tuple[str, ...]
    created_order: int
    read: bool = False


@dataclass(slots=True)
class CompanyCommunications:
    messages: list[CompanyMessage] = field(default_factory=list)
    next_order: int = 1
    pending_activity: list[tuple[str, str]] = field(default_factory=list)

    def add_activity(self, event_type: str, label: str) -> None:
        """Transient events drained by the existing company Activity controller."""
        self.pending_activity.append((event_type, label))
        self.pending_activity[:] = self.pending_activity[-40:]

    @property
    def unread_count(self) -> int:
        return sum(not message.read for message in self.messages)

    def add_unlocks(self, production_ids: list[str]) -> CompanyMessage | None:
        unique_ids = tuple(dict.fromkeys(production_ids))
        if not unique_ids:
            return None
        message = CompanyMessage(
            message_id=f"unlock-{self.next_order}",
            event_type="production_unlock",
            title="NEW PRODUCTION UNLOCKS",
            item_ids=unique_ids,
            created_order=self.next_order,
        )
        self.next_order += 1
        self.messages.append(message)
        self.messages[:] = self.messages[-100:]
        return message

    def mark_read(self, message_id: str) -> None:
        for message in self.messages:
            if message.message_id == message_id:
                message.read = True
                return
