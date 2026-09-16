"""Test tầng WebSocket thật qua TestClient.

Trước đây chỗ này chỉ được thử bằng script tay nên main.py — file có nhiều
logic điều phối nhất — ở mức 0% coverage.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.domain.session import MAX_FOLLOWUPS
from app.main import app

DONE = json.dumps({"type": "explanation_done"})


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "session_log_file", tmp_path / "s.jsonl")
    monkeypatch.setattr(settings, "profile_file", tmp_path / "p.json")
    return TestClient(app)


def _one_turn(ws) -> list:
    ws.send_bytes(b"\x00" * 100)
    ws.send_text(DONE)
    return [ws.receive() for _ in range(7)]


def test_health():
    assert TestClient(app).get("/health").json()["status"] == "ok"


def test_mot_luot_day_đay_du(client):
    with client.websocket_connect("/ws/session") as ws:
        assert ws.receive_json() == {"type": "state", "state": "STUDENT_TEACHING"}
        msgs = _one_turn(ws)

    texts = [json.loads(m["text"]) for m in msgs if m.get("text")]
    kinds = [t["type"] for t in texts]
    assert kinds.count("state") == 2  # CHECKING roi den ket qua cham
    assert any(m.get("bytes") for m in msgs), "khong co audio nao duoc gui"

    # Cau dem phai den TRUOC ket qua cham, neu khong thi mat y nghia lap cho.
    filler = next(i for i, t in enumerate(texts) if t.get("filler") is True)
    verdict = next(i for i, t in enumerate(texts) if t.get("type") == "state" and i > 0)
    assert filler < verdict


def test_ngat_ket_noi_giua_chung_khong_lam_server_no(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_json()
        ws.send_bytes(b"\x00" * 50)
    # Vao lai duoc nghia la handler da thoat sach, khong ket treo.
    with client.websocket_connect("/ws/session") as ws:
        assert ws.receive_json()["state"] == "STUDENT_TEACHING"


def test_bai_hoc_lay_tu_file_chu_khong_hardcode(client):
    body = client.get("/lesson").json()
    assert body["concept"] and body["source_span_ids"]
    assert all(s.startswith("[") for s in body["source_span_ids"])


def test_ket_phien_goi_y_dung_doan_co_that(client):
    """Hết lượt hỏi thì phải trỏ được về đoạn CÓ THẬT để xem lại — nếu bộ lọc
    mã bịa loại sạch evidence thì tính năng này im lặng chết."""
    spans = client.get("/lesson").json()["source_span_ids"]

    with client.websocket_connect("/ws/session") as ws:
        ws.receive_json()
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


def test_bam_chot_luot_ma_chua_noi_gi_thi_khong_bi_tinh_mot_luot(client, monkeypatch, tmp_path):
    """Bấm nhầm hai lần, hoặc bấm trước khi kịp nói. Chạy tiếp là tiêu mất một
    lượt hỏi ngược vì lời rỗng chắc chắn bị chấm chưa đủ — phạt oan học viên."""
    from app import main

    async def _im_lang(stt, chunks):
        return "   "

    monkeypatch.setattr(main, "_transcribe", _im_lang)

    with client.websocket_connect("/ws/session") as ws:
        ws.receive_json()
        ws.send_text(DONE)
        assert ws.receive_json()["state"] == "CHECKING"
        err = ws.receive_json()
        assert err["type"] == "error"
        assert ws.receive_json()["state"] == "STUDENT_TEACHING"

    # Không lượt nào được ghi log vì không có lượt nào thực sự chạy.
    assert not (tmp_path / "s.jsonl").exists()


def test_moi_luot_deu_duoc_ghi_log_replay_duoc(client, tmp_path):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_json()
        _one_turn(ws)
        _one_turn(ws)

    rows = [
        json.loads(line)
        for line in (tmp_path / "s.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [r["turn_index"] for r in rows] == [0, 1]
    assert rows[0]["prompt_versions"]["grader"] == "v1"
    assert rows[0]["grade"]["verdict"] == "incomplete"
    assert "first_audio" in rows[0]["latency_ms"]
