from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
import re
from typing import Any

from offline_anonymizer.core.document import Document, DocumentNode, container_node, text_node
from offline_anonymizer.docx_format import recover_docx_preserving_format
from offline_anonymizer.parser import ParserFactory
from offline_anonymizer.security.mapping_crypto import read_mapping


@dataclass
class RecoveryReport:
    restored_tokens: int = 0
    missing_token_ids: list[str] = field(default_factory=list)
    unused_token_ids: list[str] = field(default_factory=list)
    used_token_ids: dict[str, int] = field(default_factory=dict)

    @property
    def missing_tokens(self) -> int:
        return len(self.missing_token_ids)

    @property
    def unused_tokens(self) -> int:
        return len(self.unused_token_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "restored_tokens": self.restored_tokens,
            "missing_tokens": self.missing_tokens,
            "unused_tokens": self.unused_tokens,
            "missing_token_ids": self.missing_token_ids,
            "unused_token_ids": self.unused_token_ids,
            "used_token_ids": self.used_token_ids,
        }


@dataclass
class RecoveryResult:
    document: Document
    report: RecoveryReport


class HtmlRecoveryEngine:
    """Recover edited HTML by reading token_id anchors, never token labels."""

    def recover_files(
        self,
        html_path: str | Path,
        mapping_path: str | Path,
    ) -> RecoveryResult:
        html_file = Path(html_path)
        mapping = read_mapping(mapping_path)
        return self.recover_html(
            html_file.read_text(encoding="utf-8"),
            mapping,
            source_path=str(html_file),
        )

    def recover_html(
        self,
        html: str,
        mapping: dict[str, dict[str, Any]],
        source_path: str = "edited.html",
    ) -> RecoveryResult:
        parser = _TokenHTMLParser(mapping)
        parser.feed(html)
        parser.close()
        children = parser.to_nodes()
        report = parser.report
        used = set(report.used_token_ids)
        report.unused_token_ids = sorted(set(mapping) - used)
        document = Document.create(source_path, "html", children=children)
        return RecoveryResult(document=document, report=report)


class MaskedDocumentRecoveryEngine:
    """Recover edited masked documents by replacing visible token markers.

    Unlike HTML recovery, .docx/.md/.txt files do not currently carry hidden
    token_id anchors. This fallback uses the visible masked_value from mapping.
    """

    def recover_files(
        self,
        document_path: str | Path,
        mapping_path: str | Path,
        preserved_docx_path: str | Path | None = None,
    ) -> RecoveryResult:
        source = Path(document_path)
        mapping = read_mapping(mapping_path)
        if source.suffix.lower() == ".docx" and preserved_docx_path is not None:
            destination = Path(preserved_docx_path)
            stats = recover_docx_preserving_format(source, destination, mapping)
            document = ParserFactory.get_parser(destination).parse(destination)
            report = RecoveryReport(
                restored_tokens=stats.restored_tokens,
                missing_token_ids=stats.missing_token_ids,
                used_token_ids=stats.used_token_ids,
            )
            report.unused_token_ids = sorted(set(mapping) - set(report.used_token_ids))
            return RecoveryResult(document=document, report=report)

        document = ParserFactory.get_parser(source).parse(source)
        report = RecoveryReport()
        token_markers = _token_markers(mapping)
        _restore_node_from_markers(document.root, token_markers, report)
        used = set(report.used_token_ids)
        report.unused_token_ids = sorted(set(mapping) - used)
        return RecoveryResult(document=document, report=report)


def _token_markers(mapping: dict[str, dict[str, Any]]) -> list[tuple[str, str, str]]:
    markers: list[tuple[str, str, str]] = []
    for token_id, record in mapping.items():
        masked_value = str(record.get("masked_value") or record.get("masked") or "")
        original = str(record.get("original") or record.get("original_value") or "")
        if masked_value and original:
            markers.append((token_id, masked_value, original))
    return sorted(markers, key=lambda item: len(item[1]), reverse=True)


