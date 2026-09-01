from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


SUPPORTED_NODE_TYPES = {
    "document",
    "heading",
    "paragraph",
    "text",
    "list",
    "list_item",
    "table",
    "table_row",
    "table_cell",
    "code_block",
    "blank_line",
}


def new_node_id(prefix: str = "node") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class TokenSpan:
    token_id: str
    start: int
    end: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "start": self.start,
            "end": self.end,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenSpan":
        return cls(
            token_id=data["token_id"],
            start=int(data["start"]),
            end=int(data["end"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DocumentNode:
    node_id: str
    node_type: str
    content: str = ""
    children: list["DocumentNode"] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    tokens: list[TokenSpan] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.node_type not in SUPPORTED_NODE_TYPES:
            raise ValueError(f"Unsupported document node type: {self.node_type}")

    @classmethod
    def create(
        cls,
        node_type: str,
        content: str = "",
        children: list["DocumentNode"] | None = None,
        metadata: dict[str, Any] | None = None,
        tokens: list[TokenSpan] | None = None,
        node_id: str | None = None,
    ) -> "DocumentNode":
        return cls(
            node_id=node_id or new_node_id(node_type),
            node_type=node_type,
            content=content,
            children=children or [],
            metadata=metadata or {},
            tokens=tokens or [],
        )

    def add_child(self, child: "DocumentNode") -> None:
        self.children.append(child)

    def text_nodes(self) -> list["DocumentNode"]:
        nodes: list[DocumentNode] = []
        if self.node_type == "text":
            nodes.append(self)
        for child in self.children:
            nodes.extend(child.text_nodes())
        return nodes

    def to_plain_text(self) -> str:
        if self.node_type in {"text", "code_block"}:
            return self.content
        if self.node_type == "table_row":
            return "\t".join(child.to_plain_text() for child in self.children)
        if self.node_type == "table":
            return "\n".join(child.to_plain_text() for child in self.children)
        if self.children:
            separator = "\n" if self.node_type in {"document", "list"} else ""
            return separator.join(child.to_plain_text() for child in self.children)
        return self.content

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "content": self.content,
            "children": [child.to_dict() for child in self.children],
            "metadata": self.metadata,
            "tokens": [token.to_dict() for token in self.tokens],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentNode":
        return cls(
            node_id=data["node_id"],
            node_type=data["node_type"],
            content=data.get("content", ""),
            children=[
                cls.from_dict(child) for child in data.get("children", [])
            ],
            metadata=data.get("metadata", {}),
            tokens=[
                TokenSpan.from_dict(token) for token in data.get("tokens", [])
            ],
        )


@dataclass
class Document:
    document_id: str
    source_path: str
    source_format: str
    root: DocumentNode
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        source_path: str | Path,
        source_format: str,
        children: list[DocumentNode] | None = None,
        document_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Document":
        path = Path(source_path)
        return cls(
            document_id=document_id or new_node_id("doc"),
            source_path=str(path),
            source_format=source_format,
            root=DocumentNode.create(
                "document",
                children=children or [],
                metadata={"source_name": path.name},
            ),
            metadata=metadata or {},
        )

    @property
    def id(self) -> str:
        return self.document_id

    @property
    def blocks(self) -> list[DocumentNode]:
        return self.root.children

    def add_child(self, node: DocumentNode) -> None:
        self.root.add_child(node)

    def find_by_type(self, node_type: str) -> list[DocumentNode]:
        found: list[DocumentNode] = []

        def visit(node: DocumentNode) -> None:
            if node.node_type == node_type:
                found.append(node)
            for child in node.children:
                visit(child)

        visit(self.root)
        return found

    def text_nodes(self) -> list[DocumentNode]:
        return self.root.text_nodes()

    def to_plain_text(self) -> str:
        return self.root.to_plain_text()

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "source_path": self.source_path,
            "source_format": self.source_format,
            "root": self.root.to_dict(),
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        return cls(
            document_id=data["document_id"],
            source_path=data.get("source_path", ""),
            source_format=data.get("source_format", ""),
            root=DocumentNode.from_dict(data["root"]),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, value: str) -> "Document":
        return cls.from_dict(json.loads(value))


def text_node(content: str, metadata: dict[str, Any] | None = None) -> DocumentNode:
    return DocumentNode.create("text", content=content, metadata=metadata)


def container_node(
    node_type: str,
    content: str = "",
    children: list[DocumentNode] | None = None,
    metadata: dict[str, Any] | None = None,
) -> DocumentNode:
    return DocumentNode.create(
        node_type,
        content=content,
        children=children,
        metadata=metadata,
    )


# Compatibility aliases for the Phase 1 skeleton. New code should use DocumentNode.
Block = DocumentNode
Inline = DocumentNode
TableRow = DocumentNode
TableCell = DocumentNode
