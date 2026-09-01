from __future__ import annotations

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


class OutputPanelWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panelContent")
        self._output_dir = str(get_app_paths().outputs_dir)
        self.path_label = QLabel(self._output_dir)
        self.path_label.setWordWrap(True)
        self.choose_button = QPushButton("选择输出目录")
        self.format_boxes = {
            "docx": QCheckBox("docx"),
            "md": QCheckBox("md"),
            "txt": QCheckBox("txt"),
        }
        self.format_boxes["docx"].setChecked(True)

        layout = QVBoxLayout(self)
        title = QLabel("输出设置")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addWidget(self.path_label)
        layout.addWidget(self.choose_button)

        formats = QHBoxLayout()
        for checkbox in self.format_boxes.values():
            formats.addWidget(checkbox)
        formats.addStretch(1)
        layout.addLayout(formats)

        self.choose_button.clicked.connect(self.select_output_dir)

    def output_dir(self) -> str:
        return self._output_dir

    def formats(self) -> list[str]:
        return [
            key for key, checkbox in self.format_boxes.items() if checkbox.isChecked()
        ]

    def set_output_dir(self, path: str) -> None:
        self._output_dir = path
        self.path_label.setText(path)

    def select_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", self._output_dir)
        if path:
            self.set_output_dir(path)
