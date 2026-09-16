"""Text-to-speech adapter interface.

Bắt buộc chunk theo câu khi stream — chờ hết cả đoạn LLM sinh xong mới TTS
sẽ cộng dồn latency theo độ dài câu trả lời (xem hồ sơ research latency).
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class TextToSpeech(ABC):
    @abstractmethod
    async def synthesize_sentence(self, sentence: str) -> AsyncIterator[bytes]:
        """Nhận MỘT câu đã hoàn chỉnh (không phải cả đoạn), trả về audio chunk streaming."""
        raise NotImplementedError


class MockTTS(TextToSpeech):
    async def synthesize_sentence(self, sentence: str) -> AsyncIterator[bytes]:
        yield b""
