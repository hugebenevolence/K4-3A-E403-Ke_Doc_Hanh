"""Port speech-to-text, hướng realtime.

Interface trả partial chứ không chỉ trả final: partial về trong <500ms cho phép
hiện chữ lên màn hình ngay khi học viên đang nói, và cho talker khởi động sớm.
Chờ final mới làm gì là mất đứt 1-2 giây.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True)
class Transcript:
    text: str
    is_final: bool


class SpeechToText(ABC):
    @abstractmethod
    def stream(self, audio: AsyncIterator[bytes]) -> AsyncIterator[Transcript]:
        """Nhận audio chunk streaming, trả về transcript partial rồi final."""
