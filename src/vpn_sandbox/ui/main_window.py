from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from vpn_sandbox.app.controller import AppController
from vpn_sandbox.core.models import ZoneKind
from vpn_sandbox.core.policy import NetworkSnapshot
from vpn_sandbox.ui.text import zone_label
from vpn_sandbox.ui.view_models import build_zone_card
from vpn_sandbox.ui.widgets import StatusBadge, set_table_rows


_ZONE_ORDER = (ZoneKind.VPN, ZoneKind.DIRECT)


class MainWindow(QMainWindow):
    def __init__(self, controller: AppController) -> None:
        super().__init__()
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

    def add_manual_app_for_test(
        self,
        zone,
        exe_path: str,
        display_name: str,
    ) -> None:
        self.controller.add_manual_app(
            zone=zone,
            exe_path=exe_path,
            display_name=display_name,
        )
        self.refresh()

    def save_vpn_profile_for_test(
        self,
        country_code: str,
        country_name: str,
        city: str | None,
        external_ip: str,
        protocol: str | None,
        client_name: str | None,
        custom_name: str | None,
        make_active: bool = True,
    ) -> None:
        from vpn_sandbox.core.models import Confidence

        self.controller.save_vpn_profile(
            country_code=country_code,
            country_name=country_name,
            city=city,
            external_ip=external_ip,
            protocol=protocol,
            client_name=client_name,
            confidence=Confidence.CERTAIN,
            custom_name=custom_name,
            make_active=make_active,
        )
        self.refresh()

    def save_direct_profile_for_test(
        self,
        interface_name: str,
        gateway: str | None,
        dns_servers: tuple[str, ...],
        custom_name: str | None,
        make_active: bool = True,
    ) -> None:
        self.controller.save_direct_profile(
            interface_name=interface_name,
            gateway=gateway,
            dns_servers=dns_servers,
            custom_name=custom_name,
            make_active=make_active,
        )
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
        add_vpn_button = QPushButton("Добавить VPN-профиль")
        add_vpn_button.clicked.connect(self._show_add_vpn_profile_dialog)
        layout.addWidget(add_vpn_button)
        add_direct_button = QPushButton("Добавить прямой профиль")
        add_direct_button.clicked.connect(self._show_add_direct_profile_dialog)
        layout.addWidget(add_direct_button)
        layout.addStretch()
        return tab

    def _apps_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self._apps_table.setHorizontalHeaderLabels(["Зона", "Приложение", "Путь"])
        layout.addWidget(self._apps_table)
        add_button = QPushButton("Добавить вручную")
        add_button.clicked.connect(self._show_add_app_dialog)
        layout.addWidget(add_button)
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

    def _show_add_app_dialog(self) -> None:
        file_name, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Выберите приложение",
            "",
            "Windows applications (*.exe)",
        )
        if not file_name:
            return

        zone_name, ok = QInputDialog.getItem(
            self,
            "Зона",
            "Куда добавить приложение",
            ["VPN-зона", "Прямая зона"],
            0,
            False,
        )
        if not ok:
            return

        zone = ZoneKind.VPN if zone_name == "VPN-зона" else ZoneKind.DIRECT
        try:
            self.add_manual_app_for_test(
                zone=zone,
                exe_path=file_name,
                display_name=Path(file_name).stem,
            )
        except ValueError:
            QMessageBox.warning(
                self,
                "Приложение уже добавлено",
                "Это приложение уже добавлено в одну из зон. Удалите его из текущей зоны, чтобы добавить в другую.",
            )

    def _show_add_vpn_profile_dialog(self) -> None:
        country_code, ok = QInputDialog.getText(
            self,
            "Добавить VPN-профиль",
            "Код страны",
        )
        if not ok or not country_code.strip():
            return
        country_code = country_code.strip()

        country_name, ok = QInputDialog.getText(
            self,
            "Добавить VPN-профиль",
            "Название страны",
        )
        if not ok or not country_name.strip():
            return
        country_name = country_name.strip()

        external_ip, ok = QInputDialog.getText(
            self,
            "Добавить VPN-профиль",
            "Внешний IP",
        )
        if not ok or not external_ip.strip():
            return
        external_ip = external_ip.strip()

        city, ok = QInputDialog.getText(
            self,
            "Добавить VPN-профиль",
            "Город (необязательно)",
        )
        if not ok:
            return
        protocol, ok = QInputDialog.getText(
            self,
            "Добавить VPN-профиль",
            "Протокол (необязательно)",
        )
        if not ok:
            return
        client_name, ok = QInputDialog.getText(
            self,
            "Добавить VPN-профиль",
            "Клиент (необязательно)",
        )
        if not ok:
            return
        custom_name, ok = QInputDialog.getText(
            self,
            "Добавить VPN-профиль",
            "Имя профиля (необязательно)",
        )
        if not ok:
            return

        self.save_vpn_profile_for_test(
            country_code=country_code,
            country_name=country_name,
            city=city.strip() or None,
            external_ip=external_ip,
            protocol=protocol.strip() or None,
            client_name=client_name.strip() or None,
            custom_name=custom_name.strip() or None,
        )

    def _show_add_direct_profile_dialog(self) -> None:
        interface_name, ok = QInputDialog.getText(
            self,
            "Добавить прямой профиль",
            "Имя интерфейса",
        )
        if not ok or not interface_name.strip():
            return
        interface_name = interface_name.strip()

        gateway, ok = QInputDialog.getText(
            self,
            "Добавить прямой профиль",
            "Шлюз (необязательно)",
        )
        if not ok:
            return
        dns_servers, ok = QInputDialog.getText(
            self,
            "Добавить прямой профиль",
            "DNS-серверы через запятую",
        )
        if not ok:
            return
        custom_name, ok = QInputDialog.getText(
            self,
            "Добавить прямой профиль",
            "Имя профиля (необязательно)",
        )
        if not ok:
            return

        self.save_direct_profile_for_test(
            interface_name=interface_name,
            gateway=gateway.strip() or None,
            dns_servers=tuple(
                server.strip()
                for server in dns_servers.split(",")
                if server.strip()
            ),
            custom_name=custom_name.strip() or None,
        )

    def refresh(self) -> None:
        snapshot = NetworkSnapshot(
            control_available=True,
            vpn_detected=False,
            country_code=None,
            direct_route_confirmed=False,
            geo_ip_available=True,
        )
        dashboard = self.controller.load_dashboard(snapshot)

        for label, zone_kind in zip(self._dashboard_labels, _ZONE_ORDER):
            zone = dashboard.zones.get(zone_kind)
            if zone is None:
                label.setText(f"{zone_label(zone_kind)}: нет данных")
                continue

            card = build_zone_card(zone)
            label.setText(
                f"{card.title}: {card.status}\n"
                f"{card.profile}\n"
                f"{card.app_count} · {card.reason}"
            )

        app_rows = []
        for zone_kind in _ZONE_ORDER:
            zone = dashboard.zones.get(zone_kind)
            if zone is None:
                continue
            for app in zone.apps:
                app_rows.append([app.zone.value, app.display_name, app.exe_path])
        set_table_rows(self._apps_table, app_rows)

        event_rows = [
            [event.timestamp, event.level, event.zone or "", event.reason]
            for event in dashboard.events
        ]
        set_table_rows(self._journal_table, event_rows)
