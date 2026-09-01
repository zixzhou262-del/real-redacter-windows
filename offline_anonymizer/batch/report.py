from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import platform
from pathlib import Path
from typing import Any

try:
    import resource
except ImportError:  # Windows does not provide the Unix resource module.
    resource = None  # type: ignore[assignment]

from offline_anonymizer.batch.task import TASK_FAILED, TASK_SUCCESS, BatchTask


@dataclass
class BatchResult:
    input_directory: str
    output_directory: str
    total: int
    success: int
    failed: int
    ignored: int
    start_time: str
    end_time: str
    duration_seconds: float
    average_seconds_per_file: float
    memory_peak_kb: int | None
    files: list[dict[str, Any]] = field(default_factory=list)
    ignored_files: list[str] = field(default_factory=list)
    report_file: str | None = None
    batch_mapping_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_directory": self.input_directory,
            "output_directory": self.output_directory,
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "ignored": self.ignored,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "average_seconds_per_file": self.average_seconds_per_file,
            "memory_peak_kb": self.memory_peak_kb,
            "files": self.files,
            "ignored_files": self.ignored_files,
            "report_file": self.report_file,
            "batch_mapping_file": self.batch_mapping_file,
        }

    def write(self, path: str | Path) -> None:
        report_path = Path(path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_file = str(report_path)
        report_path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def build_batch_result(
    input_directory: Path,
    output_directory: Path,
    tasks: list[BatchTask],
    ignored_files: list[str],
    start_time: str,
    end_time: str,
    duration_seconds: float,
) -> BatchResult:
    success = sum(1 for task in tasks if task.status == TASK_SUCCESS)
    failed = sum(1 for task in tasks if task.status == TASK_FAILED)
    total = len(tasks)
    return BatchResult(
        input_directory=str(input_directory),
        output_directory=str(output_directory),
        total=total,
        success=success,
        failed=failed,
        ignored=len(ignored_files),
        start_time=start_time,
        end_time=end_time,
        duration_seconds=duration_seconds,
        average_seconds_per_file=duration_seconds / total if total else 0.0,
        memory_peak_kb=_memory_peak_kb(),
        files=[task.to_dict() for task in tasks],
        ignored_files=ignored_files,
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _memory_peak_kb() -> int | None:
    if resource is None:
        return None
    try:
        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        if platform.system() == "Darwin":
            return value // 1024
        return value
    except Exception:
        return None
