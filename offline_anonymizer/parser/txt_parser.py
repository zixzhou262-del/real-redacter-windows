from __future__ import annotations

from pathlib import Path

from offline_anonymizer.core.document import Document, container_node, text_node
from offline_anonymizer.parser.base import DocumentParser


class TxtParser(DocumentParser):
    supported_extensions = {".txt"}

    def parse(self, path: str | Path) -> Document:
        source = Path(path)
        content = source.read_text(encoding="utf-8")
        paragraphs = split_paragraphs(content)
        children = [
            container_node(
                "paragraph",
                content=paragraph,
                children=[text_node(paragraph)],
                metadata={"parser": "txt"},
            )
            for paragraph in paragraphs
        ]
        return Document.create(source, "txt", children=children)


def split_paragraphs(content: str) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []

    for line in content.splitlines():
        if line.strip():
            current.append(line)
            continue
        if current:
            paragraphs.append("\n".join(current))
            current = []

    if current:
        paragraphs.append("\n".join(current))
    return paragraphs
