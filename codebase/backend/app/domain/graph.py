"""Đồ thị tri thức của MỘT học viên, gom qua mọi buổi và mọi tài liệu.

Vì sao có file này (spec §4c): học trò đang mất trí nhớ sau mỗi phiên — nó sinh
ra ngây thơ, được dạy, rồi quên sạch. Học viên không thật sự *dạy* nó, chỉ bị
nó kiểm tra, và mất đúng thứ làm học-bằng-cách-dạy hiệu quả: người ta quan tâm
tới học trò của mình hơn tới điểm của mình.

HAI LUẬT, cùng một động từ — "giảng được":
- **Đỉnh = một trang slide học viên đã giảng được.** Sáng khi bộ chấm xác nhận
  lời giảng ĐỦ, mang nguyên văn các câu họ đã nói về trang đó.
- **Cạnh = một mối nối học viên đã giảng được.** Chỉ sinh ra khi chính họ giải
  thích vì sao hai trang liên quan và bộ chấm xác nhận.

Không có gì vào đồ thị nếu không truy ngược được về một câu HỌC VIÊN đã nói.
Model biết RLHF là gì, nhưng **học trò của bạn thì không, cho tới khi bạn
giảng** — TeachYou (CHI 2024) gọi "confining the knowledge level of LLM agents"
là bài toán khó nhất của teachable agent; ở đây nó được giải bằng luật tất định.

Vì sao đỉnh là TRANG chứ không phải khái niệm rút từ câu nói: bản đầu đoán khái
niệm bằng từ chung dài nhất giữa câu và ô slide. Đo trên 7 phiên thật (18/9) nó
ra `sinh`, `luyện`, `nghiệp` — nửa chữ của "sinh văn bản", "huấn luyện", "nghiệp
vụ" — và gom mọi câu có chữ "model" vào một đỉnh, rồi câu sau ghi đè câu trước.
Học viên giảng context hai lần, cả hai được chấm đủ, mà bản đồ vẫn báo context
còn tối. Trang thì bộ chấm đã biết chắc — không có gì phải đoán.

Toàn bộ file thuần domain: không SDK, không I/O, test được không cần key.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from app.domain.leak import content_terms
from app.domain.verbatim import is_verbatim_paste

MIN_CLAIM_WORDS = 4
"""Câu ngắn hơn ngần này không phải một mệnh đề — "ừ", "đúng rồi", "token".

Đỉnh phải đọc lên được thành một ý; một từ trơ thì sau này bấm vào chỉ thấy
đúng từ đó, chẳng nhắc được người học điều gì.
"""

MAX_SENTENCES = 6
"""Số câu giữ lại cho mỗi trang, giữ những câu mới nhất.

Không ghi đè câu cũ như bản đầu: ghi đè là cách câu RLHF xoá mất câu giải thích
cơ chế ở slide 12. Nhưng cũng không giữ vô hạn — trang giảng lại mười buổi thì
khung chi tiết thành một bức tường chữ.
"""

LABEL_CHARS = 18
"""Độ dài tối đa của nhãn ngắn dưới mỗi đỉnh.

