from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from offline_anonymizer.services.result import ServiceResult


TASK_PENDING = "pending"
TASK_RUNNING = "running"
TASK_SUCCESS = "success"
TASK_FAILED = "failed"


@dataclass
class GuiTask:
    id: str
    file: str
    status: str = TASK_PENDING
    progress: int = 0
    tokens: int = 0
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "file": self.file,
            "status": self.status,
            "progress": self.progress,
            "tokens": self.tokens,
            "message": self.message,
            "metadata": self.metadata,
        }


class TaskService:
    def __init__(self) -> None:
        self._tasks: dict[str, GuiTask] = {}

    def create_task(self, file: str, message: str = "") -> ServiceResult:
        task = GuiTask(id=f"task_{uuid4().hex[:12]}", file=file, message=message)
        self._tasks[task.id] = task
        return ServiceResult.ok("任务已创建", {"task": task.to_dict()})

    def update_task(
        self,
        task_id: str,
        status: str | None = None,
        progress: int | None = None,
        tokens: int | None = None,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceResult:
        task = self._tasks.get(task_id)
        if task is None:
            return ServiceResult.fail("任务不存在", "TASK_NOT_FOUND")
        if status is not None:
            task.status = status
        if progress is not None:
            task.progress = max(0, min(100, int(progress)))
        if tokens is not None:
            task.tokens = int(tokens)
        if message is not None:
            task.message = message
        if metadata is not None:
            task.metadata.update(metadata)
        return ServiceResult.ok("任务已更新", {"task": task.to_dict()})

    def get_tasks(self) -> ServiceResult:
        return ServiceResult.ok(
            "任务列表已获取",
            {"tasks": [task.to_dict() for task in self._tasks.values()]},
        )

    def clear_tasks(self) -> ServiceResult:
        self._tasks.clear()
        return ServiceResult.ok("任务已清空", {"tasks": []})
