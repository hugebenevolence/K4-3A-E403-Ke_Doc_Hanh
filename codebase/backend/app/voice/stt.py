"""Speech-to-text adapter interface.

Đổi provider ở đây, phần còn lại của app không cần biết provider nào đang chạy.
Test sớm với giọng địa phương/informal thật trong data — Whisper gốc yếu ở
tiếng Việt phương ngữ, ưu tiên thử PhoWhisper hoặc API đã tune tiếng Việt.
"""

from abc import ABC, abstractmethod


class SpeechToText(ABC):
    @abstractmethod
    async def transcribe_chunk(self, audio_chunk: bytes) -> str | None:
        """Nhận một chunk audio streaming, trả về text nếu đã đủ để transcribe,
        None nếu cần thêm audio."""
        raise NotImplementedError


class MockSTT(SpeechToText):
    """Trả cố định một câu — dùng để test luồng end-to-end khi chưa gắn provider thật."""

    async def transcribe_chunk(self, audio_chunk: bytes) -> str | None:
        return "[mock] học viên vừa nói gì đó"
