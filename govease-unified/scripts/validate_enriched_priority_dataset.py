from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = PROJECT_ROOT / "data" / "enriched_structured_priority"
SUMMARY_PATH = PROJECT_ROOT / "data" / "catalog" / "enriched_priority_report.json"


def main() -> int:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    expected_count = int(summary["count"])
    files = sorted(DATASET_DIR.glob("*_enriched_structured.json"))
    issues: list[str] = []
    if len(files) != expected_count:
        issues.append(f"file_count_mismatch:{len(files)}!= {expected_count}")

    sample_issues: list[dict[str, Any]] = []
    for path in files[:120]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        local = validate_payload(payload)
        if local:
            sample_issues.append({"file": str(path), "issues": local})

    result = {
        "expected_count": expected_count,
        "file_count": len(files),
        "sample_issues": sample_issues,
        "issues": issues,
        "valid": not issues and not sample_issues,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if issues or sample_issues else 0


def validate_payload(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ("source", "experience", "guidance", "intake", "ui_hints", "provenance"):
        if key not in payload:
            issues.append(f"missing:{key}")
    if not isinstance(payload.get("guidance", {}).get("highlight_documents"), list):
        issues.append("highlight_documents_not_list")
    if not isinstance(payload.get("intake", {}).get("candidate_input_fields"), list):
        issues.append("candidate_input_fields_not_list")
    return issues


if __name__ == "__main__":
    raise SystemExit(main())
