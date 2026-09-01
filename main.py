from __future__ import annotations

import argparse
import json
from pathlib import Path

from offline_anonymizer.batch import BatchProcessor
from offline_anonymizer.workflow import DocumentPipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline Reversible Document Anonymizer"
    )
    parser.add_argument("--config", help="Optional config JSON path")
    parser.add_argument("--output-dir", help="Optional output directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    anonymize = subparsers.add_parser("anonymize", help="Create masked document and mapping")
    anonymize.add_argument("input_file")
    anonymize.add_argument(
        "--format",
        help="Output format, e.g. docx md txt. Defaults to input file extension.",
    )

    recover = subparsers.add_parser("recover", help="Recover edited HTML into JSON model")
    recover.add_argument("html_file")
    recover.add_argument("mapping_file")
    recover.add_argument("--output", help="Recovered document JSON path")

    export = subparsers.add_parser("export", help="Export recovered JSON to a document")
    export.add_argument("document_json")
    export.add_argument("output_file")

    pipeline = subparsers.add_parser("pipeline", help="Run full single-file workflow")
    pipeline.add_argument("input_file")
    pipeline.add_argument(
        "--formats",
        nargs="+",
        help="Output formats, e.g. docx md txt. Defaults to config.",
    )

    batch = subparsers.add_parser("batch", help="Run batch workflow for a folder")
    batch.add_argument("input_directory")
    batch.add_argument("output_directory")
    batch.add_argument(
        "--formats",
        nargs="+",
        help="Output formats, e.g. docx md txt. Defaults to config.",
    )
    batch.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Max concurrent workers. Defaults to 1 for stability.",
    )

    args = parser.parse_args()
    if args.command == "batch":
        result = BatchProcessor(
            config_path=args.config,
            max_workers=args.workers,
        ).process_directory(
            args.input_directory,
            args.output_directory,
            args.formats,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return

    workflow = DocumentPipeline(config_path=args.config, output_dir=args.output_dir)

    if args.command == "anonymize":
        source = Path(args.input_file)
        output_format = (args.format or source.suffix.removeprefix(".") or "docx").removeprefix(".")
        result = workflow.anonymize_document(
            source,
            workflow.output_dir / f"{source.stem}已脱敏.{output_format}",
            workflow.output_dir / f"{source.stem}还原映射文件.json",
        )
    elif args.command == "recover":
        result = workflow.recover(args.html_file, args.mapping_file, args.output)
    elif args.command == "export":
        result = workflow.export(args.document_json, args.output_file)
    elif args.command == "pipeline":
        result = workflow.process(args.input_file, args.formats)
    else:
        parser.error(f"Unsupported command: {args.command}")
        return

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
