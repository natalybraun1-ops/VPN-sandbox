import os

import pytest

pytest.importorskip("PyQt6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _create_first_run_dialog():
    from vpn_sandbox.ui.app import create_qapplication
    from vpn_sandbox.ui.first_run import FirstRunDialog

    app = create_qapplication([])
    return app, FirstRunDialog()


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
