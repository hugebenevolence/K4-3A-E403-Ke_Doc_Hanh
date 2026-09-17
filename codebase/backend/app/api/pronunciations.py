"""Cách người Việt ĐỌC thuật ngữ tiếng Anh, để bộ nhận dạng giọng nói nghe ra.

Đo thật (giọng đọc tiếng Anh kiểu Việt): không có cách đọc thì "reward model"
ra "report model" ở cả hai giọng thử. Bảng gõ tay (terms.SOUNDS_LIKE) chỉ có 14
từ, trong khi mỗi slide có thuật ngữ riêng — nên sinh tự động một lần cho mỗi
thuật ngữ, lưu lại, lần sau khỏi hỏi.

Sinh xong phải LỌC: Speechmatics chỉ nhận cách đọc viết bằng chữ của chính ngôn
ngữ đó. Một cách đọc lẫn chữ tiếng Anh ("mô del") không những vô dụng mà còn
dạy bộ nhận dạng nghe sai.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Sequence
from pathlib import Path

from app.domain.leak import looks_english
from app.domain.terms import SOUNDS_LIKE
from app.ports.llm import LLMClient, ModelTier
from app.prompts import registry
from app.prompts.schemas import PronunciationOutput

log = logging.getLogger(__name__)

PROMPT_VERSION = "v1"
BATCH = 60
MAX_HINTS = 3
MAX_SYLLABLES = 6
"""Speechmatics tự bỏ mục dài hơn 6 từ."""


def valid_hint(hint: str) -> str | None:
    """Cách đọc hợp lệ đã chuẩn hoá, hoặc None nếu có âm tiết không phải tiếng Việt."""
    words = re.sub(r"[^\w\s]", " ", hint.lower()).split()
    if not words or len(words) > MAX_SYLLABLES:
        return None
    if any(looks_english(w) for w in words):
        return None
    return " ".join(words)


class PronunciationCache:
    def __init__(self, path: Path):
        self._path = path
        try:
            self.table: dict[str, list[str]] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.table = {}

    def missing(self, terms: Sequence[str]) -> list[str]:
        known = self.table.keys() | {k.lower() for k in SOUNDS_LIKE}
        return [t for t in dict.fromkeys(terms) if t.lower() not in known]

    async def ensure(self, terms: Sequence[str], llm: LLMClient) -> int:
        """Sinh cách đọc cho những thuật ngữ chưa có. Trả về số thuật ngữ thêm được.

        Không bao giờ raise: thiếu cách đọc thì bộ nhận dạng kém đi một chút,
        còn hỏng ở đây mà làm rớt cả phiên thì tệ hơn nhiều.
        """
        todo = self.missing(terms)
        added = 0
        for start in range(0, len(todo), BATCH):
            batch = todo[start:start + BATCH]
            try:
                out = await llm.structured(
                    system=registry.compose_system("pronunciation", PROMPT_VERSION),
                    user="Thuật ngữ:\n" + "\n".join(f"- {t}" for t in batch),
                    schema=PronunciationOutput,
                    tier=ModelTier.STANDARD,
                )
            except Exception:
                log.exception("Sinh cách đọc thuật ngữ hỏng, bỏ qua lô này")
                continue
            wanted = {t.lower() for t in batch}
            for item in out.items:
                key = item.term.strip().lower()
                if key not in wanted:
                    continue
                hints = [h for h in dict.fromkeys(filter(None, map(valid_hint, item.sounds_like)))]
                if hints:
                    self.table[key] = hints[:MAX_HINTS]
                    added += 1
        if added:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self.table, ensure_ascii=False, indent=1), encoding="utf-8")
        return added
