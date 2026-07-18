from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .model_config import ModelConfig


@dataclass(frozen=True)
class IntentParserStatus:
    enabled: bool
    provider: str
    model: str
    reason: str | None = None


class LLMIntentParser:
    """Optional low-cost layer: infer entry domain and disambiguation signals from free text."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.status = self._build_status(config)

    def parse(
        self, 
        user_message: str, 
        supported_domains: list[str] | None = None,
        context_slots: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        if not self.status.enabled:
            return None

        try:
            from openai import OpenAI
        except ImportError:
            return None

        # Default to the 11 new life-event domains if none provided
        if not supported_domains:
            supported_domains = [
                "co_con_nho", "hoc_tap", "viec_lam", "cu_tru_giay_to",
                "hon_nhan_gia_dinh", "dien_nha_dat", "suc_khoe_y_te",
                "phuong_tien_nguoi_lai", "huu_tri", "nguoi_than_qua_doi",
                "giai_quyet_khieu_kien"
            ]

        payload = {
            "user_message": user_message,
            "supported_domains": supported_domains,
            "context_slots": context_slots or {}
        }

        client = OpenAI(api_key=self.config.openai_api_key)
        try:
            response = client.chat.completions.create(
                model=self.config.llm_model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a public-service intent parsing AI. Classify the user's message into one of the "
                            "supported_domains (or unknown). "
                            "You must also detect if the query is ambiguous, missing prerequisites, or out of scope.\n"
                            "Return JSON strictly with these keys:\n"
                            "- domain (string or null)\n"
                            "- subdomain (string or null)\n"
                            "- intent (string or null)\n"
                            "- slot_updates (dict)\n"
                            "- ambiguity_flags (list of strings)\n"
                            "- missing_prerequisites (list of strings)\n"
                            "- clarifying_question_candidate (string or null)\n"
                            "- confidence (float between 0.0 and 1.0)\n"
                            "- out_of_scope (boolean)"
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
            )
        except Exception:
            return None

        content = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return None
            
        if not isinstance(parsed, dict):
            return None
            
        return {
            "domain": parsed.get("domain"),
            "subdomain": parsed.get("subdomain"),
            "intent": parsed.get("intent"),
            "slot_updates": parsed.get("slot_updates") or {},
            "ambiguity_flags": parsed.get("ambiguity_flags") or [],
            "missing_prerequisites": parsed.get("missing_prerequisites") or [],
            "clarifying_question_candidate": parsed.get("clarifying_question_candidate"),
            "confidence": float(parsed.get("confidence", 0.0)),
            "out_of_scope": bool(parsed.get("out_of_scope", False)),
        }

    @staticmethod
    def _build_status(config: ModelConfig) -> IntentParserStatus:
        if not config.enable_llm_intent:
            return IntentParserStatus(
                enabled=False,
                provider=config.llm_provider,
                model=config.llm_model,
                reason="disabled_by_config",
            )
        if not config.openai_api_key:
            return IntentParserStatus(
                enabled=False,
                provider=config.llm_provider,
                model=config.llm_model,
                reason="missing_openai_api_key",
            )
        return IntentParserStatus(
            enabled=True,
            provider=config.llm_provider,
            model=config.llm_model,
        )
