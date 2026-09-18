"""Canh hai lỗi rò mà AskTIM đã gặp trên production — ở đây nặng hơn vì đầu ra
đi thẳng vào TTS và sẽ được đọc thành tiếng."""

from __future__ import annotations

import pytest

from app.domain.sanitize import sanitize_spoken, soften_punctuation, speakable


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


# --- Dấu ghép ý: nghe được khi đọc thành tiếng ---------------------------------


def test_gach_dai_ghep_hai_y_thanh_dau_phay():
    """Câu thật học viên chê khó nghe (18/9)."""
    cau = "Mình chưa rõ: nguồn tách Generative AI và LLM — bạn giải giúp chỗ đó được không?"
    assert "—" not in soften_punctuation(cau)
    assert "LLM, bạn giải giúp" in soften_punctuation(cau)


def test_dau_hai_cham_giu_nguyen_vi_ten_trang_co_no():
    assert soften_punctuation("RLHF: ba bước uốn cỗ máy") == "RLHF: ba bước uốn cỗ máy"


def test_dau_trang_tri_va_dau_phay_thua_bi_don():
    assert soften_punctuation("Bạn nói *context*, — vậy sao?") == "Bạn nói context, vậy sao?"
    assert soften_punctuation("hai ý; ba ý — bốn ý.") == "hai ý, ba ý, bốn ý."


def test_speakable_gop_ca_ba_buoc():
    assert speakable('{"question": "REWARD MODEL học gì — bạn nói giúp mình?"}') == (
        "reward model học gì, bạn nói giúp mình?"
    )
