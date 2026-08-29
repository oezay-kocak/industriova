from __future__ import annotations

from PySide6.QtCore import QRect, QSize


def clamp_window_size_to_available(desired: QSize, available: QRect, margin: int = 24) -> QSize:
    usable_width = max(320, available.width() - margin)
    usable_height = max(240, available.height() - margin)
    return QSize(min(desired.width(), usable_width), min(desired.height(), usable_height))


def clamp_window_geometry_to_available(rect: QRect, available: QRect, margin: int = 12) -> QRect:
    size = clamp_window_size_to_available(rect.size(), available, margin * 2)
    max_x = available.right() - size.width() + 1 - margin
    max_y = available.bottom() - size.height() + 1 - margin
    x = min(max(rect.x(), available.x() + margin), max_x)
    y = min(max(rect.y(), available.y() + margin), max_y)
    return QRect(x, y, size.width(), size.height())
