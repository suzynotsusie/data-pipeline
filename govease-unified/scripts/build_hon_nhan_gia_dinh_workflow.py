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


ROOT = Path(__file__).resolve().parents[2]
FULL_DATA_CSV = ROOT / "main" / "full-data.csv"
RAW_DATA_DIR = ROOT / "raw_data"
WORKFLOW_DIR = ROOT / "data" / "workflows" / "hon_nhan_gia_dinh"
TESTS_DIR = ROOT / "tests" / "workflows" / "hon_nhan_gia_dinh"
MAPPING_CSV = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.csv"
MAPPING_JSON = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.json"
CHECKLIST_DOC = ROOT / "govease-unified" / "docs" / "codex-workstream-checklist.md"

DOMAIN_KEY = "hon_nhan_gia_dinh"
WORKFLOW_FAMILY = "marriage_family_workflow"
UPDATED_AT = str(date.today())

SUBDOMAINS = {
    "ket_hon": {
        "label": "Kết hôn",
        "event_id": 274,
        "summary": "Nhóm thủ tục đăng ký kết hôn, đăng ký lại kết hôn và ghi chú kết hôn hoặc ly hôn đã được giải quyết ở nước ngoài.",
        "codes": [
            "1.000094",
            "1.000593",
            "1.000736",
            "1.000894",
            "1.004746",
            "2.000507",
            "2.000513",
            "2.000554",
            "2.000698",
            "2.000806",
            "2.002189",
        ],
        "entry_prompts": [
            "Bạn đang muốn đăng ký kết hôn, đăng ký lại hay ghi chú việc kết hôn hoặc ly hôn đã làm ở nước ngoài?",
            "Trường hợp của bạn là trong nước, có yếu tố nước ngoài hay ở khu vực biên giới?",
        ],
    },
    "giam_ho": {
        "label": "Giám hộ",
        "event_id": 275,
        "summary": "Nhóm thủ tục đăng ký giám hộ, chấm dứt hoặc thay đổi giám hộ và giám sát việc giám hộ.",
        "codes": [
            "1.001669",
            "1.004837",
            "1.004845",
            "2.000560",
            "2.000584",
            "2.000756",
            "3.000322",
            "3.000323",
        ],
        "entry_prompts": [
            "Bạn đang cần đăng ký giám hộ, chấm dứt giám hộ hay thay đổi thông tin giám hộ?",
            "Việc giám hộ này là trong nước, có yếu tố nước ngoài hay giữa công dân Việt Nam ở nước ngoài?",
        ],
    },
    "nhan_cha_me_con": {
        "label": "Nhận cha, mẹ, con",
        "event_id": 279,
        "summary": "Nhóm thủ tục nhận cha, mẹ, con và các trường hợp kết hợp khai sinh với nhận cha, mẹ, con.",
        "codes": [
            "1.000080",
            "1.000689",
            "1.001022",
            "1.001121",
            "1.001695",
            "2.000779",
        ],
        "entry_prompts": [
            "Bạn đang làm thủ tục nhận cha, mẹ, con riêng hay kết hợp với đăng ký khai sinh?",
            "Trường hợp của bạn là trong nước, có yếu tố nước ngoài hay tại khu vực biên giới?",
        ],
    },
    "nhan_con_nuoi": {
        "label": "Nhận con nuôi",
        "event_id": 281,
        "summary": "Nhóm thủ tục nhận con nuôi trong nước, có yếu tố nước ngoài, đăng ký lại và ghi chú nuôi con nuôi.",
        "codes": [
            "1.003005",
            "1.003160",
            "1.003179",
            "1.003198",
            "1.003213",
            "1.003976",
            "1.004878",
            "2.000540",
            "2.001255",
            "2.001263",
            "2.002363",
        ],
        "entry_prompts": [
            "Bạn đang muốn nhận con nuôi trong nước, có yếu tố nước ngoài hay ghi chú/đăng ký lại việc nuôi con nuôi?",
            "Trường hợp của bạn là cá nhân nhận con nuôi, người nước ngoài nhận trẻ em Việt Nam, hay thủ tục tại cơ quan đại diện ở nước ngoài?",
        ],
    },
    "cai_chinh_trich_luc_ho_tich": {
        "label": "Cải chính, trích lục hộ tịch",
        "event_id": 286,
        "summary": "Nhóm thủ tục thay đổi, cải chính, bổ sung thông tin hộ tịch và ghi chú các việc hộ tịch đã giải quyết ở nước ngoài.",
        "codes": [
            "1.004859",
            "2.000547",
            "2.000702",
            "2.000748",
        ],
        "entry_prompts": [
            "Bạn đang cần cải chính hộ tịch hay ghi chú việc hộ tịch đã được giải quyết ở nước ngoài?",
            "Nội dung cần xử lý là thay đổi thông tin hộ tịch, xác định lại dân tộc hay ghi chú sự kiện hộ tịch khác?",
        ],
    },
}

