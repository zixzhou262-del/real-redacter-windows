from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import tempfile
from typing import Any, Callable
from zipfile import ZIP_DEFLATED, ZipFile

from offline_anonymizer.anonymizer.engine import AnonymizationEngine


WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WORD_PARAGRAPH = f"{{{WORD_NAMESPACE}}}p"
WORD_TEXT = f"{{{WORD_NAMESPACE}}}t"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


@dataclass
class DocxRecoveryStats:
    restored_tokens: int = 0
    missing_token_ids: list[str] = field(default_factory=list)
    used_token_ids: dict[str, int] = field(default_factory=dict)


def anonymize_docx_preserving_format(
    source: str | Path,
    destination: str | Path,
    engine: AnonymizationEngine,
) -> int:
    """Mask text inside the original OOXML package without rebuilding Word styles."""
    source_path = Path(source)
    document_id = f"docx:{source_path.resolve()}"
    occurrence_count = 0

    def transform(root: Any, part_name: str) -> None:
        nonlocal occurrence_count
        for paragraph_index, paragraph in enumerate(root.iter(WORD_PARAGRAPH)):
            text_elements = list(paragraph.iter(WORD_TEXT))
            original = "".join(element.text or "" for element in text_elements)
            if not original:
                continue
            detections = engine.detect(original)
            if not detections:
                continue
            node_id = f"{part_name}:paragraph:{paragraph_index}"
            prepared = []
            for detection in detections:
                token = engine.registry.get_or_create_token(
                    detection.type,
                    detection.value,
                    metadata={
                        "detector": detection.detector,
                        **detection.metadata,
                    },
                )
                prepared.append((detection, token))

            for detection, token in reversed(prepared):
                _replace_span(
                    text_elements,
                    detection.start,
                    detection.end,
                    token.masked_value,
                )

            length_delta = 0
            for detection, token in prepared:
                masked_start = detection.start + length_delta
                masked_end = masked_start + len(token.masked_value)
                engine.registry.record_occurrence(
                    token.token_id,
                    document_id=document_id,
                    node_id=node_id,
                    original_start=detection.start,
                    original_end=detection.end,
                    masked_start=masked_start,
                    masked_end=masked_end,
                )
                length_delta += len(token.masked_value) - (
                    detection.end - detection.start
                )
                occurrence_count += 1

    _rewrite_docx_package(source_path, Path(destination), transform)
    return occurrence_count


def recover_docx_preserving_format(
    source: str | Path,
    destination: str | Path,
    mapping: dict[str, dict[str, Any]],
) -> DocxRecoveryStats:
    """Restore visible token markers while retaining the edited DOCX package."""
    stats = DocxRecoveryStats()
    marker_records = _marker_records(mapping)
    marker_pattern = _marker_pattern(marker_records)
    known_markers = set(marker_records)

    def transform(root: Any, _part_name: str) -> None:
        for paragraph in root.iter(WORD_PARAGRAPH):
            text_elements = list(paragraph.iter(WORD_TEXT))
            value = "".join(element.text or "" for element in text_elements)
            if not value:
                continue
            matches = list(marker_pattern.finditer(value)) if marker_pattern else []
            for match in reversed(matches):
                marker = match.group(0)
                token_id, original = marker_records[marker]
                _replace_span(text_elements, match.start(), match.end(), original)
                stats.restored_tokens += 1
                stats.used_token_ids[token_id] = stats.used_token_ids.get(token_id, 0) + 1

            remaining = "".join(element.text or "" for element in text_elements)
            for marker in re.findall(r"\[[^\[\]\s]{1,20}\d{3}\]", remaining):
                if marker in known_markers or marker in stats.missing_token_ids:
                    continue
                stats.missing_token_ids.append(marker)

    _rewrite_docx_package(Path(source), Path(destination), transform)
    return stats


