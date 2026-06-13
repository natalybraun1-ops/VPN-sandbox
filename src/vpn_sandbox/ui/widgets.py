from __future__ import annotations

from collections.abc import Sequence

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


def set_table_rows(table: QTableWidget, rows: Sequence[Sequence[object]]) -> None:
    table.clearContents()
    table.setRowCount(len(rows))
    column_count = table.columnCount()
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            if column_index >= column_count:
                break
            text = "" if value is None else str(value)
            table.setItem(row_index, column_index, QTableWidgetItem(text))
