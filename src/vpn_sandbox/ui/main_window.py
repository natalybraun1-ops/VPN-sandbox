from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from vpn_sandbox.app.controller import AppController
from vpn_sandbox.core.policy import NetworkSnapshot
from vpn_sandbox.ui.app import create_qapplication
from vpn_sandbox.ui.view_models import build_zone_card
from vpn_sandbox.ui.widgets import StatusBadge, set_table_rows


class MainWindow(QMainWindow):
    def __init__(self, controller: AppController) -> None:
        app = create_qapplication([])
        super().__init__()
        self._app = app
        self.controller = controller
        self.setWindowTitle("Песочница VPN")
        self.resize(980, 640)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._dashboard_labels: list[QLabel] = []
        self._apps_table = QTableWidget(0, 3)
        self._journal_table = QTableWidget(0, 4)

        self.tabs.addTab(self._overview_tab(), "Обзор")
        self.tabs.addTab(self._zones_tab(), "Зоны")
        self.tabs.addTab(self._profiles_tab(), "Профили")
        self.tabs.addTab(self._apps_tab(), "Приложения")
        self.tabs.addTab(self._journal_tab(), "Журнал")
        self.tabs.addTab(self._diagnostics_tab(), "Диагностика")

        self.refresh()

    def _overview_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        for _index in range(2):
            label = QLabel()
            label.setMinimumHeight(64)
            self._dashboard_labels.append(label)
            layout.addWidget(label)

        refresh_button = QPushButton("Обновить")
        refresh_button.clicked.connect(self.refresh)
        layout.addWidget(refresh_button)
        layout.addStretch()
        return tab

    def _zones_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(StatusBadge("Настройки зон"))
        layout.addWidget(QLabel("Реакции на нарушения и включение зон"))
        layout.addStretch()
        return tab

    def _profiles_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("VPN-профили и прямые профили"))
        layout.addStretch()
        return tab

    def _apps_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self._apps_table.setHorizontalHeaderLabels(["Зона", "Приложение", "Путь"])
        layout.addWidget(self._apps_table)
        return tab

    def _journal_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self._journal_table.setHorizontalHeaderLabels(
            ["Время", "Уровень", "Зона", "Причина"]
        )
        layout.addWidget(self._journal_table)
        return tab

    def _diagnostics_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.addWidget(QLabel("Локальный режим: активен"))
        layout.addWidget(QLabel("Сетевой контроль: не подключен"))
        layout.addWidget(QLabel("Служба Windows: не подключена"))
        return tab

    def refresh(self) -> None:
        snapshot = NetworkSnapshot(
            control_available=True,
            vpn_detected=False,
            country_code=None,
            direct_route_confirmed=False,
            geo_ip_available=True,
        )
        dashboard = self.controller.load_dashboard(snapshot)

        for label, zone in zip(self._dashboard_labels, dashboard.zones.values()):
            card = build_zone_card(zone)
            label.setText(
                f"{card.title}: {card.status}\n"
                f"{card.profile}\n"
                f"{card.app_count} · {card.reason}"
            )

        app_rows = [
            [app.zone.value, app.display_name, app.exe_path]
            for zone in dashboard.zones.values()
            for app in zone.apps
        ]
        set_table_rows(self._apps_table, app_rows)

        event_rows = [
            [event.timestamp, event.level, event.zone or "", event.reason]
            for event in dashboard.events
        ]
        set_table_rows(self._journal_table, event_rows)
