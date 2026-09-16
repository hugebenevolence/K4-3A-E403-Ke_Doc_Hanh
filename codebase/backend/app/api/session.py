"""Điều phối một lượt: talker nói đệm SONG SONG với reasoner chấm.

Đây là chỗ quyết định cảm giác nhanh/chậm của cả sản phẩm.

SỐ ĐO THẬT (gpt-5-nano/mini, reasoning effort minimal): talker mất ~1.8s tới
token đầu, node chấm mất 3.4–6.7s. Chạy song song nên tổng ≈ thời gian chấm chứ
không phải cộng dồn. Nhưng mục tiêu "tiếng đầu ra trong 400ms" đặt lúc thiết kế
là KHÔNG đạt được với một lượt gọi LLM — muốn đạt thì phải phát một câu đệm
dựng sẵn (không qua LLM) ngay khi lượt kết thúc.

Talker cố ý KHÔNG nằm trong graph: nó không tham gia quyết định gì, chỉ lấp
khoảng chờ. Nhét vào graph sẽ buộc phải chờ nó xong mới chạy tiếp — đúng cái
đang muốn tránh.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Literal

from app.domain.sanitize import sanitize_spoken
from app.ports.llm import LLMClient, ModelTier
from app.ports.tts import TextToSpeech
from app.prompts import registry

log = logging.getLogger(__name__)

TALKER_VERSION = "v1"
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


@dataclass(frozen=True)
class Event:
    kind: Literal["state", "transcript", "audio", "turn_done"]
    payload: Any


def _mark(existing: int | None, started: float) -> int:
    """Chấm mốc lần đầu tiên và giữ nguyên ở các lần sau."""
    return existing if existing is not None else int((perf_counter() - started) * 1000)


async def sentence_chunks(tokens: AsyncIterator[str]) -> AsyncIterator[str]:
    """Gom token tới khi hết câu rồi mới đẩy xuống TTS.

    Chờ sinh xong cả đoạn mới TTS là cộng dồn latency theo độ dài câu trả lời.
    """
    buffer = ""
    async for token in tokens:
        buffer += token
        while match := _SENTENCE_END.search(buffer):
            head, buffer = buffer[: match.end()].strip(), buffer[match.end() :]
            if head:
                yield head
    if buffer.strip():
        yield buffer.strip()


async def run_turn(
    state: dict[str, Any],
    *,
    graph,
    llm: LLMClient,
    tts: TextToSpeech,
    thread_id: str,
    reasoner_timeout_s: float = 20.0,
) -> AsyncIterator[Event]:
    """Chạy một lượt, phát event theo đúng thứ tự client cần nghe."""
    started = perf_counter()
    reasoner = asyncio.create_task(
        graph.ainvoke(state, config={"configurable": {"thread_id": thread_id}})
    )
    first_audio_ms: int | None = None

    try:
        # Talker: chỉ được nhắc lại lời học viên, tuyệt đối không chốt đúng/sai —
        # lúc nó nói thì reasoner còn chưa có kết quả. Luật này nằm trong prompt
        # talker/v1.md và phải có case eval riêng canh chừng.
        talker_tokens = llm.stream(
            system=registry.compose_system("talker", TALKER_VERSION),
            user=f"Học viên vừa nói:\n{state['student_text']}",
            tier=ModelTier.FAST,
        )
        async for raw in sentence_chunks(talker_tokens):
            if not (sentence := sanitize_spoken(raw)):
                continue
            yield Event("transcript", {"role": "agent", "text": sentence, "filler": True})
            # Đẩy từng chunk ra ngay. Gom đủ cả câu rồi mới gửi là cộng dồn
            # latency đúng bằng thời gian tổng hợp cả câu.
            async for chunk in tts.synthesize(sentence):
                first_audio_ms = _mark(first_audio_ms, started)
                yield Event("audio", chunk)

        # Không có timeout thì provider treo là học viên ngồi im vô hạn, không
        # có cách nào thoát ngoài tự tải lại trang. Thà mất một lượt.
        result = await asyncio.wait_for(reasoner, timeout=reasoner_timeout_s)
        said = sanitize_spoken(result["agent_says"])
        yield Event(
            "state", {"turn_state": result["turn_state"], "verdict": result.get("verdict")}
        )
        yield Event("transcript", {"role": "agent", "text": said, "filler": False})
        async for chunk in tts.synthesize(said):
            # Cũng phải chấm mốc ở đây: talker có thể không ra tiếng nào (stream
            # hỏng, hoặc bị bộ lọc cắt sạch). Chỉ chấm trong vòng lặp talker thì
            # những lượt đó báo first_audio=0ms trong khi thực tế chờ vài giây —
            # mà đây đúng là con số đang dùng để quyết kiến trúc.
            first_audio_ms = _mark(first_audio_ms, started)
            yield Event("audio", chunk)

        yield Event(
            "turn_done",
            {
                "result": result,
                "said": said,
                # Hai số cần theo dõi: bao lâu thì học viên nghe thấy tiếng đầu
                # tiên, và bao lâu thì có kết quả chấm.
                "latency_ms": {
                    "first_audio": first_audio_ms or 0,
                    "total": int((perf_counter() - started) * 1000),
                },
            },
        )
    finally:
        # Học viên ngắt kết nối giữa lượt là chuyện thường; không dọn thì task
        # chấm chạy mồ côi và lỗi của nó không ai nhận.
        reasoner.cancel()
        try:
            await reasoner
        except asyncio.CancelledError:
            pass
        except Exception:
            # Lỗi ở đây thường đã được nêu lại ở thân hàm; nhưng nếu generator
            # bị bỏ dở TRƯỚC khi await thì đây là chỗ duy nhất còn thấy nó.
            log.exception("Node chấm hỏng ở phiên %s", thread_id)
