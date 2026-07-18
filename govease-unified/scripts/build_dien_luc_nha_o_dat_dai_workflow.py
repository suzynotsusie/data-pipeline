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
WORKFLOW_DIR = ROOT / "data" / "workflows" / "dien_luc_nha_o_dat_dai"
TESTS_DIR = ROOT / "tests" / "workflows" / "dien_luc_nha_o_dat_dai"
MAPPING_CSV = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.csv"
MAPPING_JSON = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.json"
CHECKLIST_DOC = ROOT / "govease-unified" / "docs" / "codex-workstream-checklist.md"

DOMAIN_KEY = "dien_luc_nha_o_dat_dai"
WORKFLOW_FAMILY = "housing_land_electricity_workflow"
UPDATED_AT = str(date.today())

SUBDOMAINS = {
    "dang_ky_quyen_so_huu_quyen_su_dung": {
        "label": "Đăng ký quyền sở hữu, quyền sử dụng",
        "event_id": 287,
        "summary": "Nhóm thủ tục đăng ký lần đầu, cấp đổi, cấp lại, đính chính và tách thửa liên quan đến quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất.",
        "codes": [
            "1.013978",
            "1.012783",
            "1.012786",
            "1.012790",
            "1.012784",
        ],
        "entry_prompts": [
            "Bạn đang cần đăng ký lần đầu, cấp đổi, cấp lại hay chỉnh sửa thông tin trên Giấy chứng nhận quyền sử dụng đất?",
        ],
    },
    "chuyen_nhuong_tang_cho_thua_ke": {
        "label": "Chuyển nhượng, tặng cho, thừa kế",
        "event_id": 288,
        "summary": "Nhóm thủ tục biến động đất đai do chuyển nhượng, tặng cho, thừa kế hoặc chuyển quyền gắn với tách thửa, hợp thửa.",
        "codes": [
            "1.013831",
            "1.014365",
        ],
        "entry_prompts": [
            "Bạn đang sang tên đất do mua bán, tặng cho, thừa kế hay tách thửa đồng thời chuyển quyền?",
        ],
    },
    "gop_von_the_chap": {
        "label": "Góp vốn, thế chấp",
        "event_id": 290,
        "summary": "Nhóm thủ tục đăng ký, thay đổi, xóa hoặc xử lý biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất và chuyển tiếp đăng ký thế chấp quyền tài sản phát sinh từ hợp đồng mua bán nhà ở.",
        "codes": [
            "1.011441",
            "1.011442",
            "1.011443",
            "1.011444",
            "1.011445",
        ],
        "entry_prompts": [
            "Bạn đang đăng ký mới, thay đổi, xóa hay xử lý đăng ký thế chấp hoặc biện pháp bảo đảm liên quan đến đất, nhà ở?",
        ],
    },
    "chuyen_muc_dich_su_dung": {
        "label": "Chuyển mục đích sử dụng",
        "event_id": 311,
        "summary": "Nhóm thủ tục chuyển mục đích sử dụng đất, bao gồm cả trường hợp phải xin phép và không phải xin phép cơ quan nhà nước có thẩm quyền.",
        "codes": [
            "1.013992",
            "1.115708",
        ],
        "entry_prompts": [
            "Bạn muốn chuyển mục đích sử dụng đất và cần biết trường hợp của mình có phải xin phép hay chỉ đăng ký biến động?",
        ],
    },
    "xay_dung_cong_trinh_nha_o": {
        "label": "Xây dựng công trình, nhà ở",
        "event_id": 313,
        "summary": "Nhóm thủ tục cấp phép xây dựng, sửa chữa, di dời nhà ở riêng lẻ và tiếp cận nhà ở xã hội, thuê mua nhà ở xã hội cho hộ gia đình, cá nhân.",
        "codes": [
            "1.009122",
            "1.013225",
            "1.013229",
            "1.013232",
            "1.014632",
            "1.115150",
            "1.012896",
        ],
        "entry_prompts": [
            "Bạn đang xin phép xây mới, sửa chữa, di dời nhà ở riêng lẻ hay đăng ký mua, thuê mua, thuê nhà ở xã hội?",
        ],
    },
    "cung_cap_dien_nang": {
        "label": "Cung cấp điện năng",
        "event_id": 323,
        "summary": "Nhóm thủ tục cấp điện mới cho hộ dân và thông báo phát triển điện mặt trời mái nhà tự sản xuất, tự tiêu thụ có đấu nối.",
        "codes": [
            "3.000001",
            "2.002676",
        ],
        "entry_prompts": [
            "Bạn cần cấp điện mới hay muốn thông báo phát triển điện mặt trời mái nhà có đấu nối lưới điện quốc gia?",
        ],
    },
}

