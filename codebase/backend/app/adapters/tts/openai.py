"""Adapter TTS dùng OpenAI.

VÌ SAO KHÔNG PHẢI FPT.AI như kế hoạch ban đầu: FPT trả về một URL ASYNC chứ
không phải audio, và tài liệu ghi rõ "chờ từ 5 giây đến 2 phút" — không dùng
được cho hội thoại. Thử key free thì còn bị chặn luôn:
`{"message":"API rate limit exceeded for 'free'"}` ở cả ba lần gọi liên tiếp.

OpenAI trả audio bytes ngay trong response, khớp đúng hợp đồng của port. Đo
thật: gpt-4o-mini-tts ~3.5s cho một câu, ra mp3 hợp lệ. (tts-1 mất 44s, loại.)

Giọng không phải người Việt bản địa — đây là đánh đổi có ý thức để có đường
audio chạy được. Muốn giọng Việt thật thì nâng cấp gói FPT rồi viết adapter
khác cạnh file này; phần còn lại của app không phải sửa gì.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.config import settings
from app.ports.tts import TextToSpeech


class OpenAITTS(TextToSpeech):
    def __init__(self, client: AsyncOpenAI | None = None, voice: str = "alloy"):
        self._client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        self._voice = voice

    async def synthesize(self, sentence: str) -> AsyncIterator[bytes]:
        if not sentence.strip():
            return
        response = await self._client.audio.speech.create(
            model=settings.model_tts,
            voice=self._voice,
            input=sentence,
            response_format="mp3",
            speed=settings.tts_speed,
        )
        # Đúng MỘT lần yield, cả câu trong một file mp3 trọn vẹn: frontend nạp
        # thẳng từng frame vào thẻ <audio>, mảnh byte dở dang sẽ không giải mã
        # được. Xem hợp đồng trong app/ports/tts.py.
        yield response.content
