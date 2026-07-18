from __future__ import annotations

from typing import Any


def extract_markdown_tables(lines: list[str]) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if _looks_like_header_row(line) and index + 1 < len(lines) and _looks_like_separator(lines[index + 1].strip()):
            headers = [part.strip() for part in line.strip("|").split("|")]
            rows: list[dict[str, str]] = []
            index += 2
            while index < len(lines):
                current = lines[index].strip()
                if not current.startswith("|"):
                    break
                values = [part.strip() for part in current.strip("|").split("|")]
                if len(values) == len(headers):
                    rows.append(dict(zip(headers, values)))
                index += 1
            tables.append({"headers": headers, "rows": rows})
            continue
        index += 1
    return tables


def _looks_like_header_row(line: str) -> bool:
    return line.startswith("|") and line.endswith("|") and line.count("|") >= 2


def _looks_like_separator(line: str) -> bool:
    return bool(line) and set(line) <= {"|", "-", " ", ":"}
