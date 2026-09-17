"""Nạp bài học + span nguồn từ một file JSON.

Bài thật và bài demo dùng CHUNG một định dạng, chỉ khác chỗ để file: bài thật
nằm ở knowledge/ (đã gitignore vì data pack không được commit), bài demo nằm ở
fixtures/ (tự bịa, commit được). Nhờ vậy đường chạy demo và đường chạy thật là
một, không phải hai nhánh code khác nhau.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from app.domain.lesson import Lesson
from app.domain.span import Span
from app.ports.knowledge import SpanStore


class InMemorySpanStore(SpanStore):
    def __init__(self, spans: Sequence[Span]):
        self._spans = {s.span_id: s for s in spans}

    async def get(self, span_id: str) -> Span:
        try:
            return self._spans[span_id]
        except KeyError:
            raise KeyError(f"Không có span {span_id} trong kho đã nạp") from None

    async def get_many(self, span_ids: Sequence[str]) -> tuple[Span, ...]:
        return tuple([await self.get(s) for s in span_ids])


def load_lesson(path: Path) -> tuple[Lesson, InMemorySpanStore]:
    """Đọc file bài học. Thiếu file thì báo lỗi rõ ràng chứ không im lặng chạy
    tiếp với nguồn rỗng — grounding rỗng nghĩa là chấm bịa."""
    if not path.is_file():
        raise FileNotFoundError(
            f"Không thấy file bài học tại {path}. Xem knowledge/README.md để nạp."
        )

    raw = json.loads(path.read_text(encoding="utf-8"))
    spans = [
        Span(
            span_id=s["span_id"],
            text=s["text"],
            page=s.get("page"),
            bbox=tuple(s["bbox"]) if s.get("bbox") else None,
            lines=tuple(s["lines"]) if s.get("lines") else None,
        )
        for s in raw["spans"]
    ]
    lesson = Lesson(
        concept=raw["concept"],
        source_span_ids=tuple(s.span_id for s in spans),
        vocabulary=tuple(raw.get("vocabulary", ())),
        kind=raw.get("kind", "slide"),
        code=raw.get("code", ""),
        language=raw.get("language", "python"),
    )
    return lesson, InMemorySpanStore(spans)
