from __future__ import annotations

import unittest

from backend.app.services.workflow_intake import WorkflowIntakeService
from govease_ai import ProcedureAssistant


class _FakeIntentParser:
    def __init__(self, result: dict | None):
        self.result = result
        self.calls = 0

    def parse(self, user_message: str) -> dict | None:
        self.calls += 1
        return self.result


class WorkflowIntentParserTests(unittest.TestCase):
    def test_obvious_bhyt_for_child_prefers_ai_but_keeps_safe_birth_hints(self) -> None:
        parser = _FakeIntentParser(
            {
                "domain_key": "birth_registration",
                "confidence": 0.99,
                "slot_updates": {},
            }
        )
        service = WorkflowIntakeService(ProcedureAssistant(), intent_parser=parser)

        result = service.handle("toi muon lam bhyt cho con toi")

        self.assertEqual("birth_registration", result["domain_key"])
        self.assertEqual("birth_location", result["current_node_id"])
        self.assertEqual("new_registration", result["answers"]["request_type"])
        self.assertEqual("bhyt_only", result["answers"]["wants_linked_bundle"])
        self.assertEqual(1, parser.calls)

    def test_ai_parser_is_used_when_heuristic_is_uncertain(self) -> None:
        parser = _FakeIntentParser(
            {
                "domain_key": "birth_registration",
                "confidence": 0.91,
                "slot_updates": {
                    "request_type": "new_registration",
                    "wants_linked_bundle": "bhyt_only",
                },
            }
        )
        service = WorkflowIntakeService(ProcedureAssistant(), intent_parser=parser)

        result = service.handle("toi can lam giay cho be")

        self.assertEqual(1, parser.calls)
        self.assertEqual("birth_registration", result["domain_key"])
        self.assertEqual("birth_location", result["current_node_id"])
        self.assertEqual("new_registration", result["answers"]["request_type"])

    def test_strong_residence_heuristic_is_only_a_fallback_after_ai(self) -> None:
        parser = _FakeIntentParser(
            {
                "domain_key": "unknown",
                "confidence": 0.99,
                "slot_updates": {},
            }
        )
        service = WorkflowIntakeService(ProcedureAssistant(), intent_parser=parser)

        result = service.handle("Toi muon dang ky tam tru")

        self.assertEqual("completed", result["status"])
        self.assertEqual("residence_management", result["domain_key"])
        self.assertEqual("1.004194", result["procedure"]["code"])
        self.assertEqual(1, parser.calls)

    def test_ai_parser_is_not_used_after_domain_is_already_chosen(self) -> None:
        parser = _FakeIntentParser(
            {
                "domain_key": "unknown",
                "confidence": 0.2,
                "slot_updates": {},
            }
        )
        service = WorkflowIntakeService(ProcedureAssistant(), intent_parser=parser)

        first = service.handle("Toi muon dang ky thuong tru")
        self.assertEqual(1, parser.calls)

        second = service.handle("nha thue", session_id=first["session_id"])

        self.assertEqual(1, parser.calls)
        self.assertEqual("residence_management", second["domain_key"])
        self.assertEqual("residence_need_precondition", second["current_node_id"])


if __name__ == "__main__":
    unittest.main()
