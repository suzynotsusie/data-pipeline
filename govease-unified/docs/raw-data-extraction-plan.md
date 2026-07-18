# Raw Data Extraction Plan

## Goal

Thiết kế pipeline chuyển `raw_data/*_procedure_detail.md` thành dữ liệu đủ giàu để phục vụ:

- Catalog và landing page ngoài chatbot
- Màn `GuidanceView`
- Màn `DynamicForm`
- Màn `NextStepsView`
- API thủ tục và validation theo workflow

Pipeline mục tiêu:

`raw markdown -> raw_structured.json -> normalized_structured.json -> enriched_structured.json -> UI/API payload`

## Core principle

- Phần có cấu trúc lặp lại, kiểm chứng được: dùng Python parser.
- Phần là ngôn ngữ tự nhiên dài, nhiều biến thể: dùng AI enrich offline.
- Phần là luật nghiệp vụ, schema chính thức, validation rule ID: do Python/rule engine chốt.

## Current observations from raw markdown

Các file mẫu đã rà:

- [1_001193_procedure_detail.md](C:\Users\ku060\Downloads\VAIC source\data-pipeline\raw_data\1_001193\1_001193_procedure_detail.md)
- [1_004194_procedure_detail.md](C:\Users\ku060\Downloads\VAIC source\data-pipeline\raw_data\1_004194\1_004194_procedure_detail.md)
- [1_001456_procedure_detail.md](C:\Users\ku060\Downloads\VAIC source\data-pipeline\raw_data\1_001456\1_001456_procedure_detail.md)
- [1_005142_procedure_detail.md](C:\Users\ku060\Downloads\VAIC source\data-pipeline\raw_data\1_005142\1_005142_procedure_detail.md)
- [1_014748_procedure_detail.md](C:\Users\ku060\Downloads\VAIC source\data-pipeline\raw_data\1_014748\1_014748_procedure_detail.md)

Điểm ổn định:

- Gần như luôn có các section `## Thông tin chung`, `## Trình tự thực hiện`, `## Thành phần hồ sơ`, `## Căn cứ pháp lý`, `## Kết quả xử lý`.
- `Thông tin chung` thường ở dạng bullet `* **Nhãn:** giá trị`.
- Nhiều file có bảng markdown chuẩn ở `Cách thức thực hiện`, `Thành phần hồ sơ`, `Căn cứ pháp lý`.
- Một số file có file đính kèm mẫu đơn ngay trong cột `Tệp đính kèm`.

Điểm không ổn định:

- `Cách thức thực hiện` đôi khi bị flatten thành text thường thay vì bảng.
- `Thành phần hồ sơ` có thể có nhiều nhóm con, nhiều bảng liên tiếp, xen lẫn phần `Lưu ý`.
- `Cơ quan thực hiện`, `Địa chỉ tiếp nhận HS`, `Yêu cầu, điều kiện thực hiện` nhiều lúc là `Không có thông tin`.
- Cùng một ý nghiệp vụ có thể nằm ở `Trình tự thực hiện`, `Lưu ý`, hoặc `Yêu cầu, điều kiện thực hiện`.

## Data contract by stage

### 1. `raw_structured.json`

Mục tiêu:

- Giữ được cấu trúc section
- Parse tối đa bằng rule-based parser
- Không mất dữ liệu thô
- Đánh dấu phần parse yếu bằng warning

Phải có:

- `source`
- `meta`
- `submission_methods`
- `documents.groups`
- `legal_basis`
- `results`
- `raw_sections`
- `quality`

### 2. `normalized_structured.json`

Mục tiêu:

- Chuẩn hóa field names giữa các domain
- Tách rõ `required`, `conditional`, `notes`
- Chuẩn hóa `processing_time`, `submission_place`, `authority`
- Tách attachment ra một danh sách riêng
- Trích `time_hints`, `special_cases`, `warnings`

### 3. `enriched_structured.json`

Mục tiêu:

- Bổ sung semantic layer phục vụ UI
- Có provenance rõ cái nào là AI-derived

Nên có thêm:

