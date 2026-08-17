# Batch 191 — PM 计划：/dsh-tasks 支持 AgentTeams 团队模式

> **PM (🟨)** | Date: 2026-08-17
> 配套 PRD：`batch-191-dsh-tasks-agent-teams-prd-summary.md`
> 设计依据：`docs/superpowers/plans/2026-08-17-dsh-tasks-agent-teams-design.md`（方案 B1 已批准）

## 规格摘要

**原始需求**（PRD §1.3）：平台用户提交**单一自然语言目标 + 批次模式（完整/轻量）** → DSH 船长会话（AgentTeams 九件套）自组织团队执行 → 平台实时追踪团队/成员/任务进度（`team_json` 快照）→ 完成后归档团队档案。复用 Batch 172/181/184 认领队列/沙箱/权限，不加新端点、不内嵌 DSH Web UI。

**目标时间**：单任务 30–60 分钟；全批次开发 2–3 个修正周期（Dev 阶段完成迁移→模型→schema→service→runner→API→前端全链路）。

**成功指标锚点**（PRD §2）：node 端到端冒烟 success；进度实时性 ≤ `DSH_TEAM_POLL_SECONDS`(3s)；python-sdk 冒烟失败 → **C191-1 deferred**（node 先交付）；沙箱不回归（C172-1，`test_dsh_sandbox` 扩展）；团队超时 `DSH_TEAM_TIMEOUT_SECONDS`=1800s → failed + 可读 error；取消语义不变（running 延后 → **C191-2**）；前端 vitest；门禁全绿。

**非目标红线**（PRD §3）：不改仓库级 Agent Team 技能；不做独立团队表/队列（B2）；不做任务文本内置指令（B3）；不引入 OS 沙箱；`DSH_ENABLED` 保持 false；不内嵌 DSH Web UI；running 团队任务取消延后。

## 开发任务（含依赖顺序）

依赖主线：**T1/T2（基础层，可并行）→ T3（API）→ T4/T5（执行侧）→ T6（服务）→ T7→T8（测试）→ T9（前端）→ T10（前端测试）→ T11（文档）→ T12（冒烟）→ T13（门禁/工件）**

### [ ] Task 1: 配置项新增（DSH 团队模式）
**描述**: 在 `app/core/config.py` 的 Settings 增加团队模式配置：`dsh_team_timeout_seconds: float = 1800.0`（团队任务超时，覆盖单任务 600s）、`dsh_team_poll_seconds: float = 3.0`（进度轮询间隔）、`dsh_team_profile: str = "agent-team"`（node profile 名）、`dsh_team_cordis_config: str = ""`（python-sdk 团队 cordis，空 = 内置 `team.cordis.yml`）、`dsh_team_harness_path: str = ""`（agent-team profile 安装路径，空 = 自动探测 `F:\deepseek-harness\profiles\agent-team`）。同步 `backend/.env.example` 注释。
**验收标准**:
- settings 各新字段可读且默认值符合 PRD（1800 / 3 / agent-team）
- `.env.example` 含对应注释项（不写真实凭据）
- 既有 DSH 配置（dsh_timeout_seconds 等）行为不变，无单测回归
**涉及文件**:
- `test-platform-v2/backend/app/core/config.py` — 新增字段
- `test-platform-v2/backend/.env.example` — 注释同步
**参考**: 设计文档 §4.4（超时与配额）/ PRD §2 成功指标 / PRD §5 技术考量-超时行

### [ ] Task 2: 模型 + Alembic 迁移（mode / team_json 列）
**描述**: `DshTask` 模型加 `mode: Mapped[str] = mapped_column(default="single", index=True)`（single|team）与 `team_json: Mapped[str] = mapped_column(Text, default="{}")`（团队进度快照 JSON 字符串）。新增 Alembic 迁移 `20260817_b191_dsh_team_mode`（down_revision = `20260816_b182_status_unify`，当前头，已核实；开工前仍可 `alembic heads` 复核），SQLite/PG 兼容：`add_column` 带 `server_default`、`mode` 建索引。
**验收标准**:
- `alembic upgrade head` / `downgrade -1` 在 SQLite 与 PG 兼容写法下可执行
- 迁移后 `dsh_task` 含 mode/team_json 两列；mode 默认 "single"、team_json 默认 "{}"
- `alembic heads` 单头；既有数据行迁移后 mode="single" 不回填丢失
- 模型 `from_attributes` 序列化含新字段
**涉及文件**:
- `test-platform-v2/backend/app/models/dsh_task.py` — 加两列
- `test-platform-v2/backend/alembic/versions/20260817_b191_dsh_team_mode.py` — 新迁移（命名对齐 `20260816_b181_task_queue_locks.py` 风格）
**参考**: 设计 §4.1（数据模型）/ PRD §5 Schema/迁移行 / 既有迁移 `20260816_b181_task_queue_locks.py` 写法

