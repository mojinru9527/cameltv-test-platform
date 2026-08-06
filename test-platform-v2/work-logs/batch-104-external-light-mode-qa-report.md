# Batch 104 — QA 报告（外放轻量模式）

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
| Alembic 单头 | `python -m alembic heads` | 0 | `20260806_batch104_invite_code (head)` 唯一 |
| 新功能测试 | `pytest tests/test_register.py tests/test_invite_admin.py tests/test_project_owner.py` | 0 | 21 passed |
| 相关回归 | `pytest test_auth/test_rbac_project_roles/test_forced_password_change/test_batch63_menu_catalog/test_alembic_runbook` | 0 | 31 passed |
| 后端全量回归 | `pytest -q --tb=short --ignore=tests/playwright` | 0 | **1097 passed, 3 skipped**（无新增失败） |
| 前端类型检查 | `npm run typecheck` | 0 | tsc -b 通过 |
| 前端构建 | `npm run build` | 0 | vite build 成功（3431 modules） |
| 前端全量测试 | `npx vitest run` | 0 | 91 files / **347 passed** |
| 新增前端测试 | 3 个新测试文件 | 0 | 9 passed |
| 批次门禁 | `scripts/git/scan-common-bugs.ps1` | 1* | HARD 0 / WARN 209（*与既有 WARN 基线 209 持平，见 C81-1/batch-89） |
| 批次门禁 | `scripts/git/audit-cconditions.ps1 -RequireLatestBatch` | 0 | hard errors 0 / warnings 0 |

## 逐条件验证

### C1: US-01 新用户凭邀请码注册
**变更文件**: `backend/app/api/v1/auth.py:74-98`、`backend/app/services/auth_service.py:57-97`、
`backend/app/services/invite_service.py`、`frontend/src/pages/register/index.tsx`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 注册成功并自动登录（cookie） | ✅ | `test_register_success_auto_login` + HTTP 冒烟 200 |
| 邀请码缺失/无效/过期/用尽 → 400 | ✅ | 4 条用例通过（envelope 400，HTTP 400） |
| 用户名/邮箱重复 → 400 | ✅ | 2 条用例通过 |
| 密码 <6 位 → 422 | ✅ | schema `min_length=6`，用例通过 |
| 注册未开放 → 403 | ✅ | `effective_registration_enabled=false` 用例通过 |
| 注册限流 → 429 | ✅ | 独立桶 `register_limiter`，用例通过 |
| 默认角色 tester + 权限下发 | ✅ | 冒烟 `permissions` 含 `project:self_create` |

### C2: US-02 注册用户自助创建项目
**变更文件**: `backend/app/services/project_service.py:create_project`、
`backend/app/core/deps.py:require_project_create`、`frontend/src/pages/my-projects/index.tsx`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 创建后自动成为成员 | ✅ | `test_create_project_auto_membership` 断言 ProjectMember 行 |
| 创建者成为 owner | ✅ | `project.owner_id == user.id` 用例 |
| 创建后项目切换器可见 | ✅ | `GET /projects` 立即返回，用例 + HTTP 冒烟 |
| 个人项目配额超限 → 400 | ✅ | `test_create_project_quota`（monkeypatch max=1） |
| 非成员访问他人项目 → 403 | ✅ | `test_non_member_cannot_access_project` |
| 超管全量可见 | ✅ | `test_superadmin_sees_all_projects` |

### C3: US-03 项目负责人邀请同事
**变更文件**: `backend/app/api/v1/project.py`、`backend/app/core/deps.py:require_project_owner_or`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 负责人可添加成员 | ✅ | `test_owner_can_manage_members`；同事项目列表出现 |
| 非负责人调成员接口 → 403 | ✅ | `test_non_owner_cannot_manage_members` |
| 负责人可编辑/停用自己的项目 | ✅ | `test_owner_update_delete_allowed` |

### C4: US-04 管理员发放与管理邀请码
**变更文件**: `backend/app/api/v1/system.py`、`backend/app/seed.py`、`frontend/src/pages/system/InviteCodesTab.tsx`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 生成/列表/停用 | ✅ | `test_admin_create_and_list`、`test_admin_disable_then_register_rejected` |
| 次数上限与过期时间 | ✅ | `test_admin_supports_usage_limit_and_expiry` |
| 非管理员 → 403 | ✅ | `test_non_admin_forbidden` |
| 前端脱敏展示 + 中文状态 | ✅ | InviteCodesTab 2 用例（`****1234`/`启用`/`已用尽`） |

### C5: US-05 超管全平台权限保持
**变更文件**: `backend/app/core/deps.py`（新增依赖不影响 `is_super` 分支）

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 超管可见全部项目 | ✅ | 回归 `test_superadmin_sees_all_projects` + `test_rbac_project_roles.py` 5/5 |
| 既有权限矩阵不回归 | ✅ | `test_rbac_project_roles.py`、`test_viewer_role.py` 全过 |

### C6: CI 分层核对
**变更范围**: `test-platform-v2/backend/**` + `test-platform-v2/frontend/**` + `work-logs/`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| CI 分类 | backend=true, frontend=true | 双端 required jobs 均会运行（分类器按完整 diff） |
| 本地等价门禁已执行 | ✅ | 上表全部命令为本地等价证据，退出码齐全 |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| B104-1 | P2 | `test_batch48_requirement_migration.py` 硬编码迁移头，新增迁移后 `alembic current` 断言失败（测试陈旧，非产品缺陷） | 全量回归首次 `F` → 修复后 3/3 | ✅ 已修复（动态读取单头） |
| B104-2 | P3 | `datetime.utcnow()` 弃用告警 | pytest warning | ✅ 已修复（`datetime.now(timezone.utc)` naive） |
| B104-3 | P3 | 前端集中图标表缺 `LogIn/Mail/Ticket` | typecheck TS2305 | ✅ 已修复（`ArrowRight/Send/KeyRound`） |
| B104-4 | P3 | 仓库 `api.d.ts` 与当前 openapi-typescript 版本差异巨大（28k 行漂移，预存） | 重新生成对比 | ✅ 采用最小手工契约同步（+243），全量重生成留作后续 C 条件 |

## 发布建议

状态: **READY**
必修复: 0   建议修复: 0

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 3–5h vs ≈4h | 0/0/1/3 | 1 | 工具链 + 测试陈旧 | ① 补丁落点先小样验证 worktree 相对路径；② 新增迁移后先跑 `test_batch48_requirement_migration` 类头断言 |

## 技能使用

- `cameltv-bug-guard` → 编码前避坑清单（cookie 污染、双 404 约定、Select 空值、副作用四铁律已逐条自检）；
- `cameltv-ui-conventions` → 注册页/我的项目/邀请码 Tab 按规范实现（四态、中文状态、语义 Token、触控目标）；
- `test-case-design` → 用例覆盖结构；
- KB 检索因后端未常驻运行采用本地证据替代（PATTERNS.md + work-logs），已在看板记录。
