# Audit File GovEase-AI Khi Đưa Vào Pipeline

Ngày cập nhật: 2026-07-17

## Nguyên tắc Audit

- `Giữ`: cần cho bản sản phẩm hợp nhất.
- `Giữ nhưng xem lại`: hữu ích, nhưng cần chỉnh hoặc chưa tối ưu.
- `Không copy / loại`: không cần trong bản hợp nhất hiện tại.

## 1. Top-level

| Path | Quyết định | Nhận xét |
| --- | --- | --- |
| `.env.example` | Giữ và sửa | Đã đổi model mặc định sang `gpt-5-mini`, thêm `GOVEASE_DATA_ROOT`. |
| `.gitignore` | Không copy | Có thể tạo lại riêng theo `data-pipeline` nếu cần. |
| `.python-version` | Không copy | Không cần thiết cho bản hợp nhất hiện tại. |
| `.backend.stdout.log` | Không copy | File runtime, không nên đưa vào bản chính. |
| `.backend.stderr.log` | Không copy | File runtime, không nên đưa vào bản chính. |
| `README.md` | Giữ nhưng xem lại | Hữu ích, nhưng vẫn mô tả repo gốc chứ chưa phản ánh hoàn toàn bản unified. |
| `Checkpoints.md` | Giữ | Có giá trị tham chiếu tiến độ hackathon. |
| `pyproject.toml` | Giữ | Hữu ích cho dependency Python. |
| `requirements.txt` | Giữ | Cần cho cài đặt cơ bản. |
| `requirements-dev.txt` | Giữ | Cần khi chạy test/local dev. |
| `requirements-production.txt` | Giữ | Có ích khi deploy. |
| `render.yaml` | Giữ | Cần cho story deploy backend. |
| `vercel.json` | Giữ | Cần cho story deploy frontend. |
| `uv.lock` | Không copy | Không cần nếu chưa chuẩn hóa bằng `uv`. |
| `ingest.py` | Giữ | Cần build Chroma index. |
| `query_test.py` | Giữ | Hữu ích để sanity-check dữ liệu và logic. |
| `data/` | Không copy | Bản unified dùng chung `data-pipeline/data`. |

## 2. backend

| Path | Quyết định | Nhận xét |
| --- | --- | --- |
| `backend/app/main.py` | Giữ | Entry point rõ ràng, hợp lý. |
| `backend/app/api/routes.py` | Giữ nhưng xem lại | Là route chính, sau này cần cấy workflow engine vào `intake`. |
| `backend/app/config.py` | Giữ và sửa | Đã đổi model mặc định, thêm biến data root. |
| `backend/app/errors.py` | Giữ | Hợp lý. |
| `backend/app/schemas.py` | Giữ | Hợp lý, cần cho API contract. |
| `backend/app/services/chat.py` | Giữ nhưng xem lại | Tốt cho RAG chat, nhưng không phải intake deterministic. |
| `backend/app/services/index_manager.py` | Giữ | Hợp lý cho lifecycle index. |
| `backend/app/services/procedures.py` | Giữ | Quan trọng cho form schema và procedure metadata. |
| `backend/app/services/administrative_units.py` | Giữ | Cần nếu form cần dữ liệu tỉnh/thành. |
| `backend/app/rag/retriever.py` | Giữ | Cần cho retrieval. |
| `backend/start.py` | Giữ nhưng xem lại | Có thể giữ để chạy nhanh, nhưng không bắt buộc nếu dùng `uvicorn`. |
| `backend/requirements.txt` | Giữ | Có ích. |
| `backend/package-lock.json` | Loại | Không hợp lý trong backend Python, đã xóa khỏi bản unified. |
| `backend/tests/test_api.py` | Giữ | Cần cho API regression. |

## 3. govease_ai core

| Path | Quyết định | Nhận xét |
| --- | --- | --- |
| `govease_ai/assistant.py` | Giữ nhưng xem lại | Lõi intake/check hiện tại; sau này cần phối hợp với workflow engine. |
| `govease_ai/procedure_data.py` | Giữ và sửa | Đã sửa để dùng `data-pipeline/data` mặc định. |
| `govease_ai/retrieval.py` | Giữ | Quan trọng cho classify/search fallback. |
| `govease_ai/chunking.py` | Giữ | Cần cho indexing. |
| `govease_ai/embeddings.py` | Giữ | Cần cho OpenAI/local embeddings. |
| `govease_ai/index_manifest.py` | Giữ | Cần cho versioned index. |
| `govease_ai/model_config.py` | Giữ nhưng xem lại | Nên đồng bộ thêm với chiến lược model cuối cùng của nhóm. |
| `govease_ai/validation.py` | Giữ | Quan trọng, hợp lý. |
| `govease_ai/semantic_validation.py` | Giữ nhưng xem lại | Hợp lý nhưng nên để optional đúng như hiện tại. |
| `govease_ai/__init__.py` | Giữ | Chuẩn package. |

