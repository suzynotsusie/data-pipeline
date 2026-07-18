from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = ROOT.parent / "data" / "workflows"
MAPPING_PATH = ROOT / "data" / "catalog" / "citizen_procedure_mapping.csv"
GROUPS_PATH = ROOT / "data" / "catalog" / "citizen_group_domains.json"
OUTPUT_JSON = ROOT / "data" / "reports" / "citizen_semantic_audit.json"
OUTPUT_CSV = ROOT / "data" / "reports" / "citizen_semantic_audit.csv"
RESOLUTION_JSON = ROOT / "data" / "reports" / "citizen_semantic_resolutions.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.procedures import procedure_detail
from govease_ai.procedure_data import load_procedure_store

STOPWORDS = {
    "va",
    "voi",
    "cua",
    "cho",
    "theo",
    "tren",
    "tai",
    "trong",
    "mot",
    "nhung",
    "nguoi",
    "thu",
    "tuc",
    "thu_tuc",
    "cap",
    "dang",
    "ky",
    "thuc",
    "hien",
    "ve",
    "den",
    "doi",
    "tu",
    "nay",
    "neu",
    "duoc",
    "khi",
    "hoac",
    "co",
    "khong",
    "da",
    "la",
    "so",
    "giay",
    "ban",
    "mau",
    "truong",
    "hop",
    "noi",
    "nop",
    "ho",
    "so",
    "ket",
    "qua",
}

MANUAL_GROUP_KEYWORDS = {
    "co_con_nho": {"khai_sinh", "tre_em", "duoi_6_tuoi", "giay_khai_sinh", "trich_luc_ho_tich"},
    "hoc_tap": {"hoc_tap", "tuyen_sinh", "hoc_bong", "van_bang", "chung_chi", "chuyen_truong", "tot_nghiep", "hoc_sinh", "sinh_vien"},
    "viec_lam": {"viec_lam", "lao_dong", "that_nghiep", "thu_nhap_ca_nhan", "giay_phep_lao_dong", "tuyen_dung", "bao_hiem_xa_hoi"},
    "cu_tru_giay_to": {"cu_tru", "thuong_tru", "tam_tru", "tam_vang", "can_cuoc", "ho_chieu", "ly_lich_tu_phap"},
    "hon_nhan_gia_dinh": {"ket_hon", "ly_hon", "giam_ho", "nhan_cha_me_con", "nuoi_con_nuoi", "cai_chinh_ho_tich"},
    "dien_luc_nha_o_dat_dai": {"dat_dai", "nha_o", "dien_luc", "xay_dung", "giay_chung_nhan", "the_chap", "quyen_su_dung_dat"},
    "suc_khoe_y_te": {"y_te", "kham_chua_benh", "vien_phi", "bao_hiem_y_te", "kham_benh"},
    "phuong_tien_nguoi_lai": {"phuong_tien", "dang_kiem", "dang_ky_xe", "giay_phep_lai_xe", "sat_hach"},
    "huu_tri": {"huu_tri", "luong_huu", "nghi_huu", "bao_hiem_xa_hoi_mot_lan"},
    "nguoi_than_qua_doi": {"khai_tu", "mai_tang", "tu_tuat", "mai_tang_phi"},
    "giai_quyet_khieu_kien": {"khieu_nai", "kien_nghi", "tranh_chap"},
}

