# Batch 172 — Design Spec
> **Design (🎨)** | Date: 2026-08-14 | Status: 已验收（有条件）

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind + CVA；Token 走语义类（bg-muted / text-muted-foreground / border / variant / bg-status-*），不写死裸色阶。主题由 data-theme-id + .dark 驱动。复用组件：`PageHeader` / `Card` / `DataTable`/`Table` / `AsyncState`（或 Loading/Empty/ErrorState）/ `Sheet` / `Dialog` / `Textarea` / `Badge` / `Skeleton` / sonner toast / Lucide 图标（`size-4`）。

## 0.5 关键设计决策（本批为全栈，先定运行时与契约）

### D1. dsh 运行时抽象（`app/services/dsh/dsh_runner.py`）
- `run_dsh_task(task, workspace, session_root, model, timeout) -> DshRunResult(final_response, exit_code, error, session_dir)`。
- runtime 选择：`dsh_runtime=python-sdk`（生产 Linux：`deepseek-harness-sdk` 锁版本，bundled runtime 无需 Node）；`dsh_runtime=node`（本地 Windows 开发：子进程调 `dsh --profile headless`，超时 kill）。
- 依赖注入 + `runtime_available()`；测试用 mock runner，不依赖真实凭据。
- 理由：官方 Python SDK 持久 PTY 仅 POSIX；Windows 本地用 Node CLI 规避，两条路径统一返回同一结果结构。

### D2. DshTask 模型与状态机
- 表 `dsh_task`：`id`(int PK) / `project_id` / `task`(Text) / `status`(pending|running|success|failed|cancelled) / `params_json` / `output_text` / `session_dir` / `error` / `operator_id` / `created_at` / `started_at` / `finished_at`。
- 状态流转：pending → running → success | failed；pending 可 cancel。失败必须落 `error` 原因。

### D3. API 契约（OpenAPI 同步）
- `POST /api/v1/dsh-tasks` {task, params?} → {id, status}
- `GET /api/v1/dsh-tasks?page&page_size&status` → Page<DshTaskOut>
- `GET /api/v1/dsh-tasks/{id}` → DshTaskOut
- `POST /api/v1/dsh-tasks/{id}/cancel` → DshTaskOut
- `GET /api/v1/dsh-tasks/health` → {available, reason}（前端未启用 503 态依据）
- 权限：复用 `agent:run` / `agent:view`；项目隔离（project_id 过滤，与 agent_run_service 同模式）。

### D4. Agent 工作台执行型 Agent
- `AGENT_META` 新增 `dsh_execution`（label「DSH 执行」/ icon Terminal / artifact_type dsh_execution）；orchestrator 对该类型走 dsh_runner，user_input 即任务文本，输出/错误写入 AiArtifact 与 AgentRun。
- `GET /api/v1/agents/types` 返回 `available` 随 `dsh_available()`。

## 1. 组件规格表

### 1.1 DSH 任务页（新页面 `/dsh-tasks`，`pages/dsh-tasks/index.tsx`）
| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|----------|--------|
| PageHeader（标题「DSH 任务」+ 操作区） | 工具条 flex items-center gap-2 | 语义类 | — |
| 新建按钮 | Button default 尺寸（h-9） | variant=default | hover/active/focus ring 全局 |
| 新建 Dialog | DialogContent p-4；Textarea h-9 起，任务描述可多行 | Label 语义类 | 提交中禁用 + Loader2 animate-spin |
| 状态 Badge | Badge 默认 | pending=muted / running=info / success=success / failed=danger / cancelled=muted（中文映射） | 同 agent-workbench STATUS_BADGE 风格 |
| 详情 Sheet | SheetContent sm:max-w-lg；移动端 bottom | Card 背景语义 | 关闭按钮 aria-label |
| 输出块 | `<pre className="whitespace-pre-wrap font-mono text-xs">` | text-muted-foreground | — |

### 1.2 Agent 工作台 DSH 执行入口（改 `pages/agent-workbench/index.tsx`）
| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|----------|--------|
| Agent 类型卡/触发入口 | 复用现有类型卡片布局 | AGENT_ICONS/AGENT_COLORS 补 dsh_execution（Terminal 图标 + info/neutral 色） | 点击开触发 Dialog |
| 触发 Dialog | 复用现有 triggerDialog | Textarea 输入任务 | 提交中禁用 |
| runs 详情输出 | `<pre>` JSON.parse 后 JSON.stringify(x,null,2)，解析失败兜底原样 | font-mono text-xs | — |

## 2. 布局与响应式
| 断点 | 布局 | 变化 |
|------|------|------|
| <768px | 单列；Table 横向滚动（overflow-x-auto）；详情 Sheet bottom 全宽 | 工具条换行 gap-2 |
| md 768 | 列表 + 详情 Sheet sm:max-w-lg 右侧 | 保留 |
| lg 1024+ | 不变，最大宽度跟随布局容器 | — |

## 3. 状态设计核对（四态）
| 组件 | Loading | Empty | Error | 未启用(503) |
|------|---------|-------|-------|-------------|
| DSH 任务列表 | Skeleton 行 x3 | EmptyState「暂无 DSH 任务」 | ErrorState + 重试按钮 | Alert「DSH 服务未启用/未配置凭据」+ 原因（读 /health） |
| 新建提交 | 按钮 Loader2 禁用 | — | toast 失败原因 | 同上，提交入口禁用 |
| Agent 工作台触发 | 触发中禁用 | 类型列表空态 | runs 加载失败 ErrorState | 类型 available=false + unavailable_reason 展示（现有逻辑） |
| 详情输出 | Skeleton | 无输出显示「暂无输出」 | error 字段红字展示 | — |

## 4. 设计 QA 走查发现
### 🟠 P2-1 新 Agent 类型缺图标/颜色条目
`pages/agent-workbench/index.tsx:44-55` AGENT_ICONS/AGENT_COLORS 为固定字典，新增 dsh_execution 不补条目会无图标/无色。→ **建议**：补 `dsh_execution: Terminal` + info 色条目。
### 🟠 P2-2 输出 JSON 需格式化展示
`pages/agent-workbench/index.tsx` runs 详情输出若为原始 JSON 串直出，对非技术用户不可读。→ **建议**：统一 `JSON.parse → JSON.stringify(x,null,2)` + `<pre>`，解析失败原样兜底（对齐 ui-conventions Red Flag 6）。
### 🟡 P3-1 状态标签字典复用
现有 STATUS_BADGE 已是中文映射且覆盖 pending/running/success/failed/cancelled → DSH 任务页复用同字典，不新造一套（避免两处颜色漂移）。

## 5. 设计签核
结论：**有条件通过**。P2-1/P2-2 为必改项（随 Dev 实现一并落实）；无 P1 阻断项；P3-1 为规范约束。
