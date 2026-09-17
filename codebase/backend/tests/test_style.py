"""Văn phong lời agent: những luật chặn bằng code sau khi prompt dặn không đủ."""

from __future__ import annotations

import asyncio

from app.domain.sanitize import tame_shouting
from app.graph.nodes import _heard, _reanchor, close_review, close_taught


def test_ha_chu_hoa_ca_cum_nhung_giu_viet_tat():
    # Đo được thật: agent chép nguyên "REWARD MODEL" từ slide vào câu nói.
    assert tame_shouting("Mình chưa rõ REWARD MODEL lấy điểm ở đâu") == "Mình chưa rõ reward model lấy điểm ở đâu"
    assert tame_shouting("LLM được huấn luyện bằng RLHF") == "LLM được huấn luyện bằng RLHF"
    assert tame_shouting("AI ML") == "AI ML"


UNCOVERED = "Reward model học cách chấm điểm thay người, rồi điểm đó dùng để tối ưu model"
STUDENT = "người chấm cho điểm, câu nào đúng thì được cộng điểm"


def test_y_minh_hieu_la_nhac_lai_loi_hoc_vien_thi_giu():
    assert _heard(["Người chấm cho điểm từng câu trả lời"], UNCOVERED, STUDENT) == [
        "Người chấm cho điểm từng câu trả lời"
    ]


def test_y_minh_hieu_la_noi_ho_tu_khoa_chua_ai_noi_thi_bo():
    # "reward model", "tối ưu" — học viên chưa hề nói ra. Diễn đạt lại "cho gọn"
    # bằng chính từ khoá của nguồn là nói hộ đáp án.
    kept = _heard(
        ["Người chấm cho điểm", "Reward model học chấm điểm rồi tối ưu model"], UNCOVERED, STUDENT
    )
    assert kept == ["Người chấm cho điểm"]


def test_toi_da_ba_y_va_bo_dong_rong():
    kept = _heard(["a b c", "", "d e f", "g h i", "j k l"], "", "")
    assert kept == ["a b c", "d e f", "g h i"]


def test_cau_du_phong_khong_lap_nguyen_van_hai_lan_lien():
    # Quan sát thật: học viên nghe y nguyên một câu dự phòng hai ba lần liền.
    first = _reanchor({"asked_questions": ["q1"]})
    second = _reanchor({"asked_questions": ["q1", "q2"]})
    assert first != second


def test_cau_chot_khong_mang_theo_y_cua_luot_truoc():
    # State của LangGraph giữ nguyên trường cũ qua các lượt: node nào đặt
    # agent_says mà quên đặt agent_understood thì gạch đầu dòng lượt trước
    # dính sang câu chốt.
    assert asyncio.run(close_taught({}))["agent_understood"] == []
    assert asyncio.run(close_review({}))["agent_understood"] == []


def test_cau_du_phong_khong_tu_mau_thuan_voi_y_vua_liet_ke():
    # Vừa hiện "Mình hiểu là: …" ngay trên, mà câu hỏi lại là "mình chưa theo
    # kịp đoạn vừa rồi" — nghe như không hề nghe học viên nói gì.
    after_bullets = _reanchor({"asked_questions": ["q1"]}, heard=True)
    assert "chưa theo kịp" not in after_bullets


VOCAB = ["model", "LLM", "RLHF", "reward", "token"]


def test_y_chep_lai_chu_may_nghe_nham_thi_bo():
    # Đo được thật: học viên nói "model", máy nghe thành "JSON", "button"; agent
    # chép nguyên vào "Mình hiểu là: người chấm dùng JSON/button để cho điểm".
    kept = _heard(
        ["Người chấm dùng JSON/button để cho điểm", "Model học từ điểm được cộng hoặc trừ"],
        "", "", vocabulary=VOCAB,
    )
    assert kept == ["Model học từ điểm được cộng hoặc trừ"]


def test_viet_tat_that_cua_bai_van_giu():
    assert _heard(["LLM được chỉnh bằng RLHF"], "", "", vocabulary=VOCAB) == ["LLM được chỉnh bằng RLHF"]


def test_gach_cheo_doi_thanh_chu_hoac():
    assert _heard(["Câu đúng được cộng/trừ điểm"], "", "", vocabulary=VOCAB) == ["Câu đúng được cộng hoặc trừ điểm"]


def test_tu_tieng_viet_khong_dau_khong_bi_coi_la_chu_la():
    # Bản đầu coi mọi chữ không dấu là tiếng Anh, bỏ nhầm một ý hoàn toàn đúng.
    point = "Điểm chấm người ta cộng cho câu đúng và trừ cho câu sai"
    assert _heard([point], "", "", vocabulary=VOCAB) == [point]


def test_ha_chu_hoa_khi_di_kem_viet_tat_ngan():
    # Đo được thật: "GENERATIVE AI" lọt qua bản đầu vì "AI" chỉ có 2 ký tự.
    assert tame_shouting("vòng GENERATIVE AI nằm ngoài LLM") == "vòng generative AI nằm ngoài LLM"
    assert tame_shouting("dữ liệu dạng JSON") == "dữ liệu dạng JSON"
