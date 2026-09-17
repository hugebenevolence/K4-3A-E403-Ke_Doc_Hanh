"""Sàn tối thiểu để một lượt chấm có nghĩa — cả nguồn lẫn lời giảng.

Mọi con số ở đây đến từ dữ liệu thật, không phải từ cảm tính: 4 lượt chạy golden
set trong `eval/results/` và phiên hỏng 2e6d52f3 trong `var/sessions.jsonl`.
Xem `app/domain/substance.py` để biết phép đo.
"""

from __future__ import annotations

import pytest

from app.adapters.knowledge.pdf import Deck
from app.adapters.knowledge.selection import lesson_from_selection
from app.domain.session import TeachBackSession, TurnState
from app.domain.span import Span
from app.domain.substance import is_thin_teachback, teachable_words
from app.domain.verdict import Evidence, GradeResult, Verdict, decide

CHINH = Evidence("[T06-138]", "cơ chế", covered_by_student=True, key=True)


def test_noi_qua_it_thi_khong_the_la_da_giang_du():
    """Ca hỏng trên người dùng thật (phiên 2e6d52f3): "LLM là 1 ngôn ngữ lớn
    chứa nhiều dữ liệu" — 9 chữ — được đóng phiên là ĐÃ GIẢNG ĐỦ."""
    assert decide((CHINH,), "", verbatim=False, thin=False) is Verdict.SUFFICIENT
    assert decide((CHINH,), "", verbatim=False, thin=True) is Verdict.INCOMPLETE


def test_nguong_noi_it_tinh_cong_don_ca_buoi():
    """Giảng một nửa rồi nói nốt nửa sau khi bị hỏi lại vẫn là đã giảng đủ —
    sàn này chặn người nói quá ít, không chặn người nói thành nhiều lượt."""
    assert is_thin_teachback(["mô hình đoán chữ tiếp theo"])
    assert not is_thin_teachback(
        [
            "mô hình đoán chữ tiếp theo",
            "nó nối chữ vừa đoán vào câu rồi chạy lại để đoán chữ kế tiếp",
            "giống bàn phím điện thoại gợi ý từ này nối sang từ kia",
        ]
    )


def test_noi_trai_mot_y_chinh_la_hieu_sai_chu_khong_phai_thieu():
    """M01 hỏng 4/4 lượt chạy: câu sai nghe hợp lý bị hạ xuống thành "còn
    thiếu" vì ô mâu thuẫn văn xuôi để rỗng. Hỏi theo từng ý thì không né được."""
    trai = Evidence("[T06-138]", "cơ chế", covered_by_student=True, key=True,
                    contradicted_by_student=True)
    assert decide((trai,), "", verbatim=False) is Verdict.INCORRECT


def test_noi_trai_chi_tiet_phu_thi_hoi_them_chu_khong_ket_toi_cung_khong_cho_qua():
    """Mức phạt phải khớp mức sai. Trái một chi tiết phụ chưa phải là hiểu sai
    cơ chế — nhưng đóng phiên "đã hiểu" thì học viên mang nguyên chỗ sai đó về,
    và thẻ "cần xem lại" cũng không hiện vì phiên đạt thì không hiện thẻ nào."""
    phu_sai = Evidence("[T06-139]", "con số", covered_by_student=True, key=False,
                       contradicted_by_student=True)
    assert decide((CHINH, phu_sai), "", verbatim=False) is Verdict.INCOMPLETE


def _grade(verdict: Verdict, evidence: tuple[Evidence, ...]) -> GradeResult:
    return GradeResult(verdict=verdict, evidence=evidence, gap_summary="")


def test_phien_dat_thi_khong_hien_the_can_xem_lai():
    """Phiên 2e6d52f3 đóng bằng "Học trò đã hiểu phần này" mà ngay dưới vẫn hiện
    thẻ "Cần xem lại · 1", trỏ vào một dòng tiêu đề. Hai câu đó không thể cùng
    đúng trên một màn hình."""
    phu_chua_noi = Evidence("[T06-139]", "con số", covered_by_student=False, key=False)
    s = TeachBackSession(source_span_id="[T06-138]", concept="c")
    assert s.record(_grade(Verdict.SUFFICIENT, (CHINH, phu_chua_noi))) is TurnState.TAUGHT
    assert s.review_span_ids == ()


