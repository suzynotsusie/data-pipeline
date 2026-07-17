import urllib.request
import json
import sys
import re
from urllib.parse import urlparse

# Set output encoding to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')

def clean_html(text):
    if not text:
        return ""
    # Strip HTML tags
    clean = re.sub(r'<[^>]+>', '\n', text)
    # Replace multiple newlines with single/double newlines
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

def extract_raw_text(url):
    parsed = urlparse(url)
    procedure_id = parsed.path.rstrip("/").split("/")[-1] if parsed.path else None
    
    if not procedure_id:
        return "Invalid URL"
        
    api_url = "https://dichvucong.gov.vn/api/v1/configuring/formality/get-formality-by-citizen"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json; charset=UTF-8",
    }
    
    payload = json.dumps({"id": procedure_id}).encode('utf-8')
    req = urllib.request.Request(api_url, data=payload, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as resp:
            api_data = json.loads(resp.read().decode('utf-8')).get("data", {})
            if not api_data:
                return "No data found"
                
            output = []
            output.append(f"=== TÊN THỦ TỤC: {api_data.get('name')} ===")
            output.append(f"Mã số: {api_data.get('code')}")
            output.append(f"Số quyết định: {api_data.get('decisionNo') or 'N/A'}")
            output.append(f"Cấp thực hiện: {get_implementing_level(api_data)}")
            output.append(f"Lĩnh vực: {api_data.get('category', {}).get('name') if api_data.get('category') else 'N/A'}")
            output.append(f"Đối tượng thực hiện: {', '.join([s.get('name') for s in api_data.get('subjectTypesDetails', []) if s.get('name')]) or 'N/A'}")
            output.append(f"Cơ quan ban hành: {api_data.get('departmentPromulgateName') or 'N/A'}")
            output.append(f"Địa chỉ tiếp nhận HS: {api_data.get('dossierReceivingAddresses') or 'N/A'}")
            output.append(f"Cơ quan phối hợp: {api_data.get('coordinatingAgencies') or 'N/A'}")
            
            # Trình tự thực hiện
            output.append("\n--- TRÌNH TỰ THỰC HIỆN ---")
            steps = api_data.get("executionSteps", [])
            for i, step in enumerate(steps):
                step_name = step.get("name", "").strip()
                step_desc = clean_html(step.get("description", ""))
                if step_name:
                    output.append(f"Bước {i+1}. {step_name}:\n{step_desc}")
                else:
                    output.append(step_desc)
            
            # Cách thức thực hiện
            output.append("\n--- CÁCH THỨC THỰC HIỆN ---")
            methods = api_data.get("executionMethods", [])
            for method in methods:
                method_name = method.get("name", "").strip()
                method_desc = clean_html(method.get("description", ""))
                output.append(f"+ {method_name}: {method_desc}")
                
            # Thành phần hồ sơ
            output.append("\n--- THÀNH PHẦN HỒ SƠ ---")
            exec_cases = api_data.get("executionCases", [])
            for case in exec_cases:
                case_name = case.get("name", "").strip()
                output.append(f"\n[{case_name}]")
                components = case.get("profileComponents", [])
                for idx, comp in enumerate(components):
                    comp_name = comp.get("name", "").strip()
                    orig_qty = comp.get("originalQty")
                    copy_qty = comp.get("copyQty")
                    
                    qty_str = ""
                    if orig_qty is not None:
                        qty_str += f"{orig_qty} bản chính"
                    if copy_qty is not None:
                        if qty_str:
                            qty_str += ", "
                        qty_str += f"{copy_qty} bản sao"
                        
                    qty_info = f" ({qty_str})" if qty_str else ""
                    
                    # Parse attachments if any
                    attachments = comp.get("attachments", [])
                    att_info = []
                    for att in attachments:
                        att_name = att.get("fileName")
                        att_path = att.get("filePath")
                        if att_name and att_path:
                            # Construct the full download URL
                            download_url = f"https://dichvucong.gov.vn/{att_path}"
                            att_info.append(f"   + File đính kèm: {att_name}\n   + Link tải: {download_url}")
                    
                    comp_text = f"{idx+1}. {comp_name}{qty_info}"
                    if att_info:
                        comp_text += "\n" + "\n".join(att_info)
                    output.append(comp_text)
            
            # Yêu cầu điều kiện
            output.append("\n--- YÊU CẦU, ĐIỀU KIỆN ---")
            reqs = api_data.get("requirementsAndConditions", [])
            if isinstance(reqs, str):
                output.append(clean_html(reqs))
            elif isinstance(reqs, list):
                for req_item in reqs:
                    if isinstance(req_item, dict):
                        output.append(clean_html(req_item.get("content") or req_item.get("name")))
                    else:
                        output.append(clean_html(str(req_item)))
            
            # Căn cứ pháp lý
            output.append("\n--- CĂN CỨ PHÁP LÝ ---")
            basis = api_data.get("legalBasisesDetails", [])
            for b in basis:
                output.append(f"- {b.get('name')} (Số hiệu: {b.get('code')})")
                
            # Kết quả thực hiện
            output.append("\n--- KẾT QUẢ THỰC HIỆN ---")
            results = api_data.get("resultsDetails", [])
            for r in results:
                output.append(f"- {r.get('name')}")
                
            return "\n".join(output)
            
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sử dụng: python extract_raw_text.py <url>")
        sys.exit(1)
    url = sys.argv[1]
    print(extract_raw_text(url))
