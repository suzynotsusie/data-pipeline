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
WORKFLOW_DIR = ROOT / "data" / "workflows" / "hoc_tap"
TESTS_DIR = ROOT / "tests" / "workflows" / "hoc_tap"
MAPPING_CSV = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.csv"
MAPPING_JSON = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.json"
CHECKLIST_DOC = ROOT / "govease-unified" / "docs" / "codex-workstream-checklist.md"

DOMAIN_KEY = "hoc_tap"
WORKFLOW_FAMILY = "education_study_workflow"
UPDATED_AT = str(date.today())

SUBDOMAINS = {
    "tuyen_sinh": {
        "label": "Tuyển sinh",
        "event_id": 254,
        "summary": "Nhóm thủ tục tuyển sinh, đăng ký dự thi, phúc khảo, xét tuyển và công nhận tốt nghiệp cho người học.",
        "codes": [
            "1.001942",
            "1.003734",
            "1.005090",
            "1.005095",
            "1.005098",
            "1.005142",
            "1.009394",
            "1.010776",
            "1.010779",
            "1.013338",
            "1.014957",
            "3.000181",
            "3.000182",
        ],
        "entry_prompts": [
            "Bạn đang muốn đăng ký dự thi, xét tuyển, phúc khảo hay công nhận tốt nghiệp?",
            "Nhu cầu của bạn là tuyển sinh phổ thông, đại học hay thi lấy chứng chỉ?",
        ],
    },
    "chuyen_truong": {
        "label": "Chuyển trường",
        "event_id": 255,
        "summary": "Nhóm thủ tục chuyển trường, tiếp nhận học sinh và điều chỉnh quá trình học tập khi người học thay đổi nơi học.",
        "codes": [
            "1.005108",
            "1.010627",
            "2.001904",
            "2.002854",
            "2.002855",
            "2.002856",
            "2.002857",
        ],
        "entry_prompts": [
            "Bạn muốn chuyển trường trong nước, từ nước ngoài về hay xin học lại/tiếp nhận vào trường mới?",
            "Việc chuyển trường này là cho học sinh phổ thông hay diện học tập có yếu tố nước ngoài?",
        ],
    },
    "hoc_bong_va_ho_tro": {
        "label": "Học bổng và chính sách hỗ trợ",
        "event_id": 256,
        "summary": "Nhóm thủ tục học bổng, miễn giảm học phí, hỗ trợ chi phí học tập, hỗ trợ bán trú và các chính sách tài chính cho người học.",
        "codes": [
            "1.001622",
            "1.001714",
            "1.002982",
            "1.003702",
            "1.008950",
            "1.009002",
            "1.010497",
            "1.014334",
            "1.014335",
            "1.014336",
            "1.014337",
            "1.014997",
            "2.001959",
            "2.001960",
            "2.002770",
            "2.002771",
            "2.002851",
        ],
        "entry_prompts": [
            "Bạn đang xin học bổng, miễn giảm học phí hay hỗ trợ chi phí học tập?",
            "Chính sách này áp dụng cho mầm non, phổ thông, giáo dục nghề nghiệp hay đại học?",
        ],
    },
    "van_bang_chung_chi": {
        "label": "Cấp văn bằng, chứng chỉ; công nhận văn bằng, chứng chỉ do cơ sở nước ngoài cấp",
        "event_id": 257,
        "summary": "Nhóm thủ tục cấp lại, cấp bản sao, chỉnh sửa, công nhận văn bằng chứng chỉ và cấp bằng sau tốt nghiệp.",
        "codes": [
            "1.000915",
            "1.001895",
            "1.001912",
            "1.004889",
            "2.002850",
            "3.000465",
            "3.000466",
        ],
        "entry_prompts": [
            "Bạn muốn xin bản sao, cấp lại, chỉnh sửa hay công nhận văn bằng/chứng chỉ?",
            "Văn bằng của bạn do cơ sở trong nước hay nước ngoài cấp?",
        ],
    },
    "hoc_tap_o_nuoc_ngoai_bang_ngan_sach": {
        "label": "Học tập ở nước ngoài bằng ngân sách nhà nước",
        "event_id": 259,
        "summary": "Nhóm thủ tục cử đi học, tuyển chọn đi học, gia hạn, tạm dừng và tiếp nhận du học sinh theo diện học bổng ngân sách nhà nước.",
        "codes": [
            "1.001694",
            "1.002499",
            "1.002543",
            "1.005086",
            "1.010628",
        ],
        "entry_prompts": [
            "Bạn đang chuẩn bị đi học nước ngoài bằng ngân sách nhà nước, đang học ở nước ngoài hay đã tốt nghiệp về nước?",
            "Bạn cần cử đi học, gia hạn thời gian học tập, tạm dừng học hay tiếp nhận sau khi về nước?",
        ],
    },
}

