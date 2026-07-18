from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = PROJECT_ROOT.parent
NORMALIZED_DIR = PROJECT_ROOT / "data" / "normalized_structured"
ENRICHED_DIR = PROJECT_ROOT / "data" / "enriched_structured_priority"
MAPPING_PATH = PROJECT_ROOT / "data" / "catalog" / "citizen_procedure_mapping.json"
OUTPUT_DIR = PIPELINE_ROOT / "data" / "procedure_payloads"
SUMMARY_PATH = OUTPUT_DIR / "build_report.json"

BIRTH_RELATIONSHIPS = [
    "Cha",
    "Mẹ",
    "Ông nội",
    "Bà nội",
    "Ông ngoại",
    "Bà ngoại",
    "Anh ruột",
    "Chị ruột",
    "Bác ruột",
    "Chú ruột",
    "Cậu ruột",
    "Cô ruột",
    "Dì ruột",
    "Cá nhân đang nuôi dưỡng trẻ",
    "Tổ chức đang nuôi dưỡng trẻ",
]
VIETNAM_PROVINCES = [
    "Thành phố Hà Nội",
    "Tỉnh Cao Bằng",
    "Tỉnh Tuyên Quang",
    "Tỉnh Điện Biên",
    "Tỉnh Lai Châu",
    "Tỉnh Sơn La",
    "Tỉnh Lào Cai",
    "Tỉnh Thái Nguyên",
    "Tỉnh Lạng Sơn",
    "Tỉnh Quảng Ninh",
    "Tỉnh Bắc Ninh",
    "Tỉnh Phú Thọ",
    "Thành phố Hải Phòng",
    "Tỉnh Hưng Yên",
    "Tỉnh Ninh Bình",
    "Tỉnh Thanh Hóa",
    "Tỉnh Nghệ An",
    "Tỉnh Hà Tĩnh",
    "Tỉnh Quảng Trị",
    "Thành phố Huế",
    "Thành phố Đà Nẵng",
    "Tỉnh Quảng Ngãi",
    "Tỉnh Gia Lai",
    "Tỉnh Khánh Hòa",
    "Tỉnh Đắk Lắk",
    "Tỉnh Lâm Đồng",
    "Tỉnh Đồng Nai",
    "Thành phố Hồ Chí Minh",
    "Tỉnh Tây Ninh",
    "Tỉnh Đồng Tháp",
    "Tỉnh Vĩnh Long",
    "Tỉnh An Giang",
    "Thành phố Cần Thơ",
    "Tỉnh Cà Mau",
    "Nước ngoài/Khác",
]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    mapping_rows = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    mapping_by_code = {row["procedure_code"]: row for row in mapping_rows if row.get("procedure_code")}

    outputs: list[dict[str, Any]] = []
    for normalized_path in sorted(NORMALIZED_DIR.glob("*_normalized_structured.json")):
        normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
        code = normalized.get("source", {}).get("procedure_code")
        if not code:
            continue
        enriched_path = ENRICHED_DIR / f"{code.replace('.', '_')}_enriched_structured.json"
        if not enriched_path.exists():
            continue
        enriched = json.loads(enriched_path.read_text(encoding="utf-8"))
        mapping_row = mapping_by_code.get(code, {})
        payload = build_payload(normalized, enriched, mapping_row)
        output_path = OUTPUT_DIR / f"{code.replace('.', '_')}_payload.json"
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(
            {
                "procedure_code": code,
                "group_key": payload.get("group_key"),
                "workflow_family": payload.get("workflow_family"),
                "input_field_count": len(payload.get("input_fields") or []),
                "document_count": len(payload.get("documents", {}).get("normally_required") or [])
                + len(payload.get("documents", {}).get("conditional") or []),
                "output_path": str(output_path),
            }
        )

    summary = {
        "count": len(outputs),
        "output_dir": str(OUTPUT_DIR),
        "outputs": outputs,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"count": len(outputs), "summary_path": str(SUMMARY_PATH)}, ensure_ascii=False, indent=2))


