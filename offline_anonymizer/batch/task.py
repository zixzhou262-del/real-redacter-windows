from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_PENDING = "pending"
TASK_PROCESSING = "processing"
TASK_SUCCESS = "success"
TASK_FAILED = "failed"


@dataclass
class BatchTask:
    file: str
    relative_path: str
    status: str = TASK_PENDING
    start_time: str | None = None
    end_time: str | None = None
    tokens: int = 0
    recovered_tokens: int = 0
    output_files: dict[str, str] = field(default_factory=dict)
    masked_html: str | None = None
    mapping_file: str | None = None
    masked_document: str | None = None
    recovered_document: str | None = None
    error: str | None = None

    @classmethod
    def from_path(cls, path: Path, relative_path: Path) -> "BatchTask":
        return cls(file=str(path), relative_path=relative_path.as_posix())

    def mark_processing(self) -> None:
        self.status = TASK_PROCESSING
        self.start_time = _now()

    def mark_success(self, result: Any) -> None:
        self.status = TASK_SUCCESS
        self.end_time = _now()
        self.masked_html = result.masked_html
        self.mapping_file = result.mapping_file
        self.masked_document = result.masked_document
        self.recovered_document = result.recovered_document
        self.output_files = result.output_files
        self.tokens = int(result.report.get("tokens", 0) or 0)
        self.recovered_tokens = int(result.report.get("recovered_tokens", 0) or 0)

    def mark_failed(self, error: Exception | str) -> None:
        self.status = TASK_FAILED
        self.end_time = _now()
        self.error = str(error)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "relative_path": self.relative_path,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "tokens": self.tokens,
            "recovered_tokens": self.recovered_tokens,
            "masked_html": self.masked_html,
            "mapping_file": self.mapping_file,
            "masked_document": self.masked_document,
            "recovered_document": self.recovered_document,
            "output_files": self.output_files,
            "error": self.error,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
