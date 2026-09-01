import tempfile
import unittest
from pathlib import Path

from offline_anonymizer.anonymizer.engine import AnonymizationEngine
from offline_anonymizer.anonymizer.token_registry import TokenRegistry
from offline_anonymizer.core.document import Document, container_node, text_node
from offline_anonymizer.renderer.html_renderer import HtmlRenderer
from offline_anonymizer.security.mapping_crypto import read_mapping


def document_from_text(text):
    return Document.create(
        "report.txt",
        "txt",
        children=[
            container_node(
                "paragraph",
                content=text,
                children=[text_node(text)],
            )
        ],
    )


class HtmlRendererTest(unittest.TestCase):
    def test_renderer_outputs_token_anchors(self):
        registry = TokenRegistry()
        anonymized = AnonymizationEngine(registry=registry).anonymize(
            document_from_text("北京科技有限公司获得500万元贷款")
        )

        result = HtmlRenderer().render(anonymized, registry)

        self.assertIn('class="masked-token token-company"', result.html)
        self.assertIn('data-token-id="company_001"', result.html)
        self.assertIn('data-token-type="company"', result.html)
        self.assertIn('title="类型：company | Token ID：company_001"', result.html)
        self.assertIn('data-token-id="money_001"', result.html)
        self.assertIn('class="masked-token token-money"', result.html)
        self.assertIn("[企业001]", result.html)
        self.assertNotIn("北京科技有限公司获得", result.html)
        self.assertEqual(
            result.mapping["company_001"]["original"],
            "北京科技有限公司",
        )
        self.assertEqual(result.mapping["money_001"]["original"], "500万元")

    def test_renderer_writes_html_and_separate_mapping(self):
        registry = TokenRegistry()
        anonymized = AnonymizationEngine(registry=registry).anonymize(
            document_from_text("北京科技有限公司获得500万元贷款")
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "report_masked.html"
            mapping_path = Path(tmpdir) / "report_mapping.json"
            HtmlRenderer().write(anonymized, registry, html_path, mapping_path)

            html = html_path.read_text(encoding="utf-8")
            mapping = read_mapping(mapping_path)

        self.assertIn('data-mapping-src="report_mapping.json"', html)
        self.assertIn('data-token-id="company_001"', html)
        self.assertNotIn('"original": "北京科技有限公司"', html)
        self.assertEqual(mapping["company_001"]["type"], "company")
        self.assertEqual(mapping["company_001"]["original"], "北京科技有限公司")

    def test_renderer_preserves_document_structures(self):
        registry = TokenRegistry()
        document = Document.create(
            "report.md",
            "md",
            children=[
                container_node(
                    "heading",
                    content="项目介绍",
                    children=[text_node("项目介绍")],
                    metadata={"level": 1},
                ),
                container_node(
                    "list",
                    children=[
                        container_node(
                            "list_item",
                            content="北京科技有限公司",
                            children=[text_node("北京科技有限公司")],
                        )
                    ],
                    metadata={"list_type": "bullet"},
                ),
                container_node(
                    "table",
                    children=[
                        container_node(
                            "table_row",
                            children=[
                                container_node(
                                    "table_cell",
                                    content="500万元",
                                    children=[
                                        container_node(
                                            "paragraph",
                                            content="500万元",
                                            children=[text_node("500万元")],
                                        )
                                    ],
                                )
                            ],
                        )
                    ],
                ),
                container_node(
                    "code_block",
                    content="secret = '北京科技有限公司'",
                    children=[text_node("secret = '北京科技有限公司'")],
                ),
            ],
        )
        anonymized = AnonymizationEngine(registry=registry).anonymize(document)

        html = HtmlRenderer().render(anonymized, registry).html

        self.assertIn("<h1", html)
        self.assertIn("<ul", html)
        self.assertIn("<table", html)
        self.assertIn("<pre", html)
        self.assertIn("secret = &#x27;北京科技有限公司&#x27;", html)


if __name__ == "__main__":
    unittest.main()
