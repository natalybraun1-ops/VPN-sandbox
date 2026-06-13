from __future__ import annotations

from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QRadioButton,
    QVBoxLayout,
)

from vpn_sandbox.core.models import OperatingMode


class FirstRunDialog(QDialog):
    _MODE_LABELS: dict[OperatingMode, str] = {
        OperatingMode.DUAL_ZONE: (
            "Две зоны: VPN-приложения и прямые приложения одновременно"
        ),
        OperatingMode.VPN_ONLY: (
            "VPN-only: весь выбранный трафик должен идти через VPN"
        ),
        OperatingMode.DIRECT_ONLY: (
            "Прямой режим: выбранный трафик должен обходить VPN"
        ),
    }

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Песочница VPN")
        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        self._mode_buttons: dict[OperatingMode, QRadioButton] = {}
        self._mode_by_button_id: dict[int, OperatingMode] = {}

        form = QFormLayout()
        for button_id, (mode, label) in enumerate(self._MODE_LABELS.items()):
            button = QRadioButton(label)
            self._mode_group.addButton(button, button_id)
            self._mode_buttons[mode] = button
            self._mode_by_button_id[button_id] = mode
            form.addRow(button)
        self._mode_buttons[OperatingMode.DUAL_ZONE].setChecked(True)

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

    def button_for_mode(self, mode: OperatingMode) -> QRadioButton:
        return self._mode_buttons[mode]

    def selected_mode(self) -> OperatingMode:
        return self._mode_by_button_id[self._mode_group.checkedId()]
