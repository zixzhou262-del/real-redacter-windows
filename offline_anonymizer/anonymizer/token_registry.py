from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


TOKEN_LABELS = {
    "company": "企业",
    "person": "姓名",
    "money": "金额",
    "percent": "百分比",
    "date": "日期",
    "number": "数字",
    "phone": "电话",
    "email": "邮箱",
    "custom": "敏感",
}


@dataclass
class Token:
    token_id: str
    token_type: str
    masked_value: str
    original_value: str
    normalized_value: str
    created_time: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)
    occurrences: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "token_type": self.token_type,
            "masked_value": self.masked_value,
            "original_value": self.original_value,
            "normalized_value": self.normalized_value,
            "created_time": self.created_time,
            "metadata": self.metadata,
            "occurrences": self.occurrences,
        }


class TokenRegistry:
    """Token identity store for reversible anonymization.

    Recovery must use token_id. Occurrence positions are only audit/display data.
    """

    def __init__(self, labels: dict[str, str] | None = None) -> None:
        self._labels = labels or TOKEN_LABELS
        self._counters: dict[str, int] = {}
        self._by_identity: dict[tuple[str, str], Token] = {}
        self._by_id: dict[str, Token] = {}

    def create_token(
        self,
        type: str,
        original: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        return self.get_or_create_token(type, original, metadata).token_id

    def get_or_create_token(
        self,
        token_type: str,
        original: str,
        metadata: dict[str, Any] | None = None,
    ) -> Token:
        normalized = self.normalize(original)
        identity = (token_type, normalized)
        if identity in self._by_identity:
            return self._by_identity[identity]

        index = self._next_index(token_type)
        label = self._labels.get(token_type, self._labels["custom"])
        token = Token(
            token_id=f"{token_type}_{index:03d}",
            token_type=token_type,
            masked_value=f"[{label}{index:03d}]",
            original_value=original,
            normalized_value=normalized,
            metadata=metadata or {},
        )
        self._by_identity[identity] = token
        self._by_id[token.token_id] = token
        return token

    def get_token(self, token_id: str) -> Token | None:
        return self._by_id.get(token_id)

    def restore_token(self, token_id: str) -> str:
        token = self.get_token(token_id)
        if token is None:
            raise KeyError(f"Unknown token_id: {token_id}")
        return token.original_value

    def record_occurrence(
        self,
        token_id: str,
        document_id: str,
        node_id: str,
        original_start: int,
        original_end: int,
        masked_start: int,
        masked_end: int,
    ) -> None:
        token = self.get_token(token_id)
        if token is None:
            raise KeyError(f"Unknown token_id: {token_id}")
        token.occurrences.append(
            {
                "document_id": document_id,
                "node_id": node_id,
                "original_start": original_start,
                "original_end": original_end,
                "masked_start": masked_start,
                "masked_end": masked_end,
            }
        )

    def export_mapping(self) -> dict[str, dict[str, Any]]:
        return {token_id: token.to_dict() for token_id, token in self._by_id.items()}

    def save_mapping(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.export_mapping(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def all_tokens(self) -> list[Token]:
        return list(self._by_id.values())

    @staticmethod
    def normalize(value: str) -> str:
        return "".join(value.split())

    def _next_index(self, token_type: str) -> int:
        self._counters[token_type] = self._counters.get(token_type, 0) + 1
        return self._counters[token_type]
