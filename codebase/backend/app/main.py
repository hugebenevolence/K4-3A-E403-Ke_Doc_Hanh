"""FastAPI entrypoint — cũng là composition root: chỗ duy nhất biết provider nào đang chạy.

Chạy: uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import json
import logging
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from langgraph.checkpoint.memory import InMemorySaver

from app.adapters.knowledge.local import load_lesson
from app.adapters.knowledge.pdf import Deck, load_deck
from app.adapters.knowledge.selection import lesson_from_selection
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
from app.graph.nodes import GRADER_VERSION, PERSONA_VERSION, open_session
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

def _build_deps(selection: list[str] | None = None) -> tuple[
    Lesson, SpanStore, LLMClient, SpeechToText, TextToSpeech, SessionLog, ProfileStore
]:
    # Gọi mỗi lần mở kết nối. Với mock thì không sao, nhưng khi viết adapter
    # thật thì HTTP client phải là singleton ở tầng module — tạo client mới cho
    # mỗi phiên sẽ mở thừa connection pool và sớm muộn cạn socket.
    session_log = JsonlSessionLog(settings.session_log_file)
    profiles = JsonProfileStore(settings.profile_file)

    lesson, spans = _lesson(selection)
    if settings.use_mocks:
        return lesson, spans, MockLLM(), MockSTT(), MockTTS(), session_log, profiles

    llm, tts = _shared_providers()
    return lesson, spans, llm, _speech_to_text(lesson), tts, session_log, profiles


def _lesson(selection: list[str] | None):
    """Bài học của phiên này.

    Học viên đã kéo chọn vùng trên slide thì dựng bài từ đúng vùng đó. Chưa
    chọn gì (hoặc không có slide, như khi chạy test) thì rơi về file bài học —
    đường đó giữ nguyên để repo vẫn chạy được ngay khi mới clone.
    """
    deck = _current_deck()
    if selection and deck is not None:
        return lesson_from_selection(deck, selection)
    return load_lesson(_lesson_file())


def _current_deck() -> Deck | None:
    path = settings.slides_pdf
    if not path or not path.is_file():
        return None
    return _deck(str(path), path.stat().st_mtime)


@lru_cache(maxsize=4)
def _deck(path: str, mtime: float) -> Deck:
    # Đọc cả bộ slide mất vài giây; cache theo thời điểm sửa file để thay slide
    # là tự đọc lại, không phải khởi động lại server.
    return load_deck(Path(path))


def _lesson_file():
    """File bài học đang chạy, theo LESSON_MODE ("slide" hay "code").

    LESSON_MODE quyết định TRƯỚC: có knowledge/lesson.json (bài slide thật) mà
    đang để mode=code thì vẫn phải ra bài code, nếu không đổi mode xong chẳng
    thấy gì thay đổi và rất khó hiểu tại sao.

    Hai chế độ dùng CHUNG toàn bộ backend — chỉ khác file bài và prompt chấm.
    Đó là điểm của việc Span mang được cả toạ độ trang lẫn khoảng dòng."""
    if settings.lesson_mode == "code":
        if not settings.enable_code_mode:
            log.warning("LESSON_MODE=code nhưng chế độ code đang tạm ẩn — dùng bài slide")
        else:
            return settings.demo_code_lesson_file
    # Bài slide thật nếu đã nạp, không thì bài demo.
    return (
        settings.lesson_file if settings.lesson_file.is_file() else settings.demo_lesson_file
    )


def _speech_to_text(lesson: Lesson) -> SpeechToText:
    """STT tạo theo từng bài vì nó mang từ điển thuật ngữ của chính bài đó.

    Không tốn gì: object chỉ giữ key + danh sách từ, kết nối chỉ mở khi có
    người nói. Khác với LLM/TTS — hai cái đó giữ connection pool nên phải dùng
    chung cả tiến trình.
    """
    if not settings.speechmatics_api_key:
        log.warning("Chưa có SPEECHMATICS_API_KEY — đường nói dùng mock, hãy gõ chữ để thử")
        return MockSTT()

    from app.adapters.stt.speechmatics import SpeechmaticsRealtimeSTT

    return SpeechmaticsRealtimeSTT(vocabulary=lesson.vocabulary)


@lru_cache(maxsize=1)
def _shared_providers() -> tuple[LLMClient, TextToSpeech]:
    """Dùng chung cho cả tiến trình: mỗi lần tạo mới là một connection pool mới,
    mở theo từng phiên sẽ sớm cạn socket."""
    from app.adapters.llm.openai import OpenAILLM
    from app.adapters.tts.openai import OpenAITTS

    return OpenAILLM(), OpenAITTS()


@app.get("/lesson")
async def lesson_info():
    """Frontend hỏi bài học đang chạy để hiện lên màn hình, thay vì chép cứng."""
    lesson, store, *_ = _build_deps()
    spans = await store.get_many(lesson.source_span_ids)
    return {
        "concept": lesson.concept,
        "kind": lesson.kind,
        "code": lesson.code,
        "language": lesson.language,
        "has_slides": lesson.kind == "slide"
        and bool(settings.slides_pdf and settings.slides_pdf.is_file()),
        # bbox theo hệ PyMuPDF (gốc trên-trái). Frontend phải đổi sang hệ của
        # PDF.js trước khi vẽ — xem ghi chú trong js/slides.js.
        "spans": [
            {
                "span_id": s.span_id,
                "page": s.page,
                "bbox": list(s.bbox) if s.bbox else None,
                "lines": list(s.lines) if s.lines else None,
                # Nội dung thật để client hiện lại nguyên văn khi đối chiếu —
                # học viên thấy được agent đang dựa vào đúng chữ nào trên slide.
                "text": s.text,
            }
            for s in spans
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "mocks": settings.use_mocks}


@app.get("/slides.pdf")
async def slides():
    """Phục vụ chính file slide của bài đang học, để frontend render bằng PDF.js.

    Học viên nhìn slide và dạy lại ngay tại đó — đúng bối cảnh dùng thật trên
    VLearn, thay vì một khung chat rời rạc không biết đang nói về cái gì.
    """
    path = settings.slides_pdf
    if not path or not path.is_file():
        raise HTTPException(404, "Chưa cấu hình SLIDES_PDF trong .env")
    return FileResponse(path, media_type="application/pdf")


def _require_deck() -> Deck:
    deck = _current_deck()
    if deck is None:
        raise HTTPException(404, "Chưa cấu hình SLIDES_PDF trong .env")
    return deck


@app.get("/slides/outline")
async def slides_outline():
    """Tiêu đề từng trang slide cho thanh bên."""
    deck = _require_deck()
    return [{"page": n, "title": deck.titles.get(n, "")} for n in range(1, deck.pages + 1)]


@app.get("/slides/blocks")
async def slides_blocks():
    """Mọi ô nội dung của bộ slide kèm toạ độ, để học viên kéo khung chọn.

    Frontend tự tính ô nào nằm trong khung để hiện ngay khi đang kéo, không phải
    hỏi server mỗi lần rê chuột. Server vẫn kiểm lại mã ô lúc bắt đầu phiên.
    """
    deck = _require_deck()
    return [
        {"span_id": s.span_id, "page": s.page, "bbox": list(s.bbox), "text": s.text}
        for s in deck.spans
        if s.bbox
    ]


@app.websocket("/ws/session")
async def teach_back_session(ws: WebSocket):
    """Một phiên = một học viên dạy lại một khái niệm.

    Audio đi bằng binary frame, điều khiển đi bằng JSON frame.
    Client chỉ được mở mic khi state cho phép VÀ audio agent đã phát xong —
    nếu không mic sẽ bắt lại chính giọng agent qua loa.
    """
    await ws.accept()
    # Vùng học viên đã chọn trên slide, gửi kèm lúc mở kết nối.
    selection = [sid for sid in (ws.query_params.get("spans") or "").split(",") if sid]
    try:
        lesson, spans, llm, stt, tts, session_log, profiles = _build_deps(selection)
    except ValueError:
        await ws.send_json(
            {"type": "error", "message": "Vùng đã chọn không còn khớp với slide — bạn chọn lại nhé."}
        )
        await ws.close()
        return
    graph = build_graph(llm, spans, checkpointer=InMemorySaver())

    session_id = str(uuid.uuid4())
    # Hồ sơ theo học viên chứ không theo phiên — đó là điểm của trí nhớ xuyên
    # buổi. Không có student_id thì mọi người dùng chung một hồ sơ và nó vô nghĩa.
    student_id = ws.query_params.get("student_id", "demo")
    profile = await profiles.load(student_id)

    live: LiveTurn | None = None
    live_code = lesson.code
    first_turn = True
    turn_index = 0
    review_spans: list[str] = []

    async def partial_to_client(text: str) -> None:
        """Chữ chạy lên màn hình khi học viên còn đang nói — không có cái này
        thì họ nói vào khoảng không, không biết mic có ăn hay không."""
        await ws.send_json({"type": "partial", "text": text})

    async def send_state(state: str, **extra) -> None:
        """Gửi state kèm luật mic của chính state đó.

        Ngưỡng im lặng là quyết định sư phạm chứ không phải hằng số giao diện:
        im lặng sau một câu hỏi ngược nghĩa là học viên đang nghĩ, im lặng giữa
        lúc đang giảng nghĩa là hết lượt. Luật ở domain/session.py, frontend
        chỉ thi hành.

        Trước đây frontend không hề biết tới luật này — nó chỉ nhận mỗi tên
        state — nên hai thuộc tính kia là code chết, và học viên vừa bị hỏi
        xong, ngập ngừng vài giây là bị cắt lời.
        """
        turn = TurnState[state]
        await ws.send_json(
            {
                "type": "state",
                "state": state,
                "mic_open": turn.mic_open,
                "silence_ms": turn.silence_tolerance_ms,
                **extra,
            }
        )

    # Mở bài bằng một câu hỏi cụ thể thay vì để học viên nhìn ô trống tự nghĩ
    # xem nên nói gì. Hỏng thì vẫn vào phiên được — mất câu mở bài còn hơn mất
    # cả phiên vì một lượt gọi LLM trục trặc.
    try:
        opening = await open_session(
            llm, spans, list(lesson.source_span_ids), profile.recurring_gaps,
            lesson.concept, lesson.code,
        )
        await ws.send_json(
            {"type": "transcript", "role": "agent", "text": opening, "filler": False}
        )
        for chunk in [c async for c in tts.synthesize(opening)]:
            await ws.send_bytes(chunk)
    except Exception:
        log.exception("Mở bài hỏng ở phiên %s", session_id)

    await send_state(TurnState.STUDENT_TEACHING.name)

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
            # Học viên sửa code thì lượt chấm sau phải theo bản họ đang nhìn,
            # không phải bản gốc — nếu không agent nhận xét về code đã cũ.
            if (edited := command.get("code")) is not None:
                live_code = str(edited)

            if command.get("type") == "explanation_text":
                if live is not None:
                    await live.abort()
                    live = None
                await send_state(TurnState.CHECKING.name)
                student_text = str(command.get("text", ""))
            elif command.get("type") == "explanation_done":
                await send_state(TurnState.CHECKING.name)
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
                        await send_state(turn_state_for_retry(first_turn))
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
                await send_state(turn_state_for_retry(first_turn))
                continue

            await ws.send_json(
                {"type": "transcript", "role": "student", "text": student_text}
            )

            # Chỉ lượt đầu mới gửi thông tin phiên. Các lượt sau chỉ gửi lời học
            # viên, phần còn lại (followups_asked, asked_questions) do
            # checkpointer giữ. Gửi lại followups_asked từ đây là tạo ra hai
            # nguồn sự thật cho cùng một con số, sớm muộn cũng lệch nhau.
            turn_input: dict = {"student_text": student_text}
            if lesson.kind == "code":
                turn_input["code"] = live_code
            if first_turn:
                turn_input |= {
                    "session_id": session_id,
                    "student_id": student_id,
                    "concept": lesson.concept,
                    "source_span_ids": list(lesson.source_span_ids),
                    "followups_asked": 0,
                    "recurring_gaps": dict(profile.recurring_gaps),
                    "code": live_code,
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
                        await send_state(
                            turn_state,
                            verdict=event.payload.get("verdict"),
                            evidence=event.payload.get("evidence") or [],
                        )
                    elif event.kind == "activity":
                        await ws.send_json({"type": "activity", **event.payload})
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
                await send_state(turn_state)

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

