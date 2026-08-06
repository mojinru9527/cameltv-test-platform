# Batch 105 — PM Plan（租户模式）

> **PM (🟨)** | Date: 2026-08-06

## 规格摘要

**原始需求**: C104-1 租户层：用户→组织/团队→项目；注册自动个人组织、团队组织创建与
成员邀请、项目归属组织、组织成员访问组织项目、存量项目迁移（PRD US-01~05）。
**目标时间**: 4–6 小时（单窗口 Codex 执行）

## 开发任务

### [ ] Task 1: 批次工件与看板初始化
**描述**: PRD/PM/Design 落盘，创建 DEV 看板，登记 C104-1 纳入与 C104-2~4 豁免。
**验收标准**: 三份工件无占位符；看板含切片表。
**涉及文件**: `work-logs/batch-105-tenant-organization-{prd-summary,pm-plan,design-spec}.md`、
`work-logs/kanbans/DEV-batch-105-tenant-organization.md`

### [ ] Task 2: 后端组织模型 + 迁移回填 + 配置
**描述**: 新增 `Organization`/`OrganizationMember` 模型与 Alembic 迁移：
建表 + `sys_project.organization_id` 列 + 为现有用户创建个人组织并回填其项目；
新增 `max_team_organizations_per_user` 配置（默认 5）。
**验收标准**:
- `pytest tests/test_organization_migration.py`：迁移建表、回填幂等、存量项目归属正确、数据不丢；
- Alembic 单头；`test_batch48_requirement_migration.py` 等既有迁移测试不回归。
**涉及文件**:
- `backend/app/models/organization.py` — 新模型
- `backend/alembic/versions/20260806_batch105_organization.py` — 迁移+回填
- `backend/app/models/__init__.py` — 注册模型
- `backend/app/core/config.py` — 新配置
- `backend/tests/test_organization_migration.py` — 新测试
**参考**: PRD US-04/§5；Batch 104 迁移样式。

### [ ] Task 3: 后端组织接口 + 注册自动个人组织
**描述**: `GET/POST /organizations`、`PUT/DELETE /organizations/{id}`（负责人/管理员）、
`GET/POST/DELETE /organizations/{id}/members`（负责人/管理员）、
`GET /organizations/{id}/projects`（组织成员）；注册时自动创建个人组织并加入；
`LoginOut/MeOut` 返回 organizations。
**验收标准**:
- `pytest tests/test_organization_api.py`：列表/创建/改名/停用/成员邀请移除/权限 403/
  上限 400/注册自动个人组织；
- 停用组织时其项目不可用（项目状态联动或显式提示）。
**涉及文件**:
- `backend/app/api/v1/organization.py` — 新路由
- `backend/app/api/v1/router.py` — 注册路由
- `backend/app/services/organization_service.py` — 新服务
- `backend/app/core/deps.py` — require_org_owner_or_admin
- `backend/app/schemas/organization.py` — 新 schema
- `backend/app/schemas/auth.py` — LoginOut/MeOut 扩展
- `backend/app/services/auth_service.py` — 注册创建个人组织
- `backend/app/seed.py` — menu:organization
- `backend/tests/test_organization_api.py` — 新测试
**参考**: PRD US-01/02；Batch 104 邀请码/项目接口模式。

### [ ] Task 4: 项目归属组织 + 组织成员访问
**描述**: `ProjectCreate` 增加可选 `organization_id`（默认创建者个人组织）；创建时校验
组织成员身份；`require_project` 增加「项目所属组织成员」放行；`GET /projects` 返回
organization_id/organization_name；`projects_for_user` 增加组织成员可见集合。
**验收标准**:
- `pytest tests/test_organization_project_access.py`：组织成员进入组织项目 200、
  非组织非项目成员 403、项目成员（非组织）仍可访问、超管全量、创建默认个人组织；
- 既有 `test_rbac_project_roles.py`/`test_project_owner.py` 不回归。
**涉及文件**:
- `backend/app/services/project_service.py` — organization 归属/可见集合
- `backend/app/core/deps.py` — require_project 组织成员放行
- `backend/app/schemas/project.py` — organization 字段
- `backend/app/api/v1/project.py` — 创建参数
- `backend/tests/test_organization_project_access.py` — 新测试
**参考**: PRD US-03/05。

### [ ] Task 5: 前端组织管理页与项目组织联动
**描述**: 新增「组织管理」页（列表/新建团队组织/成员邀请移除/改名停用/组织项目列表）；
项目创建对话框增加组织选择（默认个人组织）；我的项目表格显示组织名；路由与菜单接入。
**验收标准**:
- vitest 新增测试通过；`npm run typecheck && npm run lint && npm run build` 全绿；
- Network 验证无 N+1（组织成员/项目列表各单次请求）。
**涉及文件**:
- `frontend/src/pages/organization/index.tsx` — 新页面
- `frontend/src/router/index.tsx` — /organizations 路由
- `frontend/src/api/organization.ts` — 新 API
- `frontend/src/api/auth.ts` — LoginResult 类型扩展
- `frontend/src/types/index.ts` — Organization 类型
- `frontend/src/pages/my-projects/index.tsx` — 组织选择/组织标签
- `frontend/src/pages/organization/__tests__/OrganizationPage.test.tsx` — 新测试
**参考**: PRD US-01/02/03；Batch 104 我的项目页模式。

### [ ] Task 6: QA 硬门禁 + 回归 + 总确认
**描述**: 全量 pytest/vitest/lint/build/ruff/迁移单头；QA 报告 + Leader 判决 +
C 条件登记；展示变更摘要做一次总确认。
**验收标准**: 硬门禁全绿；QA 含命令与退出码；Leader APPROVED。
**涉及文件**: QA/Leader 工件 + 看板。

## 质量要求

- [ ] 响应式（组织页 Desktop + Tablet）  - [ ] OpenAPI 契约同步（新端点）
- [ ] 单元测试覆盖（pytest/vitest）  - [ ] 无障碍（ARIA/键盘）
- [ ] 无 console 报错/告警  - [ ] 双 404 约定（C86-1）
- [ ] C104-5：首个补丁验证写入 worktree
