"""Các node quyết định.

Dependency (LLM, kho span) được tiêm qua closure ở build.py thay vì import
trực tiếp, để test node mà không cần provider thật.
"""

from __future__ import annotations

import logging

from app.domain.session import TeachBackSession, TurnState
from app.domain.span import normalize_span_id
from app.domain.verbatim import is_verbatim_paste
from app.domain.verdict import Evidence, GradeResult, decide
from app.graph.state import TeachBackState
from app.ports.knowledge import SpanStore
from app.ports.llm import LLMClient, ModelTier
from app.prompts import registry
from app.prompts.schemas import FollowupOutput, GradeOutput

log = logging.getLogger(__name__)

GRADER_VERSION = "v2"
PERSONA_VERSION = "v1"


def make_grade_node(llm: LLMClient, spans: SpanStore):
    async def grade(state: TeachBackState) -> TeachBackState:
        span_ids = state.get("source_span_ids") or []
        if not span_ids:
            # Chấm mà không có nguồn thì chỉ còn kiến thức chung của model —
            # đúng cái mà thiết kế grounding cấm. Thà hỏng to còn hơn chấm bịa.
            raise ValueError("Phiên không có source_span_ids; không thể chấm có căn cứ")

        source = await spans.get_many(span_ids)
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

        # Model có thể bịa ra mã đoạn không tồn tại. Không lọc thì mã bịa đó
        # chui vào log, vào hồ sơ học viên, rồi hiện lên màn hình dưới dạng
        # "xem lại đoạn [T06-999]" — học viên đi tìm một đoạn không có thật.
        # Đây là chỗ chặn được bằng luật tất định, không cần hỏi lại model.
        # Khớp nới theo dạng chuẩn hoá rồi trả về mã CANONICAL, để mọi thứ ghi
        # xuống log/hồ sơ đều cùng một dạng dù model viết kiểu gì.
        known = {normalize_span_id(s.span_id): s.span_id for s in source}
        cited = tuple(
            Evidence(known[key], e.quote, e.covered_by_student)
            for e in out.evidence
            if (key := normalize_span_id(e.span_id)) in known
        )
        if bogus := [
            e.span_id for e in out.evidence if normalize_span_id(e.span_id) not in known
        ]:
            log.warning("Bỏ %d mã đoạn không có thật do model bịa: %s", len(bogus), bogus)

        verdict = decide(cited, out.contradiction, verbatim=verbatim)
        grade_result = GradeResult(
            verdict=verdict,
            evidence=cited,
            gap_summary=(
                "học viên đang đọc lại gần nguyên văn tài liệu, chưa diễn đạt bằng lời mình"
                if verbatim
                else (out.gap_summary or out.contradiction)
            ),
        )

        session = TeachBackSession(
            source_span_id=span_ids[0],
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

        asked = state.get("asked_questions") or []
        history = (
            "\n\nMình đã hỏi những câu này rồi, đừng hỏi lại theo cùng một kiểu:\n"
            + "\n".join(f"- {q}" for q in asked)
            if asked
            else ""
        )

        # Chỗ học viên đã vấp ở buổi trước: nói ra được thì câu hỏi bớt máy móc
        # và học viên thấy agent thật sự đang theo mình qua nhiều buổi.
        gaps = state.get("recurring_gaps") or {}
        if repeated := [sid for sid in (state.get("source_span_ids") or []) if gaps.get(sid)]:
            history += (
                f"\n\nBuổi trước bạn ấy cũng chưa thông chỗ {', '.join(repeated)} — "
                "có thể nhắc nhẹ điều đó, nhưng đừng làm bạn ấy thấy bị chấm điểm."
            )

        out = await llm.structured(
            system=registry.compose_system("student_persona", PERSONA_VERSION, source),
            user=(
                f"Học viên vừa nói:\n{state['student_text']}\n\n"
                f"Chỗ hổng cần hỏi vào:\n{state['gap_summary']}{history}"
            ),
            schema=FollowupOutput,
            tier=ModelTier.STANDARD,
        )
        # Trích dẫn bịa còn tệ hơn không trích: frontend sẽ dùng mã này để
        # highlight vùng trên slide, trỏ sai là học viên mất niềm tin ngay.
        canonical = {normalize_span_id(s.span_id): s.span_id for s in source}
        cites = canonical.get(normalize_span_id(out.cites_span_id or ""))
        if out.cites_span_id and not cites:
            log.warning("Bỏ trích dẫn bịa trong câu hỏi ngược: %s", out.cites_span_id)

        return {
            "agent_says": out.question,
            "cites_span_id": cites,
            "asked_questions": [out.question],
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
