import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

from offline_anonymizer.services import DocumentService
from offline_anonymizer.version import DISPLAY_NAME, VERSION


PYSIDE_AVAILABLE = importlib.util.find_spec("PySide6") is not None
RUN_QT_WIDGET_TESTS = os.environ.get("RUN_QT_WIDGET_TESTS") == "1"


def configure_qt_for_test():
    import PySide6

    plugin_root = Path(PySide6.__file__).resolve().parent / "Qt" / "plugins"
    os.environ.setdefault("QT_PLUGIN_PATH", str(plugin_root))
    os.environ.setdefault(
        "QT_QPA_PLATFORM_PLUGIN_PATH",
        str(plugin_root / "platforms"),
    )
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class GuiImportTest(unittest.TestCase):
    def test_service_dependency_is_available(self):
        self.assertIsInstance(DocumentService(), DocumentService)

    @unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
    def test_v110_rule_panel_only_exposes_supported_rules(self):
        from offline_anonymizer.gui.widgets.rule_panel import RULE_LABELS

        self.assertEqual(
            RULE_LABELS,
            {
                "money": "金额",
                "percent": "百分比",
                "number": "数字",
            },
        )

    @unittest.skipUnless(
        PYSIDE_AVAILABLE and RUN_QT_WIDGET_TESTS,
        "Qt widget tests require RUN_QT_WIDGET_TESTS=1",
    )
    def test_rule_panel_preserves_custom_only_selection(self):
        configure_qt_for_test()
        from PySide6.QtWidgets import QApplication

        from offline_anonymizer.gui.widgets.rule_panel import RulePanelWidget

        app = QApplication.instance() or QApplication([])
        panel = RulePanelWidget()
        panel.checkboxes["money"].setChecked(False)
        panel.checkboxes["percent"].setChecked(False)
        panel.checkboxes["number"].setChecked(False)
        panel.checkboxes["custom"].setChecked(True)
        panel.custom_keywords_edit.setPlainText("苹果")

        self.assertEqual(
            panel.rules(),
            {"money": False, "percent": False, "number": False, "custom": True},
        )
        self.assertEqual(panel.custom_keywords(), ["苹果"])
        self.assertIsNotNone(app)

    def test_stylesheet_uses_windows_safe_checkmark_uri(self):
        from offline_anonymizer.gui.style import get_stylesheet

        stylesheet = get_stylesheet("dark")
        self.assertIn("QCheckBox::indicator:checked", stylesheet)
        self.assertIn("url(\"file://", stylesheet)
        self.assertIn("QPlainTextEdit#customKeywordsEdit", stylesheet)

    @unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
    def test_gui_modules_can_import(self):
        from offline_anonymizer.gui.main_window import MainWindow
        from offline_anonymizer.gui.workers import TaskWorker
        from offline_anonymizer.gui.widgets import FilePickerWidget

        self.assertIsNotNone(MainWindow)
        self.assertIsNotNone(TaskWorker)
        self.assertIsNotNone(FilePickerWidget)

    @unittest.skipUnless(
        PYSIDE_AVAILABLE and RUN_QT_WIDGET_TESTS,
        "Qt widget tests require RUN_QT_WIDGET_TESTS=1",
    )
    def test_main_window_can_be_created(self):
        configure_qt_for_test()
        from PySide6.QtWidgets import QApplication

        from offline_anonymizer.gui.main_window import MainWindow

        app = QApplication.instance() or QApplication([])
        window = MainWindow()

        self.assertEqual(window.windowTitle(), f"{DISPLAY_NAME} {VERSION}")
        self.assertIsNotNone(app)

    @unittest.skipUnless(
        PYSIDE_AVAILABLE and RUN_QT_WIDGET_TESTS,
        "Qt widget tests require RUN_QT_WIDGET_TESTS=1",
    )
    def test_main_window_keeps_worker_until_background_task_finishes(self):
        configure_qt_for_test()
        from PySide6.QtCore import QEventLoop, QTimer
        from PySide6.QtWidgets import QApplication

        from offline_anonymizer.gui.main_window import MainWindow

        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_file = root / "example.txt"
            input_file.write_text("北京科技有限公司收入500万元", encoding="utf-8")

            window = MainWindow()
            window._show_success = lambda data: None
            window._show_message = lambda message: None
            window.file_picker.set_path(str(input_file), False)
            window.output_panel.set_output_dir(str(root / "outputs"))
            window.start_processing()

            self.assertEqual(len(window._workers), 1)

            loop = QEventLoop()

            def stop_when_done():
                if not window._workers:
                    loop.quit()

            timer = QTimer()
            timer.timeout.connect(stop_when_done)
            timer.start(20)
            QTimer.singleShot(5000, loop.quit)
            loop.exec()
            timer.stop()

            self.assertEqual(len(window._workers), 0)
            self.assertEqual(window.task_table.table.item(0, 1).text(), "完成")
        self.assertIsNotNone(app)


if __name__ == "__main__":
    unittest.main()
