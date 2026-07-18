from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = PROJECT_ROOT / "data" / "normalized_structured_samples"

REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "normalizer_version",
    "source",
    "procedure",
    "submission",
    "documents",
    "process",
    "eligibility",
    "results",
    "legal_basis",
    "attachments",
    "signals",
}


def main() -> int:
    sample_paths = sorted(SAMPLES_DIR.glob("*_normalized_structured.json"))
    if not sample_paths:
        print(json.dumps({"error": "No normalized samples found."}, ensure_ascii=False, indent=2))
        return 1

    reports: list[dict[str, Any]] = []
    has_error = False
    for sample_path in sample_paths:
        payload = json.loads(sample_path.read_text(encoding="utf-8"))
        issues = validate_payload(payload)
        reports.append(
            {
                "file": str(sample_path),
                "procedure_code": payload.get("source", {}).get("procedure_code"),
                "issues": issues,
            }
        )
        if issues:
            has_error = True

    print(json.dumps({"reports": reports, "valid": not has_error}, ensure_ascii=False, indent=2))
    return 1 if has_error else 0


def validate_payload(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    missing_top_level = sorted(REQUIRED_TOP_LEVEL_KEYS - payload.keys())
    if missing_top_level:
        issues.append(f"missing_top_level:{','.join(missing_top_level)}")

    source = payload.get("source")
    if not isinstance(source, dict) or not source.get("procedure_code"):
        issues.append("source_invalid")

    submission = payload.get("submission")
    if not isinstance(submission, dict) or not isinstance(submission.get("methods"), list):
        issues.append("submission_invalid")

    documents = payload.get("documents")
    if not isinstance(documents, dict):
        issues.append("documents_invalid")
    else:
        if not isinstance(documents.get("required"), list):
            issues.append("documents_required_not_list")
        if not isinstance(documents.get("conditional"), list):
            issues.append("documents_conditional_not_list")

    return issues


if __name__ == "__main__":
    raise SystemExit(main())
