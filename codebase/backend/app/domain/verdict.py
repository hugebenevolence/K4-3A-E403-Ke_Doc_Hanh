"""Kết quả chấm lời giải thích của học viên.

Thuần domain: không import SDK nào, để test được mà không cần API key.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Verdict(str, Enum):
    """Định danh tiếng Anh cho đồng nhất với TurnState và khoá JSON; phần văn
    xuôi hướng dẫn model vẫn là tiếng Việt."""

    SUFFICIENT = "sufficient"  # đủ đúng, bằng lời học viên → agent "hiểu", kết phiên
    INCOMPLETE = "incomplete"  # đúng hướng nhưng thiếu/mơ hồ → hỏi ngược đúng chỗ hổng
    INCORRECT = "incorrect"  # có phần trái nguồn → hỏi gợi mở, không sửa hộ


@dataclass(frozen=True)
class Evidence:
    """Một ý trong nguồn, kèm việc học viên đã nói tới nó hay chưa.

    span_id trỏ về span đã ingest (mã đoạn transcript, hoặc vùng slide sau này),
    nhờ đó frontend highlight lại đúng chỗ khi agent hỏi ngược.
    """

    span_id: str
    quote: str
    covered_by_student: bool


@dataclass(frozen=True)
class GradeResult:
    verdict: Verdict
    evidence: tuple[Evidence, ...]
    gap_summary: str  # chỗ hổng lớn nhất — đầu vào để sinh câu hỏi ngược

    @property
    def uncovered(self) -> tuple[Evidence, ...]:
        return tuple(e for e in self.evidence if not e.covered_by_student)


def decide(
    evidence: tuple[Evidence, ...], contradiction: str, *, verbatim: bool
) -> Verdict:
    """Suy ra verdict từ các nhận định cụ thể của model.

    Cố ý KHÔNG để model tự chốt: đo thực tế cho thấy khi được tự quyết, nó
    không bao giờ trả `sufficient` — viết ra chỗ hổng xong là đã tự cam kết
    "còn thiếu", kể cả khi chính nó ghi "không có chỗ thiếu lớn".

    Thứ tự ưu tiên: nói trái nguồn > đọc lại nguyên văn > còn ý chưa chạm tới.
    """
    if contradiction.strip():
        return Verdict.INCORRECT
    if not evidence:
        # Không trích được ý nào từ nguồn nghĩa là chưa chấm được gì, không
        # phải là học viên đã nói đủ.
        return Verdict.INCOMPLETE
    if verbatim or any(not e.covered_by_student for e in evidence):
        return Verdict.INCOMPLETE
    return Verdict.SUFFICIENT
