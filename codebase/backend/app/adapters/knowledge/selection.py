"""Dựng bài học từ vùng học viên tự chọn trên slide.

Trước đây bài học nằm cố định trong một file (knowledge/lesson.json), nên cả
sản phẩm chỉ giảng được đúng một chỗ của slide 20. Học viên thật thì kẹt ở chỗ
nào mở chỗ đó ra: 42% câu hỏi trong chatlog bắt đầu bằng việc bôi đen một đoạn
trên slide. Nên bài học phải dựng ra từ chính vùng họ chọn, lúc họ chọn.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.adapters.knowledge.local import InMemorySpanStore
from app.adapters.knowledge.pdf import Deck
from app.domain.lesson import Lesson

MAX_CONCEPT_WORDS = 12
"""Trang không có tiêu đề thì lấy đầu ô đầu tiên làm tên, cắt ở ngần này chữ."""


def lesson_from_selection(deck: Deck, span_ids: Sequence[str]) -> tuple[Lesson, InMemorySpanStore]:
    """Bài học gồm đúng các ô đã chọn, xếp theo thứ tự đọc trên slide.

    Mã không có trong bộ slide thì bỏ qua — frontend có thể giữ vùng chọn từ
    một phiên bản slide cũ. Không còn ô nào thì báo lỗi chứ không chạy với nguồn
    rỗng: nguồn rỗng nghĩa là bộ chấm chấm bịa.
    """
    wanted = set(span_ids)
    chosen = [s for s in deck.spans if s.span_id in wanted]
    if not chosen:
        raise ValueError("Vùng đã chọn không khớp ô nào trên slide")

    page = chosen[0].page
    concept = deck.titles.get(page) or " ".join(chosen[0].text.split()[:MAX_CONCEPT_WORDS])
    lesson = Lesson(
        concept=concept,
        source_span_ids=tuple(s.span_id for s in chosen),
        vocabulary=deck.terms,
        kind="slide",
    )
    # Kho chứa cả bộ slide chứ không chỉ vùng đã chọn: agent có thể trỏ học
    # viên sang ô bên cạnh, và trích dẫn đó phải tra ra được.
    return lesson, InMemorySpanStore(deck.spans)
