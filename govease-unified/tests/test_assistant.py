from __future__ import annotations

import json
import unittest
from pathlib import Path

from govease_ai import ProcedureAssistant


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_test_cases(filename: str) -> list[dict]:
    candidates = [
        PROJECT_ROOT / "data" / "test_cases" / filename,
        PROJECT_ROOT.parent / "data" / "test_cases" / filename,
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Could not find fixture {filename} in: {candidates}")


class ProcedureAssistantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.assistant = ProcedureAssistant()
        cls.intake_cases = _load_test_cases("intake_cases.json")

    def test_generated_intake_cases_route_to_expected_procedure(self) -> None:
        for case in self.intake_cases:
            with self.subTest(case=case["id"]):
                result = self.assistant.guided_intake(case["user_need"])
                self.assertFalse(result["needs_clarification"], result)
                self.assertEqual(case["expected_procedure_code"], result["procedure"]["code"])

    def test_intake_response_contains_checklist_and_citations(self) -> None:
        result = self.assistant.guided_intake("Tôi thuê nhà và cần đăng ký tạm trú")
        self.assertEqual("1.004194", result["procedure"]["code"])
        self.assertGreaterEqual(len(result["checklist"]["documents"]), 2)
        self.assertGreaterEqual(len(result["checklist"]["steps"]), 2)
        self.assertTrue(result["sources"])
        self.assertTrue(all(source["source_url"] for source in result["sources"]))

    def test_birth_hospital_answer_omits_unmentioned_special_case_documents(self) -> None:
        result = self.assistant.guided_intake(
            "T\u00f4i m\u1edbi sinh con \u1edf b\u1ec7nh vi\u1ec7n, "
            "mu\u1ed1n l\u00e0m gi\u1ea5y khai sinh l\u1ea7n \u0111\u1ea7u cho b\u00e9."
        )
        answer = result["answer"].lower()
        self.assertEqual("1.001193", result["procedure"]["code"])
        self.assertIn("nh\u1eadn k\u1ebft qu\u1ea3", answer)
        self.assertNotIn("c\u00f2n 1 b\u01b0\u1edbc", answer)
        self.assertNotIn("tr\u1ebb b\u1ecb b\u1ecf r\u01a1i", answer)

    def test_birth_general_checklist_answer_includes_conditional_documents(self) -> None:
        result = self.assistant.guided_intake(
            "Con t\u00f4i v\u1eeba sinh, t\u00f4i c\u1ea7n bi\u1ebft h\u1ed3 s\u01a1 khai sinh g\u1ed3m gi\u1ea5y t\u1edd g\u00ec."
        )
        answer = result["answer"].lower()
        self.assertEqual("1.001193", result["procedure"]["code"])
        self.assertIn("gi\u1ea5y t\u1edd ch\u1ec9 c\u1ea7n n\u1ebfu", answer)
        self.assertIn("tr\u1ebb b\u1ecb b\u1ecf r\u01a1i", answer)

    def test_birth_special_case_answer_includes_matching_conditional_document(self) -> None:
        result = self.assistant.guided_intake(
            "L\u00e0m khai sinh cho em b\u00e9 b\u1ecb b\u1ecf r\u01a1i th\u00ec c\u1ea7n chu\u1ea9n b\u1ecb th\u00eam g\u00ec?"
        )
        answer = result["answer"].lower()
        self.assertEqual("1.001193", result["procedure"]["code"])
        self.assertIn("b\u1ecf r\u01a1i", answer)
        self.assertIn("bi\u00ean b\u1ea3n", answer)

    def test_ambiguous_intake_returns_stable_question_id(self) -> None:
        result = self.assistant.guided_intake("Tôi cần hỗ trợ thủ tục")
        self.assertTrue(result["needs_clarification"])
        self.assertEqual("procedure-domain", result["clarifying_question_id"])
        self.assertTrue(result["clarifying_question"])

    def test_answered_clarification_completes_selected_procedure(self) -> None:
        result = self.assistant.guided_intake(
            "Đăng ký khai sinh lần đầu cho con mới sinh",
            procedure_identifier="1.001193",
            answers={"q-case-type": "Đăng ký khai sinh lần đầu"},
        )
        self.assertFalse(result["needs_clarification"])
        self.assertEqual(
            {"q-case-type": "Đăng ký khai sinh lần đầu"},
            result["answers"],
        )

    def test_out_of_scope_need_is_not_assigned_to_arbitrary_catalog_record(self) -> None:
        result = self.assistant.guided_intake("Tôi muốn xin giấy phép xây dựng nhà ở")
        selected = (result.get("procedure") or {}).get("code")
        self.assertIn(selected, {None, "1.001193", "1.004194"})
        if selected is not None:
            self.assertTrue(result["needs_clarification"])


if __name__ == "__main__":
    unittest.main()
