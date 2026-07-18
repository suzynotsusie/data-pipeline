from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIRS = {
    "raw_structured_samples": PROJECT_ROOT / "data" / "raw_structured_samples",
    "normalized_structured_samples": PROJECT_ROOT / "data" / "normalized_structured_samples",
}
GOLDEN_ROOT = PROJECT_ROOT / "data" / "golden"


def main() -> int:
    reports: list[dict[str, Any]] = []
    failed = False

    for bucket, sample_dir in SAMPLE_DIRS.items():
        golden_dir = GOLDEN_ROOT / bucket
        sample_files = sorted(sample_dir.glob("*.json"))
        golden_files = sorted(golden_dir.glob("*.json"))

        if len(sample_files) != len(golden_files):
            reports.append(
                {
                    "bucket": bucket,
                    "issues": [f"file_count_mismatch:{len(sample_files)}!={len(golden_files)}"],
                }
            )
            failed = True
            continue

        for sample_path in sample_files:
            golden_path = golden_dir / sample_path.name
            if not golden_path.exists():
                reports.append({"bucket": bucket, "file": sample_path.name, "issues": ["golden_missing"]})
                failed = True
                continue

            sample_payload = make_stable_snapshot(json.loads(sample_path.read_text(encoding="utf-8")))
            golden_payload = json.loads(golden_path.read_text(encoding="utf-8"))
            if sample_payload != golden_payload:
                reports.append({"bucket": bucket, "file": sample_path.name, "issues": ["content_mismatch"]})
                failed = True

    print(json.dumps({"reports": reports, "valid": not failed}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


def make_stable_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    cloned = json.loads(json.dumps(payload, ensure_ascii=False))
    cloned.pop("extracted_at", None)
    return cloned


if __name__ == "__main__":
    raise SystemExit(main())
