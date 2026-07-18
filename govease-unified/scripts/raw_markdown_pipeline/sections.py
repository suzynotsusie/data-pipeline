from __future__ import annotations

from dataclasses import dataclass

from .utils import section_key


@dataclass
class Section:
    title: str
    key: str
    body: str


def split_sections(text: str) -> tuple[str, list[Section]]:
    lines = text.splitlines()
    title = ""
    sections: list[Section] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            if current_title is not None:
                sections.append(
                    Section(
                        title=current_title,
                        key=section_key(current_title),
                        body="\n".join(current_lines).strip(),
                    )
                )
            current_title = line[3:].strip()
            current_lines = []
            continue
        if current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        sections.append(
            Section(
                title=current_title,
                key=section_key(current_title),
                body="\n".join(current_lines).strip(),
            )
        )

    return title, sections