### [ ] Task 3: Schema + API（mode 校验 / team_json 出参）
**描述**: `app/schemas/dsh.py`：`DshTaskCreate` 加 `mode: Literal["single","team"] = "single"`；`params.batch_mode` 校验（`Literal["full","light"]`，仅 team 模式必填，非法值拒绝）；`DshTaskOut` 加 `mode: str = "single"` 与 `team_json: dict = {}`（from_attributes 兼容字符串 → dict 转换）。`app/api/v1/dsh_tasks.py`：create 透传 mode 与 batch_mode 到 `submit_task`；无新端点。
**验收标准**:
- POST `/api/v1/dsh-tasks` 传 `mode="team"` + `params.batch_mode="full"` 创建成功且返回 mode=team
- 非法 mode（如 `"x"`）/ 非法 batch_mode → 4xx 明确错误（遵循既有校验风格）
- 详情/列表响应含 mode 与 team_json 字段（team_json 为空时 `{}`）
- C86-1 双 404 约定：详情/取消对不存在任务与跨项目任务均返回 404（既有行为回归断言）
**涉及文件**:
- `test-platform-v2/backend/app/schemas/dsh.py` — Create/Out 扩展
- `test-platform-v2/backend/app/api/v1/dsh_tasks.py` — create 透传 + out 序列化
- `test-platform-v2/backend/tests/test_dsh_tasks.py` — API 层用例（或并入 Task 7）
**参考**: 设计 §4.5（API/Schema）/ PRD §5 API/前端行 / C86-1 双 404 约定

### [ ] Task 4: dsh_runner 团队运行时路由
**描述**: `run_dsh_task` 增加 `mode: str = "single"` 关键字参数：`mode=="team"` 时 node 路径命令改为 `--profile agent-team`（profile 名读 `dsh_team_profile`，harness 入口不变）；python-sdk 路径改用 `team.cordis.yml`（`dsh_team_cordis_config` 或内置文件）；团队任务超时走 `dsh_team_timeout_seconds`（透传 `run_dsh_task(timeout=...)` 既有 exit 124 路径）。并发闸门/隔离工作区/文本配额对团队任务**同样生效**（C172-1 不回归）。
**验收标准**:
- `run_dsh_task(mode="team")` node 分支 cmd 含 `--profile agent-team`（mock subprocess 断言）
- `run_dsh_task(mode="team")` python-sdk 分支 cordis 指向 team.cordis.yml
- 团队任务超时 → `DshRunResult(exit_code=124, timed_out=True, error 可读)`
- 团队任务仍经 `_concurrency_gate` 与 `_workspace_for`（复用，不新增旁路）
- single 模式行为与现状完全一致（回归）
**涉及文件**:
- `test-platform-v2/backend/app/services/dsh/dsh_runner.py` — 签名 + 分支
- `test-platform-v2/backend/tests/test_dsh_runner.py` / `test_dsh_sandbox.py` — 断言（或并入 Task 7）
**参考**: 设计 §4.2/§4.4 / PRD §5 双运行时路由、超时行 / Batch 184 沙箱语义

