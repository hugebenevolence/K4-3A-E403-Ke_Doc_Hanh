"""Bài học: khái niệm cần dạy lại + các span nguồn để đối chiếu.

Tách ra khỏi code vì nội dung bài nằm ngoài repo (data pack không được commit),
và vì đổi bài không nên phải sửa Python.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Lesson:
    concept: str  # câu học viên sẽ được yêu cầu dạy lại
    source_span_ids: tuple[str, ...]

    # Thuật ngữ rút tự động từ chính bộ slide, mớm cho bộ nhận dạng giọng nói.
    # Không gõ tay theo từng bài: bài nào cũng có thuật ngữ riêng, gõ tay thì
    # bài mới lại quên. Xem domain/terms.py.
    vocabulary: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.concept.strip():
            raise ValueError("Bài học phải có tên khái niệm")
        if not self.source_span_ids:
            raise ValueError(
                f"Bài {self.concept!r} không có span nguồn — không chấm có căn cứ được"
            )
