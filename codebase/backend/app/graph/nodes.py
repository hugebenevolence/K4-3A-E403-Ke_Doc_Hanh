"""Các node quyết định.

Dependency (LLM, kho span) được tiêm qua closure ở build.py thay vì import
trực tiếp, để test node mà không cần provider thật.
"""

from __future__ import annotations

import logging
import re

from app.domain.graph import PageRef, denies_relation, short_label, spoken_label
from app.domain.leak import (
    about_source,
    confirms_answer,
    content_terms,
    leaked_terms,
    leaks_answer,
    looks_english,
    off_topic,
    suggests_fix,
    takes_teacher_role,
)
from app.domain.session import TeachBackSession, TurnState
from app.domain.span import normalize_span_id
from app.domain.substance import is_thin_teachback
from app.domain.verbatim import echoes_student, is_verbatim_paste, quotes_source
from app.domain.verdict import Evidence, GradeResult, Verdict, decide
from app.graph.state import TeachBackState
from app.ports.knowledge import SpanStore
from app.ports.llm import LLMClient, ModelTier
from app.prompts import registry
from app.prompts.schemas import FollowupOutput, GradeOutput, LinkOpenerOutput

log = logging.getLogger(__name__)

GRADER_VERSION = "v4"
GRADER_CODE_VERSION = "v2"
GRADER_LINK_VERSION = "v4"
PERSONA_VERSION = "v3"
OPENER_VERSION = "v3"
LINK_OPENER_VERSION = "v2"


async def open_session(
    llm: LLMClient,
    spans: SpanStore,
    lesson_span_ids: list[str],
    recurring_gaps: dict,
    concept: str = "khái niệm này",
    code: str = "",
) -> str:
    """Câu mở bài: mời học viên dạy, neo vào một chỗ cụ thể trong nguồn.

    Không có bước này thì học viên bấm "Bắt đầu phiên" xong nhìn một ô trống và
    phải tự nghĩ ra nên nói gì — đó là lúc hầu hết người ta bỏ cuộc, hoặc đọc
    lại slide cho xong. Một câu hỏi cụ thể buộc người ta phải dừng lại nghĩ,
    và đó mới là điểm của cả bài tập này.
    """
    source = await spans.get_many(lesson_span_ids)
    hint = (
        "\n\nBuổi trước bạn ấy cũng chưa thông đúng chỗ này — có thể nhắc nhẹ, "
        "nhưng vẫn phải là câu hỏi mở, không phải câu dò bài."
        if any(recurring_gaps.get(s) for s in lesson_span_ids)
        else ""
    )
    if code:
        # Quan sát thật: mở bài cho bài code lại đi mách luôn cách sửa — "tại
        # sao vòng trong vẫn duyệt từ đầu thay vì CHỈ TỪ i+1?" — tức là đưa sẵn
        # tối ưu mà học viên phải tự tìm ra. Prompt mở bài dùng chung không có
        # luật này vì bài slide không có "cách sửa" để mà lỡ miệng.
        hint += (
            "\n\nĐây là buổi giải thích CODE. Hỏi về những gì code ĐANG làm, "
            "tuyệt đối không gợi ý nó NÊN làm gì: không nêu cách sửa, không "
            "nhắc tên thuật toán hay cấu trúc dữ liệu tốt hơn, không nói 'thay "
            "vì', 'lẽ ra', 'chỉ cần'. Học viên phải tự tìm ra."
        )

    system = registry.compose_system("opener", OPENER_VERSION, source, code=code)
    body = "\n".join(s.text for s in source)

    for attempt in range(2):
        out = await llm.structured(
            system=system,
            user=f"Hãy mở đầu buổi học.{hint}",
            schema=FollowupOutput,
            tier=ModelTier.STANDARD,
        )
        # Model rất hay mở bài bằng cách TRÍCH THẲNG nguồn ("mình thấy nguồn
        # nói ... — giải thích chỗ đó nhé?"), tức là đọc hộ đúng câu học viên
        # phải tự nói ra. Prompt cấm nhưng không giữ được, nên chặn bằng luật:
        # một câu hỏi mở bài không có lý do gì trùng liền mạch với nguồn.
        if quotes_source(out.question, body):
            log.warning("Câu mở bài trích nguyên văn nguồn, viết lại (lần %d)", attempt + 1)
            hint += (
                "\n\nCÂU BẠN VỪA VIẾT ĐÃ TRÍCH NGUYÊN VĂN ĐOẠN NGUỒN. Viết lại, "
                "chỉ nêu HIỆN TƯỢNG bằng lời của bạn, tuyệt đối không chép chữ "
                "nào liền mạch từ nguồn."
            )
            continue
        if not code and not about_source(out.question, body):
            log.warning("Câu mở bài không nói gì về vùng đã chọn, viết lại (lần %d)", attempt + 1)
            hint += (
                "\n\nCÂU BẠN VỪA VIẾT KHÔNG NÓI GÌ VỀ ĐOẠN NGUỒN — nó nói về một chủ "
                "đề khác. Chỉ hỏi về đúng nội dung trong đoạn nguồn bên trên."
            )
            continue
        if code and suggests_fix(out.question):
            log.warning("Câu mở bài mách cách sửa, viết lại (lần %d)", attempt + 1)
            hint += (
                "\n\nCÂU BẠN VỪA VIẾT ĐÃ MÁCH CÁCH SỬA. Chỉ hỏi về những gì code "
                "ĐANG làm — không so sánh với cách làm khác, không dùng 'thay vì', "
                "'lẽ ra', 'chỉ cần', và không nhắc tới chỉ số hay cấu trúc nào "
                "mà code hiện chưa dùng."
            )
            continue
        return out.question

    # Viết lại vẫn trích thì thà mở bài nhạt còn hơn đọc hộ bài.
    log.warning("Mở bài vẫn trích nguồn sau khi viết lại, dùng câu an toàn")
    return f"Bạn giảng cho mình nghe về {concept} đi, mình chưa nắm được chỗ này."


