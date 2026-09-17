"""Xem đồ thị tri thức của một học viên, và thử lại việc rút mệnh đề.

    python scripts/dump_graph.py                     # liệt kê mọi học viên
    python scripts/dump_graph.py --student member1   # đồ thị của một người
    python scripts/dump_graph.py --replay member1    # dựng lại từ log phiên thật

`--replay` là công cụ debug chính: nó chạy lại phép rút mệnh đề trên đúng những
lượt đã ghi trong `var/sessions.jsonl` và in ra CẢ những câu bị loại kèm lý do.
Không có nó thì đồ thị chỉ im lặng bỏ sót, và không ai lần ra được vì sao một
câu học viên rõ ràng đã nói lại không thành đỉnh.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.adapters.store.jsonl import JsonGraphStore
from app.config import settings
from app.domain.graph import LINK_LABEL, KnowledgeGraph, claims_from_turn, links_from_turn


def _in_do_thi(g: KnowledgeGraph) -> None:
    if not g.claims:
        print("  (rỗng — học viên này chưa giảng nổi ý nào)")
        return
    print(f"  {len(g.claims)} đỉnh · {len(g.links)} cạnh")
    for c in sorted(g.claims.values(), key=lambda c: -c.times_taught):
        print(f"\n  ● {c.concept}   ({c.times_taught} buổi)")
        print(f"      họ nói: {c.said}")
        print(f"      neo vào: {', '.join(c.span_ids)}")
    if g.links:
        print()
        for l in g.links.values():
            print(f"  → {l.source} --{LINK_LABEL.get(l.kind, l.kind)}--> {l.target}")
            print(f"      vì họ nói: {l.evidence}")


def _replay(student_id: str) -> None:
    """Chạy lại phép rút mệnh đề trên log thật, in cả phần bị loại."""
    path = settings.session_log_file
    if not path.is_file():
        print(f"Chưa có log phiên ở {path}")
        return

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        print("Log phiên rỗng")
        return

    print(f"Dựng lại từ {len(rows)} lượt trong {path.name}\n")
    for r in rows:
        grade = r.get("grade") or {}
        evidence = grade.get("evidence") or []
        covered = [
            (e["span_id"], e.get("quote", ""))
            for e in evidence
            if e.get("covered_by_student") and not e.get("contradicted_by_student")
        ]
        claims, bo_qua = claims_from_turn(r["student_text"], covered, r["session_id"])
        links = links_from_turn(r["student_text"], claims, r["session_id"])

        print(f"— lượt {r['turn_index']} · nhãn {grade.get('verdict')} · phiên {r['session_id'][:8]}")
        print(f"  học viên: {r['student_text'][:110]}")
        if not covered:
            print("  (bộ chấm không xác nhận ô nào là đã nói tới → không có gì để neo)")
        for c in claims:
            print(f"  ✓ ĐỈNH {c.concept:14} <- {c.said[:80]}")
        for l in links:
            print(f"  ✓ CẠNH {l.source} → {l.target} ({l.kind})")
        for cau, ly_do in bo_qua:
            print(f"  ✗ loại  ({ly_do}) {cau[:70]}")
        print()

    print(
        "Lưu ý: quote trong log là TRÍCH NGẮN của ô nguồn, không phải cả ô, nên\n"
        "phép rút ở đây hơi khắt khe hơn lúc chạy thật (lúc đó nó đọc cả ô)."
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--student", default="")
    ap.add_argument("--replay", default="")
    args = ap.parse_args()

    if args.replay:
        _replay(args.replay)
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
