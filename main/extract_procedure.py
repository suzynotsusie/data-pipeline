import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import quote, urlparse

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:
    sync_playwright = None


sys.stdout.reconfigure(encoding="utf-8")


DEFAULT_MAIN_DIR = "C:/Users/ku060/Downloads/VAIC source/data-pipeline/main"
DEFAULT_RAW_DIR = "C:/Users/ku060/Downloads/VAIC source/data-pipeline/raw_data"
API_URL = "https://dichvucong.gov.vn/api/v1/configuring/formality/get-formality-by-citizen"


def clean_html(text):
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", "\n", text)
    cleaned = re.sub(r"\n+", "\n", cleaned)
    return cleaned.strip()


def format_or_none(value, fallback="Không có thông tin"):
    if not value:
        return fallback
    cleaned = clean_html(str(value))
    return cleaned if cleaned else fallback


def get_implementing_level(data):
    levels = []
    if data.get("isWard"):
        levels.append("Cấp xã")
    if data.get("isProvince"):
        levels.append("Cấp tỉnh")
    if data.get("isMinistry"):
        levels.append("Cấp bộ/ngành")
    if data.get("isOtherAgency"):
        levels.append("Cơ quan khác")
    return ", ".join(levels) if levels else "N/A"


def get_formality_type(data):
    value = data.get("formalityType")
    if not value:
        return None
    mapping = {
        "ASSIGNED_REGULATION": "TTHC được luật giao quy định chi tiết",
        "STANDARD": "Thủ tục hành chính tiêu chuẩn",
    }
    return mapping.get(value, value)


def format_fees(fee_list):
    if not fee_list:
        return "Không có thông tin"
    parts = []
    for fee in fee_list:
        name = fee.get("name")
        amount = fee.get("amount")
        if name and amount is not None:
            parts.append(f"{name}: {amount} VNĐ")
        elif name:
            parts.append(name)
        elif amount is not None:
            parts.append(f"{amount} VNĐ")
    return ", ".join(parts) if parts else "Không có thông tin"


def extract_url_from_row(row):
    for cell in reversed(row):
        value = cell.strip()
        if value.startswith("http"):
            return value
    return ""


def make_attachment_link(base_raw_dir, code_str, filename):
    encoded_name = quote(filename)
    normalized_raw_dir = base_raw_dir.replace("\\", "/")
    return f"file:///{normalized_raw_dir}/{code_str}/{encoded_name}"


def download_attachments(page_url, attachments, output_dir):
    if not attachments:
        print("   Thủ tục này không có file đính kèm nào.")
        return

    print(f"   Tìm thấy {len(attachments)} file đính kèm cần tải về.")
    if sync_playwright is None:
        print("   Bỏ qua bước tải file đính kèm vì chưa cài playwright trong môi trường hiện tại.")
        return

    print("   Đang khởi tạo trình duyệt giả lập để tải file...")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        page.goto(page_url, wait_until="networkidle", timeout=30000)
        page.wait_for_selector("text=Thành phần hồ sơ", timeout=15000)
        page.wait_for_timeout(3000)

        for index, attachment in enumerate(attachments, start=1):
            filename = attachment.get("fileName")
            print(f"   [{index}/{len(attachments)}] Đang tải file: {filename}")

            rows = page.locator("tr").all()
            target_row = None
            for row in rows:
                if filename in row.inner_text():
                    target_row = row
                    break

            if not target_row:
                print(f"      -> Không tìm thấy hàng hiển thị file '{filename}' trên giao diện.")
                continue

            button = target_row.locator("button").first
            if not button:
                print(f"      -> Không tìm thấy nút tải cho file '{filename}'.")
                continue

            try:
                with page.expect_download(timeout=15000) as download_info:
                    button.click()
                download = download_info.value
                save_path = os.path.join(output_dir, download.suggested_filename)
                download.save_as(save_path)
                print(f"      -> Tải thành công! Đã lưu tại: {save_path}")
            except Exception as exc:
                print(f"      -> Lỗi khi tải file: {exc}")

        browser.close()


