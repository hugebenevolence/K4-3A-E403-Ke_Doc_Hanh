"""Persona 'học trò' — trung tâm quyết định AI của lát cắt D3.

Học viên DẠY một khái niệm cho agent; agent không được lộ đáp án, chỉ hỏi
ngược đúng MỘT chỗ giải thích hổng/mơ hồ/sai (đối chiếu với source_span),
và chỉ đánh dấu "đã dạy được" khi giải thích đủ đúng.

State machine tối thiểu (xem codebase/README.md và hồ sơ research turn-taking):
  STUDENT_TEACHING   -> học viên đang giải thích; im lặng ngắn không hẳn là
                        hết câu (đang suy nghĩ cách diễn đạt) — không cắt sớm.
  CHECKING           -> đối chiếu explanation với self.source_span (LLM call
                        trung tâm, bắt buộc theo rubric R5).
  ASKING_FOLLOWUP    -> agent hỏi ngược đúng một chỗ hổng/mơ hồ/sai, không
                        tự bổ sung hộ, không lộ đáp án dù bị hỏi dồn.
  STUDENT_RESPONDING -> chờ học viên trả lời câu hỏi ngược — ngưỡng im lặng
                        DÀI (đang suy nghĩ), không coi im lặng là bỏ cuộc.
  TAUGHT             -> đạt tiêu chí "đã dạy được" công bố trước — kết phiên.
"""

from enum import Enum, auto


class TurnState(Enum):
    STUDENT_TEACHING = auto()
    CHECKING = auto()
    ASKING_FOLLOWUP = auto()
    STUDENT_RESPONDING = auto()
    TAUGHT = auto()


class StudentAgentSession:
    def __init__(self, source_span: str, concept: str):
        self.source_span = source_span
        self.concept = concept
        self.state = TurnState.STUDENT_TEACHING
        self.gaps_raised = 0  # đếm số lần đã hỏi ngược — tránh hỏi dồn vô hạn

    async def evaluate_explanation(self, explanation_text: str) -> str:
        """Gọi LLM đối chiếu explanation_text với self.source_span.
        Trả về "day_duoc" | "ho" | "sai" — xem prompts/student_persona.py.

        "day_duoc": giải thích đủ đúng bằng lời của học viên — agent "hiểu",
                     kết phiên.
        "ho":        đúng hướng nhưng còn thiếu/mơ hồ — hỏi ngược MỘT câu tại
                     đúng chỗ hổng, không tự bổ sung hộ.
        "sai":       có phần sai (kể cả khi học viên nói rất tự tin) — không
                     sửa hộ, hỏi lại một câu gợi mở để học viên tự phát hiện.

        Đây là lời gọi AI thật ở quyết định trung tâm (bắt buộc theo rubric
        R5) — KHÔNG hardcode kết quả khi build bản Working.
        """
        raise NotImplementedError
