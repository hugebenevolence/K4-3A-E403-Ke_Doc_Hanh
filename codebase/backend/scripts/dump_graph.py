"""Xem đồ thị tri thức của một học viên, và thử lại việc rút mệnh đề.

    python scripts/dump_graph.py                     # liệt kê mọi học viên
    python scripts/dump_graph.py --student member1   # đồ thị của một người
    python scripts/dump_graph.py --replay            # dựng lại từ log phiên thật

`--replay` là công cụ debug chính: nó dựng lại đồ thị từ đúng những lượt đã ghi
trong `var/sessions.jsonl` và in ra CẢ những câu bị loại kèm lý do.
Nó chạy trên MỌI lượt trong log, không lọc theo học viên được — `TurnLog` không
ghi `student_id`. Cần lọc thì phải thêm trường đó vào log trước.
Không có nó thì đồ thị chỉ im lặng bỏ sót, và không ai lần ra được vì sao một
câu học viên rõ ràng đã nói lại không thành đỉnh.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.adapters.store.jsonl import JsonGraphStore
from app.api.graph_sync import absorb_turn
from app.config import settings
from app.domain.graph import LINK_LABEL, KnowledgeGraph, PageRef, page_key


def _in_do_thi(g: KnowledgeGraph) -> None:
    if not g.claims:
        print("  (rỗng — học viên này chưa giảng nổi ý nào)")
        return
    print(f"  {len(g.claims)} đỉnh · {len(g.links)} cạnh")
    for c in sorted(g.claims.values(), key=lambda c: -c.times_taught):
        print(f"\n  ● {c.title or c.concept}   [{c.concept}] · {c.times_taught} buổi")
        for cau in c.sentences:
            print(f"      họ nói: {cau}")
    if g.links:
        print()
        for l in g.links.values():
            print(f"  → {l.source} --{LINK_LABEL.get(l.kind, l.kind)}--> {l.target}")
            print(f"      vì họ nói: {l.evidence}")


_MA_O = re.compile(r"^\[(?P<deck>.+)-p(?P<page>\d+)-")


def _trang_cua(evidence: list[dict]) -> PageRef | None:
    """Dựng lại trang của một lượt từ mã ô trong bằng chứng chấm.

    Log không ghi thẳng mã bộ slide, nhưng mã ô mang sẵn nó: "[d1-slide-hackathon-p12-02]".
    """
    from app.main import _find_deck

    for e in evidence:
        m = _MA_O.match(e.get("span_id", ""))
        if not m:
            continue
        deck = _find_deck(m["deck"])
        if deck is None:
            return None
        page = int(m["page"])
        on_page = [s for s in deck.spans if s.page == page]
        return PageRef(
            key=page_key(m["deck"], page),
            title=deck.titles.get(page) or f"Trang {page}",
            deck=m["deck"],
            page=page,
            span_ids=tuple(s.span_id for s in on_page),
            text="\n".join(s.text for s in on_page),
        )
    return None


def _replay() -> None:
    """Dựng lại đồ thị từ log thật, in cả phần bị loại."""
    path = settings.session_log_file
    if not path.is_file():
        print(f"Chưa có log phiên ở {path}")
        return

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        print("Log phiên rỗng")
        return

    print(f"Dựng lại từ {len(rows)} lượt trong {path.name}\n")
    g = KnowledgeGraph(student_id="replay")
    loi_cua_phien: dict[str, list[str]] = {}
    for r in rows:
        grade = r.get("grade") or {}
        trang = _trang_cua(grade.get("evidence") or [])
        texts = loi_cua_phien.setdefault(r["session_id"], [])
        texts.append(r["student_text"])
        ket_qua = absorb_turn(
            g, page=trang, student_texts=texts, verdict=grade.get("verdict"), session_id=r["session_id"]
        )
        print(f"— lượt {r['turn_index']} · nhãn {grade.get('verdict')} · phiên {r['session_id'][:8]}"
              f" · {trang.key if trang else 'không neo được trang'}")
        print(f"  học viên: {r['student_text'][:110]}")
        for viec, trang_bi_doi in (ket_qua.get("đã làm") or {}).items():
            print(f"  ✓ {viec}: {', '.join(trang_bi_doi)}")
        for cau, ly_do in ket_qua.get("bỏ qua") or []:
            print(f"  ✗ loại  ({ly_do}) {cau[:70]}")
        print()

    print("=== đồ thị dựng lại ===")
    _in_do_thi(g)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--student", default="")
    ap.add_argument("--replay", action="store_true")
    args = ap.parse_args()

    if args.replay:
        _replay()
        return

    store = JsonGraphStore(settings.graph_file)
    if not settings.graph_file.is_file():
        print(f"Chưa có đồ thị nào ở {settings.graph_file}")
        return

    moi_nguoi = json.loads(settings.graph_file.read_text(encoding="utf-8"))
    ai = [args.student] if args.student else list(moi_nguoi)
    for student_id in ai:
        print(f"\n=== {student_id} ===")
        _in_do_thi(asyncio.run(store.load(student_id)))


if __name__ == "__main__":
    main()
