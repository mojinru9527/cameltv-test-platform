"""v331-gap B1 — /missions 菜单入口门控契约。

背景（V30-103 查漏补缺）：seed 菜单表此前无 missions 入口，AITDE V3 flag
开启后用户只能手输 URL 进入智能测试任务。

契约：
1. menu:missions 权限行存在时（含存量库），AITDE_V3 关闭 → /missions 不出现在
   /system/menus 菜单树（与 /api/v2 的 require_aitde_v3 同源 fail-closed）；
2. AITDE_V3 开启 → /missions 出现在菜单树；
3. 开关恢复后不影响其他菜单。
"""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.models.rbac import Permission


@pytest.fixture
def restore_aitde_flag():
    original = settings.aitde_v3_enabled
    yield
    settings.aitde_v3_enabled = original


@pytest.fixture
def missions_menu_row(db_session):
    db_session.add(
        Permission(
            code="menu:missions", name="智能测试任务", type="menu",
            path="/missions", icon="SparklesOutlined", sort=24,
        )
    )
    db_session.add(
        Permission(
            code="menu:workbench", name="工作台", type="menu",
            path="/workbench", icon="DashboardOutlined", sort=1,
        )
    )
    db_session.commit()


def _menu_paths(resp) -> set[str]:
    assert resp.status_code == 200, resp.text
    payload = resp.json()["data"]
    modules = payload["modules"] if isinstance(payload, dict) else payload

    def flatten(items):
        for item in items:
            yield item.get("path") or ""
            yield from flatten(item.get("children") or [])

    return set(flatten(modules))


def test_missions_hidden_when_aitde_v3_disabled(
    client, auth_headers, missions_menu_row, restore_aitde_flag
):
    settings.aitde_v3_enabled = False
    resp = client.get("/api/v1/system/menus", headers=auth_headers)
    paths = _menu_paths(resp)
    assert "/missions" not in paths


def test_missions_visible_when_aitde_v3_enabled(
    client, auth_headers, missions_menu_row, restore_aitde_flag
):
    settings.aitde_v3_enabled = True
    resp = client.get("/api/v1/system/menus", headers=auth_headers)
    paths = _menu_paths(resp)
    assert "/missions" in paths
    # 其他入口不受 flag 切换影响
    assert "/workbench" in paths
