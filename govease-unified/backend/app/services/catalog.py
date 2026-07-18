from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from govease_ai.procedure_data import ProcedureDataStore, ProcedureRecord


CATALOG_ROOT = Path(__file__).resolve().parents[3] / "data" / "catalog"
GROUPS_PATH = CATALOG_ROOT / "citizen_groups.json"
MAPPING_PATH = CATALOG_ROOT / "citizen_procedure_mapping.csv"
PIPELINE_ROOT = Path(__file__).resolve().parents[4]
FULL_DATA_PATH = PIPELINE_ROOT / "main" / "full-data.csv"
RAW_DATA_ROOT = PIPELINE_ROOT / "raw_data"


@dataclass(frozen=True)
class CatalogGroup:
    key: str
    label: str
    official_group_id: int
    official_url: str
    description: str
    preferred_workflow_family: str | None = None


class CitizenCatalogService:
    def __init__(self, store: ProcedureDataStore) -> None:
        self.store = store
        self.groups = self._load_groups()
        self.mappings = self._load_mapping_rows()
        self.full_data_by_code = self._load_full_data_by_code()
        self.group_index: dict[str, list[dict[str, Any]]] = {}
        for row in self.mappings:
            self.group_index.setdefault(str(row["group_key"]), []).append(row)

    def list_groups(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for group in self.groups:
            procedures = self._group_procedure_cards(group.key)
            items.append(
                {
                    "key": group.key,
                    "label": group.label,
                    "official_group_id": group.official_group_id,
                    "official_url": group.official_url,
                    "description": group.description,
                    "preferred_workflow_family": group.preferred_workflow_family,
                    "procedure_count": len(procedures),
                    "raw_data_count": sum(1 for item in procedures if item["raw_data_available"]),
                    "workflow_ready_count": sum(1 for item in procedures if item["support_level"] == "workflow_ready"),
                    "catalog_ready_count": sum(1 for item in procedures if item["support_level"] == "catalog_ready"),
                    "raw_only_count": sum(1 for item in procedures if item["support_level"] == "raw_only"),
                }
            )
        return items

    def get_group(self, group_key: str) -> dict[str, Any] | None:
        group = next((item for item in self.groups if item.key == group_key), None)
        if group is None:
            return None
        procedures = self._group_procedure_cards(group.key)
        return {
            "key": group.key,
            "label": group.label,
            "official_group_id": group.official_group_id,
            "official_url": group.official_url,
            "description": group.description,
            "preferred_workflow_family": group.preferred_workflow_family,
            "procedures": procedures,
            "procedure_count": len(procedures),
        }

    def list_group_procedure_codes(self, group_key: str) -> list[str]:
        return [str(item["procedure_code"]) for item in self.group_index.get(group_key, [])]

    def preferred_workflow_family(self, group_key: str | None) -> str | None:
        if not group_key:
            return None
        group = next((item for item in self.groups if item.key == group_key), None)
        return group.preferred_workflow_family if group else None

    def list_procedures_for_group(self, group_key: str) -> list[dict[str, Any]]:
        return self._group_procedure_cards(group_key)

    def _group_procedure_cards(self, group_key: str) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        for row in self.group_index.get(group_key, []):
            code = str(row["procedure_code"])
            record = self.store.find(code)
            full_data = self.full_data_by_code.get(code, {})
            cards.append(
                {
                    "code": code,
                    "title": self._pick_title(record, full_data),
                    "source_url": self._pick_source_url(record, full_data),
                    "field": full_data.get("LÄ©nh vá»±c") or full_data.get("field"),
                    "raw_data_available": self._has_raw_data(code),
                    "normalized_available": _as_bool(row.get("normalized_available")),
                    "detail_level": record.detail_level if record else None,
                    "workflow_family": row.get("workflow_family") or None,
                    "support_level": row.get("support_level") or "catalog_ready",
                    "in_workflow_dataset": _as_bool(row.get("in_workflow_dataset") or row.get("workflow_data_available")),
                    "notes": row.get("notes") or "",
                }
            )
        return cards

    def _pick_title(self, record: ProcedureRecord | None, full_data: dict[str, str]) -> str:
        if record and record.title:
            return record.title
        return full_data.get("TÃªn", "")

    def _pick_source_url(self, record: ProcedureRecord | None, full_data: dict[str, str]) -> str:
        if record and record.source_url:
            return record.source_url
        return full_data.get("URL", "")

    def _has_raw_data(self, code: str) -> bool:
        folder = RAW_DATA_ROOT / code.replace(".", "_")
        return folder.exists() and any(folder.glob("*_procedure_detail.md"))

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_groups() -> list[CatalogGroup]:
        payload = json.loads(GROUPS_PATH.read_text(encoding="utf-8"))
        groups = payload.get("groups", []) if isinstance(payload, dict) else []
        return [
            CatalogGroup(
                key=str(item["key"]),
                label=str(item["label"]),
                official_group_id=int(item["official_group_id"]),
                official_url=str(item["official_url"]),
                description=str(item.get("description") or ""),
                preferred_workflow_family=str(item["preferred_workflow_family"]) if item.get("preferred_workflow_family") else None,
            )
            for item in groups
        ]

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_mapping_rows() -> list[dict[str, str]]:
        with MAPPING_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_full_data_by_code() -> dict[str, dict[str, str]]:
        if not FULL_DATA_PATH.exists():
            return {}
        with FULL_DATA_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        result: dict[str, dict[str, str]] = {}
        for row in rows:
            code = str(row.get("MÃ£ sá»‘") or "").strip()
            if code:
                result[code] = row
        return result


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
