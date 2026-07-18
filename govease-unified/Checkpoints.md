# Trợ lý AI cho Thủ tục Hành chính Công

Giải pháp AI hỗ trợ người dân thực hiện thủ tục hành chính (đăng ký thường trú, khai sinh, giấy phép...) thông qua ba năng lực: hướng dẫn ban đầu, kiểm tra trước khi nộp, và tích hợp liền mạch vào cổng dịch vụ công hiện có.

## Vấn đề

Khi cần thực hiện một thủ tục hành chính, người dân gặp ba trở ngại:

1. **Không biết cần chuẩn bị gì** — giấy tờ, biểu mẫu, hay nơi nộp.
2. **Không biết mình điền đúng hay sai** — chỉ phát hiện lỗi sau khi cán bộ kiểm tra.
3. **Tắc nghẽn hỗ trợ** — quá nhiều câu hỏi, quá ít cán bộ, người dân phải đi lại nhiều lần.

## Giải pháp: Ba năng lực

1. **Hướng dẫn ban đầu (Guided intake)** — người dùng mô tả nhu cầu bằng ngôn ngữ tự nhiên, AI hỏi làm rõ khi cần và trả về danh sách giấy tờ cụ thể cùng quy trình từng bước, có ví dụ minh họa.
2. **Kiểm tra trước khi nộp (Pre-submission checking)** — người dùng nhập thông tin đã điền, AI phát hiện lỗi phổ biến, trường thiếu, và xung đột dữ liệu, kèm gợi ý sửa.
3. **Tích hợp liền mạch (Seamless integration)** — nhúng trực tiếp vào cổng dịch vụ công hiện có qua API, widget, hoặc chatbot, không cần cài đặt ứng dụng mới.

Dữ liệu lấy từ Cổng Dịch vụ công Quốc gia (dichvucong.gov.vn) và danh mục biểu mẫu hành chính theo lĩnh vực.

## Kế hoạch triển khai trong 48 giờ

### Checkpoint 0 (Giờ 0–3): Chốt phạm vi

- Chọn **2–3 thủ tục** để làm trọn vẹn từ đầu đến cuối. Gợi ý: đăng ký thường trú, khai sinh, và một giấy phép liên quan đến kinh doanh. Tránh "giấy phép xây dựng" trừ khi có người đọc quy định xây dựng nhanh.
- Với mỗi thủ tục, ghi rõ: giấy tờ cần thiết, biểu mẫu cần thiết, cơ quan/nơi nộp, và 5–8 trường thông tin hay bị điền sai (sai định dạng CMND/CCCD, ngày tháng không khớp, thiếu chữ ký, sai quan hệ chủ hộ...).
- Chốt stack ngay:
  - Backend: FastAPI (Python).
  - Vector store: Chroma.
  - LLM: Codex API để sinh câu trả lời, một model embedding `text-embedding-3-small` để retrieval.
  - Frontend: một trang Next.js/React, dùng làm cả demo độc lập lẫn widget chat nhúng.
  - Hosting: Render/Railway cho API, Vercel cho frontend.

### Checkpoint 1 (Giờ 3–10): Dữ liệu + pipeline RAG

- Thu thập thủ công các trang thủ tục, mẫu biểu, hướng dẫn cho 2–3 thủ tục đã chọn. Lưu dưới dạng Markdown/JSON có cấu trúc.
- Chia chunk theo *bước logic* (một chunk = một mục giấy tờ, một giải thích trường biểu mẫu, một bước quy trình), không chia theo cửa sổ token cố định.
- Xây script ingest → embedding → lưu vào vector store. Test với 10 câu hỏi thủ công mỗi thủ tục.
- **Kiểm tra:** context lấy về đúng và có thể trích dẫn được (giữ trường `source_url` cho mỗi chunk).

### Checkpoint 2 (Giờ 10–20): Năng lực 1 — Hướng dẫn ban đầu

- Luồng hội thoại: mô tả nhu cầu → phân loại thủ tục (few-shot) → hỏi lại tối đa MỘT câu nếu mơ hồ → retrieval → sinh danh sách giấy tờ, quy trình từng bước, ví dụ minh họa cho ít nhất một trường phức tạp.
- Đầu ra có cấu trúc (JSON → checklist trên UI), không phải văn bản dài.
- **Kiểm tra:** 5 cách diễn đạt khác nhau của cùng một nhu cầu đều dẫn đến đúng thủ tục và checklist.

### Checkpoint 3 (Giờ 20–30): Năng lực 2 — Kiểm tra trước khi nộp

Hai lớp kiểm tra:

1. **Luật xác định (rules)** cho các trường đã liệt kê ở Checkpoint 0.
2. **LLM kiểm tra chéo** để bắt xung đột ngữ nghĩa mà luật không bắt được.

Đầu ra: danh sách lỗi, mỗi lỗi gồm trường bị lỗi, lỗi gì, gợi ý sửa.

- **Kiểm tra:** 5 mẫu đơn có cài sẵn lỗi (kết hợp cả hai lớp), tất cả đều bị phát hiện đúng.

### Checkpoint 4 (Giờ 30–36): Năng lực 3 — Tích hợp

- REST API (`/api/intake`, `/api/check`) kèm OpenAPI spec.
- Widget nhúng: đoạn JS nhỏ gắn iframe hoặc shadow-DOM chat box, nhúng vào một trang HTML "cổng dịch vụ công" giả lập tự tạo.
- **Kiểm tra:** widget tải và hoạt động trên trang HTML thuần, không có JS nào khác.

### Checkpoint 5 (Giờ 36–42): Deploy demo trực tiếp

- Deploy backend + frontend lên URL công khai ngay từ bây giờ. Chừa thời gian dự phòng cho lỗi deploy (env vars, CORS, cold start).
- Test lại toàn bộ luồng trên URL đã deploy.

### Checkpoint 6 (Giờ 42–46): Tài liệu bàn giao

- **Sơ đồ kiến trúc**: người dùng → widget/API → backend → (retrieval: vector store + embedding model) + (generation: Claude API) + (validation: rule engine) → phản hồi.
- **Tài liệu một trang**: vấn đề, giải pháp, người dùng mục tiêu, lộ trình triển khai (thí điểm một tỉnh/một thủ tục → mở rộng số thủ tục → tích hợp toàn cổng).

### Checkpoint 7 (Giờ 46–48): Dự phòng

- Sửa lỗi phát sinh lúc deploy, tập dượt kịch bản demo, chuẩn bị bản ghi hình dự phòng.

## Ghi chú quan trọng

- **Trích dẫn nguồn** ngay trong mỗi câu trả lời (link về đúng trang/chunk trên dichvucong.gov.vn) — nhắm thẳng vào tiêu chí "độ chính xác so với quy định hiện hành".
- **Tách biệt** bộ kiểm tra dựa trên luật (rule-based) với phần kiểm tra bằng LLM, cả trong code lẫn khi trình bày — cho thấy tư duy kỹ thuật, không chỉ là lớp bọc quanh API.

## Tiêu chí đánh giá

- Độ chính xác và đầy đủ của hướng dẫn so với quy định hiện hành.
- Khả năng phát hiện lỗi và thiếu sót trong thông tin đã điền.
- Tính khả thi khi tích hợp vào hệ thống dịch vụ công hiện có, kèm lộ trình thí điểm cụ thể.
- Trải nghiệm người dùng tổng thể cho người dân không rành công nghệ.