# 子项目 B 设计：/dsh-tasks 支持 AgentTeams 团队模式

> 日期：2026-08-17 | 状态：设计已批准（方案 B1） | 批次模式：完整批次
> 批次：batch-191-dsh-tasks-agent-teams | 执行器：DeepSeek_Harness（模式②船长工作流，自举）

## 1. 背景与目标

test-platform-v2 已通过 ADR-0018 接入 DeepSeek Harness 执行能力：A（用例生成 harness 模式）、
B（Agent 工作台执行型 Agent）、C（DSH 任务执行模块 `/api/v1/dsh-tasks/*`，Batch 172/181/184）。
当前 C 模块是**单任务形态**：提交自然语言任务 → worker 调 `run_dsh_task` 一次执行 → 输出落库。

Batch 190 已将仓库级 Agent Team 流水线移植为 DSH AgentTeams 船长模式（模式②）。用户要求把同一能力
接入测试平台产品：**平台用户提交一个自然语言目标，平台以 DSH 船长会话执行（dsh-agent-teams 插件），
并实时追踪团队/成员/任务进度**。

**目标**：`/dsh-tasks` 支持团队模式（mode=team）：提交单一目标 + 可选批次模式 → 船长自组织团队 →
平台展示实时进度（成员/任务/状态树）→ 完成后归档团队档案。

**范围**：test-platform-v2 backend + frontend + docs + 测试。不改仓库级 Agent Team 技能
（Batch 190 已交付）。

## 2. 现状盘点（探索结论）

| 项 | 现状 |
|----|------|
| 任务模型 | `dsh_task` 表：task/status/params_json/output_text/session_dir/error/operator_id/locked_by/locked_at（Batch 181 统一认领锁） |
| 服务层 | `dsh_task_service.py`：submit/list/get/cancel + `QueueWorkerLoop` 轮询 + `atomic_claim` 认领 + `ThreadPoolExecutor(max_workers=2)` |
| 执行抽象 | `dsh_runner.py`：`run_dsh_task(task, workspace, session_root, model, timeout, extra_env) -> DshRunResult`；双运行时（node CLI headless / python-sdk）；Batch 184 沙箱：隔离工作区 `ws-{uuid}`、全局并发闸门 `_concurrency_gate`（DSH_MAX_CONCURRENT 默认 1）、任务字符上限、python-sdk env 锁 |
| API | `dsh_tasks.py`：health/create/list/detail/cancel；权限 agent:view / agent:run |
| Schema | `schemas/dsh.py`：DshTaskCreate（task, params）/ DshTaskOut / DshHealthOut |
| 配置 | `config.py` DSH_*：enabled/runtime/model/timeout(600s)/max_output_chars/max_concurrent/max_task_chars/cordis_config/harness_path |
| 前端 | `frontend/src/pages/dsh-tasks/index.tsx`（12.8KB）：列表 + 提交 + 详情 |
| 插件状态 | `@nanmicoder/dsh-agent-teams@0.1.5` 仅装入 web profile；**headless profile 与 minimal.cordis.yml 均未含插件**——团队模式需新增执行侧配置 |
| 团队状态 | AgentTeams 状态落 `<workspace>/.agent-teams/{team}/team.json`（文件，单进程串行写）；本机已验证九件套全链路 |

## 3. 方案选型（B1 已批准）

| 方案 | 做法 | 结论 |
|------|------|------|
| **B1 模型扩展 + 复用现有队列（选定）** | `dsh_task` 加 `mode`(single/team) + `team_json`(进度快照) 列；同一认领队列/沙箱/权限；worker 团队分支启动团队运行时 + 进度线程轮询 `.agent-teams/`；前端一页扩展 | ✅ 复用 Batch 172/181/184 全部基础设施 |
| B2 独立表+独立队列 | 新表新 worker | 割裂、重复认领/沙箱/权限代码 |
| B3 任务文本内置指令 | 不改模型 | 无法结构化展示实时进度，输出不可控 |

## 4. 架构设计

