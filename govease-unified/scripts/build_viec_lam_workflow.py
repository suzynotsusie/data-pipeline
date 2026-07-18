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
WORKFLOW_DIR = ROOT / "data" / "workflows" / "viec_lam"
TESTS_DIR = ROOT / "tests" / "workflows" / "viec_lam"
MAPPING_CSV = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.csv"
MAPPING_JSON = ROOT / "govease-unified" / "data" / "catalog" / "citizen_procedure_mapping.json"
CHECKLIST_DOC = ROOT / "govease-unified" / "docs" / "codex-workstream-checklist.md"

DOMAIN_KEY = "viec_lam"
WORKFLOW_FAMILY = "employment_workflow"
UPDATED_AT = str(date.today())

SUBDOMAINS = {
    "ho_tro_tu_van_gioi_thieu_viec_lam": {
        "label": "Hỗ trợ, tư vấn giới thiệu việc làm",
        "event_id": 260,
        "summary": "Nhóm thủ tục hỗ trợ tư vấn, giới thiệu việc làm và hỗ trợ đi làm trong, ngoài tỉnh hoặc đi làm việc ở nước ngoài.",
        "codes": [
            "1.012474",
            "1.014746",
            "2.002681",
            "2.002682",
        ],
        "entry_prompts": [
            "Bạn đang cần tư vấn việc làm, hỗ trợ tìm việc hay hỗ trợ chi phí để đi làm việc?",
            "Bạn muốn tìm việc trong nước, ngoài tỉnh hay đi làm việc ở nước ngoài?",
        ],
    },
    "tuyen_dung": {
        "label": "Tuyển dụng",
        "event_id": 261,
        "summary": "Nhóm thủ tục đăng ký lao động và điều chỉnh trạng thái lao động, phục vụ nhu cầu tìm việc và quản lý hồ sơ việc làm của người lao động.",
        "codes": [
            "1.115302",
            "1.115303",
            "1.115304",
            "1.115305",
            "1.115306",
            "1.115307",
            "1.115308",
            "1.115309",
        ],
        "entry_prompts": [
            "Bạn đang muốn đăng ký thông tin lao động mới hay điều chỉnh trạng thái việc làm hiện tại?",
            "Hiện bạn đang có việc làm, thất nghiệp hay không tham gia hoạt động kinh tế?",
        ],
    },
    "bao_hiem_xa_hoi_that_nghiep_tro_cap": {
        "label": "Bảo hiểm xã hội, thất nghiệp, trợ cấp",
        "event_id": 262,
        "summary": "Nhóm thủ tục tham gia, hưởng, tiếp tục hưởng, tạm dừng, chấm dứt và chuyển nơi hưởng trợ cấp thất nghiệp.",
        "codes": [
            "1.001601",
            "1.014745",
            "1.014748",
            "1.014749",
            "1.014750",
            "1.014751",
            "1.014752",
            "1.014753",
        ],
        "entry_prompts": [
            "Bạn đang tham gia hay đang hưởng trợ cấp thất nghiệp, hoặc cần thay đổi trạng thái hưởng?",
            "Bạn cần nộp hồ sơ mới, thông báo tìm việc hằng tháng, chuyển nơi hưởng hay dừng/chấm dứt hưởng?",
        ],
    },
    "chung_chi_hanh_nghe": {
        "label": "Chứng chỉ hành nghề",
        "event_id": 264,
        "summary": "Nhóm thủ tục đánh giá, cấp và cấp lại chứng chỉ kỹ năng nghề quốc gia cho người lao động.",
        "codes": [
            "1.115477",
            "1.115480",
            "1.115481",
            "1.115482",
        ],
        "entry_prompts": [
            "Bạn đang cần đánh giá kỹ năng nghề, cấp chứng chỉ hay cấp lại chứng chỉ kỹ năng nghề?",
        ],
    },
    "nang_ngach": {
        "label": "Nâng ngạch",
        "event_id": 265,
        "summary": "Nhóm thủ tục hỗ trợ đào tạo, bồi dưỡng và nâng cao trình độ kỹ năng nghề để phát triển nghề nghiệp.",
        "codes": [
            "1.014578",
            "1.014747",
            "1.014754",
            "1.115483",
            "2.002821",
        ],
        "entry_prompts": [
            "Bạn đang cần hỗ trợ đào tạo, bồi dưỡng hay nâng cao kỹ năng nghề để phát triển công việc?",
            "Bạn là người lao động trực tiếp hay người sử dụng lao động đang xin hỗ trợ đào tạo?",
        ],
    },
    "thue_thu_nhap_ca_nhan": {
        "label": "Thuế thu nhập cá nhân",
        "event_id": 266,
        "summary": "Nhóm thủ tục khai thuế thu nhập cá nhân trực tiếp đối với thu nhập từ tiền lương, tiền công.",
        "codes": [
            "2.002237",
        ],
        "entry_prompts": [
            "Bạn đang cần khai thuế thu nhập cá nhân trực tiếp cho thu nhập từ lương, tiền công?",
        ],
    },
    "cap_phep_lao_dong_nguoi_nuoc_ngoai": {
        "label": "Cấp phép lao động cho người nước ngoài",
        "event_id": 267,
        "summary": "Nhóm thủ tục cấp, cấp lại, gia hạn giấy phép lao động hoặc xác nhận miễn giấy phép lao động cho người nước ngoài làm việc tại Việt Nam.",
        "codes": [
            "1.004527",
            "1.014196",
            "1.014197",
            "1.014198",
            "1.014199",
            "1.014200",
            "1.014201",
            "2.000725",
            "2.000731",
            "2.000902",
            "2.000907",
            "2.001830",
            "2.001940",
        ],
        "entry_prompts": [
            "Bạn đang cần xin giấy phép lao động mới, cấp lại, gia hạn hay xin xác nhận không thuộc diện cấp giấy phép?",
            "Trường hợp này là lao động nước ngoài thông thường hay thuộc chương trình lao động kết hợp kỳ nghỉ/chuyên gia khoa học công nghệ?",
        ],
    },
}

