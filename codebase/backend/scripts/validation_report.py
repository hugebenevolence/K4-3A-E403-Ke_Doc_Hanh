"""Tóm tắt HÀNH VI của từng người thử từ log của server — cho validation/.

    python scripts/validation_report.py member1 member2 --since 2026-09-19T09:00
    python scripts/validation_report.py member1 --texts    # kèm lời họ giảng

Hành vi quan sát được là tầng bằng chứng mạnh nhất (02-guide §4.2): người thử
NÓI "dễ dùng" không bằng việc họ giảng mấy lượt mới xong, bỏ ngang ở đâu, có
giảng sai rồi tự sửa không. Người quan sát ghi lời nói; script này ghi phần còn
lại, lấy thẳng từ var/ của bản đang chạy — không gọi API, không tốn credit.

Chỉ đọc. Lượt của ai lấy theo trường student_id trong log phiên; log cũ chưa có
trường đó thì lấy qua mã phiên trong tiến độ và bản đồ của người đó.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

VAR = Path(__file__).resolve().parents[1] / "var"
SPAN = re.compile(r"\[(.+)-p(\d+)-\w+\]")
KIND = {"page": "giảng trang", "link": "nối hai trang", "code": "bài code"}


def _load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def _page(span_id: str) -> str:
    m = SPAN.match(span_id or "")
    return f"{m.group(1)} tr.{m.group(2)}" if m else span_id


def _key(key: str) -> str:
    deck, _, page = key.rpartition(":")
    return f"{deck} tr.{page}"


def _when(iso: str) -> datetime:
    """Log ghi giờ UTC; --since người ta gõ giờ máy. Đưa cả hai về giờ máy."""
    t = datetime.fromisoformat(iso)
    return (t if t.tzinfo else t.astimezone()).astimezone()


def _minutes(a: str, b: str) -> float:
    return (_when(b) - _when(a)).total_seconds() / 60


def report(
    student: str, rows: list[dict], progress: dict, graph: dict, since: str, texts: bool
) -> str:
    prog = progress.get(student, {}).get("pages", {})
    links = graph.get(student, {}).get("links", [])
    link_sessions = {lk["session"]: lk for lk in links}
    known = {s for p in prog.values() for s in p.get("sessions", [])} | set(
        link_sessions
    )

    turns = defaultdict(list)
    for r in rows:
        if (r.get("student_id") == student or r["session_id"] in known) and (
            not since or _when(r["at"]) >= _when(since)
        ):
            turns[r["session_id"]].append(r)
    sessions = sorted(turns.values(), key=lambda t: t[0]["at"])

    out = [f"## {student}", ""]
    if not sessions:
        return "\n".join(out + ["Chưa có lượt nào trong khoảng thời gian này.", ""])

    out += [
        "| # | bắt đầu | loại | trang | lượt | nhãn qua từng lượt | kết | phút lượt đầu → cuối |",
        "|---|---|---|---|---|---|---|---|",
    ]
    lat, taught, incorrect = [], 0, 0
    for i, t in enumerate(sessions, 1):
        t.sort(key=lambda r: r["turn_index"])
        verdicts = [(r.get("grade") or {}).get("verdict", "?") for r in t]
        kind = t[0].get("kind") or (
            "link" if t[0]["session_id"] in link_sessions else "page"
        )
        lk = link_sessions.get(t[0]["session_id"])
        page = (
            f"{_key(lk['source'])} — {_key(lk['target'])}"
            if lk
            else _page(t[0]["source_span_id"])
        )
        ok = "sufficient" in verdicts
        taught += ok
        incorrect += "incorrect" in verdicts
        lat += [
            r["latency_ms"]["first_audio"]
            for r in t
            if r.get("latency_ms", {}).get("first_audio")
        ]
        out.append(
            f"| {i} | {_when(t[0]['at']):%d/%m %H:%M} | {KIND.get(kind, kind)} | {page} | {len(t)} | "
            f"{' → '.join(verdicts)} | {'dạy được' if ok else 'chưa'} | {f'{_minutes(t[0]['at'], t[-1]['at']):.1f}' if len(t) > 1 else '—'} |"
        )
        if texts:
            for r in t:
                said = r["student_text"].replace("|", "/").replace("\n", " ")
                out.append(f"|  |  |  |  | ↳ {r['turn_index']} | {said[:200]} |  |  |")

    levels = defaultdict(int)
    for p in prog.values():
        levels[
            "đã hiểu"
            if p.get("taught_sessions")
            else "cần sửa"
            if p.get("last_verdict") == "incorrect"
            else "đang học"
        ] += 1
    out += [
        "",
        f"- {len(sessions)} phiên, {sum(len(t) for t in sessions)} lượt; dạy được {taught}/{len(sessions)} phiên",
        f"- {incorrect} phiên có lượt bị chấm SAI (hiểu lầm lộ ra) · {len(links)} mối nối trên bản đồ",
        f"- tiến độ: {', '.join(f'{v} {k}' for k, v in sorted(levels.items())) or 'trống'}",
    ]
    if lat:
        out.append(
            f"- chờ tới tiếng đầu tiên của học trò: trung vị {statistics.median(lat) / 1000:.1f}s, chậm nhất {max(lat) / 1000:.1f}s"
        )
    return "\n".join(out + [""])


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("students", nargs="+", help="tài khoản người thử, vd member1")
    ap.add_argument(
        "--since",
        default="",
        help="chỉ lấy lượt từ thời điểm này (ISO, vd 2026-09-19T09:00)",
    )
    ap.add_argument(
        "--texts", action="store_true", help="kèm lời người thử giảng ở từng lượt"
    )
    ap.add_argument(
        "--var", type=Path, default=VAR, help="thư mục var/ của bản đang chạy"
    )
    args = ap.parse_args()

    log = args.var / "sessions.jsonl"
    rows = (
        [
            json.loads(line)
            for line in log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if log.is_file()
        else []
    )
    progress = _load(args.var / "progress.json", {})
    graph = _load(args.var / "graphs.json", {})
    for s in args.students:
        print(report(s, rows, progress, graph, args.since, args.texts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
