"""Log phiên — định dạng replay được.

Giữ đủ để dựng lại golden set từ phiên thật thay vì bịa case: mỗi lượt ghi
prompt version + span đã dùng + verdict, nên chạy lại được y hệt sau khi sửa
prompt. Quality bar khoá ở CP4, sau đó không thu thêm được nữa — nên ghi từ đầu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.domain.verdict import GradeResult


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TurnLog:
    session_id: str
    turn_index: int
    student_text: str
    source_span_id: str
    prompt_versions: dict[str, str]  # {"grader": "v1", "talker": "v1", ...}
    grade: GradeResult | None
    agent_said: str
    latency_ms: dict[str, int] = field(default_factory=dict)  # {"talker": 380, "grader": 1420}
    at: str = field(default_factory=_now)


@dataclass
class StudentProfile:
    """Trí nhớ xuyên phiên: học viên đã dạy gì, vấp ở đâu, lặp lại chỗ nào.

    Dùng để agent nhắc được "lần trước bạn cũng dừng ở chỗ này" và để giảng viên
    thấy lớp hổng ở đâu nhiều nhất.
    """

    student_id: str
    concepts_taught: dict[str, str] = field(default_factory=dict)  # concept -> verdict cuối
    recurring_gaps: dict[str, int] = field(default_factory=dict)  # span_id -> số lần vấp

    def absorb(self, concept: str, grade: GradeResult) -> None:
        self.concepts_taught[concept] = grade.verdict.value
        for ev in grade.uncovered:
            self.recurring_gaps[ev.span_id] = self.recurring_gaps.get(ev.span_id, 0) + 1
