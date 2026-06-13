from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QRadioButton,
    QVBoxLayout,
)

from vpn_sandbox.core.models import OperatingMode


class FirstRunDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Первый запуск")
        self._vpn_only = QRadioButton("Только VPN-контроль")
        self._direct_only = QRadioButton("Только прямой обход VPN")
        self._dual_zone = QRadioButton("Две зоны")
        self._dual_zone.setChecked(True)

        form = QFormLayout()
        form.addRow(self._dual_zone)
        form.addRow(self._vpn_only)
        form.addRow(self._direct_only)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def selected_mode(self) -> OperatingMode:
        if self._vpn_only.isChecked():
            return OperatingMode.VPN_ONLY
        if self._direct_only.isChecked():
            return OperatingMode.DIRECT_ONLY
        return OperatingMode.DUAL_ZONE
