import os

import pytest

pytest.importorskip("PyQt6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_create_qapplication_returns_single_instance():
    from PyQt6.QtWidgets import QApplication
    from vpn_sandbox.ui.app import create_qapplication

    app = create_qapplication([])

    assert app is QApplication.instance()
    assert app.applicationName() == "Песочница VPN"
