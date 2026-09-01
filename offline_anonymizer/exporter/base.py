from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from offline_anonymizer.core.document import Document


class DocumentExporter(ABC):
    supported_extensions: set[str] = set()

    def supports(self, path: str | Path) -> bool:
        value = str(path).lower()
        extension = value if value.startswith(".") else Path(value).suffix.lower()
        return extension in self.supported_extensions

    @abstractmethod
    def export(self, document: Document, path: str | Path) -> None:
        raise NotImplementedError
