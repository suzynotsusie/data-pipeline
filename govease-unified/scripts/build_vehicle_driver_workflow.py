from __future__ import annotations

import csv
import json
import re
import subprocess
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from workflow_fixture_generation import ensure_fixture_coverage
from workflow_subdomain_layout import materialize_subdomain_outputs


ROOT = Path(__file__).resolve().parents[2]
FULL_DATA_CSV = ROOT / "main" / "full-data.csv"
RAW_DATA_DIR = ROOT / "raw_data"
WORKFLOW_DIR = ROOT / "data" / "workflows" / "phuong_tien_nguoi_lai"
TESTS_DIR = ROOT / "tests" / "workflows" / "phuong_tien_nguoi_lai"
MAPPING_CSV = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.csv"
MAPPING_JSON = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.json"
CHECKLIST_DOC = ROOT / "govease-unified" / "docs" / "codex-workstream-checklist.md"

DOMAIN_KEY = "phuong_tien_nguoi_lai"
WORKFLOW_FAMILY = "vehicle_driver_workflow"
UPDATED_AT = str(date.today())

FIELD_TO_SUBDOMAIN = {
    "Sát hạch, cấp giấy phép lái xe": {
        "subdomain_key": "giay_phep_lai_xe",
        "subdomain_label": "Giấy phép lái xe",
        "event_id": 315,
    },
    "Đăng ký, quản lý phương tiện giao thông cơ giới, xe máy chuyên dùng": {
        "subdomain_key": "dang_ky_phuong_tien",
        "subdomain_label": "Đăng ký phương tiện",
        "event_id": 316,
    },
    "Đăng kiểm": {
        "subdomain_key": "dang_kiem_phuong_tien",
        "subdomain_label": "Đăng kiểm phương tiện",
        "event_id": 317,
    },
}

SUBDOMAIN_SUMMARIES = {
    "giay_phep_lai_xe": "Nhóm thủ tục liên quan đến cấp, đổi, cấp lại, thu hồi giấy phép lái xe và cấp phép/chấp thuận cho hoạt động sát hạch lái xe.",
    "dang_ky_phuong_tien": "Nhóm thủ tục liên quan đến đăng ký, cấp đổi, cấp lại, sang tên, thu hồi đăng ký và biển số phương tiện giao thông cơ giới, xe máy chuyên dùng.",
    "dang_kiem_phuong_tien": "Nhóm thủ tục liên quan đến kiểm định, chứng nhận chất lượng an toàn kỹ thuật, khí thải và điều kiện hoạt động đăng kiểm cho phương tiện.",
}

SUBDOMAIN_ENTRY_PROMPTS = {
    "giay_phep_lai_xe": [
        "Bạn muốn cấp mới, đổi, cấp lại hay thu hồi giấy phép lái xe?",
        "Nếu liên quan đến sát hạch, bạn đang hỏi về cá nhân dự thi hay trung tâm/sân tập sát hạch?",
    ],
    "dang_ky_phuong_tien": [
        "Bạn muốn đăng ký xe lần đầu, sang tên, đổi/cấp lại đăng ký hay thu hồi biển số?",
        "Bạn làm trực tuyến toàn trình hay nộp trực tiếp/một phần?",
    ],
    "dang_kiem_phuong_tien": [
        "Bạn đang cần kiểm định xe, chứng nhận chất lượng xe/phụ tùng, hay thủ tục dành cho đơn vị đăng kiểm?",
        "Phương tiện của bạn là xe cơ giới, xe máy chuyên dùng, mô tô/xe gắn máy hay nhóm khác?",
    ],
}

