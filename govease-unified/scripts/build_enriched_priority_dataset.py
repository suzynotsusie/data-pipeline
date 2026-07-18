from __future__ import annotations

import json
from pathlib import Path

from enriched_pipeline import enrich_normalized_structured


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NORMALIZED_DIR = PROJECT_ROOT / "data" / "normalized_structured"
MAPPING_PATH = PROJECT_ROOT / "data" / "catalog" / "citizen_procedure_mapping.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "enriched_structured_priority"
SUMMARY_PATH = PROJECT_ROOT / "data" / "catalog" / "enriched_priority_report.json"
TARGET_GROUPS = {
    "co_con_nho",
    "hon_nhan_gia_dinh",
    "cu_tru_giay_to",
    "suc_khoe_y_te",
    "hoc_tap",
    "dien_luc_nha_o_dat_dai",
    "giai_quyet_khieu_kien",
    "huu_tri",
    "nguoi_than_qua_doi",
    "phuong_tien_nguoi_lai",
    "viec_lam",
}


def main() -> None:
    rows = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    selected_rows = []
    seen_codes: set[str] = set()
    for row in rows:
        code = row.get("procedure_code")
        if row.get("group_key") not in TARGET_GROUPS or not code or code in seen_codes:
            continue
        seen_codes.add(code)
        selected_rows.append(row)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = []
    for row in selected_rows:
        code = row["procedure_code"]
        normalized_path = NORMALIZED_DIR / f"{code.replace('.', '_')}_normalized_structured.json"
        if not normalized_path.exists():
            continue
        normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
        enriched = enrich_normalized_structured(normalized, row)
        output_path = OUTPUT_DIR / f"{code.replace('.', '_')}_enriched_structured.json"
        output_path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(
            {
                "procedure_code": code,
                "group_key": row.get("group_key"),
                "output_path": str(output_path),
                "input_field_count": len(enriched["intake"]["candidate_input_fields"]),
                "special_case_count": len(enriched["guidance"]["special_cases"]),
            }
        )

    payload = {
        "target_groups": sorted(TARGET_GROUPS),
        "output_dir": str(OUTPUT_DIR),
        "count": len(outputs),
        "outputs": outputs,
    }
    SUMMARY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"count": len(outputs), "summary_path": str(SUMMARY_PATH)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