INTAKE_CASES = [
    {
        "id": "intake-study-01",
        "user_need": "Tôi muốn đăng ký dự thi tốt nghiệp trung học phổ thông.",
        "expected_procedure_code": "1.005142",
        "expected_terms": ["dự thi", "tốt nghiệp trung học phổ thông"],
    },
    {
        "id": "intake-study-02",
        "user_need": "Tôi cần phúc khảo bài thi tốt nghiệp THPT.",
        "expected_procedure_code": "1.005095",
        "expected_terms": ["phúc khảo", "bài thi"],
    },
    {
        "id": "intake-study-03",
        "user_need": "Tôi muốn xét tuyển đại học và cao đẳng ngành giáo dục mầm non.",
        "expected_procedure_code": "1.001942",
        "expected_terms": ["xét tuyển", "đại học"],
    },
    {
        "id": "intake-study-04",
        "user_need": "Con tôi cần chuyển trường và được trường mới tiếp nhận.",
        "expected_procedure_code": "2.002854",
        "expected_terms": ["chuyển trường", "tiếp nhận học sinh"],
    },
    {
        "id": "intake-study-05",
        "user_need": "Tôi từ nước ngoài về và muốn cho con tiếp tục học ở Việt Nam.",
        "expected_procedure_code": "2.002855",
        "expected_terms": ["từ nước ngoài về nước", "tiếp nhận học sinh"],
    },
    {
        "id": "intake-study-06",
        "user_need": "Tôi xin miễn giảm học phí cho con đang đi học phổ thông.",
        "expected_procedure_code": "1.010497",
        "expected_terms": ["miễn giảm học phí", "hỗ trợ chi phí học tập"],
    },
    {
        "id": "intake-study-07",
        "user_need": "Tôi muốn xin học bổng và hỗ trợ đồ dùng học tập cho người khuyết tật.",
        "expected_procedure_code": "1.001714",
        "expected_terms": ["học bổng", "người khuyết tật"],
    },
    {
        "id": "intake-study-08",
        "user_need": "Tôi cần cấp bản sao văn bằng từ sổ gốc.",
        "expected_procedure_code": "3.000465",
        "expected_terms": ["bản sao văn bằng", "sổ gốc"],
    },
    {
        "id": "intake-study-09",
        "user_need": "Tôi cần công nhận bằng đại học do trường nước ngoài cấp để dùng ở Việt Nam.",
        "expected_procedure_code": "1.000915",
        "expected_terms": ["công nhận bằng", "cơ sở giáo dục nước ngoài"],
    },
    {
        "id": "intake-study-10",
        "user_need": "Tôi muốn được cử đi học nước ngoài bằng ngân sách nhà nước.",
        "expected_procedure_code": "1.001694",
        "expected_terms": ["cử đi học nước ngoài", "ngân sách nhà nước"],
    },
]

