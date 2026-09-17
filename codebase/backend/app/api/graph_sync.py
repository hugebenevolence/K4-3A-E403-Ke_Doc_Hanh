"""Nối kết quả chấm một lượt vào đồ thị tri thức của học viên.

Đứng ở tầng api/ chứ không phải domain/ vì nó cần tra text của ô nguồn qua
`SpanStore` — một port. Luật thì nằm hết trong `domain/graph.py`; file này chỉ
lấy đúng dữ liệu và ghi lại nó đã làm gì.

MỌI thứ vào đồ thị đều đi qua đây, nên đây cũng là chỗ duy nhất phải log cho ra
hồn: một đồ thị im lặng bỏ sót là thứ không ai lần ra được vì sao.
"""

from __future__ import annotations

import logging

from app.domain.graph import KnowledgeGraph, claims_from_turn, links_from_turn
from app.ports.knowledge import SpanStore

log = logging.getLogger(__name__)


async def absorb_turn(
    graph: KnowledgeGraph,
    spans: SpanStore,
    *,
    student_text: str,
    evidence: list[dict],
    session_id: str,
) -> dict:
    """Cập nhật đồ thị theo một lượt vừa chấm. Trả về tóm tắt để log/để test.

    Chỉ ô nào bộ chấm xác nhận học viên ĐÃ nói tới và KHÔNG nói trái mới được
    sinh đỉnh. Ô bị đánh dấu nói trái thì ngược lại: khái niệm cũ ở đó bị GỠ
    khỏi đồ thị — học viên vừa chứng minh là mình hiểu sai chỗ đó, giữ lại thì
    buổi sau học trò mang ra hỏi như thể họ đã dạy đúng.
    """
    covered_ids = [
        e["span_id"]
        for e in evidence
        if e.get("covered_by_student") and not e.get("contradicted_by_student")
    ]
    wrong_ids = [e["span_id"] for e in evidence if e.get("contradicted_by_student")]

    covered = [(s.span_id, s.text) for s in await spans.get_many(covered_ids)]
    claims, bo_qua = claims_from_turn(student_text, covered, session_id)

    viec: dict[str, list[str]] = {"thêm mới": [], "giảng lại": [], "sửa lời": [], "gỡ": [], "nối": []}
    for claim in claims:
        viec[graph.absorb(claim)].append(claim.concept)
    for link in links_from_turn(student_text, claims, session_id):
        if graph.connect(link):
            viec["nối"].append(f"{link.source}→{link.target}")

    # Gỡ sau khi thêm: cùng một lượt có thể vừa dạy đúng ô này vừa nói sai ô kia.
    for span_id in wrong_ids:
        for concept, claim in list(graph.claims.items()):
            if span_id in claim.span_ids:
                graph.forget(concept)
                viec["gỡ"].append(concept)

    tom_tat = {k: v for k, v in viec.items() if v}
    if tom_tat:
        log.info("Đồ thị %s: %s", graph.student_id, tom_tat)
    for cau, ly_do in bo_qua:
        log.info("Đồ thị %s bỏ qua (%s): %s", graph.student_id, ly_do, cau[:90])

    return {"đã làm": tom_tat, "bỏ qua": bo_qua}


MAX_KNOWN = 8
"""Số mệnh đề cũ tối đa đưa xuống prompt hỏi ngược.

Đưa cả đồ thị là câu hỏi loãng ra và prompt phình theo số buổi đã học. Tám ý
gần nhất đủ để bắc một cây cầu, và vẫn vừa một màn hình nếu cần đọc log.
"""


def known_claims(graph: KnowledgeGraph, span_ids: list[str]) -> list[dict]:
    """Những điều học viên ĐÃ dạy được, để học trò bắc cầu sang ở câu hỏi sau.

    Xếp ý thuộc đúng vùng đang giảng lên trước — câu hỏi bắc cầu chỉ sắc khi hai
    đầu cầu gần nhau. Ý của bài khác vẫn được mang theo, vì đó chính là chỗ đồ
    thị xuyên tài liệu có giá trị: nối thứ học hôm trước vào thứ đang học.
    """
    dang_giang = set(span_ids)
    xep = sorted(
        graph.claims.values(),
        key=lambda c: (0 if dang_giang & set(c.span_ids) else 1, -c.times_taught),
    )
    return [{"concept": c.concept, "said": c.said} for c in xep[:MAX_KNOWN]]
