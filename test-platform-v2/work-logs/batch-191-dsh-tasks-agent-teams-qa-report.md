# Batch 191 — QA 报告

> **QA (🔍)** | Date: 2026-08-17 | Verdict: **PASS**（首轮 NEEDS WORK → 修复 02253b9 复验通过，见「复验记录」）

**批次**: /dsh-tasks 支持 AgentTeams 团队模式（方案 B1，六部门流水线第五棒）
**分支**: `feature/batch-191-dsh-tasks-agent-teams`（executor=DeepSeek_Harness，worktree=`F:\CamelTv-worktrees\DeepSeek_Harness-batch-191-dsh-tasks-agent-teams`）
**执行人**: qa（会话 905cbdde-998a-488d-9348-27d265dc84b3）
**依赖**: T4 Dev 交付 5 提交（db13ee6 / f190f14 / 89d1c09 / 242f31a / 9946059），36 文件 2917+/28-

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 12 | 12 | 0 | 0 |

- ✅ 后端专项 pytest（4 文件 56 用例）、ruff F821、Alembic 单头 + upgrade head
- ✅ 前端 typecheck、build、vitest（专项 9/9 + 全量 488/488，修复 02253b9 后全绿）
- ✅ 提交完整性、CI 分层、模板资产静态校验、C191-1/C191-2 判定
- ✅ R-1 真实冒烟（环境受限，如实记录 deferred——非代码缺陷，见 R-1 节）

## 可执行门禁（命令、退出码、日志摘要）

### 后端（venv=`F:\CamelTv\test-platform-v2\backend\.venv`，cwd=worktree `test-platform-v2/backend`）

| # | 命令 | 退出码 | 结果摘要 |
|---|------|--------|---------|
| B1 | `python -m pytest tests/test_dsh_tasks.py tests/test_dsh_runner.py tests/test_dsh_sandbox.py tests/test_agent_team_persona.py` | 0 | **56 passed** in 2.83s（1 warning：StarletteDeprecation，无失败） |
| B2 | `python -m pytest`（全量回归） | 1 | **1606 passed, 5 failed, 3 skipped** in 384s；5 失败全部为 lanhu-mcp 子模块/既有基线（见 B2a/B2b），**本批 0 新增失败** |
| B2a | 子模块未初始化（worktree 环境）：`test_deploy_compose_contract::test_backend_build_context_contains_runner_and_root_lanhu_submodule`（断言 `lanhu-mcp/lanhu_mcp_server.py` is_file=False）、`test_lanhu_provider::test_backend_declares_all_pinned_lanhu_runtime_dependencies`（FileNotFoundError `lanhu-mcp/requirements.txt`） | — | `git submodule status` 显示 `-3cfd2ef... lanhu-mcp`（未初始化）；**CI 环境子模块初始化后不受影响**；非批次缺陷 |
| B2b | 既有基线（在 main 检出 `F:\CamelTv` 同命令复现 3 failed）：`test_lanhu_login_hook` ×2、`test_lanhu_provider::test_pinned_runtime_provides_login_hooks` | 1 | main 检出（子模块已初始化）仍 3 failed → **基线失败，非本批引入** |
| B3 | `python -m ruff check app --select F821` | 0 | **All checks passed!**（ruff 0.16.1） |
| B4 | `python -m alembic heads` | 0 | 单头：`20260817_b191_dsh_team_mode (batch27) (head)` |
| B5 | `python -m alembic upgrade head` + `alembic current` | 0 | upgrade 可执行；current = `20260817_b191_dsh_team_mode (head)`；迁移 down_revision=`20260816_b182_status_unify` 与设计规范一致 |

### 前端（cwd=worktree `test-platform-v2/frontend`，node v24.15.0）

