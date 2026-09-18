"""Mức hiểu từng trang slide (domain/progress.py).

Mức hiểu chỉ đi lên nhờ kết quả chấm thật, và phải khớp với bản đồ hiểu biết:
"đã hiểu" trở lên đúng bằng đỉnh sáng, giảng sai thì "cần sửa".
"""

from __future__ import annotations

import asyncio

from app.adapters.store.jsonl import JsonProgressStore
from app.domain.progress import Progress

TRANG = "d1-slide-hackathon:14"


def _p(*luot):
    """luot: (buổi, nhãn) theo thứ tự."""
    prog = Progress(student_id="nhan")
    for i, (buoi, nhan) in enumerate(luot):
        prog.record(TRANG, buoi, nhan, f"2026-09-18T10:{i:02d}:00+07:00")
    return prog.pages[TRANG]


def test_chua_giang_lan_nao_la_chua_hoc():
    assert Progress(student_id="nhan").pages.get(TRANG) is None


def test_thu_ma_chua_du_la_dang_hoc():
    assert _p(("b1", "incomplete")).level == "dang_hoc"


def test_du_o_mot_buoi_la_da_hieu():
    assert _p(("b1", "incomplete"), ("b1", "sufficient")).level == "da_hieu"


def test_du_o_hai_buoi_khac_nhau_moi_la_vung():
    """Giảng được ngay sau khi vừa đọc có thể chỉ là nhớ ngắn hạn."""
    assert _p(("b1", "sufficient"), ("b1", "sufficient")).level == "da_hieu"
    assert _p(("b1", "sufficient"), ("b2", "sufficient")).level == "vung"


def test_da_hieu_roi_ma_giang_sai_thi_can_sua():
    """Khớp với bản đồ: giảng sai thì đỉnh tắt, ở đây trang thành cần sửa."""
    assert _p(("b1", "sufficient"), ("b2", "sufficient"), ("b3", "incorrect")).level == "can_sua"


def test_sai_roi_tu_sua_ngay_trong_buoi_thi_het_can_sua():
    assert _p(("b1", "incorrect"), ("b1", "sufficient")).level == "da_hieu"


def test_mot_buoi_nhieu_luot_van_dem_la_mot_buoi():
    pp = _p(("b1", "incomplete"), ("b1", "incomplete"), ("b1", "incomplete"))
    assert len(pp.sessions) == 1


def test_luu_roi_doc_lai_giu_nguyen(tmp_path):
    async def main():
        store = JsonProgressStore(tmp_path / "p.json")
        prog = Progress(student_id="nhan")
        prog.record(TRANG, "b1", "sufficient", "2026-09-18T10:00:00+07:00")
        await store.save(prog)
        doc = await store.load("nhan")
        assert doc.pages == prog.pages
        assert (await store.load("nguoi-khac")).pages == {}

    asyncio.run(main())
