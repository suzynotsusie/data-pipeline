from __future__ import annotations

from typing import Any

from .guidance import build_user_guidance
from .model_config import ModelConfig
from .procedure_data import ProcedureDataStore, ProcedureRecord, load_procedure_store
from .retrieval import KeywordRetriever, normalize_text
from .semantic_validation import LLMSemanticValidator
from .validation import SubmissionValidator


class ProcedureAssistant:
    def __init__(
        self,
        store: ProcedureDataStore | None = None,
        *,
        model_config: ModelConfig | None = None,
    ):
        self.model_config = model_config or ModelConfig.from_env()
        self.store = store or load_procedure_store()
        self.retriever = KeywordRetriever(self.store)
        self.validator = SubmissionValidator(self.store)
        self.semantic_validator = LLMSemanticValidator(self.model_config)

    def guided_intake(
        self,
        user_need: str,
        *,
        n_context: int = 6,
        procedure_identifier: str | None = None,
        answers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        answers = answers or {}
        retrieval_query = " ".join([user_need, *[str(value) for value in answers.values() if value]]).strip()
        if procedure_identifier:
            record = self.store.find(procedure_identifier)
            confidence = 100.0 if record else 0.0
        else:
            procedure_code, confidence = self.retriever.classify(retrieval_query)
            record = self.store.find(procedure_code) if procedure_code else None
        if record is None:
            result = {
                "needs_clarification": True,
                "clarifying_question_id": "procedure-domain",
                "clarifying_question": "Bạn muốn làm thủ tục về cư trú, hộ tịch hay một lĩnh vực khác?",
                "answers": answers,
                "confidence": 0.0,
                "procedure": None,
                "checklist": {"documents": [], "conditional_documents": [], "steps": []},
                "sources": [],
            }
            result["answer"] = _render_intake_answer(result, user_need=user_need)
            return result

        contexts = [
            result.chunk
            for result in self.retriever.search(retrieval_query, n_results=n_context)
            if result.chunk["metadata"].get("procedure_code") == record.code
        ]

        clarification = _first_clarifying_question(record)
        needs_clarification = confidence < 2.0 and not answers and clarification is not None

        result = {
            "needs_clarification": needs_clarification,
            "clarifying_question_id": clarification["id"] if needs_clarification else None,
            "clarifying_question": clarification["question"] if needs_clarification else None,
            "answers": answers,
            "confidence": round(confidence, 2),
            "procedure": {
                "id": record.id,
                "code": record.code,
                "title": record.title,
                "source_url": record.source_url,
                "detail_level": record.detail_level,
            },
            "checklist": {
                "documents": _documents(record, group="normally_required") + _documents(record, group="forms"),
                "conditional_documents": _documents(record, group="conditional"),
                "steps": _steps(record),
            },
            "examples": _examples(record),
            "common_errors": _common_errors(record),
            "sources": _sources(contexts, record),
            "model": {
                "classifier": "few_shot_plus_keyword_retrieval",
                "generation": "structured_json_checklist",
                "llm_provider": self.model_config.llm_provider,
                "llm_model": self.model_config.llm_model,
            },
            "retrieved_context": [
                {
                    "chunk_id": chunk["id"],
                    "content_type": chunk["metadata"].get("content_type"),
                    "title": chunk["metadata"].get("title"),
                    "text": chunk["text"],
                    "source_url": chunk["metadata"].get("source_url"),
                }
                for chunk in contexts
            ],
        }
        result["checklist"].update(build_user_guidance(record.data))
        result["answer"] = _render_intake_answer(result, user_need=user_need)
        return result

    def check_submission(self, procedure_identifier: str, submission: dict[str, Any]) -> dict[str, Any]:
        record = self.store.require(procedure_identifier)
        rule_issues = self.validator.validate(record.code or record.id, submission)
        llm_issues = self.semantic_validator.validate(record, submission, rule_issues)
        issues = _dedupe_issues(rule_issues + llm_issues)
        result = {
            "procedure": {
                "id": record.id,
                "code": record.code,
                "title": record.title,
                "source_url": record.source_url,
            },
            "ready_to_submit": not any(issue["severity"] == "error" for issue in issues),
            "issues": issues,
            "validation_layers": {
                "rules": {
                    "enabled": True,
                    "issue_count": len(rule_issues),
                },
                "llm_semantic": {
                    "enabled": self.semantic_validator.status.enabled,
                    "provider": self.semantic_validator.status.provider,
                    "model": self.semantic_validator.status.model,
                    "reason": self.semantic_validator.status.reason,
                    "issue_count": len(llm_issues),
                },
            },
        }
        result["answer"] = _render_submission_answer(result)
        return result


def _documents(record: ProcedureRecord, *, group: str) -> list[dict[str, Any]]:
    docs = record.data.get("documents")
    if not isinstance(docs, dict):
        return []
    values = docs.get(group) or []
    if not values and group == "normally_required":
        values = docs.get("presented") or _named_summary_items(docs.get("summary")) or []
    if not isinstance(values, list):
        return []

    normalized = []
    for item in values:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("document") or item.get("form_name") or item.get("condition")
        normalized.append(
            {
                "name": name,
                "condition": item.get("condition") or item.get("applies_when") or item.get("group"),
                "quantity": item.get("quantity") or _quantity_from_summary_item(item),
                "notes": item.get("notes") or item.get("note") or item.get("why") or item.get("tep_dinh_kem"),
                "alternatives": item.get("alternatives") or item.get("documents"),
            }
        )
    normalized = [item for item in normalized if _clean_text(item.get("name"))]
    if normalized:
        return normalized

    if group == "normally_required":
        guidance = record.data.get("guidance") or {}
        highlights = guidance.get("highlight_documents") if isinstance(guidance, dict) else []
        fallback: list[dict[str, Any]] = []
        for item in highlights or []:
            if not isinstance(item, dict):
                continue
            bucket = str(item.get("bucket") or "").strip()
            if bucket not in {"required", "presented"}:
                continue
            name = _clean_text(item.get("name"))
            if not name:
                continue
            fallback.append(
                {
                    "name": name,
                    "condition": "; ".join(item.get("conditions") or []) or None,
                    "quantity": None,
                    "notes": None,
                    "alternatives": None,
                }
            )
        return fallback
    return []


def _steps(record: ProcedureRecord) -> list[dict[str, Any]]:
    steps = []
    raw_steps = record.data.get("steps") or record.data.get("procedure_steps") or []
    if not raw_steps:
        raw_steps = [
            {
                "title": method.get("label"),
                "description": method.get("description"),
            }
            for method in record.data.get("submission_methods") or []
            if isinstance(method, dict)
        ]
    for index, item in enumerate(raw_steps, start=1):
        if not isinstance(item, dict):
            continue
        steps.append(
            {
                "order": item.get("order") or index,
                "title": item.get("title"),
                "description": item.get("description"),
                "example": item.get("example"),
            }
        )
    if steps:
        return steps
    return _derived_steps(record)


def _quantity_from_summary_item(item: dict[str, Any]) -> str | None:
    parts = []
    if item.get("ban_chinh") is not None:
        parts.append(f"{item['ban_chinh']} ban chinh")
    if item.get("ban_sao") is not None:
        parts.append(f"{item['ban_sao']} ban sao")
    return ", ".join(parts) or None


def _named_summary_items(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    return [
        item
        for item in values
        if isinstance(item, dict) and _clean_text(item.get("name") or item.get("document"))
    ]


def _derived_steps(record: ProcedureRecord) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    methods = record.data.get("submission_methods") or []
    if isinstance(methods, list):
        for item in methods:
            if not isinstance(item, dict):
                continue
            steps.append(
                {
                    "order": len(steps) + 1,
                    "title": item.get("label") or item.get("code"),
                    "description": item.get("description"),
                    "example": item.get("processing_time"),
                }
            )

    agency = record.data.get("agency")
    if isinstance(agency, dict):
        place = agency.get("submission_place") or agency.get("executing_agency")
        if place:
            steps.append(
                {
                    "order": len(steps) + 1,
                    "title": "Submission place",
                    "description": place,
                    "example": agency.get("executing_agency"),
                }
            )

    processing_note = record.data.get("processing_note")
    if processing_note:
        steps.append(
            {
                "order": len(steps) + 1,
                "title": "Processing note",
                "description": processing_note,
                "example": None,
            }
        )
    return steps


def _examples(record: ProcedureRecord) -> list[str]:
    examples = []
    for step in record.data.get("steps") or []:
        if isinstance(step, dict) and step.get("example"):
            examples.append(str(step["example"]))
    return examples[:2]


def _common_errors(record: ProcedureRecord) -> list[dict[str, str]]:
    errors = []
    for item in record.data.get("common_errors") or []:
        if not isinstance(item, dict):
            continue
        errors.append(
            {
                "field": str(item.get("field") or item.get("category") or item.get("error_type") or ""),
                "problem": str(item.get("issue") or item.get("error") or item.get("error_type") or ""),
                "fix": str(item.get("fix") or item.get("fix_suggestion") or item.get("suggested_check") or ""),
            }
        )
    return errors


def _first_clarifying_question(record: ProcedureRecord) -> dict[str, str] | None:
    questions = record.data.get("clarifying_questions") or []
    for item in questions:
        if isinstance(item, dict) and item.get("question"):
            return {
                "id": str(item.get("id") or "clarification"),
                "question": str(item["question"]),
            }
    return None


def _sources(contexts: list[dict[str, Any]], record: ProcedureRecord) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for chunk in contexts:
        meta = chunk.get("metadata", {})
        source_url = meta.get("source_url") or record.source_url
        key = (chunk.get("id", ""), source_url)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "chunk_id": chunk.get("id", ""),
                "title": meta.get("title") or record.title,
                "source_url": source_url,
            }
        )
    if not sources and record.source_url:
        sources.append({"chunk_id": record.id, "title": record.title, "source_url": record.source_url})
    return sources