```
提交（mode=team + 目标文本 + 批次模式 full/light）
  → dsh_task 行（pending, mode=team）
  → 现有 worker 认领（同队列）
  → execute_task 团队分支：
      ① 隔离工作区 ws-{uuid}（Batch 184 语义沿用；团队状态目录在其中）
      ② 团队运行时：
         - node：`--profile agent-team`（新增 profile，含 @nanmicoder/dsh-agent-teams + 船长 persona）
         - python-sdk：`team.cordis.yml`（新增组合，minimal 基础上加插件 + 船长 persona）
      ③ 执行线程跑 run_dsh_task（船长会话；task 文本 = 平台用户目标，经 persona 引导自组织）
      ④ 进度线程轮询 {ws}/.agent-teams/{team}/team.json → 解析 → 写 dsh_task.team_json（幂等）
      ⑤ 结束：team_json 终态（成员/任务/结论）+ output_text；超时/失败留 error
  → 前端 /dsh-tasks：提交面板可选团队模式；列表/详情展示团队进度树（定时刷新）
```

### 4.1 数据模型（dsh_task 扩展）

```python
mode: Mapped[str] = mapped_column(default="single", index=True)   # single | team
team_json: Mapped[str] = mapped_column(Text, default="{}")        # 团队进度快照（JSON 字符串）
```

Alembic 迁移：`20260817_b191_dsh_team_mode`（SQLite/PG 兼容：加两列，default 值）。

### 4.2 团队运行时配置

**node（agent-team profile）**：复制 headless profile 语义，新增 `{dsh 安装}/profiles/agent-team/`，
依赖加 `@nanmicoder/dsh-agent-teams`，cordis.yml 加插件行 + 船长 persona 系统提示词。
实现位置：`services/dsh/agent-team/` 下提供 profile 模板 + 部署说明；运行时经
`DSH_TEAM_HARNESS_PATH`/自动探测 `F:\deepseek-harness\profiles\agent-team`。

**python-sdk（team.cordis.yml）**：在 `minimal.cordis.yml` 基础上加：

```yaml
- id: agent-teams
  name: '@nanmicoder/dsh-agent-teams'
```

（插件为 npm bundle，SDK 环境需可解析该包——风险见 §7 R-2）

**船长 persona（两运行时共用提示词）**：
```
你是测试平台提交的 DSH 船长。用户目标：{task}；批次模式：{full|light}。
用 agent_teams_* 工具：建团队 → 加成员（full: product/pm/design/dev/qa；light: product/qa）→
建带依赖任务 → 认领派发 → 收件 → 汇总最终报告。产出写入工作区 work-logs/ 或报告文本。
```

### 4.3 进度轮询（worker 内）

- `execute_task` 团队分支：`threading.Thread(target=run_dsh_task)` 执行；主线程轮询
  `{ws}/.agent-teams/`（间隔 `DSH_TEAM_POLL_SECONDS`，默认 3s），每次读 team.json →
  `json.dumps` 写 `task.team_json`（每行独立 `SessionLocal` 短会话，避免与执行线程争用）。
- 终态归一：执行结束再读一次 team.json 作为终态；任务 status 沿用 single 语义
  （success/failed/cancelled，batch 184 词表）。
- 取消：仅 pending 可取消（现状语义不变）；running 的团队任务取消延后（下批可做）。

### 4.4 超时与配额

- 新增 `DSH_TEAM_TIMEOUT_SECONDS`（默认 1800s，覆盖单任务 600s 上限）；团队任务超时走
  `run_dsh_task(timeout=...)` 既有超时路径（exit 124）。
- 任务文本上限沿用 `DSH_MAX_TASK_CHARS`；批次模式参数走 params（`params.batch_mode`）。

### 4.5 API / Schema

- `DshTaskCreate` 加 `mode: str = "single"`（校验 single|team）+ `params.batch_mode`（full|light）。
- `DshTaskOut` 加 `mode: str`、`team_json: dict = {}`。
- 列表/详情不加新端点（复用现有）；`team_json` 随详情返回，前端定时刷新详情。

### 4.6 前端（/dsh-tasks 页扩展）

- 提交面板：模式选择（单选：标准 / 团队），团队模式显示批次模式（完整/轻量）下拉。
- 列表：mode 列（标准/团队徽标）。
- 详情：mode=team 时渲染团队进度树——成员卡（角色/状态）、任务列表（依赖/状态/output 摘要）、
  团队结论；`setInterval` 定时刷新（组件卸载清理，遵循 §3.4 React 规则）。
