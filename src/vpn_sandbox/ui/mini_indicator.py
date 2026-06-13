from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from vpn_sandbox.core.models import ZoneStatus


class MiniIndicator(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Песочница VPN")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self._label = QLabel("Статус зон")

        layout = QVBoxLayout()
        layout.addWidget(self._label)
        self.setLayout(layout)

        self.resize(220, 80)

    def update_status(self, status: ZoneStatus, text: str) -> None:
        self._label.setText(f"{text} · {status.value}")

    def status_text(self) -> str:
        return self._label.text()
