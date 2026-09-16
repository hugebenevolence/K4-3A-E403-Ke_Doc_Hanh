"""STT giả — phát lại partial rồi final để test nhịp frontend."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.ports.stt import SpeechToText, Transcript

_SCRIPT = "LLM bịa là vì dữ liệu huấn luyện vốn đã có thiên lệch sẵn rồi"


class MockSTT(SpeechToText):
    async def stream(self, audio: AsyncIterator[bytes]) -> AsyncIterator[Transcript]:
        words = _SCRIPT.split()
        async for _ in audio:
            pass
        for i in range(1, len(words)):
            yield Transcript(text=" ".join(words[:i]), is_final=False)
        yield Transcript(text=_SCRIPT, is_final=True)
