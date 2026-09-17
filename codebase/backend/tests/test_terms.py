"""Rút thuật ngữ từ nội dung bài để mớm cho bộ nhận dạng giọng nói.

Bối cảnh: đo thật thấy máy nghe "temperature" thành "template" rồi "computer
cô ta", nghe "LLM" thành "Em". Danh sách này nhắm đúng nhóm từ đó.
"""

from __future__ import annotations

from app.domain.terms import extract_terms

SLIDE = (
    "Model tối ưu cho câu nghe hợp lý, không phải tra sự thật — nên có thể "
    "tự tin mà sai (hallucination). Chuyển sang dùng RAG và tools. "
    "Điều chỉnh temperature để giảm sáng tạo. LLM đoán token tiếp theo."
)


def test_lay_duoc_thuat_ngu_tieng_anh_giua_cau_tieng_viet():
    terms = extract_terms(SLIDE)
    for must in ("hallucination", "temperature", "token", "LLM", "RAG"):
        assert must in terms, f"thiếu {must}: {terms}"


def test_khong_lay_manh_vo_cua_tu_tieng_viet():
    """PyMuPDF tách "Chuyển" thành "Chuy" + "ển"; nếu khớp cả mảnh không dấu
    thì bộ nhận dạng bị mớm toàn ng/nh/ch/th — hại hơn không mớm gì."""
    terms = [t.lower() for t in extract_terms(SLIDE)]
    for junk in ("chuy", "ng", "nh", "ch", "th", "tr", "ph", "gi"):
        assert junk not in terms, f"lọt mảnh vỡ {junk!r}: {terms}"


def test_bo_tu_tieng_viet_von_khong_dau():
    # "trong"/"theo" không dấu thật, nhưng là tiếng Việt thường — mớm vô nghĩa.
    terms = [t.lower() for t in extract_terms("Trong bài này theo quan điểm đó")]
    assert terms == [], terms


def test_giu_viet_tat_ngan_nhung_bo_hu_tu_tieng_anh():
    terms = extract_terms("Dùng AI và ML. We know it does work here or not.")
    assert "AI" in terms and "ML" in terms
    assert not {"we", "it", "or", "not"} & {t.lower() for t in terms}


def test_gop_bien_the_hoa_thuong_lam_mot():
    terms = [t.lower() for t in extract_terms("Token, token và TOKEN nữa")]
    assert terms.count("token") == 1


# --- Cụm thuật ngữ và từ điển theo vùng đang giảng -----------------------------


def test_rut_cum_nhieu_tu_chu_khong_chi_tu_don():
    # Đo thật: với từ điển chỉ gồm từ đơn, "machine learning" ra "Learning",
    # "reward model" ra "report model", "generative AI" mất hẳn.
    from app.domain.terms import extract_phrases

    text = "Machine learning — học từ dữ liệu. Deep learning — mạng nơ-ron. Generative AI — sinh nội dung. ↓ REWARD MODEL máy chấm điểm"
    assert set(extract_phrases(text)) >= {"machine learning", "deep learning", "generative AI", "reward model"}


def test_dong_chu_hoa_dai_cua_so_do_khong_thanh_cum_rac():
    from app.domain.terms import extract_phrases

    assert extract_phrases("ARTIFICIAL INTELLIGENCE MACHINE LEARNING DEEP LEARNING") == ()


def test_cum_toan_viet_tat_khong_tinh():
    from app.domain.terms import extract_phrases

    assert extract_phrases("LLM GPT · Claude · Kimi") == ()


def test_thuat_ngu_cua_vung_dang_giang_dung_dau():
    from app.domain.terms import session_vocabulary

    vocab = session_vocabulary(["Deep learning — mạng nơ-ron nhiều tầng"], ("token", "prompt", "context"))
    assert vocab[0] == "deep learning"
    assert vocab.index("token") > vocab.index("deep learning")


def test_chu_hoa_khong_phai_viet_tat_ha_ve_thuong():
    from app.domain.terms import session_vocabulary

    vocab = session_vocabulary(["ARTIFICIAL MODEL RLHF"], ())
    assert "model" in vocab and "RLHF" in vocab and "MODEL" not in vocab


def test_cach_doc_chi_nhan_am_tiet_tieng_viet():
    from app.api.pronunciations import valid_hint

    assert valid_hint("Mô đồ") == "mô đồ"
    assert valid_hint("mô del") is None  # lẫn chữ tiếng Anh: dạy bộ nhận dạng nghe sai
    assert valid_hint("a b c d e f g") is None  # dài hơn 6 từ Speechmatics tự bỏ
