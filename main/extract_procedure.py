import urllib.request
import json
import sys
import os
import re
import csv
from urllib.parse import urlparse, quote
from playwright.sync_api import sync_playwright

# Ensure output encoding is UTF-8
sys.stdout.reconfigure(encoding='utf-8')

def clean_html(text):
    if not text:
        return ""
    # Strip HTML tags
    clean = re.sub(r'<[^>]+>', '\n', text)
    # Replace multiple newlines
    clean = re.sub(r'\n+', '\n', clean)
    return clean.strip()

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
    val = data.get("formalityType")
    if not val:
        return None
    mapping = {
        "ASSIGNED_REGULATION": "TTHC được luật giao quy định chi tiết",
        "STANDARD": "Thủ tục hành chính tiêu chuẩn"
    }
    return mapping.get(val, val)

def format_fees(fee_list):
    if not fee_list:
        return "Không có thông tin"
    fee_strs = []
    for f in fee_list:
        name = f.get("name")
        amount = f.get("amount")
        if name and amount is not None:
            fee_strs.append(f"{name}: {amount} VNĐ")
        elif name:
            fee_strs.append(name)
        elif amount is not None:
            fee_strs.append(f"{amount} VNĐ")
    return ", ".join(fee_strs) if fee_strs else "Không có thông tin"

def format_or_none(val, fallback="Không có thông tin"):
    if not val:
        return fallback
    cleaned = clean_html(str(val))
    return cleaned if cleaned else fallback