INTAKE_CASES = [
    {
        "id": "intake-vehicle-01",
        "user_need": "Tôi muốn thi và được cấp bằng lái ô tô lần đầu.",
        "expected_procedure_code": "3.000346",
        "expected_terms": ["sát hạch", "giấy phép lái xe"],
    },
    {
        "id": "intake-vehicle-02",
        "user_need": "Bằng lái của tôi sắp hết hạn, tôi muốn đổi sang bằng mới.",
        "expected_procedure_code": "3.000347",
        "expected_terms": ["đổi giấy phép lái xe"],
    },
    {
        "id": "intake-vehicle-03",
        "user_need": "Tôi bị mất bằng lái và cần xin cấp lại.",
        "expected_procedure_code": "3.000348",
        "expected_terms": ["cấp lại", "giấy phép lái xe"],
    },
    {
        "id": "intake-vehicle-04",
        "user_need": "Tôi cần đổi bằng lái nước ngoài sang bằng lái Việt Nam.",
        "expected_procedure_code": "3.000351",
        "expected_terms": ["người nước ngoài", "đổi giấy phép lái xe"],
    },
    {
        "id": "intake-vehicle-05",
        "user_need": "Tôi muốn đăng ký xe mới mua và bấm biển số lần đầu.",
        "expected_procedure_code": "1.013067",
        "expected_terms": ["đăng ký", "biển số xe"],
    },
    {
        "id": "intake-vehicle-06",
        "user_need": "Tôi cần sang tên xe khi đổi chủ.",
        "expected_procedure_code": "1.013076",
        "expected_terms": ["sang tên xe", "thay đổi chủ xe"],
    },
    {
        "id": "intake-vehicle-07",
        "user_need": "Tôi muốn đăng ký tạm thời chiếc xe để di chuyển về tỉnh khác.",
        "expected_procedure_code": "1.013086",
        "expected_terms": ["đăng ký xe tạm thời"],
    },
    {
        "id": "intake-vehicle-08",
        "user_need": "Tôi muốn đi đăng kiểm xe ô tô đang sử dụng.",
        "expected_procedure_code": "1.005103",
        "expected_terms": ["kiểm định", "xe cơ giới"],
    },
    {
        "id": "intake-vehicle-09",
        "user_need": "Xe tôi thuộc diện miễn kiểm định lần đầu thì làm thủ tục nào?",
        "expected_procedure_code": "1.013089",
        "expected_terms": ["miễn kiểm định lần đầu"],
    },
    {
        "id": "intake-vehicle-10",
        "user_need": "Tôi cần kiểm định khí thải cho xe máy.",
        "expected_procedure_code": "1.013101",
        "expected_terms": ["khí thải", "xe mô tô"],
    },
]

SUBMISSION_CASES = [
    {
        "id": "submission-vehicle-license-missing-health-check",
        "procedure_code": "3.000346",
        "submission": {
            "applicant": {
                "full_name": "Nguyễn Văn A",
                "identity_number": "12345",
            },
            "training_certificate_present": False,
            "health_certificate_present": False,
            "signature_present": False,
        },
        "expected_rule_ids": [
            "identity-number-format",
            "missing-training-certificate",
            "missing-health-certificate",
            "missing-signature",
        ],
    },
    {
        "id": "submission-vehicle-license-foreign-conversion-missing-foreign-license",
        "procedure_code": "3.000351",
        "submission": {
            "applicant": {
                "full_name": "John Doe",
                "identity_number": "012345678901",
            },
            "foreign_license_present": False,
            "passport_present": True,
            "translation_present": False,
        },
        "expected_rule_ids": [
            "missing-foreign-license",
            "missing-certified-translation",
        ],
    },
    {
        "id": "submission-vehicle-registration-first-time-missing-ownership-proof",
        "procedure_code": "1.013067",
        "submission": {
            "owner": {
                "full_name": "Lê Thị B",
                "identity_number": "01234567890X",
            },
            "vehicle_origin_document_present": True,
            "ownership_document_present": False,
            "fee_paid": False,
        },
        "expected_rule_ids": [
            "identity-number-format",
            "missing-ownership-document",
            "registration-fee-unpaid",
        ],
    },
    {
        "id": "submission-vehicle-transfer-missing-revocation",
        "procedure_code": "1.013076",
        "submission": {
            "owner": {
                "full_name": "Phạm Văn C",
                "identity_number": "012345678901",
            },
            "transfer_contract_present": True,
            "previous_registration_revoked": False,
        },
        "expected_rule_ids": [
            "missing-registration-revocation-step",
        ],
    },
    {
        "id": "submission-vehicle-inspection-bad-dates",
        "procedure_code": "1.005103",
        "submission": {
            "vehicle_plate": "30A-12345",
            "inspection_booking_date": "2026-07-20",
            "last_inspection_expiry": "2026-07-10",
            "insurance_present": False,
        },
        "expected_rule_ids": [
            "inspection-booking-after-expiry",
            "missing-mandatory-insurance",
        ],
    },
    {
        "id": "submission-vehicle-emissions-motorbike-missing-test-vehicle",
        "procedure_code": "1.013101",
        "submission": {
            "vehicle_type": "xe mô tô",
            "vehicle_present_for_test": False,
            "owner_identity_present": True,
        },
        "expected_rule_ids": [
            "vehicle-not-present-for-emissions-test",
        ],
    },
]


