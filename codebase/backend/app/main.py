"""FastAPI entrypoint — cũng là composition root: chỗ duy nhất biết provider nào đang chạy.

Chạy: uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from pydantic import BaseModel

from app.adapters.knowledge.local import load_lesson
from app.adapters.knowledge.pdf import Deck, attach_descriptions, deck_slug, load_deck
from app.adapters.knowledge.selection import lesson_from_selection
from app.adapters.llm.mock import MockLLM
from app.adapters.store.jsonl import JsonlSessionLog, JsonProfileStore
from app.adapters.stt.mock import MockSTT
from app.adapters.tts.mock import MockTTS
from app.api.auth import (
    check_password,
    issue_token,
    make_secret,
    parse_members,
    verify_token,
)
from app.api.live_turn import LiveTurn
from app.api.pronunciations import PronunciationCache
from app.api.session import TALKER_VERSION, run_turn
from app.config import settings
from app.domain.lesson import Lesson
from app.domain.log import TurnLog
from app.domain.sanitize import sanitize_spoken, tame_shouting
from app.domain.session import TurnState
from app.domain.verdict import Evidence, GradeResult, Verdict
from app.graph.build import build_graph
from app.graph.nodes import (
    GRADER_CODE_VERSION,
    GRADER_VERSION,
    PERSONA_VERSION,
    open_session,
)
from app.ports.knowledge import SpanStore
from app.ports.llm import LLMClient, LLMUnavailable
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
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

def _build_deps(selection: list[str] | None = None, deck: str | None = None) -> tuple[
    Lesson, SpanStore, LLMClient, SpeechToText, TextToSpeech, SessionLog, ProfileStore
]:
    # Gọi mỗi lần mở kết nối. Với mock thì không sao, nhưng khi viết adapter
    # thật thì HTTP client phải là singleton ở tầng module — tạo client mới cho
    # mỗi phiên sẽ mở thừa connection pool và sớm muộn cạn socket.
    session_log = JsonlSessionLog(settings.session_log_file)
    profiles = JsonProfileStore(settings.profile_file)

    lesson, spans = _lesson(selection, deck)
    if settings.use_mocks:
        return lesson, spans, MockLLM(), MockSTT(), MockTTS(), session_log, profiles

    llm, tts = _shared_providers()
    return lesson, spans, llm, _speech_to_text(lesson), tts, session_log, profiles


def _lesson(selection: list[str] | None, deck: str | None = None):
    """Bài học của phiên này.

    Học viên đã kéo chọn vùng trên slide thì dựng bài từ đúng vùng đó. Chưa
    chọn gì (hoặc không có slide, như khi chạy test) thì rơi về file bài học —
    đường đó giữ nguyên để repo vẫn chạy được ngay khi mới clone.
    """
    found = _find_deck(deck)
    if selection and found is not None:
        return lesson_from_selection(found, selection)
    return load_lesson(_lesson_file())


def _deck_paths() -> dict[str, Path]:
    """Mọi bộ slide đang cấu hình, theo mã bộ."""
    paths: list[Path] = []
    if settings.slides_dir and settings.slides_dir.is_dir():
        paths += sorted(settings.slides_dir.glob("*.pdf"))
    if settings.slides_pdf and settings.slides_pdf.is_file():
        paths.append(settings.slides_pdf)
    return {deck_slug(path): path for path in paths}


def _find_deck(slug: str | None) -> Deck | None:
    """Bộ slide theo mã; không nói mã mà chỉ có đúng một bộ thì lấy bộ đó."""
    paths = _deck_paths()
    if slug is None and len(paths) == 1:
        slug = next(iter(paths))
    path = paths.get(slug or "")
    return _deck(str(path), path.stat().st_mtime) if path else None


@lru_cache(maxsize=8)
def _deck(path: str, mtime: float) -> Deck:
    # Đọc cả bộ slide mất vài giây; cache theo thời điểm sửa file để thay slide
    # là tự đọc lại, không phải khởi động lại server.
    try:
        descriptions = json.loads(settings.figures_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        descriptions = {}
    return attach_descriptions(load_deck(Path(path)), descriptions)


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

    sounds_like = _pronunciations().table if settings.enable_generated_pronunciations else None
    return SpeechmaticsRealtimeSTT(vocabulary=lesson.vocabulary, sounds_like=sounds_like)


@lru_cache(maxsize=1)
def _pronunciations() -> PronunciationCache:
    return PronunciationCache(settings.pronunciation_file)


_BACKGROUND: set[asyncio.Task] = set()

PRONUNCIATION_TERMS = 60
"""Chỉ sinh cách đọc cho đầu danh sách — tức thuật ngữ của vùng đang giảng, vì
từ điển phiên đã xếp chúng lên trước."""


@lru_cache(maxsize=1)
def _graph_store() -> InMemoryStore:
    """Store xuyên phiên của LangGraph — MỘT bản cho cả tiến trình.

    Checkpointer giữ mạch trong một buổi; store là thứ sống qua nhiều buổi, nên
    nó KHÔNG được tạo theo từng kết nối — tạo theo phiên thì nó chỉ là một
    checkpointer thứ hai, rỗng lại từ đầu mỗi lần ai đó bấm "Bắt đầu giảng".

    Nói thẳng hiện trạng: hôm nay chưa node nào đọc từ store. Trí nhớ xuyên buổi
    đang đi qua `JsonProfileStore` (ghi ra file, đọc lại lúc mở phiên, bơm vào
    state ở lượt đầu). Store được lắp sẵn vì `compile()` chỉ nhận nó ở đây —
    node nào cần nhớ xuyên buổi về sau là có sẵn đường, không phải sửa lại
    composition root và mọi chỗ gọi.
    """
    return InMemoryStore()


@lru_cache(maxsize=1)
def _shared_providers() -> tuple[LLMClient, TextToSpeech]:
    """Dùng chung cho cả tiến trình: mỗi lần tạo mới là một connection pool mới,
    mở theo từng phiên sẽ sớm cạn socket."""
    from app.adapters.llm.openai import OpenAILLM
    from app.adapters.tts.openai import OpenAITTS

    return OpenAILLM(), OpenAITTS()


api = APIRouter(prefix="/api")


@lru_cache(maxsize=1)
def _auth_secret() -> str:
    return settings.auth_secret or make_secret()


def _members() -> dict[str, str]:
    return parse_members(settings.members)


def require_member(authorization: str | None = Header(default=None)) -> str:
    """Tên thành viên đang gọi. Không cấu hình MEMBERS thì bỏ qua đăng nhập."""
    if not _members():
        return "demo"
    token = (authorization or "").removeprefix("Bearer ").strip()
    name = verify_token(token, _auth_secret()) if token else None
    if name is None or name not in _members():
        raise HTTPException(401, "Cần đăng nhập")
    return name


class LoginBody(BaseModel):
    username: str
    password: str


@api.post("/auth/login")
async def login(body: LoginBody):
    members = _members()
    if not members:
        return {"token": "", "name": "demo", "auth": False}
    name = body.username.strip()
    if not check_password(members, name, body.password):
        raise HTTPException(401, "Sai tên đăng nhập hoặc mật khẩu")
    return {"token": issue_token(name, _auth_secret()), "name": name, "auth": True}


@api.get("/me")
async def me(member: str = Depends(require_member)):
    return {"name": member, "auth": bool(_members())}


@api.get("/health")
async def health():
    return {"status": "ok", "mocks": settings.use_mocks}


@api.get("/lesson")
async def lesson_info(member: str = Depends(require_member)):
    """Bài học mặc định (khi chưa chọn vùng) — giữ cho đường chạy không có slide."""
    lesson, store, *_ = _build_deps()
    spans = await store.get_many(lesson.source_span_ids)
    return {
        "concept": lesson.concept,
        "kind": lesson.kind,
        "has_slides": bool(_deck_paths()),
        "spans": [
            {"span_id": s.span_id, "page": s.page, "bbox": list(s.bbox) if s.bbox else None, "text": s.text}
            for s in spans
        ],
    }


def _deck_or_404(slug: str) -> Deck:
    deck = _find_deck(slug)
    if deck is None:
        raise HTTPException(404, f"Không có bộ slide {slug}")
    return deck


@api.get("/decks")
async def decks(member: str = Depends(require_member)):
    """Thư viện: các bộ slide chọn được để học."""
    try:
        names = json.loads(settings.decks_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        names = {}
    out = []
    for slug in _deck_paths():
        deck = _deck_or_404(slug)
        meta = names.get(slug, {})
        out.append(
            {
                "slug": slug,
                "title": meta.get("title") or deck.titles.get(1) or slug,
                "subtitle": meta.get("subtitle", ""),
                "pages": deck.pages,
                "figures": sum(1 for s in deck.spans if s.kind == "figure"),
            }
        )
    return out


@api.get("/decks/{slug}/pdf")
async def deck_pdf(slug: str, member: str = Depends(require_member)):
    path = _deck_paths().get(slug)
    if not path:
        raise HTTPException(404, f"Không có bộ slide {slug}")
    return FileResponse(path, media_type="application/pdf")


@api.get("/decks/{slug}/outline")
async def deck_outline(slug: str, member: str = Depends(require_member)):
    """Tiêu đề từng trang slide cho thanh bên."""
    deck = _deck_or_404(slug)
    return [{"page": n, "title": deck.titles.get(n, "")} for n in range(1, deck.pages + 1)]


@api.get("/decks/{slug}/blocks")
async def deck_blocks(slug: str, member: str = Depends(require_member)):
    """Mọi ô nội dung của bộ slide kèm toạ độ, để học viên kéo khung chọn.

    Frontend tự tính ô nào nằm trong khung để hiện ngay khi đang kéo, không phải
    hỏi server mỗi lần rê chuột. Server vẫn kiểm lại mã ô lúc bắt đầu phiên.
    """
    deck = _deck_or_404(slug)
    return [
        {"span_id": s.span_id, "page": s.page, "bbox": list(s.bbox), "text": s.text, "kind": s.kind}
        for s in deck.spans
        if s.bbox
    ]


@api.websocket("/ws/session")
async def teach_back_session(ws: WebSocket):
    """Một phiên = một học viên dạy lại một khái niệm.

    Audio đi bằng binary frame, điều khiển đi bằng JSON frame.
    Client chỉ được mở mic khi state cho phép VÀ audio agent đã phát xong —
    nếu không mic sẽ bắt lại chính giọng agent qua loa.
    """
    await ws.accept()
    # Trình duyệt không gắn được header vào WebSocket, nên token đi qua query.
    member: str | None = "demo"
    if _members():
        member = verify_token(ws.query_params.get("token") or "", _auth_secret())
        if member not in _members():
            await ws.send_json(
                {"type": "error", "message": "Phiên đăng nhập đã hết hạn — bạn đăng nhập lại nhé."}
            )
            await ws.close(code=4401)
            return
    # Vùng học viên đã chọn trên slide, gửi kèm lúc mở kết nối.
    selection = [sid for sid in (ws.query_params.get("spans") or "").split(",") if sid]
    try:
        lesson, spans, llm, stt, tts, session_log, profiles = _build_deps(
            selection, ws.query_params.get("deck")
        )
    except ValueError as exc:
        # Nói đúng chuyện gì đã xảy ra: "chọn lại đi" mà không nói vì sao thì
        # học viên chọn lại y chỗ cũ. Hai lý do hiện có — vùng không còn khớp
        # slide, và vùng chỉ có tiêu đề — cần hai hành động khác nhau.
        await ws.send_json(
            {
                "type": "error",
                "message": str(exc) or "Vùng đã chọn không còn khớp với slide — bạn chọn lại nhé.",
            }
        )
        await ws.close()
        return
    # Checkpointer theo từng kết nối (mạch của đúng buổi này), store dùng chung
    # cả tiến trình (thứ sống qua nhiều buổi). Truyền thiếu một trong hai là lỗi
    # kiến trúc hay gặp nhất với LangGraph — xem graph/build.py.
    graph = build_graph(llm, spans, checkpointer=InMemorySaver(), store=_graph_store())

    # Sinh cách đọc kiểu Việt cho thuật ngữ của vùng đang giảng, chạy NỀN song
    # song với câu mở bài: học viên còn phải nghe câu hỏi xong mới nói, đủ thời
    # gian để bảng kịp đầy trước lượt nói đầu tiên. Không chờ, không làm chậm gì.
    if not settings.use_mocks and settings.enable_generated_pronunciations:
        task = asyncio.create_task(
            _pronunciations().ensure(lesson.vocabulary[:PRONUNCIATION_TERMS], llm)
        )
        # Giữ tham chiếu tới khi xong: asyncio chỉ giữ tham chiếu yếu tới task,
        # không giữ thì task có thể bị dọn giữa chừng. Để nó chạy nốt cả khi
        # học viên đã rời phiên — kết quả được lưu lại cho lần sau.
        _BACKGROUND.add(task)
        task.add_done_callback(_BACKGROUND.discard)

    session_id = str(uuid.uuid4())
    # Hồ sơ theo học viên chứ không theo phiên — đó là điểm của trí nhớ xuyên
    # buổi. Không có student_id thì mọi người dùng chung một hồ sơ và nó vô nghĩa.
    # Đã đăng nhập thì hồ sơ theo tên thành viên — mỗi người một trí nhớ riêng,
    # dù học trên máy nào.
    student_id = member if _members() else ws.query_params.get("student_id", "demo")
    profile = await profiles.load(student_id)

    live: LiveTurn | None = None
    last_grade: GradeResult | None = None
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
    opening = ""
    try:
        opening = await open_session(
            llm, spans, list(lesson.source_span_ids), profile.recurring_gaps,
            lesson.concept, lesson.code,
        )
        # Câu mở bài không đi qua run_turn nên phải tự lọc; đo được thật: lọt
        # "REWARD MODEL" viết hoa y như slide.
        opening = tame_shouting(sanitize_spoken(opening))
        await ws.send_json(
            {"type": "transcript", "role": "agent", "text": opening, "filler": False}
        )
        for chunk in [c async for c in tts.synthesize(opening)]:
            await ws.send_bytes(chunk)
    except LLMUnavailable:
        # Provider chết ngay từ câu mở bài: không có câu hỏi mở, và nếu im lặng
        # thì học viên ngồi trước một ô trống đúng cái cảnh mà câu mở bài sinh
        # ra để tránh. Nói thật ngay, đừng để họ nói xong một lượt rồi mới biết.
        log.exception("Provider không dùng được lúc mở bài ở phiên %s", session_id)
        await ws.send_json(
            {
                "type": "error",
                "message": (
                    "Mình chưa gọi được dịch vụ AI nên chưa mở bài được — lỗi phía "
                    "hệ thống. Bạn chờ một chút rồi tải lại trang nhé."
                ),
            }
        )
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
                    "vocabulary": list(lesson.vocabulary),
                    "followups_asked": 0,
                    "recurring_gaps": dict(profile.recurring_gaps),
                    "code": live_code,
                    # Câu mở bài sinh ngoài graph nên graph không tự biết nó.
                    # Không đưa vào thì lượt đầu bị chấm như một lời giảng tự
                    # phát, trong khi nó là câu TRẢ LỜI cho một câu hỏi hẹp —
                    # và câu hỏi ngược đầu tiên có thể hỏi lại y hệt câu mở bài.
                    "asked_questions": [opening] if opening else [],
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
                        # Hồ sơ ghi MỘT LẦN mỗi buổi, ở lượt kết — không phải
                        # mỗi lượt. `recurring_gaps` đếm "bao nhiêu BUỔI đã vấp
                        # chỗ này"; cộng theo lượt thì một buổi bốn lượt thành
                        # bốn lần vấp, và học trò nói "buổi trước bạn cũng chưa
                        # thông chỗ này" ngay trong buổi ĐẦU TIÊN của người ta.
                        # Đo được trên hồ sơ thật: [d1-slide-hackathon-p1-01]
                        # đếm 3 sau đúng một buổi.
                        last_grade = await _log_turn(
                            session_log, session_id, turn_index, student_text, event
                        )
                        review_spans = event.payload["result"].get("review_span_ids", [])
                        turn_index += 1
                    else:
                        await ws.send_json({"type": "transcript", **event.payload})
            except WebSocketDisconnect:
                raise
            except LLMUnavailable:
                # Hết hạn mức / sai key / provider quá tải. KHÔNG được nói "mình
                # nghe chưa rõ" — lời giảng của họ không có lỗi gì, và họ sẽ nói
                # lại mãi trong khi vấn đề nằm ở phía mình. Gặp thật 17/9: API
                # trả 429 credit_balance_exhausted giữa lúc đang đo golden set.
                log.exception("Provider không dùng được ở phiên %s", session_id)
                await ws.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Mình chưa gọi được dịch vụ AI — lỗi phía hệ thống, "
                            "không phải do bạn nói. Bạn chờ một chút rồi thử lại nhé."
                        ),
                    }
                )
                # KHÔNG dùng `first_turn`: nó đã bị lật thành False ngay lúc
                # dựng turn_input, trước khối try này. Lượt đầu mà hỏng thì học
                # viên vẫn đang giảng dở, không phải đang trả lời câu hỏi ngược —
                # hai trạng thái đó có ngưỡng chờ im lặng khác nhau (6s so với
                # 2s), và CLAUDE.md gọi đây là chỗ chịu lực.
                turn_state = turn_state_for_retry(turn_index == 0)
                await send_state(turn_state)
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
                # Buổi đã đóng: giờ mới cộng vào hồ sơ, theo kết quả lượt cuối.
                # Bỏ dở giữa chừng thì không ghi gì — chưa học xong thì chưa có
                # gì để nhớ, và đó cũng là cách duy nhất để "số buổi" đúng nghĩa.
                if last_grade is not None:
                    profile.absorb(lesson.concept, last_grade)
                    await profiles.save(profile)
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
                # Bài code chạy bộ chấm khác; ghi cứng GRADER_VERSION là log trỏ
                # về một prompt chưa từng chạy, và lượt đó replay lại sẽ ra kết
                # quả không so được với thứ đã thật sự xảy ra.
                "grader": GRADER_CODE_VERSION if result.get("code") else GRADER_VERSION,
                "student_persona": PERSONA_VERSION,
                "talker": TALKER_VERSION,
            },
            grade=grade,
            agent_said=event.payload["said"],
            latency_ms=event.payload["latency_ms"],
        )
    )
    return grade



def mount_frontend(target_app: FastAPI, dist: Path) -> None:
    """Phục vụ giao diện đã build ngay từ backend: deploy một service là đủ.

    Đường dẫn nào không phải file có thật thì trả index.html — để tải lại trang
    ở /learn/... hay /login vẫn vào đúng trang thay vì báo 404.
    """
    index = dist / "index.html"
    if not index.is_file():
        return
    root = dist.resolve()
    # Windows không đăng ký đuôi .mjs, FileResponse đoán ra text/plain, và trình
    # duyệt từ chối chạy worker của PDF.js — slide vẫn hiện nhưng vẽ chậm hẳn.
    mimetypes.add_type("text/javascript", ".mjs")

    @target_app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        target = (dist / path).resolve()
        # Chặn "../" thoát ra ngoài thư mục build.
        if path and target.is_file() and root in target.parents:
            return FileResponse(target)
        return FileResponse(index)


app.include_router(api)
mount_frontend(app, settings.frontend_dist)
