"""Đồ thị tri thức: đỉnh là trang đã giảng được, cạnh là mối nối đã giảng được (spec §4c).

Luật xương sống được canh ở đây: không có gì vào đồ thị nếu không truy ngược
được về một câu HỌC VIÊN đã nói. Phần lớn test bên dưới còn mang tên một lỗi đo
được thật trên 7 phiên chạy qua WebSocket ngày 18/9 — để chúng không quay lại.
"""

from __future__ import annotations

import asyncio

import pytest

from app.adapters.store.jsonl import JsonGraphStore
from app.api.graph_sync import absorb_link, absorb_turn, known_claims
from app.domain.graph import (
    LABEL_CHARS,
    MAX_SENTENCES,
    KnowledgeGraph,
    Link,
    PageRef,
    page_claim,
    page_key,
    short_label,
    split_key,
)

# Chữ thật của trang 14 bộ d1 — dùng chữ thật để luật lọc câu lạc đề và câu
# chép lại đo đúng thứ nó sẽ gặp khi chạy.
CONTEXT = PageRef(
    key="d1-slide-hackathon:14",
    title="Context: bàn làm việc có hạn của model",
    deck="d1-slide-hackathon",
    page=14,
    span_ids=("[d1-slide-hackathon-p14-01]", "[d1-slide-hackathon-p14-02]"),
    text=(
        "Context: bàn làm việc có hạn của model\n"
        "Mỗi lần trả lời, model chỉ nhìn được một lượng chữ có hạn — gọi là context. "
        "Hãy hình dung một bàn làm việc: mọi thứ muốn model thấy phải bày lên bàn.\n"
        "Context càng dài càng tốn tiền và càng chậm — bàn rộng không có nghĩa là dùng tốt"
    ),
)
TOKEN = PageRef(
    key="d1-slide-hackathon:13",
    title='Token: model không đọc "từ", model đọc mảnh chữ',
    deck="d1-slide-hackathon",
    page=13,
    span_ids=("[d1-slide-hackathon-p13-02]",),
    text=(
        "Model không nhìn từ nguyên vẹn. Nó cắt văn bản thành các mảnh nhỏ gọi là "
        "token: có từ là một mảnh, có từ vỡ ba bốn mảnh. Tiếng Việt tốn token hơn tiếng Anh."
    ),
)

GIANG_CONTEXT = (
    "Context là lượng chữ model nhìn thấy được trong một lần trả lời, giống bộ nhớ tạm có giới hạn. "
    "Context càng dài thì càng tốn tiền và càng chậm, và model hay quên phần nằm ở giữa."
)


def _absorb(g, page, texts, verdict, session="phien-1"):
    return absorb_turn(g, page=page, student_texts=texts, verdict=verdict, session_id=session)


# --- Đỉnh ------------------------------------------------------------------


def test_dinh_la_trang_va_mang_nguyen_van_loi_hoc_vien():
    """Đỉnh là ghi chú bằng lời của chính học viên — không phải lời model diễn
    đạt lại, cũng không phải chữ trên slide."""
    claim, _ = page_claim([GIANG_CONTEXT], CONTEXT, "phien-1")
    assert claim.concept == "d1-slide-hackathon:14"
    assert claim.title == CONTEXT.title
    assert all(cau in GIANG_CONTEXT for cau in claim.sentences)
    assert claim.said in claim.sentences


def test_giang_mot_trang_hai_buoi_thi_trang_sang_va_giu_ca_hai_cach_noi():
    """Lỗi đo được 18/9: giảng context hai buổi, cả hai được chấm đủ, mà bản đồ
    vẫn báo context còn tối — vì câu bị gán khoá "model" và "nghiệp". Theo trang
    thì không có gì để đoán, và buổi sau CỘNG thêm cách nói chứ không ghi đè."""
    g = KnowledgeGraph(student_id="nhan")
    _absorb(g, CONTEXT, [GIANG_CONTEXT], "sufficient", "buoi-1")
    lan_hai = "Model chỉ nhìn được một khoảng chữ nhất định mỗi lần, nhồi thêm thì chậm và đắt hơn."
    _absorb(g, CONTEXT, [lan_hai], "sufficient", "buoi-2")

    assert list(g.claims) == ["d1-slide-hackathon:14"]
    dinh = g.claims["d1-slide-hackathon:14"]
    assert dinh.times_taught == 2
    assert lan_hai.rstrip(".") in dinh.sentences
    assert any("bộ nhớ tạm" in cau for cau in dinh.sentences), "câu buổi đầu bị ghi đè"


def test_trang_khac_khong_ghi_de_len_nhau():
    """Lỗi đo được 18/9: câu RLHF ("cỗ máy đoán token dần biết nghe lời") đè
    lên câu giải thích cơ chế của slide 12 vì cả hai chạm chữ "token"."""
    g = KnowledgeGraph(student_id="nhan")
    _absorb(g, CONTEXT, [GIANG_CONTEXT], "sufficient")
    _absorb(g, TOKEN, ["Model cắt câu ra từng mảnh nhỏ, một chữ tiếng Việt có dấu có thể thành mấy mảnh token"],
            "sufficient")
    assert set(g.claims) == {CONTEXT.key, TOKEN.key}
    assert "bộ nhớ tạm" in " ".join(g.claims[CONTEXT.key].sentences)


