"""Bóc slide PDF thành span có toạ độ.

Mỗi span giữ page + bbox để highlight lại đúng vùng trên slide — đây là "nguồn
đúng chỗ" mà cả luồng dựa vào: học viên bôi đen một thuật ngữ thì phải mở rộng
ra được đúng cái ô chứa nó, và bước xem lại nguồn phải trỏ được đúng ô đó.

Những chỗ khó, đều đã gặp thật trên bộ slide của khoá:

1. Watermark, header, chân trang lặp trên mọi trang ("AI IN ACTION -
   HACKATHON", "DAY 02 · 37 / 83") lẫn vào nội dung. Lọc bằng tần suất, sau
   khi đã bỏ chữ số — chân trang có số trang đổi theo từng trang nên đếm
   nguyên văn thì không bao giờ thấy nó lặp.

2. PyMuPDF trả mỗi DÒNG riêng, nên một ô nội dung vỡ thành năm sáu mảnh. Phải
   ghép lại, và cách ghép đã sai hai lần:
   - Gom theo MÉP TRÁI: hỏng với chữ căn giữa. Dòng hai của một câu căn giữa
     bắt đầu ở x khác hẳn dòng một, nên bị xếp sang "cột" khác — slide 20 mất
     nửa câu "tra sổ (RAG), tools, và luôn kiểm chứng", và bộ chấm chấm học
     viên theo một câu cụt.
   - Gom theo độ chồng bề ngang với CẢ NHÓM: một dòng rộng bắc cầu dính hai
     cột lại. Giờ chỉ so với DÒNG CUỐI của nhóm, nên cột bên cạnh không bao
     giờ dính vào.

3. Tiêu đề trang nằm sát ô đầu tiên và từng bị dán vào nó. Tách riêng bằng cỡ
   chữ: dòng chữ to nhất ở phần trên trang, to hơn hẳn phần thân.

Toạ độ giữ nguyên hệ của PyMuPDF (gốc trên-trái), cùng hệ với canvas PDF.js
sau khi nhân tỉ lệ, nên frontend không phải lật trục y.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.domain.span import Span
from app.domain.terms import extract_terms

BOILERPLATE_PAGE_RATIO = 0.5
"""Chữ xuất hiện ở quá nửa số trang là watermark/header, không phải nội dung."""

LINE_GAP_FACTOR = 1.8
"""Khoảng trống dọc quá ngần này lần chiều cao dòng thì là sang ô nội dung khác."""

TITLE_ZONE = 0.1
"""Tiêu đề trang chỉ nằm trong ngần này phần trên cùng của trang.

