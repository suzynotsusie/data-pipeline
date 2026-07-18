from __future__ import annotations

import json
import unittest
from pathlib import Path

from govease_ai import ProcedureAssistant


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_test_cases(filename: str) -> list[dict]:
    candidates = [
        PROJECT_ROOT / "data" / "test_cases" / filename,
        PROJECT_ROOT.parent / "data" / "test_cases" / filename,
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Could not find fixture {filename} in: {candidates}")


class SubmissionValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.assistant = ProcedureAssistant()
        cls.submission_cases = _load_test_cases("submission_cases.json")

    def test_generated_submission_cases_catch_expected_errors(self) -> None:
        for case in self.submission_cases:
            with self.subTest(case=case["id"]):
                result = self.assistant.check_submission(case["procedure_code"], case["submission"])
                actual = {issue["rule_id"] for issue in result["issues"]}
                expected = set(case["expected_rule_ids"])
                self.assertTrue(expected.issubset(actual), f"missing={expected - actual}, actual={actual}")

    def test_clean_temporary_residence_submission_is_ready(self) -> None:
        result = self.assistant.check_submission(
            "1.004194",
            {
                "applicant": {
                    "full_name": "Lê Văn F",
                    "identity_number": "012345678904",
                    "is_minor": False,
                },
                "temporary_address": {
                    "province_code": "01",
                    "district_code": "001",
                    "ward_code": "00001",
                    "detail": "45 Lê Lợi",
                },
                "permanent_address": {
                    "province_code": "79",
                    "district_code": "760",
                    "ward_code": "26734",
                    "detail": "89 Hai Bà Trưng",
                },
                "stay_start_date": "2026-07-10",
                "stay_end_date": "2026-10-10",
                "accommodation_proof": "Hợp đồng thuê nhà",
                "signature_present": True,
            },
        )
        self.assertTrue(result["ready_to_submit"], result)
        self.assertEqual([], result["issues"])

    def test_validation_layers_are_reported_separately(self) -> None:
        result = self.assistant.check_submission(
            "1.004194",
            {
                "applicant": {
                    "full_name": "Le Van D",
                    "identity_number": "abc",
                    "is_minor": False,
                },
                "temporary_address": {
                    "province_code": "01",
                    "district_code": "001",
                    "ward_code": "00001",
                    "detail": "12 Nguyen Trai",
                },
                "permanent_address": {
                    "province_code": "01",
                    "district_code": "001",
                    "ward_code": "00001",
                    "detail": "12 Nguyen Trai",
                },
                "stay_start_date": "2026-07-10",
                "stay_end_date": "2026-07-09",
                "accommodation_proof": "",
                "signature_present": False,
            },
        )
        self.assertTrue(result["validation_layers"]["rules"]["enabled"])
        self.assertFalse(result["validation_layers"]["llm_semantic"]["enabled"])
        self.assertEqual("disabled_by_default", result["validation_layers"]["llm_semantic"]["reason"])

    def test_issues_are_ready_for_field_level_frontend_rendering(self) -> None:
        result = self.assistant.check_submission(
            "1.004194",
            {"applicant": {"identity_number": "bad"}, "signature_present": False},
        )
        self.assertTrue(result["issues"])
        for issue in result["issues"]:
            self.assertIn("evidence", issue)
            self.assertIn("blocking", issue)
            self.assertIn("source_url", issue)

    def test_telex_name_typo_is_reported(self) -> None:
        result = self.assistant.check_submission(
            "1.001193",
            {
                "child": {
                    "full_name": "Nguyeenx An",
                    "birth_date": "2026-07-01",
                    "gender": "Nam",
                    "birth_place": "Thành phố Hà Nội",
                    "native_place": "Thành phố Hà Nội",
                },
                "mother": {"identity_number": "012345678901"},
                "requester": {"identity_number": "012345678901", "relationship_to_child": "Mẹ"},
                "birth_certificate": {"available": True},
                "submission": {"signature_or_confirmation": True},
            },
        )
        self.assertIn("possible-telex-typo", {issue["rule_id"] for issue in result["issues"]})

    def test_nine_digit_identity_number_is_rejected(self) -> None:
        issues = self.assistant.validator.validate(
            "1.004194",
            {"applicant": {"identity_number": "123456789"}},
        )
        self.assertIn("identity-number-format", {issue["rule_id"] for issue in issues})

    def test_synthetic_identity_number_is_flagged(self) -> None:
        issues = self.assistant.validator.validate(
            "1.004194",
            {"applicant": {"identity_number": "123456789012"}},
        )
        self.assertIn("identity-number-looks-synthetic", {issue["rule_id"] for issue in issues})

    def test_incomplete_administrative_address_is_reported(self) -> None:
        issues = self.assistant.validator.validate(
            "1.004194",
            {"temporary_address": {"province_code": "01", "detail": "12A"}},
        )
        rule_ids = {issue["rule_id"] for issue in issues}
        self.assertIn("incomplete-administrative-address", rule_ids)
        self.assertNotIn("address-detail-too-short", rule_ids)

    def test_short_address_detail_is_reported(self) -> None:
        issues = self.assistant.validator.validate(
            "1.004194",
            {
                "temporary_address": {
                    "province_code": "01",
                    "district_code": "001",
                    "ward_code": "00001",
                    "detail": "12A",
                }
            },
        )
        self.assertIn("address-detail-too-short", {issue["rule_id"] for issue in issues})


if __name__ == "__main__":
    unittest.main()
