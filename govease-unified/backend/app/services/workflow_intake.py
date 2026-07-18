from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from govease_ai import LLMIntentParser, ProcedureAssistant
from govease_ai.procedure_data import DEFAULT_DATA_ROOT

CATALOG_ROOT = Path(__file__).resolve().parents[3] / "data" / "catalog"
logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower().strip())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return text.replace("đ", "d")


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


OPTION_LABELS = {
    "birth_registration": "Khai sinh",
    "residence_management": "Cư trú",
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
    "copy_extract": "Xin bản sao hoặc trích lục giấy khai sinh.",
    "foreign_record_note": "Ghi nhận việc đã đăng ký ở nước ngoài.",
    "existing_personal_documents": "Người đã có giấy tờ cá nhân nhưng thiếu khai sinh hợp lệ.",
    "mobile_service": "Trường hợp làm theo diện lưu động.",
    "domestic": "Trẻ sinh tại Việt Nam.",
    "abroad": "Trẻ sinh ở nước ngoài.",
    "yes": "Đúng với trường hợp của bạn.",
    "no": "Không đúng với trường hợp của bạn.",
    "register_permanent": "Đăng ký ở ổn định lâu dài tại địa chỉ đó.",
    "register_temporary": "Đăng ký ở tạm tại nơi ở hiện tại.",
    "extend_temporary": "Gia hạn thời gian tạm trú đã có.",
    "delete_temporary": "Xóa đăng ký tạm trú cũ.",
    "delete_permanent": "Xóa đăng ký thường trú cũ.",
    "split_household": "Tách khỏi hộ hiện tại để thành hộ riêng.",
    "adjust_data": "Sửa hoặc cập nhật dữ liệu cư trú.",
    "absence_notice": "Khai báo vắng khỏi nơi cư trú một thời gian.",
    "lodging_notice": "Thông báo có người lưu trú ngắn hạn.",
    "residence_confirmation": "Xin xác nhận thông tin cư trú hiện có.",
    "eligibility_confirmation": "Xin xác nhận điều kiện trước khi đăng ký cư trú.",
    "fallback_info_declaration": "Khai báo nơi ở khi chưa đủ điều kiện đăng ký chính thức.",
    "owned_home": "Nhà thuộc sở hữu của bạn hoặc gia đình bạn.",
    "rented_borrowed_stayed": "Nhà thuê, mượn hoặc ở nhờ.",
    "vehicle_dwelling": "Phương tiện như tàu, thuyền, xe dùng để ở.",
    "need_confirmation": "Cần xin xác nhận trước khi đi tiếp.",
    "ready_for_main_registration": "Đã đủ điều kiện để nộp hồ sơ chính.",
    "new": "Trường hợp đăng ký mới.",
    "already_registered": "Đã từng đăng ký ở địa chỉ này.",
    "not_eligible": "Hiện chưa đủ điều kiện đăng ký.",
}

YES_NO_OPTIONS = [
    {"value": "yes", "label": "Có", "description": "Đúng với trường hợp của bạn."},
    {"value": "no", "label": "Không", "description": "Không đúng với trường hợp của bạn."},
]

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
            "yes": {"set": {"residence_goal": "fallback_info_declaration", "registration_status": "not_eligible"}},
            "no": {"next": "residence_goal"},
        },
    },
}


@dataclass
class DomainBundle:
    key: str
    label: str
    config: dict[str, Any]
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


@dataclass
class WorkflowSession:
    session_id: str
    domain_key: str | None = None
    current_node_id: str | None = None
    asked_node_ids: list[str] = field(default_factory=list)
    slots: dict[str, Any] = field(default_factory=dict)
    messages: list[dict[str, str]] = field(default_factory=list)
    completed_route_id: str | None = None
    interaction_mode: str = "fast_track"


