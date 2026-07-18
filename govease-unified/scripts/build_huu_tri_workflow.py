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
WORKFLOW_DIR = ROOT / "data" / "workflows" / "huu_tri"
TESTS_DIR = ROOT / "tests" / "workflows" / "huu_tri"
MAPPING_CSV = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.csv"
MAPPING_JSON = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.json"
CHECKLIST_DOC = ROOT / "govease-unified" / "docs" / "codex-workstream-checklist.md"

DOMAIN_KEY = "huu_tri"
WORKFLOW_FAMILY = "retirement_workflow"
UPDATED_AT = str(date.today())

SUBDOMAINS = {
    "chuan_bi_nghi_huu": {
        "label": "Chuẩn bị nghỉ hưu",
        "event_id": 318,
        "summary": (
            "Nhóm thủ tục chuẩn bị hồ sơ, quá trình tham gia bảo hiểm xã hội và các điều kiện nền tảng "
            "để người dân sẵn sàng bước sang giai đoạn nghỉ hưu hoặc chọn phương án hưởng thay thế."
        ),
        "codes": [
            "1.014160",
            "1.014162",
            "1.002179",
            "1.014181",
            "1.014183",
            "1.014173",
            "1.013198",
            "2.002342",
            "2.002343",
            "2.002761",
        ],
        "entry_prompts": [
            "Bạn đang chuẩn bị nghỉ hưu, cần rà điều kiện hưởng lương hưu hay cập nhật quá trình tham gia bảo hiểm xã hội?",
            "Bạn muốn đăng ký tham gia BHXH, điều chỉnh thông tin, tính thời gian công tác hay xem phương án hưởng khi chưa đủ điều kiện nghỉ hưu?",
        ],
    },
    "che_do_huu_tri": {
        "label": "Chế độ hưu trí",
        "event_id": 319,
        "summary": (
            "Nhóm thủ tục hưởng lương hưu, trợ cấp hưu trí xã hội, chuyển nơi hưởng, thay đổi hình thức nhận "
            "và các chế độ phát sinh trong quá trình đang hưởng hưu trí."
        ),
        "codes": [
            "1.014171",
            "1.014172",
            "1.001742",
            "1.014176",
            "1.014175",
            "1.014174",
            "1.014027",
            "1.014589",
            "1.012822",
            "2.000605",
            "2.000809",
            "2.000755",
            "1.001646",
            "2.000762",
            "1.013140",
            "1.013142",
            "1.001710",
            "2.000740",
        ],
        "entry_prompts": [
            "Bạn đang muốn hưởng lương hưu, chuyển nơi nhận, đổi cách nhận hay điều chỉnh chế độ đang hưởng?",
            "Trường hợp của bạn là hưu trí BHXH bắt buộc, BHXH tự nguyện, trợ cấp hưu trí xã hội hay chế độ hưu trí đặc thù?",
        ],
    },
}