def test_doc_lai_nguyen_van_tai_lieu_khong_thanh_dinh():
    """Chép lại slide không phải là hiểu — đúng luật bộ chấm đang dùng."""
    claim, bo_qua = page_claim([CONTEXT.text], CONTEXT, "phien-1")
    assert claim is None
    assert any("nguyên văn" in ly_do for _, ly_do in bo_qua)


def test_cau_lac_de_va_cau_qua_ngan_bi_loai():
    cau_lac_de = "Hôm qua mình đi ăn phở ở quán đầu ngõ rất ngon"
    claim, bo_qua = page_claim([f"{GIANG_CONTEXT} {cau_lac_de}. Đúng rồi."], CONTEXT, "p")
    assert cau_lac_de not in claim.sentences
    ly_do = {l for _, l in bo_qua}
    assert "không nói gì tới nội dung trang này" in ly_do
    assert "quá ngắn để là một mệnh đề" in ly_do


def test_giu_toi_da_so_cau_moi_nhat():
    g = KnowledgeGraph(student_id="nhan")
    for i in range(MAX_SENTENCES + 3):
        _absorb(g, CONTEXT, [f"Context lần {i} là lượng chữ model nhìn thấy được mỗi lần trả lời"],
                "sufficient", f"buoi-{i}")
    cau = g.claims[CONTEXT.key].sentences
    assert len(cau) == MAX_SENTENCES
    assert cau[-1].startswith(f"Context lần {MAX_SENTENCES + 2}")


# --- Khi nào sáng, khi nào tắt ------------------------------------------------


def test_chi_sang_khi_duoc_cham_la_du():
    g = KnowledgeGraph(student_id="nhan")
    _absorb(g, CONTEXT, [GIANG_CONTEXT], "incomplete")
    assert g.claims == {}


def test_lan_sau_chua_du_khong_xoa_cong_suc_buoi_truoc():
    """Chưa đủ không có nghĩa là hiểu sai."""
    g = KnowledgeGraph(student_id="nhan")
    _absorb(g, CONTEXT, [GIANG_CONTEXT], "sufficient", "buoi-1")
    _absorb(g, CONTEXT, ["Context là cái gì đó của model"], "incomplete", "buoi-2")
    assert CONTEXT.key in g.claims


def test_giang_sai_thi_trang_tat_cung_moi_canh_cua_no():
    """Học viên vừa cho thấy mình hiểu sai chính trang đó. Giữ lại thì buổi sau
    học trò mang ra hỏi như thể họ đã dạy đúng."""
    g = KnowledgeGraph(student_id="nhan")
    _absorb(g, CONTEXT, [GIANG_CONTEXT], "sufficient")
    _absorb(g, TOKEN, ["Model cắt chữ thành các mảnh nhỏ gọi là token để đọc"], "sufficient")
    assert g.connect(Link(CONTEXT.key, TOKEN.key, "explained", "context đo bằng token", "p"))

    _absorb(g, CONTEXT, ["Context càng dài thì model càng nhớ tốt, cứ dán hết vào"], "incorrect")
    assert CONTEXT.key not in g.claims
    assert g.links == {}


def test_phien_khong_neo_vao_trang_nao_thi_do_thi_dung_yen():
    g = KnowledgeGraph(student_id="nhan")
    assert _absorb(g, None, [GIANG_CONTEXT], "sufficient") == {}
    assert g.claims == {}


# --- Cạnh ------------------------------------------------------------------


def test_canh_chi_noi_hai_trang_da_giang_duoc():
    g = KnowledgeGraph(student_id="nhan")
    _absorb(g, CONTEXT, [GIANG_CONTEXT], "sufficient")
    assert not g.connect(Link(CONTEXT.key, TOKEN.key, "explained", "...", "p"))


def test_noi_a_voi_b_va_b_voi_a_la_mot_canh():
    g = KnowledgeGraph(student_id="nhan")
    _absorb(g, CONTEXT, [GIANG_CONTEXT], "sufficient")
    _absorb(g, TOKEN, ["Model cắt chữ thành các mảnh nhỏ gọi là token để đọc"], "sufficient")
    g.connect(Link(CONTEXT.key, TOKEN.key, "explained", "lần một", "p1"))
    g.connect(Link(TOKEN.key, CONTEXT.key, "explained", "lần hai", "p2"))
    assert len(g.links) == 1


# --- Nhãn và khoá --------------------------------------------------------------


