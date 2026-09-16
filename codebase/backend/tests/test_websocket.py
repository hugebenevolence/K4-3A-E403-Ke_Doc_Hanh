"""Test tầng WebSocket thật qua TestClient.

Trước đây chỗ này chỉ được thử bằng script tay nên main.py — file có nhiều
logic điều phối nhất — ở mức 0% coverage.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

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
