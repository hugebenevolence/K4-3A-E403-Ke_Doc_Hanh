"""Chặn mã đoạn bịa.

Đây là đường bịa đặt nguy hiểm nhất còn lại: model trả về một span_id không có
thật, và hệ thống tin ngay — ghi vào log, cộng vào hồ sơ học viên, rồi hiện lên
màn hình thành "xem lại đoạn [T06-999]". Học viên đi tìm một đoạn không tồn tại.

Chặn được bằng luật tất định (đối chiếu với đúng tập span đã nạp), không cần
hỏi lại model và không tốn thêm token.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from langgraph.checkpoint.memory import InMemorySaver

from app.adapters.knowledge.local import InMemorySpanStore
from app.domain.span import Span
from app.graph.build import build_graph
from app.ports.llm import LLMClient, ModelTier, T
from app.prompts.schemas import FollowupOutput, GradeOutput

REAL = Span(span_id="[T06-138]", text="nguồn có thật")
STATE = {
    "session_id": "s", "student_id": "u", "concept": "c",
    "source_span_ids": ["[T06-138]"], "student_text": "giải thích ngắn",
    "followups_asked": 0,
}


class HallucinatingLLM(LLMClient):
    """Bịa mã đoạn ở cả phần chấm lẫn phần trích dẫn trong câu hỏi."""

    async def structured(self, *, system: str, user: str, schema: type[T], tier: ModelTier) -> T:
        if schema is GradeOutput:
            return schema(
                evidence=[
                    {"span_id": "[T06-138]", "quote": "thật", "key": True, "covered_by_student": False},
                    {"span_id": "[T06-999]", "quote": "bịa", "key": True, "covered_by_student": False},
                ],
                gap_summary="thiếu nguyên nhân",
                contradiction="",
            )
        return FollowupOutput(question="Sao lại thế bạn?", cites_span_id="[KHONG-CO-THAT]")

    async def stream(self, *, system: str, user: str, tier: ModelTier) -> AsyncIterator[str]:
        yield "ừm."


def _run(state):
    graph = build_graph(
        HallucinatingLLM(), InMemorySpanStore([REAL]), checkpointer=InMemorySaver()
    )
    return asyncio.run(graph.ainvoke(state, config={"configurable": {"thread_id": "t"}}))


def test_ma_doan_bia_bi_loai_khoi_evidence():
    result = _run(dict(STATE))
    span_ids = [e["span_id"] for e in result["evidence"]]
    assert span_ids == ["[T06-138]"], f"mã bịa lọt vào evidence: {span_ids}"


def test_khong_bao_gio_bao_hoc_vien_xem_lai_doan_khong_ton_tai():
    result = _run(dict(STATE))
    assert "[T06-999]" not in result["review_span_ids"]


def test_trich_dan_bia_trong_cau_hoi_nguoc_bi_go_bo():
    # Frontend dùng mã này để highlight vùng slide; trỏ sai là mất niềm tin ngay.
    assert _run(dict(STATE))["cites_span_id"] is None


# --- Học viên hỏi chen câu lạc đề (O03) ---------------------------------------

OFF_TOPIC = "link github bài của trường đang bị đóng đúng không"


class EchoingLLM(LLMClient):
    """Hỏi lại đúng câu học viên vừa nói — quan sát được thật ở case O03."""

    async def structured(self, *, system: str, user: str, schema: type[T], tier: ModelTier) -> T:
        if schema is GradeOutput:
            return schema(
                evidence=[
                    {"span_id": "[T06-138]", "quote": "thật", "key": True, "covered_by_student": False}
                ],
                gap_summary="học viên chưa nói gì về nguồn",
                contradiction="",
            )
        return FollowupOutput(question=f"{OFF_TOPIC.capitalize()}?", cites_span_id=None)

    async def stream(self, *, system: str, user: str, tier: ModelTier) -> AsyncIterator[str]:
        yield "ừm."


def test_khong_hoi_lai_nguyen_cau_lac_de_cua_hoc_vien():
    graph = build_graph(
        EchoingLLM(), InMemorySpanStore([REAL]), checkpointer=InMemorySaver()
    )
    result = asyncio.run(
        graph.ainvoke(
            dict(STATE, student_text=OFF_TOPIC), config={"configurable": {"thread_id": "t2"}}
        )
    )
    says = result["agent_says"].lower()
    assert "github" not in says, says
    # Nói thẳng là không biết rồi mời quay lại phần đang giảng.
    assert "quay lại" in says