- `overview_summary`
- `common_errors`
- `special_cases`
- `candidate_input_fields`
- `validation_hints`
- `next_step_summary`

## Extraction matrix

| Target field | Source section | Primary method | AI? | Confidence target |
| --- | --- | --- | --- | --- |
| `procedure_code` | `Thông tin chung` | Python regex/bullet parser | No | Very high |
| `title` | H1 document title | Python heading parser | No | Very high |
| `decision_number` | `Thông tin chung` | Python bullet parser | No | Very high |
| `level` | `Thông tin chung` | Python bullet parser | No | Very high |
| `procedure_type` | `Thông tin chung` | Python bullet parser | No | High |
| `field` | `Thông tin chung` | Python bullet parser | No | Very high |
| `target_users` | `Thông tin chung` | Python split by comma | No | High |
| `authority` | `Thông tin chung` or `Cơ quan thực hiện` | Python bullet parser with fallback section parser | No | High |
| `receiving_address` | `Thông tin chung` | Python bullet parser | No | High |
| `related_procedures` | `Thủ tục hành chính liên quan` | Python text parser | Optional fallback | Medium |
| `steps[]` | `Trình tự thực hiện` | Python step splitter | Optional enrich | Medium-high |
| `submission_methods[]` | `Cách thức thực hiện` | Python markdown table parser | AI fallback only if table broken | High |
| `processing_time` | `Cách thức thực hiện` | Python table parser + regex fallback | AI fallback | High |
| `fee` | `Cách thức thực hiện` | Python table parser | No | High |
| `documents.groups[]` | `Thành phần hồ sơ` | Python subsection + table parser | No | High |
| `documents[].attachment_path` | `Thành phần hồ sơ` | Python markdown link parser | No | Very high |
| `documents[].conditions` | `Thành phần hồ sơ`, `Lưu ý` | Python keyword rules + AI enrich | Yes | Medium |
| `legal_basis[]` | `Căn cứ pháp lý` | Python markdown table parser | No | Very high |
| `results[]` | `Kết quả xử lý` | Python bullet parser | No | High |
| `eligibility.conditions[]` | `Yêu cầu, điều kiện thực hiện` | Python list parser | AI enrich optional | Medium-high |
| `special_cases[]` | `Lưu ý`, `Yêu cầu`, `Trình tự` | Python keyword rules + AI synthesis | Yes | Medium |
| `warnings[]` | `Lưu ý`, `Trình tự` | Python keyword rules + AI synthesis | Yes | Medium |
| `candidate_input_fields[]` | documents + conditions + workflow family | Domain enricher | Yes, propose only | Medium |
| `validation_hints[]` | conditions + notes + workflow family | Domain enricher | Yes, propose only | Medium |
| `overview_summary` | all structured sections | AI summarize from normalized JSON | Yes | Medium-high |

## What should be Python-only

- Section splitting by heading
- Bullet parsing in `Thông tin chung`
- Markdown table parsing
- Attachment path extraction
- Legal basis row extraction
- Result code extraction
- Final API response shape
- Validation rule IDs
- Coverage/test fixture generation

## What can use AI offline

- Recovering a broken section when table parsing fails badly
- Summarizing long process text into short UI copy
- Deriving `special_cases`
- Deriving `common_errors`
- Proposing candidate form fields
- Proposing validation hints and help text

## Recommended Python parser modules

### `parser_py.sections`

Responsibilities:

- Detect H1 title
- Detect all `##` sections
- Preserve original text per section

Output:

- `raw_sections`

### `parser_py.meta`

Responsibilities:

- Parse `Thông tin chung`
- Normalize common labels:
  - `Mã thủ tục`
  - `Số quyết định`
  - `Cấp thực hiện`
  - `Loại thủ tục`
  - `Lĩnh vực`
  - `Đối tượng thực hiện`
  - `Cơ quan có thẩm quyền`
  - `Địa chỉ tiếp nhận HS`
  - `Cơ quan được ủy quyền`
  - `Cơ quan phối hợp`

### `parser_py.tables`

Responsibilities:

- Parse markdown tables
- Handle repeated headers
- Return rows as plain dictionaries

Must support:

