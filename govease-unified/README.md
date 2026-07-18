# GovEase Unified

Đây là bản hợp nhất của `GovEase-AI` được đưa vào `data-pipeline` để làm nền tảng sản phẩm chính.

Mục tiêu của bản này:

- giữ backend FastAPI, frontend Next.js, widget nhúng, validation và deploy scaffold từ `GovEase-AI`
- dùng chung dữ liệu từ `data-pipeline/data`
- chuẩn bị chỗ để gắn workflow engine của `workflow-chatbot` vào luồng intake

Kiến trúc hiện tại vẫn là RAG-style assistant, chưa phải fine-tuned model. Hướng phát triển đích là:

`workflow engine + shared data + RAG explanation + validation`

Trong đó:

- workflow engine quyết định route
- RAG và LLM giải thích, checklist hóa và hỗ trợ trả lời tự nhiên
- validation kiểm tra trước khi nộp

## Backend API

Thư mục này chứa backend, frontend và core logic cần để tiếp tục build sản phẩm trong `data-pipeline`.

```text
govease-unified/
|-- backend/
|   `-- app/
|       |-- api/             # FastAPI routes
|       |-- rag/             # Chroma retrieval adapter
|       |-- services/        # OpenAI Responses API orchestration
|       `-- main.py
|-- frontend/                # Next.js portal demo and embeddable widget
|-- govease_ai/              # Existing domain/RAG core
|-- docs/                    # Unified architecture and audit docs
`-- render.yaml
```

Nguồn dữ liệu mặc định không nằm trong repo này nữa. Bản unified dùng chung:

`data-pipeline/data`

### Run locally

Từ thư mục `data-pipeline/govease-unified`:

```powershell
python -m pip install -r requirements-dev.txt
uvicorn backend.app.main:app --reload
```

The API is available at `http://localhost:8000` and its interactive OpenAPI documentation is at `http://localhost:8000/docs`.

Chạy portal demo ở terminal thứ hai:

```powershell
cd frontend
Copy-Item .env.example .env.local
npm ci
npm run dev
```

The full demo is available at `http://localhost:3000`; the iframe-compatible assistant is at `/widget`. For Vercel, set `NEXT_PUBLIC_API_URL` to the public Render API and include the Vercel origin in Render's `CORS_ORIGINS`.

The separate frontend project should configure its API base URL to this service and call endpoints under `/api`. Add every allowed frontend origin to the comma-separated `CORS_ORIGINS` environment variable.

### API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Service health check |
| `POST` | `/api/chat` | RAG conversation endpoint |
| `POST` | `/api/intake` | Deterministic procedure classification and checklist |
| `POST` | `/api/check` | Pre-submission validation |

The stable integration contract is versioned under `/api/v1`:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/ready` | Data, Chroma and OpenAI readiness |
| `GET` | `/api/v1/procedures` | Pilot procedure catalog |
| `GET` | `/api/v1/procedures/{code}` | Procedure metadata |
| `GET` | `/api/v1/procedures/{code}/form-schema` | Machine-readable frontend form schema |
| `POST` | `/api/v1/intake` | Stateful-by-contract guided intake |
| `POST` | `/api/v1/procedures/{code}/validate` | Field-level submission validation |

Xem thêm:

- [UNIFIED_ARCHITECTURE.md](C:\Users\ku060\Downloads\VAIC source\data-pipeline\govease-unified\docs\UNIFIED_ARCHITECTURE.md)
- [FILE_AUDIT.md](C:\Users\ku060\Downloads\VAIC source\data-pipeline\govease-unified\docs\FILE_AUDIT.md)
- [api-integration.md](C:\Users\ku060\Downloads\VAIC source\data-pipeline\govease-unified\docs\api-integration.md)
- [architecture.md](C:\Users\ku060\Downloads\VAIC source\data-pipeline\govease-unified\docs\architecture.md)
- [frontend-architecture.md](C:\Users\ku060\Downloads\VAIC source\data-pipeline\govease-unified\docs\frontend-architecture.md)
- [render-deployment.md](C:\Users\ku060\Downloads\VAIC source\data-pipeline\govease-unified\docs\render-deployment.md)

Frontend-specific documentation: [frontend architecture](docs/frontend-architecture.md) and [official data sources](docs/data-sources.md).

### Deploy

Render đọc `render.yaml`. Thêm `OPENAI_API_KEY` và các frontend origin hợp lệ trong `CORS_ORIGINS`. API sẽ tự kiểm tra và khởi tạo index khi cần.

## Current Status

As of Friday, July 17, 2026:

| Area | Status |
| --- | --- |
| Source procedures collected | 73 from dichvucong.gov.vn source data |
| Procedures loaded by current Python store | 52 normalized unique records |
| Detailed templates | 2: birth registration and temporary residence |
| Chroma chunks generated | 403 |
| Guided intake cases | 20 passing (10 per pilot procedure) |
| Pre-submission cases | 7 passing, including 2 clean submissions |
| Checkpoint embedding model | `text-embedding-3-small` |
| Local embedding fallback | `paraphrase-multilingual-mpnet-base-v2` |
| Validation layers | Deterministic rules + optional LLM semantic checker |
| Unit tests | Theo test suite hiện có trong thư mục `tests/` và `backend/tests/` |

Xem thêm [Checkpoints.md](C:\Users\ku060\Downloads\VAIC source\data-pipeline\govease-unified\Checkpoints.md) cho kế hoạch checkpoint ban đầu.

## Capabilities

1. Guided intake
   - Classifies a user's natural-language need into a procedure using few-shot examples plus retrieval.
   - Returns structured checklist data: documents, conditional documents, steps, examples, common errors, and citations.
   - Uses the detailed templates first when available.

2. Pre-submission checking
   - Validates common format mistakes such as invalid dates, missing required fields, bad identity-number formats, and missing signatures.
   - Performs deterministic cross-field checks such as birth-date mismatch with a birth certificate or temporary address matching permanent address.
   - Keeps the LLM semantic checker as a separate optional layer, matching the checkpoint design.
   - Returns structured issues with field, rule ID, severity, layer, message, suggestion, and source URL.

3. Retrieval training
   - Builds logical chunks from procedure JSON instead of fixed token windows.
   - Uses OpenAI `text-embedding-3-small` by default.
   - Embeds chunks into a persistent Chroma database.
   - Keeps generated `chroma_db/` out of git.

## Project Structure

```text
GovEase-AI/
|-- govease_ai/
|   |-- assistant.py          # Guided intake and submission checking facade
|   |-- chunking.py           # Logical chunks for RAG training
|   |-- model_config.py       # Checkpoint model defaults and env config
|   |-- embeddings.py         # Application-owned OpenAI/local embedding service
|   |-- procedure_data.py     # Data loading and normalization
|   |-- retrieval.py          # Deterministic local retrieval/classification fallback
|   |-- semantic_validation.py # Optional LLM semantic validation layer
|   `-- validation.py         # Rule-based and cross-field submission checks
|-- data/
|   |-- birth_procedure/      # Detailed birth-registration template and source data
|   |-- residence_procedures/ # Residence procedures and tam-tru detailed template
|   |-- civil_status_procedures/
|   |-- thutuc/               # Source CSV
|   `-- test_cases/           # Generated intake and submission fixtures
|-- tests/                    # Unit tests
|-- scripts/
|-- ingest.py                 # Train/build Chroma retrieval index
|-- query_test.py             # Run generated sanity cases
|-- requirements.txt
|-- Checkpoints.md
`-- README.md
```

