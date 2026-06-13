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
