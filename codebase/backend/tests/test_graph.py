"""Đồ thị tri thức: luật vào/ra của đỉnh và cạnh (spec §4c).

Luật xương sống được canh ở đây: không có gì vào đồ thị nếu không truy ngược
được về một câu HỌC VIÊN đã nói. Mọi test dưới đây đều là một cách phá luật đó.
"""

from __future__ import annotations

from app.domain.graph import (
    Claim,
    KnowledgeGraph,
    Link,
    claims_from_turn,
    links_from_turn,
)

# Nguyên văn ô nội dung của slide 13 (bộ d1) — cố ý dùng chữ thật thay vì
# fixture tự bịa: ô thật nhắc "token" nhiều lần nên nó mới là chủ đề của ô, còn
# fixture bịa một lần thì hoà tần suất với "model" và test đo nhầm thứ khác.
TOKEN = (
    "[d1-p13-02]",
    "Model không nhìn từ nguyên vẹn. Nó cắt văn bản thành các mảnh nhỏ gọi là "
    "token: có từ là một mảnh, có từ vỡ ba bốn mảnh, cả dấu câu và khoảng trắng "
    "cũng là token. Tiếng Việt, code và JSON tốn token hơn tiếng Anh.",
)
ATTENTION = (
    "[d1-p15-01]",
    "Attention: mỗi token nhìn sang các token trước và chấm điểm mức liên quan.",
)


def test_dinh_mang_nguyen_van_cau_cua_hoc_vien():
    """Đỉnh là ghi chú bằng lời của chính học viên — không phải lời model diễn
    đạt lại, cũng không phải chữ trên slide."""
    cau = "Model cắt chữ thành các mảnh nhỏ gọi là token chứ không đọc nguyên từ"
    claims, _ = claims_from_turn(cau, [TOKEN], "phien-1")
    assert [c.concept for c in claims] == ["token"]
    assert claims[0].said == cau
    assert claims[0].span_ids == ("[d1-p13-02]",)


def test_doc_lai_nguyen_van_tai_lieu_khong_thanh_dinh():
    """Chép lại slide không phải là hiểu — đúng luật bộ chấm đang dùng."""
    claims, bo_qua = claims_from_turn(TOKEN[1], [TOKEN], "phien-1")
    assert claims == []
    assert any("nguyên văn" in ly_do for _, ly_do in bo_qua)


def test_cau_khong_neo_duoc_vao_nguon_thi_khong_thanh_dinh():
    """Nói đúng chủ đề chung chung mà không chạm ô nguồn nào đã chấm là đã nói
    tới thì không có gì để neo — đồ thị rỗng còn hơn đồ thị bịa."""
    claims, bo_qua = claims_from_turn(
        "Cái này thì em thấy nó cũng hay và khá là dễ hiểu", [TOKEN], "phien-1"
    )
    assert claims == []
    assert bo_qua


def test_mot_khai_niem_mot_dinh_trong_cung_mot_luot():
    """Hai câu cùng nói về token thì giữ câu neo chắc hơn, không để câu sau đè
    câu trước chỉ vì nó đứng sau."""
    loi = (
        "Model cắt văn bản thành các mảnh nhỏ gọi là token. "
        "Tiếng Việt thì tốn token hơn tiếng Anh."
    )
    claims, bo_qua = claims_from_turn(loi, [TOKEN], "phien-1")
    assert len(claims) == 1
    assert "cắt văn bản" in claims[0].said
    assert any("neo chắc hơn" in ly_do for _, ly_do in bo_qua)


def test_canh_chi_sinh_ra_tu_lien_tu_cua_chinh_hoc_vien():
    loi = "Model chỉ đoán token tiếp theo thôi. Nhờ vậy attention biết token nào đáng nhìn."
    claims, _ = claims_from_turn(loi, [TOKEN, ATTENTION], "phien-1")
    links = links_from_turn(loi, claims, "phien-1")
    assert [(l.source, l.target, l.kind) for l in links] == [("token", "attention", "cause")]
    # Bằng chứng phải là câu THẬT của học viên, để sau còn kiểm được.
    assert links[0].evidence in loi


def test_khong_co_lien_tu_thi_khong_co_canh():
    """Nói hai ý cạnh nhau KHÔNG phải là nối chúng. Tự nối hộ thì đồ thị không
    còn là bản đồ hiểu biết của học viên nữa."""
    loi = "Model đoán token tiếp theo. Attention chấm điểm mức liên quan."
    claims, _ = claims_from_turn(loi, [TOKEN, ATTENTION], "phien-1")
    assert links_from_turn(loi, claims, "phien-1") == []


def test_cung_khai_niem_o_hai_bai_nhap_vao_mot_dinh():
    """Phạm vi xuyên tài liệu: đây là chỗ học viên thấy Day 1 dính vào Day 2."""
    g = KnowledgeGraph(student_id="nhan")
    g.absorb(Claim("token", "Model cắt chữ thành mảnh", ("[d1-p13-02]",), ("phien-1",)))
    g.absorb(Claim("token", "Prompt dài thì tốn token", ("[d2-p09-01]",), ("phien-2",)))

    assert list(g.claims) == ["token"]
    assert g.claims["token"].span_ids == ("[d1-p13-02]", "[d2-p09-01]")
    assert g.claims["token"].times_taught == 2


