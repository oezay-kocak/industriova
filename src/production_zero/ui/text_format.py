from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel



def smart_card_title(text: str) -> str:
    return " ".join(text.replace("\n", " ").split())


def count_label(count: int, singular: str, plural: str | None = None) -> str:
    """Format a counted UI noun without leaking mechanical ``s`` suffixes."""
    return f"{count} {singular if count == 1 else (plural or singular + 's')}"



class SmartCardTitleLabel(QLabel):
    def __init__(self, text: str = "", *, uppercase_display: bool = False) -> None:
        super().__init__(text)
        self._uppercase_display = uppercase_display
        self.setWordWrap(False)

    def paintEvent(self, event) -> None:  # noqa: N802
        formatted = smart_card_title(self.text())
        if not self._uppercase_display and "\n" not in formatted:
            super().paintEvent(event)
            return
        from PySide6.QtGui import QPainter

        painter = QPainter(self)
        try:
            painter.setFont(self.font())
            painter.setPen(self.palette().color(self.foregroundRole()))
            lines = formatted.splitlines()
            if self._uppercase_display:
                lines = [line.upper() for line in lines]
            line_height = self.height() / max(1, len(lines))
            alignment = self.alignment() or (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            for index, line in enumerate(lines[:2]):
                rect = self.rect()
                rect.setTop(round(index * line_height))
                rect.setHeight(round(line_height))
                painter.drawText(rect, alignment, line)
        finally:
            painter.end()