def _render_intake_answer(result: dict[str, Any], *, user_need: str = "") -> str:
    procedure = result.get("procedure")
    if not procedure:
        question = result.get("clarifying_question") or "Bạn có thể mô tả rõ hơn thủ tục cần thực hiện không?"
        return f"Tôi chưa xác định chắc thủ tục phù hợp từ câu hỏi này. {question}"

    lines = [f"Thủ tục phù hợp là {procedure.get('title')} (mã {procedure.get('code')})."]
    if result.get("needs_clarification") and result.get("clarifying_question"):
        lines.append(f"Tôi cần xác nhận thêm: {result['clarifying_question']}")

    checklist = result.get("checklist") or {}
    documents = checklist.get("documents") or []
    next_step_summary = _clean_text(checklist.get("next_step_summary"))
    user_steps = checklist.get("user_steps") or []
    if documents:
        lines.append("Hồ sơ chính cần chuẩn bị:")
        lines.extend(_format_document_lines(documents, limit=10))

    conditional_documents = _conditional_documents_for_answer(
        user_need,
        checklist.get("conditional_documents") or [],
    )
    if conditional_documents:
        if _should_show_all_conditional_documents(user_need):
            lines.append("Giấy tờ chỉ cần nếu thuộc trường hợp đặc biệt:")
        else:
            lines.append("Giấy tờ phát sinh phù hợp với câu hỏi:")
        lines.extend(_format_document_lines(conditional_documents, limit=6))

    if next_step_summary:
        lines.append(next_step_summary)

    steps = user_steps or checklist.get("steps") or []
    if steps:
        lines.append("Các bước nên làm:")
        for step in steps:
            title = _clean_text(step.get("title")) or f"Bước {step.get('order')}"
            description = _clean_text(step.get("description"))
            lines.append(f"- {title}: {description}" if description else f"- {title}")

    errors = result.get("common_errors") or []
    if errors:
        lines.append("Lưu ý dễ sai:")
        for item in errors[:3]:
            problem = _clean_text(item.get("problem"))
            fix = _clean_text(item.get("fix"))
            if problem and fix:
                lines.append(f"- {problem} Cách sửa: {fix}")
            elif problem:
                lines.append(f"- {problem}")

    sources = [source for source in result.get("sources", []) if source.get("source_url")]
    if sources:
        lines.append(f"Nguồn tham khảo: {sources[0].get('source_url')}")
    return "\n".join(line for line in lines if line)


