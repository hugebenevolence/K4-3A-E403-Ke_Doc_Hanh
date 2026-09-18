"""Lái 7 phiên THẬT qua WebSocket (gõ chữ thay giọng nói) để kiểm bản đồ hiểu biết (spec §4c).

Đi đúng đường người dùng đi — đăng nhập, mở phiên theo vùng slide, gõ lời giảng,
nghe câu hỏi ngược — với LLM thật. Chạy vào một server RIÊNG để không làm bẩn
đồ thị của tài khoản thật:

    S=var/e2e
    MEMBERS="kgtest:kgpass123" AUTH_SECRET=e2e GRAPH_FILE=$S/graphs.json       PROFILE_FILE=$S/profiles.json SESSION_LOG_FILE=$S/sessions.jsonl       uvicorn app.main:app --port 8010
    python scripts/drive_sessions.py            # ghi kết quả vào var/e2e/

Kỳ vọng với bản đồ theo trang: 4 trang sáng (d1 tr.12, 19, 14 và d2 tr.16),
trang token không sáng (một lần chép slide, một lần giảng sai).
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

import websockets

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))
from run_golden_set import deck_of

HTTP = "http://127.0.0.1:8010/api"
WS = "ws://127.0.0.1:8010/api/ws/session"
OUT = BACKEND / "var" / "e2e"

DECKS = {"d1": deck_of("d1"), "d2": deck_of("d2")}


def page_spans(slug: str, page: int) -> list[str]:
    return [s.span_id for s in DECKS[slug].spans if s.page == page]


def span_text(slug: str, span_id: str) -> str:
    return next(s.text for s in DECKS[slug].spans if s.span_id == span_id)


SESSIONS = [
    ("S1 sinh văn bản (đủ, có liên từ)", "d1", 12, [
        ("Model sinh văn bản bằng cách đoán một token tiếp theo dựa trên xác suất. "
        "Sau đó nó nối token vừa đoán vào ngữ cảnh rồi chạy lại từ đầu để đoán token kế tiếp. "
        "Vì vậy câu trả lời được tạo ra từng mảnh một chứ không phải nghĩ ra cả câu một lúc."),
    ]),
    ("S2 token (đủ)", "d1", 13, [
        ("Model không đọc nguyên cả từ mà cắt văn bản thành các mảnh nhỏ gọi là token. "
        "Có từ là một mảnh, có từ bị cắt thành nhiều mảnh. "
        "Tiếng Việt có dấu nên thường tốn nhiều token hơn tiếng Anh, vì vậy cùng một câu mà viết tiếng Việt thì tốn tiền hơn."),
    ]),
    ("S3 RLHF (thiếu → câu hỏi bắc cầu)", "d1", 19, [
        "RLHF là bước người ta cho model viết ra nhiều câu trả lời cho cùng một câu hỏi.",
        ("Sau đó người chấm xếp hạng các câu trả lời đó, rồi model được huấn luyện để tăng xác suất những câu được điểm cao. "
        "Nhờ vậy cỗ máy đoán token dần biết nghe lời."),
    ]),
    ("S4 context Day 1", "d1", 14, [
        ("Context là lượng chữ model nhìn thấy được trong một lần trả lời, giống như bộ nhớ tạm có giới hạn. "
        "Context càng dài thì càng tốn tiền và càng chậm, và model hay quên mất phần nằm ở giữa."),
    ]),
    ("S5 context Day 2 (gộp xuyên tài liệu?)", "d2", 16, [
        ("Một hệ thống AI thật không chỉ có model. "
        "Context ở đây là tri thức riêng như tài liệu nghiệp vụ và hồ sơ khách hàng, nhờ vậy AI trả lời đúng với doanh nghiệp. "
        "Ngoài ra còn planning để chia nhỏ việc và tools để gọi API hay database."),
    ]),
    ("S6 token SAI (phải gỡ đỉnh)", "d1", 13, [
        "Mỗi token là đúng một từ trọn vẹn. Tiếng Việt tốn ít token hơn tiếng Anh vì từ tiếng Việt ngắn hơn.",
    ]),
    ("S7 dán nguyên văn slide (không được lên đồ thị)", "d1", 12, [
        span_text("d1", "[d1-slide-hackathon-p12-02]"),
    ]),
]


def login() -> str:
    body = json.dumps({"username": "kgtest", "password": "kgpass123"}).encode()
    req = urllib.request.Request(f"{HTTP}/auth/login", body, {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))["token"]


def get_graph(token: str) -> dict:
    req = urllib.request.Request(f"{HTTP}/graph", headers={"Authorization": f"Bearer {token}"})
    return json.load(urllib.request.urlopen(req))


async def until_turn_over(ws, log: list) -> str:
    """Đọc tới khi tới lượt học viên nói, hoặc phiên đóng. Trả về lý do dừng."""
    heard_agent = False
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=120)
        if isinstance(raw, bytes):
            continue
        msg = json.loads(raw)
        log.append(msg)
        kind = msg.get("type")
        if kind == "transcript" and msg.get("role") == "agent" and not msg.get("filler"):
            heard_agent = True
        if kind == "session_end":
            return "end"
        if kind == "error":
            return "error"
        if kind == "state" and msg.get("mic_open") and heard_agent:
            return "turn"


async def run_session(token: str, name: str, slug: str, page: int, turns: list[str]) -> dict:
    query = {"token": token, "deck": f"{slug}-slide-hackathon", "spans": ",".join(page_spans(slug, page)), "student_id": "kgtest"}
    rec = {"name": name, "deck": slug, "page": page, "turns": []}
    async with websockets.connect(f"{WS}?{urlencode(query)}", max_size=None) as ws:
        opening: list = []
        await until_turn_over(ws, opening)
        rec["opener"] = [m["text"] for m in opening if m.get("type") == "transcript"]
        for text in turns:
            log: list = []
            await ws.send(json.dumps({"type": "explanation_text", "text": text}))
            stop = await until_turn_over(ws, log)
            states = [m for m in log if m.get("type") == "state" and m.get("verdict")]
            rec["turns"].append({
                "said": text,
                "verdict": states[-1]["verdict"] if states else None,
                "evidence": states[-1].get("evidence") if states else None,
                "agent": [m["text"] for m in log if m.get("type") == "transcript" and m.get("role") == "agent"],
                "errors": [m.get("message") for m in log if m.get("type") == "error"],
                "stop": stop,
            })
            if stop != "turn":
                break
    return rec


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    token = login()
    records = []
    for name, slug, page, turns in SESSIONS:
        t0 = time.time()
        rec = await run_session(token, name, slug, page, turns)
        rec["seconds"] = round(time.time() - t0, 1)
        records.append(rec)
        verdicts = " → ".join(str(t["verdict"]) for t in rec["turns"])
        print(f"{name}: {verdicts} ({rec['seconds']}s)", flush=True)
    (OUT / "sessions.out.json").write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "graph.api.json").write_text(json.dumps(get_graph(token), ensure_ascii=False, indent=1), encoding="utf-8")
    print("xong")


asyncio.run(main())
