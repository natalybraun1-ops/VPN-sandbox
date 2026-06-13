from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem


class StatusBadge(QLabel):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setMinimumWidth(120)
        self.setStyleSheet(
            "padding: 6px 10px;"
            "border: 1px solid #b8c2cc;"
            "border-radius: 4px;"
        )


def set_table_rows(table: QTableWidget, rows: list[list[str]]) -> None:
    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            table.setItem(row_index, column_index, QTableWidgetItem(value))
