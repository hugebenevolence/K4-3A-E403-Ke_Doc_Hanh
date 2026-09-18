"""Schema output của LLM.

MODEL KHÔNG TỰ CHỐT VERDICT. Nó chỉ trả lời từng câu hỏi cụ thể, kiểm chứng
được: mỗi ý cốt lõi học viên đã nói tới chưa, và có nói trái ý đó không.
Verdict do code suy ra từ đó (xem domain/verdict.py).

Hai câu hỏi đó đều hỏi theo TỪNG Ý. Bản trước hỏi chung "có chỗ nào nói trái
nguồn không" bằng một ô văn xuôi, và nó bắn hụt đều đặn: model mô tả chỗ sai
trong `gap_summary` rồi để ô mâu thuẫn rỗng, nên một lời giảng SAI bị hạ xuống
thành "còn thiếu" — hoặc tệ hơn, thành "đã đủ" (phiên thật 5eaa59a3).

Vì sao: bản đầu để model tự chốt verdict sau khi viết gap_summary, và nó không
bao giờ cho `sufficient` — viết ra chỗ hổng xong là đã tự cam kết "còn thiếu",
kể cả khi chính nó ghi "không có chỗ thiếu lớn". Bỏ hẳn quyết định đó khỏi tay
model thì hết cả một lớp thiếu nhất quán.

THỨ TỰ FIELD LÀ CỐ Ý: liệt kê căn cứ trước, nhận định sau.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EvidenceOut(BaseModel):
    span_id: str = Field(
        description=(
            "CHÉP ĐÚNG mã đoạn đứng đầu ô nguồn, cả dấu ngoặc vuông, ví dụ "
            "[d1-slide-hackathon-p15-02]. Không tự đặt mã mới, không đánh số lại "
            "kiểu s1/s2/ý1, không viết tắt. Mã không có trong ĐOẠN NGUỒN sẽ bị "
            "loại và ý đó coi như không được nêu."
        )
    )
    quote: str = Field(description="Trích ngắn nguyên văn từ đoạn nguồn")
    key: bool = Field(
        description=(
            "Ý CHÍNH (cơ chế chính của đoạn nguồn, thiếu là chưa hiểu phần này) "
            "hay chi tiết phụ (con số ví dụ, tên riêng, nguồn trích dẫn)? "
            "Thường chỉ 1–3 ý là chính."
        )
    )
    covered_by_student: bool = Field(
        description=(
            "Học viên đã nói tới ý này chưa. Diễn đạt khác chữ mà đúng bản chất "
            "thì TÍNH LÀ RỒI — đây là dạy lại, không phải học thuộc lòng."
        )
    )
    contradicted_by_student: bool = Field(
        default=False,
        description=(
            "Học viên nói điều TRÁI với đúng ý này (không phải chỉ thiếu). "
            "Thiếu → false. Nói sang cơ chế khác mà không phủ nhận ý này → false. "
            "Chỉ true khi lời họ và ý này không thể cùng đúng."
        ),
    )


class GradeOutput(BaseModel):
    evidence: list[EvidenceOut]
    contradiction: str = Field(
        default="",
        description=(
            "Một câu mô tả chỗ học viên nói TRÁI với nguồn — chỉ điền khi đã có "
            "ý nào được đánh `contradicted_by_student`. Để RỖNG nếu học viên "
            "chỉ thiếu ý chứ không nói sai. Thiếu không phải là sai."
        ),
    )
    gap_summary: str = Field(
        default="",
        description=(
            "Chỗ hổng lớn nhất, một câu — mô tả chỗ THIẾU, không viết lời giải "
            "đúng vào đây. Để RỖNG nếu học viên đã nói đủ mọi ý."
        ),
    )


class FollowupOutput(BaseModel):
    understood: list[str] = Field(
        default_factory=list,
        description=(
            "0–3 ý ngắn học viên ĐÃ nói, diễn đạt lại gọn. Không thêm ý nào từ "
            "nguồn mà học viên chưa nói. Rỗng nếu học viên chưa nói được ý nào."
        ),
    )
    question: str = Field(description="Một câu hỏi ngược, dưới 40 từ, không lộ đáp án")
    cites_span_id: str | None = Field(
        default=None, description="Span được trích trong câu hỏi, nếu có — để frontend highlight"
    )


class LinkOpenerOutput(BaseModel):
    """Câu mở phiên nối hai trang.

    `angle` đứng TRƯỚC `question` vì cùng lý do `verdict` đứng cuối GradeOutput:
    model chọn kiểu câu hỏi xong rồi mới viết, thay vì viết một câu "liên quan
    gì" chung chung rồi gán kiểu sau.
    """

    angle: Literal["common", "contrast", "effect"] = Field(
        description=(
            "Kiểu câu hỏi hợp nhất với hai điều học viên đã nói: `common` — hỏi "
            "hai thứ giống nhau ở đâu; `contrast` — hỏi hai thứ khác nhau ở đâu "
            "(hợp khi hai khái niệm dễ bị nhầm với nhau); `effect` — hỏi cái này "
            "làm cái kia thay đổi ra sao."
        )
    )
    question: str = Field(
        description=(
            "Một câu hỏi, dưới 45 từ: đặt hai điều học viên đã giảng cạnh nhau "
            "BẰNG LỜI CỦA HỌ, rồi hỏi theo `angle`. Không tự nói ra điểm chung, "
            "chỗ khác hay tác động đó."
        )
    )


class Pronunciation(BaseModel):
    term: str = Field(description="Đúng thuật ngữ gốc được đưa, không sửa cách viết")
    sounds_like: list[str] = Field(description="2–3 cách sinh viên Việt phát âm, chữ quốc ngữ có dấu")


class PronunciationOutput(BaseModel):
    items: list[Pronunciation]
