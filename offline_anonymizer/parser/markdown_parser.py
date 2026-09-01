from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from offline_anonymizer.core.document import Document, DocumentNode, container_node, text_node
from offline_anonymizer.parser.base import DocumentParser


class MarkdownParser(DocumentParser):
    supported_extensions = {".md", ".markdown"}

    def parse(self, path: str | Path) -> Document:
        source = Path(path)
        content = source.read_text(encoding="utf-8")
        children = parse_markdown(content)
        return Document.create(source, "md", children=children)


def parse_markdown(content: str) -> list[DocumentNode]:
    markdown_it = _load_markdown_it()
    if markdown_it is not None:
        return _parse_with_markdown_it(content, markdown_it)
    return _parse_with_fallback(content)


def _load_markdown_it() -> Any | None:
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        return None
    return MarkdownIt("commonmark").enable("table")


def _parse_with_markdown_it(content: str, markdown_it: Any) -> list[DocumentNode]:
    tokens = markdown_it.parse(content)
    nodes: list[DocumentNode] = []
    index = 0

    while index < len(tokens):
        token = tokens[index]
        if token.type == "heading_open":
            inline = tokens[index + 1]
            level = int(token.tag[1])
            nodes.append(_heading(inline.content, level, {"parser": "markdown-it-py"}))
            index += 3
            continue
        if token.type == "paragraph_open":
            inline = tokens[index + 1]
            nodes.append(_paragraph(inline.content, {"parser": "markdown-it-py"}))
            index += 3
            continue
        if token.type == "bullet_list_open":
            list_node, index = _consume_markdown_it_list(tokens, index, "bullet")
            nodes.append(list_node)
            continue
        if token.type == "ordered_list_open":
            list_node, index = _consume_markdown_it_list(tokens, index, "ordered")
            nodes.append(list_node)
            continue
        if token.type == "fence":
            nodes.append(
                container_node(
                    "code_block",
                    content=token.content.rstrip("\n"),
                    children=[text_node(token.content.rstrip("\n"))],
                    metadata={
                        "language": token.info.strip(),
                        "parser": "markdown-it-py",
                    },
                )
            )
            index += 1
            continue
        if token.type == "table_open":
            table_node, index = _consume_markdown_it_table(tokens, index)
            nodes.append(table_node)
            continue
        index += 1

    return nodes


def _consume_markdown_it_list(
    tokens: list[Any], start: int, list_type: str
) -> tuple[DocumentNode, int]:
    items: list[DocumentNode] = []
    index = start + 1
    while index < len(tokens) and tokens[index].type != f"{'bullet' if list_type == 'bullet' else 'ordered'}_list_close":
        if tokens[index].type == "list_item_open":
            parts: list[str] = []
            index += 1
            while index < len(tokens) and tokens[index].type != "list_item_close":
                if tokens[index].type == "inline":
                    parts.append(tokens[index].content)
                index += 1
            item_content = "\n".join(parts)
            items.append(
                container_node(
                    "list_item",
                    content=item_content,
                    children=[text_node(item_content)],
                )
            )
        index += 1
    return (
        container_node(
            "list",
            children=items,
            metadata={"list_type": list_type, "parser": "markdown-it-py"},
        ),
        index + 1,
    )


def _consume_markdown_it_table(tokens: list[Any], start: int) -> tuple[DocumentNode, int]:
    rows: list[DocumentNode] = []
    index = start + 1
    current_cells: list[DocumentNode] = []
    while index < len(tokens) and tokens[index].type != "table_close":
        token = tokens[index]
        if token.type in {"tr_open"}:
            current_cells = []
        elif token.type in {"th_open", "td_open"}:
            inline = tokens[index + 1]
            cell_text = inline.content
            current_cells.append(
                container_node(
                    "table_cell",
                    content=cell_text,
                    children=[_paragraph(cell_text, {"parser": "markdown-it-py"})],
                )
            )
        elif token.type == "tr_close":
            rows.append(container_node("table_row", children=current_cells))
        index += 1
    return (
        container_node("table", children=rows, metadata={"parser": "markdown-it-py"}),
        index + 1,
    )


def _parse_with_fallback(content: str) -> list[DocumentNode]:
    nodes: list[DocumentNode] = []
    lines = content.splitlines()
    index = 0

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        fence_match = re.match(r"^```(.*)$", line.strip())
        if fence_match:
            language = fence_match.group(1).strip()
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            code = "\n".join(code_lines)
            nodes.append(
                container_node(
                    "code_block",
                    content=code,
                    children=[text_node(code)],
                    metadata={"language": language, "parser": "fallback"},
                )
            )
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            nodes.append(_heading(heading_match.group(2).strip(), level, {"parser": "fallback"}))
            index += 1
            continue

        if _is_table_start(lines, index):
            table_node, index = _consume_fallback_table(lines, index)
            nodes.append(table_node)
            continue

        list_match = re.match(r"^\s*(?:[-*+]\s+|\d+\.\s+)(.+)$", line)
        if list_match:
            list_node, index = _consume_fallback_list(lines, index)
            nodes.append(list_node)
            continue

        paragraph_lines = [line.strip()]
        index += 1
        while index < len(lines) and lines[index].strip():
            if re.match(r"^(#{1,6})\s+|^\s*(?:[-*+]\s+|\d+\.\s+)|^```", lines[index]):
                break
            if _is_table_start(lines, index):
                break
            paragraph_lines.append(lines[index].strip())
            index += 1
        paragraph = " ".join(paragraph_lines)
        nodes.append(_paragraph(paragraph, {"parser": "fallback"}))

    return nodes


def _consume_fallback_list(lines: list[str], start: int) -> tuple[DocumentNode, int]:
    items: list[DocumentNode] = []
    index = start
    list_type = "ordered" if re.match(r"^\s*\d+\.\s+", lines[index]) else "bullet"
    pattern = r"^\s*(?:[-*+]\s+|\d+\.\s+)(.+)$"

    while index < len(lines):
        match = re.match(pattern, lines[index])
        if not match:
            break
        content = match.group(1).strip()
        items.append(
            container_node(
                "list_item",
                content=content,
                children=[text_node(content)],
                metadata={"parser": "fallback"},
            )
        )
        index += 1

    return (
        container_node(
            "list",
            children=items,
            metadata={"list_type": list_type, "parser": "fallback"},
        ),
        index,
    )


def _consume_fallback_table(lines: list[str], start: int) -> tuple[DocumentNode, int]:
    rows: list[DocumentNode] = []
    index = start
    while index < len(lines) and "|" in lines[index] and lines[index].strip():
        if re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[index]):
            index += 1
            continue
        cells = [
            cell.strip()
            for cell in lines[index].strip().strip("|").split("|")
        ]
        rows.append(
            container_node(
                "table_row",
                children=[
                    container_node(
                        "table_cell",
                        content=cell,
                        children=[_paragraph(cell, {"parser": "fallback"})],
                    )
                    for cell in cells
                ],
            )
        )
        index += 1
    return container_node("table", children=rows, metadata={"parser": "fallback"}), index


def _is_table_start(lines: list[str], index: int) -> bool:
    return (
        index + 1 < len(lines)
        and "|" in lines[index]
        and re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[index + 1])
        is not None
    )


def _heading(content: str, level: int, metadata: dict[str, Any]) -> DocumentNode:
    return container_node(
        "heading",
        content=content,
        children=[text_node(content)],
        metadata={"level": level, **metadata},
    )


def _paragraph(content: str, metadata: dict[str, Any]) -> DocumentNode:
    return container_node(
        "paragraph",
        content=content,
        children=[text_node(content)],
        metadata=metadata,
    )
