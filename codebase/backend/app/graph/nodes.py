"""Các node quyết định.

Dependency (LLM, kho span) được tiêm qua closure ở build.py thay vì import
trực tiếp, để test node mà không cần provider thật.
"""

from __future__ import annotations

import logging

from app.domain.leak import leaked_terms, leaks_answer
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

        # KHÔNG dùng `contradiction` làm gap_summary. Nó mô tả chỗ học viên nói
        # sai bằng cách nêu ra cái đúng ("quy cho nhiệt độ, trong khi nguồn nói
        # là áp suất"), và gap_summary được đưa thẳng cho persona làm đề bài
        # hỏi ngược — tức là đọc luôn đáp án vào câu hỏi. Đã quan sát thấy thật:
        # học viên nói "trên đó lạnh hơn", agent hỏi lại "cái lạnh đó liên quan
        # thế nào đến áp suất khí quyển".
        if verbatim:
            gap = "học viên đang đọc lại gần nguyên văn tài liệu, chưa diễn đạt bằng lời mình"
        elif out.gap_summary.strip():
            gap = out.gap_summary
        elif any(not e.covered_by_student for e in cited):
            # Cố ý KHÔNG nhét trích dẫn nguồn vào đây: quote chính là ý học viên
            # đang thiếu, đưa xuống persona là đọc luôn đáp án vào câu hỏi.
            gap = "còn một ý cốt lõi trong nguồn mà học viên chưa chạm tới"
        else:
            gap = "lời giải thích chưa khớp với nguồn, nhưng chưa xác định được thiếu ở đâu"

        grade_result = GradeResult(verdict=verdict, evidence=cited, gap_summary=gap)

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


def _reanchor(state: TeachBackState) -> str:
    """Câu hỏi dùng khi viết lại vẫn lộ đáp án.

    Câu chung chung ("bạn giải thích thêm chỗ đó được không?") là câu tệ nhất:
    học viên không biết "chỗ đó" là chỗ nào, và quan sát thật cho thấy nó rơi
    đúng vào lúc học viên đang lạc đề — tức lúc họ cần được neo lại nhất.

    Nhắc tên khái niệm KHÔNG phải là lộ đáp án: nó đang hiện sẵn trên màn hình.
    Lộ là nói ra phần NỘI DUNG học viên còn thiếu.
    """
    concept = (state.get("concept") or "").strip()
    if not concept:
        return "Bạn kể lại cho mình từ đầu được không, mình chưa bắt kịp."
    return (
        f"Thật ra mình vẫn chưa nối được chỗ bạn vừa nói với {concept}. "
        "Bạn thử kể lại từ đầu giúp mình nhé?"
    )


def _uncovered_text(state: TeachBackState, source) -> str:
    """Nội dung những span học viên chưa chạm tới — tức phần đang thiếu.

    Đây chính là thứ câu hỏi ngược không được nói hộ.
    """
    missing = {
        normalize_span_id(e["span_id"])
        for e in (state.get("evidence") or [])
        if not e.get("covered_by_student")
    }
    return "\n".join(s.text for s in source if normalize_span_id(s.span_id) in missing)


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
        if any(gaps.get(sid) for sid in (state.get("source_span_ids") or [])):
            # Cố ý không đưa mã đoạn thô vào đây — model sẽ đọc "[DEMO-01]"
            # thành tiếng giữa buổi học, nghe như máy đọc lỗi.
            history += (
                "\n\nBuổi trước bạn ấy cũng chưa thông đúng chỗ này — có thể nhắc "
                "nhẹ điều đó, nhưng đừng làm bạn ấy thấy bị chấm điểm."
            )

        system = registry.compose_system("student_persona", PERSONA_VERSION, source)
        user = (
            f"Nội dung vừa nghe được:\n{state['student_text']}\n\n"
            f"Chỗ hổng cần hỏi vào:\n{state['gap_summary']}{history}"
        )
        out = await llm.structured(
            system=system, user=user, schema=FollowupOutput, tier=ModelTier.STANDARD
        )

        # Chặn lộ đáp án bằng luật tất định thay vì tin prompt. Nếu câu hỏi nói
        # ra từ khoá của đúng phần học viên còn thiếu thì học viên chỉ cần gật
        # đầu là xong — mất sạch ý nghĩa của việc hỏi ngược.
        uncovered = _uncovered_text(state, source)
        if uncovered and leaks_answer(out.question, uncovered, state["student_text"]):
            leaked = leaked_terms(out.question, uncovered, state["student_text"])
            log.warning("Câu hỏi ngược làm lộ đáp án (%s), hỏi lại", sorted(leaked))
            out = await llm.structured(
                system=system,
                user=(
                    f"{user}\n\nCÂU BẠN VỪA VIẾT ĐÃ LỘ ĐÁP ÁN vì có nhắc tới: "
                    f"{', '.join(sorted(leaked))}. Viết lại câu hỏi KHÔNG dùng "
                    "những từ đó và không nói hộ phần học viên còn thiếu."
                ),
                schema=FollowupOutput,
                tier=ModelTier.STANDARD,
            )
            if leaks_answer(out.question, uncovered, state["student_text"]):
                log.warning("Viết lại vẫn lộ, dùng câu hỏi neo lại khái niệm")
                out = FollowupOutput(question=_reanchor(state), cites_span_id=None)
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
