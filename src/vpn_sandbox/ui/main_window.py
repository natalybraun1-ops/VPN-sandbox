from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
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
from vpn_sandbox.core.models import ViolationAction, ZoneKind, ZoneSettings
from vpn_sandbox.core.policy import NetworkSnapshot
from vpn_sandbox.ui.text import violation_action_label, zone_label
from vpn_sandbox.ui.view_models import build_zone_card
from vpn_sandbox.ui.widgets import StatusBadge, set_table_rows


_ZONE_ORDER = (ZoneKind.VPN, ZoneKind.DIRECT)
_DUPLICATE_MANAGED_APP_MESSAGE = "application is already managed"


class MainWindow(QMainWindow):
    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Песочница VPN")
        self.resize(980, 640)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._dashboard_labels: list[QLabel] = []
        self._zone_enabled_checkboxes: dict[ZoneKind, QCheckBox] = {}
        self._zone_violation_actions: dict[ZoneKind, QComboBox] = {}
        self._zone_warn_acknowledged_checkboxes: dict[ZoneKind, QCheckBox] = {}
        self._vpn_profiles_table = QTableWidget(0, 3)
        self._direct_profiles_table = QTableWidget(0, 3)
        self._apps_table = QTableWidget(0, 3)
        self._journal_table = QTableWidget(0, 4)
        self._app_row_ids: list[str] = []
        self._vpn_profile_row_ids: list[str] = []
        self._direct_profile_row_ids: list[str] = []

        self.tabs.addTab(self._overview_tab(), "Обзор")
        self.tabs.addTab(self._zones_tab(), "Зоны")
        self.tabs.addTab(self._profiles_tab(), "Профили")
        self.tabs.addTab(self._apps_tab(), "Приложения")
        self.tabs.addTab(self._journal_tab(), "Журнал")
        self.tabs.addTab(self._diagnostics_tab(), "Диагностика")

        self.refresh()

    def add_manual_app_for_test(
        self,
        zone: ZoneKind,
        exe_path: str,
        display_name: str,
    ) -> None:
        self.controller.add_manual_app(
            zone=zone,
            exe_path=exe_path,
            display_name=display_name,
        )
        self.refresh()

    def remove_managed_app_for_test(self, app_id: str) -> None:
        self.controller.remove_managed_app(app_id)
        self.refresh()

    def save_zone_settings_for_test(
        self,
        zone: ZoneKind,
        enabled: bool,
        violation_action: ViolationAction,
        warn_only_acknowledged: bool,
        active_profile_id: str | None = None,
    ) -> None:
        self.controller.save_zone_settings(
            ZoneSettings(
                zone=zone,
                enabled=enabled,
                violation_action=violation_action,
                warn_only_acknowledged=warn_only_acknowledged,
                active_profile_id=active_profile_id,
            )
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

    def delete_vpn_profile_for_test(self, profile_id: str) -> None:
        self.controller.delete_vpn_profile(profile_id)
        self.refresh()

    def activate_vpn_profile_for_test(self, profile_id: str) -> None:
        self.controller.activate_vpn_profile(profile_id)
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

    def delete_direct_profile_for_test(self, profile_id: str) -> None:
        self.controller.delete_direct_profile(profile_id)
        self.refresh()

    def activate_direct_profile_for_test(self, profile_id: str) -> None:
        self.controller.activate_direct_profile(profile_id)
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
        for zone in _ZONE_ORDER:
            row = QHBoxLayout()
            row.addWidget(QLabel(zone_label(zone)))

            enabled = QCheckBox("Включена")
            self._zone_enabled_checkboxes[zone] = enabled
            row.addWidget(enabled)

            action = QComboBox()
            for violation_action in ViolationAction:
                action.addItem(violation_action_label(violation_action), violation_action)
            self._zone_violation_actions[zone] = action
            row.addWidget(action)

            warn_acknowledged = QCheckBox("Warn-only подтвержден")
            self._zone_warn_acknowledged_checkboxes[zone] = warn_acknowledged
            row.addWidget(warn_acknowledged)

            save_button = QPushButton("Сохранить")
            save_button.clicked.connect(
                lambda _checked=False, selected_zone=zone: (
                    self._save_zone_settings_from_controls(selected_zone)
                )
            )
            row.addWidget(save_button)
            layout.addLayout(row)
        layout.addStretch()
        return tab

    def _profiles_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self._vpn_profiles_table.setHorizontalHeaderLabels(
            ["Профиль", "IP", "Активен"]
        )
        layout.addWidget(self._vpn_profiles_table)
        layout.addWidget(QLabel("VPN-профили и прямые профили"))
        add_vpn_button = QPushButton("Добавить VPN-профиль")
        add_vpn_button.clicked.connect(self._show_add_vpn_profile_dialog)
        layout.addWidget(add_vpn_button)
        vpn_actions = QHBoxLayout()
        activate_vpn_button = QPushButton("Сделать активным")
        activate_vpn_button.clicked.connect(self._activate_selected_vpn_profile)
        vpn_actions.addWidget(activate_vpn_button)
        delete_vpn_button = QPushButton("Удалить VPN-профиль")
        delete_vpn_button.clicked.connect(self._delete_selected_vpn_profile)
        vpn_actions.addWidget(delete_vpn_button)
        layout.addLayout(vpn_actions)
        self._direct_profiles_table.setHorizontalHeaderLabels(
            ["Профиль", "Интерфейс", "Активен"]
        )
        layout.addWidget(self._direct_profiles_table)
        add_direct_button = QPushButton("Добавить прямой профиль")
        add_direct_button.clicked.connect(self._show_add_direct_profile_dialog)
        layout.addWidget(add_direct_button)
        direct_actions = QHBoxLayout()
        activate_direct_button = QPushButton("Сделать активным")
        activate_direct_button.clicked.connect(self._activate_selected_direct_profile)
        direct_actions.addWidget(activate_direct_button)
        delete_direct_button = QPushButton("Удалить прямой профиль")
        delete_direct_button.clicked.connect(self._delete_selected_direct_profile)
        direct_actions.addWidget(delete_direct_button)
        layout.addLayout(direct_actions)
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
        remove_button = QPushButton("Удалить выбранное")
        remove_button.clicked.connect(self._remove_selected_managed_app)
        layout.addWidget(remove_button)
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
        except ValueError as exc:
            if str(exc) != _DUPLICATE_MANAGED_APP_MESSAGE:
                raise
            QMessageBox.warning(
                self,
                "Приложение уже добавлено",
                "Это приложение уже добавлено в одну из зон. Удалите его из текущей зоны, чтобы добавить в другую.",
            )

    def _selected_row_id(self, table: QTableWidget, row_ids: list[str]) -> str | None:
        row = table.currentRow()
        if row < 0 or row >= len(row_ids):
            return None
        return row_ids[row]

    def _remove_selected_managed_app(self) -> None:
        app_id = self._selected_row_id(self._apps_table, self._app_row_ids)
        if app_id is None:
            return
        self.remove_managed_app_for_test(app_id)

    def _activate_selected_vpn_profile(self) -> None:
        profile_id = self._selected_row_id(
            self._vpn_profiles_table,
            self._vpn_profile_row_ids,
        )
        if profile_id is None:
            return
        self.activate_vpn_profile_for_test(profile_id)

    def _delete_selected_vpn_profile(self) -> None:
        profile_id = self._selected_row_id(
            self._vpn_profiles_table,
            self._vpn_profile_row_ids,
        )
        if profile_id is None:
            return
        self.delete_vpn_profile_for_test(profile_id)

    def _activate_selected_direct_profile(self) -> None:
        profile_id = self._selected_row_id(
            self._direct_profiles_table,
            self._direct_profile_row_ids,
        )
        if profile_id is None:
            return
        self.activate_direct_profile_for_test(profile_id)

    def _delete_selected_direct_profile(self) -> None:
        profile_id = self._selected_row_id(
            self._direct_profiles_table,
            self._direct_profile_row_ids,
        )
        if profile_id is None:
            return
        self.delete_direct_profile_for_test(profile_id)

    def _save_zone_settings_from_controls(self, zone: ZoneKind) -> None:
        action = self._zone_violation_actions[zone].currentData()
        if not isinstance(action, ViolationAction):
            action = ViolationAction.CLOSE_AFTER_20
        existing = self.controller.get_zone_settings(zone)
        self.save_zone_settings_for_test(
            zone=zone,
            enabled=self._zone_enabled_checkboxes[zone].isChecked(),
            violation_action=action,
            warn_only_acknowledged=(
                self._zone_warn_acknowledged_checkboxes[zone].isChecked()
            ),
            active_profile_id=existing.active_profile_id if existing else None,
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
        self._refresh_zone_controls()
        self._refresh_profile_tables()

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
        self._app_row_ids = []
        for zone_kind in _ZONE_ORDER:
            zone = dashboard.zones.get(zone_kind)
            if zone is None:
                continue
            for app in zone.apps:
                app_rows.append([app.zone.value, app.display_name, app.exe_path])
                self._app_row_ids.append(app.id)
        set_table_rows(self._apps_table, app_rows)

        event_rows = [
            [event.timestamp, event.level, event.zone or "", event.reason]
            for event in dashboard.events
        ]
        set_table_rows(self._journal_table, event_rows)

    def _refresh_zone_controls(self) -> None:
        get_zone_settings = getattr(self.controller, "get_zone_settings", None)
        if get_zone_settings is None:
            return
        for zone in _ZONE_ORDER:
            settings = get_zone_settings(zone)
            if settings is None:
                continue
            self._zone_enabled_checkboxes[zone].setChecked(settings.enabled)
            action_index = self._zone_violation_actions[zone].findData(
                settings.violation_action
            )
            if action_index >= 0:
                self._zone_violation_actions[zone].setCurrentIndex(action_index)
            self._zone_warn_acknowledged_checkboxes[zone].setChecked(
                settings.warn_only_acknowledged
            )

    def _refresh_profile_tables(self) -> None:
        self._vpn_profile_row_ids = []
        self._direct_profile_row_ids = []
        list_vpn_profiles = getattr(self.controller, "list_vpn_profiles", None)
        list_direct_profiles = getattr(self.controller, "list_direct_profiles", None)
        get_zone_settings = getattr(self.controller, "get_zone_settings", None)
        if list_vpn_profiles is None or list_direct_profiles is None:
            set_table_rows(self._vpn_profiles_table, [])
            set_table_rows(self._direct_profiles_table, [])
            return

        vpn_settings = (
            get_zone_settings(ZoneKind.VPN) if get_zone_settings is not None else None
        )
        vpn_rows = []
        for profile in list_vpn_profiles():
            self._vpn_profile_row_ids.append(profile.id)
            is_active = vpn_settings and vpn_settings.active_profile_id == profile.id
            vpn_rows.append(
                [
                    profile.effective_name,
                    profile.external_ip,
                    "yes" if is_active else "",
                ]
            )
        set_table_rows(self._vpn_profiles_table, vpn_rows)

        direct_settings = (
            get_zone_settings(ZoneKind.DIRECT) if get_zone_settings is not None else None
        )
        direct_rows = []
        for profile in list_direct_profiles():
            self._direct_profile_row_ids.append(profile.id)
            is_active = (
                direct_settings and direct_settings.active_profile_id == profile.id
            )
            direct_rows.append(
                [
                    profile.effective_name,
                    profile.interface_name,
                    "yes" if is_active else "",
                ]
            )
        set_table_rows(self._direct_profiles_table, direct_rows)