INTAKE_CASES = [
    {
        "id": "intake-family-01",
        "user_need": "Tôi muốn đăng ký kết hôn với người nước ngoài tại Việt Nam.",
        "expected_procedure_code": "2.000806",
        "expected_terms": ["đăng ký kết hôn", "có yếu tố nước ngoài"],
    },
    {
        "id": "intake-family-02",
        "user_need": "Tôi cần ghi chú ly hôn đã được tòa án nước ngoài giải quyết.",
        "expected_procedure_code": "2.000554",
        "expected_terms": ["ghi vào sổ hộ tịch", "ly hôn"],
    },
    {
        "id": "intake-family-03",
        "user_need": "Gia đình tôi muốn đăng ký giám hộ cho cháu.",
        "expected_procedure_code": "1.004837",
        "expected_terms": ["đăng ký giám hộ"],
    },
    {
        "id": "intake-family-04",
        "user_need": "Tôi muốn chấm dứt việc giám hộ đã đăng ký trước đây.",
        "expected_procedure_code": "1.004845",
        "expected_terms": ["chấm dứt giám hộ"],
    },
    {
        "id": "intake-family-05",
        "user_need": "Tôi muốn làm thủ tục nhận cha con cho con tôi.",
        "expected_procedure_code": "1.001022",
        "expected_terms": ["nhận cha, mẹ, con"],
    },
    {
        "id": "intake-family-06",
        "user_need": "Tôi vừa sinh con và muốn khai sinh kết hợp nhận cha cho cháu.",
        "expected_procedure_code": "1.000689",
        "expected_terms": ["khai sinh kết hợp", "nhận cha, mẹ, con"],
    },
    {
        "id": "intake-family-07",
        "user_need": "Tôi muốn đăng ký nhận con nuôi trong nước.",
        "expected_procedure_code": "2.001263",
        "expected_terms": ["nuôi con nuôi trong nước"],
    },
    {
        "id": "intake-family-08",
        "user_need": "Tôi cần ghi chú việc nuôi con nuôi đã giải quyết ở nước ngoài.",
        "expected_procedure_code": "2.002363",
        "expected_terms": ["ghi vào sổ đăng ký nuôi con nuôi", "nước ngoài"],
    },
    {
        "id": "intake-family-09",
        "user_need": "Tôi muốn cải chính thông tin hộ tịch trên giấy tờ đã đăng ký.",
        "expected_procedure_code": "1.004859",
        "expected_terms": ["cải chính", "bổ sung thông tin hộ tịch"],
    },
    {
        "id": "intake-family-10",
        "user_need": "Tôi muốn ghi chú việc nhận cha con đã được giải quyết ở nước ngoài.",
        "expected_procedure_code": "2.000547",
        "expected_terms": ["ghi vào sổ hộ tịch", "nhận cha, mẹ, con"],
    },
]