MANUAL_SUBDOMAIN_KEYWORDS = {
    "lien_thong_khai_sinh_bao_hiem_cu_tru": {"lien_thong", "khai_sinh", "bao_hiem_y_te", "thuong_tru"},
    "khai_sinh": {"khai_sinh", "giay_khai_sinh", "trich_luc_ho_tich"},
    "bao_hiem_y_te": {"bao_hiem_y_te", "the_bhyt"},
    "cu_tru": {"cu_tru", "thuong_tru", "tam_tru"},
    "tuyen_sinh": {"tuyen_sinh", "xet_tuyen", "du_tuyen", "tot_nghiep"},
    "chuyen_truong": {"chuyen_truong", "chuyen_nganh", "chuyen_noi_hoc"},
    "hoc_bong_va_ho_tro": {"hoc_bong", "ho_tro_hoc_tap", "mien_giam", "tro_cap_hoc_tap"},
    "van_bang_chung_chi": {"van_bang", "chung_chi", "cong_nhan_van_bang"},
    "hoc_tap_o_nuoc_ngoai_bang_ngan_sach": {"nuoc_ngoai", "ngan_sach", "du_hoc"},
    "ho_tro_tu_van_gioi_thieu_viec_lam": {"tu_van_viec_lam", "gioi_thieu_viec_lam", "tim_viec", "ve_xe"},
    "tuyen_dung": {"tuyen_dung", "du_tuyen", "ung_tuyen"},
    "bao_hiem_xa_hoi_that_nghiep_tro_cap": {"bao_hiem_xa_hoi", "that_nghiep", "tro_cap", "om_dau", "thai_san"},
    "chung_chi_hanh_nghe": {"chung_chi_hanh_nghe", "chung_chi_ky_nang", "tham_tra_vien"},
    "nang_ngach": {"nang_ngach", "thang_hang", "xep_hang"},
    "thue_thu_nhap_ca_nhan": {"thue", "thu_nhap_ca_nhan", "khai_thue"},
    "cap_phep_lao_dong_nguoi_nuoc_ngoai": {"giay_phep_lao_dong", "nguoi_nuoc_ngoai", "mien_gpld"},
    "ho_khau": {"ho_khau", "thuong_tru"},
    "tam_tru": {"tam_tru"},
    "luu_tru": {"luu_tru"},
    "can_cuoc_chung_minh_nhan_dan": {"can_cuoc", "cccd", "cmnd"},
    "ho_chieu": {"ho_chieu", "xuat_nhap_canh"},
    "tam_vang": {"tam_vang"},
    "ket_hon": {"ket_hon", "ly_hon", "huy_ket_hon"},
    "giam_ho": {"giam_ho", "cham_dut_giam_ho"},
    "nhan_cha_me_con": {"nhan_cha", "nhan_me", "xac_dinh_cha_me_con"},
    "nhan_con_nuoi": {"nuoi_con_nuoi", "nhan_con_nuoi"},
    "cai_chinh_trich_luc_ho_tich": {"trich_luc_ho_tich", "cai_chinh_ho_tich", "thay_doi_ho_tich"},
    "dang_ky_quyen_so_huu_quyen_su_dung": {"giay_chung_nhan", "quyen_su_dung_dat", "quyen_so_huu"},
    "chuyen_nhuong_tang_cho_thua_ke": {"chuyen_nhuong", "tang_cho", "thua_ke"},
    "gop_von_the_chap": {"the_chap", "gop_von", "bao_dam"},
    "chuyen_muc_dich_su_dung": {"chuyen_muc_dich_su_dung"},
    "xay_dung_cong_trinh_nha_o": {"xay_dung", "nha_o", "cong_trinh"},
    "cung_cap_dien_nang": {"dien_nang", "cap_dien"},
    "kham_chua_benh": {"kham_chua_benh", "kham_benh", "chua_benh"},
    "chinh_sach_y_te": {"y_te", "chinh_sach_y_te", "vien_phi"},
    "giay_phep_lai_xe": {"giay_phep_lai_xe", "sat_hach", "bang_lai"},
    "dang_ky_phuong_tien": {"dang_ky_xe", "bien_so", "phuong_tien"},
    "dang_kiem_phuong_tien": {"dang_kiem", "kiem_dinh", "an_toan_ky_thuat"},
    "chuan_bi_nghi_huu": {"nghi_huu", "chuan_bi_nghi_huu"},
    "che_do_huu_tri": {"huu_tri", "luong_huu", "tro_cap_huu_tri"},
    "khai_tu": {"khai_tu"},
    "che_do_tu_tuat_mai_tang_phi": {"tu_tuat", "mai_tang_phi", "mai_tang"},
    "giai_quyet_khieu_kien": {"khieu_nai", "kien_nghi", "tranh_chap"},
}


