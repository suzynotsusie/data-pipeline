from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from govease_ai import ProcedureAssistant
from govease_ai.retrieval import normalize_text

from backend.app.config import Settings
from backend.app.rag.retriever import ChromaRetriever
from backend.app.schemas import ChatMessage, ChatResponse, Source


SYSTEM_PROMPT = """Bạn là GovEase AI, trợ lý hướng dẫn thủ tục hành chính Việt Nam.
Chỉ trả lời dựa trên NGỮ CẢNH được cung cấp. Trình bày ngắn gọn, dễ làm theo, dùng
tiếng Việt. Không bịa thêm quy định, lệ phí hoặc thời hạn. Nếu dữ liệu chưa đủ,
nói rõ và đề nghị người dùng kiểm tra nguồn chính thức. Không đưa ra tư vấn pháp lý.
"""


class ChatService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.assistant = ProcedureAssistant()
        self.chroma = ChromaRetriever(settings)

    def answer(self, message: str, history: list[ChatMessage]) -> ChatResponse:
        intake = self.assistant.guided_intake(message)
        guard = _guard_chat_answer(message, intake, self.assistant)
        if guard is not None:
            return ChatResponse(
                answer=guard["answer"],
                sources=_sources([], {"sources": guard.get("sources") or intake.get("sources") or []}),
                procedure=guard.get("procedure"),
                mode=guard["mode"],
            )
        chunks = self.chroma.search(message)
        if not chunks:
            chunks = intake.get("retrieved_context", [])

        sources = _sources(chunks, intake)
        if not self.settings.openai_api_key:
            return ChatResponse(
                answer=intake.get("answer") or _fallback_answer(intake),
                sources=sources,
                procedure=intake.get("procedure"),
                mode="retrieval-only",
            )

        context = "\n\n".join(
            f"[{index}] {chunk.get('text', '')}" for index, chunk in enumerate(chunks, start=1)
        )
        prior = "\n".join(f"{item.role}: {item.content}" for item in history[-6:])
        prompt = f"LỊCH SỬ:\n{prior or '(không có)'}\n\nNGỮ CẢNH:\n{context}\n\nCÂU HỎI:\n{message}"
        response = OpenAI(
            api_key=self.settings.openai_api_key,
            timeout=self.settings.openai_timeout_seconds,
            max_retries=2,
        ).responses.create(
            model=self.settings.llm_model,
            instructions=SYSTEM_PROMPT,
            input=prompt,
        )
        return ChatResponse(
            answer=response.output_text.strip(),
            sources=sources,
            procedure=intake.get("procedure"),
            mode="rag",
        )


def _fallback_answer(intake: dict[str, Any]) -> str:
    procedure = intake.get("procedure")
    if not procedure:
        return intake.get("clarifying_question") or "Bạn có thể mô tả rõ hơn thủ tục cần thực hiện không?"
    checklist = intake.get("checklist", {})
    documents = [item.get("name") for item in checklist.get("documents", []) if item.get("name")]
    steps = [item.get("title") or item.get("description") for item in checklist.get("steps", [])]
    lines = [f"Thủ tục phù hợp: {procedure['title']}."]
    if documents:
        lines.append("Hồ sơ cần chuẩn bị: " + "; ".join(documents[:6]) + ".")
    if steps:
        lines.append("Các bước chính: " + "; ".join(filter(None, steps[:5])) + ".")
    lines.append("Hãy đối chiếu lại nguồn chính thức trước khi nộp hồ sơ.")
    return "\n\n".join(lines)


def _guard_chat_answer(
    message: str,
    intake: dict[str, Any],
    assistant: ProcedureAssistant,
) -> dict[str, Any] | None:
    text = normalize_text(message)
    if _is_general_explanatory_query(text):
        return {
            "answer": _general_explanation_answer(text),
            "procedure": None,
            "sources": [],
            "mode": "explain-first",
        }

    procedure = intake.get("procedure") or {}
    confidence = float(intake.get("confidence", 0) or 0)
    if not procedure or (confidence < 2.0 and not intake.get("answers")):
        return {
            "answer": intake.get("clarifying_question")
            or "Mình chưa đủ chắc để chốt đúng thủ tục. Bạn mô tả ngắn gọn mục tiêu thực tế của bạn để mình hỏi tiếp từng bước nhé.",
            "procedure": None,
            "sources": intake.get("sources") or [],
            "mode": "clarify-first",
        }

    if _asks_about_fee(text):
        fee_answer = _fee_guard_answer(procedure.get("code"), assistant)
        if fee_answer is not None:
            return {
                "answer": fee_answer,
                "procedure": procedure,
                "sources": intake.get("sources") or [],
                "mode": "guarded-fee",
            }
    return None


