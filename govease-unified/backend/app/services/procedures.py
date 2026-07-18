from __future__ import annotations

from typing import Any

from govease_ai.guidance import build_user_guidance
from govease_ai.procedure_data import ProcedureDataStore, ProcedureRecord

PROVINCE_SOURCE_URL = "https://danhmuchanhchinh.nso.gov.vn/DMDVHC.asmx"
PROVINCE_OPTIONS_ENDPOINT = "/api/v1/administrative-units/provinces"
FIELD_HELP = {
    "identity_number": "Nhập đúng 12 chữ số trên căn cước công dân hoặc tài khoản VNeID. Bản demo chỉ kiểm tra cấu trúc, chưa xác minh chủ sở hữu.",
    "administrative_address": "Chọn đủ tỉnh/thành phố, quận/huyện, xã/phường rồi nhập thêm số nhà, đường, ngõ hoặc thôn/tổ.",
    "address": "Địa chỉ cần đủ đơn vị hành chính và phần chi tiết để cơ quan tiếp nhận xác định nơi cư trú.",
}
VIETNAM_PROVINCES = [
    "Thành phố Hà Nội", "Tỉnh Cao Bằng", "Tỉnh Tuyên Quang", "Tỉnh Điện Biên",
    "Tỉnh Lai Châu", "Tỉnh Sơn La", "Tỉnh Lào Cai", "Tỉnh Thái Nguyên",
    "Tỉnh Lạng Sơn", "Tỉnh Quảng Ninh", "Tỉnh Bắc Ninh", "Tỉnh Phú Thọ",
    "Thành phố Hải Phòng", "Tỉnh Hưng Yên", "Tỉnh Ninh Bình", "Tỉnh Thanh Hóa",
    "Tỉnh Nghệ An", "Tỉnh Hà Tĩnh", "Tỉnh Quảng Trị", "Thành phố Huế",
    "Thành phố Đà Nẵng", "Tỉnh Quảng Ngãi", "Tỉnh Gia Lai", "Tỉnh Khánh Hòa",
    "Tỉnh Đắk Lắk", "Tỉnh Lâm Đồng", "Tỉnh Đồng Nai", "Thành phố Hồ Chí Minh",
    "Tỉnh Tây Ninh", "Tỉnh Đồng Tháp", "Tỉnh Vĩnh Long", "Tỉnh An Giang",
    "Thành phố Cần Thơ", "Tỉnh Cà Mau", "Nước ngoài/Khác",
]
BIRTH_RELATIONSHIPS = [
    "Cha", "Mẹ", "Ông nội", "Bà nội", "Ông ngoại", "Bà ngoại",
    "Anh ruột", "Chị ruột", "Bác ruột", "Chú ruột", "Cậu ruột",
    "Cô ruột", "Dì ruột", "Cá nhân đang nuôi dưỡng trẻ",
    "Tổ chức đang nuôi dưỡng trẻ",
]


def procedure_summary(record: ProcedureRecord) -> dict[str, Any]:
    agency = record.data.get("agency")
    agency_name = record.data.get("agency")
    if isinstance(agency, dict):
        agency_name = agency.get("executing_agency") or agency.get("submission_place")
    return {
        "id": record.id,
        "code": record.code,
        "title": record.title,
        "detail_level": record.detail_level,
        "source_url": record.source_url,
        "status": record.data.get("status", "unknown"),
        "agency": agency_name,
    }


def list_procedures(store: ProcedureDataStore, *, detailed_only: bool) -> list[dict[str, Any]]:
    records = store.detailed_records() if detailed_only else store.records
    return [procedure_summary(record) for record in records]


def procedure_detail(record: ProcedureRecord) -> dict[str, Any]:
    documents = record.data.get("documents") or {}
    guidance = build_user_guidance(record.data)
    primary_documents = _primary_documents(documents, guidance=record.data.get("guidance"))
    conditional_documents = _normalize_document_items(documents.get("conditional") or [])
    form_documents = _normalize_document_items(documents.get("forms") or [])
    return {
        **procedure_summary(record),
        "scope": record.data.get("scope"),
        "target_users": record.data.get("target_users", []),
        "submission_methods": record.data.get("submission_methods", []),
        "processing_note": record.data.get("processing_note"),
        "legal_bases": record.data.get("legal_bases") or record.data.get("legal_basis") or [],
        "guidance": record.data.get("guidance") or {},
        "next_steps": record.data.get("next_steps") or {},
        "clarifying_questions": record.data.get("clarifying_questions") or [],
        "checklist": {
            "documents": primary_documents,
            "conditional_documents": conditional_documents,
            "forms": form_documents,
            "notes": documents.get("notes") or [],
            "steps": record.data.get("steps") or [],
            "user_steps": guidance.get("user_steps") or [],
            "next_step_summary": guidance.get("next_step_summary"),
            "overview_summary": guidance.get("overview_summary"),
            "processing_time_summary": guidance.get("processing_time_summary"),
            "submission_place_summary": guidance.get("submission_place_summary"),
        },
        "data_version": record.data.get("schema_version"),
        "provenance": record.data.get("provenance") or record.data.get("source") or {},
    }


