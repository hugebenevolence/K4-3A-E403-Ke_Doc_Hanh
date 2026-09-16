"""Nạp prompt theo version và ghép đúng thứ tự tận dụng prompt caching.

Prompt nằm ở file .md ngoài code: prompt-engineer sửa không cần đụng Python, và
mỗi dòng log trỏ được về đúng version đã chạy.

QUY TẮC CACHE: OpenAI chỉ cache theo PREFIX chung (≥1024 token, giữ 24h, giảm
90% phần cache). Nên `system` chứa toàn bộ phần cố định (hướng dẫn + đoạn
nguồn) và `user` chứa phần biến thiên (lời học viên). Nhét lời học viên vào
system là mất sạch giảm giá, vì prefix khác nhau ở mọi lượt gọi.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.domain.span import Span

PROMPTS_DIR = Path(__file__).parent


@lru_cache(maxsize=32)
def load(name: str, version: str) -> str:
    path = PROMPTS_DIR / name / f"{version}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Không thấy prompt {name}/{version} tại {path}")
    return path.read_text(encoding="utf-8").strip()


def compose_system(name: str, version: str, spans: tuple[Span, ...]) -> str:
    """Phần cố định: hướng dẫn + đoạn nguồn. Không nhét gì biến thiên vào đây."""
    source = "\n\n".join(f"[{s.span_id}] {s.text}" for s in spans)
    return f"{load(name, version)}\n\n## ĐOẠN NGUỒN\n\n{source}"
