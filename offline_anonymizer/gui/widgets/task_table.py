from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


HEADERS = ["文件", "状态", "进度", "Token数量", "耗时", "结果", "错误/消息"]


class TaskTableWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._rows_by_task: dict[str, int] = {}

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)

    def add_task(self, task_id: str, file: str, status: str = "等待") -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._rows_by_task[task_id] = row
        values = [file, status, "0", "0", "", "", ""]
        for column, value in enumerate(values):
            self.table.setItem(row, column, QTableWidgetItem(value))

    def update_task(
        self,
        task_id: str,
        status: str | None = None,
        progress: int | None = None,
        tokens: int | None = None,
        duration: str | None = None,
        result_path: str | None = None,
        message: str | None = None,
    ) -> None:
        row = self._rows_by_task.get(task_id)
        if row is None:
            return
        updates = {
            1: status,
            2: str(progress) if progress is not None else None,
            3: str(tokens) if tokens is not None else None,
            4: duration,
            5: result_path,
            6: message,
        }
        for column, value in updates.items():
            if value is not None:
                self.table.setItem(row, column, QTableWidgetItem(value))

    def clear_records(self) -> None:
        self.table.setRowCount(0)
        self._rows_by_task.clear()
