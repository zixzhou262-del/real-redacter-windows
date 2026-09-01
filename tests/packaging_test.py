import unittest
from pathlib import Path

from offline_anonymizer.version import APP_NAME, VERSION


class PackagingConfigTest(unittest.TestCase):
    def test_pyinstaller_spec_exists_and_points_to_gui_entry(self):
        spec_path = Path("build/offline_anonymizer.spec")
        spec = spec_path.read_text(encoding="utf-8")

        self.assertTrue(spec_path.exists())
        self.assertIn('ENTRY_SCRIPT = PROJECT_ROOT / "offline_anonymizer" / "gui" / "app.py"', spec)
        self.assertIn("offline_anonymizer/resources", spec)
        self.assertIn('collect_data_files("docx")', spec)
        self.assertIn('APP_NAME = "ReaL Redacter"', spec)
        self.assertIn('name=f"{APP_NAME}.app"', spec)

    def test_app_version_is_packaging_version(self):
        self.assertEqual(APP_NAME, "ReaL Redacter")
        self.assertEqual(VERSION, "2.2.2")

    def test_windows_spec_and_workflow_match_current_release(self):
        spec = Path("build/offline_anonymizer_windows.spec").read_text(encoding="utf-8")
        workflow = Path(".github/workflows/build-windows.yml").read_text(encoding="utf-8")

        self.assertIn('APP_NAME = "ReaL Redacter"', spec)
        self.assertIn('APP_VERSION = "2.2.2"', spec)
        self.assertIn("windows_version_info.txt", spec)
        self.assertIn("runs-on: windows-latest", workflow)
        self.assertIn("ReaL Redacter-2.2.2-windows-x64.zip", workflow)


if __name__ == "__main__":
    unittest.main()
