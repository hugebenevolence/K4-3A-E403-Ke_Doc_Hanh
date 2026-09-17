"""Bắt câu hỏi ngược làm lộ đáp án.

Tiêu chí "Không lộ đáp án" là 15 điểm của rubric D3, và prompt suông không giữ
được: đã quan sát thấy thật — học viên nói "trên đó lạnh hơn", agent hỏi lại
"cái lạnh đó liên quan thế nào đến ÁP SUẤT KHÍ QUYỂN", đưa luôn từ khoá học
viên đang thiếu.

Cách bắt: một câu hỏi làm lộ đáp án là câu chứa những từ đặc trưng của đoạn
nguồn mà học viên CHƯA hề nói ra. Nếu bỏ câu hỏi đi mà học viên vẫn biết phải
nói gì, tức là câu hỏi đã nói hộ.

Làm bằng luật tất định thay vì hỏi thêm một LLM nữa: không tốn token, không
dao động giữa các lượt chạy, và chạy được cả khi provider hỏng.
"""

from __future__ import annotations

import re
import unicodedata

MIN_LEAKED_TERMS = 2
"""Một từ trùng có thể là tình cờ; hai từ đặc trưng trở lên thì không."""

MIN_TERM_LEN = 3
"""Từ quá ngắn trong tiếng Việt hầu hết là hư từ, bỏ qua."""

# Hư từ tiếng Việt hay gặp — trùng những từ này không nói lên điều gì.
_STOPWORDS = frozenset(
    ["và", "là", "của", "có", "không", "được", "cho", "với", "thì", "mà", "nên", "khi", "này", "đó", "các", "những", "một", "trong", "ra", "vào", "lên", "xuống", "về", "từ", "đến", "bị", "do", "nếu", "nhưng", "hay", "hoặc", "cũng", "đã", "sẽ", "đang", "rất", "hơn", "nhất", "bạn", "mình", "cái", "việc", "điều", "gì", "sao", "vì", "tại", "bởi", "nó", "chúng", "ta", "người",
     # Từ giao tiếp mà chính vai học trò nói suốt ("mình chưa hiểu", "bạn nói
     # thế nào", "có thể"). Đo được thật: 3 trong 7 lần bộ lọc bắn là do trùng
     # đúng những chữ này — "nói", "thể", "vậy", "rồi" — chứ không lộ gì cả.
     "nói", "thể", "vậy", "rồi", "thấy", "chưa", "giúp", "hiểu", "biết", "nghĩ",
     "kiểu", "chỗ", "cách", "thế", "lại", "đâu", "nào", "cùng", "còn", "như",
     "thôi", "luôn", "đây", "kia", "nhé", "nhỉ"]
)


def content_terms(text: str) -> set[str]:
    """Từ mang nội dung: bỏ hư từ và âm tiết quá ngắn."""
    text = unicodedata.normalize("NFC", text).lower()
    words = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE).split()
    return {w for w in words if len(w) >= MIN_TERM_LEN and w not in _STOPWORDS}


def leaked_terms(
    question: str, uncovered_source: str, student_text: str, visible: str = ""
) -> set[str]:
    """Từ đặc trưng của phần nguồn học viên chưa chạm tới, mà câu hỏi lại nói ra.

    Trừ đi những gì học viên đã tự nói: nhắc lại lời học viên thì không phải lộ.
    Trừ luôn những gì đang hiện sẵn trên màn hình (`visible`, như tiêu đề slide):
    đo được thật, câu hỏi bị chặn vì chữ "bước", "thành" — nằm ngay trên tiêu đề
    "RLHF: ba bước uốn cỗ máy đoán token thành trợ lý…" mà học viên đang nhìn.
    """
    known = content_terms(student_text) | content_terms(visible)
    return content_terms(question) & (content_terms(uncovered_source) - known)


def leaks_answer(question: str, uncovered_source: str, student_text: str, visible: str = "") -> bool:
    return len(leaked_terms(question, uncovered_source, student_text, visible)) >= MIN_LEAKED_TERMS


