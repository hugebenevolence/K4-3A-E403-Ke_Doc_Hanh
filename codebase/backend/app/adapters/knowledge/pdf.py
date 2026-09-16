"""Bóc slide PDF thành span có toạ độ.

Mỗi span giữ page + bbox để giai đoạn sau highlight lại đúng vùng trên slide,
và để học viên kéo chọn vùng mình sắp dạy.

Hai chỗ khó, đều đã gặp thật trên bộ slide của khoá:

1. Watermark và header lặp trên mọi trang ("AI IN ACTION - HACKATHON") lẫn vào
   nội dung. Lọc bằng tần suất: chữ nào xuất hiện ở quá nửa số trang thì không
   phải nội dung của trang nào cả.

2. PyMuPDF trả mỗi DÒNG là một block, nên một ô nội dung trên slide bị vỡ thành
   năm sáu mảnh rời. Ghép lại theo cột và khoảng cách dọc, nếu không thì mỗi
   span chỉ là nửa câu và chấm theo đó là vô nghĩa.

Toạ độ giữ nguyên hệ của PyMuPDF (gốc trên-trái). Frontend dùng PDF.js với gốc
dưới-trái nên PHẢI đổi hệ trước khi vẽ — đây là bug kinh điển, xem ghi chú
trong codebase/README.md.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pymupdf

from app.domain.span import Span
from app.domain.terms import extract_terms

BOILERPLATE_PAGE_RATIO = 0.5
"""Chữ xuất hiện ở quá nửa số trang là watermark/header, không phải nội dung."""

COLUMN_TOLERANCE = 24.0
"""Lệch mép trái trong ngần này điểm thì vẫn coi là cùng một cột."""

LINE_GAP_FACTOR = 1.8
"""Khoảng trống dọc quá ngần này lần chiều cao dòng thì là sang ô nội dung khác."""


def _norm(text: str) -> str:
    return " ".join(text.split())


def _boilerplate(doc: pymupdf.Document) -> set[str]:
    seen = Counter()
    for page in doc:
        seen.update({_norm(b[4]) for b in page.get_text("blocks") if b[6] == 0 and b[4].strip()})
    threshold = max(2, int(len(doc) * BOILERPLATE_PAGE_RATIO))
    return {text for text, n in seen.items() if n >= threshold}


def _columns(blocks: list[tuple]) -> list[list[tuple]]:
    """Gom block thành cột theo MÉP TRÁI.

    Mép trái là tín hiệu cột thật của slide (ba ô nội dung cùng bắt đầu ở
    x=54/362/669). Gom theo độ chồng bề ngang thì hỏng: một block tiêu đề rộng
    chồng lên cả hai cột và bắc cầu dính chúng lại.

    Phải gom cột TRƯỚC rồi mới xét khoảng cách dọc — làm ngược lại thì block
    nằm cao hơn nhưng đứng sau trong thứ tự x cho khoảng cách ÂM, luôn lọt
    ngưỡng, và footer bị dán vào tiêu đề.
    """
    cols: list[list[tuple]] = []
    for block in sorted(blocks, key=lambda b: b[0]):
        if cols and abs(block[0] - cols[-1][0][0]) <= COLUMN_TOLERANCE:
            cols[-1].append(block)
        else:
            cols.append([block])
    return cols


def _merge(blocks: list[tuple]) -> list[tuple[str, tuple[float, float, float, float]]]:
    """Ghép các dòng liền nhau trong cùng một cột thành một ô nội dung."""
    cards: list[list[tuple]] = []
    for col in _columns(blocks):
        for block in sorted(col, key=lambda b: b[1]):
            if cards and cards[-1][-1] in col:
                last = cards[-1][-1]
                gap = block[1] - last[3]
                if 0 <= gap < LINE_GAP_FACTOR * max(last[3] - last[1], 1):
                    cards[-1].append(block)
                    continue
            cards.append([block])

    merged = []
    for card in cards:
        text = _norm(" ".join(b[4] for b in card))
        bbox = (
            min(b[0] for b in card),
            min(b[1] for b in card),
            max(b[2] for b in card),
            max(b[3] for b in card),
        )
        merged.append((text, bbox))
    return merged


def deck_terms(path: Path) -> tuple[str, ...]:
    """Thuật ngữ của CẢ bộ slide, để mớm cho bộ nhận dạng giọng nói.

    Lấy toàn bộ chứ không chỉ trang đang học: học viên hay nhắc tới thuật ngữ
    ở trang khác khi giải thích. Bỏ watermark/header trước khi rút, không thì
    "ACTION" và "HACKATHON" lọt vào từ điển.
    """
    with pymupdf.open(path) as doc:
        skip = _boilerplate(doc)
        content = [
            _norm(b[4])
            for page in doc
            for b in page.get_text("blocks")
            if b[6] == 0 and b[4].strip() and _norm(b[4]) not in skip
        ]
    return extract_terms(*content)


def parse_slide(path: Path, page_number: int, *, min_words: int = 4) -> list[Span]:
    """Bóc một trang slide (đánh số từ 1) thành các span có toạ độ."""
    with pymupdf.open(path) as doc:
        if not 1 <= page_number <= len(doc):
            raise ValueError(f"{path.name} chỉ có {len(doc)} trang, không có trang {page_number}")
        skip = _boilerplate(doc)
        page = doc[page_number - 1]
        blocks = [
            b
            for b in page.get_text("blocks")
            if b[6] == 0 and b[4].strip() and _norm(b[4]) not in skip
        ]
        cards = _merge(blocks)

    slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")
    return [
        Span(span_id=f"[{slug}-p{page_number}-{i:02d}]", text=text, page=page_number, bbox=bbox)
        for i, (text, bbox) in enumerate(cards, 1)
        if len(text.split()) >= min_words
    ]
