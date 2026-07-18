# Citizen Expansion Task Plan

Updated: 2026-07-18

## Goal

Mở rộng bản demo hiện tại từ 2 domain workflow (`Khai sinh`, `Cư trú`) thành cấu trúc `Công dân -> Nhóm sự kiện -> Thủ tục`, nhưng vẫn tái sử dụng tối đa kiến trúc backend, dữ liệu `full-data.csv`, và `raw_data` đang có.

Tài liệu này coi `mapping nhóm` chỉ là một phần của bài toán. Để mở rộng hoàn toàn theo project hiện tại, cần bổ sung cả taxonomy, catalog API, intake routing, UI state, validation scope, và test coverage.

## Current State

- Frontend đã hiển thị tên nhóm `Công dân` và `Doanh nghiệp`, nhưng mới là danh sách tĩnh, chưa có data model hay API filter: [page.tsx](C:\Users\ku060\Downloads\VAIC source\data-pipeline\govease-unified\frontend\app\page.tsx)
- Trợ lý đang hoạt động theo 2 domain workflow cứng là `birth_registration` và `residence_management`: [workflow_intake.py](C:\Users\ku060\Downloads\VAIC source\data-pipeline\govease-unified\backend\app\services\workflow_intake.py)
- API thủ tục hiện chỉ trả danh sách procedure chung, chưa có khái niệm `persona`, `group`, `subcategory`: [routes.py](C:\Users\ku060\Downloads\VAIC source\data-pipeline\govease-unified\backend\app\api\routes.py)
- Procedure store đọc dữ liệu khá generic, có thể tái dùng tốt cho catalog mở rộng: [procedure_data.py](C:\Users\ku060\Downloads\VAIC source\data-pipeline\govease-unified\govease_ai\procedure_data.py)
- `full-data.csv` đã có toàn bộ mã số, tên, lĩnh vực, URL nguồn: [full-data.csv](C:\Users\ku060\Downloads\VAIC source\data-pipeline\main\full-data.csv)
- `raw_data` đã có nhiều thủ tục chi tiết, có thể tận dụng để xác nhận coverage và hỗ trợ gán nhóm: [raw_data](C:\Users\ku060\Downloads\VAIC source\data-pipeline\raw_data)

## Important Product Rule

`Khai sinh` và `Cư trú` không còn nên bị xem là top-level domain hiển thị cho người dùng.

Trong mô hình mở rộng:

- `Khai sinh` sẽ là một hoặc nhiều procedure family nằm dưới nhóm `Có con nhỏ`
- `Cư trú` sẽ là procedure family nằm dưới nhóm `Cư trú và giấy tờ tùy thân`
- Workflow engine vẫn có thể giữ `birth_registration` và `residence_management` ở tầng nội bộ để định tuyến
- UI và catalog phải hiển thị theo nhóm mới, không bám vào tên domain kỹ thuật hiện tại

## Missing Work Beyond Mapping

Chỉ làm `group -> procedure_code` là chưa đủ vì còn thiếu:

1. Một taxonomy chính thức để backend và frontend dùng chung.
2. Một catalog API trả về nhóm, thủ tục, coverage `raw_data`, và trạng thái hỗ trợ.
3. Một lớp nối giữa `group` sản phẩm và `domain` kỹ thuật hiện tại.
4. Một chiến lược fallback cho những nhóm chưa có workflow riêng.
5. Cập nhật UI để người dùng đi từ `nhóm -> thủ tục -> trợ lý`, thay vì nhảy thẳng vào 2 flow demo.
6. Test để đảm bảo việc thêm nhóm mới không làm hỏng 2 workflow hiện có.

## Target Architecture

### 1. Information architecture

- `persona`
  - `citizen`
- `citizen_group`
  - `co_con_nho`
  - `hoc_tap`
  - `viec_lam`
  - `cu_tru_giay_to`
  - `hon_nhan_gia_dinh`
  - `dien_luc_nha_o_dat_dai`
  - `suc_khoe_y_te`
  - `phuong_tien_nguoi_lai`
  - `huu_tri`
  - `nguoi_than_qua_doi`
  - `giai_quyet_khieu_kien`
- `procedure_family`
  - ví dụ: `birth_registration`, `residence_management`, `marriage_registration`, `death_registration`
- `procedure`
  - procedure code cụ thể như `1.001193`, `1.004194`

### 2. Runtime behavior

- Người dùng chọn hoặc gõ nhu cầu từ màn hình `Công dân`
- UI gửi thêm context `persona` hoặc `group` nếu người dùng đã chọn từ danh mục
- Backend dùng `group` để thu hẹp tập candidate procedures
- Nếu group đã có workflow family, dùng workflow engine
- Nếu group chưa có workflow family, dùng retrieval + catalog guidance + procedure shortlist

