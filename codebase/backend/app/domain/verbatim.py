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


QUOTE_RUN_WORDS = 6
"""Ngưỡng cho câu AGENT nói ra, chặt hơn nhiều so với ngưỡng chấm học viên.

Học viên trùng vài từ với bài là bình thường — họ đang nói về đúng chủ đề đó.
Agent thì khác: một câu hỏi mở bài hay hỏi ngược không có lý do gì trùng liền
mạch sáu từ với nguồn, trừ khi nó đang chép lại câu mà học viên phải tự nói.
"""


def quotes_source(agent_text: str, source_text: str) -> bool:
    """Agent có đang trích nguyên văn đoạn nguồn không."""
    _, longest = verbatim_overlap(agent_text, source_text)
    return longest >= QUOTE_RUN_WORDS


def is_verbatim_paste(student_text: str, source_text: str) -> bool:
    ratio, longest = verbatim_overlap(student_text, source_text)
    if longest >= LONGEST_RUN_WORDS:
        return True
    return (
        len(_words(student_text)) >= MIN_WORDS_FOR_RATIO and ratio >= OVERLAP_RATIO
    )


ECHO_RUN_WORDS = 7
"""Agent nhại lại liền mạch ngần này từ của học viên thì không còn là hỏi nữa.

Đo trên 57 lượt của hai lần chạy golden set: câu hỏi ngược bình thường trùng
dài nhất 5 từ (A02 nhắc lại "token là gì và tại sao" trước khi hỏi tiếp), còn
lượt hỏng thì trùng 10 từ — chép nguyên câu học viên vừa nói. Ngưỡng 7 nằm
giữa hai nhóm đó.
"""


def echoes_student(agent_text: str, student_text: str) -> bool:
    """Câu hỏi ngược có đang chép lại chính lời học viên không.

    Quan sát thật (O03): học viên đang giảng thì hỏi chen "link github bài của
    trường đang bị đóng đúng không", và học trò hỏi lại đúng câu đó. Câu lạc đề
    không phải lời giảng nên không có chỗ hổng nào để hỏi vào, model bí và nhại
    lại — nghe như máy vọng tiếng, và tệ hơn là nó biến câu lạc đề thành chủ đề
    của buổi học.
    """
    _, longest = verbatim_overlap(agent_text, student_text)
    return longest >= ECHO_RUN_WORDS
