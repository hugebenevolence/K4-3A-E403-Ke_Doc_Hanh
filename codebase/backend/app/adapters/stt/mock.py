"""STT giả — phát lại partial rồi final để test nhịp frontend.

Cố ý trả một câu KHÔNG dính tới bài nào cụ thể: mock trước đây trả sẵn một câu
về bias dữ liệu, trong khi bài demo lại nói về nước sôi, nên người test tưởng
hệ thống chấm sai. Muốn thử nội dung thật thì dùng đường gõ chữ
(`explanation_text`), ở đó lời học viên là thật.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.ports.stt import SpeechToText, Transcript

_SCRIPT = "đây là lời nói giả lập, hãy dùng ô nhập chữ để thử nội dung thật"


class MockSTT(SpeechToText):
    async def stream(self, audio: AsyncIterator[bytes]) -> AsyncIterator[Transcript]:
        words = _SCRIPT.split()
        async for _ in audio:
            pass
        for i in range(1, len(words)):
            yield Transcript(text=" ".join(words[:i]), is_final=False)
        yield Transcript(text=_SCRIPT, is_final=True)
