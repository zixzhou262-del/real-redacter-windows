from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from offline_anonymizer.app_environment import (
    get_app_paths,
    load_resource_json,
    resolve_app_placeholders,
)

DEFAULT_CONFIG_RESOURCE = "default_config.json"


def load_config(
    path: str | Path | None = None,
    include_user: bool | None = None,
) -> dict[str, Any]:
    if include_user is None:
        include_user = path is None
    config = load_resource_json(DEFAULT_CONFIG_RESOURCE)
    user_config = get_app_paths().user_config
    if include_user and user_config.exists():
        config = deep_merge(config, _read_json(user_config))
    if path is not None:
        config = deep_merge(config, _read_json(Path(path)))
    return resolve_app_placeholders(config)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