def build_payload(normalized: dict[str, Any], enriched: dict[str, Any], mapping_row: dict[str, Any]) -> dict[str, Any]:
    code = normalized.get("source", {}).get("procedure_code")
    title = normalized.get("source", {}).get("title")
    field = normalized.get("source", {}).get("field")
    source_markdown_path = _source_markdown_path(code)
    source_url = source_markdown_path.as_uri() if source_markdown_path.exists() else ""
    time_badge = enriched.get("ui_hints", {}).get("time_badge")
    authorities = normalized.get("procedure", {}).get("authorities") or []
    receiving_places = normalized.get("procedure", {}).get("receiving_places") or []

    return {
        "schema_version": "3.0",
        "record_type": "public_service_procedure_payload",
        "id": f"procedure-{code}",
        "procedure_code": code,
        "code": code,
        "title": title,
        "language": "vi",
        "status": "generated_from_pipeline",
        "field": field,
        "group_key": enriched.get("source", {}).get("group_key"),
        "workflow_family": enriched.get("source", {}).get("workflow_family"),
        "subflow": enriched.get("source", {}).get("subflow"),
        "source": {
            "source_url": source_url,
            "source_markdown_path": str(source_markdown_path),
            "normalized_payload_path": str(_normalized_path(code)),
            "enriched_payload_path": str(_enriched_path(code)),
        },
        "scope": {
            "included": enriched.get("experience", {}).get("overview_summary"),
            "not_included": [],
        },
        "agency": {
            "executing_agency": authorities[0] if authorities else None,
            "submission_place": receiving_places[0] if receiving_places else None,
            "receiving_places": receiving_places,
        },
        "target_users": normalized.get("procedure", {}).get("target_users") or [],
        "submission_methods": [_submission_method(item) for item in normalized.get("submission", {}).get("methods", [])],
        "processing_note": _processing_note(normalized, enriched),
        "documents": {
            "normally_required": [_document_item(item) for item in normalized.get("documents", {}).get("required", [])],
            "conditional": [_conditional_document_item(item) for item in normalized.get("documents", {}).get("conditional", [])],
            "forms": [_form_item(item) for item in normalized.get("documents", {}).get("forms", [])],
            "presented": [_document_item(item) for item in normalized.get("documents", {}).get("presented", [])],
            "notes": normalized.get("documents", {}).get("notes") or [],
            "summary": [_document_summary_item(item) for item in _all_document_items(normalized)],
        },
        "steps": [_step_item(index, item) for index, item in enumerate(normalized.get("process", {}).get("steps", []), start=1)],
        "input_fields": _input_fields(code, normalized, enriched),
        "validation_rules": _validation_rules(normalized, enriched),
        "common_errors": _common_errors(enriched),
        "clarifying_questions": _clarifying_questions(enriched),
        "legal_basis": normalized.get("legal_basis", {}).get("items") or [],
        "legal_bases": normalized.get("legal_basis", {}).get("items") or [],
        "faq": _faq_items(normalized, enriched),
        "guidance": enriched.get("guidance") or {},
        "next_steps": {
            "summary": enriched.get("experience", {}).get("next_step_summary"),
            "time_badge": time_badge,
            "result_label": enriched.get("ui_hints", {}).get("result_label"),
            "primary_channel": enriched.get("ui_hints", {}).get("primary_channel"),
            "channels": normalized.get("submission", {}).get("channels") or [],
        },
        "notes": normalized.get("process", {}).get("notes") or [],
        "provenance": {
            "pipeline": "raw->structured->normalized->enriched->ui_api_payload",
            "normalizer_version": normalized.get("normalizer_version"),
            "enricher_version": enriched.get("enricher_version"),
            "mapping_notes": mapping_row.get("notes"),
            "supported_group": enriched.get("provenance", {}).get("supported_group"),
        },
    }


def _source_markdown_path(code: str) -> Path:
    return PIPELINE_ROOT / "raw_data" / code.replace(".", "_") / f"{code.replace('.', '_')}_procedure_detail.md"


def _normalized_path(code: str) -> Path:
    return NORMALIZED_DIR / f"{code.replace('.', '_')}_normalized_structured.json"


