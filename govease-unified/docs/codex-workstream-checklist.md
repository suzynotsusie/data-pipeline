# Codex Workstream Checklist

## Scope Boundary

Codex chi lam cac hang muc thuoc:

- Data processing
- Domain/subdomain logic
- Workflow dataset generation
- Decision tree and slot config
- Workflow test data
- Frontend/UI integration cho 11 nhom Cong dan

Codex khong lam cac hang muc loi backend sau:

- Core intake parser architecture
- Core disambiguation engine framework
- Core backend routing engine
- Test runner framework

## Current Status

### Da xong

- Tao citizen catalog va mapping cho nhom Cong dan
- Chuan hoa danh sach domain -> subdomain trong:
  - [citizen_group_domains.json](C:/Users/ku060/Downloads/VAIC%20source/data-pipeline/govease-unified/data/catalog/citizen_group_domains.json)
- Build mapping procedure cho Cong dan trong:
  - [citizen_procedure_mapping.csv](C:/Users/ku060/Downloads/VAIC%20source/data-pipeline/govease-unified/data/catalog/citizen_procedure_mapping.csv)
  - [citizen_procedure_mapping.json](C:/Users/ku060/Downloads/VAIC%20source/data-pipeline/govease-unified/data/catalog/citizen_procedure_mapping.json)
- Cap nhat va bo sung `raw_data` theo mapping
- Bao phu `raw_data` hien tai:
  - `2076/2076` procedure codes trong mapping da co `raw_data`
- Doi ten co du lieu workflow thanh:
  - `in_workflow_dataset`

### Dang thuoc phan Codex va con phai lam

#### Phase 2

- Tao workflow dataset cho tung domain/subdomain
- Uu tien rollout:
  - `phuong_tien_nguoi_lai` (da co workflow dataset va test data cho 70 ma thu tuc / 3 subdomain)
  - `hoc_tap` (da co workflow dataset va test data cho 49 ma thu tuc / 5 subdomain)
  - `hon_nhan_gia_dinh` (da co workflow dataset va test data cho 40 ma thu tuc / 5 subdomain)
  - `nguoi_than_qua_doi` (da co workflow dataset va test data cho 18 ma thu tuc / 2 subdomain)

Deliverables cho moi domain/subdomain:

- `summary.csv`
- `normalized.json`
- `workflow_engine_config.json`

Thu muc muc tieu:

- `data/workflows/{domain}/{subdomain}/`

#### Phase 3

- Thiet ke intent
- Thiet ke slots
- Thiet ke decision tree
- Mapping cau tra loi -> `procedure_code`

Yeu cau:

- Bam theo format dang dung cua `birth_registration`
- Bam theo format dang dung cua `residence_management`

#### Phase 6

- Tao `intake_cases.json`
- Tao `submission_cases.json`
- Bo sung data test cho tung workflow domain

Thu muc muc tieu:

- `tests/workflows/{domain}/`

#### Phase 7

- Tich hop frontend hien thi:
  - 11 nhom chinh
  - subdomain
  - payload intake theo `group_key` va `subdomain_key`

## Next Codex Move

Buoc tiep theo dung pham vi Codex la:

1. Mo rong cach lam nay sang domain Cong dan tiep theo uu tien cao
2. Xac dinh subdomain citizen-facing cho nhom nay
3. Sinh:
   - `summary.csv`
   - `normalized.json`
   - `workflow_engine_config.json`
4. Tao:
   - `intake_cases.json`
   - `submission_cases.json`

## Coordination Rule

Neu mot viec can sua vao:

- `intent_parser.py`
- `intake_disambiguation.py`
- `workflow_intake.py`
- core backend routing/test runner

thi xem do la phan Antigravity, khong phai phan Codex theo plan nay.
