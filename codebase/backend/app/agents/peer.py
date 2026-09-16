"""Persona 'bạn học sai' — trung tâm quyết định AI của lát cắt.

State machine tối thiểu (xem codebase/README.md và hồ sơ research turn-taking):
  AI_SPEAKING            -> đang nói ra misconception, ngưỡng ngắt lời NGẮN (~300ms)
  LISTENING_FOR_INTERRUPT -> chờ học viên "giơ tay" ngắt lời
  STUDENT_TURN           -> đang nghe học viên sửa
  CHECKING               -> đối chiếu với nguồn transcript (LLM call trung tâm)
  CONFIRMING             -> nói kết quả; nếu vừa mới HỎI NGƯỢC thì tăng ngưỡng
                            chờ lên vài giây (thời gian suy nghĩ), không coi
                            im lặng là hết lượt.
"""

from enum import Enum, auto


class TurnState(Enum):
    AI_SPEAKING = auto()
    LISTENING_FOR_INTERRUPT = auto()
    STUDENT_TURN = auto()
    CHECKING = auto()
    CONFIRMING = auto()


class PeerAgentSession:
    def __init__(self, source_span: str, misconception: str):
        self.source_span = source_span
        self.misconception = misconception
        self.state = TurnState.AI_SPEAKING

    async def check_correction(self, student_text: str) -> str:
        """Gọi LLM đối chiếu student_text với self.source_span.
        Trả về "dung_du" | "dung_thieu" | "sai" — xem prompts/peer_persona.py.

        Đây là lời gọi AI thật ở quyết định trung tâm (bắt buộc theo rubric R5) —
        KHÔNG hardcode kết quả khi build bản Working.
        """
        raise NotImplementedError
