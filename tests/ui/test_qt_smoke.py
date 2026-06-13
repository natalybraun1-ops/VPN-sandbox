import os
from pathlib import Path

import pytest

pytest.importorskip("PyQt6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _ensure_qapplication():
    from vpn_sandbox.ui.app import create_qapplication

    return create_qapplication([])


def _create_first_run_dialog():
    from vpn_sandbox.ui.first_run import FirstRunDialog

    app = _ensure_qapplication()
    return app, FirstRunDialog()


def _table_text(table, row: int, column: int) -> str:
    item = table.item(row, column)
    return "" if item is None else item.text()


def _patch_input_text_sequence(monkeypatch, answers):
    from PyQt6.QtWidgets import QInputDialog

    values = iter(answers)

    def get_text(*_args):
        return next(values)

    monkeypatch.setattr(QInputDialog, "getText", get_text)


def test_create_qapplication_returns_single_instance():
    from PyQt6.QtWidgets import QApplication
    from vpn_sandbox.ui.app import create_qapplication

    app = create_qapplication([])

    assert app is QApplication.instance()
    assert app.applicationName() == "Песочница VPN"


def test_create_qapplication_updates_existing_instance_metadata():
    from PyQt6.QtWidgets import QApplication
    from vpn_sandbox.ui.app import create_qapplication

    existing = QApplication.instance() or QApplication([])
    existing.setApplicationName("python")
    existing.setOrganizationName("Other")

    app = create_qapplication([])

    assert app is existing
    assert app.applicationName() == "Песочница VPN"
    assert app.organizationName() == "VPN Sandbox"


def test_first_run_dialog_defaults_to_dual_zone_mode():
    from vpn_sandbox.core.models import OperatingMode

    _app, dialog = _create_first_run_dialog()

    assert dialog.windowTitle() == "Песочница VPN"
    assert dialog.selected_mode() == OperatingMode.DUAL_ZONE


def test_first_run_dialog_has_required_mode_labels():
    from vpn_sandbox.core.models import OperatingMode

    _app, dialog = _create_first_run_dialog()

    assert {
        mode: dialog.button_for_mode(mode).text()
        for mode in OperatingMode
    } == {
        OperatingMode.VPN_ONLY: (
            "VPN-only: весь выбранный трафик должен идти через VPN"
        ),
        OperatingMode.DIRECT_ONLY: (
            "Прямой режим: выбранный трафик должен обходить VPN"
        ),
        OperatingMode.DUAL_ZONE: (
            "Две зоны: VPN-приложения и прямые приложения одновременно"
        ),
    }


def test_first_run_dialog_returns_selected_mode_from_button_group():
    from PyQt6.QtWidgets import QButtonGroup
    from vpn_sandbox.core.models import OperatingMode

    _app, dialog = _create_first_run_dialog()

    assert dialog.findChild(QButtonGroup) is not None
    for mode in (
        OperatingMode.VPN_ONLY,
        OperatingMode.DIRECT_ONLY,
        OperatingMode.DUAL_ZONE,
    ):
        dialog.button_for_mode(mode).setChecked(True)

        assert dialog.selected_mode() == mode


def test_main_window_contains_expected_tabs(tmp_path: Path):
    from vpn_sandbox.app.bootstrap import open_app_context
    from vpn_sandbox.core.models import OperatingMode
    from vpn_sandbox.ui.main_window import MainWindow

    _app = _ensure_qapplication()
    context = open_app_context(tmp_path)
    context.controller.configure_mode(OperatingMode.DUAL_ZONE)

    window = MainWindow(context.controller)

    assert window.windowTitle() == "Песочница VPN"
    assert [window.tabs.tabText(index) for index in range(window.tabs.count())] == [
        "Обзор",
        "Зоны",
        "Профили",
        "Приложения",
        "Журнал",
        "Диагностика",
    ]
    context.close()


def test_set_table_rows_clears_stale_cells_and_keeps_headers():
    from PyQt6.QtWidgets import QTableWidget
    from vpn_sandbox.ui.widgets import set_table_rows

    _app = _ensure_qapplication()
    table = QTableWidget(0, 3)
    table.setHorizontalHeaderLabels(["A", "B", "C"])

    set_table_rows(table, [["new", "old", "stale"]])
    set_table_rows(table, [["new"]])

    assert table.rowCount() == 1
    assert table.columnCount() == 3
    assert [table.horizontalHeaderItem(index).text() for index in range(3)] == [
        "A",
        "B",
        "C",
    ]
    assert [_table_text(table, 0, index) for index in range(3)] == ["new", "", ""]

    set_table_rows(table, [])

    assert table.rowCount() == 0
    assert table.columnCount() == 3


def test_set_table_rows_normalizes_values_and_ignores_extra_cells():
    from PyQt6.QtWidgets import QTableWidget
    from vpn_sandbox.ui.widgets import set_table_rows

    _app = _ensure_qapplication()
    table = QTableWidget(0, 2)

    set_table_rows(table, [[None, 42, "ignored"]])

    assert table.rowCount() == 1
    assert table.columnCount() == 2
    assert [_table_text(table, 0, index) for index in range(2)] == ["", "42"]


def test_main_window_refresh_populates_dashboard_apps_and_journal(tmp_path: Path):
    from vpn_sandbox.app.bootstrap import open_app_context
    from vpn_sandbox.core.models import OperatingMode, ZoneKind
    from vpn_sandbox.events.journal import EventRecord
    from vpn_sandbox.ui.main_window import MainWindow

    _app = _ensure_qapplication()
    context = open_app_context(tmp_path)
    try:
        context.controller.configure_mode(OperatingMode.DUAL_ZONE)
        context.controller.add_manual_app(
            ZoneKind.DIRECT,
            r"C:\Tools\browser.exe",
            "Browser",
        )
        context.journal.append(
            EventRecord(
                timestamp="2026-06-13T12:00:00",
                level="warning",
                zone=ZoneKind.DIRECT.value,
                app="Browser",
                reason="Direct route not guaranteed",
                details={},
            )
        )

        window = MainWindow(context.controller)

        assert any(label.text().strip() for label in window._dashboard_labels)
        assert window._apps_table.rowCount() == 1
        assert [_table_text(window._apps_table, 0, index) for index in range(3)] == [
            ZoneKind.DIRECT.value,
            "Browser",
            r"C:\Tools\browser.exe",
        ]
        assert window._journal_table.rowCount() == 1
        assert [
            _table_text(window._journal_table, 0, index)
            for index in range(4)
        ] == [
            "2026-06-13T12:00:00",
            "warning",
            ZoneKind.DIRECT.value,
            "Direct route not guaranteed",
        ]
    finally:
        context.close()


def test_main_window_adds_manual_app_from_action(tmp_path: Path):
    from vpn_sandbox.app.bootstrap import open_app_context
    from vpn_sandbox.core.models import OperatingMode, ZoneKind
    from vpn_sandbox.ui.main_window import MainWindow

    _app = _ensure_qapplication()
    context = open_app_context(tmp_path)
    try:
        context.controller.configure_mode(OperatingMode.DUAL_ZONE)
        window = MainWindow(context.controller)

        window.add_manual_app_for_test(
            zone=ZoneKind.VPN,
            exe_path="C:/Apps/browser.exe",
            display_name="Browser",
        )

        assert context.repository.list_managed_apps(ZoneKind.VPN)[0].display_name == "Browser"
    finally:
        context.close()


def test_main_window_add_app_dialog_warns_for_duplicate_app(monkeypatch):
    from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
    from vpn_sandbox.app.controller import DashboardState
    from vpn_sandbox.core.models import OperatingMode, ZoneKind
    from vpn_sandbox.ui.main_window import MainWindow

    class DuplicateController:
        def __init__(self) -> None:
            self.calls = []

        def load_dashboard(self, _snapshot):
            return DashboardState(
                operating_mode=OperatingMode.DUAL_ZONE,
                zones={},
                events=(),
            )

        def add_manual_app(self, zone, exe_path, display_name):
            self.calls.append((zone, exe_path, display_name))
            raise ValueError("application is already managed")

    warnings = []
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args: ("C:/Apps/browser.exe", ""),
    )
    monkeypatch.setattr(
        QInputDialog,
        "getItem",
        lambda *args: ("VPN-зона", True),
    )
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda parent, title, message: warnings.append((parent, title, message)),
    )

    _app = _ensure_qapplication()
    controller = DuplicateController()
    window = MainWindow(controller)

    window._show_add_app_dialog()

    assert controller.calls == [
        (ZoneKind.VPN, "C:/Apps/browser.exe", "browser"),
    ]
    assert warnings == [
        (
            window,
            "Приложение уже добавлено",
            "Это приложение уже добавлено в одну из зон. Удалите его из текущей зоны, чтобы добавить в другую.",
        )
    ]


