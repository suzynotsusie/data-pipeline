from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from govease_ai.index_manifest import read_manifest
from govease_ai.model_config import ModelConfig
from ingest import train_index


class FakeEmbeddingService:
    model = "test-embedding"

    def embed_documents(self, texts):
        return [[float(index), 1.0, 2.0] for index, _ in enumerate(texts)]

    def embed_query(self, text):
        return [0.0, 1.0, 2.0]


class FakeCollection:
    def __init__(self):
        self.items = {}

    def upsert(self, *, ids, documents, embeddings, metadatas):
        self.items.update({item_id: (document, embedding, metadata) for item_id, document, embedding, metadata in zip(ids, documents, embeddings, metadatas)})

    def count(self):
        return len(self.items)


class FakeChromaClient:
    def __init__(self):
        self.collections = {}

    def get_or_create_collection(self, *, name, metadata):
        return self.collections.setdefault(name, FakeCollection())

    def delete_collection(self, name):
        self.collections.pop(name, None)


class IndexingTests(unittest.TestCase):
    def test_ingest_supplies_embeddings_and_promotes_manifest_atomically(self) -> None:
        with TemporaryDirectory() as directory:
            client = FakeChromaClient()
            config = ModelConfig(embedding_model="test-embedding")
            report = train_index(
                db_dir=Path(directory),
                model_config=config,
                embedding_service=FakeEmbeddingService(),
                chroma_client=client,
            )
            manifest = read_manifest(directory)

        self.assertIsNotNone(manifest)
        self.assertEqual(report["collection"], manifest.active_collection)
        self.assertEqual(report["chunks"], manifest.chunk_count)
        self.assertEqual(3, manifest.embedding_dimensions)
        self.assertTrue(report["collection"].startswith("procedures-"))

    def test_real_persistent_chroma_accepts_and_queries_application_vectors(self) -> None:
        import chromadb

        with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            client = chromadb.PersistentClient(path=directory)
            config = ModelConfig(embedding_model="test-embedding")
            report = train_index(
                db_dir=Path(directory),
                model_config=config,
                embedding_service=FakeEmbeddingService(),
                chroma_client=client,
            )
            collection = client.get_collection(report["collection"])
            result = collection.query(query_embeddings=[[0.0, 1.0, 2.0]], n_results=1)

        self.assertEqual(1, len(result["ids"][0]))


if __name__ == "__main__":
    unittest.main()
