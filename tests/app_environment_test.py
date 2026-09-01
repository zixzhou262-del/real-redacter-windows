import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from offline_anonymizer.app_environment import (
    APP_HOME_ENV,
    ensure_app_directories,
    ensure_user_config,
    get_app_paths,
    load_resource_json,
    resource_path,
    startup_check,
)
from offline_anonymizer.config import load_config
from offline_anonymizer.services import ConfigService
from offline_anonymizer.workflow.logger import WorkflowLogger


class AppEnvironmentTest(unittest.TestCase):
    def test_creates_macos_user_data_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {APP_HOME_ENV: str(Path(tmpdir) / "app")}, clear=False):
                paths = ensure_app_directories()

                self.assertTrue(paths.config_dir.exists())
                self.assertTrue(paths.logs_dir.exists())
                self.assertTrue(paths.outputs_dir.exists())
                self.assertTrue(paths.mappings_dir.exists())
                self.assertTrue(paths.temp_dir.exists())

    def test_uses_local_app_data_on_windows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            local_app_data = Path(tmpdir) / "LocalAppData"
            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}, clear=True):
                with patch("platform.system", return_value="Windows"):
                    paths = get_app_paths()

            self.assertEqual(paths.root.parent, local_app_data)
            self.assertEqual(paths.config_dir, paths.root / "config")
            self.assertEqual(paths.logs_dir, paths.root / "logs")

    def test_loads_user_config_over_default_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {APP_HOME_ENV: str(Path(tmpdir) / "app")}, clear=False):
                paths = ensure_app_directories()
                paths.user_config.write_text(
                    json.dumps({"rules": {"money": False}}),
                    encoding="utf-8",
                )

                config = load_config()

                self.assertFalse(config["rules"]["money"])
                self.assertNotIn("company", config["rules"])
                self.assertTrue(config["rules"]["number"])
                self.assertTrue(config["rules"]["percent"])
                self.assertTrue(config["rules"]["custom"])
                self.assertEqual(config["paths"]["output_dir"], str(paths.outputs_dir))

    def test_config_service_saves_to_user_config_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {APP_HOME_ENV: str(Path(tmpdir) / "app")}, clear=False):
                paths = ensure_app_directories()
                result = ConfigService().save_config({"rules": {"money": False}})

                self.assertTrue(result.success)
                self.assertEqual(result.data["path"], str(paths.user_config))
                self.assertTrue(paths.user_config.exists())

    def test_writes_workflow_log_to_user_log_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {APP_HOME_ENV: str(Path(tmpdir) / "app")}, clear=False):
                paths = ensure_app_directories()
                WorkflowLogger(paths.logs_dir).write(
                    {"file": "example.txt", "status": "success"}
                )

                log_path = paths.logs_dir / "workflow.jsonl"
                self.assertTrue(log_path.exists())
                self.assertIn("example.txt", log_path.read_text(encoding="utf-8"))

    def test_reads_packaged_resources(self):
        resource = resource_path("default_config.json")
        config = load_resource_json("default_config.json")

        self.assertTrue(resource.exists())
        self.assertIn("rules", config)

    def test_startup_check_and_gui_entry_import(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {APP_HOME_ENV: str(Path(tmpdir) / "app")}, clear=False):
                result = startup_check()
                ensure_user_config()
                module = importlib.import_module("offline_anonymizer.gui.app")

                self.assertTrue(result.ok)
                self.assertTrue(result.paths.user_config.exists())
                self.assertTrue(hasattr(module, "main"))


if __name__ == "__main__":
    unittest.main()
