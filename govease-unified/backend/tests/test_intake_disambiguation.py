import pytest
from backend.app.services.intake_disambiguation import IntakeDisambiguator
from govease_ai.intent_parser import LLMIntentParser

class MockParser:
    def __init__(self, response):
        self.response = response

    def parse(self, user_message, context_slots=None):
        return self.response

def test_disambiguator_missing_prerequisites():
    mock_parser = MockParser({
        "domain": "phuong_tien_nguoi_lai",
        "subdomain": "giay_phep_lai_xe",
        "intent": "doi_giay_phep",
        "slot_updates": {},
        "ambiguity_flags": [],
        "missing_prerequisites": ["license_type"],
        "clarifying_question_candidate": "Bạn muốn đổi bằng lái ô tô hay xe máy?",
        "confidence": 0.85,
        "out_of_scope": False
    })
    
    disambiguator = IntakeDisambiguator(parser=mock_parser)
    result = disambiguator.process_intake("Tôi muốn đổi bằng lái")
    
    assert result.needs_clarification is True
    assert result.clarifying_question == "Bạn muốn đổi bằng lái ô tô hay xe máy?"
    assert result.blocked_reason == "ambiguous_or_missing_prerequisite"
    assert result.domain == "phuong_tien_nguoi_lai"

def test_disambiguator_out_of_scope():
    mock_parser = MockParser({
        "domain": None,
        "subdomain": None,
        "intent": None,
        "slot_updates": {},
        "ambiguity_flags": [],
        "missing_prerequisites": [],
        "clarifying_question_candidate": None,
        "confidence": 0.9,
        "out_of_scope": True
    })
    
    disambiguator = IntakeDisambiguator(parser=mock_parser)
    result = disambiguator.process_intake("Tôi muốn mua bảo hiểm cho xe máy")
    
    assert result.needs_clarification is False
    assert result.blocked_reason == "out_of_scope"

def test_disambiguator_clear_route():
    mock_parser = MockParser({
        "domain": "phuong_tien_nguoi_lai",
        "subdomain": "giay_phep_lai_xe",
        "intent": "doi_giay_phep",
        "slot_updates": {"license_type": "oto"},
        "ambiguity_flags": [],
        "missing_prerequisites": [],
        "clarifying_question_candidate": None,
        "confidence": 0.95,
        "out_of_scope": False
    })
    
    disambiguator = IntakeDisambiguator(parser=mock_parser)
    result = disambiguator.process_intake("Tôi muốn đổi bằng lái ô tô")
    
    assert result.needs_clarification is False
    assert result.blocked_reason is None
    assert result.domain == "phuong_tien_nguoi_lai"
    assert result.slot_updates == {"license_type": "oto"}
