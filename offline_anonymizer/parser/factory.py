from __future__ import annotations

from pathlib import Path

from offline_anonymizer.parser.base import DocumentParser
from offline_anonymizer.parser.docx_parser import DocxParser
from offline_anonymizer.parser.markdown_parser import MarkdownParser
from offline_anonymizer.parser.txt_parser import TxtParser


class ParserFactory:
    _parsers: list[DocumentParser] = [
        DocxParser(),
        MarkdownParser(),
        TxtParser(),
    ]

    @classmethod
    def get_parser(cls, file_type_or_path: str | Path) -> DocumentParser:
        value = str(file_type_or_path).lower()
        extension = value if value.startswith(".") else Path(value).suffix.lower()
        if not extension:
            extension = f".{value}"

        for parser in cls._parsers:
            if extension in parser.supported_extensions:
                return parser

        raise ValueError(f"Unsupported document format: {file_type_or_path}")

    @classmethod
    def register(cls, parser: DocumentParser) -> None:
        cls._parsers.append(parser)