def test_main_window_add_app_dialog_reraises_unexpected_value_error(monkeypatch):
    from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
    from vpn_sandbox.app.controller import DashboardState
    from vpn_sandbox.core.models import OperatingMode
    from vpn_sandbox.ui.main_window import MainWindow

    class BrokenController:
        def load_dashboard(self, _snapshot):
            return DashboardState(
                operating_mode=OperatingMode.DUAL_ZONE,
                zones={},
                events=(),
            )

        def add_manual_app(self, zone, exe_path, display_name):
            raise ValueError("different validation failure")

    warnings = []
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args: ("C:/Apps/browser.exe", ""),
    )
    monkeypatch.setattr(
        QInputDialog,
        "getItem",
        lambda *args: ("VPN-зона", True),
    )
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *args: warnings.append(args),
    )

    _app = _ensure_qapplication()
    window = MainWindow(BrokenController())

    with pytest.raises(ValueError, match="different validation failure"):
        window._show_add_app_dialog()

    assert warnings == []


def test_main_window_saves_active_vpn_profile_from_action(tmp_path: Path):
    from vpn_sandbox.app.bootstrap import open_app_context
    from vpn_sandbox.core.models import ZoneKind
    from vpn_sandbox.ui.main_window import MainWindow

    _app = _ensure_qapplication()
    context = open_app_context(tmp_path)
    try:
        window = MainWindow(context.controller)

        window.save_vpn_profile_for_test(
            country_code="DE",
            country_name="Germany",
            city="Berlin",
            external_ip="203.0.113.10",
            protocol="WireGuard",
            client_name="wg-client",
            custom_name="Berlin WG",
        )

        profiles = context.repository.list_vpn_profiles()
        assert len(profiles) == 1
        assert profiles[0].effective_name == "Berlin WG"
        settings = context.repository.get_zone_settings(ZoneKind.VPN)
        assert settings is not None
        assert settings.active_profile_id == profiles[0].id
    finally:
        context.close()


