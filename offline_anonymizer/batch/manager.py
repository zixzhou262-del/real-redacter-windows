from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from offline_anonymizer.anonymizer.token_registry import TokenRegistry
from offline_anonymizer.batch.report import BatchResult, build_batch_result, utc_now
from offline_anonymizer.batch.task import BatchTask
from offline_anonymizer.config import load_config
from offline_anonymizer.parser import ParserFactory
from offline_anonymizer.security.mapping_crypto import write_mapping
from offline_anonymizer.workflow import DocumentPipeline


SUPPORTED_EXTENSIONS = {".docx", ".md", ".markdown", ".txt"}


class BatchProcessor:
    def __init__(
        self,
        config_path: str | Path | None = None,
        config: dict[str, Any] | None = None,
        max_workers: int = 1,
    ) -> None:
        self.config = config or load_config(config_path)
        self.max_workers = max(1, int(max_workers))

    def process_directory(
        self,
        input_directory: str | Path,
        output_directory: str | Path,
        output_formats: list[str] | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> BatchResult:
        input_root = Path(input_directory)
        output_root = Path(output_directory)
        start_clock = perf_counter()
        start_time = utc_now()
        tasks, ignored_files = self.scan(input_root)
        self._prepare_output_dirs(output_root)
        registry = TokenRegistry(labels=self.config.get("token_labels"))
        completed = 0
        self._emit(
            progress_callback,
            event="batch_started",
            total=len(tasks),
            completed=0,
            success=0,
            failed=0,
        )

        for task in tasks:
            self._emit_task(progress_callback, "task_started", task, completed, len(tasks))
            self._run_task(task, input_root, output_root, output_formats, registry)
            completed += 1
            self._emit_task(progress_callback, "task_finished", task, completed, len(tasks))

        end_time = utc_now()
        duration = perf_counter() - start_clock
        batch_mapping_file = self._write_batch_mapping(output_root, tasks, registry)
        result = build_batch_result(
            input_root,
            output_root,
            tasks,
            ignored_files,
            start_time,
            end_time,
            duration,
        )
        result.batch_mapping_file = str(batch_mapping_file)
        result.write(output_root / "reports" / "batch_report.json")
        self._emit(
            progress_callback,
            event="batch_finished",
            total=result.total,
            completed=result.total,
            success=result.success,
            failed=result.failed,
            report_file=result.report_file,
            batch_mapping_file=result.batch_mapping_file,
        )
        return result

    def scan(self, input_root: Path) -> tuple[list[BatchTask], list[str]]:
        tasks: list[BatchTask] = []
        ignored: list[str] = []
        for path in sorted(input_root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(input_root)
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                tasks.append(BatchTask.from_path(path, relative))
            else:
                ignored.append(relative.as_posix())
        return tasks, ignored

    def _run_task(
        self,
        task: BatchTask,
        input_root: Path,
        output_root: Path,
        output_formats: list[str] | None,
        registry: TokenRegistry,
    ) -> BatchTask:
        task.mark_processing()
        paths: dict[str, Any] | None = None
        try:
            source = Path(task.file)
            relative = source.relative_to(input_root)
            paths = self._output_paths(output_root, relative, output_formats)
            pipeline = DocumentPipeline(
                config=self._task_config(output_root),
                output_dir=output_root,
            )
            result = pipeline.anonymize_document(
                source,
                paths["document"],
                paths["mapping"],
                registry=registry,
            )
            task.mark_success(result)
        except Exception as exc:
            if paths is not None:
                for path in paths.values():
                    Path(path).unlink(missing_ok=True)
            task.mark_failed(exc)
        return task

    def _output_paths(
        self,
        output_root: Path,
        relative: Path,
        output_formats: list[str] | None,
    ) -> dict[str, Any]:
        stem_path = relative.with_suffix("")
        formats = output_formats or self.config.get("output", {}).get(
            "default_formats",
            [relative.suffix.removeprefix(".") or "docx"],
        )
        output_format = formats[0].removeprefix(".") if formats else "docx"
        return {
            "document": output_root
            / stem_path.parent
            / f"{stem_path.name}已脱敏.{output_format}",
            "mapping": output_root
            / stem_path.parent
            / f"{stem_path.name}还原映射文件.json",
        }

    def _task_config(self, output_root: Path) -> dict[str, Any]:
        config = dict(self.config)
        paths = dict(config.get("paths", {}))
        paths["output_dir"] = str(output_root)
        paths["log_dir"] = str(output_root / "reports" / "logs")
        config["paths"] = paths
        return config

    @staticmethod
    def _prepare_output_dirs(output_root: Path) -> None:
        for name in ["reports"]:
            (output_root / name).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _write_batch_mapping(
        output_root: Path,
        tasks: list[BatchTask],
        registry: TokenRegistry,
    ) -> Path:
        mapping = registry.export_mapping()
        batch_mapping = output_root / "批量还原映射文件.json"
        write_mapping(batch_mapping, mapping)
        for task in tasks:
            if task.status == "success" and task.mapping_file:
                write_mapping(task.mapping_file, mapping)
        return batch_mapping

    @staticmethod
    def _emit(
        callback: Callable[[dict[str, Any]], None] | None,
        **payload: Any,
    ) -> None:
        if callback is not None:
            callback(payload)

    def _emit_task(
        self,
        callback: Callable[[dict[str, Any]], None] | None,
        event: str,
        task: BatchTask,
        completed: int,
        total: int,
    ) -> None:
        self._emit(
            callback,
            event=event,
            total=total,
            completed=completed,
            current_file=task.file,
            task=task.to_dict(),
        )
