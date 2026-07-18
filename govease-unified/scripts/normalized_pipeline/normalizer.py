from __future__ import annotations

import re
from typing import Any

from raw_markdown_pipeline.utils import compact_whitespace, slugify


def normalize_raw_structured(payload: dict[str, Any]) -> dict[str, Any]:
    meta = payload.get("meta", {})
    source = payload.get("source", {})
    methods = payload.get("submission_methods", [])
    documents = payload.get("documents", {})
    process = payload.get("process", {})
    eligibility = payload.get("eligibility", {})
    raw_sections = payload.get("raw_sections", {})

    normalized_documents = _normalize_documents(documents)
    normalized_methods = _normalize_methods(methods)
    receiving_places = _extract_receiving_places(meta.get("receiving_address") or raw_sections.get("dia_chi_tiep_nhan_hs"))
    authorities = _extract_authorities(meta.get("authority") or raw_sections.get("co_quan_thuc_hien"))
    process_notes = _extract_process_notes(process.get("steps", []))
    document_signal = _document_signal(payload, normalized_documents)

    return {
        "schema_version": "1.0",
        "normalizer_version": "0.2.0",
        "source": {
            "procedure_code": source.get("procedure_code"),
            "title": meta.get("title"),
            "raw_structured_parser_version": source.get("parser_version"),
            "field": meta.get("field"),
        },
        "procedure": {
            "level": meta.get("level"),
            "procedure_type": meta.get("procedure_type"),
            "target_users": meta.get("target_users") or [],
            "authorities": authorities,
            "receiving_places": receiving_places,
        },
        "submission": {
            "channels": sorted({item["channel"] for item in normalized_methods if item.get("channel")}),
            "methods": normalized_methods,
            "timing_summary": _build_timing_summary(normalized_methods),
        },
        "documents": normalized_documents,
        "process": {
            "steps": [_normalize_step(step) for step in process.get("steps", []) if not _is_process_heading(step)],
            "step_count": len([step for step in process.get("steps", []) if not _is_process_heading(step)]),
            "notes": process_notes,
        },
        "eligibility": {
            "conditions": [compact_whitespace(item) for item in eligibility.get("conditions", []) if compact_whitespace(item)],
            "has_conditions": bool(eligibility.get("conditions")),
        },
        "results": {
            "items": payload.get("results", []),
            "primary_result": _pick_primary_result(payload.get("results", [])),
        },
        "legal_basis": {
            "items": payload.get("legal_basis", []),
            "count": len(payload.get("legal_basis", [])),
        },
        "attachments": payload.get("attachments", []),
        "signals": {
            "raw_parse_warnings": payload.get("quality", {}).get("parse_warnings", []),
            "missing_documents": document_signal["missing_documents"],
            "documents_section_present": document_signal["documents_section_present"],
            "documents_declared_empty": document_signal["documents_declared_empty"],
            "documents_only_in_notes": document_signal["documents_only_in_notes"],
            "missing_results": len(payload.get("results", [])) == 0,
        },
    }


