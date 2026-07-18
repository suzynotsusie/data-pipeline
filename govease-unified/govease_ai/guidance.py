from __future__ import annotations

from typing import Any

CHANNEL_LABELS = {
    "in_person": "trực tiếp",
    "online": "trực tuyến",
    "postal": "bưu chính",
}


def build_user_guidance(data: dict[str, Any]) -> dict[str, Any]:
    raw_steps = _raw_steps(data)
    methods = _submission_methods(data)
    documents = _document_count(data)
    processing_time = _processing_time_summary(data, methods)
    submission_place = _submission_place_summary(data)
    next_step_summary = _existing_next_step_summary(data) or _build_next_step_summary(methods, documents)
    overview_summary = _existing_overview_summary(data) or _build_overview_summary(
        processing_time=processing_time,
        submission_place=submission_place,
        next_step_summary=next_step_summary,
    )

    return {
        "overview_summary": overview_summary,
        "next_step_summary": next_step_summary,
        "processing_time_summary": processing_time,
        "submission_place_summary": submission_place,
        "submission_method_labels": methods,
        "user_steps": _user_steps(raw_steps, methods),
    }


def _raw_steps(data: dict[str, Any]) -> list[dict[str, Any]]:
    values = data.get("steps") or data.get("procedure_steps") or []
    if not isinstance(values, list):
        return []
    return [item for item in values if isinstance(item, dict)]


