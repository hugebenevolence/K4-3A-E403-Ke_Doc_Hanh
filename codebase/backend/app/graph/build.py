"""Dựng graph quyết định.

Cố ý KHÔNG dùng vòng lặp ReAct: luồng dạy-lại có cấu trúc ổn định (chấm →
rẽ nhánh → hỏi ngược hoặc kết), nên workflow tất định vừa rẻ vừa đoán trước
được. Thêm tool sau này là thêm node, không phải thả cho model tự lặp.

Talker (câu đệm lúc chờ) KHÔNG nằm trong graph — nó là việc của tầng
orchestration ở api/, chạy song song với lần invoke này. Xem app/api/session.py.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.domain.session import TurnState
from app.graph.nodes import (
    close_review,
    close_taught,
    make_followup_node,
    make_grade_node,
)
from app.graph.state import TeachBackState
from app.ports.knowledge import SpanStore
from app.ports.llm import LLMClient


def _route(state: TeachBackState) -> str:
    match state["turn_state"]:
        case TurnState.TAUGHT.name:
            return "close_taught"
        case TurnState.SUGGEST_REVIEW.name:
            return "close_review"
        case _:
            return "ask_followup"


def build_graph(llm: LLMClient, spans: SpanStore, *, checkpointer=None, store=None):
    """checkpointer = trí nhớ trong phiên; store = trí nhớ xuyên phiên.

    Truyền thiếu một trong hai là lỗi kiến trúc hay gặp nhất với LangGraph:
    checkpointer giữ mạch hội thoại, store giữ hồ sơ học viên qua nhiều buổi.
    """
    g = StateGraph(TeachBackState)
    g.add_node("grade", make_grade_node(llm, spans))
    g.add_node("ask_followup", make_followup_node(llm, spans))
    g.add_node("close_taught", close_taught)
    g.add_node("close_review", close_review)

    g.add_edge(START, "grade")
    g.add_conditional_edges("grade", _route, ["ask_followup", "close_taught", "close_review"])
    for terminal in ("ask_followup", "close_taught", "close_review"):
        g.add_edge(terminal, END)

    return g.compile(checkpointer=checkpointer, store=store)
