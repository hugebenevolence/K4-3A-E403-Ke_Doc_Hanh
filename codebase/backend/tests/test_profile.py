"""Trí nhớ xuyên phiên: hồ sơ theo học viên, không theo phiên.

Đây là thứ phân biệt "nhớ trong một buổi" (checkpointer lo) với "theo học viên
qua nhiều buổi" (hồ sơ lo). Thiếu vế sau thì mỗi buổi agent lại gặp học viên
như người lạ.
"""

from __future__ import annotations

import asyncio
import json

from app.adapters.store.jsonl import JsonProfileStore
from app.domain.verdict import Evidence, GradeResult, Verdict


def _grade(*span_ids: str) -> GradeResult:
    return GradeResult(
        verdict=Verdict.INCOMPLETE,
        evidence=tuple(Evidence(s, "trích", covered_by_student=False) for s in span_ids),
        gap_summary="thiếu nguyên nhân",
    )


def test_cho_hong_lap_lai_duoc_dem_don_qua_cac_buoi(tmp_path):
    async def main():
        store = JsonProfileStore(tmp_path / "profiles.json")

        for _ in range(3):
            profile = await store.load("nhan")  # mỗi vòng = một buổi mới
            profile.absorb("vì sao LLM bịa", _grade("[T06-138]"))
            await store.save(profile)

        profile = await store.load("nhan")
        assert profile.recurring_gaps["[T06-138]"] == 3
        assert profile.concepts_taught["vì sao LLM bịa"] == "incomplete"

    asyncio.run(main())


def test_ho_so_cua_hai_hoc_vien_khong_lan_vao_nhau(tmp_path):
    async def main():
        store = JsonProfileStore(tmp_path / "profiles.json")
        for who in ("an", "binh"):
            p = await store.load(who)
            p.absorb("khái niệm", _grade(f"[span-{who}]"))
            await store.save(p)

        an = await store.load("an")
        assert list(an.recurring_gaps) == ["[span-an]"]

    asyncio.run(main())


def test_hoc_vien_moi_thi_ho_so_rong_chu_khong_loi(tmp_path):
    async def main():
        store = JsonProfileStore(tmp_path / "chua-ton-tai.json")
        profile = await store.load("nguoi-moi")
        assert profile.recurring_gaps == {} and profile.concepts_taught == {}

    asyncio.run(main())


def test_y_da_noi_toi_thi_khong_tinh_la_cho_hong(tmp_path):
    async def main():
        store = JsonProfileStore(tmp_path / "profiles.json")
        profile = await store.load("nhan")
        profile.absorb(
            "khái niệm",
            GradeResult(
                verdict=Verdict.SUFFICIENT,
                evidence=(Evidence("[T06-138]", "trích", covered_by_student=True),),
                gap_summary="",
            ),
        )
        assert profile.recurring_gaps == {}

    asyncio.run(main())


def test_ho_so_hong_thi_bat_dau_lai_chu_khong_giet_moi_phien(tmp_path):
    """Hồ sơ được nạp ngay khi mở kết nối, nên một file JSON méo là MỌI người
    đều không vào học được. Mất trí nhớ cũ còn hơn mất cả sản phẩm."""

    async def main():
        path = tmp_path / "profiles.json"
        path.write_text('{"nhan": {"student_i', encoding="utf-8")  # ghi dở rồi tắt máy
        store = JsonProfileStore(path)

        profile = await store.load("nhan")
        assert profile.recurring_gaps == {}
        giu_lai = list(tmp_path.glob("profiles.hong-*.json"))
        assert giu_lai, "file hỏng phải được giữ lại kèm mốc thời gian"

    asyncio.run(main())


def test_ghi_ho_so_khong_de_lai_file_cut_giua_chung(tmp_path):
    """Ghi đè thẳng sẽ cắt file về rỗng trước khi viết. Đổi chỗ file tạm thì
    hoặc là bản cũ, hoặc là bản mới — không bao giờ có bản cụt."""

    async def main():
        path = tmp_path / "profiles.json"
        store = JsonProfileStore(path)
        p = await store.load("nhan")
        p.absorb("khái niệm", _grade("[T06-138]"))
        await store.save(p)

        assert json.loads(path.read_text(encoding="utf-8"))["nhan"]
        assert not path.with_suffix(".tmp").exists(), "còn sót file tạm"

    asyncio.run(main())
