"""Trích dẫn slide gắn vào câu của agent.

Luật quan trọng nhất ở đây không phải hiển thị mà là KHI NÀO được trích:

- Chốt "đã hiểu" -> trích ý học viên vừa dạy được. An toàn tuyệt đối vì chính
  họ vừa nói ra ý đó.
- Chốt "xem lại" -> trích ý còn thiếu. Hết phiên rồi, không còn lượt nào để họ
  tự tìm, và trỏ đúng chỗ cần xem lại là việc track D3 yêu cầu.
- Giữa phiên -> KHÔNG trích ý còn thiếu (persona bị cấm trong prompt, và client
  cũng không in nguyên văn ra).
"""

from __future__ import annotations

import asyncio

from app.domain.session import TurnState
from app.graph.nodes import close_review, close_taught

EVIDENCE = [
    {"span_id": "[A]", "quote": "ý đã nói", "covered_by_student": True},
    {"span_id": "[B]", "quote": "ý còn thiếu", "covered_by_student": False},
]


def test_chot_da_hieu_thi_trich_y_hoc_vien_vua_day_duoc():
    out = asyncio.run(close_taught({"evidence": EVIDENCE}))
    assert out["cites_span_id"] == "[A]"
    assert out["turn_state"] == TurnState.TAUGHT.name


def test_chot_xem_lai_thi_tro_vao_y_con_thieu():
    out = asyncio.run(close_review({"review_span_ids": ["[B]"]}))
    assert out["cites_span_id"] == "[B]"
    assert out["turn_state"] == TurnState.SUGGEST_REVIEW.name


def test_khong_co_gi_de_trich_thi_de_trong_chu_khong_bia():
    assert asyncio.run(close_taught({}))["cites_span_id"] is None
    assert asyncio.run(close_review({}))["cites_span_id"] is None


def test_chot_da_hieu_khong_bao_gio_tro_vao_y_con_thieu():
    # Nếu lỡ trích [B] ở đây thì hoá ra vừa khen vừa đưa luôn đáp án.
    assert asyncio.run(close_taught({"evidence": EVIDENCE}))["cites_span_id"] != "[B]"
