from __future__ import annotations

import argparse
from pathlib import Path

from offline_anonymizer.anonymizer.engine import AnonymizationEngine
from offline_anonymizer.anonymizer.token_registry import TokenRegistry
from offline_anonymizer.parser.factory import ParserFactory
from offline_anonymizer.renderer.html_renderer import HtmlRenderer


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render an anonymized local HTML preview from a document."
    )
    parser.add_argument("input", help="Input .docx, .md, or .txt file")
    parser.add_argument("html_output", help="Output masked HTML preview path")
    parser.add_argument("mapping_output", help="Output token mapping JSON path")
    args = parser.parse_args()

    input_path = Path(args.input)
    html_output = Path(args.html_output)
    mapping_output = Path(args.mapping_output)

    document = ParserFactory.get_parser(input_path).parse(input_path)
    registry = TokenRegistry()
    anonymized = AnonymizationEngine(registry=registry).anonymize(document)
    HtmlRenderer().write(anonymized, registry, html_output, mapping_output)


if __name__ == "__main__":
    main()