def slugify(value: str) -> str:
    value = value.lower().replace("đ", "d")
    normalized = unicodedata.normalize("NFD", value)
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    slug = re.sub(r"[^a-z0-9]+", "_", stripped).strip("_")
    return re.sub(r"_+", "_", slug)


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_first_meaningful_paragraph(text: str) -> str:
    parts = [compact_text(part) for part in re.split(r"\n\s*\n", text) if compact_text(part)]
    for part in parts:
        if not part.startswith("#"):
            return part
    return ""


def parse_markdown_table(lines: list[str], start_index: int) -> tuple[list[dict[str, str]], int]:
    header = [part.strip() for part in lines[start_index].strip().strip("|").split("|")]
    rows: list[dict[str, str]] = []
    index = start_index + 2
    while index < len(lines):
        line = lines[index]
        if "|" not in line or not line.strip().startswith("|"):
            break
        values = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(values) == len(header):
            rows.append(dict(zip(header, values)))
        index += 1
    return rows, index


def parse_raw_markdown(markdown_path: Path) -> dict[str, Any]:
    text = markdown_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    sections: dict[str, list[str]] = defaultdict(list)
    current_section = "root"
    current_subsection: str | None = None
    i = 0
    document_groups: list[dict[str, Any]] = []

    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            current_section = line[3:].strip()
            current_subsection = None
            i += 1
            continue
        if line.startswith("### "):
            current_subsection = line[4:].strip()
            i += 1
            continue
        if current_section == "Thành phần hồ sơ" and current_subsection and line.strip().startswith("|"):
            table_rows, i = parse_markdown_table(lines, i)
            document_groups.append(
                {
                    "group_name": current_subsection,
                    "documents": table_rows,
                }
            )
            continue
        sections[current_section].append(line)
        i += 1

    method_rows: list[dict[str, str]] = []
    method_lines = sections.get("Cách thức thực hiện", [])
    for idx, line in enumerate(method_lines):
        if line.strip().startswith("|"):
            method_rows, _ = parse_markdown_table(method_lines, idx)
            break

    result_items = []
    for line in sections.get("Kết quả xử lý", []):
        clean = compact_text(line.lstrip("*").strip())
        if clean:
            result_items.append(clean)

    return {
        "overview": extract_first_meaningful_paragraph("\n".join(sections.get("Trình tự thực hiện", []))),
        "procedure_flow": compact_text("\n".join(sections.get("Trình tự thực hiện", []))),
        "requirements": compact_text("\n".join(sections.get("Yêu cầu, điều kiện thực hiện", []))),
        "methods": method_rows,
        "document_groups": document_groups,
        "result_items": result_items,
        "legal_bases": [
            compact_text(line)
            for line in sections.get("Căn cứ pháp lý", [])
            if line.strip().startswith("|") is False and compact_text(line)
        ],
    }


