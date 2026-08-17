# Batch 191 — PRD：/dsh-tasks 支持 AgentTeams 团队模式（子项目 B）

> **Product (🟦)** | Date: 2026-08-17 | Status: Draft → Review
> **mode: full**（新行为 + 新 Schema 列 + 新配置项 + 新执行侧依赖，六部门工件）
> 来源：用户需求（2026-08-17 已确认）——平台用户提交单一自然语言目标 + 批次模式（完整/轻量）→ DSH 船长会话自组织团队执行 → 平台实时追踪团队/成员/任务进度 → 完成后归档团队档案。
> 执行：DeepSeek Harness（AgentTeams 船长模式，本批自举）
> 设计依据：`docs/superpowers/plans/2026-08-17-dsh-tasks-agent-teams-design.md`（方案 B1 已批准）

---

## 1. 问题陈述

### 1.1 现状：单任务形态

`/dsh-tasks`（ADR-0018 形态 C，Batch 172 落地 / Batch 181 认领锁 / Batch 184 沙箱加固）当前是**单任务形态**：用户提交一条自然语言任务 → worker 认领 → `run_dsh_task` 一次执行 → `output_text` 落库。执行链完整（隔离工作区 ws-{uuid}、全局并发闸门 `DSH_MAX_CONCURRENT`、任务字符配额、python-sdk env 锁），但**没有协作维度**。

### 1.2 局限（用户痛点）

1. **复杂目标需人工分解**：一个跨领域目标（如「为登录模块生成用例 + 设计接口测试 + 跑回归」）只能拆成多条单任务逐个提交；任务间无依赖图、无上下文交接、无角色分工，产物割裂。
2. **执行是黑盒**：任务 running 期间平台看不到任何中间进度（谁在做什么、做到哪一步、有无卡住），长任务只能干等最终输出。
3. **结果无团队档案**：只有最终文本，没有「成员分工 → 任务依赖 → 各步结论 → 汇总」的协作轨迹，无法复盘与追溯。

### 1.3 需求与证据

1. **用户明确要求（2026-08-17）**：把 Batch 190 已移植的 DSH AgentTeams 船长能力（`@nanmicoder/dsh-agent-teams` 九件套：create/add_member/create_task/claim_task/send_message/update_task/status/delete，本机已验证全链路）接入测试平台产品——提交单一目标 → 船长自组织团队 → 平台实时追踪 → 完成归档。
2. **Batch 190 PRD-lite 非目标承接**：Batch 190 明确声明「`/dsh-tasks` 支持 AgentTeams 团队模式（子项目 B）不在本批，另行完整批次」——本批即该承接。
3. **仓库侧已验证价值**：仓库 Agent Team 流水线（六部门、任务依赖图、工件交接）证明团队模式对复杂目标的可行性与产出质量；平台用户需要同等能力而无需操作 DSH GUI（ADR-0018 弃选方案 A：不内嵌 DSH Web UI）。
4. **基础设施就绪**：Batch 181 统一认领队列 + Batch 184 沙箱（隔离工作区/并发闸门/配额）可整体复用，团队模式不新增安全面。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 团队任务提交 | 无（仅 single） | `mode=team` 创建成功；非法 mode 被 schema 拒绝（校验可测） | 后端单测 |
| 端到端执行（node） | 无 | node `agent-team` profile 真实 mini 团队任务 success：`team_json` 终态含成员/任务/结论结构，`output_text` 含最终报告 | 冒烟（QA） |
| 进度实时性 | 无 | 详情页定时刷新可见 `team_json` 快照更新（轮询粒度 `DSH_TEAM_POLL_SECONDS`=3s） | 冒烟/集成 |
| python-sdk 团队模式 | 无 | `team.cordis.yml` 冒烟 success；**失败 → 登记 C191-1 deferred（解除条件=SDK bundled runtime 可加载 npm bundle 插件），node 先交付** | 冒烟（QA） |
| 沙箱不回归（C172-1） | 隔离工作区 + 并发闸门 + 配额 | `test_dsh_sandbox.py` 扩展团队模式用例全绿（团队任务仍走 ws-{uuid}/`DSH_MAX_CONCURRENT`/文本配额） | pytest |
| 团队超时 | 单任务 600s | `DSH_TEAM_TIMEOUT_SECONDS`=1800s 超时 → `failed` + 可读 `error`（不悬挂） | 单测/集成 |
| 取消语义 | 仅 pending 可取消 | 不变（running 团队任务取消延后=非目标，登记 C191-2） | 后端单测 |
| 前端 | 列表+提交+详情 | 提交面板模式选择 + 批次模式下拉 + 列表 mode 徽标 + 团队进度树（成员卡/任务列表/团队结论）；vitest 覆盖渲染与轮询清理 | vitest |
| 质量门禁 | — | `ruff check app --select F821` / pytest / typecheck / build / vitest 全绿；Alembic 单头 | CI + QA |

