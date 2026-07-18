from __future__ import annotations

import json
from pathlib import Path

from normalized_pipeline import normalize_raw_structured
from raw_markdown_pipeline import parse_procedure_markdown


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = PROJECT_ROOT.parent
RAW_DATA_ROOT = PIPELINE_ROOT / "raw_data"
REPORT_PATH = PROJECT_ROOT / "data" / "catalog" / "procedure_coverage_report.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "normalized_structured"
SUMMARY_PATH = PROJECT_ROOT / "data" / "catalog" / "normalized_structured_report.json"


def main() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    ready_rows = [row for row in report["rows"] if row["status"] == "ready"]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary: list[dict[str, object]] = []
    for row in ready_rows:
        code = row["procedure_code"]
        markdown_path = RAW_DATA_ROOT / code.replace(".", "_") / f"{code.replace('.', '_')}_procedure_detail.md"
        raw_payload = parse_procedure_markdown(markdown_path)
        normalized = normalize_raw_structured(raw_payload)
        output_path = OUTPUT_DIR / f"{code.replace('.', '_')}_normalized_structured.json"
        output_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        summary.append(
            {
                "procedure_code": code,
                "output_path": str(output_path),
                "channels": normalized["submission"]["channels"],
                "document_count": normalized["documents"]["document_count"],
                "notes_count": len(normalized["documents"]["notes"]),
                "process_step_count": normalized["process"]["step_count"],
            }
        )

    payload = {
        "source_report": str(REPORT_PATH),
        "ready_count": len(ready_rows),
        "output_dir": str(OUTPUT_DIR),
        "outputs": summary,
    }
    SUMMARY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ready_count": len(ready_rows), "output_dir": str(OUTPUT_DIR), "summary_path": str(SUMMARY_PATH)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
