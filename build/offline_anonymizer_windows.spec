# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


APP_NAME = "ReaL Redacter"
APP_VERSION = "2.2.3"
PROJECT_ROOT = Path(SPECPATH).parent
if PROJECT_ROOT.name == "build":
    PROJECT_ROOT = PROJECT_ROOT.parent

ENTRY_SCRIPT = PROJECT_ROOT / "offline_anonymizer" / "gui" / "app.py"
RESOURCE_DIR = PROJECT_ROOT / "offline_anonymizer" / "resources"
ICON_FILE = PROJECT_ROOT / "offline_anonymizer" / "resources" / "icon.png"
VERSION_FILE = PROJECT_ROOT / "build" / "windows_version_info.txt"

datas = [
    (str(RESOURCE_DIR), "offline_anonymizer/resources"),
]
datas += collect_data_files("docx")

hiddenimports = [
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtNetwork",
    "offline_anonymizer.gui.app",
    "offline_anonymizer.gui.main_window",
    "offline_anonymizer.gui.widgets.file_picker",
    "offline_anonymizer.gui.widgets.output_panel",
    "offline_anonymizer.gui.widgets.recovery_panel",
    "offline_anonymizer.gui.widgets.rule_panel",
    "offline_anonymizer.gui.widgets.task_table",
    "offline_anonymizer.gui.workers.task_worker",
    "offline_anonymizer.services.document_service",
    "offline_anonymizer.workflow.pipeline",
    "offline_anonymizer.batch.manager",
    "offline_anonymizer.docx_format",
    "offline_anonymizer.parser.docx_parser",
    "offline_anonymizer.parser.markdown_parser",
    "offline_anonymizer.parser.txt_parser",
    "offline_anonymizer.exporter.docx_exporter",
    "offline_anonymizer.exporter.markdown_exporter",
    "offline_anonymizer.exporter.txt_exporter",
]
hiddenimports += collect_submodules("docx")
hiddenimports += collect_submodules("markdown_it")

a = Analysis(
    [str(ENTRY_SCRIPT)],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_FILE) if ICON_FILE.exists() else None,
    version=str(VERSION_FILE) if VERSION_FILE.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
