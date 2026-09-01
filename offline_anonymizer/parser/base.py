from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from offline_anonymizer.core.document import Document


class DocumentParser(ABC):
    supported_extensions: set[str] = set()

    def supports(self, path: str | Path) -> bool:
        value = str(path).lower()
        extension = value if value.startswith(".") else Path(value).suffix.lower()
        return extension in self.supported_extensions

    @property
    def format_name(self) -> str:
        extension = next(iter(self.supported_extensions), "")
        return extension.removeprefix(".")

    @abstractmethod
    def parse(self, path: str | Path) -> Document:
        raise NotImplementedError