def form_schema(record: ProcedureRecord) -> dict[str, Any]:
    fields = []
    raw_fields = record.data.get("input_fields") or _fallback_fields(record)
    for item in raw_fields:
        if not isinstance(item, dict):
            continue
        path = str(item.get("field") or item.get("field_id") or "").strip()
        if not path:
            continue
        field_type = str(item.get("type") or "string")
        if item.get("field_type") and not item.get("type"):
            field_type = str(item.get("field_type"))
        options = item.get("options") or item.get("values") or []
        options_source_url = record.source_url
        options_endpoint = None
        if record.code == "1.001193" and path == "child.gender":
            field_type = "enum"
            options = ["Nam", "Nữ"]
        elif record.code == "1.001193" and path in {"child.birth_place", "child.native_place"}:
            field_type = "enum"
            options = VIETNAM_PROVINCES
            options_source_url = PROVINCE_SOURCE_URL
            options_endpoint = PROVINCE_OPTIONS_ENDPOINT
        elif record.code == "1.001193" and path == "requester.relationship_to_child":
            field_type = "enum"
            options = BIRTH_RELATIONSHIPS
        if record.code == "1.004194" and path in {"temporary_address", "permanent_address"}:
            field_type = "administrative_address"

        validation: dict[str, Any] = {}
        if item.get("format"):
            validation["format"] = item["format"]
        if field_type == "identity_number":
            validation["pattern"] = "^[0-9]{12}$"
            validation["format"] = "12 chữ số, ưu tiên tự động điền từ tài khoản VNeID/DVCQG"
        fields.append(
            {
                "path": path,
                "label": item.get("label") or path,
                "type": field_type,
                "required": bool(item.get("required")),
                "example": item.get("example"),
                "options": options,
                "options_source_url": options_source_url,
                "options_endpoint": options_endpoint,
                "prefill_source": "vneid" if field_type == "identity_number" else None,
                "read_only_when_verified": field_type == "identity_number",
                "help_text": item.get("help_text") or FIELD_HELP.get(field_type),
                "validation": validation,
                "source_url": record.source_url,
            }
        )
    return {
        "procedure": procedure_summary(record),
        "fields": fields,
        "source_url": record.source_url,
        "schema_version": record.data.get("schema_version", "1.0"),
    }


def _primary_documents(documents: dict[str, Any], *, guidance: Any) -> list[dict[str, Any]]:
    primary = _normalize_document_items(documents.get("normally_required") or [])
    if primary:
        return primary

    primary = _normalize_document_items(documents.get("presented") or [])
    if primary:
        return primary

    primary = _normalize_document_items(documents.get("summary") or [])
    if primary:
        return primary

    highlights = guidance.get("highlight_documents") if isinstance(guidance, dict) else []
    fallback: list[dict[str, Any]] = []
    for item in highlights or []:
        if not isinstance(item, dict):
            continue
        bucket = str(item.get("bucket") or "").strip()
        if bucket not in {"required", "presented"}:
            continue
        name = _clean_text(item.get("name"))
        if not name:
            continue
        fallback.append(
            {
                "name": _compact_document_name(name),
                "condition": "; ".join(str(value).strip() for value in item.get("conditions") or [] if str(value).strip()) or None,
                "quantity": None,
                "notes": None,
                "alternatives": None,
            }
        )
    return fallback


def _normalize_document_items(values: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        name = _clean_text(item.get("name") or item.get("document") or item.get("form_name") or item.get("title"))
        if not name:
            continue
        full_name = name
        notes = _clean_text(item.get("notes") or item.get("note") or item.get("why") or item.get("tep_dinh_kem"))
        name = _compact_document_name(name)
        if name != full_name and not notes:
            notes = full_name
        normalized.append(
            {
                "name": name,
                "condition": _clean_text(item.get("condition") or item.get("applies_when") or item.get("group")) or None,
                "quantity": _document_quantity(item),
                "notes": notes or None,
                "alternatives": item.get("alternatives") or item.get("documents"),
            }
        )
    return normalized


def _document_quantity(item: dict[str, Any]) -> str | None:
    quantity = _clean_text(item.get("quantity"))
    if quantity:
        return quantity
    parts: list[str] = []
    if item.get("ban_chinh") is not None:
        parts.append(f"{item['ban_chinh']} bản chính")
    if item.get("ban_sao") is not None:
        parts.append(f"{item['ban_sao']} bản sao")
    return ", ".join(parts) or None


def _compact_document_name(value: str) -> str:
    name = _clean_text(value)
    if len(name) <= 160:
        return name
    for separator in (". ", "; ", " - ", ": "):
        if separator in name:
            candidate = name.split(separator, 1)[0].strip()
            if 12 <= len(candidate) <= 160:
                return candidate
    return name[:157].rstrip() + "..."


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _fallback_fields(record: ProcedureRecord) -> list[dict[str, Any]]:
    if record.code != "1.004194":
        return []
    return [
        {"field": "applicant.full_name", "label": "Họ và tên người đăng ký", "type": "string", "required": True},
        {"field": "applicant.identity_number", "label": "Số CCCD/CMND", "type": "identity_number", "required": True},
        {"field": "applicant.is_minor", "label": "Người đăng ký chưa thành niên", "type": "boolean", "required": False},
        {"field": "temporary_address", "label": "Địa chỉ tạm trú", "type": "administrative_address", "required": True},
        {"field": "permanent_address", "label": "Địa chỉ thường trú", "type": "administrative_address", "required": True},
        {"field": "stay_start_date", "label": "Ngày bắt đầu tạm trú", "type": "date", "format": "YYYY-MM-DD", "required": True},
        {"field": "stay_end_date", "label": "Ngày kết thúc tạm trú", "type": "date", "format": "YYYY-MM-DD", "required": True},
        {"field": "accommodation_proof", "label": "Thông tin chứng minh chỗ ở hợp pháp", "type": "string", "required": True},
        {"field": "guardian_consent", "label": "Ý kiến đồng ý của cha mẹ hoặc người giám hộ", "type": "string", "required": False},
        {"field": "signature_present", "label": "Đã ký hoặc xác nhận điện tử", "type": "boolean", "required": True},
    ]