@pytest.mark.parametrize(
    ("title", "nhan"),
    [
        ("Context: bàn làm việc có hạn của model", "Context"),
        ("Sinh văn bản = đoán → nối vào câu → đoán tiếp", "Sinh văn bản"),
        ("Hệ thống AI = Model + Context + Planning + Tools", "Hệ thống AI"),
        ("Lịch sử AI 70 năm", "Lịch sử AI 70 năm"),
        # Dòng thời gian: năm trơ trọi không nói được trang dạy gì.
        ("1980: Hệ chuyên gia (expert system)", "1980 Hệ chuyên gia"),
        ("AI IN ACTION - Day 1", "AI IN ACTION"),
    ],
)
def test_nhan_ngan_lay_ten_trang(title, nhan):
    assert short_label(title) == nhan


def test_nhan_dai_bi_cat_o_ranh_gioi_tu():
    nhan = short_label("Tìm đúng vấn đề trước khi tìm giải pháp")
    assert nhan.endswith("…")
    assert len(nhan) <= LABEL_CHARS + 1


def test_khoa_trang_doc_nguoc_duoc_ca_khi_ma_bo_slide_co_gach():
    assert split_key(page_key("d1-slide-hackathon", 14)) == ("d1-slide-hackathon", 14)


# --- Lưu trữ và câu hỏi bắc cầu -----------------------------------------------


def test_luu_roi_doc_lai_giu_nguyen_moi_cau(tmp_path):
    async def main():
        store = JsonGraphStore(tmp_path / "g.json")
        g = KnowledgeGraph(student_id="nhan")
        _absorb(g, CONTEXT, [GIANG_CONTEXT], "sufficient")
        await store.save(g)
        doc = await store.load("nhan")
        assert doc.claims == g.claims

    asyncio.run(main())


def test_doc_duoc_file_ghi_truoc_khi_co_truong_sentences(tmp_path):
    import json

    path = tmp_path / "g.json"
    path.write_text(json.dumps({"nhan": {"claims": [
        {"concept": "token", "said": "câu cũ", "span_ids": [], "sessions": ["p"]}
    ], "links": []}}), encoding="utf-8")
    g = asyncio.run(JsonGraphStore(path).load("nhan"))
    assert g.claims["token"].sentences == ("câu cũ",)


def test_bac_cau_dua_ten_trang_va_cau_cua_hoc_vien():
    g = KnowledgeGraph(student_id="nhan")
    _absorb(g, CONTEXT, [GIANG_CONTEXT], "sufficient")
    da_day = known_claims(g, ["[d1-slide-hackathon-p99-01]"])
    assert da_day == [{"concept": CONTEXT.title, "said": g.claims[CONTEXT.key].said}]


# --- Phiên nối hai trang -------------------------------------------------------

NOI = (
    "Context dài thì model phải đọc nhiều token hơn, mà token là đơn vị tính tiền, "
    "nên dán cả tài liệu vào vừa chậm vừa tốn. Ngoài ra hôm nay trời đẹp quá bạn ạ."
)


def _hai_trang_sang():
    g = KnowledgeGraph(student_id="nhan")
    _absorb(g, CONTEXT, [GIANG_CONTEXT], "sufficient")
    _absorb(g, TOKEN, ["Model cắt chữ thành các mảnh nhỏ gọi là token để đọc"], "sufficient")
    return g


def _noi(g, texts, verdict):
    return absorb_link(g, a=CONTEXT, b=TOKEN, student_texts=texts, verdict=verdict, session_id="noi-1")


def test_noi_duoc_thi_sinh_canh_mang_cau_cham_ca_hai_trang():
    """Bằng chứng của cạnh là câu nói tới CẢ HAI trang — câu thật sự nối."""
    g = _hai_trang_sang()
    _noi(g, [NOI], "sufficient")
    (canh,) = g.links.values()
    assert {canh.source, canh.target} == {CONTEXT.key, TOKEN.key}
    assert "token" in canh.evidence and "Context" in canh.evidence
    assert "trời đẹp" not in canh.evidence


def test_noi_chua_toi_thi_khong_co_canh():
    g = _hai_trang_sang()
    _noi(g, ["Hai trang này liên quan tới nhau vì đều nói về AI"], "incomplete")
    assert g.links == {}


def test_noi_sai_khong_tat_hai_trang():
    """Hiểu sai cách hai trang liên quan không có nghĩa là hiểu sai từng trang."""
    g = _hai_trang_sang()
    _noi(g, ["Context càng dài thì càng ít token nên càng rẻ"], "incorrect")
    assert g.links == {}
    assert {CONTEXT.key, TOKEN.key} <= set(g.claims)


def test_khong_noi_duoc_trang_chua_giang():
    g = KnowledgeGraph(student_id="nhan")
    _absorb(g, CONTEXT, [GIANG_CONTEXT], "sufficient")
    _noi(g, [NOI], "sufficient")
    assert g.links == {}


def test_prompt_cham_moi_noi_nap_duoc_kem_san_an_toan():
    from app.graph.nodes import GRADER_LINK_VERSION
    from app.prompts import registry

    system = registry.compose_system("grader_link", GRADER_LINK_VERSION, [])
    assert "MỐI NỐI" in system and "SÀN AN TOÀN" in system
