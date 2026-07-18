# Kiến trúc Hợp Nhất GovEase AI

Ngày cập nhật: 2026-07-17

## 1. Mục tiêu

Thư mục `data-pipeline/govease-unified` là bản hợp nhất kỹ thuật để nhóm tiếp tục phát triển sản phẩm chính.

Mục tiêu của bản hợp nhất:

- Dùng `GovEase-AI` làm nền tảng chính cho frontend, backend API, validation, widget nhúng và deployment.
- Dùng dữ liệu chung từ `data-pipeline/data` để tránh tách đôi nguồn dữ liệu.
- Giữ hướng phát triển `workflow-chatbot` như một workflow engine chuyên cho guided intake và deterministic routing.
- Tạo một kiến trúc đủ sạch để sau đó cấy decision tree vào backend chính thay vì giữ hai app độc lập lâu dài.

## 2. Quyết định Kiến trúc

### Nền tảng chính

Giữ `GovEase-AI` làm shell sản phẩm vì nó đã có:

- backend FastAPI có versioned API
- frontend Next.js có widget `/widget`
- validation 2 lớp
- tài liệu, test và deployment scaffold

### Workflow engine

Giữ `workflow-chatbot` như nguồn logic intake cho 2 domain:

- khai sinh
- cư trú

Phần này không nên tiếp tục sống như app độc lập trong dài hạn. Nó nên được tách thành một service/module để backend chính gọi vào.

## 3. Kiến trúc Đích

```text
Người dùng
  -> Widget / Portal UI (Next.js)
  -> API GovEase Unified (FastAPI)
      -> Intake Orchestrator
          -> Workflow Engine (decision tree + slot filling)
          -> RAG Retriever (Chroma)
          -> Procedure Data Store (data-pipeline/data)
      -> Validation Service
          -> Rule Validator
          -> Optional LLM Semantic Validator
      -> Procedure / Form Schema API
```

## 4. Vai trò của từng khối

### Frontend Next.js

Nhiệm vụ:

- nhận nhu cầu tự nhiên
- hiển thị clarifying question
- hiển thị checklist
- hiển thị form schema và validation issues
- hỗ trợ widget nhúng vào portal khác

Không nên chứa business logic chọn route.

### FastAPI Backend

Nhiệm vụ:

- là API contract ổn định cho demo
- quản lý session intake
- gọi workflow engine để xác định route
- gọi RAG để lấy giải thích, checklist và nguồn
- gọi validation để pre-check

### Workflow Engine

Nhiệm vụ:

- giữ state hỏi đáp
- xác định slot nào còn thiếu
- nếu user nói nhảy cóc thì trích nhiều slot cùng lúc
- hỏi đúng node thiếu tiếp theo
- chốt route theo decision tree

Workflow engine quyết định route. LLM không được tự quyết route cuối.

### RAG Layer

Nhiệm vụ:

- giải thích thủ tục
- sinh checklist dễ hiểu
- lấy citations/source_url
- hỗ trợ câu trả lời mềm hơn, dễ hiểu hơn

RAG không nên là lớp duy nhất để phân loại thủ tục cho 2 domain pilot.

### Validation Layer

Nhiệm vụ:

- kiểm tra field-level lỗi phổ biến
- kiểm tra cross-field logic
- dùng LLM semantic validator như lớp phụ trợ, không phải lớp bắt buộc

## 5. Nguồn Dữ Liệu Chung

Thay vì giữ `GovEase-AI/data` như một cây dữ liệu riêng, bản hợp nhất mặc định dùng:

`data-pipeline/data`

Lý do:

- đây là nơi nhóm đang chuẩn hóa dữ liệu pilot
- tránh 2 phiên bản dữ liệu lệch nhau
- dễ audit và update từ pipeline

## 6. Lộ trình Hợp Nhất Code

### Giai đoạn 1

- dùng `govease-unified` làm app chính trong pipeline
- giữ `workflow-chatbot` chạy riêng để tham chiếu logic
- tiếp tục hoàn thiện workflow cho khai sinh và cư trú

### Giai đoạn 2

- trích workflow engine từ `workflow-chatbot/app.py`
- đưa sang backend `govease-unified/backend/app/services/workflow_*`
- để `/api/v1/intake` gọi workflow engine trước
- nếu route đã rõ thì trả checklist
- nếu route chưa rõ thì trả clarifying question

### Giai đoạn 3

- frontend Next.js đổi từ intake kiểu classify đơn sang intake stateful thật
- hiển thị câu hỏi từng bước, quick options, progress, checklist

## 7. Quy tắc Thiết kế Quan trọng

- Decision tree quyết định route.
- LLM chỉ dùng để hiểu câu tự nhiên và diễn giải.
- Dữ liệu sống chung ở `data-pipeline/data`.
- Widget và portal demo tiếp tục lấy từ `GovEase-AI`.
- Validation phải giữ tách biệt với intake.

## 8. Kết luận

`govease-unified` là nơi nên tiếp tục build.

- `GovEase-AI` cung cấp khung sản phẩm mạnh hơn.
- `workflow-chatbot` cung cấp logic intake tốt hơn.
- Bản hợp nhất đúng là: `GovEase-AI shell + workflow engine + shared pipeline data`.
