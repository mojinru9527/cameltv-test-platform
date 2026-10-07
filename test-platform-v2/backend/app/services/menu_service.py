"""菜单服务 —— 按用户权限点构建侧边栏菜单树。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.rbac import Permission
from app.schemas.system import MenuOut

# 平台简化批次：已删除模块的菜单 code。存量库中可能仍有这些权限行，继续过滤防止
# 指向已删除路由的菜单复活；seed.py 已不再为新库生成。
HIDDEN_MENU_CODES = {
    # (batch-212) menu:testplan：旧测试计划独立入口删除，存量库旧权限行继续过滤。
    "menu:testplan",
    # 本次简化批次硬删：报告/数据集/集成/通知/组织/DSH/智能测试任务/Durable Runtime
    "menu:report", "menu:dataset", "menu:integration", "menu:notify",
    "menu:organization", "menu:dsh_tasks", "menu:missions", "menu:runtime",
    "menu:metrics", "menu:onboarding",
    # 历史下架：专项/性能/项目入口/Agent 工作台/脑图/Playground/质量追溯
    "menu:special", "menu:perftest", "menu:project",
    "menu:agent-workbench", "menu:mindmap", "menu:playground", "menu:trace",
    # (c165-3) 知识中心子项与页内 Tab 完全同源（/knowledge?tab=xxx）
    "menu:knowledge:project", "menu:knowledge:platform",
    "menu:knowledge:graph", "menu:knowledge:artifacts",
}


def effective_hidden_menu_codes() -> set[str]:
    """硬下线菜单 ∪ 环境变量 DISABLED_MENUS 声明的软下线菜单。

    平台简化批次：通知/集成已硬删（不再需要默认软下线）；DISABLED_MENUS 保留为
    运营兜底（默认空），可对任何已上线菜单做临时软下线。
    """
    extra = {code.strip() for code in settings.disabled_menus.split(",") if code.strip()}
    return HIDDEN_MENU_CODES | extra


def menu_tree(db: Session, codes: list[str]) -> list[MenuOut]:
    perms = db.scalars(
        select(Permission).where(Permission.type == "menu").order_by(Permission.sort)
    ).all()
    is_super = "*" in codes
    hidden = effective_hidden_menu_codes()
    visible = [p for p in perms if (is_super or p.code in codes) and p.code not in hidden]

    # Build flat list first
    nodes: dict[int, MenuOut] = {}
    for p in visible:
        nodes[p.id] = MenuOut(
            code=p.code, name=p.name, path=p.path, icon=p.icon, sort=p.sort,
        )

    # Attach children to parents
    roots: list[MenuOut] = []
    for p in visible:
        if p.parent_id and p.parent_id in nodes:
            nodes[p.parent_id].children.append(nodes[p.id])
        else:
            roots.append(nodes[p.id])

    # Sort roots by sort order
    roots.sort(key=lambda m: m.sort)
    return roots
