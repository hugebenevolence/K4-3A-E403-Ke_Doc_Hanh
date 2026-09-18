"""Dựng lại lớp chữ cho một bộ slide chỉ có ảnh, để app giảng được trên nó.

    python scripts/ocr_pdf.py <pdf ảnh> <pdf ra>            # cả bộ
    python scripts/ocr_pdf.py <pdf ảnh> <pdf ra> --pages 1-2  # thử vài trang

Vì sao cần: có bộ slide xuất ra PDF dưới dạng MỘT ẢNH mỗi trang (đo được: 48
trang, 0 ô chữ). Bộ tách slide không có chữ nào để cắt thành ô, nên học viên
không chọn được vùng nào và bộ chấm không có gì để đối chiếu.

Cách làm: chụp từng trang, nhờ model có thị giác chép lại NGUYÊN VĂN chữ theo
từng khối kèm vị trí, rồi ghép vào một PDF mới — giữ nguyên ảnh gốc, thêm một
lớp chữ VÔ HÌNH đặt đúng chỗ từng khối. Người học vẫn thấy slide y như cũ, còn
bộ tách slide đọc được chữ và toạ độ như mọi bộ khác.

Chép nguyên văn chứ không tóm tắt: bộ chấm đối chiếu lời học viên với đúng chữ
trên slide, và luật "đọc lại nguyên văn" cũng so với chữ đó.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import sys
from pathlib import Path

import pymupdf
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import AsyncOpenAI

from app.config import settings

PROMPT = (
    "Đây là MỘT trang slide bài giảng, xuất ra dưới dạng ảnh. Chép lại TOÀN BỘ chữ "
    "nhìn thấy, NGUYÊN VĂN, đúng dấu tiếng Việt, không tóm tắt, không sửa, không dịch. "
    "Gom chữ thành các KHỐI như người đọc nhìn thấy: tiêu đề là một khối, mỗi đoạn "
    "hoặc mỗi gạch đầu dòng là một khối, chữ trong từng ô của sơ đồ là một khối. "
    "Với mỗi khối, cho toạ độ khung bao theo tỉ lệ của ảnh (0 là mép trái/trên, 1 là "
    "mép phải/dưới). Khối đầu tiên là tiêu đề trang nếu có. Bỏ qua logo và số trang."
)

# Font có đủ dấu tiếng Việt cho lớp chữ vô hình. Font dựng sẵn của PDF chỉ có
# bảng Latin-1: chèn chữ có dấu vào là mất dấu, và bộ chấm đọc ra "Xac dinh".
FONTS = [Path(r"C:\Windows\Fonts\arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]

RENDER_WIDTH = 1600
"""Bề ngang ảnh gửi đi (px). Đủ để đọc chữ nhỏ trên slide, không phí token."""

PARALLEL = 6


class Block(BaseModel):
    text: str = Field(description="Chữ của khối, nguyên văn")
    x0: float = Field(ge=0, le=1)
    y0: float = Field(ge=0, le=1)
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)


class PageText(BaseModel):
    blocks: list[Block]


async def read_page(client: AsyncOpenAI, png: bytes, sem: asyncio.Semaphore) -> PageText:
    image = "data:image/png;base64," + base64.b64encode(png).decode()
    async with sem:
        resp = await client.responses.parse(
            model=settings.model_standard,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": PROMPT},
                        {"type": "input_image", "image_url": image, "detail": "high"},
                    ],
                }
            ],
            text_format=PageText,
        )
    return resp.output_parsed or PageText(blocks=[])


def _fit(page: pymupdf.Page, rect: pymupdf.Rect, text: str, font: str) -> None:
    """Chèn chữ vô hình vừa khít khung — thu nhỏ cỡ chữ tới khi chứa hết."""
    size = max(4.0, min(rect.height * 0.8, 60.0))
    while size >= 2:
        if page.insert_textbox(rect, text, fontname=font, fontsize=size, render_mode=3) >= 0:
            return
        size *= 0.8
    # Khung quá nhỏ so với lượng chữ (model khoanh hụt): nới khung xuống dưới
    # thay vì bỏ chữ — mất chữ là mất căn cứ để chấm.
    page.insert_textbox(rect + (0, 0, 0, rect.height * 3), text, fontname=font, fontsize=2, render_mode=3)


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--pages", default="", help="ví dụ 1-2; bỏ trống là cả bộ")
    args = ap.parse_args()

    fontfile = next((f for f in FONTS if f.is_file()), None)
    if fontfile is None:
        print("Không tìm thấy font có dấu tiếng Việt", file=sys.stderr)
        return 1

    src = pymupdf.open(args.src)
    lo, _, hi = args.pages.partition("-")
    chon = range(int(lo) - 1, int(hi or lo)) if lo else range(len(src))

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    sem = asyncio.Semaphore(PARALLEL)
    anh = []
    for i in chon:
        page = src[i]
        zoom = RENDER_WIDTH / page.rect.width
        anh.append(page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png"))
    ket_qua = await asyncio.gather(*(read_page(client, png, sem) for png in anh))

    out = pymupdf.open()
    for i, doc in zip(chon, ket_qua, strict=True):
        out.insert_pdf(src, from_page=i, to_page=i)
        page = out[-1]
        page.insert_font(fontname="vn", fontfile=str(fontfile))
        w, h = page.rect.width, page.rect.height
        for b in doc.blocks:
            text = b.text.strip()
            if not text:
                continue
            rect = pymupdf.Rect(b.x0 * w, b.y0 * h, max(b.x1, b.x0 + 0.01) * w, max(b.y1, b.y0 + 0.01) * h)
            _fit(page, rect, text, "vn")
        print(f"trang {i + 1}: {len(doc.blocks)} khối · {doc.blocks[0].text[:60] if doc.blocks else '(trống)'}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.save(args.out, garbage=3, deflate=True)
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
