from __future__ import annotations

from pathlib import Path

from offline_anonymizer.core.document import Document, DocumentNode
from offline_anonymizer.exporter.base import DocumentExporter


class MarkdownExporter(DocumentExporter):
    supported_extensions = {".md", ".markdown"}

    def export(self, document: Document, path: str | Path) -> None:
        Path(path).write_text(render_markdown(document), encoding="utf-8")


def render_markdown(document: Document) -> str:
    return "\n\n".join(
        rendered
        for rendered in (_render_node(node) for node in document.blocks)
        if rendered != ""
    )


def _render_node(node: DocumentNode) -> str:
    if node.node_type == "heading":
        level = max(1, min(int(node.metadata.get("level", 1)), 6))
        return f"{'#' * level} {node.to_plain_text()}"
    if node.node_type == "paragraph":
        return node.to_plain_text()
    if node.node_type == "text":
        return node.content
    if node.node_type == "list":
        ordered = node.metadata.get("list_type") == "ordered"
        lines: list[str] = []
        for index, child in enumerate(node.children, start=1):
            marker = f"{index}." if ordered else "-"
            lines.append(f"{marker} {child.to_plain_text()}")
        return "\n".join(lines)
    if node.node_type == "list_item":
        return f"- {node.to_plain_text()}"
    if node.node_type == "table":
        return _render_table(node)
    if node.node_type == "code_block":
        language = node.metadata.get("language", "")
        return f"```{language}\n{node.content}\n```"
    if node.node_type == "blank_line":
        return ""
    return node.to_plain_text()


def _render_table(node: DocumentNode) -> str:
    rows = [
        [_cell_text(cell) for cell in row.children]
        for row in node.children
        if row.node_type == "table_row"
    ]
    if not rows:
        return ""

    column_count = max(len(row) for row in rows)
    normalized = [row + [""] * (column_count - len(row)) for row in rows]
    header = normalized[0]
    separator = ["---"] * column_count
    body = normalized[1:]

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(lines)


def _cell_text(node: DocumentNode) -> str:
    return node.to_plain_text().replace("\n", " ").strip()
