"""LLM giả — chạy được toàn bộ luồng mà không tốn credit, không cần key.

Verdict quyết định theo độ dài lời giải thích, nên gõ dài dần là thấy được máy
trạng thái đi từ INCOMPLETE sang SUFFICIENT. Dùng để debug luồng, KHÔNG dùng để chấm.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.ports.llm import LLMClient, ModelTier, T
from app.prompts.schemas import FollowupOutput, GradeOutput

_ENOUGH_WORDS = 40


class MockLLM(LLMClient):
    async def structured(
        self, *, system: str, user: str, schema: type[T], tier: ModelTier
    ) -> T:
        if schema is GradeOutput:
            covered = len(user.split()) >= _ENOUGH_WORDS
            return schema(
                evidence=[
                    {
                        "span_id": "[mock-001]",
                        "quote": "ý cốt lõi giả lập",
                        "covered_by_student": covered,
                    }
                ],
                gap_summary="" if covered else "chưa nói tới nguồn gốc của vấn đề",
                verdict="sufficient" if covered else "incomplete",
            )
        if schema is FollowupOutput:
            return schema(question="Chỗ đó thì vì sao lại xảy ra vậy bạn?", cites_span_id=None)
        raise NotImplementedError(f"MockLLM chưa hỗ trợ schema {schema.__name__}")

    async def stream(
        self, *, system: str, user: str, tier: ModelTier
    ) -> AsyncIterator[str]:
        for piece in ("À, ", "để mình nắm lại ", "ý bạn vừa nói nhé."):
            yield piece
