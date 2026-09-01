from __future__ import annotations

from copy import deepcopy

from offline_anonymizer.anonymizer.detector import Detection, Detector, default_detectors
from offline_anonymizer.anonymizer.token_registry import TokenRegistry
from offline_anonymizer.core.document import Document, DocumentNode, TokenSpan, text_node


class AnonymizationEngine:
    def __init__(
        self,
        detectors: list[Detector] | None = None,
        registry: TokenRegistry | None = None,
    ) -> None:
        self.detectors = detectors or default_detectors()
        self.registry = registry or TokenRegistry()

    def anonymize(self, document: Document) -> Document:
        anonymized = deepcopy(document)
        self._anonymize_node(anonymized.root, anonymized.document_id, inside_code=False)
        return anonymized

    def detect(self, text: str) -> list[Detection]:
        detections: list[Detection] = []
        for detector in self.detectors:
            detections.extend(detector.detect(text))
        return resolve_conflicts(detections)

    def anonymize_text(
        self,
        text: str,
        document_id: str,
        node_id: str,
    ) -> tuple[str, list[TokenSpan]]:
        """Mask one logical text surface without changing its surrounding format."""
        detections = self.detect(text)
        if not detections:
            return text, []

        parts: list[str] = []
        spans: list[TokenSpan] = []
        cursor = 0

        for detection in detections:
            if detection.start < cursor:
                continue
            parts.append(text[cursor : detection.start])
            token = self.registry.get_or_create_token(
                detection.type,
                detection.value,
                metadata={
                    "detector": detection.detector,
                    **detection.metadata,
                },
            )
            masked_start = sum(len(part) for part in parts)
            parts.append(token.masked_value)
            masked_end = masked_start + len(token.masked_value)
            spans.append(
                TokenSpan(
                    token_id=token.token_id,
                    start=masked_start,
                    end=masked_end,
                    metadata={
                        "token_type": token.token_type,
                        "masked_value": token.masked_value,
                        "original_value": token.original_value,
                        "original_start": detection.start,
                        "original_end": detection.end,
                        "detector": detection.detector,
                    },
                )
            )
            self.registry.record_occurrence(
                token.token_id,
                document_id=document_id,
                node_id=node_id,
                original_start=detection.start,
                original_end=detection.end,
                masked_start=masked_start,
                masked_end=masked_end,
            )
            cursor = detection.end

        parts.append(text[cursor:])
        return "".join(parts), spans

    def _anonymize_node(
        self, node: DocumentNode, document_id: str, inside_code: bool
    ) -> None:
        current_inside_code = inside_code or node.node_type == "code_block"

        if node.node_type == "text" and not current_inside_code:
            self._anonymize_text_node(node, document_id)
            return
        if not current_inside_code and _is_plain_text_container(node):
            self._anonymize_text_container(node, document_id)
            return

        for child in node.children:
            self._anonymize_node(child, document_id, current_inside_code)

        if node.children and node.node_type not in {"document", "table", "table_row"}:
            node.content = "".join(child.to_plain_text() for child in node.children)

    def _anonymize_text_node(self, node: DocumentNode, document_id: str) -> None:
        masked, spans = self.anonymize_text(
            node.content,
            document_id=document_id,
            node_id=node.node_id,
        )
        if not spans:
            return
        node.content = masked
        node.tokens = spans

    def _anonymize_text_container(
        self,
        node: DocumentNode,
        document_id: str,
    ) -> None:
        first_text = node.text_nodes()[0] if node.text_nodes() else None
        metadata = dict(first_text.metadata) if first_text is not None else {}
        merged = node.to_plain_text() or node.content
        if not self.detect(merged):
            return
        merged_node = text_node(merged, metadata=metadata)
        self._anonymize_text_node(merged_node, document_id)
        node.content = merged_node.content
        node.children = [merged_node] if merged_node.content else []


def resolve_conflicts(detections: list[Detection]) -> list[Detection]:
    selected: list[Detection] = []
    for detection in sorted(
        detections,
        key=lambda item: (item.start, -item.priority, -(item.end - item.start)),
    ):
        if not any(detection.overlaps(existing) for existing in selected):
            selected.append(detection)
            continue

        better_selected: list[Detection] = []
        should_add = True
        for existing in selected:
            if not detection.overlaps(existing):
                better_selected.append(existing)
                continue
            if _is_better(detection, existing):
                continue
            should_add = False
            better_selected.append(existing)
        if should_add:
            better_selected.append(detection)
        selected = better_selected

    return sorted(selected, key=lambda item: item.start)


def _is_better(candidate: Detection, existing: Detection) -> bool:
    if candidate.priority != existing.priority:
        return candidate.priority > existing.priority
    return (candidate.end - candidate.start) > (existing.end - existing.start)


def _is_plain_text_container(node: DocumentNode) -> bool:
    return (
        node.node_type in {"paragraph", "heading", "list_item"}
        and bool(node.children)
        and all(child.node_type == "text" for child in node.children)
    )
