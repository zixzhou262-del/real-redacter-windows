from __future__ import annotations

from pathlib import Path
import re
import shutil
from typing import Any, Callable

from offline_anonymizer.batch import BatchProcessor
from offline_anonymizer.config import load_config
from offline_anonymizer.services.error_report import write_error_report
from offline_anonymizer.services.exceptions import classify_exception
from offline_anonymizer.services.result import ServiceResult
from offline_anonymizer.workflow import DocumentPipeline

ProgressCallback = Callable[[dict[str, Any]], None]


class DocumentService:
    def process_file(
        self,
        input_file: str | Path,
        output_dir: str | Path,
        config: dict[str, Any] | None = None,
        formats: list[str] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> ServiceResult:
        output_root: Path | None = None
        try:
            source = self._input_file(input_file)
            output_root = self._create_run_dir(output_dir, f"{source.stem} 脱敏文件")
            self._emit(
                progress_callback,
                "running",
                "准备处理文件",
                progress=0,
                file=str(source),
                output_dir=str(output_root),
            )
            workflow = DocumentPipeline(
                config=self._runtime_config(config, output_root),
                output_dir=output_root,
            )

            self._emit(
                progress_callback,
                "running",
                "解析并脱敏文档",
                progress=30,
                file=str(source),
            )
            output_format = self._single_output_format(
                formats,
                workflow.config.get("output", {}).get("default_formats", ["docx"]),
                source,
            )
            document_path = output_root / f"{source.stem}已脱敏.{output_format}"
            mapping_path = output_root / f"{source.stem}还原映射文件.json"
            anonymized = workflow.anonymize_document(source, document_path, mapping_path)

            output_files: dict[str, str] = {}
            output_files.update(anonymized.output_files)

            report = {
                "status": "success",
                "tokens": anonymized.report.get("tokens", 0),
                "outputs": list(output_files),
            }
            data = {
                "html": "",
                "mapping": anonymized.mapping_file,
                "masked_document": "",
                "recovered_document": "",
                "documents": list(output_files.values()),
                "output_files": output_files,
                "output_dir": str(output_root),
                "report": report,
            }
            self._emit(progress_callback, "success", "文件处理完成", progress=100, **data)
            return ServiceResult.ok("文件处理完成", data)
        except Exception as exc:
            error = classify_exception(exc, "process")
            self._remove_run_dir(output_root)
            error_report = self._error_report(
                output_dir,
                input_file,
                "脱敏",
                error.code,
                error.message,
                error.detail,
            )
            data = {"error_report": str(error_report), "report_file": str(error_report)}
            self._emit(
                progress_callback,
                "failed",
                error.message,
                progress=100,
                error_code=error.code,
                **data,
            )
            return ServiceResult.fail(error.message, error.code, error.detail, data)

    def process_batch(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        config: dict[str, Any] | None = None,
        formats: list[str] | None = None,
        workers: int = 1,
        progress_callback: ProgressCallback | None = None,
    ) -> ServiceResult:
        output_root: Path | None = None
        try:
            def on_batch_progress(payload: dict[str, Any]) -> None:
                total = int(payload.get("total", 0) or 0)
                completed = int(payload.get("completed", 0) or 0)
                current_file = payload.get("current_file")
                event = payload.get("event", "")
                message = "开始批量处理"
                if event == "task_started":
                    message = f"处理中：{current_file}"
                elif event == "task_finished":
                    message = f"已完成 {completed}/{total}"
                elif event == "batch_finished":
                    message = "批量处理完成"
                progress = int((completed / total) * 100) if total else 0
                self._emit(
                    progress_callback,
                    "running",
                    message,
                    progress=progress,
                    batch_event=event,
                    **payload,
                )

            self._emit(
                progress_callback,
                "running",
                "开始批量处理",
                progress=0,
                file=str(input_dir),
            )
            input_root = self._input_directory(input_dir)
            output_root = self._create_run_dir(
                output_dir,
                f"{input_root.name} 脱敏文件",
            )
            result = BatchProcessor(
                config=self._runtime_config(config, output_root),
                max_workers=workers,
            ).process_directory(
                input_root,
                output_root,
                output_formats=formats,
                progress_callback=on_batch_progress,
            )
            data = result.to_dict()
            data["output_dir"] = str(output_root)
            if result.failed:
                error_report = self._error_report(
                    output_root,
                    input_root,
                    "批量脱敏",
                    "BATCH_PARTIAL_ERROR",
                    f"{result.failed} 个文档脱敏失败",
                    context={"files": [item for item in data["files"] if item["status"] == "failed"]},
                )
                data["error_report"] = str(error_report)
            if result.success == 0:
                failure_context = dict(data)
                failure_context.pop("output_dir", None)
                self._remove_run_dir(output_root)
                output_root = None
                error_report = self._error_report(
                    output_dir,
                    input_root,
                    "批量脱敏",
                    "BATCH_ERROR",
                    "没有文档成功完成脱敏",
                    context=failure_context,
                )
                failure_data = {
                    **failure_context,
                    "error_report": str(error_report),
                    "report_file": str(error_report),
                    "batch_mapping_file": None,
                }
                self._emit(
                    progress_callback,
                    "failed",
                    "批量脱敏失败，请查看错误报告",
                    progress=100,
                    error_code="BATCH_ERROR",
                    **failure_data,
                )
                return ServiceResult.fail(
                    "批量脱敏失败，请查看错误报告",
                    "BATCH_ERROR",
                    "没有文档成功完成脱敏",
                    failure_data,
                )
            self._emit(progress_callback, "success", "批量处理完成", progress=100, **data)
            return ServiceResult.ok("批量处理完成", data)
        except Exception as exc:
            error = classify_exception(exc, "batch")
            self._remove_run_dir(output_root)
            error_report = self._error_report(
                output_dir,
                input_dir,
                "批量脱敏",
                error.code,
                error.message,
                error.detail,
            )
            data = {"error_report": str(error_report), "report_file": str(error_report)}
            self._emit(
                progress_callback,
                "failed",
                error.message,
                error_code=error.code,
                **data,
            )
            return ServiceResult.fail(error.message, error.code, error.detail, data)

    def recover_document(
        self,
        html_file: str | Path,
        mapping_file: str | Path,
        output_dir: str | Path,
        formats: list[str] | None = None,
        config: dict[str, Any] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> ServiceResult:
        output_root: Path | None = None
        try:
            self._emit(
                progress_callback,
                "running",
                "开始恢复文档",
                progress=0,
                file=str(html_file),
            )
            recovery_source = self._input_file(html_file)
            mapping_source = self._input_file(mapping_file)
            recovery_name = self._base_document_name(recovery_source.stem)
            output_root = self._create_run_dir(output_dir, f"{recovery_name} 恢复文件")
            workflow = DocumentPipeline(
                config=self._runtime_config(config, output_root),
                output_dir=output_root,
            )
            selected_formats = [
                value.removeprefix(".")
                for value in (
                    formats
                    or workflow.config.get("output", {}).get(
                        "default_formats",
                        ["docx"],
                    )
                )
            ]
            recovered_path = output_root / f"{recovery_source.stem}_recovered_document.json"
            if recovery_source.suffix.lower() in {".html", ".htm"}:
                recovered = workflow.recover(recovery_source, mapping_source, recovered_path)
            else:
                preserved_docx_path = (
                    output_root / f"{recovery_source.stem}_recovered.docx"
                    if recovery_source.suffix.lower() == ".docx"
                    and "docx" in selected_formats
                    else None
                )
                recovered = workflow.recover_masked_document(
                    recovery_source,
                    mapping_source,
                    recovered_path,
                    preserved_docx_path=preserved_docx_path,
                )
            report = recovered.report
            if report.get("missing_tokens", 0):
                self._remove_run_dir(output_root)
                output_root = None
                error_report = self._error_report(
                    output_dir,
                    recovery_source,
                    "恢复",
                    "RECOVERY_ERROR",
                    "部分脱敏内容无法恢复，请检查映射文件",
                    str(report),
                    context={"recovery_report": report},
                )
                data = {
                    "recovered_document": "",
                    "documents": [],
                    "output_files": {},
                    "report": report,
                    "error_report": str(error_report),
                    "report_file": str(error_report),
                }
                self._emit(
                    progress_callback,
                    "failed",
                    "部分脱敏内容无法恢复，请检查映射文件",
                    progress=100,
                    report=report,
                    error_report=str(error_report),
                    report_file=str(error_report),
                )
                return ServiceResult.fail(
                    "部分脱敏内容无法恢复，请检查映射文件",
                    "RECOVERY_ERROR",
                    str(report),
                    data,
                )
            self._emit(
                progress_callback,
                "running",
                "恢复校验通过，正在导出",
                progress=70,
                recovered_document=recovered.recovered_document,
            )
            output_files: dict[str, str] = dict(recovered.output_files)
            for normalized in selected_formats:
                if normalized in output_files:
                    continue
                output_path = output_root / f"{recovery_source.stem}_recovered.{normalized}"
                exported = workflow.export(recovered.recovered_document, output_path)
                output_files.update(exported.output_files)
            data = {
                "recovered_document": recovered.recovered_document,
                "documents": list(output_files.values()),
                "output_files": output_files,
                "output_dir": str(output_root),
                "report": report,
            }
            self._emit(progress_callback, "success", "文档恢复完成", progress=100, **data)
            return ServiceResult.ok("文档恢复完成", data)
        except Exception as exc:
            error = classify_exception(exc, "recover")
            self._remove_run_dir(output_root)
            error_report = self._error_report(
                output_dir,
                html_file,
                "恢复",
                error.code,
                error.message,
                error.detail,
            )
            data = {"error_report": str(error_report), "report_file": str(error_report)}
            self._emit(
                progress_callback,
                "failed",
                error.message,
                progress=100,
                error_code=error.code,
                **data,
            )
            return ServiceResult.fail(error.message, error.code, error.detail, data)

    def export_document(
        self,
        recovered_json: str | Path,
        output_file: str | Path,
        config: dict[str, Any] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> ServiceResult:
        try:
            self._emit(progress_callback, "running", "开始导出文档", file=str(recovered_json))
            result = DocumentPipeline(
                config=self._runtime_config(config, Path(output_file).parent),
                output_dir=Path(output_file).parent,
            ).export(recovered_json, output_file)
            data = {
                "documents": list(result.output_files.values()),
                "output_files": result.output_files,
                "report": result.report,
            }
            self._emit(progress_callback, "success", "文档导出完成", **data)
            return ServiceResult.ok("文档导出完成", data)
        except Exception as exc:
            error = classify_exception(exc, "export")
            self._emit(
                progress_callback,
                "failed",
                error.message,
                error_code=error.code,
            )
            return ServiceResult.fail(error.message, error.code, error.detail)

    @staticmethod
    def _emit(
        callback: ProgressCallback | None,
        status: str,
        message: str,
        **payload: Any,
    ) -> None:
        if callback is None:
            return
        callback({"status": status, "message": message, **payload})

    @staticmethod
    def _runtime_config(
        config: dict[str, Any] | ServiceResult | None,
        output_root: Path,
    ) -> dict[str, Any]:
        if isinstance(config, ServiceResult):
            config = config.data.get("config") if config.success else None
        effective = dict(config) if config is not None else load_config()
        paths = dict(effective.get("paths", {}))
        paths["output_dir"] = str(output_root)
        if config is None:
            paths["log_dir"] = str(output_root / "logs")
        effective["paths"] = paths
        return effective

    @classmethod
    def _create_run_dir(cls, output_dir: str | Path, label: str) -> Path:
        root = Path(output_dir)
        safe_label = cls._safe_folder_name(label) or "document"
        root.mkdir(parents=True, exist_ok=True)
        candidate = root / safe_label
        index = 2
        while candidate.exists():
            candidate = root / f"{safe_label} ({index})"
            index += 1
        candidate.mkdir(parents=True, exist_ok=False)
        return candidate

    @staticmethod
    def _safe_folder_name(value: str) -> str:
        cleaned = re.sub(r"[^\w\u4e00-\u9fff. -]+", "_", value.strip())
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip("._")[:80]

    @staticmethod
    def _single_output_format(
        requested_formats: list[str] | None,
        default_formats: list[str] | None,
        source: Path,
    ) -> str:
        choices = requested_formats or default_formats or [source.suffix.removeprefix(".")]
        if not choices:
            return source.suffix.removeprefix(".") or "docx"
        return choices[0].removeprefix(".")

    @staticmethod
    def _clean_path(value: str | Path) -> Path:
        text = str(value).strip().strip('"').strip("'")
        return Path(text).expanduser().resolve(strict=False)

    @classmethod
    def _input_file(cls, value: str | Path) -> Path:
        path = cls._clean_path(value)
        if not path.exists():
            raise FileNotFoundError(f"Input file does not exist: {path}")
        if not path.is_file():
            raise FileNotFoundError(f"Input path is not a file: {path}")
        return path

    @classmethod
    def _input_directory(cls, value: str | Path) -> Path:
        path = cls._clean_path(value)
        if not path.exists():
            raise FileNotFoundError(f"Input directory does not exist: {path}")
        if not path.is_dir():
            raise FileNotFoundError(f"Input path is not a directory: {path}")
        return path

    @staticmethod
    def _remove_run_dir(path: Path | None) -> None:
        if path is None or not path.exists():
            return
        shutil.rmtree(path, ignore_errors=True)

    @staticmethod
    def _base_document_name(stem: str) -> str:
        value = re.sub(r"(?:已脱敏|_masked)$", "", stem, flags=re.IGNORECASE).strip()
        return value or stem

    @staticmethod
    def _error_report(
        output_dir: str | Path,
        source: str | Path,
        operation: str,
        error_code: str,
        message: str,
        detail: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> Path:
        return write_error_report(
            output_dir,
            source,
            operation,
            error_code,
            message,
            detail,
            context,
        )
