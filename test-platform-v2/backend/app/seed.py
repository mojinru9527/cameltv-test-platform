"""首次启动初始化数据 —— 权限/角色/管理员/测试用户/默认项目（幂等）。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.project import Project, ProjectMember
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User

# 菜单权限点：(code, name, parent_code, path, icon, sort)
_MENUS = [
    ("menu:workbench", "工作台", "", "/workbench", "DashboardOutlined", 1),
    ("menu:trace", "质量追溯", "", "/trace", "NodeIndexOutlined", 2),
    ("menu:requirement", "需求文档", "", "/requirement", "FileTextOutlined", 3),
    ("menu:versionmission", "版本测试任务", "", "/version-mission", "GitBranchOutlined", 4),
    ("menu:mindmap", "用例脑图", "", "/mindmap", "ShareAltOutlined", 5),
    ("menu:testcase", "用例服务", "", "/testcase", "ProfileOutlined", 6),
    ("menu:testplan", "测试计划", "", "/testplan", "ScheduleOutlined", 7),
    ("menu:apitest", "接口测试", "", "/apitest", "ApiOutlined", 8),
    ("menu:uitest", "UI 自动化", "", "/uitest", "RobotOutlined", 9),
    ("menu:special", "专项测试", "", "/special", "PlayCircleOutlined", 10),
    ("menu:schedule", "定时任务", "", "/schedule", "ClockCircleOutlined", 11),
    ("menu:report", "报告中心", "", "/report", "BarChartOutlined", 12),
    ("menu:system", "系统管理", "", "/system", "SettingOutlined", 13),
    ("menu:project", "项目管理", "", "/project", "AppstoreOutlined", 14),
    ("menu:defect", "缺陷管理", "", "/defect", "BugOutlined", 15),
    ("menu:dataset", "测试数据集", "", "/dataset", "DatabaseOutlined", 16),
    ("menu:integration", "集成配置", "", "/integration", "LinkOutlined", 17),
    ("menu:knowledge", "知识中心", "", "/knowledge", "BrainCircuitOutlined", 18),
    ("menu:agent-workbench", "Agent 工作台", "", "/agent-workbench", "SparklesOutlined", 19),
]

# 操作权限点（按模块分组）：(code, name, type)
_ACTIONS = [
    # 系统管理 - 用户
    ("system:user:list", "查看用户", "button"),
    ("system:user:create", "新建用户", "button"),
    ("system:user:update", "编辑用户", "button"),
    ("system:user:delete", "删除用户", "button"),
    # 系统管理 - 角色
    ("system:role:list", "查看角色", "button"),
    ("system:role:create", "新建角色", "button"),
    ("system:role:update", "编辑角色", "button"),
    ("system:role:delete", "删除角色", "button"),
    # 系统管理 - 审计
    ("system:audit:list", "查看审计日志", "button"),
    # 用例服务
    ("testcase:list", "查看用例", "button"),
    ("testcase:detail", "查看用例详情", "button"),
    ("testcase:create", "新建用例", "button"),
    ("testcase:update", "编辑用例", "button"),
    ("testcase:delete", "删除用例", "button"),
    ("testcase:export", "导出用例", "button"),
    # 测试计划
    ("testplan:list", "查看计划列表", "button"),
    ("testplan:detail", "查看计划详情", "button"),
    ("testplan:create", "创建计划", "button"),
    ("testplan:update", "编辑计划", "button"),
    ("testplan:delete", "删除计划", "button"),
    ("testplan:execute", "执行用例", "button"),
    # 报告中心
    ("report:list", "查看报告", "button"),
    ("report:detail", "查看报告详情", "button"),
    ("report:create", "生成报告", "button"),
    ("report:delete", "删除报告", "button"),
    # 定时任务
    ("schedule:list", "查看定时任务", "button"),
    ("schedule:create", "创建定时任务", "button"),
    ("schedule:update", "编辑定时任务", "button"),
    ("schedule:delete", "删除定时任务", "button"),
    ("schedule:trigger", "手动触发", "button"),
    # 缺陷管理
    ("defect:list", "查看缺陷", "button"),
    ("defect:detail", "查看缺陷详情", "button"),
    ("defect:create", "新建缺陷", "button"),
    ("defect:update", "编辑缺陷", "button"),
    ("defect:delete", "删除缺陷", "button"),
    # 专项测试
    ("avcheck:list", "查看专项测试", "button"),
    ("avcheck:detail", "查看专项测试详情", "button"),
    ("avcheck:create", "创建专项测试", "button"),
    ("avcheck:delete", "删除专项测试", "button"),
    ("avcheck:trigger", "触发专项检测", "button"),
    # UI 自动化
    ("uitest:list", "查看UI自动化", "button"),
    ("uitest:detail", "查看UI自动化详情", "button"),
    ("uitest:create", "创建UI自动化任务", "button"),
    ("uitest:update", "编辑UI自动化任务", "button"),
    ("uitest:delete", "删除UI自动化任务", "button"),
    ("uitest:trigger", "触发UI自动化", "button"),
    # API 测试
    ("apitest:execute", "执行接口测试", "button"),
    ("apitest:view", "查看接口测试", "button"),
    ("apitest:import", "导入接口文档", "button"),
    ("apitest:generate", "生成接口用例", "button"),
    ("apitest:task", "管理执行任务", "button"),
    ("apitest:asset_manage", "管理接口资产", "button"),
    ("apitest:execute_prod", "执行生产环境接口测试", "button"),
    # 项目管理
    ("project:list", "查看项目列表", "button"),
    ("project:detail", "查看项目详情", "button"),
    ("project:create", "创建项目", "button"),
    ("project:update", "编辑项目", "button"),
    ("project:delete", "删除项目", "button"),
    ("project:manage", "管理项目成员", "button"),
    # 需求文档
    ("requirement:upload", "上传需求文档", "button"),
    ("requirement:generate", "AI生成用例", "button"),
    ("requirement:import", "导入生成用例", "button"),
    # 版本测试任务
    ("mission:list", "查看版本测试任务", "button"),
    ("mission:detail", "查看版本测试任务详情", "button"),
    ("mission:create", "创建版本测试任务", "button"),
    ("mission:update", "编辑版本测试任务", "button"),
    ("mission:delete", "删除版本测试任务", "button"),
    ("mission:log", "记录Agent部门日志", "button"),
    ("mission:generate", "生成版本测试资产", "button"),
    # API Token 管理 (P1-6/S3)
    ("token:list", "查看 API Token", "button"),
    ("token:manage", "管理 API Token", "button"),
    # 通知配置 (P1-6/S3)
    ("notify:list", "查看通知配置", "button"),
    ("notify:manage", "管理通知配置", "button"),
    # 用例评审 (C3)
    ("review:submit", "提交评审", "button"),
    ("review:approve", "审批评审", "button"),
    # 测试数据集 (V2.5)
    ("dataset:list", "查看数据集", "button"),
    ("dataset:create", "新建数据集", "button"),
    ("dataset:update", "编辑数据集", "button"),
    ("dataset:delete", "删除数据集", "button"),
    # 集成配置 (V2.6)
    ("integration:list", "查看集成配置", "button"),
    ("integration:manage", "管理集成配置", "button"),
    ("integration:sync", "执行同步操作", "button"),
    # 知识中心 (RAG / Agent 持续学习 — M0)
    ("knowledge:view", "查看知识中心", "button"),
    ("knowledge:manage", "管理知识源（重解析/废弃）", "button"),
    ("knowledge:approve", "审核知识与 AI 产物", "button"),
    ("agent:view", "查看 Agent 执行记录", "button"),
    ("agent:list", "查看 Agent 执行记录（已弃用，请使用 agent:view）", "button"),
    ("agent:run", "手动触发 Agent", "button"),
    ("agent:admin", "管理 Agent 配置", "button"),
    ("ai_artifact:import", "导入 AI 产物到正式资产", "button"),
    # LLM-Wiki 知识库 / 差异对比 (VNext-1..3) — 收在知识中心，不新增菜单
    ("wiki:view", "查看 Wiki 页面与差异报告", "button"),
    ("wiki:manage", "导入来源、触发编译、重试任务", "button"),
    ("wiki:approve", "审核 Wiki 页面与差异处理", "button"),
    ("wiki:diff", "发起知识库对比", "button"),
]

# 测试人员可见的菜单子集
_TESTER_ACTIONS = {
    "apitest:execute", "apitest:view", "apitest:import", "apitest:generate",
    "apitest:task", "apitest:asset_manage",
    "knowledge:view",
    "agent:view", "agent:list",
    "wiki:view", "wiki:diff",
}

_TESTER_MENUS = {
    "menu:workbench", "menu:trace", "menu:requirement", "menu:versionmission", "menu:mindmap", "menu:testcase", "menu:testplan",
    "menu:apitest", "menu:uitest", "menu:special", "menu:schedule", "menu:report",
    "menu:defect", "menu:dataset", "menu:integration", "menu:knowledge", "menu:agent-workbench",
}


def _get_or_create(db: Session, model, defaults: dict | None = None, **filters):
    obj = db.scalar(select(model).filter_by(**filters))
    if obj:
        return obj, False
    params = {**filters, **(defaults or {})}
    obj = model(**params)
    db.add(obj)
    db.flush()
    return obj, True


def run_seed() -> None:
    db: Session = None  # type: ignore[assignment]
    from app.core.db import SessionLocal

    db = SessionLocal()
    try:
        # 1) 超级权限通配点
        star, _ = _get_or_create(
            db, Permission, defaults={"name": "超级权限", "type": "api"}, code="*",
        )

        # 2) 菜单 + 操作权限点
        code_to_perm: dict[str, Permission] = {}
        for code, name, _parent, path, icon, sort in _MENUS:
            perm, _ = _get_or_create(
                db, Permission,
                defaults={"name": name, "type": "menu", "path": path, "icon": icon, "sort": sort},
                code=code,
            )
            code_to_perm[code] = perm
        for code, name, ptype in _ACTIONS:
            perm, _ = _get_or_create(
                db, Permission, defaults={"name": name, "type": ptype}, code=code,
            )
            code_to_perm[code] = perm

        # 3) 角色
        admin_role, _ = _get_or_create(
            db, Role, defaults={"name": "超级管理员", "data_scope": "global", "remark": "拥有全部权限"},
            code="admin",
        )
        tester_role, _ = _get_or_create(
            db, Role, defaults={"name": "测试人员", "data_scope": "project"}, code="tester",
        )

        # 4) 角色-权限
        _get_or_create(db, RolePermission, role_id=admin_role.id, permission_id=star.id)
        for code in _TESTER_MENUS:
            if code in code_to_perm:
                _get_or_create(db, RolePermission, role_id=tester_role.id, permission_id=code_to_perm[code].id)
        for code in _TESTER_ACTIONS:
            if code in code_to_perm:
                _get_or_create(db, RolePermission, role_id=tester_role.id, permission_id=code_to_perm[code].id)

        # 5) 管理员用户
        admin_user, created_admin = _get_or_create(
            db, User,
            defaults={
                "password": hash_password(settings.effective_admin_password),
                "nickname": "超级管理员",
                "email": "admin@cameltv.local",
                "status": 1,
                "must_change_password": settings.admin_password == "",
            },
            username=settings.admin_username,
        )

        # 5.5) 测试用户（方便验证角色隔离）
        import secrets as _secrets
        tester_pwd = settings.tester_password or _secrets.token_urlsafe(10)
        tester_user, created_tester = _get_or_create(
            db, User,
            defaults={
                "password": hash_password(tester_pwd),
                "nickname": "测试同学",
                "email": "tester@cameltv.local",
                "status": 1,
            },
            username=settings.tester_username,
        )

        # 6) 默认项目
        project, _ = _get_or_create(
            db, Project,
            defaults={"name": "CamelTv 体育平台", "description": "默认样板项目", "owner_id": admin_user.id},
            code="cameltv",
        )

        # 7) 管理员加入默认项目 + 全局管理员角色
        _get_or_create(db, ProjectMember, project_id=project.id, user_id=admin_user.id,
                       defaults={"role_id": admin_role.id})
        _get_or_create(db, UserRole, user_id=admin_user.id, role_id=admin_role.id, project_id=0)

        # 7.5) 测试用户分配 tester 角色（全局）
        _, already = _get_or_create(db, UserRole, user_id=tester_user.id, role_id=tester_role.id, project_id=0)
        if not already:
            _get_or_create(db, ProjectMember, project_id=project.id, user_id=tester_user.id,
                           defaults={"role_id": tester_role.id})

        db.commit()
        if created_admin:
            print(f"[seed] 初始管理员已创建：{settings.admin_username}")
            if settings.admin_password:
                print("[seed] 管理员使用自定义密码")
            else:
                print("[seed] 管理员使用自动生成密码（见启动日志），首次登录需修改")
        if created_tester:
            print(f"[seed] 测试用户已创建：{settings.tester_username}")
            if not settings.tester_password:
                print(f"[seed] 测试用户自动生成密码：{tester_pwd}")
    finally:
        db.close()
