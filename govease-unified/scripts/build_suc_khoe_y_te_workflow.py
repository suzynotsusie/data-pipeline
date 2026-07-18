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
WORKFLOW_DIR = ROOT / "data" / "workflows" / "suc_khoe_y_te"
TESTS_DIR = ROOT / "tests" / "workflows" / "suc_khoe_y_te"
MAPPING_CSV = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.csv"
MAPPING_JSON = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.json"
CHECKLIST_DOC = ROOT / "govease-unified" / "docs" / "codex-workstream-checklist.md"

DOMAIN_KEY = "suc_khoe_y_te"
WORKFLOW_FAMILY = "healthcare_medical_policy_workflow"
UPDATED_AT = str(date.today())

SUBDOMAINS = {
    "kham_chua_benh": {
        "label": "Khám, chữa bệnh",
        "event_id": 312,
        "summary": "Nhóm thủ tục chi trả trực tiếp chi phí khám, chữa bệnh bảo hiểm y tế và xác nhận không cùng chi trả trong năm cho người dân đi khám chữa bệnh.",
        "codes": [
            "1.001656",
        ],
        "entry_prompts": [
            "Bạn đang cần thanh toán trực tiếp chi phí khám chữa bệnh BHYT hay xin giấy chứng nhận không cùng chi trả trong năm?",
        ],
    },
    "chinh_sach_y_te": {
        "label": "Chính sách y tế",
        "event_id": 314,
        "summary": "Nhóm thủ tục liên quan đến tham gia BHYT, điều chỉnh thông tin sổ BHXH/thẻ BHYT và hưởng các chế độ ốm đau, thai sản, tai nạn lao động, bệnh nghề nghiệp, dưỡng sức phục hồi sức khỏe.",
        "codes": [
            "1.002759",
            "1.001939",
            "1.001667",
            "2.000693",
            "1.001598",
            "1.001521",
            "1.001632",
            "1.001643",
        ],
        "entry_prompts": [
            "Bạn muốn tham gia hoặc điều chỉnh thẻ BHYT/sổ BHXH, hay đang làm hồ sơ hưởng chế độ ốm đau, thai sản, tai nạn lao động, bệnh nghề nghiệp?",
        ],
    },
}

INTAKE_CASES = [
    {
        "id": "intake-health-01",
        "user_need": "Tôi muốn thanh toán trực tiếp chi phí khám chữa bệnh BHYT.",
        "expected_procedure_code": "1.001656",
        "expected_terms": ["khám chữa bệnh bhyt", "thanh toán trực tiếp"],
    },
    {
        "id": "intake-health-02",
        "user_need": "Tôi muốn đăng ký đóng và cấp thẻ BHYT cho người chỉ tham gia BHYT.",
        "expected_procedure_code": "1.001939",
        "expected_terms": ["đóng bhyt", "cấp thẻ bhyt"],
    },
    {
        "id": "intake-health-03",
        "user_need": "Tôi cần đổi lại thông tin trên thẻ BHYT.",
        "expected_procedure_code": "1.002759",
        "expected_terms": ["đổi thông tin", "thẻ bhyt"],
    },
    {
        "id": "intake-health-04",
        "user_need": "Tôi muốn làm hồ sơ hưởng chế độ ốm đau.",
        "expected_procedure_code": "1.001667",
        "expected_terms": ["chế độ ốm đau"],
    },
    {
        "id": "intake-health-05",
        "user_need": "Tôi muốn giải quyết hưởng chế độ thai sản.",
        "expected_procedure_code": "2.000693",
        "expected_terms": ["chế độ thai sản"],
    },
    {
        "id": "intake-health-06",
        "user_need": "Tôi cần làm chế độ tai nạn lao động lần đầu.",
        "expected_procedure_code": "1.001632",
        "expected_terms": ["tai nạn lao động", "lần đầu"],
    },
]

