"""Các node quyết định.

Dependency (LLM, kho span) được tiêm qua closure ở build.py thay vì import
trực tiếp, để test node mà không cần provider thật.
"""

from __future__ import annotations

from app.domain.session import TeachBackSession, TurnState
from app.domain.verbatim import is_verbatim_paste
from app.domain.verdict import Evidence, GradeResult, Verdict
from app.graph.state import TeachBackState
from app.ports.knowledge import SpanStore
from app.ports.llm import LLMClient, ModelTier
from app.prompts import registry
from app.prompts.schemas import FollowupOutput, GradeOutput

GRADER_VERSION = "v1"
PERSONA_VERSION = "v1"


def make_grade_node(llm: LLMClient, spans: SpanStore):
    async def grade(state: TeachBackState) -> TeachBackState:
        source = await spans.get_many(state["source_span_ids"])
        student_text = state["student_text"]

        # Tiền kiểm tất định trước khi tốn một lượt gọi LLM: đọc lại nguyên văn
        # nguồn không phải là dạy lại, dù model có thấy "đúng hết" đi nữa.
        verbatim = is_verbatim_paste(student_text, "\n".join(s.text for s in source))

        out = await llm.structured(
            system=registry.compose_system("grader", GRADER_VERSION, source),
            user=f"Lời học viên vừa giải thích:\n\n{student_text}",
            schema=GradeOutput,
            tier=ModelTier.STANDARD,
        )

        verdict = Verdict(out.verdict)
        if verbatim and verdict is Verdict.DAY_DUOC:
            verdict = Verdict.HO

        grade_result = GradeResult(
            verdict=verdict,
            evidence=tuple(
                Evidence(e.span_id, e.quote, e.covered_by_student) for e in out.evidence
            ),
            gap_summary=(
                "học viên đang đọc lại gần nguyên văn tài liệu, chưa diễn đạt bằng lời mình"
                if verbatim
                else out.gap_summary
            ),
        )

        session = TeachBackSession(
            source_span_id=state["source_span_ids"][0],
            concept=state["concept"],
            followups_asked=state.get("followups_asked", 0),
        )
        next_state = session.record(grade_result)

        return {
            "evidence": [e.__dict__ for e in grade_result.evidence],
            "gap_summary": grade_result.gap_summary,
            "verdict": verdict.value,
            "was_verbatim": verbatim,
            "followups_asked": session.followups_asked,
            "review_span_ids": list(session.review_span_ids),
            "turn_state": next_state.name,
        }

    return grade


def make_followup_node(llm: LLMClient, spans: SpanStore):
    async def ask_followup(state: TeachBackState) -> TeachBackState:
        source = await spans.get_many(state["source_span_ids"])
        out = await llm.structured(
            system=registry.compose_system("student_persona", PERSONA_VERSION, source),
            user=(
                f"Học viên vừa nói:\n{state['student_text']}\n\n"
                f"Chỗ hổng cần hỏi vào:\n{state['gap_summary']}"
            ),
            schema=FollowupOutput,
            tier=ModelTier.STANDARD,
        )
        return {
            "agent_says": out.question,
            "cites_span_id": out.cites_span_id,
            "turn_state": TurnState.STUDENT_RESPONDING.name,
        }

    return ask_followup


async def close_taught(state: TeachBackState) -> TeachBackState:
    return {
        "agent_says": "À mình hiểu rồi! Cảm ơn bạn, giờ mình thấy rõ chỗ đó rồi.",
        "turn_state": TurnState.TAUGHT.name,
    }


async def close_review(state: TeachBackState) -> TeachBackState:
    # Hết lượt hỏi mà chưa đủ: KHÔNG nói đáp án, không phán học viên sai — chỉ
    # trỏ về chỗ nên xem lại. Đây là ràng buộc đạo đức của track, không phải
    # lựa chọn về giọng điệu.
    return {
        "agent_says": (
            "Cảm ơn bạn đã giảng cho mình. Mình vẫn còn lấn cấn một chỗ — "
            "bạn xem lại giúp mình đoạn được đánh dấu rồi mình học lại nhé."
        ),
        "turn_state": TurnState.SUGGEST_REVIEW.name,
    }
