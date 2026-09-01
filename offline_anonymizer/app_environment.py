from __future__ import annotations

from dataclasses import dataclass
import importlib.resources as resources
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any

from offline_anonymizer.version import APP_NAME


APP_HOME_ENV = "OFFLINE_ANONYMIZER_HOME"


@dataclass(frozen=True)
class AppPaths:
    root: Path
    config_dir: Path
    logs_dir: Path
    outputs_dir: Path
    mappings_dir: Path
    temp_dir: Path
    user_config: Path

    def as_dict(self) -> dict[str, str]:
        return {
            "root": str(self.root),
            "config_dir": str(self.config_dir),
            "logs_dir": str(self.logs_dir),
            "outputs_dir": str(self.outputs_dir),
            "mappings_dir": str(self.mappings_dir),
            "temp_dir": str(self.temp_dir),
            "user_config": str(self.user_config),
        }


@dataclass
class StartupCheckResult:
    ok: bool
    errors: list[str]
    warnings: list[str]
    paths: AppPaths

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
            "paths": self.paths.as_dict(),
        }


def get_app_paths(base_dir: str | Path | None = None) -> AppPaths:
    root = Path(base_dir) if base_dir is not None else _default_app_root()
    return AppPaths(
        root=root,
        config_dir=root / "config",
        logs_dir=root / "logs",
        outputs_dir=root / "outputs",
        mappings_dir=root / "mappings",
        temp_dir=root / "temp",
        user_config=root / "config" / "config.json",
    )


def ensure_app_directories(base_dir: str | Path | None = None) -> AppPaths:
    paths = get_app_paths(base_dir)
    for directory in [
        paths.config_dir,
        paths.logs_dir,
        paths.outputs_dir,
        paths.mappings_dir,
        paths.temp_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)
    return paths


def ensure_user_config(base_dir: str | Path | None = None) -> Path:
    paths = ensure_app_directories(base_dir)
    if not paths.user_config.exists():
        paths.user_config.write_text(
            load_resource_text("default_config.json"),
            encoding="utf-8",
        )
    return paths.user_config


def resource_path(name: str) -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidate = Path(bundle_root) / "offline_anonymizer" / "resources" / name
        if candidate.exists():
            return candidate

    resource = resources.files("offline_anonymizer.resources").joinpath(name)
    with resources.as_file(resource) as path:
        return Path(path)


def load_resource_text(name: str) -> str:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidate = Path(bundle_root) / "offline_anonymizer" / "resources" / name
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    return resources.files("offline_anonymizer.resources").joinpath(name).read_text(
        encoding="utf-8"
    )


def load_resource_json(name: str) -> dict[str, Any]:
    return json.loads(load_resource_text(name))


def resolve_app_placeholders(config: dict[str, Any]) -> dict[str, Any]:
    paths = get_app_paths()
    replacements = {
        "__APP_ROOT__": str(paths.root),
        "__APP_CONFIG__": str(paths.config_dir),
        "__APP_LOGS__": str(paths.logs_dir),
        "__APP_OUTPUTS__": str(paths.outputs_dir),
        "__APP_MAPPINGS__": str(paths.mappings_dir),
        "__APP_TEMP__": str(paths.temp_dir),
    }

    def resolve(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: resolve(item) for key, item in value.items()}
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if isinstance(value, str):
            for marker, replacement in replacements.items():
                value = value.replace(marker, replacement)
        return value

    return resolve(config)


def startup_check(base_dir: str | Path | None = None) -> StartupCheckResult:
    paths = ensure_app_directories(base_dir)
    errors: list[str] = []
    warnings: list[str] = []

    try:
        ensure_user_config(base_dir)
    except Exception as exc:
        errors.append(f"配置文件初始化失败：{exc}")

    if not resource_path("default_config.json").exists():
        errors.append("内置默认配置缺失。")

    required = ["docx"]
    optional = ["markdown_it", "PySide6"]
    for module in required:
        if importlib.util.find_spec(module) is None:
            errors.append(f"缺少运行依赖：{module}")
    for module in optional:
        if importlib.util.find_spec(module) is None:
            warnings.append(f"运行依赖未安装或当前环境不可用：{module}")

    return StartupCheckResult(
        ok=not errors,
        errors=errors,
        warnings=warnings,
        paths=paths,
    )


def _default_app_root() -> Path:
    override = os.environ.get(APP_HOME_ENV)
    if override:
        return Path(override)
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if platform.system() == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / APP_NAME
        return Path.home() / "AppData" / "Local" / APP_NAME
    return Path.home() / f".{APP_NAME}"
