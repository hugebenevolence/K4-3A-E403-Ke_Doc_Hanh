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

import logging
from collections.abc import AsyncIterator

from openai import AsyncOpenAI, OpenAIError

from app.config import settings
from app.ports.llm import LLMClient, LLMUnavailable, ModelTier, T

log = logging.getLogger(__name__)

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


def _log_cache(model: str, response) -> None:
    """Ghi lại mỗi lượt gọi ăn cache được bao nhiêu token.

    Prompt caching là chỗ 90% chi phí của prefix được giảm, và cả thiết kế
    registry (phần cố định trước, lời học viên sau) chỉ tồn tại vì nó. Nhưng
    trước giờ không có gì canh: đo tay đúng MỘT lần (1664/1822 token ăn cache)
    rồi thôi. Đổi prompt, đổi thứ tự ghép, hay mỗi vùng slide một prefix mới —
    cache trượt lúc nào cũng không ai biết, chỉ thấy hoá đơn.

    Đọc phòng thủ bằng getattr: tên trường usage là chuyện của SDK, và một dòng
    log không được phép làm hỏng lượt học.
    """
    try:
        usage = getattr(response, "usage", None)
        details = getattr(usage, "input_tokens_details", None)
        cached = getattr(details, "cached_tokens", None)
        log.info(
            "%s · token vào %s (cache %s) · ra %s",
            model,
            getattr(usage, "input_tokens", "?"),
            "?" if cached is None else cached,
            getattr(usage, "output_tokens", "?"),
        )
    except Exception:  # noqa: BLE001 — log hỏng không được kéo theo lượt học
        log.debug("Không đọc được usage để ghi cache", exc_info=True)


class OpenAILLM(LLMClient):
    def __init__(self, client: AsyncOpenAI | None = None):
        # Client dùng chung cho cả tiến trình: mỗi lần tạo mới là một
        # connection pool mới, mở theo từng phiên sẽ sớm cạn socket.
        self._client = client or AsyncOpenAI(api_key=settings.openai_api_key)

    async def structured(
        self, *, system: str, user: str, schema: type[T], tier: ModelTier
    ) -> T:
        try:
            response = await self._client.responses.parse(
                model=_MODEL[tier],
                instructions=system,
                input=user,
                text_format=schema,
                reasoning={"effort": _EFFORT[tier]},
                service_tier=settings.openai_service_tier,
            )
        except OpenAIError as err:
            # Dịch lỗi của SDK sang lỗi của PORT, để tầng trên nói đúng chuyện
            # gì đã xảy ra mà không cần biết nhà cung cấp nào. Nguyên văn lỗi
            # vẫn còn trong chuỗi ngoại lệ cho log.
            raise LLMUnavailable(str(err)) from err
        _log_cache(_MODEL[tier], response)
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError(
                f"{_MODEL[tier]} không trả về output khớp schema {schema.__name__}"
            )
        return parsed

    async def stream(
        self, *, system: str, user: str, tier: ModelTier
    ) -> AsyncIterator[str]:
        try:
            events = await self._client.responses.create(
                model=_MODEL[tier],
                instructions=system,
                input=user,
                reasoning={"effort": _EFFORT[tier]},
                service_tier=settings.openai_service_tier,
                stream=True,
            )
        except OpenAIError as err:
            raise LLMUnavailable(str(err)) from err
        async for event in events:
            if event.type == "response.output_text.delta":
                yield event.delta
