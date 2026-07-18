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
WORKFLOW_DIR = ROOT / "data" / "workflows" / "nguoi_than_qua_doi"
TESTS_DIR = ROOT / "tests" / "workflows" / "nguoi_than_qua_doi"
MAPPING_CSV = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.csv"
MAPPING_JSON = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.json"
CHECKLIST_DOC = ROOT / "govease-unified" / "docs" / "codex-workstream-checklist.md"

DOMAIN_KEY = "nguoi_than_qua_doi"
WORKFLOW_FAMILY = "death_family_support_workflow"
UPDATED_AT = str(date.today())

SUBDOMAINS = {
    "khai_tu": {
        "label": "Khai tử",
        "event_id": 320,
        "summary": "Nhóm thủ tục đăng ký khai tử, đăng ký lại khai tử và ghi chú việc khai tử đã được giải quyết ở nước ngoài.",
        "codes": [
            "1.000419",
            "1.000656",
            "1.001766",
            "1.004827",
            "1.005461",
            "2.000497",
            "2.000527",
            "2.000547",
            "2.000702",
        ],
        "entry_prompts": [
            "Bạn đang cần đăng ký khai tử, đăng ký lại khai tử hay ghi chú việc khai tử đã được giải quyết ở nước ngoài?",
            "Trường hợp này là trong nước, có yếu tố nước ngoài, khu vực biên giới hay công dân Việt Nam ở nước ngoài?",
        ],
    },
    "che_do_tu_tuat_mai_tang_phi": {
        "label": "Chế độ tử tuất, mai táng phí",
        "event_id": 321,
        "summary": "Nhóm thủ tục hưởng chế độ tử tuất, trợ cấp mai táng và hỗ trợ chi phí mai táng cho thân nhân người đã mất.",
        "codes": [
            "1.001731",
            "1.010456",
            "1.014028",
            "1.014177",
            "1.014359",
            "2.000821",
            "2.002307",
            "2.002308",
            "2.002862",
        ],
        "entry_prompts": [
            "Bạn đang cần hưởng trợ cấp tử tuất, trợ cấp mai táng hay hỗ trợ chi phí mai táng?",
            "Người đã mất thuộc nhóm bảo hiểm xã hội, bảo trợ xã hội, người có công hay chính sách địa phương đặc thù?",
        ],
    },
}

INTAKE_CASES = [
    {
        "id": "intake-death-01",
        "user_need": "Gia đình tôi cần đăng ký khai tử cho người thân vừa mất.",
        "expected_procedure_code": "1.000656",
        "expected_terms": ["đăng ký khai tử"],
    },
    {
        "id": "intake-death-02",
        "user_need": "Tôi cần đăng ký lại khai tử vì giấy tờ cũ bị mất.",
        "expected_procedure_code": "1.005461",
        "expected_terms": ["đăng ký lại khai tử"],
    },
    {
        "id": "intake-death-03",
        "user_need": "Người thân mất ở nước ngoài, tôi cần ghi chú lại vào sổ hộ tịch Việt Nam.",
        "expected_procedure_code": "2.000547",
        "expected_terms": ["ghi vào sổ hộ tịch", "khai tử"],
    },
    {
        "id": "intake-death-04",
        "user_need": "Tôi muốn làm thủ tục hưởng chế độ tử tuất cho thân nhân.",
        "expected_procedure_code": "2.000821",
        "expected_terms": ["chế độ tử tuất"],
    },
    {
        "id": "intake-death-05",
        "user_need": "Gia đình tôi cần nhận trợ cấp mai táng từ bảo hiểm xã hội.",
        "expected_procedure_code": "1.014177",
        "expected_terms": ["trợ cấp mai táng", "bảo hiểm xã hội"],
    },
    {
        "id": "intake-death-06",
        "user_need": "Tôi cần hỗ trợ chi phí mai táng cho đối tượng bảo trợ xã hội.",
        "expected_procedure_code": "1.001731",
        "expected_terms": ["hỗ trợ chi phí mai táng", "bảo trợ xã hội"],
    },
]