def build_markdown(api_data, url, base_raw_dir):
    code_str = api_data.get("code", "procedure").replace(".", "_")
    attachments = []
    md = []

    md.append(f"# {api_data.get('name')}\n")

    md.append("## Thông tin chung\n")
    md.append(f"* **Mã thủ tục:** {format_or_none(api_data.get('code'))}")
    proposal_no = api_data.get("procedureProposal", {}).get("proposalNumber")
    md.append(f"* **Số quyết định:** {format_or_none(proposal_no)}")
    md.append(f"* **Cấp thực hiện:** {format_or_none(get_implementing_level(api_data))}")
    md.append(f"* **Loại thủ tục:** {format_or_none(get_formality_type(api_data))}")

    categories = [item.get("name") for item in api_data.get("categoriesDetails", []) if item.get("name")]
    md.append(f"* **Lĩnh vực:** {format_or_none(', '.join(categories))}")

    subjects = [item.get("name") for item in api_data.get("subjectTypesDetails", []) if item.get("name")]
    md.append(f"* **Đối tượng thực hiện:** {format_or_none(', '.join(subjects))}")

    authorities = [item.get("name") for item in api_data.get("departmentsAuthority", []) if item.get("name")]
    md.append(f"* **Cơ quan có thẩm quyền:** {format_or_none(', '.join(authorities))}")
    md.append(f"* **Địa chỉ tiếp nhận HS:** {format_or_none(api_data.get('dossierReceivingAddresses'))}")

    authorized = [item.get("name") for item in api_data.get("departmentsAuthorized", []) if item.get("name")]
    md.append(f"* **Cơ quan được ủy quyền:** {format_or_none(', '.join(authorized))}")

    coordinating = [item.get("name") for item in api_data.get("departmentsCoordinating", []) if item.get("name")]
    md.append(f"* **Cơ quan phối hợp:** {format_or_none(', '.join(coordinating))}\n")

    md.append("## Thủ tục hành chính liên quan\n")
    related = api_data.get("procedureRelatedGroup", [])
    if related:
        for item in related:
            md.append(f"* {item.get('name')} (Mã: `{item.get('code')}`)")
        md.append("")
    else:
        md.append("Không có thông tin\n")

    md.append("## Trình tự thực hiện\n")
    steps = api_data.get("executionSteps", [])
    if steps:
        for index, step in enumerate(steps, start=1):
            step_name = (step.get("name") or "").strip()
            description = clean_html(step.get("description", ""))
            if step_name:
                md.append(f"{index}. **{step_name}**\n\n   {description.replace(chr(10), chr(10) + '   ')}\n")
            else:
                md.append(f"{index}. {description.replace(chr(10), chr(10) + '   ')}\n")
    else:
        md.append("Không có thông tin\n")

    md.append("## Cách thức thực hiện\n")
    methods = api_data.get("executionMethods", [])
    if methods:
        md.append("| Hình thức nộp | Thời gian giải quyết | Phí, lệ phí | Mô tả |")
        md.append("| --- | --- | --- | --- |")
        method_map = {
            "ONLINE": "Trực tuyến",
            "POSTAL": "Dịch vụ bưu chính",
            "DIRECT": "Trực tiếp",
        }
        for method in methods:
            method_name = method_map.get(method.get("submissionMethod", ""), method.get("submissionMethod", "") or "Khác")
            time_value = method.get("processingTime")
            time_unit = method.get("processingTimeUnit")
            time_unit_label = "ngày làm việc" if time_unit == "WORKING_DAY" else "ngày"
            time_info = f"{time_value} {time_unit_label}" if time_value else "N/A"
            fee_info = format_fees(method.get("fees", []))
            description = clean_html(method.get("description", "")) or "Không có thông tin"
            md.append(f"| {method_name} | {time_info} | {fee_info} | {description.replace(chr(10), '<br>')} |")
        md.append("")
    else:
        md.append("Không có thông tin\n")

    md.append("## Thành phần hồ sơ\n")
    execution_cases = api_data.get("executionCases", [])
    if execution_cases:
        for execution_case in execution_cases:
            case_name = (execution_case.get("name") or "").strip()
            if case_name:
                md.append(f"### {case_name}\n")

            md.append("| Tên giấy tờ | Bản chính | Bản sao | Tệp đính kèm |")
            md.append("| --- | --- | --- | --- |")

            for component in execution_case.get("profileComponents", []):
                name = (component.get("name") or "").strip().replace("\n", "<br>")
                original_qty = component.get("originalQty")
                copy_qty = component.get("copyQty")
                original_str = str(original_qty) if original_qty is not None else "0"
                copy_str = str(copy_qty) if copy_qty is not None else "0"

                component_links = []
                for attachment in component.get("attachments", []):
                    filename = attachment.get("fileName")
                    if not filename:
                        continue
                    attachments.append(attachment)
                    component_links.append(f"[{filename}]({make_attachment_link(base_raw_dir, code_str, filename)})")

                attachment_cell = "<br>".join(component_links) if component_links else "Không có"
                md.append(f"| {name} | {original_str} | {copy_str} | {attachment_cell} |")
            md.append("")
    else:
        md.append("Không có thông tin\n")

    md.append("## Căn cứ pháp lý\n")
    legal_basises = api_data.get("legalBasisesDetails", [])
    if legal_basises:
        md.append("| Tên văn bản pháp lý | Mã văn bản |")
        md.append("| --- | --- |")
        for item in legal_basises:
            name = (item.get("name") or "").strip().replace("\n", "<br>")
            code = (item.get("code") or "").strip()
            md.append(f"| {name} | {code} |")
        md.append("")
    else:
        md.append("Không có thông tin\n")

    md.append("## Cơ quan thực hiện\n")
    executing = [item.get("name") for item in api_data.get("departmentsExecuting", []) if item.get("name")]
    md.append(format_or_none(", ".join(executing)) + "\n")

    md.append("## Yêu cầu, điều kiện thực hiện\n")
    requirements = api_data.get("requirementsAndConditions", [])
    if isinstance(requirements, str) and requirements.strip():
        md.append(clean_html(requirements) + "\n")
    elif isinstance(requirements, list) and requirements:
        for item in requirements:
            if isinstance(item, dict):
                md.append(f"* {clean_html(item.get('content') or item.get('name'))}")
            else:
                md.append(f"* {clean_html(str(item))}")
        md.append("")
    else:
        md.append("Không có thông tin\n")

    md.append("## Kết quả xử lý\n")
    results = api_data.get("resultsDetails", [])
    if results:
        for item in results:
            md.append(f"* {item.get('name')} (Mã: `{item.get('code')}`)")
        md.append("")
    else:
        md.append("Không có thông tin\n")

    md.append("## Từ khóa\n")
    md.append(format_or_none(api_data.get("keywords")) + "\n")

    md.append("## Mô tả\n")
    md.append(format_or_none(api_data.get("description")) + "\n")

    return code_str, "\n".join(md), attachments