Đo trên cả hai bộ slide: tiêu đề nằm ở y/H = 0,037 (trung vị), còn hàng ô nội
dung đầu tiên của slide 20 bắt đầu ở 0,17. Bản đầu đặt 0,2 và test bắt được
ngay: trang không có tiêu đề thì tiêu đề của ô đầu tiên (chữ to, ở trên cao)
bị nhận nhầm là tiêu đề trang và bị tách khỏi chính nội dung của nó."""

TITLE_SIZE_MARGIN = 0.5
"""Cỡ chữ tiêu đề phải to hơn chữ thân ít nhất ngần này điểm mới tính."""


@dataclass(frozen=True)
class Line:
    """Một dòng chữ trên slide — thứ PyMuPDF thực sự trả về."""

    text: str
    bbox: tuple[float, float, float, float]
    size: float

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]


def _norm(text: str) -> str:
    return " ".join(text.split())


def _shape(text: str) -> str:
    """Bỏ chữ số để nhận ra chân trang kiểu "DAY 02 · 37 / 83" là cùng một thứ."""
    return re.sub(r"\d+", "#", _norm(text))


def _raw_lines(page: pymupdf.Page) -> list[Line]:
    lines = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            text = _norm("".join(span["text"] for span in line["spans"]))
            if text:
                size = max(span["size"] for span in line["spans"])
                lines.append(Line(text, tuple(line["bbox"]), size))
    return lines


def _read_deck(path: Path) -> tuple[list[list[Line]], list[float]]:
    """Đọc MỘT lần các dòng nội dung của mọi trang, đã bỏ watermark/header.

    Phải đọc cả bộ mới biết chữ nào lặp trên mọi trang. Bản trước làm việc đó
    lại từ đầu cho mỗi trang được hỏi, nên đọc cả bộ slide thành O(trang²) —
    mà đánh chỉ mục thì cần đúng việc đọc cả bộ.
    """
    with pymupdf.open(path) as doc:
        pages = [_raw_lines(page) for page in doc]
        heights = [page.rect.height for page in doc]

    seen: Counter[str] = Counter()
    for lines in pages:
        seen.update({_shape(line.text) for line in lines})
    threshold = max(2, int(len(pages) * BOILERPLATE_PAGE_RATIO))
    skip = {shape for shape, n in seen.items() if n >= threshold}

    content = [[ln for ln in lines if _shape(ln.text) not in skip] for lines in pages]
    return content, heights


def _title_lines(lines: list[Line], page_height: float) -> list[Line]:
    """Dòng tiêu đề trang: chữ to nhất ở phần trên cùng, to hơn hẳn phần thân."""
    top = [ln for ln in lines if ln.bbox[1] < page_height * TITLE_ZONE]
    body_size = max((ln.size for ln in lines if ln not in top), default=0.0)
    title_size = max((ln.size for ln in top), default=0.0)
    return [ln for ln in top if ln.size == title_size and title_size > body_size + TITLE_SIZE_MARGIN]


def _group(lines: list[Line], page_height: float) -> list[list[Line]]:
    """Ghép các dòng thành ô nội dung. Tiêu đề trang (nếu có) luôn là nhóm đầu."""
    if not lines:
        return []

    title = _title_lines(lines, page_height)

    groups: list[list[Line]] = []
    for line in sorted(
        (ln for ln in lines if ln not in title),
        key=lambda ln: (round(ln.bbox[1]), ln.bbox[0]),
    ):
        x0, y0, x1, _ = line.bbox
        best: tuple[float, list[Line]] | None = None
        for group in groups:
            last = group[-1]
            overlap = min(x1, last.bbox[2]) - max(x0, last.bbox[0])
            gap = y0 - last.bbox[3]
            # Chiều cao dòng NHỎ hơn: so với dòng to thì một câu trích cỡ lớn
            # ngay trên sẽ nuốt luôn đoạn chữ thường nằm cách nó cả một khoảng.
            height = min(line.height, last.height)
            fits = overlap > 0 and -height < gap < LINE_GAP_FACTOR * height
            if fits and (best is None or gap < best[0]):
                best = (gap, group)
        if best:
            best[1].append(line)
        else:
            groups.append([line])

    return ([title] if title else []) + groups


def _to_card(group: list[Line]) -> tuple[str, tuple[float, float, float, float]]:
    text = _norm(" ".join(ln.text for ln in group))
    bbox = (
        min(ln.bbox[0] for ln in group),
        min(ln.bbox[1] for ln in group),
        max(ln.bbox[2] for ln in group),
        max(ln.bbox[3] for ln in group),
    )
    return text, bbox


def deck_terms(path: Path) -> tuple[str, ...]:
    """Thuật ngữ của CẢ bộ slide, để mớm cho bộ nhận dạng giọng nói.

    Lấy toàn bộ chứ không chỉ trang đang học: học viên hay nhắc tới thuật ngữ
    ở trang khác khi giải thích. Bỏ watermark/header trước khi rút, không thì
    "ACTION" và "HACKATHON" lọt vào từ điển.
    """
    pages, _ = _read_deck(path)
    return extract_terms(*(line.text for lines in pages for line in lines))


def deck_outline(path: Path) -> list[dict]:
    """Dàn ý cả bộ slide: mỗi trang một dòng tiêu đề, để thanh bên liệt kê được
    "Slide 20 · Giới hạn bẩm sinh…" thay vì một cột số trang vô nghĩa.

    Trang không nhận ra được tiêu đề thì lấy dòng chữ đầu tiên — thà hơi dài
    còn hơn để trống.
    """
    pages, heights = _read_deck(path)
    outline = []
    for number, (lines, height) in enumerate(zip(pages, heights, strict=True), 1):
        title = _title_lines(lines, height)
        text = " ".join(ln.text for ln in title) if title else (lines[0].text if lines else "")
        outline.append({"page": number, "title": text})
    return outline


def parse_deck(path: Path, *, min_words: int = 4) -> list[Span]:
    """Bóc cả bộ slide thành span có toạ độ, trang đánh số từ 1."""
    pages, heights = _read_deck(path)
    slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")
    spans = []
    for page_number, (lines, height) in enumerate(zip(pages, heights, strict=True), 1):
        cards = [_to_card(g) for g in _group(lines, height)]
        spans += [
            Span(span_id=f"[{slug}-p{page_number}-{i:02d}]", text=text, page=page_number, bbox=bbox)
            for i, (text, bbox) in enumerate(cards, 1)
            if len(text.split()) >= min_words
        ]
    return spans


def parse_slide(path: Path, page_number: int, *, min_words: int = 4) -> list[Span]:
    """Bóc một trang slide (đánh số từ 1) thành các span có toạ độ."""
    # Đếm trang thật chứ không suy từ span: trang cuối có thể không có ô nào
    # đủ chữ, và khi đó suy ra sẽ báo nhầm là trang không tồn tại.
    with pymupdf.open(path) as doc:
        count = len(doc)
    if not 1 <= page_number <= count:
        raise ValueError(f"{path.name} chỉ có {count} trang, không có trang {page_number}")
    return [sp for sp in parse_deck(path, min_words=min_words) if sp.page == page_number]
