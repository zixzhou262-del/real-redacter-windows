from __future__ import annotations

import argparse
import json
from pathlib import Path

from offline_anonymizer.recovery.recovery_engine import HtmlRecoveryEngine


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recover an edited HTML preview into a document model JSON."
    )
    parser.add_argument("html_input", help="Edited masked HTML file")
    parser.add_argument("mapping_input", help="Token mapping JSON file")
    parser.add_argument("document_output", help="Recovered document JSON path")
    parser.add_argument("report_output", help="Recovery report JSON path")
    args = parser.parse_args()

    result = HtmlRecoveryEngine().recover_files(args.html_input, args.mapping_input)
    Path(args.document_output).write_text(result.document.to_json(), encoding="utf-8")
    Path(args.report_output).write_text(
        json.dumps(result.report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
