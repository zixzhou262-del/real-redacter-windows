from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from offline_anonymizer.anonymizer.detector import custom_detectors, default_detectors
from offline_anonymizer.anonymizer.engine import AnonymizationEngine
from offline_anonymizer.anonymizer.token_registry import TokenRegistry
from offline_anonymizer.config import load_config
from offline_anonymizer.core.document import Document
from offline_anonymizer.docx_format import anonymize_docx_preserving_format
from offline_anonymizer.exporter import ExporterFactory
from offline_anonymizer.parser import ParserFactory
from offline_anonymizer.recovery import HtmlRecoveryEngine, MaskedDocumentRecoveryEngine
from offline_anonymizer.renderer import HtmlRenderer
from offline_anonymizer.security.mapping_crypto import write_mapping
from offline_anonymizer.workflow.logger import WorkflowLogger


SUPPORTED_RULE_TYPES = {"money", "number", "percent"}


@dataclass
class WorkflowResult:
    original_file: str
    masked_html: str | None = None
    mapping_file: str | None = None
    masked_document: str | None = None
    recovered_document: str | None = None
    output_files: dict[str, str] = field(default_factory=dict)
    report: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_file": self.original_file,
            "masked_html": self.masked_html,
            "mapping_file": self.mapping_file,
            "masked_document": self.masked_document,
            "recovered_document": self.recovered_document,
            "output_files": self.output_files,
            "report": self.report,
        }


