from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock

from backend.app.config import Settings, settings
from govease_ai.chunking import build_chunks_for_store
from govease_ai.index_manifest import read_manifest
from govease_ai.procedure_data import load_procedure_store
from ingest import data_fingerprint, train_index


@dataclass(frozen=True)
class IndexState:
    status: str = "not_started"
    ready: bool = False
    active_collection: str | None = None
    chunk_count: int = 0
    message: str | None = None


class IndexManager:
    def __init__(self, config: Settings):
        self.config = config
        self._lock = Lock()
        self._state = IndexState()

    def snapshot(self) -> dict:
        with self._lock:
            return asdict(self._state)

    def initialize(self) -> None:
        self._set_state(IndexState(status="checking"))
        try:
            existing = self._validated_existing_index()
            if existing:
                self._set_state(existing)
                return
            if not self.config.auto_initialize_index:
                self._set_state(IndexState(status="not_initialized", message="Automatic indexing is disabled."))
                return
            if not self.config.openai_api_key:
                self._set_state(IndexState(status="degraded", message="OPENAI_API_KEY is not configured."))
                return

            self._set_state(IndexState(status="building"))
            report = train_index(
                db_dir=Path(self.config.chroma_path),
                collection_name=self.config.chroma_collection,
            )
            self._set_state(
                IndexState(
                    status="ready",
                    ready=True,
                    active_collection=report["collection"],
                    chunk_count=report["chunks"],
                )
            )
        except Exception as exc:
            self._set_state(IndexState(status="failed", message=f"{type(exc).__name__}: {exc}"))

    def _validated_existing_index(self) -> IndexState | None:
        manifest = read_manifest(self.config.chroma_path)
        if manifest is None or manifest.embedding_model != self.config.embedding_model:
            return None
        chunks = build_chunks_for_store(load_procedure_store())
        expected_fingerprint = data_fingerprint(chunks, self.config.embedding_model)
        if manifest.data_fingerprint != expected_fingerprint:
            return None

        import chromadb

        client = chromadb.PersistentClient(path=self.config.chroma_path)
        collection = client.get_collection(manifest.active_collection)
        if collection.count() != manifest.chunk_count:
            return None
        return IndexState(
            status="ready",
            ready=True,
            active_collection=manifest.active_collection,
            chunk_count=manifest.chunk_count,
        )

    def _set_state(self, state: IndexState) -> None:
        with self._lock:
            self._state = state


index_manager = IndexManager(settings)
