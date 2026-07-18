from __future__ import annotations

import csv
import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel, Field


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
STATIC_DIR = BASE_DIR / "static"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower().strip())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return text.replace("đ", "d")


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


@dataclass
class ProcedureRecord:
    code: str
    title: str
    agency: str
    submit_to: str
    summary: str
    source_url: str


@dataclass
class DomainBundle:
    key: str
    label: str
    config: dict[str, Any]
    procedures: dict[str, ProcedureRecord]
    node_map: dict[str, dict[str, Any]] = field(default_factory=dict)

    def route_candidates(self, slots: dict[str, Any]) -> list[dict[str, Any]]:
        slots = _normalize_residence_slots(slots) if self.key == "residence_management" else dict(slots)
        candidates: list[dict[str, Any]] = []
        for route in self.config["decision_tree"]["routes"]:
            compatible = True
            for key, value in route["conditions"].items():
                current = slots.get(key)
                if current in (None, "", "unknown"):
                    continue
                if current != value:
                    compatible = False
                    break
            if compatible:
                candidates.append(route)
        return candidates

    def exact_match(self, slots: dict[str, Any]) -> dict[str, Any] | None:
        slots = _normalize_residence_slots(slots) if self.key == "residence_management" else dict(slots)
        for route in self.route_candidates(slots):
            if all(slots.get(key) == value for key, value in route["conditions"].items()):
                return route
        return None


OPTION_LABELS = {
    "new_registration": "Khai sinh mới",
    "re_registration": "Đăng ký lại",
    "copy_extract": "Xin bản sao hoặc trích lục",
    "foreign_record_note": "Ghi vào sổ việc đã làm ở nước ngoài",
    "existing_personal_documents": "Đã có hồ sơ cá nhân nhưng chưa có khai sinh hợp lệ",
    "mobile_service": "Diện lưu động",
    "domestic": "Trong nước",
    "abroad": "Ở nước ngoài",
    "yes": "Có",
    "no": "Không",
    "none": "Không liên thông",
    "bhyt_only": "Liên thông bảo hiểm y tế",
    "bhyt_and_residence": "Liên thông BHYT và thường trú",
    "standard": "Thông thường",
    "mobile": "Lưu động",
    "border_area": "Khu vực biên giới",
    "consular": "Cơ quan đại diện",
    "birth_only": "Chỉ việc khai sinh",
    "multi_civil_status": "Nhóm hộ tịch khác",
    "register_permanent": "Đăng ký thường trú",
    "register_temporary": "Đăng ký tạm trú",
    "extend_temporary": "Gia hạn tạm trú",
    "delete_temporary": "Xóa tạm trú",
    "delete_permanent": "Xóa thường trú",
    "split_household": "Tách hộ",
    "adjust_data": "Điều chỉnh dữ liệu cư trú",
    "absence_notice": "Khai báo tạm vắng",
    "lodging_notice": "Thông báo lưu trú",
    "residence_confirmation": "Xác nhận thông tin cư trú",
    "eligibility_confirmation": "Xác nhận điều kiện",
    "fallback_info_declaration": "Khai báo thông tin cư trú khi chưa đủ điều kiện",
    "owned_home": "Nhà thuộc sở hữu của mình",
    "rented_borrowed_stayed": "Nhà thuê, mượn hoặc ở nhờ",
    "vehicle_dwelling": "Phương tiện dùng để ở",
    "need_confirmation": "Cần xin xác nhận trước",
    "ready_for_main_registration": "Đã sẵn sàng nộp hồ sơ chính",
    "new": "Đăng ký mới",
    "already_registered": "Đã đăng ký rồi",
    "not_eligible": "Chưa đủ điều kiện",
}

OPTION_DESCRIPTIONS = {
    "new_registration": "Làm giấy khai sinh lần đầu cho trẻ.",
    "re_registration": "Làm lại giấy khai sinh khi đã mất hoặc thiếu bản chính hợp lệ.",
    "copy_extract": "Xin bản sao giấy khai sinh hoặc trích lục hộ tịch.",
    "foreign_record_note": "Ghi nhận vào sổ hộ tịch ở Việt Nam việc đã làm tại nước ngoài.",
    "existing_personal_documents": "Người đã có giấy tờ cá nhân nhưng chưa có khai sinh đúng chuẩn.",
    "mobile_service": "Trường hợp làm theo diện lưu động, không phải nộp theo cách thông thường.",
    "domestic": "Trẻ sinh tại Việt Nam.",
    "abroad": "Trẻ sinh ở nước ngoài.",
    "yes": "Đúng với trường hợp của bạn.",
    "no": "Không phải trường hợp của bạn.",
    "none": "Chỉ làm khai sinh, chưa làm thêm thủ tục liên thông.",
    "bhyt_only": "Làm thêm thẻ bảo hiểm y tế cho trẻ.",
    "bhyt_and_residence": "Làm thêm bảo hiểm y tế và đăng ký thường trú cho trẻ.",
    "standard": "Làm theo quy trình thông thường tại cơ quan có thẩm quyền.",
    "mobile": "Làm theo diện lưu động.",
    "border_area": "Trường hợp thuộc khu vực biên giới.",
    "consular": "Làm qua cơ quan đại diện Việt Nam ở nước ngoài.",
    "birth_only": "Chỉ liên quan đến việc khai sinh.",
    "multi_civil_status": "Liên quan thêm tới việc hộ tịch khác ngoài khai sinh.",
    "register_permanent": "Đăng ký ở ổn định lâu dài tại nơi ở mới.",
    "register_temporary": "Đăng ký ở tạm tại nơi bạn đang ở hiện tại.",
    "extend_temporary": "Gia hạn thời gian tạm trú đã đăng ký trước đó.",
    "delete_temporary": "Xóa đăng ký tạm trú khi bạn không còn ở đó nữa.",
    "delete_permanent": "Xóa đăng ký thường trú tại địa chỉ cũ.",
    "split_household": "Tách khỏi hộ hiện tại để thành hộ riêng.",
    "adjust_data": "Sửa thông tin cư trú đang bị sai hoặc cần cập nhật.",
    "absence_notice": "Báo với cơ quan rằng bạn sẽ vắng mặt khỏi nơi ở một thời gian.",
    "lodging_notice": "Thông báo có người đến ở ngắn hạn tại chỗ ở đó.",
    "residence_confirmation": "Xin giấy xác nhận thông tin cư trú hiện có của bạn.",
    "eligibility_confirmation": "Xin giấy xác nhận điều kiện nhà ở trước khi đăng ký cư trú.",
    "fallback_info_declaration": "Khai báo nơi ở hiện tại khi bạn chưa đủ điều kiện đăng ký cư trú chính thức.",
    "owned_home": "Nhà thuộc sở hữu của bạn hoặc gia đình bạn.",
    "rented_borrowed_stayed": "Nhà thuê, mượn hoặc ở nhờ người khác.",
    "vehicle_dwelling": "Phương tiện như tàu, thuyền, xe... được dùng để ở.",
    "need_confirmation": "Bạn cần xin giấy xác nhận trước rồi mới làm thủ tục chính.",
    "ready_for_main_registration": "Bạn muốn vào luôn thủ tục đăng ký chính.",
    "new": "Trường hợp đăng ký mới.",
    "already_registered": "Thông tin này đã từng được đăng ký trước đó.",
    "not_eligible": "Hiện tại bạn chưa đủ điều kiện để đăng ký chính thức.",
}

