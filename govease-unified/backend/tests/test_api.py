import os
import unittest

from fastapi.testclient import TestClient

os.environ["CORS_ORIGINS"] = "http://localhost:3000,https://gov-ease-ai.vercel.app"

from backend.app.main import app


class ApiTests(unittest.TestCase):
    client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(200, response.status_code)
        self.assertEqual("ok", response.json()["status"])

    def test_production_frontend_cors_preflight(self) -> None:
        response = self.client.options(
            "/api/v1/intake",
            headers={
                "Origin": "https://gov-ease-ai.vercel.app",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            "https://gov-ease-ai.vercel.app",
            response.headers.get("access-control-allow-origin"),
        )

    def test_intake(self) -> None:
        response = self.client.post("/api/intake", json={"message": "Tôi cần đăng ký tạm trú"})
        self.assertEqual(200, response.status_code)
        self.assertEqual("1.004194", response.json()["procedure"]["code"])

    def test_v1_intake_preserves_clarification_answers(self) -> None:
        response = self.client.post(
            "/api/v1/intake",
            json={
                "message": "Đăng ký khai sinh lần đầu",
                "procedure_code": "1.001193",
                "answers": {"q-case-type": "Đăng ký khai sinh lần đầu"},
            },
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual("completed", response.json()["status"])
        self.assertEqual(
            "Đăng ký khai sinh lần đầu",
            response.json()["answers"]["q-case-type"],
        )

    def test_v1_intake_workflow_birth_can_finish_statefully(self) -> None:
        first = self.client.post(
            "/api/v1/intake",
            json={"message": "Tôi muốn làm khai sinh mới có yếu tố nước ngoài"},
        )
        self.assertEqual(200, first.status_code)
        first_payload = first.json()
        self.assertEqual("needs_clarification", first_payload["status"])
        self.assertEqual("birth_registration", first_payload["domain_key"])
        self.assertEqual("birth_location", first_payload["current_node_id"])
        self.assertTrue(first_payload["quick_replies"])

        second = self.client.post(
            "/api/v1/intake",
            json={"session_id": first_payload["session_id"], "message": "trong nước"},
        )
        self.assertEqual(200, second.status_code)
        second_payload = second.json()
        self.assertEqual("needs_clarification", second_payload["status"])
        self.assertEqual("birth_parent_recognition", second_payload["current_node_id"])

    def test_v1_intake_workflow_residence_can_finish_statefully(self) -> None:
        first = self.client.post(
            "/api/v1/intake",
            json={"message": "Tôi muốn đăng ký tạm trú"},
        )
        self.assertEqual(200, first.status_code)
        payload = first.json()
        self.assertEqual("completed", payload["status"])
        self.assertEqual("1.004194", payload["procedure"]["code"])

    def test_v1_intake_understands_direct_permanent_residence_request(self) -> None:
        response = self.client.post(
            "/api/v1/intake",
            json={"message": "Toi muon dang ky thuong tru"},
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("needs_clarification", payload["status"])
        self.assertEqual("residence_management", payload["domain_key"])
        self.assertEqual("residence_place_type", payload["current_node_id"])

    def test_v1_intake_owned_home_does_not_fall_into_missing_preconfirmation_route(self) -> None:
        first = self.client.post(
            "/api/v1/intake",
            json={"message": "Toi nghi lai roi toi muon lam thuong tru"},
        )
        self.assertEqual(200, first.status_code)
        first_payload = first.json()
        self.assertEqual("needs_clarification", first_payload["status"])
        self.assertEqual("residence_place_type", first_payload["current_node_id"])

        second = self.client.post(
            "/api/v1/intake",
            json={"session_id": first_payload["session_id"], "message": "owned_home"},
        )
        self.assertEqual(200, second.status_code)
        second_payload = second.json()
        self.assertEqual("completed", second_payload["status"])
        self.assertEqual("1.004222", second_payload["procedure"]["code"])
        self.assertEqual("register_permanent", second_payload["workflow_state"]["slots"]["residence_goal"])
        self.assertEqual(
            "ready_for_main_registration",
            second_payload["workflow_state"]["slots"]["need_precondition_confirmation"],
        )

    def test_v1_intake_can_infer_birth_workflow_from_bhyt_for_child(self) -> None:
        response = self.client.post(
            "/api/v1/intake",
            json={"message": "toi muon lam bao hiem y te cho con toi"},
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("needs_clarification", payload["status"])
        self.assertEqual("birth_registration", payload["domain_key"])
        self.assertEqual("birth_location", payload["current_node_id"])
        self.assertEqual("new_registration", payload["answers"]["request_type"])
        self.assertEqual("bhyt_only", payload["answers"]["wants_linked_bundle"])

    def test_v1_intake_can_complete_abroad_birth_consular_from_one_message(self) -> None:
        response = self.client.post(
            "/api/v1/intake",
            json={"message": "Toi muon lam khai sinh moi cho con sinh o Nhat, lam tai co quan dai dien Viet Nam"},
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("completed", payload["status"])
        self.assertEqual("birth_registration", payload["domain_key"])
        self.assertEqual("1.001020", payload["procedure"]["code"])

    def test_v1_intake_can_switch_domain_mid_session(self) -> None:
        first = self.client.post(
            "/api/v1/intake",
            json={"message": "residence_management"},
        )
        self.assertEqual(200, first.status_code)
        first_payload = first.json()
        self.assertEqual("needs_clarification", first_payload["status"])
        self.assertEqual("residence_management", first_payload["domain_key"])

        second = self.client.post(
            "/api/v1/intake",
            json={
                "session_id": first_payload["session_id"],
                "message": "Tôi nghĩ là tôi biết mình cần làm gì rồi, tôi làm giấy khai sinh mới",
            },
        )
        self.assertEqual(200, second.status_code)
        second_payload = second.json()
        self.assertEqual("needs_clarification", second_payload["status"])
        self.assertEqual("birth_registration", second_payload["domain_key"])
        self.assertEqual("birth_location", second_payload["current_node_id"])

    def test_v1_catalog_and_form_schema(self) -> None:
        catalog = self.client.get("/api/v1/procedures")
        self.assertEqual(200, catalog.status_code)
        self.assertEqual(2, catalog.json()["total"])
        schema = self.client.get("/api/v1/procedures/1.004194/form-schema")
        self.assertEqual(200, schema.status_code)
        self.assertTrue(schema.json()["fields"])

    def test_v1_errors_have_request_id(self) -> None:
        response = self.client.get("/api/v1/procedures/not-found")
        self.assertEqual(404, response.status_code)
        self.assertEqual("PROCEDURE_NOT_FOUND", response.json()["error"]["code"])
        self.assertTrue(response.json()["error"]["request_id"])


if __name__ == "__main__":
    unittest.main()
