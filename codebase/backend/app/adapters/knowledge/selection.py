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
from app.domain.substance import MIN_SOURCE_WORDS, teachable_words
from app.domain.terms import session_vocabulary

MAX_CONCEPT_WORDS = 12
"""Trang không có tiêu đề thì lấy đầu ô đầu tiên làm tên, cắt ở ngần này chữ."""

THIN_SELECTION = (
    "Phần bạn chọn chỉ có tiêu đề, chưa có nội dung để giảng — "
    "bạn mở một trang có phần thân rồi chọn lại nhé."
)


def lesson_from_selection(deck: Deck, span_ids: Sequence[str]) -> tuple[Lesson, InMemorySpanStore]:
    """Bài học gồm đúng các ô đã chọn, xếp theo thứ tự đọc trên slide.

    Mã không có trong bộ slide thì bỏ qua — frontend có thể giữ vùng chọn từ
    một phiên bản slide cũ. Không còn ô nào thì báo lỗi chứ không chạy với nguồn
    rỗng: nguồn rỗng nghĩa là bộ chấm chấm bịa.

    Vùng quá mỏng có HAI cách chữa, theo thứ tự: nới ra cả trang, rồi mới từ
    chối. Frontend cũng nới (Learn.jsx) nhưng luật phải nằm ở đây mới đúng chỗ —
    server là nơi duy nhất biết chắc vùng đó có gì, và cả harness golden set lẫn
    một client cũ đều đi qua đây.
    """
    wanted = set(span_ids)
    chosen = [s for s in deck.spans if s.span_id in wanted]
    if not chosen:
        # Lời báo lỗi đi thẳng ra cho học viên (xem main.py), nên viết cho họ đọc.
        raise ValueError("Vùng đã chọn không còn khớp với slide — bạn chọn lại nhé.")

    page = chosen[0].page
    title = deck.titles.get(page) or ""

    def thin(spans: list) -> bool:
        return teachable_words(spans, title) < MIN_SOURCE_WORDS

    def has_figure(spans: list) -> bool:
        # Sơ đồ gần như không có chữ trong PDF nhưng vẫn là nguyên một ý để
        # giảng — ngưỡng chữ không áp cho nó. Phải xét lại SAU KHI NỚI nữa:
        # chọn mỗi dòng chú thích dưới một sơ đồ thì lúc đầu vùng chọn không có
        # hình, nới ra cả trang mới có — xét một lần ở đầu là từ chối oan đúng
        # những trang hình mà chỗ khác trong hệ vẫn cho giảng.
        return any(s.kind == "figure" for s in spans)

    # Chọn đúng một cái hình thì VẪN nới ra cả trang. Bản trước coi "có hình" là
    # đủ dày rồi dừng luôn ở đó, nên nguồn của cả buổi chỉ còn một ô ghi "Hình
    # minh hoạ" — quan sát thật trên trang "Sự ra đời của Deep Learning": câu mở
    # bài thành "trong hình minh hoạ đó, chỗ nào đang diễn tả ý chính của
    # slide?", tức là hỏi vu vơ vì không có gì để hỏi vào. Chữ quanh hình trên
    # cùng trang là thứ nói hình đó đang minh hoạ CHO ĐIỀU GÌ.
    if thin(chosen):
        chosen = [s for s in deck.spans if s.page == page]
    if thin(chosen) and not has_figure(chosen):
        # Cả trang cũng chỉ có tiêu đề: trang bìa, trang phân mục. Chạy tiếp là
        # dựng ra một phiên mà "ý cốt lõi" của nguồn chính là dòng tiêu đề, và
        # câu nào nhắc đúng chủ đề cũng chạm được nó — phiên thật 2e6d52f3 đóng
        # TAUGHT sau 9 chữ đúng theo đường đó.
        raise ValueError(THIN_SELECTION)

    concept = title or " ".join(chosen[0].text.split()[:MAX_CONCEPT_WORDS])
    lesson = Lesson(
        concept=concept,
        source_span_ids=tuple(s.span_id for s in chosen),
        vocabulary=session_vocabulary([s.text for s in chosen], deck.terms),
        kind="slide",
    )
    # Kho chứa cả bộ slide chứ không chỉ vùng đã chọn: agent có thể trỏ học
    # viên sang ô bên cạnh, và trích dẫn đó phải tra ra được.
    return lesson, InMemorySpanStore(deck.spans)
