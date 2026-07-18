import os
import unittest

from fastapi.testclient import TestClient

os.environ["CORS_ORIGINS"] = "http://localhost:3000,https://gov-ease-ai.vercel.app"

from backend.app.main import app


class WorkflowScenarioTests(unittest.TestCase):
    client = TestClient(app)

    def test_intake_real_world_scenarios(self) -> None:
        cases = [
            {"message": "Toi muon dang ky tam tru", "status": "completed", "code": "1.004194"},
            {"message": "Toi can dang ky tam tru cho nha tro", "status": "completed", "code": "1.004194"},
            {"message": "Toi muon gia han tam tru", "status": "completed", "code": "1.002755"},
            {"message": "Toi can gia han tam tru vi sap het han", "status": "completed", "code": "1.002755"},
            {"message": "Toi muon xoa tam tru", "status": "completed", "code": "1.010028"},
            {"message": "Toi can xoa dang ky tam tru cu", "status": "completed", "code": "1.010028"},
            {"message": "Toi muon xoa thuong tru", "status": "completed", "code": "1.003197"},
            {"message": "Toi can khai bao tam vang", "status": "completed", "code": "1.003677"},
            {"message": "Toi se vang nha mot thoi gian va can khai bao tam vang", "status": "completed", "code": "1.003677"},
            {"message": "Toi muon thong bao luu tru", "status": "completed", "code": "2.001159"},
            {"message": "Toi can bao co nguoi den o ngan han, thong bao luu tru", "status": "completed", "code": "2.001159"},
            {"message": "Toi muon tach ho", "status": "completed", "code": "1.010038"},
            {"message": "Toi can dieu chinh thong tin cu tru", "status": "completed", "code": "1.010039"},
            {"message": "Toi muon xin xac nhan thong tin cu tru", "status": "completed", "code": "1.010041"},
            {"message": "Toi can xac nhan dieu kien thuong tru khi dang o thue nha", "status": "completed", "code": "1.013314"},
            {"message": "Toi can xac nhan dieu kien thuong tru cho noi o la xe de o", "status": "completed", "code": "1.013313"},
            {"message": "Toi chua du dieu kien dang ky cu tru nhung van muon khai bao thong tin cu tru", "status": "completed", "code": "1.010040"},
            {"message": "Toi muon dang ky thuong tru", "status": "needs_clarification", "domain": "residence_management", "node": "residence_need_precondition"},
            {"message": "Toi dang o thue va muon dang ky thuong tru", "status": "needs_clarification", "domain": "residence_management", "node": "residence_need_precondition"},
            {"message": "Toi muon lam khai sinh cho con", "status": "needs_clarification", "domain": "birth_registration", "node": "birth_location"},
            {"message": "Toi muon dang ky khai sinh lan dau", "status": "needs_clarification", "domain": "birth_registration", "node": "birth_location"},
            {"message": "Lam lai giay khai sinh vi mat ban chinh", "status": "needs_clarification", "domain": "birth_registration", "node": "birth_foreign_element"},
            {"message": "Xin trich luc khai sinh", "status": "completed", "code": "2.000635"},
            {"message": "Xin ban sao giay khai sinh", "status": "completed", "code": "2.000635"},
            {"message": "Toi muon lam khai sinh moi cho con sinh o Nhat, lam tai co quan dai dien Viet Nam", "status": "completed", "code": "1.001020"},
            {"message": "Con toi sinh o My, toi muon lam khai sinh tai co quan dai dien Viet Nam", "status": "completed", "code": "1.001020"},
            {"message": "Toi can dang ky khai sinh moi trong nuoc nhung co yeu to nuoc ngoai vi me la nguoi Han Quoc", "status": "needs_clarification", "domain": "birth_registration", "node": "birth_parent_recognition"},
            {"message": "Toi can dang ky khai sinh ket hop nhan cha me con co yeu to nuoc ngoai", "status": "needs_clarification", "domain": "birth_registration", "node": "birth_request_type"},
            {"message": "Toi muon dang ky khai sinh ket hop nhan cha me con", "status": "needs_clarification", "domain": "birth_registration", "node": "birth_request_type"},
            {"message": "Toi muon ghi vao so ho tich viec da lam o nuoc ngoai", "status": "needs_clarification", "domain": "birth_registration", "node": "birth_existing_documents_context"},
            {"message": "Nguoi nay da co giay to ca nhan nhung chua co khai sinh hop le", "status": "needs_clarification", "domain": "birth_registration", "node": "birth_foreign_element"},
            {"message": "Toi muon lam khai sinh luu dong", "status": "completed", "code": "1.003583"},
            {"message": "Toi khong biet minh can lam gi, toi vua sinh em be", "status": "needs_clarification", "domain": "birth_registration", "node": "birth_request_type"},
            {"message": "toi nghiem tuc khong hieu thuong tru voi tam tru khac nhau the nao", "status": "needs_clarification", "domain": "residence_management", "node": "residence_goal"},
            {"message": "Giai thich giup toi thuong tru la gi, tam tru la gi", "status": "needs_clarification", "domain": "residence_management", "node": "residence_goal"},
            {"message": "Toi khong biet khai sinh moi khac dang ky lai the nao", "status": "needs_clarification", "domain": "birth_registration", "node": "birth_request_type"},
            {"message": "Toi khong hieu khau tru tam tru la gi", "status": "needs_clarification", "domain": "residence_management", "node": "residence_goal"},
            {"message": "Toi muon dang ky thuong tru, da du dieu kien roi", "status": "completed", "code": "1.004222"},
            {"message": "Toi muon dang ky thuong tru, toi can xin xac nhan dieu kien truoc", "status": "needs_clarification", "domain": "residence_management", "node": "residence_place_type"},
            {"message": "Toi muon dang ky thuong tru, nha do la xe de o va toi can xac nhan dieu kien", "status": "completed", "code": "1.013313"},
            {"message": "Toi da co tam tru roi va gio muon gia han", "status": "completed", "code": "1.002755"},
            {"message": "Toi muon dang ky o tam tai noi dang thue", "status": "completed", "code": "1.004194"},
            {"message": "Toi muon nhap ho khau", "status": "needs_clarification", "domain": "residence_management", "node": "residence_need_precondition"},
            {"message": "Toi muon sua thong tin cu tru bi sai", "status": "completed", "code": "1.010039"},
            {"message": "Toi can giay xac nhan cu tru", "status": "completed", "code": "1.010041"},
            {"message": "Toi can bao luu tru cho khach o lai qua dem", "status": "completed", "code": "2.001159"},
            {"message": "Toi muon bao tam vang vi sap di xa", "status": "completed", "code": "1.003677"},
            {"message": "Toi muon xoa dang ky thuong tru cu", "status": "completed", "code": "1.003197"},
            {"message": "Toi muon xoa dang ky tam tru cu", "status": "completed", "code": "1.010028"},
            {"message": "Toi muon dang ky tam tru, khong phai gia han", "status": "completed", "code": "1.004194"},
            {"message": "Toi muon lam giay khai sinh moi cho be sinh trong nuoc", "status": "needs_clarification", "domain": "birth_registration", "node": "birth_foreign_element"},
            {"message": "Toi muon lam giay khai sinh moi cho be sinh trong nuoc, bo me deu la nguoi Viet", "status": "needs_clarification", "domain": "birth_registration", "node": "birth_parent_recognition"},
            {"message": "Toi muon lam giay khai sinh moi cho be sinh trong nuoc, bo me deu la nguoi Viet, chi khai sinh thoi", "status": "completed", "code": "1.001193"},
            {"message": "Toi muon lam giay khai sinh moi cho be sinh trong nuoc, bo me deu la nguoi Viet, chi khai sinh thoi, khong lien thong", "status": "completed", "code": "1.001193"},
            {"message": "Toi muon lam khai sinh moi co yeu to nuoc ngoai o khu vuc bien gioi", "status": "needs_clarification", "domain": "birth_registration", "node": "birth_location"},
            {"message": "Toi muon lam khai sinh moi trong nuoc co yeu to nuoc ngoai o khu vuc bien gioi", "status": "needs_clarification", "domain": "birth_registration", "node": "birth_parent_recognition"},
            {"message": "Toi muon lam khai sinh moi trong nuoc co yeu to nuoc ngoai o khu vuc bien gioi, khong nhan cha me con", "status": "completed", "code": "1.000110"},
            {"message": "Toi muon lam khai sinh moi trong nuoc co yeu to nuoc ngoai, khong nhan cha me con, thong thuong", "status": "completed", "code": "2.000528"},
            {"message": "Toi muon lam khai sinh moi trong nuoc, khong co yeu to nuoc ngoai, nhan cha me con", "status": "completed", "code": "1.000689"},
        ]

        for case in cases:
            with self.subTest(message=case["message"]):
                response = self.client.post("/api/v1/intake", json={"message": case["message"]})
                self.assertEqual(200, response.status_code)
                payload = response.json()
                self.assertEqual(case["status"], payload["status"])
                if "code" in case:
                    self.assertEqual(case["code"], payload["procedure"]["code"])
                if "domain" in case:
                    self.assertEqual(case["domain"], payload["domain_key"])
                if "node" in case:
                    self.assertEqual(case["node"], payload["current_node_id"])


if __name__ == "__main__":
    unittest.main()