_LINK_FRAME = (
    "giống khác nhau điểm chung tác động ảnh hưởng thay đổi "
    "hai trang theo gọi phần trên lúc dùng làm"
)
"""Chữ của chính ba hướng hỏi và của việc "đặt hai trang cạnh nhau".

Đo được bằng model thật: "hai kiểu Context ở hai trang đó khác nhau ở chỗ
nào?" — một câu mở rất tốt, vì học viên đã dùng chữ Context theo hai nghĩa —
bị chặn là lộ vì trùng "hai", "trang", "trên" với chữ trên slide. Cặp nào
trượt vì những chữ này là rơi về câu viết sẵn."""

_KY_HIEU_TRANG = re.compile(
    r"\b(?:trang|slide)\s*(?:[ab]\b|\d|kia\b|thứ\b|đầu\b|sau\b|trước\b|một\b|hai\b)",
    re.IGNORECASE,
)
"""Gọi trang theo ký hiệu thay vì theo tên.

Prompt cấm rồi mà model thật vẫn viết "còn trang kia nói…", "slide thứ nhất
gọi Context là…": thứ tự A/B là chuyện nội bộ của prompt, học viên chỉ thấy
hai ô trên bản đồ và không biết ô nào là A."""

MAX_LINK_OPENER_WORDS = 60
"""Câu mở phiên nối được đọc thành tiếng; prompt đòi dưới 45 từ, quá 60 là
model đang kể lại cả hai trang chứ không còn là một câu hỏi."""


def link_fallback(a: PageRef, b: PageRef) -> str:
    """Câu mở phiên nối viết sẵn, dùng khi model viết lại vẫn trượt.

    Không hỏi "hai trang liên quan gì": câu đó mời đúng câu trả lời rỗng "đều
    nói về AI". Nêu sẵn ba hướng để học viên có chỗ bám mà vẫn không lộ gì.
    """
    return (
        f"Bạn đã dạy mình «{short_label(a.title)}» và «{short_label(b.title)}» rồi. "
        "Theo bạn, hai thứ đó giống nhau ở đâu, khác nhau ở đâu, "
        "hay cái này làm cái kia thay đổi?"
    )


def _link_opener_flaw(
    question: str, source: str, learner: str, visible: str, sides: list[set[str]]
) -> str:
    """Lỗi của câu mở phiên nối, viết thành lời nhắc cho lần viết lại. Rỗng là đạt."""
    if confirms_answer(question):
        return (
            "ĐÃ HỎI KIỂU 'có phải… không', tức là đưa sẵn một mối nối để học viên "
            "gật đầu. Hỏi mở, để học viên tự tìm."
        )
    if takes_teacher_role(question):
        return "ĐÃ NHẬN VAI NGƯỜI GIẢNG. Bạn là học trò, bạn chỉ hỏi."
    if leaks_answer(question, source, learner, visible):
        leaked = ", ".join(sorted(leaked_terms(question, source, learner, visible)))
        return (
            f"ĐÃ NÓI RA ĐIỀU HỌC VIÊN CHƯA HỀ NÓI ({leaked}). Chỉ dùng những gì "
            "học viên đã nói ở hai trang."
        )
    if _KY_HIEU_TRANG.search(question):
        return (
            "GỌI TRANG BẰNG KÝ HIỆU ('trang A', 'trang kia', 'slide thứ nhất'). "
            "Học viên không biết bạn đánh số thế nào — gọi mỗi trang bằng tên của nó."
        )
    terms = content_terms(question)
    if not all(terms & side for side in sides):
        return (
            "CHƯA NHẮC TỚI CẢ HAI TRANG. Gói lại một ý học viên đã nói ở mỗi "
            "trang, bằng chính lời họ, và gọi trang bằng tên của nó."
        )
    if len(question.split()) > MAX_LINK_OPENER_WORDS:
        return "QUÁ DÀI. Một câu hỏi dưới 45 từ, mỗi trang chỉ một ý."
    return ""


async def open_link_session(
    llm: LLMClient, a: PageRef, b: PageRef, a_said: list[str], b_said: list[str]
) -> str:
    """Câu mở phiên nối hai trang, dựng từ chính lời học viên đã giảng ở mỗi trang.

    Bản trước là một câu cố định "Hai trang đó liên quan gì với nhau?" — không
    lộ được gì, nhưng cũng không cho học viên chỗ nào để bám: họ phải tự nhớ
    lại mình đã nói gì ở hai buổi khác nhau, và câu trả lời dễ nhất là "đều nói
    về AI". Nhắc lại lời của chính họ ở hai trang rồi hỏi theo MỘT hướng (giống
    ở đâu, khác ở đâu, cái này làm cái kia đổi ra sao) thì họ biết ngay phải
    nghĩ từ đâu — và nhiều cặp trang đáng PHÂN BIỆT hơn là đáng nối.

    Model chỉ được thấy lời học viên, không thấy nguồn: không có nguồn thì
    không có mối nối nào để lỡ miệng đọc hộ. Kiến thức chung của model vẫn có
    thể lọt ra, nên câu hỏi vẫn qua bộ lọc lộ đáp án với nguồn của cả hai trang.
    """
    a_said = [s for s in a_said if s.strip()]
    b_said = [s for s in b_said if s.strip()]
    source = f"{a.text}\n{b.text}"
    learner = " ".join([*a_said, *b_said])
    # Tên hai trang đang hiện trên bản đồ, và khung câu hỏi ("khác nhau ở
    # đâu") là chính thứ được dặn phải hỏi — trùng chữ nguồn cũng không lộ gì.
    visible = f"{a.title} {b.title} {_LINK_FRAME}"
    # "Chạm tới một trang" tính bằng từ RIÊNG của trang đó. Hai trang hay có
    # chung chữ ("câu trả lời" ở cả RLHF lẫn context), và tính cả chữ chung thì
    # một câu chỉ hỏi về một trang vẫn lọt qua như đã hỏi cả hai. Tên trang cũng
    # tính: học viên không còn câu nào rõ ở một trang thì chỉ còn tên để gọi.
    ta = content_terms(" ".join([*a_said, a.title]))
    tb = content_terms(" ".join([*b_said, b.title]))
    sides = [(ta - tb) or ta, (tb - ta) or tb]

    def trang(p: PageRef, said: list[str]) -> str:
        lines = "\n".join(f"> {s}" for s in said) or "> (không còn câu nào rõ)"
        # Tên để NÓI, không phải tiêu đề slide: model gọi trang bằng đúng cái
        # tên mình đưa, nên đưa tiêu đề đầy đủ là nó đọc cả "— nằm ở đâu trong
        # cùng một hệ?" ra miệng, còn đưa nhãn bản đồ là nó đọc cả dấu ba chấm.
        return f"Trang «{spoken_label(p.title)}»\nHọc viên đã nói:\n{lines}"

    user = f"{trang(a, a_said)}\n\n{trang(b, b_said)}"
    system = registry.compose_system("link_opener", LINK_OPENER_VERSION)
    hint = ""
    for attempt in range(2):
        out = await llm.structured(
            system=system, user=user + hint, schema=LinkOpenerOutput, tier=ModelTier.STANDARD
        )
        flaw = _link_opener_flaw(out.question, source, learner, visible, sides)
        if not flaw:
            log.info("Mở phiên nối kiểu %s: %s", out.angle, out.question)
            return out.question
        log.warning("Câu mở phiên nối hỏng (lần %d): %s — %s", attempt + 1, flaw, out.question)
        hint += f"\n\nCÂU BẠN VỪA VIẾT {flaw}"

    log.warning("Mở phiên nối vẫn hỏng sau khi viết lại, dùng câu viết sẵn")
    return link_fallback(a, b)


