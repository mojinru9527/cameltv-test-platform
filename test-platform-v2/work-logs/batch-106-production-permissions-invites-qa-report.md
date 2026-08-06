# Batch 106 — QA 报告（生产启用 + 组织权限映射 + 项目邀请链接）

> **QA (🔍)** | Date: 2026-08-06 | Verdict: PASS

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 12（US-01~04 拆分 + 6 门禁） | 12 | 0 | 0 |

## 可执行门禁（命令、退出码与结果）

| 门禁 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 后端未定义符号 | `ruff check app/ --select F821` | 0 | All checks passed |
| 后端应用导入 | `python -c "import app.main"` | 0 | import OK |
| Alembic 单头 | `python -m alembic heads` | 0 | `20260806_batch106_project_invite (head)` 唯一 |
| 新功能测试 | `pytest test_org_permission_mapping.py test_project_invite.py` | 0 | **14 passed** |
| 相关回归 | rbac/project_owner/organization/register/auth/alembic/batch48/batch63 | 0 | 63 passed |
| 后端全量回归 | `pytest -q --tb=short --ignore=tests/playwright` | 0 | **1133 passed, 3 skipped** |
| 前端类型检查/lint/构建 | `npm run typecheck && npm run lint && npm run build` | 0 | 全绿 |
| 前端全量测试 | `npx vitest run` | 0 | 92 files / **352 passed** |
| 批次门禁 | `scan-common-bugs.ps1` | 1* | HARD 0 / WARN 209（*既有基线持平） |
| 批次门禁 | `audit-cconditions.ps1 -RequireLatestBatch` | 0 | hard errors 0 / warnings 0 |

## 逐条件验证

### C1: US-01 生产启用
**变更文件**: `deploy/production-enablement-checklist.md`、`config/runtime/production.env.example`、
`work-logs/evidence/batch-106/README.md`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 检查清单（前置/变量/迁移/验证/回滚/登记） | ✅ | 清单落盘 |
| 迁移演练（SQLite 全链） | ✅ | organization/invite/batch48/alembic 测试 9/9 |
| PostgreSQL 契约 | ✅（CI 证据） | `backend-check-pg` PG16 在 PR required checks 执行 |
| 生产切换执行 | ⏳ 人工步骤 | Railway CLI 未安装 + 执行窗口需用户确认 → C106-1 |

### C2: US-02 组织权限映射
**变更文件**: `backend/app/services/rbac_service.py`、`backend/app/core/deps.py`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 组织负责人管理组织项目成员/门禁 | ✅ | `test_org_owner_can_manage_org_project` |
| 组织管理员（role 2）可管理 | ✅ | `test_org_admin_can_manage_org_project` |
| 普通组织成员 403 | ✅ | `test_org_member_cannot_manage_org_project` |
| permissions 含 project:manage/update | ✅ | `test_permission_codes_include_project_manage_for_org_owner` |
| 无需项目成员身份（组织维度访问） | ✅ | `test_org_owner_manage_requires_org_membership_not_project` |
| 冒烟：org admin 读取质量门禁 200 | ✅ | HTTP 实测 |

### C3: US-03 项目邀请链接
**变更文件**: `backend/app/models/project_invite.py`、迁移、`project_invite_service.py`、
`project.py`、`auth.py`/`auth_service.py`、前端注册页与成员 Sheet

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 负责人生成链接（限次/有效期） | ✅ | `test_owner_generates_invite` + 冒烟 |
| 非负责人 403 | ✅ | `test_non_owner_cannot_generate` |
| 注册自动入项目 + 组织 | ✅ | `test_register_with_valid_token_joins_project_and_org` + 冒烟 |
| 无效/过期/用尽/停用 400 | ✅ | 4 条用例 |
| token 免除平台邀请码 | ✅ | 冒烟（INVITE_CODE_REQUIRED=true 下仅凭项目 token 注册成功） |
| 列表脱敏/停用 | ✅ | `test_list_invites_masked`、`test_disable_invite_rejects_registration` |
| 前端入口与注册页参数 | ✅ | vitest 扩展（按钮可见、invite 参数提交） |

### C4: US-04 超管与隔离不回归

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 超管全量 | ✅ | 全量回归 1133 passed（含 viewer/rbac/project_owner） |
| 隔离不回归 | ✅ | 组织/项目越权 403 用例保持通过 |

### C5: CI 分层核对

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 变更范围 | backend + frontend + deploy + docs + C-CONDITIONS | 双端 required jobs 均运行 |
| 本地等价门禁 | ✅ | 命令与退出码齐全 |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| B106-1 | P1 | Batch 103 合入产生 merge 迁移，新增迁移若以旧头为父会导致 Alembic 多头 | `alembic heads` 双头 → 修正 down_revision 后单头 | ✅ 已修复 |
| B106-2 | P3 | 前端 `isOwner(null)` TS 报错 | typecheck TS2345 | ✅ 已修复（null 守卫） |
| B106-3 | P3 | 注册测试 payload 断言未含新增字段 | vitest 1 失败 | ✅ 已修复 |

## 发布建议

状态: **READY**（生产切换为 C106-1 人工步骤，不阻塞代码合入）
必修复: 0   建议修复: 0

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 5–7h vs ≈6h | 0/1/0/2 | 2 | 外部批次合入 + 契约漂移 | 新批次开工先 `alembic heads` 确认基线头；前端 mock 断言用 objectContaining |

## 技能使用

- `cameltv-bug-guard` → Token 生成/迁移/权限避坑；
- `cameltv-ui-conventions` → 邀请链接 Dialog/注册页提示；
- `test-case-design` → 用例覆盖；
- KB 检索：本地证据替代运行中知识库（PATTERNS/work-logs），已记录。
