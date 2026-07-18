from __future__ import annotations

import re

from .utils import compact_whitespace


META_LABEL_MAP = {
    "Mã thủ tục": "procedure_code",
    "Số quyết định": "decision_number",
    "Cấp thực hiện": "level",
    "Loại thủ tục": "procedure_type",
    "Lĩnh vực": "field",
    "Đối tượng thực hiện": "target_users",
    "Cơ quan có thẩm quyền": "authority",
    "Địa chỉ tiếp nhận HS": "receiving_address",
    "Cơ quan được ủy quyền": "delegated_authority",
    "Cơ quan phối hợp": "coordinating_authority",
    "Nguồn fallback": "source_url",
}


def parse_meta(section_text: str) -> dict[str, object]:
    result: dict[str, object] = {
        "procedure_code": None,
        "decision_number": None,
        "level": None,
        "procedure_type": None,
        "field": None,
        "target_users": [],
        "authority": None,
        "receiving_address": None,
        "delegated_authority": None,
        "coordinating_authority": None,
        "source_url": None,
    }
    for line in section_text.splitlines():
        match = re.match(r"^\*\s+\*\*(.+?)\:\*\*\s*(.*)$", line.strip())
        if not match:
            continue
        raw_label, raw_value = match.groups()
        label = raw_label.strip()
        value = compact_whitespace(raw_value)
        key = META_LABEL_MAP.get(label)
        if not key:
            continue
        if value == "Không có thông tin":
            value = ""
        if key == "target_users":
            result[key] = [item.strip() for item in value.split(",") if item.strip()]
        else:
            result[key] = value or None
    return result