_SAID_PREFIX = "> "
"""Mỗi lượt học viên đã nói là MỘT dòng mở đầu bằng dấu này.

Một dòng một lượt để model đọc được ranh giới giữa các lượt, và để mock đếm
được đúng số chữ học viên nói mà không lẫn chữ của khung prompt.
"""


def _grade_user(said: list[str], asked: list[str]) -> str:
    """Phần biến thiên của prompt chấm: mọi lượt học viên đã nói trong buổi.

    Đưa cả buổi chứ không chỉ lượt cuối. Bản trước chỉ gửi đúng lượt vừa nói,
    nên một mảnh trả lời cho câu hỏi hẹp bị đem đối chiếu với TOÀN BỘ đoạn
    nguồn — hoặc trượt oan, hoặc (phiên thật 2e6d52f3) cho qua cả bài chỉ vì
    một mảnh.

    Câu hỏi ngược gần nhất đi kèm ở cuối: không có nó thì dòng cuối đọc lên như
    một lời giảng cụt lủn thay vì một câu trả lời.
    """
    lines = "\n".join(_SAID_PREFIX + " ".join(text.split()) for text in said)
    block = f"Lời học viên trong buổi này, theo thứ tự từng lượt:\n\n{lines}"
    if asked:
        block += (
            f"\n\nDòng cuối là câu trả lời cho câu mình vừa hỏi: "
            f"«{' '.join(asked[-1].split())}»"
        )
    return block