INTAKE_CASES = [
    {
        "id": "intake-employment-01",
        "user_need": "Tôi cần hỗ trợ tư vấn, giới thiệu việc làm tại trung tâm dịch vụ việc làm.",
        "expected_procedure_code": "1.014746",
        "expected_terms": ["tư vấn", "giới thiệu việc làm"],
    },
    {
        "id": "intake-employment-02",
        "user_need": "Tôi muốn đăng ký lao động vì đang thất nghiệp và cần cập nhật tình trạng việc làm.",
        "expected_procedure_code": "1.115305",
        "expected_terms": ["đăng ký lao động", "thất nghiệp"],
    },
    {
        "id": "intake-employment-03",
        "user_need": "Tôi muốn nộp hồ sơ hưởng trợ cấp thất nghiệp.",
        "expected_procedure_code": "1.014748",
        "expected_terms": ["hưởng trợ cấp thất nghiệp"],
    },
    {
        "id": "intake-employment-04",
        "user_need": "Tôi cần thông báo tìm kiếm việc làm hằng tháng để tiếp tục nhận trợ cấp thất nghiệp.",
        "expected_procedure_code": "1.014749",
        "expected_terms": ["thông báo hằng tháng", "tìm kiếm việc làm"],
    },
    {
        "id": "intake-employment-05",
        "user_need": "Tôi muốn được cấp chứng chỉ kỹ năng nghề quốc gia.",
        "expected_procedure_code": "1.115480",
        "expected_terms": ["cấp chứng chỉ kỹ năng nghề quốc gia"],
    },
    {
        "id": "intake-employment-06",
        "user_need": "Tôi cần hỗ trợ tham gia đào tạo nâng cao trình độ kỹ năng nghề.",
        "expected_procedure_code": "1.115483",
        "expected_terms": ["hỗ trợ", "đào tạo", "nâng cao trình độ kỹ năng nghề"],
    },
    {
        "id": "intake-employment-07",
        "user_need": "Tôi cần khai thuế thu nhập cá nhân trực tiếp cho tiền lương.",
        "expected_procedure_code": "2.002237",
        "expected_terms": ["khai thuế thu nhập cá nhân", "tiền lương"],
    },
    {
        "id": "intake-employment-08",
        "user_need": "Công ty tôi muốn cấp giấy phép lao động cho người nước ngoài mới sang làm việc.",
        "expected_procedure_code": "1.014199",
        "expected_terms": ["cấp giấy phép lao động", "người lao động nước ngoài"],
    },
]