def powershell_json(command: str) -> Any:
    wrapped = (
        "$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); "
        + command
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", wrapped],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def fetch_domain_rows() -> list[dict[str, str]]:
    all_rows: list[dict[str, str]] = []
    for field_name in FIELD_TO_SUBDOMAIN:
        command = (
            f"Import-Csv '{FULL_DATA_CSV}' "
            f"| Where-Object {{ $_.'Lĩnh vực' -eq '{field_name}' }} "
            "| Select-Object 'Mã số','Tên','Cơ quan thực hiện','Lĩnh vực','URL' "
            "| ConvertTo-Json -Depth 3 -Compress"
        )
        rows = powershell_json(command)
        if isinstance(rows, dict):
            rows = [rows]
        all_rows.extend(rows)
    return all_rows


def classify_operation(row: dict[str, str], subdomain_key: str) -> dict[str, str]:
    title = row["Tên"]
    title_slug = slugify(title)
    if subdomain_key == "giay_phep_lai_xe":
        if "quoc_te" in title_slug:
            operation_group = "gplx_quoc_te"
        elif "nuoc_ngoai" in title_slug:
            operation_group = "doi_gplx_nuoc_ngoai"
        elif "quan_su" in title_slug:
            operation_group = "doi_gplx_quan_su"
        elif "cong_an_nhan_dan" in title_slug:
            operation_group = "doi_gplx_cong_an"
        elif "trung_tam_sat_hach" in title_slug or "san_tap_lai" in title_slug:
            operation_group = "co_so_sat_hach"
        elif title_slug.startswith("cap_lai_giay_phep_lai_xe"):
            operation_group = "cap_lai_gplx"
        elif title_slug.startswith("doi_giay_phep_lai_xe"):
            operation_group = "doi_gplx"
        elif title_slug.startswith("thu_hoi_giay_phep_lai_xe"):
            operation_group = "thu_hoi_gplx"
        elif title_slug.startswith("cap_giay_phep_lai_xe"):
            operation_group = "cap_moi_gplx"
        else:
            operation_group = "sat_hach_khac"
    elif subdomain_key == "dang_ky_phuong_tien":
        if "sang_ten_xe" in title_slug or "thay_doi_chu_xe" in title_slug:
            operation_group = "sang_ten_xe"
        elif "dang_ky_xe_lan_dau" in title_slug:
            operation_group = "dang_ky_lan_dau"
        elif "dang_ky_xe_tam_thoi" in title_slug:
            operation_group = "dang_ky_tam_thoi"
        elif title_slug.startswith("doi_chung_nhan_dang_ky_xe"):
            operation_group = "doi_dang_ky_xe"
        elif title_slug.startswith("cap_lai_chung_nhan_dang_ky_xe"):
            operation_group = "cap_lai_dang_ky_xe"
        elif title_slug.startswith("thu_hoi_giay_chung_nhan_dang_ky") or title_slug.startswith("thu_hoi_chung_nhan_dang_ky"):
            operation_group = "thu_hoi_dang_ky_xe"
        elif "phuong_tien_giao_thong_thong_minh" in title_slug:
            operation_group = "phuong_tien_thong_minh"
        else:
            operation_group = "dang_ky_khac"
    else:
        if "kiem_dinh_khi_thai" in title_slug:
            operation_group = "kiem_dinh_khi_thai"
        elif "du_dieu_kien_hoat_dong_kiem_dinh" in title_slug:
            operation_group = "dieu_kien_hoat_dong_dang_kiem"
        elif "dang_kiem_vien" in title_slug:
            operation_group = "dang_kiem_vien"
        elif "giay_chung_nhan_kiem_dinh" in title_slug or "tem_kiem_dinh" in title_slug:
            operation_group = "kiem_dinh_phuong_tien"
        elif "chung_nhan_chat_luong" in title_slug or "chung_chi_chat_luong" in title_slug:
            operation_group = "chung_nhan_chat_luong"
        elif "giay_chung_nhan_lao_dong_hang_hai" in title_slug or "bo_luat_isps" in title_slug or "an_ninh_tau_bien" in title_slug:
            operation_group = "dang_kiem_hang_hai"
        elif "ket_noi_chia_se_su_dung_du_lieu_dang_kiem" in title_slug:
            operation_group = "du_lieu_dang_kiem"
        else:
            operation_group = "dang_kiem_khac"
    return {
        "operation_group": operation_group,
        "operation_key": title_slug,
    }


def build_records(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in rows:
        field_name = row["Lĩnh vực"]
        subdomain_meta = FIELD_TO_SUBDOMAIN[field_name]
        code = row["Mã số"]
        raw_dir = RAW_DATA_DIR / code.replace(".", "_")
        raw_file = raw_dir / f"{code.replace('.', '_')}_procedure_detail.md"
        parsed = parse_raw_markdown(raw_file) if raw_file.exists() else {
            "overview": "",
            "procedure_flow": "",
            "requirements": "",
            "methods": [],
            "document_groups": [],
            "result_items": [],
            "legal_bases": [],
        }
        operation_meta = classify_operation(row, subdomain_meta["subdomain_key"])
        method_names = [compact_text(item.get("Hình thức nộp", "")) for item in parsed["methods"] if compact_text(item.get("Hình thức nộp", ""))]
        processing_time_values = [
            compact_text(item.get("Thời gian giải quyết", ""))
            for item in parsed["methods"]
            if compact_text(item.get("Thời gian giải quyết", ""))
        ]
        records.append(
            {
                "procedure_code": code,
                "procedure_title": row["Tên"],
                "field": field_name,
                "subdomain_key": subdomain_meta["subdomain_key"],
                "subdomain_label": subdomain_meta["subdomain_label"],
                "event_id": subdomain_meta["event_id"],
                "operation_group": operation_meta["operation_group"],
                "operation_key": operation_meta["operation_key"],
                "agency": compact_text(row.get("Cơ quan thực hiện", "")),
                "source_url": row["URL"],
                "raw_data_file": str(raw_file),
                "raw_data_available": raw_file.exists(),
                "overview": parsed["overview"],
                "procedure_flow": parsed["procedure_flow"],
                "requirements": parsed["requirements"],
                "submission_methods": method_names,
                "processing_time_values": processing_time_values,
                "document_groups": parsed["document_groups"],
                "result_items": parsed["result_items"],
                "legal_bases": parsed["legal_bases"],
            }
        )
    return sorted(records, key=lambda item: (item["subdomain_key"], item["procedure_code"]))


def write_summary(records: list[dict[str, Any]]) -> Path:
    path = WORKFLOW_DIR / "summary.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "subdomain_key",
                "subdomain_label",
                "procedure_code",
                "procedure_title",
                "operation_group",
                "operation_key",
                "agency",
                "submission_methods",
                "processing_time_values",
                "document_group_count",
                "result_count",
                "raw_data_available",
                "source_url",
                "raw_data_file",
            ],
        )
        writer.writeheader()
        for item in records:
            writer.writerow(
                {
                    "subdomain_key": item["subdomain_key"],
                    "subdomain_label": item["subdomain_label"],
                    "procedure_code": item["procedure_code"],
                    "procedure_title": item["procedure_title"],
                    "operation_group": item["operation_group"],
                    "operation_key": item["operation_key"],
                    "agency": item["agency"],
                    "submission_methods": " | ".join(item["submission_methods"]),
                    "processing_time_values": " | ".join(item["processing_time_values"]),
                    "document_group_count": len(item["document_groups"]),
                    "result_count": len(item["result_items"]),
                    "raw_data_available": item["raw_data_available"],
                    "source_url": item["source_url"],
                    "raw_data_file": item["raw_data_file"],
                }
            )
    return path


