"""Dựng sẵn dữ liệu cho tài khoản quay video demo, bằng PHIÊN THẬT (LLM thật).

    python scripts/seed_demo.py --base https://<link> --user member5 --password ...

Sau khi chạy, tài khoản có: 3 trang "đã hiểu" (Day 1 tr.14 Context, tr.19 RLHF,
Day 2 tr.16 Hệ thống AI), 1 trang "cần sửa" (Day 1 tr.13 Token) và CHƯA có mối
nối nào — để video quay được cảnh nối hai trang ngay trên bản đồ. Trang 12 (Sinh
văn bản) cố ý để trống cho cảnh giảng trực tiếp.

Không phải dữ liệu giả: mỗi dòng dưới đây đi qua đúng đường WebSocket người dùng
đi và được bộ chấm thật chấm. Khi demo phải NÓI RÕ là đã chuẩn bị trước.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.request
from urllib.parse import urlencode, urlparse

import websockets

D1, D2 = "d1-slide-hackathon", "d2-slide-hackathon"

# (bộ, trang, các lượt nói) — câu đã chạy thật và ra đúng nhãn mong muốn.
SEED = [
    (D1, 19, [
        "RLHF là bước người ta cho model viết ra nhiều câu trả lời cho cùng một câu hỏi.",
        ("Sau đó người chấm xếp hạng các câu trả lời đó, rồi model được huấn luyện để tăng xác suất những câu được "
        "điểm cao. Nhờ vậy cỗ máy đoán token dần biết nghe lời."),
    ]),
    (D1, 14, [
        ("Context là lượng chữ model nhìn thấy được trong một lần trả lời, giống như bộ nhớ tạm có giới hạn. "
        "Context càng dài thì càng tốn tiền và càng chậm, và model hay quên mất phần nằm ở giữa."),
    ]),
    (D2, 16, [
        ("Một hệ thống AI thật không chỉ có model. Context ở đây là tri thức riêng như tài liệu nghiệp vụ và hồ sơ "
        "khách hàng, nhờ vậy AI trả lời đúng với doanh nghiệp. Ngoài ra còn planning để chia nhỏ việc và tools để "
        "gọi API hay database."),
    ]),
    (D1, 13, ["Mỗi token là đúng một từ trọn vẹn. Tiếng Việt tốn ít token hơn tiếng Anh vì từ tiếng Việt ngắn hơn."]),
]


def _post(url: str, body: dict) -> dict:
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))


def _get(url: str, token: str) -> dict | list:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    return json.load(urllib.request.urlopen(req))


async def _until_turn_over(ws) -> tuple[str, str | None]:
    heard, verdict = False, None
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=120)
        if isinstance(raw, bytes):
            continue
        m = json.loads(raw)
        if m.get("type") == "state" and m.get("verdict"):
            verdict = m["verdict"]
        if m.get("type") == "transcript" and m.get("role") == "agent" and not m.get("filler"):
            heard = True
        if m.get("type") in ("session_end", "error"):
            return m["type"], verdict
        if m.get("type") == "state" and m.get("mic_open") and heard:
            return "turn", verdict


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True, help="vd https://abc.trycloudflare.com")
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    args = ap.parse_args()

    base = args.base.rstrip("/")
    ws_base = ("wss://" if urlparse(base).scheme == "https" else "ws://") + urlparse(base).netloc
    token = _post(f"{base}/api/auth/login", {"username": args.user, "password": args.password})["token"]

    for deck, page, turns in SEED:
        blocks = [b["span_id"] for b in _get(f"{base}/api/decks/{deck}/blocks", token) if b.get("page") == page]
        query = {"token": token, "deck": deck, "spans": ",".join(blocks)}
        async with websockets.connect(f"{ws_base}/api/ws/session?{urlencode(query)}", max_size=None) as ws:
            await _until_turn_over(ws)
            nhan = []
            for text in turns:
                await ws.send(json.dumps({"type": "explanation_text", "text": text}))
                stop, verdict = await _until_turn_over(ws)
                nhan.append(verdict)
                if stop != "turn":
                    break
        print(f"{deck} tr.{page}: {' → '.join(map(str, nhan))}", flush=True)

    prog = _get(f"{base}/api/progress", token)
    print("tiến độ:", prog["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
