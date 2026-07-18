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


def main() -> None:
    summary: list[dict[str, Any]] = []
    for bucket, sample_dir in SAMPLE_DIRS.items():
        golden_dir = GOLDEN_ROOT / bucket
        golden_dir.mkdir(parents=True, exist_ok=True)
        for sample_path in sorted(sample_dir.glob("*.json")):
            payload = json.loads(sample_path.read_text(encoding="utf-8"))
            stable_payload = make_stable_snapshot(payload)
            output_path = golden_dir / sample_path.name
            output_path.write_text(json.dumps(stable_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            summary.append({"bucket": bucket, "file": str(output_path)})

    print(json.dumps({"golden_files": summary}, ensure_ascii=False, indent=2))


def make_stable_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    cloned = json.loads(json.dumps(payload, ensure_ascii=False))
    cloned.pop("extracted_at", None)
    return cloned


if __name__ == "__main__":
    main()
