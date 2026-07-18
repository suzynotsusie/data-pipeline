from __future__ import annotations

import json
from pathlib import Path

from normalized_pipeline import normalize_raw_structured


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_SAMPLES_DIR = PROJECT_ROOT / "data" / "raw_structured_samples"
OUTPUT_DIR = PROJECT_ROOT / "data" / "normalized_structured_samples"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, object]] = []

    for sample_path in sorted(RAW_SAMPLES_DIR.glob("*_raw_structured.json")):
        payload = json.loads(sample_path.read_text(encoding="utf-8"))
        normalized = normalize_raw_structured(payload)
        output_path = OUTPUT_DIR / sample_path.name.replace("_raw_structured", "_normalized_structured")
        output_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        summary.append(
            {
                "procedure_code": normalized["source"]["procedure_code"],
                "output_path": str(output_path),
                "channels": normalized["submission"]["channels"],
                "required_documents": len(normalized["documents"]["required"]),
                "conditional_documents": len(normalized["documents"]["conditional"]),
                "result_count": len(normalized["results"]["items"]),
            }
        )

    print(json.dumps({"outputs": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