### [ ] Task 5: 执行侧团队配置资产（persona + team.cordis.yml + agent-team profile 模板）
**描述**: 新增 `app/services/dsh/agent_team_persona.py`：`build_agent_team_persona(task: str, batch_mode: str) -> str`，输出船长固定步骤提示词（建团队→加成员→建带依赖任务→认领派发→汇总最终报告；full 成员集 product/pm/design/dev/qa，light 成员集 product/qa；产出写入工作区 work-logs/ 或报告文本）。新增 `app/services/dsh/team.cordis.yml`：在 `minimal.cordis.yml` 基础上追加 `agent-teams` 插件行（`- id: agent-teams, name: '@nanmicoder/dsh-agent-teams'`），persona 经 `DSH_SYSTEM_PROMPT` 注入。新增 `app/services/dsh/agent-team/` 目录：agent-team profile 模板（cordis.yml 插件行 + persona 部署说明 + 安装 README，目标安装位 `F:\deepseek-harness\profiles\agent-team`，本机 harness 当前**无 profiles 目录**——需新建并验证 CLI `--profile agent-team` 可解析）。
**验收标准**:
- `build_agent_team_persona` 单测：full/light 成员集正确；含用户目标文本与固定步骤
- `team.cordis.yml` 可被 YAML 解析，含 agent-teams 插件行且 minimal 其余行不变
- `agent-team/README.md` 写明 profile 安装步骤与 `DSH_TEAM_HARNESS_PATH` 覆盖方式
- 本机 `F:\deepseek-harness\profiles\agent-team` 创建后，CLI 以 `--profile agent-team` 启动无「profile 不存在」错误（冒烟前置）
**涉及文件**:
- `test-platform-v2/backend/app/services/dsh/agent_team_persona.py` — 新增
- `test-platform-v2/backend/app/services/dsh/team.cordis.yml` — 新增
- `test-platform-v2/backend/app/services/dsh/agent-team/` — profile 模板 + README（新增）
- `test-platform-v2/backend/tests/` — persona 单测（或并入 Task 7）
**参考**: 设计 §4.2（团队运行时配置 + persona 全文字面）/ PRD §5 persona 引导行 / R-1/R-2 风险

### [ ] Task 6: dsh_task_service 团队分支 + 进度轮询线程
**描述**: `execute_task(db, task, runner=None)` 按 `task.mode` 分派：single 走现状；team 分支——① 主线程/执行线程：`threading.Thread(target=run_dsh_task, kwargs={mode:"team", ...})` 跑船长会话（task 文本=用户目标，persona 经 extra_env `DSH_SYSTEM_PROMPT` 注入）；② 轮询线程：间隔 `dsh_team_poll_seconds` 扫描 `{ws}/.agent-teams/{team}/team.json`（ws 为 `result.session_dir`/workspace 下 ws-{uuid}；team 目录为最新/唯一团队），解析后以**独立短 `SessionLocal`** 全量幂等写 `task.team_json`（绝不与执行线程共享 session，R-3）；③ 执行结束再读一次 team.json 为终态；④ 状态沿用 single 词表（success/failed），超时/异常写可读 error，`finished_at` 落库；已有 team_json 进度保留。取消语义不变（仅 pending，C191-2 登记）。
**验收标准**:
- mock runner + 临时 team.json 目录：team 分支启动轮询并持续更新 task.team_json（≥2 次快照）
- 轮询线程使用独立 SessionLocal（测试断言无共享 session 引用）
- 执行结束终态快照写入；success/failed 与 output_text/error 正确
- 团队任务超时 → status=failed + error 含超时标识；team_json 保留可查
- single 任务路径行为零变化（既有 test_dsh_tasks 全绿）
**涉及文件**:
- `test-platform-v2/backend/app/services/dsh/dsh_task_service.py` — execute_task 分支 + 轮询线程 + 终止线程清理
- `test-platform-v2/backend/tests/test_dsh_tasks.py`（或新 `test_dsh_team.py`）— 团队分支用例
**参考**: 设计 §4.3（进度轮询）/ §4.4（超时）/ PRD §5 进度轮询行 / R-3、R-4、R-5

### [ ] Task 7: 后端测试扩展（schema / service / 沙箱不回归）
**描述**: 补齐 T3–T6 的自动化测试：schema 校验（非法 mode/batch_mode 拒绝）；service submit/list 带 mode（mode 落库、列表/详情返回）；execute_task 团队分支（mock runner + mock 轮询，含超时路径）；`test_dsh_sandbox.py` 扩展团队模式用例（C172-1：团队任务仍走 ws-{uuid} 隔离工作区、`DSH_MAX_CONCURRENT` 闸门、`DSH_MAX_TASK_CHARS` 文本配额）；C172-2 python-sdk env 锁回归不变。
**验收标准**:
- 新增用例全部通过；记录 pytest 退出码（C78-1）
- `test_dsh_tasks.py` / `test_dsh_runner.py` / `test_dsh_sandbox.py` 既有用例无新增失败（基线失败需列出）
- `ruff check app --select F821` 通过
**涉及文件**:
- `test-platform-v2/backend/tests/test_dsh_tasks.py` — mode/团队分支用例
- `test-platform-v2/backend/tests/test_dsh_sandbox.py` — 团队模式不回归扩展
- `test-platform-v2/backend/tests/test_dsh_runner.py` — 团队路由断言
**参考**: 设计 §5 测试策略表 / PRD §2 沙箱指标与 C172-1 / 既有 `test_dsh_sandbox.py` 类结构

