from __future__ import annotations

import json
from pathlib import Path

from raw_markdown_pipeline import parse_procedure_markdown


UNIFIED_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = UNIFIED_ROOT.parent
RAW_DATA_ROOT = PIPELINE_ROOT / "raw_data"
OUTPUT_ROOT = UNIFIED_ROOT / "data" / "raw_structured_samples"
SAMPLE_CODES = ["1.001193", "1.004194", "1.001456", "1.005142", "1.014748"]


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, object]] = []

    for code in SAMPLE_CODES:
        markdown_path = RAW_DATA_ROOT / code.replace(".", "_") / f"{code.replace('.', '_')}_procedure_detail.md"
        payload = parse_procedure_markdown(markdown_path)
        output_path = OUTPUT_ROOT / f"{code.replace('.', '_')}_raw_structured.json"
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        summary.append(
            {
                "procedure_code": code,
                "output_path": str(output_path),
                "warnings": payload["quality"]["parse_warnings"],
                "manual_review": payload["quality"]["needs_manual_review"],
                "method_count": len(payload["submission_methods"]),
                "document_group_count": len(payload["documents"]["groups"]),
                "result_count": len(payload["results"]),
                "legal_basis_count": len(payload["legal_basis"]),
            }
        )

    print(json.dumps({"outputs": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
