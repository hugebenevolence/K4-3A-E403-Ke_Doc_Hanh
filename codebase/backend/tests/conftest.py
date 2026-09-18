"""Mọi test ghi vào thư mục tạm, không bao giờ vào var/ thật.

var/ là dữ liệu của bản đang chạy (tiến độ, bản đồ, log phiên của người thử).
Trước đây chỉ test_websocket tự đổi đường dẫn, và lại quên progress_file — mỗi
lần chạy test là thêm vài phiên giả của "demo" vào tiến độ thật.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _var_tam(tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "session_log_file", tmp_path / "s.jsonl")
    monkeypatch.setattr(settings, "profile_file", tmp_path / "p.json")
    monkeypatch.setattr(settings, "graph_file", tmp_path / "g.json")
    monkeypatch.setattr(settings, "progress_file", tmp_path / "progress.json")