class WorkflowIntakeService:
    def __init__(self, assistant: ProcedureAssistant, intent_parser: Any | None = None) -> None:
        self.assistant = assistant
        self.intent_parser = intent_parser or LLMIntentParser(assistant.model_config)
        self.sessions: dict[str, WorkflowSession] = {}
        data_root = Path(DEFAULT_DATA_ROOT)
        self.domains: dict[str, DomainBundle] = {
            "birth_registration": DomainBundle(
                key="birth_registration",
                label="Khai sinh",
                config=_read_json(data_root / "birth_procedure" / "workflow_engine_config.json"),
            ),
            "residence_management": DomainBundle(
                key="residence_management",
                label="Cư trú",
                config=_read_json(data_root / "residence_procedures" / "workflow_engine_config.json"),
            ),
        }
        self.domains = self._load_domains(data_root)
        for domain in self.domains.values():
            domain.node_map = {node["id"]: node for node in domain.config["decision_tree"]["nodes"]}
        self.code_to_domain: dict[str, str] = {}
        self.route_by_domain_and_code: dict[tuple[str, str], dict[str, Any]] = {}
        for domain_key, domain in self.domains.items():
            for route in domain.config["decision_tree"]["routes"]:
                procedure_code = route.get("procedure_code")
                if procedure_code:
                    self.code_to_domain[procedure_code] = domain_key
                    self.route_by_domain_and_code[(domain_key, procedure_code)] = route

    def _load_domains(self, data_root: Path) -> dict[str, DomainBundle]:
        labels = _workflow_domain_labels()
        domains: dict[str, DomainBundle] = {}

        legacy_paths = {
            "birth_registration": data_root / "birth_procedure" / "workflow_engine_config.json",
            "residence_management": data_root / "residence_procedures" / "workflow_engine_config.json",
        }
        for key, path in legacy_paths.items():
            if not path.exists():
                continue
            domains[key] = DomainBundle(
                key=key,
                label=labels.get(key, key.replace("_", " ").title()),
                config=_read_json(path),
            )

        workflow_root = data_root / "workflows"
        if workflow_root.exists():
            for path in sorted(workflow_root.glob("*/workflow_engine_config.json")):
                config = _read_json(path)
                key = str(config.get("domain") or path.parent.name)
                domains[key] = DomainBundle(
                    key=key,
                    label=labels.get(key, key.replace("_", " ").title()),
                    config=config,
                )
        return domains

    def _infer_entry_from_routes(self, message: str) -> dict[str, Any] | None:
        text = _normalize(message)
        if _contains_any(text, ["bao hiem", "bhyt"]) and _contains_any(text, ["con", "tre", "em be", "so sinh", "moi sinh"]):
            return {
                "domain_key": "co_con_nho" if "co_con_nho" in self.domains else "birth_registration",
                "confidence": 0.78,
                "slot_updates": {
                    **({"subdomain_key": "bao_hiem_y_te"} if "co_con_nho" in self.domains else {}),
                    **({} if "co_con_nho" in self.domains else {"request_type": "new_registration", "wants_linked_bundle": "bhyt_only"}),
                },
            }
        domain_guess = _best_matching_domain_subdomain(self.domains, message)
        if domain_guess:
            return domain_guess
        procedure_code, score = self.assistant.retriever.classify(message)
        if not procedure_code or score <= 0:
            return None
        domain_key = self.code_to_domain.get(procedure_code)
        if domain_key not in self.domains:
            return None

        route = self.route_by_domain_and_code.get((domain_key, procedure_code))
        route_conditions = dict((route or {}).get("conditions") or {})
        slot_updates = route_conditions or _heuristic_parse(domain_key, message).get("slot_updates", {})
        return {
            "domain_key": domain_key,
            "confidence": 0.6 if route_conditions else 0.55,
            "slot_updates": slot_updates,
        }

    def _infer_entry_with_ai(self, message: str) -> dict[str, Any] | None:
        raw = self.intent_parser.parse(
            message,
            supported_domains=list(self.domains.keys()),
            supported_taxonomy=_taxonomy_payload(self.domains),
        )
        if not isinstance(raw, dict):
            return None
        domain_key = raw.get("domain_key")
        if domain_key not in {*self.domains.keys(), "unknown"}:
            return None
        confidence = raw.get("confidence")
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            return None
        confidence_value = max(0.0, min(confidence_value, 1.0))
        slot_updates = _sanitize_slot_updates(domain_key, raw.get("slot_updates") or {})
        subdomain_key = raw.get("subdomain_key")
        if (
            domain_key in self.domains
            and isinstance(subdomain_key, str)
            and subdomain_key in _subdomain_labels(self.domains[domain_key].config)
        ):
            slot_updates.setdefault("subdomain_key", subdomain_key)
        return {
            "domain_key": domain_key,
            "confidence": confidence_value,
            "slot_updates": slot_updates,
        }

    def handle(
        self,
        message: str,
        *,
        session_id: str | None = None,
        preferred_domain_key: str | None = None,
        preferred_subdomain_key: str | None = None,
    ) -> dict[str, Any]:
        diagnostics = _RequestDiagnostics()
        session = self.sessions.get(session_id or "") or WorkflowSession(session_id=session_id or str(uuid4()))
        try:
            session.messages.append({"role": "user", "content": message})
            _update_interaction_mode(session, message)
            locked_domain_key = preferred_domain_key if preferred_domain_key in self.domains else None
            if session.domain_key is None and preferred_domain_key in self.domains:
                session.domain_key = preferred_domain_key
            if preferred_subdomain_key and session.slots.get("subdomain_key") in (None, "", "unknown"):
                session.slots["subdomain_key"] = preferred_subdomain_key

            latest_entry = _heuristic_entry_analysis(message)
            diagnostics.mark("heuristic_entry")
            if locked_domain_key:
                latest_entry = {
                    "domain_key": locked_domain_key,
                    "confidence": 1.0,
                    "slot_updates": dict(session.slots),
                }
            if session.domain_key is None:
                heuristic_entry = _apply_entry_heuristic_hints(message, latest_entry)
                if _should_lock_legacy_first_turn(message, heuristic_entry):
                    latest_entry = heuristic_entry
                else:
                    ai_entry = self._infer_entry_with_ai(message)
                    diagnostics.mark("ai_domain_inference")
                    if _entry_has_domain(ai_entry):
                        latest_entry = _merge_entry(ai_entry, heuristic_entry) or heuristic_entry
                    else:
                        latest_entry = heuristic_entry
                    generic_hint = _best_matching_domain_subdomain(self.domains, message)
                    diagnostics.mark("catalog_domain_match")
                    if _entry_is_better(generic_hint, latest_entry) and not _should_keep_legacy_entry(
                        message,
                        latest_entry,
                        generic_hint,
                    ):
                        latest_entry = _merge_entry(generic_hint, latest_entry) or generic_hint
                if latest_entry.get("domain_key") not in self.domains:
                    route_hint = self._infer_entry_from_routes(message)
                    diagnostics.mark("route_classifier_fallback")
                    if _entry_is_better(route_hint, latest_entry):
                        latest_entry = route_hint
            switched = _maybe_switch_domain(session, latest_entry)
            diagnostics.mark("domain_resolution")

            if session.completed_route_id and session.domain_key:
                domain = self.domains[session.domain_key]
                route = next(
                    item for item in domain.config["decision_tree"]["routes"] if item["route_id"] == session.completed_route_id
                )
                response = self._finalize_route(session, domain, route, diagnostics=diagnostics)
                self.sessions[session.session_id] = session
                return response

            if not session.domain_key:
                domain_key = latest_entry.get("domain_key")
                if domain_key not in self.domains:
                    self.sessions[session.session_id] = session
                    return self._response(
                            session,
                            status="needs_clarification",
                        question=_build_domain_selection_message(session),
                        quick_replies=_domain_selection_replies(self.domains),
                        confidence=0.2,
                    )
                session.domain_key = domain_key
                entry_updates = dict(latest_entry.get("slot_updates") or {})
                if _should_defer_route_resolution(domain_key, message):
                    entry_updates = _strip_route_level_updates(domain_key, entry_updates)
                if entry_updates:
                    _apply_updates(session, entry_updates)

            domain = self.domains[session.domain_key]
            defer_route_resolution = _should_defer_route_resolution(domain.key, message)
            if domain.key not in {"birth_registration", "residence_management"} and not session.slots.get("subdomain_key"):
                domain_hint = _best_matching_domain_subdomain({domain.key: domain}, message)
                if domain_hint and domain_hint.get("slot_updates"):
                    domain_hint_updates = dict(domain_hint["slot_updates"])
                    if defer_route_resolution:
                        domain_hint_updates = _strip_route_level_updates(domain.key, domain_hint_updates)
                    if domain_hint_updates:
                        _apply_updates(session, domain_hint_updates)
            effective_subdomain_key = preferred_subdomain_key or (
                session.slots.get("subdomain_key") if isinstance(session.slots.get("subdomain_key"), str) else None
            )
            inferred_route = None
            if not defer_route_resolution:
                inferred_route = self._infer_route_from_existing_domain(domain.key, message, effective_subdomain_key)
            diagnostics.mark("existing_domain_route_inference")
            if inferred_route:
                _apply_updates(session, inferred_route["slot_updates"])

            explain_payload = _maybe_build_explain_mode_payload(domain, session, message)
            if explain_payload is not None:
                self.sessions[session.session_id] = session
                return self._response(
                        session,
                    status="needs_clarification",
                    question=explain_payload["question"],
                    quick_replies=explain_payload["quick_replies"],
                    confidence=float(explain_payload["confidence"]),
                )

            if not session.current_node_id and session.slots:
                exact = domain.exact_match(session.slots)
                if exact and not defer_route_resolution:
                    session.completed_route_id = exact["route_id"]
                    self.sessions[session.session_id] = session
                    return self._finalize_route(session, domain, exact, diagnostics=diagnostics)

                next_node = _next_question(domain, session)
                if next_node and len(session.messages) == 1:
                    session.current_node_id = next_node["id"]
                    session.asked_node_ids.append(next_node["id"])
                    self.sessions[session.session_id] = session
                    return self._response(
                        session,
                        status="needs_clarification",
                        question=_build_question_message(domain, session, next_node, first_turn=True),
                        quick_replies=_quick_replies(next_node, session),
                        confidence=latest_entry.get("confidence", 0.78),
                    )

            if session.current_node_id is None:
                synthetic_start = _synthetic_start_node(domain.key) if not session.slots else None
                if synthetic_start:
                    session.current_node_id = synthetic_start
                    session.asked_node_ids.append(synthetic_start)
                else:
                    first_node = _next_question(domain, session)
                    if not first_node:
                        self.sessions[session.session_id] = session
                        return self._response(
                            session,
                            status="needs_clarification",
                            question="M?nh ch?a ?? d? li?u ?? ch?n ??ng th? t?c. B?n m? t? l?i ng?n g?n h?n gi?p m?nh nh?.",
                            quick_replies=[],
                            confidence=0.2,
                        )
                    session.current_node_id = first_node["id"]
                    session.asked_node_ids.append(first_node["id"])

            if _is_synthetic_node(domain.key, session.current_node_id):
                response = self._handle_synthetic(domain, session, message)
                self.sessions[session.session_id] = session
                return response

            node = domain.node_map[session.current_node_id]
            parsed = _match_node_option(node, session, message) or _heuristic_parse(domain.key, message, node.get("slot"))
            updates = parsed.get("slot_updates") or {}
            previous_slots = dict(session.slots)
            if updates:
                _apply_updates(session, updates)

            exact = domain.exact_match(session.slots)
            if exact:
                session.completed_route_id = exact["route_id"]
                session.current_node_id = None
                self.sessions[session.session_id] = session
                return self._finalize_route(session, domain, exact, diagnostics=diagnostics)

            next_node = _next_question(domain, session)
            if not next_node:
                candidates = domain.route_candidates(session.slots)
                if len(candidates) == 0 and updates:
                    session.slots = previous_slots
                    retry_payload = _retry_current_question_payload(
                        domain,
                        session,
                        prefix="M?nh th?y c?u tr? l?i v?a r?i ch?a kh?p v?i nh?nh ?ang h?i, n?n m?nh h?i l?i ??ng 1 ? n?y ?? tr?nh ?i sai th? t?c:",
                        confidence=0.4,
                    )
                    self.sessions[session.session_id] = session
                    return self._response(
                        session,
                        status="needs_clarification",
                        question=retry_payload["question"],
                        quick_replies=retry_payload["quick_replies"],
                        confidence=retry_payload["confidence"],
                    )
                if len(candidates) == 1:
                    session.completed_route_id = candidates[0]["route_id"]
                    session.current_node_id = None
                    self.sessions[session.session_id] = session
                    return self._finalize_route(session, domain, candidates[0], diagnostics=diagnostics)
                if not updates:
                    retry_payload = _retry_current_question_payload(
                        domain,
                        session,
                        prefix="M?nh ch?a b?t ??ng ? tr? l?i ? c?u n?y.",
                        confidence=parsed.get("confidence", 0.3),
                    )
                    self.sessions[session.session_id] = session
                    return self._response(
                        session,
                        status="needs_clarification",
                        question=retry_payload["question"],
                        quick_replies=retry_payload["quick_replies"],
                        confidence=retry_payload["confidence"],
                    )
                self.sessions[session.session_id] = session
                return self._response(
                    session,
                    status="needs_clarification",
                    question=parsed.get("clarification_hint")
                    or "M?nh ?? thu h?p ???c v?i nh?nh nh?ng v?n ch?a ?? ch?c ?? ch?t m?t th? t?c duy nh?t. B?n m? t? th?m ho?n c?nh c? th? gi?p m?nh nh?.",
                    quick_replies=[],
                    confidence=parsed.get("confidence", 0.3),
                )

            session.current_node_id = next_node["id"]
            if next_node["id"] not in session.asked_node_ids:
                session.asked_node_ids.append(next_node["id"])
            self.sessions[session.session_id] = session
            return self._response(
                session,
                status="needs_clarification",
                question=_build_question_message(domain, session, next_node, first_turn=len(session.asked_node_ids) <= 2),
                quick_replies=_quick_replies(next_node, session),
                confidence=max(parsed.get("confidence", 0.76), 0.82 if switched else 0.76),
            )
        finally:
            logger.info(
                "workflow_intake_timing session=%s domain=%s node=%s route=%s total_ms=%.2f steps=%s",
                session.session_id,
                session.domain_key,
                session.current_node_id,
                session.completed_route_id,
                diagnostics.snapshot(message_count=len(session.messages), slot_count=len(session.slots))["total_ms"],
                diagnostics.steps_ms,
            )

    def _handle_synthetic(self, domain: DomainBundle, session: WorkflowSession, message: str) -> dict[str, Any]:
        node_id = session.current_node_id or ""
        synthetic = SYNTHETIC_FLOWS[domain.key][node_id]
        answer = _parse_yes_no(message)
        if answer is None:
            return self._response(
                session,
                status="needs_clarification",
                question=_build_synthetic_question_message(
                    domain,
                    session,
                    synthetic["question"],
                    first_turn=len(session.asked_node_ids) <= 1,
                ),
                quick_replies=YES_NO_OPTIONS,
                confidence=0.55,
            )

        branch = synthetic[answer]
        if branch.get("set"):
            _apply_updates(session, dict(branch["set"]))

        next_id = branch.get("next")
        session.current_node_id = next_id
        if next_id and next_id not in session.asked_node_ids:
            session.asked_node_ids.append(next_id)

        exact = domain.exact_match(session.slots)
        if exact:
            session.completed_route_id = exact["route_id"]
            session.current_node_id = None
            return self._finalize_route(session, domain, exact)

        if session.current_node_id and _is_synthetic_node(domain.key, session.current_node_id):
            next_synthetic = SYNTHETIC_FLOWS[domain.key][session.current_node_id]
            return self._response(
                session,
                status="needs_clarification",
                question=_build_synthetic_question_message(domain, session, next_synthetic["question"]),
                quick_replies=YES_NO_OPTIONS,
                confidence=0.68,
            )

        if session.current_node_id and session.current_node_id in domain.node_map:
            node = domain.node_map[session.current_node_id]
            return self._response(
                session,
                status="needs_clarification",
                question=_build_question_message(domain, session, node),
                quick_replies=_quick_replies(node, session),
                confidence=0.76,
            )

        next_node = _next_question(domain, session)
        if next_node:
            session.current_node_id = next_node["id"]
            if next_node["id"] not in session.asked_node_ids:
                session.asked_node_ids.append(next_node["id"])
            return self._response(
                session,
                status="needs_clarification",
                question=_build_question_message(domain, session, next_node),
                quick_replies=_quick_replies(next_node, session),
                confidence=0.76,
            )

        return self._response(
            session,
            status="needs_clarification",
            question="Mình cần thêm một vài chi tiết để chốt đúng thủ tục.",
            quick_replies=[],
            confidence=0.3,
        )

    def _finalize_route(
        self,
        session: WorkflowSession,
        domain: DomainBundle,
        route: dict[str, Any],
        *,
        diagnostics: _RequestDiagnostics | None = None,
    ) -> dict[str, Any]:
        user_need = " ".join(item["content"] for item in session.messages if item["role"] == "user")
        intake = self.assistant.guided_intake(
            user_need,
            procedure_identifier=route["procedure_code"],
            answers=session.slots,
        )
        if diagnostics is not None:
            diagnostics.mark("guided_intake_finalize")
        procedure_payload = intake.get("procedure") or _procedure_payload_from_route(route)
        return {
            "session_id": session.session_id,
            "status": "completed",
            "needs_clarification": False,
            "clarifying_question_id": None,
            "clarifying_question": None,
            "answers": dict(session.slots),
            "confidence": 1.0,
            "procedure": procedure_payload,
            "checklist": intake.get("checklist") or {"documents": [], "conditional_documents": [], "steps": []},
            "examples": intake.get("examples") or [],
            "common_errors": intake.get("common_errors") or [],
            "sources": intake.get("sources") or [],
            "quick_replies": [],
            "current_node_id": None,
            "domain_key": domain.key,
            "domain_label": domain.label,
            "workflow_state": {
                "completed_route_id": route["route_id"],
                "procedure_code": route["procedure_code"],
                "slots": dict(session.slots),
                "why_this_route": route.get("why_this_route"),
                "interaction_mode": session.interaction_mode,
            },
        }

    def _response(
        self,
        session: WorkflowSession,
        *,
        status: str,
        question: str,
        quick_replies: list[dict[str, str]],
        confidence: float,
    ) -> dict[str, Any]:
        domain_label = self.domains[session.domain_key].label if session.domain_key in self.domains else None
        return {
            "session_id": session.session_id,
            "status": status,
            "needs_clarification": True,
            "clarifying_question_id": session.current_node_id,
            "clarifying_question": question,
            "answers": dict(session.slots),
            "confidence": float(confidence),
            "procedure": None,
            "checklist": {"documents": [], "conditional_documents": [], "steps": []},
            "examples": [],
            "common_errors": [],
            "sources": [],
            "quick_replies": quick_replies,
            "current_node_id": session.current_node_id,
            "domain_key": session.domain_key,
            "domain_label": domain_label,
            "workflow_state": {
                "slots": dict(session.slots),
                "asked_node_ids": list(session.asked_node_ids),
                "interaction_mode": session.interaction_mode,
            },
        }

    def _infer_route_from_existing_domain(
        self,
        domain_key: str,
        message: str,
        preferred_subdomain_key: str | None,
    ) -> dict[str, Any] | None:
        if domain_key in {"birth_registration", "residence_management"} and not preferred_subdomain_key:
            return None
        domain = self.domains.get(domain_key)
        if domain and preferred_subdomain_key:
            heuristic_route = _best_matching_route(domain, message, preferred_subdomain_key)
            if heuristic_route:
                return {
                    "slot_updates": dict(heuristic_route.get("conditions") or {}),
                    "confidence": 0.93,
                }
        procedure_code, score = self.assistant.retriever.classify(message)
        if not procedure_code or score <= 0:
            return None
        route = self.route_by_domain_and_code.get((domain_key, procedure_code))
        if not route:
            return None
        conditions = dict(route.get("conditions") or {})
        route_subdomain = conditions.get("subdomain_key")
        if preferred_subdomain_key and route_subdomain not in (None, "", preferred_subdomain_key):
            return None
        return {
            "slot_updates": conditions,
            "confidence": min(max(float(score), 0.6), 0.98),
        }