def _submission_methods(data: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for item in data.get("submission_methods") or []:
        if not isinstance(item, dict):
            continue
        label = _normalize_user_text(str(item.get("label") or item.get("code") or "").strip())
        if label:
            labels.append(label)
    return labels


def _document_count(data: dict[str, Any]) -> int:
    documents = data.get("documents")
    if not isinstance(documents, dict):
        return 0
    total = 0
    for key in ("normally_required", "forms", "presented", "summary"):
        values = documents.get(key)
        if isinstance(values, list):
            total += len(
                [
                    item
                    for item in values
                    if isinstance(item, dict) and str(item.get("name") or item.get("document") or "").strip()
                ]
            )
    return total


def _processing_time_summary(data: dict[str, Any], methods: list[str]) -> str | None:
    next_steps = data.get("next_steps")
    if isinstance(next_steps, dict):
        badge = str(next_steps.get("time_badge") or "").strip()
        if badge:
            return _normalize_user_text(badge)

    for item in data.get("submission_methods") or []:
        if not isinstance(item, dict):
            continue
        value = str(item.get("processing_time") or "").strip()
        if value:
            return _normalize_user_text(value)

    note = str(data.get("processing_note") or "").strip()
    if note and _looks_like_time_text(note):
        return _normalize_user_text(note)

    return "Theo quy định của cơ quan tiếp nhận" if methods else None


def _submission_place_summary(data: dict[str, Any]) -> str | None:
    agency = data.get("agency")
    if isinstance(agency, dict):
        for key in ("submission_place", "executing_agency", "name"):
            value = str(agency.get(key) or "").strip()
            if value:
                return _normalize_user_text(value)
    if isinstance(agency, str) and agency.strip():
        return _normalize_user_text(agency.strip())
    return None


def _existing_next_step_summary(data: dict[str, Any]) -> str | None:
    for value in (
        data.get("next_step_summary"),
        (data.get("next_steps") or {}).get("summary") if isinstance(data.get("next_steps"), dict) else None,
    ):
        if isinstance(value, str) and value.strip():
            return _normalize_user_text(value.strip())
    return None


def _existing_overview_summary(data: dict[str, Any]) -> str | None:
    value = data.get("overview_summary")
    if isinstance(value, str) and value.strip():
        return _normalize_user_text(value.strip())
    return None


def _build_overview_summary(
    *,
    processing_time: str | None,
    submission_place: str | None,
    next_step_summary: str | None,
) -> str | None:
    parts: list[str] = []
    if processing_time:
        parts.append(f"Thời gian xử lý tham khảo: {processing_time}.")
    if submission_place:
        parts.append(f"Nơi nộp chính: {submission_place}.")
    return " ".join(parts) or None


def _build_next_step_summary(methods: list[str], documents: int) -> str:
    channel_text = ", ".join(methods[:3]) if methods else "kênh nộp phù hợp"
    document_text = f" Bộ hồ sơ hiện có khoảng {documents} mục cần theo dõi." if documents else ""
    return f"Nên chuẩn bị giấy tờ chính trước, sau đó chọn cách nộp phù hợp trong các kênh: {channel_text}.{document_text}".strip()


def _looks_like_time_text(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in ("ngày", "giờ", "tháng", "phút", "buổi", "làm việc"))


def _normalize_user_text(value: str) -> str:
    normalized = " ".join(value.split())
    for code, label in CHANNEL_LABELS.items():
        normalized = normalized.replace(code, label)
        normalized = normalized.replace(code.upper(), label.upper())
    normalized = normalized.replace("..", ".")
    return normalized.strip()


def _user_steps(raw_steps: list[dict[str, Any]], methods: list[str]) -> list[dict[str, Any]]:
    detected = {
        "choose_channel": False,
        "prepare_documents": False,
        "submit": False,
        "supplement": False,
        "verify": False,
        "confirm": False,
        "receive": False,
    }

    for item in raw_steps:
        haystack = " ".join(
            str(item.get(key) or "").lower() for key in ("title", "description", "example")
        )
        if any(token in haystack for token in ("trực tiếp", "trực tuyến", "bưu chính", "hình thức nộp", "cổng dịch vụ công")):
            detected["choose_channel"] = True
        if any(token in haystack for token in ("tờ khai", "giấy tờ", "đính kèm", "hồ sơ")):
            detected["prepare_documents"] = True
        if any(token in haystack for token in ("nộp hồ sơ", "hoàn tất việc nộp", "tiếp nhận hồ sơ")):
            detected["submit"] = True
        if any(token in haystack for token in ("bổ sung", "hoàn thiện hồ sơ", "từ chối")):
            detected["supplement"] = True
        if any(token in haystack for token in ("thẩm tra", "xác minh", "tra cứu", "kiểm tra")):
            detected["verify"] = True
        if any(token in haystack for token in ("xác nhận", "biểu mẫu", "một ngày")):
            detected["confirm"] = True
        if any(token in haystack for token in ("trả kết quả", "nhận kết quả", "in giấy", "ký")):
            detected["receive"] = True

    if methods:
        detected["choose_channel"] = True
        detected["submit"] = True

    steps: list[dict[str, Any]] = []

    def add(title: str, description: str) -> None:
        steps.append({"order": len(steps) + 1, "title": title, "description": description, "example": None})

    if detected["choose_channel"]:
        channel_text = ", ".join(methods[:3]) if methods else "trực tiếp, trực tuyến hoặc bưu chính"
        add("Chọn cách nộp", f"Chọn kênh nộp phù hợp với hồ sơ của bạn: {channel_text}.")
    if detected["prepare_documents"]:
        add("Chuẩn bị giấy tờ", "Rà lại giấy tờ chính, mẫu tờ khai và tài liệu đính kèm theo checklist của thủ tục.")
    if detected["submit"]:
        add("Nộp hồ sơ", "Nộp hồ sơ theo kênh đã chọn và hoàn tất lệ phí nếu thủ tục có yêu cầu.")
    if detected["supplement"]:
        add("Bổ sung khi được yêu cầu", "Nếu hồ sơ thiếu hoặc chưa hợp lệ, bổ sung đúng giấy tờ theo thông báo của cơ quan tiếp nhận.")
    if detected["verify"]:
        add("Cơ quan thẩm tra", "Cơ quan tiếp nhận sẽ kiểm tra, tra cứu hoặc xác minh thêm trước khi chốt kết quả.")
    if detected["confirm"]:
        add("Xác nhận thông tin", "Nếu nộp trực tuyến, kiểm tra lại biểu mẫu điện tử và xác nhận thông tin khi hệ thống gửi lại.")
    if detected["receive"]:
        add("Nhận kết quả", "Theo dõi phiếu hẹn hoặc thông báo và nhận kết quả khi hồ sơ đã được giải quyết.")

    if steps:
        return steps[:7]

    fallback_steps = [
        ("Chuẩn bị hồ sơ", "Chuẩn bị giấy tờ chính và thông tin cá nhân theo checklist của thủ tục."),
        ("Nộp hồ sơ", "Nộp hồ sơ tại cơ quan tiếp nhận hoặc qua kênh trực tuyến nếu thủ tục hỗ trợ."),
        ("Theo dõi kết quả", "Theo dõi phản hồi từ cơ quan xử lý và bổ sung hồ sơ nếu được yêu cầu."),
    ]
    return [
        {"order": index, "title": title, "description": description, "example": None}
        for index, (title, description) in enumerate(fallback_steps, start=1)
    ]