| # | 命令 | 退出码 | 结果摘要 |
|---|------|--------|---------|
| F1 | `npm run typecheck`（tsc -b） | 0 | 通过 |
| F2 | `npm run build`（tsc -b && vite build） | 0 | ✓ built in 14.62s |
| F3 | `npx vitest run src/pages/dsh-tasks/__tests__/index.test.tsx src/pages/dsh-tasks/__tests__/team-progress.test.tsx` | 1 | **2 files failed, 7 failed \| 2 passed**（详情见缺陷 #1/#2/#3/#4） |
| F4 | `npx vitest run`（全量回归） | 1 | **3 files failed \| 115 passed；8 failed \| 480 passed**（488）— 8 失败全部指向批次新增文件（dsh-tasks 两个测试文件 7 个 + `team-progress.tsx:77 transition-all` 触发 batch54 治理 1 个）；无其他基线失败 |
| F5 | npm ci | 跳过 | 批次无任何依赖清单变更（diff 无 package.json/package-lock/pnpm-lock/requirements*），node_modules 已存在；重装不增加信息 |

### 真实冒烟（R-1，node `agent-team` profile）

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| R1a | `$DSH_HOME/profiles/agent-team` 已创建 | ❌ | `$DSH_HOME=C:\Users\26029\.dsh`；profiles/ 仅 headless、node_modules、web；**agent-team 未安装**（设计定位：安装位在 $DSH_HOME/profiles/agent-team，不入库，按 `backend/app/services/dsh/agent-team/README.md` 安装指引由运维执行） |
| R1b | CLI `--profile agent-team` 解析行为 | ✅ 机制正确 | `node F:\deepseek-harness\apps\cli\lib\bin.js --profile agent-team --dump-config` → **exit 1**，报错 `dsh: profile "agent-team" does not exist; create it with 'dsh plugin --profile agent-team add <package>'`（app-boot loadProfile）；控制组 `--profile headless --dump-config` → **exit 0** 正常输出组合配置。CLI 从 `$DSH_HOME/profiles/` 解析的设计语义成立 |
| R1c | 平台端到端团队任务冒烟 | ❌ 环境受限 | worktree `.env` **无任何 DSH_\* 配置**（`dsh_enabled=False` 默认）→ 平台无 harness 路径/凭据，`/dsh-tasks` 提交任务会走 `dsh_unavailable_reason`（DSH 未启用）；本机无凭据授权给批次冒烟 |
| R1d | 安装模板资产静态校验 | ✅ | `cordis.patch.yml.template` YAML 解析 OK（insert `@nanmicoder/dsh-agent-teams` 插件行 + stateDir/memberProvider）；`package.json.template` JSON 解析 OK（dsh-profile-agent-team，deps `^0.1.5`）；`team.cordis.yml` = minimal + agent-teams 行 |

**R-1 结论**: 环境受限 deferred。CLI 解析机制、模板资产、runner 路由（`--profile agent-team` 仅当 profile 存在才可运行）均已可执行验证；真实 mini 团队冒烟需（a）`dsh plugin --profile agent-team add @nanmicoder/dsh-agent-teams` 安装 profile（运维步骤，README 有指引），（b）平台 `.env` 配置 DSH_ENABLED/DEEPSEEK 凭据/harness 路径。**非代码缺陷，属交付环境未就绪**，建议 Leader 列为合入后运维跟进项（与 C191-1 同族）。

### C191-1 判定（python-sdk bundled runtime 加载 npm bundle 插件可行性）

**判定：deferred 成立（维持 Dev 建议，依据补充）**

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 本机 SDK 环境 | ❌ 无 | venv 中 `importlib.util.find_spec('deepseek_harness_sdk'/'deepseek_harness')` → None；pip 无 harness 包 |
| bundled runtime 架构 | 已核实 | `F:\deepseek-harness\python\sdk-runtime`：bundled runtime = **单文件预编译可执行体**（`runtime/dsh-jsonrpc-agent-pkg-{tag}`）+ 内置默认 cordis.yml；本机无该平台二进制（`resolve_bundled_launch_args` 语义=缺失即报错，sdk-runtime `__init__.py:124`） |
| 团队 cordis 路径防护（US-7） | ✅ 代码+测试 | `dsh_runner.py:273-292`：python-sdk 团队分支显式解析 `team.cordis.yml`（或 `DSH_TEAM_CORDIS_CONFIG` 覆盖），缺失 → exit 1 + 可读 error，**无静默 fallback**；`test_run_team_python_sdk_uses_team_cordis` / `test_run_team_python_sdk_custom_cordis` 覆盖 |
| 判定依据 | — | 本机无 SDK + 无 bundled 二进制 → **不可实测**；架构上 bundled 单文件运行时的外部 npm bundle 插件加载面只能在生产 Linux SDK 目标上验证。解除条件（C-CONDITIONS C191-1 原文）：SDK bundled runtime 可加载 npm bundle 插件并完成团队组合冒烟 → 成功后关闭 |