def test_chua_dat_thi_tro_vao_y_chinh_con_thieu():
    chinh_thieu = Evidence("[T06-138]", "cơ chế", covered_by_student=False, key=True)
    phu_thieu = Evidence("[T06-139]", "con số", covered_by_student=False, key=False)
    s = TeachBackSession(source_span_id="[T06-138]", concept="c")
    s.record(_grade(Verdict.INCOMPLETE, (chinh_thieu, phu_thieu)))
    assert s.review_span_ids == ("[T06-138]",)


# --- Nguồn có gì để giảng không -----------------------------------------------

BIA = (
    Span("[p1-01]", "AI IN ACTION - Day 1", page=1),
    Span(
        "[p1-02]",
        "AI & LLM Foundation Bạn đang dùng AI mỗi ngày — nhưng thực sự bên trong nó đang làm gì?",
        page=1,
    ),
)
NOI_DUNG = (
    Span("[p2-01]", "Token: model không đọc từ, model đọc mảnh chữ", page=2),
    Span(
        "[p2-02]",
        "Model không nhìn từ nguyên vẹn. Nó cắt văn bản thành các mảnh nhỏ gọi là "
        "token: có từ là một mảnh, có từ vỡ ba bốn mảnh, cả dấu câu cũng tính.",
        page=2,
    ),
    Span("[p2-03]", "Tiếng Việt có dấu nên thường tốn token hơn tiếng Anh.", page=2),
)
DECK = Deck(
    spans=BIA + NOI_DUNG,
    titles={1: "AI IN ACTION - Day 1", 2: "Token: model không đọc từ, model đọc mảnh chữ"},
    terms=("token",),
    pages=2,
)


def test_tieu_de_khong_tinh_la_noi_dung_giang_duoc():
    """Tiêu đề là TÊN của phần cần giảng, không phải nội dung để giảng. Đếm cả
    nó thì trang bìa vượt ngưỡng nhờ đúng dòng chữ không có gì để nói."""
    assert teachable_words(BIA, "AI IN ACTION - Day 1") == 18
    # Không trừ tiêu đề thì chính trang bìa lại "đủ chữ" — vì vậy `title` là
    # tham số bắt buộc, không có mặc định để ai đó quên.
    assert teachable_words(BIA, "") == 23


def test_trang_bia_khong_mo_duoc_phien():
    with pytest.raises(ValueError, match="chỉ có tiêu đề"):
        lesson_from_selection(DECK, ["[p1-01]", "[p1-02]"])


def test_chon_mot_manh_qua_mong_thi_noi_ra_ca_trang_chu_khong_tu_choi():
    """Người dùng bôi trúng mỗi dòng tiêu đề vẫn phải giảng được — nới ra cả
    trang, đúng như frontend làm, chứ không chặn họ lại."""
    lesson, _ = lesson_from_selection(DECK, ["[p2-01]"])
    assert lesson.source_span_ids == ("[p2-01]", "[p2-02]", "[p2-03]")


def test_vung_du_day_thi_giu_nguyen_dung_phan_da_chon():
    lesson, _ = lesson_from_selection(DECK, ["[p2-02]"])
    assert lesson.source_span_ids == ("[p2-02]",)


def test_cho_noi_trai_cung_phai_nam_trong_the_can_xem_lai():
    """Ý học viên hiểu SAI mới là chỗ cần quay lại nhất — nhưng nó lại là ý họ
    CÓ nhắc tới, nên lọc theo "chưa chạm tới" là bỏ sót đúng nó."""
    sai = Evidence("[T06-138]", "cơ chế", covered_by_student=True, key=True,
                   contradicted_by_student=True)
    s = TeachBackSession(source_span_id="[T06-138]", concept="c")
    s.record(_grade(Verdict.INCORRECT, (sai,)))
    assert s.review_span_ids == ("[T06-138]",)


def test_noi_lai_y_nguyen_mot_cau_khong_phai_la_noi_them():
    """Lặp ba lần một câu tám chữ là 24 từ nếu cộng thẳng — vượt sàn mà chẳng
    giảng thêm gì. Máy nhận dạng phát lại một bản final cũng rơi vào đây."""
    cau = "model đoán chữ tiếp theo rồi nối vào"
    assert is_thin_teachback([cau, cau, cau])
