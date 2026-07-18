from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any

import requests


BASE_DIR = Path(__file__).resolve().parents[1]
PIPELINE_DIR = BASE_DIR.parent
CATALOG_DIR = BASE_DIR / "data" / "catalog"
FULL_DATA_PATH = PIPELINE_DIR / "main" / "full-data.csv"
RAW_DATA_DIR = PIPELINE_DIR / "raw_data"
WORKFLOW_DATA_DIR = PIPELINE_DIR / "data"

REST_URL = "https://vpcp.dichvucong.gov.vn/jsp/rest.jsp"
GROUP_PAGE_TEMPLATE = "https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-nhom-su-kien-cho-cong-dan.html?group={group_id}"

GROUPS: "OrderedDict[int, dict[str, Any]]" = OrderedDict(
    [
        (
            750,
            {
                "key": "co_con_nho",
                "label": "Có con nhỏ",
                "description": "Các thủ tục liên quan đến khai sinh, liên thông cho trẻ em dưới 6 tuổi và việc hộ tịch gắn với trẻ em.",
                "preferred_workflow_family": "birth_registration",
            },
        ),
        (
            751,
            {
                "key": "hoc_tap",
                "label": "Học tập",
                "description": "Nhóm thủ tục dành cho nhu cầu học tập, tuyển sinh và xác nhận phục vụ đi học.",
                "preferred_workflow_family": None,
            },
        ),
        (
            752,
            {
                "key": "viec_lam",
                "label": "Việc làm",
                "description": "Nhóm thủ tục liên quan đến lao động, hỗ trợ tìm việc và chế độ khi tham gia thị trường lao động.",
                "preferred_workflow_family": None,
            },
        ),
        (
            753,
            {
                "key": "cu_tru_giay_to",
                "label": "Cư trú và giấy tờ tùy thân",
                "description": "Các thủ tục cư trú, hộ chiếu, căn cước, thông hành và giấy tờ tùy thân.",
                "preferred_workflow_family": "residence_management",
            },
        ),
        (
            754,
            {
                "key": "hon_nhan_gia_dinh",
                "label": "Hôn nhân và gia đình",
                "description": "Kết hôn, ly hôn, nhận cha mẹ con, giám hộ, con nuôi và các việc hộ tịch trong gia đình.",
                "preferred_workflow_family": None,
            },
        ),
        (
            755,
            {
                "key": "dien_luc_nha_o_dat_dai",
                "label": "Điện lực, nhà ở, đất đai",
                "description": "Nhóm thủ tục dân sinh về nhà ở, đất đai và hạ tầng liên quan.",
                "preferred_workflow_family": None,
            },
        ),
        (
            756,
            {
                "key": "suc_khoe_y_te",
                "label": "Sức khỏe và y tế",
                "description": "Nhóm thủ tục khám chữa bệnh, bảo hiểm y tế và dịch vụ sức khỏe.",
                "preferred_workflow_family": None,
            },
        ),
        (
            757,
            {
                "key": "phuong_tien_nguoi_lai",
                "label": "Phương tiện và người lái",
                "description": "Nhóm thủ tục về phương tiện, bằng lái và quyền đi lại của công dân.",
                "preferred_workflow_family": None,
            },
        ),
        (
            758,
            {
                "key": "huu_tri",
                "label": "Hưu trí",
                "description": "Nhóm thủ tục liên quan đến nghỉ hưu và chế độ sau lao động.",
                "preferred_workflow_family": None,
            },
        ),
        (
            759,
            {
                "key": "nguoi_than_qua_doi",
                "label": "Người thân qua đời",
                "description": "Các thủ tục khai tử và thủ tục phát sinh khi có người thân qua đời.",
                "preferred_workflow_family": None,
            },
        ),
        (
            771,
            {
                "key": "giai_quyet_khieu_kien",
                "label": "Giải quyết khiếu kiện",
                "description": "Nhóm thủ tục liên quan đến khiếu kiện và tương tác tố tụng hành chính, dân sự.",
                "preferred_workflow_family": None,
            },
        ),
    ]
)

WORKFLOW_SUMMARY_FILES = {
    "birth_registration": WORKFLOW_DATA_DIR / "birth_procedure" / "birth_procedures_summary.csv",
    "residence_management": WORKFLOW_DATA_DIR / "residence_procedures" / "residence_procedures_summary.csv",
}

