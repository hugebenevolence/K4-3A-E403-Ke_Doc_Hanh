"""Dựng bài học từ vùng học viên tự chọn — không cần file PDF thật."""

from __future__ import annotations

import asyncio

import pytest

from app.adapters.knowledge.pdf import Deck
from app.adapters.knowledge.selection import lesson_from_selection
from app.domain.span import Span

# Mỗi ô dài cỡ một ô nội dung thật trên slide (~25 từ). Fixture ngắn hơn thế sẽ
# bị luật "vùng chỉ có tiêu đề" nới ra cả trang — xem domain/substance.py — và
# test sẽ đo một luồng mà người dùng thật không đi qua.
DECK = Deck(
    spans=(
        Span("[d-p20-01]", "Giới hạn bẩm sinh: học giả trong bong bóng", page=20, bbox=(38, 20, 519, 48)),
        Span(
            "[d-p20-03]",
            "Nói chắc như đúng rồi. Model tối ưu cho câu nghe hợp lý chứ không tra "
            "lại sự thật, nên nó vẫn nói trôi chảy cả khi đang nói sai.",
            page=20,
            bbox=(362, 93, 612, 174),
        ),
        Span(
            "[d-p20-06]",
            "Đây không phải lỗi tạm thời — đó là bản chất của cỗ máy đoán token, và "
            "sẽ không biến mất khi model to hơn hay dữ liệu nhiều hơn.",
            page=20,
            bbox=(120, 359, 843, 391),
        ),
        Span(
            "[d-p21-02]",
            "Model rất giỏi học vẹt đường tắt khi dữ liệu có mẫu dễ đoán, nên điểm "
            "cao trên bộ kiểm tra chưa chắc có nghĩa là nó đã hiểu việc cần làm.",
            page=21,
            bbox=(40, 90, 500, 160),
        ),
    ),
    titles={20: "Giới hạn bẩm sinh: học giả trong bong bóng", 21: ""},
    terms=("LLM", "token"),
    pages=29,
)


def test_bai_hoc_dung_tu_dung_vung_da_chon_khong_co_dinh_slide_20():
    lesson, _ = lesson_from_selection(DECK, ["[d-p21-02]"])
    assert lesson.source_span_ids == ("[d-p21-02]",)


def test_thu_tu_theo_thu_tu_doc_tren_slide_khong_theo_thu_tu_bam():
    # Học viên kéo khung từ dưới lên: nguồn vẫn phải đọc từ trên xuống, không
    # thì agent hỏi về câu kết luận trước câu dẫn.
    lesson, _ = lesson_from_selection(DECK, ["[d-p20-06]", "[d-p20-03]"])
    assert lesson.source_span_ids == ("[d-p20-03]", "[d-p20-06]")


def test_ten_khai_niem_la_tieu_de_trang():
    lesson, _ = lesson_from_selection(DECK, ["[d-p20-03]"])
    assert lesson.concept == "Giới hạn bẩm sinh: học giả trong bong bóng"


def test_trang_khong_tieu_de_thi_lay_dau_o_dau_tien():
    lesson, _ = lesson_from_selection(DECK, ["[d-p21-02]"])
    assert lesson.concept.startswith("Model rất giỏi học vẹt")


def test_ma_la_bi_bo_qua_ma_khong_lam_hong_phien():
    lesson, _ = lesson_from_selection(DECK, ["[d-p20-03]", "[khong-ton-tai]"])
    assert lesson.source_span_ids == ("[d-p20-03]",)


def test_khong_con_o_nao_thi_bao_loi_chu_khong_cham_voi_nguon_rong():
    with pytest.raises(ValueError):
        lesson_from_selection(DECK, ["[khong-ton-tai]"])


def test_kho_chua_ca_bo_slide_de_trich_dan_sang_o_ben_canh_van_tra_ra():
    # Dự án chạy async bằng asyncio.run như các test khác, không kéo thêm plugin.
    _, store = lesson_from_selection(DECK, ["[d-p20-03]"])
    neighbour = asyncio.run(store.get("[d-p20-06]"))
    assert "cỗ máy đoán token" in neighbour.text


def test_vung_chon_mang_ma_bo_slide_la_thi_bao_loi_chu_khong_cham_bai_khac(monkeypatch):
    """Đo được 18/9: link mang mã bộ slide sai vẫn mở phiên bình thường, rồi chấm
    học viên theo trang 20 của bài mặc định — giảng slide này, bị hỏi về slide
    khác, không có dấu hiệu gì là đã lệch."""
    from pathlib import Path

    import pytest

    from app import main

    monkeypatch.setattr(main, "_deck_paths", lambda: {"d1-slide-hackathon": Path("d1.pdf")})
    monkeypatch.setattr(main, "_find_deck", lambda slug: None)
    with pytest.raises(ValueError, match="thư viện"):
        main._lesson(["[d1-slide-hackathon-p12-01]"], "d1")


# Trang có hình: ô hình gần như không có chữ, chữ nói hình đó minh hoạ CHO GÌ
# nằm ở các ô bên cạnh trên cùng trang.
DECK_HINH = Deck(
    spans=(
        Span("[d-p16-01]", "Sự ra đời của Deep Learning", page=16, bbox=(38, 20, 519, 48)),
        Span(
            "[d-p16-f01]",
            "Hình minh hoạ. Nhãn trong hình: Dartmouth Workshop 1956, Perceptrons 1969, "
            "AlexNet 2012, Transformer 2017.",
            page=16,
            bbox=(100, 90, 860, 420),
            kind="figure",
        ),
        Span(
            "[d-p16-04]",
            "Sau mùa đông lần hai, câu hỏi của cả ngành đổi hẳn: nếu không thể viết hết "
            "tri thức thế giới vào máy, thì có thể để máy tự học nó từ dữ liệu không?",
            page=16,
            bbox=(120, 430, 843, 470),
        ),
    ),
    titles={16: "Sự ra đời của Deep Learning"},
    terms=("deep learning",),
    pages=29,
)


def test_chon_moi_cai_hinh_thi_van_lay_chu_cua_ca_trang():
    """Nguồn chỉ có mỗi ô "Hình minh hoạ" thì không có gì để hỏi vào.

    Đo được thật trên trang "Sự ra đời của Deep Learning": câu mở bài thành
    "trong hình minh hoạ đó, chỗ nào đang diễn tả ý chính của slide?".
    """
    lesson, _ = lesson_from_selection(DECK_HINH, ["[d-p16-f01]"])
    assert "[d-p16-04]" in lesson.source_span_ids, "thiếu chữ quanh hình trên cùng trang"


def test_trang_chi_co_hinh_va_tieu_de_thi_van_giang_duoc():
    """Nới ra cả trang vẫn ít chữ thì KHÔNG từ chối, vì hình vẫn là một ý trọn vẹn."""
    chi_hinh = Deck(
        spans=tuple(s for s in DECK_HINH.spans if s.span_id != "[d-p16-04]"),
        titles=DECK_HINH.titles,
        terms=DECK_HINH.terms,
        pages=DECK_HINH.pages,
    )
    lesson, _ = lesson_from_selection(chi_hinh, ["[d-p16-f01]"])
    assert "[d-p16-f01]" in lesson.source_span_ids