@dataclass
class WorkflowProcedure:
    group_key: str
    subdomain_key: str
    subdomain_label: str
    procedure_code: str
    procedure_title: str
    field: str
    agency: str
    source_url: str
    operation_group: str
    operation_key: str
    raw_data_available: bool
    document_group_count: int
    result_count: int


def main() -> None:
    store = load_procedure_store()
    group_catalog = _load_group_catalog()
    subdomain_map = _load_workflow_summary_rows()
    mapping_rows = _load_workflow_mapping_rows()
    keyword_index = _build_keyword_index(group_catalog)
    overlap_index = _build_cross_group_index(mapping_rows)
    resolution_index = _load_resolution_index()

    findings: list[dict[str, str]] = []
    domain_counts: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()

    for row in mapping_rows:
        code = str(row["procedure_code"])
        current_domain = str(row["group_key"])
        workflow = subdomain_map.get((current_domain, code))
        current_subdomain = workflow.subdomain_key if workflow else _subdomain_from_notes(str(row.get("notes") or ""))
        record = store.find(code)
        if record is None:
            findings.append(
                _finding(
                    procedure_code=code,
                    current_domain=current_domain,
                    current_subdomain=current_subdomain or "unknown",
                    risk_type="missing_runtime_record",
                    why_flagged="Không tìm thấy runtime payload tương ứng để audit ngữ nghĩa.",
                    suggested_fix="Kiểm tra lại procedure payload hoặc mapping code này.",
                )
            )
            continue

        detail = procedure_detail(record)
        source_text = _join_text(
            record.title,
            record.data.get("field"),
            record.data.get("scope"),
            record.data.get("target_users"),
            record.data.get("notes"),
            record.data.get("processing_note"),
            (record.data.get("source") or {}).get("source_url") if isinstance(record.data.get("source"), dict) else None,
            workflow.field if workflow else None,
            workflow.operation_group if workflow else None,
            workflow.operation_key if workflow else None,
            workflow.procedure_title if workflow else None,
        )
        summary_text = _join_text(
            detail.get("checklist", {}).get("overview_summary"),
            detail.get("checklist", {}).get("next_step_summary"),
        )

        group_scores = _score_candidates(source_text, keyword_index["groups"])
        current_group_score = group_scores.get(current_domain, 0)
        best_group_key, best_group_score = _best_candidate(group_scores)
        if best_group_key and best_group_key != current_domain and current_group_score == 0 and best_group_score >= 2:
            findings.append(
                _finding(
                    procedure_code=code,
                    current_domain=current_domain,
                    current_subdomain=current_subdomain or "unknown",
                    risk_type="domain_mismatch_candidate",
                    why_flagged=f"Tín hiệu từ title/field/scope nghiêng mạnh sang domain `{best_group_key}` (score {best_group_score}) hơn domain hiện tại `{current_domain}` (score {current_group_score}).",
                    suggested_fix=f"Review lại mapping domain; ứng viên gần nhất là `{best_group_key}`.",
                )
            )

        if current_subdomain:
            subdomain_scores = _score_candidates(source_text, keyword_index["subdomains"].get(current_domain, {}))
            current_subdomain_score = subdomain_scores.get(current_subdomain, 0)
            best_subdomain_key, best_subdomain_score = _best_candidate(subdomain_scores)
            if best_subdomain_key and best_subdomain_key != current_subdomain and current_subdomain_score == 0 and best_subdomain_score >= 2:
                findings.append(
                    _finding(
                        procedure_code=code,
                        current_domain=current_domain,
                        current_subdomain=current_subdomain,
                        risk_type="subdomain_mismatch_candidate",
                        why_flagged=f"Tín hiệu từ title/field/raw overview nghiêng sang subdomain `{best_subdomain_key}` (score {best_subdomain_score}) hơn subdomain hiện tại `{current_subdomain}` (score {current_subdomain_score}).",
                        suggested_fix=f"Review lại subdomain; ứng viên gần nhất là `{best_subdomain_key}`.",
                    )
                )

        if summary_text:
            summary_group_scores = _score_candidates(summary_text, keyword_index["groups"])
            title_group_scores = _score_candidates(record.title, keyword_index["groups"])
            best_summary_group, summary_group_score = _best_candidate(summary_group_scores)
            best_title_group, title_group_score = _best_candidate(title_group_scores)
            if (
                best_summary_group
                and best_title_group
                and best_summary_group != best_title_group
                and summary_group_score >= 2
                and title_group_score >= 1
                and group_scores.get(current_domain, 0) >= 1
            ):
                findings.append(
                    _finding(
                        procedure_code=code,
                        current_domain=current_domain,
                        current_subdomain=current_subdomain or "unknown",
                        risk_type="summary_mismatch_candidate",
                        why_flagged=f"Summary đang mang tín hiệu domain `{best_summary_group}` trong khi title nghiêng sang `{best_title_group}`.",
                        suggested_fix="Review lại overview_summary / next_step_summary để bám sát bản chất thủ tục.",
                    )
                )

        checklist = detail.get("checklist") or {}
        primary_docs = checklist.get("documents") or []
        conditional_docs = checklist.get("conditional_documents") or []
        form_docs = checklist.get("forms") or []
        user_steps = checklist.get("user_steps") or []
        if not primary_docs and not form_docs:
            findings.append(
                _finding(
                    procedure_code=code,
                    current_domain=current_domain,
                    current_subdomain=current_subdomain or "unknown",
                    risk_type="thin_checklist",
                    why_flagged="Checklist không có giấy tờ chính và cũng không có form rõ ràng để người dùng bám theo.",
                    suggested_fix="Bổ sung primary checklist từ raw_data hoặc enrich lại documents.summary/normally_required.",
                )
            )
        elif len(primary_docs) <= 1 and len(form_docs) == 0:
            findings.append(
                _finding(
                    procedure_code=code,
                    current_domain=current_domain,
                    current_subdomain=current_subdomain or "unknown",
                    risk_type="thin_checklist",
                    why_flagged=f"Checklist chỉ có {len(primary_docs)} giấy tờ chính, dễ là chưa bóc đủ thành phần hồ sơ.",
                    suggested_fix="Đối chiếu lại raw_data để tách thêm giấy tờ chính hoặc biểu mẫu.",
                )
            )

        if conditional_docs and not primary_docs and all(_is_edge_case_document(item) for item in conditional_docs):
            findings.append(
                _finding(
                    procedure_code=code,
                    current_domain=current_domain,
                    current_subdomain=current_subdomain or "unknown",
                    risk_type="edge_case_only_checklist",
                    why_flagged="Checklist hiện chỉ còn giấy tờ theo trường hợp đặc biệt như ủy quyền/bưu chính, chưa có bộ giấy tờ lõi.",
                    suggested_fix="Bổ sung bộ giấy tờ cốt lõi hoặc đánh dấu thủ tục này là chưa đủ workflow-ready.",
                )
            )

        if len(user_steps) <= 2:
            findings.append(
                _finding(
                    procedure_code=code,
                    current_domain=current_domain,
                    current_subdomain=current_subdomain or "unknown",
                    risk_type="shallow_user_steps",
                    why_flagged=f"Phần user_steps chỉ có {len(user_steps)} bước, có khả năng đang quá chung hoặc chưa bóc đủ luồng thủ tục.",
                    suggested_fix="Review lại steps/raw procedure flow để sinh lại user_steps.",
                )
            )

        groups_for_code = sorted(overlap_index.get(code, []))
        if len(groups_for_code) > 1:
            findings.append(
                _finding(
                    procedure_code=code,
                    current_domain=current_domain,
                    current_subdomain=current_subdomain or "unknown",
                    risk_type="cross_group_overlap",
                    why_flagged=f"Mã này đang xuất hiện ở nhiều group Công dân: {', '.join(groups_for_code)}.",
                    suggested_fix="Xác nhận đây là overlap chủ ý hay đang kéo nhầm membership mở rộng.",
                )
            )

    findings = [finding for finding in findings if not _is_resolved_finding(finding, resolution_index)]

    for finding in findings:
        domain_counts[finding["current_domain"]] += 1
        risk_counts[finding["risk_type"]] += 1

    payload = {
        "generated_at": "2026-07-18",
        "scope": "citizen_workflow_semantic_risks",
        "workflow_procedure_count": len(mapping_rows),
        "finding_count": len(findings),
        "risk_type_counts": dict(sorted(risk_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
        "findings": findings,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "procedure_code",
                "current_domain",
                "current_subdomain",
                "risk_type",
                "why_flagged",
                "suggested_fix",
            ],
        )
        writer.writeheader()
        writer.writerows(findings)
    print(OUTPUT_JSON)
    print(OUTPUT_CSV)


def _load_workflow_mapping_rows() -> list[dict[str, str]]:
    with MAPPING_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [
        row
        for row in rows
        if row.get("persona") == "citizen" and _as_bool(row.get("in_workflow_dataset"))
    ]


def _load_resolution_index() -> dict[tuple[str, str, str], dict[str, Any]]:
    if not RESOLUTION_JSON.exists():
        return {}
    payload = json.loads(RESOLUTION_JSON.read_text(encoding="utf-8"))
    resolutions = payload.get("resolutions", [])
    index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in resolutions:
        if not isinstance(item, dict):
            continue
        key = (
            str(item.get("group_key") or ""),
            str(item.get("procedure_code") or ""),
            str(item.get("risk_type") or ""),
        )
        if all(key):
            index[key] = item
    return index


def _is_resolved_finding(
    finding: dict[str, str],
    resolution_index: dict[tuple[str, str, str], dict[str, Any]],
) -> bool:
    key = (
        str(finding.get("current_domain") or ""),
        str(finding.get("procedure_code") or ""),
        str(finding.get("risk_type") or ""),
    )
    return key in resolution_index


def _load_group_catalog() -> dict[str, dict[str, Any]]:
    payload = json.loads(GROUPS_PATH.read_text(encoding="utf-8"))
    groups = payload.get("groups", []) if isinstance(payload, dict) else []
    return {
        str(item["group_key"]): item
        for item in groups
        if isinstance(item, dict) and item.get("group_key")
    }


def _load_workflow_summary_rows() -> dict[tuple[str, str], WorkflowProcedure]:
    rows: dict[tuple[str, str], WorkflowProcedure] = {}
    for summary_path in WORKFLOW_ROOT.glob("*/summary.csv"):
        group_key = summary_path.parent.name
        with summary_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                code = str(row.get("procedure_code") or "").strip()
                if not code:
                    continue
                rows[(group_key, code)] = WorkflowProcedure(
                    group_key=group_key,
                    subdomain_key=str(row.get("subdomain_key") or "").strip(),
                    subdomain_label=str(row.get("subdomain_label") or "").strip(),
                    procedure_code=code,
                    procedure_title=str(row.get("procedure_title") or "").strip(),
                    field=str(row.get("field") or "").strip(),
                    agency=str(row.get("agency") or "").strip(),
                    source_url=str(row.get("source_url") or "").strip(),
                    operation_group=str(row.get("operation_group") or "").strip(),
                    operation_key=str(row.get("operation_key") or "").strip(),
                    raw_data_available=_as_bool(row.get("raw_data_available")),
                    document_group_count=_to_int(row.get("document_group_count")),
                    result_count=_to_int(row.get("result_count")),
                )
    return rows


def _build_keyword_index(group_catalog: dict[str, dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, set[str]] = {}
    subdomains: dict[str, dict[str, set[str]]] = {}
    for group_key, group in group_catalog.items():
        group_keywords = set(MANUAL_GROUP_KEYWORDS.get(group_key, set()))
        subdomain_keywords: dict[str, set[str]] = {}
        for item in group.get("subdomains", []):
            if not isinstance(item, dict):
                continue
            subdomain_key = str(item.get("subdomain_key") or "").strip()
            if not subdomain_key:
                continue
            keywords = set(MANUAL_SUBDOMAIN_KEYWORDS.get(subdomain_key, set()))
            subdomain_keywords[subdomain_key] = keywords
            group_keywords |= keywords
        groups[group_key] = group_keywords
        subdomains[group_key] = subdomain_keywords
    return {"groups": groups, "subdomains": subdomains}


def _build_cross_group_index(rows: list[dict[str, str]]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        index[str(row["procedure_code"])].add(str(row["group_key"]))
    return index


def _score_candidates(text: str, candidate_keywords: dict[str, set[str]]) -> dict[str, int]:
    tokens = _keywords_from_text(text)
    scores: dict[str, int] = {}
    for key, keywords in candidate_keywords.items():
        if not keywords:
            scores[key] = 0
            continue
        overlap = tokens & keywords
        score = len(overlap)
        if any(token in overlap for token in {"khai_sinh", "ket_hon", "khai_tu", "huu_tri", "dang_kiem", "giay_phep_lai_xe", "thue_thu_nhap_ca_nhan"}):
            score += 2
        scores[key] = score
    return scores


def _best_candidate(scores: dict[str, int]) -> tuple[str | None, int]:
    if not scores:
        return None, 0
    key = max(scores, key=lambda item: scores[item])
    return key, scores[key]


def _keywords_from_text(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        text = " ".join(str(item) for item in value if item)
    else:
        text = str(value)
    normalized = _normalize_text(text)
    parts = [part for part in re.split(r"[^a-z0-9]+", normalized) if part and part not in STOPWORDS]
    keywords = set(parts)
    keywords |= _compound_keywords(parts)
    return keywords


def _compound_keywords(parts: list[str]) -> set[str]:
    combos: set[str] = set()
    for size in (2, 3):
        for index in range(len(parts) - size + 1):
            window = parts[index : index + size]
            if any(token in STOPWORDS for token in window):
                continue
            combos.add("_".join(window))
    return combos


def _normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.replace("đ", "d").replace("Đ", "D")
    return value.lower()


def _join_text(*values: Any) -> str:
    chunks: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, list):
            chunks.extend(str(item) for item in value if item)
        else:
            chunks.append(str(value))
    return "\n".join(chunk for chunk in chunks if chunk)


def _subdomain_from_notes(value: str) -> str:
    match = re.search(r"workflow_generated:[^/]+/([a-z0-9_]+)", value)
    return match.group(1) if match else ""


def _finding(
    *,
    procedure_code: str,
    current_domain: str,
    current_subdomain: str,
    risk_type: str,
    why_flagged: str,
    suggested_fix: str,
) -> dict[str, str]:
    return {
        "procedure_code": procedure_code,
        "current_domain": current_domain,
        "current_subdomain": current_subdomain,
        "risk_type": risk_type,
        "why_flagged": why_flagged,
        "suggested_fix": suggested_fix,
    }


def _is_edge_case_document(item: dict[str, Any]) -> bool:
    haystack = _normalize_text(_join_text(item.get("name"), item.get("condition"), item.get("notes")))
    return "uy quyen" in haystack or "buu chinh" in haystack


def _to_int(value: Any) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


if __name__ == "__main__":
    main()
