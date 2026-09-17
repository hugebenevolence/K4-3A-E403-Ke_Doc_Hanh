"""Test tầng WebSocket thật qua TestClient.

Trước đây chỗ này chỉ được thử bằng script tay nên main.py — file có nhiều
logic điều phối nhất — ở mức 0% coverage.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.domain.session import MAX_FOLLOWUPS
from app.graph.nodes import GRADER_VERSION
from app.main import app

DONE = json.dumps({"type": "explanation_done"})


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app.config import settings

    # Ép mock bất kể .env của máy đang để gì — test không được phụ thuộc vào
    # cấu hình cá nhân, và tuyệt đối không được tự gọi API mất tiền.
    monkeypatch.setattr(settings, "use_mocks", True)
    monkeypatch.setattr(settings, "session_log_file", tmp_path / "s.jsonl")
    monkeypatch.setattr(settings, "profile_file", tmp_path / "p.json")
    return TestClient(app)


def _opening(ws) -> str:
    """Nuốt phần mở bài và trả về câu agent chào mời.

    Phiên bắt đầu bằng một câu hỏi cụ thể mời học viên dạy, chứ không phải một
    ô trống — nên message đầu tiên không còn là `state` nữa.
    """
    question = ""
    while True:
        msg = ws.receive()
        if not msg.get("text"):
            continue
        body = json.loads(msg["text"])
        if body["type"] == "transcript":
            question = body["text"]
        elif body["type"] == "state":
            assert body["state"] == "STUDENT_TEACHING"
            return question


def _one_turn(ws) -> list:
    """Chạy một lượt nói và thu hết message tới khi agent chốt câu trả lời.

    Đọc theo NỘI DUNG chứ không đếm số message: số partial thay đổi theo lời
    nói, đếm cứng là test vỡ mỗi lần đổi nhịp nhận dạng.
    """
    ws.send_bytes(b"\x00" * 100)
    ws.send_text(DONE)
    msgs = []
    while True:
        msgs.append(m := ws.receive())
        if not m.get("text"):
            continue
        body = json.loads(m["text"])
        if body["type"] == "transcript" and body.get("filler") is False:
            msgs.append(ws.receive())  # gói audio của câu chốt
            return msgs
        if body["type"] in ("session_end", "error"):
            return msgs


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_mot_luot_day_đay_du(client):
    with client.websocket_connect("/ws/session") as ws:
        assert _opening(ws), "phien phai mo bang mot cau hoi cu the"
        msgs = _one_turn(ws)

    texts = [json.loads(m["text"]) for m in msgs if m.get("text")]
    kinds = [t["type"] for t in texts]
    assert kinds.count("state") == 2  # CHECKING roi den ket qua cham
    assert any(m.get("bytes") for m in msgs), "khong co audio nao duoc gui"

    # Tien trinh that cua agent phai den TRUOC cau tra loi, de hoc vien thay no
    # dang doi chieu voi slide chu khong phai ngoi cho mot hop den.
    activity = next(i for i, t in enumerate(texts) if t["type"] == "activity")
    answer = next(
        i
        for i, t in enumerate(texts)
        if t["type"] == "transcript" and t["role"] == "agent" and t.get("filler") is False
    )
    assert activity < answer


def test_ngat_ket_noi_giua_chung_khong_lam_server_no(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_json()
        ws.send_bytes(b"\x00" * 50)
    # Vao lai duoc nghia la handler da thoat sach, khong ket treo.
    with client.websocket_connect("/ws/session") as ws:
        assert _opening(ws) is not None


def test_lesson_lay_tu_file_chu_khong_hardcode(client):
    body = client.get("/lesson").json()
    assert body["concept"] and body["spans"]
    assert all(s["span_id"].startswith("[") for s in body["spans"])


def test_ket_phien_goi_y_dung_doan_co_that(client):
    """Hết lượt hỏi thì phải trỏ được về đoạn CÓ THẬT để xem lại — nếu bộ lọc
    mã bịa loại sạch evidence thì tính năng này im lặng chết."""
    spans = [s["span_id"] for s in client.get("/lesson").json()["spans"]]

    with client.websocket_connect("/ws/session") as ws:
        _opening(ws)
        for _ in range(MAX_FOLLOWUPS + 1):
            ws.send_bytes(b"\x00" * 100)
            ws.send_text(DONE)
            while True:
                msg = ws.receive()
                if not msg.get("text"):
                    continue
                body = json.loads(msg["text"])
                if body.get("type") == "session_end":
                    assert body["outcome"] == "SUGGEST_REVIEW"
                    assert body["review_spans"], "khong goi y duoc doan nao"
                    assert set(body["review_spans"]) <= set(spans)
                    return
                if body.get("type") == "transcript" and body.get("filler") is False:
                    break


def test_bam_chot_luot_ma_chua_noi_gi_thi_khong_bi_tinh_mot_luot(client, tmp_path):
    """Bấm nhầm hai lần, hoặc bấm trước khi kịp nói. Chạy tiếp là tiêu mất một
    lượt hỏi ngược vì lời rỗng chắc chắn bị chấm chưa đủ — phạt oan học viên."""
    with client.websocket_connect("/ws/session") as ws:
        _opening(ws)
        ws.send_text(DONE)  # chốt lượt mà chưa gửi byte audio nào
        assert ws.receive_json()["state"] == "CHECKING"
        err = ws.receive_json()
        assert err["type"] == "error"
        assert ws.receive_json()["state"] == "STUDENT_TEACHING"

    # Không lượt nào được ghi log vì không có lượt nào thực sự chạy.
    assert not (tmp_path / "s.jsonl").exists()


def test_moi_luot_deu_duoc_ghi_log_replay_duoc(client, tmp_path):
    with client.websocket_connect("/ws/session") as ws:
        _opening(ws)
        _one_turn(ws)
        _one_turn(ws)

    rows = [
        json.loads(line)
        for line in (tmp_path / "s.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [r["turn_index"] for r in rows] == [0, 1]
    assert rows[0]["prompt_versions"]["grader"] == GRADER_VERSION
    assert rows[0]["grade"]["verdict"] == "incomplete"
    assert "first_audio" in rows[0]["latency_ms"]


def test_state_mang_theo_luat_mic_cua_chinh_state_do(client):
    """Ngưỡng im lặng phải đi được xuống client, không chỉ nằm trong domain.

    Luật "im lặng sau câu hỏi ngược là đang nghĩ, không phải đã nói xong" được
    CLAUDE.md gọi là load-bearing, nhưng suốt một thời gian dài nó là code chết:
    domain có thuộc tính, chỉ test gọi tới, message `state` thì chỉ mang mỗi
    tên state nên frontend không có cách nào biết mà thi hành.
    """
    states: dict[str, dict] = {}
    with client.websocket_connect("/ws/session") as ws:
        # Gom state ngay từ message đầu: câu mở bài cũng đã kèm một state rồi.
        sent = False
        for _ in range(60):
            msg = ws.receive()
            if not msg.get("text"):
                continue
            body = json.loads(msg["text"])
            if body["type"] != "state":
                continue
            states[body["state"]] = body
            if body["state"] == "STUDENT_RESPONDING":
                break
            if body["state"] == "STUDENT_TEACHING" and not sent:
                sent = True
                ws.send_bytes(b"\x00" * 100)
                ws.send_text(DONE)

    teaching = states["STUDENT_TEACHING"]
    assert teaching["mic_open"] is True
    assert teaching["silence_ms"] > 0

    # Lúc đang chấm thì mic phải đóng: không thì nó bắt luôn giọng agent qua loa.
    assert states["CHECKING"]["mic_open"] is False

    # Và ngưỡng chờ sau câu hỏi ngược phải NỚI ra so với lúc đang tự giảng.
    responding = states["STUDENT_RESPONDING"]
    assert responding["mic_open"] is True
    assert responding["silence_ms"] > teaching["silence_ms"]
