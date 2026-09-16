"""Điều phối một lượt: talker nói đệm SONG SONG với reasoner chấm.

Đây là chỗ quyết định cảm giác nhanh/chậm của cả sản phẩm. Chạy tuần tự
(chấm xong mới nói) thì học viên ngồi im 1-2 giây sau mỗi lượt. Chạy song song
thì tiếng nói đầu tiên ra trong ~400ms, còn kết quả chấm về lúc talker vừa dứt.

Talker cố ý KHÔNG nằm trong graph: nó không tham gia quyết định gì, chỉ lấp
khoảng chờ. Nhét vào graph sẽ buộc phải chờ nó xong mới chạy tiếp — đúng cái
đang muốn tránh.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal

from app.ports.llm import LLMClient, ModelTier
from app.ports.tts import TextToSpeech
from app.prompts import registry

TALKER_VERSION = "v1"
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


@dataclass(frozen=True)
class Event:
    kind: Literal["state", "transcript", "audio"]
    payload: Any


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


async def _speak(tts: TextToSpeech, sentence: str) -> list[bytes]:
    return [chunk async for chunk in tts.synthesize(sentence)]


async def run_turn(
    state: dict[str, Any],
    *,
    graph,
    llm: LLMClient,
    tts: TextToSpeech,
    thread_id: str,
) -> AsyncIterator[Event]:
    """Chạy một lượt, phát event theo đúng thứ tự client cần nghe."""
    reasoner = asyncio.create_task(
        graph.ainvoke(state, config={"configurable": {"thread_id": thread_id}})
    )

    # Talker: chỉ được nhắc lại lời học viên, tuyệt đối không chốt đúng/sai —
    # lúc nó nói thì reasoner còn chưa có kết quả. Luật này nằm trong prompt
    # talker/v1.md và phải có case eval riêng canh chừng.
    talker_tokens = llm.stream(
        system=registry.load("talker", TALKER_VERSION),
        user=f"Học viên vừa nói:\n{state['student_text']}",
        tier=ModelTier.FAST,
    )
    async for sentence in sentence_chunks(talker_tokens):
        yield Event("transcript", {"role": "agent", "text": sentence, "filler": True})
        for chunk in await _speak(tts, sentence):
            yield Event("audio", chunk)

    result = await reasoner
    yield Event("state", {"turn_state": result["turn_state"], "verdict": result.get("verdict")})
    yield Event("transcript", {"role": "agent", "text": result["agent_says"], "filler": False})
    for chunk in await _speak(tts, result["agent_says"]):
        yield Event("audio", chunk)