### C191-2 判定（running 团队任务取消延后）

**判定：成立（代码事实核实）**

- `dsh_task_service.py:129-136`：`cancel_task` 仅 `pending` 可取消，running → 返回不可取消；执行线程/轮询线程无 kill 信号路径
- C-CONDITIONS.md 已登记：C191-2 P3，解除条件=下批实现执行中终止（kill 子进程/信号）+ 轮询线程停止覆盖
- 与 PRD 非目标（running 取消延后）一致，非缺陷

### 提交完整性

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 5 个开发提交 | ✅ | db13ee6（T1/T2 配置+迁移）/ f190f14（T3/T4/T5 schema+runner+资产）/ 89d1c09（T6 团队分支+轮询线程）/ 242f31a（T7/T9 测试+前端）/ 9946059（T10 文档+看板+C191 登记）；分支领先 main 8 提交（+3 文档提交） |
| 无夹带（diff-classifier-baseline.json） | ✅ | 分支 diff 中不存在（revert 确认）；`git log origin/main..HEAD -- test-platform-v2` 无该文件 |
| worktree 干净 | ✅ | `git status`：nothing to commit；`--porcelain` 0 行 |
| worktree 元数据 | ✅ | `.ai-worktree.json`：workflow=agent-team、executor=DeepSeek_Harness、branch/base 匹配、completion 待确认 |
| 变更范围 | ✅ | 31 文件全部落在 backend / frontend / docs / work-logs / C-CONDITIONS.md（文档注册表）；无 .claude/skills、scripts/git、依赖清单改动 |
| 前后端契约一致 | ✅ | `createDshTask(task, params, mode)` ↔ 后端 `DshTaskCreate.mode Literal[single,team]` + `model_validator` 校验 batch_mode（前端测试断言 `createDshTask('跑回归', {batch_mode:'full'}, 'team')`） |

### CI 分层结论

本批变更同时含 **backend 代码**（models/schemas/services/api/alembic）+ **frontend 代码**（pages/api/tests）+ 文档 → 按 AGENTS.md §4.2 属混合/双端 → **双端 required 全量**（main-quality-gate 对 backend 域跑后端 required、frontend 域跑前端 required，混合保守双端）。本地已按同口径执行双端全量（B2/F4），与 CI 分类结论一致。

## 逐条件验证

### C191-1: python-sdk bundled runtime 加载 npm bundle 插件（deferred 判定）
**变更文件**: `backend/app/services/dsh/dsh_runner.py:249-292`、`backend/app/services/dsh/team.cordis.yml`、C-CONDITIONS.md
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 本机 SDK/bundled 二进制存在 | ❌ | find_spec=None；sdk-runtime 无平台二进制 |
| 不可测 → deferred 依据充分 | ✅ | 单文件 bundled 架构核实 + US-7 无静默 fallback 代码/测试双证 |
| 登记格式 | ✅ | C-CONDITIONS.md 含 ID/内容/优先级/解除条件；`最后更新` 行已同步 |
**✅ PASS（deferred 判定成立）**

### C191-2: running 团队任务取消延后
**变更文件**: `backend/app/services/dsh/dsh_task_service.py:129-136`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 仅 pending 可取消 | ✅ | 代码行 134-136 |
| 登记 | ✅ | C191-2 P3 + 解除条件 |
**✅ PASS**

