import unittest

from govease_ai import ProcedureAssistant

from backend.app.services.chat import (
    _asks_about_fee,
    _fee_guard_answer,
    _general_explanation_answer,
    _is_general_explanatory_query,
)


class ChatGuardTests(unittest.TestCase):
    assistant = ProcedureAssistant()

    def test_detects_general_residence_explanation_queries(self) -> None:
        self.assertTrue(_is_general_explanatory_query("thuong tru va tam tru khac nhau the nao"))

    def test_detects_general_birth_explanation_queries(self) -> None:
        self.assertTrue(_is_general_explanatory_query("khai sinh la gi, giai thich de hieu"))

    def test_general_explanation_mentions_residence_terms(self) -> None:
        answer = _general_explanation_answer("thuong tru tam tru khac nhau the nao")
        self.assertIn("Thường trú", answer)
        self.assertIn("Tạm trú", answer)

    def test_fee_guard_detects_fee_question(self) -> None:
        self.assertTrue(_asks_about_fee("dang ky tam tru mat bao nhieu tien"))

    def test_fee_guard_refuses_to_invent_missing_fee(self) -> None:
        answer = _fee_guard_answer("1.004194", self.assistant)
        self.assertIsNotNone(answer)
        self.assertIn("chưa thấy mức phí", answer.lower())

    def test_fee_guard_handles_missing_procedure(self) -> None:
        answer = _fee_guard_answer(None, self.assistant)
        self.assertIn("chưa chốt đủ chắc", answer.lower())


if __name__ == "__main__":
    unittest.main()
