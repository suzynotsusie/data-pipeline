from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = PROJECT_ROOT / "data" / "raw_structured_samples"

REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "extracted_at",
    "source",
    "meta",
    "overview",
    "process",
    "submission_methods",
    "documents",
    "eligibility",
    "results",
    "legal_basis",
    "attachments",
    "quality",
    "raw_sections",
}


def main() -> int:
    sample_paths = sorted(SAMPLES_DIR.glob("*_raw_structured.json"))
    if not sample_paths:
        print(json.dumps({"error": "No raw_structured samples found."}, ensure_ascii=False, indent=2))
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
    if not isinstance(source, dict):
        issues.append("source_not_object")
    else:
        for key in ("procedure_code", "source_markdown_path", "parser_version", "content_hash"):
            if not source.get(key):
                issues.append(f"source_missing:{key}")

    process = payload.get("process")
    if not isinstance(process, dict):
        issues.append("process_not_object")
    else:
        steps = process.get("steps")
        if not isinstance(steps, list):
            issues.append("process_steps_not_list")
        else:
            for index, step in enumerate(steps, start=1):
                if not isinstance(step, dict):
                    issues.append(f"process_step_not_object:{index}")
                    continue
                if not step.get("step_id"):
                    issues.append(f"process_step_missing:step_id:{index}")
                if "content" not in step or not str(step.get("content", "")).strip():
                    issues.append(f"process_step_missing:content:{index}")

    documents = payload.get("documents")
    if not isinstance(documents, dict):
        issues.append("documents_not_object")
    else:
        groups = documents.get("groups")
        if not isinstance(groups, list):
            issues.append("documents_groups_not_list")

    quality = payload.get("quality")
    if not isinstance(quality, dict):
        issues.append("quality_not_object")
    else:
        if "parse_warnings" not in quality or not isinstance(quality.get("parse_warnings"), list):
            issues.append("quality_parse_warnings_invalid")
        if "needs_manual_review" not in quality or not isinstance(quality.get("needs_manual_review"), bool):
            issues.append("quality_needs_manual_review_invalid")

    return issues


if __name__ == "__main__":
    raise SystemExit(main())
