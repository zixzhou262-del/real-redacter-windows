from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from offline_anonymizer.app_environment import ensure_app_directories
from offline_anonymizer.config import deep_merge, load_config
from offline_anonymizer.services.exceptions import classify_exception
from offline_anonymizer.services.result import ServiceResult


class ConfigService:
    def load_config(self, path: str | Path | None = None) -> ServiceResult:
        try:
            config = load_config(path)
            return ServiceResult.ok("配置加载完成", {"config": config})
        except Exception as exc:
            error = classify_exception(exc, "config")
            return ServiceResult.fail(error.message, error.code, error.detail)

    def build_config(
        self,
        rules: dict[str, bool] | None = None,
        output_dir: str | Path | None = None,
        formats: list[str] | None = None,
        token_labels: dict[str, str] | None = None,
        custom_keywords: list[str] | None = None,
        custom_regex: list[str] | None = None,
        base_config: dict[str, Any] | None = None,
    ) -> ServiceResult:
        try:
            config = base_config or load_config()
            override: dict[str, Any] = {}
            if rules is not None:
                override["rules"] = rules
            if output_dir is not None:
                override["paths"] = {"output_dir": str(output_dir)}
            if formats is not None:
                override["output"] = {"default_formats": formats}
            if token_labels is not None:
                override["token_labels"] = token_labels
            if custom_keywords is not None:
                override["custom_keywords"] = custom_keywords
            if custom_regex is not None:
                override["custom_regex"] = custom_regex
            built = deep_merge(config, override)
            return ServiceResult.ok("配置已生成", {"config": built})
        except Exception as exc:
            error = classify_exception(exc, "config")
            return ServiceResult.fail(error.message, error.code, error.detail)

    def save_config(self, config: dict[str, Any], path: str | Path | None = None) -> ServiceResult:
        try:
            output = Path(path) if path is not None else ensure_app_directories().user_config
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(config, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return ServiceResult.ok("配置已保存", {"path": str(output)})
        except Exception as exc:
            error = classify_exception(exc, "config")
            return ServiceResult.fail(error.message, error.code, error.detail)
