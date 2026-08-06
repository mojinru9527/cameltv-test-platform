"""首次启动初始化数据 —— 权限/角色/管理员/测试用户/默认项目（幂等）。"""
from __future__ import annotations

import secrets as _secrets

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
    ("menu:versionmission", "版本测试任务", "", "/release-bundles", "GitBranchOutlined", 4),
    # ── 知识中心（独立分组）──
    ("menu:knowledge", "知识中心", "", "/knowledge", "BrainCircuitOutlined", 5),
    ("menu:knowledge:project", "项目知识", "menu:knowledge", "/knowledge?tab=project", "FolderOpenOutlined", 1),
    ("menu:knowledge:platform", "平台研发", "menu:knowledge", "/knowledge?tab=platform", "SparklesOutlined", 2),
    ("menu:knowledge:graph", "知识图谱", "menu:knowledge", "/knowledge?tab=graph", "GitBranchOutlined", 3),
    ("menu:knowledge:artifacts", "AI审核台", "menu:knowledge", "/knowledge?tab=artifacts", "FileTextOutlined", 4),
    # ── 其余菜单 ──
    ("menu:mindmap", "用例脑图", "", "/mindmap", "ShareAltOutlined", 6),
    ("menu:testcase", "用例服务", "", "/testcase", "ProfileOutlined", 7),
    ("menu:testplan", "测试计划", "", "/testplan", "ScheduleOutlined", 8),
    ("menu:apitest", "接口测试", "", "/apitest", "ApiOutlined", 9),
    ("menu:uitest", "UI 自动化", "", "/uitest", "RobotOutlined", 10),
    ("menu:playground", "Playground", "", "/playground", "PlayCircleOutlined", 10),
    ("menu:special", "专项测试", "", "/special", "PlayCircleOutlined", 11),
    ("menu:schedule", "定时任务", "", "/schedule", "ClockCircleOutlined", 12),
    ("menu:report", "报告中心", "", "/report", "BarChartOutlined", 13),
    ("menu:system", "系统管理", "", "/system", "SettingOutlined", 14),
    ("menu:project", "项目管理", "", "/project", "AppstoreOutlined", 15),
    ("menu:myproject", "我的项目", "", "/my-projects", "AppstoreOutlined", 15),
    ("menu:organization", "组织管理", "", "/organizations", "AppstoreOutlined", 16),
    ("menu:defect", "缺陷管理", "", "/defect", "BugOutlined", 16),
    ("menu:dataset", "测试数据集", "", "/dataset", "DatabaseOutlined", 17),
    ("menu:integration", "集成配置", "", "/integration", "LinkOutlined", 18),
    ("menu:notify", "通知配置", "", "/notify", "NotificationOutlined", 19),
    ("menu:environment", "目标环境", "", "/environment", "EnvironmentOutlined", 20),
    ("menu:agent-workbench", "Agent 工作台", "", "/agent-workbench", "SparklesOutlined", 21),
    ("menu:perftest", "性能监控", "", "/perftest", "CpuOutlined", 22),
    ("menu:lanhu_evidence", "蓝湖证据包", "", "/lanhu-evidence", "FileTextOutlined", 23),
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
    # 系统管理 - 注册邀请码（Batch 104 外放轻量模式）
    ("system:invite:manage", "管理注册邀请码", "button"),
    # 运维发布控制（全局只读；不创建产品侧菜单）
    ("release:view", "查看运维发布记录", "button"),
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
    ("uitest:trigger_prod", "触发生产环境UI自动化", "button"),
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
    ("project:self_create", "自助创建项目", "button"),
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
    ("integration:sync_prod", "执行生产环境同步操作", "button"),
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
    # 蓝湖证据包 OCR — 收在知识中心/需求，不新增菜单
    ("lanhu_evidence:view", "查看蓝湖证据包", "button"),
    ("lanhu_evidence:run", "创建蓝湖证据包", "button"),
    ("lanhu_evidence:review", "人工审核证据页（OCR 缺失豁免）", "button"),
    ("lanhu_evidence:import", "导入蓝湖证据包", "button"),
    # 性能监控
    ("perftest:list", "查看性能监控", "button"),
    ("perftest:create", "创建性能监控会话", "button"),
    ("perftest:delete", "删除性能监控会话", "button"),
    ("perftest:execute", "执行性能监控", "button"),
    ("perftest:report", "查看性能报告", "button"),
]