def _enriched_path(code: str) -> Path:
    return ENRICHED_DIR / f"{code.replace('.', '_')}_enriched_structured.json"


def _submission_method(item: dict[str, Any]) -> dict[str, Any]:
    channel = item.get("channel")
    return {
        "code": (channel or "").upper(),
        "label": _channel_label(channel),
        "processing_time": item.get("processing_time_text"),
        "fee": item.get("fee_text"),
        "description": item.get("description"),
    }


def _channel_label(channel: str | None) -> str:
    return {
        "online": "Trực tuyến",
        "in_person": "Trực tiếp",
        "postal": "Dịch vụ bưu chính",
    }.get(channel or "", channel or "")


def _processing_note(normalized: dict[str, Any], enriched: dict[str, Any]) -> str | None:
    time_badge = enriched.get("ui_hints", {}).get("time_badge")
    summary = enriched.get("experience", {}).get("next_step_summary")
    if time_badge and summary:
        return f"Thời gian xử lý tham chiếu: {time_badge}. {summary}"
    if time_badge:
        return f"Thời gian xử lý tham chiếu: {time_badge}."
    return summary


def _document_item(item: dict[str, Any]) -> dict[str, Any]:
    quantity = _quantity(item)
    return {
        "name": item.get("name"),
        "quantity": quantity,
        "notes": item.get("conditions") or [],
        "group": item.get("group_name"),
        "attachment_path": item.get("attachment_path"),
    }


def _conditional_document_item(item: dict[str, Any]) -> dict[str, Any]:
    quantity = _quantity(item)
    conditions = item.get("conditions") or []
    return {
        "condition": conditions[0] if conditions else item.get("group_name"),
        "document": item.get("name"),
        "quantity": quantity,
        "notes": conditions[1:] if len(conditions) > 1 else [],
        "attachment_path": item.get("attachment_path"),
    }


def _form_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item.get("name"),
        "attachment_label": item.get("attachment_label"),
        "attachment_path": item.get("attachment_path"),
    }


def _document_summary_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "group": item.get("group"),
        "name": item.get("name"),
        "quantity": item.get("quantity"),
        "notes": item.get("notes"),
        "attachment_path": item.get("attachment_path"),
    }


