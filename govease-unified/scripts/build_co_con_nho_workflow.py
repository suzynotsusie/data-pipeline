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
WORKFLOW_DIR = ROOT / "data" / "workflows" / "co_con_nho"
TESTS_DIR = ROOT / "tests" / "workflows" / "co_con_nho"
MAPPING_CSV = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.csv"
MAPPING_JSON = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.json"
CHECKLIST_DOC = ROOT / "govease-unified" / "docs" / "codex-workstream-checklist.md"

DOMAIN_KEY = "co_con_nho"
WORKFLOW_FAMILY = "child_early_life_workflow"
UPDATED_AT = str(date.today())

SUBDOMAINS = {
    "lien_thong_khai_sinh_bao_hiem_cu_tru": {
        "label": "Liên thông khai sinh, bảo hiểm, cư trú",
        "event_id": 250,
        "summary": "Nhóm thủ tục liên thông sau sinh, kết hợp đăng ký khai sinh với cấp thẻ bảo hiểm y tế và đăng ký thường trú cho trẻ.",
        "codes": [
            "2.000986",
            "2.001023",
        ],
        "entry_prompts": [
            "Bạn muốn làm liên thông trọn gói khai sinh, bảo hiểm y tế và cư trú cho trẻ?",
        ],
    },
    "khai_sinh": {
        "label": "Khai sinh",
        "event_id": 251,
        "summary": "Nhóm thủ tục đăng ký khai sinh, đăng ký lại, bản sao, khai sinh có yếu tố nước ngoài và các biến thể kết hợp nhận cha mẹ con.",
        "codes": [
            "2.000635",
            "2.000547",
            "2.000712",
            "1.004772",
            "1.001020",
            "1.000893",
            "1.003583",
            "1.004884",
            "2.000522",
            "1.001193",
            "2.000528",
            "1.000110",
            "1.000689",
            "1.001695",
        ],
        "entry_prompts": [
            "Bạn đang cần đăng ký khai sinh mới, đăng ký lại, xin bản sao hay ghi chú khai sinh đã làm ở nước ngoài?",
            "Hồ sơ này có yếu tố nước ngoài hoặc có kết hợp nhận cha, mẹ, con không?",
        ],
    },
    "cu_tru": {
        "label": "Cư trú",
        "event_id": 253,
        "summary": "Nhóm thủ tục đăng ký thường trú cho trẻ nhỏ khi gia đình không làm qua gói liên thông đầy đủ.",
        "codes": [
            "1.004222",
        ],
        "entry_prompts": [
            "Bạn đang cần đăng ký thường trú cho trẻ sau khi làm khai sinh?",
        ],
    },
}

INTENTIONAL_OVERLAP_NOTES = {
    "2.000547": "overlap_intentional:khai_sinh_ho_tich_khac",
    "1.004222": "overlap_intentional:thuong_tru_tre_nho",
    "1.000689": "overlap_intentional:khai_sinh_ket_hop_nhan_cha_me_con",
    "1.001695": "overlap_intentional:khai_sinh_ket_hop_nhan_cha_me_con_yeu_to_nuoc_ngoai",
}