### [ ] Task 8: 前端 API 类型 + /dsh-tasks 页面扩展
**描述**: `frontend/src/api/dshTasks.ts`：`DshTask` 加 `mode: string`、`team_json: Record<string, any>`；`createDshTask` 支持 `{mode, batch_mode}` 参数。`frontend/src/pages/dsh-tasks/index.tsx`：① 提交 Dialog 加模式选择（单选：标准/团队），团队模式显示批次模式下拉（完整 full/轻量 light）；② 列表加 mode 徽标列（标准/团队）；③ 详情 Sheet：mode=team 且 team_json 非空时渲染团队进度树（成员卡：角色/状态；任务列表：依赖/状态/输出摘要；团队结论），running 时 `setInterval` 按 `DSH_TEAM_POLL_SECONDS` 粒度（3s）刷新详情——**组件卸载清理**（React §3.4 规则，AbortSignal/clearInterval）；④ executionStatus 词表不动。
**验收标准**:
- 提交团队任务带 mode+batch_mode；非法 mode 后端拒绝时前端 toast 明确错误
- 列表团队任务显示团队徽标；详情团队进度树渲染（mock team_json 数据验证）
- running 团队详情自动刷新且组件卸载后无泄漏（无 setInterval 悬挂）
- `npm run typecheck && npm run build` 通过；无 console 报错
**涉及文件**:
- `test-platform-v2/frontend/src/api/dshTasks.ts` — 类型 + 参数
- `test-platform-v2/frontend/src/pages/dsh-tasks/index.tsx` — 提交面板/列表徽标/进度树（如体积过大拆 `team-progress.tsx` 子组件）
**参考**: 设计 §4.5/§4.6 / PRD §5 API/前端行 / AGENTS.md §3.4 React 规则

### [ ] Task 9: 前端 vitest（模式切换 / 进度树 / 轮询清理）
**描述**: 新增/扩展 vitest：提交面板模式切换（标准→团队出现批次模式下拉）；团队进度树用 mock team_json 渲染成员卡/任务列表/结论；详情轮询 `setInterval` 在组件卸载时清理（fake timers 断言无残留）。
**验收标准**:
- 相关 vitest 用例全绿（记录命令与退出码）
- 既有前端测试无新增失败
**涉及文件**:
- `test-platform-v2/frontend/src/pages/dsh-tasks/__tests__/`（对齐仓库既有测试目录约定，如无则新建）
**参考**: 设计 §5 前端 vitest 行 / PRD §2 前端指标

### [ ] Task 10: 文档（ADR-0018 / README / backend CLAUDE.md / C-CONDITIONS）
**描述**: `docs/adr/0018-dsh-harness-integration.md` 状态节补充团队模式（Batch 191，方案 B1 摘要 + team_json 快照语义 + 双运行时路由）；`test-platform-v2/README.md` 增加 DSH 团队模式说明（新配置项表、`DSH_MAX_CONCURRENT=1` 排队语义 R-6、python-sdk deferred 语义 C191-1、node 先交付）；`test-platform-v2/backend/CLAUDE.md` DSH 节补充（persona/team.cordis.yml/agent-team profile 维护点）；`C-CONDITIONS.md` 登记 **C191-1**（python-sdk 冒烟失败 → deferred，解除条件=SDK bundled runtime 可加载 npm bundle 插件）与 **C191-2**（running 团队任务取消延后，解除条件=下批实现执行中终止）为建议条目，待 Leader 判决确认。
**验收标准**:
- 三份文档落库，内容与 PRD/设计一致，无过时描述
- README 覆盖新配置项与排队/deferred 语义
- C-CONDITIONS.md 含 C191-1/C191-2 建议登记（引用 PRD §8）
**涉及文件**:
- `docs/adr/0018-dsh-harness-integration.md`
- `test-platform-v2/README.md`
- `test-platform-v2/backend/CLAUDE.md`
- `C-CONDITIONS.md`
**参考**: 设计 §6 文档清单 / PRD §8 C 条件核对

