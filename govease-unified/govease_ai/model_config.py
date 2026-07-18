from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


CHECKPOINT_EMBEDDING_PROVIDER = "openai"
CHECKPOINT_EMBEDDING_MODEL = "text-embedding-3-small"
CHECKPOINT_LLM_PROVIDER = "openai-codex"
CHECKPOINT_LLM_MODEL = "gpt-5-mini"
LOCAL_EMBEDDING_PROVIDER = "local"
LOCAL_EMBEDDING_MODEL = "paraphrase-multilingual-mpnet-base-v2"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ModelConfig:
    embedding_provider: str = CHECKPOINT_EMBEDDING_PROVIDER
    embedding_model: str = CHECKPOINT_EMBEDDING_MODEL
    local_embedding_model: str = LOCAL_EMBEDDING_MODEL
    allow_local_embedding_fallback: bool = False
    llm_provider: str = CHECKPOINT_LLM_PROVIDER
    llm_model: str = CHECKPOINT_LLM_MODEL
    enable_llm_intent: bool = True
    enable_llm_semantic: bool = False
    openai_api_key: str | None = None

    @classmethod
    def from_env(
        cls,
        *,
        embedding_provider: str | None = None,
        embedding_model: str | None = None,
        allow_local_embedding_fallback: bool | None = None,
        enable_llm_semantic: bool | None = None,
        enable_llm_intent: bool | None = None,
        env_file: str | Path | None = None,
    ) -> "ModelConfig":
        _load_env_file(env_file)
        provider = embedding_provider or os.getenv("GOVEASE_EMBEDDING_PROVIDER") or CHECKPOINT_EMBEDDING_PROVIDER
        local_model = os.getenv("GOVEASE_LOCAL_EMBEDDING_MODEL") or LOCAL_EMBEDDING_MODEL
        default_embedding_model = local_model if provider == LOCAL_EMBEDDING_PROVIDER else CHECKPOINT_EMBEDDING_MODEL
        selected_embedding_model = _select_embedding_model(
            explicit_provider=embedding_provider,
            explicit_model=embedding_model,
            default_model=default_embedding_model,
        )

        return cls(
            embedding_provider=provider,
            embedding_model=selected_embedding_model,
            local_embedding_model=local_model,
            allow_local_embedding_fallback=_env_bool(
                "GOVEASE_ALLOW_LOCAL_EMBEDDING_FALLBACK",
                default=False if allow_local_embedding_fallback is None else allow_local_embedding_fallback,
            ),
            llm_provider=os.getenv("GOVEASE_LLM_PROVIDER") or CHECKPOINT_LLM_PROVIDER,
            llm_model=os.getenv("GOVEASE_LLM_MODEL") or CHECKPOINT_LLM_MODEL,
            enable_llm_intent=_env_bool(
                "GOVEASE_ENABLE_LLM_INTENT",
                default=True if enable_llm_intent is None else enable_llm_intent,
            ),
            enable_llm_semantic=_env_bool(
                "GOVEASE_ENABLE_LLM_SEMANTIC",
                default=False if enable_llm_semantic is None else enable_llm_semantic,
            ),
            openai_api_key=os.getenv("OPENAI_API_KEY") or os.getenv("CHROMA_OPENAI_API_KEY"),
        )

    @property
    def uses_checkpoint_embedding(self) -> bool:
        return (
            self.embedding_provider == CHECKPOINT_EMBEDDING_PROVIDER
            and self.embedding_model == CHECKPOINT_EMBEDDING_MODEL
        )


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _select_embedding_model(
    *,
    explicit_provider: str | None,
    explicit_model: str | None,
    default_model: str,
) -> str:
    if explicit_model:
        return explicit_model
    if explicit_provider:
        return default_model
    return os.getenv("GOVEASE_EMBEDDING_MODEL") or default_model


def _load_env_file(env_file: str | Path | None) -> None:
    paths = [Path(env_file)] if env_file else [PROJECT_ROOT / ".env"]
    for path in paths:
        if not path.exists():
            continue
        try:
            from dotenv import load_dotenv

            load_dotenv(path, override=False)
        except ImportError:
            _load_env_file_without_dependency(path)
        break


def _load_env_file_without_dependency(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
