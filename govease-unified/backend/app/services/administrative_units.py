from __future__ import annotations

from datetime import date
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

NSO_SERVICE_URL = "https://danhmuchanhchinh.nso.gov.vn/DMDVHC.asmx"
NSO_SOURCE_URL = NSO_SERVICE_URL


class AdministrativeUnitServiceError(RuntimeError):
    pass


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_units(
    payload: bytes,
    result_name: str,
    code_keys: tuple[str, ...],
    name_keys: tuple[str, ...],
) -> list[dict[str, str]]:
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as exc:
        raise AdministrativeUnitServiceError("Phản hồi danh mục đơn vị hành chính không phải XML hợp lệ.") from exc

    result = next((node for node in root.iter() if _local_name(node.tag) == result_name), None)
    if result is None:
        raise AdministrativeUnitServiceError(f"Phản hồi không chứa {result_name}.")

    dataset_root = result
    if not list(result) and (result.text or "").strip():
        try:
            dataset_root = ElementTree.fromstring(result.text.strip())
        except ElementTree.ParseError as exc:
            raise AdministrativeUnitServiceError("Không đọc được dữ liệu danh mục trong phản hồi.") from exc

    units: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in dataset_root.iter():
        values = {
            _local_name(child.tag).lower(): (child.text or "").strip()
            for child in list(row)
            if not list(child)
        }
        code = next((values[key] for key in code_keys if values.get(key)), "")
        name = next((values[key] for key in name_keys if values.get(key)), "")
        if code and name and code not in seen:
            seen.add(code)
            units.append({"code": code, "name": name})
    if not units:
        raise AdministrativeUnitServiceError("Danh mục đơn vị hành chính trả về không có dữ liệu.")
    return units


def _parse_provinces(payload: bytes) -> list[dict[str, str]]:
    return _parse_units(
        payload,
        "DanhMucTinhResult",
        ("matinh", "ma_tinh", "code"),
        ("tentinh", "ten_tinh", "name"),
    )


def _soap_call(operation: str, parameters: dict[str, str]) -> bytes:
    fields = "".join(f"<{key}>{value}</{key}>" for key, value in parameters.items())
    envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
<soap:Body><{operation} xmlns="http://tempuri.org/">{fields}</{operation}></soap:Body>
</soap:Envelope>""".encode("utf-8")
    request = Request(
        NSO_SERVICE_URL,
        data=envelope,
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"http://tempuri.org/{operation}"',
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=12) as response:
            return response.read()
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise AdministrativeUnitServiceError("Không thể kết nối danh mục đơn vị hành chính.") from exc


@lru_cache(maxsize=8)
def fetch_provinces(as_of_date: str | None = None) -> list[dict[str, str]]:
    den_ngay = as_of_date or date.today().strftime("%d/%m/%Y")
    return _parse_provinces(_soap_call("DanhMucTinh", {"DenNgay": den_ngay}))


@lru_cache(maxsize=128)
def fetch_districts(province_code: str) -> list[dict[str, str]]:
    payload = _soap_call(
        "DanhMucQuanHuyen",
        {
            "DenNgay": date.today().strftime("%d/%m/%Y"),
            "Tinh": province_code,
            "TenTinh": "",
        },
    )
    return _parse_units(
        payload,
        "DanhMucQuanHuyenResult",
        ("maquanhuyen", "ma_huyen", "mahuyen"),
        ("tenquanhuyen", "ten_huyen", "tenhuyen"),
    )


@lru_cache(maxsize=512)
def fetch_wards(province_code: str, district_code: str) -> list[dict[str, str]]:
    payload = _soap_call(
        "DanhMucPhuongXa",
        {
            "DenNgay": date.today().strftime("%d/%m/%Y"),
            "Tinh": province_code,
            "TenTinh": "",
            "QuanHuyen": district_code,
            "TenQuanHuyen": "",
        },
    )
    return _parse_units(
        payload,
        "DanhMucPhuongXaResult",
        ("maphuongxa", "ma_xa", "maxa"),
        ("tenphuongxa", "ten_xa", "tenxa"),
    )
