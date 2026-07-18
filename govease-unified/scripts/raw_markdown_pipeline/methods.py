from __future__ import annotations

import re
from typing import Any

from .tables import extract_markdown_tables
from .utils import compact_whitespace


def parse_submission_methods(section_text: str) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    lines = section_text.splitlines()
    tables = extract_markdown_tables(lines)
    for table in tables:
        headers = table["headers"]
        if "Hình thức nộp" in headers and "Thời gian giải quyết" in headers:
            methods = []
            for row in table["rows"]:
                methods.append(
                    {
                        "method": row.get("Hình thức nộp"),
                        "processing_time": _none_if_missing(row.get("Thời gian giải quyết")),
                        "fee": _none_if_missing(row.get("Phí, lệ phí")),
                        "description": _none_if_missing(row.get("Mô tả")),
                        "raw_row": {
                            "Hình thức nộp": row.get("Hình thức nộp"),
                            "Thời gian giải quyết": row.get("Thời gian giải quyết"),
                            "Phí, lệ phí": row.get("Phí, lệ phí"),
                            "Mô tả": row.get("Mô tả"),
                        },
                    }
                )
            return methods, warnings

    flattened = compact_whitespace(section_text)
    if not flattened:
        return [], warnings

    methods = _fallback_flattened_methods(flattened)
    if methods:
        return methods, warnings

    warnings.append("submission_methods_not_parsed")
    return [], warnings


def _fallback_flattened_methods(text: str) -> list[dict[str, Any]]:
    text = re.sub(r"^\s*Hình thức nộp\s+Thời hạn giải quyết\s+Phí, lệ phí\s+Mô tả\s*", "", text)
    method_names = ["Trực tiếp", "Trực tuyến", "Dịch vụ bưu chính"]
    positions = [(name, text.find(name)) for name in method_names if text.find(name) >= 0]
    positions.sort(key=lambda item: item[1])
    results: list[dict[str, Any]] = []
    for index, (name, start) in enumerate(positions):
        end = positions[index + 1][1] if index + 1 < len(positions) else len(text)
        chunk = text[start:end].strip()
        processing_time = None
        time_match = re.search(
            r"(Theo hướng dẫn.*?Bộ Giáo dục và Đào tạo|[0-9]+\s*(?:ngày|tháng|năm)(?:\s*làm việc)?)",
            chunk,
            re.IGNORECASE,
        )
        if time_match:
            processing_time = compact_whitespace(time_match.group(1))
        description_source = chunk[len(name):].strip(" -:")
        if processing_time:
            description_source = description_source.replace(processing_time, "", 1).strip(" -:.")
        description_source = re.sub(rf"^{re.escape(name)}\s*", "", description_source, flags=re.IGNORECASE)
        description_source = re.sub(r"^\d+\s+", "", description_source)
        if not description_source:
            description_match = re.search(
                r"(Trực tuyến hoặc trực tiếp[^.]*\.)",
                chunk,
                re.IGNORECASE,
            )
            if description_match:
                description_source = description_match.group(1)
        description = compact_whitespace(description_source) or None
        results.append(
            {
                "method": name,
                "processing_time": processing_time,
                "fee": None,
                "description": description,
                "raw_row": {
                    "Hình thức nộp": name,
                    "Thời gian giải quyết": processing_time,
                    "Phí, lệ phí": None,
                    "Mô tả": description,
                },
            }
        )
    return results


def _none_if_missing(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = compact_whitespace(value)
    if cleaned in {"", "Không có thông tin", "N/A"}:
        return None
    return cleaned
