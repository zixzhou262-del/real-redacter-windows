from __future__ import annotations

from abc import ABC, abstractmethod

from offline_anonymizer.anonymizer.token_registry import TokenRegistry
from offline_anonymizer.core.document import Document


class RecoveryEngine(ABC):
    @abstractmethod
    def recover_all(self, document: Document, registry: TokenRegistry) -> Document:
        raise NotImplementedError

    @abstractmethod
    def recover_token(
        self, document: Document, registry: TokenRegistry, token_id: str
    ) -> Document:
        raise NotImplementedError
