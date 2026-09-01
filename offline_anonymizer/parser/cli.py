from __future__ import annotations

import argparse
from pathlib import Path

from offline_anonymizer.parser.factory import ParserFactory


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a document into JSON DOM.")
    parser.add_argument("input", help="Input .docx, .md, or .txt file")
    parser.add_argument("output", help="Output document.json path")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    document = ParserFactory.get_parser(input_path).parse(input_path)
    output_path.write_text(document.to_json(), encoding="utf-8")


if __name__ == "__main__":
    main()
