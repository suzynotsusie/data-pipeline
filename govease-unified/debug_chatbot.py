from __future__ import annotations

import json
import sys

from govease_ai import ProcedureAssistant


DEFAULT_QUERIES = [
    "Tôi muốn đăng ký tạm trú",
    "Làm khai sinh cho em bé bị bỏ rơi thì cần chuẩn bị thêm gì?",
    "Tôi mới sinh con ở bệnh viện, muốn làm giấy khai sinh lần đầu cho bé.",
]


def main() -> None:
    assistant = ProcedureAssistant()
    queries = sys.argv[1:] or DEFAULT_QUERIES

    for index, query in enumerate(queries, start=1):
        result = assistant.guided_intake(query)
        print("=" * 100)
        print(f"CASE {index}")
        print(f"QUERY: {query}")
        print("-" * 100)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print()


if __name__ == "__main__":
    main()
