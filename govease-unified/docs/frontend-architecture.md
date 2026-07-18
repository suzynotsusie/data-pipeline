# Frontend Architecture

The frontend lives in the same repository for hackathon delivery but is a separate deployable application. It does not import Python modules, inspect `data/`, or access Chroma directly.

```mermaid
flowchart LR
    Citizen[Citizen] --> Portal[Next.js portal demo]
    Portal --> Assistant[Embedded GovEase assistant]
    External[Existing public-service portal] -->|embed.js + iframe| Widget[/widget]
    Widget --> Assistant
    Assistant -->|HTTPS JSON /api/v1| API[FastAPI on Render]
    API --> Intake[Guided intake]
    API --> Forms[Procedure form schema]
    API --> Rules[Validation engine]
    API --> RAG[Chroma + OpenAI]
    RAG --> Sources[dichvucong.gov.vn citations]
```

## UI composition

- `PortalHeader`: simulated public-service navigation and explicit demo marking.
- `CitizenAssistant`: state machine for need, guidance and validation.
- `GuidanceView`: documents, conditional requirements, steps and citations.
- `DynamicForm`: renders controls from `form-schema`, creates nested submissions and maps issues to fields.
- `FloatingAssistant`: demonstrates an in-portal chatbot entry point.
- `/widget` and `public/embed.js`: iframe integration for a plain external website.

## Models and APIs

The browser never calls OpenAI or Chroma. It uses the backend endpoints documented in `api-integration.md`. The backend uses `text-embedding-3-small` for retrieval, a configurable Codex model through the Responses API for generated answers, Chroma for vector search, and deterministic plus optional semantic validation.

## State and privacy

Conversation state is returned as `session_id`; the browser sends prior user/assistant messages back with the next intake request. Form values remain in React memory and are sent only to `/validate`. The demo does not persist identity numbers or form submissions in browser storage.

## Deployment

- Frontend: Vercel with root `vercel.json` and `NEXT_PUBLIC_API_URL` pointing to Render.
- Backend: Render with the Vercel origin included in `CORS_ORIGINS`.
- `/widget` can be embedded on any allowed origin through `embed.js`.