def run_extraction(url, base_raw_dir="C:/Users/ku060/Downloads/data/raw_data"):
    parsed = urlparse(url)
    procedure_id = parsed.path.rstrip("/").split("/")[-1] if parsed.path else None
    
    if not procedure_id:
        print(f"Đường dẫn URL '{url}' không hợp lệ.")
        return
        
    api_url = "https://dichvucong.gov.vn/api/v1/configuring/formality/get-formality-by-citizen"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json; charset=UTF-8",
    }
    
    payload = json.dumps({"id": procedure_id}).encode('utf-8')
    req = urllib.request.Request(api_url, data=payload, headers=headers, method="POST")
    
    print(f"Đang tải dữ liệu từ API cho thủ tục ID: {procedure_id}...")
    try:
        with urllib.request.urlopen(req) as resp:
            api_data = json.loads(resp.read().decode('utf-8')).get("data", {})
            if not api_data:
                print("Không tìm thấy dữ liệu thủ tục.")
                return
                
            code_str = api_data.get("code", "procedure").replace(".", "_")
            output_dir = os.path.join(base_raw_dir, code_str)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            md = []
            
            # Title
            md.append(f"# {api_data.get('name')}\n")
            
            # Metadata List
            md.append("## Thông tin chung\n")
            md.append(f"* **Mã thủ tục:** {format_or_none(api_data.get('code'))}")
            proposal_no = api_data.get("procedureProposal", {}).get("proposalNumber")
            md.append(f"* **Số quyết định:** {format_or_none(proposal_no)}")
            md.append(f"* **Cấp thực hiện:** {format_or_none(get_implementing_level(api_data))}")
            md.append(f"* **Loại thủ tục:** {format_or_none(get_formality_type(api_data))}")
            
            categories = [c.get("name") for c in api_data.get("categoriesDetails", []) if c.get("name")]
            md.append(f"* **Lĩnh vực:** {format_or_none(', '.join(categories))}")
            
            subjects = [s.get('name') for s in api_data.get('subjectTypesDetails', []) if s.get('name')]
            md.append(f"* **Đối tượng thực hiện:** {format_or_none(', '.join(subjects))}")
            
            auth_agencies = [a.get('name') for a in api_data.get('departmentsAuthority', []) if a.get('name')]
            md.append(f"* **Cơ quan có thẩm quyền:** {format_or_none(', '.join(auth_agencies))}")
            md.append(f"* **Địa chỉ tiếp nhận HS:** {format_or_none(api_data.get('dossierReceivingAddresses'))}")
            
            authorized = [a.get('name') for a in api_data.get('departmentsAuthorized', []) if a.get('name')]
            md.append(f"* **Cơ quan được ủy quyền:** {format_or_none(', '.join(authorized))}")
            
            coordinating = [c.get('name') for c in api_data.get('departmentsCoordinating', []) if c.get('name')]
            md.append(f"* **Cơ quan phối hợp:** {format_or_none(', '.join(coordinating))}\n")
            
            # --- SECTIONS ---
            
            # 1. Thủ tục hành chính liên quan
            md.append("## Thủ tục hành chính liên quan\n")
            related = api_data.get("procedureRelatedGroup", [])
            if related:
                for r in related:
                    md.append(f"* {r.get('name')} (Mã: `{r.get('code')}`)")
                md.append("")
            else:
                md.append("Không có thông tin\n")
            
            # 2. Trình tự thực hiện
            md.append("## Trình tự thực hiện\n")
            steps = api_data.get("executionSteps", [])
            if steps:
                for i, step in enumerate(steps):
                    step_name = step.get("name", "").strip()
                    step_desc = clean_html(step.get("description", ""))
                    if step_name:
                        md.append(f"{i+1}. **{step_name}**\n\n   {step_desc.replace('\n', '\n   ')}\n")
                    else:
                        md.append(f"{i+1}. {step_desc.replace('\n', '\n   ')}\n")
            else:
                md.append("Không có thông tin\n")
            
            # 3. Cách thức thực hiện
            md.append("## Cách thức thực hiện\n")
            methods = api_data.get("executionMethods", [])
            if methods:
                md.append("| Hình thức nộp | Thời gian giải quyết | Phí, lệ phí | Mô tả |")
                md.append("| --- | --- | --- | --- |")
                method_map = {
                    "ONLINE": "Trực tuyến",
                    "POSTAL": "Dịch vụ bưu chính",
                    "DIRECT": "Trực tiếp"
                }
                for method in methods:
                    sub_method = method.get("submissionMethod", "")
                    method_name = method_map.get(sub_method, sub_method or "Khác")
                    
                    time_val = method.get("processingTime")
                    time_unit = method.get("processingTimeUnit")
                    time_unit_str = "ngày làm việc" if time_unit == "WORKING_DAY" else "ngày"
                    time_info = f"{time_val} {time_unit_str}" if time_val else "N/A"
                    
                    fee_info = format_fees(method.get("fees", []))
                    
                    method_desc = clean_html(method.get("description", ""))
                    if not method_desc:
                        method_desc = "Không có thông tin"
                    method_desc_cell = method_desc.replace('\n', '<br>')
                    md.append(f"| {method_name} | {time_info} | {fee_info} | {method_desc_cell} |")
                md.append("")
            else:
                md.append("Không có thông tin\n")
                
            # 4. Thành phần hồ sơ
            md.append("## Thành phần hồ sơ\n")
            exec_cases = api_data.get("executionCases", [])
            attachments = []
            if exec_cases:
                for case in exec_cases:
                    case_name = case.get("name", "").strip()
                    if case_name:
                        md.append(f"### {case_name}\n")
                    
                    md.append("| Tên giấy tờ | Bản chính | Bản sao | Tệp đính kèm |")
                    md.append("| --- | --- | --- | --- |")
                    
                    components = case.get("profileComponents", [])
                    for comp in components:
                        comp_name = comp.get("name", "").strip().replace('\n', '<br>')
                        orig_qty = comp.get("originalQty")
                        copy_qty = comp.get("copyQty")
                        
                        orig_str = str(orig_qty) if orig_qty is not None else "0"
                        copy_str = str(copy_qty) if copy_qty is not None else "0"
                        
                        comp_atts = comp.get("attachments", [])
                        att_links = []
                        for att in comp_atts:
                            fname = att.get("fileName")
                            if fname:
                                attachments.append(att)
                                encoded_name = quote(fname)
                                local_link = f"file:///C:/Users/ku060/Downloads/data/raw_data/{code_str}/{encoded_name}"
                                att_links.append(f"[{fname}]({local_link})")
                                
                        att_cell = "<br>".join(att_links) if att_links else "Không có"
                        md.append(f"| {comp_name} | {orig_str} | {copy_str} | {att_cell} |")
                    md.append("")
            else:
                md.append("Không có thông tin\n")
            
            # 5. Căn cứ pháp lý
            md.append("## Căn cứ pháp lý\n")
            basis = api_data.get("legalBasisesDetails", [])
            if basis:
                md.append("| Tên văn bản pháp lý | Mã văn bản |")
                md.append("| --- | --- |")
                for b in basis:
                    name = b.get("name", "").strip().replace('\n', '<br>')
                    code = b.get("code", "").strip()
                    md.append(f"| {name} | {code} |")
                md.append("")
            else:
                md.append("Không có thông tin\n")
                
            # 6. Cơ quan thực hiện
            md.append("## Cơ quan thực hiện\n")
            executing = [e.get('name') for e in api_data.get('departmentsExecuting', []) if e.get('name')]
            md.append(format_or_none(", ".join(executing)) + "\n")
            
            # 7. Yêu cầu, điều kiện thực hiện
            md.append("## Yêu cầu, điều kiện thực hiện\n")
            reqs = api_data.get("requirementsAndConditions", [])
            if isinstance(reqs, str) and reqs.strip():
                md.append(clean_html(reqs) + "\n")
            elif isinstance(reqs, list) and reqs:
                for req_item in reqs:
                    if isinstance(req_item, dict):
                        md.append(f"* {clean_html(req_item.get('content') or req_item.get('name'))}")
                    else:
                        md.append(f"* {clean_html(str(req_item))}")
                md.append("")
            else:
                md.append("Không có thông tin\n")
                
            # 8. Kết quả xử lý
            md.append("## Kết quả xử lý\n")
            results = api_data.get("resultsDetails", [])
            if results:
                for r in results:
                    md.append(f"* {r.get('name')} (Mã: `{r.get('code')}`)")
                md.append("")
            else:
                md.append("Không có thông tin\n")
                
            # 9. Từ khóa
            md.append("## Từ khóa\n")
            md.append(format_or_none(api_data.get("keywords")) + "\n")
            
            # 10. Mô tả
            md.append("## Mô tả\n")
            md.append(format_or_none(api_data.get("description")) + "\n")
            
            # Save markdown file inside the raw_data/<code_str> folder
            final_md_text = "\n".join(md)
            md_filename = f"{code_str}_procedure_detail.md"
            md_path = os.path.join(output_dir, md_filename)
            
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(final_md_text)
                
            print(f"=> Đã xuất Markdown thành công ra file: {md_path}")
            
            # Handle attachments download
            if attachments:
                print(f"   Tìm thấy {len(attachments)} file đính kèm cần tải về.")
                print("   Đang khởi tạo trình duyệt giả lập để tải file...")
                
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                        viewport={"width": 1280, "height": 800}
                    )
                    page = context.new_page()
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    page.wait_for_selector("text=Thành phần hồ sơ", timeout=15000)
                    page.wait_for_timeout(3000)
                    
                    for idx, att in enumerate(attachments):
                        filename = att.get("fileName")
                        print(f"   [{idx+1}/{len(attachments)}] Đang tải file: {filename}")
                        
                        rows = page.locator("tr").all()
                        target_row = None
                        for row in rows:
                            if filename in row.inner_text():
                                target_row = row
                                break
                                
                        if not target_row:
                            print(f"      -> Không tìm thấy hàng hiển thị file '{filename}' trên giao diện.")
                            continue
                            
                        btn = target_row.locator("button").first
                        if btn:
                            try:
                                with page.expect_download(timeout=15000) as download_info:
                                    btn.click()
                                download = download_info.value
                                save_path = os.path.join(output_dir, download.suggested_filename)
                                download.save_as(save_path)
                                print(f"      -> Tải thành công! Đã lưu tại: {save_path}")
                            except Exception as e:
                                print(f"      -> Lỗi khi tải file: {e}")
                        else:
                            print(f"      -> Không tìm thấy nút tải cho file '{filename}'.")
                            
                    browser.close()
            else:
                print("   Thủ tục này không có file đính kèm nào.")
                
    except Exception as e:
        print(f"Lỗi khi xử lý thủ tục {url}: {e}")

