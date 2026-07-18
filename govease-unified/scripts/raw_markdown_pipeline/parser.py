from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from .documents import parse_documents
from .meta import parse_meta
from .methods import parse_submission_methods
from .process import parse_process
from .quality import build_quality
from .sections import split_sections
from .tables import extract_markdown_tables
from .utils import compact_whitespace, read_text, sha256_text


def parse_procedure_markdown(path: str | Path, *, parser_version: str = "0.1.0") -> dict[str, Any]:
    markdown_path = Path(path)
    text = read_text(markdown_path)
    title, sections = split_sections(text)
    section_map = {section.key: section for section in sections}
    parse_warnings: list[str] = []

    meta = parse_meta(section_map.get("thong_tin_chung").body if "thong_tin_chung" in section_map else "")
    procedure_code = str(meta.get("procedure_code") or markdown_path.parent.name.replace("_", "."))
    source_url = str(meta.get("source_url") or "")

    methods, method_warnings = parse_submission_methods(
        section_map.get("cach_thuc_thuc_hien").body if "cach_thuc_thuc_hien" in section_map else ""
    )
    parse_warnings.extend(method_warnings)

    documents, attachments, document_warnings = parse_documents(
        section_map.get("thanh_phan_ho_so").body if "thanh_phan_ho_so" in section_map else ""
    )
    parse_warnings.extend(document_warnings)

    legal_basis = _parse_legal_basis(section_map.get("can_cu_phap_ly").body if "can_cu_phap_ly" in section_map else "")
    results = _parse_results(section_map.get("ket_qua_xu_ly").body if "ket_qua_xu_ly" in section_map else "")
    related_procedures = _parse_related(section_map.get("thu_tuc_lien_quan").body if "thu_tuc_lien_quan" in section_map else "")
    conditions_text = section_map.get("yeu_cau_dieu_kien").body if "yeu_cau_dieu_kien" in section_map else ""
    keywords = _parse_keywords(section_map.get("tu_khoa").body if "tu_khoa" in section_map else "")
    overview_description = _none_if_missing(section_map.get("mo_ta").body if "mo_ta" in section_map else "")
    process_body = section_map.get("trinh_tu_thuc_hien").body if "trinh_tu_thuc_hien" in section_map else ""

    quality = build_quality(
        section_keys=set(section_map),
        parse_warnings=parse_warnings,
        methods_count=len(methods),
        document_group_count=len(documents["groups"]),
    )

    return {
        "schema_version": "1.0",
        "extracted_at": str(date.today()),
        "source": {
            "procedure_code": procedure_code,
            "source_markdown_path": str(markdown_path),
            "source_url": source_url or None,
            "parser_version": parser_version,
            "content_hash": sha256_text(text),
        },
        "meta": {
            "title": title,
            "decision_number": meta.get("decision_number"),
            "level": meta.get("level"),
            "procedure_type": meta.get("procedure_type"),
            "field": meta.get("field"),
            "target_users": meta.get("target_users") or [],
            "authority": meta.get("authority") or _none_if_missing(section_map.get("co_quan_thuc_hien").body if "co_quan_thuc_hien" in section_map else ""),
            "receiving_address": meta.get("receiving_address"),
            "delegated_authority": meta.get("delegated_authority"),
            "coordinating_authority": meta.get("coordinating_authority"),
        },
        "related_procedures": related_procedures,
        "overview": {
            "short_summary": None,
            "description": overview_description,
            "keywords": keywords,
        },
        "process": {
            "raw_text": _none_if_missing(process_body),
            "steps": parse_process(process_body),
            "milestones": [],
        },
        "submission_methods": methods,
        "documents": documents,
        "eligibility": {
            "raw_text": _none_if_missing(conditions_text),
            "conditions": _split_condition_lines(conditions_text),
            "special_cases": [],
            "warnings": [],
        },
        "results": results,
        "legal_basis": legal_basis,
        "attachments": attachments,
        "quality": quality,
        "raw_sections": {section.key: section.body or None for section in sections},
    }


def _parse_legal_basis(section_text: str) -> list[dict[str, str | None]]:
    tables = extract_markdown_tables(section_text.splitlines())
    if tables:
        first = tables[0]
        return [
            {
                "title": compact_whitespace(row.get("Tên văn bản pháp lý") or ""),
                "code": _none_if_missing(row.get("Mã văn bản")),
            }
            for row in first["rows"]
            if compact_whitespace(row.get("Tên văn bản pháp lý") or "")
        ]
    return []


def _parse_results(section_text: str) -> list[dict[str, str | None]]:
    results = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("*"):
            continue
        raw_text = compact_whitespace(stripped.lstrip("*").strip())
        if not raw_text:
            continue
        code = None
        if "(Mã:" in raw_text:
            prefix, suffix = raw_text.rsplit("(Mã:", 1)
            raw_text = compact_whitespace(prefix.rstrip(". "))
            code = compact_whitespace(suffix.rstrip(") ").replace("`", ""))
        results.append({"name": raw_text, "result_code": code, "raw_text": raw_text})
    return results


def _parse_related(section_text: str) -> list[dict[str, str | None]]:
    if not section_text or "Không có thông tin" in section_text:
        return []
    items = []
    for line in section_text.splitlines():
        text = compact_whitespace(line.lstrip("*- ").strip())
        if text:
            items.append({"title": text, "procedure_code": None, "source_text": text})
    return items


def _parse_keywords(section_text: str) -> list[str]:
    if not section_text or "Không có thông tin" in section_text:
        return []
    return [item.strip() for item in section_text.replace("\n", ",").split(",") if item.strip()]


def _split_condition_lines(section_text: str) -> list[str]:
    if not section_text or "Không có thông tin" in section_text:
        return []
    text = section_text.replace("\r", "").strip()
    split_parts = [item.strip() for item in text.splitlines() if compact_whitespace(item)]
    if len(split_parts) == 1:
        split_parts = [
            item.strip()
            for item in _split_by_markers(text, pattern=r"(?=(?:^|\s)[a-zđ]\))")
            if compact_whitespace(item)
        ]
    parts = [compact_whitespace(item) for item in split_parts if compact_whitespace(item)]
    return parts


def _split_by_markers(text: str, *, pattern: str) -> list[str]:
    return [part for part in re.split(pattern, text) if part.strip()]


def _none_if_missing(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = compact_whitespace(value)
    if cleaned in {"", "Không có thông tin"}:
        return None
    return cleaned
