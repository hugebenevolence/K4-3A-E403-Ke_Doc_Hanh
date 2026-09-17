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
from dataclasses import dataclass, replace
from pathlib import Path

import pymupdf

from app.adapters.knowledge.figures import Shape, find_figures
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


_ROUNDED_RECT = {"l": 4, "c": 32}
"""Dáng khung bo góc mà công cụ làm slide của khoá vẽ ra — đo trên cả bộ slide."""


def _raw_shapes(page: pymupdf.Page) -> list[Shape]:
    shapes = [Shape(tuple(info["bbox"]), "image") for info in page.get_image_info()]
    for drawing in page.get_drawings():
        ops = Counter(item[0] for item in drawing["items"])
        kind = "rect" if dict(ops) in (_ROUNDED_RECT, {"re": 1}) else "path"
        shapes.append(Shape(tuple(drawing["rect"]), kind))
    return shapes


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


@dataclass(frozen=True)
class Deck:
    """Cả bộ slide đã bóc, đọc file đúng MỘT lần.

    Ô nội dung, tiêu đề trang và thuật ngữ đều cần đọc cả bộ; ba hàm đọc riêng
    là ba lần mở PDF cho cùng một việc, mỗi lần vài giây.
    """

    spans: tuple[Span, ...]
    titles: dict[int, str]
    terms: tuple[str, ...]
    pages: int


FIGURE_LABEL_PREFIX = "Hình minh hoạ."


def _page_figures(path: Path) -> list[tuple[list[Shape], tuple[float, float]]]:
    with pymupdf.open(path) as doc:
        return [(_raw_shapes(page), (page.rect.width, page.rect.height)) for page in doc]


def _spans_of(pages, heights, slug: str, min_words: int, figures=None) -> list[Span]:
    spans = []
    for page_number, (lines, height) in enumerate(zip(pages, heights, strict=True), 1):
        regions = []
        if figures is not None:
            shapes, size = figures[page_number - 1]
            regions = find_figures(shapes, [(ln.text, ln.bbox) for ln in lines], size)
        # Nhãn chữ nằm trong hình thuộc về hình, không thành ô chữ riêng — nếu không
        # sơ đồ vòng tròn ở slide 3 vỡ thành hàng chục ô tí hon.
        # Tiêu đề trang không bao giờ là nhãn của hình: ảnh timeline phủ gần cả
        # trang (slide 5–9) từng nuốt luôn tiêu đề "Lịch sử AI 70 năm".
        title = {id(ln) for ln in _title_lines(lines, height)}
        regions = [
            replace(r, labels=tuple(i for i in r.labels if id(lines[i]) not in title))
            for r in regions
        ]
        taken = {i for r in regions for i in r.labels}
        text_lines = [ln for i, ln in enumerate(lines) if i not in taken]

        cards = [_to_card(g) for g in _group(text_lines, height)]
        spans += [
            Span(span_id=f"[{slug}-p{page_number}-{i:02d}]", text=text, page=page_number, bbox=bbox)
            for i, (text, bbox) in enumerate(cards, 1)
            if len(text.split()) >= min_words
        ]
        for k, region in enumerate(regions, 1):
            labels = " · ".join(lines[i].text for i in region.labels)
            text = f"{FIGURE_LABEL_PREFIX} Nhãn trong hình: {labels}." if labels else f"{FIGURE_LABEL_PREFIX}"
            spans.append(
                Span(
                    span_id=f"[{slug}-p{page_number}-f{k:02d}]",
                    text=text,
                    page=page_number,
                    bbox=tuple(round(v, 1) for v in region.bbox),
                    kind="figure",
                )
            )
    return spans


def _titles_of(pages, heights) -> dict[int, str]:
    # Trang không nhận ra được tiêu đề thì lấy dòng chữ đầu tiên — thà hơi dài
    # còn hơn để trống.
    titles = {}
    for number, (lines, height) in enumerate(zip(pages, heights, strict=True), 1):
        title = _title_lines(lines, height)
        titles[number] = " ".join(ln.text for ln in title) if title else (lines[0].text if lines else "")
    return titles


def deck_slug(path: Path) -> str:
    """Mã của bộ slide, lấy từ tên file — cũng là tiền tố của mọi mã ô trong bộ."""
    return re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")


_slug = deck_slug


def load_deck(path: Path, *, min_words: int = 4) -> Deck:
    pages, heights = _read_deck(path)
    return Deck(
        spans=tuple(_spans_of(pages, heights, _slug(path), min_words, _page_figures(path))),
        titles=_titles_of(pages, heights),
        # Rút từ CẢ bộ slide, không chỉ trang đang học: học viên hay nhắc tới
        # thuật ngữ ở trang khác khi giải thích.
        terms=extract_terms(*(line.text for lines in pages for line in lines)),
        pages=len(pages),
    )


def deck_terms(path: Path) -> tuple[str, ...]:
    """Thuật ngữ của CẢ bộ slide, để mớm cho bộ nhận dạng giọng nói."""
    pages, _ = _read_deck(path)
    return extract_terms(*(line.text for lines in pages for line in lines))


def parse_deck(path: Path, *, min_words: int = 4) -> list[Span]:
    """Bóc cả bộ slide thành span có toạ độ, trang đánh số từ 1."""
    pages, heights = _read_deck(path)
    return _spans_of(pages, heights, _slug(path), min_words)


def parse_slide(path: Path, page_number: int, *, min_words: int = 4) -> list[Span]:
    """Bóc một trang slide (đánh số từ 1) thành các span có toạ độ."""
    # Đếm trang thật chứ không suy từ span: trang cuối có thể không có ô nào
    # đủ chữ, và khi đó suy ra sẽ báo nhầm là trang không tồn tại.
    with pymupdf.open(path) as doc:
        count = len(doc)
    if not 1 <= page_number <= count:
        raise ValueError(f"{path.name} chỉ có {count} trang, không có trang {page_number}")
    return [sp for sp in parse_deck(path, min_words=min_words) if sp.page == page_number]


def attach_descriptions(deck: Deck, descriptions: dict[str, str]) -> Deck:
    """Ghép mô tả hình (sinh sẵn bằng model có thị giác) vào các ô hình.

    Không có mô tả thì ô hình giữ nguyên "Hình minh hoạ. Nhãn trong hình: …" —
    vẫn chọn được, chỉ là nguồn chấm mỏng, và vùng chọn mỏng thì giao diện tự
    mở rộng ra cả trang.
    """
    if not descriptions:
        return deck
    spans = tuple(
        replace(s, text=s.text.replace(FIGURE_LABEL_PREFIX, f"Hình: {desc}", 1))
        if s.kind == "figure" and (desc := descriptions.get(s.span_id))
        else s
        for s in deck.spans
    )
    return replace(deck, spans=spans)
