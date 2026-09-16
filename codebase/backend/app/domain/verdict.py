"""Kết quả chấm lời giải thích của học viên.

Thuần domain: không import SDK nào, để test được mà không cần API key.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Verdict(str, Enum):
    DAY_DUOC = "day_duoc"  # đủ đúng, bằng lời học viên → agent "hiểu", kết phiên
    HO = "ho"  # đúng hướng nhưng thiếu/mơ hồ → hỏi ngược đúng chỗ hổng
    SAI = "sai"  # có phần sai → hỏi gợi mở, không sửa hộ


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