- executionStatus 词表不涉及（mode 非状态值）。

## 5. 测试策略

| 层 | 覆盖 |
|----|------|
| 后端单测 | schema 校验（mode 非法值拒绝）；service submit/list 带 mode；execute_task 团队分支（mock runner + mock team.json 轮询）；超时路径 |
| 后端集成 | `test_dsh_sandbox.py` 扩展：团队模式仍走隔离工作区/并发闸门（C172-1 不回归） |
| 冒烟（真实） | node agent-team profile 跑一次 mini 团队（本机已验证插件可用）；python-sdk 团队模式冒烟（R-2 验证） |
| 前端 vitest | 提交面板模式切换；团队进度树渲染（mock 数据）；轮询清理 |

## 6. 文件清单

**后端**
- 修改 `app/models/dsh_task.py`（mode/team_json 列）
- 修改 `app/schemas/dsh.py`（mode、team_json）
- 修改 `app/api/v1/dsh_tasks.py`（create 校验 mode；out 带 mode/team_json）
- 修改 `app/services/dsh/dsh_task_service.py`（execute_task 团队分支 + 轮询线程）
- 修改 `app/services/dsh/dsh_runner.py`（团队运行时路由 + persona 注入 + 超时参数）
- 新增 `app/services/dsh/team.cordis.yml`（python-sdk 团队组合）
- 新增 `app/services/dsh/agent_team_persona.py`（船长提示词构建）
- 新增 Alembic 迁移 `20260817_b191_dsh_team_mode`
- 修改 `app/core/config.py`（dsh_team_timeout_seconds / dsh_team_poll_seconds / dsh_team_profile 等）
- 新增/修改 `backend/tests/`（service/schema/sandbox 扩展）

**前端**
- 修改 `frontend/src/pages/dsh-tasks/index.tsx`（模式选择 + 团队进度树）
- 修改 API 类型（gen:api 后生成的 dsh 类型）

**文档**
- 修改 `docs/adr/0018-dsh-harness-integration.md`（状态补充：团队模式，Batch 191）
- 修改 `test-platform-v2/README.md`（DSH 团队模式说明）与 `backend/CLAUDE.md`（DSH 节补充）
- 新增 ADR 或更新 ADR-0018 后果节（按变更范围决定）

**工件**：PRD/PM/Design/QA/Leader 六件 + 看板（完整批次）

## 7. 风险与缓解

| # | 风险 | 缓解 |
|---|------|------|
| R-1 | agent-teams 插件在 headless/无头会话可用性（插件面向 web GUI；工具侧是 Host 服务，理论可用未实测） | 首个冒烟用例即真实 node agent-team profile 跑通；失败则记录并改用 python-sdk 验证 |
| R-2 | 生产 python-sdk bundled runtime 加载第三方 npm bundle 插件能力未知 | team.cordis.yml 先行；冒烟验证失败则标记 `python-sdk 团队模式 deferred`（C 条件登记），node 先交付 |
| R-3 | 进度轮询与执行线程并发写 DB | 轮询用独立短 Session；team_json 幂等全量覆盖；不与其他线程共享 session |
| R-4 | 团队任务耗时超 600s 默认超时 | 独立 `DSH_TEAM_TIMEOUT_SECONDS`（1800s） |
| R-5 | persona 引导不稳定（模型自组织失败） | persona 明确「建团队→加成员→任务依赖→派发→汇总」步骤；失败走 error 可追溯 |
| R-6 | 并发闸门 DSH_MAX_CONCURRENT=1 使团队任务排队 | 沿用现状（安全优先），README 说明 |

## 8. 里程碑（完整批次）

1. Product：PRD（含成功指标/非目标/用户故事）
2. PM：任务拆解（30–60min/任务）
3. Design：设计规范（模型/API/前端组件/team.cordis.yml）
4. Dev：TDD 实现（迁移→模型→schema→service→runner→API→前端→文档）
5. QA：门禁 + 单测 + 集成 + 冒烟（真实团队跑通）
6. Leader：判决 + 流程回写 + 复盘卡 → 一次总确认 → 合入
