from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Query

from govease_ai import ProcedureAssistant

from backend.app.config import settings
from backend.app.errors import APIError
from backend.app.schemas import (
    ChatRequest,
    ChatResponse,
    CheckRequest,
    IntakeRequest,
    IntakeResponse,
    ValidateRequest,
)
from backend.app.services.chat import ChatService
from backend.app.services.administrative_units import (
    AdministrativeUnitServiceError,
    NSO_SOURCE_URL,
    fetch_districts,
    fetch_provinces,
    fetch_wards,
)
from backend.app.services.catalog import CitizenCatalogService
from backend.app.services.index_manager import index_manager
from backend.app.services.procedures import (
    form_schema,
    list_procedures,
    procedure_detail,
)
from backend.app.services.workflow_intake import WorkflowIntakeService


router = APIRouter()
v1_router = APIRouter()
chat_service = ChatService(settings)
assistant = ProcedureAssistant()
workflow_intake = WorkflowIntakeService(assistant)
catalog_service = CitizenCatalogService(assistant.store)


def _health_payload() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}


@router.get("/health", tags=["operations"])
@v1_router.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return _health_payload()


@v1_router.get("/ready", tags=["operations"])
def readiness() -> dict:
    detailed_count = len(assistant.store.detailed_records())
    index = index_manager.snapshot()
    ready = detailed_count > 0 and index["ready"]
    return {
        "status": "ready" if ready else "degraded",
        "components": {
            "procedure_data": {"ready": detailed_count > 0, "detailed_procedures": detailed_count},
            "index": index,
            "openai": {"configured": bool(settings.openai_api_key)},
        },
    }


@router.post("/chat", response_model=ChatResponse, tags=["assistant"])
@v1_router.post("/chat", response_model=ChatResponse, tags=["assistant"])
def chat(request: ChatRequest) -> ChatResponse:
    try:
        return chat_service.answer(request.message, request.history)
    except Exception as exc:
        raise APIError(503, "AI_SERVICE_UNAVAILABLE", "Dịch vụ AI tạm thời không khả dụng.") from exc


@router.post("/intake", tags=["intake"])
def legacy_intake(request: ChatRequest) -> dict:
    return assistant.guided_intake(request.message)


@v1_router.post("/intake", response_model=IntakeResponse, tags=["intake"])
def intake(request: IntakeRequest) -> IntakeResponse:
    if request.procedure_code and not request.session_id:
        result = assistant.guided_intake(
            request.message,
            procedure_identifier=request.procedure_code,
            answers=request.answers,
        )
        needs_clarification = bool(result.get("needs_clarification"))
        return IntakeResponse(
            session_id=request.session_id or str(uuid4()),
            status="needs_clarification" if needs_clarification else "completed",
            needs_clarification=needs_clarification,
            clarifying_question_id=result.get("clarifying_question_id"),
            clarifying_question=result.get("clarifying_question"),
            answers=result.get("answers") or request.answers or {},
            confidence=float(result.get("confidence", 0)),
            procedure=result.get("procedure"),
            checklist=result.get("checklist") or {},
            examples=result.get("examples") or [],
            common_errors=result.get("common_errors") or [],
            sources=result.get("sources") or [],
            quick_replies=[],
            current_node_id=result.get("clarifying_question_id"),
            domain_key=None,
            domain_label=None,
            workflow_state={},
        )

    preferred_domain = catalog_service.preferred_workflow_family(request.group_key)
    result = workflow_intake.handle(
        request.message,
        session_id=request.session_id,
        preferred_domain_key=preferred_domain,
    )
    return IntakeResponse(
        session_id=result["session_id"],
        status=result["status"],
        needs_clarification=bool(result["needs_clarification"]),
        clarifying_question_id=result.get("clarifying_question_id"),
        clarifying_question=result.get("clarifying_question"),
        answers=result.get("answers") or {},
        confidence=float(result.get("confidence", 0)),
        procedure=result.get("procedure"),
        checklist=result.get("checklist") or {},
        examples=result.get("examples") or [],
        common_errors=result.get("common_errors") or [],
        sources=result.get("sources") or [],
        quick_replies=result.get("quick_replies") or [],
        current_node_id=result.get("current_node_id"),
        domain_key=result.get("domain_key"),
        domain_label=result.get("domain_label"),
        workflow_state=result.get("workflow_state") or {},
    )


