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
WORKFLOW_DIR = ROOT / "data" / "workflows" / "giai_quyet_khieu_kien"
TESTS_DIR = ROOT / "tests" / "workflows" / "giai_quyet_khieu_kien"
MAPPING_CSV = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.csv"
MAPPING_JSON = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.json"
CHECKLIST_DOC = ROOT / "govease-unified" / "docs" / "codex-workstream-checklist.md"

DOMAIN_KEY = "giai_quyet_khieu_kien"
WORKFLOW_FAMILY = "complaint_resolution_workflow"
UPDATED_AT = str(date.today())

SUBDOMAINS = {
    "giai_quyet_khieu_kien": {
        "label": "Giải quyết khiếu kiện",
        "event_id": 343,
        "summary": (
            "Nhóm thủ tục tiếp nhận và giải quyết khiếu nại, tố cáo, tranh chấp, hỗ trợ tố tụng "
            "và tương tác với cơ quan giải quyết tranh chấp cho công dân."
        ),
        "codes": [
            "1.000178",
            "1.003504",
            "1.004335",
            "1.003523",
            "1.003482",
            "1.004327",
            "1.015007",
            "1.015016",
            "1.013534",
            "1.013536",
            "1.013526",
            "1.013537",
            "1.013529",
            "1.013524",
            "1.013532",
            "1.013531",
            "1.013527",
            "1.013554",
            "1.013519",
            "1.013547",
            "1.013520",
            "1.013553",
            "1.013549",
            "1.013551",
            "1.013521",
            "2.000592",
            "3.000599",
            "1.012751",
            "1.012805",
            "1.013967",
            "1.115452",
            "1.012812",
            "1.115453",
            "1.014349",
            "1.014348",
            "3.000163",
            "3.000164",
            "3.000165",
        ],
        "entry_prompts": [
            "Bạn đang cần khiếu nại, tố cáo, hòa giải tranh chấp hay nộp hồ sơ liên quan đến vụ việc đang được cơ quan có thẩm quyền giải quyết?",
            "Vấn đề của bạn thuộc nhóm khiếu nại hành chính, tố cáo, tranh chấp đất đai, tranh chấp lao động ngoài nước hay thao tác tố tụng tại Tòa án?",
        ],
    }
}

INTAKE_CASES = [
    {
        "id": "intake-complaint-01",
        "user_need": "Tôi muốn khiếu nại quyết định hành chính của cơ quan công an cấp tỉnh.",
        "expected_procedure_code": "1.003504",
        "expected_terms": ["khiếu nại", "công an", "cấp tỉnh"],
    },
    {
        "id": "intake-complaint-02",
        "user_need": "Tôi cần tố cáo hành vi của cán bộ công an cấp xã.",
        "expected_procedure_code": "1.004327",
        "expected_terms": ["tố cáo", "công an", "cấp xã"],
    },
    {
        "id": "intake-complaint-03",
        "user_need": "Tôi muốn hòa giải tranh chấp đất đai tại địa phương.",
        "expected_procedure_code": "1.012812",
        "expected_terms": ["hòa giải tranh chấp đất đai"],
    },
    {
        "id": "intake-complaint-04",
        "user_need": "Tôi cần giải quyết tranh chấp đất đai thuộc thẩm quyền cấp tỉnh.",
        "expected_procedure_code": "1.012805",
        "expected_terms": ["tranh chấp đất đai", "cấp tỉnh"],
    },
    {
        "id": "intake-complaint-05",
        "user_need": "Tôi muốn khiếu nại về trợ giúp pháp lý đã được cung cấp.",
        "expected_procedure_code": "2.000592",
        "expected_terms": ["khiếu nại", "trợ giúp pháp lý"],
    },
    {
        "id": "intake-complaint-06",
        "user_need": "Tôi cần nộp đơn khởi kiện và tài liệu chứng cứ qua cổng trực tuyến của tòa án.",
        "expected_procedure_code": "3.000163",
        "expected_terms": ["nộp đơn khởi kiện", "tài liệu chứng cứ", "tòa án"],
    },
    {
        "id": "intake-complaint-07",
        "user_need": "Tôi cần đăng ký nhận thông báo tố tụng bằng phương tiện điện tử.",
        "expected_procedure_code": "3.000164",
        "expected_terms": ["thông báo tố tụng", "phương tiện điện tử"],
    },
    {
        "id": "intake-complaint-08",
        "user_need": "Tôi cần hỗ trợ giải quyết tranh chấp với doanh nghiệp đưa lao động đi làm việc ở nước ngoài.",
        "expected_procedure_code": "1.014348",
        "expected_terms": ["tranh chấp", "lao động đi làm việc ở nước ngoài"],
    },
]