def _parse_yes_no(user_message: str) -> str | None:
    text = _normalize(user_message)
    if text in {"yes", "y", "co", "dung", "dung roi", "phai", "chinh no"}:
        return "yes"
    if text in {"no", "n", "khong", "khong phai", "chua"}:
        return "no"
    return None


@dataclass
class _RequestDiagnostics:
    started_at: float = field(default_factory=perf_counter)
    last_mark_at: float = field(default_factory=perf_counter)
    steps_ms: dict[str, float] = field(default_factory=dict)

    def mark(self, name: str) -> None:
        now = perf_counter()
        self.steps_ms[name] = round((now - self.last_mark_at) * 1000, 2)
        self.last_mark_at = now

    def snapshot(self, *, message_count: int, slot_count: int) -> dict[str, Any]:
        total_ms = round((perf_counter() - self.started_at) * 1000, 2)
        dominant_step = max(self.steps_ms.items(), key=lambda item: item[1])[0] if self.steps_ms else "none"
        return {
            "total_ms": total_ms,
            "steps_ms": dict(self.steps_ms),
            "dominant_step": dominant_step,
            "message_count": message_count,
            "slot_count": slot_count,
        }


def _synthetic_start_node(domain_key: str) -> str | None:
    starts = {
        "birth_registration": "birth_binary_new",
        "residence_management": "res_binary_register",
    }
    return starts.get(domain_key)


def _is_synthetic_node(domain_key: str, node_id: str | None) -> bool:
    return bool(node_id and node_id in SYNTHETIC_FLOWS.get(domain_key, {}))


def _quick_replies(node: dict[str, Any] | None, session: WorkflowSession | None = None) -> list[dict[str, str]]:
    if not node:
        return []
    return _quick_replies_for_items(_node_option_items(node, session))


def _quick_replies_for_options(options: list[str]) -> list[dict[str, str]]:
    if not options:
        return []
    return [
        {
            "value": option,
            "label": OPTION_LABELS.get(option, option),
            "description": OPTION_DESCRIPTIONS.get(option, ""),
        }
        for option in options
    ]


def _quick_replies_for_items(options: list[dict[str, str]]) -> list[dict[str, str]]:
    if not options:
        return []
    return options


def _match_node_option(node: dict[str, Any], session: WorkflowSession, user_message: str) -> dict[str, Any] | None:
    slot = str(node.get("slot") or "").strip()
    if not slot:
        return None
    text = _normalize(user_message)
    for option in _node_option_items(node, session):
        value = option["value"]
        label = option["label"]
        if text in {_normalize(value), _normalize(label), _normalize(OPTION_LABELS.get(value, value))}:
            return {
                "slot_updates": {slot: value},
                "confidence": 0.99,
                "needs_clarification": False,
                "clarification_hint": "",
            }
    return None


def _node_options(node: dict[str, Any], session: WorkflowSession | None = None) -> list[str]:
    return [item["value"] for item in _node_option_items(node, session)]


