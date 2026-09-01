from __future__ import annotations

from pathlib import Path

from offline_anonymizer.exporter.base import DocumentExporter
from offline_anonymizer.exporter.docx_exporter import DocxExporter
from offline_anonymizer.exporter.markdown_exporter import MarkdownExporter
from offline_anonymizer.exporter.txt_exporter import TxtExporter


class ExporterFactory:
    _exporters: list[DocumentExporter] = [
        DocxExporter(),
        MarkdownExporter(),
        TxtExporter(),
    ]

    @classmethod
    def get_exporter(cls, file_type_or_path: str | Path) -> DocumentExporter:
        value = str(file_type_or_path).lower()
        extension = value if value.startswith(".") else Path(value).suffix.lower()
        if not extension:
            extension = f".{value}"

        for exporter in cls._exporters:
            if extension in exporter.supported_extensions:
                return exporter

        raise ValueError(f"Unsupported export format: {file_type_or_path}")

    @classmethod
    def register(cls, exporter: DocumentExporter) -> None:
        cls._exporters.append(exporter)