INTAKE_CASES = [
    {
        "id": "intake-retirement-01",
        "user_need": "Tôi muốn đăng ký tham gia bảo hiểm xã hội tự nguyện để chuẩn bị sau này có lương hưu.",
        "expected_procedure_code": "1.002179",
        "expected_terms": ["bảo hiểm xã hội tự nguyện", "chuẩn bị nghỉ hưu"],
    },
    {
        "id": "intake-retirement-02",
        "user_need": "Tôi cần kiểm tra lại thời gian công tác để đủ điều kiện hưởng bảo hiểm xã hội khi nghỉ việc.",
        "expected_procedure_code": "1.014181",
        "expected_terms": ["tính thời gian công tác", "hưởng bảo hiểm xã hội"],
    },
    {
        "id": "intake-retirement-03",
        "user_need": "Tôi không đủ điều kiện hưởng lương hưu và muốn hỏi chế độ thay thế.",
        "expected_procedure_code": "1.014183",
        "expected_terms": ["không đủ điều kiện hưởng lương hưu"],
    },
    {
        "id": "intake-retirement-04",
        "user_need": "Tôi muốn làm thủ tục hưởng lương hưu theo bảo hiểm xã hội bắt buộc.",
        "expected_procedure_code": "1.014171",
        "expected_terms": ["hưởng lương hưu", "bảo hiểm xã hội bắt buộc"],
    },
    {
        "id": "intake-retirement-05",
        "user_need": "Tôi đang hưởng lương hưu và muốn chuyển nơi nhận sang tỉnh khác.",
        "expected_procedure_code": "1.001742",
        "expected_terms": ["chuyển hưởng", "lương hưu"],
    },
    {
        "id": "intake-retirement-06",
        "user_need": "Tôi muốn đổi từ nhận lương hưu tiền mặt sang tài khoản ngân hàng.",
        "expected_procedure_code": "2.000740",
        "expected_terms": ["đổi hình thức nhận", "lương hưu"],
    },
    {
        "id": "intake-retirement-07",
        "user_need": "Người thân tôi là cán bộ xã, nay muốn làm thủ tục hưởng lương hưu hàng tháng.",
        "expected_procedure_code": "2.000605",
        "expected_terms": ["cán bộ xã", "hưởng lương hưu hàng tháng"],
    },
    {
        "id": "intake-retirement-08",
        "user_need": "Tôi là người cao tuổi không có lương hưu, muốn làm trợ cấp hưu trí xã hội.",
        "expected_procedure_code": "1.014027",
        "expected_terms": ["trợ cấp hưu trí xã hội", "không có lương hưu"],
    },
]