SUBMISSION_CASES = [
    {
        "id": "submission-family-marriage-missing-status-proof",
        "procedure_code": "2.000806",
        "submission": {
            "applicants": [
                {"full_name": "Nguyễn Văn A", "identity_number": "012345678901"},
                {"full_name": "Jane Doe", "passport_number": ""},
            ],
            "marital_status_certificate_present": False,
            "translation_present": False,
        },
        "expected_rule_ids": [
            "missing-foreign-passport",
            "missing-marital-status-certificate",
            "missing-certified-translation",
        ],
    },
    {
        "id": "submission-family-guardianship-missing-basis",
        "procedure_code": "1.004837",
        "submission": {
            "guardian": {"full_name": "Trần Thị B", "identity_number": "12345X"},
            "ward": {"full_name": "Lê Văn C"},
            "guardianship_basis_present": False,
        },
        "expected_rule_ids": [
            "identity-number-format",
            "missing-guardianship-basis",
        ],
    },
    {
        "id": "submission-family-parent-child-missing-evidence",
        "procedure_code": "1.001022",
        "submission": {
            "claimant": {"full_name": "Phạm Văn D", "identity_number": "012345678901"},
            "child": {"full_name": "Phạm Thị E"},
            "relationship_evidence_present": False,
        },
        "expected_rule_ids": [
            "missing-parent-child-relationship-evidence",
        ],
    },
    {
        "id": "submission-family-adoption-missing-consent",
        "procedure_code": "2.001263",
        "submission": {
            "adopter": {"full_name": "Hoàng Thị F", "identity_number": "012345678901"},
            "child": {"full_name": "Nguyễn Văn G"},
            "child_consent_present": False,
            "guardian_consent_present": False,
        },
        "expected_rule_ids": [
            "missing-child-consent",
            "missing-guardian-consent",
        ],
    },
    {
        "id": "submission-family-correction-missing-original-record",
        "procedure_code": "1.004859",
        "submission": {
            "requester": {"full_name": "Lý Thị H", "identity_number": "012345678901"},
            "requested_change": "",
            "original_civil_status_record_present": False,
        },
        "expected_rule_ids": [
            "missing-requested-correction-content",
            "missing-original-civil-status-record",
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
    if subdomain_key == "ket_hon":
        if "ly_hon" in slug or "huy_viec_ket_hon" in slug:
            return "ghi_chu_ly_hon", slug
        if "dang_ky_lai_ket_hon" in slug:
            return "dang_ky_lai_ket_hon", slug
        if "ghi_vao_so_ho_tich_viec_ket_hon" in slug:
            return "ghi_chu_ket_hon", slug
        if "luu_dong" in slug:
            return "dang_ky_ket_hon_luu_dong", slug
        if "bien_gioi" in slug:
            return "ket_hon_bien_gioi", slug
        if "co_yeu_to_nuoc_ngoai" in slug:
            return "ket_hon_co_yeu_to_nuoc_ngoai", slug
        return "dang_ky_ket_hon", slug
    if subdomain_key == "giam_ho":
        if "giam_sat_viec_giam_ho" in slug:
            return "giam_sat_giam_ho", slug
        if "cham_dut" in slug or "thay_doi" in slug:
            return "cham_dut_hoac_thay_doi_giam_ho", slug
        if "co_yeu_to_nuoc_ngoai" in slug:
            return "giam_ho_co_yeu_to_nuoc_ngoai", slug
        if "cu_tru_o_nuoc_ngoai" in slug:
            return "giam_ho_giua_cong_dan_vn_o_nuoc_ngoai", slug
        return "dang_ky_giam_ho", slug
    if subdomain_key == "nhan_cha_me_con":
        if "khai_sinh_ket_hop" in slug:
            return "khai_sinh_ket_hop_nhan_cha_me_con", slug
        if "bien_gioi" in slug:
            return "nhan_cha_me_con_bien_gioi", slug
        if "co_yeu_to_nuoc_ngoai" in slug:
            return "nhan_cha_me_con_co_yeu_to_nuoc_ngoai", slug
        if "tam_tru_o_nuoc_ngoai" in slug:
            return "nhan_cha_me_con_giua_cong_dan_vn_o_nuoc_ngoai", slug
        return "nhan_cha_me_con", slug
    if subdomain_key == "nhan_con_nuoi":
        if "dang_ky_lai" in slug:
            return "dang_ky_lai_nuoi_con_nuoi", slug
        if "ghi_vao_so_dang_ky" in slug:
            return "ghi_chu_nuoi_con_nuoi", slug
        if "co_quan_dai_dien" in slug:
            return "nuoi_con_nuoi_tai_co_quan_dai_dien", slug
        if "nuoc_ngoai" in slug or "yeu_to_nuoc_ngoai" in slug:
            return "nuoi_con_nuoi_co_yeu_to_nuoc_ngoai", slug
        return "nuoi_con_nuoi_trong_nuoc", slug
    if "ghi_vao_so_ho_tich" in slug:
        return "ghi_chu_ho_tich_khac", slug
    if "co_yeu_to_nuoc_ngoai" in slug:
        return "cai_chinh_ho_tich_co_yeu_to_nuoc_ngoai", slug
    return "cai_chinh_bo_sung_ho_tich", slug


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
        "start_node": "family_subdomain",
        "nodes": [
            {
                "id": "family_subdomain",
                "type": "question",
                "slot": "subdomain_key",
                "question": "Bạn đang hỏi về kết hôn, giám hộ, nhận cha mẹ con, nhận con nuôi hay cải chính hộ tịch?",
                "options": list(SUBDOMAINS.keys()),
            },
            {
                "id": "family_operation",
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
                    "subdomain_key": "ket_hon | giam_ho | nhan_cha_me_con | nhan_con_nuoi | cai_chinh_trich_luc_ho_tich | unknown",
                    "operation_key": "string",
                    "operation_group": "string",
                },
                "confidence": "0_to_1",
                "needs_human_review": "boolean",
            },
        },
        "entry_prompts": [
            "Bạn đang cần làm việc về kết hôn, giám hộ, nhận cha mẹ con, nhận con nuôi hay cải chính hộ tịch?",
            "Bạn muốn đăng ký mới, đăng ký lại, ghi chú, chấm dứt hay điều chỉnh thông tin hộ tịch?",
        ],
        "slots": [
            {
                "name": "subdomain_key",
                "required": True,
                "description": "Nhánh chính của nhóm Hôn nhân và gia đình.",
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
                "field_group": "marital_status",
                "checks": [
                    "Thông tin nhân thân của các bên phải thống nhất giữa giấy tờ tùy thân, giấy xác nhận tình trạng hôn nhân và biểu mẫu nộp.",
                    "Các thủ tục có yếu tố nước ngoài phải làm rõ giấy tờ nước ngoài đã được hợp pháp hóa hoặc dịch chứng thực hay chưa.",
                ],
            },
            {
                "field_group": "family_relationship",
                "checks": [
                    "Nhóm nhận cha mẹ con phải có căn cứ chứng minh quan hệ và xác định rõ trường hợp kết hợp khai sinh hay không.",
                    "Nhóm giám hộ phải làm rõ căn cứ phát sinh, chấm dứt hoặc thay đổi giám hộ trước khi chọn thủ tục.",
                ],
            },
            {
                "field_group": "adoption_civil_status",
                "checks": [
                    "Nhóm nhận con nuôi phải xác định là trong nước, có yếu tố nước ngoài, đăng ký lại hay ghi chú kết quả từ nước ngoài.",
                    "Nhóm cải chính hộ tịch phải nêu rõ nội dung cần sửa đổi và hồ sơ gốc liên quan đến việc đăng ký hộ tịch ban đầu.",
                ],
            },
        ],
    }
    path = WORKFLOW_DIR / "workflow_engine_config.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_test_cases() -> tuple[Path, Path]:
    intake_path = TESTS_DIR / "intake_cases.json"
    submission_path = TESTS_DIR / "submission_cases.json"
    intake_path.write_text(json.dumps(INTAKE_CASES, ensure_ascii=False, indent=2), encoding="utf-8")
    submission_path.write_text(json.dumps(SUBMISSION_CASES, ensure_ascii=False, indent=2), encoding="utf-8")
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
    marker = "  - `hon_nhan_gia_dinh`\n"
    replacement = "  - `hon_nhan_gia_dinh` (da co workflow dataset va test data cho 40 ma thu tuc / 5 subdomain)\n"
    if marker in text:
        text = text.replace(marker, replacement, 1)
    next_marker = "1. Mo rong cach lam nay sang `hon_nhan_gia_dinh`\n"
    if next_marker in text:
        text = text.replace(next_marker, "1. Mo rong cach lam nay sang `nguoi_than_qua_doi`\n", 1)
    CHECKLIST_DOC.write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    records = build_records()
    summary_path = write_summary(records)
    normalized_path = write_normalized(records)
    config_path = write_workflow_config(records, summary_path, normalized_path)
    intake_path, submission_path = write_test_cases()
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