def _restore_node_from_markers(
    node: DocumentNode,
    markers: list[tuple[str, str, str]],
    report: RecoveryReport,
) -> None:
    if node.node_type == "text":
        node.content = _restore_text_from_markers(node.content, markers, report)
        node.tokens = []
        return
    if _is_plain_text_container(node):
        original = node.to_plain_text() or node.content
        restored = _restore_text_from_markers(original, markers, report)
        first_text = node.text_nodes()[0] if node.text_nodes() else None
        metadata = dict(first_text.metadata) if first_text is not None else {}
        node.content = restored
        node.children = [text_node(restored, metadata=metadata)] if restored else []
        node.tokens = []
        return
    for child in node.children:
        _restore_node_from_markers(child, markers, report)
    if node.children and node.node_type not in {"document", "table", "table_row"}:
        node.content = "".join(child.to_plain_text() for child in node.children)


def _is_plain_text_container(node: DocumentNode) -> bool:
    return (
        node.node_type in {"paragraph", "heading", "list_item", "code_block"}
        and bool(node.children)
        and all(child.node_type == "text" for child in node.children)
    )


def _restore_text_from_markers(
    value: str,
    markers: list[tuple[str, str, str]],
    report: RecoveryReport,
) -> str:
    restored = value
    for token_id, marker, original in markers:
        count = restored.count(marker)
        if count == 0:
            continue
        restored = restored.replace(marker, original)
        report.restored_tokens += count
        report.used_token_ids[token_id] = report.used_token_ids.get(token_id, 0) + count
    _record_unknown_markers(restored, {marker for _, marker, _ in markers}, report)
    return restored


def _record_unknown_markers(
    value: str,
    known_markers: set[str],
    report: RecoveryReport,
) -> None:
    for marker in re.findall(r"\[[^\[\]\s]{1,20}\d{3}\]", value):
        if marker in known_markers:
            continue
        if marker not in report.missing_token_ids:
            report.missing_token_ids.append(marker)


