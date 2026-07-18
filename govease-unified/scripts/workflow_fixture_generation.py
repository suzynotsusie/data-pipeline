from __future__ import annotations

from typing import Any


GENERIC_SUBMISSION = {
    "requester": {
        "full_name": "A",
        "identity_number": "12345X",
    },
    "reference_date": "32/13/2026",
    "signature_present": False,
}

GENERIC_EXPECTED_RULE_IDS = [
    "full-name-format",
    "identity-number-format",
    "date-format",
    "missing-signature",
]


def ensure_fixture_coverage(
    domain_key: str,
    records: list[dict[str, Any]],
    intake_cases: list[dict[str, Any]],
    submission_cases: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered_records = [
        record for record in records if str(record.get("procedure_code") or "").strip()
    ]
    intake_by_code = {
        str(case.get("expected_procedure_code") or "").strip(): case
        for case in intake_cases
        if str(case.get("expected_procedure_code") or "").strip()
    }
    submission_by_code = {
        str(case.get("procedure_code") or "").strip(): case
        for case in submission_cases
        if str(case.get("procedure_code") or "").strip()
    }

    covered_intake: list[dict[str, Any]] = []
    covered_submission: list[dict[str, Any]] = []
    for index, record in enumerate(ordered_records, start=1):
        code = str(record["procedure_code"])
        covered_intake.append(
            intake_by_code.get(code) or _build_intake_case(domain_key, index, record)
        )
        covered_submission.append(
            submission_by_code.get(code) or _build_submission_case(domain_key, index, record)
        )

    return covered_intake, covered_submission


def _build_intake_case(
    domain_key: str,
    index: int,
    record: dict[str, Any],
) -> dict[str, Any]:
    title = str(record.get("procedure_title") or "thủ tục này").strip()
    subdomain_label = str(record.get("subdomain_label") or "").strip().lower()
    title_lower = title[:1].lower() + title[1:] if title else "thủ tục này"
    expected_terms = [title]
    if subdomain_label:
        expected_terms.append(subdomain_label)
    return {
        "id": f"intake-{domain_key}-{index:02d}",
        "user_need": f"Tôi cần làm thủ tục {title_lower}.",
        "expected_procedure_code": str(record["procedure_code"]),
        "expected_terms": expected_terms,
    }


def _build_submission_case(
    domain_key: str,
    index: int,
    record: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": f"submission-{domain_key}-{index:02d}",
        "procedure_code": str(record["procedure_code"]),
        "submission": dict(GENERIC_SUBMISSION),
        "expected_rule_ids": list(GENERIC_EXPECTED_RULE_IDS),
    }