def _node_option_items(node: dict[str, Any], session: WorkflowSession | None = None) -> list[dict[str, str]]:
    if not node:
        return []

    if session and node.get("slot") == "request_type_detail" and session.domain_key == "birth_registration":
        if session.slots.get("request_type") == "foreign_record_note":
            return _option_items_from_values(["birth_only", "multi_civil_status"])

    if session and node.get("slot") == "operation_key":
        subdomain_key = session.slots.get("subdomain_key")
        options_by_subdomain = node.get("options_by_subdomain") or {}
        raw_items = options_by_subdomain.get(subdomain_key, []) if isinstance(options_by_subdomain, dict) else []
        items: list[dict[str, str]] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            value = str(raw.get("operation_key") or "").strip()
            if not value:
                continue
            label = (
                str(raw.get("procedure_title") or "").strip()
                or str(raw.get("label") or "").strip()
                or OPTION_LABELS.get(value, value)
            )
            description = str(raw.get("operation_group") or "").replace("_", " ").strip()
            items.append({"value": value, "label": label, "description": description})
        return items

    return _option_items_from_values(list(node.get("options", [])))


def _option_items_from_values(options: list[str]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for option in options:
        items.append(
            {
                "value": option,
                "label": OPTION_LABELS.get(option, option),
                "description": OPTION_DESCRIPTIONS.get(option, ""),
            }
        )
    return items


def _normalize_residence_slots(slots: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(slots)
    return _harmonize_residence_slots(normalized)


def _harmonize_residence_slots(slots: dict[str, Any]) -> dict[str, Any]:
    harmonized = dict(slots)
    goal = harmonized.get("residence_goal")
    need_confirmation = harmonized.get("need_precondition_confirmation")
    place_type = harmonized.get("residence_place_type")

    # For owner-occupied legal housing, there is no separate pre-confirmation route.
    # If the user asks for pre-confirmation anyway, route them back to direct permanent registration.
    if goal in {"register_permanent", "eligibility_confirmation"} and place_type == "owned_home":
        harmonized["residence_goal"] = "register_permanent"
        harmonized["need_precondition_confirmation"] = "ready_for_main_registration"
        return harmonized

    if (
        goal == "register_permanent"
        and need_confirmation == "need_confirmation"
        and place_type in {"rented_borrowed_stayed", "vehicle_dwelling"}
    ):
        harmonized["residence_goal"] = "eligibility_confirmation"
    return harmonized


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
    return [node["slot"] for node in domain.config["decision_tree"]["nodes"] if isinstance(node, dict) and node.get("slot")]


def _next_question(domain: DomainBundle, session: WorkflowSession) -> dict[str, Any] | None:
    effective_slots = _normalize_residence_slots(session.slots) if domain.key == "residence_management" else dict(session.slots)
    if (
        domain.key == "residence_management"
        and effective_slots.get("residence_goal") in {"register_permanent", "eligibility_confirmation"}
        and effective_slots.get("residence_place_type") in (None, "", "unknown")
    ):
        node_by_slot = {node["slot"]: node for node in domain.config["decision_tree"]["nodes"]}
        return node_by_slot.get("residence_place_type")
    if (
        domain.key == "residence_management"
        and effective_slots.get("residence_goal") == "register_permanent"
        and effective_slots.get("residence_place_type") in {"rented_borrowed_stayed", "vehicle_dwelling"}
        and effective_slots.get("need_precondition_confirmation") in (None, "", "unknown")
    ):
        node_by_slot = {node["slot"]: node for node in domain.config["decision_tree"]["nodes"]}
        return node_by_slot.get("need_precondition_confirmation")
    candidates = domain.route_candidates(effective_slots)
    if not candidates:
        return None
    node_by_slot = {node["slot"]: node for node in domain.config["decision_tree"]["nodes"]}
    relevant_slots: set[str] = set()
    for route in candidates:
        relevant_slots.update(route["conditions"].keys())
    if domain.key == "birth_registration" and (
        "wants_linked_bhyt" in relevant_slots or "wants_linked_residence" in relevant_slots
    ):
        relevant_slots.add("wants_linked_bundle")
    for slot_name in _slot_priority(domain):
        if effective_slots.get(slot_name) not in (None, "", "unknown"):
            continue
        node = node_by_slot.get(slot_name)
        if node and slot_name in relevant_slots:
            return node
    return None


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


def _build_question_message(domain: DomainBundle, session: WorkflowSession, node: dict[str, Any], first_turn: bool = False) -> str:
    summary = _build_context_summary(domain, session.slots)
    question_text = _question_text_for_node(domain, session, node)
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
            question_text,
            "Bạn có thể bấm nút gợi ý bên dưới hoặc trả lời tự nhiên.",
        ]
        if part
    )


def _build_synthetic_question_message(domain: DomainBundle, session: WorkflowSession, question: str, first_turn: bool = False) -> str:
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


def _question_text_for_node(domain: DomainBundle, session: WorkflowSession, node: dict[str, Any]) -> str:
    if domain.key == "birth_registration" and node.get("slot") == "request_type_detail":
        request_type = session.slots.get("request_type")
        if request_type == "foreign_record_note":
            return "Việc hộ tịch đã làm ở nước ngoài mà bạn muốn ghi vào sổ ở Việt Nam là khai sinh hay một việc hộ tịch khác?"
        if request_type == "existing_personal_documents":
            return "Người cần đăng ký đã có hồ sơ, giấy tờ cá nhân từ trước nhưng chưa có khai sinh hợp lệ đúng không?"
    if domain.key == "residence_management" and node.get("slot") == "residence_place_type":
        if session.slots.get("residence_goal") == "register_permanent":
            return "Chỗ ở bạn dùng để đăng ký thường trú là nhà thuộc sở hữu của mình, chỗ ở do thuê/mượn/ở nhờ, hay phương tiện dùng để ở?"
    if domain.key == "residence_management" and node.get("slot") == "need_precondition_confirmation":
        if session.slots.get("residence_place_type") in {"rented_borrowed_stayed", "vehicle_dwelling"}:
            return "Với trường hợp này, bạn muốn xin xác nhận điều kiện trước, hay đã sẵn sàng nộp hồ sơ đăng ký thường trú chính?"
    return str(node["question"])


def _retry_current_question_payload(
    domain: DomainBundle,
    session: WorkflowSession,
    *,
    prefix: str,
    confidence: float,
) -> dict[str, Any]:
    node = domain.node_map.get(session.current_node_id or "")
    if not node:
        return {
            "question": prefix,
            "quick_replies": [],
            "confidence": confidence,
        }
    return {
        "question": "\n".join(
            [
                prefix,
                _question_text_for_node(domain, session, node),
                "Bạn có thể bấm một gợi ý bên dưới hoặc trả lời ngắn gọn đúng ý này nhé.",
            ]
        ),
        "quick_replies": _quick_replies(node, session),
        "confidence": confidence,
    }


def _apply_updates(session: WorkflowSession, updates: dict[str, Any]) -> None:
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
        session.domain_key == "birth_registration"
        and session.slots.get("birth_location") == "domestic"
        and session.slots.get("has_foreign_element") == "no"
        and not session.slots.get("service_channel")
        and session.slots.get("request_type") != "mobile_service"
    ):
        session.slots["service_channel"] = "standard"
    if (
        session.domain_key == "birth_registration"
        and session.slots.get("request_type") == "new_registration"
        and session.slots.get("birth_location") == "abroad"
        and not session.slots.get("service_channel")
    ):
        # Children born abroad are handled through the overseas representative route in the current dataset.
        session.slots["service_channel"] = "consular"
    if session.domain_key == "residence_management":
        session.slots = _harmonize_residence_slots(session.slots)


ALLOWED_SLOT_VALUES: dict[str, set[str]] = {
    "request_type": {
        "new_registration",
        "re_registration",
        "copy_extract",
        "foreign_record_note",
        "existing_personal_documents",
        "mobile_service",
    },
    "birth_location": {"domestic", "abroad"},
    "has_foreign_element": {"yes", "no"},
    "combined_parent_recognition": {"yes", "no"},
    "wants_linked_bundle": {"none", "bhyt_only", "bhyt_and_residence"},
    "service_channel": {"standard", "mobile", "border_area", "consular"},
    "request_type_detail": {"birth_only", "multi_civil_status"},
    "residence_goal": {
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
    },
    "residence_place_type": {"owned_home", "rented_borrowed_stayed", "vehicle_dwelling"},
    "need_precondition_confirmation": {"need_confirmation", "ready_for_main_registration"},
    "registration_status": {"new", "already_registered", "not_eligible"},
}