INTAKE_CASES = [
    {
        "id": "intake-housing-land-01",
        "user_need": "Tôi muốn đăng ký cấp sổ đỏ lần đầu cho hộ gia đình.",
        "expected_procedure_code": "1.013978",
        "expected_terms": ["đăng ký đất đai", "cấp giấy chứng nhận lần đầu"],
    },
    {
        "id": "intake-housing-land-02",
        "user_need": "Tôi cần sang tên quyền sử dụng đất do được tặng cho.",
        "expected_procedure_code": "1.013831",
        "expected_terms": ["tặng cho", "đăng ký biến động"],
    },
    {
        "id": "intake-housing-land-03",
        "user_need": "Tôi muốn đăng ký thế chấp quyền sử dụng đất để vay ngân hàng.",
        "expected_procedure_code": "1.011441",
        "expected_terms": ["thế chấp", "biện pháp bảo đảm"],
    },
    {
        "id": "intake-housing-land-04",
        "user_need": "Tôi muốn chuyển đất sang mục đích sử dụng khác.",
        "expected_procedure_code": "1.115708",
        "expected_terms": ["chuyển mục đích sử dụng đất"],
    },
    {
        "id": "intake-housing-land-05",
        "user_need": "Tôi cần xin phép xây mới nhà ở riêng lẻ.",
        "expected_procedure_code": "1.013225",
        "expected_terms": ["cấp giấy phép xây dựng mới", "nhà ở riêng lẻ"],
    },
    {
        "id": "intake-housing-land-06",
        "user_need": "Gia đình tôi muốn đăng ký mua nhà ở xã hội.",
        "expected_procedure_code": "1.014632",
        "expected_terms": ["nhà ở xã hội", "đăng ký mua"],
    },
    {
        "id": "intake-housing-land-07",
        "user_need": "Tôi muốn làm thủ tục cấp điện mới cho nhà ở.",
        "expected_procedure_code": "3.000001",
        "expected_terms": ["cấp điện mới"],
    },
]

