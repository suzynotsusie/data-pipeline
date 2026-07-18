from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parent
MAPPING_PATH = ROOT / "data" / "catalog" / "citizen_procedure_mapping.csv"
OUTPUT_PATH = ROOT / "data" / "reports" / "citizen_production_audit.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.procedures import procedure_detail
from govease_ai.procedure_data import load_procedure_store

MOJIBAKE_RE = re.compile(
    r"(?:Ã[a-zA-ZÀ-ỹ]|Ä[a-zA-ZÀ-ỹ]|Å[a-zA-ZÀ-ỹ]|Æ[a-zA-ZÀ-ỹ]|á».|áº.|â€.|Â[a-zA-ZÀ-ỹ])"
)
CHANNEL_CODE_RE = re.compile(r"\b(?:in_person|online|postal)\b", re.IGNORECASE)


def main() -> None:
    store = load_procedure_store()
    rows = list(csv.DictReader(MAPPING_PATH.open("r", encoding="utf-8-sig", newline="")))
    workflow_rows = [row for row in rows if row.get("persona") == "citizen" and _as_bool(row.get("in_workflow_dataset"))]

    domains: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in workflow_rows:
        domains[str(row["group_key"])].append(row)

    domain_reports: list[dict[str, Any]] = []
    totals = {
        "procedures": 0,
        "fallback_summary": 0,
        "document_issues": 0,
        "text_issues": 0,
    }

    for domain_key, domain_rows in sorted(domains.items()):
        procedure_reports = []
        counts = {
            "procedures": 0,
            "fallback_summary": 0,
            "document_issues": 0,
            "text_issues": 0,
        }
        for row in sorted(domain_rows, key=lambda item: str(item["procedure_code"])):
            code = str(row["procedure_code"])
            record = store.find(code)
            if record is None:
                issue = {
                    "procedure_code": code,
                    "procedure_title": row.get("procedure_title") or "",
                    "missing_runtime_record": True,
                    "fallback_summary": None,
                    "document_issues": ["missing_runtime_record"],
                    "text_issues": ["missing_runtime_record"],
                }
                procedure_reports.append(issue)
                counts["procedures"] += 1
                counts["document_issues"] += 1
                counts["text_issues"] += 1
                continue

            detail = procedure_detail(record)
            checklist = detail.get("checklist") or {}
            fallback_summary = not bool(
                record.data.get("next_step_summary")
                or ((record.data.get("next_steps") or {}).get("summary") if isinstance(record.data.get("next_steps"), dict) else None)
            )
            document_issues = _document_issues(checklist)
            text_issues = _text_issues(detail, record.data)

            report = {
                "procedure_code": code,
                "procedure_title": detail.get("title") or row.get("procedure_title") or "",
                "fallback_summary": fallback_summary,
                "document_issues": document_issues,
                "text_issues": text_issues,
                "document_count": len(checklist.get("documents") or []),
                "conditional_document_count": len(checklist.get("conditional_documents") or []),
                "user_step_count": len(checklist.get("user_steps") or []),
                "next_step_summary": checklist.get("next_step_summary"),
                "overview_summary": checklist.get("overview_summary"),
                "submission_place_summary": checklist.get("submission_place_summary"),
                "processing_time_summary": checklist.get("processing_time_summary"),
            }
            procedure_reports.append(report)
            counts["procedures"] += 1
            if fallback_summary:
                counts["fallback_summary"] += 1
            if document_issues:
                counts["document_issues"] += 1
            if text_issues:
                counts["text_issues"] += 1

        totals["procedures"] += counts["procedures"]
        totals["fallback_summary"] += counts["fallback_summary"]
        totals["document_issues"] += counts["document_issues"]
        totals["text_issues"] += counts["text_issues"]
        domain_reports.append(
            {
                "domain_key": domain_key,
                "procedure_count": counts["procedures"],
                "fallback_summary_count": counts["fallback_summary"],
                "document_issue_count": counts["document_issues"],
                "text_issue_count": counts["text_issues"],
                "procedures": procedure_reports,
            }
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": "2026-07-18",
        "scope": "citizen_workflow_runtime",
        "totals": totals,
        "domains": domain_reports,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUTPUT_PATH)


def _document_issues(checklist: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    documents = checklist.get("documents") or []
    conditional = checklist.get("conditional_documents") or []

    if not documents:
        issues.append("no_primary_documents")
    if any(not str(item.get("name") or "").strip() for item in documents):
        issues.append("unnamed_primary_document")
    if any(len(str(item.get("name") or "")) > 280 for item in documents):
        issues.append("overlong_primary_document_label")
    if conditional and all("ủy quyền" in str(item.get("name") or "").lower() or "bưu chính" in str(item.get("name") or "").lower() for item in conditional):
        issues.append("conditional_documents_only_edge_cases")
    return issues


def _text_issues(detail: dict[str, Any], raw_data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    checklist = detail.get("checklist") or {}
    fields = [
        detail.get("title"),
        checklist.get("next_step_summary"),
        checklist.get("overview_summary"),
        checklist.get("submission_place_summary"),
        checklist.get("processing_time_summary"),
    ]
    common_errors = detail.get("guidance", {}).get("common_errors") if isinstance(detail.get("guidance"), dict) else []
    if isinstance(common_errors, list):
        fields.extend(common_errors[:3])

    text_blob = "\n".join(str(item) for item in fields if item)
    if MOJIBAKE_RE.search(text_blob):
        issues.append("mojibake_detected")
    if CHANNEL_CODE_RE.search(text_blob):
        issues.append("channel_codes_not_localized")
    if checklist.get("processing_time_summary") and checklist.get("next_step_summary"):
        if str(checklist["processing_time_summary"]).strip() == str(checklist["next_step_summary"]).strip():
            issues.append("processing_time_uses_summary_text")
    if raw_data.get("processing_note") and checklist.get("processing_time_summary"):
        if str(raw_data.get("processing_note")).strip() == str(checklist.get("processing_time_summary")).strip():
            issues.append("processing_time_falls_back_to_processing_note")
    return issues


def _as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


if __name__ == "__main__":
    main()
