"""Nạp prompt theo version và ghép đúng thứ tự tận dụng prompt caching.

Prompt nằm ở file .md ngoài code: prompt-engineer sửa không cần đụng Python, và
mỗi dòng log trỏ được về đúng version đã chạy.

THỨ TỰ GHÉP là cố ý, theo mức độ ổn định giảm dần:

    _base/ (giống nhau mọi prompt) → prompt riêng → đoạn nguồn (theo khái niệm)

OpenAI chỉ cache theo PREFIX chung (≥1024 token, giữ 24h, giảm 90% phần cache),
nên phần dùng chung phải đứng trước. Và lời học viên KHÔNG bao giờ vào `system`
— nó biến thiên mọi lượt, nhét vào là prefix khác nhau liên tục, mất sạch cache.

Sàn an toàn định nghĩa một lần ở _base/guardrails_v1.md rồi ghép vào mọi prompt,
thay vì chép lại ở từng file — chép lại là kiểu gì cũng trôi lệch khi sửa.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.domain.span import Span

PROMPTS_DIR = Path(__file__).parent

BASE_LAYERS: dict[str, tuple[str, ...]] = {
    "grader": ("guardrails_v1",),  # chấm, không nói với ai → không cần lớp persona
    "talker": ("guardrails_v1", "persona_v1"),
    "student_persona": ("guardrails_v1", "persona_v1"),
}


@lru_cache(maxsize=64)
def load(name: str, version: str) -> str:
    path = PROMPTS_DIR / name / f"{version}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Không thấy prompt {name}/{version} tại {path}")
    return path.read_text(encoding="utf-8").strip()


def compose_system(name: str, version: str, spans: tuple[Span, ...] = ()) -> str:
    """Ghép system prompt hoàn chỉnh. `spans` để trống với prompt không cần nguồn."""
    if name not in BASE_LAYERS:
        raise KeyError(f"Prompt {name!r} chưa khai báo lớp base trong BASE_LAYERS")

    parts = [load("_base", layer) for layer in BASE_LAYERS[name]]
    parts.append(load(name, version))
    if spans:
        source = "\n\n".join(f"[{s.span_id}] {s.text}" for s in spans)
        parts.append(f"# ĐOẠN NGUỒN\n\n{source}")

    return "\n\n---\n\n".join(parts)
