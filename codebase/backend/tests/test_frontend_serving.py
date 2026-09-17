"""Backend phục vụ giao diện đã build: tải lại trang con, file tĩnh, và không lộ file ngoài."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import mount_frontend


def _client(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>app</title>", encoding="utf-8")
    (dist / "assets" / "pdf.worker.min.mjs").write_text("export {}", encoding="utf-8")
    (tmp_path / "secret.env").write_text("KEY=1", encoding="utf-8")
    app = FastAPI()
    mount_frontend(app, dist)
    return TestClient(app)


def test_deep_link_falls_back_to_index(tmp_path):
    res = _client(tmp_path).get("/learn/d1?page=3")
    assert res.status_code == 200
    assert "<title>app</title>" in res.text


def test_module_worker_is_served_as_javascript(tmp_path):
    # Trình duyệt chặn module script có MIME text/plain.
    res = _client(tmp_path).get("/assets/pdf.worker.min.mjs")
    assert res.headers["content-type"].startswith("text/javascript")


def test_unknown_api_path_is_404_not_index(tmp_path):
    assert _client(tmp_path).get("/api/nope").status_code == 404


def test_cannot_escape_dist(tmp_path):
    res = _client(tmp_path).get("/..%2Fsecret.env")
    assert "KEY=1" not in res.text


def test_no_build_means_no_route(tmp_path):
    app = FastAPI()
    mount_frontend(app, tmp_path / "missing")
    assert TestClient(app).get("/").status_code == 404
