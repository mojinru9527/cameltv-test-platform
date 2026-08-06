# Batch 105 — QA 报告（租户模式）

> **QA (🔍)** | Date: 2026-08-06 | Verdict: PASS

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 10（US-01~05 拆分 + 5 门禁） | 10 | 0 | 0 |

## 可执行门禁（命令、退出码与结果）

| 门禁 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 后端未定义符号 | `.venv\Scripts\python -m ruff check app/ --select F821` | 0 | All checks passed |
| 后端应用导入 | `python -c "import app.main"` | 0 | import OK |
| Alembic 单头 | `python -m alembic heads` | 0 | `20260806_batch105_organization (head)` 唯一 |
| 组织新功能测试 | `pytest test_organization_api/test_organization_migration/test_organization_project_access` | 0 | **19 passed** |
| 相关回归 | auth/register/invite/project_owner/rbac/menu_catalog/alembic/batch48/viewer | 0 | 51 passed（含修复后重跑） |
| 后端全量回归 | `pytest -q --tb=short --ignore=tests/playwright` | 0 | **1116 passed, 3 skipped**（修复后重跑） |
| 前端类型检查 | `npm run typecheck` | 0 | tsc -b 通过 |
| 前端 lint | `npm run lint` | 0 | eslint 0 错误 |
| 前端构建 | `npm run build` | 0 | vite build 成功 |
| 前端全量测试 | `npx vitest run` | 0 | 92 files / **350 passed** |
| 批次门禁 | `scan-common-bugs.ps1` | 1* | HARD 0 / WARN 209（*既有基线持平） |
| 批次门禁 | `audit-cconditions.ps1 -RequireLatestBatch` | 0 | hard errors 0 / warnings 0 |

## 逐条件验证

### C1: US-01 注册即有个人组织
**变更文件**: `backend/app/services/auth_service.py:register`、
`backend/app/services/organization_service.py:ensure_personal_organization`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 注册自动创建个人组织 | ✅ | `test_register_creates_personal_organization`（type=personal, my_role=1） |
| 登录响应携带组织 | ✅ | `test_login_returns_organizations` |
| 端到端冒烟 | ✅ | 注册响应 organizations=1（HTTP 实测） |

### C2: US-02 创建团队组织并邀请同事
**变更文件**: `backend/app/api/v1/organization.py`、`organization_service.py`、
`frontend/src/pages/organization/index.tsx`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 创建团队组织 | ✅ | `test_create_team_organization_and_list` + HTTP 冒烟 |
| 团队组织配额 400 | ✅ | `test_team_organization_quota` |
| 按用户名邀请/不存在 400 | ✅ | `test_invite_by_username`、`test_invite_unknown_username_rejected` |
| 非负责人 403 | ✅ | `test_non_owner_cannot_manage_members` |
| 个人组织不可停用 | ✅ | `test_personal_org_cannot_be_disabled` |

### C3: US-03 组织成员访问组织项目
**变更文件**: `backend/app/core/deps.py:require_project`、`project_service.py`、
`backend/app/api/v1/organization.py:list_org_projects`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 组织成员可进入组织项目 | ✅ | `test_org_member_can_access_org_project` + HTTP 冒烟 |
| 非组织非项目成员 403 | ✅ | `test_non_org_non_project_member_forbidden` |
| 项目级成员（组织外）仍可访问 | ✅ | `test_project_member_outside_org_still_accesses` |
| 在他人组织建项目 403 | ✅ | `test_create_in_other_org_forbidden` |

### C4: US-04 存量项目迁移
**变更文件**: `backend/alembic/versions/20260806_batch105_organization.py`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 建表 + organization_id 列 | ✅ | `test_upgrade_creates_organization_tables_when_missing` |
| 每人个人组织 + 项目回填 | ✅ | `test_upgrade_backfills_personal_organizations_and_project_ownership` |
| 幂等重跑 | ✅ | 同测试二次 upgrade 组织数不变 |
| 原项目成员关系不丢 | ✅ | 迁移后 project_member 行数不变 |
| 最小旧库（无 sys_project）防御 | ✅ | `test_batch48_requirement_migration.py` 3/3 |

### C5: US-05 超管全平台权限保持
**变更文件**: `backend/app/core/deps.py`（is_super 分支不变）

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 超管可见全部项目 | ✅ | `test_superadmin_sees_all_org_projects` + 既有 rbac/viewer 回归 |
| 组织全量可见（超管） | ✅ | `organizations_for_user` is_superadmin 分支 |

### C6: CI 分层核对

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 变更范围 | backend + frontend + work-logs + docs + C-CONDITIONS | 双端 required jobs 均运行 |
| 本地等价门禁 | ✅ | 上表命令退出码齐全 |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| B105-1 | P1 | `projects_for_user` 由 ORM 改为 dict 返回，`dashboard_service.get_cross_project_stats` 消费 `p.id` 崩溃（全量回归抓出） | 首次全量回归 F → 修复后 1116 全绿 | ✅ 已修复（恢复 ORM 返回 + 接口层 `attach_organization_names`） |
| B105-2 | P2 | 迁移回填假设 sys_project 存在，最小旧库（batch48 测试）upgrade 失败 | test_batch48 F → 防御式修复 3/3 | ✅ 已修复 |
| B105-3 | P3 | TestClient cookie 串号导致跨用户测试误判（PATTERNS T3 复现） | 组织测试多处 403/200 误判 | ✅ 已修复（登录后清 cookie） |
| B105-4 | P3 | Project 模型漏加 organization_id 列（迁移有、模型无） | TypeError 由测试抓出 | ✅ 已修复 |

## 发布建议

状态: **READY**
必修复: 0   建议修复: 0

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 4–6h vs ≈5h | 0/1/1/2 | 2 | 契约变更 + 测试陈旧 | 改服务返回类型前先 `rg` 全部调用方；迁移对最小旧库做防御 |

## 技能使用

- `cameltv-bug-guard` → PATTERNS T3 cookie 串号、双 404、Select 空值逐条自检；
- `cameltv-ui-conventions` → 组织页四态/中文角色映射/触控目标；
- `test-case-design` → 用例覆盖；
- KB 检索：本地证据（PATTERNS/work-logs）替代运行中知识库，已记录。
