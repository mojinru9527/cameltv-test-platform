# Batch 47 Requirement Service Production Acceptance Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 对最新 `origin/main` 的测试平台需求服务模块完成可交付生产级功能回归与验收，补齐需求、接口、UI、权限、数据一致性及异常场景覆盖，并形成可追溯的验收结论。

**Architecture:** 以仓库 PRD、历史验收报告和 Batch 46 的 27 项修复为需求基线，先建立功能点与接口清单，再分层执行后端单元/API、前端静态门禁和浏览器端到端验收。所有发现必须包含可复现步骤、实际结果、预期结果、严重级别和证据；本批默认只补测试资产与文档，不修改生产实现。

**Tech Stack:** FastAPI、SQLAlchemy 2.0、SQLite/Alembic、Pytest、React 18、TypeScript、Vite、Vitest、Playwright

**Execution Status (2026-07-27):** Task 1～7 已执行并形成 `NEEDS WORK` 结论；Task 8 正在执行，首次 push/PR/checks 后按 Agent Team 规则等待用户再次授权最终审计与合并。

---

### Task 1: 固化版本、环境与验收基线

**Files:**
- Read: `docs/测试平台全功能验收文档-环境链接与账号汇总.md`
- Read: `test-platform-v2/docs/测试平台-完整PRD.md`
- Read: `test-platform-v2/docs/现状功能PRD.md`
- Read: `test-platform-v2/docs/测试平台使用手册.md`
- Read: `work-logs/batch-34-测试平台V2初版验收报告-2026-07-23.md`
- Read: `work-logs/kanbans/DEV-batch-46-bugfix.md`
- Create: `tests/test-cases/functional/BATCH47-测试平台需求服务-生产级验收.md`

- [ ] **Step 1: 记录被测版本与 worktree 元数据**

Run: `git rev-parse HEAD; git status --short --branch; Get-Content .ai-worktree.json`

Expected: HEAD 为最新 `origin/main`，分支为 `feature/batch-47-requirement-service-acceptance`，工作区干净，workflow/executor 为 `agent-team/codex`。

- [ ] **Step 2: 建立功能点清单**

在验收用例文档中逐项列出文档上传、蓝湖证据、功能提取、确认/驳回、AI 生成、结果回看、持久化评审、选择性导入、版本差异、API 匹配、覆盖率、模块树及跨系统关联。

Expected: 每个功能点均有需求来源、实现入口和至少一条正面、一条负面用例。

- [ ] **Step 3: 建立主流程与异常流程**

主流程为“上传/创建需求 → 提取并确认 → AI 生成 → 评审 → 导入用例库 → 覆盖率验证”；异常流覆盖未授权、缺项目、跨项目、文件非法、AI 不可用、重复提交、部分失败和删除。

Expected: 场景矩阵中的每个条件都有 `V` 或 `I`，不存在空白覆盖项。

- [ ] **Step 4: 对照 Batch 46 的 27 项修复**

Run: `git show --stat --oneline a68e492; git show --format=fuller --no-patch a68e492`

Expected: 6 个 P0、5 个 P1、7 个 P2、9 个 P3 均能映射到回归检查或明确说明不可执行原因。

### Task 2: 准备隔离测试环境

**Files:**
- Read: `.ai-worktree.json`
- Read: `test-platform-v2/backend/.env`
- Read: `test-platform-v2/frontend/.env.local`
- Verify: `test-platform-v2/backend/app/core/config.py`
- Verify: `test-platform-v2/frontend/vite.config.ts`

- [ ] **Step 1: 检查依赖和端口**

Run: `Test-Path test-platform-v2/backend/.venv; Test-Path test-platform-v2/frontend/node_modules; Get-NetTCPConnection -State Listen`

Expected: 后端使用 Batch 47 独立端口 `8006`；按用户指定，最终浏览器验收入口为开发环境 `http://127.0.0.1:5173/`。`.ai-worktree.json` 中的前端预留端口 `5179` 不用于最终 UI 验收。

- [ ] **Step 2: 安装缺失依赖**

Run: `python -m pip install -r requirements.txt`（后端，仅在独立虚拟环境缺依赖时）

Run: `npm ci`（前端，仅在 `node_modules` 不可用时）

Expected: 两端依赖安装成功且不改动锁文件。

- [ ] **Step 3: 校验数据库与迁移**

Run: `python -m alembic heads`

Run: `python -m alembic upgrade head`

Run: `python -m alembic check`

Expected: 单一 head，upgrade/check 退出码 0；测试数据只写 Batch 47 独立数据库。

- [ ] **Step 4: 启动后端与前端**

Run: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8006`

Run: `$env:VITE_DEV_PORT='5173'; $env:VITE_PROXY_TARGET='http://127.0.0.1:8006'; npm run dev -- --host 127.0.0.1 --port 5173`

Expected: `http://127.0.0.1:8006/health` 正常，`http://127.0.0.1:5173/requirement` 可登录访问。

### Task 3: 执行代码质量与既有回归

**Files:**
- Test: `test-platform-v2/backend/tests/test_requirement.py`
- Test: `test-platform-v2/backend/tests/`
- Test: `test-platform-v2/frontend/src/`