def make_grade_node(llm: LLMClient, spans: SpanStore):
    async def grade(state: TeachBackState) -> TeachBackState:
        span_ids = state.get("source_span_ids") or []
        if not span_ids:
            # Chấm mà không có nguồn thì chỉ còn kiến thức chung của model —
            # đúng cái mà thiết kế grounding cấm. Thà hỏng to còn hơn chấm bịa.
            raise ValueError("Phiên không có source_span_ids; không thể chấm có căn cứ")

        source = await spans.get_many(span_ids)
        student_text = state["student_text"]
        said = [*(state.get("said_before") or []), student_text]

        # Tiền kiểm tất định trước khi tốn một lượt gọi LLM: đọc lại nguyên văn
        # nguồn không phải là dạy lại, dù model có thấy "đúng hết" đi nữa.
        # Xét trên LƯỢT NÀY, không cộng dồn: "đang đọc lại tài liệu" là chuyện
        # của lượt vừa nói, và một lượt chép sẽ kéo tỉ lệ của cả buổi đi theo.
        verbatim = is_verbatim_paste(student_text, "\n".join(s.text for s in source))

        # Ngược lại, sàn "nói quá ít" phải tính CỘNG DỒN: giảng một nửa rồi nói
        # nốt nửa sau khi bị hỏi lại vẫn là đã giảng đủ. Xem domain/substance.py.
        thin = is_thin_teachback(said)

        # Bài code dùng prompt chấm riêng: nguồn không phải là chữ trên slide mà
        # là hành vi thật của đoạn code, và chỗ cấm quan trọng nhất đổi từ
        # "đừng nói hộ đáp án" thành "đừng sửa hộ code".
        code = state.get("code") or ""
        grader, version = (
            ("grader_code", GRADER_CODE_VERSION)
            if code
            else ("grader_link", GRADER_LINK_VERSION)
            if state.get("link")
            else ("grader", GRADER_VERSION)
        )

        out = await llm.structured(
            system=registry.compose_system(grader, version, source, code=code),
            user=_grade_user(said, state.get("asked_questions") or []),
            schema=GradeOutput,
            tier=ModelTier.STANDARD,
        )

        # Model có thể bịa ra mã đoạn không tồn tại. Không lọc thì mã bịa đó
        # chui vào log, vào hồ sơ học viên, rồi hiện lên màn hình dưới dạng
        # "xem lại đoạn [T06-999]" — học viên đi tìm một đoạn không có thật.
        # Đây là chỗ chặn được bằng luật tất định, không cần hỏi lại model.
        # Khớp nới theo dạng chuẩn hoá rồi trả về mã CANONICAL, để mọi thứ ghi
        # xuống log/hồ sơ đều cùng một dạng dù model viết kiểu gì.
        known = {normalize_span_id(s.span_id): s.span_id for s in source}
        cited = tuple(
            Evidence(
                known[key],
                e.quote,
                e.covered_by_student,
                e.key,
                e.contradicted_by_student,
            )
            for e in out.evidence
            if (key := normalize_span_id(e.span_id)) in known
        )
        if bogus := [
            e.span_id for e in out.evidence if normalize_span_id(e.span_id) not in known
        ]:
            # Bỏ SẠCH evidence là chuyện khác hẳn bỏ một mã lẻ: lượt đó không
            # còn căn cứ nào, nên `decide()` trả INCOMPLETE dù học viên giảng
            # thế nào đi nữa — học viên bị đánh trượt vì bộ chấm hỏng, không
            # phải vì lời giảng. Đo được thật: F01 và F02 trượt 0/3 lượt vì
            # model tự đặt mã "s1..s4" thay cho mã có sẵn.
            if not cited:
                log.error(
                    "Bộ chấm không trả về mã đoạn nào có thật (%s) — lượt này mất "
                    "sạch căn cứ và sẽ bị chấm là chưa đủ",
                    bogus,
                )
            else:
                log.warning("Bỏ %d mã đoạn không có thật do model bịa: %s", len(bogus), bogus)

        # Phiên NỐI: nhãn SAI chỉ được dựng trên một ý cụ thể bị đánh cờ nói
        # trái, không dựng trên ô văn xuôi `contradiction`. Ô đó vốn là tín hiệu
        # yếu (lý do ta đã chuyển sang cờ theo từng ý), và ở phiên nối nó bắn
        # đúng chỗ tệ nhất: học viên nói "hai trang này chả liên quan", bộ chấm
        # — vốn đang đi tìm một mối nối — ghi đó là nói trái, và một lập trường
        # hợp lệ bị chấm là hiểu sai. Đo được thật 18/9, phiên của member5.
        link = bool(state.get("link"))
        contradiction = out.contradiction
        if link and not any(e.contradicted_by_student for e in cited):
            if contradiction.strip():
                log.warning(
                    "Phiên nối: bỏ nhãn SAI không có ý nào bị đánh cờ nói trái — %s",
                    contradiction.strip()[:160],
                )
            contradiction = ""

        verdict = decide(cited, contradiction, verbatim=verbatim, thin=thin)

        # Bộ dò bất đồng: bộ chấm vừa nói "đủ" nhưng chính nó cũng vừa viết ra
        # một chỗ hổng. Prompt dặn rõ "nói đủ mọi ý thì gap_summary phải RỖNG",
        # nên đây là lúc nó tự mâu thuẫn — và đúng dấu hiệu đã dẫn tới phiên
        # 2e6d52f3 (đóng TAUGHT trong khi gap ghi "chưa nói cơ chế").
        #
        # KHÔNG dùng để đổi verdict: đo trên 4 lượt golden set, phần lớn lượt
        # SUFFICIENT đúng cũng kèm gap mô tả chi tiết phụ, nên hạ nhãn theo tín
        # hiệu này sẽ đánh trượt oan nhiều hơn là bắt đúng. Nó là đèn báo để lọc
        # log thật, không phải luật chấm.
        if verdict is Verdict.SUFFICIENT and out.gap_summary.strip():
            log.warning(
                "Bất đồng: chấm ĐỦ nhưng bộ chấm vẫn ghi chỗ hổng — %s",
                out.gap_summary.strip()[:200],
            )

        # KHÔNG dùng `contradiction` làm gap_summary. Nó mô tả chỗ học viên nói
        # sai bằng cách nêu ra cái đúng ("quy cho nhiệt độ, trong khi nguồn nói
        # là áp suất"), và gap_summary được đưa thẳng cho persona làm đề bài
        # hỏi ngược — tức là đọc luôn đáp án vào câu hỏi. Đã quan sát thấy thật:
        # học viên nói "trên đó lạnh hơn", agent hỏi lại "cái lạnh đó liên quan
        # thế nào đến áp suất khí quyển".
        if verbatim:
            gap = "học viên đang đọc lại gần nguyên văn tài liệu, chưa diễn đạt bằng lời mình"
        elif link and verdict is not Verdict.SUFFICIENT and denies_relation(student_text):
            # Học viên vừa nêu một LẬP TRƯỜNG: hai trang không dính gì tới nhau.
            # Câu hỏi ngược phải đi vào đúng lập trường đó — vì sao họ thấy vậy —
            # chứ không lờ đi rồi hỏi tiếp như thể họ chưa nói gì. Và không được
            # khẳng định là hai trang CÓ liên quan: đó là nối hộ, và có khi còn
            # sai, vì không phải cặp trang nào cũng nối với nhau được.
            gap = (
                "học viên cho rằng hai trang không liên quan gì tới nhau; hỏi xem vì "
                "sao họ nghĩ vậy — không gợi ý chỗ hai trang chạm nhau, và cũng không "
                "khẳng định là chúng có liên quan"
            )
        elif out.gap_summary.strip():
            gap = out.gap_summary
        elif thin:
            # Model bảo không thiếu gì, nhưng cả buổi mới được vài chữ. Chỗ hổng
            # thật là chưa có gì để mà chấm — nói thế để câu hỏi ngược mời họ
            # triển khai tiếp, chứ không đi bới một ý cụ thể không tồn tại.
            gap = "học viên mới nói được một câu rất ngắn, chưa triển khai ý nào"
        elif any(not e.covered_by_student for e in cited):
            # Cố ý KHÔNG nhét trích dẫn nguồn vào đây: quote chính là ý học viên
            # đang thiếu, đưa xuống persona là đọc luôn đáp án vào câu hỏi.
            gap = "còn một ý cốt lõi trong nguồn mà học viên chưa chạm tới"
        else:
            gap = "lời giải thích chưa khớp với nguồn, nhưng chưa xác định được thiếu ở đâu"

        grade_result = GradeResult(verdict=verdict, evidence=cited, gap_summary=gap)

        session = TeachBackSession(
            source_span_id=span_ids[0],
            concept=state["concept"],
            followups_asked=state.get("followups_asked", 0),
        )
        next_state = session.record(grade_result)

        return {
            "evidence": [e.__dict__ for e in grade_result.evidence],
            "gap_summary": grade_result.gap_summary,
            "verdict": verdict.value,
            "was_verbatim": verbatim,
            "followups_asked": session.followups_asked,
            "review_span_ids": list(session.review_span_ids),
            "turn_state": next_state.name,
            # Cộng dồn để lượt sau chấm được cả buổi, không chỉ câu cuối.
            "said_before": [student_text],
        }

    return grade


