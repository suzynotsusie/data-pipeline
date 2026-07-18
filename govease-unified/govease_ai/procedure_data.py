from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path(os.getenv("GOVEASE_DATA_ROOT", str(PROJECT_ROOT.parent / "data")))


@dataclass(frozen=True)
class ProcedureRecord:
    """Normalized view over either a detailed template or an index row."""

    id: str
    code: str
    title: str
    source_url: str
    path: Path
    data: dict[str, Any]
    detail_level: str


class ProcedureDataStore:
    def __init__(self, records: Iterable[ProcedureRecord]):
        self.records = list(records)
        self._by_key: dict[str, ProcedureRecord] = {}
        for record in self.records:
            for key in {record.id, record.code, _normalize_key(record.title)}:
                if key:
                    self._by_key[key] = record

    def find(self, identifier: str) -> ProcedureRecord | None:
        return self._by_key.get(identifier) or self._by_key.get(_normalize_key(identifier))

    def require(self, identifier: str) -> ProcedureRecord:
        record = self.find(identifier)
        if record is None:
            available = ", ".join(sorted(r.code for r in self.records if r.code))
            raise KeyError(f"Unknown procedure '{identifier}'. Available procedure codes: {available}")
        return record

    def detailed_records(self) -> list[ProcedureRecord]:
        return [record for record in self.records if record.detail_level == "detailed"]


def load_procedure_store(data_root: str | Path = DEFAULT_DATA_ROOT) -> ProcedureDataStore:
    data_root = Path(data_root)
    records_by_code: dict[str, ProcedureRecord] = {}

    for record in _load_index_records(data_root):
        _keep_best(records_by_code, record)

    for record in _load_detailed_records(data_root):
        _keep_best(records_by_code, record)

    return ProcedureDataStore(
        sorted(
            records_by_code.values(),
            key=lambda record: (record.detail_level != "detailed", record.title.lower()),
        )
    )


def _load_index_records(data_root: Path) -> Iterable[ProcedureRecord]:
    for path in data_root.glob("*/*_normalized.json"):
        payload = _read_json(path)
        entries = payload.get("procedures", []) if isinstance(payload, dict) else payload
        if not isinstance(entries, list):
            continue

        for item in entries:
            if not isinstance(item, dict):
                continue
            code = str(item.get("procedure_code") or item.get("code") or "").strip()
            title = str(item.get("title") or item.get("name") or item.get("procedure_name") or "").strip()
            if not code and not title:
                continue
            record_id = str(item.get("id") or code or _normalize_key(title)).strip()
            source_url = str(item.get("source_url") or "").strip()
            yield ProcedureRecord(
                id=record_id,
                code=code,
                title=title,
                source_url=source_url,
                path=path,
                data=item,
                detail_level="index",
            )


def _load_detailed_records(data_root: Path) -> Iterable[ProcedureRecord]:
    for path in data_root.glob("*/*.json"):
        if _is_generated_or_index_file(path):
            continue

        payload = _read_json(path)
        if not isinstance(payload, dict) or not _looks_like_detailed_template(payload):
            continue

        code = str(payload.get("procedure_code") or payload.get("code") or "").strip()
        title = str(
            payload.get("title") or payload.get("procedure_name") or payload.get("name") or code
        ).strip()
        record_id = str(payload.get("id") or code or _normalize_key(title)).strip()
        source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
        source_url = str(source.get("source_url") or payload.get("source_url") or "").strip()

        yield ProcedureRecord(
            id=record_id,
            code=code,
            title=title,
            source_url=source_url,
            path=path,
            data=payload,
            detail_level="detailed",
        )


def _keep_best(records_by_code: dict[str, ProcedureRecord], candidate: ProcedureRecord) -> None:
    key = candidate.code or candidate.id
    current = records_by_code.get(key)
    if current is None or _record_score(candidate) > _record_score(current):
        records_by_code[key] = candidate


def _record_score(record: ProcedureRecord) -> int:
    data = record.data
    score = 10 if record.detail_level == "detailed" else 1
    for field in ("documents", "steps", "common_errors", "faq", "input_fields", "validation_rules"):
        value = data.get(field)
        if value:
            score += len(value) if isinstance(value, list) else 2
    if record.source_url:
        score += 1
    return score


def _looks_like_detailed_template(payload: dict[str, Any]) -> bool:
    return bool(payload.get("documents") or payload.get("steps") or payload.get("common_errors"))


def _is_generated_or_index_file(path: Path) -> bool:
    name = path.name
    return (
        name.endswith("_normalized.json")
        or name.endswith("_raw.json")
        or name.endswith("_report.json")
        or name in {"build_report.json"}
        or name.endswith("_chunks.json")
        or name.endswith("_chunks.jsonl")
    )


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_key(value: str) -> str:
    return " ".join(value.lower().strip().split())
