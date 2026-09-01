from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class FilePickerWidget(QWidget):
    path_changed = Signal(str, bool)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panelContent")
        self.setAcceptDrops(True)
        self._selected_path = ""
        self._is_directory = False

        title = QLabel("文件选择")
        title.setObjectName("sectionTitle")
        self.path_label = QLabel("未选择")
        self.drop_label = QLabel("可直接拖入 .docx / .md / .txt 文件或文件夹")
        self.drop_label.setObjectName("mutedText")
        self.mode_label = QLabel("模式：未选择")
        self.path_label.setWordWrap(True)
        self.file_button = QPushButton("选择文档")
        self.folder_button = QPushButton("选择文件夹")

        buttons = QHBoxLayout()
        buttons.addWidget(self.file_button)
        buttons.addWidget(self.folder_button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(self.mode_label)
        layout.addLayout(buttons)
        layout.addWidget(self.drop_label)
        layout.addWidget(self.path_label)

        self.file_button.clicked.connect(self.select_file)
        self.folder_button.clicked.connect(self.select_folder)

    def selected_path(self) -> str:
        return self._selected_path

    def is_directory(self) -> bool:
        return self._is_directory

    def set_path(self, path: str, is_directory: bool = False) -> None:
        self._selected_path = path
        self._is_directory = is_directory
        label = path if path else "未选择"
        self.path_label.setText(label)
        if path:
            self.mode_label.setText("模式：批量处理" if is_directory else "模式：单文件处理")
        else:
            self.mode_label.setText("模式：未选择")
        self.path_changed.emit(path, is_directory)

    def select_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择文档",
            str(Path.home()),
            "Documents (*.docx *.md *.txt)",
        )
        if path:
            self.set_path(path, False)

    def select_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择文件夹", str(Path.home()))
        if path:
            self.set_path(path, True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = Path(url.toLocalFile())
                if path.is_dir() or path.suffix.lower() in {".docx", ".md", ".txt"}:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_dir():
                self.set_path(str(path), True)
                event.acceptProposedAction()
                return
            if path.suffix.lower() in {".docx", ".md", ".txt"}:
                self.set_path(str(path), False)
                event.acceptProposedAction()
                return
        event.ignore()
