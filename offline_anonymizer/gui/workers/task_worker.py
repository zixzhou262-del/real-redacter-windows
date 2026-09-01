from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, Slot

from offline_anonymizer.gui.workers.signals import WorkerSignals


class TaskWorker(QObject):
    def __init__(
        self,
        operation: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self.operation = operation
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @classmethod
    def process_file(
        cls,
        document_service,
        input_file,
        output_dir,
        config=None,
        formats=None,
    ) -> "TaskWorker":
        return cls(
            document_service.process_file,
            input_file,
            output_dir,
            config,
            formats,
        )

    @classmethod
    def process_batch(
        cls,
        document_service,
        input_dir,
        output_dir,
        config=None,
        formats=None,
        workers=1,
    ) -> "TaskWorker":
        return cls(
            document_service.process_batch,
            input_dir,
            output_dir,
            config,
            formats,
            workers,
        )

    @classmethod
    def recover_document(
        cls,
        document_service,
        html_file,
        mapping_file,
        output_dir,
        formats=None,
        config=None,
    ) -> "TaskWorker":
        return cls(
            document_service.recover_document,
            html_file,
            mapping_file,
            output_dir,
            formats,
            config,
        )

    @Slot()
    def run(self) -> None:
        try:
            self.kwargs["progress_callback"] = self._emit_progress
            result = self.operation(*self.args, **self.kwargs)
            payload = result.to_dict() if hasattr(result, "to_dict") else {"result": result}
            if result.success:
                self.signals.task_finished.emit(payload)
            else:
                self.signals.task_failed.emit(payload)
        except Exception as exc:
            self.signals.task_failed.emit(
                {
                    "success": False,
                    "message": "任务执行失败",
                    "error": {
                        "code": "GUI_WORKER_ERROR",
                        "detail": str(exc),
                    },
                }
            )

    def _emit_progress(self, payload: dict[str, Any]) -> None:
        self.signals.progress_update.emit(payload)
        if payload.get("batch_event"):
            self.signals.batch_progress_update.emit(payload)
        if payload.get("current_file"):
            self.signals.current_file_update.emit(payload)