@router.post("/check", tags=["validation"])
def legacy_check_submission(request: CheckRequest) -> dict:
    return _validate(request.procedure_identifier, request.submission)


@v1_router.get("/procedures", tags=["procedures"])
def procedures(
    detailed_only: bool = Query(default=True),
    group_key: str | None = Query(default=None),
) -> dict:
    if group_key:
        items = catalog_service.list_procedures_for_group(group_key)
        return {"items": items, "total": len(items), "group_key": group_key}
    items = list_procedures(assistant.store, detailed_only=detailed_only)
    return {"items": items, "total": len(items)}


@v1_router.get("/catalog/citizen-groups", tags=["catalog"])
def citizen_groups() -> dict:
    items = catalog_service.list_groups()
    return {"persona": "citizen", "items": items, "total": len(items)}


@v1_router.get("/catalog/citizen-groups/{group_key}", tags=["catalog"])
def citizen_group_detail(group_key: str) -> dict:
    payload = catalog_service.get_group(group_key)
    if payload is None:
        raise APIError(404, "GROUP_NOT_FOUND", "Không tìm thấy nhóm công dân.")
    return payload


@v1_router.get("/administrative-units/provinces", tags=["administrative-units"])
def provinces() -> dict:
    try:
        items = fetch_provinces()
    except AdministrativeUnitServiceError as exc:
        raise APIError(502, "ADMINISTRATIVE_UNIT_SERVICE_UNAVAILABLE", str(exc)) from exc
    return {"items": items, "total": len(items), "source_url": NSO_SOURCE_URL}


@v1_router.get("/administrative-units/districts", tags=["administrative-units"])
def districts(province_code: str = Query(min_length=1, max_length=10)) -> dict:
    try:
        items = fetch_districts(province_code)
    except AdministrativeUnitServiceError as exc:
        raise APIError(502, "ADMINISTRATIVE_UNIT_SERVICE_UNAVAILABLE", str(exc)) from exc
    return {"items": items, "total": len(items), "source_url": NSO_SOURCE_URL}


@v1_router.get("/administrative-units/wards", tags=["administrative-units"])
def wards(
    province_code: str = Query(min_length=1, max_length=10),
    district_code: str = Query(min_length=1, max_length=10),
) -> dict:
    try:
        items = fetch_wards(province_code, district_code)
    except AdministrativeUnitServiceError as exc:
        raise APIError(502, "ADMINISTRATIVE_UNIT_SERVICE_UNAVAILABLE", str(exc)) from exc
    return {"items": items, "total": len(items), "source_url": NSO_SOURCE_URL}


@v1_router.get("/procedures/{procedure_code}", tags=["procedures"])
def get_procedure(procedure_code: str) -> dict:
    return procedure_detail(_require_procedure(procedure_code))


@v1_router.get("/procedures/{procedure_code}/form-schema", tags=["procedures"])
def get_form_schema(procedure_code: str) -> dict:
    return form_schema(_require_procedure(procedure_code))


@v1_router.post("/procedures/{procedure_code}/validate", tags=["validation"])
def validate_submission(procedure_code: str, request: ValidateRequest) -> dict:
    return _validate(procedure_code, request.submission)


def _require_procedure(procedure_code: str):
    try:
        return assistant.store.require(procedure_code)
    except KeyError as exc:
        raise APIError(404, "PROCEDURE_NOT_FOUND", "Không tìm thấy thủ tục.") from exc


def _validate(procedure_code: str, submission: dict) -> dict:
    _require_procedure(procedure_code)
    return assistant.check_submission(procedure_code, submission)
