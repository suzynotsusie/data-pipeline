from __future__ import annotations


def build_quality(
    *,
    section_keys: set[str],
    parse_warnings: list[str],
    methods_count: int,
    document_group_count: int,
) -> dict[str, object]:
    required = {
        "thong_tin_chung",
        "trinh_tu_thuc_hien",
        "cach_thuc_thuc_hien",
        "thanh_phan_ho_so",
        "can_cu_phap_ly",
        "ket_qua_xu_ly",
    }
    section_presence = {key: key in section_keys for key in required}
    review = bool(parse_warnings) or methods_count == 0 or document_group_count == 0
    return {
        "section_presence": section_presence,
        "parse_warnings": parse_warnings,
        "needs_manual_review": review,
    }