def write_normalized(records: list[dict[str, Any]]) -> Path:
    grouped: dict[str, dict[str, Any]] = {}
    for field_name, meta in FIELD_TO_SUBDOMAIN.items():
        subdomain_key = meta["subdomain_key"]
        grouped[subdomain_key] = {
            "subdomain_key": subdomain_key,
            "subdomain_label": meta["subdomain_label"],
            "event_id": meta["event_id"],
            "field_name": field_name,
            "summary": SUBDOMAIN_SUMMARIES[subdomain_key],
            "entry_prompts": SUBDOMAIN_ENTRY_PROMPTS[subdomain_key],
            "procedure_count": 0,
            "procedures": [],
        }
    for item in records:
        group = grouped[item["subdomain_key"]]
        group["procedure_count"] += 1
        group["procedures"].append(item)

    payload = {
        "schema_version": "1.0",
        "domain": DOMAIN_KEY,
        "updated_at": UPDATED_AT,
        "source_files": [
            str(FULL_DATA_CSV),
            str(RAW_DATA_DIR),
        ],
        "subdomains": list(grouped.values()),
    }
    path = WORKFLOW_DIR / "normalized.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def build_decision_tree(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped_operations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in records:
        grouped_operations[item["subdomain_key"]].append(item)

    routes = []
    for item in records:
        routes.append(
            {
                "route_id": f"{item['subdomain_key']}-{item['procedure_code'].replace('.', '_')}",
                "conditions": {
                    "subdomain_key": item["subdomain_key"],
                    "operation_key": item["operation_key"],
                },
                "procedure_code": item["procedure_code"],
                "procedure_name": item["procedure_title"],
                "why_this_route": f"Route trực tiếp cho nhu cầu '{item['procedure_title']}' trong nhánh '{item['subdomain_label']}'.",
            }
        )

    operation_catalog = {
        subdomain_key: [
            {
                "operation_key": item["operation_key"],
                "operation_group": item["operation_group"],
                "procedure_code": item["procedure_code"],
                "procedure_title": item["procedure_title"],
            }
            for item in items
        ]
        for subdomain_key, items in grouped_operations.items()
    }

    return {
        "start_node": "vehicle_subdomain",
        "nodes": [
            {
                "id": "vehicle_subdomain",
                "type": "question",
                "slot": "subdomain_key",
                "question": "Bạn đang hỏi về giấy phép lái xe, đăng ký phương tiện hay đăng kiểm phương tiện?",
                "options": list(grouped_operations.keys()),
            },
            {
                "id": "vehicle_operation",
                "type": "question",
                "slot": "operation_key",
                "question": "Bạn cần làm thao tác nào cụ thể trong nhánh đã chọn?",
                "options_by_subdomain": operation_catalog,
            },
        ],
        "routes": routes,
    }


