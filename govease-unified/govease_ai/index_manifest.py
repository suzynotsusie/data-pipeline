from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


MANIFEST_FILENAME = "index_manifest.json"


@dataclass(frozen=True)
class IndexManifest:
    active_collection: str
    data_fingerprint: str
    embedding_model: str
    embedding_dimensions: int
    chunk_count: int
    schema_version: int = 1


def manifest_path(db_dir: str | Path) -> Path:
    return Path(db_dir) / MANIFEST_FILENAME


def read_manifest(db_dir: str | Path) -> IndexManifest | None:
    path = manifest_path(db_dir)
    if not path.exists():
        return None
    try:
        return IndexManifest(**json.loads(path.read_text(encoding="utf-8")))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def write_manifest(db_dir: str | Path, manifest: IndexManifest) -> None:
    path = manifest_path(db_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(asdict(manifest), ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
