"""菜单服务 —— 按用户权限点构建侧边栏菜单树。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.rbac import Permission
from app.schemas.system import MenuOut

# (batch-165) 已下线模块的菜单 code。存量库中可能仍有这些权限行，继续过滤防止
# 指向已删除路由的菜单复活；seed.py 已不再为新库生成。
# (P1b) menu:agent-workbench：入口收敛进 DSH 任务（页面删除，路由重定向 /dsh-tasks）。
# (P2a) menu:mindmap：思维导图并入用例服务「脑图视图」Tab（路由重定向 /testcase?tab=mindmap）。
# (P2b) menu:playground：Playground 并入用例服务 Tab（路由重定向 /testcase?tab=playground）。
HIDDEN_MENU_CODES = {
    "menu:special", "menu:perftest", "menu:project", "menu:organization",
    "menu:agent-workbench", "menu:mindmap", "menu:playground",
}


def effective_hidden_menu_codes() -> set[str]:
    """硬下线菜单 ∪ 环境变量 DISABLED_MENUS 声明的软下线菜单。

    软下线（默认 menu:notify / menu:integration）：通知与集成为 fail-closed 占位
    配置页（缺真实 SMTP/Webhook/Jira 端点），默认对用户隐藏；管理员可在 .env 将
    DISABLED_MENUS 置空或改为其他 code 列表后恢复。权限点本身仍保留在库中。
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
