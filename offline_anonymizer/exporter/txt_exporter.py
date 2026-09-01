from __future__ import annotations

from pathlib import Path

from offline_anonymizer.core.document import Document, DocumentNode
from offline_anonymizer.exporter.base import DocumentExporter


class TxtExporter(DocumentExporter):
    supported_extensions = {".txt"}

    def export(self, document: Document, path: str | Path) -> None:
        Path(path).write_text(render_txt(document), encoding="utf-8")


def render_txt(document: Document) -> str:
    return "\n\n".join(
        rendered
        for rendered in (_render_node(node) for node in document.blocks)
        if rendered != ""
    )


def _render_node(node: DocumentNode) -> str:
    if node.node_type in {"heading", "paragraph", "text", "code_block"}:
        return node.to_plain_text()
    if node.node_type == "list":
        return "\n".join(_render_node(child) for child in node.children)
    if node.node_type == "list_item":
        return f"- {node.to_plain_text()}"
    if node.node_type == "table":
        return "\n".join(_render_node(child) for child in node.children)
    if node.node_type == "table_row":
        return "\t".join(_render_node(child) for child in node.children)
    if node.node_type == "table_cell":
        return node.to_plain_text()
    if node.node_type == "blank_line":
        return ""
    return node.to_plain_text()
