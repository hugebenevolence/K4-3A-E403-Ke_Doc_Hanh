"""Mô tả các hình trên slide bằng model có thị giác, lưu vào knowledge/figures.json.

    python scripts/describe_figures.py <pdf> [<pdf>...]      # chỉ mô tả hình chưa có
    python scripts/describe_figures.py <thư mục slide>       # cả thư mục
    python scripts/describe_figures.py <pdf> --redo          # mô tả lại tất cả
    python scripts/describe_figures.py <pdf> --jobs 4        # 4 lượt gọi song song

Vì sao cần: bộ tách slide nhận ra được CHỖ nào là hình, nhưng không biết hình
vẽ GÌ — ô hình chỉ có chữ "Hình minh hoạ". Học viên chọn sơ đồ vòng tròn ở
slide 3 để giảng thì bộ chấm không có gì để đối chiếu.

Chạy một lần mỗi bộ slide, không chạy lúc học: mô tả một hình mất vài giây,
bắt học viên chờ lúc bấm "Giảng" là không được.

File sinh ra nằm ở knowledge/ (đã gitignore): mô tả được dựng từ chính nội dung
slide của data pack, không được commit. Chỉ gửi đi đúng vùng hình, không gửi cả
trang — dùng dữ liệu ở mức tối thiểu cần thiết theo luật data pack.

Ghi sau MỖI hình, và hình đã có mô tả thì bỏ qua: chạy cả thư viện mất hàng
giờ, và lần nào đứt cũng phải chạy tiếp được chứ không phải làm lại từ đầu.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
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


def _pdfs(paths: list[Path]) -> list[Path]:
    """Nhận cả file lẫn thư mục, trả về danh sách PDF theo thứ tự tên."""
    out: list[Path] = []
    for path in paths:
        out.extend(sorted(path.glob("*.pdf")) if path.is_dir() else [path])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf", type=Path, nargs="+")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--jobs", type=int, default=1, help="số lượt gọi chạy song song")
    ap.add_argument("--out", type=Path, default=settings.figures_file)
    args = ap.parse_args()

    try:
        done = json.loads(args.out.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        done = {}

    client = OpenAI(api_key=settings.openai_api_key)
    # Một tiến trình, nhiều luồng, MỘT file kết quả: hai tiến trình cùng ghi
    # figures.json thì tiến trình sau đọc bản cũ rồi ghi đè mất phần của tiến
    # trình trước. Khoá ở đây rẻ hơn nhiều so với gỡ một file đã mất dữ liệu.
    khoa = threading.Lock()

    # Chặn không cho hàng đợi phình: mỗi việc đang chờ giữ nguyên một ảnh PNG
    # đã mã hoá trong bộ nhớ, và một bộ slide có tới 415 hình.
    cho_cho = threading.Semaphore(args.jobs * 3)

    def mo_ta(span, title: str, image: str) -> None:
        try:
            resp = client.responses.create(
                model=settings.model_standard,
                reasoning={"effort": "minimal"},
                input=[{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": PROMPT.format(title=title)},
                        {"type": "input_image", "image_url": image},
                    ],
                }],
            )
            with khoa:
                done[span.span_id] = " ".join(resp.output_text.split())
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(
                    json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8"
                )
                print(f"{span.span_id}: {done[span.span_id][:110]}", flush=True)
        except Exception as loi:  # noqa: BLE001 — một hình hỏng không được giết cả lượt chạy
            # Không ghi gì vào `done`, nên lần chạy sau tự mô tả lại hình này.
            print(f"{span.span_id}: HỎNG — {loi}", flush=True)
        finally:
            cho_cho.release()

    for path in _pdfs(args.pdf):
        deck = load_deck(path)
        figures = [
            s for s in deck.spans
            if s.kind == "figure" and (args.redo or s.span_id not in done)
        ]
        print(f"\n== {path.name}: {len(figures)} hình cần mô tả", flush=True)
        with pymupdf.open(path) as doc, ThreadPoolExecutor(args.jobs) as pool:
            for span in figures:
                # Dựng ảnh ở LUỒNG CHÍNH: pymupdf không dùng chung một Document
                # cho nhiều luồng được. Phần chậm là lượt gọi model, và phần đó
                # mới là phần chạy song song.
                png = doc[span.page - 1].get_pixmap(
                    clip=pymupdf.Rect(span.bbox), dpi=144
                ).tobytes("png")
                image = "data:image/png;base64," + base64.b64encode(png).decode()
                cho_cho.acquire()
                pool.submit(mo_ta, span, deck.titles.get(span.page, ""), image)

    print(f"\nXong: {len(done)} hình có mô tả trong {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
