"""Smoke test luồng dạy-lại, chạy hoàn toàn bằng mock — không cần key, không tốn credit."""

from __future__ import annotations

import asyncio

from langgraph.checkpoint.memory import InMemorySaver

from app.adapters.knowledge.local import InMemorySpanStore
from app.adapters.llm.mock import MockLLM
from app.adapters.tts.mock import MockTTS
from app.api.session import run_turn, sentence_chunks
from app.domain.session import MAX_FOLLOWUPS, TeachBackSession, TurnState
from app.domain.span import Span
from app.domain.verbatim import is_verbatim_paste
from app.domain.verdict import Evidence, GradeResult, Verdict
from app.graph.build import build_graph

SOURCE = Span(
    span_id="[T06-138]",
    text=(
        "LLM có thể sai và không bao giờ đúng 100 phần trăm, vì phần lớn dữ liệu "
        "trên internet ít nhiều đã có thiên lệch bên trong từ trước."
    ),
)


def _grade(verdict: Verdict, covered: bool = False) -> GradeResult:
    return GradeResult(
        verdict=verdict,
        evidence=(Evidence("[T06-138]", "trích", covered),),
        gap_summary="thiếu nguồn gốc",
    )


def test_sufficient_ket_phien_ngay():
    s = TeachBackSession(source_span_id="[T06-138]", concept="hallucination")
    assert s.record(_grade(Verdict.SUFFICIENT, covered=True)) is TurnState.TAUGHT


def test_het_luot_hoi_thi_goi_y_xem_lai_chu_khong_noi_dap_an():
    s = TeachBackSession(source_span_id="[T06-138]", concept="hallucination")
    for _ in range(MAX_FOLLOWUPS):
        assert s.record(_grade(Verdict.INCOMPLETE)) is TurnState.ASKING_FOLLOWUP
    assert s.record(_grade(Verdict.INCOMPLETE)) is TurnState.SUGGEST_REVIEW
    assert s.review_span_ids == ("[T06-138]",)


def test_mic_va_nguong_im_lang_khac_nhau_theo_state():
    assert TurnState.STUDENT_RESPONDING.mic_open
    assert not TurnState.CHECKING.mic_open
    # Im lặng sau câu hỏi ngược là đang nghĩ, không phải hết lượt.
    assert (
        TurnState.STUDENT_RESPONDING.silence_tolerance_ms
        > TurnState.STUDENT_TEACHING.silence_tolerance_ms
    )


def test_bat_duoc_viec_doc_lai_nguyen_van_nguon():
    assert is_verbatim_paste(SOURCE.text, SOURCE.text)
    assert not is_verbatim_paste(
        "tại vì dữ liệu người ta viết ra vốn đã nghiêng về phía nào đó sẵn rồi", SOURCE.text
    )


def test_graph_chay_het_luot_va_talker_noi_truoc_ket_qua_cham():
    async def main():
        graph = build_graph(
            MockLLM(), InMemorySpanStore([SOURCE]), checkpointer=InMemorySaver()
        )
        state = {
            "session_id": "s1",
            "student_id": "u1",
            "concept": "vì sao LLM bịa",
            "source_span_ids": ["[T06-138]"],
            "student_text": "tại vì dữ liệu huấn luyện có thiên lệch",
            "followups_asked": 0,
        }
        events = [
            e
            async for e in run_turn(
                state, graph=graph, llm=MockLLM(), tts=MockTTS(), thread_id="s1"
            )
        ]

        kinds = [e.kind for e in events]
        assert "audio" in kinds and "state" in kinds

        # Talker phải phát TRƯỚC khi có kết quả chấm, nếu không thì mất ý nghĩa lấp chờ.
        first_filler = next(i for i, e in enumerate(events) if e.kind == "transcript")
        first_state = next(i for i, e in enumerate(events) if e.kind == "state")
        assert events[first_filler].payload["filler"] is True
        assert first_filler < first_state

        final = events[first_state].payload
        assert final["turn_state"] == TurnState.STUDENT_RESPONDING.name
        assert final["verdict"] == "incomplete"

    asyncio.run(main())


def test_cat_cau_cho_tts():
    async def main():
        async def tokens():
            for t in ("À, ", "mình hiểu rồi. ", "Bạn nói tiếp ", "đi nhé?"):
                yield t

        assert [s async for s in sentence_chunks(tokens())] == [
            "À, mình hiểu rồi.",
            "Bạn nói tiếp đi nhé?",
        ]

    asyncio.run(main())
