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
    """Optional low-cost layer: infer entry domain and a few slots from free text."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.status = self._build_status(config)

    def parse(self, user_message: str) -> dict[str, Any] | None:
        if not self.status.enabled:
            return None

        try:
            from openai import OpenAI
        except ImportError:
            return None

        payload = {
            "user_message": user_message,
            "supported_domains": [
                "birth_registration",
                "residence_management",
            ],
            "birth_slots": {
                "request_type": [
                    "new_registration",
                    "re_registration",
                    "copy_extract",
                    "foreign_record_note",
                    "existing_personal_documents",
                    "mobile_service",
                ],
                "birth_location": ["domestic", "abroad"],
                "has_foreign_element": ["yes", "no"],
                "combined_parent_recognition": ["yes", "no"],
                "wants_linked_bundle": ["none", "bhyt_only", "bhyt_and_residence"],
                "service_channel": ["standard", "mobile", "border_area", "consular"],
                "request_type_detail": ["birth_only", "multi_civil_status"],
            },
            "residence_slots": {
                "residence_goal": [
                    "register_permanent",
                    "register_temporary",
                    "extend_temporary",
                    "delete_temporary",
                    "delete_permanent",
                    "split_household",
                    "adjust_data",
                    "absence_notice",
                    "lodging_notice",
                    "residence_confirmation",
                    "eligibility_confirmation",
                    "fallback_info_declaration",
                ],
                "residence_place_type": ["owned_home", "rented_borrowed_stayed", "vehicle_dwelling"],
                "need_precondition_confirmation": ["need_confirmation", "ready_for_main_registration"],
                "registration_status": ["new", "already_registered", "not_eligible"],
            },
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
                            "You classify Vietnamese public-service intake messages. "
                            "Return JSON only. Choose one domain from birth_registration, residence_management, or unknown. "
                            "Only fill slot_updates when strongly supported by the message. "
                            "Return: domain_key, confidence, slot_updates, short_rationale."
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
            "domain_key": parsed.get("domain_key"),
            "confidence": parsed.get("confidence"),
            "slot_updates": parsed.get("slot_updates") or {},
            "short_rationale": parsed.get("short_rationale") or "",
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
