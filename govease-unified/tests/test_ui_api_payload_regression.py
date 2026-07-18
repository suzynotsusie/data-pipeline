from __future__ import annotations

import json
import unittest
from collections import defaultdict
from pathlib import Path

from backend.app.services.procedures import form_schema, procedure_detail
from govease_ai.procedure_data import load_procedure_store


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_REPORT_PATH = PROJECT_ROOT.parent / "data" / "procedure_payloads" / "build_report.json"


class UiApiPayloadRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.store = load_procedure_store()
        report = json.loads(PAYLOAD_REPORT_PATH.read_text(encoding="utf-8"))
        cls.sample_codes_by_group: dict[str, list[str]] = {}
        grouped: dict[str, list[dict]] = defaultdict(list)
        for item in report.get("outputs", []):
            if item.get("group_key"):
                grouped[str(item["group_key"])].append(item)
        for group_key, items in grouped.items():
            cls.sample_codes_by_group[group_key] = [item["procedure_code"] for item in items[:3]]

    def test_payload_report_covers_all_11_groups(self) -> None:
        self.assertEqual(
            {
                "co_con_nho",
                "cu_tru_giay_to",
                "dien_luc_nha_o_dat_dai",
                "giai_quyet_khieu_kien",
                "hoc_tap",
                "hon_nhan_gia_dinh",
                "huu_tri",
                "nguoi_than_qua_doi",
                "phuong_tien_nguoi_lai",
                "suc_khoe_y_te",
                "viec_lam",
            },
            set(self.sample_codes_by_group),
        )

    def test_representative_payloads_have_detail_and_form_shape(self) -> None:
        for group_key, procedure_codes in sorted(self.sample_codes_by_group.items()):
            for procedure_code in procedure_codes:
                with self.subTest(group_key=group_key, procedure_code=procedure_code):
                    record = self.store.require(procedure_code)
                    detail = procedure_detail(record)
                    schema = form_schema(record)

                    self.assertEqual(procedure_code, detail["code"])
                    self.assertIn("checklist", detail)
                    self.assertIn("guidance", detail)
                    self.assertIn("next_steps", detail)
                    self.assertIsInstance(detail["checklist"]["steps"], list)
                    self.assertIsInstance(detail["checklist"]["documents"], list)
                    self.assertIsInstance(detail["checklist"]["conditional_documents"], list)
                    self.assertIsInstance(detail["clarifying_questions"], list)
                    self.assertTrue(detail["provenance"])

                    self.assertEqual(procedure_code, schema["procedure"]["code"])
                    self.assertIsInstance(schema["fields"], list)
                    self.assertTrue(schema["fields"], f"Missing fields for {procedure_code}")
                    self.assertTrue(any(field["required"] for field in schema["fields"]), procedure_code)
                    self.assertTrue(all("source_url" in field for field in schema["fields"]), procedure_code)
                    self.assertTrue(all(field["path"] for field in schema["fields"]), procedure_code)
                    self.assertTrue(all(field["label"] for field in schema["fields"]), procedure_code)

    def test_payload_records_no_longer_depend_on_form_fallbacks(self) -> None:
        for group_key, procedure_codes in sorted(self.sample_codes_by_group.items()):
            for procedure_code in procedure_codes:
                with self.subTest(group_key=group_key, procedure_code=procedure_code):
                    record = self.store.require(procedure_code)
                    self.assertTrue(record.data.get("input_fields"), procedure_code)
                    self.assertTrue(record.data.get("guidance"), procedure_code)
                    self.assertTrue(record.data.get("next_steps"), procedure_code)


if __name__ == "__main__":
    unittest.main()
