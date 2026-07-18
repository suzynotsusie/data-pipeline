from __future__ import annotations

import hashlib
import re
from pathlib import Path


def compact_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return re.sub(r"_+", "_", cleaned).strip("_") or "group"


def section_key(title: str) -> str:
    mapping = {
        "Thông tin chung": "thong_tin_chung",
        "Thủ tục hành chính liên quan": "thu_tuc_lien_quan",
        "Trình tự thực hiện": "trinh_tu_thuc_hien",
        "Cách thức thực hiện": "cach_thuc_thuc_hien",
        "Thành phần hồ sơ": "thanh_phan_ho_so",
        "Căn cứ pháp lý": "can_cu_phap_ly",
        "Cơ quan thực hiện": "co_quan_thuc_hien",
        "Yêu cầu, điều kiện thực hiện": "yeu_cau_dieu_kien",
        "Kết quả xử lý": "ket_qua_xu_ly",
        "Từ khóa": "tu_khoa",
        "Mô tả": "mo_ta",
    }
    return mapping.get(title.strip(), slugify(title))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")
