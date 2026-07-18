from typing import Any

from govease_ai.intent_parser import LLMIntentParser
from .intake_disambiguation import IntakeDisambiguator
from .workflow_intake import WorkflowIntakeService

class CentralRouter:
    """
    Core router that receives intake, runs disambiguation, and either:
    - Routes to Workflow Engine (if workflow exists for the domain)
    - Fallbacks to Catalog/Procedure Picker (if no workflow)
    - Rejects or asks for clarification (if disambiguation requires it)
    """

    def __init__(self, workflow_service: WorkflowIntakeService, intent_parser: LLMIntentParser):
        self.workflow_service = workflow_service
        self.disambiguator = IntakeDisambiguator(intent_parser)
        
        # In a real scenario, this is dynamically loaded from data/workflows/
        self.supported_workflow_domains = ["phuong_tien_nguoi_lai", "birth_registration", "residence_management"]

    def process(self, session_id: str, message: str, current_session_state: dict[str, Any] | None = None) -> dict[str, Any]:
        
        # 1. Disambiguate
        disambiguation_result = self.disambiguator.process_intake(message, current_session_state)
        
        # 2. Check if clarification is needed early
        if disambiguation_result.needs_clarification:
            return {
                "status": "needs_clarification",
                "question": disambiguation_result.clarifying_question,
                "reason": disambiguation_result.blocked_reason,
                "quick_replies": []
            }
            
        if disambiguation_result.blocked_reason == "out_of_scope":
            return {
                "status": "out_of_scope",
                "question": "Xin lỗi, yêu cầu của bạn nằm ngoài phạm vi hỗ trợ của hệ thống Dịch vụ công.",
                "quick_replies": []
            }
            
        domain = disambiguation_result.domain
        
        # 3. Route to Workflow if supported
        if domain in self.supported_workflow_domains:
            # Pass to workflow engine
            return self.workflow_service.handle(
                message=message, 
                session_id=session_id, 
                preferred_domain_key=domain
            )
            
        # 4. Fallback Route
        return {
            "status": "fallback_catalog",
            "domain": domain,
            "subdomain": disambiguation_result.subdomain,
            "message": f"Chủ đề '{domain}' hiện chưa hỗ trợ hỏi đáp chi tiết. Hệ thống sẽ chuyển bạn tới danh mục thủ tục cơ bản."
        }