## Setup

```powershell
python -m pip install -r requirements-dev.txt
```

If you use the existing virtual environment on Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Create `.env` in the project root:

```text
OPENAI_API_KEY=sk-...
```

`ModelConfig.from_env()` automatically loads this `.env` file.

## Train The Retrieval Model

Checkpoint mode uses OpenAI embeddings and requires `OPENAI_API_KEY`:

```powershell
$env:OPENAI_API_KEY="sk-..."
python ingest.py
```

Successful output should look like:

```text
Training complete
  Procedures indexed: 52
  Detailed procedures: 2
  Chunks embedded: 403
  Chroma DB: ...\chroma_db
  Collection: procedures-<data-fingerprint>
  Embedding provider: openai
  Embedding model: text-embedding-3-small
  Checkpoint embedding: True
```

Offline development fallback requires the development dependencies:

```powershell
python ingest.py --local-embeddings
```

That fallback is intentionally explicit so the default model stays aligned with the checkpoint.

## Run Checks

Run all unit tests:

```powershell
python -m unittest discover -v
```

Run generated intake and submission cases:

```powershell
python query_test.py
```

Expected result:

```text
Intake cases: 20
  PASS ...

Submission cases: 7
  PASS ...
```

## Programmatic Usage

```python
from govease_ai import ProcedureAssistant

assistant = ProcedureAssistant()

intake = assistant.guided_intake(
    "Toi moi sinh con va muon lam giay khai sinh cho be."
)
print(intake["procedure"])
print(intake["checklist"])

check = assistant.check_submission(
    "1.004194",
    {
        "applicant": {
            "full_name": "Le Van D",
            "identity_number": "abc",
            "is_minor": False,
        },
        "temporary_address": "12 Nguyen Trai, Phuong A",
        "permanent_address": "12 Nguyen Trai, Phuong A",
        "stay_start_date": "2026-07-10",
        "stay_end_date": "2026-07-09",
        "accommodation_proof": "",
        "signature_present": False,
    },
)
print(check["ready_to_submit"])
print(check["issues"])
print(check["validation_layers"])
```

## Test Case Files

| File | Purpose |
| --- | --- |
| `data/test_cases/intake_cases.json` | 10 natural-language phrasing variants for procedure routing and checklist coverage |
| `data/test_cases/submission_cases.json` | 5 realistic bad submissions with expected validation rule IDs |

## Roadmap

Near-term next steps:

1. Complete human source review for both pilot records and promote their governance status.
2. Add more detailed templates for high-priority procedures beyond `khai-sinh` and `tam-tru`.
3. Wire the optional LLM semantic validator into staging with `GOVEASE_ENABLE_LLM_SEMANTIC=true`.
4. Track citation coverage, routing accuracy and validation false-positive rate in CI.
5. Pilot the API/widget with one receiving authority before expanding by sector.

## Data Source

The project data is based on public procedure information from the Vietnamese National Public Service Portal at `dichvucong.gov.vn`. Every generated assistant response is designed to preserve citation metadata through `source_url`.
