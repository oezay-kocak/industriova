from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


_GROUPED_SUFFIXES = (
    "CLASS I",
    "CLASS II",
    "CLASS III",
    "MK I",
    "MK II",
    "MK III",
    "MK IV",
    "MK V",
)


def smart_card_title(text: str) -> str:
    normalized = " ".join(text.replace("\n", " ").split())
    upper = normalized.upper()
    if " · " in normalized:
        left, right = normalized.split(" · ", 1)
        if any(right.upper().startswith(suffix) for suffix in _GROUPED_SUFFIXES):
            return f"{left}\n{right}"
    for suffix in _GROUPED_SUFFIXES:
        marker = f" {suffix}"
        if upper.endswith(marker):
            return f"{normalized[:-len(marker)]}\n{normalized[-len(suffix):]}"
    match = re.search(r"\b([IVX]+)$", normalized)
    if match is not None and match.start() > 0:
        before = normalized[: match.start()].rstrip()
        grouped = before.rsplit(" ", 1)
        if len(grouped) == 2 and grouped[1].upper() in {"MK", "CLASS"}:
            return f"{grouped[0]}\n{grouped[1]} {match.group(1)}"
    return normalized


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
