from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Detection:
    type: str
    start: int
    end: int
    value: str
    priority: int
    detector: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def overlaps(self, other: "Detection") -> bool:
        return self.start < other.end and other.start < self.end

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "start": self.start,
            "end": self.end,
            "value": self.value,
            "priority": self.priority,
            "detector": self.detector,
            "metadata": self.metadata,
        }


class Detector(ABC):
    token_type: str
    priority: int

    @abstractmethod
    def detect(self, text: str) -> list[Detection]:
        raise NotImplementedError
