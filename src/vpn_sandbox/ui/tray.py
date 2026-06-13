from __future__ import annotations

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from vpn_sandbox.ui.main_window import MainWindow
from vpn_sandbox.ui.mini_indicator import MiniIndicator


class TrayController:
    def __init__(self, window: MainWindow) -> None:
        self.window = window
        self.indicator = MiniIndicator()
        self.menu = QMenu()

        open_action = QAction("Открыть")
        mini_action = QAction("Показать мини-индикатор")
        journal_action = QAction("Открыть журнал")
        quit_action = QAction("Выход")
        self._actions = [open_action, mini_action, journal_action, quit_action]

        open_action.triggered.connect(self.window.show)
        mini_action.triggered.connect(self.indicator.show)
        journal_action.triggered.connect(lambda: self.window.tabs.setCurrentIndex(4))
        quit_action.triggered.connect(self.window.close)

        self.menu.addAction(open_action)
        self.menu.addAction(mini_action)
        self.menu.addAction(journal_action)
        self.menu.addAction(quit_action)

        self.tray = QSystemTrayIcon(QIcon(), self.window)
        self.tray.setToolTip("Песочница VPN")
        self.tray.setContextMenu(self.menu)

    def show(self) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def menu_action_texts(self) -> list[str]:
        return [action.text() for action in self.menu.actions()]