_OFF_TOPIC = (
    "Cái đó mình chịu, mình chỉ theo được phần bạn đang giảng thôi. "
    "Bạn quay lại phần đang mở, nói tiếp giúp mình nhé?"
)
"""Trả lời khi học viên hỏi chen một câu ngoài buổi giảng.

Học trò không biết gì ngoài đoạn nguồn, nên nói thẳng là không biết rồi mời
quay lại — chứ không đổi vai thành trợ lý kỹ thuật, và cũng không coi câu lạc
đề là một lời giảng để chấm.
"""


_NOT_MY_JOB = (
    "Mình mà biết thì mình đã không nhờ bạn giảng rồi. "
    "Bạn kể mình nghe một ý bạn còn nhớ thôi cũng được."
)
"""Dùng khi học trò tuột vai, nhận sẽ giảng hoặc hỏi học viên muốn mình làm gì.

Từ chối bằng chính lý do của vai chứ không bằng câu máy móc — mình không có đáp
án để đưa — rồi mở một đường vào nhỏ để học viên nói tiếp.
"""


_REANCHORS = (
    "Mình chưa theo kịp đoạn vừa rồi. Bạn thử bắt đầu từ ý bạn chắc chắn nhất được không?",
    "Chỗ này mình vẫn còn mơ hồ. Bạn lấy thử một ví dụ cụ thể giúp mình nhé?",
    "Nếu phải nói gọn trong một câu thôi, thì bạn sẽ nói phần này là gì?",
)


# Dùng khi đã có vài ý "mình hiểu là" hiện ngay phía trên: nói "mình chưa theo
# kịp" lúc đó là tự mâu thuẫn với chính mấy gạch đầu dòng vừa liệt kê.
_CONTINUES = (
    "Tới đó thì mình theo được rồi. Phần tiếp theo diễn ra thế nào vậy bạn?",
    "Mấy ý đó mình nắm rồi. Còn chỗ nào trong phần này mà bạn thấy quan trọng nữa không?",
    "Ừ, mình hiểu tới đây. Bạn nói tiếp giúp mình, sau đó thì sao?",
)


# Phiên NỐI không có "phần này", "ý bạn chắc nhất" hay "phần tiếp theo": thứ
# đang bàn là quan hệ giữa HAI trang học viên đã giảng được rồi. Dùng câu của
# phiên giảng một trang ở đây là hỏi lạc đề — đo được thật 18/9: học viên nói
# "hai trang chả liên quan", học trò đáp "còn chỗ nào trong phần này mà bạn thấy
# quan trọng nữa không?". Không câu nào dưới đây giả định hai trang CÓ nối được.
_LINK_REANCHORS = (
    "Mình chưa hình dung được hai trang đó đứng cạnh nhau thế nào. Theo bạn, cái này có làm gì thay đổi ở cái kia không?",
    "Bạn thử nghĩ một tình huống mà cả hai cùng xuất hiện xem — có không, hay chúng tách hẳn nhau?",
    "Nếu phải nói trong một câu thì bạn sẽ đặt hai trang đó cạnh nhau thế nào? Thấy không dính gì thì nói vì sao cũng được.",
)


def _reanchor(state: TeachBackState, heard: bool = False) -> str:
    """Câu hỏi dùng khi viết lại vẫn lộ đáp án.

    Đổi câu theo số lần đã hỏi. Bản trước chỉ có đúng MỘT câu, và quan sát thật
    là học viên nghe y nguyên câu "Thật ra mình vẫn chưa nối được chỗ bạn vừa
    nói với <tên slide>…" hai ba lần liền — nghe như máy, và tên slide dài thì
    câu đọc lên rất gượng.

    Mỗi câu vẫn là lời mời cụ thể (bắt đầu từ ý chắc nhất / một ví dụ / một
    câu tóm) chứ không phải "bạn giải thích thêm được không" chung chung.
    """
    asked = len(state.get("asked_questions") or [])
    if state.get("link"):
        variants = _LINK_REANCHORS
    else:
        variants = _CONTINUES if heard else _REANCHORS
    return variants[asked % len(variants)]


def _uncovered_text(state: TeachBackState, source) -> str:
    """Nội dung những span học viên chưa chạm tới — tức phần đang thiếu.

    Đây chính là thứ câu hỏi ngược không được nói hộ.
    """
    missing = {
        normalize_span_id(e["span_id"])
        for e in (state.get("evidence") or [])
        if not e.get("covered_by_student")
    }
    return "\n".join(s.text for s in source if normalize_span_id(s.span_id) in missing)


