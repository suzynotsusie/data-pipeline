from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from govease_ai import ModelConfig, ProcedureAssistant
from govease_ai.model_config import (
    CHECKPOINT_EMBEDDING_MODEL,
    CHECKPOINT_EMBEDDING_PROVIDER,
    LOCAL_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_PROVIDER,
)


class ModelConfigTests(unittest.TestCase):
    def test_default_model_matches_checkpoint_embedding(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            config = ModelConfig.from_env()
        self.assertEqual(CHECKPOINT_EMBEDDING_PROVIDER, config.embedding_provider)
        self.assertEqual(CHECKPOINT_EMBEDDING_MODEL, config.embedding_model)
        self.assertTrue(config.uses_checkpoint_embedding)

    def test_local_embedding_fallback_is_explicit(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            config = ModelConfig.from_env(embedding_provider=LOCAL_EMBEDDING_PROVIDER)
        self.assertEqual(LOCAL_EMBEDDING_PROVIDER, config.embedding_provider)
        self.assertEqual(LOCAL_EMBEDDING_MODEL, config.embedding_model)
        self.assertFalse(config.uses_checkpoint_embedding)

    def test_env_file_is_loaded(self) -> None:
        with TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("OPENAI_API_KEY=test-key-from-env-file\n", encoding="utf-8")
            with patch.dict("os.environ", {}, clear=True):
                config = ModelConfig.from_env(env_file=env_file)
        self.assertEqual("test-key-from-env-file", config.openai_api_key)

    def test_assistant_exposes_checkpoint_generation_metadata(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assistant = ProcedureAssistant()
        result = assistant.guided_intake("Toi moi sinh con va muon dang ky khai sinh")
        self.assertEqual("few_shot_plus_keyword_retrieval", result["model"]["classifier"])
        self.assertEqual("structured_json_checklist", result["model"]["generation"])


if __name__ == "__main__":
    unittest.main()