def _sanitize_slot_updates(domain_key: str | None, updates: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(updates, dict):
        return {}
    if domain_key not in {"birth_registration", "residence_management"}:
        sanitized_generic: dict[str, Any] = {}
        for key in ("subdomain_key", "operation_key"):
            value = updates.get(key)
            if isinstance(value, str) and value.strip():
                sanitized_generic[key] = value.strip()
        return sanitized_generic
    allowed_slots = {
        "birth_registration": {
            "request_type",
            "birth_location",
            "has_foreign_element",
            "combined_parent_recognition",
            "wants_linked_bundle",
            "service_channel",
            "request_type_detail",
        },
        "residence_management": {
            "residence_goal",
            "residence_place_type",
            "need_precondition_confirmation",
            "registration_status",
        },
    }[domain_key]
    sanitized: dict[str, Any] = {}
    for key, value in updates.items():
        if key not in allowed_slots:
            continue
        if not isinstance(value, str):
            continue
        if value in ALLOWED_SLOT_VALUES.get(key, set()):
            sanitized[key] = value
    return sanitized


def _strip_route_level_updates(domain_key: str | None, updates: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(updates, dict):
        return {}
    if domain_key in {"birth_registration", "residence_management"}:
        return dict(updates)
    return {
        key: value
        for key, value in updates.items()
        if key not in {"operation_key", "operation_group"} and not key.startswith("procedure_")
    }


def _should_defer_route_resolution(domain_key: str | None, message: str) -> bool:
    if domain_key in {None, "", "birth_registration", "residence_management"}:
        return False
    if _detect_interaction_mode(message) == "explain_first":
        return True
    if domain_key == "co_con_nho" and _is_generic_newborn_life_event(message):
        return True
    return False


def _entry_confidence(entry: dict[str, Any] | None) -> float:
    if not isinstance(entry, dict):
        return 0.0
    try:
        return float(entry.get("confidence", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _entry_has_domain(entry: dict[str, Any] | None) -> bool:
    return isinstance(entry, dict) and entry.get("domain_key") not in {None, "", "unknown"}


def _entry_is_better(candidate: dict[str, Any] | None, baseline: dict[str, Any] | None) -> bool:
    if not _entry_has_domain(candidate):
        return False
    if not _entry_has_domain(baseline):
        return True
    candidate_score = _entry_confidence(candidate)
    baseline_score = _entry_confidence(baseline)
    candidate_slots = len((candidate or {}).get("slot_updates") or {})
    baseline_slots = len((baseline or {}).get("slot_updates") or {})
    return (candidate_score, candidate_slots) > (baseline_score, baseline_slots)


def _should_keep_legacy_entry(
    message: str,
    baseline: dict[str, Any] | None,
    candidate: dict[str, Any] | None,
) -> bool:
    baseline_domain = (baseline or {}).get("domain_key")
    candidate_domain = (candidate or {}).get("domain_key")
    if baseline_domain not in {"birth_registration", "residence_management"}:
        return False
    if candidate_domain in {None, baseline_domain}:
        return False
    if _entry_confidence(candidate) >= _entry_confidence(baseline) + 0.12:
        return False
    if _is_generic_newborn_life_event(message):
        return False
    return True


def _should_lock_legacy_first_turn(message: str, entry: dict[str, Any] | None) -> bool:
    domain_key = (entry or {}).get("domain_key")
    if domain_key not in {"birth_registration", "residence_management"}:
        return False
    if _is_generic_newborn_life_event(message):
        return False
    return True


def _is_generic_newborn_life_event(message: str) -> bool:
    text = _normalize(message)
    if not _contains_any(text, ["moi sinh con", "vua sinh con", "moi de con", "moi sinh be", "vua sinh be"]):
        return False
    if _contains_any(
        text,
        [
            "khai sinh",
            "giay khai sinh",
            "bao hiem",
            "bhyt",
            "thuong tru",
            "tam tru",
            "trich luc",
            "dang ky",
        ],
    ):
        return False
    return True


def _merge_entry(primary: dict[str, Any] | None, fallback: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(primary, dict):
        return fallback
    merged = dict(primary)
    primary_slots = dict(primary.get("slot_updates") or {})
    fallback_slots = dict((fallback or {}).get("slot_updates") or {})
    if primary.get("domain_key") == (fallback or {}).get("domain_key"):
        for key, value in fallback_slots.items():
            primary_slots.setdefault(key, value)
    merged["slot_updates"] = primary_slots
    return merged


def _apply_entry_heuristic_hints(message: str, entry: dict[str, Any]) -> dict[str, Any]:
    updated = dict(entry)
    updated.setdefault("slot_updates", {})
    text = _normalize(message)
    slot_updates = dict(updated.get("slot_updates") or {})
    if _contains_any(text, ["bao hiem", "bhyt"]) and _contains_any(text, ["con", "tre", "em be", "so sinh", "moi sinh"]):
        updated["domain_key"] = "co_con_nho" if updated.get("domain_key") == "co_con_nho" else "birth_registration"
        updated["confidence"] = max(_entry_confidence(updated), 0.84)
        if updated["domain_key"] == "co_con_nho":
            slot_updates.setdefault("subdomain_key", "bao_hiem_y_te")
        else:
            slot_updates.setdefault("request_type", "new_registration")
            slot_updates.setdefault("wants_linked_bundle", "bhyt_only")
    updated["slot_updates"] = slot_updates
    return updated


def _heuristic_entry_analysis(user_message: str) -> dict[str, Any]:
    domain_key = None
    text = _normalize(user_message)
    interaction_mode = _detect_interaction_mode(user_message)
    if user_message in {"birth_registration", "residence_management"}:
        domain_key = user_message
    elif _contains_any(
        text,
        [
            "khai sinh",
            "giay khai sinh",
            "sinh con",
            "be sinh",
            "trich luc khai sinh",
            "vua sinh em be",
            "moi sinh em be",
            "em be moi sinh",
            "tre so sinh",
            "dang ky lai khai sinh",
            "ghi vao so ho tich",
            "ghi vao so",
            "da co giay to ca nhan",
            "khai sinh luu dong",
        ],
    ):
        domain_key = "birth_registration"
    elif _contains_any(
        text,
        [
            "tam tru",
            "thuong tru",
            "tam vang",
            "luu tru",
            "cu tru",
            "ho khau",
            "o thue",
            "o nho",
            "tach ho",
            "xoa dang ky",
            "gia han",
            "o tam",
        ],
    ):
        domain_key = "residence_management"
    return {
        "domain_key": domain_key or "unknown",
        "confidence": 0.8 if domain_key else 0.2,
        "slot_updates": (
            {}
            if interaction_mode == "explain_first"
            else _heuristic_parse(domain_key, user_message).get("slot_updates", {})
        )
        if domain_key
        else {},
    }


def _maybe_switch_domain(session: WorkflowSession, entry: dict[str, Any]) -> bool:
    next_domain = entry.get("domain_key")
    if not next_domain:
        return False
    if session.domain_key in (None, next_domain):
        return False

    confidence = float(entry.get("confidence", 0))
    slot_updates = entry.get("slot_updates") or {}
    if confidence < 0.7 and not slot_updates:
        return False

    session.domain_key = next_domain
    session.current_node_id = None
    session.asked_node_ids = []
    session.slots = {}
    session.completed_route_id = None
    if slot_updates:
        _apply_updates(session, dict(slot_updates))
    return True


def _workflow_domain_labels() -> dict[str, str]:
    labels = {
        "birth_registration": "Khai sinh",
        "residence_management": "Cư trú",
    }
    groups_path = CATALOG_ROOT / "citizen_groups.json"
    if not groups_path.exists():
        return labels
    payload = _read_json(groups_path)
    for item in payload.get("groups", []):
        if isinstance(item, dict) and item.get("key") and item.get("label"):
            labels[str(item["key"])] = str(item["label"])
    return labels


def _subdomain_labels(config: dict[str, Any]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for item in config.get("subdomain_catalog", []):
        if isinstance(item, dict) and item.get("subdomain_key") and item.get("subdomain_label"):
            labels[str(item["subdomain_key"])] = str(item["subdomain_label"])
    return labels


def _taxonomy_payload(domains: dict[str, DomainBundle]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for domain_key, domain in sorted(domains.items()):
        subdomains = [
            {"subdomain_key": subdomain_key, "subdomain_label": subdomain_label}
            for subdomain_key, subdomain_label in _subdomain_labels(domain.config).items()
        ]
        payload.append(
            {
                "domain_key": domain_key,
                "domain_label": domain.label,
                "subdomains": subdomains,
            }
        )
    return payload


def _domain_selection_replies(domains: dict[str, DomainBundle]) -> list[dict[str, str]]:
    replies: list[dict[str, str]] = []
    for domain_key, domain in sorted(domains.items()):
        replies.append({"value": domain_key, "label": domain.label})
    return replies


def _best_matching_domain_subdomain(domains: dict[str, DomainBundle], user_message: str) -> dict[str, Any] | None:
    text = _normalize(user_message)
    if not text:
        return None
    direct_domain_hints = [
        (
            "huu_tri",
            ["nghi huu", "huu tri", "luong huu", "che do huu", "benh nghe nghiep"],
            {"subdomain_key": "che_do_huu_tri"},
            0.95,
        ),
        (
            "hon_nhan_gia_dinh",
            ["giam ho"],
            {"subdomain_key": "giam_ho"},
            0.96,
        ),
        (
            "hon_nhan_gia_dinh",
            ["ket hon"],
            {"subdomain_key": "ket_hon"},
            0.95,
        ),
        (
            "hon_nhan_gia_dinh",
            ["nhan con nuoi", "nuoi con nuoi"],
            {"subdomain_key": "nhan_con_nuoi"},
            0.95,
        ),
        (
            "hon_nhan_gia_dinh",
            ["nhan cha me con"],
            {"subdomain_key": "nhan_cha_me_con"},
            0.95,
        ),
        (
            "hon_nhan_gia_dinh",
            ["ghi vao so ho tich", "trich luc ho tich", "cai chinh ho tich"],
            {"subdomain_key": "cai_chinh_trich_luc_ho_tich"},
            0.95,
        ),
        (
            "hoc_tap",
            ["hoc sinh nguoi nuoc ngoai", "tiep nhan hoc sinh", "chuyen truong"],
            {"subdomain_key": "chuyen_truong"},
            0.96,
        ),
        (
            "hoc_tap",
            ["hoc bong", "ho tro chi phi hoc tap", "mien giam hoc phi", "ban tru"],
            {"subdomain_key": "hoc_bong_va_ho_tro"},
            0.95,
        ),
        (
            "hoc_tap",
            ["van bang", "chung chi", "cong nhan van bang"],
            {"subdomain_key": "van_bang_chung_chi"},
            0.95,
        ),
        (
            "hoc_tap",
            ["hoc nuoc ngoai", "du hoc", "ngan sach nha nuoc", "cu di hoc"],
            {"subdomain_key": "hoc_tap_o_nuoc_ngoai_bang_ngan_sach"},
            0.95,
        ),
        (
            "hoc_tap",
            ["tuyen sinh", "du thi", "phuc khao", "xet tuyen"],
            {"subdomain_key": "tuyen_sinh"},
            0.95,
        ),
        (
            "viec_lam",
            ["that nghiep", "tro cap that nghiep"],
            {"subdomain_key": "bao_hiem_xa_hoi_that_nghiep_tro_cap"},
            0.96,
        ),
        (
            "viec_lam",
            ["ho tro tien ve xe", "tu van", "gioi thieu viec lam", "di lam viec ngoai tinh"],
            {"subdomain_key": "ho_tro_tu_van_gioi_thieu_viec_lam"},
            0.96,
        ),
        (
            "viec_lam",
            ["giay phep lao dong", "trong ky nghi", "nguoi nuoc ngoai lam viec", "mien giay phep lao dong"],
            {"subdomain_key": "cap_phep_lao_dong_nguoi_nuoc_ngoai"},
            0.96,
        ),
        (
            "viec_lam",
            ["chung chi ky nang", "ky nang nghe"],
            {"subdomain_key": "chung_chi_hanh_nghe"},
            0.95,
        ),
        (
            "viec_lam",
            ["dang ky lao dong", "dieu chinh thong tin dang ky lao dong"],
            {"subdomain_key": "tuyen_dung"},
            0.95,
        ),
        (
            "phuong_tien_nguoi_lai",
            ["bang lai", "giay phep lai xe", "sat hach lai xe"],
            {"subdomain_key": "giay_phep_lai_xe"},
            0.96,
        ),
        (
            "phuong_tien_nguoi_lai",
            ["dang ky xe", "bien so xe", "chung nhan dang ky xe"],
            {"subdomain_key": "dang_ky_phuong_tien"},
            0.96,
        ),
        (
            "phuong_tien_nguoi_lai",
            ["dang kiem", "kiem dinh", "khi thai", "an ninh tau bien", "lao dong hang hai", "xe co gioi", "xe may chuyen dung"],
            {"subdomain_key": "dang_kiem_phuong_tien"},
            0.95,
        ),
        (
            "dien_luc_nha_o_dat_dai",
            ["so do", "giay chung nhan", "quyen su dung dat", "cap dien", "nha o", "dat dai"],
            {},
            0.93,
        ),
    ]
    for domain_key, phrases, slot_updates, confidence in direct_domain_hints:
        if domain_key in domains and _contains_any(text, phrases):
            return {
                "domain_key": domain_key,
                "confidence": confidence,
                "slot_updates": dict(slot_updates),
            }
    if (
        "co_con_nho" in domains
        and _contains_any(text, ["trich luc khai sinh", "ban sao khai sinh", "ban sao giay khai sinh"])
    ):
        return {
            "domain_key": "co_con_nho",
            "confidence": 0.94,
            "slot_updates": {"subdomain_key": "khai_sinh"},
        }
    if (
        "nguoi_than_qua_doi" in domains
        and _contains_any(text, ["khai tu", "giay khai tu", "mai tang", "tu tuat", "nguoi than qua doi"])
    ):
        slot_updates = {"subdomain_key": "khai_tu"} if _contains_any(text, ["khai tu", "giay khai tu"]) else {}
        return {
            "domain_key": "nguoi_than_qua_doi",
            "confidence": 0.95,
            "slot_updates": slot_updates,
        }
    if (
        "co_con_nho" in domains
        and _contains_any(text, ["bao hiem", "bhyt"])
        and _contains_any(text, ["con", "tre", "em be", "so sinh", "moi sinh"])
    ):
        return {
            "domain_key": "co_con_nho",
            "confidence": 0.91,
            "slot_updates": {"subdomain_key": "bao_hiem_y_te"},
        }
    if (
        "co_con_nho" in domains
        and _contains_any(text, ["moi sinh con", "vua sinh con", "moi de con", "moi sinh be", "vua sinh be"])
    ):
        return {
            "domain_key": "co_con_nho",
            "confidence": 0.93,
            "slot_updates": {"subdomain_key": "khai_sinh"},
        }
    complaint_like = _contains_any(text, ["khieu nai", "khieu kien", "to cao", "phan anh", "tranh chap"])
    best_domain_key: str | None = None
    best_subdomain_key: str | None = None
    best_score = 0.0
    for domain_key, domain in domains.items():
        domain_text = _normalize(f"{domain.label} {domain_key.replace('_', ' ')}")
        domain_score = 0.0
        if complaint_like and domain_key == "giai_quyet_khieu_kien":
            domain_score += 4.0
        if any(phrase in text for phrase in _meaningful_phrases(domain_text)):
            domain_score += 1.5
        if any(token in text for token in re.split(r"\s+", domain_text) if len(token) >= 4):
            domain_score += 1.0

        best_domain_route_score = 0.0
        best_domain_route: dict[str, Any] | None = None
        for route in domain.config["decision_tree"]["routes"]:
            route_score = _route_match_score(route, text)
            if route_score > best_domain_route_score:
                best_domain_route_score = route_score
                best_domain_route = route

        best_subdomain_score = 0.0
        candidate_subdomain_key: str | None = None
        for subdomain_key, subdomain_label in _subdomain_labels(domain.config).items():
            subdomain_text = _normalize(f"{subdomain_label} {subdomain_key.replace('_', ' ')}")
            score = 0.0
            if any(phrase in text for phrase in _meaningful_phrases(subdomain_text)):
                score += 2.0
            if any(token in text for token in re.split(r"\s+", subdomain_text) if len(token) >= 4):
                score += 1.0
            route = _best_matching_route(domain, user_message, subdomain_key)
            if route:
                score = max(score, _route_match_score(route, text))
            if score > best_subdomain_score:
                best_subdomain_score = score
                candidate_subdomain_key = subdomain_key

        total_score = max(domain_score, best_domain_route_score, best_subdomain_score)
        if total_score > best_score:
            best_score = total_score
            best_domain_key = domain_key
            if best_subdomain_score >= max(2.0, best_domain_route_score - 0.5):
                best_subdomain_key = candidate_subdomain_key
            else:
                best_subdomain_key = (
                    str((best_domain_route or {}).get("conditions", {}).get("subdomain_key"))
                    if (best_domain_route or {}).get("conditions", {}).get("subdomain_key")
                    else None
                )

    if best_domain_key is None or best_score < 2.0:
        return None
    slot_updates: dict[str, Any] = {}
    if best_subdomain_key:
        slot_updates["subdomain_key"] = best_subdomain_key
    return {
        "domain_key": best_domain_key,
        "confidence": min(0.92, 0.58 + best_score * 0.08),
        "slot_updates": slot_updates,
    }


def _best_matching_route(domain: DomainBundle, user_message: str, subdomain_key: str) -> dict[str, Any] | None:
    text = _normalize(user_message)
    message_tokens = {token for token in re.split(r"\s+", text) if len(token) >= 3}
    best_score = 0
    best_route: dict[str, Any] | None = None
    for route in domain.config["decision_tree"]["routes"]:
        conditions = route.get("conditions") or {}
        if conditions.get("subdomain_key") != subdomain_key:
            continue
        route_text = _normalize(
            f"{route.get('procedure_name', '')} {str(conditions.get('operation_key') or '').replace('_', ' ')}"
        )
        route_tokens = {token for token in re.split(r"\s+", route_text) if len(token) >= 3}
        overlap = len(message_tokens & route_tokens)
        phrase_bonus = 2 if any(phrase in route_text for phrase in _meaningful_phrases(text)) else 0
        score = overlap + phrase_bonus
        if score > best_score:
            best_score = score
            best_route = route
    return best_route if best_score >= 2 else None


def _meaningful_phrases(text: str) -> list[str]:
    words = [word for word in re.split(r"\s+", text) if len(word) >= 3]
    phrases = [" ".join(words[index : index + 2]) for index in range(len(words) - 1)]
    phrases.extend(" ".join(words[index : index + 3]) for index in range(len(words) - 2))
    return phrases


def _action_markers(text: str) -> set[str]:
    markers: set[str] = set()
    if _contains_any(text, ["cap lai", "dang ky lai"]):
        markers.add("reissue")
    if _contains_any(text, ["cap doi", "doi giay phep", "doi chung nhan", "doi bien so", "doi giay"]):
        markers.add("exchange")
    if _contains_any(text, ["gia han"]):
        markers.add("renew")
    if _contains_any(text, ["dieu chinh", "cap nhat thong tin"]):
        markers.add("adjust")
    if _contains_any(text, ["thi", "sat hach", "lan dau"]):
        markers.add("exam")
    if _contains_any(text, ["ho tro", "tro cap", "tu van", "gioi thieu viec lam"]):
        markers.add("support")
    if _contains_any(text, ["dang ky"]):
        markers.add("register")
    if _contains_any(text, ["tiep nhan"]):
        markers.add("receive")
    if _contains_any(text, ["khieu nai"]):
        markers.add("complaint")
    if _contains_any(text, ["giam sat"]):
        markers.add("supervision")
    if _contains_any(text, ["giam ho"]):
        markers.add("guardianship")
    if not markers.intersection({"reissue", "exchange"}):
        if _contains_any(text, ["cap moi", "cap giay phep", "cap giay chung nhan", "duoc cap", "cap the"]):
            markers.add("issue")
    return markers


def _country_markers(text: str) -> set[str]:
    countries: dict[str, list[str]] = {
        "new_zealand": ["niu di lan", "new zealand"],
        "australia": ["o xto ray lia", "uc", "australia"],
        "korea": ["han quoc", "korea"],
        "china": ["trung quoc", "china"],
    }
    matched = set()
    for key, phrases in countries.items():
        if _contains_any(text, phrases):
            matched.add(key)
    return matched


def _route_match_score(route: dict[str, Any], normalized_message: str) -> float:
    route_text = _normalize(
        f"{route.get('procedure_name', '')} "
        f"{str((route.get('conditions') or {}).get('operation_key') or '').replace('_', ' ')}"
    )
    route_tokens = {token for token in re.split(r"\s+", route_text) if len(token) >= 3}
    message_tokens = {token for token in re.split(r"\s+", normalized_message) if len(token) >= 3}
    overlap = len(route_tokens & message_tokens)
    phrase_bonus = sum(1 for phrase in _meaningful_phrases(normalized_message) if phrase in route_text)
    exact_phrase_bonus = 4 if normalized_message in route_text else 0
    message_actions = _action_markers(normalized_message)
    route_actions = _action_markers(route_text)
    action_bonus = len(message_actions & route_actions) * 3
    conflicting_actions = {
        ("issue", "reissue"),
        ("issue", "exchange"),
        ("reissue", "exchange"),
        ("adjust", "support"),
        ("support", "register"),
        ("complaint", "register"),
        ("exam", "exchange"),
    }
    action_penalty = 0
    for left, right in conflicting_actions:
        if left in message_actions and right in route_actions:
            action_penalty += 3
        if right in message_actions and left in route_actions:
            action_penalty += 3
    message_countries = _country_markers(normalized_message)
    route_countries = _country_markers(route_text)
    country_bonus = len(message_countries & route_countries) * 2
    if message_countries and route_countries and not (message_countries & route_countries):
        action_penalty += 2
    return float(overlap + phrase_bonus + exact_phrase_bonus + action_bonus + country_bonus - action_penalty)


def _procedure_payload_from_route(route: dict[str, Any]) -> dict[str, Any] | None:
    procedure_code = str(route.get("procedure_code") or "").strip()
    procedure_title = str(route.get("procedure_name") or route.get("procedure_title") or "").strip()
    source_url = str(route.get("source_url") or "").strip()
    if not procedure_code and not procedure_title:
        return None
    return {
        "id": procedure_code or _normalize_key(procedure_title),
        "code": procedure_code,
        "title": procedure_title or procedure_code,
        "source_url": source_url,
        "detail_level": "workflow_index",
    }


def _update_interaction_mode(session: WorkflowSession, user_message: str) -> None:
    detected = _detect_interaction_mode(user_message)
    if detected == "fast_track":
        session.interaction_mode = "fast_track"
    elif detected == "explain_first" and not session.slots:
        session.interaction_mode = "explain_first"


def _detect_interaction_mode(user_message: str) -> str:
    text = _normalize(user_message)
    if _contains_any(
        text,
        [
            "toi biet roi",
            "di nhanh",
            "chot luon",
            "toi muon dang ky",
            "toi muon xoa",
            "toi muon gia han",
            "toi muon xin",
            "toi can dang ky",
            "toi can khai bao",
        ],
    ):
        return "fast_track"
    if _contains_any(
        text,
        [
            "khong biet",
            "chua biet",
            "khong hieu",
            "giai thich",
            "la gi",
            "khac nhau the nao",
            "nen lam gi",
            "toi nen",
        ],
    ):
        return "explain_first"
    return "fast_track"


def _build_domain_selection_message(session: WorkflowSession) -> str:
    if session.interaction_mode == "explain_first":
        return (
            "Mình có thể giải thích rất ngắn trước rồi mới chọn đúng thủ tục.\n"
            "Bạn đang muốn tìm hiểu nhóm nào để mình định hướng nhanh hơn?"
        )
    return "Mình đang hỗ trợ nhiều nhóm thủ tục. Bạn muốn bắt đầu với nhóm nào?"


def _maybe_build_explain_mode_payload(
    domain: DomainBundle,
    session: WorkflowSession,
    message: str,
) -> dict[str, Any] | None:
    if session.interaction_mode != "explain_first":
        return None
    if session.completed_route_id or session.slots:
        return None

    text = _normalize(message)
    if domain.key == "residence_management" and _is_residence_explanatory_request(text):
        session.current_node_id = "residence_goal"
        if session.current_node_id not in session.asked_node_ids:
            session.asked_node_ids.append(session.current_node_id)
        return {
            "question": (
                "Mình giải thích rất ngắn trước nhé:\n"
                "- Thường trú: ở ổn định lâu dài tại địa chỉ đó.\n"
                "- Tạm trú: ở tạm tại nơi bạn đang sống nhưng chưa phải nơi ở lâu dài.\n"
                "- Tạm vắng: báo là bạn sẽ vắng khỏi nơi ở hiện tại một thời gian.\n"
                "Giờ mình chọn giúp theo nhu cầu thực tế nhé:\n"
                "Bạn đang muốn ở lâu dài, ở tạm, hay chỉ cần báo vắng?"
            ),
            "quick_replies": [
                {
                    "value": "register_permanent",
                    "label": "Ở lâu dài",
                    "description": "Thường trú tại địa chỉ đó.",
                },
                {
                    "value": "register_temporary",
                    "label": "Ở tạm",
                    "description": "Tạm trú tại nơi đang sống.",
                },
                {
                    "value": "absence_notice",
                    "label": "Báo vắng",
                    "description": "Khai báo tạm vắng trong một thời gian.",
                },
            ],
            "confidence": 0.74,
        }
    if domain.key == "birth_registration" and _is_birth_explanatory_request(text):
        session.current_node_id = "birth_request_type"
        if session.current_node_id not in session.asked_node_ids:
            session.asked_node_ids.append(session.current_node_id)
        return {
            "question": (
                "Mình gợi ý rất ngắn trước nhé:\n"
                "- Khai sinh mới: làm giấy khai sinh lần đầu cho bé.\n"
                "- Đăng ký lại: đã có khai sinh trước đây nhưng mất hoặc thiếu bản chính hợp lệ.\n"
                "- Bản sao hoặc trích lục: xin lại thông tin đã đăng ký trước đó.\n"
                "Nếu bé mới sinh thì thường bắt đầu từ khai sinh mới.\n"
                "Bạn muốn mình đi tiếp theo hướng nào?"
            ),
            "quick_replies": [
                {
                    "value": "new_registration",
                    "label": "Khai sinh mới",
                    "description": "Làm giấy khai sinh lần đầu cho bé.",
                },
                {
                    "value": "re_registration",
                    "label": "Đăng ký lại",
                    "description": "Làm lại khi đã mất hoặc thiếu bản chính hợp lệ.",
                },
                {
                    "value": "copy_extract",
                    "label": "Xin bản sao",
                    "description": "Xin bản sao hoặc trích lục hộ tịch.",
                },
            ],
            "confidence": 0.74,
        }
    return None


def _is_residence_explanatory_request(text: str) -> bool:
    return (
        _contains_any(text, ["thuong tru", "tam tru", "tam vang", "cu tru"])
        and _contains_any(text, ["la gi", "khac nhau the nao", "giai thich", "khong hieu", "khong biet"])
    )


def _is_birth_explanatory_request(text: str) -> bool:
    return _contains_any(text, ["khai sinh", "em be moi sinh", "vua sinh em be", "tre so sinh"]) and _contains_any(
        text,
        ["la gi", "giai thich", "khong biet", "nen lam gi"],
    )


def _contains_exact_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


def _contains_any_exact_phrase(text: str, phrases: list[str]) -> bool:
    return any(_contains_exact_phrase(text, phrase) for phrase in phrases)


def _heuristic_parse(domain_key: str | None, user_message: str, expected_slot: str | None = None) -> dict[str, Any]:
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

    expected_alias_map = {
        "birth_location": {
            "trong nuoc": "domestic",
            "o nuoc ngoai": "abroad",
            "nuoc ngoai": "abroad",
        },
        "has_foreign_element": {
            "co": "yes",
            "khong": "no",
            "yes": "yes",
            "no": "no",
        },
        "combined_parent_recognition": {
            "co": "yes",
            "khong": "no",
            "yes": "yes",
            "no": "no",
            "co nhan cha me con": "yes",
            "khong nhan cha me con": "no",
        },
        "service_channel": {
            "co quan dai dien": "consular",
            "lanh su": "consular",
            "dai su quan": "consular",
            "khu vuc bien gioi": "border_area",
            "bien gioi": "border_area",
            "thong thuong": "standard",
            "binh thuong": "standard",
            "luu dong": "mobile",
        },
        "request_type_detail": {
            "khai sinh": "birth_only",
            "chi khai sinh": "birth_only",
            "giay khai sinh": "birth_only",
            "viec ho tich khac": "multi_civil_status",
            "ho tich khac": "multi_civil_status",
            "viec khac": "multi_civil_status",
            "nhom khac": "multi_civil_status",
        },
        "need_precondition_confirmation": {
            "can xin xac nhan truoc": "need_confirmation",
            "can xac nhan truoc": "need_confirmation",
            "da du dieu kien roi": "ready_for_main_registration",
            "san sang nop ho so": "ready_for_main_registration",
        },
        "residence_place_type": {
            "nha thue": "rented_borrowed_stayed",
            "o nho": "rented_borrowed_stayed",
            "muon nha": "rented_borrowed_stayed",
            "xe de o": "vehicle_dwelling",
            "phuong tien": "vehicle_dwelling",
        },
    }

    if expected_slot and text in direct_slot_map.get(expected_slot, {}):
        updates[expected_slot] = direct_slot_map[expected_slot][text]
        return {
            "slot_updates": updates,
            "confidence": 0.99,
            "needs_clarification": False,
            "clarification_hint": "",
        }

    if expected_slot and text in expected_alias_map.get(expected_slot, {}):
        updates[expected_slot] = expected_alias_map[expected_slot][text]
        return {
            "slot_updates": updates,
            "confidence": 0.99,
            "needs_clarification": False,
            "clarification_hint": "",
        }

    if domain_key == "birth_registration":
        if _is_birth_explanatory_request(text):
            return {
                "slot_updates": updates,
                "confidence": 0.25,
                "needs_clarification": True,
                "clarification_hint": "Mình có thể giải thích ngắn trước rồi mới chọn loại thủ tục khai sinh phù hợp.",
            }

        if _contains_any(text, ["dang ky lai", "mat ban chinh", "mat giay khai sinh", "lam lai khai sinh"]):
            updates["request_type"] = "re_registration"
        elif _contains_any(text, ["trich luc", "ban sao giay khai sinh", "xin ban sao"]):
            updates["request_type"] = "copy_extract"
        elif "nuoc ngoai" in text and _contains_any(text, ["ghi vao so", "ghi so ho tich", "ghi vao so ho tich"]):
            updates["request_type"] = "foreign_record_note"
        elif _contains_any(text, ["da co ho so", "da co giay to ca nhan"]):
            updates["request_type"] = "existing_personal_documents"
        elif "luu dong" in text:
            updates["request_type"] = "mobile_service"
        elif _contains_any(
            text,
            [
                "khai sinh moi",
                "lam khai sinh",
                "sinh con",
                "giay khai sinh cho con",
                "khai sinh cho be",
                "dang ky khai sinh lan dau",
            ],
        ):
            updates["request_type"] = "new_registration"

        if _contains_any(
            text,
            [
                "sinh o nuoc ngoai",
                "sinh ben nhat",
                "sinh ben han",
                "sinh ben my",
                "sinh o nhat",
                "sinh o han",
                "sinh o my",
                "tai nuoc ngoai",
                "de o nuoc ngoai",
                "co quan dai dien viet nam",
            ],
        ):
            updates["birth_location"] = "abroad"
        elif _contains_any(text, ["trong nuoc", "sinh o viet nam", "benh vien", "sinh trong nuoc"]):
            updates["birth_location"] = "domestic"

        if _contains_any(text, ["khong co yeu to nuoc ngoai", "khong yeu to nuoc ngoai", "bo me deu la nguoi viet"]):
            updates["has_foreign_element"] = "no"
        elif _contains_any(
            text,
            [
                "co yeu to nuoc ngoai",
                "yeu to nuoc ngoai",
                "nguoi nuoc ngoai",
                "bo la nguoi",
                "me la nguoi",
                "quoc tich han",
                "quoc tich nhat",
                "quoc tich my",
            ],
        ):
            updates["has_foreign_element"] = "yes"

        if _contains_any(
            text,
            [
                "khong can nhan cha",
                "khong can nhan me",
                "khong lam nhan cha me con",
                "khong nhan cha me con",
                "chi khai sinh",
            ],
        ):
            updates["combined_parent_recognition"] = "no"
        elif _contains_any(text, ["nhan cha", "nhan me", "nhan cha me con", "ket hop nhan cha", "ket hop nhan me"]):
            updates["combined_parent_recognition"] = "yes"

        if "bao hiem" in text and "thuong tru" in text:
            updates["wants_linked_bundle"] = "bhyt_and_residence"
        elif _contains_any(text, ["khong lien thong", "chi khai sinh thoi", "khong can bao hiem"]):
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

        if _contains_any(text, ["ho tich khac", "giam ho", "nuoi con nuoi"]):
            updates["request_type_detail"] = "multi_civil_status"
        elif _contains_any(text, ["khai sinh", "giay khai sinh"]):
            updates["request_type_detail"] = "birth_only"

    if domain_key == "residence_management":
        if _is_residence_explanatory_request(text):
            return {
                "slot_updates": updates,
                "confidence": 0.25,
                "needs_clarification": True,
                "clarification_hint": "Mình có thể giải thích rất ngắn trước rồi mới chọn thủ tục phù hợp.",
            }

        wants_preconfirmation = _contains_any(
            text,
            ["xin xac nhan truoc", "can xin xac nhan", "can xac nhan", "dieu kien nha o", "giay xac nhan dieu kien"],
        )

        if wants_preconfirmation:
            updates["need_precondition_confirmation"] = "need_confirmation"

        if (
            not _contains_any_exact_phrase(text, ["xoa dang ky thuong tru", "xoa thuong tru"])
            and _contains_any_exact_phrase(text, ["dang ky thuong tru", "nhap ho khau", "o lau dai", "thuong tru"])
        ):
            updates["residence_goal"] = "register_permanent"

        if "gia han" in text and "khong phai gia han" not in text and _contains_any(text, ["tam tru", "da co tam tru"]):
            updates["residence_goal"] = "extend_temporary"

        ordered_mapping = [
            ("delete_permanent", ["xoa dang ky thuong tru", "xoa thuong tru"]),
            ("delete_temporary", ["xoa dang ky tam tru", "xoa tam tru"]),
            ("extend_temporary", ["gia han tam tru", "gia han tam"]),
            ("absence_notice", ["khai bao tam vang", "tam vang"]),
            ("lodging_notice", ["thong bao luu tru", "luu tru"]),
            ("residence_confirmation", ["xac nhan thong tin cu tru", "xin xac nhan cu tru", "giay xac nhan cu tru"]),
            ("split_household", ["tach ho"]),
            ("adjust_data", ["dieu chinh thong tin cu tru", "sua thong tin cu tru", "cap nhat thong tin cu tru"]),
            ("fallback_info_declaration", ["chua du dieu kien", "khai bao thong tin cu tru"]),
            ("register_temporary", ["dang ky tam tru", "o tam", "tam tru"]),
        ]
        if updates.get("residence_goal") is None:
            for key, phrases in ordered_mapping:
                if _contains_any_exact_phrase(text, phrases):
                    updates["residence_goal"] = key
                    break
        if updates.get("residence_goal") is None and wants_preconfirmation:
            updates["residence_goal"] = "eligibility_confirmation"
        if updates.get("residence_goal") is None and _contains_any(text, ["dang ky o tam", "o tam tai", "o tam o"]):
            updates["residence_goal"] = "register_temporary"

        if _contains_any(text, ["thue nha", "nha thue", "o nho", "muon nha", "o muon", "cho o thue", "dang o thue"]):
            updates["residence_place_type"] = "rented_borrowed_stayed"
        elif _contains_any(text, ["phuong tien", "xe de o", "song tren xe", "tau thuyen de o"]):
            updates["residence_place_type"] = "vehicle_dwelling"
        elif _contains_any(text, ["nha cua toi", "nha minh", "so huu", "co so do"]):
            updates["residence_place_type"] = "owned_home"

        if _contains_any(text, ["nop ho so", "dang ky luon", "san sang nop", "du dieu kien roi"]):
            updates["need_precondition_confirmation"] = "ready_for_main_registration"

        if "chua du dieu kien" in text:
            updates["registration_status"] = "not_eligible"
        elif _contains_any(text, ["da dang ky", "da co tam tru", "da co thuong tru"]):
            updates["registration_status"] = "already_registered"
        elif _contains_any(text, ["lan dau", "chua dang ky", "dang ky moi"]):
            updates["registration_status"] = "new"

    confidence = 0.72 if updates else 0.2
    return {
        "slot_updates": updates,
        "confidence": confidence,
        "needs_clarification": not bool(updates),
        "clarification_hint": "Mình chưa map chắc vào nhánh workflow. Bạn có thể bấm một lựa chọn gợi ý bên dưới hoặc trả lời ngắn gọn hơn nhé.",
    }