- [ ] **Step 1: 执行后端硬门禁**

Run: `python -m ruff check app/ --select F821`

Expected: exit 0。

- [ ] **Step 2: 执行需求模块定向回归**

Run: `python -m pytest tests/test_requirement.py -vv --tb=short`

Expected: Batch 46 新增的 15 条回归测试及本文件全部通过。

- [ ] **Step 3: 执行相关后端测试**

Run: `python -m pytest tests/ -q --tb=short`

Expected: 记录总数、通过数和完整失败集合；不得仅写“历史失败”。

- [ ] **Step 4: 执行前端硬门禁**

Run: `npm run typecheck`

Run: `npm run build`

Expected: 两条命令均 exit 0。

- [ ] **Step 5: 执行前端回归**

Run: `npm test -- --run`

Expected: 记录测试文件数、用例数及完整失败集合。

### Task 4: 补齐并执行后端/API 验收

**Files:**
- Modify if needed: `test-platform-v2/backend/tests/test_requirement.py`
- Test: `test-platform-v2/backend/app/api/v1/requirement.py`
- Test: `test-platform-v2/backend/app/api/v1/requirement_modules.py`
- Test: `test-platform-v2/backend/app/services/requirement_service.py`

- [ ] **Step 1: 生成 OpenAPI 契约清单**

Run: `python -c "from app.main import app; import json; print(json.dumps({k:list(v) for k,v in app.openapi()['paths'].items() if 'requirement' in k}, ensure_ascii=False, indent=2))"`

Expected: 每个需求接口的 method、URL、请求 schema 和响应 schema 可追溯。

- [ ] **Step 2: 先写缺失的失败回归测试**

覆盖参数边界、缺项目、无权限、跨项目、重复提交、非法文件、超大文件、未生成先导入、无效索引、部分导入回滚、删除关联数据和审计失败不影响主业务。

Expected: 每个新增用例先能证明目标风险存在或证明现有实现已正确拒绝。

- [ ] **Step 3: 执行新增定向测试**

Run: `python -m pytest tests/test_requirement.py -vv --tb=short`

Expected: 正常行为测试通过；任何生产实现缺陷保留失败证据并登记，不直接修改业务代码。

- [ ] **Step 4: 验证返回值与数据库副作用**

对创建/上传/确认/生成/评审/导入/删除接口同时断言 HTTP 状态、业务 envelope、核心返回字段、数据库记录和审计记录。

Expected: 不以页面 toast 或 `code=0` 作为唯一成功依据。

- [ ] **Step 5: 验证可靠性与并发**

对重复导入、并发确认、并发删除与分页大列表执行最小风险验证。

Expected: 无重复记录、脏数据、500、死锁或跨项目泄露；否则登记缺陷。

### Task 5: 执行浏览器功能与 UI 验收

**Files:**
- Test: `test-platform-v2/frontend/src/pages/requirement/index.tsx`
- Test: `test-platform-v2/frontend/src/pages/requirement/ReviewPage.tsx`
- Test: `test-platform-v2/frontend/src/pages/requirement/AiResultModal.tsx`
- Test: `test-platform-v2/frontend/src/pages/requirement/ExtractionModal.tsx`
- Test: `test-platform-v2/frontend/src/pages/requirement/components/`
- Evidence: `work-logs/evidence/batch-47-requirement-service/`

- [ ] **Step 1: 自动检测本地服务**

Run: `node -e "require('./lib/helpers').detectDevServers().then(servers => console.log(JSON.stringify(servers)))"`（在 Playwright skill 目录执行）

Expected: 识别用户指定的开发环境 `http://127.0.0.1:5173`；后端请求经代理进入 Batch 47 的 `8006`。

- [ ] **Step 2: 执行桌面端核心闭环**

以可回收测试数据完成需求上传、提取、确认、生成、评审、选择性导入、列表刷新、结果回看和删除。

Expected: 每一步 UI 状态、网络请求次数、响应、数据库结果一致；每个 GET 只有一次有效请求。

- [ ] **Step 3: 执行异常与恢复场景**

验证空输入、非法格式、超大文件、AI 失败、请求超时、重复点击、关闭重开、刷新恢复、404、403、500 友好提示。

Expected: 页面不崩溃、不丢失已持久化评审结果，可取消或重试，错误提示可操作。

- [ ] **Step 4: 执行权限与项目隔离场景**

使用 admin 与 tester 权限组合，并切换两个项目验证列表、详情、写操作和直接 URL。

Expected: 前端按钮与后端权限一致；跨项目 ID 不可读取或修改。

- [ ] **Step 5: 执行响应式、键盘与可访问性检查**

视口至少覆盖 `1440x900`、`768x1024`、`375x812`；检查 Tab 顺序、对话框焦点、键盘关闭、标签、按钮名称、溢出与横向滚动。

Expected: 核心任务在桌面可完成；移动端若不承诺完整操作，至少不得遮挡、不可恢复或导致数据误操作。

- [ ] **Step 6: 保存证据**

保存关键页面截图、控制台错误、失败请求摘要和响应时间，不保存密码、Token、Cookie 或真实敏感数据。

