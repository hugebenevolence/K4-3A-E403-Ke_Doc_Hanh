"""Phát hiện học viên đọc/chép nguyên văn nguồn thay vì tự diễn đạt.

Đây là một hard test của D3. Làm bằng luật tất định thay vì hỏi LLM: rẻ hơn,
không dao động giữa các lượt chạy, và chấm được ngay cả khi LLM lỗi.
Kết quả dùng để hạ SUFFICIENT xuống INCOMPLETE — không bao giờ để tự nó kết tội học viên.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

LONGEST_RUN_WORDS = 12
"""Chuỗi trùng liên tiếp từ ngần này từ trở lên thì khó là trùng hợp ngẫu nhiên."""

OVERLAP_RATIO = 0.6
"""Quá ngần này tỉ lệ lời học viên là chữ của nguồn thì coi như đang đọc lại."""


def _words(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text).lower()
    return re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE).split()


def verbatim_overlap(student_text: str, source_text: str) -> tuple[float, int]:
    """Trả về (tỉ lệ lời học viên trùng nguồn, số từ của chuỗi trùng dài nhất)."""
    student, source = _words(student_text), _words(source_text)
    if not student:
        return 0.0, 0

    blocks = SequenceMatcher(None, student, source, autojunk=False).get_matching_blocks()
    matched = sum(b.size for b in blocks)
    longest = max((b.size for b in blocks), default=0)
    return matched / len(student), longest


def is_verbatim_paste(student_text: str, source_text: str) -> bool:
    ratio, longest = verbatim_overlap(student_text, source_text)
    return longest >= LONGEST_RUN_WORDS or ratio >= OVERLAP_RATIO
