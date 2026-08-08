"""Batch 124 — 需求/设计稿入库端点测试（幂等 + 图片服务 + 路径逃逸防护）。"""
from __future__ import annotations

import base64

import pytest


@pytest.fixture()
def kdb():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.models  # noqa: F401
    from app.core.db import Base

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    from app.models.project import Project
    session.add(Project(id=1, code="DESIGN-INGEST-TEST", name="Design Ingest Test"))
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def kclient(kdb):
    from fastapi.testclient import TestClient

    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app
    from app.models.user import User

    def _override_db():
        yield kdb

    def _super_user():
        u = User(id=1, username="digester", password="x", nickname="DI", email="di@t.local", status=1)
        return CurrentUser(user=u, permissions=["*"], project_id=1)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _super_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _payload():
    return {"sources": [{
        "title": "预测",
        "source_ref": "预测.html",
        "text": "功能点|说明\n奖励=投入×赔率(向下取整)；单场≤1000；单日≤20000。",
        "metadata": {"page": "预测", "image_count": 1},
        "images": [{"filename": "u1.png", "base64": base64.b64encode(b"\x89PNG-fake-image-bytes").decode("ascii")}],
    }]}


def test_design_asset_import_idempotent_and_serve(kclient, monkeypatch, tmp_path):
    from app.core.config import settings
    monkeypatch.setattr(settings, "lanhu_evidence_storage_dir", str(tmp_path), raising=False)

    r1 = kclient.post("/api/v1/knowledge/design-assets/import", json=_payload())
    assert r1.status_code == 200, r1.text
    d1 = r1.json()["data"]
    assert d1["created_sources"] == 1
    assert d1["created_chunks"] == 1
    assert d1["saved_images"] == 1

    # 幂等
    r2 = kclient.post("/api/v1/knowledge/design-assets/import", json=_payload())
    assert r2.status_code == 200
    assert r2.json()["data"]["created_sources"] == 0
    assert r2.json()["data"]["skipped_sources"] == 1

    # 来源可查 + 图片服务
    rr = kclient.get("/api/v1/knowledge/sources", params={"source_type": "requirement", "page_size": 10})
    assert rr.status_code == 200
    items = rr.json()["data"]["items"]
    src = next((s for s in items if s["title"] == "预测"), None)
    assert src is not None
    detail = kclient.get(f"/api/v1/knowledge/sources/{src['id']}")
    assert detail.status_code == 200, detail.text
    meta = __import__("json").loads(detail.json()["data"].get("metadata_json") or "{}")
    img_url = meta["images"][0]
    img = kclient.get(img_url)
    assert img.status_code == 200
    assert img.content == b"\x89PNG-fake-image-bytes"

    # 路径逃逸防护
    esc = kclient.get("/api/v1/knowledge/design-assets/%d/..%%2F..%%2Fetc%%2Fpasswd" % src["id"])
    assert esc.status_code in (404, 422)
