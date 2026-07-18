"""
Run retrieval, intake, and pre-submission sanity checks.

This script uses the deterministic local assistant path so it can run
quickly before or after Chroma training.

Run:
    python query_test.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from govease_ai import ProcedureAssistant


PROJECT_ROOT = Path(__file__).resolve().parent
INTAKE_CASES = PROJECT_ROOT / "data" / "test_cases" / "intake_cases.json"
SUBMISSION_CASES = PROJECT_ROOT / "data" / "test_cases" / "submission_cases.json"


def main() -> None:
    _configure_stdout()
    assistant = ProcedureAssistant()
    intake_ok = _run_intake_cases(assistant)
    submission_ok = _run_submission_cases(assistant)
    if not intake_ok or not submission_ok:
        raise SystemExit(1)


def _run_intake_cases(assistant: ProcedureAssistant) -> bool:
    cases = _read_cases(INTAKE_CASES)
    print(f"\nIntake cases: {len(cases)}")
    ok = True
    for case in cases:
        result = assistant.guided_intake(case["user_need"])
        actual_code = (result.get("procedure") or {}).get("code")
        expected_code = case["expected_procedure_code"]
        checklist_text = json.dumps(result.get("checklist", {}), ensure_ascii=False).lower()
        expected_terms = [term.lower() for term in case.get("expected_terms", [])]
        passed = actual_code == expected_code and all(term in checklist_text for term in expected_terms)
        ok = ok and passed
        status = "PASS" if passed else "FAIL"
        missing_terms = sorted(term for term in case.get("expected_terms", []) if term.lower() not in checklist_text)
        suffix = f" missing_terms={missing_terms}" if missing_terms else ""
        print(f"\n  {status} {case['id']}: expected {expected_code}, got {actual_code}{suffix}")
        print(f"    Question: {case['user_need']}")
        print("    Expected:")
        print(_indent(_to_json({"procedure_code": expected_code, "terms": case.get("expected_terms", [])}), "      "))
        print("    AI answer:")
        print(_indent(str(result.get("answer") or ""), "      "))
        print("    AI raw structured data (full checklist, not final answer):")
        print(_indent(_to_json(_intake_answer(result)), "      "))
    return ok


def _run_submission_cases(assistant: ProcedureAssistant) -> bool:
    cases = _read_cases(SUBMISSION_CASES)
    print(f"\nSubmission cases: {len(cases)}")
    ok = True
    for case in cases:
        result = assistant.check_submission(case["procedure_code"], case["submission"])
        actual_rule_ids = {issue["rule_id"] for issue in result["issues"]}
        expected_rule_ids = set(case.get("expected_rule_ids", []))
        expected_ready = case.get("expect_ready")
        readiness_matches = expected_ready is None or result["ready_to_submit"] is expected_ready
        passed = expected_rule_ids.issubset(actual_rule_ids) and readiness_matches
        ok = ok and passed
        status = "PASS" if passed else "FAIL"
        missing = sorted(expected_rule_ids - actual_rule_ids)
        suffix = f" missing={missing}" if missing else ""
        print(f"\n  {status} {case['id']}: {len(result['issues'])} issues{suffix}")
        print(f"    Question: Check submission for procedure {case['procedure_code']}")
        print(_indent(_to_json(case["submission"]), "      "))
        print("    Expected:")
        print(_indent(_to_json({"rule_ids": sorted(expected_rule_ids)}), "      "))
        print("    AI answer:")
        print(_indent(str(result.get("answer") or ""), "      "))
        print("    AI raw structured data (full checklist, not final answer):")
        print(_indent(_to_json(_submission_answer(result)), "      "))
    return ok


def _read_cases(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _intake_answer(result: dict) -> dict:
    return {
        "needs_clarification": result.get("needs_clarification"),
        "clarifying_question": result.get("clarifying_question"),
        "confidence": result.get("confidence"),
        "procedure": result.get("procedure"),
        "checklist": result.get("checklist"),
        "examples": result.get("examples"),
        "common_errors": result.get("common_errors"),
        "sources": result.get("sources"),
    }


def _submission_answer(result: dict) -> dict:
    return {
        "procedure": result.get("procedure"),
        "ready_to_submit": result.get("ready_to_submit"),
        "issues": result.get("issues"),
        "validation_layers": result.get("validation_layers"),
    }


def _to_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _indent(value: str, prefix: str) -> str:
    return "\n".join(f"{prefix}{line}" for line in value.splitlines())


if __name__ == "__main__":
    main()
