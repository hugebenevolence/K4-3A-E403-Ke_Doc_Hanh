"""Ghép block của slide thành ô nội dung.

Dùng toạ độ giả lập đúng theo layout thật của slide khoá (tiêu đề rộng trên
cùng, ba cột nội dung, một footer) — không phụ thuộc file PDF, vì slide thật
nằm trong data pack không commit được.

Hai bug đã gặp thật, test này canh không cho tái diễn.
"""

from __future__ import annotations

from app.adapters.knowledge.pdf import _merge

# (x0, y0, x1, y1, text, block_no, block_type) — đúng dạng PyMuPDF trả về.
TIEU_DE = (38, 20, 519, 48, "Giới hạn bẩm sinh", 0, 0)
COT1_A = (54, 93, 200, 111, "Bong bóng thời gian", 1, 0)
COT1_B = (54, 119, 309, 134, "Model bị đóng băng tại ngày ngừng đọc.", 2, 0)
COT2_A = (362, 93, 521, 111, "Nói chắc như đúng rồi", 3, 0)
COT2_B = (362, 119, 609, 134, "Model tối ưu cho câu nghe hợp lý.", 4, 0)
COT3_A = (669, 93, 814, 111, "Bàn làm việc có hạn", 5, 0)
FOOTER = (38, 514, 582, 527, "Biết nhiều khác làm được", 6, 0)

ALL = [TIEU_DE, COT1_A, COT1_B, COT2_A, COT2_B, COT3_A, FOOTER]


def _texts(blocks):
    return [t for t, _ in _merge(blocks)]


def test_ba_cot_khong_bi_tron_vao_nhau():
    """Bug 1: gom cột theo độ chồng bề ngang thì block tiêu đề rộng bắc cầu
    dính hai cột lại, ra câu vô nghĩa kiểu 'Nói chắc như đúng rồi Model bị
    đóng băng'."""
    joined = " | ".join(_texts(ALL))
    assert "Nói chắc như đúng rồi Model bị đóng băng" not in joined
    assert any("Nói chắc như đúng rồi" in t and "nghe hợp lý" in t for t in _texts(ALL))


def test_footer_khong_bi_dan_vao_tieu_de_cot():
    """Bug 2: sort theo x trước rồi so khoảng cách dọc thì footer (y=514) đứng
    trước tiêu đề cột (y=93) cho khoảng cách ÂM, luôn lọt ngưỡng và dính vào."""
    footer = [t for t in _texts(ALL) if "Biết nhiều" in t]
    assert footer == ["Biết nhiều khác làm được"], footer


def test_cac_dong_lien_nhau_trong_mot_cot_van_duoc_ghep():
    # Ghép được mới là mục đích chính; không ghép thì mỗi span là nửa câu.
    assert _texts([COT1_A, COT1_B]) == ["Bong bóng thời gian Model bị đóng băng tại ngày ngừng đọc."]


def test_block_cach_xa_nhau_thi_khong_ghep():
    assert len(_texts([COT1_A, FOOTER])) == 2
