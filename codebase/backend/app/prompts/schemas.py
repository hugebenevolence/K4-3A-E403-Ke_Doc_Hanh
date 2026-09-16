"""Schema output của LLM.

THỨ TỰ FIELD LÀ CỐ Ý: structured output sinh field theo thứ tự khai báo, nên
để `verdict` cuối cùng buộc model phải liệt kê căn cứ xong mới được chốt.
Đảo lên đầu là quay về chấm cảm tính rồi tìm căn cứ biện minh sau.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EvidenceOut(BaseModel):
    span_id: str
    quote: str = Field(description="Trích ngắn nguyên văn từ đoạn nguồn")
    covered_by_student: bool = Field(
        description="Học viên đã nói tới ý này chưa. Diễn đạt khác chữ mà đúng bản chất thì tính là rồi."
    )


class GradeOutput(BaseModel):
    evidence: list[EvidenceOut]
    gap_summary: str = Field(
        description="Chỗ hổng lớn nhất, một câu. Mô tả chỗ thiếu — KHÔNG viết lời giải đúng vào đây."
    )
    verdict: Literal["day_duoc", "ho", "sai"]


class FollowupOutput(BaseModel):
    question: str = Field(description="Một câu hỏi ngược, dưới 40 từ, không lộ đáp án")
    cites_span_id: str | None = Field(
        default=None, description="Span được trích trong câu hỏi, nếu có — để frontend highlight"
    )