GROUP_EXPANSION_RULES: dict[str, dict[str, list[str]]] = {
    "co_con_nho": {
        "title_includes": [
            "khai sinh",
            "tre em duoi 6 tuoi",
        ],
    },
    "hoc_tap": {
        "field_names": [
            "Giáo dục và Đào tạo thuộc hệ thống giáo dục quốc dân",
            "Giáo dục nghề nghiệp",
        ],
        "title_includes": [
            "hoc bong",
            "hoc phi",
            "hoc tap",
            "hoc sinh",
            "sinh vien",
            "tuyen sinh",
            "van bang",
            "chung chi",
        ],
    },
    "viec_lam": {
        "field_names": [
            "Việc làm",
            "An toàn lao động",
        ],
        "title_includes": [
            "viec lam",
            "that nghiep",
            "hop dong lao dong",
            "nguoi lao dong",
            "giay phep lao dong",
        ],
        "title_excludes": [
            "luong huu",
            "nghi huu",
            "tu tuat",
            "mai tang",
        ],
    },
    "cu_tru_giay_to": {
        "field_names": [
            "Đăng ký, quản lý cư trú",
            "Đăng ký quản lý cư trú",
            "Căn cước",
            "Xuất cảnh, nhập cảnh",
            "Chứng minh nhân dân",
        ],
        "title_includes": [
            "thuong tru",
            "tam tru",
            "tam vang",
            "luu tru",
            "cu tru",
            "can cuoc",
            "ho chieu",
            "giay thong hanh",
        ],
    },
    "hon_nhan_gia_dinh": {
        "title_includes": [
            "ket hon",
            "ly hon",
            "nhan cha, me, con",
            "xac dinh cha, me, con",
            "giam ho",
            "nuoi con nuoi",
        ],
    },
    "dien_luc_nha_o_dat_dai": {
        "field_names": [
            "Đất đai",
            "Nhà ở",
            "Hoạt động xây dựng",
            "Điện lực",
        ],
        "title_includes": [
            "dat dai",
            "nha o",
            "cap dien",
            "dien luc",
            "xay dung",
        ],
    },
    "suc_khoe_y_te": {
        "field_names": [
            "Bảo hiểm y tế",
            "Khám bệnh, chữa bệnh",
            "Phòng bệnh",
            "Dược phẩm",
            "Thiết bị y tế",
            "An toàn thực phẩm",
        ],
        "title_includes": [
            "bao hiem y te",
            "kham benh",
            "chua benh",
            "y te",
            "thuoc",
            "suc khoe",
        ],
    },
    "phuong_tien_nguoi_lai": {
        "field_names": [
            "Sát hạch, cấp giấy phép lái xe",
            "Đăng ký, quản lý phương tiện giao thông cơ giới, xe máy chuyên dùng",
            "Đăng kiểm",
        ],
        "title_includes": [
            "giay phep lai xe",
            "dang ky xe",
            "bien so xe",
            "dang kiem",
            "phuong tien giao thong",
        ],
    },
    "huu_tri": {
        "field_names": [
            "Bảo hiểm xã hội",
        ],
        "title_includes": [
            "huu tri",
            "luong huu",
            "nghi huu",
        ],
        "title_excludes": [
            "tu tuat",
            "mai tang",
        ],
    },
    "nguoi_than_qua_doi": {
        "title_includes": [
            "khai tu",
            "mai tang",
            "tu tuat",
            "qua doi",
        ],
    },
    "giai_quyet_khieu_kien": {
        "field_names": [
            "Tòa án",
            "Khiếu nại tố cáo",
        ],
        "title_includes": [
            "khieu nai",
            "to cao",
            "to tung",
            "toa an",
            "tranh chap",
        ],
    },
}


@dataclass
class ProcedureEntry:
    group_id: int
    group_key: str
    group_label: str
    procedure_code: str
    procedure_title: str
    source_url: str
    field: str
    raw_data_available: bool
    in_full_data: bool
    workflow_data_available: bool
    workflow_family: str | None
    support_level: str
    official_membership: bool
    expanded_membership: bool
    membership_source: str
    notes: str = ""


