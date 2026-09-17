"""Kết quả chấm lời giải thích của học viên.

Thuần domain: không import SDK nào, để test được mà không cần API key.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Verdict(str, Enum):
    """Định danh tiếng Anh cho đồng nhất với TurnState và khoá JSON; phần văn
    xuôi hướng dẫn model vẫn là tiếng Việt."""

    SUFFICIENT = "sufficient"  # đủ đúng, bằng lời học viên → agent "hiểu", kết phiên
    INCOMPLETE = "incomplete"  # đúng hướng nhưng thiếu/mơ hồ → hỏi ngược đúng chỗ hổng
    INCORRECT = "incorrect"  # có phần trái nguồn → hỏi gợi mở, không sửa hộ


@dataclass(frozen=True)
class Evidence:
    """Một ý trong nguồn, kèm việc học viên đã nói tới nó hay chưa.

    span_id trỏ về span đã ingest (mã đoạn transcript, hoặc vùng slide sau này),
    nhờ đó frontend highlight lại đúng chỗ khi agent hỏi ngược.
    """

    span_id: str
    quote: str
    covered_by_student: bool
    # Ý chính (cơ chế) hay chi tiết phụ (con số, tên riêng, nguồn trích dẫn).
    key: bool = True
    # Học viên nói TRÁI với đúng ý này (không phải chỉ thiếu).
    #
    # Hỏi theo TỪNG Ý chứ không hỏi chung "có mâu thuẫn nào không": đo trên 4
    # lượt chạy golden set, ô văn xuôi chung bắn hụt đều đặn ở M01 (4/4 lượt)
    # và M02 (2/4) — model viết chỗ sai vào `gap_summary` rồi để ô mâu thuẫn
    # rỗng, và verdict tụt về "thiếu" trong khi học viên đang hiểu sai. Thấy cả
    # trên phiên thật 5eaa59a3: "LLM tìm trong dữ liệu để đưa ra câu trả lời"
    # được chấm là ĐỦ, dù gap_summary của chính nó ghi rằng cơ chế không phải vậy.
    contradicted_by_student: bool = False


@dataclass(frozen=True)
class GradeResult:
    verdict: Verdict
    evidence: tuple[Evidence, ...]
    gap_summary: str  # chỗ hổng lớn nhất — đầu vào để sinh câu hỏi ngược

    @property
    def uncovered(self) -> tuple[Evidence, ...]:
        return tuple(e for e in self.evidence if not e.covered_by_student)


def decide(
    evidence: tuple[Evidence, ...],
    contradiction: str,
    *,
    verbatim: bool,
    thin: bool = False,
) -> Verdict:
    """Suy ra verdict từ các nhận định cụ thể của model.

    Cố ý KHÔNG để model tự chốt: đo thực tế cho thấy khi được tự quyết, nó
    không bao giờ trả `sufficient` — viết ra chỗ hổng xong là đã tự cam kết
    "còn thiếu", kể cả khi chính nó ghi "không có chỗ thiếu lớn".

    Thứ tự ưu tiên: nói trái Ý CHÍNH > đọc lại nguyên văn > nói quá ít >
    còn Ý CHÍNH chưa chạm tới > nói trái một chi tiết phụ.

    Nói trái được chia hai mức, vì mức phạt phải khớp mức sai: trái một ý chính
    là hiểu sai cơ chế (INCORRECT); trái một chi tiết phụ thì chưa tới mức đó,
    nhưng vẫn không được đóng phiên là "đã hiểu" — hỏi thêm một lượt (INCOMPLETE).
    Không có nhánh thứ hai thì một câu sai về chi tiết vẫn ra "đã giảng đủ ý",
    và học viên mang chỗ sai đó về.

    `thin` = cả buổi học viên mới nói được vài chữ (xem domain/substance.py).
    Không có sàn này thì 9 chữ cũng đóng được phiên: đã xảy ra trên người dùng
    thật (phiên 2e6d52f3) và trên 4 lượt của golden set (A01, A03, N08).

    Chỉ đòi các ý CHÍNH, không đòi mọi chi tiết trên slide. Đo trên lượt chạy
    golden set đầu tiên (eval/results/): 6 trong 9 case học viên giảng đúng cơ
    chế và tự lấy ví dụ vẫn bị chấm là thiếu, vì trên slide còn con số hoặc tên
    riêng chưa được nhắc tới. Bắt đủ mọi chi tiết là bắt học thuộc slide, trái
    với định nghĩa "đã giảng được" trong spec §7 (đúng cơ chế + ví dụ của mình).
    """
    # Model không đánh dấu ý chính nào thì coi như mọi ý đều chính — thà khắt
    # khe còn hơn cho qua một lời giảng chưa tới.
    main = [e for e in evidence if e.key] or list(evidence)

    if contradiction.strip() or any(e.contradicted_by_student for e in main):
        return Verdict.INCORRECT
    if not evidence:
        # Không trích được ý nào từ nguồn nghĩa là chưa chấm được gì, không
        # phải là học viên đã nói đủ.
        return Verdict.INCOMPLETE
    if verbatim or thin:
        return Verdict.INCOMPLETE
    if any(not e.covered_by_student for e in main):
        return Verdict.INCOMPLETE
    if any(e.contradicted_by_student for e in evidence):
        # Nói trái một CHI TIẾT PHỤ thì chưa tới mức kết tội cả lời giảng là
        # sai — nhưng cũng không thể đóng phiên là "đã hiểu" rồi để họ mang
        # nguyên chỗ hiểu sai đó về. Hỏi thêm một lượt vào đúng chỗ đó.
        return Verdict.INCOMPLETE
    return Verdict.SUFFICIENT
