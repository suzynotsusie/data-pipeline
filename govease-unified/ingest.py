"""Build a versioned Chroma index using application-owned embeddings."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from govease_ai.chunking import build_chunks_for_store
from govease_ai.embeddings import EmbeddingService, build_embedding_service
from govease_ai.index_manifest import IndexManifest, write_manifest
from govease_ai.model_config import (
    CHECKPOINT_EMBEDDING_MODEL,
    CHECKPOINT_EMBEDDING_PROVIDER,
    LOCAL_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_PROVIDER,
    ModelConfig,
)
from govease_ai.procedure_data import DEFAULT_DATA_ROOT, load_procedure_store


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DB_DIR = PROJECT_ROOT / "chroma_db"
DEFAULT_COLLECTION_NAME = "procedures"


def train_index(
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
    db_dir: Path = DEFAULT_DB_DIR,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    model_config: ModelConfig | None = None,
    embedding_service: EmbeddingService | None = None,
    chroma_client: Any | None = None,
    reset: bool = False,
) -> dict[str, Any]:
    model_config = model_config or ModelConfig.from_env()
    store = load_procedure_store(data_root)
    chunks = build_chunks_for_store(store)
    if not chunks:
        raise RuntimeError(f"No chunks generated from {data_root}")

    fingerprint = data_fingerprint(chunks, model_config.embedding_model)
    versioned_name = versioned_collection_name(collection_name, fingerprint)
    embedder = embedding_service or build_embedding_service(model_config)
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedder.embed_documents(texts)
    if len(embeddings) != len(chunks) or not embeddings:
        raise RuntimeError("Embedding service returned an unexpected number of vectors.")

    if chroma_client is None:
        import chromadb

        chroma_client = chromadb.PersistentClient(path=str(db_dir))
    if reset:
        try:
            chroma_client.delete_collection(versioned_name)
        except Exception:
            pass

    collection = chroma_client.get_or_create_collection(
        name=versioned_name,
        metadata={
            "data_fingerprint": fingerprint,
            "embedding_model": model_config.embedding_model,
            "schema_version": 1,
        },
    )
    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[_clean_metadata(chunk["metadata"]) for chunk in chunks],
    )
    if collection.count() != len(chunks):
        raise RuntimeError("Chroma index verification failed: chunk count mismatch.")

    manifest = IndexManifest(
        active_collection=versioned_name,
        data_fingerprint=fingerprint,
        embedding_model=model_config.embedding_model,
        embedding_dimensions=len(embeddings[0]),
        chunk_count=len(chunks),
    )
    write_manifest(db_dir, manifest)
    return {
        "procedures": len(store.records),
        "detailed_procedures": len(store.detailed_records()),
        "chunks": len(chunks),
        "db_dir": str(db_dir),
        "collection": versioned_name,
        "data_fingerprint": fingerprint,
        "embedding_provider": model_config.embedding_provider,
        "embedding_model": model_config.embedding_model,
        "embedding_dimensions": len(embeddings[0]),
        "checkpoint_embedding": model_config.uses_checkpoint_embedding,
    }


def data_fingerprint(chunks: list[dict[str, Any]], embedding_model: str) -> str:
    payload = {
        "embedding_model": embedding_model,
        "chunks": [{"id": chunk["id"], "text": chunk["text"], "metadata": chunk["metadata"]} for chunk in chunks],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def versioned_collection_name(base_name: str, fingerprint: str) -> str:
    safe_base = "".join(character if character.isalnum() or character in "_-" else "-" for character in base_name)
    return f"{safe_base[:48]}-{fingerprint[:12]}"


def _clean_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    return {
        key: "" if value is None else value if isinstance(value, (str, int, float, bool)) else str(value)
        for key, value in metadata.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a versioned GovEase-AI Chroma index.")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--db-dir", type=Path, default=DEFAULT_DB_DIR)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION_NAME)
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--local-embeddings", action="store_true")
    parser.add_argument("--reset-target", action="store_true", help="Delete only the target version before rebuilding.")
    args = parser.parse_args()

    provider = LOCAL_EMBEDDING_PROVIDER if args.local_embeddings else CHECKPOINT_EMBEDDING_PROVIDER
    default_model = LOCAL_EMBEDDING_MODEL if args.local_embeddings else CHECKPOINT_EMBEDDING_MODEL
    config = ModelConfig.from_env(
        embedding_provider=provider,
        embedding_model=args.model_name or default_model,
    )
    report = train_index(
        data_root=args.data_root,
        db_dir=args.db_dir,
        collection_name=args.collection,
        model_config=config,
        reset=args.reset_target,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
