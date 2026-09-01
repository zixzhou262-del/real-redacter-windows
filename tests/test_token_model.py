import unittest

from offline_anonymizer.anonymizer.token_registry import TokenRegistry


class TokenModelTest(unittest.TestCase):
    def test_registry_reuses_same_token_for_same_type_and_value(self):
        registry = TokenRegistry()

        first_id = registry.create_token("company", "北京科技有限公司")
        second_id = registry.create_token("company", " 北京科技有限公司 ")

        self.assertEqual(first_id, second_id)
        self.assertEqual(first_id, "company_001")
        self.assertEqual(registry.get_token(first_id).masked_value, "[企业001]")

    def test_registry_keeps_different_types_separate(self):
        registry = TokenRegistry()

        number_id = registry.create_token("number", "2025")
        date_id = registry.create_token("date", "2025")

        self.assertNotEqual(number_id, date_id)
        self.assertEqual(registry.get_token(number_id).masked_value, "[数字001]")
        self.assertEqual(registry.get_token(date_id).masked_value, "[日期001]")

    def test_registry_can_restore_and_export_mapping(self):
        registry = TokenRegistry()
        token_id = registry.create_token("money", "500万元")

        self.assertEqual(registry.restore_token(token_id), "500万元")
        mapping = registry.export_mapping()
        self.assertEqual(mapping["money_001"]["original_value"], "500万元")


if __name__ == "__main__":
    unittest.main()
