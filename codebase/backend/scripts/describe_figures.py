"""Mô tả các hình trên slide bằng model có thị giác, lưu vào knowledge/figures.json.

    python scripts/describe_figures.py <pdf>            # chỉ mô tả hình chưa có
    python scripts/describe_figures.py <pdf> --redo     # mô tả lại tất cả

Vì sao cần: bộ tách slide nhận ra được CHỖ nào là hình, nhưng không biết hình
vẽ GÌ — ô hình chỉ có chữ "Hình minh hoạ". Học viên chọn sơ đồ vòng tròn ở
slide 3 để giảng thì bộ chấm không có gì để đối chiếu.

Chạy một lần mỗi bộ slide, không chạy lúc học: mô tả một hình mất vài giây,
bắt học viên chờ lúc bấm "Giảng" là không được.

File sinh ra nằm ở knowledge/ (đã gitignore): mô tả được dựng từ chính nội dung
slide của data pack, không được commit. Chỉ gửi đi đúng vùng hình, không gửi cả
trang — dùng dữ liệu ở mức tối thiểu cần thiết theo luật data pack.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import OpenAI

from app.adapters.knowledge.pdf import load_deck
from app.config import settings

PROMPT = (
    "Đây là một hình trong slide bài giảng \"{title}\" (khoá AI & LLM Foundation). "
    "Mô tả bằng tiếng Việt, tối đa 70 từ, thành đoạn văn liền mạch: hình thể hiện "
    "điều gì, gồm những thành phần nào và chúng liên hệ với nhau ra sao. Chỉ mô tả "
    "những gì NHÌN THẤY trong hình, không thêm kiến thức ngoài hình. Thuật ngữ tiếng "
    "Anh giữ nguyên như trong hình, viết thường trừ chữ viết tắt."
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--out", type=Path, default=settings.figures_file)
    args = ap.parse_args()

    deck = load_deck(args.pdf)
    figures = [s for s in deck.spans if s.kind == "figure"]
    try:
        done = json.loads(args.out.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        done = {}

    client = OpenAI(api_key=settings.openai_api_key)
    with pymupdf.open(args.pdf) as doc:
        for span in figures:
            if span.span_id in done and not args.redo:
                continue
            page = doc[span.page - 1]
            png = page.get_pixmap(clip=pymupdf.Rect(span.bbox), dpi=144).tobytes("png")
            image = "data:image/png;base64," + base64.b64encode(png).decode()
            resp = client.responses.create(
                model=settings.model_standard,
                reasoning={"effort": "minimal"},
                input=[{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": PROMPT.format(title=deck.titles.get(span.page, ""))},
                        {"type": "input_image", "image_url": image},
                    ],
                }],
            )
            done[span.span_id] = " ".join(resp.output_text.split())
            print(f"{span.span_id}: {done[span.span_id][:110]}")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"Xong: {len(done)} hình có mô tả trong {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