## Deliverables

### Deliverable A. Citizen taxonomy data

Tạo một nguồn dữ liệu chuẩn cho toàn bộ nhóm `Công dân`, ví dụ:

- `persona`
- `group_key`
- `group_label`
- `official_group_id`
- `procedure_code`
- `procedure_title`
- `source_url`
- `field`
- `raw_data_available`
- `workflow_family`
- `support_level`

`support_level` đề xuất:

- `workflow_ready`: đã có guided flow hoàn chỉnh
- `catalog_ready`: đã có data và trang hướng dẫn nhưng chưa có workflow riêng
- `raw_only`: mới có raw data, chưa chuẩn hóa hiển thị
- `missing_raw`: có trong CSV nhưng chưa có raw data

### Deliverable B. Catalog API

Thêm API mới để frontend không phải hard-code nhóm:

- `GET /api/v1/catalog/citizen-groups`
- `GET /api/v1/catalog/citizen-groups/{group_key}`
- `GET /api/v1/procedures?group_key=...`

Response nên trả:

- metadata nhóm
- số lượng thủ tục
- coverage theo `workflow_ready/catalog_ready`
- danh sách procedure cards

### Deliverable C. Group-aware intake

Mở rộng `IntakeRequest` để nhận thêm:

- `persona`
- `group_key`
- `candidate_procedure_codes`

Luồng intake mới:

- nếu đã biết `group_key`, backend ưu tiên procedure thuộc group đó
- nếu group map sang workflow family hiện có, route vào workflow family tương ứng
- nếu chưa có workflow family, trả shortlist procedure và guidance thay vì ép vào flow hỏi đáp hiện tại

### Deliverable D. Frontend navigation

Mở rộng trang chủ:

- click vào nhóm sẽ mở trang hoặc panel chi tiết nhóm
- trong nhóm có danh sách thủ tục thực sự lấy từ API
- badge thể hiện trạng thái:
  - `Đã có trợ lý từng bước`
  - `Đã có hướng dẫn`
  - `Đang hoàn thiện`

### Deliverable E. Coverage report

Sinh một bảng hoặc file tổng hợp:

- nhóm nào có bao nhiêu thủ tục
- bao nhiêu thủ tục có `raw_data`
- bao nhiêu thủ tục đã có normalized data
- bao nhiêu thủ tục đã có workflow

## Concrete Task Breakdown

### Phase 1. Define shared taxonomy

Tasks:

1. Tạo file config taxonomy cho `Công dân`.
2. Chuẩn hóa key nội bộ cho 11 nhóm công dân.
3. Định nghĩa các `workflow_family` hiện có và family dự kiến trong tương lai.

Suggested files:

- New: `data-pipeline/govease-unified/data/catalog/citizen_groups.json`
- Optional: `data-pipeline/data/catalog/citizen_groups.json`

Done when:

- Frontend và backend cùng đọc được một nguồn taxonomy chung.

### Phase 2. Build citizen mapping dataset

Tasks:

1. Đọc `full-data.csv`.
2. Gán mỗi procedure vào ít nhất một `citizen_group`.
3. Đối chiếu `raw_data/<code>/...` để set `raw_data_available`.
4. Đánh dấu `workflow_family` cho các thủ tục thuộc `Khai sinh` và `Cư trú`.
5. Đánh dấu `support_level`.

Important note:

- Đây là bước mà `Khai sinh` được chuyển thành member của nhóm `Có con nhỏ`
- `Cư trú` được chuyển thành member của nhóm `Cư trú và giấy tờ tùy thân`
- Một procedure có thể thuộc nhiều nhóm nếu cần, nhưng bản đầu nên chọn `primary_group` để UI đơn giản hơn

Suggested outputs:

- `data-pipeline/govease-unified/data/catalog/citizen_procedure_mapping.csv`
- `data-pipeline/govease-unified/data/catalog/citizen_procedure_mapping.json`

Done when:

- Có thể query từ `group_key` ra procedure list sạch và biết thủ tục nào đã có raw data.

### Phase 3. Build backend catalog service

Tasks:

1. Tạo service đọc taxonomy + mapping.
2. Gộp metadata từ mapping với `ProcedureDataStore`.
3. Expose endpoint danh sách nhóm và thủ tục theo nhóm.

Suggested files:

- New: `backend/app/services/catalog.py`
- Update: `backend/app/api/routes.py`
- Update: `backend/app/schemas.py`

Done when:

- Frontend không cần hard-code danh sách nhóm và procedure cards nữa.

### Phase 4. Refactor intake to support groups

Tasks:

1. Mở rộng `IntakeRequest` nhận `group_key`.
2. Thêm lớp resolve:
   - `group_key -> candidate procedure codes`
   - `procedure_code -> workflow_family`
