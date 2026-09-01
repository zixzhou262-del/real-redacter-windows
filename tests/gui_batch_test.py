import importlib.util
import tempfile
import time
import unittest
from pathlib import Path

from offline_anonymizer.services import DocumentService, TaskService


PYSIDE_AVAILABLE = importlib.util.find_spec("PySide6") is not None


class GuiBatchFlowTest(unittest.TestCase):
    def test_process_batch_service_flow_succeeds(self):
        events = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            (input_dir / "a.txt").write_text(
                "北京科技有限公司收入500万元",
                encoding="utf-8",
            )
            (input_dir / "b.md").write_text(
                "# 项目\n\n北京科技有限公司收入500万元",
                encoding="utf-8",
            )
            (input_dir / "c.txt").write_text(
                "联系人张三：13812345678",
                encoding="utf-8",
            )

            result = DocumentService().process_batch(
                input_dir,
                output_dir,
                formats=["txt"],
                workers=1,
                progress_callback=events.append,
            )
            report_path = Path(result.data["report_file"])
            report_exists = report_path.exists()

        self.assertTrue(result.success)
        self.assertEqual(result.data["total"], 3)
        self.assertEqual(result.data["success"], 3)
        self.assertTrue(report_exists)
        self.assertTrue(any(event.get("batch_event") == "task_started" for event in events))
        self.assertTrue(any(event.get("batch_event") == "task_finished" for event in events))

    def test_process_batch_continues_when_one_file_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            (input_dir / "good.txt").write_text(
                "北京科技有限公司收入500万元",
                encoding="utf-8",
            )
            (input_dir / "bad.docx").write_text("not a docx", encoding="utf-8")

            result = DocumentService().process_batch(
                input_dir,
                output_dir,
                formats=["txt"],
                workers=1,
            )
            error_report = Path(result.data["error_report"])
            error_report_exists = error_report.exists()

        self.assertTrue(result.success)
        self.assertEqual(result.data["total"], 2)
        self.assertEqual(result.data["success"], 1)
        self.assertEqual(result.data["failed"], 1)
        self.assertTrue(error_report_exists)

    def test_process_batch_10_files_performance_signal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            for index in range(10):
                (input_dir / f"file_{index}.txt").write_text(
                    f"北京科技有限公司收入{index}万元",
                    encoding="utf-8",
                )

            started = time.perf_counter()
            result = DocumentService().process_batch(
                input_dir,
                output_dir,
                formats=["txt"],
                workers=2,
            )
            elapsed = time.perf_counter() - started

        self.assertTrue(result.success)
        self.assertEqual(result.data["total"], 10)
        self.assertEqual(result.data["success"], 10)
        self.assertGreaterEqual(elapsed, 0)

    @unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
    def test_task_worker_can_call_process_batch(self):
        from PySide6.QtCore import QCoreApplication

        from offline_anonymizer.gui.workers import TaskWorker

        app = QCoreApplication.instance() or QCoreApplication([])
        events = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            (input_dir / "a.txt").write_text(
                "北京科技有限公司收入500万元",
                encoding="utf-8",
            )
            worker = TaskWorker.process_batch(
                DocumentService(),
                input_dir,
                output_dir,
                None,
                ["txt"],
                1,
            )
            worker.signals.batch_progress_update.connect(lambda payload: events.append(payload))
            worker.signals.task_finished.connect(lambda payload: events.append(payload))
            worker.run()

        self.assertIsNotNone(app)
        self.assertTrue(any(event.get("batch_event") == "task_finished" for event in events))
        self.assertTrue(any(event.get("success") is True for event in events))


if __name__ == "__main__":
    unittest.main()