def _normalize_methods(methods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, method in enumerate(methods, start=1):
        channel = _normalize_channel(method.get("method"))
        normalized.append(
            {
                "method_id": f"method_{index}",
                "channel": channel,
                "processing_time_text": compact_whitespace(method.get("processing_time") or "") or None,
                "fee_text": compact_whitespace(method.get("fee") or "") or None,
                "description": compact_whitespace(method.get("description") or "") or None,
                "is_online": channel == "online",
                "is_postal": channel == "postal",
                "is_in_person": channel == "in_person",
            }
        )
    return normalized


def _normalize_documents(documents: dict[str, Any]) -> dict[str, Any]:
    required: list[dict[str, Any]] = []
    conditional: list[dict[str, Any]] = []
    presented: list[dict[str, Any]] = []
    notes: list[str] = []
    forms: list[dict[str, str | None]] = []
    empty_groups: list[str] = []

    for group in documents.get("groups", []):
        group_name = compact_whitespace(group.get("group_name") or "")
        group_type = compact_whitespace(group.get("group_type") or "")
        items = group.get("documents", [])
        if not items:
            empty_groups.append(group_name or "default")
            continue
        for item in group.get("documents", []):
            item_name = compact_whitespace(item.get("name") or "")
            bucket = _document_bucket(group_name, group_type, item_name, bool(item.get("is_conditional")))
            normalized_item = {
                "document_id": slugify(item.get("name") or "document"),
                "name": item_name,
                "group_name": group.get("group_name"),
                "group_type": group_type or None,
                "original_count": item.get("original_count"),
                "copy_count": item.get("copy_count"),
                "conditions": [compact_whitespace(value) for value in item.get("conditions") or [] if compact_whitespace(value)],
                "attachment_label": item.get("attachment_label"),
                "attachment_path": item.get("attachment_path"),
            }
            if item.get("attachment_path") or item.get("attachment_label"):
                forms.append(
                    {
                        "name": normalized_item["name"],
                        "attachment_label": item.get("attachment_label"),
                        "attachment_path": item.get("attachment_path"),
                    }
                )
            if item.get("notes"):
                notes.extend(compact_whitespace(note) for note in item["notes"] if compact_whitespace(note))

            if bucket == "notes":
                notes.append(item_name)
            elif bucket == "presented":
                presented.append(normalized_item)
            elif bucket == "conditional":
                conditional.append(normalized_item)
            else:
                required.append(normalized_item)

    return {
        "required": required,
        "conditional": conditional,
        "presented": presented,
        "notes": list(dict.fromkeys(compact_whitespace(note) for note in notes if compact_whitespace(note))),
        "forms": forms,
        "empty_groups": list(dict.fromkeys(name for name in empty_groups if name)),
        "document_count": len(required) + len(conditional) + len(presented),
    }


def _normalize_step(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "step_id": step.get("step_id"),
        "title": step.get("title"),
        "content": compact_whitespace(step.get("content") or ""),
        "actor": step.get("actor"),
        "channel_hint": step.get("channel_hint"),
        "time_hint": step.get("time_hint"),
    }


def _pick_primary_result(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    return results[0] if results else None


def _build_timing_summary(methods: list[dict[str, Any]]) -> dict[str, Any]:
    unique_times = []
    for method in methods:
        value = method.get("processing_time_text")
        if value and value not in unique_times:
            unique_times.append(value)
    return {
        "unique_processing_times": unique_times,
        "method_count": len(methods),
    }


def _document_signal(payload: dict[str, Any], normalized_documents: dict[str, Any]) -> dict[str, bool]:
    section_presence = payload.get("quality", {}).get("section_presence", {})
    documents_section_present = bool(section_presence.get("thanh_phan_ho_so")) or bool(
        compact_whitespace(payload.get("raw_sections", {}).get("thanh_phan_ho_so") or "")
    )
    has_structured_documents = bool(
        normalized_documents["required"] or normalized_documents["conditional"] or normalized_documents["presented"]
    )
    has_note_documents = bool(normalized_documents["notes"])
    documents_declared_empty = documents_section_present and not has_structured_documents and not has_note_documents and bool(
        normalized_documents["empty_groups"]
    )
    documents_only_in_notes = documents_section_present and not has_structured_documents and has_note_documents
    missing_documents = not documents_section_present and not has_structured_documents and not has_note_documents

    return {
        "missing_documents": missing_documents,
        "documents_section_present": documents_section_present,
        "documents_declared_empty": documents_declared_empty,
        "documents_only_in_notes": documents_only_in_notes,
    }


def _extract_authorities(value: str | None) -> list[str]:
    if not value:
        return []
    cleaned = value.replace("\r", "\n")
    parts = [compact_whitespace(item) for item in cleaned.split("\n") if _is_meaningful_text(item)]
    if not parts:
        parts = [compact_whitespace(value)] if _is_meaningful_text(value) else []
    return list(dict.fromkeys(parts))


def _extract_receiving_places(value: str | None) -> list[str]:
    if not value:
        return []
    cleaned = value.replace("\r", "\n")
    parts = []
    for line in cleaned.split("\n"):
        normalized = compact_whitespace(line.lstrip("- ").strip())
        if _is_meaningful_text(normalized):
            parts.append(normalized)
    return list(dict.fromkeys(parts))


def _normalize_channel(value: str | None) -> str | None:
    lowered = compact_whitespace(value or "").lower()
    if not lowered:
        return None
    if "trực tuyến" in lowered:
        return "online"
    if "bưu chính" in lowered:
        return "postal"
    if "trực tiếp" in lowered:
        return "in_person"
    return lowered


def _document_bucket(group_name: str, group_type: str, item_name: str, is_conditional: bool) -> str:
    group_key = f"{group_name} {group_type}".lower()
    item_key = item_name.lower()

    if "lưu ý" in group_key or "ghi chú" in group_key:
        return "notes"
    if "xuất trình" in group_key:
        return "presented"
    if is_conditional:
        return "conditional"
    if any(phrase in item_key for phrase in ["trường hợp", "nếu ", "nếu có", "đối với trường hợp"]):
        return "conditional"
    if any(
        phrase in item_key
        for phrase in [
            "người tiếp nhận có trách nhiệm",
            "người yêu cầu",
            "bản chụp",
            "việc xác định",
            "không được yêu cầu",
            "thực hiện việc nộp/xuất trình",
        ]
    ):
        return "notes"
    return "required"


def _is_process_heading(step: dict[str, Any]) -> bool:
    content = compact_whitespace(step.get("content") or "")
    return content in {"* Lưu ý:", "Lưu ý:"}


def _extract_process_notes(steps: list[dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    in_notes = False
    for step in steps:
        content = compact_whitespace(step.get("content") or "")
        if not content:
            continue
        if content in {"* Lưu ý:", "Lưu ý:"}:
            in_notes = True
            continue
        if in_notes:
            notes.append(content)
    return notes


def _is_meaningful_text(value: str | None) -> bool:
    cleaned = compact_whitespace(value or "")
    return cleaned not in {"", "Không có thông tin"}
