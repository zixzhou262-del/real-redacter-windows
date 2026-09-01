from __future__ import annotations

from abc import ABC, abstractmethod

from offline_anonymizer.anonymizer.token_registry import TokenRegistry
from offline_anonymizer.core.document import Document


class Anonymizer(ABC):
    @abstractmethod
    def anonymize(self, document: Document, registry: TokenRegistry) -> Document:
        raise NotImplementedError
