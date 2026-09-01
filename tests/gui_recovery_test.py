import importlib.util
import tempfile
import unittest
from pathlib import Path

from offline_anonymizer.services import DocumentService


DOCX_AVAILABLE = importlib.util.find_spec("docx") is not None


class GuiRecoveryFlowTest(unittest.TestCase):
    @unittest.skipUnless(DOCX_AVAILABLE, "python-docx is not installed")
    def test_recover_masked_document_and_mapping_exports_docx(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_file = root / "example.txt"
            output_dir = root / "outputs"
            recovery_dir = root / "recovery"
            input_file.write_text("北京科技有限公司收入500万元", encoding="utf-8")
            processed = DocumentService().process_file(
                input_file,
                output_dir,
                formats=["docx"],
            )

            recovered = DocumentService().recover_document(
                processed.data["documents"][0],
                processed.data["mapping"],
                recovery_dir,
                formats=["docx"],
            )

            output = Path(recovered.data["documents"][0])
            output_exists = output.exists()

        self.assertTrue(recovered.success)
        self.assertTrue(output_exists)
        self.assertTrue(str(output).endswith(".docx"))

    def test_recover_after_plain_text_edit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_file = root / "example.txt"
            output_dir = root / "outputs"
            recovery_dir = root / "recovery"
            input_file.write_text("北京科技有限公司收入500万元", encoding="utf-8")
            processed = DocumentService().process_file(
                input_file,
                output_dir,
                formats=["txt"],
            )
            masked_path = Path(processed.data["documents"][0])
            masked_path.write_text(
                masked_path.read_text(encoding="utf-8") + "，新增项目",
                encoding="utf-8",
            )

            recovered = DocumentService().recover_document(
                masked_path,
                processed.data["mapping"],
                recovery_dir,
                formats=["txt"],
            )
            text = Path(recovered.data["documents"][0]).read_text(encoding="utf-8")

        self.assertTrue(recovered.success)
        self.assertIn("北京科技有限公司收入500万元，新增项目", text)

    def test_deleted_token_does_not_block_recovery(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_file = root / "example.txt"
            output_dir = root / "outputs"
            recovery_dir = root / "recovery"
            input_file.write_text("北京科技有限公司收入500万元", encoding="utf-8")
            processed = DocumentService().process_file(
                input_file,
                output_dir,
                formats=["txt"],
            )
            masked_path = Path(processed.data["documents"][0])
            masked_path.write_text("北京科技有限公司收入", encoding="utf-8")

            recovered = DocumentService().recover_document(
                masked_path,
                processed.data["mapping"],
                recovery_dir,
                formats=["txt"],
            )
            text = Path(recovered.data["documents"][0]).read_text(encoding="utf-8")

        self.assertTrue(recovered.success)
        self.assertIn("北京科技有限公司收入", text)
        self.assertNotIn("500万元", text)
        self.assertIn("unused_tokens", recovered.data["report"])
        self.assertEqual(recovered.data["report"]["unused_tokens"], 1)

    def test_unknown_token_returns_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_file = root / "example.txt"
            output_dir = root / "outputs"
            recovery_dir = root / "recovery"
            input_file.write_text("北京科技有限公司收入500万元", encoding="utf-8")
            processed = DocumentService().process_file(
                input_file,
                output_dir,
                formats=["txt"],
            )
            masked_path = Path(processed.data["documents"][0])
            masked_path.write_text("[企业999]收入[金额001]", encoding="utf-8")

            recovered = DocumentService().recover_document(
                masked_path,
                processed.data["mapping"],
                recovery_dir,
                formats=["txt"],
            )
            report_path = Path(recovered.data["error_report"])
            report_exists = report_path.exists()
            recovery_folder_exists = (recovery_dir / "example 恢复文件").exists()

        self.assertFalse(recovered.success)
        self.assertEqual(recovered.error["code"], "RECOVERY_ERROR")
        self.assertGreater(recovered.data["report"]["missing_tokens"], 0)
        self.assertTrue(report_exists)
        self.assertFalse(recovery_folder_exists)


if __name__ == "__main__":
    unittest.main()
