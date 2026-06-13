from __future__ import annotations

import sys
from collections.abc import Sequence

from PyQt6.QtWidgets import QApplication


def create_qapplication(argv: Sequence[str] | None = None) -> QApplication:
    existing = QApplication.instance()
    app = existing if existing is not None else QApplication(list(argv or []))
    app.setApplicationName("Песочница VPN")
    app.setOrganizationName("VPN Sandbox")
    return app


def main(argv: Sequence[str] | None = None) -> int:
    app = create_qapplication(sys.argv[:1] if argv is None else argv)
    from vpn_sandbox.app.bootstrap import open_app_context
    from vpn_sandbox.ui.first_run import FirstRunDialog
    from vpn_sandbox.ui.main_window import MainWindow
    from vpn_sandbox.ui.tray import TrayController

    context = open_app_context()
    if context.controller.get_operating_mode() is None:
        dialog = FirstRunDialog()
        if dialog.exec() != dialog.DialogCode.Accepted:
            context.close()
            return 0
        context.controller.configure_mode(dialog.selected_mode())

    window = MainWindow(context.controller)
    tray = TrayController(window)
    tray.show()
    window.show()
    exit_code = app.exec()
    context.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