### R-1: node `agent-team` profile 真实可用性
| 检查项 | 结果 | 说明 |
|--------|------|------|
| profile 已创建 | ❌ | $DSH_HOME/profiles 无 agent-team（运维安装步骤，未执行） |
| CLI 解析机制 | ✅ | 缺失报错清晰（exit 1）+ headless 控制组 exit 0 |
| 端到端冒烟 | ❌ 环境受限 | .env 无 DSH 配置、无凭据 |
**⚠️ PASS（机制）+ DEFERRED（端到端）— 环境受限如实记录**

### 后端门禁（B1-B5）
**✅ 全部 PASS**（56 专项全绿；全量 0 新增失败；F821 干净；Alembic 单头+upgrade 可执行）

### 前端门禁（F1-F4）
**✅ PASS（修复 02253b9 后复验）** — 首轮 vitest 8 失败全部批次引入；修复提交后专项 9/9、全量 488/488 全绿（见「复验记录」）

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | **P1** | `team-progress.tsx:36` `currentTaskFor` 用 `task.assignee === memberId`（m.id）匹配；真实插件 team.json 中 `task.assignee`=成员**名**、`member.id`=session id（插件 snapshot.js:16/57 语义 = `assignee === member.name`）→ **生产环境成员「当前任务」恒显「—」**，核心功能不可用 | vitest `team-progress.test.tsx:73` 失败（fixture 忠实真实数据：id='m2' vs assignee='qa'）；本团队实时 team.json（members[].id=session id、tasks[].assignee='product'/'pm'/…） | ✅ 已修复（02253b9：按 `m?.name` 匹配，复验通过） |
| 2 | **P2** | `index.test.tsx:20` useAuthStore mock `() => ({ hasPerm: () => true })` 未应用 selector，组件 `useAuthStore((s)=>s.hasPerm)` 拿到整个 state 对象 → `TypeError: hasPerm is not a function` → 该文件 5 个测试全挂 | vitest index.test.tsx 5 failed（首个错误堆栈 index.tsx:44）；仓库正确范式：`WikiTabAvailability.test.tsx:15` `(selector) => selector({...})` | ✅ 已修复（02253b9：selector mock，复验通过） |
| 3 | **P2** | `team-progress.tsx:77` `transition-all` 违反 Batch 54 生产 UI 治理（动效必须显式限定 transform/opacity/color 等属性）→ 治理测试失败 | vitest `batch54-production-governance.test.ts`「动效必须显式限定属性（共 1 处）pages/dsh-tasks/team-progress.tsx:77」 | ✅ 已修复（02253b9：`transition-[width]`，全量 vitest 含治理测试通过） |
| 4 | P3 | `team-progress.test.tsx:34` `getByText('执行中')` 歧义（团队头 stage 徽标 + in_progress 任务徽标共 2 处）→ Found multiple elements | vitest 失败日志 | ✅ 已修复（02253b9：`getAllByText` 精确计数 ×2，复验通过） |
| 5 | P3 | 看板 `work-logs/kanbans/DEV-batch-191-dsh-tasks-agent-teams.md` 行 3/4/5 引用提交 `8e2d4d0` 不存在（实际 `f190f14`） | `git log --all` 无 8e2d4d0 | ✅ 已修复（02253b9：改 f190f14，行 4 补充 242f31a 修正说明） |
| 6 | P3 | R-1 真实冒烟未完成：agent-team profile 未安装 + 平台 DSH 未启用（环境受限，非代码缺陷） | R1a/R1c 证据 | deferred（运维跟进，待 Leader 判决） |

修复建议（供 Dev/Leader，**已全部按此应用**于提交 02253b9，见「复验记录」）：
1. #1：`team-progress.tsx` 改 `task?.assignee === m?.name`（与插件 snapshot.js 语义一致；测试 fixture 保持真实数据形态不变）
2. #2：mock 改 `useAuthStore: (selector: any) => selector({ hasPerm: () => true })`
3. #3：`transition-all` → `transition-[width]`（进度条仅宽度变化）
4. #4：`getAllByText('执行中').length >= 2` 或限定容器查询

## 复验记录（2026-08-17，修复提交 02253b9）

