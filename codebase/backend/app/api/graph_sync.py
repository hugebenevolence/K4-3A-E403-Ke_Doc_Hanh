"""Nối kết quả chấm một lượt vào đồ thị tri thức của học viên.

Luật nằm hết trong `domain/graph.py`; file này chỉ quyết định KHI NÀO áp luật
và ghi lại nó đã làm gì.

MỌI thứ vào đồ thị đều đi qua đây, nên đây cũng là chỗ duy nhất phải log cho ra
hồn: một đồ thị im lặng bỏ sót là thứ không ai lần ra được vì sao.
"""

from __future__ import annotations

import logging

from app.domain.graph import KnowledgeGraph, PageRef, page_claim

log = logging.getLogger(__name__)


def absorb_turn(
    graph: KnowledgeGraph,
    *,
    page: PageRef | None,
    student_texts: list[str],
    verdict: str | None,
    session_id: str,
) -> dict:
    """Cập nhật đồ thị theo một lượt vừa chấm. Trả về tóm tắt để log/để test.

    - **Đủ** → trang sáng lên, mang mọi câu học viên đã nói trong buổi.
    - **Sai** → trang tắt đi nếu trước đó đã sáng: học viên vừa cho thấy mình
      hiểu sai chính trang đó, giữ lại thì buổi sau học trò mang ra hỏi như thể
      họ đã dạy đúng.
    - **Thiếu** → không đổi gì. Chưa đủ không có nghĩa là hiểu sai, nên không
      được xoá công sức của một buổi trước; và cũng chưa đủ để sáng.

    `page` rỗng khi phiên không dựng từ một trang slide (bài demo, bài code) —
    lúc đó không có gì để neo, đồ thị đứng yên.
    """
    if page is None:
        return {}

    nhan = (verdict or "").lower()
    viec: dict[str, list[str]] = {}
    bo_qua: list[tuple[str, str]] = []

    if nhan == "sufficient":
        claim, bo_qua = page_claim(student_texts, page, session_id)
        if claim is not None:
            viec.setdefault(graph.absorb(claim), []).append(page.key)
    elif nhan == "incorrect" and graph.forget(page.key):
        viec["gỡ"] = [page.key]

    if viec:
        log.info("Đồ thị %s: %s", graph.student_id, viec)
    for cau, ly_do in bo_qua:
        log.info("Đồ thị %s bỏ qua (%s): %s", graph.student_id, ly_do, cau[:90])

    return {"đã làm": viec, "bỏ qua": bo_qua}


MAX_KNOWN = 8
"""Số trang cũ tối đa đưa xuống prompt hỏi ngược.

Đưa cả đồ thị là câu hỏi loãng ra và prompt phình theo số buổi đã học. Tám
trang đủ để bắc một cây cầu, và vẫn vừa một màn hình nếu cần đọc log.
"""


def known_claims(graph: KnowledgeGraph, span_ids: list[str]) -> list[dict]:
    """Những điều học viên ĐÃ dạy được, để học trò bắc cầu sang ở câu hỏi sau.

    Xếp trang đang giảng lên trước — câu hỏi bắc cầu chỉ sắc khi hai đầu cầu
    gần nhau. Trang của bài khác vẫn được mang theo, vì đó chính là chỗ đồ thị
    xuyên tài liệu có giá trị: nối thứ học hôm trước vào thứ đang học.
    """
    dang_giang = set(span_ids)
    xep = sorted(
        graph.claims.values(),
        key=lambda c: (0 if dang_giang & set(c.span_ids) else 1, -c.times_taught),
    )
    return [{"concept": c.title or c.concept, "said": c.said} for c in xep[:MAX_KNOWN]]
