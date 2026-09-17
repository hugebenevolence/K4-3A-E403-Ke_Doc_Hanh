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
    ["và", "là", "của", "có", "không", "được", "cho", "với", "thì", "mà", "nên", "khi", "này", "đó", "các", "những", "một", "trong", "ra", "vào", "lên", "xuống", "về", "từ", "đến", "bị", "do", "nếu", "nhưng", "hay", "hoặc", "cũng", "đã", "sẽ", "đang", "rất", "hơn", "nhất", "bạn", "mình", "cái", "việc", "điều", "gì", "sao", "vì", "tại", "bởi", "nó", "chúng", "ta", "người"]
)


def content_terms(text: str) -> set[str]:
    """Từ mang nội dung: bỏ hư từ và âm tiết quá ngắn."""
    text = unicodedata.normalize("NFC", text).lower()
    words = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE).split()
    return {w for w in words if len(w) >= MIN_TERM_LEN and w not in _STOPWORDS}


def leaked_terms(question: str, uncovered_source: str, student_text: str) -> set[str]:
    """Từ đặc trưng của phần nguồn học viên chưa chạm tới, mà câu hỏi lại nói ra.

    Trừ đi những gì học viên đã tự nói: nhắc lại lời học viên thì không phải lộ.
    """
    return content_terms(question) & (content_terms(uncovered_source) - content_terms(student_text))


def leaks_answer(question: str, uncovered_source: str, student_text: str) -> bool:
    return len(leaked_terms(question, uncovered_source, student_text)) >= MIN_LEAKED_TERMS


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