SUBMISSION_CASES = [
    {
        "id": "submission-employment-job-support-missing-profile",
        "procedure_code": "1.014746",
        "submission": {
            "applicant": {"full_name": "Nguyễn Văn A", "identity_number": "12345X"},
            "career_need": "",
            "job_seeker_profile_present": False,
        },
        "expected_rule_ids": [
            "identity-number-format",
            "missing-career-need",
            "missing-job-seeker-profile",
        ],
    },
    {
        "id": "submission-employment-unemployment-missing-termination-doc",
        "procedure_code": "1.014748",
        "submission": {
            "applicant": {"full_name": "Trần Thị B", "identity_number": "012345678901"},
            "employment_termination_document_present": False,
            "unemployment_insurance_period_proof_present": False,
        },
        "expected_rule_ids": [
            "missing-employment-termination-document",
            "missing-unemployment-insurance-proof",
        ],
    },
    {
        "id": "submission-employment-monthly-report-missing-status",
        "procedure_code": "1.014749",
        "submission": {
            "beneficiary": {"full_name": "Lê Văn C", "identity_number": "012345678901"},
            "job_search_status": "",
            "monthly_confirmation_present": False,
        },
        "expected_rule_ids": [
            "missing-job-search-status",
            "missing-monthly-confirmation",
        ],
    },
    {
        "id": "submission-employment-skill-certificate-missing-assessment",
        "procedure_code": "1.115480",
        "submission": {
            "applicant": {"full_name": "Phạm Thị D", "identity_number": "012345678901"},
            "skill_assessment_registration_present": False,
            "occupation_name": "",
        },
        "expected_rule_ids": [
            "missing-skill-assessment-registration",
            "missing-occupation-name",
        ],
    },
    {
        "id": "submission-employment-work-permit-missing-approval",
        "procedure_code": "1.014199",
        "submission": {
            "worker": {"full_name": "John Smith", "passport_number": ""},
            "employer_need_approval_present": False,
            "health_certificate_present": False,
        },
        "expected_rule_ids": [
            "missing-passport-number",
            "missing-employer-need-approval",
            "missing-health-certificate",
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
    if subdomain_key == "ho_tro_tu_van_gioi_thieu_viec_lam":
        if "tu_van_gioi_thieu_viec_lam" in slug:
            return "tu_van_gioi_thieu_viec_lam", slug
        if "ve_xe" in slug:
            return "ho_tro_chi_phi_di_lai", slug
        if "nuoc_ngoai" in slug:
            return "ho_tro_di_lam_viec_o_nuoc_ngoai", slug
        return "ho_tro_di_lam_viec_ngoai_tinh", slug
    if subdomain_key == "tuyen_dung":
        if "dieu_chinh" in slug:
            return "dieu_chinh_dang_ky_lao_dong", slug
        if "econtract" in slug:
            return "ket_noi_hop_dong_lao_dong_dien_tu", slug
        return "dang_ky_lao_dong", slug
    if subdomain_key == "bao_hiem_xa_hoi_that_nghiep_tro_cap":
        if "tham_gia_bao_hiem_that_nghiep" in slug:
            return "tham_gia_bao_hiem_that_nghiep", slug
        if "huong_tro_cap_that_nghiep" in slug:
            return "huong_tro_cap_that_nghiep", slug
        if "tim_kiem_viec_lam" in slug:
            return "thong_bao_tim_kiem_viec_lam", slug
        if "tam_dung" in slug:
            return "tam_dung_huong_tro_cap", slug
        if "tiep_tuc" in slug:
            return "tiep_tuc_huong_tro_cap", slug
        if "cham_dut" in slug:
            return "cham_dut_huong_tro_cap", slug
        if "chuyen_noi_huong" in slug:
            return "chuyen_noi_huong_tro_cap", slug
        return "uy_quyen_nhan_che_do", slug
    if subdomain_key == "chung_chi_hanh_nghe":
        if "thua_nhan_lan_nhau" in slug:
            return "cong_nhan_chung_chi_ky_nang", slug
        if "cap_lai" in slug:
            return "cap_lai_chung_chi_ky_nang", slug
        if "danh_gia" in slug:
            return "ho_tro_danh_gia_ky_nang", slug
        return "cap_chung_chi_ky_nang", slug
    if subdomain_key == "nang_ngach":
        if "nguoi_su_dung_lao_dong" in slug:
            return "ho_tro_dao_tao_duy_tri_viec_lam", slug
        if "danh_gia" in slug:
            return "ho_tro_danh_gia_ky_nang_nghe", slug
        if "dao_tao_nghe" in slug:
            return "ho_tro_dao_tao_nghe", slug
        if "dao_tao_nang_cao" in slug or "nang_cao_trinh_do_ky_nang_nghe" in slug:
            return "ho_tro_nang_cao_trinh_do_ky_nang", slug
        return "ho_tro_dao_tao_linh_vuc_moi", slug
    if subdomain_key == "thue_thu_nhap_ca_nhan":
        return "khai_thue_tncn_tu_tien_luong_tien_cong", slug
    if "khong_thuoc_dien_cap_giay_phep" in slug:
        if "cap_lai" in slug:
            return "cap_lai_xac_nhan_mien_gpld", slug
        if "gia_han" in slug:
            return "gia_han_xac_nhan_mien_gpld", slug
        return "cap_xac_nhan_mien_gpld", slug
    if "lao_dong_ket_hop_ky_nghi" in slug or "lam_viec_trong_ky_nghi" in slug:
        if "cap_lai" in slug:
            return "cap_lai_gpld_ky_nghi_ket_hop_lao_dong", slug
        return "cap_gpld_ky_nghi_ket_hop_lao_dong", slug
    if "chuyen_gia_khoa_hoc_cong_nghe" in slug:
        if "cap_lai" in slug:
            return "cap_lai_gpld_chuyen_gia_khcn", slug
        if "bao_cao" in slug:
            return "bao_cao_mien_gpld_chuyen_gia_khcn", slug
        return "cap_gpld_chuyen_gia_khcn", slug
    if "cap_lai_giay_phep_lao_dong" in slug:
        return "cap_lai_gpld_nguoi_nuoc_ngoai", slug
    if "gia_han_giay_phep_lao_dong" in slug:
        return "gia_han_gpld_nguoi_nuoc_ngoai", slug
    return "cap_gpld_nguoi_nuoc_ngoai", slug


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
        "start_node": "employment_subdomain",
        "nodes": [
            {
                "id": "employment_subdomain",
                "type": "question",
                "slot": "subdomain_key",
                "question": "Bạn đang hỏi về hỗ trợ việc làm, tuyển dụng, trợ cấp thất nghiệp, chứng chỉ nghề, nâng cao kỹ năng, thuế thu nhập cá nhân hay giấy phép lao động cho người nước ngoài?",
                "options": list(SUBDOMAINS.keys()),
            },
            {
                "id": "employment_operation",
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
                    "subdomain_key": "ho_tro_tu_van_gioi_thieu_viec_lam | tuyen_dung | bao_hiem_xa_hoi_that_nghiep_tro_cap | chung_chi_hanh_nghe | nang_ngach | thue_thu_nhap_ca_nhan | cap_phep_lao_dong_nguoi_nuoc_ngoai | unknown",
                    "operation_key": "string",
                    "operation_group": "string",
                },
                "confidence": "0_to_1",
                "needs_human_review": "boolean",
            },
        },
        "entry_prompts": [
            "Bạn đang cần tìm việc, nhận trợ cấp thất nghiệp, học nâng cao kỹ năng, khai thuế thu nhập hay làm giấy phép lao động?",
            "Bạn muốn đăng ký mới, điều chỉnh thông tin, xin hỗ trợ, xin cấp chứng chỉ hay xin giấy phép làm việc?",
        ],
        "slots": [
            {
                "name": "subdomain_key",
                "required": True,
                "description": "Nhánh chính của nhóm Việc làm.",
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
                "field_group": "employment_support",
                "checks": [
                    "Nhóm hỗ trợ việc làm và tuyển dụng phải làm rõ người dùng đang tìm việc, cập nhật tình trạng lao động hay xin hỗ trợ chi phí/liên kết việc làm.",
                    "Nếu là đăng ký hoặc điều chỉnh lao động, cần xác định rõ trạng thái hiện tại: có việc làm, thất nghiệp hay không tham gia hoạt động kinh tế.",
                ],
            },
            {
                "field_group": "unemployment_and_skills",
                "checks": [
                    "Nhóm thất nghiệp phải phân biệt rõ nộp hồ sơ hưởng mới, thông báo tìm việc hằng tháng, tiếp tục hưởng, tạm dừng, chấm dứt hay chuyển nơi hưởng.",
                    "Nhóm chứng chỉ và nâng cao kỹ năng phải làm rõ đây là cấp chứng chỉ, cấp lại hay xin hỗ trợ đào tạo/nâng cao kỹ năng nghề.",
                ],
            },
            {
                "field_group": "tax_and_foreign_work",
                "checks": [
                    "Nhóm thuế chỉ áp dụng cho khai thuế thu nhập cá nhân trực tiếp từ tiền lương, tiền công trong bộ workflow sạch này.",
                    "Nhóm giấy phép lao động cho người nước ngoài phải làm rõ là cấp mới, cấp lại, gia hạn hay xác nhận miễn giấy phép lao động.",
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
    marker = "  - `cu_tru_giay_to` (da co workflow dataset va test data cho 37 ma thu tuc / 6 subdomain)\n"
    addition = "  - `viec_lam` (da co workflow dataset va test data cho 43 ma thu tuc / 7 subdomain)\n"
    if addition not in text and marker in text:
        text = text.replace(marker, marker + addition, 1)
    next_marker = "1. Mo rong cach lam nay sang `viec_lam`\n"
    if next_marker in text:
        text = text.replace(next_marker, "1. Mo rong cach lam nay sang `co_con_nho`\n", 1)
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
