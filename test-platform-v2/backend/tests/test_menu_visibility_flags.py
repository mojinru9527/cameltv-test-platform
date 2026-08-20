"""P1a 模块可见性开关 — DISABLED_MENUS 环境配置契约。

背景：通知配置（menu:notify）与集成配置（menu:integration）缺真实
SMTP/Webhook/Jira/ELK 端点，属 fail-closed 占位配置页。平台默认对终端用户
隐藏这两个入口（侧边栏 + 访客目录），页面路由保留可直达，管理员可通过
DISABLED_MENUS 环境变量恢复。

契约：
1. 默认配置下 /system/menus 与 /auth/public-access 均不含 notify/integration；
2. DISABLED_MENUS 置空后入口恢复；
3. 开关可按需隐藏其他菜单（演示可配置性，不破坏权限数据）；
4. batch-165 硬下线菜单（special/perftest）不受开关置空影响。
"""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.models.rbac import Permission


@pytest.fixture
def restore_disabled_menus():
    original = settings.disabled_menus
    yield
    settings.disabled_menus = original


@pytest.fixture
def menu_rows(db_session):
    """插入本测试所需的菜单权限行（seed 在测试环境被禁用）。"""
    rows = [
        ("menu:workbench", "工作台", "/workbench", 1),
        ("menu:notify", "通知配置", "/notify", 19),
        ("menu:integration", "集成配置", "/integration", 18),
        ("menu:dataset", "测试数据集", "/dataset", 17),
        # batch-165 硬下线菜单：存量库仍可能有这些权限行
        ("menu:special", "专项测试", "/special", 11),
        ("menu:perftest", "性能监控", "/perftest", 22),
    ]
    for code, name, path, sort in rows:
        db_session.add(
            Permission(code=code, name=name, type="menu", path=path, icon="", sort=sort)
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


def test_default_hides_notify_and_integration(
    client, auth_headers, menu_rows, restore_disabled_menus
):
    resp = client.get("/api/v1/system/menus", headers=auth_headers)
    paths = _menu_paths(resp)
    assert "/notify" not in paths
    assert "/integration" not in paths
    assert "/workbench" in paths
    assert "/dataset" in paths

    guest = client.get("/api/v1/auth/public-access")
    guest_paths = _menu_paths(guest)
    assert "/notify" not in guest_paths
    assert "/integration" not in guest_paths
    assert "/workbench" in guest_paths


def test_empty_disabled_menus_restores_entries(
    client, auth_headers, menu_rows, restore_disabled_menus
):
    settings.disabled_menus = ""
    resp = client.get("/api/v1/system/menus", headers=auth_headers)
    paths = _menu_paths(resp)
    assert "/notify" in paths
    assert "/integration" in paths


def test_disabled_menus_is_configurable(
    client, auth_headers, menu_rows, restore_disabled_menus
):
    settings.disabled_menus = "menu:dataset"
    resp = client.get("/api/v1/system/menus", headers=auth_headers)
    paths = _menu_paths(resp)
    assert "/dataset" not in paths
    # 其他入口不受影响
    assert "/notify" in paths
    assert "/workbench" in paths


def test_hard_hidden_menus_stay_hidden(
    client, auth_headers, menu_rows, restore_disabled_menus
):
    """batch-165 硬下线菜单不受 DISABLED_MENUS 置空影响。"""
    settings.disabled_menus = ""
    resp = client.get("/api/v1/system/menus", headers=auth_headers)
    paths = _menu_paths(resp)
    assert "/special" not in paths
    assert "/perftest" not in paths