class DocumentPipeline:
    def __init__(
        self,
        config_path: str | Path | None = None,
        config: dict[str, Any] | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        self.config = config or load_config(config_path)
        self.output_dir = Path(
            output_dir or self.config.get("paths", {}).get("output_dir", "outputs")
        )
        if output_dir is not None and config is None and config_path is None:
            paths = dict(self.config.get("paths", {}))
            paths["output_dir"] = str(self.output_dir)
            paths["log_dir"] = str(self.output_dir / "logs")
            self.config["paths"] = paths
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = WorkflowLogger(
            self.config.get("paths", {}).get("log_dir", "logs")
        )

    def anonymize(self, input_file: str | Path) -> WorkflowResult:
        started = _now()
        source = Path(input_file)
        result = WorkflowResult(original_file=str(source))
        try:
            document = ParserFactory.get_parser(source).parse(source)
            registry = self._registry()
            engine = AnonymizationEngine(
                detectors=self._enabled_detectors(),
                registry=registry,
            )
            masked = engine.anonymize(document)

            html_path = self.output_dir / f"{source.stem}_masked.html"
            mapping_path = self.output_dir / f"{source.stem}_mapping.json"
            masked_document_path = self.output_dir / f"{source.stem}_masked_document.json"
            HtmlRenderer().write(masked, registry, html_path, mapping_path)
            masked_document_path.write_text(masked.to_json(), encoding="utf-8")

            result.masked_html = str(html_path)
            result.mapping_file = str(mapping_path)
            result.masked_document = str(masked_document_path)
            result.report = {
                "status": "success",
                "started_at": started,
                "ended_at": _now(),
                "tokens": len(registry.all_tokens()),
            }
            self._log("anonymize", source, result.report)
            return result
        except Exception as exc:
            result.report = self._error_report(started, exc)
            self._log("anonymize", source, result.report)
            raise

    def anonymize_to_paths(
        self,
        input_file: str | Path,
        html_path: str | Path,
        mapping_path: str | Path,
        masked_json_path: str | Path | None = None,
    ) -> WorkflowResult:
        started = _now()
        source = Path(input_file)
        result = WorkflowResult(original_file=str(source))
        try:
            document = ParserFactory.get_parser(source).parse(source)
            registry = self._registry()
            engine = AnonymizationEngine(
                detectors=self._enabled_detectors(),
                registry=registry,
            )
            masked = engine.anonymize(document)
            html_output = Path(html_path)
            mapping_output = Path(mapping_path)
            html_output.parent.mkdir(parents=True, exist_ok=True)
            mapping_output.parent.mkdir(parents=True, exist_ok=True)
            HtmlRenderer().write(masked, registry, html_output, mapping_output)
            masked_document_output = (
                Path(masked_json_path)
                if masked_json_path is not None
                else html_output.with_name(f"{source.stem}_masked_document.json")
            )
            masked_document_output.parent.mkdir(parents=True, exist_ok=True)
            masked_document_output.write_text(masked.to_json(), encoding="utf-8")

            result.masked_html = str(html_output)
            result.mapping_file = str(mapping_output)
            result.masked_document = str(masked_document_output)
            result.report = {
                "status": "success",
                "started_at": started,
                "ended_at": _now(),
                "tokens": len(registry.all_tokens()),
            }
            self._log("anonymize", source, result.report)
            return result
        except Exception as exc:
            result.report = self._error_report(started, exc)
            self._log("anonymize", source, result.report)
            raise

    def anonymize_document(
        self,
        input_file: str | Path,
        output_file: str | Path,
        mapping_file: str | Path,
        registry: TokenRegistry | None = None,
    ) -> WorkflowResult:
        started = _now()
        source = Path(input_file)
        output_path = Path(output_file)
        mapping_path = Path(mapping_file)
        result = WorkflowResult(original_file=str(source))
        try:
            registry = registry or self._registry()
            token_count_before = len(registry.all_tokens())
            engine = AnonymizationEngine(
                detectors=self._enabled_detectors(),
                registry=registry,
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mapping_path.parent.mkdir(parents=True, exist_ok=True)

            if source.suffix.lower() == ".docx" and output_path.suffix.lower() == ".docx":
                anonymize_docx_preserving_format(source, output_path, engine)
            else:
                document = ParserFactory.get_parser(source).parse(source)
                masked = engine.anonymize(document)
                ExporterFactory.get_exporter(output_path).export(masked, output_path)
            token_count_after = len(registry.all_tokens())

            write_mapping(mapping_path, registry.export_mapping())

            result.mapping_file = str(mapping_path)
            result.output_files = {output_path.suffix.removeprefix("."): str(output_path)}
            result.report = {
                "status": "success",
                "started_at": started,
                "ended_at": _now(),
                "tokens": token_count_after - token_count_before,
                "total_tokens": token_count_after,
                "output": str(output_path),
                "mapping": str(mapping_path),
            }
            self._log("anonymize_document", source, result.report)
            return result
        except Exception as exc:
            result.report = self._error_report(started, exc)
            self._log("anonymize_document", source, result.report)
            raise

    def recover(
        self,
        html_file: str | Path,
        mapping_file: str | Path,
        output_json: str | Path | None = None,
    ) -> WorkflowResult:
        started = _now()
        html_path = Path(html_file)
        mapping_path = Path(mapping_file)
        result = WorkflowResult(
            original_file=str(html_path),
            masked_html=str(html_path),
            mapping_file=str(mapping_path),
        )
        try:
            recovery = HtmlRecoveryEngine().recover_files(html_path, mapping_path)
            document_path = Path(output_json) if output_json else self.output_dir / "recovered_document.json"
            document_path.parent.mkdir(parents=True, exist_ok=True)
            document_path.write_text(recovery.document.to_json(), encoding="utf-8")
            result.recovered_document = str(document_path)
            result.report = {
                "status": "success",
                "started_at": started,
                "ended_at": _now(),
                **recovery.report.to_dict(),
            }
            self._log("recover", html_path, result.report)
            return result
        except Exception as exc:
            result.report = self._error_report(started, exc)
            self._log("recover", html_path, result.report)
            raise

    def recover_masked_document(
        self,
        masked_file: str | Path,
        mapping_file: str | Path,
        output_json: str | Path | None = None,
        preserved_docx_path: str | Path | None = None,
    ) -> WorkflowResult:
        started = _now()
        source = Path(masked_file)
        mapping_path = Path(mapping_file)
        result = WorkflowResult(
            original_file=str(source),
            mapping_file=str(mapping_path),
        )
        try:
            recovery = MaskedDocumentRecoveryEngine().recover_files(
                source,
                mapping_path,
                preserved_docx_path=preserved_docx_path,
            )
            document_path = (
                Path(output_json)
                if output_json is not None
                else self.output_dir / f"{source.stem}_recovered_document.json"
            )
            document_path.parent.mkdir(parents=True, exist_ok=True)
            document_path.write_text(recovery.document.to_json(), encoding="utf-8")
            result.recovered_document = str(document_path)
            if preserved_docx_path is not None:
                native_output = Path(preserved_docx_path)
                result.output_files["docx"] = str(native_output)
            result.report = {
                "status": "success",
                "started_at": started,
                "ended_at": _now(),
                **recovery.report.to_dict(),
                "recovery_source": source.suffix.lower().removeprefix("."),
            }
            self._log("recover_masked_document", source, result.report)
            return result
        except Exception as exc:
            result.report = self._error_report(started, exc)
            self._log("recover_masked_document", source, result.report)
            raise

    def export(
        self,
        document_json: str | Path,
        output_file: str | Path,
    ) -> WorkflowResult:
        started = _now()
        source = Path(document_json)
        output = Path(output_file)
        result = WorkflowResult(
            original_file=str(source),
            recovered_document=str(source),
        )
        try:
            document = Document.from_json(source.read_text(encoding="utf-8"))
            output.parent.mkdir(parents=True, exist_ok=True)
            ExporterFactory.get_exporter(output).export(document, output)
            result.output_files = {output.suffix.removeprefix("."): str(output)}
            result.report = {
                "status": "success",
                "started_at": started,
                "ended_at": _now(),
                "output": str(output),
            }
            self._log("export", source, result.report)
            return result
        except Exception as exc:
            result.report = self._error_report(started, exc)
            self._log("export", source, result.report)
            raise

    def process(
        self,
        input_file: str | Path,
        output_formats: list[str] | None = None,
        html_path: str | Path | None = None,
        mapping_path: str | Path | None = None,
        masked_json_path: str | Path | None = None,
        recovered_json_path: str | Path | None = None,
        output_paths: dict[str, str | Path] | None = None,
    ) -> WorkflowResult:
        started = _now()
        source = Path(input_file)
        final = WorkflowResult(original_file=str(source))
        try:
            if html_path is not None and mapping_path is not None:
                anonymized = self.anonymize_to_paths(
                    source,
                    html_path,
                    mapping_path,
                    masked_json_path,
                )
            else:
                anonymized = self.anonymize(source)
            recovered_path = (
                Path(recovered_json_path)
                if recovered_json_path is not None
                else self.output_dir / f"{source.stem}_recovered_document.json"
            )
            recovered = self.recover(
                anonymized.masked_html,
                anonymized.mapping_file,
                recovered_path,
            )

            formats = output_formats or self.config.get("output", {}).get(
                "default_formats", ["docx"]
            )
            output_files: dict[str, str] = {}
            for output_format in formats:
                normalized = output_format.removeprefix(".")
                output_path = (
                    Path(output_paths[normalized])
                    if output_paths and normalized in output_paths
                    else self.output_dir / f"{source.stem}_masked.{normalized}"
                )
                self.export(anonymized.masked_document, output_path)
                output_files[normalized] = str(output_path)

            final.masked_html = anonymized.masked_html
            final.mapping_file = anonymized.mapping_file
            final.masked_document = anonymized.masked_document
            final.recovered_document = recovered.recovered_document
            final.output_files = output_files
            final.report = {
                "status": "success",
                "started_at": started,
                "ended_at": _now(),
                "tokens": anonymized.report.get("tokens", 0),
                "recovered_tokens": recovered.report.get("restored_tokens", 0),
                "outputs": list(output_files),
            }
            self._log("pipeline", source, final.report)
            return final
        except Exception as exc:
            final.report = self._error_report(started, exc)
            self._log("pipeline", source, final.report)
            raise

    def _registry(self) -> TokenRegistry:
        return TokenRegistry(labels=self.config.get("token_labels"))

    def _enabled_detectors(self):
        configured_rules = self.config.get("rules")
        rules = configured_rules if isinstance(configured_rules, dict) else {}
        detectors = [
            detector
            for detector in default_detectors()
            if detector.token_type in SUPPORTED_RULE_TYPES
            and rules.get(detector.token_type, False)
        ]
        # A config with an explicit rules object is authoritative. For legacy
        # programmatic configs that only supplied custom keywords, preserve
        # the useful historical behavior and enable the custom detector.
        custom_enabled = rules.get(
            "custom",
            configured_rules is None
            and bool(self.config.get("custom_keywords") or self.config.get("custom_regex")),
        )
        if custom_enabled:
            detectors.extend(
                custom_detectors(
                    keywords=self.config.get("custom_keywords", []),
                    regex_patterns=self.config.get("custom_regex", []),
                )
            )
        return detectors

    def _log(self, action: str, file: Path, report: dict[str, Any]) -> None:
        self.logger.write(
            {
                "action": action,
                "file": str(file),
                "status": report.get("status"),
                "tokens": report.get("tokens"),
                "restored_tokens": report.get("restored_tokens")
                or report.get("recovered_tokens"),
                "error": report.get("error"),
            }
        )

    @staticmethod
    def _error_report(started: str, exc: Exception) -> dict[str, Any]:
        return {
            "status": "error",
            "started_at": started,
            "ended_at": _now(),
            "error": str(exc),
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