Vành tối xếp 16 đỉnh quanh khung 900px, mỗi nhãn có chừng 120px — 18 ký tự cỡ
12px là vừa khít. Tiêu đề đầy đủ vẫn hiện trong khung chi tiết.
"""


@dataclass(frozen=True)
class PageRef:
    """Một trang slide đang được giảng, đủ để neo câu nói vào nó."""

    key: str  # "d1-slide-hackathon:12" — khoá xuyên buổi của đỉnh
    title: str
    deck: str
    page: int
    span_ids: tuple[str, ...]
    text: str  # toàn bộ chữ trên trang, để lọc câu chép lại hoặc lạc đề


@dataclass(frozen=True)
class Claim:
    """Một trang học viên đã giảng được, và chính những câu họ đã nói về nó.

    Tên `Claim` giữ lại từ bản đầu để kho lưu trữ đọc được file cũ; `concept`
    giờ là khoá trang (`page_key`).
    """

    concept: str
    said: str  # câu tiêu biểu — dài nhất của lần giảng gần nhất; học trò dùng để bắc cầu
    title: str = ""
    sentences: tuple[str, ...] = ()
    span_ids: tuple[str, ...] = ()
    sessions: tuple[str, ...] = ()

    @property
    def times_taught(self) -> int:
        """Số BUỔI đã giảng được trang này — độ đậm của đỉnh trên đồ thị."""
        return len(self.sessions)


LINK_LABEL = {"explained": "bạn đã nối"}


@dataclass(frozen=True)
class Link:
    """Một mối nối giữa hai trang, kèm ĐÚNG câu học viên đã dùng để giải thích.

    Giữ `evidence` không phải để hiển thị cho đẹp: nó là bằng chứng cạnh này do
    học viên nối chứ không phải hệ thống suy ra. Mất nó thì không ai kiểm được.
    """

    source: str
    target: str
    kind: str
    evidence: str
    session: str = ""


@dataclass
class KnowledgeGraph:
    """Đồ thị của một học viên. Khoá theo trang, nên sống qua mọi buổi và mọi bộ slide."""

    student_id: str
    claims: dict[str, Claim] = field(default_factory=dict)
    links: dict[tuple[str, str], Link] = field(default_factory=dict)

    def absorb(self, claim: Claim) -> str:
        """Thêm trang, hoặc cộng lần giảng mới vào trang đã có. Trả về việc vừa làm.

        CỘNG câu chứ không thay: mỗi lần giảng lại được là thêm một cách nói về
        cùng một trang, và chính những cách nói khác nhau đó là thứ đáng đọc lại.
        """
        cu = self.claims.get(claim.concept)
        if cu is None:
            self.claims[claim.concept] = claim
            return "thêm mới"

        cau = list(dict.fromkeys([*cu.sentences, *claim.sentences]))[-MAX_SENTENCES:]
        self.claims[claim.concept] = replace(
            cu,
            said=claim.said or cu.said,
            title=claim.title or cu.title,
            sentences=tuple(cau),
            span_ids=tuple(dict.fromkeys([*cu.span_ids, *claim.span_ids])),
            sessions=tuple(dict.fromkeys([*cu.sessions, *claim.sessions])),
        )
        return "giảng lại" if claim.sessions and claim.sessions[0] not in cu.sessions else "thêm câu"

    def connect(self, link: Link) -> bool:
        """Nối hai trang. Bỏ qua nếu một đầu chưa từng được học viên giảng được."""
        if link.source == link.target:
            return False
        if link.source not in self.claims or link.target not in self.claims:
            return False
        # Một cặp chỉ có MỘT cạnh, bất kể ai đứng trước: nối A với B rồi nối B
        # với A là cùng một mối nối, vẽ hai lần thì thành đường đôi.
        khoa = tuple(sorted((link.source, link.target)))
        self.links[khoa] = link
        return True

    def forget(self, concept: str) -> bool:
        """Bỏ một trang (và mọi cạnh của nó) khi hoá ra học viên hiểu sai trang đó.

        Đồ thị được phép rỗng, nhưng không được phép SAI: một đỉnh sai nằm lại
        sẽ được học trò mang ra hỏi ở buổi sau như thể học viên đã dạy đúng.
        """
        if concept not in self.claims:
            return False
        del self.claims[concept]
        for key in [k for k in self.links if concept in k]:
            del self.links[key]
        return True

    @property
    def taught_span_ids(self) -> set[str]:
        """Mọi ô tài liệu nằm trên một trang học viên đã giảng được."""
        return {sid for c in self.claims.values() for sid in c.span_ids}


def page_key(deck: str, page: int) -> str:
    return f"{deck}:{page}"


def split_key(key: str) -> tuple[str, int]:
    """Ngược lại của `page_key`. Mã bộ slide có thể chứa dấu gạch, không chứa ':'."""
    deck, _, page = key.rpartition(":")
    return deck, int(page) if page.isdigit() else 0


_NGAT_TIEU_DE = re.compile(r"\s*[:=—–·(?]\s*|\s+-\s+")


def short_label(title: str) -> str:
    """Nhãn ngắn dưới đỉnh: phần tiêu đề trước dấu hai chấm / bằng / gạch dài.

    Bộ slide của khoá đặt tiêu đề kiểu "Context: bàn làm việc có hạn của model",
    "Sinh văn bản = đoán → nối vào câu" — phần đầu chính là tên của trang.

    Trừ khi phần đầu không có chữ nào: dòng thời gian viết "1980: Hệ chuyên
    gia", và đo trên bản đồ thật, năm trơ trọi thành năm đỉnh tên "1980",
    "2009", "2017"… không nói được trang đó dạy gì.
    """
    phan = _NGAT_TIEU_DE.split((title or "").strip(), maxsplit=1)
    dau = phan[0].strip() or (title or "").strip()
    if len(phan) > 1 and not any(ch.isalpha() for ch in dau):
        dau = f"{dau} {_NGAT_TIEU_DE.split(phan[1].strip(), maxsplit=1)[0].strip()}"
    if len(dau) <= LABEL_CHARS:
        return dau
    cat = dau[:LABEL_CHARS].rsplit(" ", 1)[0].rstrip(",;")
    return f"{cat}…"


_SENTENCE = re.compile(r"[^.!?…\n]+")


def sentences(text: str) -> list[str]:
    """Tách lời học viên thành câu. Lời từ máy nghe thường thiếu dấu câu, nên
    câu ở đây có thể dài — chấp nhận được, vì đỉnh cần một Ý trọn vẹn."""
    return [s.strip() for s in _SENTENCE.findall(text or "") if s.strip()]


def learner_sentences(
    student_texts: list[str], page_text: str
) -> tuple[list[str], list[tuple[str, str]]]:
    """Những câu của học viên đáng ghi vào trang. Trả về (câu giữ, lý do các câu bị loại).

    Danh sách lý do trả ra ngoài để log và để script dump giải thích được "vì
    sao câu này không lên đồ thị" — không có nó thì đồ thị im lặng bỏ sót và
    không ai biết đường lần.
    """
    giu: list[str] = []
    bo: list[tuple[str, str]] = []
    tu_trang = content_terms(page_text)

    for text in student_texts:
        # Xét chép-nguyên-văn trên CẢ LƯỢT trước: dán nguyên một ô slide vào thì
        # từng câu lẻ lại quá ngắn để luật câu bắt được (cần 12 từ trùng liền
        # mạch), và cả đoạn chép vẫn lọt vào thành một chùm câu.
        if page_text and is_verbatim_paste(text, page_text):
            bo.append((text, "đọc gần nguyên văn tài liệu"))
            continue
        for cau in sentences(text):
            if len(cau.split()) < MIN_CLAIM_WORDS:
                bo.append((cau, "quá ngắn để là một mệnh đề"))
            elif page_text and is_verbatim_paste(cau, page_text):
                bo.append((cau, "đọc gần nguyên văn tài liệu"))
            elif tu_trang and not (content_terms(cau) & tu_trang):
                bo.append((cau, "không nói gì tới nội dung trang này"))
            else:
                giu.append(cau)

    return list(dict.fromkeys(giu)), bo


# Cách người Việt nói "hai cái này chẳng dính gì tới nhau". Cố ý ngắn và cụ thể:
# chữ "liên quan" đứng một mình thì học viên vẫn dùng khi đang NỐI ("nó liên
# quan ở chỗ…"), nên chỉ bắt khi đi liền với một từ phủ định.
_KHONG_LIEN_QUAN = re.compile(
    r"\b(không|chả|chẳng|đâu có|ko|k)\s+(hề\s+)?(liên\s+quan|dính|dính dáng|liên hệ|"
    r"có gì chung|có gì liên quan|nối|kết nối)",
    re.IGNORECASE,
)


def denies_relation(text: str) -> bool:
    """Học viên đang khẳng định hai trang KHÔNG liên quan gì tới nhau.

    Đó là một LẬP TRƯỜNG, không phải một câu trả lời sai. Nguồn của hai trang
    hiếm khi nói chúng có liên quan hay không, nên không có gì để nó trái với.
    Đo được thật 18/9: "Tôi thấy nó chả liên quan cái chó gì cả" bị chấm là
    NÓI SAI, rồi học trò đáp bằng một câu dự phòng về "phần này" và nhắc lại
    một ý học viên nói từ buổi trước — ba chỗ hỏng liền, không chỗ nào nghe
    vào điều người ta vừa nói.
    """
    return bool(_KHONG_LIEN_QUAN.search(" ".join((text or "").split())))


def link_from_session(
    a: PageRef, b: PageRef, student_texts: list[str], session_id: str
) -> tuple[Link | None, list[tuple[str, str]]]:
    """Dựng cạnh cho hai trang VỪA ĐƯỢC CHẤM LÀ ĐÃ NỐI ĐƯỢC.

    Bằng chứng là câu của học viên chạm tới nội dung của CẢ HAI trang — đó mới
    là câu thật sự nối. Không có câu nào như vậy thì lấy câu dài nhất: bộ chấm
    đã xác nhận là họ nối được, chỉ là mối nối trải ra nhiều câu.
    """
    giu, bo = learner_sentences(student_texts, f"{a.text}\n{b.text}")
    if not giu:
        return None, bo
    tu_a, tu_b = content_terms(a.text), content_terms(b.text)
    hai_dau = [c for c in giu if content_terms(c) & tu_a and content_terms(c) & tu_b]
    return Link(a.key, b.key, "explained", max(hai_dau or giu, key=len), session_id), bo


def page_claim(
    student_texts: list[str], page: PageRef, session_id: str
) -> tuple[Claim | None, list[tuple[str, str]]]:
    """Dựng đỉnh cho một trang VỪA ĐƯỢC CHẤM LÀ ĐỦ, từ mọi lượt nói trong buổi.

    Gom cả buổi chứ không chỉ lượt cuối: lượt đầu thường là phần giảng chính,
    lượt sau là câu trả lời cho câu hỏi ngược — cả hai đều là lời giảng.
    """
    giu, bo = learner_sentences(student_texts, page.text)
    if not giu:
        return None, bo
    return (
        Claim(
            concept=page.key,
            said=max(giu, key=len),
            title=page.title,
            sentences=tuple(giu),
            span_ids=page.span_ids,
            sessions=(session_id,),
        ),
        bo,
    )
