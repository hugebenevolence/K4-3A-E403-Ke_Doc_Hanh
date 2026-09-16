"""Sinh knowledge/lesson.json từ một trang slide PDF.

    python scripts/build_lesson.py <pdf> <trang> "<tên khái niệm>" [--only 05 07]
    python scripts/build_lesson.py <pdf> <trang> --list      # xem trang có gì

File sinh ra nằm ở knowledge/ (đã gitignore) vì chứa nội dung data pack của
BTC — không được commit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.adapters.knowledge.pdf import deck_terms, parse_slide
from app.config import settings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("page", type=int)
    ap.add_argument("concept", nargs="?", default="")
    ap.add_argument("--list", action="store_true", help="chỉ in ra trang có những span nào")
    ap.add_argument("--only", nargs="*", help="chỉ lấy span có hậu tố này, vd 05 07")
    ap.add_argument("--out", type=Path, default=settings.lesson_file)
    args = ap.parse_args()

    spans = parse_slide(args.pdf, args.page)
    if not spans:
        print(f"Trang {args.page} không có span nào đủ dài để dạy.", file=sys.stderr)
        return 1

    if args.list:
        for s in spans:
            print(f"{s.span_id}\n    {s.text[:150]}")
        return 0

    if args.only:
        wanted = {o.zfill(2) for o in args.only}
        spans = [s for s in spans if s.span_id.rsplit("-", 1)[-1].rstrip("]") in wanted]
        if not spans:
            print(f"Không span nào khớp --only {args.only}", file=sys.stderr)
            return 1

    if not args.concept:
        print("Thiếu tên khái niệm (hoặc dùng --list).", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "concept": args.concept,
                "source": f"{args.pdf.name} trang {args.page}",
                # Rút từ CẢ bộ slide, không chỉ trang đang học: học viên hay
                # nhắc thuật ngữ ở trang khác khi giải thích.
                "vocabulary": list(deck_terms(args.pdf)),
                "spans": [
                    {"span_id": s.span_id, "text": s.text, "page": s.page, "bbox": list(s.bbox)}
                    for s in spans
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Đã ghi {len(spans)} span vào {args.out}")
    for s in spans:
        print(f"  {s.span_id}: {s.text[:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
