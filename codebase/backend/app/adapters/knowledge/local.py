"""Nạp span nguồn từ knowledge/ (thư mục đã gitignore).

Data pack của BTC không được commit, nên repo chỉ có loader; nội dung span phải
tự nạp về máy — xem knowledge/README.md. Thiếu file thì báo lỗi rõ ràng chứ
không im lặng chạy tiếp với nguồn rỗng, vì grounding rỗng nghĩa là chấm bịa.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from app.domain.span import Span
from app.ports.knowledge import SpanStore


class LocalSpanStore(SpanStore):
    def __init__(self, path: Path):
        if not path.is_file():
            raise FileNotFoundError(
                f"Chưa có file span tại {path}. Xem knowledge/README.md để nạp từ brief/data/."
            )
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._spans = {
            s["span_id"]: Span(
                span_id=s["span_id"],
                text=s["text"],
                page=s.get("page"),
                bbox=tuple(s["bbox"]) if s.get("bbox") else None,
            )
            for s in raw
        }

    async def get(self, span_id: str) -> Span:
        try:
            return self._spans[span_id]
        except KeyError:
            raise KeyError(f"Không có span {span_id} trong kho đã nạp") from None

    async def get_many(self, span_ids: Sequence[str]) -> tuple[Span, ...]:
        return tuple([await self.get(s) for s in span_ids])


class InMemorySpanStore(SpanStore):
    """Dùng cho test và cho luồng mock — không đụng tới data pack."""

    def __init__(self, spans: Sequence[Span]):
        self._spans = {s.span_id: s for s in spans}

    async def get(self, span_id: str) -> Span:
        return self._spans[span_id]

    async def get_many(self, span_ids: Sequence[str]) -> tuple[Span, ...]:
        return tuple(self._spans[s] for s in span_ids)
