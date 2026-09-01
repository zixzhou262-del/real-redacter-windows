from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class WorkerSignals(QObject):
    progress_update = Signal(dict)
    batch_progress_update = Signal(dict)
    current_file_update = Signal(dict)
    task_finished = Signal(dict)
    task_failed = Signal(dict)