SUBMISSION_CASES = [
    {
        "id": "submission-bhyt-payment-missing-invoice",
        "procedure_code": "1.001656",
        "submission": {
            "patient": {"full_name": "Nguyễn Thị A", "insurance_number": "TE1234567890"},
            "hospital_invoice_present": False,
            "treatment_documents_present": False,
            "year_of_treatment": "",
        },
        "expected_rule_ids": [
            "missing-hospital-invoice",
            "missing-treatment-documents",
            "missing-year-of-treatment",
        ],
    },
    {
        "id": "submission-bhyt-registration-missing-identity",
        "procedure_code": "1.001939",
        "submission": {
            "applicant": {"full_name": "Trần Văn B", "identity_number": ""},
            "participation_group": "",
            "payment_proof_present": False,
        },
        "expected_rule_ids": [
            "missing-identity-number",
            "missing-participation-group",
            "missing-payment-proof",
        ],
    },
    {
        "id": "submission-sick-benefit-missing-medical-leave",
        "procedure_code": "1.001667",
        "submission": {
            "employee": {"full_name": "Lê Thị C", "social_insurance_number": ""},
            "medical_leave_certificate_present": False,
            "leave_period": "",
        },
        "expected_rule_ids": [
            "missing-social-insurance-number",
            "missing-medical-leave-certificate",
            "missing-leave-period",
        ],
    },
    {
        "id": "submission-maternity-benefit-missing-child-info",
        "procedure_code": "2.000693",
        "submission": {
            "beneficiary": {"full_name": "Phạm Thị D", "social_insurance_number": "1234567890"},
            "child_birth_information_present": False,
            "benefit_reason": "",
        },
        "expected_rule_ids": [
            "missing-child-birth-information",
            "missing-benefit-reason",
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
    if subdomain_key == "kham_chua_benh":
        return "chi_tra_bhyt_kham_chua_benh", slug
    if "the_bhyt" in slug or "so_bhxh" in slug or "dieu_chinh_thong_tin" in slug:
        return "dieu_chinh_so_bhxh_the_bhyt", slug
    if "chi_tham_gia_bhyt" in slug or "cap_the_bhyt" in slug:
        return "tham_gia_bhyt_tu_nguyen", slug
    if "thai_san" in slug:
        return "huong_che_do_thai_san", slug
    if "om_dau" in slug:
        return "huong_che_do_om_dau", slug
    if "dsphsk" in slug:
        return "huong_duong_suc_phuc_hoi", slug
    if "lan_dau" in slug:
        return "huong_tnld_bnn_lan_dau", slug
    if "tai_phat" in slug or "thuong_tat_benh_tat_tai_phat" in slug:
        return "huong_tnld_bnn_tai_phat", slug
    return "huong_tnld_bnn_tiep_tuc", slug


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
        "start_node": "healthcare_subdomain",
        "nodes": [
            {
                "id": "healthcare_subdomain",
                "type": "question",
                "slot": "subdomain_key",
                "question": "Bạn đang cần thanh toán chi phí khám chữa bệnh BHYT hay làm hồ sơ về thẻ BHYT, sổ BHXH và các chế độ y tế?",
                "options": list(SUBDOMAINS.keys()),
            },
            {
                "id": "healthcare_operation",
                "type": "question",
                "slot": "operation_key",
                "question": "Trong nhánh đã chọn, bạn đang cần xử lý việc gì cụ thể?",
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
                    "subdomain_key": "kham_chua_benh | chinh_sach_y_te | unknown",
                    "operation_key": "string",
                    "operation_group": "string",
                },
                "confidence": "0_to_1",
                "needs_human_review": "boolean",
            },
        },
        "entry_prompts": [
            "Bạn đang cần thanh toán chi phí khám chữa bệnh BHYT hay làm thủ tục thẻ BHYT, sổ BHXH và các chế độ sức khỏe?",
            "Bạn muốn tham gia BHYT, đổi thông tin thẻ, hay nộp hồ sơ hưởng ốm đau, thai sản, tai nạn lao động?",
        ],
        "slots": [
            {
                "name": "subdomain_key",
                "required": True,
                "description": "Nhánh chính của nhóm Sức khỏe và y tế.",
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
                "field_group": "bhyt_medical_payment",
                "checks": [
                    "Nhóm khám chữa bệnh cần làm rõ người dân đang xin thanh toán trực tiếp chi phí khám chữa bệnh BHYT hay xin giấy chứng nhận không cùng chi trả trong năm.",
                    "Cần kiểm tra đầy đủ chứng từ khám chữa bệnh, hóa đơn, thời điểm điều trị và thông tin thẻ BHYT trước khi nhận hồ sơ.",
                ],
            },
            {
                "field_group": "insurance_and_benefits",
                "checks": [
                    "Nhóm chính sách y tế phải phân biệt rõ thủ tục tham gia BHYT, điều chỉnh sổ BHXH/thẻ BHYT và các chế độ ốm đau, thai sản, TNLĐ, BNN, dưỡng sức phục hồi sức khỏe.",
                    "Hồ sơ chế độ cần có số BHXH, căn cứ phát sinh quyền lợi và giấy tờ chuyên môn hoặc giấy tờ xác nhận tình trạng tương ứng với từng chế độ.",
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
        "official_membership": True if in_json else "true",
        "expanded_membership": False if in_json else "false",
        "membership_source": "official",
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
    marker = "  - `dien_luc_nha_o_dat_dai` (da co workflow dataset va test data cho 23 ma thu tuc / 6 subdomain)\n"
    addition = "  - `suc_khoe_y_te` (da co workflow dataset va test data cho 9 ma thu tuc / 2 subdomain)\n"
    if addition not in text and marker in text:
        text = text.replace(marker, marker + addition, 1)
    next_marker = "1. Mo rong cach lam nay sang `suc_khoe_y_te`\n"
    if next_marker in text:
        text = text.replace(next_marker, "1. Mo rong cach lam nay sang `huu_tri`\n", 1)
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
