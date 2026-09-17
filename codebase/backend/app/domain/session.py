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

        if grade.verdict is Verdict.SUFFICIENT:
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
        """Span nên gợi ý xem lại: Ý CHÍNH học viên chưa chạm tới ở lần chấm cuối.

        Phiên đạt thì rỗng, và chỉ lấy ý chính. Bản trước lấy MỌI ý chưa chạm
        tới nên màn kết tự mâu thuẫn: phiên thật 2e6d52f3 đóng bằng "Học trò đã
        hiểu phần này" mà ngay dưới vẫn hiện thẻ "Cần xem lại · 1" — trỏ vào một
        dòng tiêu đề mà học viên chẳng có gì để nói về nó.

        Không còn ý chính nào thiếu thì rơi về mọi ý chưa chạm tới, để lượt kết
        bằng gợi ý xem lại luôn có chỗ để trỏ tới.
        """
        if not self.grades:
            return ()
        last = self.grades[-1]
        if last.verdict is Verdict.SUFFICIENT:
            # Đã đủ ý chính thì không còn gì BẮT BUỘC phải xem lại. Chi tiết phụ
            # chưa nhắc tới không phải là chỗ hổng — chính `decide()` vừa quyết
            # định như vậy khi đóng phiên.
            return ()
        # Chỗ nói TRÁI cũng phải nằm trong danh sách xem lại, không chỉ chỗ chưa
        # nói tới. Lọc theo mỗi `uncovered` thì đúng ý học viên hiểu sai lại bị
        # bỏ sót — họ có nhắc tới nó, chỉ là nhắc sai — và đó mới là chỗ cần
        # quay lại nhất.
        wrong = tuple(
            e for e in last.evidence if e.contradicted_by_student or not e.covered_by_student
        )
        return tuple(e.span_id for e in wrong if e.key) or tuple(e.span_id for e in wrong)