# 测试人员可见的菜单子集
_TESTER_ACTIONS = {
    # Batch 104 外放轻量模式：自助建项目
    "project:self_create",
    # 用例服务（B87-Q1 核心缺口）
    "testcase:list", "testcase:detail", "testcase:create", "testcase:update",
    "testcase:delete", "testcase:export",
    # 测试计划
    "testplan:list", "testplan:detail", "testplan:create", "testplan:update",
    "testplan:delete", "testplan:execute",
    # 报告中心（删除留管理员）
    "report:list", "report:detail", "report:create",
    # 定时任务
    "schedule:list", "schedule:create", "schedule:update", "schedule:delete",
    "schedule:trigger",
    # 缺陷管理（删除留管理员）
    "defect:list", "defect:detail", "defect:create", "defect:update",
    # 需求文档（上传/生成/导入）
    "requirement:upload", "requirement:generate", "requirement:import",
    # 测试数据集
    "dataset:list", "dataset:create", "dataset:update", "dataset:delete",
    # 用例评审
    "review:submit", "review:approve",
    # 版本测试任务（删除与 AI 生成留管理员）
    "mission:list", "mission:detail", "mission:create", "mission:update",
    "mission:log",
    # 通知配置
    "notify:list", "notify:manage",
    # UI 自动化（生产触发留管理员）
    "uitest:list", "uitest:detail", "uitest:create", "uitest:update",
    "uitest:delete", "uitest:trigger",
    # 专项测试
    "avcheck:list", "avcheck:detail", "avcheck:create", "avcheck:delete",
    "avcheck:trigger",
    # 接口测试（保留；生产执行留管理员）
    "apitest:execute", "apitest:view", "apitest:import", "apitest:generate",
    "apitest:task", "apitest:asset_manage",
    # 知识 / Wiki / Agent（只读视角；管理/审核留管理员）
    "knowledge:view",
    "agent:view", "agent:list",
    "wiki:view", "wiki:diff",
    # 蓝湖证据包（采集可发起；导入/审核留管理员）
    "lanhu_evidence:view", "lanhu_evidence:run",
    # 性能监控
    "perftest:list", "perftest:create", "perftest:delete", "perftest:execute", "perftest:report",
}

# 运营只读角色（C31-3）：仅查看，无任何写操作
_VIEWER_MENUS = {
    "menu:workbench", "menu:trace", "menu:requirement", "menu:report", "menu:defect",
    "menu:dataset", "menu:knowledge",
    "menu:knowledge:project", "menu:knowledge:platform", "menu:knowledge:graph",
    "menu:knowledge:artifacts",
    "menu:myproject",
    "menu:organization",
}

_VIEWER_ACTIONS = {
    "testcase:list", "testcase:detail",
    "testplan:list", "testplan:detail",
    "report:list", "report:detail",
    "defect:list", "defect:detail",
    "schedule:list",
    "dataset:list",
    "knowledge:view",
    "wiki:view",
    "lanhu_evidence:view",
    "perftest:list",
    "apitest:view",
    "uitest:list",
    "avcheck:list",
    "mission:list",
}