## 3. 非目标（本次不做）

| 项 | 原因/说明 |
|----|----------|
| 不改仓库级 Agent Team 技能 | Batch 190 已交付（`.claude/skills/cameltv-agent-team/`、`docs/agent-team/`）；本批只消费插件能力，不重复移植 |
| running 团队任务取消 | 现状语义（仅 pending 可取消）保持不变；running 取消延后，登记 **C191-2**（解除条件=下批实现执行中终止） |
| python-sdk 团队模式冒烟失败则 deferred | 既定缓解（设计文档 R-2）：冒烟失败标记 **C191-1** deferred，node 先交付，不阻塞本批 |
| 独立团队任务表/独立队列（方案 B2） | 方案评审已弃选：割裂、重复认领/沙箱/权限代码；B1 模型扩展复用现有队列 |
| 任务文本内置指令（方案 B3） | 已弃选：无法结构化展示实时进度、输出不可控 |
| OS 级沙箱（seccomp/nsjail） | C184-1 已评估成文（ADR-0020 三层模型），生产 Railway 容器为隔离单元；本批不引入 |
| 生产 `DSH_ENABLED=true` | 保持 false（C172-1 语义延续）；启用是独立部署决策 |
| 平台内嵌 DSH Web UI | ADR-0018 弃选方案 A 维持；进度经 `team_json` 在平台内展示 |
| 多船长/任务重试/团队调度 | 单船长会话语义；失败走 `error` 可追溯（R-5） |

## 4. 用户故事 + 验收标准

### US-1 提交团队任务
> 作为平台 QA 工程师，我希望提交**一个**自然语言目标并选择团队模式与批次模式，由 DSH 船长自组织团队完成，而不是手工拆任务逐个提交。

- **Given** 我在 /dsh-tasks 页选择「团队模式」并输入目标 + 批次模式（完整/轻量）
- **When** 提交
- **Then** 创建 `mode=team` 任务（pending）；worker 认领后启动 DSH 船长会话（persona 引导建团队→加成员→建带依赖任务→认领派发→汇总）；非法 mode 被拒绝并返回明确错误

### US-2 实时进度追踪
> 作为平台用户，我希望提交后随时看到团队/成员/任务进度，而不是进入 DSH GUI 或干等。

- **Given** `mode=team` 任务 running
- **When** 打开任务详情（页面定时刷新）
- **Then** 详情展示团队进度树：成员卡（角色/状态）、任务列表（依赖/状态/输出摘要）、当前阶段；数据来自 `team_json` 快照，刷新粒度 ≤ `DSH_TEAM_POLL_SECONDS`

### US-3 完成归档
> 作为平台用户，我希望团队任务完成后能看到协作轨迹与最终结论。