def run_extraction(url, base_raw_dir=DEFAULT_RAW_DIR):
    parsed = urlparse(url)
    procedure_id = parsed.path.rstrip("/").split("/")[-1] if parsed.path else None
    if not procedure_id:
        print(f"Đường dẫn URL không hợp lệ: {url}")
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json; charset=UTF-8",
    }
    payload = json.dumps({"id": procedure_id}).encode("utf-8")
    request = urllib.request.Request(API_URL, data=payload, headers=headers, method="POST")

    print(f"Đang tải dữ liệu từ API cho thủ tục ID: {procedure_id}...")
    try:
        with urllib.request.urlopen(request) as response:
            api_data = json.loads(response.read().decode("utf-8")).get("data", {})
    except urllib.error.HTTPError as exc:
        if exc.code == 400:
            print(f"   Bỏ qua thủ tục do API trả về 400 cho ID {procedure_id}. URL này có thể không tồn tại hoặc không hợp lệ trên DVCQG.")
            return
        print(f"Lỗi HTTP khi xử lý thủ tục {url}: {exc}")
        return
    except Exception as exc:
        print(f"Lỗi khi xử lý thủ tục {url}: {exc}")
        return

    if not api_data:
        print("Không tìm thấy dữ liệu thủ tục.")
        return

    code_str, markdown_text, attachments = build_markdown(api_data, url, base_raw_dir)
    output_dir = os.path.join(base_raw_dir, code_str)
    os.makedirs(output_dir, exist_ok=True)

    md_path = os.path.join(output_dir, f"{code_str}_procedure_detail.md")
    with open(md_path, "w", encoding="utf-8") as file:
        file.write(markdown_text)

    print(f"=> Đã xuất Markdown thành công ra file: {md_path}")
    download_attachments(url, attachments, output_dir)


