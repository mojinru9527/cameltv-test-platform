# Batch 104 — Leader Verdict（外放轻量模式）

> **Leader (🎯)** | Date: 2026-08-06 | Decision: APPROVED（待用户一次总确认 + PR required checks 全绿后合入）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 通过 | 后端 21 新测试 + 全量 1097 通过；前端 347 测试 + typecheck + build 全绿 |
| 风险 | 低 | 注册默认关闭（生产），邀请码强制，注册限流，项目配额，所有者级权限收敛 |
| 覆盖 | 通过 | US-01~05 全覆盖；越权 403、配额 400、重复 400/422、限流 429 均有断言 |

## 关键决策（已批准）

1. **外放采用「用户自助 + 邀请码」轻量模式**：注册必须邀请码（默认），生产默认关闭注册开关，
   灰度时由运维显式开启 —— 避免匿名注册与资源滥用。
2. **创建项目即成为负责人+成员**：修复既有「创建后不可见」缺口；所有者管理自己项目无需全局权限点，
   超管 `*` 权限与全量可见性保持不变。
3. **个人项目配额**（默认 5）作为外放后的第一道资源护栏；超管不限。
4. **租户/组织层明确不纳入本批**：由下一批次（C104-1）在合并后最新 main 上实施。

## 抽检通过

- ✅ `backend/app/services/project_service.py:create_project` — 自动 `ProjectMember` + 配额校验；
- ✅ `backend/app/core/deps.py:require_project_owner_or` — 超管/所有者/全局权限三分支，成员校验保留；
- ✅ `backend/app/api/v1/auth.py:register` — 开关 403 → 限流 429 → 注册 → cookie 自动登录；
- ✅ `backend/app/seed.py` — `system:invite:manage`、`project:self_create`、`menu:myproject` 幂等；
- ✅ `backend/alembic/versions/20260806_batch104_invite_code.py` — 单头（`alembic heads` 验证）；
- ✅ `frontend/src/pages/my-projects/index.tsx` — 负责人徽标/成员 Sheet/停用确认/四态齐备；
- ✅ `frontend/src/pages/register/index.tsx` — zod 校验、内联错误、成功跳转；
- ✅ 门禁：ruff F821 0、app 导入 OK、scan-common-bugs HARD 0、audit-cconditions 0 硬错、
  vitest 347/347、pytest 1097 passed/3 skipped（退出码 0 记录于 QA 报告）。

## 判决

**APPROVED**。QA 硬门禁全绿、缺陷清单 0 阻塞（P2×1 已修复、P3×3 已修复）。
合入前置：① 用户一次总确认（推送 + Draft PR + required checks 通过后合入）；
② PR 首轮审计 `audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex`；
③ required checks 全绿后最终审计（`-RequireSuccessfulChecks`）。

## 下一批次 Leader 条件

- **C104-1**: 租户/组织层（用户 → 组织 → 项目）批次必须在 batch-104 合入后从最新 `origin/main`
  创建；设计含 `organization_id` 预留、组织成员两级权限与数据迁移方案。
- **C104-2**: 生产启用注册前须由用户确认：`REGISTRATION_ENABLED=true`、
  `INVITE_CODE_REQUIRED=true`、邀请码发放流程与配额监控；确认结果登记到交付清单。
- **C104-3**: 仓库 `frontend/src/types/api.d.ts` 用锁定版本 openapi-typescript 全量重生成，
  核对 28k 行漂移根因（工具版本差异），并将「契约漂移」纳入后续批次自检或 CI 校验。
- **C104-4**: 评估「项目邀请链接」（同事凭链接注册并自动加入项目）作为下一阶段增强，
  需要通知链路与注册-入项目原子化设计。
- **C104-5**: 编辑工具落点校验：后续批次开工首个补丁必须验证写入目录为任务 worktree
  （`git status` 在 worktree 内核对），防止写入控制工作区。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 编辑工具默认以会话目录为根，首轮补丁写入控制工作区 | 已恢复主干 + 改用 `../CamelTv-worktrees/...` 前缀；经验写入本地开发备忘 | `docs/agent-team/local-dev-workflow.md` 常见坑表 + C104-5 |
| 新增迁移后既有测试硬编码迁移头导致全量回归失败（测试陈旧） | 修复为动态读取单头，后续批次不再踩 | `backend/tests/test_batch48_requirement_migration.py` |
| api.d.ts 与生成工具版本差异巨大（预存漂移） | 本批最小手工契约同步；全量重生成留 C104-3 | C104-3 |
| 外放后匿名注册风险 | 开关默认关闭 + 邀请码 + 限流 + 配额（决策已批准） | PRD §5 / 本判决 |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 3–5h vs ≈4h | 0/0/1/3 | 1 | 工具链 + 测试陈旧 | 首个补丁先验证 worktree 落点；新迁移后先跑头断言测试 |

## 技能使用

- `cameltv-agent-team` → 流水线事实源；
- `cameltv-bug-guard` / `cameltv-ui-conventions` / `test-case-design` → 见 QA 报告「技能使用」；
- 知识审计：本批「创建项目自动成员」「所有者权限依赖」「补丁落点教训」具备入库价值，随
  C104-1/2/3/4/5 与流程回写跟踪，未单独 ingest（本批无运行中知识库后端，记录于工件）。
