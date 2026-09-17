"""Lọc lần cuối trước khi agent nói ra.

Không phải phòng xa: dự án AskTIM (Socratic tutor chạy production ở MIT) ghi
nhận đúng hai lỗi này trên người dùng thật —

  A. JSON output hỏng → cả bọc `{"...":"..."}` bị đổ thẳng ra cho học viên,
     kéo theo phần lập luận đáng lẽ phải ẩn.
  B. JSON hợp lệ, nhưng phần lời nói kết thúc bằng thẻ tool bịa ra
     (`</invoke>`, `</parameter>`) và bị đọc lên.

Ở hệ này hậu quả nặng hơn vì đầu ra đi thẳng vào TTS — thẻ rác sẽ được ĐỌC
THÀNH TIẾNG giữa buổi học.
"""

from __future__ import annotations

import json
import re

_TAG = re.compile(r"</?[A-Za-z_][\w:.\-]*\s*/?>")
_SPOKEN_FIELDS = ("question", "agent_says", "text")


def sanitize_spoken(text: str) -> str:
    """Trả về phần thực sự được nói. Không bao giờ raise — im lặng còn hơn đọc rác."""
    if not text:
        return ""

    text = _unwrap_json_envelope(text)
    text = _TAG.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def _unwrap_json_envelope(text: str) -> str:
    """Model thỉnh thoảng trả cả bọc JSON thay vì mỗi phần lời nói."""
    stripped = text.strip()
    if not stripped.startswith("{"):
        return text
    try:
        parsed = json.loads(stripped)
    except (ValueError, TypeError):
        return text
    if not isinstance(parsed, dict):
        return text
    for field in _SPOKEN_FIELDS:
        if isinstance(parsed.get(field), str):
            return parsed[field]
    return text


# Chữ HOA từ 4 ký tự: "REWARD", "MODEL", "GENERATIVE". Viết tắt thật thì không
# đọc thành tiếng được (RLHF, JSON — tối đa một nguyên âm) nên giữ nguyên.
_CAPS_WORD = re.compile(r"\b[A-Z]{4,}\b")


def _readable(word: str) -> bool:
    return sum(c in "AEIOUY" for c in word) >= 2


def tame_shouting(text: str) -> str:
    """Hạ chữ HOA của từ tiếng Anh thường về chữ thường, giữ chữ viết tắt.

    Model chép nguyên cách viết của slide ("REWARD MODEL", "GENERATIVE AI") vào
    câu nói, đọc lên như đang quát, và trái với văn phong đã quy định. Bản đầu
    chỉ bắt cụm hai từ HOA dài liền nhau nên lọt "GENERATIVE AI" (chữ đi kèm chỉ
    có 2 ký tự); giờ xét từng chữ.
    """
    return _CAPS_WORD.sub(lambda m: m.group(0).lower() if _readable(m.group(0)) else m.group(0), text)