- normal table
- table with blank rows
- consecutive tables in same section

### `parser_py.methods`

Responsibilities:

- Extract `submission_methods[]`
- First try markdown table parser
- If not found, fallback to regex/text heuristics

Must detect:

- `Trực tuyến`
- `Trực tiếp`
- `Dịch vụ bưu chính`
- time text
- fee text
- description text

### `parser_py.documents`

Responsibilities:

- Split `Thành phần hồ sơ` into groups
- Detect subsection headings like `###`
- Parse tables below each group
- Extract attachment links
- Mark notes-only rows

Must produce:

- `documents.groups[]`
- `attachments[]`

### `parser_py.process`

Responsibilities:

- Parse `Trình tự thực hiện`
- Split by:
  - `Bước 1`, `Bước 2`
  - numbered list
  - `(i)`, `(ii)`, `(iii)`
  - bullet `-`, `+`

Output:

- `process.raw_text`
- `process.steps[]`

### `parser_py.quality`

Responsibilities:

- Add `parse_warnings`
- Set `needs_manual_review`

Trigger warnings when:

- section missing
- methods section not parsed into rows
- documents section has free text but zero rows
- file contains malformed attachment links
- more than one high-value field is `Không có thông tin`

## Recommended AI enrichers

### `ai_enricher.overview`

Input:

- normalized meta
- methods
- results
- top document groups

Output:

- `overview_summary`
- `next_step_summary`

### `ai_enricher.special_cases`

Input:

- process text
- conditions
- notes rows

Output:

- `special_cases[]`
- `warnings[]`
- `common_errors[]`

### `ai_enricher.form_candidates`

Input:

- document groups
- conditions
- workflow family
- known field library

Output:

- `candidate_input_fields[]`
- `validation_hints[]`

Constraint:

- must include confidence
- must include provenance
- cannot directly become final API schema

## Recommended normalized data model

### Overview

- `overview.processing_time_summary`
- `overview.primary_submission_places`
- `overview.primary_channels`
- `overview.fee_summary`

### Checklist

- `checklist.primary_documents`
- `checklist.conditional_documents`
- `checklist.notes`

### Procedure actions

- `procedure_actions.user_steps`
- `procedure_actions.authority_steps`
- `procedure_actions.deadlines`

### Validation support

- `form_candidates`
- `special_cases`
- `validation_hints`

## Best rollout order

### Phase 1

Do with Python only:

- section parser
- metadata parser
- methods parser
- document parser
- legal basis parser
- results parser
- attachment extractor

Success criteria:

- `raw_structured.json` build được ổn định cho top 30 thủ tục

### Phase 2

Do with Python first, AI enrich second:

- process step extraction
- warning extraction
- special-case extraction
- overview summaries

Success criteria:

- thay được placeholder metadata trong `GuidanceView`

### Phase 3

Domain-specific enrichment:

- workflow family rules
- candidate form fields
- validation hints

Success criteria:

- giảm fallback trong [procedures.py](C:\Users\ku060\Downloads\VAIC source\data-pipeline\govease-unified\backend\app\services\procedures.py)

### Phase 4

Reviewer loop:

- confidence threshold
- manual review queue
- golden files for parser outputs

Success criteria:

- parser chạy được hàng loạt mà không cần sửa tay cho từng procedure

## Immediate next implementation tasks

1. Tạo package `scripts/raw_markdown_pipeline/`.
2. Implement `sections.py`, `meta.py`, `tables.py`.
3. Implement `documents.py` và `methods.py`.
4. Sinh thử `raw_structured.json` cho:
   - `1.001193`
   - `1.004194`
   - `1.001456`
   - `1.005142`
   - `1.014748`
5. Ghi `parse_warnings` cho từng file.
6. Sau khi parser ổn mới thêm AI enrich offline.

## Decision

Hướng làm thông minh nhất là:

- dùng Python để bảo toàn và chuẩn hóa structure
- dùng AI offline để enrich phần semantic khó
- không dùng AI runtime để quyết định schema chính thức hoặc validation rules
- luôn giữ `raw_sections` và provenance để có thể audit ngược