QA 打回项由 dev 修复（提交 `02253b9`，4 文件 51+/28-），QA 在 worktree 实跑复验：

| # | 命令 | 退出码 | 结果 |
|---|------|--------|------|
| V1 | `npx vitest run src/pages/dsh-tasks/__tests__/index.test.tsx src/pages/dsh-tasks/__tests__/team-progress.test.tsx` | 0 | **2 files / 9 tests passed**（首轮 7 failed → 0） |
| V2 | `npx vitest run`（全量） | 0 | **118 files / 488 tests passed**（首轮 8 failed → 0；含 batch54 治理测试） |
| V3 | `npm run typecheck` | 0 | 通过 |
| V4 | `npm run build` | 0 | ✓ built in 8.75s |

- P1 复验点：`team-progress.test.tsx`「成员当前任务推导」通过（断言 `当前：门禁回归` 与 `当前：—`），且组件 diff 确认 `currentTaskFor/doneRatio` 按 `m?.name` 匹配（与插件 snapshot.js 语义一致）
- P2 复验点：`index.test.tsx` 5 用例通过（selector mock 生效）；治理测试通过（`transition-[width]`）
- P3 复验点：`getAllByText('执行中').length===2` 精确计数通过；看板 diff 确认 8e2d4d0 → f190f14（行 4 补充 242f31a 修正说明）
- 测试基建修复（scrollIntoView polyfill、advanceTimersByTimeAsync、pending 隔离列表轮询）不改变被测行为，V2 全量无回归
- 后端门禁未受修复影响（仅前端 4 文件），维持首轮 B1-B5 全绿结论

**结论：5 项修复（P1×1/P2×2/P3×2）全部闭环，前端门禁由 FAIL 转 PASS。**

## 发布建议

状态: **READY（QA 门禁侧）**   必修复: **0**（首轮 3 项已闭环）   建议修复: 0（首轮 P3×2 已闭环）   deferred 跟进: 1（#6 R-1 运维跟进，非代码缺陷）

- QA 门禁全部通过：后端 B1-B5 全绿、前端 typecheck/build/vitest（专项 9/9 + 全量 488/488）全绿、提交完整性/CI 分层核对通过
- R-1/C191-1 属环境受限 deferred（agent-team profile 未安装、平台 DSH 未启用、本机无 SDK），建议 Leader 判决时给出运维跟进条件（安装 profile + 平台 DSH 配置后补真实冒烟；C191-1 解除条件=生产 Linux SDK 环境实测）
- CI 预期：main-quality-gate 双端 required；后端域全量在 CI（子模块初始化）预期 3 个既有基线失败（test_lanhu_login_hook ×2、test_lanhu_provider::test_pinned_runtime_provides_login_hooks），前端域预期 0 失败——本批无新增失败
- 合入前请按 AGENTS.md §2.3 完成总确认流程（推送 + Draft PR + required checks 全绿后 Leader APPROVED）

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 2h vs ~2.5h（全量回归 384s pytest + 45s vitest + 冒烟核查）；复验 +0.3h | 0/1/2/3 | 1（QA 打回→dev 修复→复验闭环，一次通过） | ①字段语义未对齐真实数据（assignee=name vs id，组件照搬后端 fixture 的 id 概念）；②测试 mock 范式未对照仓库既有模式（selector 型 mock）；③治理规则（transition-all）未纳入 Dev 自检清单 | 前端消费插件/外部数据前，先对照真实数据样本（如插件 snapshot.js 语义）确认字段身份；新增测试文件先 grep 仓库同款 mock 范式；PR 前跑一次全量 vitest（45s 成本）而非只跑新增文件；修复提交前自查 Batch 54 治理规则 |

**技能使用**:
- `cameltv-agent-team`（DEPARTMENTS.md §5 QA 模板）→ QA 报告结构/严重级/复盘卡格式
- `cameltv-api-test` 未启用（本批为 pytest/vitest 门禁，非 API 用例编写）— 备注
- 测试证据全部为可执行命令输出（pytest/vitest/ruff/alembic/node CLI），无目测代替执行
