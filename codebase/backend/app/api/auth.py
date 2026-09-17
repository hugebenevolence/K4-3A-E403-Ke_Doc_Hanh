"""Đăng nhập cho bản thử nghiệm nội bộ: danh sách thành viên cố định, không có DB.

Vì sao vẫn phải kiểm ở server chứ không chỉ chặn ở giao diện: khi deploy lên
mạng, ai biết địa chỉ WebSocket cũng gọi thẳng được — mỗi phiên gọi LLM, nhận
dạng giọng nói, đọc thành tiếng, tức là tiêu credit thật. Chặn ở giao diện chỉ
che được cái nút, không che được API.

Cố ý tối giản:
- Tài khoản đọc từ biến môi trường MEMBERS="an:matkhau1,binh:matkhau2".
- Token là "tên|hạn" ký HMAC-SHA256, không lưu phía server. Đổi AUTH_SECRET là
  mọi token cũ mất hiệu lực — đó là cách "đăng xuất tất cả".
- Không đặt MEMBERS thì tắt hẳn đăng nhập: chạy trên máy cá nhân và chạy test
  không phải đăng nhập.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

TOKEN_TTL_S = 7 * 24 * 3600
"""Một tuần: đủ cho một đợt thử nghiệm mà không bắt đăng nhập lại mỗi ngày."""


def parse_members(raw: str) -> dict[str, str]:
    """ "an:mk1, binh:mk2" -> {"an": "mk1", "binh": "mk2"}. Dòng sai định dạng bị bỏ qua."""
    members = {}
    for item in raw.split(","):
        name, sep, password = item.strip().partition(":")
        if sep and name.strip() and password:
            members[name.strip()] = password
    return members


def check_password(members: dict[str, str], name: str, password: str) -> bool:
    expected = members.get(name)
    # So sánh thời gian hằng: không để lộ độ dài khớp qua thời gian phản hồi.
    return expected is not None and hmac.compare_digest(expected, password)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str, secret: str) -> str:
    return _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())


def issue_token(name: str, secret: str, now: float | None = None) -> str:
    expires = int((now if now is not None else time.time()) + TOKEN_TTL_S)
    payload = f"{name}|{expires}"
    return f"{_b64(payload.encode())}.{_sign(payload, secret)}"


def verify_token(token: str, secret: str, now: float | None = None) -> str | None:
    """Tên thành viên nếu token hợp lệ và còn hạn, None nếu không."""
    try:
        encoded, signature = token.split(".", 1)
        payload = _unb64(encoded).decode()
        name, expires = payload.rsplit("|", 1)
    except (ValueError, UnicodeDecodeError):
        return None
    if not hmac.compare_digest(_sign(payload, secret), signature):
        return None
    if int(expires) < (now if now is not None else time.time()):
        return None
    return name


def make_secret() -> str:
    """Khoá ký dùng khi không cấu hình AUTH_SECRET — token mất hiệu lực khi khởi động lại."""
    return secrets.token_urlsafe(32)
