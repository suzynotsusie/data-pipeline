import unittest

from backend.app.services.workflow_intake import WorkflowIntakeService


class _FakeRetriever:
    def __init__(self, default_code: str | None = None, default_score: float = 0.0) -> None:
        self.default_code = default_code
        self.default_score = default_score

    def classify(self, message: str) -> tuple[str | None, float]:
        return self.default_code, self.default_score


class _FakeAssistant:
    def __init__(self, *, code: str | None = None, score: float = 0.0) -> None:
        self.model_config = object()
        self.retriever = _FakeRetriever(code, score)
        self.guided_calls: list[tuple[str, str | None, dict]] = []

    def guided_intake(self, user_need: str, procedure_identifier: str | None = None, answers: dict | None = None) -> dict:
        self.guided_calls.append((user_need, procedure_identifier, answers or {}))
        return {
            "procedure": {
                "id": procedure_identifier or "stub",
                "code": procedure_identifier,
                "title": "Stub procedure",
                "source_url": "",
                "detail_level": "workflow_index",
            },
            "checklist": {"documents": [], "conditional_documents": [], "steps": []},
            "examples": [],
            "common_errors": [],
            "sources": [],
            "needs_clarification": False,
            "confidence": 1.0,
            "answers": answers or {},
        }


class _FakeIntentParser:
    def __init__(self, result: dict | None):
        self.result = result

    def parse(self, user_message: str, **_: object) -> dict | None:
        return self.result


class WorkflowRouteGuardTests(unittest.TestCase):
    def test_employment_support_ticket_does_not_drift_into_retirement(self) -> None:
        assistant = _FakeAssistant()
        service = WorkflowIntakeService(assistant, intent_parser=_FakeIntentParser({"domain_key": "unknown", "confidence": 0.0, "slot_updates": {}}))

        result = service.handle("Toi can lam thu tuc ho tro tien ve xe cho nguoi lao dong")

        self.assertEqual("completed", result["status"])
        self.assertEqual("viec_lam", result["domain_key"])
        self.assertEqual("1.012474", result["procedure"]["code"])

    def test_work_holiday_issue_is_not_confused_with_reissue(self) -> None:
        assistant = _FakeAssistant()
        service = WorkflowIntakeService(assistant, intent_parser=_FakeIntentParser({"domain_key": "unknown", "confidence": 0.0, "slot_updates": {}}))

        result = service.handle("Toi can lam thu tuc cap giay phep lam viec trong ky nghi cho cong dan Niu-Di-Lan")

        self.assertEqual("completed", result["status"])
        self.assertEqual("viec_lam", result["domain_key"])
        self.assertEqual("2.000731", result["procedure"]["code"])

    def test_driver_license_first_issue_is_not_confused_with_exchange(self) -> None:
        assistant = _FakeAssistant()
        service = WorkflowIntakeService(assistant, intent_parser=_FakeIntentParser({"domain_key": "unknown", "confidence": 0.0, "slot_updates": {}}))

        result = service.handle("Toi muon thi va duoc cap bang lai o to lan dau")

        self.assertEqual("completed", result["status"])
        self.assertEqual("phuong_tien_nguoi_lai", result["domain_key"])
        self.assertEqual("3.000346", result["procedure"]["code"])

    def test_guardianship_domain_beats_generic_residence_keyword(self) -> None:
        assistant = _FakeAssistant()
        service = WorkflowIntakeService(assistant, intent_parser=_FakeIntentParser({"domain_key": "unknown", "confidence": 0.0, "slot_updates": {}}))

        result = service.handle("Toi can lam thu tuc dang ky viec giam ho giua cong dan Viet Nam cu tru o nuoc ngoai voi nhau")

        self.assertEqual("completed", result["status"])
        self.assertEqual("hon_nhan_gia_dinh", result["domain_key"])
        self.assertEqual("2.000560", result["procedure"]["code"])

    def test_broad_newborn_question_does_not_lock_specific_child_route(self) -> None:
        assistant = _FakeAssistant(code="1.000689", score=0.97)
        parser = _FakeIntentParser(
            {
                "domain_key": "co_con_nho",
                "confidence": 0.97,
                "slot_updates": {
                    "subdomain_key": "khai_sinh",
                    "operation_key": "thu_tuc_dang_ky_khai_sinh_ket_hop_dang_ky_nhan_cha_me_con",
                },
            }
        )
        service = WorkflowIntakeService(assistant, intent_parser=parser)

        result = service.handle("toi moi sinh con nen lam thu tuc gi")

        self.assertEqual("needs_clarification", result["status"])
        self.assertEqual("co_con_nho", result["domain_key"])
        self.assertEqual("child_operation", result["current_node_id"])
        self.assertEqual("khai_sinh", result["answers"]["subdomain_key"])
        self.assertNotIn("operation_key", result["answers"])
        self.assertFalse(assistant.guided_calls)
        self.assertGreaterEqual(len(result["quick_replies"]), 3)

    def test_specific_child_request_can_still_complete_directly(self) -> None:
        assistant = _FakeAssistant(code="1.000689", score=0.97)
        parser = _FakeIntentParser(
            {
                "domain_key": "co_con_nho",
                "confidence": 0.97,
                "slot_updates": {
                    "subdomain_key": "khai_sinh",
                    "operation_key": "thu_tuc_dang_ky_khai_sinh_ket_hop_dang_ky_nhan_cha_me_con",
                },
            }
        )
        service = WorkflowIntakeService(assistant, intent_parser=parser)

        result = service.handle(
            "toi muon lam khai sinh ket hop nhan cha cho con",
            preferred_domain_key="co_con_nho",
            preferred_subdomain_key="khai_sinh",
        )

        self.assertEqual("completed", result["status"])
        self.assertEqual("co_con_nho", result["domain_key"])
        self.assertEqual("1.000689", result["procedure"]["code"])
        self.assertEqual(1, len(assistant.guided_calls))


if __name__ == "__main__":
    unittest.main()
