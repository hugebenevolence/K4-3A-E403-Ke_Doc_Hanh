"""Canh hai lỗi rò mà AskTIM đã gặp trên production — ở đây nặng hơn vì đầu ra
đi thẳng vào TTS và sẽ được đọc thành tiếng."""

from __future__ import annotations

import pytest

from app.domain.sanitize import sanitize_spoken


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Mode B: thẻ tool bịa ra bám đuôi câu trả lời hợp lệ
        ("Chỗ đó vì sao vậy bạn?</invoke>", "Chỗ đó vì sao vậy bạn?"),
        ("Bạn nói thêm đi.</parameter>\n</invoke>", "Bạn nói thêm đi."),
        ("<question>Sao lại thế?</question>", "Sao lại thế?"),
        # Mode A: cả bọc JSON bị đổ ra thay vì mỗi phần lời nói
        ('{"question": "Cái đó bắt đầu từ đâu?", "cites_span_id": null}', "Cái đó bắt đầu từ đâu?"),
        ('{"agent_says": "Mình hiểu rồi!"}', "Mình hiểu rồi!"),
    ],
)
def test_loc_duoc_rac_truoc_khi_doc_thanh_tieng(raw, expected):
    assert sanitize_spoken(raw) == expected


@pytest.mark.parametrize(
    "clean",
    [
        "Ừm, để mình nắm lại ý bạn vừa nói.",
        "Vậy 3 < 5 thì sao bạn?",  # dấu < thường không được nhầm thành thẻ
        "Bạn giải thích thêm giúp mình chỗ [T06-138] nhé?",
    ],
)
def test_khong_dung_vao_cau_sach(clean):
    assert sanitize_spoken(clean) == clean


def test_khong_bao_gio_raise():
    for junk in ("", "{", '{"khong_co_field": 1}', "{]"):
        assert isinstance(sanitize_spoken(junk), str)
