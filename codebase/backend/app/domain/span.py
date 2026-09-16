"""Span nguồn — đơn vị grounding của cả hệ thống.

Mọi lượt chấm đều phải quy được về một span có id. Giai đoạn thoại: span là mã
đoạn transcript ([Txx-NNN]). Giai đoạn PDF: thêm page + bbox để highlight lại
đúng vùng trên slide, id vẫn giữ nguyên kiểu nên tầng trên không phải sửa.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    span_id: str  # "[T06-138]" hoặc "slide-04-p3-l12"
    text: str
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None  # toạ độ PyMuPDF (gốc trên-trái)


def normalize_span_id(raw: str) -> str:
    """Dạng so khớp: bỏ ngoặc, khoảng trắng, hoa thường.

    Model trả mã đoạn với đủ kiểu biến thể — "[T06-138]", "T06-138",
    "[[T06-138]]". Khớp cứng từng ký tự thì evidence đúng cũng bị ném đi và
    verdict tụt oan; khớp nới thế này chỉ chấp nhận khác biệt về hình thức, mã
    không có thật vẫn bị loại.
    """
    return raw.strip().strip("[]").strip().upper()
