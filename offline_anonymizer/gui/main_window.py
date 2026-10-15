from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from offline_anonymizer.gui.widgets import (
    FilePickerWidget,
    OutputPanelWidget,
    RecoveryPanelWidget,
    RulePanelWidget,
    TaskTableWidget,
)
from offline_anonymizer.gui.workers import TaskWorker
from offline_anonymizer.app_environment import resource_path
from offline_anonymizer.services import ConfigService, DocumentService, TaskService
from offline_anonymizer.version import DISPLAY_NAME, VERSION
from offline_anonymizer.gui.style import get_stylesheet


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{DISPLAY_NAME} {VERSION}")
        self.setWindowIcon(QIcon(str(resource_path("icon.png"))))
        self.resize(1220, 820)
        self.setMinimumSize(1040, 720)

        self.document_service = DocumentService()
        self.config_service = ConfigService()
        self.task_service = TaskService()
        self._theme = self._load_theme()
        self.setStyleSheet(get_stylesheet(self._theme))
        self._threads: list[QThread] = []
        self._workers: list[TaskWorker] = []
        self._last_html_path = ""
        self._last_output_dir = ""
        self._last_report_path = ""
        self._batch_rows: dict[str, str] = {}
        self._generated_mapping_files: set[str] = set()

        self.file_picker = FilePickerWidget()
        self.rule_panel = RulePanelWidget()
        self.output_panel = OutputPanelWidget()
        self.task_table = TaskTableWidget()
        self.recovery_panel = RecoveryPanelWidget()
        self.start_button = QPushButton("开始脱敏")
        self.start_button.setObjectName("primaryButton")
        self.open_review_button = QPushButton("打开审核页面")
        self.open_review_button.setEnabled(False)
        self.open_output_button = QPushButton("打开输出目录")
        self.open_output_button.setEnabled(False)
        self.restore_open_output_button = QPushButton("打开输出目录")
        self.restore_open_output_button.setEnabled(False)
        self.open_report_button = QPushButton("打开报告")
        self.open_report_button.setEnabled(False)
        self.clear_records_button = QPushButton("清空记录")
        self.delete_mappings_button = QPushButton("删除映射文件")
        self.save_settings_button = QPushButton("保存设置")
        self.save_settings_button.setObjectName("primaryButton")
        self.redact_nav_button: QPushButton | None = None
        self.restore_nav_button: QPushButton | None = None
        self.help_nav_button: QPushButton | None = None
        self.settings_nav_button: QPushButton | None = None
        self.dark_theme_button: QPushButton | None = None
        self.light_theme_button: QPushButton | None = None
        self.batch_worker_combo = QComboBox()
        for value in ["1", "2", "4", "8"]:
            self.batch_worker_combo.addItem(value)
        self.batch_worker_combo.setCurrentText(str(self._load_batch_workers()))

        root = QWidget()
        root.setObjectName("appRoot")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._create_sidebar())

        container = QWidget()
        container.setObjectName("mainContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(self._create_header())

        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("pageStack")
        self.page_stack.addWidget(self._create_redact_page())
        self.page_stack.addWidget(self._create_restore_page())
        self.page_stack.addWidget(self._create_help_page())
        self.page_stack.addWidget(self._create_settings_page())
        layout.addWidget(self.page_stack)
        layout.addWidget(self._create_task_history_panel())

        self.action_stack = QStackedWidget()
        self.action_stack.setObjectName("actionStack")
        self.action_stack.addWidget(self._create_redact_action_bar())
        self.action_stack.addWidget(self._create_restore_action_bar())
        self.action_stack.addWidget(self._create_help_action_bar())
        self.action_stack.addWidget(self._create_settings_action_bar())
        layout.addWidget(self.action_stack)

        scroll = QScrollArea()
        scroll.setObjectName("mainScroll")
        scroll.viewport().setObjectName("mainScrollViewport")
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        root_layout.addWidget(scroll, 1)
        self.setCentralWidget(root)
        self.statusBar().showMessage("就绪")

        self.start_button.clicked.connect(self.start_processing)
        self.open_review_button.clicked.connect(self.open_review_page)
        self.open_output_button.clicked.connect(self.open_output_dir)
        self.restore_open_output_button.clicked.connect(self.open_output_dir)
        self.open_report_button.clicked.connect(self.open_report)
        self.clear_records_button.clicked.connect(self.clear_task_records)
        self.delete_mappings_button.clicked.connect(self.delete_generated_mappings)
        self.save_settings_button.clicked.connect(self.save_settings)
        self.recovery_panel.recover_button.clicked.connect(self.start_recovery)
        self.file_picker.path_changed.connect(self._on_input_path_changed)

    def _create_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(216)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(10)

        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo.setPixmap(
            QPixmap(str(resource_path("icon.png"))).scaled(
                56,
                56,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        layout.addWidget(logo)

        name = QLabel(DISPLAY_NAME)
        name.setObjectName("sideTitle")
        name.setAlignment(Qt.AlignCenter)
        name.setWordWrap(False)
        layout.addWidget(name)

        version = QLabel(f"v{VERSION}")
        version.setObjectName("appSubtitle")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        layout.addSpacing(12)

        self.redact_nav_button = QPushButton("脱敏")
        self.redact_nav_button.setObjectName("navButtonActive")
        self.redact_nav_button.clicked.connect(lambda: self.switch_page("redact"))
        layout.addWidget(self.redact_nav_button)

        self.restore_nav_button = QPushButton("恢复")
        self.restore_nav_button.setObjectName("navButton")
        self.restore_nav_button.clicked.connect(lambda: self.switch_page("restore"))
        layout.addWidget(self.restore_nav_button)

        self.help_nav_button = QPushButton("使用说明")
        self.help_nav_button.setObjectName("navButton")
        self.help_nav_button.clicked.connect(lambda: self.switch_page("help"))
        layout.addWidget(self.help_nav_button)

        self.settings_nav_button = QPushButton("设置")
        self.settings_nav_button.setObjectName("navButton")
        self.settings_nav_button.clicked.connect(lambda: self.switch_page("settings"))
        layout.addWidget(self.settings_nav_button)

        layout.addStretch(1)
        mode = QLabel("● Local Mode\nNo network")
        mode.setObjectName("appSubtitle")
        mode.setAlignment(Qt.AlignLeft)
        layout.addWidget(mode)
        return sidebar

    def switch_page(self, page: str) -> None:
        page_indexes = {"redact": 0, "restore": 1, "help": 2, "settings": 3}
        current = page if page in page_indexes else "redact"
        self.page_stack.setCurrentIndex(page_indexes[current])
        self.action_stack.setCurrentIndex(page_indexes[current])
        self._set_nav_active(self.redact_nav_button, current == "redact")
        self._set_nav_active(self.restore_nav_button, current == "restore")
        self._set_nav_active(self.help_nav_button, current == "help")
        self._set_nav_active(self.settings_nav_button, current == "settings")
        status_text = {
            "redact": "脱敏模式",
            "restore": "恢复模式",
            "help": "使用说明",
            "settings": "设置",
        }
        self.statusBar().showMessage(status_text[current])

    @staticmethod
    def _set_nav_active(button: QPushButton | None, active: bool) -> None:
        if button is None:
            return
        button.setObjectName("navButtonActive" if active else "navButton")
        button.style().unpolish(button)
        button.style().polish(button)

    def _on_input_path_changed(self, path: str, is_directory: bool) -> None:
        if not path:
            return
        selected = Path(path)
        output_dir = selected.parent
        self.output_panel.set_output_dir(str(output_dir))

    def _create_header(self) -> QWidget:
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        title_block = QVBoxLayout()
        title = QLabel(DISPLAY_NAME)
        title.setObjectName("appTitle")
        subtitle = QLabel("Offline reversible document redaction")
        subtitle.setObjectName("appSubtitle")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        layout.addLayout(title_block)
        layout.addStretch(1)
        build = QLabel(f"Version {VERSION}")
        build.setObjectName("appSubtitle")
        layout.addWidget(build)
        return header

    def _create_redact_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("redactPage")
        grid = QGridLayout(page)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        grid.addWidget(self._card(self.file_picker), 0, 0)
        grid.addWidget(self._card(self.rule_panel), 0, 1)
        grid.addWidget(self._create_preview_panel(), 0, 2, 2, 1)
        grid.addWidget(self._card(self.output_panel), 1, 0, 1, 2)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 3)
        return page

    def _create_restore_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("restorePage")
        grid = QGridLayout(page)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        grid.addWidget(self._card(self.recovery_panel), 0, 0)
        grid.addWidget(self._create_restore_help_panel(), 0, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)
        return page

    def _create_settings_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("settingsPage")
        grid = QGridLayout(page)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        grid.addWidget(self._create_theme_panel(), 0, 0)
        grid.addWidget(self._create_donation_panel(), 0, 1)
        grid.addWidget(self._create_batch_worker_panel(), 1, 0)
        grid.addWidget(self._create_settings_info_panel(), 1, 1)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 2)
        return page

    def _create_help_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("helpPage")
        grid = QGridLayout(page)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        grid.addWidget(self._create_help_redact_panel(), 0, 0)
        grid.addWidget(self._create_help_restore_panel(), 0, 1)
        grid.addWidget(self._create_help_safety_panel(), 1, 0, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        return page

    def _create_task_history_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("处理记录")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.clear_records_button)
        header.addWidget(self.delete_mappings_button)
        layout.addLayout(header)
        layout.addWidget(self.task_table)
        return frame

    def _create_redact_action_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("actionBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        layout.addWidget(self.start_button)
        layout.addWidget(self.open_review_button)
        layout.addWidget(self.restore_open_output_button)
        layout.addWidget(self.open_report_button)
        layout.addStretch(1)
        status = QLabel("本地处理 · 不上传文件")
        status.setObjectName("appSubtitle")
        layout.addWidget(status)
        return bar

    def _create_restore_action_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("actionBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        layout.addWidget(self.open_output_button)
        layout.addStretch(1)
        status = QLabel("恢复只依赖映射 JSON 与仍存在的 Token")
        status.setObjectName("appSubtitle")
        layout.addWidget(status)
        return bar

    def _create_settings_action_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("actionBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        layout.addWidget(self.save_settings_button)
        layout.addStretch(1)
        status = QLabel("设置会保存到本机用户目录")
        status.setObjectName("appSubtitle")
        layout.addWidget(status)
        return bar

    def _create_help_action_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("actionBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        status = QLabel("建议：脱敏后务必保留对应映射 JSON，否则无法恢复原文。")
        status.setObjectName("appSubtitle")
        layout.addWidget(status)
        layout.addStretch(1)
        return bar

    def _create_help_redact_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("previewPane")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("脱敏怎么用")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        for text in [
            "1. 在左侧选择“脱敏”。",
            "2. 拖入一个文档，或选择一个文件夹进行批量脱敏。",
            "3. 勾选金额、数字、百分比，或填写自定义敏感词。",
            "4. 选择输出格式，点击“开始脱敏”。",
            "5. 结果保存在“原文档名称 脱敏文件”文件夹中。",
            "6. 若处理失败，只生成错误报告，不留下脱敏文件夹。",
        ]:
            label = QLabel(text)
            label.setObjectName("mutedText")
            label.setWordWrap(True)
            layout.addWidget(label)
        layout.addStretch(1)
        return frame

    def _create_help_restore_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("previewPane")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("恢复怎么用")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        for text in [
            "1. 在左侧选择“恢复”。",
            "2. 拖入或选择已脱敏文档。",
            "3. 选择对应的还原映射 JSON。",
            "4. 选择输出格式，点击“恢复并导出”。",
            "5. 删除过的脱敏标记不会恢复；仍存在的标记会精准还原。",
            "6. 结果保存在“原文档名称 恢复文件”文件夹中。",
        ]:
            label = QLabel(text)
            label.setObjectName("mutedText")
            label.setWordWrap(True)
            layout.addWidget(label)
        layout.addStretch(1)
        return frame

    def _create_help_safety_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("previewPane")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("重要提醒")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        for text in [
            "还原映射 JSON 是恢复原文的钥匙。删除后，对应已脱敏文档无法再恢复。",
            "如果把多个批量脱敏文档合并成一个新文档，请使用批量还原映射文件恢复。",
            "普通文字可以随意修改；只要脱敏标记仍在，恢复就按映射 ID 进行。",
        ]:
            label = QLabel(text)
            label.setObjectName("mutedText")
            label.setWordWrap(True)
            layout.addWidget(label)
        return frame

    def _create_theme_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("previewPane")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        title = QLabel("外观")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        hint = QLabel("切换浅色或深色模式。设置会在关闭应用后保留。")
        hint.setObjectName("mutedText")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        row = QHBoxLayout()
        self.dark_theme_button = QPushButton("深色模式")
        self.light_theme_button = QPushButton("浅色模式")
        self.dark_theme_button.clicked.connect(lambda: self.apply_theme("dark"))
        self.light_theme_button.clicked.connect(lambda: self.apply_theme("light"))
        row.addWidget(self.dark_theme_button)
        row.addWidget(self.light_theme_button)
        row.addStretch(1)
        layout.addLayout(row)

        self._refresh_theme_buttons()
        layout.addStretch(1)
        return frame

    def _create_donation_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("previewPane")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("打赏作者")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        qr = QLabel()
        qr.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(str(resource_path("donation_qr.jpg")))
        if not pixmap.isNull():
            qr.setPixmap(
                pixmap.scaled(
                    260,
                    260,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
        else:
            qr.setText("二维码资源未找到")
            qr.setObjectName("mutedText")
        layout.addWidget(qr)

        caption = QLabel("Buy me a coffee")
        caption.setObjectName("mutedText")
        caption.setAlignment(Qt.AlignCenter)
        layout.addWidget(caption)
        layout.addStretch(1)
        return frame

    def _create_batch_worker_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("previewPane")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("批量并发")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        hint = QLabel(
            "批量处理文件夹时，同时处理几个文件。1 最稳，2 适合日常使用，4 适合文件多且电脑性能较好，8 可能让电脑变卡。"
        )
        hint.setObjectName("mutedText")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        row = QHBoxLayout()
        row.addWidget(QLabel("同时处理"))
        row.addWidget(self.batch_worker_combo)
        row.addWidget(QLabel("个文件"))
        row.addStretch(1)
        layout.addLayout(row)

        note = QLabel("建议默认使用 1 或 2；如果文档很大，优先选择 1。")
        note.setObjectName("mutedText")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return frame

    def _create_settings_info_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("previewPane")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("本地运行")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        for text in [
            "自定义敏感词、外观设置和输出偏好会保存在本机用户目录。",
            "所有文档处理仍在本地完成，不上传文件。",
            "映射文件会以本地可逆保护格式保存，恢复时请保留对应 JSON。",
        ]:
            label = QLabel(text)
            label.setObjectName("mutedText")
            label.setWordWrap(True)
            layout.addWidget(label)
        return frame

    def _create_preview_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("previewPane")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("审核预览")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        muted = QLabel("处理完成后可打开 HTML 审核页面，Token 将保留可逆映射。")
        muted.setObjectName("mutedText")
        muted.setWordWrap(True)
        layout.addWidget(muted)

        sample_title = QLabel("示例 Token")
        sample_title.setObjectName("appSubtitle")
        layout.addWidget(sample_title)

        for text in ["[金额001]  95,600.00", "[数字001]  202501", "[自定义001]  Project Phoenix"]:
            pill = QLabel(text)
            pill.setObjectName("tokenPill")
            layout.addWidget(pill)

        layout.addSpacing(8)
        mapping_title = QLabel("映射文件")
        mapping_title.setObjectName("appSubtitle")
        layout.addWidget(mapping_title)
        mapping = QLabel("还原时请选择对应 JSON 映射文件。批量合并文档请使用批量还原映射文件。")
        mapping.setObjectName("mutedText")
        mapping.setWordWrap(True)
        layout.addWidget(mapping)
        layout.addStretch(1)
        return frame

    def _create_restore_help_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("previewPane")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("恢复说明")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        lines = [
            "选择已脱敏文档或审核 HTML。",
            "选择对应的还原映射 JSON。",
            "合并多个批量脱敏文档后，请选择批量还原映射文件。",
            "删除过的 Token 不会恢复；仍保留的 Token 会按 ID 精准恢复。",
        ]
        for line in lines:
            label = QLabel(line)
            label.setObjectName("mutedText")
            label.setWordWrap(True)
            layout.addWidget(label)

        sample = QLabel("[金额001]  →  原始金额")
        sample.setObjectName("tokenPill")
        layout.addWidget(sample)
        layout.addStretch(1)
        return frame

    @staticmethod
    def _card(widget: QWidget) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(widget)
        return frame

    def start_processing(self) -> None:
        selected = self.file_picker.selected_path()
        if not selected:
            self._show_message("请选择有效文件或文件夹。")
            return
        selected_path = self._clean_selected_path(selected)
        selected = str(selected_path)
        if self.file_picker.is_directory() and not selected_path.is_dir():
            self._show_message("请选择有效文件夹。")
            return
        if not self.file_picker.is_directory() and not selected_path.is_file():
            self._show_message("请选择有效文件。")
            return

        task_result = self.task_service.create_task(selected)
        task = task_result.data["task"]
        self._persist_user_preferences(show_message=False)
        config = self._build_config()

        if self.file_picker.is_directory():
            self._batch_rows.clear()
            self.task_table.add_task(task["id"], selected, "等待")
            worker = TaskWorker.process_batch(
                self.document_service,
                selected,
                self.output_panel.output_dir(),
                config,
                self.output_panel.formats(),
                self.batch_workers(),
            )
        else:
            self.task_table.add_task(task["id"], selected, "等待")
            worker = TaskWorker.process_file(
                self.document_service,
                selected,
                self.output_panel.output_dir(),
                config,
                self.output_panel.formats(),
            )
        self._run_background(task["id"], worker)

    def start_recovery(self) -> None:
        html_file = self.recovery_panel.html_file()
        mapping_file = self.recovery_panel.mapping_file()
        if not html_file or not mapping_file:
            self._show_message("请选择审核/脱敏文件和Mapping文件。")
            return
        if not Path(html_file).is_file() or not Path(mapping_file).is_file():
            self._show_message("请选择有效的审核/脱敏文件和Mapping文件。")
            return

        task_result = self.task_service.create_task(html_file)
        task = task_result.data["task"]
        self._persist_user_preferences(show_message=False)
        self.task_table.add_task(task["id"], html_file, "等待")
        self._run_background(
            task["id"],
            TaskWorker.recover_document(
                self.document_service,
                html_file,
                mapping_file,
                self.recovery_panel.output_dir(),
                self.recovery_panel.formats(),
                self._build_config(),
            ),
        )

    def _build_config(self) -> dict:
        result = self.config_service.build_config(
            rules=self.rule_panel.rules(),
            output_dir=self.output_panel.output_dir(),
            formats=self.output_panel.formats(),
            custom_keywords=self.rule_panel.custom_keywords(),
        )
        if result.success:
            return result.data.get("config", {})

        # Keep the selected checkboxes authoritative even if a user config
        # cannot be read or written on Windows. Falling back to an empty config
        # would make the pipeline load defaults and enable every rule.
        return {
            "rules": self.rule_panel.rules(),
            "custom_keywords": self.rule_panel.custom_keywords(),
            "paths": {"output_dir": self.output_panel.output_dir()},
            "output": {"default_formats": self.output_panel.formats()},
        }

    def _load_theme(self) -> str:
        result = self.config_service.load_config()
        config = result.data.get("config", {}) if result.success else {}
        theme = str(config.get("ui", {}).get("theme", "dark")).lower()
        return "light" if theme == "light" else "dark"

    def _load_batch_workers(self) -> int:
        result = self.config_service.load_config()
        config = result.data.get("config", {}) if result.success else {}
        try:
            value = int(config.get("ui", {}).get("batch_workers", 1))
        except (TypeError, ValueError):
            value = 1
        return value if value in {1, 2, 4, 8} else 1

    def batch_workers(self) -> int:
        return int(self.batch_worker_combo.currentText())

    def apply_theme(self, theme: str) -> None:
        self._theme = "light" if theme == "light" else "dark"
        self.setStyleSheet(get_stylesheet(self._theme))
        self._refresh_theme_buttons()
        self._persist_user_preferences(show_message=False)
        self.statusBar().showMessage("已切换浅色模式" if self._theme == "light" else "已切换深色模式")

    def _refresh_theme_buttons(self) -> None:
        if self.dark_theme_button is not None:
            self.dark_theme_button.setObjectName(
                "primaryButton" if self._theme == "dark" else ""
            )
            self.dark_theme_button.style().unpolish(self.dark_theme_button)
            self.dark_theme_button.style().polish(self.dark_theme_button)
        if self.light_theme_button is not None:
            self.light_theme_button.setObjectName(
                "primaryButton" if self._theme == "light" else ""
            )
            self.light_theme_button.style().unpolish(self.light_theme_button)
            self.light_theme_button.style().polish(self.light_theme_button)

    def save_settings(self) -> None:
        result = self._persist_user_preferences(show_message=True)
        if result and result.success:
            self.statusBar().showMessage("设置已保存")

    def _persist_user_preferences(self, show_message: bool = False):
        config = {
            "rules": self.rule_panel.rules(),
            "custom_keywords": self.rule_panel.custom_keywords(),
            "paths": {"output_dir": self.output_panel.output_dir()},
            "output": {"default_formats": self.output_panel.formats()},
            "ui": {
                "theme": self._theme,
                "batch_workers": self.batch_workers(),
            },
        }
        result = self.config_service.save_config(config)
        if show_message:
            self._show_message(result.message)
        return result

    def _run_background(self, task_id: str, worker: TaskWorker) -> None:
        thread = QThread(self)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.signals.progress_update.connect(
            lambda payload, current=task_id: self._on_progress(current, payload)
        )
        worker.signals.batch_progress_update.connect(
            lambda payload, current=task_id: self._on_batch_progress(current, payload)
        )
        worker.signals.task_finished.connect(
            lambda payload, current=task_id: self._on_finished(current, payload)
        )
        worker.signals.task_failed.connect(
            lambda payload, current=task_id: self._on_failed(current, payload)
        )
        worker.signals.task_finished.connect(thread.quit)
        worker.signals.task_failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(
            lambda current_thread=thread, current_worker=worker: self._cleanup_worker(
                current_thread,
                current_worker,
            )
        )
        self._threads.append(thread)
        self._workers.append(worker)
        thread.start()

    def _cleanup_worker(self, thread: QThread, worker: TaskWorker) -> None:
        if thread in self._threads:
            self._threads.remove(thread)
        if worker in self._workers:
            self._workers.remove(worker)

    def _on_progress(self, task_id: str, payload: dict) -> None:
        status = payload.get("status", "running")
        message = payload.get("message", "")
        progress = int(payload.get("progress", 0) or 0)
        self.task_table.update_task(task_id, status="处理中", progress=progress, message=message)
        self.task_service.update_task(task_id, status=status, progress=progress, message=message)
        self.statusBar().showMessage(message or "处理中")

    def _on_batch_progress(self, task_id: str, payload: dict) -> None:
        event = payload.get("batch_event")
        task = payload.get("task") or {}
        total = int(payload.get("total", 0) or 0)
        completed = int(payload.get("completed", 0) or 0)

        if event == "batch_started":
            self.task_table.update_task(
                task_id,
                status="处理中",
                progress=0,
                message=f"批量任务 0/{total}",
            )
            return

        file_path = task.get("file") or payload.get("current_file")
        if not file_path:
            return
        row_id = self._batch_rows.get(file_path)
        if row_id is None:
            row_id = f"{task_id}:{file_path}"
            self._batch_rows[file_path] = row_id
            self.task_table.add_task(row_id, file_path, "等待")

        if event == "task_started":
            self.task_table.update_task(
                row_id,
                status="处理中",
                progress=0,
                message="处理中",
            )
        elif event == "task_finished":
            status = "完成" if task.get("status") == "success" else "失败"
            tokens = int(task.get("tokens", 0) or 0)
            message = task.get("error") or "完成"
            duration = self._duration_text(task.get("start_time"), task.get("end_time"))
            outputs = task.get("output_files") or {}
            first_output = next(iter(outputs.values()), "")
            self.task_table.update_task(
                row_id,
                status=status,
                progress=100,
                tokens=tokens,
                duration=duration,
                result_path=first_output,
                message=message,
            )
            overall = int((completed / total) * 100) if total else 0
            self.task_table.update_task(
                task_id,
                status="处理中",
                progress=overall,
                message=f"批量任务 {completed}/{total}",
            )

    def _on_finished(self, task_id: str, payload: dict) -> None:
        data = payload.get("data", {})
        report = data.get("report", {})
        tokens = int(report.get("tokens", 0) or 0)
        message = payload.get("message", "处理完成")
        documents = data.get("documents", [])
        result_path = documents[0] if documents else data.get("html", "")
        if data.get("recovered_document") and not data.get("html"):
            message = "恢复完成"
        if "files" in data:
            tokens = sum(int(item.get("tokens", 0) or 0) for item in data.get("files", []))
            result_path = data.get("report_file", "")
        self.task_table.update_task(
            task_id,
            status="完成",
            progress=100,
            tokens=tokens,
            result_path=result_path,
            message=message,
        )
        self.task_service.update_task(
            task_id,
            status="success",
            progress=100,
            tokens=tokens,
            message=message,
        )
        self.statusBar().showMessage(message)
        self._last_html_path = data.get("html", "") or ""
        self._last_output_dir = (
            data.get("output_dir")
            or (
                self.recovery_panel.output_dir()
                if data.get("recovered_document") and not data.get("html")
                else self.output_panel.output_dir()
            )
        )
        self._last_report_path = data.get("report_file", "") or ""
        self._remember_mapping_files(data)
        self.open_review_button.setEnabled(bool(self._last_html_path))
        self.open_output_button.setEnabled(bool(self._last_output_dir))
        self.restore_open_output_button.setEnabled(bool(self._last_output_dir))
        self.open_report_button.setEnabled(bool(self._last_report_path))
        self._show_success(data)

    def _remember_mapping_files(self, data: dict) -> None:
        for key in ("mapping", "batch_mapping_file"):
            value = data.get(key)
            if value:
                self._generated_mapping_files.add(str(value))
        for item in data.get("files", []):
            mapping_file = item.get("mapping_file")
            if mapping_file:
                self._generated_mapping_files.add(str(mapping_file))

    def _on_failed(self, task_id: str, payload: dict) -> None:
        message = payload.get("message", "任务失败")
        data = payload.get("data", {})
        report = data.get("report", {})
        if report:
            missing = report.get("missing_tokens", 0)
            unused = report.get("unused_tokens", 0)
            if missing or unused:
                message = f"{message}（未知Token {missing}，丢失Token {unused}）"
        error_report = data.get("error_report") or data.get("report_file")
        if error_report:
            message = f"{message}\n错误报告：{error_report}"
            self._last_report_path = str(error_report)
            self.open_report_button.setEnabled(True)
        self.task_table.update_task(
            task_id,
            status="失败",
            progress=100,
            message=message,
        )
        self.task_service.update_task(
            task_id,
            status="failed",
            progress=100,
            message=message,
        )
        self.statusBar().showMessage(message)
        self._show_message(message)

    def _show_message(self, message: str) -> None:
        QMessageBox.information(self, "提示", message)

    def clear_task_records(self) -> None:
        self.task_table.clear_records()
        self.task_service.clear_tasks()
        self._batch_rows.clear()
        self.statusBar().showMessage("记录已清空")

    def delete_generated_mappings(self) -> None:
        mapping_paths = [
            Path(path)
            for path in sorted(self._generated_mapping_files)
            if path and Path(path).suffix.lower() == ".json"
        ]
        existing_paths = [path for path in mapping_paths if path.exists()]
        if not existing_paths:
            self._show_message("当前没有可删除的映射文件。")
            return
        result = QMessageBox.question(
            self,
            "确认删除映射文件",
            (
                f"将删除 {len(existing_paths)} 个还原映射 JSON 文件。\n\n"
                "删除后，对应已脱敏文档将无法恢复原文。\n"
                "确定要继续吗？"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result != QMessageBox.Yes:
            return

        deleted = 0
        failed: list[str] = []
        for path in existing_paths:
            try:
                path.unlink()
                deleted += 1
                self._generated_mapping_files.discard(str(path))
            except Exception as exc:
                failed.append(f"{path}: {exc}")
        if failed:
            self._show_message(f"已删除 {deleted} 个映射文件，{len(failed)} 个删除失败。")
        else:
            self._show_message(f"已删除 {deleted} 个映射文件。")
        self.statusBar().showMessage(f"已删除 {deleted} 个映射文件")

    def _show_success(self, data: dict) -> None:
        lines = ["处理完成"]
        if "total" in data:
            lines.extend(
                [
                    f"总文件：{data.get('total', 0)}",
                    f"成功：{data.get('success', 0)}",
                    f"失败：{data.get('failed', 0)}",
                ]
            )
            if data.get("report_file"):
                lines.append(f"批量报告：{data['report_file']}")
            if data.get("batch_mapping_file"):
                lines.append(f"批量还原映射文件：{data['batch_mapping_file']}")
        elif data.get("html") or (data.get("mapping") and data.get("documents")):
            lines[0] = "脱敏完成"
            if data.get("output_dir"):
                lines.append(f"本次输出文件夹：{data['output_dir']}")
            if data.get("html"):
                lines.append(f"HTML审核文件：{data['html']}")
            if data.get("mapping"):
                lines.append(f"映射文件：{data['mapping']}")
            for document in data.get("documents", []):
                lines.append(f"输出文档：{document}")
        elif data.get("recovered_document"):
            lines[0] = "恢复完成"
            if data.get("output_dir"):
                lines.append(f"本次输出文件夹：{data['output_dir']}")
            for document in data.get("documents", []):
                lines.append(f"输出文档：{document}")

        box = QMessageBox(self)
        box.setWindowTitle("处理完成")
        box.setText("\n".join(lines))
        open_button = box.addButton("打开输出目录", QMessageBox.ActionRole)
        box.addButton("关闭", QMessageBox.AcceptRole)
        box.exec()
        if box.clickedButton() == open_button:
            self.open_output_dir()

    def open_review_page(self) -> None:
        if not self._last_html_path:
            self._show_message("尚未生成审核页面。")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_html_path))

    def open_output_dir(self) -> None:
        if not self._last_output_dir:
            self._show_message("尚未选择输出目录。")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_output_dir))

    def open_report(self) -> None:
        if not self._last_report_path:
            self._show_message("尚未生成批量报告。")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_report_path))

    @staticmethod
    def _duration_text(start_time: str | None, end_time: str | None) -> str:
        if not start_time or not end_time:
            return ""
        try:
            from datetime import datetime

            start = datetime.fromisoformat(start_time)
            end = datetime.fromisoformat(end_time)
            return f"{(end - start).total_seconds():.2f}s"
        except Exception:
            return ""

    def closeEvent(self, event) -> None:  # noqa: N802
        self._persist_user_preferences(show_message=False)
        super().closeEvent(event)

    @staticmethod
    def _clean_selected_path(path: str) -> Path:
        return Path(path.strip().strip('"').strip("'")).expanduser().resolve(strict=False)
