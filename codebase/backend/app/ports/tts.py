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
        """Trả audio cho một câu.

        HỢP ĐỒNG: mỗi phần tử yield ra phải là MỘT FILE ÂM THANH PHÁT ĐƯỢC ĐỘC
        LẬP (mp3/wav trọn vẹn), không phải mảnh byte của một file.

        Lý do: frontend coi mỗi binary frame là một clip và nạp thẳng vào thẻ
        <audio> qua blob URL. Yield mảnh byte dở dang thì trình duyệt không giải
        mã được và câu đó mất tiếng — lỗi này chỉ lộ ra khi cắm TTS thật, vì
        mock trả im lặng nên không ai nghe thấy gì bất thường.

        Muốn stream nhỏ giọt thật sự thì phải đổi frontend sang MediaSource
        Extensions; đó là stretch goal, không phải việc của adapter.
        """