YES_NO_OPTIONS = [
    {"value": "yes", "label": "Đúng rồi", "description": "Đúng với trường hợp của tôi."},
    {"value": "no", "label": "Không phải", "description": "Không đúng với trường hợp của tôi."},
]

ASSIST_MODES = {
    "guided": {
        "label": "Dẫn từng bước",
        "description": "Phù hợp khi bạn chưa chắc mình cần thủ tục nào.",
    },
    "fast_track": {
        "label": "Đi nhanh",
        "description": "Phù hợp khi bạn đã biết gần đúng thủ tục và muốn rút ngắn câu hỏi.",
    },
}

PERSONA_LABELS = {
    "elderly_confused": "Người dùng lớn tuổi, cần giải thích kỹ",
    "first_time_unclear": "Người dùng lần đầu, chưa rõ thủ tục",
    "semi_clear": "Người dùng biết đại khái, còn thiếu vài ý",
    "knows_procedure": "Người dùng biết khá rõ thủ tục",
    "compliance_careful": "Người dùng cẩn thận, muốn đi chắc từng bước",
}

SYNTHETIC_FLOWS: dict[str, dict[str, dict[str, Any]]] = {
    "birth_registration": {
        "birth_binary_new": {
            "question": "Bạn đang làm giấy khai sinh lần đầu cho trẻ phải không?",
            "yes": {"set": {"request_type": "new_registration"}},
            "no": {"next": "birth_binary_copy"},
        },
        "birth_binary_copy": {
            "question": "Bạn đang xin bản sao hoặc trích lục giấy khai sinh phải không?",
            "yes": {"set": {"request_type": "copy_extract"}},
            "no": {"next": "birth_binary_reregister"},
        },
        "birth_binary_reregister": {
            "question": "Bạn đang làm lại khai sinh vì đã mất hoặc thiếu bản chính hợp lệ?",
            "yes": {"set": {"request_type": "re_registration"}},
            "no": {"next": "birth_binary_existing_docs"},
        },
        "birth_binary_existing_docs": {
            "question": "Người cần làm thủ tục đã có giấy tờ cá nhân nhưng chưa có khai sinh hợp lệ?",
            "yes": {"set": {"request_type": "existing_personal_documents"}},
            "no": {"next": "birth_binary_foreign_note"},
        },
        "birth_binary_foreign_note": {
            "question": "Bạn đang ghi nhận vào sổ hộ tịch ở Việt Nam một việc khai sinh đã làm ở nước ngoài?",
            "yes": {"set": {"request_type": "foreign_record_note"}},
            "no": {"next": "birth_binary_mobile"},
        },
        "birth_binary_mobile": {
            "question": "Đây có phải trường hợp làm theo diện lưu động không?",
            "yes": {"set": {"request_type": "mobile_service"}},
            "no": {"next": "birth_request_type"},
        },
    },
    "residence_management": {
        "res_binary_register": {
            "question": "Bạn đang muốn đăng ký nơi ở mới hoặc gia hạn nơi ở hiện tại phải không?",
            "yes": {"next": "res_binary_long_term"},
            "no": {"next": "res_binary_remove"},
        },
        "res_binary_long_term": {
            "question": "Bạn muốn đăng ký ở ổn định lâu dài tại địa chỉ đó?",
            "yes": {"set": {"residence_goal": "register_permanent"}},
            "no": {"next": "res_binary_extend"},
        },
        "res_binary_extend": {
            "question": "Bạn đã có tạm trú ở đó rồi và giờ chỉ muốn gia hạn thêm thời gian?",
            "yes": {"set": {"residence_goal": "extend_temporary"}},
            "no": {"set": {"residence_goal": "register_temporary"}},
        },
        "res_binary_remove": {
            "question": "Bạn đang muốn xóa một đăng ký cư trú cũ?",
            "yes": {"next": "res_binary_remove_type"},
            "no": {"next": "res_binary_split"},
        },
        "res_binary_remove_type": {
            "question": "Đó là xóa đăng ký thường trú phải không?",
            "yes": {"set": {"residence_goal": "delete_permanent"}},
            "no": {"set": {"residence_goal": "delete_temporary"}},
        },
        "res_binary_split": {
            "question": "Bạn muốn tách khỏi hộ hiện tại để thành hộ riêng?",
            "yes": {"set": {"residence_goal": "split_household"}},
            "no": {"next": "res_binary_adjust"},
        },
        "res_binary_adjust": {
            "question": "Bạn đang muốn sửa thông tin cư trú đang bị sai hoặc cần cập nhật?",
            "yes": {"set": {"residence_goal": "adjust_data"}},
            "no": {"next": "res_binary_absence"},
        },
        "res_binary_absence": {
            "question": "Bạn sắp vắng khỏi nơi ở hiện tại trong một thời gian và cần khai báo?",
            "yes": {"set": {"residence_goal": "absence_notice"}},
            "no": {"next": "res_binary_lodging"},
        },
        "res_binary_lodging": {
            "question": "Bạn cần báo có người đến ở ngắn hạn tại chỗ ở đó?",
            "yes": {"set": {"residence_goal": "lodging_notice"}},
            "no": {"next": "res_binary_confirmation"},
        },
        "res_binary_confirmation": {
            "question": "Bạn đang cần một giấy xác nhận liên quan đến cư trú?",
            "yes": {"next": "res_binary_confirmation_type"},
            "no": {"next": "res_binary_not_eligible"},
        },
        "res_binary_confirmation_type": {
            "question": "Bạn cần xác nhận thông tin cư trú hiện có của mình?",
            "yes": {"set": {"residence_goal": "residence_confirmation"}},
            "no": {"set": {"residence_goal": "eligibility_confirmation"}},
        },
        "res_binary_not_eligible": {
            "question": "Bạn chưa đủ điều kiện đăng ký cư trú chính thức nhưng vẫn muốn khai báo nơi ở hiện tại?",
            "yes": {"set": {"residence_goal": "fallback_info_declaration"}},
            "no": {"next": "residence_goal"},
        },
    },
}


