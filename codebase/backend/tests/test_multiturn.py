"""Hành vi qua nhiều lượt trong cùng một phiên.

Các lượt sau CHỈ gửi lời học viên; số lượt đã hỏi và các câu đã hỏi do
checkpointer giữ. Nếu tầng gọi cũng tự đếm thì sẽ có hai nguồn sự thật cho
cùng một con số, và sớm muộn lệch nhau.
"""

from __future__ import annotations

import asyncio

from langgraph.checkpoint.memory import InMemorySaver

from app.adapters.knowledge.local import InMemorySpanStore
from app.adapters.llm.mock import MockLLM
from app.domain.session import MAX_FOLLOWUPS, TurnState
from app.domain.span import Span
from app.graph.build import build_graph
from app.prompts.schemas import GradeOutput

SPAN = Span(span_id="[T06-138]", text="nguồn giả lập")
SHORT = "tại vì dữ liệu có thiên lệch"  # ngắn → MockLLM luôn trả incomplete
CONFIG = {"configurable": {"thread_id": "phien-1"}}


def _first_turn() -> dict:
    return {
        "session_id": "phien-1",
        "student_id": "u1",
        "concept": "vì sao LLM bịa",
        "source_span_ids": [SPAN.span_id],
        "student_text": SHORT,
        "followups_asked": 0,
    }


def test_dem_luot_hoi_tu_tang_qua_cac_luot_ma_khong_can_tang_goi_dem_ho():
    async def main():
        graph = build_graph(
            MockLLM(), InMemorySpanStore([SPAN]), checkpointer=InMemorySaver()
        )

        # ASKING_FOLLOWUP chỉ là state trung gian để rẽ nhánh; hỏi xong thì
        # graph trả về STUDENT_RESPONDING vì tới lượt học viên nói.
        result = await graph.ainvoke(_first_turn(), config=CONFIG)
        assert result["turn_state"] == TurnState.STUDENT_RESPONDING.name
        assert result["followups_asked"] == 1

        # Các lượt sau chỉ gửi lời học viên, không gửi lại followups_asked.
        for expected in range(2, MAX_FOLLOWUPS + 1):
            result = await graph.ainvoke({"student_text": SHORT}, config=CONFIG)
            assert result["turn_state"] == TurnState.STUDENT_RESPONDING.name
            assert result["followups_asked"] == expected

        # Hết mức thì kết phiên bằng gợi ý xem lại, không phải bằng đáp án.
        result = await graph.ainvoke({"student_text": SHORT}, config=CONFIG)
        assert result["turn_state"] == TurnState.SUGGEST_REVIEW.name
        assert "xem lại" in result["agent_says"]

    asyncio.run(main())


def test_agent_nho_nhung_cau_da_hoi_de_khong_hoi_lap():
    async def main():
        graph = build_graph(
            MockLLM(), InMemorySpanStore([SPAN]), checkpointer=InMemorySaver()
        )
        await graph.ainvoke(_first_turn(), config=CONFIG | {"configurable": {"thread_id": "p2"}})
        result = await graph.ainvoke(
            {"student_text": SHORT}, config={"configurable": {"thread_id": "p2"}}
        )
        assert len(result["asked_questions"]) == 2

    asyncio.run(main())


def test_khong_co_nguon_thi_hong_to_chu_khong_cham_bia():
    async def main():
        graph = build_graph(MockLLM(), InMemorySpanStore([]), checkpointer=InMemorySaver())
        state = _first_turn() | {"source_span_ids": []}
        try:
            await graph.ainvoke(state, config={"configurable": {"thread_id": "p3"}})
        except ValueError as e:
            assert "source_span_ids" in str(e)
        else:
            raise AssertionError("chấm không nguồn mà vẫn chạy — grounding bị bỏ qua")

    asyncio.run(main())


class _SpyLLM(MockLLM):
    """Ghi lại phần user của mỗi lượt gọi chấm, để soi xem bộ chấm THẤY những gì."""

    def __init__(self):
        self.graded: list[str] = []

    async def structured(self, *, system, user, schema, tier):
        if schema is GradeOutput:
            self.graded.append(user)
        return await super().structured(system=system, user=user, schema=schema, tier=tier)


def test_bo_cham_thay_ca_buoi_chu_khong_chi_cau_vua_noi():
    """Lượt sau là câu TRẢ LỜI cho một câu hỏi hẹp, không phải một lời giảng mới.

    Bản trước chỉ gửi đúng lượt vừa nói, nên mảnh trả lời đó bị đem đối chiếu
    với toàn bộ đoạn nguồn — hoặc trượt oan, hoặc cho qua cả bài chỉ vì một
    mảnh (phiên thật 2e6d52f3).
    """

    async def main():
        llm = _SpyLLM()
        graph = build_graph(llm, InMemorySpanStore([SPAN]), checkpointer=InMemorySaver())
        config = {"configurable": {"thread_id": "p4"}}
        await graph.ainvoke(_first_turn() | {"student_text": "ý thứ nhất"}, config=config)
        await graph.ainvoke({"student_text": "ý thứ hai"}, config=config)

        lan_dau, lan_sau = llm.graded
        assert "> ý thứ nhất" in lan_dau and "ý thứ hai" not in lan_dau
        # Lượt hai phải thấy CẢ HAI ý, cộng câu hỏi mà lượt đó đang trả lời.
        assert "> ý thứ nhất" in lan_sau and "> ý thứ hai" in lan_sau
        assert "Chỗ đó thì vì sao lại xảy ra vậy bạn?" in lan_sau

    asyncio.run(main())


def test_giang_du_y_qua_hai_luot_van_duoc_tinh_la_da_giang():
    """Cộng dồn không chỉ để chấm đúng — nó là điều kiện để phiên KẾT THÚC được.

    MockLLM cho "đủ" khi học viên nói từ 40 từ trở lên. Chia đúng số chữ ấy làm
    hai lượt: bản chỉ-chấm-lượt-cuối sẽ không bao giờ đóng phiên.
    """

    async def main():
        nua = " ".join(f"chữ{i}" for i in range(21))
        graph = build_graph(
            MockLLM(), InMemorySpanStore([SPAN]), checkpointer=InMemorySaver()
        )
        config = {"configurable": {"thread_id": "p5"}}
        dau = await graph.ainvoke(_first_turn() | {"student_text": nua}, config=config)
        assert dau["turn_state"] == TurnState.STUDENT_RESPONDING.name

        sau = await graph.ainvoke({"student_text": nua.replace("chữ", "từ")}, config=config)
        assert sau["turn_state"] == TurnState.TAUGHT.name

    asyncio.run(main())
