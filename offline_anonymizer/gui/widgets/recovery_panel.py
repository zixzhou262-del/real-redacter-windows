from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from offline_anonymizer.app_environment import get_app_paths


class RecoveryPanelWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panelContent")
        self.setAcceptDrops(True)
        self._html_file = ""
        self._mapping_file = ""
        self._output_dir = str(get_app_paths().outputs_dir)
        self.html_label = QLabel("审核/脱敏文件：未选择")
        self.mapping_label = QLabel("Mapping：未选择")
        self.output_label = QLabel(f"输出目录：{self._output_dir}")
        self.drop_label = QLabel("可拖入待恢复文档或还原映射 JSON")
        self.drop_label.setObjectName("mutedText")
        self.html_button = QPushButton("选择审核/脱敏文件")
        self.mapping_button = QPushButton("选择映射文件")
        self.output_button = QPushButton("选择输出目录")
        self.recover_button = QPushButton("恢复并导出")
        self.format_boxes = {
            "docx": QCheckBox("docx"),
            "md": QCheckBox("md"),
            "txt": QCheckBox("txt"),
        }
        self.format_boxes["docx"].setChecked(True)

        layout = QVBoxLayout(self)
        title = QLabel("恢复")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addWidget(self.html_label)
        layout.addWidget(self.mapping_label)
        layout.addWidget(self.output_label)
        layout.addWidget(self.drop_label)

        buttons = QHBoxLayout()
        buttons.addWidget(self.html_button)
        buttons.addWidget(self.mapping_button)
        buttons.addWidget(self.output_button)
        buttons.addWidget(self.recover_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        formats = QHBoxLayout()
        formats.addWidget(QLabel("恢复格式"))
        for checkbox in self.format_boxes.values():
            formats.addWidget(checkbox)
        formats.addStretch(1)
        layout.addLayout(formats)

        self.html_button.clicked.connect(self.select_html)
        self.mapping_button.clicked.connect(self.select_mapping)
        self.output_button.clicked.connect(self.select_output_dir)

    def html_file(self) -> str:
        return self._html_file

    def mapping_file(self) -> str:
        return self._mapping_file

    def output_dir(self) -> str:
        return self._output_dir

    def formats(self) -> list[str]:
        return [
            key for key, checkbox in self.format_boxes.items() if checkbox.isChecked()
        ]

    def set_html_file(self, path: str) -> None:
        self._html_file = path
        self.html_label.setText(f"审核/脱敏文件：{path or '未选择'}")
        if path:
            self.set_output_dir(str(Path(path).parent))

    def set_mapping_file(self, path: str) -> None:
        self._mapping_file = path
        self.mapping_label.setText(f"Mapping：{path or '未选择'}")

    def set_output_dir(self, path: str) -> None:
        self._output_dir = path
        self.output_label.setText(f"输出目录：{path or '未选择'}")

    def select_html(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择审核/脱敏文件",
            str(Path.home()),
            "Recoverable Files (*.html *.htm *.docx *.md *.txt)",
        )
        if path:
            self.set_html_file(path)

    def select_mapping(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择Mapping",
            str(Path.home()),
            "JSON (*.json)",
        )
        if path:
            self.set_mapping_file(path)

    def select_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", self._output_dir)
        if path:
            self.set_output_dir(path)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = Path(url.toLocalFile())
                if path.suffix.lower() in {".json", ".html", ".htm", ".docx", ".md", ".txt"}:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        accepted = False
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            suffix = path.suffix.lower()
            if suffix == ".json":
                self.set_mapping_file(str(path))
                accepted = True
            elif suffix in {".html", ".htm", ".docx", ".md", ".txt"}:
                self.set_html_file(str(path))
                accepted = True
        if accepted:
            event.acceptProposedAction()
        else:
            event.ignore()