def _load_birth_procedures() -> dict[str, ProcedureRecord]:
    rows = _read_csv(DATA_DIR / "birth_procedure" / "birth_procedures_summary.csv")
    procedures: dict[str, ProcedureRecord] = {}
    for row in rows:
        code = row["ma_thu_tuc"]
        procedures[code] = ProcedureRecord(
            code=code,
            title=row["ten_thu_tuc"],
            agency=row["co_quan_thuc_hien"],
            submit_to=row["noi_nop"],
            summary=row["7_truong_tien_kiem"],
            source_url=row["link_nguon"],
        )
    return procedures


def _load_residence_procedures() -> dict[str, ProcedureRecord]:
    rows = _read_csv(DATA_DIR / "residence_procedures" / "residence_procedures_summary.csv")
    procedures: dict[str, ProcedureRecord] = {}
    for row in rows:
        code = row["Mã số"]
        procedures[code] = ProcedureRecord(
            code=code,
            title=row["Tên"],
            agency=row["Cơ quan thực hiện"],
            submit_to=row["Loại thủ tục"],
            summary=f"Lĩnh vực: {row['Lĩnh vực']}. Ưu tiên: {row['Ưu tiên']}.",
            source_url=row["URL"],
        )
    return procedures


DOMAINS: dict[str, DomainBundle] = {
    "birth_registration": DomainBundle(
        key="birth_registration",
        label="Khai sinh",
        config=_read_json(DATA_DIR / "birth_procedure" / "workflow_engine_config.json"),
        procedures=_load_birth_procedures(),
    ),
    "residence_management": DomainBundle(
        key="residence_management",
        label="Cư trú",
        config=_read_json(DATA_DIR / "residence_procedures" / "workflow_engine_config.json"),
        procedures=_load_residence_procedures(),
    ),
}

for domain in DOMAINS.values():
    domain.node_map = {node["id"]: node for node in domain.config["decision_tree"]["nodes"]}


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)
    preferred_mode: str | None = None
    group_key: str | None = None
    subdomain_key: str | None = None


class SessionState(BaseModel):
    session_id: str
    domain_key: str | None = None
    current_node_id: str | None = None
    asked_node_ids: list[str] = Field(default_factory=list)
    slots: dict[str, Any] = Field(default_factory=dict)
    messages: list[dict[str, str]] = Field(default_factory=list)
    completed_route_id: str | None = None
    assist_mode: str | None = None
    user_mode: str | None = None
    persona_key: str | None = None


SESSIONS: dict[str, SessionState] = {}


