"""FastAPI entrypoint — cũng là composition root: chỗ duy nhất biết provider nào đang chạy.

Chạy: uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
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
from starlette.websockets import WebSocketState

from app.adapters.knowledge.local import InMemorySpanStore, load_lesson
from app.adapters.knowledge.pdf import Deck, attach_descriptions, deck_slug, load_deck
from app.adapters.knowledge.selection import lesson_from_selection
from app.adapters.llm.mock import MockLLM
from app.adapters.store.jsonl import (
    JsonGraphStore,
    JsonlSessionLog,
    JsonProfileStore,
    JsonProgressStore,
)
from app.adapters.stt.mock import MockSTT
from app.adapters.tts.mock import MockTTS
from app.api.auth import (
    check_password,
    issue_token,
    make_secret,
    parse_members,
    verify_token,
)
from app.api.graph_sync import absorb_link, absorb_turn, known_claims
from app.api.live_turn import LiveTurn
from app.api.pronunciations import PronunciationCache
from app.api.session import TALKER_VERSION, run_turn
from app.config import settings
from app.domain.graph import (
    LINK_LABEL,
    KnowledgeGraph,
    PageRef,
    page_key,
    short_label,
    split_key,
)
from app.domain.lesson import Lesson
from app.domain.log import TurnLog
from app.domain.progress import LEVELS
from app.domain.sanitize import speakable
from app.domain.session import TurnState
from app.domain.substance import MIN_SOURCE_WORDS, teachable_words
from app.domain.terms import session_vocabulary
from app.domain.verdict import Evidence, GradeResult, Verdict
from app.graph.build import build_graph
from app.graph.nodes import (
    GRADER_CODE_VERSION,
    GRADER_LINK_VERSION,
    GRADER_VERSION,
    PERSONA_VERSION,
    open_link_session,
    open_session,
)
from app.ports.knowledge import SpanStore
from app.ports.llm import LLMClient, LLMUnavailable
from app.ports.store import GraphStore, ProfileStore, SessionLog
from app.ports.stt import SpeechToText
from app.ports.tts import TextToSpeech

# uvicorn chỉ cấu hình logger CỦA NÓ; logger của app rơi về root với mức
# WARNING, nên mọi dòng INFO ta cất công viết ra đều bị nuốt. Đặt ở đây
# một lần cho cả tiến trình.
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(levelname)s  %(name)s  %(message)s",
)

log = logging.getLogger(__name__)

@asynccontextmanager
async def _lifespan(_app: FastAPI):
    # Thread riêng để server nhận kết nối ngay. DAEMON: thread của executor mặc
    # định giữ tiến trình lại tới khi đọc xong 28 file PDF — đo được, bộ test
    # (mỗi TestClient khởi động app một lần) từ 6 giây thành 38 giây.
    threading.Thread(target=_warm_decks, name="warm-decks", daemon=True).start()
    yield


app = FastAPI(title="Ke Doc Hanh — Track D3 teach-back", lifespan=_lifespan)

# Frontend chạy ở cổng khác (http.server 5500) nên fetch /lesson là cross-origin.
# WebSocket không cần CORS nhưng fetch thì có. Chỉ mở cho localhost — đây là
# prototype chạy máy cá nhân, không deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

def _build_deps(
    selection: list[str] | None = None,
    deck: str | None = None,
    link: tuple[str, str] | None = None,
) -> tuple[
    Lesson, SpanStore, LLMClient, SpeechToText, TextToSpeech, SessionLog, ProfileStore, GraphStore
]:
    # Gọi mỗi lần mở kết nối. Với mock thì không sao, nhưng khi viết adapter
    # thật thì HTTP client phải là singleton ở tầng module — tạo client mới cho
    # mỗi phiên sẽ mở thừa connection pool và sớm muộn cạn socket.
    session_log = JsonlSessionLog(settings.session_log_file)
    profiles = JsonProfileStore(settings.profile_file)
    graphs = JsonGraphStore(settings.graph_file)

    lesson, spans = _link_lesson(*link) if link else _lesson(selection, deck)
    if settings.use_mocks:
        return lesson, spans, MockLLM(), MockSTT(), MockTTS(), session_log, profiles, graphs

    llm, tts = _shared_providers()
    return lesson, spans, llm, _speech_to_text(lesson), tts, session_log, profiles, graphs


def _page_ref(deck: str | None, lesson: Lesson) -> PageRef | None:
    """Trang slide mà phiên này đang giảng — đỉnh của đồ thị neo vào đây.

    Rỗng khi phiên không dựng từ một trang slide (bài demo, bài code): lúc đó
    không có trang nào để sáng lên.
    """
    found = _find_deck(deck)
    if found is None or lesson.kind != "slide":
        return None
    ids = set(lesson.source_span_ids)
    page = next((s.page for s in found.spans if s.span_id in ids and s.page), None)
    if page is None:
        return None
    slug = deck if deck in _deck_paths() else next(iter(_deck_paths()), "")
    return _page_by_key(page_key(slug, page))


def _page_by_key(key: str) -> PageRef | None:
    """Trang slide theo khoá của đồ thị ("d1-slide-hackathon:14"), ở BẤT KỲ bộ nào."""
    slug, page = split_key(key)
    found = _find_deck(slug) if slug in _deck_paths() else None
    on_page = [s for s in found.spans if s.page == page] if found else []
    if not on_page:
        return None
    return PageRef(
        key=page_key(slug, page),
        title=found.titles.get(page) or f"Trang {page}",
        deck=slug,
        page=page,
        span_ids=tuple(s.span_id for s in on_page),
        text="\n".join(s.text for s in on_page),
    )


def _link_lesson(a_key: str, b_key: str) -> tuple[Lesson, SpanStore]:
    """Bài của phiên NỐI HAI TRANG: nguồn là ô của cả hai trang.

    Hai trang có thể thuộc hai bộ slide khác nhau — đó chính là chỗ đáng nối
    nhất — nên kho ô gom cả hai bộ, không chỉ bộ của trang đầu.
    """
    a, b = _page_by_key(a_key), _page_by_key(b_key)
    if a is None or b is None or a.key == b.key:
        raise ValueError("Không mở được phiên nối — bạn chọn lại hai trang trên bản đồ nhé.")
    decks = {p.deck: _find_deck(p.deck) for p in (a, b)}
    ids = (*a.span_ids, *b.span_ids)
    lesson = Lesson(
        concept=f"mối nối giữa «{short_label(a.title)}» và «{short_label(b.title)}»",
        source_span_ids=ids,
        vocabulary=session_vocabulary(
            [a.text, b.text], [t for d in decks.values() for t in d.terms]
        ),
        kind="slide",
    )
    return lesson, InMemorySpanStore([s for d in decks.values() for s in d.spans])


def _taught(knowledge: KnowledgeGraph, page: PageRef) -> list[str]:
    """Những câu học viên đã nói về một trang — nguyên liệu cho câu mở phiên nối."""
    claim = knowledge.claims[page.key]
    return list(claim.sentences) or [claim.said]


def _lesson(selection: list[str] | None, deck: str | None = None):
    """Bài học của phiên này.

    Học viên đã kéo chọn vùng trên slide thì dựng bài từ đúng vùng đó. Chưa
    chọn gì (hoặc không có slide, như khi chạy test) thì rơi về file bài học —
    đường đó giữ nguyên để repo vẫn chạy được ngay khi mới clone.
    """
    found = _find_deck(deck)
    if selection and found is not None:
        return lesson_from_selection(found, selection)
    # Có vùng chọn mà không tìm thấy bộ slide của nó thì phải BÁO, không được
    # rơi về file bài học: đo được 18/9, link mang mã bộ slide cũ mở phiên
    # bình thường rồi chấm học viên theo trang 20 của bài mặc định — họ giảng
    # slide này, bị hỏi về slide khác, và không có dấu hiệu gì là đã lệch.
    if selection and _deck_paths():
        raise ValueError("Không tìm thấy bộ slide này nữa — bạn mở lại bài từ thư viện nhé.")
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
    return _deck(str(path), path.stat().st_mtime, _figures_mtime()) if path else None


def _figures_mtime() -> float:
    """Thời điểm sửa file mô tả hình, để nó cũng nằm trong khoá cache bộ slide.

    Mô tả hình sinh dần ở tiến trình khác (scripts/describe_figures.py) và một
    lượt chạy cả thư viện mất hàng giờ. Khoá cache chỉ theo mtime của PDF thì
    mô tả mới nằm im trong file cho tới lần khởi động lại sau — đúng lúc người
    ta đang thử thì trang có hình vẫn hỏi vu vơ như cũ.
    """
    try:
        return settings.figures_file.stat().st_mtime
    except OSError:
        return 0.0


DECK_CACHE = 64
"""Số bộ slide giữ trong bộ nhớ. Phải lớn hơn số bộ đang cấu hình: thư viện và
bản đồ duyệt QUA MỌI BỘ mỗi lần tải, nên cache nhỏ hơn số bộ là mỗi lần tải lại
đọc lại PDF từ đầu. Đo 18/9: 28 bộ, đọc hết mất ~40 giây — với cache 8 cũ thì
lần nào mở thư viện cũng chờ chừng đó."""


@lru_cache(maxsize=DECK_CACHE)
def _deck(path: str, mtime: float, figures_mtime: float = 0.0) -> Deck:
    # Đọc cả bộ slide mất vài giây; cache theo thời điểm sửa file để thay slide
    # HOẶC thêm mô tả hình là tự đọc lại, không phải khởi động lại server.
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


def _teachable_pages(slug: str) -> list[tuple[int, str]]:
    """Các trang của một bộ slide mà học viên CÓ THỂ giảng: (số trang, tiêu đề).

    Cùng luật với lúc mở phiên (`teachable_words`), cộng thêm bỏ tiêu đề lặp ở
    nhiều trang ("AI IN ACTION - Day 1" ở cả bìa lẫn trang sau là tên của bộ,
    không phải của trang). Bản đồ và tiến độ dùng CHUNG danh sách này, để "12/40
    trang đã hiểu" và vành tối trên bản đồ đếm cùng một mẫu số.
    """
    path = _deck_paths().get(slug)
    return list(_teachable_cached(str(path), path.stat().st_mtime)) if path else []


@lru_cache(maxsize=DECK_CACHE)
def _teachable_cached(path: str, mtime: float) -> tuple[tuple[int, str], ...]:
    deck = _deck(path, mtime)
    theo_trang: dict[int, list] = {}
    for s in deck.spans:
        if s.page:
            theo_trang.setdefault(s.page, []).append(s)
    tieu_de = list(deck.titles.values())
    lap = {t for t in tieu_de if tieu_de.count(t) > 1}
    return tuple(
        (page, deck.titles.get(page) or "")
        for page in sorted(theo_trang)
        if (deck.titles.get(page) or "") not in lap
        and teachable_words(theo_trang[page], deck.titles.get(page) or "") >= MIN_SOURCE_WORDS
    )


def _deck_or_404(slug: str) -> Deck:
    deck = _find_deck(slug)
    if deck is None:
        raise HTTPException(404, f"Không có bộ slide {slug}")
    return deck


@api.get("/graph")
async def knowledge_graph(
    student_id: str = "demo", deck: str = "", member: str = Depends(require_member)
):
    """Đồ thị tri thức của học viên đang đăng nhập (spec §4c).

    Đỉnh sáng = mệnh đề họ đã tự nói ra và bộ chấm xác nhận có căn cứ; cạnh =
    quan hệ chính họ nối; vùng tối = khái niệm của bài mà họ chưa giảng nổi.
    """
    who = member if _members() else student_id
    graph = await JsonGraphStore(settings.graph_file).load(who)

    claims = []
    for claim in graph.claims.values():
        deck, page = split_key(claim.concept)
        claims.append(
            {
                "concept": claim.concept,
                "title": claim.title,
                "label": short_label(claim.title),
                "said": claim.said,
                "sentences": list(claim.sentences),
                "times_taught": claim.times_taught,
                "deck": deck,
                "page": page,
            }
        )

    # Vành tối = những TRANG còn giảng được mà học viên chưa giảng nổi. Dùng
    # đúng luật mở phiên (`teachable_words`) để lọc: trang bìa, trang agenda
    # không có gì để giảng thì cũng không được hiện ra như một chỗ "còn tối".
    # Bản đầu lấy vành tối từ danh sách thuật ngữ mớm cho nhận dạng giọng nói,
    # nên bản đồ bảo học viên còn tối ở "arxiv" và "kimi".
    # Chỉ các bộ học viên ĐANG học (có trang sáng hoặc đã thử giảng): với 28
    # bộ slide, gửi hết là cả nghìn trang tối trong khi bản đồ chỉ vẽ 16.
    progress = await JsonProgressStore(settings.progress_file).load(who)
    dang_hoc = {split_key(k)[0] for k in [*graph.claims, *progress.pages]}
    # Mở bản đồ từ một trang đang học: bộ đó luôn có mặt, để đánh dấu được
    # "bạn đang ở đây" kể cả khi chưa giảng được trang nào của bộ.
    if deck in _deck_paths():
        dang_hoc.add(deck)
    dim = []
    for slug in _deck_paths():
        if dang_hoc and slug not in dang_hoc:
            continue
        for page, title in _teachable_pages(slug):
            key = page_key(slug, page)
            if key not in graph.claims:
                dim.append(
                    {"concept": key, "title": title, "label": short_label(title), "deck": slug, "page": page}
                )
        if not dang_hoc:
            break  # chưa học gì: một bộ là đủ để bản đồ có vành ngoài

    return {
        "student_id": who,
        "claims": sorted(claims, key=lambda c: -c["times_taught"]),
        "links": [
            {
                "source": l.source,
                "target": l.target,
                "kind": l.kind,
                "label": LINK_LABEL.get(l.kind, l.kind),
                "evidence": l.evidence,
            }
            for l in graph.links.values()
        ],
        "dim": dim,
    }


@api.get("/progress")
async def progress_api(student_id: str = "demo", member: str = Depends(require_member)):
    """Mức hiểu từng trang của học viên đang đăng nhập, gom theo bộ slide.

    Mẫu số là số trang GIẢNG ĐƯỢC của bộ (`_teachable_pages`), không phải tổng
    số trang: trang bìa và trang agenda không có gì để hiểu.
    """
    who = member if _members() else student_id
    progress = await JsonProgressStore(settings.progress_file).load(who)
    decks: dict[str, dict] = {}
    recent = []
    for key, pp in progress.pages.items():
        slug, page = split_key(key)
        if slug not in _deck_paths():
            continue
        entry = decks.setdefault(slug, {"pages": {}})
        entry["pages"][page] = {
            "level": pp.level,
            "attempts": len(pp.sessions),
            "taught": len(pp.taught_sessions),
            "last_at": pp.last_at,
        }
        titles = dict(_teachable_pages(slug))
        recent.append(
            {"deck": slug, "page": page, "title": titles.get(page, f"Trang {page}"), "level": pp.level, "at": pp.last_at}
        )
    summary = dict.fromkeys(LEVELS, 0)
    for slug, entry in decks.items():
        tong = len(_teachable_pages(slug))
        levels = dict.fromkeys(LEVELS, 0)
        for v in entry["pages"].values():
            levels[v["level"]] += 1
        levels["moi"] = max(0, tong - sum(levels.values()))
        entry |= {"teachable": tong, "levels": levels}
        for k, n in levels.items():
            if k != "moi":
                summary[k] += n
    recent.sort(key=lambda r: r["at"], reverse=True)
    return {"student_id": who, "summary": summary, "decks": decks, "recent": recent[:8]}


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
    link = (
        (ws.query_params.get("a") or "", ws.query_params.get("b") or "")
        if ws.query_params.get("mode") == "link"
        else None
    )
    try:
        lesson, spans, llm, stt, tts, session_log, profiles, graphs = _build_deps(
            selection, ws.query_params.get("deck"), link
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
    # Đồ thị tri thức: thứ học viên đã DẠY ĐƯỢC qua mọi buổi, mọi tài liệu.
    # KHÔNG đặt tên `graph`: biến đó đã là LangGraph đã compile ở ngay trên,
    # và đè lên nó thì mọi lượt chấm chết với 'KnowledgeGraph has no astream'.
    knowledge = await graphs.load(student_id)
    progress_store = JsonProgressStore(settings.progress_file)
    progress = await progress_store.load(student_id)
    page_ref = None if link else _page_ref(ws.query_params.get("deck"), lesson)
    # Phiên nối chỉ mở được giữa hai trang ĐÃ sáng: nối một trang học viên chưa
    # giảng nổi là bắt họ nối hai thứ mà học trò còn chưa biết.
    link_pages = (_page_by_key(link[0]), _page_by_key(link[1])) if link else None
    if link_pages and not all(p and p.key in knowledge.claims for p in link_pages):
        await ws.send_json(
            {"type": "error", "message": "Hai trang phải giảng được rồi thì mới nối được."}
        )
        await ws.close()
        return
    # Mọi lượt nói của buổi này: trang sáng lên với CẢ phần giảng chính lẫn câu
    # trả lời cho câu hỏi ngược, không chỉ lượt cuối cùng.
    session_texts: list[str] = []

    live: LiveTurn | None = None
    last_grade: GradeResult | None = None
    live_code = lesson.code
    first_turn = True
    turn_index = 0
    review_spans: list[str] = []

    async def tell(payload: dict) -> None:
        """Gửi cho học viên, im lặng bỏ qua nếu họ đã đóng tab.

        Đường phục hồi lỗi chạy SAU khi một thứ khác đã hỏng, và lý do hay gặp
        nhất chính là học viên đóng tab giữa phiên. Lúc đó socket đã đóng,
        `send_json` ném RuntimeError, và câu báo lỗi lại làm sập luôn handler —
        quan sát thật trên bản deploy rạng sáng 18/9, hai lần trong một log.

        Không nuốt lỗi bừa: chỉ bỏ qua đúng trường hợp phía kia đã đi.
        """
        if ws.application_state is not WebSocketState.CONNECTED:
            return
        try:
            await ws.send_json(payload)
        except (WebSocketDisconnect, RuntimeError):
            log.info("Học viên đã rời phiên, bỏ qua tin %r", payload.get("type"))

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
        await tell(
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
        opening = (
            await open_link_session(
                llm, *link_pages, *(_taught(knowledge, p) for p in link_pages)
            )
            if link_pages
            else await open_session(
                llm, spans, list(lesson.source_span_ids), profile.recurring_gaps,
                lesson.concept, lesson.code,
            )
        )
        # Câu mở bài không đi qua run_turn nên phải tự lọc; đo được thật: lọt
        # "REWARD MODEL" viết hoa y như slide.
        opening = speakable(opening)
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
                    "known_claims": known_claims(knowledge, list(lesson.source_span_ids)),
                    "code": live_code,
                    "link": bool(link_pages),
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
                            session_log, session_id, turn_index, student_text, event, student_id
                        )
                        review_spans = event.payload["result"].get("review_span_ids", [])
                        # Đồ thị lưu NGAY sau mỗi lượt, không đợi kết phiên như
                        # hồ sơ: đây là trí nhớ của học trò, mà học viên đóng
                        # tab giữa chừng là chuyện thường — mất thứ họ vừa dạy
                        # được thì đúng cái tính năng này sinh ra để tránh.
                        session_texts.append(student_text)
                        verdict = event.payload["result"].get("verdict")
                        if link_pages:
                            absorb_link(
                                knowledge,
                                a=link_pages[0],
                                b=link_pages[1],
                                student_texts=session_texts,
                                verdict=verdict,
                                session_id=session_id,
                            )
                        else:
                            absorb_turn(
                                knowledge,
                                page=page_ref,
                                student_texts=session_texts,
                                verdict=verdict,
                                session_id=session_id,
                            )
                            if page_ref is not None and verdict:
                                # Ghi theo LƯỢT, như đồ thị: học viên đóng tab
                                # giữa buổi vẫn giữ được lần thử vừa rồi.
                                progress.record(
                                    page_ref.key,
                                    session_id,
                                    verdict,
                                    datetime.now().astimezone().isoformat(timespec="seconds"),
                                )
                                await progress_store.save(progress)
                        await graphs.save(knowledge)
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
                await tell(
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
                await tell(
                    {"type": "error", "message": "Mình nghe chưa rõ, bạn nói lại giúp mình nhé."}
                )
                turn_state = TurnState.STUDENT_TEACHING.name
                await send_state(turn_state)

            if TurnState[turn_state].is_terminal:
                # Buổi đã đóng: giờ mới cộng vào hồ sơ, theo kết quả lượt cuối.
                # Bỏ dở giữa chừng thì không ghi gì — chưa học xong thì chưa có
                # gì để nhớ, và đó cũng là cách duy nhất để "số buổi" đúng nghĩa.
                if last_grade is not None and not link_pages:
                    profile.absorb(lesson.concept, last_grade)
                    await profiles.save(profile)
                await tell(
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
    session_log, session_id: str, index: int, student_text: str, event, student_id: str = ""
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
                "grader": (
                    GRADER_CODE_VERSION
                    if result.get("code")
                    else GRADER_LINK_VERSION
                    if result.get("link")
                    else GRADER_VERSION
                ),
                "student_persona": PERSONA_VERSION,
                "talker": TALKER_VERSION,
            },
            grade=grade,
            agent_said=event.payload["said"],
            student_id=student_id,
            kind="code" if result.get("code") else "link" if result.get("link") else "page",
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


def _warm_decks() -> None:
    """Đọc sẵn mọi bộ slide (chạy ở thread nền lúc server lên, xem `_lifespan`).

    Không đọc sẵn thì người đầu tiên mở thư viện chờ ~40 giây trong lúc server
    đọc 28 file PDF.
    """
    for slug in _deck_paths():
        try:
            _find_deck(slug)
            _teachable_pages(slug)
        except Exception:
            log.exception("Không đọc được bộ slide %s", slug)
    log.info("Đã nạp sẵn %d bộ slide", len(_deck_paths()))
