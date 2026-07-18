from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_ROOT.parent
PIPELINE_ROOT = PROJECT_ROOT.parent
RAW_DATA_ROOT = PIPELINE_ROOT / "raw_data"
CATALOG_CSV = PROJECT_ROOT / "data" / "catalog" / "citizen_procedure_mapping.csv"
REPORT_DIR = PROJECT_ROOT / "data" / "catalog"
REPORT_JSON = REPORT_DIR / "procedure_coverage_report.json"

sys.path.insert(0, str(SCRIPT_ROOT))

from raw_markdown_pipeline import parse_procedure_markdown  # noqa: E402


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    procedures = load_unique_procedures(CATALOG_CSV)
    report_rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    workflow_counts: dict[str, Counter[str]] = defaultdict(Counter)

    for procedure in procedures:
        code = procedure["procedure_code"]
        markdown_path = RAW_DATA_ROOT / code.replace(".", "_") / f"{code.replace('.', '_')}_procedure_detail.md"
        status, details = audit_procedure(procedure, markdown_path)
        counts[status] += 1
        workflow_counts[procedure["group_key"]][status] += 1
        report_rows.append(
            {
                **procedure,
                "status": status,
                "raw_markdown_path": str(markdown_path) if markdown_path.exists() else None,
                **details,
            }
        )

    summary = {
        "source_csv": str(CATALOG_CSV),
        "total_unique_procedure_codes": len(procedures),
        "status_counts": dict(counts),
        "workflow_group_counts": {group: dict(counter) for group, counter in sorted(workflow_counts.items())},
        "examples": build_examples(report_rows),
        "rows": report_rows,
    }
    REPORT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary | {"rows": f"{len(report_rows)} rows written to {REPORT_JSON}"}, ensure_ascii=False, indent=2))
    return 0


def load_unique_procedures(csv_path: Path) -> list[dict[str, str]]:
    unique: dict[str, dict[str, str]] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            code = (row.get("procedure_code") or "").strip()
            if not code or code in unique:
                continue
            unique[code] = {
                "procedure_code": code,
                "procedure_title": (row.get("procedure_title") or "").strip(),
                "group_key": (row.get("group_key") or "").strip(),
                "workflow_family": (row.get("workflow_family") or "").strip(),
                "support_level": (row.get("support_level") or "").strip(),
                "raw_data_available_csv": (row.get("raw_data_available") or "").strip(),
                "field": (row.get("field") or "").strip(),
                "source_url": (row.get("source_url") or "").strip(),
            }
    return sorted(unique.values(), key=lambda item: item["procedure_code"])


def audit_procedure(procedure: dict[str, str], markdown_path: Path) -> tuple[str, dict[str, Any]]:
    if not markdown_path.exists():
        return (
            "missing",
            {
                "parse_warnings": [],
                "needs_manual_review": None,
                "method_count": 0,
                "document_group_count": 0,
                "result_count": 0,
                "legal_basis_count": 0,
                "error": None,
            },
        )

    try:
        payload = parse_procedure_markdown(markdown_path)
    except Exception as exc:  # noqa: BLE001
        return (
            "warning",
            {
                "parse_warnings": [],
                "needs_manual_review": None,
                "method_count": 0,
                "document_group_count": 0,
                "result_count": 0,
                "legal_basis_count": 0,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )

    parse_warnings = list(payload["quality"]["parse_warnings"])
    manual_review = bool(payload["quality"]["needs_manual_review"])

    if manual_review:
        status = "manual_review"
    elif parse_warnings:
        status = "warning"
    else:
        status = "ready"

    return (
        status,
        {
            "parse_warnings": parse_warnings,
            "needs_manual_review": manual_review,
            "method_count": len(payload["submission_methods"]),
            "document_group_count": len(payload["documents"]["groups"]),
            "result_count": len(payload["results"]),
            "legal_basis_count": len(payload["legal_basis"]),
            "error": None,
        },
    )


def build_examples(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    examples: dict[str, list[dict[str, Any]]] = {}
    for status in ("ready", "warning", "manual_review", "missing"):
        sample_rows = [row for row in rows if row["status"] == status][:10]
        examples[status] = [
            {
                "procedure_code": row["procedure_code"],
                "procedure_title": row["procedure_title"],
                "group_key": row["group_key"],
                "parse_warnings": row["parse_warnings"],
                "error": row["error"],
            }
            for row in sample_rows
        ]
    return examples


if __name__ == "__main__":
    raise SystemExit(main())
