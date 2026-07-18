from __future__ import annotations

from typing import Any

from govease_ai import ModelConfig
from govease_ai.embeddings import OpenAIEmbeddingService
from govease_ai.index_manifest import read_manifest

from backend.app.config import Settings


class ChromaRetriever:
    def __init__(self, settings: Settings):
        self.settings = settings

    def search(self, query: str, n_results: int = 6) -> list[dict[str, Any]]:
        try:
            import chromadb
        except ImportError:
            return []

        config = ModelConfig.from_env(
            embedding_provider="openai",
            embedding_model=self.settings.embedding_model,
        )
        if not config.openai_api_key:
            return []

        manifest = read_manifest(self.settings.chroma_path)
        if manifest is None or manifest.embedding_model != self.settings.embedding_model:
            return []

        client = chromadb.PersistentClient(path=self.settings.chroma_path)
        try:
            collection = client.get_collection(manifest.active_collection)
        except Exception:
            return []

        query_embedding = OpenAIEmbeddingService(
            api_key=config.openai_api_key,
            model=config.embedding_model,
            timeout_seconds=self.settings.openai_timeout_seconds,
        ).embed_query(query)
        result = collection.query(query_embeddings=[query_embedding], n_results=n_results)
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        return [
            {"id": chunk_id, "text": text, "metadata": metadata or {}}
            for chunk_id, text, metadata in zip(ids, documents, metadatas)
        ]