def _rewrite_docx_package(
    source: Path,
    destination: Path,
    transform: Callable[[Any, str], None],
) -> None:
    try:
        from lxml import etree
    except ImportError as exc:
        raise RuntimeError("lxml is required to preserve DOCX formatting") from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.NamedTemporaryFile(
        prefix=f".{destination.stem}-",
        suffix=".docx",
        dir=destination.parent,
        delete=False,
    )
    temporary_path = Path(temporary.name)
    temporary.close()
    try:
        with ZipFile(source, "r") as source_zip, ZipFile(
            temporary_path,
            "w",
            compression=ZIP_DEFLATED,
        ) as destination_zip:
            for info in source_zip.infolist():
                payload = source_zip.read(info.filename)
                if _is_editable_word_part(info.filename):
                    parser = etree.XMLParser(
                        remove_blank_text=False,
                        resolve_entities=False,
                        huge_tree=True,
                    )
                    root = etree.fromstring(payload, parser=parser)
                    transform(root, info.filename)
                    payload = etree.tostring(
                        root,
                        encoding="UTF-8",
                        xml_declaration=True,
                        standalone=True,
                    )
                destination_zip.writestr(info, payload)
        temporary_path.replace(destination)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _is_editable_word_part(name: str) -> bool:
    if name in {
        "word/document.xml",
        "word/footnotes.xml",
        "word/endnotes.xml",
        "word/comments.xml",
        "word/glossary/document.xml",
    }:
        return True
    return bool(re.fullmatch(r"word/(?:header|footer)\d+\.xml", name))


def _marker_records(
    mapping: dict[str, dict[str, Any]],
) -> dict[str, tuple[str, str]]:
    records: dict[str, tuple[str, str]] = {}
    for token_id, record in mapping.items():
        if not isinstance(record, dict):
            continue
        marker = str(record.get("masked_value") or record.get("masked") or "")
        original = str(record.get("original") or record.get("original_value") or "")
        if marker and original:
            records[marker] = (token_id, original)
    return records


def _marker_pattern(records: dict[str, tuple[str, str]]) -> re.Pattern[str] | None:
    if not records:
        return None
    alternatives = sorted(records, key=len, reverse=True)
    return re.compile("|".join(re.escape(marker) for marker in alternatives))


def _replace_span(
    elements: list[Any],
    start: int,
    end: int,
    replacement: str,
) -> None:
    if start < 0 or end <= start:
        return

    positions: list[tuple[Any, str, int, int]] = []
    cursor = 0
    for element in elements:
        value = element.text or ""
        positions.append((element, value, cursor, cursor + len(value)))
        cursor += len(value)

    touched = [
        item
        for item in positions
        if item[3] > start and item[2] < end
    ]
    if not touched:
        return

    overlap_lengths = [
        min(item[3], end) - max(item[2], start)
        for item in touched
    ]
    chunks = _split_replacement(replacement, overlap_lengths)
    first = touched[0]
    last = touched[-1]
    prefix = first[1][: max(0, start - first[2])]
    suffix = last[1][max(0, end - last[2]) :]

    for index, (element, _value, _segment_start, _segment_end) in enumerate(touched):
        value = chunks[index]
        if index == 0:
            value = prefix + value
        if index == len(touched) - 1:
            value += suffix
        _set_word_text(element, value)


def _split_replacement(value: str, weights: list[int]) -> list[str]:
    if len(weights) <= 1:
        return [value]
    total = sum(weights)
    if total <= 0:
        return [value, *("" for _ in weights[1:])]

    boundaries = [0]
    cumulative = 0
    for weight in weights[:-1]:
        cumulative += weight
        boundary = (len(value) * cumulative + total // 2) // total
        boundaries.append(max(boundaries[-1], min(len(value), boundary)))
    boundaries.append(len(value))
    return [
        value[boundaries[index] : boundaries[index + 1]]
        for index in range(len(weights))
    ]


def _set_word_text(element: Any, value: str) -> None:
    element.text = value
    if value.startswith((" ", "\t", "\n")) or value.endswith((" ", "\t", "\n")):
        element.set(XML_SPACE, "preserve")
    else:
        element.attrib.pop(XML_SPACE, None)