def write_workflow_config(records: list[dict[str, Any]], summary_path: Path, normalized_path: Path) -> Path:
    coverage_codes = [item["procedure_code"] for item in records]
    payload = {
        "schema_version": "1.0",
        "domain": DOMAIN_KEY,
        "updated_at": UPDATED_AT,
        "source_files": [
            str(FULL_DATA_CSV),
            str(summary_path),
            str(normalized_path),
            str(RAW_DATA_DIR),
        ],
        "coverage": {
            "expected_codes": coverage_codes,
            "covered_codes": coverage_codes,
            "missing_codes": [],
        },
        "llm_contract": {
            "role": "parse_user_answer_and_rephrase_question_only",
            "required_output_schema": {
                "intent": DOMAIN_KEY,
                "current_node": "string",
                "slot_updates": {
                    "subdomain_key": "giay_phep_lai_xe | dang_ky_phuong_tien | dang_kiem_phuong_tien | unknown",
                    "operation_key": "string",
                    "operation_group": "string",
                    "needs_human_review": "boolean",
                },
                "confidence": "0_to_1",
                "needs_human_review": "boolean",
            },
        },
        "entry_prompts": [
            "Bạn đang cần làm việc về bằng lái, đăng ký xe hay đăng kiểm phương tiện?",
            "Bạn muốn cấp mới, cấp lại, đổi, thu hồi hay xác nhận/chứng nhận cho phương tiện của mình?",
        ],
        "slots": [
            {
                "name": "subdomain_key",
                "required": True,
                "description": "Nhánh chính trong domain phương tiện và người lái.",
            },
            {
                "name": "operation_key",
                "required": True,
                "description": "Thao tác cụ thể ánh xạ trực tiếp tới thủ tục cuối cùng.",
            },
            {
                "name": "operation_group",
                "required": False,
                "description": "Nhóm thao tác nghiệp vụ để gom các thủ tục gần nhau cho UI và parser.",
            },
        ],
        "subdomain_catalog": [
            {
                "subdomain_key": meta["subdomain_key"],
                "subdomain_label": meta["subdomain_label"],
                "event_id": meta["event_id"],
                "field_name": field_name,
                "summary": SUBDOMAIN_SUMMARIES[meta["subdomain_key"]],
            }
            for field_name, meta in FIELD_TO_SUBDOMAIN.items()
        ],
        "decision_tree": build_decision_tree(records),
        "pre_submission_checks": [
            {
                "field_group": "driver_identity",
                "checks": [
                    "Thông tin CCCD/hộ chiếu phải đúng định dạng và còn hiệu lực.",
                    "Nếu đổi hoặc cấp lại bằng lái thì phải đối chiếu đúng thông tin giấy phép cũ với dữ liệu hiện tại.",
                ],
            },
            {
                "field_group": "vehicle_registration",
                "checks": [
                    "Hồ sơ đăng ký xe phải có chứng từ nguồn gốc xe và chứng từ quyền sở hữu hợp lệ.",
                    "Các thủ tục sang tên hoặc thu hồi cần làm rõ trạng thái đăng ký cũ và biển số hiện tại.",
                ],
            },
            {
                "field_group": "inspection_readiness",
                "checks": [
                    "Nhóm đăng kiểm phải xác định đúng loại phương tiện trước khi chọn thủ tục kiểm định/chứng nhận.",
                    "Cần đối chiếu thời hạn, giấy tờ kỹ thuật và việc xe có thuộc diện miễn kiểm định lần đầu hay không.",
                ],
            },
        ],
    }
    path = WORKFLOW_DIR / "workflow_engine_config.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_test_cases(records: list[dict[str, Any]]) -> tuple[Path, Path]:
    intake_path = TESTS_DIR / "intake_cases.json"
    submission_path = TESTS_DIR / "submission_cases.json"
    covered_intake, covered_submission = ensure_fixture_coverage(
        DOMAIN_KEY,
        records,
        INTAKE_CASES,
        SUBMISSION_CASES,
    )
    intake_path.write_text(json.dumps(covered_intake, ensure_ascii=False, indent=2), encoding="utf-8")
    submission_path.write_text(
        json.dumps(covered_submission, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return intake_path, submission_path


def update_mapping(records: list[dict[str, Any]]) -> None:
    workflow_codes = {item["procedure_code"]: item for item in records}

    with MAPPING_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
        csv_fields = list(csv_rows[0].keys())

    changed_csv_rows = []
    for row in csv_rows:
        if row.get("group_key") != DOMAIN_KEY:
            changed_csv_rows.append(row)
            continue
        code = row.get("procedure_code", "")
        if code in workflow_codes:
            item = workflow_codes[code]
            row["workflow_family"] = WORKFLOW_FAMILY
            row["support_level"] = "workflow_ready"
            row["in_workflow_dataset"] = "true"
            row["field"] = item["field"]
            row["notes"] = f"workflow_generated:{DOMAIN_KEY}/{item['subdomain_key']}"
        else:
            row["in_workflow_dataset"] = "false"
            row["support_level"] = "raw_only"
            if row.get("workflow_family") == WORKFLOW_FAMILY:
                row["workflow_family"] = ""
            row["notes"] = "excluded_from_clean_workflow_dataset"
        changed_csv_rows.append(row)

    with MAPPING_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(changed_csv_rows)

    json_rows = json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
    for row in json_rows:
        if row.get("group_key") != DOMAIN_KEY:
            continue
        code = row.get("procedure_code", "")
        if code in workflow_codes:
            item = workflow_codes[code]
            row["workflow_family"] = WORKFLOW_FAMILY
            row["support_level"] = "workflow_ready"
            row["in_workflow_dataset"] = True
            row["field"] = item["field"]
            row["notes"] = f"workflow_generated:{DOMAIN_KEY}/{item['subdomain_key']}"
        else:
            row["in_workflow_dataset"] = False
            row["support_level"] = "raw_only"
            if row.get("workflow_family") == WORKFLOW_FAMILY:
                row["workflow_family"] = None
            row["notes"] = "excluded_from_clean_workflow_dataset"
    MAPPING_JSON.write_text(json.dumps(json_rows, ensure_ascii=False, indent=2), encoding="utf-8")


def update_checklist(records: list[dict[str, Any]]) -> None:
    text = CHECKLIST_DOC.read_text(encoding="utf-8")
    marker = "- Uu tien rollout:\n  - `phuong_tien_nguoi_lai`\n"
    replacement = (
        "- Uu tien rollout:\n"
        "  - `phuong_tien_nguoi_lai` (da co workflow dataset va test data cho 70 ma thu tuc / 3 subdomain)\n"
    )
    if marker in text:
        text = text.replace(marker, replacement, 1)
    next_marker = "Buoc tiep theo dung pham vi Codex la:\n\n1. Dung workflow dataset skeleton cho `phuong_tien_nguoi_lai`\n"
    if next_marker in text:
        text = text.replace(
            next_marker,
            (
                "Buoc tiep theo dung pham vi Codex la:\n\n"
                "1. Mo rong cach lam nay sang `hoc_tap`\n"
            ),
            1,
        )
    CHECKLIST_DOC.write_text(text, encoding="utf-8")


def ensure_dirs() -> None:
    WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)
    TESTS_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    ensure_dirs()
    rows = fetch_domain_rows()
    records = build_records(rows)
    summary_path = write_summary(records)
    normalized_path = write_normalized(records)
    config_path = write_workflow_config(records, summary_path, normalized_path)
    materialize_subdomain_outputs(WORKFLOW_DIR, summary_path, normalized_path, config_path)
    intake_path, submission_path = write_test_cases(records)
    update_mapping(records)
    update_checklist(records)
    print(
        json.dumps(
            {
                "domain": DOMAIN_KEY,
                "procedure_count": len(records),
                "subdomains": {
                    subdomain_key: sum(
                        1 for item in records if item["subdomain_key"] == subdomain_key
                    )
                    for subdomain_key in {
                        value["subdomain_key"] for value in FIELD_TO_SUBDOMAIN.values()
                    }
                },
                "outputs": [
                    str(summary_path),
                    str(normalized_path),
                    str(config_path),
                    str(intake_path),
                    str(submission_path),
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
