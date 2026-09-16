"""Port gọi LLM.

Call site chọn TIER chứ không chọn tên model — đổi model là đổi config, không
phải sửa code. Phân tầng này là quyết định về chi phí: ngân sách cả dự án là
$5 credit, xem bảng trong codebase/README.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from enum import Enum
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ModelTier(Enum):
    FAST = "fast"  # talker: paraphrase lấp chờ, cần TTFT thấp, không cần thông minh
    STANDARD = "standard"  # reasoner: chấm lời giải thích — quyết định AI trung tâm
    JUDGE = "judge"  # chấm rubric offline khi ghi vào eval/results — chạy thưa, không tiếc tiền


class LLMClient(ABC):
    @abstractmethod
    async def structured(
        self, *, system: str, user: str, schema: type[T], tier: ModelTier
    ) -> T:
        """Gọi có schema, trả về object đã validate.

        `system` phải là phần CỐ ĐỊNH (persona + rubric + span nguồn) và `user`
        là phần biến thiên — prompt caching của OpenAI chỉ ăn theo prefix chung,
        đảo thứ tự là mất giảm giá 90%.
        """

    @abstractmethod
    def stream(self, *, system: str, user: str, tier: ModelTier) -> AsyncIterator[str]:
        """Stream token để TTS cắt theo câu, không chờ sinh xong cả đoạn."""
