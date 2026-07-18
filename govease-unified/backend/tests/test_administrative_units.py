import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ["CORS_ORIGINS"] = "http://localhost:3000,https://gov-ease-ai.vercel.app"

from backend.app.main import app
from backend.app.services.administrative_units import (
    AdministrativeUnitServiceError,
    _parse_provinces,
    _parse_units,
)


SOAP_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body><DanhMucTinhResponse xmlns="http://tempuri.org/"><DanhMucTinhResult>
    <NewDataSet xmlns=""><Table><MaTinh>01</MaTinh><TenTinh>Thành phố Hà Nội</TenTinh></Table><Table><MaTinh>79</MaTinh><TenTinh>Thành phố Hồ Chí Minh</TenTinh></Table></NewDataSet>
  </DanhMucTinhResult></DanhMucTinhResponse></soap:Body>
</soap:Envelope>""".encode("utf-8")

DISTRICT_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body><DanhMucQuanHuyenResponse xmlns="http://tempuri.org/"><DanhMucQuanHuyenResult>
    <NewDataSet xmlns=""><Table><MaQuanHuyen>001</MaQuanHuyen><TenQuanHuyen>Quận Ba Đình</TenQuanHuyen></Table></NewDataSet>
  </DanhMucQuanHuyenResult></DanhMucQuanHuyenResponse></soap:Body>
</soap:Envelope>""".encode("utf-8")


class AdministrativeUnitTests(unittest.TestCase):
    client = TestClient(app)

    def test_parse_provinces_from_soap_dataset(self) -> None:
        self.assertEqual(
            [{"code": "01", "name": "Thành phố Hà Nội"}, {"code": "79", "name": "Thành phố Hồ Chí Minh"}],
            _parse_provinces(SOAP_RESPONSE),
        )

    def test_parse_districts_from_soap_dataset(self) -> None:
        self.assertEqual(
            [{"code": "001", "name": "Quận Ba Đình"}],
            _parse_units(
                DISTRICT_RESPONSE,
                "DanhMucQuanHuyenResult",
                ("maquanhuyen", "ma_huyen", "mahuyen"),
                ("tenquanhuyen", "ten_huyen", "tenhuyen"),
            ),
        )

    @patch("backend.app.api.routes.fetch_provinces", return_value=[{"code": "01", "name": "Thành phố Hà Nội"}])
    def test_provinces_endpoint(self, _fetch) -> None:
        response = self.client.get("/api/v1/administrative-units/provinces")
        self.assertEqual(200, response.status_code)
        self.assertEqual("01", response.json()["items"][0]["code"])

    @patch("backend.app.api.routes.fetch_districts", return_value=[{"code": "001", "name": "Quận Ba Đình"}])
    def test_districts_endpoint(self, _fetch) -> None:
        response = self.client.get("/api/v1/administrative-units/districts?province_code=01")
        self.assertEqual(200, response.status_code)
        self.assertEqual("001", response.json()["items"][0]["code"])

    @patch("backend.app.api.routes.fetch_wards", return_value=[{"code": "00001", "name": "Phường Phúc Xá"}])
    def test_wards_endpoint(self, _fetch) -> None:
        response = self.client.get("/api/v1/administrative-units/wards?province_code=01&district_code=001")
        self.assertEqual(200, response.status_code)
        self.assertEqual("00001", response.json()["items"][0]["code"])

    @patch("backend.app.api.routes.fetch_provinces", side_effect=AdministrativeUnitServiceError("upstream unavailable"))
    def test_provinces_endpoint_reports_upstream_failure(self, _fetch) -> None:
        response = self.client.get("/api/v1/administrative-units/provinces")
        self.assertEqual(502, response.status_code)
        self.assertEqual("ADMINISTRATIVE_UNIT_SERVICE_UNAVAILABLE", response.json()["error"]["code"])


if __name__ == "__main__":
    unittest.main()
