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


def vocab_entries(terms: tuple[str, ...], generated: dict[str, list[str]] | None = None) -> list[dict]:
    """Đổi danh sách thuật ngữ sang dạng additional_vocab của Speechmatics,
    gắn thêm cách đọc cho những từ đã biết.

    `generated` là cách đọc sinh tự động (xem api/pronunciations.py); cách đọc
    gõ tay trong SOUNDS_LIKE được ưu tiên vì đã có người kiểm.
    """
    generated = generated or {}
    entries = []
    for term in terms:
        entry: dict = {"content": term}
        hints = (
            SOUNDS_LIKE.get(term)
            or SOUNDS_LIKE.get(term.lower())
            or generated.get(term.lower())
        )
        if hints:
            entry["sounds_like"] = list(hints)
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


# --- Cụm thuật ngữ nhiều từ ---------------------------------------------------
#
# Đo thật (giọng đọc tiếng Anh kiểu Việt, 8 đoạn): với từ điển chỉ gồm TỪ ĐƠN,
# mọi chỗ trượt đều là cụm — "machine learning" ra "Learning", "reward model"
# ra "report model", "generative AI" mất hẳn. Khai "reward" và "model" riêng lẻ
# không giúp bộ nhận dạng biết hai từ đó hay đi liền nhau.

MAX_PHRASE_WORDS = 3
"""Dài hơn thì gần như luôn là cả dòng chữ viết HOA của sơ đồ bị ghép lại
("ARTIFICIAL INTELLIGENCE MACHINE LEARNING DEEP LEARNING") chứ không phải thuật
ngữ. Cụm thật thì đã có ở chỗ khác trên slide dưới dạng ngắn."""

_EDGE_STOPWORDS = frozenset(["the", "a", "an", "of", "and", "or", "to", "in", "on", "for", "with", "by", "is", "are", "behind"])

_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*")


def _english_token(word: str) -> bool:
    # Import muộn: leak.py cũng là domain, tránh vòng import lúc nạp module.
    from app.domain.leak import looks_english

    return not _has_diacritic(word) and looks_english(word)


def _normalize_word(word: str) -> str:
    """Hạ chữ HOA về thường nếu không phải viết tắt ("MODEL" → "model", "RLHF" giữ).

    Bộ nhận dạng trả về ĐÚNG cách viết đã khai, nên khai "LEARNING" thì học
    viên sẽ thấy lời mình hiện ra thành chữ HOA. Tên riêng ("Claude") giữ nguyên.
    """
    from app.domain.leak import is_acronym

    return word.lower() if word.isupper() and not is_acronym(word) else word


def _normalize_phrase(words: list[str]) -> str:
    # Trong cụm thì viết thường hết trừ viết tắt: "Deep Learning" → "deep learning",
    # "Generative AI" → "generative AI".
    from app.domain.leak import is_acronym

    return " ".join(w if is_acronym(w) else w.lower() for w in words)


def extract_phrases(*texts: str) -> tuple[str, ...]:
    """Cụm 2–3 từ tiếng Anh đứng liền nhau, xếp theo tần suất giảm dần."""
    counts: Counter[str] = Counter()
    for text in texts:
        # Dấu câu, "·", "—", ":" là ranh giới cụm; chỉ khoảng trắng mới nối.
        for segment in re.split(r"[^\w\s-]|_", text):
            run: list[str] = []
            for word in segment.split() + [""]:
                if word and _TOKEN.fullmatch(word) and _english_token(word):
                    run.append(word)
                    continue
                while run and run[0].lower() in _EDGE_STOPWORDS:
                    run.pop(0)
                while run and run[-1].lower() in _EDGE_STOPWORDS:
                    run.pop()
                from app.domain.leak import is_acronym

                all_acronyms = all(is_acronym(w) for w in run)
                if 2 <= len(run) <= MAX_PHRASE_WORDS and not all_acronyms:
                    counts[_normalize_phrase(run)] += 1
                run = []
    return tuple(p for p, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


SESSION_VOCAB_LIMIT = 300
"""Speechmatics khuyên dưới 1000 mục; giữ xa ngưỡng đó để thuật ngữ của vùng
đang giảng không bị loãng giữa cả trăm từ của những slide khác."""


def session_vocabulary(selected_texts: list[str], deck_terms: tuple[str, ...]) -> tuple[str, ...]:
    """Từ điển cho một phiên: thuật ngữ của VÙNG ĐANG GIẢNG trước, cả bộ slide sau.

    Học viên đang giảng slide nào thì nói thuật ngữ của slide đó nhiều nhất.
    Xếp theo tần suất cả bộ thì "deep learning" của slide 3 nằm lẫn sau hàng
    chục từ của những slide khác.
    """
    ordered: list[str] = []
    seen: set[str] = set()
    for term in (*extract_phrases(*selected_texts), *extract_terms(*selected_texts), *deck_terms):
        words = term.split()
        term = _normalize_phrase(words) if len(words) > 1 else _normalize_word(term)
        key = term.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(term)
    return tuple(ordered[:SESSION_VOCAB_LIMIT])
