import importlib.util
import tempfile
import unittest
from pathlib import Path

from offline_anonymizer.services import DocumentService, TaskService


PYSIDE_AVAILABLE = importlib.util.find_spec("PySide6") is not None


class GuiServiceFlowTest(unittest.TestCase):
    def test_single_file_service_flow_updates_task_states(self):
        events = []
        task_service = TaskService()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_file = root / "example.txt"
            output_dir = root / "outputs"
            input_file.write_text("北京科技有限公司收入500万元", encoding="utf-8")

            created = task_service.create_task(str(input_file))
            task_id = created.data["task"]["id"]
            self.assertEqual(created.data["task"]["status"], "pending")

            def on_progress(payload):
                events.append(payload)
                task_service.update_task(
                    task_id,
                    status=payload["status"],
                    progress=payload.get("progress", 0),
                    message=payload["message"],
                )

            result = DocumentService().process_file(
                input_file,
                output_dir,
                formats=["txt"],
                progress_callback=on_progress,
            )
            task_service.update_task(
                task_id,
                status="success" if result.success else "failed",
                progress=100,
                tokens=result.data.get("report", {}).get("tokens", 0),
                message=result.message,
            )
            tasks = task_service.get_tasks().data["tasks"]
            mapping_exists = Path(result.data["mapping"]).exists()
            document_exists = Path(result.data["documents"][0]).exists()

        self.assertTrue(result.success)
        self.assertEqual(tasks[0]["status"], "success")
        self.assertEqual(events[0]["status"], "running")
        self.assertEqual(events[-1]["status"], "success")
        self.assertIn(0, [event.get("progress") for event in events])
        self.assertIn(100, [event.get("progress") for event in events])
        self.assertEqual(result.data["html"], "")
        self.assertTrue(mapping_exists)
        self.assertTrue(document_exists)

    @unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
    def test_task_worker_can_call_document_service_process_file(self):
        from PySide6.QtCore import QCoreApplication

        from offline_anonymizer.gui.workers import TaskWorker

        app = QCoreApplication.instance() or QCoreApplication([])
        events = []

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_file = root / "example.txt"
            output_dir = root / "outputs"
            input_file.write_text("北京科技有限公司收入500万元", encoding="utf-8")
            worker = TaskWorker.process_file(
                DocumentService(),
                input_file,
                output_dir,
                None,
                ["txt"],
            )
            worker.signals.progress_update.connect(lambda payload: events.append(payload))
            worker.signals.task_finished.connect(lambda payload: events.append(payload))
            worker.run()

        self.assertIsNotNone(app)
        self.assertTrue(any(event.get("success") is True for event in events))


if __name__ == "__main__":
    unittest.main()
