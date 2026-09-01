from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from offline_anonymizer.core.document import Document, DocumentNode, container_node, text_node
from offline_anonymizer.parser.base import DocumentParser


class DocxParser(DocumentParser):
    supported_extensions = {".docx"}

    def parse(self, path: str | Path) -> Document:
        try:
            from docx import Document as DocxDocument
        except ImportError as exc:
            raise RuntimeError("python-docx is required to parse .docx files") from exc

        source = Path(path)
        docx_document = DocxDocument(str(source))
        children: list[DocumentNode] = []

        for block in iter_docx_blocks(docx_document):
            if block.__class__.__name__ == "Paragraph":
                node = paragraph_to_node(block)
                if node is not None:
                    children.append(node)
            elif block.__class__.__name__ == "Table":
                children.append(table_to_node(block))

        return Document.create(source, "docx", children=children)


def iter_docx_blocks(docx_document: Any) -> Iterator[Any]:
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    body = docx_document.element.body
    for child in body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, docx_document)
        elif child.tag.endswith("}tbl"):
            yield Table(child, docx_document)


def paragraph_to_node(paragraph: Any) -> DocumentNode | None:
    content = _paragraph_text(paragraph)
    if not content.strip():
        return None

    style_name = _style_name(paragraph)
    node_type = "heading" if _is_heading(style_name) else "paragraph"
    metadata: dict[str, Any] = {
        "style": style_name,
        "parser": "python-docx",
    }

    if node_type == "heading":
        metadata["level"] = _heading_level(style_name)
    if _is_list(paragraph, style_name):
        node_type = "list"
        metadata["list_type"] = _list_type(style_name)
        item = container_node(
            "list_item",
            content=content,
            children=run_text_nodes(paragraph),
            metadata={"style": style_name, "parser": "python-docx"},
        )
        return container_node(node_type, children=[item], metadata=metadata)

    return container_node(
        node_type,
        content=content,
        children=run_text_nodes(paragraph),
        metadata=metadata,
    )


def run_text_nodes(paragraph: Any) -> list[DocumentNode]:
    nodes: list[DocumentNode] = []
    for run in paragraph.runs:
        run_text = _run_text(run)
        if not run_text:
            continue
        font_metadata = _font_metadata(run)
        nodes.append(
            text_node(
                run_text,
                metadata={
                    "bold": _format_flag(run, "bold"),
                    "italic": _format_flag(run, "italic"),
                    "underline": _format_flag(run, "underline"),
                    "style": _style_name(run) or None,
                    **font_metadata,
                },
            )
        )
    fallback_text = _paragraph_text(paragraph)
    if not nodes and fallback_text:
        nodes.append(text_node(fallback_text))
    return nodes


def table_to_node(table: Any) -> DocumentNode:
    row_nodes: list[DocumentNode] = []
    for row in table.rows:
        cell_nodes: list[DocumentNode] = []
        for cell in row.cells:
            cell_blocks = [paragraph_to_node(paragraph) for paragraph in cell.paragraphs]
            cell_children = [node for node in cell_blocks if node is not None]
            cell_content = "\n".join(node.content for node in cell_children)
            cell_nodes.append(
                container_node(
                    "table_cell",
                    content=cell_content,
                    children=cell_children,
                    metadata={"parser": "python-docx"},
                )
            )
        row_nodes.append(container_node("table_row", children=cell_nodes))
    return container_node("table", children=row_nodes, metadata={"parser": "python-docx"})


def _is_heading(style_name: str) -> bool:
    normalized = style_name.lower()
    return normalized.startswith("heading") or style_name.startswith("标题")


def _heading_level(style_name: str) -> int:
    digits = "".join(character for character in style_name if character.isdigit())
    return int(digits) if digits else 1


def _is_list(paragraph: Any, style_name: str) -> bool:
    normalized = style_name.lower()
    if "list" in normalized or "列表" in style_name:
        return True
    try:
        paragraph_properties = paragraph._p.pPr
        return paragraph_properties is not None and paragraph_properties.numPr is not None
    except Exception:
        return False


def _list_type(style_name: str) -> str:
    normalized = style_name.lower()
    if "number" in normalized or "编号" in style_name:
        return "ordered"
    return "bullet"


def _paragraph_text(paragraph: Any) -> str:
    try:
        return paragraph.text or ""
    except Exception:
        parts = [_run_text(run) for run in getattr(paragraph, "runs", [])]
        return "".join(parts)


def _run_text(run: Any) -> str:
    try:
        return run.text or ""
    except Exception:
        try:
            return "".join(run._element.itertext())
        except Exception:
            return ""


def _style_name(value: Any) -> str:
    try:
        style = value.style
        name = style.name if style is not None else ""
        return name if isinstance(name, str) else str(name or "")
    except Exception:
        return ""


def _format_flag(run: Any, attribute: str) -> bool:
    try:
        return bool(getattr(run, attribute))
    except Exception:
        return False


def _font_metadata(run: Any) -> dict[str, str]:
    names: dict[str, str] = {}
    try:
        direct_name = _valid_font_name(run.font.name)
        if direct_name:
            names["font_name"] = direct_name
    except Exception:
        pass

    try:
        from docx.oxml.ns import qn

        properties = run._element.rPr
        fonts = properties.rFonts if properties is not None else None
        if fonts is None:
            return names
        latin = _valid_font_name(
            fonts.get(qn("w:ascii")) or fonts.get(qn("w:hAnsi"))
        )
        east_asia = _valid_font_name(fonts.get(qn("w:eastAsia")))
        if latin:
            names["font_name"] = latin
        if east_asia:
            names["font_east_asia"] = east_asia
    except Exception:
        pass
    return names


def _valid_font_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = "".join(character for character in value.strip() if ord(character) >= 32)
    if not cleaned or len(cleaned) > 128:
        return None
    return cleaned
