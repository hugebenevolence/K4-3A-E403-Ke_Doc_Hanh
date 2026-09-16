"""Máy trạng thái lượt của một phiên dạy-lại.

Ràng buộc thiết kế (xem CLAUDE.md): ngưỡng im lặng phải khác nhau theo state —
học viên là người nói chính, nên chỉ nới ngưỡng chờ khi vừa hỏi ngược
(STUDENT_RESPONDING), vì im lặng lúc đó là đang suy nghĩ chứ không phải hết lượt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from app.domain.verdict import GradeResult, Verdict

MAX_FOLLOWUPS = 3
"""2 lượt hỏi ngược + 1 lượt chốt. Hết mức này thì kết phiên bằng gợi ý xem lại,
không bao giờ bằng cách nói đáp án."""


class TurnState(Enum):
    STUDENT_TEACHING = auto()
    CHECKING = auto()
    ASKING_FOLLOWUP = auto()
    STUDENT_RESPONDING = auto()
    TAUGHT = auto()
    SUGGEST_REVIEW = auto()

    @property
    def is_terminal(self) -> bool:
        return self in (TurnState.TAUGHT, TurnState.SUGGEST_REVIEW)

    @property
    def mic_open(self) -> bool:
        """Frontend chỉ được mở mic ở các state này (và còn phải chờ TTS phát
        xong nữa — xem app.js), để mic không bắt lại chính giọng agent."""
        return self in (TurnState.STUDENT_TEACHING, TurnState.STUDENT_RESPONDING)

    @property
    def silence_tolerance_ms(self) -> int:
        return 6000 if self is TurnState.STUDENT_RESPONDING else 2000


@dataclass
class TeachBackSession:
    """Một phiên = một học viên dạy lại một khái niệm, bám vào một span nguồn."""

    source_span_id: str
    concept: str
    state: TurnState = TurnState.STUDENT_TEACHING
    followups_asked: int = 0
    grades: list[GradeResult] = field(default_factory=list)

    def record(self, grade: GradeResult) -> TurnState:
        """Ghi nhận kết quả chấm và chuyển state. Trả về state mới."""
        self.grades.append(grade)

        if grade.verdict is Verdict.DAY_DUOC:
            self.state = TurnState.TAUGHT
        elif self.followups_asked >= MAX_FOLLOWUPS:
            self.state = TurnState.SUGGEST_REVIEW
        else:
            self.followups_asked += 1
            self.state = TurnState.ASKING_FOLLOWUP

        return self.state

    def followup_delivered(self) -> TurnState:
        """Agent vừa phát xong câu hỏi ngược → tới lượt học viên trả lời."""
        self.state = TurnState.STUDENT_RESPONDING
        return self.state

    @property
    def review_span_ids(self) -> tuple[str, ...]:
        """Span nên gợi ý xem lại: những ý học viên chưa chạm tới ở lần chấm cuối."""
        if not self.grades:
            return ()
        return tuple(e.span_id for e in self.grades[-1].uncovered)