def main() -> None:
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    full_data = load_full_data()
    workflow_codes = load_workflow_codes()
    session = requests.Session()

    group_payload: dict[str, Any] = {"persona": "citizen", "groups": []}
    entries: list[ProcedureEntry] = []
    report_rows: list[dict[str, Any]] = []
    missing_raw_codes: list[str] = []

    for group_id, meta in GROUPS.items():
        official_procedures = fetch_group_procedures(session, group_id)
        merged_procedures = merge_group_procedures(
            group_key=meta["key"],
            official_procedures=official_procedures,
            full_data=full_data,
            workflow_codes=workflow_codes,
        )

        official_count = sum(1 for item in merged_procedures if item["official_membership"])
        expanded_count = sum(1 for item in merged_procedures if item["expanded_membership"])
        raw_count = 0
        workflow_ready = 0
        workflow_data_count = 0
        missing_raw_for_group = 0

        group_payload["groups"].append(
            {
                "key": meta["key"],
                "label": meta["label"],
                "official_group_id": group_id,
                "official_url": GROUP_PAGE_TEMPLATE.format(group_id=group_id),
                "description": meta["description"],
                "preferred_workflow_family": meta["preferred_workflow_family"],
                "official_procedure_count": official_count,
                "expanded_procedure_count": expanded_count,
                "procedure_count": len(merged_procedures),
            }
        )

        for procedure in merged_procedures:
            code = procedure["procedure_code"]
            row = full_data.get(code)
            field = str(row.get("Lĩnh vực") or "").strip() if row else ""
            source_url = procedure["detail_url"] or (str(row.get("URL") or "").strip() if row else "")
            raw_available = has_raw_data(code)
            in_full_data = row is not None
            workflow_family = workflow_codes.get(code)
            workflow_data_available = workflow_family is not None
            support_level = infer_support_level(raw_available, workflow_family)

            notes: list[str] = []
            if not in_full_data:
                notes.append("Không tìm thấy mã này trong full-data.csv")
            elif not raw_available:
                notes.append("Có trong full-data.csv nhưng chưa có raw_data")
            if procedure["source_note"]:
                notes.append(procedure["source_note"])

            entries.append(
                ProcedureEntry(
                    group_id=group_id,
                    group_key=meta["key"],
                    group_label=meta["label"],
                    procedure_code=code,
                    procedure_title=procedure["procedure_title"],
                    source_url=source_url,
                    field=field,
                    raw_data_available=raw_available,
                    in_full_data=in_full_data,
                    workflow_data_available=workflow_data_available,
                    workflow_family=workflow_family,
                    support_level=support_level,
                    official_membership=procedure["official_membership"],
                    expanded_membership=procedure["expanded_membership"],
                    membership_source=procedure["membership_source"],
                    notes=" | ".join(notes),
                )
            )

            if raw_available:
                raw_count += 1
            elif in_full_data:
                missing_raw_codes.append(code)
                missing_raw_for_group += 1

            if workflow_data_available:
                workflow_data_count += 1
            if support_level == "workflow_ready":
                workflow_ready += 1

        report_rows.append(
            {
                "group_id": group_id,
                "group_key": meta["key"],
                "group_label": meta["label"],
                "official_procedure_count": official_count,
                "expanded_procedure_count": expanded_count,
                "procedure_count": len(merged_procedures),
                "raw_data_count": raw_count,
                "missing_raw_count": missing_raw_for_group,
                "workflow_ready_count": workflow_ready,
                "workflow_data_count": workflow_data_count,
            }
        )

    entries.sort(key=lambda item: (item.group_key, item.membership_source, item.procedure_title, item.procedure_code))

    write_groups_json(group_payload)
    write_mapping_csv(entries)
    write_mapping_json(entries)
    write_report_json(report_rows, missing_raw_codes)

    print(f"Wrote {len(entries)} citizen procedure mappings across {len(report_rows)} groups.")
    print(f"Missing raw_data codes found in full-data.csv: {len(sorted(set(missing_raw_codes)))}")
    if missing_raw_codes:
        print(",".join(sorted(set(missing_raw_codes))))


def fetch_group_procedures(session: requests.Session, group_id: int) -> list[dict[str, str]]:
    procedures = fetch_group_procedures_via_group_service(session, group_id)
    if procedures:
        return procedures

    event_ids = fetch_group_event_ids(session, group_id)
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for event_id in event_ids:
        for item in fetch_group_procedures_via_event_service(session, event_id):
            code = str(item["procedure_code"])
            if code in seen:
                continue
            seen.add(code)
            merged.append(item)
    return merged


