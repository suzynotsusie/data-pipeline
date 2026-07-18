from typing import Any

from govease_ai.intent_parser import LLMIntentParser

class IntakeDisambiguationResult:
    def __init__(
        self,
        domain: str | None,
        subdomain: str | None,
        intent: str | None,
        slot_updates: dict[str, Any],
        needs_clarification: bool,
        clarifying_question: str | None,
        blocked_reason: str | None,
    ):
        self.domain = domain
        self.subdomain = subdomain
        self.intent = intent
        self.slot_updates = slot_updates
        self.needs_clarification = needs_clarification
        self.clarifying_question = clarifying_question
        self.blocked_reason = blocked_reason

    def to_dict(self):
        return {
            "domain": self.domain,
            "subdomain": self.subdomain,
            "intent": self.intent,
            "slot_updates": self.slot_updates,
            "needs_clarification": self.needs_clarification,
            "clarifying_question": self.clarifying_question,
            "blocked_reason": self.blocked_reason,
        }

class IntakeDisambiguator:
    """
    Decides the next action based on AI intent parser results and rules.
    If ambiguous -> ask clarification.
    If out of scope -> block.
    If clear -> route to workflow engine.
    """

    def __init__(self, parser: LLMIntentParser):
        self.parser = parser
        # Define minimum confidence threshold
        self.confidence_threshold = 0.6

    def process_intake(
        self, user_message: str, current_session_state: dict[str, Any] | None = None
    ) -> IntakeDisambiguationResult:
        
        current_session_state = current_session_state or {}
        context_slots = current_session_state.get("slots", {})

        # 1. Run AI Parser
        parse_result = self.parser.parse(user_message, context_slots=context_slots)

        if not parse_result:
            return IntakeDisambiguationResult(
                domain=None,
                subdomain=None,
                intent=None,
                slot_updates={},
                needs_clarification=True,
                clarifying_question="Hệ thống đang bận hoặc không hiểu yêu cầu của bạn, xin vui lòng nói rõ hơn.",
                blocked_reason="parser_failed"
            )

        # 2. Check Out of Scope
        if parse_result.get("out_of_scope"):
            return IntakeDisambiguationResult(
                domain=None,
                subdomain=None,
                intent=None,
                slot_updates={},
                needs_clarification=False,
                clarifying_question=None,
                blocked_reason="out_of_scope"
            )

        # 3. Check Confidence
        confidence = parse_result.get("confidence", 0.0)
        domain = parse_result.get("domain")
        
        if confidence < self.confidence_threshold or not domain:
            return IntakeDisambiguationResult(
                domain=domain,
                subdomain=parse_result.get("subdomain"),
                intent=parse_result.get("intent"),
                slot_updates=parse_result.get("slot_updates", {}),
                needs_clarification=True,
                clarifying_question="Bạn có thể mô tả cụ thể hơn loại thủ tục bạn muốn làm không?",
                blocked_reason="low_confidence"
            )

        # 4. Check Ambiguity and Prerequisites
        ambiguity_flags = parse_result.get("ambiguity_flags", [])
        missing_prerequisites = parse_result.get("missing_prerequisites", [])

        if ambiguity_flags or missing_prerequisites:
            candidate_question = parse_result.get("clarifying_question_candidate")
            if not candidate_question:
                candidate_question = "Để hỗ trợ chính xác nhất, bạn có thể cung cấp thêm thông tin về tình trạng hồ sơ hiện tại không?"
            
            return IntakeDisambiguationResult(
                domain=domain,
                subdomain=parse_result.get("subdomain"),
                intent=parse_result.get("intent"),
                slot_updates=parse_result.get("slot_updates", {}),
                needs_clarification=True,
                clarifying_question=candidate_question,
                blocked_reason="ambiguous_or_missing_prerequisite"
            )

        # 5. Clear Route
        return IntakeDisambiguationResult(
            domain=domain,
            subdomain=parse_result.get("subdomain"),
            intent=parse_result.get("intent"),
            slot_updates=parse_result.get("slot_updates", {}),
            needs_clarification=False,
            clarifying_question=None,
            blocked_reason=None
        )