## 4. frontend

| Path | Quyết định | Nhận xét |
| --- | --- | --- |
| `frontend/package.json` | Giữ | Cần cho Next.js app. |
| `frontend/package-lock.json` | Giữ | Hữu ích để cài dependency ổn định. |
| `frontend/next.config.ts` | Giữ | Cần thiết. |
| `frontend/tsconfig.json` | Giữ | Cần thiết. |
| `frontend/.env.example` | Giữ | Cần cho local run. |
| `frontend/README.md` | Giữ nhưng xem lại | Giá trị thấp, có thể gộp sau vào README chính. |
| `frontend/app/page.tsx` | Giữ | Trang demo chính. |
| `frontend/app/widget/page.tsx` | Giữ | Quan trọng cho widget nhúng. |
| `frontend/app/layout.tsx` | Giữ | Cần thiết. |
| `frontend/app/globals.css` | Giữ | Quan trọng cho UI demo. |
| `frontend/components/CitizenAssistant.tsx` | Giữ nhưng cần nâng cấp | Đây là nơi nên gắn intake stateful mới. |
| `frontend/components/DynamicForm.tsx` | Giữ | Quan trọng cho pre-submission check. |
| `frontend/components/GuidanceView.tsx` | Giữ | Quan trọng cho checklist và step guidance. |
| `frontend/components/FloatingAssistant.tsx` | Giữ | Hữu ích cho trải nghiệm demo. |
| `frontend/components/PortalHeader.tsx` | Giữ | Hữu ích cho trình diễn portal. |
| `frontend/components/Icon.tsx` | Giữ | Hạ tầng UI. |
| `frontend/lib/api.ts` | Giữ nhưng xem lại | Sẽ cần đổi nếu API intake đổi contract sâu hơn. |
| `frontend/lib/types.ts` | Giữ nhưng xem lại | Cần đồng bộ khi workflow intake được nâng cấp. |
| `frontend/public/embed.js` | Giữ | Rất quan trọng cho câu chuyện widget nhúng. |

## 5. tests

| Path | Quyết định | Nhận xét |
| --- | --- | --- |
| `tests/test_assistant.py` | Giữ | Giá trị cao cho intake/checklist. |
| `tests/test_validation.py` | Giữ | Giá trị cao cho pre-check. |
| `tests/test_chunking.py` | Giữ | Hữu ích cho indexing correctness. |
| `tests/test_indexing.py` | Giữ | Hữu ích cho ingest/index lifecycle. |
| `tests/test_model_config.py` | Giữ | Hữu ích. |
| `tests/test_procedure_api_model.py` | Giữ | Hữu ích cho API/data schema. |
| `tests/__init__.py` | Giữ | Chuẩn package test. |

## 6. docs

| Path | Quyết định | Nhận xét |
| --- | --- | --- |
| `docs/api-integration.md` | Giữ | Hữu ích. |
| `docs/architecture.md` | Giữ | Hữu ích. |
| `docs/data-governance.md` | Giữ | Hữu ích vì nhóm đang làm data rất mạnh. |
| `docs/data-sources.md` | Giữ | Hữu ích. |
| `docs/evaluation-report.md` | Giữ | Hữu ích cho pitch/judging. |
| `docs/frontend-architecture.md` | Giữ | Hữu ích cho UI/system discussion. |
| `docs/one-page-summary.md` | Giữ | Hữu ích cho deliverable. |
| `docs/render-deployment.md` | Giữ | Hữu ích cho demo public URL. |
| `docs/UNIFIED_ARCHITECTURE.md` | Giữ | Mới thêm, là tài liệu định hướng bản hợp nhất. |

## 7. scripts

| Path | Quyết định | Nhận xét |
| --- | --- | --- |
| `scripts/analyze_procedures.py` | Giữ nhưng xem lại | Có ích nội bộ, không critical cho demo runtime. |

## 8. Kết luận

Trong bản unified hiện tại:

- đã giữ lại code, tests, docs và deploy scaffold quan trọng
- đã bỏ dữ liệu trùng và file runtime thừa
- đã xóa `backend/package-lock.json` vì không hợp lý
- đã cấu hình để dùng chung `data-pipeline/data`

Bước tiếp theo nên làm là cấy workflow engine của `workflow-chatbot` vào luồng `/api/v1/intake`.