def _all_document_items(normalized: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in normalized.get("documents", {}).get("required", []):
        items.append(_document_item(item))
    for item in normalized.get("documents", {}).get("conditional", []):
        items.append(_conditional_document_item(item))
    for item in normalized.get("documents", {}).get("forms", []):
        items.append(_form_item(item))
    return items


def _quantity(item: dict[str, Any]) -> str | None:
    original = item.get("original_count")
    copies = item.get("copy_count")
    if original is None and copies is None:
        return None
    return f"{original or 0} bản chính, {copies or 0} bản sao"


def _step_item(index: int, item: dict[str, Any]) -> dict[str, Any]:
    title = item.get("title") or f"Bước {index}"
    return {
        "order": index,
        "title": title,
        "description": item.get("content"),
        "example": item.get("time_hint") or item.get("channel_hint"),
    }


def _input_fields(code: str, normalized: dict[str, Any], enriched: dict[str, Any]) -> list[dict[str, Any]]:
    if code == "1.001193":
        return [
            {"field": "child.full_name", "label": "Họ, chữ đệm, tên trẻ", "type": "string", "required": True},
            {"field": "child.birth_date", "label": "Ngày sinh", "type": "date", "format": "YYYY-MM-DD", "required": True},
            {"field": "child.gender", "label": "Giới tính", "type": "enum", "required": True, "options": ["Nam", "Nữ"]},
            {"field": "child.birth_place", "label": "Nơi sinh", "type": "enum", "required": True, "options": VIETNAM_PROVINCES},
            {"field": "child.native_place", "label": "Quê quán", "type": "enum", "required": True, "options": VIETNAM_PROVINCES},
            {"field": "father.identity_number", "label": "Số định danh/CCCD của cha", "type": "identity_number", "required": False},
            {"field": "mother.identity_number", "label": "Số định danh/CCCD của mẹ", "type": "identity_number", "required": True},
            {"field": "requester.identity_number", "label": "Số định danh/CCCD của người yêu cầu", "type": "identity_number", "required": True},
            {
                "field": "requester.relationship_to_child",
                "label": "Quan hệ với trẻ",
                "type": "enum",
                "required": True,
                "options": BIRTH_RELATIONSHIPS,
            },
            {"field": "birth_certificate.available", "label": "Có giấy chứng sinh", "type": "boolean", "required": True},
            {"field": "signature_present", "label": "Đã ký hoặc xác nhận điện tử", "type": "boolean", "required": True},
        ]

    if code == "1.004194":
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

    fields: list[dict[str, Any]] = []
    channel_options = [_channel_label(value) for value in normalized.get("submission", {}).get("channels", [])]
    for item in enriched.get("intake", {}).get("candidate_input_fields", []):
        field = {
            "field": item.get("field_id"),
            "label": item.get("label"),
            "type": _field_type(item.get("field_type")),
            "required": bool(item.get("required")),
        }
        if field["type"] == "date":
            field["format"] = "YYYY-MM-DD"
        if item.get("field_id") == "submission_channel_preference" and channel_options:
            field["options"] = channel_options
        fields.append(field)
    return fields


def _field_type(value: str | None) -> str:
    return {
        "text": "string",
        "date": "date",
        "boolean": "boolean",
        "enum": "enum",
    }.get(value or "", value or "string")


def _validation_rules(normalized: dict[str, Any], enriched: dict[str, Any]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for index, field in enumerate(_input_fields(normalized.get("source", {}).get("procedure_code"), normalized, enriched), start=1):
        if not field.get("required"):
            continue
        rules.append(
            {
                "id": f"required-{index}",
                "severity": "error",
                "field": field.get("field"),
                "rule": "Trường bắt buộc phải có dữ liệu hợp lệ trước khi nộp.",
                "message": f"Thiếu trường bắt buộc: {field.get('label')}.",
            }
        )
    for index, hint in enumerate(enriched.get("guidance", {}).get("validation_hints", []), start=1):
        rules.append(
            {
                "id": f"hint-{index}",
                "severity": "warning",
                "field": "general",
                "rule": hint,
                "message": hint,
            }
        )
    return rules[:20]


def _common_errors(enriched: dict[str, Any]) -> list[dict[str, Any]]:
    errors = []
    hints = enriched.get("guidance", {}).get("validation_hints", [])
    for item in enriched.get("guidance", {}).get("common_errors", []):
        errors.append(
            {
                "field": "general",
                "issue": item,
                "fix": hints[0] if hints else "Kiểm tra lại giấy tờ, dữ liệu định danh và biểu mẫu trước khi nộp.",
            }
        )
    return errors


def _clarifying_questions(enriched: dict[str, Any]) -> list[dict[str, Any]]:
    questions = []
    for index, question in enumerate(enriched.get("intake", {}).get("suggested_clarifying_questions", []), start=1):
        questions.append({"id": f"clarify_{index}", "question": question, "purpose": "workflow_intake"})
    return questions


def _faq_items(normalized: dict[str, Any], enriched: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    channels = normalized.get("submission", {}).get("channels") or []
    if channels:
        items.append(
            {
                "question": "Có thể nộp qua kênh nào?",
                "answer": "Các kênh hiện có: " + ", ".join(_channel_label(channel) for channel in channels) + ".",
            }
        )
    time_badge = enriched.get("ui_hints", {}).get("time_badge")
    if time_badge:
        items.append(
            {
                "question": "Thời gian xử lý tham chiếu là bao lâu?",
                "answer": f"Thời gian xử lý tham chiếu hiện có là {time_badge}.",
            }
        )
    result_label = enriched.get("ui_hints", {}).get("result_label")
    if result_label:
        items.append(
            {
                "question": "Kết quả chính của thủ tục là gì?",
                "answer": f"Kết quả chính được trích xuất là {result_label}.",
            }
        )
    return items


if __name__ == "__main__":
    main()
