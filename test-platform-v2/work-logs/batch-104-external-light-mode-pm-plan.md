# Batch 104 — PM Plan（外放轻量模式）

> **PM (🟨)** | Date: 2026-08-06

## 规格摘要

**原始需求**: 平台外放：开放注册（管理员发邀请码）+ 用户自助创建项目并成为负责人
+ 邀请同事协作；超管保持全平台权限（PRD §4 US-01~05）。
**目标时间**: 3–5 小时（单窗口 Codex 执行）

## 开发任务

### [ ] Task 1: 批次工件与看板初始化
**描述**: 落盘 PRD/PM/Design 工件，创建 DEV 看板并登记本批 US 与切片。
**验收标准**: 三份工件存在且无占位符；看板含切片表与当前位置。
**涉及文件**:
- `test-platform-v2/work-logs/batch-104-external-light-mode-{prd-summary,pm-plan,design-spec}.md` — 工件
- `test-platform-v2/work-logs/kanbans/DEV-batch-104-external-light-mode.md` — 看板

### [ ] Task 2: 后端注册基础（配置 + 邀请码模型 + 迁移 + 注册接口）
**描述**: 新增 settings 配置（registration_enabled / invite_code_required /
default_registration_role / max_projects_per_user / 注册限流）；新增 `InviteCode`
模型与 Alembic 迁移（单头）；`POST /auth/register` 公开接口：校验邀请码、用户名/邮箱
唯一、创建用户并赋予默认角色、自动登录（复用 cookie/JWT 逻辑）、注册频率限制。
**验收标准**:
- `pytest tests/test_register.py` 通过：注册成功/邀请码无效/过期/用尽/用户名邮箱重复/限流；
- 注册成功后 `/auth/me` 可用，用户拥有 tester 全局角色；
- 关闭 `registration_enabled` 时注册返回 403。
**涉及文件**:
- `backend/app/core/config.py` — 新配置
- `backend/app/models/invite_code.py` — 新模型
- `backend/alembic/versions/20260806_batch104_invite_code.py` — 迁移
- `backend/app/schemas/auth.py` — RegisterIn/RegisterOut
- `backend/app/api/v1/auth.py` — register 端点
- `backend/app/services/invite_service.py` — 邀请码校验/消耗
- `backend/tests/test_register.py` — 新测试
**参考**: PRD US-01 / §5；现有 `auth.py::login` 限流与 cookie 逻辑。

### [ ] Task 3: 后端自助项目（自动成员 + 配额 + 所有者权限）
**描述**: `create_project` 自动写入 `ProjectMember`（owner + 项目管理员角色，超管除外仍需
保留现状语义）；新增个人项目数配额校验；新增 `require_project_owner` 依赖；项目编辑/删除/
成员管理接口改为「全局权限 或 项目所有者」放行；普通用户 `GET /projects` 语义不变。
**验收标准**:
- `pytest tests/test_project_owner.py` 通过：创建即成员、配额超限 400、
  所有者可管理成员、非所有者 403、超管全量；
- 现有 `test_rbac_project_roles.py` 与 `test_auth.py` 不回归。
**涉及文件**:
- `backend/app/services/project_service.py` — 自动成员 + 配额
- `backend/app/core/deps.py` — require_project_owner
- `backend/app/api/v1/project.py` — 所有者放行
- `backend/app/schemas/project.py` — 配额错误消息
- `backend/tests/test_project_owner.py` — 新测试
**参考**: PRD US-02 / US-05；现有 `require_permission`/`require_project` 结构。

### [ ] Task 4: 后端邀请码管理接口
**描述**: `GET/POST /system/invite-codes`、`POST /system/invite-codes/{id}/disable`
（管理员权限 `system:invite:manage`，seed 补权限点）；创建支持 usage_limit/expires_at；
列表含已用次数与状态。
**验收标准**:
- `pytest tests/test_invite_admin.py` 通过：创建/列表/停用/权限 403/停用后注册 400；
- seed 幂等补权限点。
**涉及文件**:
- `backend/app/api/v1/system.py` — 邀请码管理端点
- `backend/app/schemas/system.py` — InviteCodeOut/In
- `backend/app/seed.py` — `system:invite:manage` 权限点
- `backend/tests/test_invite_admin.py` — 新测试
**参考**: PRD US-04；现有 `system.py` 用户管理端点模式。

### [ ] Task 5: 前端注册页与入口
**描述**: 新增 `/register` 页面（用户名/昵称/邮箱/密码/邀请码，表单校验、错误内联展示）；
登录页添加「注册」入口；注册成功自动登录并跳「我的项目」；路由无需登录守卫。
**验收标准**:
- `vitest` RegisterPage 测试通过（校验/提交/成功跳转）；
- `npm run typecheck && npm run build` 通过。
**涉及文件**:
- `frontend/src/pages/register/index.tsx` — 新页面
- `frontend/src/router/index.tsx` — /register 路由
- `frontend/src/pages/login/index.tsx` — 注册入口
- `frontend/src/api/auth.ts` — register() 封装
- `frontend/src/pages/register/__tests__/RegisterPage.test.tsx` — 新测试
**参考**: PRD US-01；现有 `login/index.tsx` 表单模式。

### [ ] Task 6: 前端我的项目与所有者能力
**描述**: 项目管理页拆出普通用户「我的项目」视图（`GET /projects`，含新建按钮与成员管理，
权限由 owner 放行）；系统管理新增「邀请码」管理（admin 专属，列表/新建/停用）；
项目创建对话框提交后刷新项目切换器。
**验收标准**:
- `vitest` ProjectPage/InviteCodesTab 测试通过；
- 普通用户视图不请求 `/projects/all`（Network 验证单次请求）；
- `npm run typecheck && npm run build` 通过。
**涉及文件**:
- `frontend/src/pages/project/index.tsx` — 双模式视图
- `frontend/src/pages/system/InviteCodesTab.tsx` — 新 Tab
- `frontend/src/pages/system/index.tsx` — 挂载 Tab
- `frontend/src/api/system.ts` — invite codes API
- `frontend/src/pages/project/__tests__/ProjectPage.test.tsx` — 更新/新增
**参考**: PRD US-02/03/04；现有 `UsersTab.tsx` 管理页模式。

### [ ] Task 7: QA 硬门禁 + 回归 + 总确认
**描述**: 执行前端 typecheck/build/vitest、后端 ruff F821/app 导入/Alembic 单头/
受影响模块 pytest + 关键路径回归；产出 QA 报告与 Leader 判决；展示变更摘要做一次总确认。
**验收标准**: 硬门禁全绿；QA 报告含命令、退出码、缺陷清单；Leader APPROVED。
**涉及文件**: QA/Leader 工件 + 看板更新。
**参考**: DEPARTMENTS.md QA/Leader 模板；C75-3/C76-2/C78-1。

## 质量要求

- [ ] 响应式（Desktop + Tablet；注册页/项目页）  - [ ] OpenAPI 同步（新端点进契约）
- [ ] 单元测试覆盖（后端 pytest / 前端 vitest）  - [ ] 无障碍（ARIA/键盘）
- [ ] 无 console 报错/告警  - [ ] 无调试遗留（console.log/print/breakpoint）
- [ ] 双 404 约定（C86-1）：新增测试断言用 assert_guard_404 / HTTP 200+code 404
