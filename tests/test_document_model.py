import unittest

from offline_anonymizer.core.document import (
    Document,
    DocumentNode,
    TokenSpan,
    container_node,
    text_node,
)


class DocumentModelTest(unittest.TestCase):
    def test_document_model_can_represent_core_structures(self):
        document = Document.create(
            "report.md",
            "md",
            children=[
                container_node(
                    "heading",
                    content="贷款报告",
                    children=[text_node("贷款报告")],
                    metadata={"level": 1},
                ),
                container_node(
                    "paragraph",
                    content="[企业001]收入[金额001]",
                    children=[
                        DocumentNode.create(
                            "text",
                            content="[企业001]收入[金额001]",
                            tokens=[
                                TokenSpan(
                                    token_id="tok_company_0001",
                                    start=0,
                                    end=7,
                                )
                            ],
                        )
                    ],
                ),
                container_node(
                    "table",
                    children=[
                        container_node(
                            "table_row",
                            children=[
                                container_node(
                                    "table_cell",
                                    content="备注",
                                    children=[
                                        container_node(
                                            "paragraph",
                                            content="备注",
                                            children=[text_node("备注")],
                                        )
                                    ],
                                )
                            ],
                        )
                    ],
                ),
                container_node(
                    "code_block",
                    content="x=1",
                    children=[text_node("x=1")],
                ),
            ],
        )

        data = document.to_dict()

        self.assertEqual(data["root"]["children"][0]["node_type"], "heading")
        self.assertEqual(
            data["root"]["children"][1]["children"][0]["tokens"][0]["token_id"],
            "tok_company_0001",
        )
        self.assertEqual(
            data["root"]["children"][2]["children"][0]["children"][0]["node_type"],
            "table_cell",
        )
        self.assertIn("贷款报告", document.to_plain_text())


if __name__ == "__main__":
    unittest.main()
