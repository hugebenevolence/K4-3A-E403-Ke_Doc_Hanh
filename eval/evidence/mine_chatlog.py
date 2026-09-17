"""Đếm bằng chứng từ chatlog VLearn cho spec §1–§2 (chuẩn B — mining).

Chạy lại được: người chấm có data pack thì chạy đúng lệnh này ra đúng các số
trong eval/evidence/mining.md. Data pack KHÔNG nằm trong repo (luật bảo mật),
script chỉ đọc từ brief/data/ trên máy.

    python eval/evidence/mine_chatlog.py

Mọi quy tắc xếp loại nằm ở các regex bên dưới — đọc là biết đếm cái gì.
"""

from __future__ import annotations

import collections
import csv
import re
import statistics
import sys
from pathlib import Path

CSV = Path(__file__).resolve().parents[2] / "brief/data/vlearn-pack/chatlog/tutor_turns.csv"

# Bỏ tiền tố ngữ cảnh giao diện tự chèn trước câu hỏi, chỉ giữ lời học viên gõ.
PREFIX = re.compile(r'^\((Trang \d+, đoạn được chọn: ".*?"|Đang học phần ".*?")\)\s*', re.S)

# Học viên xin được giảng: câu mẫu "giải thích đoạn bôi đen" hoặc tự gõ.
EXPLAIN = re.compile(r"giải thích|là gì|nghĩa là gì|hiểu thế nào|hiểu như thế nào|không hiểu|chưa hiểu", re.I)

# Học viên tự nói ra cách hiểu của mình và muốn được kiểm (cơ hội dạy lại).
SELF_EXPLAIN = re.compile(
    r"(em|mình|tôi|t)\s+(hiểu|nghĩ)\s+(là|rằng|như)|có phải (là )?|đúng không"
    r"|hiểu (như vậy|thế) (có )?đúng|tức là|nghĩa là .*(đúng|phải) không",
    re.I,
)

# Đòi đáp án / làm hộ.
ASK_ANSWER = re.compile(
    r"đáp án|cho (em|mình|tôi) (câu trả lời|lời giải)|giải (hộ|giùm|giúp) |làm (hộ|giùm|giúp)"
    r"|trả lời (hộ|giùm)|viết (hộ|giùm|giúp)",
    re.I,
)

# Xin câu hỏi ôn tập / quiz.
QUIZ = re.compile(r"trắc nghiệm|trắc nghiêm|quiz|câu hỏi ôn|ôn tập|kiểm tra nhanh|bộ câu hỏi|flashcard", re.I)

# Hỏi lại cùng một đoạn đã chọn: cùng học viên, cùng buổi, cùng 80 ký tự đầu đoạn chọn.
SELECTED = re.compile(r'^\(Trang (\d+), đoạn được chọn: "(.*?)"\)', re.S)


def body(row: dict) -> str:
    return PREFIX.sub("", row["student_question"]).strip()


def pct(part: int, whole: int) -> str:
    return f"{part:,}/{whole:,} ({100 * part / whole:.1f}%)".replace(",", ".")


def describe(name: str, rows: list[dict], total: int) -> str:
    k4 = [r for r in rows if r["cohort_hint"] == "K4"]
    up = sum(r["rating"] == "up" for r in rows)
    down = sum(r["rating"] == "down" for r in rows)
    return (
        f"| {name} | {pct(len(rows), total)} | {len({r['student'] for r in rows})} "
        f"| {len(k4)} lượt · {len({r['student'] for r in k4})} HV | {up}/{down} |"
    )


def main() -> None:
    if not CSV.exists():
        sys.exit(f"Không thấy {CSV} — data pack chỉ có trên máy thành viên, không commit.")
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    n = len(rows)
    nonpreset = [r for r in rows if r["is_preset"] != "True"]

    print(f"Tổng: {n} lượt · {len({r['student'] for r in rows})} học viên")
    k4 = [r for r in rows if r["cohort_hint"] == "K4"]
    print(f"K4: {len(k4)} lượt · {len({r['student'] for r in k4})} học viên\n")

    print("## Nước đi sư phạm của tutor (cột move_used)\n")
    for move, count in collections.Counter(r["move_used"] or "(rỗng)" for r in rows).most_common():
        print(f"- {move}: {pct(count, n)}")

    explain = [r for r in rows if EXPLAIN.search(r["student_question"])]
    self_explain = [r for r in nonpreset if SELF_EXPLAIN.search(body(r))]
    ask_answer = [r for r in nonpreset if ASK_ANSWER.search(body(r))]
    quiz = [r for r in nonpreset if QUIZ.search(body(r))]
    no_cite = [r for r in rows if r["has_citation"] == "False"]
    long_reply = [r for r in rows if int(r["reply_len"]) > 1500]

    print("\n## Các nhóm lượt\n")
    print("| Nhóm | Lượt | Học viên | Trong K4 | Rating up/down |")
    print("|---|---|---|---|---|")
    print(describe("Xin được giảng (EXPLAIN)", explain, n))
    print(describe("Tự nói cách hiểu, muốn được kiểm (SELF_EXPLAIN, không tính câu mẫu)", self_explain, n))
    print(describe("Đòi đáp án / làm hộ (ASK_ANSWER)", ask_answer, n))
    print(describe("Xin quiz / ôn tập (QUIZ)", quiz, n))
    print(describe("Tutor trả lời không trích dẫn", no_cite, n))
    print(describe("Tutor trả lời dài hơn 1500 ký tự", long_reply, n))

    moves = collections.Counter(r["move_used"] for r in self_explain)
    print(f"\nKhi học viên tự nói cách hiểu ({len(self_explain)} lượt), tutor chọn: {dict(moves.most_common())}")

    groups: dict[tuple, list] = collections.defaultdict(list)
    for r in rows:
        if m := SELECTED.match(r["student_question"]):
            groups[(r["student"], r["lecture_code"], r["course_id"], m.group(2).strip()[:80])].append(r)
    repeated = [g for g in groups.values() if len(g) >= 2]
    print(
        f"\nHỏi lại cùng một đoạn đã chọn: {pct(len(repeated), len(groups))} đoạn · "
        f"{sum(len(g) for g in repeated)} lượt · {len({g[0]['student'] for g in repeated})} học viên"
    )

    print(f"\nCâu mẫu bấm sẵn: {pct(sum(r['is_preset'] == 'True' for r in rows), n)}")
    print(f"understanding_level có giá trị: {pct(sum(bool(r['understanding_level']) for r in rows), n)}")
    rated = [r for r in rows if r["rating"]]
    print(f"Có rating: {pct(len(rated), n)} · down {sum(r['rating'] == 'down' for r in rated)}")
    print(f"reply_len trung vị: {statistics.median(int(r['reply_len']) for r in rows):.0f} ký tự")


if __name__ == "__main__":
    main()
