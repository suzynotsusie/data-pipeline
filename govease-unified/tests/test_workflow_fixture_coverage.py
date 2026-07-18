from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = PROJECT_ROOT.parent


class WorkflowFixtureCoverageTests(unittest.TestCase):
    def test_workflow_cases_cover_every_procedure_code(self) -> None:
        workflows_root = PIPELINE_ROOT / "data" / "workflows"
        tests_root = PIPELINE_ROOT / "tests" / "workflows"
        for summary_path in sorted(workflows_root.glob("*/summary.csv")):
            workflow_key = summary_path.parent.name
            intake_path = tests_root / workflow_key / "intake_cases.json"
            submission_path = tests_root / workflow_key / "submission_cases.json"
            with self.subTest(workflow=workflow_key):
                self.assertTrue(intake_path.exists(), intake_path)
                self.assertTrue(submission_path.exists(), submission_path)

                with summary_path.open(encoding="utf-8") as handle:
                    summary_rows = list(csv.DictReader(handle))
                expected_codes = {
                    str(row.get("procedure_code") or "").strip()
                    for row in summary_rows
                    if str(row.get("procedure_code") or "").strip()
                }
                intake_cases = json.loads(intake_path.read_text(encoding="utf-8"))
                submission_cases = json.loads(submission_path.read_text(encoding="utf-8"))

                intake_codes = {case["expected_procedure_code"] for case in intake_cases}
                submission_codes = {case["procedure_code"] for case in submission_cases}

                self.assertEqual(expected_codes, intake_codes)
                self.assertEqual(expected_codes, submission_codes)
                self.assertEqual(len(intake_cases), len(intake_codes))
                self.assertEqual(len(submission_cases), len(submission_codes))


if __name__ == "__main__":
    unittest.main()
