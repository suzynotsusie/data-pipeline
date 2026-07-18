from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = PROJECT_ROOT / "data" / "normalized_structured"
SUMMARY_PATH = PROJECT_ROOT / "data" / "catalog" / "normalized_structured_report.json"


def main() -> int:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    ready_count = int(summary["ready_count"])
    files = sorted(DATASET_DIR.glob("*_normalized_structured.json"))
    issues: list[str] = []

    if len(files) != ready_count:
        issues.append(f"file_count_mismatch:{len(files)}!= {ready_count}")

    sample_issues: list[dict[str, Any]] = []
    for path in files[:100]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        local_issues = validate_payload(payload)
        if local_issues:
            sample_issues.append({"file": str(path), "issues": local_issues})

    result = {
        "ready_count": ready_count,
        "file_count": len(files),
        "sample_issues": sample_issues,
        "valid": not issues and not sample_issues,
        "issues": issues,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if issues or sample_issues else 0


def validate_payload(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    documents = payload.get("documents", {})
    if not isinstance(documents.get("required"), list):
        issues.append("required_not_list")
    if not isinstance(documents.get("conditional"), list):
        issues.append("conditional_not_list")
    if not isinstance(documents.get("presented"), list):
        issues.append("presented_not_list")
    if not isinstance(documents.get("notes"), list):
        issues.append("notes_not_list")

    process = payload.get("process", {})
    if not isinstance(process.get("steps"), list):
        issues.append("process_steps_not_list")
    if not isinstance(process.get("notes"), list):
        issues.append("process_notes_not_list")

    return issues


if __name__ == "__main__":
    raise SystemExit(main())