def fetch_group_procedures_via_group_service(session: requests.Session, group_id: int) -> list[dict[str, str]]:
    page = 1
    results: list[dict[str, Any]] = []
    total_records: int | None = None

    while True:
        payload = {
            "service": "dvcqg_get_all_procedure_by_group_event_v2",
            "type": "ref",
            "groupEventId": str(group_id),
            "number_record": 50,
            "current_page": page,
            "keyWord": "",
        }
        batch = post_service(session, payload)
        if not batch:
            break
        if total_records is None:
            total_records = int(batch[0].get("TOTAL_RECORDS") or len(batch))
        results.extend(batch)
        if len(results) >= total_records or len(batch) < 50:
            break
        page += 1

    return dedupe_procedures(
        {
            "procedure_code": str(item.get("PROCEDURE_CODE") or "").strip(),
            "procedure_title": clean_text(item.get("PROCEDURE_NAME")),
            "detail_url": procedure_detail_url(str(item.get("PROCEDURE_CODE") or "").strip()),
        }
        for item in results
    )


def fetch_group_event_ids(session: requests.Session, group_id: int) -> list[str]:
    html = session.get(GROUP_PAGE_TEMPLATE.format(group_id=group_id), timeout=30).text
    event_ids = re.findall(r"getProcedureByEvent\((\d+)\)", html)
    deduped: list[str] = []
    seen: set[str] = set()
    for event_id in event_ids:
        if event_id not in seen:
            seen.add(event_id)
            deduped.append(event_id)
    return deduped


def fetch_group_procedures_via_event_service(session: requests.Session, event_id: str) -> list[dict[str, str]]:
    page = 1
    results: list[dict[str, Any]] = []
    total_records: int | None = None

    while True:
        payload = {
            "service": "dvcqg_gets_procedure_by_event_service_v2",
            "type": "ref",
            "page_index": page,
            "procedure_name": "",
            "page_size": 50,
            "event_id": str(event_id),
        }
        batch = post_service(session, payload)
        if not batch:
            break
        if total_records is None:
            total_records = int(batch[0].get("TOTAL") or len(batch))
        results.extend(batch)
        if len(results) >= total_records or len(batch) < 50:
            break
        page += 1

    return dedupe_procedures(
        {
            "procedure_code": str(item.get("PROCEDURE_CODE") or "").strip(),
            "procedure_title": clean_text(item.get("PROCEDURE_NAME")),
            "detail_url": procedure_detail_url(str(item.get("PROCEDURE_CODE") or "").strip()),
        }
        for item in results
    )


