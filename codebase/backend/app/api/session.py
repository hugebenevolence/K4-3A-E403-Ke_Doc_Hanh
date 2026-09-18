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

from app.config import settings
from app.domain.sanitize import speakable
from app.ports.llm import LLMClient, ModelTier
from app.ports.tts import TextToSpeech
from app.prompts import registry

log = logging.getLogger(__name__)

TALKER_VERSION = "v1"
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


@dataclass(frozen=True)
class Event:
    kind: Literal["state", "transcript", "audio", "turn_done", "activity"]
    payload: Any


# Tên node -> việc mà học viên hiểu được. Phát ra theo tiến trình THẬT của
# graph chứ không phải đếm giờ giả: Apple HIG khuyên dùng chỉ báo tiến trình
# xác định (determinate) thay vì vòng xoay mơ hồ, vì nó cho người ta biết còn
# bao lâu và hệ thống đang làm gì — ở đây còn quan trọng hơn bình thường, vì
# cả sản phẩm dựa vào việc học viên tin rằng agent thật sự đối chiếu với slide.
ACTIVITY = {
    "grade": "Đối chiếu với slide",
    "ask_followup": "Soạn câu hỏi",
    "close_taught": "Chốt lại",
    "close_review": "Chốt lại",
}


async def _drive_graph(graph, state, thread_id: str, steps: asyncio.Queue) -> dict:
    """Chạy graph và báo từng node vừa xong ra ngoài."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        async for update in graph.astream(state, config=config, stream_mode="updates"):
            for node in update:
                await steps.put(node)
    finally:
        # Báo "hết bước" KỂ CẢ KHI HỎNG. Không có finally thì graph hỏng giữa
        # chừng sẽ không ai đẩy None vào hàng đợi, vòng đọc bước ở run_turn đứng
        # chờ cho tới hết `reasoner_timeout_s` (20 giây!) rồi mới ném TimeoutError
        # — nên học viên vừa phải chờ 20 giây, vừa nhận lời nhắn sai nguyên nhân,
        # vì lỗi thật (hết hạn mức, provider 429) đã bị TimeoutError che mất.
        await steps.put(None)

    # stream_mode="updates" chỉ trả phần TỪNG NODE vừa ghi, không phải cả state
    # như ainvoke — nên những trường do lượt trước để lại (source_span_ids,
    # concept...) sẽ thiếu. Lấy bản đầy đủ từ checkpointer.
    snapshot = await graph.aget_state(config)
    return dict(snapshot.values)


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
    steps: asyncio.Queue[str | None] = asyncio.Queue()
    reasoner = asyncio.create_task(_drive_graph(graph, state, thread_id, steps))
    first_audio_ms: int | None = None

    try:
        # Talker: chỉ được nhắc lại lời học viên, tuyệt đối không chốt đúng/sai —
        # lúc nó nói thì reasoner còn chưa có kết quả. Luật này nằm trong prompt
        # talker/v1.md và phải có case eval riêng canh chừng.
        #
        # MẶC ĐỊNH TẮT, và đây là kết luận từ số đo chứ không phải bỏ cho gọn:
        # sau khi bật service_tier=priority, node chấm chỉ còn ~1.7s, trong khi
        # talker cần ~1.8s gọi LLM + ~2.4s TTS = ~4.2s mới ra được câu đệm. Nó
        # không thể lấp một khoảng ngắn hơn chính nó — bật lên chỉ làm học viên
        # phải nghe thêm một câu thừa rồi mới tới câu hỏi thật. Phần "agent
        # đang làm gì" giờ do chỉ báo tiến trình trên màn hình lo, hiện tức thì
        # và không tốn token. Bật lại nếu đổi sang tier chậm hoặc model chậm.
        if settings.enable_talker:
            talker_tokens = llm.stream(
                system=registry.compose_system("talker", TALKER_VERSION),
                # Không dán nhãn "Học viên" ở đây: model echo lại thành "Ừm,
                # học viên nói rằng..." — gọi người đối diện ở ngôi thứ ba,
                # nghe như máy đọc biên bản chứ không phải bạn học nghe giảng.
                user=f"Nội dung vừa nghe được:\n{state['student_text']}",
                tier=ModelTier.FAST,
            )
            async for raw in sentence_chunks(talker_tokens):
                if not (sentence := speakable(raw)):
                    continue
                yield Event(
                    "transcript", {"role": "agent", "text": sentence, "filler": True}
                )
                async for chunk in tts.synthesize(sentence):
                    first_audio_ms = _mark(first_audio_ms, started)
                    yield Event("audio", chunk)

                # ĐÚNG MỘT CÂU, cắt bằng code chứ không tin prompt. Quan sát
                # thật: talker nói ba câu, và câu thứ ba là "Bạn có muốn mình
                # gợi ý cách diễn đạt lại ý này ngắn gọn hơn để học thuộc
                # không?" — vừa phá vai học trò (đang đề nghị dạy lại học viên)
                # vừa phá tiền đề của cả track. Câu đầu gần như luôn là câu
                # nhắc lại đúng ý; những câu sau là chỗ model bắt đầu tự diễn.
                break

        # Báo từng bước agent vừa làm xong, để học viên thấy nó đang đối chiếu
        # với slide thật chứ không phải ngồi chờ một hộp đen.
        while (node := await asyncio.wait_for(steps.get(), reasoner_timeout_s)) is not None:
            if label := ACTIVITY.get(node):
                yield Event("activity", {"step": node, "label": label})

        # Không có timeout thì provider treo là học viên ngồi im vô hạn, không
        # có cách nào thoát ngoài tự tải lại trang. Thà mất một lượt.
        result = await asyncio.wait_for(reasoner, timeout=reasoner_timeout_s)
        said = speakable(result["agent_says"])
        understood = [speakable(p) for p in result.get("agent_understood") or []]
        yield Event(
            "transcript",
            {
                "role": "agent",
                "text": said,
                # Hiện thành gạch đầu dòng trên màn hình, KHÔNG đọc thành tiếng:
                # nghe thêm vài câu nhắc lại trước câu hỏi là học viên phải chờ
                # lâu hơn đúng lúc họ đang muốn trả lời.
                "understood": understood,
                "filler": False,
                # Span agent tự trích trong câu nói. An toàn để hiện nguyên văn:
                # persona bị cấm trích đúng ý học viên đang thiếu, nên cái nó
                # trích là chỗ học viên đã chạm tới hoặc chỗ nó thấy lấn cấn.
                "cites_span_id": result.get("cites_span_id"),
            },
        )
        async for chunk in tts.synthesize(said):
            # Cũng phải chấm mốc ở đây: talker có thể không ra tiếng nào (stream
            # hỏng, hoặc bị bộ lọc cắt sạch). Chỉ chấm trong vòng lặp talker thì
            # những lượt đó báo first_audio=0ms trong khi thực tế chờ vài giây —
            # mà đây đúng là con số đang dùng để quyết kiến trúc.
            first_audio_ms = _mark(first_audio_ms, started)
            yield Event("audio", chunk)

        # State đi SAU câu hỏi và tiếng, không phải trước. State mở mic cho học
        # viên; gửi nó trước thì đo được mic mở sẵn 2,4 giây trong lúc TTS còn
        # đang tổng hợp — giao diện báo "tới lượt bạn" khi agent còn chưa hỏi.
        yield Event(
            "state",
            {
                "turn_state": result["turn_state"],
                "verdict": result.get("verdict"),
                # Căn cứ chấm, gửi nguyên về client: đây là dữ liệu THẬT model
                # vừa dùng để quyết định, và là thứ làm học viên tin được rằng
                # hệ thống bám slide chứ không phán bừa.
                "evidence": result.get("evidence") or [],
            },
        )
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