SUBMISSION_CASES = [
    {
        "id": "submission-complaint-police-missing-decision",
        "procedure_code": "1.003504",
        "submission": {
            "complainant": {"full_name": "Nguyễn Văn A", "identity_number": "12345X"},
            "administrative_decision_present": False,
            "complaint_reason": "",
        },
        "expected_rule_ids": [
            "identity-number-format",
            "missing-administrative-decision",
            "missing-complaint-reason",
        ],
    },
    {
        "id": "submission-complaint-denunciation-missing-evidence",
        "procedure_code": "1.004327",
        "submission": {
            "denouncer": {"full_name": "Trần Thị B", "identity_number": "012345678901"},
            "denounced_person_information": "",
            "evidence_documents_present": False,
        },
        "expected_rule_ids": [
            "missing-denounced-person-information",
            "missing-evidence-documents",
        ],
    },
    {
        "id": "submission-complaint-land-mediation-missing-location",
        "procedure_code": "1.012812",
        "submission": {
            "requester": {"full_name": "Lê Văn C", "identity_number": "012345678901"},
            "land_plot_information": "",
            "dispute_location": "",
        },
        "expected_rule_ids": [
            "missing-land-plot-information",
            "missing-dispute-location",
        ],
    },
    {
        "id": "submission-complaint-legal-aid-missing-service-info",
        "procedure_code": "2.000592",
        "submission": {
            "requester": {"full_name": "Phạm Thị D", "identity_number": "012345678901"},
            "legal_aid_case_reference": "",
            "complaint_content": "",
        },
        "expected_rule_ids": [
            "missing-legal-aid-case-reference",
            "missing-complaint-content",
        ],
    },
    {
        "id": "submission-complaint-court-filing-missing-docs",
        "procedure_code": "3.000163",
        "submission": {
            "plaintiff": {"full_name": "Hoàng Văn E", "identity_number": "012345678901"},
            "petition_file_present": False,
            "evidence_bundle_present": False,
        },
        "expected_rule_ids": [
            "missing-petition-file",
            "missing-evidence-bundle",
        ],
    },
    {
        "id": "submission-complaint-overseas-labor-dispute-missing-contract",
        "procedure_code": "1.014348",
        "submission": {
            "worker": {"full_name": "Vũ Thị F", "identity_number": "012345678901"},
            "overseas_labor_contract_present": False,
            "dispute_description": "",
        },
        "expected_rule_ids": [
            "missing-overseas-labor-contract",
            "missing-dispute-description",
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


def classify_operation(title: str, field: str) -> tuple[str, str]:
    slug = slugify(title)
    field_slug = slugify(field)
    if "to_cao" in slug:
        if "cong_an_nhan_dan" in slug:
            return "to_cao_cong_an", slug
        if "bo_quoc_phong" in slug or "quoc_phong" in field_slug:
            return "to_cao_quoc_phong", slug
        return "to_cao", slug
    if "khieu_nai" in slug:
        if "cong_an_nhan_dan" in slug:
            return "khieu_nai_cong_an", slug
        if "so_huu_cong_nghiep" in slug:
            return "khieu_nai_so_huu_cong_nghiep", slug
        if "tro_giup_phap_ly" in slug:
            return "khieu_nai_tro_giup_phap_ly", slug
        if "cap_nuoc" in slug or "linh_vuc_cap_nuoc" in slug:
            return "khieu_nai_dich_vu_cap_nuoc", slug
        if "bo_quoc_phong" in slug or "quoc_phong" in field_slug:
            return "khieu_nai_quoc_phong", slug
        return "khieu_nai_hanh_chinh", slug
    if "hoa_giai_tranh_chap_dat_dai" in slug:
        return "hoa_giai_tranh_chap_dat_dai", slug
    if "tranh_chap_dat_dai" in slug:
        return "giai_quyet_tranh_chap_dat_dai", slug
    if "lao_dong_di_lam_viec_o_nuoc_ngoai" in slug:
        return "ho_tro_tranh_chap_lao_dong_ngoai_nuoc", slug
    if "khoi_kien" in slug:
        return "nop_don_khoi_kien", slug
    if "van_ban_to_tung" in slug and "dien_tu" in slug:
        return "nhan_thong_bao_to_tung_dien_tu", slug
    if "cap_sao_ban_an" in slug:
        return "xin_cap_sao_ban_an_tai_lieu", slug
    return "giai_quyet_khieu_kien_khac", slug


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
        operation_group, operation_key = classify_operation(row["Tên"], row.get("Lĩnh vực", ""))
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
    return sorted(records, key=lambda item: (item["operation_group"], item["procedure_code"]))


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
    payload = {
        "schema_version": "1.0",
        "domain": DOMAIN_KEY,
        "updated_at": UPDATED_AT,
        "source_files": [str(FULL_DATA_CSV), str(RAW_DATA_DIR)],
        "subdomains": [
            {
                "subdomain_key": "giai_quyet_khieu_kien",
                "subdomain_label": SUBDOMAINS["giai_quyet_khieu_kien"]["label"],
                "event_id": SUBDOMAINS["giai_quyet_khieu_kien"]["event_id"],
                "summary": SUBDOMAINS["giai_quyet_khieu_kien"]["summary"],
                "entry_prompts": SUBDOMAINS["giai_quyet_khieu_kien"]["entry_prompts"],
                "procedure_count": len(records),
                "procedures": records,
            }
        ],
    }
    path = WORKFLOW_DIR / "normalized.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def build_decision_tree(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped_operations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in records:
        grouped_operations[item["operation_group"]].append(item)
    routes = []
    for item in records:
        routes.append(
            {
                "route_id": f"{item['operation_group']}-{item['procedure_code'].replace('.', '_')}",
                "conditions": {
                    "subdomain_key": item["subdomain_key"],
                    "operation_key": item["operation_key"],
                },
                "procedure_code": item["procedure_code"],
                "procedure_name": item["procedure_title"],
                "why_this_route": f"Route trực tiếp cho nhu cầu '{item['procedure_title']}' trong nhóm '{item['operation_group']}'.",
            }
        )
    return {
        "start_node": "complaint_need_type",
        "nodes": [
            {
                "id": "complaint_need_type",
                "type": "question",
                "slot": "operation_group",
                "question": "Bạn đang cần khiếu nại, tố cáo, giải quyết tranh chấp hay thao tác tố tụng/tòa án?",
                "options": sorted(grouped_operations),
            },
            {
                "id": "complaint_operation",
                "type": "question",
                "slot": "operation_key",
                "question": "Bạn cần thủ tục cụ thể nào trong nhóm đã chọn?",
                "options_by_group": {
                    key: [
                        {
                            "operation_key": item["operation_key"],
                            "procedure_code": item["procedure_code"],
                            "procedure_title": item["procedure_title"],
                            "field": item["field"],
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
                    "subdomain_key": "giai_quyet_khieu_kien | unknown",
                    "operation_group": "khieu_nai_cong_an | to_cao_cong_an | khieu_nai_so_huu_cong_nghiep | khieu_nai_quoc_phong | to_cao_quoc_phong | khieu_nai_tro_giup_phap_ly | khieu_nai_dich_vu_cap_nuoc | giai_quyet_tranh_chap_dat_dai | hoa_giai_tranh_chap_dat_dai | ho_tro_tranh_chap_lao_dong_ngoai_nuoc | nop_don_khoi_kien | nhan_thong_bao_to_tung_dien_tu | xin_cap_sao_ban_an_tai_lieu | unknown",
                    "operation_key": "string",
                },
                "confidence": "0_to_1",
                "needs_human_review": "boolean",
            },
        },
        "entry_prompts": [
            "Bạn đang muốn khiếu nại, tố cáo, hòa giải tranh chấp đất đai hay thao tác với hồ sơ tại Tòa án?",
            "Vụ việc của bạn thuộc nhóm cơ quan công an, quốc phòng, đất đai, lao động ngoài nước, sở hữu công nghiệp hay tố tụng tại Tòa án?",
        ],
        "slots": [
            {
                "name": "subdomain_key",
                "required": True,
                "description": "Nhánh chính của nhóm Giải quyết khiếu kiện.",
            },
            {
                "name": "operation_group",
                "required": True,
                "description": "Loại nhu cầu tranh chấp/khiếu nại/tố tụng cấp cao cho bước phân nhánh đầu tiên.",
            },
            {
                "name": "operation_key",
                "required": True,
                "description": "Thao tác cụ thể ánh xạ trực tiếp tới thủ tục cuối cùng.",
            },
        ],
        "subdomain_catalog": [
            {
                "subdomain_key": "giai_quyet_khieu_kien",
                "subdomain_label": SUBDOMAINS["giai_quyet_khieu_kien"]["label"],
                "event_id": SUBDOMAINS["giai_quyet_khieu_kien"]["event_id"],
                "summary": SUBDOMAINS["giai_quyet_khieu_kien"]["summary"],
            }
        ],
        "decision_tree": build_decision_tree(records),
        "pre_submission_checks": [
            {
                "field_group": "complaint_and_denunciation",
                "checks": [
                    "Nhóm khiếu nại, tố cáo cần làm rõ cơ quan/đơn vị bị khiếu nại, tố cáo và cấp giải quyết phù hợp trước khi chọn thủ tục chi tiết.",
                    "Hồ sơ khiếu nại phải có nội dung vụ việc, quyết định/hành vi bị khiếu nại hoặc mô tả rõ căn cứ phát sinh tranh chấp.",
                ],
            },
            {
                "field_group": "dispute_and_litigation",
                "checks": [
                    "Nhóm tranh chấp đất đai cần phân biệt hòa giải tại cấp xã với thủ tục giải quyết tranh chấp theo thẩm quyền cấp xã, cấp tỉnh hoặc bộ.",
                    "Nhóm tố tụng/tòa án cần phân biệt nộp đơn khởi kiện, đăng ký nhận thông báo điện tử và xin cấp sao bản án, tài liệu hồ sơ vụ án.",
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
    marker = "  - `huu_tri` (da co workflow dataset va test data cho 28 ma thu tuc / 2 subdomain)\n"
    addition = "  - `giai_quyet_khieu_kien` (da co workflow dataset va test data cho 38 ma thu tuc / 1 subdomain)\n"
    if addition not in text and marker in text:
        text = text.replace(marker, marker + addition, 1)
    next_marker = "1. Mo rong cach lam nay sang `giai_quyet_khieu_kien`\n"
    if next_marker in text:
        text = text.replace(
            next_marker,
            "1. Tich hop frontend hien thi cho 11 nhom Cong dan va payload intake theo `group_key` / `subdomain_key`\n",
            1,
        )
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