def post_service(session: requests.Session, payload: dict[str, Any]) -> list[dict[str, Any]]:
    response = session.post(
        REST_URL,
        data={"params": json.dumps(payload, ensure_ascii=False)},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def dedupe_procedures(items: Any) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        code = str(item.get("procedure_code") or "").strip()
        if not code or code in seen:
            continue
        seen.add(code)
        output.append(item)
    return output


def load_full_data() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with FULL_DATA_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            code = str(row.get("Mã số") or "").strip()
            if code:
                rows[code] = row
    return rows


def load_workflow_codes() -> dict[str, str]:
    codes: dict[str, str] = {}
    for workflow_family, path in WORKFLOW_SUMMARY_FILES.items():
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                code = str(row.get("ma_thu_tuc") or row.get("Mã số") or "").strip()
                if code:
                    codes[code] = workflow_family
    return codes


def merge_group_procedures(
    group_key: str,
    official_procedures: list[dict[str, str]],
    full_data: dict[str, dict[str, str]],
    workflow_codes: dict[str, str],
) -> list[dict[str, Any]]:
    merged: OrderedDict[str, dict[str, Any]] = OrderedDict()

    for item in official_procedures:
        code = str(item["procedure_code"]).strip()
        if not code:
            continue
        merged[code] = {
            "procedure_code": code,
            "procedure_title": item["procedure_title"],
            "detail_url": item["detail_url"],
            "official_membership": True,
            "expanded_membership": False,
            "membership_source": "official",
            "source_note": "",
        }

    for code, row in full_data.items():
        source_note = match_expansion_rule(group_key, code, row, workflow_codes)
        if source_note is None:
            continue

        title = clean_text(row.get("Tên"))
        detail_url = str(row.get("URL") or "").strip()

        if code in merged:
            merged[code]["expanded_membership"] = True
            merged[code]["membership_source"] = "official+expanded"
            if source_note != "workflow_seed":
                merged[code]["source_note"] = source_note
            continue

        merged[code] = {
            "procedure_code": code,
            "procedure_title": title,
            "detail_url": detail_url,
            "official_membership": False,
            "expanded_membership": True,
            "membership_source": "expanded",
            "source_note": source_note,
        }

    return list(merged.values())


def match_expansion_rule(
    group_key: str,
    code: str,
    row: dict[str, str],
    workflow_codes: dict[str, str],
) -> str | None:
    workflow_family = workflow_codes.get(code)
    if group_key == "co_con_nho" and workflow_family == "birth_registration":
        return "workflow_seed"
    if group_key == "cu_tru_giay_to" and workflow_family == "residence_management":
        return "workflow_seed"

    rule = GROUP_EXPANSION_RULES.get(group_key, {})
    normalized_title = normalize_text(row.get("Tên"))
    normalized_field = normalize_text(row.get("Lĩnh vực"))

    for field_name in rule.get("field_names", []):
        if normalized_field == normalize_text(field_name):
            if has_excluded_phrase(normalized_title, rule.get("title_excludes", [])):
                return None
            return f"field:{field_name}"

    for phrase in rule.get("title_includes", []):
        if phrase in normalized_title:
            if has_excluded_phrase(normalized_title, rule.get("title_excludes", [])):
                return None
            return f"title:{phrase}"

    return None


def has_excluded_phrase(normalized_title: str, phrases: list[str]) -> bool:
    return any(phrase in normalized_title for phrase in phrases)


def infer_support_level(raw_available: bool, workflow_family: str | None) -> str:
    if workflow_family:
        return "workflow_ready"
    if raw_available:
        return "raw_only"
    return "catalog_ready"


def has_raw_data(code: str) -> bool:
    folder = RAW_DATA_DIR / code.replace(".", "_")
    return folder.exists() and any(folder.glob("*_procedure_detail.md"))


def procedure_detail_url(code: str) -> str:
    return f"https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-hanh-chinh.html?ma_thu_tuc={code}"


def clean_text(value: Any) -> str:
    text = unescape(str(value or "")).strip()
    return re.sub(r"\s+", " ", text)


def normalize_text(value: Any) -> str:
    text = clean_text(value).lower()
    normalized = unicodedata.normalize("NFD", text)
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = normalized.replace("đ", "d")
    return re.sub(r"\s+", " ", normalized).strip()


def write_groups_json(payload: dict[str, Any]) -> None:
    path = CATALOG_DIR / "citizen_groups.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_mapping_csv(entries: list[ProcedureEntry]) -> None:
    path = CATALOG_DIR / "citizen_procedure_mapping.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "persona",
                "group_key",
                "procedure_code",
                "procedure_title",
                "workflow_family",
                "support_level",
                "raw_data_available",
                "in_full_data",
                "workflow_data_available",
                "official_membership",
                "expanded_membership",
                "membership_source",
                "field",
                "source_url",
                "notes",
            ]
        )
        for entry in entries:
            writer.writerow(
                [
                    "citizen",
                    entry.group_key,
                    entry.procedure_code,
                    entry.procedure_title,
                    entry.workflow_family or "",
                    entry.support_level,
                    "true" if entry.raw_data_available else "false",
                    "true" if entry.in_full_data else "false",
                    "true" if entry.workflow_data_available else "false",
                    "true" if entry.official_membership else "false",
                    "true" if entry.expanded_membership else "false",
                    entry.membership_source,
                    entry.field,
                    entry.source_url,
                    entry.notes,
                ]
            )


def write_mapping_json(entries: list[ProcedureEntry]) -> None:
    path = CATALOG_DIR / "citizen_procedure_mapping.json"
    payload = [
        {
            "persona": "citizen",
            "group_id": entry.group_id,
            "group_key": entry.group_key,
            "group_label": entry.group_label,
            "procedure_code": entry.procedure_code,
            "procedure_title": entry.procedure_title,
            "workflow_family": entry.workflow_family,
            "support_level": entry.support_level,
            "raw_data_available": entry.raw_data_available,
            "in_full_data": entry.in_full_data,
            "workflow_data_available": entry.workflow_data_available,
            "official_membership": entry.official_membership,
            "expanded_membership": entry.expanded_membership,
            "membership_source": entry.membership_source,
            "field": entry.field,
            "source_url": entry.source_url,
            "notes": entry.notes,
        }
        for entry in entries
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report_json(report_rows: list[dict[str, Any]], missing_raw_codes: list[str]) -> None:
    path = CATALOG_DIR / "citizen_catalog_report.json"
    payload = {
        "generated_at": "2026-07-18",
        "groups": report_rows,
        "missing_raw_codes_in_full_data": sorted(set(missing_raw_codes)),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
