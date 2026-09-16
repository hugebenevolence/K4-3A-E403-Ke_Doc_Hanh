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
"""Chuỗi trùng liên tiếp từ ngần này từ trở lên thì khó là trùng hợp ngẫu nhiên.

Đây là tín hiệu ĐÁNG TIN nhất: chép thì trùng dài liền mạch, tự nói thì không.
"""

MIN_WORDS_FOR_RATIO = 25
"""Dưới ngần này từ thì tỉ lệ trùng là nhiễu, không được dùng để kết luận.

Câu ngắn mà đúng thì gần như toàn từ chủ đề lấy từ bài — "áp suất giảm nên nước
sôi ở nhiệt độ thấp hơn" cho ratio 1.00 dù học viên tự nghĩ ra. Áp luật tỉ lệ ở
đây là vu cho người trả lời đúng tội đọc lại sách, đúng thứ tệ nhất hệ thống
này có thể làm.
"""

OVERLAP_RATIO = 0.8
"""Với câu đủ dài, quá ngần này là đang ghép chữ của nguồn chứ không tự diễn đạt."""


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
    if longest >= LONGEST_RUN_WORDS:
        return True
    return (
        len(_words(student_text)) >= MIN_WORDS_FOR_RATIO and ratio >= OVERLAP_RATIO
    )