_TESTER_MENUS = {
    "menu:workbench", "menu:trace", "menu:requirement", "menu:versionmission", "menu:mindmap", "menu:testcase", "menu:testplan",
    "menu:apitest", "menu:uitest", "menu:playground", "menu:special", "menu:schedule", "menu:report",
    "menu:defect", "menu:dataset", "menu:integration", "menu:knowledge", "menu:agent-workbench",
    "menu:perftest", "menu:notify", "menu:environment",
    "menu:knowledge:project", "menu:knowledge:platform", "menu:knowledge:graph", "menu:knowledge:artifacts",
    "menu:lanhu_evidence",
    "menu:myproject",
    "menu:organization",
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

        # 2) 菜单 + 操作权限点（两遍：先创建全部菜单，再回填 parent_id）
        code_to_perm: dict[str, Permission] = {}
        for code, name, _parent, path, icon, sort in _MENUS:
            perm, _ = _get_or_create(
                db, Permission,
                defaults={"name": name, "type": "menu", "path": path, "icon": icon, "sort": sort},
                code=code,
            )
            # The seed catalog is the canonical menu definition. Reconcile mutable
            # fields as well as creating missing records, otherwise renamed routes
            # stay stale forever in existing environments.
            perm.name = name
            perm.type = "menu"
            perm.path = path
            perm.icon = icon
            perm.sort = sort
            code_to_perm[code] = perm
        # 第二遍：回填 parent_id
        for code, name, parent_code, path, icon, sort in _MENUS:
            if parent_code and parent_code in code_to_perm:
                perm = code_to_perm[code]
                perm.parent_id = code_to_perm[parent_code].id
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
        viewer_role, _ = _get_or_create(
            db, Role, defaults={"name": "运营只读", "data_scope": "project",
                                "remark": "仅查看，无写操作（C31-3）"},
            code="viewer",
        )

        # 4) 角色-权限
        _get_or_create(db, RolePermission, role_id=admin_role.id, permission_id=star.id)
        for code in _TESTER_MENUS:
            if code in code_to_perm:
                _get_or_create(db, RolePermission, role_id=tester_role.id, permission_id=code_to_perm[code].id)
        for code in _TESTER_ACTIONS:
            if code in code_to_perm:
                _get_or_create(db, RolePermission, role_id=tester_role.id, permission_id=code_to_perm[code].id)
        for code in _VIEWER_MENUS | _VIEWER_ACTIONS:
            if code in code_to_perm:
                _get_or_create(db, RolePermission, role_id=viewer_role.id, permission_id=code_to_perm[code].id)

        # 5) 管理员用户
        admin_user = db.scalar(
            select(User).filter_by(username=settings.admin_username)
        )
        created_admin = admin_user is None
        if created_admin:
            admin_user = User(
                username=settings.admin_username,
                password=hash_password(settings.get_initial_admin_password()),
                nickname="超级管理员",
                email="admin@cameltv.local",
                status=1,
                must_change_password=settings.admin_password == "",
            )
            db.add(admin_user)
            db.flush()

        # 5.5) 测试用户（方便验证角色隔离）
        tester_pwd: str | None = None
        tester_user = db.scalar(
            select(User).filter_by(username=settings.tester_username)
        )
        created_tester = tester_user is None
        if created_tester:
            tester_pwd = settings.tester_password or _secrets.token_urlsafe(10)
            tester_user = User(
                username=settings.tester_username,
                password=hash_password(tester_pwd),
                nickname="测试同学",
                email="tester@cameltv.local",
                status=1,
            )
            db.add(tester_user)
            db.flush()

        # 5.6) 运营只读用户（C31-3）
        viewer_pwd: str | None = None
        viewer_user = db.scalar(
            select(User).filter_by(username=settings.viewer_username)
        )
        created_viewer = viewer_user is None
        if created_viewer:
            viewer_pwd = settings.viewer_password or _secrets.token_urlsafe(10)
            viewer_user = User(
                username=settings.viewer_username,
                password=hash_password(viewer_pwd),
                nickname="运营只读",
                email="viewer@cameltv.local",
                status=1,
            )
            db.add(viewer_user)
            db.flush()

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

        # 7.5) 测试用户分配 tester 角色并加入默认项目。两条关系必须
        # 独立幂等创建，确保全新数据库第一次启动后账号即可使用。
        _get_or_create(
            db,
            UserRole,
            user_id=tester_user.id,
            role_id=tester_role.id,
            project_id=0,
        )
        _get_or_create(
            db,
            ProjectMember,
            project_id=project.id,
            user_id=tester_user.id,
            defaults={"role_id": tester_role.id},
        )
        _get_or_create(
            db,
            UserRole,
            user_id=viewer_user.id,
            role_id=viewer_role.id,
            project_id=0,
        )
        _get_or_create(
            db,
            ProjectMember,
            project_id=project.id,
            user_id=viewer_user.id,
            defaults={"role_id": viewer_role.id},
        )

        db.commit()
        if created_admin:
            print(f"[seed] 初始管理员已创建：{settings.admin_username}")
            if settings.admin_password:
                print("[seed] 管理员使用自定义密码")
            else:
                print("[seed] 管理员使用自动生成密码（见启动日志），首次登录需修改")
        if created_tester:
            print(f"[seed] 测试用户已创建：{settings.tester_username}")
            if not settings.tester_password and tester_pwd is not None:
                print(f"[seed] 测试用户自动生成密码：{tester_pwd}")
        # viewer 密码由部署环境 env VIEWER_PASSWORD 提供；不打印，避免凭据散落与 WARN 增长
        _ = viewer_user
    finally:
        db.close()
