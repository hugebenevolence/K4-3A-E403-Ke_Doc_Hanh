"""Câu mở phiên NỐI HAI TRANG: dựng từ lời học viên, không lộ mối nối.

Bản trước là một câu cố định cho mọi cặp trang — "Bạn đã dạy mình «AI, ML,
Deep…» và «RLHF» rồi. Hai trang đó liên quan gì với nhau vậy bạn?" (18/9).
Không lộ gì, nhưng không cho học viên chỗ nào để bám, và nhiều cặp trang đáng
PHÂN BIỆT hơn là đáng nối. Giờ model viết câu mở từ chính lời học viên, và
mấy test dưới đây giữ các chốt chặn quanh nó.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest

from app.adapters.llm.mock import MockLLM
from app.domain.graph import PageRef
from app.graph.nodes import link_fallback, open_link_session
from app.ports.llm import LLMClient, ModelTier, T
from app.prompts import registry
from app.prompts.schemas import LinkOpenerOutput

RLHF = PageRef(
    key="d1-slide-hackathon:19",
    title="RLHF: ba bước uốn cỗ máy đoán token thành trợ lý biết nghe lời",
    deck="d1-slide-hackathon",
    page=19,
    span_ids=("[d1-slide-hackathon-p19-01]",),
    text=(
        "Người chấm xếp hạng các câu trả lời, reward model học theo cách chấm đó, "
        "rồi model được chỉnh để ra câu được điểm cao."
    ),
)
CONTEXT = PageRef(
    key="d1-slide-hackathon:14",
    title="Context: bàn làm việc có hạn của model",
    deck="d1-slide-hackathon",
    page=14,
    span_ids=("[d1-slide-hackathon-p14-02]",),
    text=(
        "Mỗi lần trả lời, model chỉ nhìn được một lượng chữ có hạn. Hãy hình dung "
        "một bàn làm việc: mọi thứ muốn model thấy phải bày lên bàn."
    ),
)
NOI_RLHF = ["Người chấm xếp hạng các câu trả lời rồi model học tăng xác suất câu được điểm cao"]
NOI_CONTEXT = ["Context là lượng chữ model nhìn thấy được trong một lần trả lời"]

TOT = (
    "Bạn nói người chấm xếp hạng câu trả lời để model học, còn context là lượng "
    "chữ model nhìn thấy mỗi lần trả lời. Hai thứ đó khác nhau ở chỗ nào vậy bạn?"
)


class _Model(LLMClient):
    """Trả lần lượt từng câu viết sẵn, và ghi lại mọi prompt đã nhận."""

    def __init__(self, *questions: str):
        self.questions = list(questions)
        self.calls: list[tuple[str, str]] = []

    async def structured(self, *, system: str, user: str, schema: type[T], tier: ModelTier) -> T:
        assert schema is LinkOpenerOutput
        self.calls.append((system, user))
        return schema(angle="contrast", question=self.questions[len(self.calls) - 1])

    async def stream(self, *, system: str, user: str, tier: ModelTier) -> AsyncIterator[str]:
        yield ""


def _mo(model: LLMClient) -> str:
    return asyncio.run(open_link_session(model, RLHF, CONTEXT, NOI_RLHF, NOI_CONTEXT))


def test_cau_mo_tot_duoc_dung_nguyen():
    model = _Model(TOT)
    assert _mo(model) == TOT
    assert len(model.calls) == 1


def test_model_chi_thay_loi_hoc_vien_khong_thay_nguon():
    """Không có nguồn trong prompt thì không có mối nối nào để lỡ miệng đọc hộ."""
    model = _Model(TOT)
    _mo(model)
    system, user = model.calls[0]
    assert NOI_RLHF[0] in user and NOI_CONTEXT[0] in user
    # Tên gọi được thành tiếng: không phải nhãn cắt cụt ("AI, ML, Deep…"),
    # cũng không phải cả cái tiêu đề slide.
    assert "Trang «RLHF»" in user and "Trang «Context»" in user
    assert "học theo cách chấm đó" not in system + user
    assert "bày lên bàn" not in system + user


@pytest.mark.parametrize(
    "hong",
    [
        # Đưa sẵn mối nối để gật đầu.
        "Có phải context chính là chỗ người chấm xếp hạng câu trả lời không bạn?",
        # Nói ra điều học viên chưa hề nói ở cả hai trang: reward model, bày lên bàn.
        "Bạn nói người chấm xếp hạng, còn context là lượng chữ — vậy reward model có bày lên bàn không?",
        # Chỉ nhắc một trang.
        "Người chấm xếp hạng các câu trả lời theo tiêu chí nào vậy bạn?",
        # Nhận vai người giảng.
        "Để mình giải thích: người chấm xếp hạng câu trả lời, còn context là lượng chữ model thấy.",
        # Gọi trang bằng ký hiệu: học viên không biết trang nào là A.
        "Bạn nói trang A là người chấm xếp hạng câu trả lời, còn trang B là lượng chữ model thấy — khác nhau ở đâu?",
        "Bạn nói người chấm xếp hạng câu trả lời, còn slide thứ hai nói context là lượng chữ model thấy — giống nhau chỗ nào?",
    ],
)
def test_cau_mo_hong_thi_viet_lai(hong):
    model = _Model(hong, TOT)
    assert _mo(model) == TOT
    # Lần viết lại được nói rõ vì sao lần đầu hỏng, không phải gọi lại y nguyên.
    assert "CÂU BẠN VỪA VIẾT" in model.calls[1][1]


def test_viet_lai_van_hong_thi_dung_cau_viet_san():
    hong = "Người chấm xếp hạng các câu trả lời theo tiêu chí nào vậy bạn?"
    assert _mo(_Model(hong, hong)) == link_fallback(RLHF, CONTEXT)


def test_cau_viet_san_khong_hoi_lien_quan_gi_chung_chung():
    cau = link_fallback(RLHF, CONTEXT)
    assert "liên quan gì" not in cau
    assert "giống" in cau and "khác" in cau


def test_trang_khong_con_cau_nao_ro_thi_nhac_ten_trang_cung_tinh():
    """Không đòi được lời học viên ở một trang khi họ không còn câu nào rõ."""
    cau = "Bạn nói người chấm xếp hạng câu trả lời, còn context thì khác ở chỗ nào vậy bạn?"
    model = _Model(cau)
    out = asyncio.run(open_link_session(model, RLHF, CONTEXT, NOI_RLHF, []))
    assert out == cau


def test_mock_di_qua_duoc_cac_chot_chan():
    """Đường chạy mock phải giống đường chạy thật, không rơi về câu viết sẵn."""
    out = _mo(MockLLM())
    assert out != link_fallback(RLHF, CONTEXT)
    assert "Người chấm xếp hạng" in out and "Context là lượng chữ" in out


def test_prompt_mo_phien_noi_nap_duoc_kem_san_an_toan_va_vai_hoc_tro():
    from app.graph.nodes import LINK_OPENER_VERSION

    system = registry.compose_system("link_opener", LINK_OPENER_VERSION)
    assert "SÀN AN TOÀN" in system and "HỌC TRÒ" in system and "angle" in system