SUBMISSION_CASES = [
    {
        "id": "submission-study-exam-registration-missing-identity",
        "procedure_code": "1.005142",
        "submission": {
            "candidate": {
                "full_name": "Nguyễn Văn A",
                "identity_number": "1234A",
            },
            "graduation_year": "",
            "exam_subjects": [],
            "signature_present": False,
        },
        "expected_rule_ids": [
            "identity-number-format",
            "missing-graduation-year",
            "missing-exam-subject-selection",
            "missing-signature",
        ],
    },
    {
        "id": "submission-study-transfer-missing-school-record",
        "procedure_code": "2.002854",
        "submission": {
            "student": {
                "full_name": "Trần Thị B",
                "grade_level": "10",
            },
            "current_school_record_present": False,
            "receiving_school_confirmation_present": False,
        },
        "expected_rule_ids": [
            "missing-school-record",
            "missing-receiving-school-confirmation",
        ],
    },
    {
        "id": "submission-study-financial-support-missing-proof",
        "procedure_code": "1.010497",
        "submission": {
            "learner": {
                "full_name": "Lê Văn C",
                "identity_number": "012345678901",
            },
            "school_level": "",
            "support_category_proof_present": False,
        },
        "expected_rule_ids": [
            "missing-school-level",
            "missing-support-category-proof",
        ],
    },
    {
        "id": "submission-study-diploma-copy-missing-registry-info",
        "procedure_code": "3.000465",
        "submission": {
            "requester": {
                "full_name": "Phạm Thị D",
                "identity_number": "012345678901",
            },
            "registry_book_reference": "",
            "graduation_information_match": False,
        },
        "expected_rule_ids": [
            "missing-registry-book-reference",
            "graduation-information-mismatch",
        ],
    },
    {
        "id": "submission-study-abroad-extension-missing-approval",
        "procedure_code": "1.002543",
        "submission": {
            "student": {
                "full_name": "Hoàng Văn E",
                "identity_number": "012345678901",
            },
            "current_study_plan_present": True,
            "extension_reason": "",
            "sponsoring_agency_approval_present": False,
        },
        "expected_rule_ids": [
            "missing-extension-reason",
            "missing-sponsoring-agency-approval",
        ],
    },
]

PROCEDURE_METADATA_OVERRIDES = {
    "1.005108": {
        "Tên": "Thuyên chuyển đối tượng học bổ túc trung học cơ sở",
        "Cơ quan thực hiện": "Trung tâm Giáo dục thường xuyên",
        "Lĩnh vực": "Giáo dục thường xuyên",
        "URL": "https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-hanh-chinh.html?ma_thu_tuc=1.005108",
    },
    "2.001904": {
        "Tên": "Tiếp nhận đối tượng học bổ túc trung học cơ sở",
        "Cơ quan thực hiện": "Sở Giáo dục và Đào tạo",
        "Lĩnh vực": "Giáo dục thường xuyên",
        "URL": "https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-hanh-chinh.html?ma_thu_tuc=2.001904",
    },
}


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
    existing_codes = {row["Mã số"] for row in rows}
    for code in codes:
        if code not in existing_codes and code in PROCEDURE_METADATA_OVERRIDES:
            rows.append({"Mã số": code, **PROCEDURE_METADATA_OVERRIDES[code]})
    return rows


