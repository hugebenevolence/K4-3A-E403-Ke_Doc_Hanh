"""Port tra span nguồn.

Nội dung span nằm ngoài repo (knowledge/ đã gitignore) vì data pack của BTC
không được commit — xem knowledge/README.md để biết cách nạp.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.span import Span


class SpanStore(ABC):
    @abstractmethod
    async def get(self, span_id: str) -> Span: ...

    @abstractmethod
    async def get_many(self, span_ids: Sequence[str]) -> tuple[Span, ...]: ...
