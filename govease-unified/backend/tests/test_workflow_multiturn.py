import os
import unittest

from fastapi.testclient import TestClient

os.environ["CORS_ORIGINS"] = "http://localhost:3000,https://gov-ease-ai.vercel.app"

from backend.app.main import app


class WorkflowMultiTurnTests(unittest.TestCase):
    client = TestClient(app)

    def _start(self, message: str) -> dict:
        response = self.client.post("/api/v1/intake", json={"message": message})
        self.assertEqual(200, response.status_code)
        return response.json()

    def _next(self, session_id: str, message: str) -> dict:
        response = self.client.post("/api/v1/intake", json={"session_id": session_id, "message": message})
        self.assertEqual(200, response.status_code)
        return response.json()

    def test_birth_standard_domestic_full_path(self) -> None:
        first = self._start("Toi muon lam khai sinh cho con")
        self.assertEqual("birth_registration", first["domain_key"])
        self.assertEqual("birth_location", first["current_node_id"])

        second = self._next(first["session_id"], "trong nuoc")
        self.assertEqual("birth_foreign_element", second["current_node_id"])

        third = self._next(first["session_id"], "khong")
        self.assertEqual("birth_parent_recognition", third["current_node_id"])

        fourth = self._next(first["session_id"], "khong")
        self.assertEqual("birth_linked_services", fourth["current_node_id"])

        fifth = self._next(first["session_id"], "khong lien thong")
        self.assertEqual("completed", fifth["status"])
        self.assertEqual("1.001193", fifth["procedure"]["code"])

    def test_birth_foreign_element_border_area_path(self) -> None:
        first = self._start("Toi muon lam khai sinh moi")
        second = self._next(first["session_id"], "trong nuoc")
        third = self._next(first["session_id"], "co yeu to nuoc ngoai")
        fourth = self._next(first["session_id"], "khong")
        final = self._next(first["session_id"], "khu vuc bien gioi")

        self.assertEqual("completed", final["status"])
        self.assertEqual("1.000110", final["procedure"]["code"])
        self.assertEqual("border_area", final["answers"]["service_channel"])

    def test_birth_parent_recognition_foreign_element_path(self) -> None:
        first = self._start("Toi muon lam khai sinh cho con")
        second = self._next(first["session_id"], "trong nuoc")
        third = self._next(first["session_id"], "co")
        final = self._next(first["session_id"], "co nhan cha me con")

        self.assertEqual("completed", final["status"])
        self.assertEqual("1.001695", final["procedure"]["code"])

    def test_birth_explain_mode_then_choose_new_registration(self) -> None:
        first = self._start("Toi khong biet khai sinh moi khac dang ky lai the nao")
        self.assertEqual("birth_registration", first["domain_key"])
        self.assertEqual("birth_request_type", first["current_node_id"])
        self.assertIn("gợi ý rất ngắn", first["clarifying_question"])

        second = self._next(first["session_id"], "khai sinh moi")
        self.assertEqual("birth_location", second["current_node_id"])

    def test_residence_temporary_extend_multiturn(self) -> None:
        first = self._start("residence_management")
        self.assertEqual("residence_management", first["domain_key"])
        self.assertEqual("res_binary_register", first["current_node_id"])

        second = self._next(first["session_id"], "co")
        self.assertEqual("res_binary_long_term", second["current_node_id"])

        third = self._next(first["session_id"], "khong")
        self.assertEqual("res_binary_extend", third["current_node_id"])

        final = self._next(first["session_id"], "co")
        self.assertEqual("completed", final["status"])
        self.assertEqual("1.002755", final["procedure"]["code"])

    def test_residence_permanent_ready_for_main_registration(self) -> None:
        first = self._start("Toi muon dang ky thuong tru")
        self.assertEqual("residence_place_type", first["current_node_id"])

        second = self._next(first["session_id"], "nha cua toi")
        self.assertEqual("completed", second["status"])
        self.assertEqual("1.004222", second["procedure"]["code"])

    def test_residence_permanent_ready_for_main_registration_rented_home(self) -> None:
        first = self._start("Toi muon dang ky thuong tru")
        self.assertEqual("residence_place_type", first["current_node_id"])

        second = self._next(first["session_id"], "nha thue")
        self.assertEqual("residence_need_precondition", second["current_node_id"])

        final = self._next(first["session_id"], "da du dieu kien roi")
        self.assertEqual("completed", final["status"])
        self.assertEqual("1.004222", final["procedure"]["code"])

    def test_residence_permanent_need_confirmation_rented_home(self) -> None:
        first = self._start("Toi muon dang ky thuong tru")
        second = self._next(first["session_id"], "nha thue")
        self.assertEqual("residence_need_precondition", second["current_node_id"])

        final = self._next(first["session_id"], "can xin xac nhan truoc")
        self.assertEqual("completed", final["status"])
        self.assertEqual("1.013314", final["procedure"]["code"])

    def test_birth_foreign_record_note_uses_matching_options(self) -> None:
        first = self._start("Toi muon ghi vao so ho tich viec da lam o nuoc ngoai")
        self.assertEqual("birth_registration", first["domain_key"])
        self.assertEqual("birth_existing_documents_context", first["current_node_id"])
        option_values = {item["value"] for item in first["quick_replies"]}
        self.assertEqual({"birth_only", "multi_civil_status"}, option_values)

        final = self._next(first["session_id"], "khai sinh")
        self.assertEqual("completed", final["status"])
        self.assertEqual("2.000712", final["procedure"]["code"])

    def test_residence_explain_mode_then_choose_temporary(self) -> None:
        first = self._start("Toi khong hieu thuong tru voi tam tru khac nhau the nao")
        self.assertEqual("residence_management", first["domain_key"])
        self.assertEqual("residence_goal", first["current_node_id"])
        self.assertIn("Thường trú", first["clarifying_question"])

        final = self._next(first["session_id"], "o tam")
        self.assertEqual("completed", final["status"])
        self.assertEqual("1.004194", final["procedure"]["code"])

    def test_mid_session_switch_from_residence_to_birth(self) -> None:
        first = self._start("residence_management")
        self.assertEqual("res_binary_register", first["current_node_id"])

        second = self._next(first["session_id"], "Toi doi y, toi muon lam giay khai sinh moi")
        self.assertEqual("birth_registration", second["domain_key"])
        self.assertEqual("birth_location", second["current_node_id"])

    def test_mid_session_switch_from_birth_to_residence(self) -> None:
        first = self._start("Toi muon lam khai sinh cho con")
        self.assertEqual("birth_location", first["current_node_id"])

        second = self._next(first["session_id"], "Khong, toi muon dang ky tam tru")
        self.assertEqual("completed", second["status"])
        self.assertEqual("residence_management", second["domain_key"])
        self.assertEqual("1.004194", second["procedure"]["code"])

    def test_birth_abroad_consular_multiturn_short_answers(self) -> None:
        first = self._start("Toi muon lam khai sinh cho con")
        second = self._next(first["session_id"], "o nuoc ngoai")
        final = self._next(first["session_id"], "co quan dai dien")

        self.assertEqual("completed", final["status"])
        self.assertEqual("1.001020", final["procedure"]["code"])

    def test_residence_delete_temporary_multiturn_binary_path(self) -> None:
        first = self._start("residence_management")
        second = self._next(first["session_id"], "khong")
        self.assertEqual("res_binary_remove", second["current_node_id"])

        third = self._next(first["session_id"], "co")
        self.assertEqual("res_binary_remove_type", third["current_node_id"])

        final = self._next(first["session_id"], "khong")
        self.assertEqual("completed", final["status"])
        self.assertEqual("1.010028", final["procedure"]["code"])


if __name__ == "__main__":
    unittest.main()