def make_followup_node(llm: LLMClient, spans: SpanStore):
    async def ask_followup(state: TeachBackState) -> TeachBackState:
        source = await spans.get_many(state["source_span_ids"])

        # Câu lạc đề không có chỗ hổng nào để hỏi vào. Chặn TRƯỚC khi gọi model:
        # để model tự viết lúc này là nó bám theo chuyện lạc đề và biến câu hỏi
        # chen thành chủ đề buổi học — mà gọi thì vẫn mất tiền.
        joined = " ".join(s.text for s in source)
        link = bool(state.get("link"))
        # "Hai trang này chả liên quan" trong phiên nối là một câu trả lời, không
        # phải chuyện ngoài lề — đáp bằng "cái đó mình chịu" là lờ đi đúng điều
        # học viên vừa khẳng định.
        stance = link and denies_relation(state["student_text"])
        if not stance and off_topic(state["student_text"], joined):
            log.warning("Lượt này lạc đề, không hỏi ngược theo nó")
            return {
                "agent_says": _OFF_TOPIC,
                "agent_understood": [],
                "cites_span_id": None,
                "asked_questions": [_OFF_TOPIC],
                "turn_state": TurnState.STUDENT_RESPONDING.name,
            }

        # CỐ Ý xét trên LƯỢT NÀY, không cộng dồn cả buổi — ngược với bộ chấm.
        #
        # Bộ lọc lộ đáp án trừ đi những gì học viên đã tự nói: nhắc lại lời họ
        # thì không phải là lộ. Nới "đã nói" ra cả buổi nghe hợp lý, nhưng nó
        # làm guard yếu dần theo từng lượt: học viên buột ra một từ khoá ở lượt
        # 1 trong lúc mô tả SAI cơ chế — bộ chấm vẫn để ý đó là chưa chạm tới —
        # thế là từ đó trở đi agent được phép nói thẳng từ khoá ấy vào câu hỏi,
        # và học viên chỉ cần gật. "Không lộ đáp án" là điều kiện cứng của
        # rubric và lượt chạy 5 đang sạch 26/26; không đánh đổi nó lấy một câu
        # hỏi mượt hơn khi chưa đo được.
        asked = state.get("asked_questions") or []
        history = (
            "\n\nMình đã hỏi những câu này rồi, đừng hỏi lại theo cùng một kiểu:\n"
            + "\n".join(f"- {q}" for q in asked)
            if asked
            else ""
        )

        # Chỗ học viên đã vấp ở buổi trước: nói ra được thì câu hỏi bớt máy móc
        # và học viên thấy agent thật sự đang theo mình qua nhiều buổi.
        gaps = state.get("recurring_gaps") or {}
        if any(gaps.get(sid) for sid in (state.get("source_span_ids") or [])):
            # Cố ý không đưa mã đoạn thô vào đây — model sẽ đọc "[DEMO-01]"
            # thành tiếng giữa buổi học, nghe như máy đọc lỗi.
            history += (
                "\n\nBuổi trước bạn ấy cũng chưa thông đúng chỗ này — có thể nhắc "
                "nhẹ điều đó, nhưng đừng làm bạn ấy thấy bị chấm điểm."
            )

        # Bắc cầu sang thứ học viên đã DẠY ĐƯỢC ở buổi trước (spec §4c). Đây là
        # câu hỏi không tutor nào hỏi được, vì nó dựng từ chính lời họ: "bạn dạy
        # mình là model chỉ đoán chữ tiếp theo — vậy cái xếp hạng này làm nó đổi
        # kiểu gì?". Và nó ép nối các mảnh rời, đúng bước từ knowledge-telling
        # sang knowledge-building.
        #
        # An toàn theo đúng lý do `_heard` an toàn: `said` là NGUYÊN VĂN câu của
        # học viên, nhắc lại lời họ thì không phải lộ. Bộ lọc lộ đáp án vẫn chạy
        # sau đó như thường.
        if da_day := state.get("known_claims") or []:
            history += "\n\nBuổi trước chính bạn ấy đã dạy mình mấy ý này:\n" + "\n".join(
                f"- {c['said']}" for c in da_day
            )
            history += (
                "\n\nNếu ý nào trong số đó nối được với chỗ hổng lần này, hãy bắc cầu "
                "sang nó bằng chính lời bạn ấy — nhắc lại lời họ thì không phải nói hộ."
            )

        code = state.get("code") or ""
        system = registry.compose_system(
            "student_persona", PERSONA_VERSION, source, code=code
        )
        if code:
            # Persona viết cho bài slide nên quen miệng gọi "đoạn nguồn"; đang
            # bàn về code mà nói vậy thì học viên không hiểu đang trỏ vào đâu.
            history += (
                "\n\nĐây là buổi giải thích CODE: gọi là 'code', 'dòng', 'vòng lặp' "
                "chứ đừng gọi là 'đoạn nguồn'. Và tuyệt đối không gợi ý cách sửa "
                "hay nêu tên thuật toán tốt hơn — học viên phải tự tìm ra."
            )
        user = (
            f"Nội dung vừa nghe được:\n{state['student_text']}\n\n"
            f"Chỗ hổng cần hỏi vào:\n{state['gap_summary']}{history}"
        )
        out = await llm.structured(
            system=system, user=user, schema=FollowupOutput, tier=ModelTier.STANDARD
        )

        # Chặn lộ đáp án bằng luật tất định thay vì tin prompt. Nếu câu hỏi nói
        # ra từ khoá của đúng phần học viên còn thiếu thì học viên chỉ cần gật
        # đầu là xong — mất sạch ý nghĩa của việc hỏi ngược.
        uncovered = _uncovered_text(state, source)
        visible = state.get("concept") or ""
        # Bộ lọc lộ đáp án trừ đi những gì học viên ĐÃ tự nói. Ở phiên nối,
        # nội dung của hai trang chính là thứ họ đã giảng được ở buổi trước — lời
        # họ nằm sẵn trong đồ thị. Không tính phần đó thì khi họ chưa nối được gì,
        # TOÀN BỘ chữ của hai trang thành "phần còn thiếu", câu hỏi nào nhắc tới
        # RLHF hay context cũng bị coi là lộ, và học trò rơi về câu dự phòng.
        # Thứ không được nói hộ ở phiên nối là MỐI NỐI, không phải hai trang.
        da_noi = state["student_text"]
        if link:
            da_noi += " " + " ".join(c["said"] for c in state.get("known_claims") or [])
        # Giữ lại phần "mình hiểu là" của lần viết đầu: nếu câu hỏi phải thay bằng
        # câu dự phòng thì học viên vẫn thấy mình được nghe, thay vì nhận một câu
        # chung chung sau khi đã giảng được kha khá.
        first_heard = out.understood
        if uncovered and leaks_answer(out.question, uncovered, da_noi, visible):
            leaked = leaked_terms(out.question, uncovered, da_noi, visible)
            log.warning("Câu hỏi ngược làm lộ đáp án (%s), hỏi lại", sorted(leaked))
            out = await llm.structured(
                system=system,
                user=(
                    f"{user}\n\nCÂU BẠN VỪA VIẾT ĐÃ LỘ ĐÁP ÁN vì có nhắc tới: "
                    f"{', '.join(sorted(leaked))}. Viết lại câu hỏi KHÔNG dùng "
                    "những từ đó và không nói hộ phần học viên còn thiếu."
                ),
                schema=FollowupOutput,
                tier=ModelTier.STANDARD,
            )
            if leaks_answer(out.question, uncovered, da_noi, visible):
                log.warning("Viết lại vẫn lộ, dùng câu hỏi neo lại khái niệm")
                out = FollowupOutput(question=_reanchor(state, heard=bool(first_heard)), understood=first_heard, cites_span_id=None)

        # Câu hỏi "có phải X không" đưa sẵn X cho học viên gật đầu, dù X không
        # trùng chữ nào với nguồn — bộ lọc từ khoá ở trên không thấy được.
        if confirms_answer(out.question):
            log.warning("Câu hỏi ngược dạng 'có phải… không', hỏi lại: %s", out.question)
            out = await llm.structured(
                system=system,
                user=(
                    f"{user}\n\nCÂU BẠN VỪA VIẾT LÀ CÂU 'CÓ PHẢI … KHÔNG' — nó đưa sẵn "
                    "câu trả lời cho học viên gật đầu. Viết lại thành câu hỏi mở "
                    "(vì sao / thế nào / điều gì), không nêu sẵn phương án nào."
                ),
                schema=FollowupOutput,
                tier=ModelTier.STANDARD,
            )
            if confirms_answer(out.question) or (
                uncovered and leaks_answer(out.question, uncovered, da_noi, visible)
            ):
                log.warning("Viết lại vẫn là câu xác nhận hoặc vẫn lộ, dùng câu hỏi neo lại")
                out = FollowupOutput(question=_reanchor(state, heard=bool(first_heard)), understood=first_heard, cites_span_id=None)

        # Câu lạc đề không có chỗ hổng nào để hỏi vào, nên model hay nhại lại
        # nguyên câu học viên vừa nói. Bắt bằng độ trùng chuỗi, không hỏi thêm
        # LLM: nhại lại thì trùng dài liền mạch, hỏi thật thì không.
        if echoes_student(out.question, state["student_text"]):
            log.warning("Câu hỏi ngược nhại lại lời học viên, chuyển sang câu ngoài phạm vi")
            out = FollowupOutput(question=_OFF_TOPIC, understood=[], cites_span_id=None)

        # Nhận vai người giảng là hỏng nặng hơn lộ một từ khoá: học viên hết
        # lý do phải tự nói. Xét cả phần "mình hiểu là", vì câu tuột vai hay
        # nằm ở đó ("Bạn muốn mình giải thích attention nhưng chưa nêu gì").
        if takes_teacher_role(" ".join([out.question, *out.understood])):
            log.warning("Học trò nhận vai người giảng, thay bằng câu từ chối đúng vai")
            out = FollowupOutput(question=_NOT_MY_JOB, understood=[], cites_span_id=None)

        # Với bài code, lộ đáp án mang hình dạng khác: mách cách sửa. Phải bắt
        # riêng, vì phần code học viên chưa nói tới KHÔNG phải thứ cấm nhắc —
        # cấm là nói ra cách làm tốt hơn, mà cách nói đó không trùng từ nào với
        # nguồn nên bộ lọc từ khoá ở trên không thấy.
        if code and suggests_fix(out.question):
            log.warning("Câu hỏi ngược mách cách sửa, hỏi lại")
            out = await llm.structured(
                system=system,
                user=(
                    f"{user}\n\nCÂU BẠN VỪA VIẾT ĐÃ MÁCH CÁCH SỬA. Chỉ hỏi về "
                    "những gì code ĐANG làm — không so sánh với cách làm khác, "
                    "không dùng 'thay vì', 'lẽ ra', 'chỉ cần', 'tốt hơn'."
                ),
                schema=FollowupOutput,
                tier=ModelTier.STANDARD,
            )
            if suggests_fix(out.question):
                log.warning("Viết lại vẫn mách cách sửa, dùng câu hỏi neo lại")
                out = FollowupOutput(question=_reanchor(state, heard=bool(first_heard)), understood=first_heard, cites_span_id=None)

        # Trích dẫn bịa còn tệ hơn không trích: frontend sẽ dùng mã này để
        # highlight vùng trên slide, trỏ sai là học viên mất niềm tin ngay.
        canonical = {normalize_span_id(s.span_id): s.span_id for s in source}
        cites = canonical.get(normalize_span_id(out.cites_span_id or ""))
        if out.cites_span_id and not cites:
            log.warning("Bỏ trích dẫn bịa trong câu hỏi ngược: %s", out.cites_span_id)

        return {
            "agent_says": out.question,
            "agent_understood": _heard(
                out.understood,
                uncovered,
                da_noi,
                visible,
                state.get("vocabulary"),
                said=_said_this_session(state),
                earlier=[c["said"] for c in state.get("known_claims") or []],
            ),
            "cites_span_id": cites,
            "asked_questions": [out.question],
            "turn_state": TurnState.STUDENT_RESPONDING.name,
        }

    return ask_followup