Expected: 每条失败用例至少有一个可定位证据。

### Task 6: 形成验收结论并补齐测试资产

**Files:**
- Create: `work-logs/batch-47-需求服务生产级验收报告-2026-07-27.md`
- Modify: `tests/test-cases/functional/BATCH47-测试平台需求服务-生产级验收.md`
- Modify if stale: `test-platform-v2/docs/现状功能PRD.md`
- Modify if stale: `test-platform-v2/docs/测试平台使用手册.md`

- [ ] **Step 1: 回填全部用例执行结果**

每条用例记录通过/失败/阻塞、实际结果、执行人、证据和缺陷编号。

Expected: P0/P1 全部有结果；阻塞必须说明外部依赖和已完成的替代验证。

- [ ] **Step 2: 输出覆盖率矩阵**

按功能点统计基本流、负面、边界、权限、接口返回、数据库副作用、UI、兼容和可靠性覆盖。

Expected: 基本功能点覆盖率 100%，每个需求点至少一正一负；未达标项明确列为缺口。

- [ ] **Step 3: 登记缺陷**

缺陷标题采用“测试平台-需求服务-功能：操作产生现象”，并包含版本、环境、账号角色、前置条件、复现步骤、实际/预期、严重程度、优先级、复现概率和证据。

Expected: 致命/严重问题阻断 READY；一般问题依据版本门槛计算是否可发布。

- [ ] **Step 4: 给出生产级判定**

结论只能为 `READY`、`CONDITIONAL` 或 `NEEDS WORK`，并列出必修复、建议修复、阻塞和复测范围。

Expected: 结论可由命令退出码、用例结果和证据独立复核。

- [ ] **Step 5: 执行文档和测试资产自检**

Run: `rg -n "TODO|TBD|系统内部错误|请联系管理员" docs/superpowers/plans/2026-07-27-batch-47-requirement-service-acceptance.md tests/test-cases/functional/BATCH47-测试平台需求服务-生产级验收.md work-logs/batch-47-需求服务生产级验收报告-2026-07-27.md`

Expected: 无占位符；若引用错误文案，仅出现在实际缺陷证据中并注明。

### Task 7: 提交前本地门禁

**Files:**
- Verify: all Batch 47 changed files

- [ ] **Step 1: 审查变更范围**

Run: `git status --short; git diff --check; git diff --stat`

Expected: 只包含 Batch 47 测试资产、报告和经验证的测试补充，无凭据、数据库、截图敏感信息或无关变更。

- [ ] **Step 2: 重跑受影响域门禁**

Run: `python -m ruff check app/ --select F821`

Run: `python -m pytest tests/test_requirement.py -vv --tb=short`

Run: `npm run typecheck`

Run: `npm run build`

Run: `npm test -- --run`

Expected: 记录全部退出码与失败集合，满足仓库提交前自检要求。

- [ ] **Step 3: 复核计划覆盖**

逐项对照本计划、PRD 和验收用例文档，确认没有未解释的空白需求点、占位符或类型/字段漂移。

Expected: QA 报告中的功能点、用例、证据和结论一一可追溯。

### Task 8: Push、PR 与合并 main

**Files:**
- Verify: `.github/pull_request_template.md`
- Verify: `scripts/git/audit-ai-pr.ps1`
- Verify: `scripts/git/confirm-agent-team-completion.ps1`

- [ ] **Step 1: 向用户展示变更摘要**

按 `AGENTS.md` 模板列出分支、目标 `main`、变更文件、自检结果和风险。

Expected: 只包含 Batch 47 范围文件，并明确所有失败、阻塞和基线差异。

- [ ] **Step 2: 提交并 push 功能分支**

Run: `git push -u origin feature/batch-47-requirement-service-acceptance`

Expected: 只 push 功能分支，绝不直接 push `main`。

- [ ] **Step 3: 创建 Draft PR 指向 main**

Run: `gh pr create --draft --base main --head feature/batch-47-requirement-service-acceptance --title "test(batch-47): 需求服务生产级回归与验收" --body-file <qa-summary-file>`

Expected: Draft PR 创建成功，base 为 `main`。

- [ ] **Step 4: 基础审计并等待首轮 checks**

Run: `pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex`

Expected: 基础审计通过，并取得最新提交的 required checks 结果。

- [ ] **Step 5: 再次向用户确认执行器与最终合并授权**

首轮 checks 完成后，明确询问“实际执行器仍为 Codex 吗，是否授权最终审计与合并？”并停止等待。

Expected: 只有收到用户明确确认后才能继续。

- [ ] **Step 6: 记录完成确认并执行最终审计**

Run: `pwsh scripts/git/confirm-agent-team-completion.ps1 -Executor codex -UserConfirmedCompletion`

Run: `pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex -RequireSuccessfulChecks`

Expected: 完成确认证据已推送，required checks 全绿，最终审计通过。

- [ ] **Step 7: 将 PR squash merge 到 main**

通过 GitHub PR 执行 squash merge。

Expected: PR 已合并到 `main`，功能分支交付完成；不在本地或远端直接 push `main`。