def test_main_window_vpn_profile_dialog_saves_entered_values(tmp_path: Path, monkeypatch):
    from vpn_sandbox.app.bootstrap import open_app_context
    from vpn_sandbox.core.models import ZoneKind
    from vpn_sandbox.ui.main_window import MainWindow

    _patch_input_text_sequence(
        monkeypatch,
        [
            (" DE ", True),
            (" Germany ", True),
            (" 203.0.113.10 ", True),
            (" Berlin ", True),
            (" WireGuard ", True),
            (" wg-client ", True),
            (" Berlin WG ", True),
        ],
    )

    _app = _ensure_qapplication()
    context = open_app_context(tmp_path)
    try:
        window = MainWindow(context.controller)

        window._show_add_vpn_profile_dialog()

        profiles = context.repository.list_vpn_profiles()
        assert len(profiles) == 1
        assert profiles[0].country_code == "DE"
        assert profiles[0].country_name == "Germany"
        assert profiles[0].city == "Berlin"
        assert profiles[0].external_ip == "203.0.113.10"
        assert profiles[0].protocol == "WireGuard"
        assert profiles[0].client_name == "wg-client"
        assert profiles[0].custom_name == "Berlin WG"
        settings = context.repository.get_zone_settings(ZoneKind.VPN)
        assert settings is not None
        assert settings.active_profile_id == profiles[0].id
    finally:
        context.close()


def test_main_window_saves_active_direct_profile_from_action(tmp_path: Path):
    from vpn_sandbox.app.bootstrap import open_app_context
    from vpn_sandbox.core.models import ZoneKind
    from vpn_sandbox.ui.main_window import MainWindow

    _app = _ensure_qapplication()
    context = open_app_context(tmp_path)
    try:
        window = MainWindow(context.controller)

        window.save_direct_profile_for_test(
            interface_name="Ethernet",
            gateway="192.0.2.1",
            dns_servers=("1.1.1.1", "8.8.8.8"),
            custom_name="Office LAN",
        )

        profiles = context.repository.list_direct_profiles()
        assert len(profiles) == 1
        assert profiles[0].effective_name == "Office LAN"
        settings = context.repository.get_zone_settings(ZoneKind.DIRECT)
        assert settings is not None
        assert settings.active_profile_id == profiles[0].id
    finally:
        context.close()


def test_main_window_direct_profile_dialog_saves_dns_servers(tmp_path: Path, monkeypatch):
    from vpn_sandbox.app.bootstrap import open_app_context
    from vpn_sandbox.core.models import ZoneKind
    from vpn_sandbox.ui.main_window import MainWindow

    _patch_input_text_sequence(
        monkeypatch,
        [
            (" Ethernet ", True),
            (" 192.0.2.1 ", True),
            ("1.1.1.1, 8.8.8.8", True),
            (" Office LAN ", True),
        ],
    )

    _app = _ensure_qapplication()
    context = open_app_context(tmp_path)
    try:
        window = MainWindow(context.controller)

        window._show_add_direct_profile_dialog()

        profiles = context.repository.list_direct_profiles()
        assert len(profiles) == 1
        assert profiles[0].interface_name == "Ethernet"
        assert profiles[0].gateway == "192.0.2.1"
        assert profiles[0].dns_servers == ("1.1.1.1", "8.8.8.8")
        assert profiles[0].custom_name == "Office LAN"
        settings = context.repository.get_zone_settings(ZoneKind.DIRECT)
        assert settings is not None
        assert settings.active_profile_id == profiles[0].id
    finally:
        context.close()