def _conditional_documents_for_answer(user_need: str, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not user_need:
        return []
    query = normalize_text(user_need)
    matched = [item for item in documents if _conditional_document_matches(query, item)]
    if matched:
        return matched
    if _should_show_all_conditional_documents(user_need):
        return documents
    return []


def _should_show_all_conditional_documents(user_need: str) -> bool:
    query = normalize_text(user_need)
    return _has_any(
        query,
        (
            "ho so",
            "giay to",
            "gom gi",
            "can gi",
            "can biet",
            "can chuan bi",
            "chuan bi gi",
        ),
    )


def _conditional_document_matches(normalized_query: str, item: dict[str, Any]) -> bool:
    condition_text = normalize_text(
        " ".join(
            _clean_text(item.get(key))
            for key in ("condition", "name", "document", "notes")
            if item.get(key)
        )
    )
    if _has_any(normalized_query, ("bo roi", "bi bo roi")):
        return _has_any(condition_text, ("bo roi", "bi bo roi"))
    if _has_any(normalized_query, ("mang thai ho", "thai ho")):
        return _has_any(condition_text, ("mang thai ho", "thai ho"))
    if _has_any(normalized_query, ("uy quyen", "lam thay", "nop thay", "nguoi khac")):
        return _has_any(condition_text, ("uy quyen", "nguoi khac"))
    if _has_any(normalized_query, ("chua thanh nien", "vi thanh nien", "con nho")):
        return _has_any(condition_text, ("chua thanh nien", "vi thanh nien"))
    return False


def _has_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(term in value for term in terms)


def _render_submission_answer(result: dict[str, Any]) -> str:
    procedure = result.get("procedure") or {}
    title = procedure.get("title") or "thủ tục này"
    code = procedure.get("code")
    heading = f"Kết quả kiểm tra hồ sơ cho {title}"
    if code:
        heading += f" (mã {code})"
    heading += "."

    if result.get("ready_to_submit"):
        return "\n".join(
            [
                heading,
                "Hồ sơ chưa có lỗi nghiêm trọng theo các quy tắc hiện tại và có thể chuẩn bị để nộp.",
            ]
        )

    lines = [heading, "Hồ sơ chưa sẵn sàng để nộp. Cần xử lý các điểm sau:"]
    for issue in result.get("issues") or []:
        field = _clean_text(issue.get("field"))
        message = _clean_text(issue.get("message"))
        suggestion = _clean_text(issue.get("suggestion"))
        rule_id = _clean_text(issue.get("rule_id"))
        label = field or rule_id or "Mục hồ sơ"
        detail = message or "Có lỗi cần kiểm tra."
        line = f"- {label}: {detail}"
        if suggestion:
            line += f" Cách sửa: {suggestion}"
        lines.append(line)

    source_url = procedure.get("source_url")
    if source_url:
        lines.append(f"Nguồn tham khảo: {source_url}")
    return "\n".join(lines)


def _format_document_lines(documents: list[dict[str, Any]], *, limit: int) -> list[str]:
    lines = []
    visible_documents = documents if len(documents) <= limit + 2 else documents[:limit]
    for item in visible_documents:
        name = _clean_text(item.get("name")) or "Giấy tờ"
        details = []
        quantity = _clean_text(item.get("quantity"))
        condition = _clean_text(item.get("condition"))
        alternatives = item.get("alternatives")
        if quantity and quantity != "0 ban chinh, 0 ban sao":
            details.append(quantity)
        if condition:
            details.append(f"nhóm/điều kiện: {condition}")
        if isinstance(alternatives, list) and alternatives:
            details.append("có thể thay thế bằng: " + "; ".join(str(value) for value in alternatives[:3]))
        suffix = f" ({'; '.join(details)})" if details else ""
        lines.append(f"- {name}{suffix}")
    if len(documents) > len(visible_documents):
        lines.append(f"- Còn {len(documents) - len(visible_documents)} giấy tờ khác trong checklist chi tiết.")
    return lines


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _dedupe_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for issue in issues:
        key = (str(issue.get("layer")), str(issue.get("field")), str(issue.get("rule_id")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    return deduped
