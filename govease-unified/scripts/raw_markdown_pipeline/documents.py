from __future__ import annotations

import re
from typing import Any

from .tables import extract_markdown_tables
from .utils import compact_whitespace, slugify


LINK_PATTERN = re.compile(r"\[(?P<label>[^\]]+)\]\((?P<path>[^)]+)\)")
ATTACHMENT_FILE_PATTERN = re.compile(
    r"(?P<filename>[\wÀ-ỹ .()/-]+\.(?:docx|doc|pdf|xls|xlsx|zip))$",
    re.IGNORECASE,
)
COUNT_PATTERN = re.compile(
    r"Bản chính:\s*(?P<original>\d+|-)?\s*-\s*Bản sao:\s*(?P<copy>\d+|-)?",
    re.IGNORECASE,
)


def parse_documents(section_text: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    groups: list[dict[str, Any]] = []
    attachments: list[dict[str, Any]] = []
    if _is_empty_section(section_text):
        groups.append(
            {
                "group_id": "default",
                "group_name": "default",
                "group_type": "unknown",
                "documents": [],
            }
        )
        return {"groups": groups, "flattened_documents": []}, attachments, warnings
    current_group = "default"
    buffer: list[str] = []

    def flush_group(group_name: str, lines: list[str]) -> None:
        if not lines:
            return
        local_tables = extract_markdown_tables(lines)
        if not local_tables:
            return
        group_documents: list[dict[str, Any]] = []
        has_document_table = False
        for table in local_tables:
            headers = {compact_whitespace(header) for header in table["headers"]}
            if {"Tên giấy tờ", "Bản chính", "Bản sao"} <= headers or "Bao gồm" in headers:
                has_document_table = True
            for row in table["rows"]:
                raw_name = row.get("Tên giấy tờ") or row.get("Bao gồm") or ""
                raw_name = _clean_document_name(raw_name)
                if not raw_name:
                    continue
                attachment_label = None
                attachment_path = None
                link_field = row.get("Tệp đính kèm") or row.get("Mẫu đơn, tờ khai") or ""
                link_matches = list(LINK_PATTERN.finditer(link_field))
                if link_matches:
                    attachment_label = link_matches[0].group("label")
                    attachment_path = link_matches[0].group("path")
                    for match in link_matches:
                        attachments.append(
                            {
                                "label": match.group("label"),
                                "path": match.group("path"),
                                "source_section": "Thành phần hồ sơ",
                                "document_name": raw_name,
                            }
                        )
                is_conditional = "trường hợp" in raw_name.lower() or "nếu" in raw_name.lower()
                conditions = []
                if is_conditional:
                    conditions.append(raw_name)
                notes = []
                if raw_name.startswith("*Lưu ý") or raw_name.startswith("Ví dụ:"):
                    notes.append(raw_name)
                group_documents.append(
                    {
                        "name": raw_name,
                        "original_count": _none_if_missing(row.get("Bản chính")),
                        "copy_count": _none_if_missing(row.get("Bản sao")),
                        "attachment_label": attachment_label,
                        "attachment_path": attachment_path,
                        "is_conditional": is_conditional,
                        "conditions": conditions,
                        "notes": notes,
                        "raw_text": raw_name,
                    }
                )
        if group_documents or has_document_table:
            groups.append(
                {
                    "group_id": slugify(group_name),
                    "group_name": group_name,
                    "group_type": _group_type(group_name),
                    "documents": group_documents,
                }
            )

    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("### "):
            flush_group(current_group, buffer)
            current_group = stripped[4:].strip()
            buffer = []
            continue
        buffer.append(line)
    flush_group(current_group, buffer)

    if not groups and compact_whitespace(section_text):
        fallback_group, fallback_attachments = _fallback_flattened_documents(section_text)
        if fallback_group:
            groups.append(fallback_group)
            attachments.extend(fallback_attachments)
        else:
            warnings.append("documents_not_parsed")

    flattened = []
    for group in groups:
        for item in group["documents"]:
            flattened.append(
                {
                    "name": item["name"],
                    "group_name": group["group_name"],
                    "is_conditional": item["is_conditional"],
                }
            )

    return {"groups": groups, "flattened_documents": flattened}, attachments, warnings


def _fallback_flattened_documents(section_text: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    flattened = compact_whitespace(section_text)
    if not flattened:
        return None, []

    flattened = re.sub(r"^\s*Bao gồm\s+Tên giấy tờ\s+Mẫu đơn, tờ khai\s+Số lượng\s*", "", flattened)
    matches = list(COUNT_PATTERN.finditer(flattened))
    if not matches:
        return None, []

    documents: list[dict[str, Any]] = []
    attachments: list[dict[str, Any]] = []
    previous_end = 0

    for match in matches:
        chunk = compact_whitespace(flattened[previous_end:match.start()])
        previous_end = match.end()
        if not chunk:
            continue

        attachment_label = None
        attachment_path = None
        attachment_match = ATTACHMENT_FILE_PATTERN.search(chunk)
        if attachment_match:
            attachment_path = compact_whitespace(attachment_match.group("filename"))
            attachment_label = attachment_path.split("/")[-1]
            chunk = compact_whitespace(chunk[: attachment_match.start()])

        original_count = _normalize_count(match.group("original"))
        copy_count = _normalize_count(match.group("copy"))
        chunk = _clean_document_name(chunk)
        is_conditional = "trường hợp" in chunk.lower() or "nếu có" in chunk.lower()
        conditions = [chunk] if is_conditional else []

        document = {
            "name": chunk,
            "original_count": original_count,
            "copy_count": copy_count,
            "attachment_label": attachment_label,
            "attachment_path": attachment_path,
            "is_conditional": is_conditional,
            "conditions": conditions,
            "notes": [],
            "raw_text": compact_whitespace(f"{chunk} Bản chính: {original_count} - Bản sao: {copy_count}"),
        }
        documents.append(document)

        if attachment_path:
            attachments.append(
                {
                    "label": attachment_label,
                    "path": attachment_path,
                    "source_section": "Thành phần hồ sơ",
                    "document_name": chunk,
                }
            )

    if not documents:
        return None, []

    return (
        {
            "group_id": "default",
            "group_name": "default",
            "group_type": "required",
            "documents": documents,
        },
        attachments,
    )


def _clean_document_name(value: str) -> str:
    cleaned = compact_whitespace(value)
    cleaned = re.sub(r"^[+*\-]\s*", "", cleaned)
    return cleaned.strip()


def _normalize_count(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = compact_whitespace(value)
    if cleaned in {"", "-"}:
        return None
    return cleaned


def _is_empty_section(value: str) -> bool:
    return compact_whitespace(value).lower() in {"", "không có thông tin"}


def _group_type(value: str) -> str:
    lowered = value.lower()
    if "lưu ý" in lowered:
        return "notes"
    if "xuất trình" in lowered:
        return "present"
    if "điều kiện" in lowered or "trường hợp" in lowered:
        return "conditional"
    if value == "default":
        return "unknown"
    return "required"


def _none_if_missing(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = compact_whitespace(value)
    if cleaned in {"", "Không có", "Không có thông tin"}:
        return None
    return cleaned