SUBMISSION_CASES = [
    {
        "id": "submission-death-registration-missing-certificate",
        "procedure_code": "1.000656",
        "submission": {
            "declarant": {"full_name": "Nguyễn Văn A", "identity_number": "12345X"},
            "deceased": {"full_name": "Trần Thị B"},
            "death_notice_present": False,
        },
        "expected_rule_ids": [
            "identity-number-format",
            "missing-death-notice",
        ],
    },
    {
        "id": "submission-death-reregistration-missing-record",
        "procedure_code": "1.005461",
        "submission": {
            "requester": {"full_name": "Phạm Văn C", "identity_number": "012345678901"},
            "old_registration_information_present": False,
            "reason_for_reregistration": "",
        },
        "expected_rule_ids": [
            "missing-old-death-registration-information",
            "missing-reregistration-reason",
        ],
    },
    {
        "id": "submission-death-foreign-note-missing-proof",
        "procedure_code": "2.000547",
        "submission": {
            "requester": {"full_name": "Lê Thị D", "identity_number": "012345678901"},
            "foreign_death_record_present": False,
            "translation_present": False,
        },
        "expected_rule_ids": [
            "missing-foreign-death-record",
            "missing-certified-translation",
        ],
    },
    {
        "id": "submission-death-survivor-benefit-missing-relation",
        "procedure_code": "2.000821",
        "submission": {
            "claimant": {"full_name": "Hoàng Văn E", "identity_number": "012345678901"},
            "deceased_insurance_record_present": True,
            "relationship_proof_present": False,
        },
        "expected_rule_ids": [
            "missing-relationship-proof",
        ],
    },
    {
        "id": "submission-death-funeral-support-missing-payment-doc",
        "procedure_code": "1.014177",
        "submission": {
            "claimant": {"full_name": "Vũ Thị F", "identity_number": "012345678901"},
            "death_certificate_present": True,
            "funeral_expense_documents_present": False,
        },
        "expected_rule_ids": [
            "missing-funeral-expense-documents",
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
    if subdomain_key == "khai_tu":
        if "dang_ky_lai_khai_tu" in slug:
            return "dang_ky_lai_khai_tu", slug
        if "ghi_vao_so_ho_tich" in slug or "ghi_vao_so_ho_tich_cac_viec_ho_tich" in slug:
            return "ghi_chu_khai_tu", slug
        if "luu_dong" in slug:
            return "khai_tu_luu_dong", slug
        if "bien_gioi" in slug:
            return "khai_tu_bien_gioi", slug
        if "co_yeu_to_nuoc_ngoai" in slug:
            return "khai_tu_co_yeu_to_nuoc_ngoai", slug
        if "o_nuoc_ngoai" in slug:
            return "khai_tu_cho_cong_dan_vn_o_nuoc_ngoai", slug
        return "dang_ky_khai_tu", slug
    if "tu_tuat" in slug:
        return "che_do_tu_tuat", slug
    if "bao_hiem_xa_hoi" in slug or "tro_cap_mai_tang" in slug:
        return "tro_cap_mai_tang_bhxh", slug
    if "bao_tro_xa_hoi" in slug or "huu_tri_xa_hoi" in slug:
        return "ho_tro_mai_tang_bao_tro_xa_hoi", slug
    if "cuu_chien_binh" in slug:
        return "mai_tang_phi_cuu_chien_binh", slug
    if "thanh_nien_xung_phong" in slug:
        return "mai_tang_phi_thanh_nien_xung_phong", slug
    if "dan_cong_hoa_tuyen" in slug:
        return "mai_tang_phi_dan_cong_hoa_tuyen", slug
    if "dan_toc_thieu_so" in slug:
        return "ho_tro_mai_tang_dia_phuong", slug
    return "mai_tang_phi_khac", slug


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
        "start_node": "death_subdomain",
        "nodes": [
            {
                "id": "death_subdomain",
                "type": "question",
                "slot": "subdomain_key",
                "question": "Bạn đang hỏi về khai tử hay chế độ tử tuất, mai táng phí?",
                "options": list(SUBDOMAINS.keys()),
            },
            {
                "id": "death_operation",
                "type": "question",
                "slot": "operation_key",
                "question": "Bạn cần làm thao tác nào cụ thể trong nhánh đã chọn?",
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
                    "subdomain_key": "khai_tu | che_do_tu_tuat_mai_tang_phi | unknown",
                    "operation_key": "string",
                    "operation_group": "string",
                },
                "confidence": "0_to_1",
                "needs_human_review": "boolean",
            },
        },
        "entry_prompts": [
            "Bạn đang cần làm khai tử cho người thân hay xin chế độ tử tuất, mai táng phí?",
            "Bạn muốn đăng ký mới, đăng ký lại, ghi chú khai tử hay xin trợ cấp hỗ trợ sau khi người thân qua đời?",
        ],
        "slots": [
            {
                "name": "subdomain_key",
                "required": True,
                "description": "Nhánh chính của nhóm Người thân qua đời.",
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
                "field_group": "death_registration",
                "checks": [
                    "Nhóm khai tử phải xác định rõ nơi người mất qua đời, nơi cư trú và loại giấy tờ xác nhận việc tử vong.",
                    "Các trường hợp có yếu tố nước ngoài phải kiểm tra đủ giấy tờ nước ngoài và bản dịch/chứng thực kèm theo.",
                ],
            },
            {
                "field_group": "survivor_support",
                "checks": [
                    "Nhóm tử tuất và mai táng phí phải xác định rõ người đã mất thuộc chế độ BHXH, bảo trợ xã hội, người có công hay chính sách địa phương.",
                    "Thân nhân đứng đơn cần có căn cứ chứng minh quan hệ với người đã mất và chứng từ liên quan đến việc mai táng nếu thủ tục yêu cầu.",
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


def update_checklist(records: list[dict[str, Any]]) -> None:
    text = CHECKLIST_DOC.read_text(encoding="utf-8")
    marker = "  - `nguoi_than_qua_doi`\n"
    replacement = "  - `nguoi_than_qua_doi` (da co workflow dataset va test data cho 18 ma thu tuc / 2 subdomain)\n"
    if marker in text:
        text = text.replace(marker, replacement, 1)
    next_marker = "1. Mo rong cach lam nay sang `nguoi_than_qua_doi`\n"
    if next_marker in text:
        text = text.replace(next_marker, "1. Mo rong cach lam nay sang domain Cong dan tiep theo uu tien cao\n", 1)
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
    update_checklist(records)
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