class WorkflowLLM:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def detect_domain(self, user_message: str) -> tuple[str | None, str]:
        if user_message in DOMAINS:
            return user_message, ""
        if self.client:
            try:
                parsed = self._call_llm(
                    system_message=(
                        "You classify the user's Vietnamese administrative intent. "
                        "Return JSON only with keys domain_key, confidence, reasoning_short. "
                        "Allowed domain_key values: birth_registration, residence_management, unknown."
                    ),
                    user_payload={
                        "message": user_message,
                        "hints": {
                            "birth_registration": "khai sinh, giấy khai sinh, sinh con, trẻ em, bảo hiểm y tế cho trẻ dưới 6 tuổi",
                            "residence_management": "thường trú, tạm trú, tạm vắng, lưu trú, cư trú, hộ khẩu",
                        },
                    },
                )
                key = parsed.get("domain_key")
                if key in DOMAINS:
                    return key, ""
            except Exception:
                pass

        text = _normalize(user_message)
        if _contains_any(text, ["khai sinh", "giay khai sinh", "sinh con", "be sinh", "trich luc khai sinh"]):
            return "birth_registration", ""
        if _contains_any(text, ["tam tru", "thuong tru", "tam vang", "luu tru", "cu tru", "ho khau", "o thue", "o nho", "chuyen cho o", "giay xac nhan noi o"]):
            return "residence_management", ""
        return None, "Mình đang hỗ trợ 2 nhóm chính là khai sinh và cư trú. Bạn muốn bắt đầu với nhóm nào?"

    def analyze_entry(self, user_message: str) -> dict[str, Any]:
        if user_message in DOMAINS:
            return {
                "domain_key": user_message,
                "user_mode": "needs_guidance",
                "persona_key": "first_time_unclear",
                "assist_mode": "guided",
                "confidence": 1.0,
                "slot_updates": {},
                "reasoning_short": "User chose a domain directly.",
            }

        if self.client:
            try:
                parsed = self._call_llm(
                    system_message=(
                        "You analyze the first user turn for a Vietnamese public-service workflow assistant. "
                        "Return strict JSON only with keys: domain_key, user_mode, persona_key, assist_mode, confidence, slot_updates, reasoning_short. "
                        "user_mode must be one of knows_procedure, partially_clear, needs_guidance, or needs_reassurance. "
                        "assist_mode must be one of fast_track or guided. "
                        "domain_key must be birth_registration, residence_management, or unknown. "
                        "If the user clearly names a known procedure or a very specific request, use knows_procedure. "
                        "If the user is still describing a life situation and needs help navigating, use needs_guidance."
                    ),
                    user_payload={
                        "message": user_message,
                        "supported_domains": list(DOMAINS.keys()),
                        "allowed_birth_slots": [
                            "request_type",
                            "birth_location",
                            "has_foreign_element",
                            "combined_parent_recognition",
                            "wants_linked_bundle",
                            "service_channel",
                            "request_type_detail",
                        ],
                        "allowed_residence_slots": [
                            "residence_goal",
                            "residence_place_type",
                            "need_precondition_confirmation",
                            "registration_status",
                        ],
                    },
                )
                if parsed.get("domain_key") in DOMAINS:
                    parsed.setdefault("slot_updates", {})
                    parsed.setdefault("assist_mode", "guided")
                    parsed.setdefault("persona_key", "first_time_unclear")
                    return parsed
            except Exception:
                pass

        return _heuristic_entry_analysis(user_message)

    def parse_answer(self, domain: DomainBundle, session: SessionState, user_message: str) -> dict[str, Any]:
        node = domain.node_map.get(session.current_node_id or "")
        if self.client and node:
            try:
                parsed = self._call_llm(
                    system_message=(
                        "You are a workflow parser for a Vietnamese public-service assistant. "
                        "Return strict JSON only with keys: slot_updates, confidence, needs_clarification, clarification_hint. "
                        "slot_updates must be an object. You may fill multiple slots if the user answered them naturally."
                    ),
                    user_payload={
                        "domain": domain.key,
                        "domain_label": domain.label,
                        "current_question": node["question"],
                        "expected_slot": node["slot"],
                        "allowed_values": node.get("options", []),
                        "current_slots": session.slots,
                        "user_message": user_message,
                    },
                )
                if isinstance(parsed.get("slot_updates"), dict):
                    return parsed
            except Exception:
                pass

        return _heuristic_parse(domain.key, user_message, node["slot"] if node else None)

    def _call_llm(self, system_message: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        assert self.client is not None
        response = self.client.responses.create(
            model=self.model,
            instructions=system_message,
            input=json.dumps(user_payload, ensure_ascii=False),
        )
        text = response.output_text.strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("LLM did not return JSON")
        return json.loads(match.group(0))


LLM = WorkflowLLM()


def _heuristic_parse(domain_key: str, user_message: str, expected_slot: str | None = None) -> dict[str, Any]:
    text = _normalize(user_message)
    updates: dict[str, Any] = {}

    direct_slot_map = {
        "request_type": {
            "new_registration": "new_registration",
            "re_registration": "re_registration",
            "copy_extract": "copy_extract",
            "foreign_record_note": "foreign_record_note",
            "existing_personal_documents": "existing_personal_documents",
            "mobile_service": "mobile_service",
        },
        "birth_location": {"domestic": "domestic", "abroad": "abroad"},
        "has_foreign_element": {"yes": "yes", "no": "no"},
        "combined_parent_recognition": {"yes": "yes", "no": "no"},
        "wants_linked_bundle": {
            "none": "none",
            "bhyt_only": "bhyt_only",
            "bhyt_and_residence": "bhyt_and_residence",
        },
        "service_channel": {
            "standard": "standard",
            "mobile": "mobile",
            "border_area": "border_area",
            "consular": "consular",
        },
        "request_type_detail": {"birth_only": "birth_only", "multi_civil_status": "multi_civil_status"},
        "residence_goal": {
            "register_permanent": "register_permanent",
            "register_temporary": "register_temporary",
            "extend_temporary": "extend_temporary",
            "delete_temporary": "delete_temporary",
            "delete_permanent": "delete_permanent",
            "split_household": "split_household",
            "adjust_data": "adjust_data",
            "absence_notice": "absence_notice",
            "lodging_notice": "lodging_notice",
            "residence_confirmation": "residence_confirmation",
            "eligibility_confirmation": "eligibility_confirmation",
            "fallback_info_declaration": "fallback_info_declaration",
        },
        "residence_place_type": {
            "owned_home": "owned_home",
            "rented_borrowed_stayed": "rented_borrowed_stayed",
            "vehicle_dwelling": "vehicle_dwelling",
        },
        "need_precondition_confirmation": {
            "need_confirmation": "need_confirmation",
            "ready_for_main_registration": "ready_for_main_registration",
        },
        "registration_status": {"new": "new", "already_registered": "already_registered", "not_eligible": "not_eligible"},
    }

    if expected_slot and text in direct_slot_map.get(expected_slot, {}):
        updates[expected_slot] = direct_slot_map[expected_slot][text]
        return {
            "slot_updates": updates,
            "confidence": 0.99,
            "needs_clarification": False,
            "clarification_hint": "",
        }

    if expected_slot in {"has_foreign_element", "combined_parent_recognition"} and text in {"yes", "no"}:
        updates[expected_slot] = text
        return {
            "slot_updates": updates,
            "confidence": 0.99,
            "needs_clarification": False,
            "clarification_hint": "",
        }

    if domain_key == "birth_registration":
        if text in {
            "new_registration",
            "re_registration",
            "copy_extract",
            "foreign_record_note",
            "existing_personal_documents",
            "mobile_service",
        }:
            updates["request_type"] = text
        if text in {"domestic", "abroad"}:
            updates["birth_location"] = text
        if text in {"yes", "no"} and expected_slot in {"has_foreign_element", "combined_parent_recognition"}:
            updates[expected_slot] = text
        if text in {"none", "bhyt_only", "bhyt_and_residence"}:
            updates["wants_linked_bundle"] = text
        if text in {"standard", "mobile", "border_area", "consular"}:
            updates["service_channel"] = text
        if text in {"birth_only", "multi_civil_status"}:
            updates["request_type_detail"] = text

        if _contains_any(text, ["dang ky lai", "mat ban chinh", "mat giay khai sinh", "lam lai khai sinh"]):
            updates["request_type"] = "re_registration"
        elif _contains_any(text, ["trich luc", "ban sao giay khai sinh", "xin ban sao"]):
            updates["request_type"] = "copy_extract"
        elif "nuoc ngoai" in text and _contains_any(text, ["ghi vao so", "ghi so ho tich"]):
            updates["request_type"] = "foreign_record_note"
        elif _contains_any(text, ["da co ho so", "da co giay to ca nhan"]):
            updates["request_type"] = "existing_personal_documents"
        elif "luu dong" in text:
            updates["request_type"] = "mobile_service"
        elif _contains_any(text, ["khai sinh moi", "lam khai sinh", "sinh con", "giay khai sinh cho con", "khai sinh cho be"]):
            updates["request_type"] = "new_registration"

        if _contains_any(
            text,
            [
                "sinh o nuoc ngoai",
                "sinh ben nhat",
                "sinh ben han",
                "sinh ben my",
                "sinh ben duc",
                "tai nuoc ngoai",
                "de o nuoc ngoai",
                "sinh o overseas",
            ],
        ):
            updates["birth_location"] = "abroad"
        elif _contains_any(text, ["trong nuoc", "sinh o viet nam", "benh vien", "sinh trong nuoc"]):
            updates["birth_location"] = "domestic"

        if _contains_any(
            text,
            [
                "khong co yeu to nuoc ngoai",
                "khong yeu to nuoc ngoai",
                "chi nguoi viet",
                "khong co nguoi nuoc ngoai",
                "bo me deu la nguoi viet",
                "ca bo me deu la nguoi viet",
            ],
        ):
            updates["has_foreign_element"] = "no"
        elif _contains_any(
            text,
            [
                "co yeu to nuoc ngoai",
                "yeu to nuoc ngoai",
                "nguoi nuoc ngoai",
                "quoc tich nuoc ngoai",
                "bo la nguoi",
                "me la nguoi",
                "bo nguoi",
                "me nguoi",
                "cha la nguoi",
                "me mang quoc tich",
                "bo mang quoc tich",
                "cha mang quoc tich",
                "quoc tich han",
                "quoc tich nhat",
                "quoc tich my",
                "quoc tich uc",
                "quoc tich duc",
                "quoc tich phap",
            ],
        ):
            updates["has_foreign_element"] = "yes"

        if _contains_any(
            text,
            [
                "khong can nhan cha",
                "khong can nhan me",
                "khong nhan cha me con",
                "khong lam nhan cha me con",
                "khong ket hop nhan cha me con",
                "chi khai sinh",
            ],
        ):
            updates["combined_parent_recognition"] = "no"
        elif _contains_any(
            text,
            [
                "nhan cha",
                "nhan me",
                "nhan cha me con",
                "ket hop nhan cha",
                "ket hop nhan me",
                "ket hop nhan cha me con",
            ],
        ):
            updates["combined_parent_recognition"] = "yes"

        if "bao hiem" in text and "thuong tru" in text:
            updates["wants_linked_bundle"] = "bhyt_and_residence"
        elif _contains_any(text, ["khong lien thong", "chi khai sinh thoi", "khong can bao hiem", "chi lam khai sinh thoi"]):
            updates["wants_linked_bundle"] = "none"
        elif _contains_any(text, ["bao hiem", "bhyt"]):
            updates["wants_linked_bundle"] = "bhyt_only"

        if "bien gioi" in text:
            updates["service_channel"] = "border_area"
        elif _contains_any(text, ["co quan dai dien", "lanh su", "dai su quan"]):
            updates["service_channel"] = "consular"
        elif "luu dong" in text:
            updates["service_channel"] = "mobile"
        elif _contains_any(text, ["thong thuong", "binh thuong", "ubnd xa"]):
            updates["service_channel"] = "standard"

        if _contains_any(text, ["ho tich khac", "giam ho", "nuoi con nuoi", "nhan cha me con o nuoc ngoai"]):
            updates["request_type_detail"] = "multi_civil_status"
        elif _contains_any(text, ["khai sinh", "giay khai sinh"]):
            updates["request_type_detail"] = "birth_only"

    if domain_key == "residence_management":
        if text in direct_slot_map["residence_goal"]:
            updates["residence_goal"] = text
        if text in direct_slot_map["residence_place_type"]:
            updates["residence_place_type"] = text
        if text in direct_slot_map["need_precondition_confirmation"]:
            updates["need_precondition_confirmation"] = text
        if text in direct_slot_map["registration_status"]:
            updates["registration_status"] = text

        mapping = {
            "register_permanent": ["dang ky thuong tru", "thuong tru", "nhap ho khau", "o lau dai"],
            "register_temporary": ["dang ky tam tru", "tam tru", "o tam"],
            "extend_temporary": ["gia han tam tru", "gia han tam"],
            "delete_temporary": ["xoa tam tru"],
            "delete_permanent": ["xoa thuong tru"],
            "split_household": ["tach ho"],
            "adjust_data": ["dieu chinh thong tin", "sua thong tin cu tru", "cap nhat thong tin cu tru"],
            "absence_notice": ["tam vang", "khai bao tam vang"],
            "lodging_notice": ["luu tru", "thong bao luu tru"],
            "residence_confirmation": ["xac nhan thong tin cu tru", "xin xac nhan cu tru", "giay xac nhan cu tru"],
            "eligibility_confirmation": ["xac nhan dieu kien", "dien tich binh quan", "nha o khong tranh chap"],
            "fallback_info_declaration": ["chua du dieu kien", "khai bao thong tin cu tru"],
        }
        for key, phrases in mapping.items():
            if _contains_any(text, phrases):
                updates["residence_goal"] = key
                break

        if _contains_any(text, ["thue nha", "nha thue", "o nho", "muon nha", "o muon", "cho o thue", "dang o thue"]):
            updates["residence_place_type"] = "rented_borrowed_stayed"
        elif _contains_any(text, ["phuong tien", "xe de o", "song tren xe", "tau thuyen de o"]):
            updates["residence_place_type"] = "vehicle_dwelling"
        elif _contains_any(text, ["nha cua toi", "nha minh", "so huu", "nha cua gia dinh", "co so do"]):
            updates["residence_place_type"] = "owned_home"

        if _contains_any(
            text,
            [
                "xin xac nhan truoc",
                "can xac nhan",
                "dieu kien nha o",
                "giay xac nhan dieu kien",
                "xac nhan dieu kien truoc",
                "chua du dieu kien dang ky ngay",
            ],
        ):
            updates["need_precondition_confirmation"] = "need_confirmation"
        elif _contains_any(text, ["nop ho so", "dang ky luon", "san sang nop", "du dieu kien roi", "vao dang ky chinh"]):
            updates["need_precondition_confirmation"] = "ready_for_main_registration"

        if "chua du dieu kien" in text:
            updates["registration_status"] = "not_eligible"
        elif _contains_any(text, ["da dang ky", "da co tam tru", "da co thuong tru"]):
            updates["registration_status"] = "already_registered"
        elif _contains_any(text, ["lan dau", "chua dang ky", "dang ky moi"]):
            updates["registration_status"] = "new"

    if expected_slot and expected_slot not in updates and updates:
        confidence = 0.72
    else:
        confidence = 0.56 if updates else 0.2

    return {
        "slot_updates": updates,
        "confidence": confidence,
        "needs_clarification": not bool(updates),
        "clarification_hint": "Mình chưa map chắc vào nhánh workflow. Bạn có thể bấm một lựa chọn nhanh bên dưới hoặc trả lời ngắn gọn hơn nhé.",
    }


def _normalize_residence_slots(slots: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(slots)
    if (
        normalized.get("residence_goal") == "register_permanent"
        and normalized.get("need_precondition_confirmation") == "need_confirmation"
    ):
        normalized["residence_goal"] = "eligibility_confirmation"
    return normalized


def _slot_priority(domain: DomainBundle) -> list[str]:
    if domain.key == "birth_registration":
        return [
            "request_type",
            "birth_location",
            "has_foreign_element",
            "combined_parent_recognition",
            "service_channel",
            "wants_linked_bundle",
            "request_type_detail",
        ]
    if domain.key == "residence_management":
        return [
            "residence_goal",
            "registration_status",
            "need_precondition_confirmation",
            "residence_place_type",
        ]
    return [node["slot"] for node in domain.config["decision_tree"]["nodes"]]


def _question_options(node: dict[str, Any]) -> list[str]:
    return [str(option) for option in node.get("options", [])]


def _quick_replies(node: dict[str, Any] | None) -> list[dict[str, str]]:
    if not node:
        return []
    return [
        {
            "value": option,
            "label": OPTION_LABELS.get(option, option),
            "description": OPTION_DESCRIPTIONS.get(option, ""),
        }
        for option in _question_options(node)
    ]


def _is_synthetic_node(domain_key: str, node_id: str | None) -> bool:
    return bool(node_id and node_id in SYNTHETIC_FLOWS.get(domain_key, {}))


def _synthetic_node(domain_key: str, node_id: str) -> dict[str, Any]:
    return SYNTHETIC_FLOWS[domain_key][node_id]


def _synthetic_start_node(domain_key: str) -> str | None:
    starts = {
        "birth_registration": "birth_binary_new",
        "residence_management": "res_binary_register",
    }
    return starts.get(domain_key)


def _parse_yes_no(user_message: str) -> str | None:
    text = _normalize(user_message)
    if text in {"yes", "y", "co", "dung", "dung roi", "phai", "chinh no"}:
        return "yes"
    if text in {"no", "n", "khong", "khong phai", "chua"}:
        return "no"
    return None


def _heuristic_entry_analysis(user_message: str) -> dict[str, Any]:
    text = _normalize(user_message)
    domain_key, clarification = LLM.detect_domain(user_message)
    if not domain_key:
        return {
            "domain_key": "unknown",
            "user_mode": "needs_guidance",
            "persona_key": "first_time_unclear",
            "assist_mode": "guided",
            "confidence": 0.2,
            "slot_updates": {},
            "reasoning_short": clarification,
        }

    slot_updates = _heuristic_parse(domain_key, user_message).get("slot_updates", {})
    user_mode = "needs_guidance"
    persona_key = "first_time_unclear"
    assist_mode = "guided"
    confidence = 0.72 if slot_updates else 0.45

    if _contains_any(text, ["toi da tra cuu", "toi biet roi", "cho toi checklist", "toi can nhanh", "khoi hoi tung buoc"]):
        user_mode = "knows_procedure"
        persona_key = "knows_procedure"
        assist_mode = "fast_track"
        confidence = max(confidence, 0.9)

    if _contains_any(text, ["toi khong ro", "toi khong biet", "giai thich giup", "huong dan tung buoc", "toi lon tuoi", "toi khong ranh cong nghe"]):
        user_mode = "needs_reassurance"
        persona_key = "elderly_confused"
        assist_mode = "guided"
        confidence = max(confidence, 0.78)

    if domain_key == "residence_management":
        if _contains_any(
            text,
            [
                "dang ky tam tru",
                "dang ky thuong tru",
                "gia han tam tru",
                "xoa tam tru",
                "xoa thuong tru",
                "tach ho",
                "dieu chinh thong tin cu tru",
                "khai bao tam vang",
                "thong bao luu tru",
                "xac nhan thong tin cu tru",
                "xac nhan dieu kien",
            ],
        ):
            user_mode = "knows_procedure"
            persona_key = "knows_procedure"
            assist_mode = "fast_track"
            confidence = 0.93
        elif _contains_any(text, ["o thue", "o nho", "chuyen cho o", "can giay xac nhan noi o"]):
            user_mode = "partially_clear"
            persona_key = "semi_clear"
            assist_mode = "guided"
            confidence = max(confidence, 0.8)
    if domain_key == "birth_registration":
        if _contains_any(
            text,
            [
                "dang ky lai khai sinh",
                "xin ban sao",
                "trich luc khai sinh",
                "ghi vao so ho tich",
                "dang ky khai sinh ket hop",
                "dang ky khai sinh",
            ],
        ):
            user_mode = "knows_procedure"
            persona_key = "knows_procedure"
            assist_mode = "fast_track"
            confidence = 0.9
        elif _contains_any(text, ["toi moi sinh con", "lam giay khai sinh cho be", "khai sinh cho be"]):
            user_mode = "partially_clear"
            persona_key = "semi_clear"
            assist_mode = "guided"
            confidence = 0.82

    return {
        "domain_key": domain_key,
        "user_mode": user_mode,
        "persona_key": persona_key,
        "assist_mode": assist_mode,
        "confidence": confidence,
        "slot_updates": slot_updates,
        "reasoning_short": "Heuristic entry analysis.",
    }


def _build_context_summary(domain: DomainBundle, slots: dict[str, Any]) -> str:
    if domain.key == "birth_registration":
        parts: list[str] = []
        request_type = slots.get("request_type")
        if request_type:
            parts.append(OPTION_LABELS.get(request_type, request_type).lower())
        birth_location = slots.get("birth_location")
        if birth_location:
            parts.append(OPTION_LABELS.get(birth_location, birth_location).lower())
        if slots.get("has_foreign_element") == "yes":
            parts.append("có yếu tố nước ngoài")
        if slots.get("has_foreign_element") == "no":
            parts.append("không có yếu tố nước ngoài")
        if parts:
            return "Mình đang hiểu đây là trường hợp " + ", ".join(parts) + "."
    if domain.key == "residence_management":
        parts = []
        goal = slots.get("residence_goal")
        if goal:
            parts.append(OPTION_LABELS.get(goal, goal).lower())
        place = slots.get("residence_place_type")
        if place:
            parts.append(OPTION_LABELS.get(place, place).lower())
        if parts:
            return "Mình đang hiểu nhu cầu của bạn là " + ", ".join(parts) + "."
    return ""


def _next_question(domain: DomainBundle, session: SessionState) -> dict[str, Any] | None:
    effective_slots = _normalize_residence_slots(session.slots) if domain.key == "residence_management" else dict(session.slots)
    candidates = domain.route_candidates(effective_slots)
    if not candidates:
        return None
    node_by_slot = {node["slot"]: node for node in domain.config["decision_tree"]["nodes"]}
    relevant_slots: set[str] = set()
    for route in candidates:
        relevant_slots.update(route["conditions"].keys())
    for slot_name in _slot_priority(domain):
        if effective_slots.get(slot_name) not in (None, "", "unknown"):
            continue
        node = node_by_slot.get(slot_name)
        if node and slot_name in relevant_slots:
            return node
    return None


def _build_question_message(domain: DomainBundle, session: SessionState, node: dict[str, Any], first_turn: bool = False) -> str:
    summary = _build_context_summary(domain, session.slots)
    if first_turn and summary:
        intro = "Để chốt đúng thủ tục, mình cần hỏi thêm 1 ý ngắn:"
    elif first_turn:
        intro = "Mình đã nhận ra nhóm thủ tục phù hợp. Cho mình hỏi nhanh 1 ý để đi đúng nhánh nhé:"
    else:
        intro = "Mình cần hỏi thêm 1 ý nữa để chốt đúng thủ tục:"
    return "\n".join(
        part
        for part in [
            summary,
            intro,
            node["question"],
            "Bạn có thể bấm nút gợi ý bên dưới hoặc trả lời tự nhiên.",
        ]
        if part
    )


def _build_synthetic_question_message(domain: DomainBundle, session: SessionState, question: str, first_turn: bool = False) -> str:
    summary = _build_context_summary(domain, session.slots)
    if first_turn and summary:
        intro = "Mình đang gỡ rối dần để chọn đúng thủ tục cho bạn:"
    elif first_turn:
        intro = "Mình sẽ hỏi từng câu rất ngắn để tránh bắt bạn chọn trong một danh sách dài:"
    else:
        intro = "Mình hỏi thêm 1 câu Có / Không để thu hẹp tiếp nhé:"
    return "\n".join(
        part
        for part in [
            summary,
            intro,
            question,
            "Bạn có thể bấm nút bên dưới hoặc trả lời tự nhiên.",
        ]
        if part
    )


def _conflict_message(domain: DomainBundle, session: SessionState, updates: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    if domain.key == "birth_registration":
        birth_location = session.slots.get("birth_location")
        service_channel = session.slots.get("service_channel")
        if birth_location == "abroad" and service_channel == "border_area":
            return (
                "Mình thấy có một điểm chưa khớp: `khu vực biên giới` thường dùng cho trường hợp khai sinh có yếu tố nước ngoài nhưng xử lý trong nước, còn `sinh ở nước ngoài` thường đi theo nhánh cơ quan đại diện hoặc một nhánh khác trong nước. Bạn chọn lại giúp mình nhé.",
                [
                    {"value": "consular", "label": OPTION_LABELS["consular"], "description": OPTION_DESCRIPTIONS["consular"]},
                    {"value": "domestic", "label": OPTION_LABELS["domestic"], "description": "Nếu lúc nãy bạn chọn nhầm, hãy quay về nhánh sinh trong nước."},
                ],
            )
        if birth_location == "abroad" and service_channel == "standard":
            return (
                "Mình thấy trường hợp `sinh ở nước ngoài` chưa khớp với lựa chọn `thông thường`. Bạn thử chọn lại theo hướng `cơ quan đại diện` nếu làm ở nước ngoài, hoặc chọn lại nơi sinh nếu lúc trước bạn bấm nhầm nhé.",
                [
                    {"value": "consular", "label": OPTION_LABELS["consular"], "description": OPTION_DESCRIPTIONS["consular"]},
                    {"value": "domestic", "label": OPTION_LABELS["domestic"], "description": "Chọn lại nếu thực tế trẻ sinh trong nước."},
                ],
            )
    return (
        "Mình thấy các thông tin vừa rồi đang chưa khớp nhau nên chưa thể chốt đúng thủ tục. Bạn chọn lại ý gần nhất hoặc mô tả lại ngắn gọn giúp mình nhé.",
        [],
    )


def _result_payload(domain: DomainBundle, route: dict[str, Any], session: SessionState) -> dict[str, Any]:
    procedure = domain.procedures.get(route["procedure_code"])
    if not procedure:
        raise KeyError(f"Thiếu dữ liệu tóm tắt cho mã {route['procedure_code']}")
    return {
        "route_id": route["route_id"],
        "procedure_code": procedure.code,
        "procedure_name": procedure.title,
        "agency": procedure.agency,
        "submit_to": procedure.submit_to,
        "summary": procedure.summary,
        "source_url": procedure.source_url,
        "why_this_route": route["why_this_route"],
        "collected_slots": session.slots,
    }


def _assistant_response(
    session: SessionState,
    text: str,
    result: dict[str, Any] | None = None,
    quick_replies: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "message": text,
        "domain_key": session.domain_key,
        "domain_label": DOMAINS[session.domain_key].label if session.domain_key else None,
        "assist_mode": session.assist_mode,
        "assist_mode_label": ASSIST_MODES.get(session.assist_mode or "", {}).get("label"),
        "user_mode": session.user_mode,
        "persona_key": session.persona_key,
        "persona_label": PERSONA_LABELS.get(session.persona_key or ""),
        "current_node_id": session.current_node_id,
        "slots": session.slots,
        "completed": result is not None,
        "result": result,
        "quick_replies": quick_replies or [],
    }


def _apply_updates(session: SessionState, updates: dict[str, Any]) -> None:
    bundle_value = updates.get("wants_linked_bundle")
    if bundle_value == "none":
        updates.setdefault("wants_linked_bhyt", "no")
        updates.setdefault("wants_linked_residence", "no")
    elif bundle_value == "bhyt_only":
        updates.setdefault("wants_linked_bhyt", "yes")
        updates.setdefault("wants_linked_residence", "no")
    elif bundle_value == "bhyt_and_residence":
        updates.setdefault("wants_linked_bhyt", "yes")
        updates.setdefault("wants_linked_residence", "yes")
    session.slots.update(updates)
    if (
        session.domain_key == "residence_management"
        and session.slots.get("residence_goal") == "register_permanent"
        and session.slots.get("need_precondition_confirmation") == "need_confirmation"
    ):
        session.slots["residence_goal"] = "eligibility_confirmation"


app = FastAPI(title="GovEase AI Workflow Chatbot")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "openai_configured": bool(LLM.api_key),
        "model": LLM.model,
        "domains": [{"key": item.key, "label": item.label} for item in DOMAINS.values()],
    }

@app.get("/api/catalog")
def get_catalog() -> dict[str, Any]:
    catalog_path = DATA_DIR.parent / "govease-unified" / "data" / "catalog" / "citizen_group_domains.json"
    if catalog_path.exists():
        return _read_json(catalog_path)
    return {}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    session_id = request.session_id or str(uuid4())
    session = SESSIONS.get(session_id) or SessionState(session_id=session_id)
    session.messages.append({"role": "user", "content": request.message})

    if session.completed_route_id and session.domain_key:
        domain = DOMAINS[session.domain_key]
        route = next(
            item for item in domain.config["decision_tree"]["routes"] if item["route_id"] == session.completed_route_id
        )
        result = _result_payload(domain, route, session)
        SESSIONS[session_id] = session
        return _assistant_response(
            session,
            "Mình đã chốt được thủ tục phù hợp ở lượt trước rồi. Nếu bạn muốn đi lại từ đầu cho trường hợp khác, hãy tải lại trang nhé.",
            result=result,
        )

    if not session.domain_key:
        entry = LLM.analyze_entry(request.message)
        domain_key = entry.get("domain_key")
        if domain_key not in DOMAINS:
            SESSIONS[session_id] = session
            return _assistant_response(
                session,
                entry.get("reasoning_short") or "Mình đang hỗ trợ 2 nhóm chính là khai sinh và cư trú. Bạn muốn bắt đầu với nhóm nào?",
                quick_replies=[
                    {"value": "birth_registration", "label": "Khai sinh"},
                    {"value": "residence_management", "label": "Cư trú"},
                ],
            )
        session.domain_key = domain_key
        session.user_mode = entry.get("user_mode") or session.user_mode or "needs_guidance"
        session.persona_key = entry.get("persona_key") or session.persona_key or "first_time_unclear"
        session.assist_mode = request.preferred_mode or entry.get("assist_mode") or session.assist_mode or "guided"
        entry_updates = entry.get("slot_updates") or {}
        if entry_updates:
            _apply_updates(session, dict(entry_updates))
    elif request.preferred_mode in ASSIST_MODES:
        session.assist_mode = request.preferred_mode

    domain = DOMAINS[session.domain_key]

    if not session.current_node_id and session.slots:
        exact = domain.exact_match(session.slots)
        if exact:
            session.completed_route_id = exact["route_id"]
            result = _result_payload(domain, exact, session)
            SESSIONS[session_id] = session
            return _assistant_response(
                session,
                (
                    f"Mình nhận ra bạn đã biết khá rõ nhu cầu của mình, nên mình chốt nhanh luôn: "
                    f"{result['procedure_name']} (mã {result['procedure_code']})."
                ),
                result=result,
            )

        next_node = _next_question(domain, session)
        if next_node and session.messages and len(session.messages) == 1:
            session.current_node_id = next_node["id"]
            session.asked_node_ids.append(next_node["id"])
            SESSIONS[session_id] = session
            return _assistant_response(
                session,
                _build_question_message(domain, session, next_node, first_turn=True),
                quick_replies=_quick_replies(next_node),
            )

    if session.current_node_id is None:
        if session.assist_mode == "guided" and not session.slots:
            synthetic_start = _synthetic_start_node(domain.key)
        else:
            synthetic_start = None
        if synthetic_start:
            session.current_node_id = synthetic_start
            session.asked_node_ids.append(synthetic_start)
        else:
            first_node = _next_question(domain, session)
            if not first_node:
                raise HTTPException(status_code=500, detail="Workflow bị thiếu node đầu vào.")
            session.current_node_id = first_node["id"]
            session.asked_node_ids.append(first_node["id"])

    if _is_synthetic_node(domain.key, session.current_node_id):
        node_id = session.current_node_id
        synthetic = _synthetic_node(domain.key, node_id)
        answer = _parse_yes_no(request.message)
        if answer is None:
            SESSIONS[session_id] = session
            return _assistant_response(
                session,
                _build_synthetic_question_message(
                    domain,
                    session,
                    synthetic["question"],
                    first_turn=len(session.asked_node_ids) <= 1,
                ),
                quick_replies=YES_NO_OPTIONS,
            )

        branch = synthetic[answer]
        if branch.get("set"):
            _apply_updates(session, dict(branch["set"]))

        next_id = branch.get("next")
        if next_id:
            if next_id in domain.node_map:
                session.current_node_id = next_id
                if next_id not in session.asked_node_ids:
                    session.asked_node_ids.append(next_id)
            else:
                session.current_node_id = next_id
                if next_id not in session.asked_node_ids:
                    session.asked_node_ids.append(next_id)
        else:
            session.current_node_id = None

        exact = domain.exact_match(session.slots)
        if exact:
            session.completed_route_id = exact["route_id"]
            session.current_node_id = None
            result = _result_payload(domain, exact, session)
            SESSIONS[session_id] = session
            return _assistant_response(
                session,
                (
                    f"Mình đã chốt được thủ tục phù hợp: {result['procedure_name']} "
                    f"(mã {result['procedure_code']}). Mình cũng đã cập nhật phần tóm tắt ở cột bên phải để bạn xem nhanh."
                ),
                result=result,
            )

        if session.current_node_id and _is_synthetic_node(domain.key, session.current_node_id):
            next_synthetic = _synthetic_node(domain.key, session.current_node_id)
            SESSIONS[session_id] = session
            return _assistant_response(
                session,
                _build_synthetic_question_message(domain, session, next_synthetic["question"]),
                quick_replies=YES_NO_OPTIONS,
            )

        if session.current_node_id and session.current_node_id in domain.node_map:
            node = domain.node_map[session.current_node_id]
            SESSIONS[session_id] = session
            return _assistant_response(
                session,
                _build_question_message(domain, session, node, first_turn=False),
                quick_replies=_quick_replies(node),
            )

        next_node = _next_question(domain, session)
        if next_node:
            session.current_node_id = next_node["id"]
            if next_node["id"] not in session.asked_node_ids:
                session.asked_node_ids.append(next_node["id"])
            SESSIONS[session_id] = session
            return _assistant_response(
                session,
                _build_question_message(domain, session, next_node, first_turn=False),
                quick_replies=_quick_replies(next_node),
            )

    parsed = LLM.parse_answer(domain, session, request.message)
    updates = parsed.get("slot_updates") or {}

    if updates:
        previous_slots = dict(session.slots)
        _apply_updates(session, updates)
    else:
        previous_slots = dict(session.slots)

    exact = domain.exact_match(session.slots)
    if exact:
        session.completed_route_id = exact["route_id"]
        session.current_node_id = None
        result = _result_payload(domain, exact, session)
        SESSIONS[session_id] = session
        return _assistant_response(
            session,
            (
                f"Mình đã chốt được thủ tục phù hợp: {result['procedure_name']} "
                f"(mã {result['procedure_code']}). Mình cũng đã cập nhật phần tóm tắt ở cột bên phải để bạn xem nhanh."
            ),
            result=result,
        )

    next_node = _next_question(domain, session)
    if not next_node:
        candidates = domain.route_candidates(session.slots)
        if len(candidates) == 0 and updates:
            session.slots = previous_slots
            text, quick_replies = _conflict_message(domain, session, updates)
            SESSIONS[session_id] = session
            return _assistant_response(
                session,
                text,
                quick_replies=quick_replies,
            )
        if len(candidates) == 1:
            session.completed_route_id = candidates[0]["route_id"]
            session.current_node_id = None
            result = _result_payload(domain, candidates[0], session)
            SESSIONS[session_id] = session
            return _assistant_response(
                session,
                f"Mình đã thu hẹp còn 1 thủ tục phù hợp: {result['procedure_name']} (mã {result['procedure_code']}).",
                result=result,
            )
        SESSIONS[session_id] = session
        return _assistant_response(
            session,
            parsed.get("clarification_hint")
            or "Mình đã thu hẹp được vài nhánh nhưng vẫn chưa đủ chắc để chốt một thủ tục duy nhất. Bạn mô tả thêm hoàn cảnh cụ thể giúp mình nhé.",
        )

    session.current_node_id = next_node["id"]
    if next_node["id"] not in session.asked_node_ids:
        session.asked_node_ids.append(next_node["id"])

    SESSIONS[session_id] = session
    return _assistant_response(
        session,
        _build_question_message(
            domain,
            session,
            next_node,
            first_turn=len(session.asked_node_ids) <= 2,
        ),
        quick_replies=_quick_replies(next_node),
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8010"))
    uvicorn.run(app, host="127.0.0.1", port=port)
