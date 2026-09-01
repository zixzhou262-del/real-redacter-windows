from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

from offline_anonymizer.app_environment import get_app_paths


def write_error_report(
    output_dir: str | Path,
    source: str | Path,
    operation: str,
    error_code: str,
    message: str,
    detail: str | None = None,
    context: dict[str, Any] | None = None,
) -> Path:
    source_path = Path(str(source).strip().strip('"').strip("'"))
    source_name = _safe_name(source_path.stem or source_path.name) or "文档"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{source_name}{operation}错误报告_{timestamp}.json"
    report_dir = _writable_report_dir(Path(output_dir), source_path)
    report_path = _available_path(report_dir / filename)
    payload = {
        "status": "failed",
        "operation": operation,
        "input": str(source_path),
        "time": datetime.now().astimezone().isoformat(),
        "error_code": error_code,
        "message": message,
        "detail": detail,
        "context": context or {},
    }
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return report_path


def _writable_report_dir(preferred: Path, source: Path) -> Path:
    candidates = [preferred.expanduser()]
    if source.parent != Path("."):
        candidates.append(source.expanduser().parent)
    candidates.append(get_app_paths().logs_dir)
    last_error: Exception | None = None
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".real_redacter_write_test"
            probe.touch(exist_ok=True)
            probe.unlink(missing_ok=True)
            return candidate
        except Exception as exc:
            last_error = exc
    raise OSError("无法创建错误报告") from last_error


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", value.strip())
    return cleaned.strip("._")[:80]


def _available_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1
