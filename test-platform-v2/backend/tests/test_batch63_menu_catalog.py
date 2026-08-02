"""Batch 63 Slice 4 — 菜单/权限对账契约（B60-P1-002）。

要求：通知配置与目标环境必须有菜单入口；tester 角色菜单必须与 seed 目录一致，
成熟模块（缺陷/数据集/集成/Agent/性能）不可被静默隐藏。
"""

from __future__ import annotations

from app.seed import _MENUS, _TESTER_MENUS


def test_menu_catalog_contains_notify_and_environment():
    codes = [entry[0] for entry in _MENUS]
    assert "menu:notify" in codes
    assert "menu:environment" in codes


def test_menu_paths_match_frontend_routes():
    path_by_code = {entry[0]: entry[3] for entry in _MENUS}
    assert path_by_code["menu:notify"] == "/notify"
    assert path_by_code["menu:environment"] == "/environment"
    assert path_by_code["menu:defect"] == "/defect"
    assert path_by_code["menu:dataset"] == "/dataset"
    assert path_by_code["menu:integration"] == "/integration"
    assert path_by_code["menu:agent-workbench"] == "/agent-workbench"
    assert path_by_code["menu:perftest"] == "/perftest"


def test_tester_role_has_all_mature_module_menus():
    for required in [
        "menu:workbench",
        "menu:defect",
        "menu:dataset",
        "menu:integration",
        "menu:notify",
        "menu:environment",
        "menu:knowledge",
        "menu:agent-workbench",
        "menu:perftest",
    ]:
        assert required in _TESTER_MENUS, f"tester 缺少菜单 {required}"


def test_tester_menu_entries_exist_in_catalog():
    catalog = {entry[0] for entry in _MENUS}
    orphans = sorted(_TESTER_MENUS - catalog)
    assert orphans == []
