from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT.parent / "data" / "procedure_payloads"
SUMMARY_PATH = DATA_ROOT / "build_report.json"


def main() -> int:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    expected_count = int(summary["count"])
    files = sorted(DATA_ROOT.glob("*_payload.json"))
    issues: list[str] = []
    if len(files) != expected_count:
        issues.append(f"file_count_mismatch:{len(files)}!={expected_count}")

    sample_issues: list[dict[str, Any]] = []
    for path in files[:160]:
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
    for key in ("procedure_code", "title", "source", "documents", "steps", "input_fields", "guidance", "next_steps"):
        if key not in payload:
            issues.append(f"missing:{key}")
    if not isinstance(payload.get("documents", {}).get("normally_required"), list):
        issues.append("normally_required_not_list")
    if not isinstance(payload.get("documents", {}).get("conditional"), list):
        issues.append("conditional_not_list")
    if not isinstance(payload.get("steps"), list):
        issues.append("steps_not_list")
    if not isinstance(payload.get("input_fields"), list):
        issues.append("input_fields_not_list")
    return issues


if __name__ == "__main__":
    raise SystemExit(main())
