from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .model_config import LOCAL_EMBEDDING_PROVIDER, ModelConfig


class EmbeddingService(Protocol):
    model: str

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


@dataclass
class OpenAIEmbeddingService:
    api_key: str
    model: str
    timeout_seconds: float = 30.0
    batch_size: int = 64

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            timeout=self.timeout_seconds,
            max_retries=2,
        )
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = list(texts[start : start + self.batch_size])
            response = client.embeddings.create(model=self.model, input=batch)
            embeddings.extend(item.embedding for item in sorted(response.data, key=lambda item: item.index))
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


@dataclass
class LocalEmbeddingService:
    model: str

    def __post_init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._encoder = SentenceTransformer(self.model)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._encoder.encode(list(texts), normalize_embeddings=False)
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def build_embedding_service(config: ModelConfig, *, timeout_seconds: float = 30.0) -> EmbeddingService:
    if config.embedding_provider == LOCAL_EMBEDDING_PROVIDER:
        return LocalEmbeddingService(config.local_embedding_model)
    if not config.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings.")
    return OpenAIEmbeddingService(
        api_key=config.openai_api_key,
        model=config.embedding_model,
        timeout_seconds=timeout_seconds,
    )
