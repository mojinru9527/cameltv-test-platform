"""Batch 116（C115-3）— 平台 XHR 采集 API 测试（mock 服务层）。"""
from __future__ import annotations

from unittest.mock import patch

def test_create_capture_task(client, auth_headers) -> None:
    client.headers.update(auth_headers)
    fake = {"id": "cap-test", "status": "running", "pages": ["/", "/q/news"], "sample_count": 0,
            "file": "", "error": "", "project_id": 1}
    with patch("app.services.xhr_capture_service.create_capture_task", return_value=fake):
        r = client.post("/api/v1/ui-tests/capture", json={"pages": ["/", "/q/news"]})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["id"] == "cap-test" and data["status"] == "running"


def test_create_capture_empty_pages_422(client, auth_headers) -> None:
    client.headers.update(auth_headers)
    r = client.post("/api/v1/ui-tests/capture", json={"pages": []})
    assert r.status_code == 422


def test_get_capture_task(client, auth_headers) -> None:
    client.headers.update(auth_headers)
    fake = {"id": "cap-done", "status": "done", "pages": ["/"], "sample_count": 12,
            "file": "/tmp/x.json", "error": ""}
    with patch("app.services.xhr_capture_service.get_task", return_value=fake):
        r = client.get("/api/v1/ui-tests/capture/cap-done")
    assert r.status_code == 200
    assert r.json()["data"]["sample_count"] == 12


def test_get_capture_missing_404(client, auth_headers) -> None:
    client.headers.update(auth_headers)
    with patch("app.services.xhr_capture_service.get_task", return_value=None):
        r = client.get("/api/v1/ui-tests/capture/cap-missing")
    assert r.status_code == 404