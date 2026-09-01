from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from offline_anonymizer.app_environment import startup_check
from offline_anonymizer.app_environment import resource_path
from offline_anonymizer.version import APP_NAME, VERSION


def main() -> int:
    check = startup_check()
    if "--self-check" in sys.argv:
        print(
            json.dumps(
                {
                    "app": APP_NAME,
                    "version": VERSION,
                    "startup": check.to_dict(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if check.ok else 1

    if not check.ok:
        print("启动检查失败：", file=sys.stderr)
        for error in check.errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    try:
        import PySide6

        _configure_qt_plugin_path(PySide6)
        from PySide6.QtGui import QFont, QIcon
        from PySide6.QtWidgets import QApplication

        from offline_anonymizer.gui.main_window import MainWindow
    except Exception as exc:
        print(f"GUI依赖加载失败：{exc}", file=sys.stderr)
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setFont(QFont("Helvetica Neue", 13))
    app.setWindowIcon(QIcon(str(resource_path("icon.png"))))
    window = MainWindow()
    window.show()
    for warning in check.warnings:
        print(f"启动警告：{warning}", file=sys.stderr)
    return app.exec()


def _configure_qt_plugin_path(pyside_module) -> None:
    plugin_root = Path(pyside_module.__file__).resolve().parent / "Qt" / "plugins"
    if plugin_root.exists():
        os.environ.setdefault("QT_PLUGIN_PATH", str(plugin_root))
        os.environ.setdefault(
            "QT_QPA_PLATFORM_PLUGIN_PATH",
            str(plugin_root / "platforms"),
        )


if __name__ == "__main__":
    raise SystemExit(main())
