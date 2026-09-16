"""FastAPI entrypoint — cũng là composition root: chỗ duy nhất biết provider nào đang chạy.

Chạy: uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import json
import logging
import uuid
from functools import lru_cache

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.memory import InMemorySaver

from app.adapters.knowledge.local import load_lesson
from app.adapters.llm.mock import MockLLM
from app.adapters.store.jsonl import JsonlSessionLog, JsonProfileStore
from app.adapters.stt.mock import MockSTT
from app.adapters.tts.mock import MockTTS
from app.api.live_turn import LiveTurn
from app.api.session import TALKER_VERSION, run_turn
from app.config import settings
from app.domain.lesson import Lesson
from app.domain.log import TurnLog
from app.domain.session import TurnState
from app.domain.verdict import Evidence, GradeResult, Verdict
from app.graph.build import build_graph
from app.graph.nodes import GRADER_VERSION, PERSONA_VERSION
from app.ports.knowledge import SpanStore
from app.ports.llm import LLMClient
from app.ports.store import ProfileStore, SessionLog
from app.ports.stt import SpeechToText
from app.ports.tts import TextToSpeech

log = logging.getLogger(__name__)

app = FastAPI(title="Ke Doc Hanh — Track D3 teach-back")

# Frontend chạy ở cổng khác (http.server 5500) nên fetch /lesson là cross-origin.
# WebSocket không cần CORS nhưng fetch thì có. Chỉ mở cho localhost — đây là
# prototype chạy máy cá nhân, không deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["GET"],
    allow_headers=["*"],
)

def _build_deps() -> tuple[
    Lesson, SpanStore, LLMClient, SpeechToText, TextToSpeech, SessionLog, ProfileStore
]:
    # Gọi mỗi lần mở kết nối. Với mock thì không sao, nhưng khi viết adapter
    # thật thì HTTP client phải là singleton ở tầng module — tạo client mới cho
    # mỗi phiên sẽ mở thừa connection pool và sớm muộn cạn socket.
    session_log = JsonlSessionLog(settings.session_log_file)
    profiles = JsonProfileStore(settings.profile_file)

    if settings.use_mocks:
        lesson, spans = load_lesson(settings.demo_lesson_file)
        return lesson, spans, MockLLM(), MockSTT(), MockTTS(), session_log, profiles

    # Bài thật nếu đã nạp, không thì vẫn dùng bài demo — để chạy LLM thật được
    # ngay mà chưa cần đụng tới data pack.
    lesson_file = (
        settings.lesson_file if settings.lesson_file.is_file() else settings.demo_lesson_file
    )
    lesson, spans = load_lesson(lesson_file)
    llm, stt, tts = _shared_providers()
    return lesson, spans, llm, stt, tts, session_log, profiles


@lru_cache(maxsize=1)
def _shared_providers() -> tuple[LLMClient, SpeechToText, TextToSpeech]:
    """Dùng chung cho cả tiến trình: mỗi lần tạo mới là một connection pool mới,
    mở theo từng phiên sẽ sớm cạn socket."""
    from app.adapters.llm.openai import OpenAILLM
    from app.adapters.stt.speechmatics import SpeechmaticsRealtimeSTT
    from app.adapters.tts.openai import OpenAITTS

    stt = SpeechmaticsRealtimeSTT() if settings.speechmatics_api_key else MockSTT()
    if not settings.speechmatics_api_key:
        log.warning("Chưa có SPEECHMATICS_API_KEY — đường nói dùng mock, hãy gõ chữ để thử")
    return OpenAILLM(), stt, OpenAITTS()


@app.get("/lesson")
async def lesson_info():
    """Frontend hỏi bài học đang chạy để hiện lên màn hình, thay vì chép cứng."""
    lesson, _, *_ = _build_deps()
    return {"concept": lesson.concept, "source_span_ids": list(lesson.source_span_ids)}


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
    lesson, spans, llm, stt, tts, session_log, profiles = _build_deps()
    graph = build_graph(llm, spans, checkpointer=InMemorySaver())

    session_id = str(uuid.uuid4())
    # Hồ sơ theo học viên chứ không theo phiên — đó là điểm của trí nhớ xuyên
    # buổi. Không có student_id thì mọi người dùng chung một hồ sơ và nó vô nghĩa.
    student_id = ws.query_params.get("student_id", "demo")
    profile = await profiles.load(student_id)

    live: LiveTurn | None = None
    first_turn = True
    turn_index = 0
    review_spans: list[str] = []

    async def partial_to_client(text: str) -> None:
        """Chữ chạy lên màn hình khi học viên còn đang nói — không có cái này
        thì họ nói vào khoảng không, không biết mic có ăn hay không."""
        await ws.send_json({"type": "partial", "text": text})

    await ws.send_json({"type": "state", "state": TurnState.STUDENT_TEACHING.name})

    try:
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                break

            if (chunk := message.get("bytes")) is not None:
                # Mở phiên nhận dạng ngay ở gói audio đầu tiên của lượt, để
                # partial chạy lên màn hình trong lúc học viên còn đang nói.
                if live is None:
                    live = LiveTurn(stt, partial_to_client)
                live.feed(chunk)
                continue

            if message.get("text") is None:
                continue
            command = json.loads(message["text"])

            # Hai đường vào cùng dẫn tới một chỗ: nói (qua STT) hoặc gõ chữ.
            # Đường gõ chữ không phải tạm bợ — nó test được phần sư phạm mà
            # không lẫn lỗi nhận dạng giọng nói, và là phương án dự phòng nếu
            # mic hỏng giữa buổi demo.
            if command.get("type") == "explanation_text":
                if live is not None:
                    await live.abort()
                    live = None
                await ws.send_json({"type": "state", "state": TurnState.CHECKING.name})
                student_text = str(command.get("text", ""))
            elif command.get("type") == "explanation_done":
                await ws.send_json({"type": "state", "state": TurnState.CHECKING.name})
                if live is None:
                    student_text = ""
                else:
                    try:
                        student_text = await live.finish()
                    except Exception:
                        # STT hỏng KHÔNG được giết cả phiên. Chỗ này trước đây
                        # nằm ngoài khối bảo vệ bên dưới nên một lượt nhận dạng
                        # lỗi là rớt kết nối, học viên chỉ thấy "Đã ngắt kết nối".
                        log.exception("STT hỏng ở phiên %s", session_id)
                        await ws.send_json(
                            {
                                "type": "error",
                                "message": "Mình chưa nghe rõ được. Bạn thử lại, hoặc gõ chữ cũng được.",
                            }
                        )
                        await ws.send_json(
                            {"type": "state", "state": turn_state_for_retry(first_turn)}
                        )
                        continue
                    finally:
                        live = None
            else:
                continue

            if not student_text.strip():
                # Bấm chốt lượt mà chưa nói gì (hoặc bấm hai lần liên tiếp).
                # Chạy tiếp sẽ tiêu mất một lượt hỏi ngược vì lời rỗng chắc
                # chắn bị chấm là chưa đủ — trả lại lượt thay vì phạt oan.
                await ws.send_json(
                    {"type": "error", "message": "Mình chưa nghe thấy gì, bạn thử nói lại nhé."}
                )
                await ws.send_json({"type": "state", "state": turn_state_for_retry(first_turn)})
                continue

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
                    "concept": lesson.concept,
                    "source_span_ids": list(lesson.source_span_ids),
                    "followups_asked": 0,
                    "recurring_gaps": dict(profile.recurring_gaps),
                }
                first_turn = False

            turn_state = TurnState.CHECKING.name
            try:
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
                        profile.absorb(lesson.concept, grade)
                        await profiles.save(profile)
                        review_spans = event.payload["result"].get("review_span_ids", [])
                        turn_index += 1
                    else:
                        await ws.send_json({"type": "transcript", **event.payload})
            except WebSocketDisconnect:
                raise
            except Exception:
                # Provider thật sẽ hỏng theo đủ kiểu: hết quota, timeout, 401,
                # JSON méo. Để lỗi thoát ra đây là rớt kết nối giữa buổi học mà
                # học viên không nhận được lời nào. Thà mất một lượt còn hơn
                # mất cả phiên — trả về lượt nói để họ thử lại.
                log.exception("Lượt %d của phiên %s hỏng", turn_index, session_id)
                await ws.send_json(
                    {"type": "error", "message": "Mình nghe chưa rõ, bạn nói lại giúp mình nhé."}
                )
                turn_state = TurnState.STUDENT_TEACHING.name
                await ws.send_json({"type": "state", "state": turn_state})

            if TurnState[turn_state].is_terminal:
                await ws.send_json(
                    {
                        "type": "session_end",
                        "outcome": turn_state,
                        # Đoạn nên xem lại = những ý học viên chưa chạm tới ở
                        # lần chấm cuối. Không phải đáp án, chỉ là chỗ để quay lại.
                        "review_spans": review_spans,
                    }
                )
                break

    except WebSocketDisconnect:
        pass
    finally:
        if live is not None:
            await live.abort()


def turn_state_for_retry(first_turn: bool) -> str:
    """Lượt đầu thì quay lại trạng thái đang giảng; các lượt sau là đang trả lời
    câu hỏi ngược — hai trạng thái này có ngưỡng chờ im lặng khác nhau."""
    return (
        TurnState.STUDENT_TEACHING.name if first_turn else TurnState.STUDENT_RESPONDING.name
    )


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

