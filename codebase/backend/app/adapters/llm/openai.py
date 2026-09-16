"""Adapter OpenAI qua Responses API.

Vì sao Responses API chứ không phải Chat Completions: nó tách `instructions`
(phần cố định) khỏi `input` (phần biến thiên) đúng như port đã thiết kế, và
đúng thứ tự mà prompt caching cần — đo thực tế thấy cache ăn từ lượt gọi thứ
hai trở đi (1664/1822 token được tính giá 10%).

Schema ép ở tầng API bằng `text_format`, không phải xin model trả JSON trong
prompt. Đây là bài học từ AskTIM: tin model tự serialize thì sớm muộn cả bọc
JSON hỏng sẽ đổ thẳng ra cho học viên.

REASONING EFFORT là quyết định quan trọng nhất trong file này. Đo trên
gpt-5-nano với cùng một câu:

    effort      TTFT      output token
    minimal     1.8s      34
    low         2.3s      187
    (mặc định)  5.5s      753

Mặc định đốt 753 token reasoning cho một câu nhắc lại — vừa chậm gấp ba vừa
đắt gấp hai mươi. Nên mỗi tier ghim effort riêng theo việc nó làm.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.config import settings
from app.ports.llm import LLMClient, ModelTier, T

_MODEL = {
    ModelTier.FAST: settings.model_fast,
    ModelTier.STANDARD: settings.model_standard,
    ModelTier.JUDGE: settings.model_judge,
}

_EFFORT = {
    ModelTier.FAST: "minimal",  # chỉ nhắc lại lời học viên, không có gì để suy nghĩ
    ModelTier.STANDARD: "minimal",  # đủ cho việc đối chiếu từng ý; xem ghi chú đầu file
    ModelTier.JUDGE: "low",  # chấm rubric offline, chạy thưa nên đổi tốc lấy độ chắc
}


class OpenAILLM(LLMClient):
    def __init__(self, client: AsyncOpenAI | None = None):
        # Client dùng chung cho cả tiến trình: mỗi lần tạo mới là một
        # connection pool mới, mở theo từng phiên sẽ sớm cạn socket.
        self._client = client or AsyncOpenAI(api_key=settings.openai_api_key)

    async def structured(
        self, *, system: str, user: str, schema: type[T], tier: ModelTier
    ) -> T:
        response = await self._client.responses.parse(
            model=_MODEL[tier],
            instructions=system,
            input=user,
            text_format=schema,
            reasoning={"effort": _EFFORT[tier]},
            service_tier=settings.openai_service_tier,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError(
                f"{_MODEL[tier]} không trả về output khớp schema {schema.__name__}"
            )
        return parsed

    async def stream(
        self, *, system: str, user: str, tier: ModelTier
    ) -> AsyncIterator[str]:
        events = await self._client.responses.create(
            model=_MODEL[tier],
            instructions=system,
            input=user,
            reasoning={"effort": _EFFORT[tier]},
            service_tier=settings.openai_service_tier,
            stream=True,
        )
        async for event in events:
            if event.type == "response.output_text.delta":
                yield event.delta