def _is_general_explanatory_query(text: str) -> bool:
    if _contains_any(text, ["khac nhau the nao", "giai thich", "la gi", "khong hieu", "khong biet"]):
        if _contains_any(text, ["thuong tru", "tam tru", "tam vang", "cu tru"]):
            return True
        if _contains_any(text, ["khai sinh", "trich luc", "dang ky lai", "em be moi sinh"]):
            return True
    return False


def _general_explanation_answer(text: str) -> str:
    if _contains_any(text, ["thuong tru", "tam tru", "tam vang", "cu tru"]):
        return (
            "Giải thích rất ngắn:\n\n"
            "- Thường trú: bạn ở ổn định lâu dài tại một địa chỉ.\n"
            "- Tạm trú: bạn đang ở tạm tại một nơi khác, ví dụ thuê trọ hoặc ở nhờ trong một thời gian.\n"
            "- Tạm vắng: bạn báo là mình sẽ vắng khỏi nơi ở hiện tại trong một thời gian.\n\n"
            "Nếu bạn muốn, mình có thể đi tiếp theo kiểu rất thực tế: hỏi vài câu ngắn để chọn đúng thủ tục cho bạn."
        )
    return (
        "Giải thích rất ngắn:\n\n"
        "- Khai sinh mới: làm giấy khai sinh lần đầu cho bé.\n"
        "- Đăng ký lại khai sinh: đã từng có khai sinh nhưng mất hoặc thiếu bản chính hợp lệ.\n"
        "- Bản sao hoặc trích lục: xin lại thông tin đã đăng ký trước đó.\n\n"
        "Nếu bạn muốn, mình có thể hỏi từng câu ngắn để chọn đúng loại thủ tục phù hợp."
    )


def _asks_about_fee(text: str) -> bool:
    return _contains_any(
        text,
        [
            "bao nhieu tien",
            "le phi",
            "phi",
            "mat bao nhieu tien",
            "dong bao nhieu",
            "chi phi",
        ],
    )


def _fee_guard_answer(procedure_code: str | None, assistant: ProcedureAssistant) -> str | None:
    if not procedure_code:
        return "Mình chưa chốt đủ chắc thủ tục nên chưa thể nói chính xác về lệ phí."
    record = assistant.store.find(procedure_code)
    if record is None:
        return "Mình chưa tìm thấy đủ dữ liệu để trả lời chính xác về lệ phí."
    fee_summary = _extract_fee_summary(record.data)
    if fee_summary:
        return f"Lệ phí hiện có trong dữ liệu của mình: {fee_summary}"
    return (
        f"Mình chưa thấy mức phí/lệ phí được ghi rõ trong dữ liệu hiện có của thủ tục mã {procedure_code}. "
        "Để tránh nói sai, bạn nên kiểm tra lại trên nguồn chính thức hoặc nơi tiếp nhận hồ sơ."
    )


def _extract_fee_summary(data: dict[str, Any]) -> str | None:
    for key in ("fees", "fee", "charges", "cost", "le_phi", "phi_le_phi"):
        value = data.get(key)
        summary = _stringify_small_value(value)
        if summary:
            return summary
    return None


def _stringify_small_value(value: Any) -> str | None:
    if value in (None, "", [], {}, ()):
        return None
    if isinstance(value, str):
        cleaned = " ".join(value.split())
        return cleaned[:240] if cleaned else None
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        parts = [part for part in (_stringify_small_value(item) for item in value[:3]) if part]
        return "; ".join(parts) or None
    if isinstance(value, dict):
        try:
            compact = json.dumps(value, ensure_ascii=False)
        except TypeError:
            return None
        return compact[:240] if compact else None
    return None


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _sources(chunks: list[dict[str, Any]], intake: dict[str, Any]) -> list[Source]:
    output: list[Source] = []
    seen: set[str] = set()
    for chunk in chunks:
        metadata = chunk.get("metadata") or {}
        url = metadata.get("source_url", "")
        key = url or chunk.get("id", "")
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(Source(
            title=metadata.get("title") or metadata.get("procedure_title") or "Nguồn thủ tục",
            source_url=url,
            chunk_id=chunk.get("id") or chunk.get("chunk_id", ""),
        ))
    if not output:
        for source in intake.get("sources", []):
            output.append(Source(**source))
    return output[:6]