3. Nếu `group_key` thuộc family workflow hiện có:
   - route vào `birth_registration` hoặc `residence_management`
4. Nếu `group_key` chưa có workflow:
   - dùng retrieval giới hạn theo group
   - trả top procedures + official sources + CTA chọn thủ tục

Suggested files:

- Update: `backend/app/schemas.py`
- Update: `backend/app/api/routes.py`
- Update: `backend/app/services/workflow_intake.py`
- Update: `govease_ai/retrieval.py`

Done when:

- UI chọn `Có con nhỏ` vẫn dùng được flow `Khai sinh`
- UI chọn `Cư trú và giấy tờ tùy thân` vẫn dùng được flow `Cư trú`
- Các nhóm khác chưa có workflow vẫn không bị dead end

### Phase 5. Update frontend IA

Tasks:

1. Thay danh sách tĩnh ở `page.tsx` bằng data từ API.
2. Thêm state `selectedGroup`.
3. Hiển thị procedure cards theo group.
4. Khi user vào trợ lý từ group, gửi kèm `group_key`.
5. Cập nhật text `PHẠM VI DEMO 2 thủ tục` thành số liệu động theo coverage.

Suggested files:

- Update: `frontend/app/page.tsx`
- Update: `frontend/components/CitizenAssistant.tsx`
- Update: `frontend/lib/api.ts`
- Update: `frontend/lib/types.ts`

Done when:

- Người dùng đi theo hành trình `Nhóm công dân -> Thủ tục -> Trợ lý`

### Phase 6. Expand validation and form support strategically

Tasks:

1. Không cố mở validation engine cho toàn bộ nhóm ngay.
2. Giữ validation sâu cho các thủ tục đã có schema tốt như `Khai sinh`, `Tạm trú`.
3. Với nhóm mới, trước mắt hỗ trợ:
   - official source links
   - checklist
   - basic guidance
4. Chỉ thêm form schema khi thủ tục đó đã có normalized data đủ tốt.

Done when:

- Phạm vi hỗ trợ của từng thủ tục được thể hiện rõ, không gây hiểu nhầm là tất cả đều full AI workflow.

### Phase 7. Tests and rollout guards

Tasks:

1. Test mapping coverage.
2. Test catalog endpoints.
3. Test `group_key=co_con_nho` vẫn route ra `birth_registration`.
4. Test `group_key=cu_tru_giay_to` vẫn route ra `residence_management`.
5. Test nhóm chưa có workflow trả shortlist hợp lệ.

Suggested files:

- New: `backend/tests/test_catalog.py`
- Update: `backend/tests/test_api.py`
- Update: `backend/tests/test_workflow_scenarios.py`

Done when:

- Mở rộng nhóm không làm vỡ behavior hiện có của 2 flow demo.

## Priority Order For Today

Nếu mục tiêu là tạo nền mở rộng thật sự trong hôm nay, thứ tự nên là:

1. Taxonomy file cho `Công dân`
2. Mapping dataset + cờ `raw_data_available`
3. Catalog API
4. Frontend đọc nhóm và procedure từ API
5. Group-aware intake tối thiểu cho `Có con nhỏ` và `Cư trú và giấy tờ tùy thân`

Không nên cố hoàn thành trong hôm nay:

- workflow riêng cho toàn bộ 11 nhóm
- validation sâu cho tất cả thủ tục
- UX hoàn chỉnh cho toàn bộ `Doanh nghiệp`

## Definition of Done For Citizen Expansion v1

`Citizen expansion v1` được coi là hoàn thành khi:

1. Toàn bộ 11 nhóm `Công dân` có mặt trong catalog.
2. Mỗi nhóm có danh sách thủ tục lấy từ dữ liệu thật.
3. Bảng mapping chỉ rõ thủ tục nào đã có `raw_data`.
4. `Có con nhỏ` nối được tới flow `Khai sinh`.
5. `Cư trú và giấy tờ tùy thân` nối được tới flow `Cư trú`.
6. Các nhóm còn lại ít nhất có catalog + official links + shortlist.
7. Frontend không còn hard-code “2 thủ tục demo” như trạng thái duy nhất của sản phẩm.

## Next Implementation Suggestion

Bước triển khai hợp lý tiếp theo là:

1. Tạo `citizen_groups.json`
2. Tạo `citizen_procedure_mapping.csv/json`
3. Thêm `catalog.py` và endpoint `citizen-groups`
4. Sau đó mới nối UI

Làm theo thứ tự này sẽ giữ kiến trúc sạch và giúp mở rộng sang `Doanh nghiệp` sau đó gần như là lặp lại cùng một pattern dữ liệu và API.
