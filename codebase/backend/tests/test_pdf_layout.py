"""Ghép các dòng của slide thành ô nội dung.

Dùng toạ độ và cỡ chữ lấy đúng từ slide 20 của bộ slide Day 1 (đo bằng
PyMuPDF) — không phụ thuộc file PDF, vì slide thật nằm trong data pack không
commit được.

Bốn bug đã gặp thật, test này canh không cho tái diễn.
"""

from __future__ import annotations

from app.adapters.knowledge.pdf import Line, _group, _shape

PAGE_HEIGHT = 540.0

TIEU_DE = Line("Giới hạn bẩm sinh: học giả trong bong bóng", (38, 20, 519, 48), 24)
COT1_A = Line("Bong bóng thời gian", (54, 93, 200, 111), 15)
COT1_B = Line('Model bị "đóng băng" tại ngày ngừng đọc.', (54, 119, 309, 134), 12)
COT2_A = Line("Nói chắc như đúng rồi", (362, 93, 521, 111), 15)
COT2_B = Line("Model tối ưu cho câu nghe hợp lý, không", (362, 119, 609, 134), 12)
COT2_C = Line("phải tra sự thật — nên có thể tự tin mà sai", (362, 138, 612, 154), 12)
COT3_A = Line("Bàn làm việc có hạn", (669, 93, 814, 111), 15)
TRICH = Line('"Why does it work? We don\'t know."', (157, 282, 798, 311), 18)
# Câu căn giữa xuống dòng: dòng hai bắt đầu ở x khác hẳn dòng một.
CALLOUT_1 = Line("Đây không phải lỗi tạm thời — đó là bản chất của cỗ máy đoán token. Vì vậy ta cần prompt tốt, context sạch, tra", (120, 359, 843, 375), 12)
CALLOUT_2 = Line("sổ (RAG), tools, và luôn kiểm chứng.", (363, 375, 600, 391), 12)
FOOTER = Line("Biết nhiều khác làm được", (38, 514, 582, 527), 11)

ALL = [TIEU_DE, COT1_A, COT1_B, COT2_A, COT2_B, COT2_C, COT3_A, TRICH, CALLOUT_1, CALLOUT_2, FOOTER]


def _texts(lines):
    return [" ".join(ln.text for ln in g) for g in _group(lines, PAGE_HEIGHT)]


def test_cau_can_giua_xuong_dong_khong_bi_cat_doi():
    """Bug 3: gom theo mép trái thì dòng hai của câu căn giữa bị xếp sang cột
    khác. Slide 20 mất nửa câu, và bộ chấm chấm học viên theo một câu cụt."""
    callout = [t for t in _texts(ALL) if "cỗ máy đoán token" in t]
    assert callout == [f"{CALLOUT_1.text} {CALLOUT_2.text}"]


def test_tieu_de_trang_tach_rieng_khong_dan_vao_o_dau():
    """Bug 4: tiêu đề nằm sát ô đầu tiên, lệch mép trái chỉ 16 điểm, từng bị
    dán vào ô đó."""
    groups = _texts(ALL)
    assert groups[0] == TIEU_DE.text
    assert not any(TIEU_DE.text in t and "Bong bóng thời gian" in t for t in groups)


def test_ba_cot_khong_bi_tron_vao_nhau():
    """Bug 1: một dòng rộng bắc cầu dính hai cột lại, ra câu vô nghĩa kiểu
    'Nói chắc như đúng rồi Model bị đóng băng'."""
    groups = _texts(ALL)
    assert not any("Nói chắc" in t and "đóng băng" in t for t in groups)
    assert f"{COT2_A.text} {COT2_B.text} {COT2_C.text}" in groups


def test_cot_ben_canh_khong_dinh_vao_dong_rong_phia_tren():
    # Một dòng rộng ngay trên hai cột: cột trái có thể nhận nó, cột phải thì
    # không bao giờ được nhận cùng.
    rong = Line("Ba giới hạn bẩm sinh của một cỗ máy đoán chữ tiếp theo", (54, 60, 900, 76), 12)
    groups = _texts([rong, COT1_B, COT2_B])
    assert not any("đóng băng" in t and "nghe hợp lý" in t for t in groups)


def test_footer_khong_bi_dan_vao_o_nao():
    """Bug 2: footer nằm cách xa mọi ô vẫn từng bị dán vào tiêu đề cột."""
    assert FOOTER.text in _texts(ALL)


def test_cau_trich_co_chu_lon_khong_nuot_doan_chu_nho_ben_duoi():
    groups = _texts(ALL)
    assert TRICH.text in groups


def test_cac_dong_lien_nhau_trong_mot_o_van_duoc_ghep():
    assert _texts([COT1_A, COT1_B]) == [f"{COT1_A.text} {COT1_B.text}"]


def test_chan_trang_doi_so_trang_van_nhan_ra_la_cung_mot_thu():
    # Đếm nguyên văn thì "DAY 02 · 37 / 83" và "DAY 02 · 38 / 83" là hai chữ
    # khác nhau, không bao giờ lặp đủ nhiều để bị lọc.
    assert _shape("DAY 02 · 37 / 83") == _shape("DAY 02 · 38 / 83")
    assert _shape("Bong bóng thời gian") != _shape("Nói chắc như đúng rồi")


def test_tieu_de_trang_nhan_ra_rieng_de_lam_dan_y():
    from app.adapters.knowledge.pdf import _title_lines

    assert _title_lines(ALL, PAGE_HEIGHT) == [TIEU_DE]
    # Trang không có tiêu đề thì không bịa ra tiêu đề từ ô nội dung.
    assert _title_lines([COT1_A, COT1_B, COT2_A], PAGE_HEIGHT) == []