def process_csv_files(main_dir="C:/Users/ku060/Downloads/data/main"):
    # Find all CSV files in the folder
    csv_files = [f for f in os.listdir(main_dir) if f.endswith(".csv")]
    if not csv_files:
        print(f"Không tìm thấy file CSV nào trong {main_dir}.")
        return
        
    print(f"Tìm thấy {len(csv_files)} file CSV cần xử lý.")
    processed_urls = set()
    
    for csv_file in csv_files:
        csv_path = os.path.join(main_dir, csv_file)
        print(f"\nĐang đọc dữ liệu từ file: {csv_file}...")
        
        try:
            with open(csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None) # skip header
                
                for row in reader:
                    if not row or len(row) < 2:
                        continue
                    # The last column contains the link
                    ma_so = row[0].strip()
                    url = row[-1].strip()
                    
                    if url.startswith("http"):
                        if url in processed_urls:
                            print(f"Bỏ qua URL trùng lặp đã xử lý: {url}")
                            continue
                        processed_urls.add(url)
                        print(f"\n--------------------------------------------------")
                        print(f"Bắt đầu xử lý thủ tục: {ma_so}")
                        run_extraction(url)
        except Exception as e:
            print(f"Lỗi khi đọc file CSV {csv_file}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single URL execution mode
        url = sys.argv[1]
        run_extraction(url)
    else:
        # Default: Process all CSVs in the main folder
        process_csv_files()
