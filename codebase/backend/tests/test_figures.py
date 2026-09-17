"""Nhận ra hình trên slide — toạ độ lấy đúng từ bộ slide Day 1 (đo bằng PyMuPDF),
không cần file PDF vì data pack không commit được."""

from __future__ import annotations

from app.adapters.knowledge.figures import Shape, find_figures

PAGE = (960.0, 540.0)
BACKGROUND = Shape((0, 0, 960, 540), "rect")


def test_ba_o_chu_co_khung_bo_goc_khong_bi_nhan_nham_la_hinh():
    # Slide 20: ba ô chữ, mỗi ô là một khung bo góc có chữ bên trong.
    shapes = [BACKGROUND, *(Shape((x, 79, x + 289, 190), "rect") for x in (39, 346, 654))]
    lines = [("Bong bóng thời gian", (54, 93, 200, 111)), ("Nói chắc như đúng rồi", (362, 93, 521, 111)), ("Bàn làm việc có hạn", (669, 93, 814, 111))]
    assert find_figures(shapes, lines, PAGE) == []


def test_so_do_vong_tron_long_nhau_thanh_mot_hinh_va_gom_nhan():
    # Slide 3: năm vòng tròn đồng tâm vẽ bằng đường cong, nhãn chữ nằm bên trong.
    circles = [Shape((161, 109, 544, 491), "path"), Shape((199, 146, 506, 454), "path"), Shape((268, 216, 437, 384), "path")]
    lines = [
        ("ARTIFICIAL INTELLIGENCE", (290, 120, 420, 132)),
        ("LLM GPT · Claude · Kimi", (310, 290, 400, 305)),
        ("Machine learning — học từ dữ liệu", (650, 170, 900, 185)),  # chú thích bên cạnh
    ]
    [figure] = find_figures([BACKGROUND, *circles], lines, PAGE)
    assert figure.raster is False
    assert figure.labels == (0, 1)  # chú thích bên ngoài vẫn là ô chữ riêng


def test_anh_chup_la_hinh_con_logo_nho_thi_khong():
    shapes = [Shape((45, 68, 322, 398), "image"), Shape((900, 10, 930, 40), "image")]
    [figure] = find_figures(shapes, [], PAGE)
    assert figure.raster and figure.bbox == (45, 68, 322, 398)


def test_o_chu_nam_trong_vung_so_do_khong_bi_nuot_vao_hinh():
    # Slide 24: vòng lặp vẽ bằng nét, xung quanh là các ô chữ có khung.
    loop = Shape((338, 203, 589, 371), "path")
    card = Shape((500, 165, 660, 228), "rect")
    lines = [("② Reasoning bộ não LLM chia bước", (510, 180, 650, 210)), ("quan sát kết quả → lặp lại", (400, 280, 520, 295))]
    [figure] = find_figures([BACKGROUND, loop, card], lines, PAGE)
    assert figure.labels == (1,)


def test_mui_ten_le_loi_khong_thanh_hinh():
    arrow = Shape((178, 354, 210, 378), "path")
    assert find_figures([BACKGROUND, arrow], [], PAGE) == []
