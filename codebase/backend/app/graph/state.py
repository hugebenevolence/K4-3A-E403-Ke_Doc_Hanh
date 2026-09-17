"""State của graph.

Chỉ chứa field có cấu trúc, không chứa chain-of-thought thô của model — để log
đọc được và audit được. Phần model tự lập luận nằm trong `evidence`/`gap_summary`
đã được schema hoá, không phải văn xuôi tự do.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class TeachBackState(TypedDict, total=False):
    session_id: str
    student_id: str
    concept: str
    source_span_ids: list[str]
    # Thuật ngữ của bài (tiếng Anh trên slide). Dùng để nhận ra chữ tiếng Anh LẠ
    # trong lời agent — thường là chữ máy nghe nhầm bị chép lại ("JSON").
    vocabulary: list[str]

    student_text: str  # lời học viên vừa nói (đã STT final)
    followups_asked: int

    # Mọi lượt học viên đã nói trong buổi, theo thứ tự.
    #
    # Node `grade` đọc nó TRƯỚC khi ghi lượt hiện tại vào, nên ở đó nó là
    # "các lượt trước". Sau khi grade ghi xong, reducer đã cộng lượt này vào —
    # node chạy sau trong cùng lượt (ask_followup) sẽ thấy cả lượt hiện tại.
    # Đừng cộng thêm student_text vào nó ở những node đó.
    #
    # Không có cái này thì mỗi lượt chấm lại từ đầu trên đúng một câu: mảnh trả
    # lời cho một câu hỏi hẹp bị đem so với TOÀN BỘ đoạn nguồn, và người giảng
    # đủ ý qua hai lượt không bao giờ đạt được vì lượt sau không nhớ lượt trước.
    said_before: Annotated[list[str], operator.add]

    # Bài code: mã nguồn học viên đang giải thích. Rỗng với bài slide.
    code: str

    # Cộng dồn qua các lượt (reducer của LangGraph). Không có cái này thì lượt
    # sau agent không biết mình đã hỏi gì và hỏi lại y câu cũ.
    asked_questions: Annotated[list[str], operator.add]

    # Nạp từ hồ sơ học viên lúc mở phiên: span_id -> số buổi trước đã vấp.
    # Cho phép agent nhận ra "chỗ này lần trước cũng chưa thông".
    recurring_gaps: dict[str, int]

    evidence: list[dict[str, Any]]
    gap_summary: str
    verdict: str
    was_verbatim: bool

    agent_says: str  # câu agent sẽ nói ra (hỏi ngược / chốt / gợi ý xem lại)
    # Những ý học viên đã nói mà agent nghe hiểu, hiện thành gạch đầu dòng trên
    # màn hình (không đọc thành tiếng). Node nào đặt agent_says cũng phải đặt
    # lại trường này, không thì gạch đầu dòng của lượt trước dính sang lượt sau.
    agent_understood: list[str]
    cites_span_id: str | None
    review_span_ids: list[str]
    turn_state: str  # tên TurnState sau lượt này — frontend dựa vào đây mở/đóng mic
