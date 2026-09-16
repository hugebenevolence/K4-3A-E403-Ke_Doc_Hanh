"""Test canh các lỗi làm hỏng mục tiêu độ trễ và làm rò tài nguyên.

Hai chỗ này không sai về kết quả nên test chức năng thường không bắt được —
phải canh riêng bằng thứ tự sự kiện.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.adapters.knowledge.local import InMemorySpanStore
from app.adapters.llm.mock import MockLLM
from app.api.session import run_turn
from app.domain.span import Span
from app.graph.build import build_graph
from app.ports.tts import TextToSpeech

SPAN = Span(span_id="[T06-138]", text="nguồn giả lập")
STATE = {
    "session_id": "s1",
    "student_id": "u1",
    "concept": "test",
    "source_span_ids": ["[T06-138]"],
    "student_text": "một lời giải thích ngắn",
    "followups_asked": 0,
}


class TracingTTS(TextToSpeech):
    """Ghi lại thời điểm sinh ra từng chunk, để phát hiện việc gom cả câu."""

    def __init__(self, trace: list[str]):
        self.trace = trace

    async def synthesize(self, sentence: str) -> AsyncIterator[bytes]:
        for i in range(3):
            self.trace.append(f"tts{i}")
            yield f"chunk{i}".encode()


def _graph():
    return build_graph(MockLLM(), InMemorySpanStore([SPAN]), checkpointer=InMemorySaver())


def test_audio_phai_chay_ra_ngay_chu_khong_gom_het_ca_cau():
    """Gom hết chunk của một câu rồi mới gửi là cộng dồn latency đúng bằng
    thời gian tổng hợp cả câu — mất ý nghĩa của việc cắt câu cho TTS."""

    async def main():
        trace: list[str] = []
        async for event in run_turn(
            STATE, graph=_graph(), llm=MockLLM(), tts=TracingTTS(trace), thread_id="s1"
        ):
            if event.kind == "audio":
                trace.append("gui")

        first_batch = trace[: trace.index("gui") + 1]
        # Nếu stream đúng: sinh 1 chunk là gửi ngay -> ["tts0", "gui"].
        # Nếu gom cả câu: ["tts0", "tts1", "tts2", "gui"].
        assert first_batch == ["tts0", "gui"], f"đang gom cả câu: {first_batch}"

    asyncio.run(main())


class ChattyLLM(MockLLM):
    """Talker nói nhiều câu — đúng cái quan sát được khi chạy thật."""

    async def stream(self, *, system: str, user: str, tier) -> AsyncIterator[str]:
        yield "Ừm, ý bạn là temperature ảnh hưởng tới kết quả. "
        yield "Bạn cho rằng nó làm mô hình tự tin nhưng sai. "
        yield "Bạn có muốn mình gợi ý cách diễn đạt lại cho dễ học thuộc không?"


def test_talker_chi_duoc_noi_dung_mot_cau():
    """Prompt quy định một câu nhưng model không nghe. Quan sát thật: nó nói ba
    câu, và câu thứ ba là 'Bạn có muốn mình gợi ý... để học thuộc không?' — vừa
    phá vai học trò (đang đề nghị dạy lại học viên) vừa phá tiền đề của track."""

    async def main():
        fillers = [
            e.payload["text"]
            async for e in run_turn(
                STATE, graph=_graph(), llm=ChattyLLM(), tts=TracingTTS([]), thread_id="s1"
            )
            if e.kind == "transcript" and e.payload.get("filler")
        ]
        assert len(fillers) == 1, f"talker nói {len(fillers)} câu: {fillers}"
        assert "học thuộc" not in fillers[0]

    asyncio.run(main())


def test_provider_treo_thi_bo_luot_chu_khong_treo_vo_han():
    """Không có timeout thì học viên ngồi im vô hạn, không cách nào thoát ngoài
    tải lại trang. Thà mất một lượt."""

    class SlowGraph:
        async def ainvoke(self, state, config=None):
            await asyncio.sleep(30)

    async def main():
        with pytest.raises(asyncio.TimeoutError):
            async for _ in run_turn(
                STATE,
                graph=SlowGraph(),
                llm=MockLLM(),
                tts=TracingTTS([]),
                thread_id="s1",
                reasoner_timeout_s=0.05,
            ):
                pass

    asyncio.run(main())


def test_bo_do_giua_chung_thi_khong_de_lai_task_treo():
    """Client ngắt kết nối giữa lượt là chuyện thường. Task chấm phải được dọn,
    không để lại 'Task exception was never retrieved' hoặc task chạy mồ côi."""

    async def main():
        gen = run_turn(
            STATE, graph=_graph(), llm=MockLLM(), tts=TracingTTS([]), thread_id="s1"
        )
        await anext(gen)  # lấy đúng một event rồi bỏ
        await gen.aclose()

        await asyncio.sleep(0)
        treo = [t for t in asyncio.all_tasks() if not t.done() and t is not asyncio.current_task()]
        assert not treo, f"còn task mồ côi: {treo}"

    asyncio.run(main())
