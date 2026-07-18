from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "GovEase AI API"
    environment: str = os.getenv("GOVEASE_ENV", "development")
    api_prefix: str = "/api"
    api_v1_prefix: str = "/api/v1"
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3010").split(",")
        if origin.strip()
    )
    data_root: str = os.getenv("GOVEASE_DATA_ROOT", "../data")
    chroma_path: str = os.getenv("CHROMA_PATH", "chroma_db")
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "procedures")
    embedding_model: str = os.getenv("GOVEASE_EMBEDDING_MODEL", "text-embedding-3-small")
    llm_model: str = os.getenv("GOVEASE_LLM_MODEL", "gpt-5-mini")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_timeout_seconds: float = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))
    auto_initialize_index: bool = os.getenv("GOVEASE_AUTO_INITIALIZE_INDEX", "true").lower() in {
        "1", "true", "yes", "on"
    }


settings = Settings()