def classify_operation(title: str, subdomain_key: str) -> tuple[str, str]:
    slug = slugify(title)
    if subdomain_key == "tuyen_sinh":
        if "phuc_khao" in slug:
            return "phuc_khao", slug
        if "cong_nhan_tot_nghiep" in slug or "tot_nghiep" in slug:
            return "tot_nghiep", slug
        if "du_thi" in slug:
            return "dang_ky_du_thi", slug
        if "xet_tuyen" in slug or "tuyen_sinh" in slug:
            return "xet_tuyen", slug
        return "tuyen_sinh_khac", slug
    if subdomain_key == "chuyen_truong":
        if "hoc_lai" in slug:
            return "hoc_lai", slug
        if "tu_nuoc_ngoai_ve_nuoc" in slug:
            return "tiep_nhan_tu_nuoc_ngoai", slug
        if "nguoi_nuoc_ngoai" in slug:
            return "tiep_nhan_nguoi_nuoc_ngoai", slug
        if "chuyen_truong" in slug or "thuyen_chuyen" in slug or "chuyen_nganh" in slug:
            return "chuyen_truong", slug
        return "tiep_nhan_hoc_sinh", slug
    if subdomain_key == "hoc_bong_va_ho_tro":
        if "hoc_bong" in slug:
            return "hoc_bong", slug
        if "mien_giam_hoc_phi" in slug:
            return "mien_giam_hoc_phi", slug
        if "ho_tro_chi_phi_hoc_tap" in slug:
            return "ho_tro_chi_phi_hoc_tap", slug
        if "ho_tro_an_trua" in slug or "tro_cap" in slug:
            return "tro_cap_hoc_tap", slug
        if "ban_tru" in slug or "gao" in slug:
            return "ho_tro_ban_tru", slug
        return "chinh_sach_ho_tro_khac", slug
    if subdomain_key == "van_bang_chung_chi":
        if "ban_sao" in slug:
            return "cap_ban_sao", slug
        if "cap_lai" in slug:
            return "cap_lai", slug
        if "chinh_sua" in slug:
            return "chinh_sua", slug
        if "cong_nhan_bang" in slug:
            return "cong_nhan_van_bang", slug
        if "xet_cap_bang" in slug or "xet_tot_nghiep" in slug:
            return "cap_bang_sau_tot_nghiep", slug
        return "van_bang_chung_chi_khac", slug
    if "gia_han" in slug:
        return "gia_han_hoc_tap", slug
    if "tiep_nhan_du_hoc_sinh" in slug:
        return "tiep_nhan_du_hoc_sinh", slug
    if "tam_dung_hoc" in slug:
        return "tam_dung_hoc_tap", slug
    if "cung_tuyen_sinh" in slug or "tuyen_sinh" in slug:
        return "tuyen_chon_di_hoc", slug
    return "cu_di_hoc_nuoc_ngoai", slug


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
        "start_node": "study_subdomain",
        "nodes": [
            {
                "id": "study_subdomain",
                "type": "question",
                "slot": "subdomain_key",
                "question": "Bạn đang hỏi về tuyển sinh, chuyển trường, học bổng hỗ trợ, văn bằng chứng chỉ hay học tập ở nước ngoài bằng ngân sách nhà nước?",
                "options": list(SUBDOMAINS.keys()),
            },
            {
                "id": "study_operation",
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
                    "subdomain_key": "tuyen_sinh | chuyen_truong | hoc_bong_va_ho_tro | van_bang_chung_chi | hoc_tap_o_nuoc_ngoai_bang_ngan_sach | unknown",
                    "operation_key": "string",
                    "operation_group": "string",
                },
                "confidence": "0_to_1",
                "needs_human_review": "boolean",
            },
        },
        "entry_prompts": [
            "Bạn đang cần làm việc về tuyển sinh, chuyển trường, hỗ trợ học tập, văn bằng chứng chỉ hay du học bằng ngân sách nhà nước?",
            "Bạn muốn đăng ký mới, điều chỉnh, xin hỗ trợ, xin công nhận hay xin cấp lại giấy tờ học tập?",
        ],
        "slots": [
            {
                "name": "subdomain_key",
                "required": True,
                "description": "Nhánh chính của nhóm Học tập.",
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
                "field_group": "education_identity",
                "checks": [
                    "Thông tin người học phải thống nhất giữa giấy tờ nhân thân, hồ sơ trường học và biểu mẫu nộp.",
                    "Phải xác định đúng cấp học hoặc chương trình đào tạo trước khi chọn thủ tục.",
                ],
            },
            {
                "field_group": "financial_support",
                "checks": [
                    "Các thủ tục hỗ trợ học tập phải có giấy tờ chứng minh đúng diện hưởng chính sách.",
                    "Nếu xin miễn giảm học phí hoặc học bổng thì phải làm rõ cơ sở giáo dục và bậc học hiện tại.",
                ],
            },
            {
                "field_group": "abroad_study",
                "checks": [
                    "Nhóm học tập ở nước ngoài phải làm rõ trạng thái đi học, đang học hay đã hoàn thành về nước.",
                    "Các yêu cầu gia hạn hoặc tạm dừng phải có căn cứ phê duyệt của cơ quan cử đi học hoặc cơ quan quản lý.",
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
    marker = "  - `hoc_tap`\n"
    replacement = "  - `hoc_tap` (da co workflow dataset va test data cho 49 ma thu tuc / 5 subdomain)\n"
    if marker in text:
        text = text.replace(marker, replacement, 1)
    next_marker = "1. Mo rong cach lam nay sang `hoc_tap`\n"
    if next_marker in text:
        text = text.replace(next_marker, "1. Mo rong cach lam nay sang `hon_nhan_gia_dinh`\n", 1)
    stale_block = """2. Tach 3 subdomain:
   - `giay_phep_lai_xe`
   - `dang_ky_phuong_tien`
   - `dang_kiem_phuong_tien`
3. Sinh:
   - `summary.csv`
   - `normalized.json`
   - `workflow_engine_config.json`
4. Tao:
   - `intake_cases.json`
   - `submission_cases.json`
"""
    refreshed_block = """2. Xac dinh subdomain citizen-facing cho nhom nay
3. Sinh:
   - `summary.csv`
   - `normalized.json`
   - `workflow_engine_config.json`
4. Tao:
   - `intake_cases.json`
   - `submission_cases.json`
"""
    if stale_block in text:
        text = text.replace(stale_block, refreshed_block, 1)
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
