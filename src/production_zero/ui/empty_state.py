from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from production_zero.ui.resource_icons import ResourceIconWidget


class EmptyStatePanel(QFrame):
    """Shared framed panel for true empty gallery or selector states."""

    def __init__(
        self,
        title: str,
        message: str,
        *,
        accent: str = "neutral",
        action: QPushButton | None = None,
        object_name: str = "emptyStatePanel",
        parent: QWidget | None = None,
        show_icon: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setProperty("emptyStatePanel", True)
        self.setProperty("accent", accent)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 26, 24, 26)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if show_icon:
            icon = ResourceIconWidget("storage", "package", accent, size=46)
            icon.setParent(self)
            icon.setObjectName("emptyStateIcon")
            layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)

        title_label = QLabel(title.upper(), self)
        title_label.setObjectName("emptyStateTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        message_label = QLabel(message, self)
        message_label.setObjectName("emptyStateMessage")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        if action is not None:
            action.setParent(self)
            action.setObjectName(action.objectName() or "emptyStateAction")
            layout.addWidget(action, 0, Qt.AlignmentFlag.AlignHCenter)
