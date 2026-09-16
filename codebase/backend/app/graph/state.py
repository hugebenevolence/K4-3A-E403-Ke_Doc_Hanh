"""State của graph.

Chỉ chứa field có cấu trúc, không chứa chain-of-thought thô của model — để log
đọc được và audit được. Phần model tự lập luận nằm trong `evidence`/`gap_summary`
đã được schema hoá, không phải văn xuôi tự do.
"""

from __future__ import annotations

from typing import Any, TypedDict


class TeachBackState(TypedDict, total=False):
    session_id: str
    student_id: str
    concept: str
    source_span_ids: list[str]

    student_text: str  # lời học viên vừa nói (đã STT final)
    followups_asked: int

    evidence: list[dict[str, Any]]
    gap_summary: str
    verdict: str
    was_verbatim: bool

    agent_says: str  # câu agent sẽ nói ra (hỏi ngược / chốt / gợi ý xem lại)
    cites_span_id: str | None
    review_span_ids: list[str]
    turn_state: str  # tên TurnState sau lượt này — frontend dựa vào đây mở/đóng mic