def process_csv_rows(reader, base_raw_dir):
    processed_urls = set()
    for row in reader:
        if not row or len(row) < 2:
            continue

        ma_so = row[0].strip()
        url = extract_url_from_row(row)
        if not url.startswith("http"):
            print(f"Bỏ qua dòng không có URL hợp lệ cho mã {ma_so}: {url}")
            continue

        if url in processed_urls:
            print(f"Bỏ qua URL trùng lặp đã xử lý: {url}")
            continue

        processed_urls.add(url)
        print("\n--------------------------------------------------")
        print(f"Bắt đầu xử lý thủ tục: {ma_so}")
        run_extraction(url, base_raw_dir=base_raw_dir)


def process_single_csv_file(csv_path, base_raw_dir=DEFAULT_RAW_DIR):
    csv_file = os.path.basename(csv_path)
    print(f"\nĐang đọc dữ liệu từ file: {csv_file}...")
    try:
        with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file)
            header = next(reader, None)
            if not header:
                print(f"File CSV rỗng hoặc không có header: {csv_path}")
                return
            process_csv_rows(reader, base_raw_dir)
    except Exception as exc:
        print(f"Lỗi khi đọc file CSV {csv_path}: {exc}")


def process_csv_files(main_dir=DEFAULT_MAIN_DIR, base_raw_dir=DEFAULT_RAW_DIR):
    csv_files = sorted(name for name in os.listdir(main_dir) if name.lower().endswith(".csv"))
    if not csv_files:
        print(f"Không tìm thấy file CSV nào trong {main_dir}.")
        return

    print(f"Tìm thấy {len(csv_files)} file CSV cần xử lý.")
    for csv_file in csv_files:
        process_single_csv_file(os.path.join(main_dir, csv_file), base_raw_dir=base_raw_dir)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Trích xuất chi tiết thủ tục từ URL hoặc file CSV cùng định dạng."
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="URL chi tiết một thủ tục trên dichvucong.gov.vn",
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        help="Đường dẫn tới một file CSV cùng định dạng với file mẫu",
    )
    parser.add_argument(
        "--dir",
        dest="csv_dir",
        default=DEFAULT_MAIN_DIR,
        help="Thư mục chứa các file CSV cần xử lý",
    )
    parser.add_argument(
        "--raw-dir",
        dest="raw_dir",
        default=DEFAULT_RAW_DIR,
        help="Thư mục lưu kết quả raw_data",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.url:
        run_extraction(arguments.url, base_raw_dir=arguments.raw_dir)
    elif arguments.csv_path:
        process_single_csv_file(arguments.csv_path, base_raw_dir=arguments.raw_dir)
    else:
        process_csv_files(main_dir=arguments.csv_dir, base_raw_dir=arguments.raw_dir)