SUBMISSION_CASES = [
    {
        "id": "submission-land-first-registration-missing-plot",
        "procedure_code": "1.013978",
        "submission": {
            "applicant": {"full_name": "Nguyễn Văn A", "identity_number": "012345678901"},
            "land_parcel_number": "",
            "land_use_origin": "",
            "attached_documents_present": False,
        },
        "expected_rule_ids": [
            "missing-land-parcel-number",
            "missing-land-use-origin",
            "missing-land-registration-documents",
        ],
    },
    {
        "id": "submission-mortgage-registration-missing-collateral-info",
        "procedure_code": "1.011441",
        "submission": {
            "secured_party": {"full_name": "Ngân hàng B"},
            "grantor": {"full_name": "Trần Thị C"},
            "collateral_description": "",
            "guarantee_contract_present": False,
        },
        "expected_rule_ids": [
            "missing-collateral-description",
            "missing-guarantee-contract",
        ],
    },
    {
        "id": "submission-building-permit-missing-design",
        "procedure_code": "1.013225",
        "submission": {
            "owner": {"full_name": "Lê Văn D", "identity_number": "012345678901"},
            "construction_address": "",
            "design_drawings_present": False,
            "land_use_right_document_present": False,
        },
        "expected_rule_ids": [
            "missing-construction-address",
            "missing-design-drawings",
            "missing-land-use-right-document",
        ],
    },
    {
        "id": "submission-electricity-new-connection-missing-load",
        "procedure_code": "3.000001",
        "submission": {
            "requester": {"full_name": "Phạm Thị E"},
            "service_address": "",
            "requested_capacity_kw": "",
            "identity_document_present": False,
        },
        "expected_rule_ids": [
            "missing-service-address",
            "missing-requested-capacity",
            "missing-identity-document",
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
    if subdomain_key == "dang_ky_quyen_so_huu_quyen_su_dung":
        if "lan_dau" in slug:
            return "dang_ky_lan_dau", slug
        if "cap_doi" in slug:
            return "cap_doi_giay_chung_nhan", slug
        if "cap_lai" in slug or "bi_mat" in slug:
            return "cap_lai_giay_chung_nhan", slug
        if "dinh_chinh" in slug:
            return "dinh_chinh_giay_chung_nhan", slug
        if "tach_thua" in slug or "hop_thua" in slug:
            return "tach_hop_thua", slug
        return "dang_ky_quyen_su_dung_dat", slug
    if subdomain_key == "chuyen_nhuong_tang_cho_thua_ke":
        if "tach_thua" in slug or "hop_thua" in slug:
            return "tach_thua_gan_chuyen_quyen", slug
        return "dang_ky_bien_dong_chuyen_quyen", slug
    if subdomain_key == "gop_von_the_chap":
        if "thay_doi" in slug:
            return "thay_doi_bien_phap_bao_dam", slug
        if "xoa" in slug:
            return "xoa_bien_phap_bao_dam", slug
        if "xu_ly_tai_san_bao_dam" in slug:
            return "xu_ly_tai_san_bao_dam", slug
        if "chuyen_tiep" in slug or "the_chap_quyen_tai_san" in slug:
            return "chuyen_tiep_dang_ky_the_chap", slug
        return "dang_ky_bien_phap_bao_dam", slug
    if subdomain_key == "chuyen_muc_dich_su_dung":
        if "khong_phai_xin_phep" in slug:
            return "dang_ky_bien_dong_khong_xin_phep", slug
        return "xin_chuyen_muc_dich_su_dung_dat", slug
    if subdomain_key == "xay_dung_cong_trinh_nha_o":
        if "nha_o_xa_hoi" in slug and ("mua" in slug or "thue_mua" in slug or "thue" in slug):
            return "tiep_can_nha_o_xa_hoi", slug
        if "di_doi" in slug:
            return "cap_phep_di_doi_cong_trinh_nha_o", slug
        if "sua_chua" in slug or "cai_tao" in slug:
            return "cap_phep_sua_chua_cai_tao", slug
        if "co_thoi_han" in slug:
            return "cap_phep_xay_dung_co_thoi_han", slug
        return "cap_phep_xay_dung_moi", slug
    if "dien_mat_troi" in slug:
        return "thong_bao_dien_mat_troi_mai_nha", slug
    return "cap_dien_moi", slug


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
        "start_node": "housing_land_electricity_subdomain",
        "nodes": [
            {
                "id": "housing_land_electricity_subdomain",
                "type": "question",
                "slot": "subdomain_key",
                "question": "Bạn đang cần làm việc về sổ đất, sang tên, thế chấp, chuyển mục đích sử dụng đất, xây dựng nhà ở hay cấp điện?",
                "options": list(SUBDOMAINS.keys()),
            },
            {
                "id": "housing_land_electricity_operation",
                "type": "question",
                "slot": "operation_key",
                "question": "Trong nhánh đã chọn, bạn đang cần thao tác cụ thể nào?",
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
                    "subdomain_key": "dang_ky_quyen_so_huu_quyen_su_dung | chuyen_nhuong_tang_cho_thua_ke | gop_von_the_chap | chuyen_muc_dich_su_dung | xay_dung_cong_trinh_nha_o | cung_cap_dien_nang | unknown",
                    "operation_key": "string",
                    "operation_group": "string",
                },
                "confidence": "0_to_1",
                "needs_human_review": "boolean",
            },
        },
        "entry_prompts": [
            "Bạn cần làm việc về quyền sử dụng đất, sang tên, thế chấp, chuyển mục đích, xây dựng nhà ở hay điện sinh hoạt?",
            "Bạn muốn đăng ký mới, chỉnh lý biến động, xin phép xây dựng, đăng ký nhà ở xã hội hay cấp điện mới?",
        ],
        "slots": [
            {
                "name": "subdomain_key",
                "required": True,
                "description": "Nhánh chính của nhóm Điện lực, nhà ở, đất đai.",
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
                "field_group": "land_registration",
                "checks": [
                    "Nhóm đất đai phải làm rõ loại biến động: đăng ký lần đầu, cấp đổi, cấp lại, đính chính, tách thửa hay sang tên do chuyển quyền.",
                    "Thông tin thửa đất, số Giấy chứng nhận, chủ sử dụng đất và giấy tờ chứng minh nguồn gốc đất phải thống nhất giữa tờ khai và hồ sơ đính kèm.",
                ],
            },
            {
                "field_group": "secured_transactions",
                "checks": [
                    "Nhóm góp vốn, thế chấp phải xác định rõ là đăng ký mới, thay đổi, xóa hay thông báo xử lý tài sản bảo đảm.",
                    "Nếu là thế chấp quyền tài sản phát sinh từ hợp đồng mua bán nhà ở, phải có thông tin hợp đồng và tài sản gắn liền với đất đủ để định danh tài sản bảo đảm.",
                ],
            },
            {
                "field_group": "construction_and_housing",
                "checks": [
                    "Nhóm xây dựng, nhà ở phải phân biệt rõ xây mới, sửa chữa, cải tạo, di dời hay tiếp cận nhà ở xã hội.",
                    "Các trường hợp xin phép xây dựng nhà ở riêng lẻ cần kiểm tra địa chỉ xây dựng, quyền sử dụng đất và bản vẽ thiết kế trước khi nhận hồ sơ.",
                ],
            },
            {
                "field_group": "electricity_services",
                "checks": [
                    "Nhóm điện năng phải phân biệt giữa cấp điện mới và thông báo phát triển điện mặt trời mái nhà có đấu nối.",
                    "Nếu là cấp điện mới, cần có địa chỉ sử dụng điện, nhu cầu công suất và giấy tờ định danh người yêu cầu.",
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
    marker = "  - `nguoi_than_qua_doi` (da co workflow dataset va test data cho 18 ma thu tuc / 2 subdomain)\n"
    addition = "  - `dien_luc_nha_o_dat_dai` (da co workflow dataset va test data cho 23 ma thu tuc / 6 subdomain)\n"
    if addition not in text and marker in text:
        text = text.replace(marker, marker + addition, 1)
    next_marker = "1. Mo rong cach lam nay sang `dien_luc_nha_o_dat_dai`\n"
    if next_marker in text:
        text = text.replace(next_marker, "1. Mo rong cach lam nay sang `suc_khoe_y_te`\n", 1)
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
