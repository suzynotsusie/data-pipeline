from __future__ import annotations

import unittest

from backend.app.services.procedures import form_schema, list_procedures
from govease_ai.procedure_data import load_procedure_store


class ProcedureApiModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.store = load_procedure_store()

    def test_catalog_defaults_can_expose_detailed_pilot_procedures(self) -> None:
        items = list_procedures(self.store, detailed_only=True)
        self.assertEqual({"1.001193", "1.004194"}, {item["code"] for item in items})

    def test_form_schema_has_required_fields_and_sources(self) -> None:
        for code in ("1.001193", "1.004194"):
            with self.subTest(code=code):
                schema = form_schema(self.store.require(code))
                self.assertTrue(schema["fields"])
                self.assertTrue(any(field["required"] for field in schema["fields"]))
                self.assertTrue(all(field["source_url"] for field in schema["fields"]))

    def test_birth_form_uses_current_control_lists(self) -> None:
        schema = form_schema(self.store.require("1.001193"))
        fields = {field["path"]: field for field in schema["fields"]}
        self.assertEqual(["Nam", "Nữ"], fields["child.gender"]["options"])
        self.assertGreaterEqual(len(fields["child.birth_place"]["options"]), 34)
        self.assertIn("Cá nhân đang nuôi dưỡng trẻ", fields["requester.relationship_to_child"]["options"])
        self.assertEqual("^[0-9]{12}$", fields["mother.identity_number"]["validation"]["pattern"])
        self.assertEqual("vneid", fields["mother.identity_number"]["prefill_source"])


if __name__ == "__main__":
    unittest.main()
