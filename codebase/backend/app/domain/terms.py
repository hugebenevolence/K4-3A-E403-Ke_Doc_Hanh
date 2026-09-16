"""Rút thuật ngữ ra khỏi nội dung bài để mớm cho bộ nhận dạng giọng nói.

Vì sao cần: đo thật trên bài giảng tiếng Việt, máy nghe "temperature" thành
"template" rồi "computer cô ta", nghe "LLM" thành "Em". Thuật ngữ tiếng Anh
nằm giữa câu tiếng Việt là chỗ nhận dạng yếu nhất — mà đó lại đúng là những
từ quyết định việc chấm đúng hay sai.

Rút tự động theo từng bài thay vì gõ tay danh sách: bài nào cũng có thuật ngữ
riêng, gõ tay thì bài mới lại quên.

Mẹo nhận dạng: trong slide tiếng Việt, chữ nào KHÔNG có dấu gần như chắc chắn
là tiếng Anh hoặc tên riêng. Tiếng Việt viết đúng chính tả thì hầu hết âm tiết
đều mang dấu.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

MIN_LEN = 4
"""Từ ngắn hơn hầu hết là hư từ tiếng Anh (or, it, we) hoặc mảnh vỡ — viết tắt
toàn hoa được miễn trừ riêng."""

MAX_TERMS = 120
"""Speechmatics nhận danh sách dài, nhưng nhồi quá thì nó bắt đầu nghe nhầm
sang thuật ngữ ở chỗ không nên."""

# Chữ không dấu nhưng vẫn là tiếng Việt, hoặc từ tiếng Anh quá phổ thông để
# đáng đưa vào từ điển riêng.
_NOISE = frozenset(
    ["la", "va", "co", "cho", "khong", "the", "mot", "hai", "ba", "ta", "ma", "nao", "ra", "vao", "len", "tren", "duoi", "the", "and", "for", "with", "that", "this", "from", "you", "your", "are", "was", "has", "have", "will", "can", "cac", "tu", "khi", "hay", "noi", "lam", "nhu", "sao", "vi", "trong", "theo", "quan", "thay", "gian", "minh", "nghe", "sang", "dung", "cung", "sinh", "ban", "can", "cham", "chinh", "danh", "dan", "giao", "hoc", "hanh", "khach", "loai", "mang", "muon", "nam", "ngay", "nhan", "phan", "tang", "tham", "than", "thong", "tien", "toan", "trang", "trinh", "van", "xem", "giang", "doan", "hoan"]
)
"""Gồm cả từ tiếng Việt vốn không mang dấu ("trong", "theo", "quan") — mẹo
"không dấu thì là tiếng Anh" không bắt được nhóm này, mà mớm chúng cho bộ nhận
dạng thì vô nghĩa vì đó đã là từ tiếng Việt thường."""

# Hai lookaround "không kề chữ cái nào" là phần quan trọng nhất của regex này.
# Thiếu chúng thì "Chuy" trong "Chuyển" cũng khớp, vì "ể" không nằm trong
# [A-Za-z] — và bộ nhận dạng sẽ được mớm toàn mảnh vỡ tiếng Việt (ng, nh, ch,
# th, ph...), tức là còn hại hơn không mớm gì.
_LETTER = r"[^\W\d_]"
_WORD = re.compile(
    rf"(?<!{_LETTER})[A-Za-z][A-Za-z0-9]*(?:[-–][A-Za-z0-9]+)*(?!{_LETTER})"
)


def _has_diacritic(word: str) -> bool:
    return any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", word))


def _worth_keeping(word: str) -> bool:
    # Viết tắt ngắn vẫn giữ (AI, ML, MoE); từ thường phải đủ dài mới đáng.
    if word.isupper() and len(word) >= 2:
        return True
    return len(word) >= MIN_LEN


# Cách người Việt ĐỌC các thuật ngữ hay gặp nhất của khoá.
#
# Vì sao cần: khai mỗi mặt chữ là chưa đủ, bộ nhận dạng tiếng Việt còn cần biết
# từ đó NGHE ra sao khi người Việt đọc.
#
# CHƯA KIỂM CHỨNG ĐƯỢC. Đo A/B bằng giọng tổng hợp thì không thấy khác biệt,
# nhưng phép đo đó KHÔNG hợp lệ: giọng TTS đọc "temperature" theo phát âm
# tiếng Anh giữa câu tiếng Việt, và bộ nhận dạng bỏ hẳn từ đó thay vì nghe
# nhầm. Người Việt thật đọc là "tem-pơ-rơ-chơ" — đúng cái bảng này nhắm tới.
# Chỉ đo được bằng giọng người thật; xem lại sau khi có bản ghi buổi test.
#
# Đây là danh sách dùng chung cho cả khoá chứ không phải gõ tay theo từng bài:
# mấy từ này lặp ở mọi buổi, còn thuật ngữ riêng của từng bài vẫn rút tự động.
SOUNDS_LIKE: dict[str, list[str]] = {
    "LLM": ["eo eo em", "en lờ em", "el el em"],
    "AI": ["ây ai", "a i"],
    "API": ["ây pi ai", "a pi i"],
    "temperature": ["tem pơ rờ chơ", "tem pơ ra tua", "tem pe rơ chơ"],
    "token": ["tô ken", "tốc ken", "thô ken"],
    "prompt": ["prom", "prôm", "phrom"],
    "hallucination": ["ha lu xi nây sần", "ha lu si nê sân"],
    "context": ["con tếch", "công tét"],
    "fine-tuning": ["phai tiu ninh", "fai tuy ning"],
    "RAG": ["rát", "rắc"],
    "RLHF": ["a eo ếch ép"],
    "model": ["mô đeo", "mo đen"],
    "agent": ["ây dần", "ê dần"],
    "embedding": ["em be đinh", "am bét đinh"],
}


def vocab_entries(terms: tuple[str, ...]) -> list[dict]:
    """Đổi danh sách thuật ngữ sang dạng additional_vocab của Speechmatics,
    gắn thêm cách đọc cho những từ đã biết."""
    entries = []
    for term in terms:
        entry: dict = {"content": term}
        if hints := SOUNDS_LIKE.get(term) or SOUNDS_LIKE.get(term.lower()):
            entry["sounds_like"] = hints
        entries.append(entry)

    # Thuật ngữ có cách đọc nhưng bài này không nhắc tới vẫn nên khai: học viên
    # hay dùng từ ngoài slide khi tự diễn đạt.
    known = {t.lower() for t in terms}
    entries.extend(
        {"content": term, "sounds_like": hints}
        for term, hints in SOUNDS_LIKE.items()
        if term.lower() not in known
    )
    return entries


def extract_terms(*texts: str) -> tuple[str, ...]:
    """Thuật ngữ đáng mớm cho bộ nhận dạng, xếp theo tần suất giảm dần."""
    counts: Counter[str] = Counter()
    for text in texts:
        for match in _WORD.finditer(text):
            word = match.group()
            if _has_diacritic(word) or not _worth_keeping(word):
                continue
            if word.lower() in _NOISE:
                continue
            counts[word] += 1

    # Gộp các biến thể hoa/thường về dạng hay gặp nhất: "Token" và "token" là
    # một từ, khai hai lần chỉ làm loãng danh sách.
    canonical: dict[str, tuple[int, str]] = {}
    for word, n in counts.items():
        key = word.lower()
        best_n, best_word = canonical.get(key, (0, word))
        canonical[key] = (best_n + n, best_word if best_n >= n else word)

    ranked = sorted(canonical.values(), key=lambda pair: (-pair[0], pair[1].lower()))
    return tuple(word for _, word in ranked[:MAX_TERMS])
