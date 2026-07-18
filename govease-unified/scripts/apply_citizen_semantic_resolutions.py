from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAPPING_CSV = ROOT / "data" / "catalog" / "citizen_procedure_mapping.csv"
MAPPING_JSON = ROOT / "data" / "catalog" / "citizen_procedure_mapping.json"
REPORT_DIR = ROOT / "data" / "reports"
OUTPUT_CSV = REPORT_DIR / "citizen_semantic_resolutions.csv"
OUTPUT_JSON = REPORT_DIR / "citizen_semantic_resolutions.json"
UPDATED_AT = str(date.today())

RESOLUTIONS = [
    {
        "procedure_code": "2.001023",
        "group_key": "co_con_nho",
        "current_subdomain": "bao_hiem_y_te",
        "risk_type": "subdomain_mismatch_candidate",
        "resolution": "changed_subdomain",
        "target_subdomain": "lien_thong_khai_sinh_bao_hiem_cu_tru",
        "status": "applied",
        "reason": "Thủ tục là gói liên thông khai sinh + BHYT, không phải nhánh BHYT độc lập.",
        "note_suffix": "",
    },
    {
        "procedure_code": "1.012783",
        "group_key": "dien_luc_nha_o_dat_dai",
        "current_subdomain": "dang_ky_quyen_so_huu_quyen_su_dung",
        "risk_type": "subdomain_mismatch_candidate",
        "resolution": "keep_current_subdomain",
        "target_subdomain": "dang_ky_quyen_so_huu_quyen_su_dung",
        "status": "reviewed",
        "reason": "Tên thủ tục là cấp đổi Giấy chứng nhận quyền sử dụng đất, đúng nhánh đăng ký quyền.",
        "note_suffix": "semantic_review:keep_current_subdomain_2026_07_18",
    },
    {
        "procedure_code": "1.012784",
        "group_key": "dien_luc_nha_o_dat_dai",
        "current_subdomain": "dang_ky_quyen_so_huu_quyen_su_dung",
        "risk_type": "subdomain_mismatch_candidate",
        "resolution": "keep_current_subdomain",
        "target_subdomain": "dang_ky_quyen_so_huu_quyen_su_dung",
        "status": "reviewed",
        "reason": "Tách thửa, hợp thửa là thủ tục đất đai cốt lõi, không phải xây dựng nhà ở.",
        "note_suffix": "semantic_review:keep_current_subdomain_2026_07_18",
    },
    {
        "procedure_code": "1.012790",
        "group_key": "dien_luc_nha_o_dat_dai",
        "current_subdomain": "dang_ky_quyen_so_huu_quyen_su_dung",
        "risk_type": "subdomain_mismatch_candidate",
        "resolution": "keep_current_subdomain",
        "target_subdomain": "dang_ky_quyen_so_huu_quyen_su_dung",
        "status": "reviewed",
        "reason": "Đính chính Giấy chứng nhận đã cấp thuộc nhóm đăng ký, cấp đổi, chỉnh lý giấy chứng nhận.",
        "note_suffix": "semantic_review:keep_current_subdomain_2026_07_18",
    },
    {
        "procedure_code": "1.013992",
        "group_key": "dien_luc_nha_o_dat_dai",
        "current_subdomain": "chuyen_muc_dich_su_dung",
        "risk_type": "subdomain_mismatch_candidate",
        "resolution": "keep_current_subdomain",
        "target_subdomain": "chuyen_muc_dich_su_dung",
        "status": "reviewed",
        "reason": "Tên thủ tục nêu rõ chuyển mục đích sử dụng đất, nên giữ ở nhánh hiện tại.",
        "note_suffix": "semantic_review:keep_current_subdomain_2026_07_18",
    },
    {
        "procedure_code": "2.000547",
        "group_key": "co_con_nho",
        "current_subdomain": "khai_sinh",
        "risk_type": "cross_group_overlap",
        "resolution": "intentional_overlap",
        "target_subdomain": "khai_sinh",
        "status": "reviewed",
        "reason": "Thủ tục hộ tịch khác có bao gồm khai sinh nên giữ overlap ở nhóm Có con nhỏ.",
        "note_suffix": "semantic_review:intentional_overlap_2026_07_18",
    },
    {
        "procedure_code": "2.000547",
        "group_key": "hon_nhan_gia_dinh",
        "current_subdomain": "cai_chinh_trich_luc_ho_tich",
        "risk_type": "cross_group_overlap",
        "resolution": "intentional_overlap",
        "target_subdomain": "cai_chinh_trich_luc_ho_tich",
        "status": "reviewed",
        "reason": "Thủ tục hộ tịch khác bao gồm các nhánh quan hệ gia đình và cải chính hộ tịch.",
        "note_suffix": "semantic_review:intentional_overlap_2026_07_18",
    },
    {
        "procedure_code": "2.000547",
        "group_key": "nguoi_than_qua_doi",
        "current_subdomain": "khai_tu",
        "risk_type": "domain_mismatch_candidate",
        "resolution": "keep_current_domain",
        "target_subdomain": "khai_tu",
        "status": "reviewed",
        "reason": "Thủ tục hộ tịch khác có bao gồm khai tử, nên membership ở nhóm Người thân qua đời là hợp lệ.",
        "note_suffix": "semantic_review:keep_current_domain_2026_07_18",
    },
    {
        "procedure_code": "2.000547",
        "group_key": "nguoi_than_qua_doi",
        "current_subdomain": "khai_tu",
        "risk_type": "cross_group_overlap",
        "resolution": "intentional_overlap",
        "target_subdomain": "khai_tu",
        "status": "reviewed",
        "reason": "Thủ tục hộ tịch khác có bao gồm khai tử nên overlap là chủ ý.",
        "note_suffix": "semantic_review:intentional_overlap_2026_07_18",
    },
    {
        "procedure_code": "1.004222",
        "group_key": "co_con_nho",
        "current_subdomain": "cu_tru",
        "risk_type": "cross_group_overlap",
        "resolution": "intentional_overlap",
        "target_subdomain": "cu_tru",
        "status": "reviewed",
        "reason": "Đăng ký thường trú cho trẻ nhỏ là route hợp lệ của hành trình sau sinh.",
        "note_suffix": "semantic_review:intentional_overlap_2026_07_18",
    },
    {
        "procedure_code": "1.004222",
        "group_key": "cu_tru_giay_to",
        "current_subdomain": "ho_khau",
        "risk_type": "cross_group_overlap",
        "resolution": "intentional_overlap",
        "target_subdomain": "ho_khau",
        "status": "reviewed",
        "reason": "Đây vẫn là thủ tục cư trú chuẩn, overlap với Có con nhỏ là do citizen journey.",
        "note_suffix": "semantic_review:intentional_overlap_2026_07_18",
    },
    {
        "procedure_code": "1.000689",
        "group_key": "co_con_nho",
        "current_subdomain": "khai_sinh",
        "risk_type": "cross_group_overlap",
        "resolution": "intentional_overlap",
        "target_subdomain": "khai_sinh",
        "status": "reviewed",
        "reason": "Thủ tục kết hợp khai sinh và nhận cha mẹ con phải xuất hiện ở nhóm Có con nhỏ.",
        "note_suffix": "semantic_review:intentional_overlap_2026_07_18",
    },
    {
        "procedure_code": "1.000689",
        "group_key": "hon_nhan_gia_dinh",
        "current_subdomain": "nhan_cha_me_con",
        "risk_type": "cross_group_overlap",
        "resolution": "intentional_overlap",
        "target_subdomain": "nhan_cha_me_con",
        "status": "reviewed",
        "reason": "Đây cũng là thủ tục quan hệ gia đình cốt lõi nên overlap là chủ ý.",
        "note_suffix": "semantic_review:intentional_overlap_2026_07_18",
    },
    {
        "procedure_code": "1.001695",
        "group_key": "co_con_nho",
        "current_subdomain": "khai_sinh",
        "risk_type": "cross_group_overlap",
        "resolution": "intentional_overlap",
        "target_subdomain": "khai_sinh",
        "status": "reviewed",
        "reason": "Bản có yếu tố nước ngoài vẫn là workflow khai sinh cho trẻ nhỏ.",
        "note_suffix": "semantic_review:intentional_overlap_2026_07_18",
    },
    {
        "procedure_code": "1.001695",
        "group_key": "hon_nhan_gia_dinh",
        "current_subdomain": "nhan_cha_me_con",
        "risk_type": "cross_group_overlap",
        "resolution": "intentional_overlap",
        "target_subdomain": "nhan_cha_me_con",
        "status": "reviewed",
        "reason": "Yếu tố nước ngoài không làm mất bản chất quan hệ gia đình của thủ tục.",
        "note_suffix": "semantic_review:intentional_overlap_2026_07_18",
    },
]