- **Given** 团队任务结束（success）
- **Then** 详情展示 `team_json` 终态（成员分工/任务结果/团队结论），`output_text` 含最终报告，`status=success`；列表可区分团队/标准任务（mode 徽标）

### US-4 失败与超时可追溯
> 作为平台用户，我希望任务失败或超时时看到明确错误，而不是永久悬挂。

- **Given** 执行超过 `DSH_TEAM_TIMEOUT_SECONDS`（1800s）或执行异常
- **Then** `status=failed` + 可读 `error`（含超时标识/异常摘要），`finished_at` 落库；已有 `team_json` 进度保留可查

### US-5 取消语义（保守）
> 作为平台用户，我希望提交错误的任务可取消。

- **Given** 任务 `pending`
- **When** 取消
- **Then** `status=cancelled`（现状语义不变）；running 团队任务取消延后（C191-2）

### US-6 沙箱不回归
> 作为安全审计者，我希望团队模式不绕过 Batch 184 沙箱。

- **Given** `mode=team` 任务执行
- **Then** 仍在 ws-{uuid} 隔离工作区、受 `DSH_MAX_CONCURRENT` 闸门约束、任务文本配额生效（C172-1 不回归，`test_dsh_sandbox` 扩展覆盖）

### US-7 双运行时可用
> 作为平台运维，我希望团队模式在 node 与 python-sdk 两个运行时均可用；python-sdk 若不可用则如实登记 deferred 而非静默降级。

- **Given** 生产环境 `DSH_RUNTIME=python-sdk`
- **Then** 冒烟验证 `team.cordis.yml` 团队组合；失败 → 登记 C191-1 deferred（README/ADR 注明 node 先行），不静默 fallback 到单任务

## 5. 技术考量

| 项 | 考量 | 风险/缓解 |
|----|------|-----------|
| 双运行时路由 | `dsh_runner` 团队分支按 `DSH_RUNTIME` 选择：node → `agent-team` profile（新增，含插件 + 船长 persona）；python-sdk → `team.cordis.yml`（minimal 基础加插件行） | R-1：插件在 headless 会话可用性未实测（工具侧为 Host 服务理论可用）→ 首个冒烟即真实跑通验证；失败则记录 |
| 插件依赖 | `@nanmicoder/dsh-agent-teams@0.1.5`（npm bundle）当前仅装入 web profile；执行侧需新增 profile/组合 | R-2：SDK bundled runtime 加载第三方 npm bundle 能力未知 → 冒烟失败则 C191-1 deferred，node 先交付 |
| 超时 | 新增 `DSH_TEAM_TIMEOUT_SECONDS`（默认 1800s）覆盖单任务 600s 上限；走 `run_dsh_task(timeout=...)` 既有超时路径（exit 124） | R-4 已缓解；超时错误可读 |
| 并发 | `DSH_MAX_CONCURRENT=1` 闸门沿用（团队任务排队不丢任务）；python-sdk env 锁沿用（C172-2 不回归） | R-6：安全优先，README 说明排队语义 |
| 进度轮询 | worker 内独立线程轮询 `{ws}/.agent-teams/{team}/team.json`，独立短 `SessionLocal` 全量幂等写 `team_json`；结束再读一次为终态 | R-3：不与执行线程共享 session；快照全量覆盖无增量合并 |
| persona 引导 | 船长提示词固定步骤（建团队→加成员→建带依赖任务→派发→汇总），task 文本=用户目标，批次模式驱动成员集（full: product/pm/design/dev/qa；light: product/qa） | R-5：模型自组织失败走 `error` 可追溯，不静默成功 |
| 数据大小 | `team_json` 快照可能随成员/任务数增长；`output_text` 已有 20000 字符截断 | 评估 team_json 写入截断策略，与现有配额口径对齐；前端树渲染用 mock 数据验证 |
| Schema/迁移 | `dsh_task` 加 `mode`（default "single", index）+ `team_json`（Text, default "{}"）；Alembic 迁移 SQLite/PG 兼容 | 单头校验；C86-1 双 404 约定应用于新增断言 |
| 取消 | 仅 pending 可取消（现状）；running 团队取消延后 | 登记 C191-2 |
| API/前端 | `DshTaskCreate.mode`（校验 single\|team）+ `params.batch_mode`（full\|light）；`DshTaskOut.mode/team_json`；列表/详情复用现有端点 | 不加新端点；详情定时刷新（组件卸载清理，遵循 React 规则） |

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 1. 开发（TDD） | 开发/测试环境 | 迁移→模型→schema→service（团队分支+轮询）→runner（双运行时路由+persona）→API→前端全链路实现；后端单测/集成全绿 |
| 2. QA 门禁 | QA | `ruff F821`/typecheck/build/vitest/pytest 全绿；`test_dsh_sandbox` 扩展不回归（C172-1） |
| 3. 真实冒烟 | 本地/test | node `agent-team` profile 跑通一次 mini 团队（建队→成员→任务→进度→终态）；python-sdk 冒烟成功或登记 C191-1 deferred |
| 4. test 部署验证 | 平台用户 | /dsh-tasks 团队模式端到端可用：提交→实时进度→完成归档；详情页团队进度树正常 |
| 5. 生产 | 生产用户 | 跟随 DSH 部署决策（本批不改变 `DSH_ENABLED=false`）；启用后团队模式可用（README/ADR-0018 补充说明） |