def test_day_sai_roi_tu_sua_thi_thay_chu_khong_chong_them():
    """Case R02. Giữ cả hai là đồ thị tích lại chính hiểu lầm của học viên."""
    g = KnowledgeGraph(student_id="nhan")
    g.absorb(Claim("token", "Mỗi token là một từ", ("[d1-p13-02]",), ("phien-1",)))
    viec = g.absorb(Claim("token", "À không, token là mảnh chữ", ("[d1-p13-02]",), ("phien-1",)))

    assert viec == "sửa lời"
    assert g.claims["token"].said == "À không, token là mảnh chữ"
    assert g.claims["token"].times_taught == 1


def test_canh_khong_noi_vao_dinh_chua_ton_tai():
    g = KnowledgeGraph(student_id="nhan")
    g.absorb(Claim("token", "Model cắt chữ thành mảnh", ("[d1-p13-02]",), ("phien-1",)))
    assert not g.connect(Link("token", "attention", "cause", "câu nào đó"))
    assert g.links == {}


def test_hieu_sai_thi_dinh_bi_go_cung_moi_canh_cua_no():
    """Đồ thị được phép rỗng, nhưng không được phép sai: một đỉnh sai nằm lại sẽ
    được học trò mang ra hỏi ở buổi sau như thể học viên đã dạy đúng."""
    g = KnowledgeGraph(student_id="nhan")
    g.absorb(Claim("token", "Model cắt chữ thành mảnh", ("[d1-p13-02]",), ("phien-1",)))
    g.absorb(Claim("attention", "Mỗi token nhìn lại token trước", ("[d1-p15-01]",), ("phien-1",)))
    g.connect(Link("token", "attention", "cause", "nhờ vậy attention biết nhìn đâu"))

    assert g.forget("token")
    assert list(g.claims) == ["attention"]
    assert g.links == {}
    assert g.taught_span_ids == {"[d1-p15-01]"}


# --- Nối vào một lượt chấm thật -----------------------------------------------


def test_o_bi_danh_dau_noi_trai_thi_khai_niem_o_do_bi_go():
    """Học viên vừa chứng minh mình hiểu sai chỗ đó. Giữ lại thì buổi sau học
    trò mang ra hỏi như thể họ đã dạy đúng."""
    import asyncio

    from app.adapters.knowledge.local import InMemorySpanStore
    from app.api.graph_sync import absorb_turn
    from app.domain.span import Span

    async def main():
        store = InMemorySpanStore([Span(TOKEN[0], TOKEN[1]), Span(*ATTENTION)])
        g = KnowledgeGraph(student_id="nhan")
        g.absorb(Claim("token", "Mỗi token là một từ", (TOKEN[0],), ("phien-0",)))

        await absorb_turn(
            g,
            store,
            student_text="Mỗi token là một từ mà, em nghĩ vậy",
            evidence=[{"span_id": TOKEN[0], "covered_by_student": True,
                       "contradicted_by_student": True}],
            session_id="phien-1",
        )
        assert "token" not in g.claims

    asyncio.run(main())


def test_chi_o_da_duoc_cham_la_da_noi_toi_moi_sinh_dinh():
    import asyncio

    from app.adapters.knowledge.local import InMemorySpanStore
    from app.api.graph_sync import absorb_turn
    from app.domain.span import Span

    async def main():
        store = InMemorySpanStore([Span(TOKEN[0], TOKEN[1]), Span(*ATTENTION)])
        g = KnowledgeGraph(student_id="nhan")
        bao_cao = await absorb_turn(
            g,
            store,
            student_text="Model cắt chữ thành các mảnh nhỏ gọi là token chứ không đọc nguyên từ",
            # Ô attention CHƯA được nói tới: không được sinh đỉnh nào cho nó.
            evidence=[
                {"span_id": TOKEN[0], "covered_by_student": True, "contradicted_by_student": False},
                {"span_id": ATTENTION[0], "covered_by_student": False, "contradicted_by_student": False},
            ],
            session_id="phien-1",
        )
        assert list(g.claims) == ["token"]
        assert bao_cao["đã làm"] == {"thêm mới": ["token"]}

    asyncio.run(main())


def test_o_cu_bi_danh_sai_khong_xoa_y_vua_giang_lai_dung():
    """Một đỉnh gom nhiều ô qua nhiều buổi. Chỉ cần một ô CŨ bị đánh dấu nói
    trái mà xoá luôn mệnh đề họ vừa giảng lại đúng ở ô khác thì học viên mất
    thành quả vì một lỗi họ đã sửa xong."""
    import asyncio

    from app.adapters.knowledge.local import InMemorySpanStore
    from app.api.graph_sync import absorb_turn
    from app.domain.span import Span

    async def main():
        store = InMemorySpanStore([Span(TOKEN[0], TOKEN[1]), Span(*ATTENTION)])
        g = KnowledgeGraph(student_id="nhan")
        g.absorb(Claim("token", "Mỗi token là một từ", (ATTENTION[0],), ("phien-0",)))

        bao_cao = await absorb_turn(
            g,
            store,
            student_text="Máy băm câu ra thành từng miếng nhỏ, mỗi miếng đó người ta gọi là token",
            evidence=[
                # Vừa giảng lại ĐÚNG ở ô này…
                {"span_id": TOKEN[0], "covered_by_student": True, "contradicted_by_student": False},
                # …trong khi ô cũ vẫn bị đánh dấu là nói trái.
                {"span_id": ATTENTION[0], "covered_by_student": False, "contradicted_by_student": True},
            ],
            session_id="phien-1",
        )
        assert "token" in g.claims, bao_cao
        assert "gỡ" not in bao_cao["đã làm"]

    asyncio.run(main())
