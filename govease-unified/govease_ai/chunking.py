from __future__ import annotations

import json
from typing import Any

from .procedure_data import ProcedureDataStore, ProcedureRecord


def build_chunks_for_store(store: ProcedureDataStore) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for record in store.records:
        chunks.extend(build_chunks(record))
    return chunks


def build_chunks(record: ProcedureRecord) -> list[dict[str, Any]]:
    data = record.data
    chunks: list[dict[str, Any]] = []

    def add(content_type: str, title: str, content: Any, index: int = 0, importance: str = "medium") -> None:
        text = _stringify(content)
        if not text:
            return
        chunk_id = f"{record.id}-{content_type}-{index}".replace(" ", "-")
        chunks.append(
            {
                "id": chunk_id,
                "text": text,
                "metadata": {
                    "procedure_id": record.id,
                    "procedure_code": record.code,
                    "procedure_title": record.title,
                    "source_url": record.source_url,
                    "content_type": content_type,
                    "title": title,
                    "importance": importance,
                    "detail_level": record.detail_level,
                    "data_path": str(record.path),
                },
            }
        )

    add("overview", record.title, _overview_text(record), importance="critical")

    agency = data.get("agency")
    if agency:
        add("agency", "Agency and submission place", agency, importance="high")

    submission_methods = data.get("submission_methods")
    if submission_methods:
        add("submission_methods", "Submission methods", submission_methods, importance="high")

    documents = data.get("documents")
    if isinstance(documents, dict):
        _add_document_chunks(add, documents)

    for index, step in enumerate(data.get("steps") or [], start=1):
        title = _first_text(step, "title") or f"Step {index}"
        add("step", title, step, index=index, importance="high")

    for index, error in enumerate(data.get("common_errors") or [], start=1):
        title = _first_text(error, "field", "category", "error_type", "error") or f"Common error {index}"
        add("common_error", title, error, index=index, importance="high")

    for index, question in enumerate(data.get("faq") or [], start=1):
        title = _first_text(question, "question") or f"FAQ {index}"
        add("faq", title, question, index=index)

    for index, field in enumerate(data.get("input_fields") or [], start=1):
        title = _first_text(field, "label", "field") or f"Input field {index}"
        add("input_field", title, field, index=index)

    for index, rule in enumerate(data.get("validation_rules") or [], start=1):
        title = _first_text(rule, "id", "field") or f"Validation rule {index}"
        add("validation_rule", title, rule, index=index, importance="high")

    if record.detail_level == "index":
        for key in ("description", "notes", "processing_time_days", "fee", "priority", "status"):
            if data.get(key) not in (None, "", []):
                add(key, key, {key: data[key]}, importance="medium")

    return chunks


def _add_document_chunks(add, documents: dict[str, Any]) -> None:
    groups = [
        ("forms", "form", "Form", "high"),
        ("normally_required", "required_document", "Required document", "critical"),
        ("summary", "required_document", "Required document", "critical"),
        ("conditional", "conditional_document", "Conditional document", "high"),
        ("outputs", "output", "Output", "medium"),
        ("notes", "document_note", "Document note", "medium"),
    ]
    for group_key, content_type, default_title, importance in groups:
        values = documents.get(group_key)
        if isinstance(values, list):
            for index, item in enumerate(values, start=1):
                title = _first_text(item, "name", "document", "form_name", "condition") or f"{default_title} {index}"
                add(content_type, title, item, index=index, importance=importance)
        elif values:
            add(content_type, default_title, values, index=1, importance=importance)


def _overview_text(record: ProcedureRecord) -> str:
    data = record.data
    parts = [f"Procedure: {record.title}", f"Code: {record.code}"]
    for key in ("description", "deadline_note", "processing_note", "notes"):
        if data.get(key):
            parts.append(f"{key}: {_stringify(data[key])}")

    scope = data.get("scope")
    if isinstance(scope, dict):
        for key in ("included", "routing_note", "not_included"):
            if scope.get(key):
                parts.append(f"scope.{key}: {_stringify(scope[key])}")

    return "\n".join(part for part in parts if part and part != "Code: ")


def _first_text(item: Any, *keys: str) -> str:
    if not isinstance(item, dict):
        return ""
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _stringify(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