def _append_note(base: str, suffix: str) -> str:
    base = (base or "").strip()
    suffix = (suffix or "").strip()
    if not suffix:
        return base
    if not base:
        return suffix
    if suffix in base:
        return base
    return f"{base}; {suffix}"


def _resolution_index() -> dict[tuple[str, str], dict[str, str]]:
    return {
        (item["group_key"], item["procedure_code"]): item
        for item in RESOLUTIONS
    }


def update_mapping_files() -> None:
    resolution_index = _resolution_index()

    with MAPPING_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())

    for row in rows:
        key = (str(row.get("group_key") or ""), str(row.get("procedure_code") or ""))
        resolution = resolution_index.get(key)
        if not resolution:
            continue
        row["notes"] = _append_note(str(row.get("notes") or ""), resolution["note_suffix"])

    with MAPPING_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    json_rows = json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
    for row in json_rows:
        key = (str(row.get("group_key") or ""), str(row.get("procedure_code") or ""))
        resolution = resolution_index.get(key)
        if not resolution:
            continue
        row["notes"] = _append_note(str(row.get("notes") or ""), resolution["note_suffix"])

    MAPPING_JSON.write_text(json.dumps(json_rows, ensure_ascii=False, indent=2), encoding="utf-8")


def write_resolution_reports() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in RESOLUTIONS:
        rows.append(
            {
                "updated_at": UPDATED_AT,
                **item,
            }
        )

    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "updated_at",
                "procedure_code",
                "group_key",
                "current_subdomain",
                "risk_type",
                "resolution",
                "target_subdomain",
                "status",
                "reason",
                "note_suffix",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "updated_at": UPDATED_AT,
                "resolution_count": len(rows),
                "resolutions": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    write_resolution_reports()
    update_mapping_files()
    print(
        json.dumps(
            {
                "updated_at": UPDATED_AT,
                "resolution_count": len(RESOLUTIONS),
                "outputs": [
                    str(OUTPUT_CSV),
                    str(OUTPUT_JSON),
                    str(MAPPING_CSV),
                    str(MAPPING_JSON),
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
