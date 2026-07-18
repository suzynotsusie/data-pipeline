from __future__ import annotations

import re

from .utils import compact_whitespace


STEP_SPLIT_PATTERN = re.compile(
    r"(?=(?:^|\s)(?:Bước\s+\d+[:.]|[0-9]+\.\s+Bước\s*\d*[:.]|[a-zđ]\)\s+))",
    re.IGNORECASE | re.MULTILINE,
)


def parse_process(section_text: str) -> list[dict[str, object]]:
    raw = section_text.strip()
    if not raw:
        return []
    chunks = [chunk.strip(" \n") for chunk in STEP_SPLIT_PATTERN.split(raw) if compact_whitespace(chunk)]
    if len(chunks) == 1:
        chunks = _split_paragraph_steps(raw)
    steps = []
    for index, chunk in enumerate(chunks, start=1):
        title_match = re.match(r"^(Bước\s+\d+[:.]?|[a-zđ]\)|[a-zđ]\.)", chunk, re.IGNORECASE)
        title = title_match.group(1) if title_match else None
        content = compact_whitespace(chunk)
        actor = "authority" if any(token in content.lower() for token in ["cơ quan", "cán bộ", "công chức"]) else "user"
        steps.append(
            {
                "step_id": f"step_{index}",
                "index": index,
                "title": title,
                "content": content,
                "actor": actor,
                "time_hint": _extract_time_hint(content),
                "channel_hint": _extract_channel_hint(content),
                "artifacts": [],
            }
        )
    return steps


def _split_paragraph_steps(raw: str) -> list[str]:
    normalized_lines = [compact_whitespace(line) for line in raw.splitlines() if compact_whitespace(line)]
    if len(normalized_lines) > 1:
        return normalized_lines
    return [compact_whitespace(raw)]


def _extract_time_hint(text: str) -> str | None:
    match = re.search(r"([0-9]+\s*(?:ngày|tháng|năm)(?:\s*làm việc)?)", text, re.IGNORECASE)
    return match.group(1) if match else None


def _extract_channel_hint(text: str) -> str | None:
    lowered = text.lower()
    if "trực tuyến" in lowered:
        return "trực tuyến"
    if "bưu chính" in lowered:
        return "dịch vụ bưu chính"
    if "trực tiếp" in lowered:
        return "trực tiếp"
    return None
