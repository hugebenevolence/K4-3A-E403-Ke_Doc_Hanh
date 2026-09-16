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

    def __post_init__(self) -> None:
        if not self.concept.strip():
            raise ValueError("Bài học phải có tên khái niệm")
        if not self.source_span_ids:
            raise ValueError(
                f"Bài {self.concept!r} không có span nguồn — không chấm có căn cứ được"
            )