# Dấu hiệu agent đang MÁCH cách sửa thay vì hỏi về code đang có.
#
# Với bài code, "lộ đáp án" mang hình dạng khác bài slide: không phải đọc hộ
# một câu trong nguồn, mà là gợi ý cải tiến. Quan sát thật, prompt cấm rồi mà
# model vẫn viết "tại sao vòng trong duyệt từ đầu THAY VÌ chỉ từ i+1" — câu đó
# đưa sẵn tối ưu mà học viên phải tự tìm ra.
#
# Bắt bằng cách nhận dạng lối nói KHUYÊN BẢO, vì nội dung lời khuyên thì vô số
# mà cách nói thì chỉ vài kiểu.
_PRESCRIPTIVE = (
    "thay vì",
    "lẽ ra",
    "đáng lẽ",
    "chỉ cần",
    "nên dùng",
    "tốt hơn",
    "tối ưu hơn",
    "nhanh hơn nếu",
    "i+1",
    "i + 1",
)


def suggests_fix(question: str) -> bool:
    """Câu hỏi có đang mách cách sửa không (chỉ áp cho bài code)."""
    lowered = question.lower()
    return any(marker in lowered for marker in _PRESCRIPTIVE)


def about_source(question: str, source: str) -> bool:
    """Câu hỏi có nói về chính đoạn nguồn không — ít nhất một từ nội dung chung.

    Đo được thật: nguồn chỉ là một dòng tiêu đề ("Sinh văn bản = đoán → nối vào
    câu → đoán tiếp") thì câu mở bài lại hỏi "nói rất chắc mà thông tin sai
    cùng tồn tại kiểu gì" — chép nguyên ví dụ mẫu trong prompt, về một slide
    khác hẳn. Học viên chọn slide 12 mà bị hỏi về slide 20.

    Ngưỡng một từ là cố ý thấp: câu hỏi hay thì nêu hiện tượng bằng lời khác,
    không được bắt nó trùng nhiều chữ với nguồn — trùng nhiều là trích nguyên văn.
    """
    return bool(content_terms(question) & content_terms(source))


# --- Nhận ra chữ tiếng Anh giữa câu tiếng Việt ---------------------------------
#
# Không dấu KHÔNG có nghĩa là tiếng Anh: "cho", "sai", "tin" là tiếng Việt.
# Bản đầu dựa vào dấu và bỏ nhầm một ý hoàn toàn đúng ("cộng cho câu đúng, trừ
# cho câu sai"). Nhận theo cấu trúc âm tiết thì chắc hơn: tiếng Việt không bao
# giờ có f, j, w, z, và chỉ kết thúc bằng một nhóm phụ âm cuối rất hẹp.
_VI_SYLLABLE = re.compile(
    r"^(?:ngh|ng|nh|ch|gh|gi|kh|ph|qu|th|tr|b|c|d|g|h|k|l|m|n|p|r|s|t|v|x)?"
    r"[aeiouy]{1,3}"
    r"(?:ch|nh|ng|c|m|n|p|t)?$"
)


def _plain(word: str) -> str:
    stripped = unicodedata.normalize("NFD", word.lower())
    return "".join(c for c in stripped if not unicodedata.combining(c)).replace("đ", "d")


def looks_english(word: str) -> bool:
    """Chữ không thể là một âm tiết tiếng Việt — gần như chắc là tiếng Anh."""
    return bool(word) and not _VI_SYLLABLE.match(_plain(word))


# --- Câu hỏi xác nhận: "Có phải … không?" -------------------------------------


def confirms_answer(question: str) -> bool:
    """Câu hỏi dạng "có phải X không" — đưa sẵn X để học viên gật đầu.

    Prompt ghi rõ kiểu này là SAI ("Có phải do dữ liệu huấn luyện bị thiên lệch
    không bạn?"), vậy mà đo được thật: "có phải hệ thống sinh nhiều phương án
    trả lời cho cùng một câu hay không?" — đọc hộ đúng bước học viên còn thiếu.
    Nội dung X thì vô số, nhưng lối hỏi thì chỉ có một, nên bắt theo lối hỏi.
    """
    return "có phải" in unicodedata.normalize("NFC", question).lower()