class _Frame:
    def __init__(
        self,
        node_type: str,
        tag: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.node_type = node_type
        self.tag = tag
        self.metadata = metadata or {}
        self.children: list[DocumentNode] = []
        self.parts: list[str] = []

    def add_text(self, value: str) -> None:
        self.parts.append(value)

    def content(self) -> str:
        return "".join(self.parts)

    def to_node(self) -> DocumentNode | None:
        content = self.content()
        if self.node_type == "root":
            return None
        if self.node_type in {"list", "table", "table_row"}:
            return container_node(
                self.node_type,
                children=self.children,
                metadata=self.metadata,
            )
        if self.node_type == "table_cell":
            if not self.children and content:
                self.children.append(
                    container_node(
                        "paragraph",
                        content=content,
                        children=[text_node(content)],
                    )
                )
            return container_node(
                "table_cell",
                content=content,
                children=self.children,
                metadata=self.metadata,
            )
        if self.node_type == "code_block":
            return container_node(
                "code_block",
                content=content,
                children=[text_node(content)],
                metadata=self.metadata,
            )
        return container_node(
            self.node_type,
            content=content,
            children=[text_node(content)] if content else [],
            metadata=self.metadata,
        )


class _TokenFrame:
    def __init__(self, token_id: str, token_type: str | None = None) -> None:
        self.token_id = token_id
        self.token_type = token_type
        self.parts: list[str] = []

    def add_text(self, value: str) -> None:
        self.parts.append(value)

    def fallback_label(self) -> str:
        return "".join(self.parts)


class _TokenHTMLParser(HTMLParser):
    _IGNORED_TAGS = {"head", "style", "script"}

    def __init__(self, mapping: dict[str, dict[str, Any]]) -> None:
        super().__init__(convert_charrefs=True)
        self.mapping = mapping
        self.report = RecoveryReport()
        self.frames: list[_Frame | _TokenFrame] = [_Frame("root")]
        self.ignore_depth = 0
        self.article_depth = 0
        self.found_surface = False
        self.capture_enabled = True

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag in self._IGNORED_TAGS:
            self.ignore_depth += 1
            return

        classes = set(attributes.get("class", "").split())
        if "document-surface" in classes:
            self.found_surface = True
            self.capture_enabled = True
            self.article_depth = 1
            self.frames = [_Frame("root")]
            return

        if self.found_surface:
            if self.article_depth <= 0:
                self.capture_enabled = False
                return
            self.article_depth += 1

        if not self._can_capture():
            return

        token_id = attributes.get("data-token-id")
        if token_id:
            self.frames.append(_TokenFrame(token_id, attributes.get("data-token-type")))
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.frames.append(
                _Frame("heading", tag, {"level": int(tag[1]), "source_tag": tag})
            )
        elif tag == "p":
            self.frames.append(_Frame("paragraph", tag))
        elif tag in {"ul", "ol"}:
            self.frames.append(
                _Frame(
                    "list",
                    tag,
                    {"list_type": "ordered" if tag == "ol" else "bullet"},
                )
            )
        elif tag == "li":
            self.frames.append(_Frame("list_item", tag))
        elif tag == "table":
            self.frames.append(_Frame("table", tag))
        elif tag == "tr":
            self.frames.append(_Frame("table_row", tag))
        elif tag in {"td", "th"}:
            self.frames.append(_Frame("table_cell", tag))
        elif tag == "pre":
            self.frames.append(_Frame("code_block", tag))
        elif tag == "br":
            self._current().add_text("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._IGNORED_TAGS:
            self.ignore_depth = max(0, self.ignore_depth - 1)
            return

        if self.found_surface:
            if self.article_depth <= 0:
                return
            self.article_depth -= 1

        if not self._can_capture() and not self.frames:
            return

        if tag == "span" and isinstance(self._current(), _TokenFrame):
            token_frame = self.frames.pop()
            assert isinstance(token_frame, _TokenFrame)
            self._current().add_text(self._restore_token(token_frame))
            return

        expected = {
            "h1": "heading",
            "h2": "heading",
            "h3": "heading",
            "h4": "heading",
            "h5": "heading",
            "h6": "heading",
            "p": "paragraph",
            "ul": "list",
            "ol": "list",
            "li": "list_item",
            "table": "table",
            "tr": "table_row",
            "td": "table_cell",
            "th": "table_cell",
            "pre": "code_block",
        }.get(tag)
        if expected is None:
            return
        self._close_frame(expected)

    def handle_data(self, data: str) -> None:
        if not self._can_capture():
            return
        if isinstance(self._current(), _Frame) and self._current().node_type in {
            "root",
            "list",
            "table",
            "table_row",
        }:
            if not data.strip():
                return
        self._current().add_text(data)

    def to_nodes(self) -> list[DocumentNode]:
        root = self.frames[0]
        assert isinstance(root, _Frame)
        content = root.content().strip()
        if content:
            root.children.append(
                container_node("paragraph", content=content, children=[text_node(content)])
            )
            root.parts = []
        return root.children

    def _restore_token(self, frame: _TokenFrame) -> str:
        record = self.mapping.get(frame.token_id)
        if record is None:
            if frame.token_id not in self.report.missing_token_ids:
                self.report.missing_token_ids.append(frame.token_id)
            return frame.fallback_label()
        self.report.restored_tokens += 1
        self.report.used_token_ids[frame.token_id] = (
            self.report.used_token_ids.get(frame.token_id, 0) + 1
        )
        return str(record.get("original") or record.get("original_value") or "")

    def _close_frame(self, expected_node_type: str) -> None:
        if len(self.frames) <= 1:
            return
        frame = self.frames.pop()
        if not isinstance(frame, _Frame) or frame.node_type != expected_node_type:
            return
        node = frame.to_node()
        if node is None:
            return
        parent = self._current()
        if isinstance(parent, _Frame) and parent.node_type in {
            "root",
            "list",
            "table",
            "table_row",
            "table_cell",
        }:
            parent.children.append(node)
            return
        parent.add_text(node.to_plain_text())

    def _can_capture(self) -> bool:
        return self.ignore_depth == 0 and self.capture_enabled

    def _current(self) -> _Frame | _TokenFrame:
        return self.frames[-1]
