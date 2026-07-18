# API Integration Guide

The external frontend should set its API base URL to the deployed Render service and call `/api/v1` endpoints. The complete interactive contract is available at `/docs` and `/openapi.json`.

## Guided intake

```http
POST /api/v1/intake
Content-Type: application/json
```

```json
{
  "message": "Tôi thuê nhà và cần đăng ký tạm trú",
  "history": [],
  "answers": {}
}
```

Keep the returned `session_id`. When the response has `status=needs_clarification`, append the prior messages to `history` on the next request. Once the frontend knows the chosen procedure, it may send `procedure_code` to keep the conversation scoped.

## Build a form

```http
GET /api/v1/procedures/1.004194/form-schema
```

Render controls from `fields`. Use `path` as the stable field identifier and send the resulting nested object to:

```http
POST /api/v1/procedures/1.004194/validate
```

```json
{
  "submission": {
    "applicant": {"full_name": "Nguyễn Văn A", "identity_number": "012345678901"},
    "temporary_address": "12 Nguyễn Trãi"
  }
}
```

Map every returned issue to its `field`. `blocking=true` prevents submission; warnings should remain visible but need not block the user.

## Stable errors

```json
{
  "error": {
    "code": "PROCEDURE_NOT_FOUND",
    "message": "Không tìm thấy thủ tục.",
    "request_id": "..."
  }
}
```

Send an optional `X-Request-ID` header to correlate frontend and backend logs. Configure the frontend origin in the backend `CORS_ORIGINS` allowlist.