MAX_UNDERSTOOD = 3

_LATIN = re.compile(r"(?<![^\W\d_])[A-Za-z][A-Za-z0-9]{2,}(?![^\W\d_])")


def _latin_words(text: str) -> list[str]:
    """Từ viết bằng chữ Latin không dấu, từ 3 ký tự — tức gần như chắc là tiếng Anh."""
    return _LATIN.findall(text or "")


def _said_this_session(state: TeachBackState) -> str:
    """Mọi lời học viên đã nói TRONG PHIÊN NÀY, kể cả lượt vừa xong.

    Ở node hỏi ngược, `said_before` đã gồm luôn lượt hiện tại (reducer cộng nó
    vào ngay sau node chấm — xem graph/state.py), nên chỉ thêm `student_text`
    khi nó chưa nằm ở cuối, để khỏi đếm hai lần.
    """
    said = list(state.get("said_before") or [])
    if not said or said[-1] != state["student_text"]:
        said.append(state["student_text"])
    return " ".join(said)


def _heard(
    points: list[str],
    uncovered: str,
    student_text: str,
    visible: str = "",
    vocabulary: list[str] | None = None,
    *,
    said: str | None = None,
    earlier: list[str] | None = None,
) -> list[str]:
    """Chỉ giữ những ý "mình nghe hiểu" không nói hộ phần học viên còn thiếu.

    Prompt dặn phần này chỉ được chứa điều học viên đã nói, nhưng đây đúng là
    chỗ dễ lộ nhất: model "diễn đạt lại cho gọn" bằng chính từ khoá của nguồn mà
    học viên chưa hề nói ra. Dòng nào lộ thì bỏ hẳn dòng đó — thiếu một gạch đầu
    dòng không sao, lộ đáp án thì mất ý nghĩa của cả buổi.
    """
    known = {w.lower() for w in (vocabulary or ())} | {w.lower() for w in _latin_words(visible)}
    kept = []
    for point in points:
        # "chấm/điểm", "cộng/trừ": gộp hai chữ bằng gạch chéo đọc lên như ghi
        # chú nháp, không phải câu nói.
        point = " ".join(point.replace("/", " hoặc ").split())
        if not point:
            continue
        # Chữ tiếng Anh không có trong từ vựng của bài gần như luôn là chữ máy
        # nghe nhầm bị chép lại: "JSON", "button" khi học viên nói "model".
        # Prompt cấm hai lần mà model vẫn chép, nên bỏ cả dòng — chép lại lỗi
        # của máy là làm học viên tưởng mình nói sai.
        # Viết tắt THẬT của bài (LLM, RLHF) đã nằm sẵn trong từ vựng, nên không
        # cần miễn trừ chữ viết HOA — miễn trừ là lọt đúng "JSON".
        strange = [w for w in _latin_words(point) if looks_english(w) and w.lower() not in known]
        if vocabulary is not None and strange:
            log.warning("Bỏ ý 'mình hiểu là' vì chép chữ lạ có thể do nghe nhầm %s: %s", strange, point)
            continue
        if uncovered and leaks_answer(point, uncovered, student_text, visible):
            log.warning("Bỏ ý 'mình hiểu là' vì nói hộ phần còn thiếu: %s", point)
            continue
        # "Mình hiểu là" nghĩa là "BẠN VỪA NÓI thế này". Một dòng không trùng NỔI
        # MỘT từ nội dung nào với lời học viên trong phiên này thì không thể là
        # điều họ vừa nói — nó được lấy từ chỗ khác. Đo được thật 18/9: học viên
        # nói "hai trang chả liên quan", dòng hiện ra lại là câu RLHF họ dạy từ
        # buổi TRƯỚC (persona được đưa đồ thị để bắc cầu, và chép nó sang đây).
        # Ngưỡng một từ là cố ý thấp: đo trên 55 dòng thật của golden set, dòng
        # bám lời học viên yếu nhất vẫn trùng một từ; dòng lỗi kia trùng không từ.
        if said is not None and not content_terms(point) & content_terms(said):
            log.warning("Bỏ ý 'mình hiểu là' vì không bám vào lời nào học viên nói phiên này: %s", point)
            continue
        # Luật một-từ ở trên hở đúng chỗ đắt nhất: học viên dùng vài từ chung
        # của khoá ("model", "trả lời") là câu chép từ buổi trước lọt qua. Gốc
        # lỗi là persona được đưa những câu học viên đã dạy (để bắc cầu trong
        # CÂU HỎI) rồi chép sang phần này. Nên so thẳng: dòng nào giống một câu
        # buổi trước HƠN giống lời vừa nói thì là chép, không phải nghe.
        if said is not None and earlier:
            tu = content_terms(point)
            bay_gio = len(tu & content_terms(said))
            truoc_do = max(len(tu & content_terms(c)) for c in earlier)
            if truoc_do > bay_gio:
                log.warning("Bỏ ý 'mình hiểu là' vì chép từ lời buổi trước chứ không phải vừa nói: %s", point)
                continue
        kept.append(point)
    return kept[:MAX_UNDERSTOOD]


