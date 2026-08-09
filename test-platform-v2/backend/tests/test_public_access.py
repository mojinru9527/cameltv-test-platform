"""Batch 128 — anonymous platform discovery contract."""
from __future__ import annotations

from app.models.rbac import Permission


def test_public_access_exposes_safe_module_catalog_without_auth(client, db_session):
    root = Permission(
        code="menu:testcase",
        name="用例服务",
        type="menu",
        path="/testcase",
        icon="ProfileOutlined",
        sort=7,
    )
    db_session.add(root)
    db_session.flush()
    db_session.add(
        Permission(
            code="menu:testcase:mindmap",
            name="用例脑图",
            type="menu",
            path="/mindmap",
            icon="ShareAltOutlined",
            sort=1,
            parent_id=root.id,
        )
    )
    db_session.commit()

    response = client.get("/api/v1/auth/public-access")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["registration_enabled"] is True
    assert data["invite_code_required"] is False
    assert data["modules"] == [
        {
            "code": "menu:testcase",
            "name": "用例服务",
            "path": "/testcase",
            "icon": "ProfileOutlined",
            "sort": 7,
            "children": [
                {
                    "code": "menu:testcase:mindmap",
                    "name": "用例脑图",
                    "path": "/mindmap",
                    "icon": "ShareAltOutlined",
                    "sort": 1,
                    "children": [],
                }
            ],
        }
    ]
    assert "permissions" not in data
    assert "projects" not in data
    assert "user" not in data
