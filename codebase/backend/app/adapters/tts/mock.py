"""TTS giả — trả im lặng, chỉ để kiểm nhịp gửi audio frame."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.ports.tts import TextToSpeech


class MockTTS(TextToSpeech):
    async def synthesize(self, sentence: str) -> AsyncIterator[bytes]:
        yield b"\x00" * 320
