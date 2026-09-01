from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServiceResult:
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    @classmethod
    def ok(
        cls,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> "ServiceResult":
        return cls(success=True, message=message, data=data or {}, error=None)

    @classmethod
    def fail(
        cls,
        message: str,
        error_code: str,
        detail: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> "ServiceResult":
        return cls(
            success=False,
            message=message,
            data=data or {},
            error={
                "code": error_code,
                "detail": detail,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "error": self.error,
        }