@pytest.mark.parametrize(
    ("dialog_name", "answers", "profile_list_name"),
    [
        ("_show_add_vpn_profile_dialog", [("", False)], "list_vpn_profiles"),
        ("_show_add_vpn_profile_dialog", [("DE", True), ("   ", True)], "list_vpn_profiles"),
        ("_show_add_direct_profile_dialog", [("", False)], "list_direct_profiles"),
        ("_show_add_direct_profile_dialog", [("   ", True)], "list_direct_profiles"),
    ],
)
def test_main_window_profile_dialog_skips_cancel_or_empty_required_field(
    tmp_path: Path,
    monkeypatch,
    dialog_name: str,
    answers,
    profile_list_name: str,
):
    from vpn_sandbox.app.bootstrap import open_app_context
    from vpn_sandbox.ui.main_window import MainWindow

    _patch_input_text_sequence(monkeypatch, answers)

    _app = _ensure_qapplication()
    context = open_app_context(tmp_path)
    try:
        window = MainWindow(context.controller)

        getattr(window, dialog_name)()

        assert getattr(context.repository, profile_list_name)() == []
    finally:
        context.close()


def test_main_window_refresh_uses_explicit_zone_order_and_clears_missing_zone():
    from vpn_sandbox.app.controller import DashboardState, ZoneDashboard
    from vpn_sandbox.core.models import OperatingMode, ZoneKind, ZoneStatus
    from vpn_sandbox.ui.main_window import MainWindow
    from vpn_sandbox.ui.text import zone_label

    class FakeController:
        def __init__(self, *dashboards: DashboardState) -> None:
            self._dashboards = list(dashboards)
            self._index = 0

        def load_dashboard(self, _snapshot):
            dashboard = self._dashboards[min(self._index, len(self._dashboards) - 1)]
            self._index += 1
            return dashboard

    vpn_zone = ZoneDashboard(
        zone=ZoneKind.VPN,
        enabled=True,
        status=ZoneStatus.ATTENTION,
        reason="VPN missing",
        apps=(),
        active_profile_name=None,
    )
    direct_zone = ZoneDashboard(
        zone=ZoneKind.DIRECT,
        enabled=True,
        status=ZoneStatus.OK,
        reason="Direct route confirmed",
        apps=(),
        active_profile_name=None,
    )
    first_dashboard = DashboardState(
        operating_mode=OperatingMode.DUAL_ZONE,
        zones={ZoneKind.DIRECT: direct_zone, ZoneKind.VPN: vpn_zone},
        events=(),
    )
    missing_direct_dashboard = DashboardState(
        operating_mode=OperatingMode.DUAL_ZONE,
        zones={ZoneKind.VPN: vpn_zone},
        events=(),
    )

    _app = _ensure_qapplication()
    window = MainWindow(FakeController(first_dashboard, missing_direct_dashboard))

    assert window._dashboard_labels[0].text().startswith(zone_label(ZoneKind.VPN))
    assert window._dashboard_labels[1].text().startswith(zone_label(ZoneKind.DIRECT))

    direct_text = window._dashboard_labels[1].text()
    window.refresh()

    assert window._dashboard_labels[1].text() != direct_text
    assert window._dashboard_labels[1].text() == f"{zone_label(ZoneKind.DIRECT)}: нет данных"


def test_mini_indicator_can_update_status_text():
    from vpn_sandbox.core.models import ZoneStatus
    from vpn_sandbox.ui.mini_indicator import MiniIndicator

    _app = _ensure_qapplication()
    indicator = MiniIndicator()
    try:
        indicator.update_status(ZoneStatus.ATTENTION, "Требует внимания")

        assert "Требует внимания" in indicator.status_text()
    finally:
        indicator.close()


def test_tray_controller_builds_menu(tmp_path: Path):
    from vpn_sandbox.app.bootstrap import open_app_context
    from vpn_sandbox.core.models import OperatingMode
    from vpn_sandbox.ui.main_window import MainWindow
    from vpn_sandbox.ui.tray import TrayController

    _app = _ensure_qapplication()
    context = open_app_context(tmp_path)
    try:
        context.controller.configure_mode(OperatingMode.DUAL_ZONE)
        window = MainWindow(context.controller)
        tray = TrayController(window)

        assert tray.menu_action_texts() == [
            "Открыть",
            "Показать мини-индикатор",
            "Открыть журнал",
            "Выход",
        ]
    finally:
        context.close()
