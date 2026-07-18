from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass


BASE_URL = "http://127.0.0.1:8010"
sys.stdout.reconfigure(encoding="utf-8")


@dataclass
class Scenario:
    name: str
    messages: list[str]
    preferred_mode: str | None = None


def get_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE_URL}{path}") as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def print_payload(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def run_health_check() -> None:
    print_section("HEALTH")
    payload = get_json("/api/health")
    print_payload(payload)


def run_scenario(scenario: Scenario) -> None:
    print_section(scenario.name)
    session_id: str | None = None

    for index, message in enumerate(scenario.messages, start=1):
        request_payload = {
            "message": message,
        }
        if session_id:
            request_payload["session_id"] = session_id
        if scenario.preferred_mode:
            request_payload["preferred_mode"] = scenario.preferred_mode

        response_payload = post_json("/api/chat", request_payload)
        session_id = response_payload["session_id"]

        print(f"\n[{index}] USER: {message}")
        print(f"[{index}] BOT: {response_payload['message']}")
        print(f"[{index}] MODE: {response_payload.get('assist_mode_label')}")
        print(f"[{index}] PERSONA: {response_payload.get('persona_label')}")
        print(f"[{index}] NODE: {response_payload.get('current_node_id')}")
        print(f"[{index}] COMPLETED: {response_payload.get('completed')}")
        print(f"[{index}] SLOTS: {json.dumps(response_payload.get('slots', {}), ensure_ascii=False)}")
        quick_replies = response_payload.get("quick_replies", [])
        if quick_replies:
            labels = [item.get("label", "") for item in quick_replies]
            print(f"[{index}] QUICK REPLIES: {labels}")
        result = response_payload.get("result")
        if result:
            print(
                f"[{index}] RESULT: {result.get('procedure_name')} ({result.get('procedure_code')})"
            )


def main() -> int:
    scenarios = [
        Scenario(
            name="Guided Birth From Situation",
            preferred_mode="guided",
            messages=[
                "Tôi mới sinh con ở bệnh viện, muốn làm giấy khai sinh cho bé",
                "Không có yếu tố nước ngoài",
                "Không cần làm nhận cha mẹ con",
                "Chỉ làm khai sinh thôi",
            ],
        ),
        Scenario(
            name="Fast Residence From Known Procedure",
            preferred_mode="fast_track",
            messages=[
                "Tôi muốn đăng ký tạm trú",
            ],
        ),
        Scenario(
            name="Guided Residence From Real-Life Need",
            preferred_mode="guided",
            messages=[
                "Tôi đang ở thuê và không rõ cần làm gì",
                "Đúng rồi",
                "Không phải",
            ],
        ),
    ]

    try:
        run_health_check()
        for scenario in scenarios:
            run_scenario(scenario)
        return 0
    except urllib.error.URLError as exc:
        print("Không gọi được API. Hãy chắc rằng server đang chạy ở", BASE_URL)
        print("Chi tiết:", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
