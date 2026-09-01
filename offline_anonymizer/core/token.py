from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


DEFAULT_TOKEN_LABELS = {
    "company": "企业",
    "person": "姓名",
    "money": "金额",
    "percent": "百分比",
    "date": "日期",
    "number": "数字",
    "phone": "手机",
    "email": "邮箱",
    "custom": "敏感",
}


@dataclass(frozen=True)
class TokenLocation:
    document_id: str
    block_id: str
    inline_index: int | None = None
    start: int | None = None
    end: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "block_id": self.block_id,
            "inline_index": self.inline_index,
            "start": self.start,
            "end": self.end,
        }


@dataclass
class Token:
    id: str
    type: str
    masked_value: str
    original_value: str
    location: list[TokenLocation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def add_location(self, location: TokenLocation) -> None:
        self.location.append(location)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "masked_value": self.masked_value,
            "original_value": self.original_value,
            "location": [item.to_dict() for item in self.location],
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class TokenRegistry:
    """In-memory token identity registry used by future stores and engines."""

    def __init__(self, labels: dict[str, str] | None = None) -> None:
        self._labels = labels or DEFAULT_TOKEN_LABELS
        self._counters: dict[str, int] = {}
        self._by_identity: dict[tuple[str, str], Token] = {}
        self._by_id: dict[str, Token] = {}

    def get_or_create(
        self,
        token_type: str,
        original_value: str,
        location: TokenLocation | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Token:
        normalized = self.normalize(original_value)
        identity = (token_type, normalized)

        if identity in self._by_identity:
            token = self._by_identity[identity]
            if location is not None:
                token.add_location(location)
            return token

        index = self._next_index(token_type)
        label = self._labels.get(token_type, self._labels["custom"])
        token = Token(
            id=f"tok_{token_type}_{index:04d}",
            type=token_type,
            masked_value=f"[{label}{index:03d}]",
            original_value=original_value,
            location=[location] if location is not None else [],
            metadata={"normalized": normalized, **(metadata or {})},
        )
        self._by_identity[identity] = token
        self._by_id[token.id] = token
        return token

    def get_by_id(self, token_id: str) -> Token | None:
        return self._by_id.get(token_id)

    def all_tokens(self) -> list[Token]:
        return list(self._by_id.values())

    @staticmethod
    def normalize(value: str) -> str:
        return "".join(value.split())

    def _next_index(self, token_type: str) -> int:
        self._counters[token_type] = self._counters.get(token_type, 0) + 1
        return self._counters[token_type]
