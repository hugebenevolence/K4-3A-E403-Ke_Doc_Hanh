"""Port text-to-speech.

Nhận MỘT câu đã hoàn chỉnh, không nhận cả đoạn: tầng trên buffer token tới khi
gặp . ! ? rồi mới flush xuống đây. Chờ LLM sinh xong cả đoạn mới TTS là cộng
dồn latency theo độ dài câu trả lời.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class TextToSpeech(ABC):
    @abstractmethod
    def synthesize(self, sentence: str) -> AsyncIterator[bytes]:
        """Trả audio chunk streaming cho một câu."""
