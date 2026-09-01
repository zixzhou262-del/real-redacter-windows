from __future__ import annotations

import argparse
from pathlib import Path

from offline_anonymizer.core.document import Document
from offline_anonymizer.exporter.factory import ExporterFactory


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a document model JSON to .docx, .md, or .txt."
    )
    parser.add_argument("document_json", help="Recovered document model JSON")
    parser.add_argument("output", help="Output .docx, .md, or .txt path")
    args = parser.parse_args()

    document = Document.from_json(Path(args.document_json).read_text(encoding="utf-8"))
    ExporterFactory.get_exporter(args.output).export(document, args.output)


if __name__ == "__main__":
    main()
