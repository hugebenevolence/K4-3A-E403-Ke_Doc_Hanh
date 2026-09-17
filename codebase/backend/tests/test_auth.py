"""Đăng nhập cho bản thử nghiệm: đủ để người ngoài không tiêu credit của nhóm."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.api.auth import TOKEN_TTL_S, issue_token, parse_members, verify_token
from app.main import app


def test_doc_danh_sach_thanh_vien():
    assert parse_members("an:mk1, binh:mk2,hong-dinh-dang") == {"an": "mk1", "binh": "mk2"}


def test_token_dung_thi_ra_ten_sai_chu_ky_hoac_het_han_thi_khong():
    token = issue_token("an", "bi-mat", now=1000)
    assert verify_token(token, "bi-mat", now=1001) == "an"
    assert verify_token(token, "khoa-khac", now=1001) is None
    assert verify_token(token, "bi-mat", now=1000 + TOKEN_TTL_S + 1) is None
    assert verify_token("rac", "bi-mat") is None


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "use_mocks", True)
    monkeypatch.setattr(settings, "members", "an:mat-khau")
    monkeypatch.setattr(settings, "auth_secret", "bi-mat-test")
    monkeypatch.setattr(settings, "session_log_file", tmp_path / "s.jsonl")
    monkeypatch.setattr(settings, "profile_file", tmp_path / "p.json")
    return TestClient(app)


def test_dang_nhap_dung_thi_duoc_token_sai_thi_401(client):
    ok = client.post("/api/auth/login", json={"username": "an", "password": "mat-khau"})
    assert ok.status_code == 200 and ok.json()["token"]
    bad = client.post("/api/auth/login", json={"username": "an", "password": "sai"})
    assert bad.status_code == 401


def test_api_can_token_khi_da_bat_dang_nhap(client):
    assert client.get("/api/decks").status_code == 401
    token = client.post("/api/auth/login", json={"username": "an", "password": "mat-khau"}).json()["token"]
    assert client.get("/api/decks", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    # Health không cần đăng nhập — để nền tảng deploy kiểm tra service còn sống.
    assert client.get("/api/health").status_code == 200


def test_websocket_khong_co_token_thi_bi_tu_choi(client):
    """Chặn ở giao diện chỉ che được cái nút; gọi thẳng WebSocket vẫn tiêu credit."""
    with client.websocket_connect("/api/ws/session") as ws:
        msg = json.loads(ws.receive_text())
    assert msg["type"] == "error"
