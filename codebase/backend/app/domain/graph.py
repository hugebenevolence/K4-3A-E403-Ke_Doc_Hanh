"""Đồ thị tri thức của MỘT học viên, gom qua mọi buổi và mọi tài liệu.

Vì sao có file này (spec §4c): học trò đang mất trí nhớ sau mỗi phiên — nó sinh
ra ngây thơ, được dạy, rồi quên sạch. Học viên không thật sự *dạy* nó, chỉ bị
nó kiểm tra, và mất đúng thứ làm học-bằng-cách-dạy hiệu quả: người ta quan tâm
tới học trò của mình hơn tới điểm của mình.

LUẬT XƯƠNG SỐNG — không có gì vào đồ thị nếu không truy ngược được về một câu
HỌC VIÊN ĐÃ NÓI. Đỉnh mang nguyên văn câu của họ; cạnh chỉ sinh ra khi chính họ
nối hai ý bằng một liên từ trong lời giảng. Không câu nào của model được phép
thành đỉnh, và không quan hệ nào được suy diễn hộ.

Đây là ranh giới làm sản phẩm này khác ChatGPT: model *biết* RLHF là gì, nhưng
**học trò của bạn thì không, cho tới khi bạn giảng**. TeachYou (CHI 2024) gọi
"confining the knowledge level of LLM agents" là bài toán khó nhất của teachable
agent; ở đây nó được giải bằng luật tất định chứ không bằng lời dặn trong prompt.

Toàn bộ file thuần domain: không SDK, không I/O, test được không cần key.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from app.domain.leak import content_terms
from app.domain.terms import extract_terms
from app.domain.verbatim import is_verbatim_paste

MIN_CLAIM_WORDS = 4
"""Câu ngắn hơn ngần này không phải một mệnh đề — "ừ", "đúng rồi", "token".

