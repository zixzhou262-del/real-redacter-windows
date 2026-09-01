from __future__ import annotations

import argparse
import json
from pathlib import Path

from offline_anonymizer.anonymizer.engine import AnonymizationEngine
from offline_anonymizer.anonymizer.token_registry import TokenRegistry
from offline_anonymizer.parser.factory import ParserFactory


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse and anonymize a document into JSON model files."
    )
    parser.add_argument("input", help="Input .docx, .md, or .txt file")
    parser.add_argument("document_output", help="Output anonymized document JSON path")
    parser.add_argument("mapping_output", help="Output token mapping JSON path")
    args = parser.parse_args()

    input_path = Path(args.input)
    document_output = Path(args.document_output)
    mapping_output = Path(args.mapping_output)

    document = ParserFactory.get_parser(input_path).parse(input_path)
    registry = TokenRegistry()
    anonymized = AnonymizationEngine(registry=registry).anonymize(document)

    document_output.write_text(anonymized.to_json(), encoding="utf-8")
    mapping_output.write_text(
        json.dumps(registry.export_mapping(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
