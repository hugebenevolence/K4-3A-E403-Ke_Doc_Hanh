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
    "grader_code": ("guardrails_v1",),
    "talker": ("guardrails_v1", "persona_v2"),
    "student_persona": ("guardrails_v1", "persona_v2"),
    "opener": ("guardrails_v1", "persona_v2"),
    # Việc kỹ thuật cho bộ nhận dạng giọng nói, không nói với học viên — nhưng
    # vẫn giữ sàn an toàn: thuật ngữ lấy từ nội dung slide, không kiểm soát được.
    "pronunciation": ("guardrails_v1",),
}


@lru_cache(maxsize=64)
def load(name: str, version: str) -> str:
    path = PROMPTS_DIR / name / f"{version}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Không thấy prompt {name}/{version} tại {path}")
    return path.read_text(encoding="utf-8").strip()


def compose_system(
    name: str, version: str, spans: tuple[Span, ...] = (), code: str = ""
) -> str:
    """Ghép system prompt hoàn chỉnh. `spans` để trống với prompt không cần nguồn."""
    if name not in BASE_LAYERS:
        raise KeyError(f"Prompt {name!r} chưa khai báo lớp base trong BASE_LAYERS")

    parts = [load("_base", layer) for layer in BASE_LAYERS[name]]
    parts.append(load(name, version))

    if code:
        # Đánh số dòng để model trỏ được vào đúng dòng khi nhận xét — không có
        # số thì nó chỉ nói chung chung "vòng lặp bên trên".
        numbered = "\n".join(
            f"{i:>3} | {line}" for i, line in enumerate(code.splitlines(), 1)
        )
        parts.append(f"# CODE HỌC VIÊN ĐANG GIẢI THÍCH\n\n```\n{numbered}\n```")

    if spans:
        # span_id đã chứa sẵn ngoặc vuông ("[T06-138]"). Bọc thêm lần nữa thành
        # "[[T06-138]]" và model sẽ echo lại đúng dạng đó, rồi bộ lọc mã bịa
        # ném sạch evidence — chấm sai mà không ai thấy lỗi ở đâu.
        source = "\n\n".join(f"{s.span_id} {s.text}" for s in spans)
        label = "NHẬN ĐỊNH VỀ CODE" if code else "ĐOẠN NGUỒN"
        parts.append(f"# {label}\n\n{source}")

    return "\n\n---\n\n".join(parts)
