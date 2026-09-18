"""Phiên NỐI HAI TRANG khi học viên nói hai trang không liên quan.

Mọi test dưới đây dựng lại đúng một lượt thật (18/9, member5, RLHF × Context):

    học trò: Bạn đã dạy mình «RLHF» và «Context» rồi. Hai trang đó liên quan gì
             với nhau vậy bạn?
    học viên: Tôi thấy nó chả liên quan cái chó gì cả.
    → nhãn INCORRECT
    → "Mình hiểu là: Người chấm xếp hạng rồi model học tăng xác suất…"
    → "Mấy ý đó mình nắm rồi. Còn chỗ nào trong phần này mà bạn thấy quan trọng…"

Ba chỗ hỏng liền, và không chỗ nào nghe vào điều người ta vừa nói.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.adapters.knowledge.local import InMemorySpanStore
from app.domain.graph import denies_relation
from app.domain.span import Span
from app.graph.build import build_graph
from app.graph.nodes import _LINK_REANCHORS
from app.ports.llm import LLMClient, ModelTier, T
from app.prompts.schemas import FollowupOutput, GradeOutput

RLHF = Span(
    "[d1-slide-hackathon-p19-01]",
    "RLHF: ba bước uốn cỗ máy đoán token thành trợ lý biết nghe lời. Người chấm "
    "xếp hạng các câu trả lời, reward model học theo, rồi model được chỉnh để ra "
    "câu được điểm cao.",
)
CONTEXT = Span(
    "[d1-slide-hackathon-p14-02]",
    "Mỗi lần trả lời, model chỉ nhìn được một lượng chữ có hạn — gọi là context. "
    "Hãy hình dung một bàn làm việc: mọi thứ muốn model thấy phải bày lên bàn.",
)
NOI_THAT = "Tôi thấy nó chả liên quan cái chó gì cả."
CAU_BUOI_TRUOC = "Người chấm xếp hạng câu trả lời rồi model học tăng xác suất câu được điểm cao"


class _BoChamTimMoiNoi(LLMClient):
    """Bộ chấm đi tìm một mối nối, gặp "không liên quan" thì ghi là nói trái —
    đúng như nó đã làm trên phiên thật — và persona chép câu buổi trước sang."""

    def __init__(self, question: str):
        self.question = question

    async def structured(self, *, system: str, user: str, schema: type[T], tier: ModelTier) -> T:
        if schema is GradeOutput:
            return schema(
                evidence=[
                    {"span_id": RLHF.span_id, "quote": "RLHF", "key": False,
                     "covered_by_student": False, "contradicted_by_student": False},
                    {"span_id": CONTEXT.span_id, "quote": "context", "key": False,
                     "covered_by_student": False, "contradicted_by_student": False},
                ],
                contradiction="Học viên nói hai trang không liên quan, trái với nguồn.",
                gap_summary="Học viên chỉ nói ngắn rằng hai trang không liên quan.",
            )
        return FollowupOutput(question=self.question, understood=[CAU_BUOI_TRUOC])

    async def stream(self, *, system: str, user: str, tier: ModelTier) -> AsyncIterator[str]:
        yield "ừm."


def _chay(question: str) -> dict:
    graph = build_graph(
        _BoChamTimMoiNoi(question),
        InMemorySpanStore([RLHF, CONTEXT]),
        checkpointer=InMemorySaver(),
    )
    state = {
        "session_id": "noi-1",
        "student_id": "member5",
        "concept": "mối nối giữa «RLHF» và «Context»",
        "source_span_ids": [RLHF.span_id, CONTEXT.span_id],
        "student_text": NOI_THAT,
        "followups_asked": 0,
        "link": True,
        "asked_questions": ["Bạn đã dạy mình «RLHF» và «Context» rồi. Hai trang đó liên quan gì với nhau vậy bạn?"],
        "known_claims": [{"concept": "d1-slide-hackathon:19", "said": CAU_BUOI_TRUOC}],
    }
    return asyncio.run(graph.ainvoke(state, config={"configurable": {"thread_id": "t"}}))


@pytest.mark.parametrize(
    "cau",
    [
        NOI_THAT,
        "hai cái này không liên quan gì tới nhau",
        "em thấy chẳng dính dáng gì",
        "k liên quan đâu",
        "Hai trang đó không hề liên quan",
    ],
)
def test_nhan_ra_lap_truong_khong_lien_quan(cau):
    assert denies_relation(cau)


@pytest.mark.parametrize(
    "cau",
    [
        "Hai trang liên quan ở chỗ context đo bằng token",
        "RLHF chỉnh model theo điểm, còn context là bàn làm việc — nó liên quan vì cả hai giới hạn thứ model thấy",
        "Không phải model nhớ hết, nên context có hạn",
    ],
)
def test_cau_dang_noi_thi_khong_bi_nham_la_phu_nhan(cau):
    assert not denies_relation(cau)


def test_noi_khong_lien_quan_khong_bi_cham_la_hieu_sai():
    """Nguồn của hai trang không nói chúng có liên quan hay không, nên một lập
    trường "không liên quan" không có gì để trái với. Nhãn SAI ở phiên nối phải
    dựng trên một ý cụ thể bị đánh cờ nói trái, không trên ô văn xuôi."""
    ket_qua = _chay("Vì sao bạn thấy hai trang đó không dính gì tới nhau vậy?")
    assert ket_qua["verdict"] == "incomplete"


def test_cau_hoi_nguoc_di_vao_dung_lap_truong_do():
    ket_qua = _chay("Vì sao bạn thấy hai trang đó không dính gì tới nhau vậy?")
    # Không chỉ kiểm chữ "không liên quan" — chỗ hổng bộ chấm tự viết cũng có
    # chữ đó, nên assert như vậy vẫn xanh trên code cũ. Cái cần khoá là persona
    # được dặn HỎI VÌ SAO và KHÔNG khẳng định hai trang có liên quan.
    assert "hỏi xem vì sao" in ket_qua["gap_summary"]
    assert "không khẳng định là chúng có liên quan" in ket_qua["gap_summary"]
    assert ket_qua["agent_says"] == "Vì sao bạn thấy hai trang đó không dính gì tới nhau vậy?"


def test_minh_hieu_la_khong_chep_cau_tu_buoi_truoc():
    """Học viên vừa nói đúng một câu "chả liên quan". Không có gì để "hiểu là"."""
    ket_qua = _chay("Vì sao bạn thấy hai trang đó không dính gì tới nhau vậy?")
    assert ket_qua["agent_understood"] == []


def test_cau_du_phong_cua_phien_noi_khong_noi_ve_phan_nay():
    """Câu hỏi lộ đáp án cả hai lần thì rơi về câu dự phòng — và câu đó phải là
    câu của phiên NỐI, không phải "còn chỗ nào trong phần này"."""
    lo = "Bàn làm việc có hạn thì lượng chữ model nhìn được ảnh hưởng gì?"
    ket_qua = _chay(lo)
    assert ket_qua["agent_says"] in _LINK_REANCHORS
    assert "phần này" not in ket_qua["agent_says"]


def test_luat_bam_loi_do_thang_vao_heard():
    """Test ở trên xanh cả trên code cũ vì một lý do phụ: ở fixture đó code cũ
    rẽ sang nhánh "lạc đề", vốn trả về danh sách rỗng sẵn. Nên đo thẳng vào luật
    bám lời: giữ dòng học viên thật sự vừa nói, bỏ dòng chép từ buổi trước.

    Lời vừa nói CỐ Ý chạm vài từ chung với câu buổi trước ("model", "trả lời"):
    đó là ca làm luật một-từ bị hở, và là ca hay gặp nhất khi đang học cùng một
    khoá — mọi câu đều nhắc model."""
    from app.graph.nodes import _heard

    that = "Context là lượng chữ model nhìn được mỗi lần trả lời"
    giu = _heard(
        ["Context là lượng chữ model nhìn được", CAU_BUOI_TRUOC],
        uncovered="",
        student_text=that,
        said=that,
        earlier=[CAU_BUOI_TRUOC],
    )
    assert giu == ["Context là lượng chữ model nhìn được"]


def test_khong_co_buoi_truoc_thi_luat_chep_khong_lam_gi():
    """Đồ thị rỗng (như golden set) thì luật chép-từ-buổi-trước không được đụng
    tới gì — con số 23/26 đo trên tài khoản rỗng phải còn nguyên giá trị."""
    from app.graph.nodes import _heard

    that = "Context là lượng chữ model nhìn được mỗi lần trả lời"
    assert _heard(["Context là lượng chữ model nhìn được"], "", that, said=that, earlier=[]) == [
        "Context là lượng chữ model nhìn được"
    ]
