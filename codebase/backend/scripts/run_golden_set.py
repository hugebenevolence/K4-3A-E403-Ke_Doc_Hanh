"""Chạy trọn bộ golden set qua graph thật, ghi kết quả ra eval/results/.

    python scripts/run_golden_set.py                    # chạy tất cả
    python scripts/run_golden_set.py --only N01,M04     # chạy vài case
    python scripts/run_golden_set.py --mocks            # thử script, không tốn credit

Đi thẳng vào graph bằng đường gõ chữ, không qua WebSocket: đúng những node
quyết định (chấm → rẽ nhánh → hỏi ngược / đóng phiên), bỏ nhận dạng giọng nói,
đọc thành tiếng và câu mở bài — ba thứ không nằm trong ba chiều chấm và mỗi
lượt đều tốn thêm tiền.

Máy chấm được phần khớp chuỗi của D2 (không làm hộ) và gợi ý cho D3 (hỏi đúng
chỗ). Cột nào máy không chắc thì để trống cho người chấm — xem eval/golden-set/
golden-set.md.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from app.adapters.knowledge.pdf import attach_descriptions, load_deck
from app.adapters.knowledge.selection import lesson_from_selection
from app.adapters.llm.mock import MockLLM
from app.adapters.llm.openai import OpenAILLM
from app.config import settings
from app.domain.substance import MIN_SOURCE_WORDS, teachable_words
from app.graph.build import build_graph

REPO = Path(__file__).resolve().parents[3]
CASES = REPO / "eval/golden-set/cases.jsonl"
RESULTS = REPO / "eval/results"


def fold(text: str) -> str:
    """Bỏ dấu, thường hoá — để khớp chuỗi không lệ thuộc dấu và hoa thường."""
    stripped = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return stripped.replace("đ", "d").replace("Đ", "D").lower()


def plain(text: str) -> str:
    """Thường hoá nhưng GIỮ DẤU — dùng để dò cụm cấm.

    Bỏ dấu thì chấm sai: câu "bắt đầu bằng bước gì và kết thúc ra sao" bị đọc
    thành có cụm cấm "thực ra" (kết-thúc-ra ≈ thực-ra khi mất dấu), và M03 bị
    ghi là lộ đáp án dù câu hỏi hoàn toàn sạch. Trong tiếng Việt dấu là một
    phần của chữ, không phải thứ trang trí bỏ đi được.
    """
    return unicodedata.normalize("NFC", text).lower()


def deck_of(slug: str):
    path = settings.slides_dir / f"{slug}-slide-hackathon.pdf"
    try:
        descriptions = json.loads(settings.figures_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        descriptions = {}
    return attach_descriptions(load_deck(path), descriptions)


def widen(chosen: list, on_page: list, title: str) -> list[str]:
    """Vùng quá mỏng thì giảng cả trang — đúng như sản phẩm làm.

    Dùng chung đúng ngưỡng và đúng phép đếm với `domain/substance.py` (bỏ ô tiêu
    đề trang). Harness lệch luật thì nó dựng ra những phiên mà sản phẩm không
    bao giờ tạo được, và con số đo được không nói lên điều gì về sản phẩm.
    """
    if any(s.kind == "figure" for s in chosen):
        return [s.span_id for s in chosen]
    picked = chosen if teachable_words(chosen, title) >= MIN_SOURCE_WORDS else on_page
    return [s.span_id for s in picked]


def pick_spans(deck, case) -> list[str]:
    """Vùng slide học viên chọn trong case."""
    page = case["page"]
    on_page = [s for s in deck.spans if s.page == page]
    title = deck.titles.get(page) or ""
    rule = case["select"]
    if rule == "page":
        return [s.span_id for s in on_page]
    if isinstance(rule, dict) and "contains" in rule:
        needle = fold(rule["contains"])
        hit = [s for s in on_page if needle in fold(s.text)]
        return widen(hit, on_page, title) if hit else [s.span_id for s in on_page]
    if isinstance(rule, dict) and rule.get("kind") == "figure":
        hit = [s.span_id for s in on_page if s.kind == "figure"]
        return hit or [s.span_id for s in on_page]
    if isinstance(rule, dict) and rule.get("title_only"):
        return widen(on_page[:1], on_page, title) if on_page else []
    raise ValueError(f"select lạ: {rule}")


async def run_case(case, llm, rep: int = 0) -> dict:
    deck = deck_of(case["deck"])
    span_ids = pick_spans(deck, case)
    lesson, store = lesson_from_selection(deck, span_ids)
    graph = build_graph(llm, store, checkpointer=InMemorySaver(), store=InMemoryStore())

    source_text = "\n".join(s.text for s in await store.get_many(lesson.source_span_ids))
    turns_said = case["turns"]
    if case.get("verbatim_from_source"):
        # Case "đọc nguyên văn slide": lấy thẳng chữ trên trang làm lời học viên.
        turns_said = [source_text[:600]]

    # Mỗi lượt lặp là một phiên riêng: chung thread_id thì checkpointer giữ lại
    # lời của lượt trước và lượt sau không còn là một phép đo độc lập.
    thread = f"golden-{case['id']}-r{rep}"
    turns = []
    for i, said in enumerate(turns_said):
        payload: dict = {"student_text": said}
        if i == 0:
            payload |= {
                "session_id": thread,
                "student_id": "golden",
                "concept": lesson.concept,
                "source_span_ids": list(lesson.source_span_ids),
                "vocabulary": list(lesson.vocabulary),
                "followups_asked": 0,
                "recurring_gaps": {},
                "code": "",
            }
        result = await graph.ainvoke(payload, config={"configurable": {"thread_id": thread}})
        turns.append(
            {
                "said": said,
                "verdict": result.get("verdict"),
                "turn_state": result.get("turn_state"),
                "agent_says": result.get("agent_says", ""),
                "understood": result.get("agent_understood") or [],
                "cites_span_id": result.get("cites_span_id"),
                "gap_summary": result.get("gap_summary", ""),
            }
        )
    return judge(case, turns, source_text) | {"rep": rep}


def judge(case, turns, source_text: str) -> dict:
    """Ba chiều D1/D2/D3. Máy chỉ chấm phần khớp chuỗi được; còn lại để người."""
    expects = case["expect"]
    d1_rows = []
    for expect, turn in zip(expects, turns, strict=False):
        # Nhãn từ graph là chữ thường ("incomplete"), kỳ vọng viết hoa.
        got = (turn["verdict"] or "").upper()
        d1_rows.append(expect == "ANY" or got == expect)
    d1 = all(d1_rows) and len(turns) == len(expects)
    if case.get("expect_close_last"):
        d1 = d1 and turns[-1]["turn_state"] in ("TAUGHT", "SUGGEST_REVIEW")

    # D2: lời học trò (câu nói + các ý "Mình hiểu là") không được chứa cụm cấm,
    # và không được hỏi quá một câu.
    banned = [*case.get("must_not", []), *case.get("never", [])]
    leaks, extra_questions = [], []
    for turn in turns:
        blob = plain(" ".join([turn["agent_says"], *turn["understood"]]))
        leaks += [phrase for phrase in banned if plain(phrase) in blob]
        if turn["agent_says"].count("?") > 1:
            extra_questions.append(turn["agent_says"].count("?"))
    d2 = not leaks and not extra_questions

    # D3: gợi ý cho người chấm — câu hỏi có chạm từ khoá của chỗ hổng không.
    anchors = case.get("gap", [])
    hit = None
    if anchors:
        blob = plain(" ".join(t["agent_says"] for t in turns))
        hit = [a for a in anchors if plain(a) in blob]
    return {
        "id": case["id"],
        "layer": case["layer"],
        "source": case.get("source", []),
        "expect": expects,
        "turns": turns,
        "d1": d1,
        "d2": d2,
        "d2_leaks": leaks,
        "d2_extra_questions": extra_questions,
        "d3_hits": hit,
        "manual": case.get("manual", ""),
        "source_chars": len(source_text),
    }


def mark(ok: bool | None) -> str:
    return {True: "đạt", False: "KHÔNG", None: "—"}[ok]


def _by_case(rows: list[dict]) -> dict[str, list[dict]]:
    """Gom các lượt lặp của cùng một case, giữ nguyên thứ tự case."""
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["id"], []).append(r)
    return groups


def unstable(reps: list[dict]) -> bool:
    """Cùng một lời giảng, cùng một bản build, mà lượt được lượt không.

    Đây mới là con số đáng đọc. Chạy một lượt rồi báo "77%" là báo một lần tung
    đồng xu: spec §7 đã ghi nhận D1 chạy 20–23/26 qua các lượt của CÙNG bản build.
    """
    return len({r["d1"] for r in reps}) > 1


def report(rows: list[dict], started: str, build: str | None = None) -> str:
    groups = _by_case(rows)
    n_reps = max(len(v) for v in groups.values()) if groups else 1

    hard_fail = sorted({
        r["id"] for r in rows
        if (r["layer"] in ("③", "④") and not r["d2"])
        or ("INCORRECT" in r["expect"] and any((t["verdict"] or "").upper() == "SUFFICIENT" for t in r["turns"]))
    })
    # Tổng của TỪNG lượt chạy, không phải tổng gộp: mỗi lượt là một lần đo cả bộ.
    totals = [
        sum(1 for reps in groups.values() if i < len(reps) and reps[i]["d1"] and reps[i]["d2"])
        for i in range(n_reps)
    ]
    wobbly = [cid for cid, reps in groups.items() if unstable(reps)]

    if n_reps > 1:
        headline = (
            f"**D1+D2 tự động: trung vị {median(totals):.0f}/{len(groups)} "
            f"({100 * median(totals) / max(len(groups), 1):.0f}%)** qua {n_reps} lượt chạy "
            f"(từng lượt: {', '.join(str(t) for t in totals)}) — "
            "D3 và các ô '—' cần người chấm (xem cách chấm trong golden-set.md)."
        )
    else:
        headline = (
            f"**D1+D2 tự động: {totals[0]}/{len(groups)} ({100 * totals[0] / max(len(groups), 1):.0f}%)** — "
            "D3 và các ô '—' cần người chấm (xem cách chấm trong golden-set.md)."
        )

    lines = [
        f"# Lượt chạy golden set — {started}",
        "",
        build
        or (
            f"Bản build: {settings.model_standard} · service tier {settings.openai_service_tier} · "
            f"{'MOCK' if settings.use_mocks else 'provider thật'}"
            + (f" · {n_reps} lượt chạy mỗi case" if n_reps > 1 else "")
        ),
        "",
        headline,
        "",
        f"Điều kiện cứng: {'ĐẠT' if not hard_fail else 'KHÔNG ĐẠT — ' + ', '.join(hard_fail)}"
        + (" (một lượt vi phạm là trượt — điều kiện cứng không lấy trung vị)" if n_reps > 1 else ""),
        "",
    ]
    if n_reps > 1:
        lines += [
            f"**Case dao động giữa các lượt: {len(wobbly)}/{len(groups)}**"
            + (" — " + ", ".join(sorted(wobbly)) if wobbly else " — không có case nào"),
            "",
            (
                "Case dao động là chỗ bộ chấm chưa có ranh giới ổn định; sửa ở đó ăn hơn "
                "sửa ở case hỏng đều, vì case hỏng đều ít nhất còn đoán trước được."
            ),
            "",
        ]

    lines += [
        "| Case | Lớp | Kỳ vọng | Nhãn chấm được | D1 | D2 | D3 (gợi ý) | Ghi chú máy |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for cid, reps in groups.items():
        first = reps[0]
        seen: list[str] = []
        for r in reps:
            got = " → ".join(str(t["verdict"]) for t in r["turns"])
            if got not in seen:
                seen.append(got)
        note = []
        if any(r["d2_leaks"] for r in reps):
            note.append("lộ: " + ", ".join(sorted({p for r in reps for p in r["d2_leaks"]})))
        if any(r["d2_extra_questions"] for r in reps):
            note.append("có lượt hỏi nhiều hơn một câu")
        if unstable(reps):
            note.append("DAO ĐỘNG giữa các lượt")
        if first["manual"]:
            note.append("người chấm: " + first["manual"])
        d1 = f"{sum(1 for r in reps if r['d1'])}/{len(reps)}" if n_reps > 1 else mark(first["d1"])
        d2 = f"{sum(1 for r in reps if r['d2'])}/{len(reps)}" if n_reps > 1 else mark(first["d2"])
        hits = first["d3_hits"]
        d3 = "—" if hits is None else ("chạm: " + ", ".join(hits) if hits else "không chạm từ khoá nào")
        lines.append(
            f"| {cid} | {first['layer']} | {' → '.join(first['expect'])} | {' / '.join(seen)} "
            f"| {d1} | {d2} | {d3} | {'; '.join(note)} |"
        )

    lines += ["", "## Lời học trò từng case", ""]
    for cid, reps in groups.items():
        first = reps[0]
        lines.append(f"### {cid} ({first['layer']}) — kỳ vọng {' → '.join(first['expect'])}")
        # Chỉ chép chi tiết lượt đầu; case dao động thì chép hết, vì đúng chỗ đó
        # mới cần đọc tay xem hai lượt khác nhau ở đâu.
        for r in reps if unstable(reps) else reps[:1]:
            if len(reps) > 1 and unstable(reps):
                lines.append(f"*lượt chạy {r.get('rep', 0) + 1} — D1 {mark(r['d1'])}*")
            for i, t in enumerate(r["turns"], 1):
                lines.append(f"- **Lượt {i}** · học viên: {t['said'][:200]}")
                lines.append(f"  - nhãn: `{t['verdict']}` · trạng thái: `{t['turn_state']}` · trích: `{t['cites_span_id']}`")
                if t["understood"]:
                    lines.append("  - mình hiểu là: " + " / ".join(t["understood"]))
                lines.append(f"  - học trò nói: {t['agent_says']}")
        lines.append("")
    return "\n".join(lines)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--mocks", action="store_true")
    ap.add_argument("--concurrency", type=int, default=3)
    # Chạy mỗi case nhiều lượt. Một lượt chạy là MỘT lần tung đồng xu: cùng bản
    # build, D1 đã đo được 20–23/26 qua các lượt (spec §7). Ba lượt cho biết
    # con số thật nằm quanh đâu, và case nào đang bập bênh.
    ap.add_argument("--repeat", type=int, default=1)
    # Chấm lại từ lượt đã chạy: sửa cách chấm mà không gọi lại LLM.
    ap.add_argument("--rejudge", default="")
    args = ap.parse_args()

    if args.mocks:
        settings.use_mocks = True
    cases = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.only:
        wanted = {c.strip() for c in args.only.split(",")}
        cases = [c for c in cases if c["id"] in wanted]

    if args.rejudge:
        by_id = {c["id"]: c for c in cases}
        old = json.loads(Path(args.rejudge).read_text(encoding="utf-8"))
        rows = [judge(by_id[r["id"]], r["turns"], "x" * r.get("source_chars", 0)) for r in old]
        stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M")
        started = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M") + f" (chấm lại từ {Path(args.rejudge).name})"
        (RESULTS / f"run-{stamp}.md").write_text(
            report(rows, started, build=f"Bản build: xem lượt gốc `{Path(args.rejudge).name}`"),
            encoding="utf-8",
        )
        (RESULTS / f"run-{stamp}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"-> eval/results/run-{stamp}.md")
        return

    llm = MockLLM() if settings.use_mocks else OpenAILLM()
    started = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M")
    gate = asyncio.Semaphore(args.concurrency)

    async def one(case, rep):
        async with gate:
            try:
                row = await run_case(case, llm, rep)
            except Exception as err:  # noqa: BLE001 — một case hỏng không được kéo đổ cả lượt chạy
                row = {
                    "id": case["id"], "layer": case["layer"], "source": case.get("source", []),
                    "expect": case["expect"], "turns": [], "d1": False, "d2": False,
                    "d2_leaks": [], "d2_extra_questions": [], "d3_hits": None,
                    "manual": f"LỖI KHI CHẠY: {err}", "source_chars": 0, "rep": rep,
                }
            tag = f" (lượt {rep + 1})" if args.repeat > 1 else ""
            print(f"{row['id']}{tag}: D1 {mark(row['d1'])} · D2 {mark(row['d2'])}", flush=True)
            return row

    rows = await asyncio.gather(
        *(one(c, r) for c in cases for r in range(max(1, args.repeat)))
    )
    order = [c["id"] for c in cases]
    rows.sort(key=lambda r: (order.index(r["id"]), r.get("rep", 0)))

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M")
    (RESULTS / f"run-{stamp}.md").write_text(report(list(rows), started), encoding="utf-8")
    (RESULTS / f"run-{stamp}.json").write_text(json.dumps(list(rows), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> eval/results/run-{stamp}.md")


if __name__ == "__main__":
    asyncio.run(main())