## 7. 技能使用

| 技能 | 产出/结论 |
|------|-----------|
| `cameltv-agent-team`（DEPARTMENTS.md §1 + SKILL.md + pipeline-modes.md） | PRD 模板结构；批次模式判定：引入新行为/新 Schema/新配置/新依赖 → **mode: full**（六部门工件） |
| `brainstorming` | 已加载评估：需求与设计方向已在设计文档（方案 B1）中经用户确认，PRD 据此提炼，无需重复设计确认；HARD-GATE 不触发（本工件为文档，非实现动作） |
| `using-superpowers` | 会话启动技能路由：定位到 cameltv-agent-team（团队流水线）与 brainstorming（产品定义） |
| 文档核查（read/glob/grep） | C-CONDITIONS.md 遗留条件核对、`dsh_task_service.py`/`dsh_runner.py` 现状确认、batch-184/190 PRD 格式对齐；非测试证据 |

## 8. C 条件核对

- **C172-1（Closed/Batch 184）**：团队模式必须沿用隔离工作区/并发闸门/配额——本批 `test_dsh_sandbox` 扩展覆盖（US-6），不回归 ✅
- **C172-2（Closed/Batch 184）**：python-sdk env 锁沿用，团队模式 python-sdk 路径不绕过 ✅
- **C184-1（Closed/Batch 186）**：OS 级沙箱不引入（Railway 容器为隔离单元），本批不触碰 ✅
- **C75-1** mode:full 已记录 ✅ | **C75-3** PR 前运行 `audit-cconditions.ps1 -RequireLatestBatch` ✅ | **C76-2** `scan-common-bugs` ✅ | **C78-1** 受影响模块 pytest 记录退出码 ✅ | **C86-1** 新增断言遵循双 404 约定 ✅ | **C104-5** 本批写入位于任务 worktree `F:\CamelTv-worktrees\DeepSeek_Harness-batch-191-dsh-tasks-agent-teams`（git 分支 feature/batch-191-dsh-tasks-agent-teams）✅ | **C63-3** C-CONDITIONS.md 维护，本 PRD 引用 C63 条件 ✅
- **新增建议（待 Leader 判决确认）**：
  - **C191-1**：python-sdk 团队模式冒烟失败 → deferred（解除条件=SDK bundled runtime 可加载 npm bundle 插件，或提供替代方案）；node 先交付
  - **C191-2**：running 团队任务取消延后（解除条件=下批实现执行中终止语义）
