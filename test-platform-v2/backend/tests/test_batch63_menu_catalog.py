"""Batch 63 Slice 4 — 菜单/权限对账契约（B60-P1-002）。

要求：通知配置与目标环境必须有菜单入口；tester 角色菜单必须与 seed 目录一致，
成熟模块（缺陷/数据集/集成/Agent）不可被静默隐藏。
(batch-165) 专项测试/性能监控按产品决策隐藏：菜单不再生成，入口由 menu_service 过滤。
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


def test_p1b_agent_workbench_menu_removed_from_seed():
    """(P1b 入口收敛) Agent 工作台已并入 DSH 任务：菜单种子移除，
    menu_service.HIDDEN_MENU_CODES 拦截存量库旧权限行，前端路由重定向 /dsh-tasks。"""
    from app.seed import _TESTER_ACTIONS

    codes = [entry[0] for entry in _MENUS]
    assert "menu:agent-workbench" not in codes
    assert "menu:agent-workbench" not in _TESTER_MENUS
    # 承接入口：DSH 任务菜单存在且 tester 角色经 _TESTER_ACTIONS 获得
    assert "menu:dsh_tasks" in codes
    assert "menu:dsh_tasks" in _TESTER_ACTIONS


def test_batch165_hidden_menus_removed_from_seed():
    """(batch-165) 专项测试/性能监控已从菜单种子移除，避免新库生成入口。"""
    codes = [entry[0] for entry in _MENUS]
    assert "menu:special" not in codes
    assert "menu:perftest" not in codes
    assert "menu:special" not in _TESTER_MENUS
    assert "menu:perftest" not in _TESTER_MENUS


def test_c1652_project_organization_menus_removed_from_seed():
    """(C165-2) 项目管理/组织管理已收敛到 我的项目，避免新库生成冗余入口。"""
    codes = [entry[0] for entry in _MENUS]
    assert "menu:project" not in codes
    assert "menu:organization" not in codes
    assert "menu:project" not in _TESTER_MENUS
    assert "menu:organization" not in _TESTER_MENUS
    assert "menu:myproject" in codes


def test_tester_role_has_all_mature_module_menus():
    for required in [
        "menu:workbench",
        "menu:defect",
        "menu:dataset",
        "menu:integration",
        "menu:notify",
        "menu:environment",
        "menu:knowledge",
    ]:
        assert required in _TESTER_MENUS, f"tester 缺少菜单 {required}"


def test_tester_menu_entries_exist_in_catalog():
    catalog = {entry[0] for entry in _MENUS}
    orphans = sorted(_TESTER_MENUS - catalog)
    assert orphans == []
