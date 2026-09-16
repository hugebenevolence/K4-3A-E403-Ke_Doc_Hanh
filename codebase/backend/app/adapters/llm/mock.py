"""LLM giả — chạy được toàn bộ luồng mà không tốn credit, không cần key.

Verdict quyết định theo độ dài lời giải thích, nên gõ dài dần là thấy được máy
trạng thái đi từ INCOMPLETE sang SUFFICIENT. Dùng để debug luồng, KHÔNG dùng để chấm.

Mock cố ý trích đúng span_id có thật trong prompt thay vì bịa một mã cho xong:
bộ lọc mã đoạn bịa sẽ loại mã giả, và khi đó demo mất luôn phần gợi ý đoạn cần
xem lại — tức là đường chạy mock không còn giống đường chạy thật nữa.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator

from app.ports.llm import LLMClient, ModelTier, T
from app.prompts.schemas import FollowupOutput, GradeOutput

_ENOUGH_WORDS = 40
_SPAN_IN_PROMPT = re.compile(r"^\[([^\]]+)\]", re.MULTILINE)


def _spans_from(system: str) -> list[str]:
    """Đọc mã đoạn ra từ mục ĐOẠN NGUỒN mà registry đã ghép vào system prompt."""
    return [f"[{m}]" for m in _SPAN_IN_PROMPT.findall(system)]


class MockLLM(LLMClient):
    async def structured(
        self, *, system: str, user: str, schema: type[T], tier: ModelTier
    ) -> T:
        if schema is GradeOutput:
            covered = len(user.split()) >= _ENOUGH_WORDS
            spans = _spans_from(system) or ["[KHONG-DOC-DUOC-SPAN]"]
            return schema(
                evidence=[
                    {
                        "span_id": span,
                        "quote": "ý cốt lõi giả lập",
                        "covered_by_student": covered,
                    }
                    for span in spans
                ],
                gap_summary="" if covered else "chưa nói tới nguyên nhân nằm ở đâu",
                contradiction="",
            )
        if schema is FollowupOutput:
            return schema(question="Chỗ đó thì vì sao lại xảy ra vậy bạn?", cites_span_id=None)
        raise NotImplementedError(f"MockLLM chưa hỗ trợ schema {schema.__name__}")

    async def stream(
        self, *, system: str, user: str, tier: ModelTier
    ) -> AsyncIterator[str]:
        for piece in ("À, ", "để mình nắm lại ", "ý bạn vừa nói nhé."):
            yield piece
