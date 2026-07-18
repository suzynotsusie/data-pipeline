from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from .chunking import build_chunks_for_store
from .procedure_data import ProcedureDataStore


@dataclass(frozen=True)
class SearchResult:
    score: float
    chunk: dict[str, Any]


class KeywordRetriever:
    """Fast deterministic fallback for tests and local development."""

    def __init__(self, store: ProcedureDataStore):
        self.store = store
        self._supported_codes = {record.code for record in store.detailed_records() if record.code}
        self._indexed = []
        for chunk in build_chunks_for_store(store):
            meta = chunk["metadata"]
            searchable = " ".join(
                [
                    chunk["text"],
                    meta.get("procedure_title", ""),
                    meta.get("procedure_code", ""),
                    meta.get("content_type", ""),
                ]
            )
            self._indexed.append((chunk, _tokens(searchable)))

    def search(self, query: str, n_results: int = 5) -> list[SearchResult]:
        query_tokens = _expand_query_tokens(query)
        scored: list[SearchResult] = []
        for chunk, chunk_tokens in self._indexed:
            overlap = query_tokens & chunk_tokens
            if not overlap:
                continue
            meta = chunk["metadata"]
            score = float(len(overlap))
            if meta.get("content_type") in {"overview", "required_document", "step", "common_error"}:
                score += 0.5
            title_tokens = _tokens(meta.get("procedure_title", ""))
            score += 0.25 * len(query_tokens & title_tokens)
            scored.append(SearchResult(score=score, chunk=chunk))

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:n_results]

    def classify(self, query: str) -> tuple[str | None, float]:
        normalized = normalize_text(query)
        birth_signals = (
            "khai sinh", "giay khai sinh", "tre so sinh", "con moi sinh", "em be moi sinh",
            "con moi de", "ngay sinh cho con",
        )
        residence_signals = (
            "tam tru", "o tro", "thue nha", "noi o tam", "dang ky cu tru",
            "song tam thoi", "khac dia chi thuong tru",
        )
        if any(_contains_phrase(normalized, signal) for signal in birth_signals):
            return "1.001193", 100.0
        if any(_contains_phrase(normalized, signal) for signal in residence_signals):
            return "1.004194", 100.0
        generic_requests = (
            "ho tro thu tuc",
            "can lam giay to",
            "chua biet thu tuc",
            "khong biet lam gi",
        )
        if any(_contains_phrase(normalized, signal) for signal in generic_requests):
            return None, 0.0
        unsupported_domains = (
            "giay phep xay dung", "dang ky kinh doanh", "bao hiem xa hoi",
            "cap giay phep lai xe", "quyen su dung dat",
        )
        if any(_contains_phrase(normalized, signal) for signal in unsupported_domains):
            return None, 0.0

        results = self.search(query, n_results=12)
        by_code: dict[str, float] = {}
        for result in results:
            code = result.chunk["metadata"].get("procedure_code")
            if not code or code not in self._supported_codes:
                continue
            by_code[code] = by_code.get(code, 0.0) + result.score
        for example in FEW_SHOT_CLASSIFICATION_EXAMPLES:
            overlap = _expand_query_tokens(query) & _expand_query_tokens(example["text"])
            if overlap:
                by_code[example["procedure_code"]] = by_code.get(example["procedure_code"], 0.0) + (
                    len(overlap) * 1.5
                )
        if not by_code:
            return None, 0.0
        code, score = max(by_code.items(), key=lambda item: item[1])
        return code, score


FEW_SHOT_CLASSIFICATION_EXAMPLES = [
    {
        "text": "Tôi mới sinh con và muốn đăng ký khai sinh lần đầu.",
        "procedure_code": "1.001193",
    },
    {
        "text": "Không có giấy chứng sinh thì khai sinh cần giấy thay thế nào?",
        "procedure_code": "1.001193",
    },
    {
        "text": "Làm giấy khai sinh cho trẻ em bị bỏ rơi cần chuẩn bị gì?",
        "procedure_code": "1.001193",
    },
    {
        "text": "Tôi thuê phòng trọ và cần đăng ký tạm trú.",
        "procedure_code": "1.004194",
    },
    {
        "text": "Mới chuyển đến nơi ở tạm thời thì hồ sơ tạm trú gồm giấy tờ gì?",
        "procedure_code": "1.004194",
    },
    {
        "text": "Đăng ký tạm trú cho người chưa thành niên cần giấy đồng ý không?",
        "procedure_code": "1.004194",
    },
]


def normalize_text(value: str) -> str:
    value = value.lower().replace("đ", "d")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return value


def _tokens(value: str) -> set[str]:
    normalized = normalize_text(value)
    return {token for token in re.findall(r"[a-z0-9]+", normalized) if len(token) > 1}


def _contains_phrase(normalized: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", normalized) is not None


def _expand_query_tokens(query: str) -> set[str]:
    normalized = normalize_text(query)
    tokens = _tokens(normalized)
    if any(term in normalized for term in ("khai sinh", "giay khai sinh", "tre", "con moi sinh", "con moi de", "em be")):
        tokens.update({"khai", "sinh", "tre", "birth", "certificate"})
    if any(term in normalized for term in ("tam tru", "o tro", "thue nha", "noi o tam", "chuyen den", "song tam thoi")):
        tokens.update({"tam", "tru", "cu", "residence", "temporary"})
    return tokens
