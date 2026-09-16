"""FastAPI entrypoint — cũng là composition root: chỗ duy nhất biết provider nào đang chạy.

Chạy: uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from langgraph.checkpoint.memory import InMemorySaver

from app.adapters.knowledge.local import InMemorySpanStore
from app.adapters.llm.mock import MockLLM
from app.adapters.store.jsonl import JsonlSessionLog, JsonProfileStore
from app.adapters.stt.mock import MockSTT
from app.adapters.tts.mock import MockTTS
from app.api.session import TALKER_VERSION, run_turn
from app.config import settings
from app.domain.log import TurnLog
from app.domain.session import TurnState
from app.domain.span import Span
from app.domain.verdict import Evidence, GradeResult, Verdict
from app.graph.build import build_graph
from app.graph.nodes import GRADER_VERSION, PERSONA_VERSION
from app.ports.knowledge import SpanStore
from app.ports.llm import LLMClient
from app.ports.store import ProfileStore, SessionLog
from app.ports.stt import SpeechToText
from app.ports.tts import TextToSpeech

app = FastAPI(title="Ke Doc Hanh — Track D3 teach-back")

CONCEPT = "vì sao LLM bịa"
DEMO_SPAN = Span(
    span_id="[T06-138]",
    text="(chưa nạp knowledge/spans.json — xem knowledge/README.md)",
)


def _build_deps() -> tuple[
    SpanStore, LLMClient, SpeechToText, TextToSpeech, SessionLog, ProfileStore
]:
    log = JsonlSessionLog(settings.session_log_file)
    profiles = JsonProfileStore(settings.profile_file)
    if settings.use_mocks:
        return InMemorySpanStore([DEMO_SPAN]), MockLLM(), MockSTT(), MockTTS(), log, profiles
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
    spans, llm, stt, tts, session_log, profiles = _build_deps()
    graph = build_graph(llm, spans, checkpointer=InMemorySaver())

    session_id = str(uuid.uuid4())
    # Hồ sơ theo học viên chứ không theo phiên — đó là điểm của trí nhớ xuyên
    # buổi. Không có student_id thì mọi người dùng chung một hồ sơ và nó vô nghĩa.
    student_id = ws.query_params.get("student_id", "demo")
    profile = await profiles.load(student_id)

    audio_buffer: list[bytes] = []
    first_turn = True
    turn_index = 0

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

            # Chỉ lượt đầu mới gửi thông tin phiên. Các lượt sau chỉ gửi lời học
            # viên, phần còn lại (followups_asked, asked_questions) do
            # checkpointer giữ. Gửi lại followups_asked từ đây là tạo ra hai
            # nguồn sự thật cho cùng một con số, sớm muộn cũng lệch nhau.
            turn_input: dict = {"student_text": student_text}
            if first_turn:
                turn_input |= {
                    "session_id": session_id,
                    "student_id": student_id,
                    "concept": CONCEPT,
                    "source_span_ids": [DEMO_SPAN.span_id],
                    "followups_asked": 0,
                    "recurring_gaps": dict(profile.recurring_gaps),
                }
                first_turn = False

            turn_state = TurnState.CHECKING.name
            async for event in run_turn(
                turn_input, graph=graph, llm=llm, tts=tts, thread_id=session_id
            ):
                if event.kind == "audio":
                    await ws.send_bytes(event.payload)
                elif event.kind == "state":
                    turn_state = event.payload["turn_state"]
                    await ws.send_json({"type": "state", "state": turn_state})
                elif event.kind == "turn_done":
                    grade = await _log_turn(
                        session_log, session_id, turn_index, student_text, event
                    )
                    profile.absorb(CONCEPT, grade)
                    await profiles.save(profile)
                    turn_index += 1
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

    except WebSocketDisconnect:
        pass


async def _log_turn(
    session_log, session_id: str, index: int, student_text: str, event
) -> GradeResult:
    """Ghi lượt ở dạng replay được.

    Giữ prompt version để sau khi sửa prompt vẫn dựng lại được lượt cũ — golden
    set sẽ lắp từ phiên thật thay vì bịa case. Quality bar khoá ở CP4, sau đó
    không thu thêm được nữa.
    """
    result = event.payload["result"]
    grade = GradeResult(
        verdict=Verdict(result["verdict"]),
        evidence=tuple(Evidence(**e) for e in result.get("evidence", [])),
        gap_summary=result.get("gap_summary", ""),
    )
    await session_log.append(
        TurnLog(
            session_id=session_id,
            turn_index=index,
            student_text=student_text,
            source_span_id=result["source_span_ids"][0],
            prompt_versions={
                "grader": GRADER_VERSION,
                "student_persona": PERSONA_VERSION,
                "talker": TALKER_VERSION,
            },
            grade=grade,
            agent_said=event.payload["said"],
            latency_ms=event.payload["latency_ms"],
        )
    )
    return grade


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