async def close_taught(state: TeachBackState) -> TeachBackState:
    # Trích lại chính ý học viên vừa dạy được: đây là lúc trích dẫn có giá trị
    # nhất và an toàn tuyệt đối — họ đã tự nói ra ý đó rồi, không lộ gì cả, mà
    # lại thấy công mình vừa bỏ ra ứng với đúng chỗ nào trên slide.
    covered = [e["span_id"] for e in (state.get("evidence") or []) if e.get("covered_by_student")]
    return {
        # KHÔNG khen "giảng kỹ": câu này là chuỗi cứng, nói y hệt nhau dù học
        # viên giảng 9 chữ hay 90 chữ. Phiên thật 2e6d52f3 đóng bằng đúng câu
        # "cảm ơn bạn đã giảng kỹ cho mình" sau một câu 9 chữ — lời khen sai chỗ
        # làm hỏng niềm tin vào mọi lời khen còn lại.
        "agent_says": "À, tới đây thì mình hiểu rồi. Cảm ơn bạn đã giảng cho mình.",
        "agent_understood": [],
        "cites_span_id": covered[0] if covered else None,
        "turn_state": TurnState.TAUGHT.name,
    }


async def close_review(state: TeachBackState) -> TeachBackState:
    # Hết lượt hỏi mà chưa đủ: KHÔNG nói đáp án, không phán học viên sai — chỉ
    # trỏ về chỗ nên xem lại. Đây là ràng buộc đạo đức của track, không phải
    # lựa chọn về giọng điệu.
    # Hết phiên rồi thì trỏ thẳng vào chỗ cần xem lại — đây đúng là việc track
    # D3 yêu cầu ("gợi ý học viên xem lại đoạn nào"), và không còn là lộ đáp án
    # vì không còn lượt nào để họ tự tìm nữa.
    review = state.get("review_span_ids") or []
    return {
        "agent_says": (
            "Cảm ơn bạn đã giảng cho mình. Mình vẫn còn lấn cấn một chỗ — "
            "bạn xem lại giúp mình đoạn được đánh dấu rồi mình học lại nhé."
        ),
        "agent_understood": [],
        "cites_span_id": review[0] if review else None,
        "turn_state": TurnState.SUGGEST_REVIEW.name,
    }