INTAKE_CASES = [
    {
        "id": "intake-child-01",
        "user_need": "Tôi muốn làm khai sinh mới cho con sinh trong nước.",
        "expected_procedure_code": "1.001193",
        "expected_terms": ["đăng ký khai sinh"],
    },
    {
        "id": "intake-child-02",
        "user_need": "Tôi muốn làm khai sinh kết hợp nhận cha cho con.",
        "expected_procedure_code": "1.000689",
        "expected_terms": ["khai sinh kết hợp", "nhận cha mẹ con"],
    },
    {
        "id": "intake-child-03",
        "user_need": "Tôi cần làm liên thông khai sinh và cấp thẻ bảo hiểm y tế cho bé dưới 6 tuổi.",
        "expected_procedure_code": "2.001023",
        "expected_terms": ["liên thông", "bảo hiểm y tế"],
    },
    {
        "id": "intake-child-04",
        "user_need": "Tôi muốn làm cả khai sinh, thường trú và bảo hiểm y tế cho trẻ trong một lần.",
        "expected_procedure_code": "2.000986",
        "expected_terms": ["liên thông", "thường trú", "bảo hiểm y tế"],
    },
    {
        "id": "intake-child-05",
        "user_need": "Tôi cần đăng ký lại khai sinh vì mất giấy tờ gốc.",
        "expected_procedure_code": "1.004884",
        "expected_terms": ["đăng ký lại khai sinh"],
    },
    {
        "id": "intake-child-06",
        "user_need": "Tôi muốn xin bản sao giấy khai sinh.",
        "expected_procedure_code": "2.000635",
        "expected_terms": ["bản sao giấy khai sinh"],
    },
    {
        "id": "intake-child-07",
        "user_need": "Con tôi sinh tại Việt Nam nhưng có yếu tố nước ngoài và cần làm khai sinh kết hợp nhận cha cho bé.",
        "expected_procedure_code": "1.001695",
        "expected_terms": ["yếu tố nước ngoài", "nhận cha mẹ con"],
    },
    {
        "id": "intake-child-08",
        "user_need": "Tôi cần đăng ký khai sinh có yếu tố nước ngoài cho con, không kèm nhận cha mẹ con.",
        "expected_procedure_code": "2.000528",
        "expected_terms": ["khai sinh có yếu tố nước ngoài"],
    },
    {
        "id": "intake-child-09",
        "user_need": "Tôi muốn làm khai sinh có yếu tố nước ngoài tại khu vực biên giới cho em bé.",
        "expected_procedure_code": "1.000110",
        "expected_terms": ["biên giới", "yếu tố nước ngoài"],
    },
    {
        "id": "intake-child-10",
        "user_need": "Con tôi sinh ở nước ngoài và có quốc tịch Việt Nam, tôi muốn đăng ký khai sinh cho bé.",
        "expected_procedure_code": "1.001020",
        "expected_terms": ["sinh ở nước ngoài", "quốc tịch Việt Nam"],
    },
    {
        "id": "intake-child-11",
        "user_need": "Người thân của tôi đã có hồ sơ cá nhân nhưng chưa có khai sinh, giờ muốn đăng ký khai sinh.",
        "expected_procedure_code": "1.004772",
        "expected_terms": ["đã có hồ sơ", "giấy tờ cá nhân"],
    },
    {
        "id": "intake-child-12",
        "user_need": "Tôi cần đăng ký khai sinh có yếu tố nước ngoài cho người đã có hồ sơ, giấy tờ cá nhân.",
        "expected_procedure_code": "1.000893",
        "expected_terms": ["đã có hồ sơ", "yếu tố nước ngoài"],
    },
    {
        "id": "intake-child-13",
        "user_need": "Tôi muốn ghi vào sổ hộ tịch việc khai sinh đã đăng ký ở nước ngoài cho con.",
        "expected_procedure_code": "2.000712",
        "expected_terms": ["ghi vào sổ hộ tịch", "khai sinh ở nước ngoài"],
    },
    {
        "id": "intake-child-14",
        "user_need": "Tôi cần ghi chú việc nhận cha con đã được cơ quan nước ngoài giải quyết vào sổ hộ tịch Việt Nam.",
        "expected_procedure_code": "2.000547",
        "expected_terms": ["hộ tịch khác", "cơ quan nước ngoài"],
    },
    {
        "id": "intake-child-15",
        "user_need": "Gia đình ở vùng khó khăn, tôi muốn đăng ký khai sinh lưu động cho trẻ.",
        "expected_procedure_code": "1.003583",
        "expected_terms": ["khai sinh lưu động"],
    },
    {
        "id": "intake-child-16",
        "user_need": "Tôi cần đăng ký lại khai sinh có yếu tố nước ngoài vì giấy tờ cũ thất lạc.",
        "expected_procedure_code": "2.000522",
        "expected_terms": ["đăng ký lại", "yếu tố nước ngoài"],
    },
    {
        "id": "intake-child-17",
        "user_need": "Tôi muốn đăng ký thường trú cho con mới sinh sau khi đã làm khai sinh.",
        "expected_procedure_code": "1.004222",
        "expected_terms": ["đăng ký thường trú cho trẻ"],
    },
]

