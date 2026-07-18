from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)


class IntakeRequest(ChatRequest):
    session_id: str | None = Field(default=None, max_length=100)
    procedure_code: str | None = Field(default=None, max_length=50)
    persona: str | None = Field(default=None, max_length=50)
    group_key: str | None = Field(default=None, max_length=100)
    subdomain_key: str | None = Field(default=None, max_length=100)
    candidate_procedure_codes: list[str] = Field(default_factory=list, max_length=50)
    answers: dict[str, Any] = Field(default_factory=dict)


class Source(BaseModel):
    title: str
    source_url: str = ""
    chunk_id: str = ""


class QuickReply(BaseModel):
    value: str
    label: str
    description: str = ""


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    procedure: dict[str, Any] | None = None
    mode: str


class CheckRequest(BaseModel):
    procedure_identifier: str
    submission: dict[str, Any]


class ValidateRequest(BaseModel):
    submission: dict[str, Any]


class IntakeResponse(BaseModel):
    session_id: str
    status: Literal["needs_clarification", "completed"]
    needs_clarification: bool
    clarifying_question_id: str | None = None
    clarifying_question: str | None = None
    answers: dict[str, Any] = Field(default_factory=dict)
    confidence: float
    procedure: dict[str, Any] | None = None
    checklist: dict[str, Any]
    examples: list[str] = Field(default_factory=list)
    common_errors: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    quick_replies: list[QuickReply] = Field(default_factory=list)
    current_node_id: str | None = None
    domain_key: str | None = None
    domain_label: str | None = None
    workflow_state: dict[str, Any] = Field(default_factory=dict)


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
