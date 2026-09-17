"""Schema output của LLM.

MODEL KHÔNG TỰ CHỐT VERDICT. Nó chỉ trả lời từng câu hỏi cụ thể, kiểm chứng
được: mỗi ý cốt lõi học viên đã nói tới chưa, và có chỗ nào nói trái nguồn
không. Verdict do code suy ra từ đó (xem domain/verdict.py).

Vì sao: bản đầu để model tự chốt verdict sau khi viết gap_summary, và nó không
bao giờ cho `sufficient` — viết ra chỗ hổng xong là đã tự cam kết "còn thiếu",
kể cả khi chính nó ghi "không có chỗ thiếu lớn". Bỏ hẳn quyết định đó khỏi tay
model thì hết cả một lớp thiếu nhất quán.

THỨ TỰ FIELD LÀ CỐ Ý: liệt kê căn cứ trước, nhận định sau.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceOut(BaseModel):
    span_id: str
    quote: str = Field(description="Trích ngắn nguyên văn từ đoạn nguồn")
    covered_by_student: bool = Field(
        description=(
            "Học viên đã nói tới ý này chưa. Diễn đạt khác chữ mà đúng bản chất "
            "thì TÍNH LÀ RỒI — đây là dạy lại, không phải học thuộc lòng."
        )
    )


class GradeOutput(BaseModel):
    evidence: list[EvidenceOut]
    contradiction: str = Field(
        default="",
        description=(
            "Chỗ học viên nói TRÁI với đoạn nguồn, nếu có. Để RỖNG nếu học viên "
            "chỉ thiếu ý chứ không nói sai. Thiếu không phải là sai."
        ),
    )
    gap_summary: str = Field(
        default="",
        description=(
            "Chỗ hổng lớn nhất, một câu — mô tả chỗ THIẾU, không viết lời giải "
            "đúng vào đây. Để RỖNG nếu học viên đã nói đủ mọi ý."
        ),
    )


class FollowupOutput(BaseModel):
    understood: list[str] = Field(
        default_factory=list,
        description=(
            "0–3 ý ngắn học viên ĐÃ nói, diễn đạt lại gọn. Không thêm ý nào từ "
            "nguồn mà học viên chưa nói. Rỗng nếu học viên chưa nói được ý nào."
        ),
    )
    question: str = Field(description="Một câu hỏi ngược, dưới 40 từ, không lộ đáp án")
    cites_span_id: str | None = Field(
        default=None, description="Span được trích trong câu hỏi, nếu có — để frontend highlight"
    )
