from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .model_config import ModelConfig
from .procedure_data import ProcedureRecord
from .validation import Issue


@dataclass(frozen=True)
class SemanticValidatorStatus:
    enabled: bool
    provider: str
    model: str
    reason: str | None = None


class LLMSemanticValidator:
    """Optional checkpoint layer 2: LLM cross-checks after deterministic rules."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.status = self._build_status(config)

    def validate(
        self,
        record: ProcedureRecord,
        submission: dict[str, Any],
        rule_issues: list[Issue],
    ) -> list[Issue]:
        if not self.status.enabled:
            return []

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install the openai package to enable LLM semantic validation.") from exc

        client = OpenAI(api_key=self.config.openai_api_key)
        payload = {
            "procedure": {
                "code": record.code,
                "title": record.title,
                "source_url": record.source_url,
                "common_errors": record.data.get("common_errors", []),
                "validation_rules": record.data.get("validation_rules", []),
            },
            "submission": submission,
            "existing_rule_issues": rule_issues,
        }

        response = client.chat.completions.create(
            model=self.config.llm_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the semantic validation layer for Vietnamese public-service forms. "
                        "Return JSON only with an 'issues' array. Each issue must include field, "
                        "rule_id, severity, message, and suggestion. Do not repeat existing rule issues."
                    ),
                },
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        )

        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        issues = parsed.get("issues", [])
        if not isinstance(issues, list):
            return []

        normalized: list[Issue] = []
        for item in issues:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "field": str(item.get("field") or "submission"),
                    "rule_id": str(item.get("rule_id") or "llm-semantic-check"),
                    "severity": str(item.get("severity") or "warning"),
                    "layer": "llm_semantic",
                    "message": str(item.get("message") or "Potential semantic conflict."),
                    "suggestion": str(item.get("suggestion") or "Review this field against the source procedure."),
                    "source_url": record.source_url,
                    "evidence": str(item.get("evidence") or "Potential conflict identified by semantic review."),
                    "blocking": False,
                }
            )
        return normalized

    @staticmethod
    def _build_status(config: ModelConfig) -> SemanticValidatorStatus:
        if not config.enable_llm_semantic:
            return SemanticValidatorStatus(
                enabled=False,
                provider=config.llm_provider,
                model=config.llm_model,
                reason="disabled_by_default",
            )
        if not config.openai_api_key:
            return SemanticValidatorStatus(
                enabled=False,
                provider=config.llm_provider,
                model=config.llm_model,
                reason="missing_openai_api_key",
            )
        return SemanticValidatorStatus(
            enabled=True,
            provider=config.llm_provider,
            model=config.llm_model,
        )
