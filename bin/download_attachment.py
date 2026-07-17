import sys
import os
import re
from playwright.sync_api import sync_playwright

def download_file(url, file_pattern=None, output_dir="C:/Users/ku060/Downloads/data"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"Khởi tạo trình duyệt headless để truy cập: {url}")
    with sync_playwright() as p:
        # Launch chromium (headless=True to run in background, set false if you want to see it)
        browser = p.chromium.launch(headless=True)
        # Set viewport and user-agent to resemble a real browser
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        # Navigate to the page
        print("Đang tải trang web và vượt qua kiểm tra WAF...")
        page.goto(url, wait_until="networkidle", timeout=30000)
        
        # Wait a bit for React to render components and resolve APIs
        print("Đang đợi các thành phần hồ sơ tải xuống...")
        page.wait_for_selector("text=Thành phần hồ sơ", timeout=15000)
        page.wait_for_timeout(3000) # Thêm thời gian chờ ổn định
        
        # Find rows containing file attachments (.doc, .docx, .pdf, or matching pattern)
        rows = page.locator("tr").all()
        matching_row = None
        target_filename = ""
        
        for row in rows:
            text = row.inner_text()
            # If pattern is provided, search by pattern, else search for any .doc / .docx / .pdf file row
            if file_pattern:
                if re.search(file_pattern, text, re.IGNORECASE):
                    matching_row = row
                    # Try to extract the filename from the text
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    for l in lines:
                        if any(ext in l.lower() for ext in [".doc", ".docx", ".pdf"]):
                            target_filename = l
                            break
                    break
            else:
                # Find any file row
                if any(ext in text.lower() for ext in [".doc", ".docx", ".pdf"]):
                    matching_row = row
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    for l in lines:
                        if any(ext in l.lower() for ext in [".doc", ".docx", ".pdf"]):
                            target_filename = l
                            break
                    break
                    
        if not matching_row:
            print("Không tìm thấy hàng nào chứa file tài liệu phù hợp.")
            browser.close()
            return None
            
        print(f"Tìm thấy tệp tin: '{target_filename}'")
        
        # Locate the button inside this row
        download_button = matching_row.locator("button").first
        if not download_button:
            print("Không tìm thấy nút tải file cho hàng này.")
            browser.close()
            return None
            
        # Click download button and wait for download to start
        print("Đang bấm nút tải file trực tiếp từ giao diện trang web...")
        try:
            with page.expect_download(timeout=15000) as download_info:
                download_button.click()
            download = download_info.value
            
            # Save download
            suggested_name = download.suggested_filename
            save_path = os.path.join(output_dir, suggested_name)
            print(f"Đang lưu file về máy: {save_path}")
            download.save_as(save_path)
            print("Tải file thành công!")
            browser.close()
            return save_path
        except Exception as e:
            print(f"Lỗi khi tải file: {e}")
            browser.close()
            return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sử dụng: python download_attachment.py <url> [tên_file_hoặc_định_dạng]")
        sys.exit(1)
        
    url = sys.argv[1]
    pattern = sys.argv[2] if len(sys.argv) > 2 else None
    download_file(url, pattern)