Đỉnh của đồ thị phải đọc lên được thành một ý; một từ trơ thì sau này bấm vào
chỉ thấy đúng từ đó, chẳng nhắc được người học điều gì.
"""

MIN_CONCEPT_LEN = 4
"""Độ dài tối thiểu của khoá khái niệm khi phải rơi về từ nội dung tiếng Việt."""


@dataclass(frozen=True)
class Claim:
    """Một mệnh đề học viên đã tự nói ra, và chỗ nó neo vào tài liệu.

    `concept` là khoá XUYÊN TÀI LIỆU: cùng một khái niệm giảng ở Day 1 và Day 2
    nối vào cùng một đỉnh, `span_ids` giữ cả hai chỗ. Đó là chỗ giá trị thật —
    học viên thấy được thứ học hôm trước dính vào thứ hôm sau ở đâu, thứ mà đọc
    từng slide rời không bao giờ thấy.
    """

    concept: str
    said: str  # NGUYÊN VĂN câu của học viên, không diễn đạt lại
    span_ids: tuple[str, ...] = ()
    sessions: tuple[str, ...] = ()

    @property
    def times_taught(self) -> int:
        """Số BUỔI đã giảng lại được ý này — độ đậm của đỉnh trên đồ thị."""
        return len(self.sessions)


# Liên từ tiếng Việt và quan hệ chúng nói ra. Cố ý ngắn: mỗi từ thêm vào là một
# cách nữa để sinh ra cạnh mà học viên không thật sự có ý nối.
_CONNECTIVES: tuple[tuple[str, str], ...] = (
    ("bởi vì", "cause"),
    ("tại vì", "cause"),
    ("cho nên", "cause"),
    ("do đó", "cause"),
    ("dẫn tới", "cause"),
    ("dẫn đến", "cause"),
    ("nhờ vậy", "cause"),
    ("nên", "cause"),
    ("vì", "cause"),
    ("sau đó", "sequence"),
    ("tiếp theo", "sequence"),
    ("rồi tới", "sequence"),
    ("khác với", "contrast"),
    ("ngược lại", "contrast"),
    ("không phải là", "contrast"),
)

LINK_LABEL = {"cause": "dẫn tới", "sequence": "rồi tới", "contrast": "khác với"}


@dataclass(frozen=True)
class Link:
    """Một quan hệ giữa hai mệnh đề, kèm ĐÚNG câu học viên đã dùng để nối.

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
    """Đồ thị của một học viên. Khoá theo `concept`, nên gộp xuyên tài liệu."""

    student_id: str
    claims: dict[str, Claim] = field(default_factory=dict)
    links: dict[tuple[str, str], Link] = field(default_factory=dict)

    def absorb(self, claim: Claim) -> str:
        """Thêm hoặc CẬP NHẬT một mệnh đề. Trả về việc vừa làm, để log đọc được.

        Gặp lại khái niệm cũ thì THAY lời bằng câu mới nhất chứ không chồng
        thêm: học viên dạy sai rồi tự sửa (case R02) mà đồ thị giữ cả hai thì
        nó tích lại chính hiểu lầm của họ. Span và buổi thì cộng dồn — đó mới
        là thứ cho biết ý này đã được giảng ở bao nhiêu chỗ, bao nhiêu lần.
        """
        cu = self.claims.get(claim.concept)
        if cu is None:
            self.claims[claim.concept] = claim
            return "thêm mới"

        self.claims[claim.concept] = replace(
            cu,
            said=claim.said,
            span_ids=tuple(dict.fromkeys([*cu.span_ids, *claim.span_ids])),
            sessions=tuple(dict.fromkeys([*cu.sessions, *claim.sessions])),
        )
        return "giảng lại" if claim.sessions and claim.sessions[0] not in cu.sessions else "sửa lời"

    def connect(self, link: Link) -> bool:
        """Nối hai mệnh đề. Bỏ qua nếu một đầu chưa từng được học viên nói ra."""
        if link.source == link.target:
            return False
        if link.source not in self.claims or link.target not in self.claims:
            return False
        self.links[(link.source, link.target)] = link
        return True

    def forget(self, concept: str) -> bool:
        """Bỏ một mệnh đề (và mọi cạnh của nó) khi hoá ra học viên hiểu sai.

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
        """Mọi ô tài liệu học viên đã giảng nổi ít nhất một ý."""
        return {sid for c in self.claims.values() for sid in c.span_ids}


_SENTENCE = re.compile(r"[^.!?…\n]+")

# Nhãn đứng đầu một ô slide: "Token:", "Attention:", "Bong bóng thời gian:".
_NHAN_DAU_O = re.compile(r"\s*([A-Za-z][A-Za-z0-9-]{2,})\s*:")


def sentences(text: str) -> list[str]:
    """Tách lời học viên thành câu. Lời từ máy nghe thường thiếu dấu câu, nên
    câu ở đây có thể dài — chấp nhận được, vì đỉnh cần một Ý trọn vẹn."""
    return [s.strip() for s in _SENTENCE.findall(text or "") if s.strip()]


def _concept_of(sentence: str, span_text: str) -> str | None:
    """Khoá khái niệm cho một câu, suy từ chỗ nó giao với ô nguồn.

    Ưu tiên THUẬT NGỮ của bài (token, attention, RLHF): chúng viết giống nhau ở
    mọi tài liệu nên gộp xuyên tài liệu được ngay. Câu giảng hoàn toàn bằng
    tiếng Việt thì rơi về từ nội dung chung dài nhất — vẫn tất định, vẫn gộp
    được, chỉ là khoá kém đẹp hơn.
    """
    trong_cau = content_terms(sentence)

    # Nhãn đứng đầu ô — "Token: model không đọc từ…", "Attention: mỗi từ…" —
    # chính là tên của thứ ô đó dạy, và bộ slide của khoá viết kiểu này khắp
    # nơi. Tin nó TRƯỚC tần suất: phần thân của ô nói về attention vẫn nhắc chữ
    # "token" nhiều hơn chữ "attention", nên chỉ đếm tần suất thì đỉnh của cả
    # trang attention lại mang tên token.
    nhan = _NHAN_DAU_O.match(span_text)
    if nhan and nhan.group(1).lower() in trong_cau:
        return nhan.group(1).lower()

    # `extract_terms` trả về THEO TẦN SUẤT trong chính ô nguồn, nên phần tử đầu
    # tiên là chủ đề của ô chứ không phải một từ vô tình lọt vào. Lấy theo độ
    # dài thì hỏng đúng chỗ quan trọng: ô nói về token cũng nhắc "model" vài
    # lần, hai từ dài bằng nhau, và đỉnh rơi vào "model" — một từ hub mà mọi
    # câu trong bài đều chạm, nên cả đồ thị dồn hết vào một đỉnh.
    for term in extract_terms(span_text):
        if term.lower() in trong_cau:
            return term.lower()

    chung = trong_cau & content_terms(span_text)
    # `sorted` trước khi `max`: duyệt thẳng một set thì thứ tự đổi theo
    # PYTHONHASHSEED, nên hai từ dài bằng nhau ("nhiệt"/"lượng") cho ra khoá
    # khác nhau giữa hai lần khởi động server. Mà `concept` chính là khoá gộp
    # xuyên buổi — khoá đổi nghĩa là một đỉnh tách làm đôi sau mỗi lần restart.
    du_dai = sorted(w for w in chung if len(w) >= MIN_CONCEPT_LEN)
    return max(du_dai, key=len) if du_dai else None


def claims_from_turn(
    student_text: str,
    covered: list[tuple[str, str]],
    session_id: str,
) -> tuple[list[Claim], list[tuple[str, str]]]:
    """Rút mệnh đề từ MỘT lượt giảng. Trả về (mệnh đề, lý do các câu bị loại).

    `covered` là những ô nguồn mà bộ chấm xác nhận học viên ĐÃ nói tới và KHÔNG
    nói trái — chỉ chúng mới được sinh đỉnh. Lấy cả ô chưa chạm tới thì đồ thị
    ghi nhận những thứ học viên chưa hề giảng được.

    Danh sách lý do loại trả ra ngoài để log và để script dump giải thích được
    "vì sao câu này không lên đồ thị" — không có nó thì đồ thị im lặng bỏ sót và
    không ai biết đường lần.
    """
    ket_qua: list[tuple[int, Claim]] = []
    bo_qua: list[tuple[str, str]] = []
    nguon = "\n".join(text for _, text in covered)

    # Xét chép-nguyên-văn trên CẢ LƯỢT trước, không chỉ từng câu: dán nguyên một
    # ô slide vào thì từng câu lẻ lại quá ngắn để luật câu bắt được (cần 12 từ
    # trùng liền mạch), và cả đoạn chép vẫn lọt vào đồ thị thành một chùm đỉnh.
    if nguon and is_verbatim_paste(student_text, nguon):
        return [], [(student_text, "đọc gần nguyên văn tài liệu")]

    for cau in sentences(student_text):
        if len(cau.split()) < MIN_CLAIM_WORDS:
            bo_qua.append((cau, "quá ngắn để là một mệnh đề"))
            continue
        # Đọc lại nguyên văn tài liệu thì không phải lời của họ, dù bộ chấm có
        # thấy nó phủ đủ ý đi nữa — đúng luật đang dùng ở bộ chấm.
        if nguon and is_verbatim_paste(cau, nguon):
            bo_qua.append((cau, "đọc gần nguyên văn tài liệu"))
            continue

        # Chấm theo HAI BẬC, không phải một điểm cộng. Ô có NHÃN ĐẦU khớp với
        # câu luôn thắng, vì nhãn đó là tên của chính thứ ô ấy dạy.
        #
        # Đo trên slide thật (d1 trang 15) cho thấy vì sao phải là bậc chứ không
        # phải cộng điểm: câu giảng về attention trùng 4 từ với ô tiêu đề
        # "Attention: …" nhưng trùng tới 23 từ với ô thân bài — mà ô thân bài
        # nhắc "token" nhiều nhất. Cộng vài điểm thì thân bài vẫn thắng, và cả
        # trang attention lại mọc ra một đỉnh mang tên token, nhập luôn vào đỉnh
        # token của bài trước. Hai ý khác hẳn nhau dồn thành một.
        tot_nhat: tuple[tuple[int, int], str, str] | None = None
        for span_id, span_text in covered:
            concept = _concept_of(cau, span_text)
            if concept is None:
                continue
            nhan = _NHAN_DAU_O.match(span_text)
            co_nhan = 1 if nhan and nhan.group(1).lower() == concept else 0
            diem = (co_nhan, len(content_terms(cau) & content_terms(span_text)))
            if tot_nhat is None or diem > tot_nhat[0]:
                tot_nhat = (diem, concept, span_id)

        if tot_nhat is None:
            bo_qua.append((cau, "không neo được vào ô nguồn nào đã chấm là đã nói tới"))
            continue

        _, concept, span_id = tot_nhat
        diem = tot_nhat[0][1]
        ket_qua.append(
            (diem, Claim(concept=concept, said=cau, span_ids=(span_id,), sessions=(session_id,)))
        )

    # MỘT đỉnh cho mỗi khái niệm trong một lượt, giữ câu neo chắc nhất vào nguồn.
    # Không gom thì câu sau đè câu trước chỉ vì nó đứng sau: nói "model cắt chữ
    # thành mảnh gọi là token" rồi "tiếng Việt tốn token hơn tiếng Anh" sẽ còn
    # lại đúng câu thứ hai — mất hẳn câu nói ra cơ chế.
    tot_theo_concept: dict[str, tuple[int, Claim]] = {}
    for diem, claim in ket_qua:
        cu = tot_theo_concept.get(claim.concept)
        if cu is None or diem > cu[0]:
            if cu is not None:
                bo_qua.append((cu[1].said, f"cùng khái niệm '{claim.concept}', câu khác neo chắc hơn"))
            tot_theo_concept[claim.concept] = (diem, claim)
        else:
            bo_qua.append((claim.said, f"cùng khái niệm '{claim.concept}', câu khác neo chắc hơn"))

    return [claim for _, claim in tot_theo_concept.values()], bo_qua


def links_from_turn(
    student_text: str, claims: list[Claim], session_id: str
) -> list[Link]:
    """Cạnh chỉ sinh ra từ liên từ CHÍNH HỌC VIÊN dùng.

    Hai dạng bắt được, và chỉ hai:
    1. Một câu có liên từ ở giữa — "model đoán token *nên* câu mới trôi chảy":
       vế trái và vế phải neo vào hai khái niệm khác nhau.
    2. Câu sau MỞ ĐẦU bằng liên từ — "... . *Sau đó* reward model xếp hạng":
       nối khái niệm của câu trước với khái niệm của câu này.

    Không có dạng thứ ba. Mọi cách suy ra quan hệ khác đều là hệ thống tự nối
    hộ, và một đồ thị tự nối hộ thì không còn là bản đồ hiểu biết của học viên.
    """
    theo_cau = {c.said: c.concept for c in claims}
    ra: list[Link] = []
    truoc: str | None = None

    for cau in sentences(student_text):
        concept = theo_cau.get(cau)
        thap = cau.lower()

        for tu, kind in _CONNECTIVES:
            vi_tri = thap.find(tu)
            if vi_tri <= 0:  # -1 = không có; 0 = đứng đầu câu, xử ở nhánh dưới
                continue
            trai, phai = cau[:vi_tri], cau[vi_tri + len(tu) :]
            a = next((c.concept for c in claims if c.said == cau and _co_trong(trai, c.concept)), None)
            b = next((c.concept for c in claims if _co_trong(phai, c.concept)), None)
            if a and b and a != b:
                ra.append(Link(a, b, kind, cau.strip(), session_id))
            break

        if truoc and concept and concept != truoc:
            for tu, kind in _CONNECTIVES:
                if thap.startswith(tu):
                    ra.append(Link(truoc, concept, kind, cau.strip(), session_id))
                    break

        if concept:
            truoc = concept

    return ra


def _co_trong(doan: str, concept: str) -> bool:
    return concept in content_terms(doan)