### [ ] Task 11: 真实冒烟（node mini 团队 + python-sdk 判定）
**描述**: 本地真实跑通一次 node `agent-team` profile mini 团队任务（建队→加成员→建带依赖任务→认领派发→进度→终态）：提交 mode=team 任务 → 详情轮询可见 team_json 快照更新（粒度 ≤3s）→ 终态 team_json 含成员/任务/结论结构 + output_text 含最终报告。python-sdk 冒烟（`team.cordis.yml`）：成功则记录；失败 → 登记 **C191-1 deferred**（README/ADR 注明 node 先行），**不静默 fallback 到单任务**（US-7）。
**验收标准**:
- node 冒烟 success：team_json 终态结构与 output_text 报告齐备（截图/日志为 QA 证据）
- 进度实时性：两次详情拉取间 team_json 有变化（轮询粒度内）
- python-sdk 冒烟结果如实记录（成功 或 C191-1 deferred 登记，含失败原因）
- 冒烟全程任务在 ws-{uuid} 工作区执行（沙箱不回归实证）
**涉及文件**: （无代码文件；证据入 QA 报告）
**参考**: 设计 §5 冒烟行 / §7 R-1/R-2 / PRD §6 阶段 3

### [ ] Task 12: 质量门禁 + 六件工件收尾（QA/Leader/看板）
**描述**: 全量门禁：`ruff check app --select F821`、pytest 全量（记录基线 vs 本分支失败集合）、`npm run typecheck`、`npm run build`、vitest、Alembic 单头；QA 报告（含冒烟证据、C191-1/C191-2 状态）、Leader 判决（C191-1/C191-2 确认）、看板更新；一次总确认 → push → Draft PR → `audit-ai-pr.ps1`（-ExpectedWorkflow agent-team -ExpectedExecutor DeepSeek_Harness）→ required checks 全绿 → 合入 main。
**验收标准**:
- 全部 required checks 绿；无新增测试失败；Alembic 单头
- 六件工件 + 看板齐全；C191-1/C191-2 状态由 Leader 判决确认
- PR 合入 main；本地无未推送提交
**涉及文件**: （流程工件 `test-platform-v2/work-logs/batch-191-*` + 看板）
**参考**: DEPARTMENTS.md §5/§6/§7 / AGENTS.md §2.3-2.4 / PRD §6 阶段 4-5

## 依赖顺序图

```
T1 config ──────┐
                ├──→ T3 schema/API ──→ T8 前端 ──→ T9 前端测试
T2 模型+迁移 ────┘        │
                         ├──→ T6 service ──→ T7 后端测试 ──→ T11 冒烟 ──→ T12 门禁/工件
T4 runner 路由 ──────────┘
T5 persona/cordis/profile（依赖 T1 配置名，可与 T4 并行）
T10 文档（依赖 T6 语义确认，可与 T7–T9 并行）
```

## 质量要求

- [x] 后端单测覆盖（schema/service/runner/sandbox，T7）
- [x] 前端 vitest 覆盖（模式切换/进度树/轮询清理，T9）
- [x] OpenAPI 同步（DshTaskCreate.mode / DshTaskOut.mode+team_json，T3）
- [x] Alembic 单头 + SQLite/PG 兼容（T2）
- [x] React 副作用规范：详情轮询 setInterval 卸载清理、无 N+1 请求（T8，AGENTS.md §3.4）
- [ ] 响应式（Desktop + Tablet）：团队进度树在详情 Sheet 内自适应（前端实现时验证）
- [ ] 无障碍（ARIA/键盘）：模式选择/批次模式下拉可键盘操作（前端实现时验证）
- [ ] 无 console 报错/告警（QA 阶段验证）
- [ ] 无调试遗留（console.log/print/breakpoint）、无硬编码密钥（提交前自检）

## 风险提示

- **R-1/R-2（插件可用性）**：node agent-team profile 与 python-sdk team.cordis.yml 均为本批新建，headless 可用性未实测 → Task 5 先建 profile 并验证 `--profile agent-team` 可解析，Task 11 真实冒烟兜底；python-sdk 失败按既定缓解登记 C191-1，**node 先交付，不阻塞本批**。
- **team 目录发现**：`{ws}/.agent-teams/{team}/team.json` 的 team 目录名由插件运行时生成，轮询需扫描目录取最新/唯一团队（Task 6 实现细节，mock 测试先行）。
- **轮询与执行并发写 DB（R-3）**：轮询线程必须独立短 SessionLocal 全量幂等写，禁止共享 session。
- **进度树数据量（PRD §5）**：team_json 可能随成员/任务增长，写入沿用输出截断口径评估（如超长截断并注明），前端树渲染用 mock 验证。
- **B2/B3 弃选不回退**：团队模式必须复用现有认领队列/沙箱/权限，禁止为省事新增旁路。
