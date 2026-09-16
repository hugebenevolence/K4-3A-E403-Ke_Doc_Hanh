"""FastAPI entrypoint — cũng là composition root: chỗ duy nhất biết provider nào đang chạy.

Chạy: uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from langgraph.checkpoint.memory import InMemorySaver

from app.adapters.knowledge.local import InMemorySpanStore, LocalSpanStore
from app.adapters.llm.mock import MockLLM
from app.adapters.stt.mock import MockSTT
from app.adapters.tts.mock import MockTTS
from app.api.session import run_turn
from app.config import settings
from app.domain.session import TurnState
from app.domain.span import Span
from app.graph.build import build_graph
from app.ports.knowledge import SpanStore

app = FastAPI(title="Ke Doc Hanh — Track D3 teach-back")

DEMO_SPAN = Span(
    span_id="[T06-138]",
    text="(chưa nạp knowledge/spans.json — xem knowledge/README.md)",
)


def _build_deps() -> tuple[SpanStore, object, object, object]:
    if settings.use_mocks:
        return InMemorySpanStore([DEMO_SPAN]), MockLLM(), MockSTT(), MockTTS()
    raise NotImplementedError(
        "Chưa gắn provider thật. Viết adapter theo port trong app/ports/ rồi "
        "wire vào đây — không sửa call site ở chỗ khác."
    )


@app.get("/health")
async def health():
    return {"status": "ok", "mocks": settings.use_mocks}


@app.websocket("/ws/session")
async def teach_back_session(ws: WebSocket):
    """Một phiên = một học viên dạy lại một khái niệm.

    Audio đi bằng binary frame, điều khiển đi bằng JSON frame.
    Client chỉ được mở mic khi state cho phép VÀ audio agent đã phát xong —
    nếu không mic sẽ bắt lại chính giọng agent qua loa.
    """
    await ws.accept()
    spans, llm, stt, tts = _build_deps()
    graph = build_graph(llm, spans, checkpointer=InMemorySaver())

    session_id = str(uuid.uuid4())
    audio_buffer: list[bytes] = []
    followups_asked = 0

    await ws.send_json({"type": "state", "state": TurnState.STUDENT_TEACHING.name})

    try:
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                break

            if (chunk := message.get("bytes")) is not None:
                audio_buffer.append(chunk)
                continue

            if message.get("text") is None:
                continue
            if json.loads(message["text"]).get("type") != "explanation_done":
                continue

            await ws.send_json({"type": "state", "state": TurnState.CHECKING.name})
            student_text = await _transcribe(stt, audio_buffer)
            audio_buffer.clear()
            await ws.send_json(
                {"type": "transcript", "role": "student", "text": student_text}
            )

            turn_state = TurnState.CHECKING.name
            async for event in run_turn(
                {
                    "session_id": session_id,
                    "student_id": "demo",
                    "concept": "vì sao LLM bịa",
                    "source_span_ids": [DEMO_SPAN.span_id],
                    "student_text": student_text,
                    "followups_asked": followups_asked,
                },
                graph=graph,
                llm=llm,
                tts=tts,
                thread_id=session_id,
            ):
                if event.kind == "audio":
                    await ws.send_bytes(event.payload)
                elif event.kind == "state":
                    turn_state = event.payload["turn_state"]
                    await ws.send_json({"type": "state", "state": turn_state})
                else:
                    await ws.send_json({"type": "transcript", **event.payload})

            if TurnState[turn_state].is_terminal:
                await ws.send_json(
                    {
                        "type": "session_end",
                        "outcome": turn_state,
                        "source_span": DEMO_SPAN.span_id,
                    }
                )
                break
            followups_asked += 1

    except WebSocketDisconnect:
        pass


async def _transcribe(stt, chunks: list[bytes]) -> str:
    """MVP gom hết audio của lượt rồi mới STT.

    Port đã có sẵn dạng streaming (trả partial trước final), nên khi cắm
    Speechmatics vào để lấy partial <500ms thì chỉ sửa trong hàm này.
    """

    async def replay() -> AsyncIterator[bytes]:
        for c in chunks:
            yield c

    text = ""
    async for t in stt.stream(replay()):
        if t.is_final:
            text = t.text
    return text