SUBMISSION_CASES = [
    {
        "id": "submission-retirement-voluntary-missing-contact",
        "procedure_code": "1.002179",
        "submission": {
            "applicant": {"full_name": "Nguyễn Văn A", "identity_number": "12345X"},
            "participation_plan": "",
            "contact_address": "",
        },
        "expected_rule_ids": [
            "identity-number-format",
            "missing-participation-plan",
            "missing-contact-address",
        ],
    },
    {
        "id": "submission-retirement-service-years-missing-period",
        "procedure_code": "1.014181",
        "submission": {
            "applicant": {"full_name": "Trần Thị B", "identity_number": "012345678901"},
            "work_period_documents_present": False,
            "requested_period_explanation": "",
        },
        "expected_rule_ids": [
            "missing-work-period-documents",
            "missing-requested-period-explanation",
        ],
    },
    {
        "id": "submission-retirement-one-time-missing-choice",
        "procedure_code": "1.014183",
        "submission": {
            "applicant": {"full_name": "Lê Văn C", "identity_number": "012345678901"},
            "retirement_eligibility_review_present": False,
            "selected_benefit_option": "",
        },
        "expected_rule_ids": [
            "missing-retirement-eligibility-review",
            "missing-selected-benefit-option",
        ],
    },
    {
        "id": "submission-retirement-pension-missing-book",
        "procedure_code": "1.014171",
        "submission": {
            "applicant": {"full_name": "Phạm Thị D", "identity_number": "012345678901"},
            "social_insurance_book_present": False,
            "retirement_decision_present": False,
        },
        "expected_rule_ids": [
            "missing-social-insurance-book",
            "missing-retirement-decision",
        ],
    },
    {
        "id": "submission-retirement-transfer-missing-destination",
        "procedure_code": "1.001742",
        "submission": {
            "beneficiary": {"full_name": "Hoàng Văn E", "identity_number": "012345678901"},
            "current_receiving_location": "",
            "target_receiving_location": "",
        },
        "expected_rule_ids": [
            "missing-current-receiving-location",
            "missing-target-receiving-location",
        ],
    },
    {
        "id": "submission-retirement-social-allowance-missing-age-proof",
        "procedure_code": "1.014027",
        "submission": {
            "applicant": {"full_name": "Vũ Thị F", "identity_number": "012345678901"},
            "age_proof_present": False,
            "no_pension_confirmation_present": False,
        },
        "expected_rule_ids": [
            "missing-age-proof",
            "missing-no-pension-confirmation",
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
            document_groups.append({"group_name": current_subsection, "documents": table_rows})
            continue
        sections[current_section].append(line)
        i += 1

    method_rows: list[dict[str, str]] = []
    for idx, line in enumerate(sections.get("Cách thức thực hiện", [])):
        if line.strip().startswith("|"):
            method_rows, _ = parse_markdown_table(sections["Cách thức thực hiện"], idx)
            break

    return {
        "overview": extract_first_meaningful_paragraph("\n".join(sections.get("Trình tự thực hiện", []))),
        "procedure_flow": compact_text("\n".join(sections.get("Trình tự thực hiện", []))),
        "requirements": compact_text("\n".join(sections.get("Yêu cầu, điều kiện thực hiện", []))),
        "methods": method_rows,
        "document_groups": document_groups,
        "result_items": [
            compact_text(line.lstrip("*").strip())
            for line in sections.get("Kết quả xử lý", [])
            if compact_text(line.lstrip("*").strip())
        ],
    }


def powershell_json(command: str) -> Any:
    wrapped = "$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); " + command
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", wrapped],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def fetch_rows_by_codes(codes: list[str]) -> list[dict[str, str]]:
    quoted_codes = ",".join(f"'{code}'" for code in codes)
    command = (
        f"Import-Csv '{FULL_DATA_CSV}' "
        f"| Where-Object {{ $_.'Mã số' -in @({quoted_codes}) }} "
        "| Select-Object 'Mã số','Tên','Cơ quan thực hiện','Lĩnh vực','URL' "
        "| ConvertTo-Json -Depth 3 -Compress"
    )
    rows = powershell_json(command)
    if isinstance(rows, dict):
        rows = [rows]
    return rows


def classify_operation(title: str, subdomain_key: str) -> tuple[str, str]:
    slug = slugify(title)
    if subdomain_key == "chuan_bi_nghi_huu":
        if "dang_ky_tham_gia_bao_hiem_xa_hoi" in slug:
            return "dang_ky_tham_gia_bhxh", slug
        if "bhxh_tu_nguyen" in slug or "dong_bhxh_tu_nguyen" in slug:
            return "tham_gia_bhxh_tu_nguyen", slug
        if "dieu_chinh_thong_tin" in slug:
            return "dieu_chinh_thong_tin_bhxh", slug
        if "tinh_thoi_gian_cong_tac" in slug:
            return "ra_soat_thoi_gian_dong_bhxh", slug
        if "khong_du_dieu_kien_huong_luong_huu" in slug:
            return "xu_ly_chua_du_dieu_kien_huu", slug
        if "bao_hiem_xa_hoi_mot_lan" in slug:
            return "huong_bhxh_mot_lan", slug
        if "benh_nghe_nghiep" in slug:
            return "ho_so_benh_nghe_nghiep_sau_nghi_huu", slug
        if "co_yeu" in slug:
            return "cong_nhan_tuoi_nghe_dac_thu", slug
        return "xac_nhan_dieu_kien_nghi_huu", slug
    if "bhxh_tu_nguyen" in slug:
        return "huong_luong_huu_bhxh_tu_nguyen", slug
    if "huong_luong_huu" in slug:
        return "huong_luong_huu", slug
    if "chuyen_huong" in slug:
        return "chuyen_noi_huong_huu", slug
    if "thay_doi_hinh_thuc_nhan" in slug or "thay_doi_thong_tin_ca_nhan" in slug:
        return "thay_doi_cach_nhan_huu", slug
    if "tiep_tuc_huong" in slug:
        return "tiep_tuc_huong_huu", slug
    if "ra_nuoc_ngoai_de_dinh_cu" in slug:
        return "nhan_tro_cap_khi_dinh_cu_nuoc_ngoai", slug
    if "tru_cap_huu_tri_xa_hoi" in slug:
        return "huong_tro_cap_huu_tri_xa_hoi", slug
    if "nguoi_cao_tuoi" in slug:
        return "ho_tro_nguoi_cao_tuoi_khong_luong_huu", slug
    if "can_bo_xa" in slug:
        return "huong_huu_can_bo_xa", slug
    if "nha_giao" in slug:
        return "phu_cap_tham_nien_nha_giao_nghi_huu", slug
    if "quyet_dinh_so_613" in slug:
        return "tro_cap_hang_thang_theo_qd_613", slug
    if "quan_nhan" in slug or "phuc_vien" in slug or "xuat_ngu" in slug:
        return "huu_tri_quan_nhan", slug
    if "dieu_chinh_huy_quyet_dinh_cham_dut_huong" in slug:
        return "dieu_chinh_ho_so_huong_huu", slug
    return "che_do_huu_tri_khac", slug


def ensure_dirs() -> None:
    WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)
    TESTS_DIR.mkdir(parents=True, exist_ok=True)


def build_records() -> list[dict[str, Any]]:
    code_to_subdomain = {
        code: subdomain_key
        for subdomain_key, meta in SUBDOMAINS.items()
        for code in meta["codes"]
    }
    rows = fetch_rows_by_codes(list(code_to_subdomain))
    records: list[dict[str, Any]] = []
    for row in rows:
        code = row["Mã số"]
        subdomain_key = code_to_subdomain[code]
        raw_file = RAW_DATA_DIR / code.replace(".", "_") / f"{code.replace('.', '_')}_procedure_detail.md"
        parsed = parse_raw_markdown(raw_file) if raw_file.exists() else {
            "overview": "",
            "procedure_flow": "",
            "requirements": "",
            "methods": [],
            "document_groups": [],
            "result_items": [],
        }
        operation_group, operation_key = classify_operation(row["Tên"], subdomain_key)
        records.append(
            {
                "procedure_code": code,
                "procedure_title": row["Tên"],
                "subdomain_key": subdomain_key,
                "subdomain_label": SUBDOMAINS[subdomain_key]["label"],
                "event_id": SUBDOMAINS[subdomain_key]["event_id"],
                "field": row.get("Lĩnh vực", ""),
                "agency": compact_text(row.get("Cơ quan thực hiện", "")),
                "source_url": row.get("URL", ""),
                "raw_data_file": str(raw_file),
                "raw_data_available": raw_file.exists(),
                "operation_group": operation_group,
                "operation_key": operation_key,
                "overview": parsed["overview"],
                "procedure_flow": parsed["procedure_flow"],
                "requirements": parsed["requirements"],
                "submission_methods": [
                    compact_text(item.get("Hình thức nộp", ""))
                    for item in parsed["methods"]
                    if compact_text(item.get("Hình thức nộp", ""))
                ],
                "processing_time_values": [
                    compact_text(item.get("Thời gian giải quyết", ""))
                    for item in parsed["methods"]
                    if compact_text(item.get("Thời gian giải quyết", ""))
                ],
                "document_groups": parsed["document_groups"],
                "result_items": parsed["result_items"],
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
                "field",
                "operation_group",
                "operation_key",
                "agency",
                "submission_methods",
                "processing_time_values",
                "document_group_count",
                "result_count",
                "raw_data_available",
                "source_url",
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
                    "field": item["field"],
                    "operation_group": item["operation_group"],
                    "operation_key": item["operation_key"],
                    "agency": item["agency"],
                    "submission_methods": " | ".join(item["submission_methods"]),
                    "processing_time_values": " | ".join(item["processing_time_values"]),
                    "document_group_count": len(item["document_groups"]),
                    "result_count": len(item["result_items"]),
                    "raw_data_available": item["raw_data_available"],
                    "source_url": item["source_url"],
                }
            )
    return path


def write_normalized(records: list[dict[str, Any]]) -> Path:
    grouped = {}
    for subdomain_key, meta in SUBDOMAINS.items():
        grouped[subdomain_key] = {
            "subdomain_key": subdomain_key,
            "subdomain_label": meta["label"],
            "event_id": meta["event_id"],
            "summary": meta["summary"],
            "entry_prompts": meta["entry_prompts"],
            "procedure_count": 0,
            "procedures": [],
        }
    for item in records:
        grouped[item["subdomain_key"]]["procedure_count"] += 1
        grouped[item["subdomain_key"]]["procedures"].append(item)
    payload = {
        "schema_version": "1.0",
        "domain": DOMAIN_KEY,
        "updated_at": UPDATED_AT,
        "source_files": [str(FULL_DATA_CSV), str(RAW_DATA_DIR)],
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
    return {
        "start_node": "retirement_subdomain",
        "nodes": [
            {
                "id": "retirement_subdomain",
                "type": "question",
                "slot": "subdomain_key",
                "question": "Bạn đang chuẩn bị nghỉ hưu hay đang làm thủ tục hưởng, điều chỉnh chế độ hưu trí?",
                "options": list(SUBDOMAINS.keys()),
            },
            {
                "id": "retirement_operation",
                "type": "question",
                "slot": "operation_key",
                "question": "Bạn cần thao tác nào cụ thể trong nhánh đã chọn?",
                "options_by_subdomain": {
                    key: [
                        {
                            "operation_key": item["operation_key"],
                            "operation_group": item["operation_group"],
                            "procedure_code": item["procedure_code"],
                            "procedure_title": item["procedure_title"],
                        }
                        for item in value
                    ]
                    for key, value in grouped_operations.items()
                },
            },
        ],
        "routes": routes,
    }


def write_workflow_config(records: list[dict[str, Any]], summary_path: Path, normalized_path: Path) -> Path:
    payload = {
        "schema_version": "1.0",
        "domain": DOMAIN_KEY,
        "updated_at": UPDATED_AT,
        "source_files": [str(FULL_DATA_CSV), str(summary_path), str(normalized_path), str(RAW_DATA_DIR)],
        "coverage": {
            "expected_codes": [item["procedure_code"] for item in records],
            "covered_codes": [item["procedure_code"] for item in records if item["raw_data_available"]],
            "missing_codes": [item["procedure_code"] for item in records if not item["raw_data_available"]],
        },
        "llm_contract": {
            "role": "parse_user_answer_and_rephrase_question_only",
            "required_output_schema": {
                "intent": DOMAIN_KEY,
                "current_node": "string",
                "slot_updates": {
                    "subdomain_key": "chuan_bi_nghi_huu | che_do_huu_tri | unknown",
                    "operation_key": "string",
                    "operation_group": "string",
                },
                "confidence": "0_to_1",
                "needs_human_review": "boolean",
            },
        },
        "entry_prompts": [
            "Bạn đang hỏi về chuẩn bị hồ sơ nghỉ hưu hay đang hưởng lương hưu, trợ cấp hưu trí?",
            "Bạn muốn tham gia BHXH để chuẩn bị nghỉ hưu, xin hưởng lương hưu, chuyển nơi nhận hay điều chỉnh cách nhận chế độ?",
        ],
        "slots": [
            {
                "name": "subdomain_key",
                "required": True,
                "description": "Nhánh chính của nhóm Hưu trí.",
            },
            {
                "name": "operation_key",
                "required": True,
                "description": "Thao tác cụ thể ánh xạ trực tiếp tới thủ tục cuối cùng.",
            },
            {
                "name": "operation_group",
                "required": False,
                "description": "Nhóm thao tác để gom các thủ tục gần nhau cho UI và parser.",
            },
        ],
        "subdomain_catalog": [
            {
                "subdomain_key": key,
                "subdomain_label": meta["label"],
                "event_id": meta["event_id"],
                "summary": meta["summary"],
            }
            for key, meta in SUBDOMAINS.items()
        ],
        "decision_tree": build_decision_tree(records),
        "pre_submission_checks": [
            {
                "field_group": "retirement_preparation",
                "checks": [
                    "Nhánh chuẩn bị nghỉ hưu phải làm rõ người dùng đang tham gia BHXH bắt buộc hay tự nguyện, cần bổ sung thời gian đóng hay rà lại điều kiện hưởng.",
                    "Nếu người dùng chưa đủ điều kiện hưởng lương hưu thì cần phân biệt rõ giữa phương án hưởng BHXH một lần và các chế độ chuyển tiếp hoặc hỗ trợ khác.",
                ],
            },
            {
                "field_group": "retirement_benefit",
                "checks": [
                    "Nhánh chế độ hưu trí phải xác định rõ đây là hưởng mới, tiếp tục hưởng, chuyển nơi nhận, đổi hình thức nhận hay điều chỉnh hồ sơ đang hưởng.",
                    "Các thủ tục trợ cấp hưu trí xã hội cần kiểm tra điều kiện không có lương hưu, độ tuổi và xác nhận về tình trạng hưởng trợ cấp hằng tháng hiện tại.",
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


def build_mapping_row(item: dict[str, Any], in_json: bool) -> dict[str, Any]:
    return {
        "persona": "citizen",
        "group_key": DOMAIN_KEY,
        "procedure_code": item["procedure_code"],
        "procedure_title": item["procedure_title"],
        "workflow_family": WORKFLOW_FAMILY,
        "support_level": "workflow_ready",
        "raw_data_available": item["raw_data_available"] if in_json else str(item["raw_data_available"]).lower(),
        "in_full_data": True if in_json else "true",
        "in_workflow_dataset": True if in_json else "true",
        "official_membership": False if in_json else "false",
        "expanded_membership": True if in_json else "true",
        "membership_source": "expanded",
        "field": item["field"],
        "source_url": item["source_url"],
        "notes": f"workflow_generated:{DOMAIN_KEY}/{item['subdomain_key']}",
    }


def update_mapping(records: list[dict[str, Any]]) -> None:
    workflow_codes = {item["procedure_code"]: item for item in records}
    with MAPPING_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
        csv_fields = list(csv_rows[0].keys())
    csv_existing_codes = {row.get("procedure_code", "") for row in csv_rows if row.get("group_key") == DOMAIN_KEY}
    for row in csv_rows:
        if row.get("group_key") != DOMAIN_KEY:
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
    for code, item in workflow_codes.items():
        if code not in csv_existing_codes:
            csv_rows.append(build_mapping_row(item, in_json=False))
    with MAPPING_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(csv_rows)

    json_rows = json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
    json_existing_codes = {row.get("procedure_code", "") for row in json_rows if row.get("group_key") == DOMAIN_KEY}
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
    for code, item in workflow_codes.items():
        if code not in json_existing_codes:
            json_rows.append(build_mapping_row(item, in_json=True))
    MAPPING_JSON.write_text(json.dumps(json_rows, ensure_ascii=False, indent=2), encoding="utf-8")


def update_checklist() -> None:
    text = CHECKLIST_DOC.read_text(encoding="utf-8")
    marker = "  - `suc_khoe_y_te` (da co workflow dataset va test data cho 9 ma thu tuc / 2 subdomain)\n"
    addition = "  - `huu_tri` (da co workflow dataset va test data cho 28 ma thu tuc / 2 subdomain)\n"
    if addition not in text and marker in text:
        text = text.replace(marker, marker + addition, 1)
    next_marker = "1. Mo rong cach lam nay sang `huu_tri`\n"
    if next_marker in text:
        text = text.replace(next_marker, "1. Mo rong cach lam nay sang `giai_quyet_khieu_kien`\n", 1)
    CHECKLIST_DOC.write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    records = build_records()
    summary_path = write_summary(records)
    normalized_path = write_normalized(records)
    config_path = write_workflow_config(records, summary_path, normalized_path)
    materialize_subdomain_outputs(WORKFLOW_DIR, summary_path, normalized_path, config_path)
    intake_path, submission_path = write_test_cases(records)
    update_mapping(records)
    update_checklist()
    print(
        json.dumps(
            {
                "domain": DOMAIN_KEY,
                "procedure_count": len(records),
                "subdomains": {
                    key: sum(1 for item in records if item["subdomain_key"] == key)
                    for key in SUBDOMAINS
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