SUBMISSION_CASES = [
    {
        "id": "submission-child-birth-domestic-invalid-core-fields",
        "procedure_code": "1.001193",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-linked-bhyt-invalid-core-fields",
        "procedure_code": "2.001023",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-linked-full-invalid-core-fields",
        "procedure_code": "2.000986",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-reregistration-domestic-invalid-core-fields",
        "procedure_code": "1.004884",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-parent-recognition-invalid-core-fields",
        "procedure_code": "1.000689",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-foreign-border-invalid-core-fields",
        "procedure_code": "1.000110",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-foreign-existing-record-invalid-core-fields",
        "procedure_code": "1.000893",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-abroad-birth-invalid-core-fields",
        "procedure_code": "1.001020",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-foreign-parent-recognition-invalid-core-fields",
        "procedure_code": "1.001695",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-mobile-birth-invalid-core-fields",
        "procedure_code": "1.003583",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-existing-record-invalid-core-fields",
        "procedure_code": "1.004772",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-reregistration-foreign-invalid-core-fields",
        "procedure_code": "2.000522",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-foreign-birth-invalid-core-fields",
        "procedure_code": "2.000528",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-foreign-civil-status-note-invalid-core-fields",
        "procedure_code": "2.000547",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-copy-extract-invalid-core-fields",
        "procedure_code": "2.000635",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-foreign-birth-note-invalid-core-fields",
        "procedure_code": "2.000712",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
        ],
    },
    {
        "id": "submission-child-permanent-residence-invalid-core-fields",
        "procedure_code": "1.004222",
        "submission": {
            "requester": {"full_name": "A", "identity_number": "12345X"},
            "child": {"birth_date": "32/13/2026"},
            "signature_present": False,
        },
        "expected_rule_ids": [
            "full-name-format",
            "identity-number-format",
            "date-format",
            "missing-signature",
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
    if subdomain_key == "lien_thong_khai_sinh_bao_hiem_cu_tru":
        return "lien_thong_khai_sinh_bao_hiem_cu_tru", slug
    if subdomain_key == "cu_tru":
        return "dang_ky_thuong_tru_cho_tre", slug
    if "ban_sao" in slug or "trich_luc" in slug:
        return "cap_ban_sao_khai_sinh", slug
    if "ghi_vao_so_ho_tich" in slug and "khai_sinh_da_dang_ky" in slug:
        return "ghi_chu_khai_sinh_o_nuoc_ngoai", slug
    if "ghi_vao_so_ho_tich" in slug:
        return "ghi_chu_ho_tich_khac_lien_quan_khai_sinh", slug
    if "dang_ky_lai_khai_sinh" in slug:
        return "dang_ky_lai_khai_sinh", slug
    if "khai_sinh_luu_dong" in slug:
        return "dang_ky_khai_sinh_luu_dong", slug
    if "co_yeu_to_nuoc_ngoai" in slug and "nhan_cha_me_con" in slug:
        return "khai_sinh_ket_hop_nhan_cha_me_con_co_yeu_to_nuoc_ngoai", slug
    if "co_yeu_to_nuoc_ngoai" in slug and "cho_nguoi_da_co_ho_so" in slug:
        return "khai_sinh_cho_nguoi_da_co_ho_so_co_yeu_to_nuoc_ngoai", slug
    if "co_yeu_to_nuoc_ngoai" in slug and "tai_khu_vuc_bien_gioi" in slug:
        return "khai_sinh_co_yeu_to_nuoc_ngoai_bien_gioi", slug
    if "co_yeu_to_nuoc_ngoai" in slug:
        return "khai_sinh_co_yeu_to_nuoc_ngoai", slug
    if "nhan_cha_me_con" in slug:
        return "khai_sinh_ket_hop_nhan_cha_me_con", slug
    if "cho_nguoi_da_co_ho_so" in slug:
        return "khai_sinh_cho_nguoi_da_co_ho_so", slug
    if "sinh_ra_o_nuoc_ngoai" in slug:
        return "khai_sinh_cho_tre_sinh_o_nuoc_ngoai", slug
    return "dang_ky_khai_sinh", slug


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
        "start_node": "child_subdomain",
        "nodes": [
            {
                "id": "child_subdomain",
                "type": "question",
                "slot": "subdomain_key",
                "question": "Bạn đang hỏi về liên thông sau sinh, khai sinh, bảo hiểm y tế hay cư trú cho trẻ?",
                "options": list(SUBDOMAINS.keys()),
            },
            {
                "id": "child_operation",
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
                    "subdomain_key": "lien_thong_khai_sinh_bao_hiem_cu_tru | khai_sinh | cu_tru | unknown",
                    "operation_key": "string",
                    "operation_group": "string",
                },
                "confidence": "0_to_1",
                "needs_human_review": "boolean",
            },
        },
        "entry_prompts": [
            "Bạn đang cần làm việc về khai sinh, bảo hiểm y tế hay cư trú cho trẻ nhỏ?",
            "Bạn muốn làm khai sinh riêng, liên thông thêm bảo hiểm hoặc cư trú, hay xin lại giấy tờ đã có?",
        ],
        "slots": [
            {
                "name": "subdomain_key",
                "required": True,
                "description": "Nhánh chính của nhóm Có con nhỏ.",
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
                "field_group": "child_birth_information",
                "checks": [
                    "Thông tin trẻ gồm họ tên, ngày sinh, nơi sinh và giới tính phải thống nhất giữa giấy chứng sinh, tờ khai và hồ sơ liên thông.",
                    "Nhóm khai sinh có yếu tố nước ngoài hoặc kết hợp nhận cha mẹ con cần đối chiếu chặt chẽ giấy tờ nhân thân của cha mẹ.",
                ],
            },
            {
                "field_group": "linked_services",
                "checks": [
                    "Nếu làm liên thông bảo hiểm y tế hoặc cư trú, dữ liệu của trẻ và cha mẹ phải đồng bộ giữa hồ sơ khai sinh, bảo hiểm và cư trú.",
                    "Đăng ký thường trú cho trẻ cần có địa chỉ cư trú rõ ràng và hồ sơ chứng minh chỗ ở hợp lệ khi không làm qua gói liên thông đầy đủ.",
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


def mapping_note_for(item: dict[str, Any]) -> str:
    note = f"workflow_generated:{DOMAIN_KEY}/{item['subdomain_key']}"
    overlap_note = INTENTIONAL_OVERLAP_NOTES.get(item["procedure_code"])
    if overlap_note:
        note = f"{note}; {overlap_note}"
    return note


def update_mapping(records: list[dict[str, Any]]) -> None:
    workflow_codes = {item["procedure_code"]: item for item in records}
    with MAPPING_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
        csv_fields = list(csv_rows[0].keys())
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
            row["notes"] = mapping_note_for(item)
        else:
            row["in_workflow_dataset"] = "false"
            row["support_level"] = "raw_only"
            if row.get("workflow_family") in {"birth_registration", "residence_management", WORKFLOW_FAMILY}:
                row["workflow_family"] = ""
            row["notes"] = "excluded_from_clean_workflow_dataset"
    with MAPPING_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(csv_rows)

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
            row["notes"] = mapping_note_for(item)
        else:
            row["in_workflow_dataset"] = False
            row["support_level"] = "raw_only"
            if row.get("workflow_family") in {"birth_registration", "residence_management", WORKFLOW_FAMILY}:
                row["workflow_family"] = None
            row["notes"] = "excluded_from_clean_workflow_dataset"
    MAPPING_JSON.write_text(json.dumps(json_rows, ensure_ascii=False, indent=2), encoding="utf-8")


def update_checklist() -> None:
    text = CHECKLIST_DOC.read_text(encoding="utf-8")
    marker = "- Uu tien rollout:\n"
    addition = "  - `co_con_nho` (da co workflow dataset va test data cho 17 ma thu tuc / 4 subdomain)\n"
    if addition not in text and marker in text:
        text = text.replace(
            marker,
            marker + addition,
            1,
        )
    next_marker = "1. Mo rong cach lam nay sang `co_con_nho`\n"
    if next_marker in text:
        text = text.replace(next_marker, "1. Mo rong cach lam nay sang `dien_luc_nha_o_dat_dai`\n", 1)
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
