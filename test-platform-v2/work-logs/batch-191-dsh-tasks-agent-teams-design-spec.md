# Batch 191 — Design Spec：/dsh-tasks 支持 AgentTeams 团队模式

> **Design (🎨)** | Date: 2026-08-17 | Status: 就绪
> 配套 PRD：`batch-191-dsh-tasks-agent-teams-prd-summary.md`（mode: full，US-1~US-7）
> 配套 PM：`batch-191-dsh-tasks-agent-teams-pm-plan.md`（13 任务 T1–T13，依赖主线 T1/T2→T3→T4/T5/T6→T7→T8/T9→T10→T11→T12）
> 设计依据：`docs/superpowers/plans/2026-08-17-dsh-tasks-agent-teams-design.md`（方案 B1 已批准）
> 本规范把 PM 13 任务落到 Dev 可直接执行的技术契约；**§7 记录开工核实结果与对 PM 计划的 2 处事实修正**。

---

## 0. 技术体系确认

| 层 | 栈 | 关键约定（来源） |
|----|----|------------------|
| 后端 | FastAPI + SQLAlchemy 2.0（`Mapped`/`mapped_column`）+ Pydantic v2 + Alembic；DB = SQLite（dev）/ PostgreSQL（prod） | 分层：Router→Service→Model；**路由层禁 ORM**（Batch 181，`tests/test_route_layer_orm_ban.py` 守卫）；认领式任务队列统一走 `app/core/task_queue.py`（QueueSpec + atomic_claim，禁自研 SELECT→改→commit）；响应 envelope `{code,message,data}`（code=0 成功）；分页 `{items,total,page,page_size}` |
| 执行抽象 | `dsh_runner.run_dsh_task`（node CLI headless / python-sdk bundled runtime，Batch 184 沙箱：ws-{uuid} 隔离工作区 + `_concurrency_gate` 闸门 + `DSH_MAX_TASK_CHARS` 配额 + python-sdk env 锁） | 团队模式**复用**全部沙箱语义（C172-1 不回归），不新增旁路 |
| 前端 | React 19 + TS + shadcn/ui（Radix + Tailwind 语义类 + CVA），Lucide 图标，sonner toast | `cameltv-ui-conventions`：Token 走语义类（`bg-muted`/`text-muted-foreground`/`bg-status-*`），不裸色阶；四态（Loading/Empty/Error/503）齐备；AGENTS.md §3.4 React 副作用规则（useEffect 清理、无 N+1、useCallback 无 setState 循环依赖） |
| 团队运行时 | `@nanmicoder/dsh-agent-teams@0.1.5`（npm bundle 插件，web profile 已装验证）；AgentTeams 状态落 `<workspace>/.agent-teams/{teamId}/team.json` + `inbox/*.jsonl` | 工具九件套：`agent_teams_create` / `add_member` / `remove_member` / `create_task` / `claim_task` / `update_task` / `send_message` / `status` / `delete`（插件 lib/tools.js 已核实） |

**状态词表边界**（避免 Batch 182 混淆）：`dsh_task.status` 是**队列生命周期词表** `pending|running|success|failed|cancelled`（Batch 172 既有，PRD/PM/设计文档一致确认不动）；Batch 182 统一词表（passed 等）针对 test_execution 等执行状态表，**不适用于 dsh_task**。团队内部任务状态词表（`pending|claimed|in_progress|completed|failed|cancelled`）是插件 `team.json` 的字段，与 dsh_task.status 无关，前端展示单独映射。

---

## 1. 数据模型设计（PM T2）

### 1.1 `DshTask` 新增两列（`backend/app/models/dsh_task.py`）

```python
mode: Mapped[str] = mapped_column(default="single", index=True)  # single | team（Batch 191）
team_json: Mapped[str] = mapped_column(Text, default="{}")       # 团队进度快照（JSON 字符串，幂等全量覆盖）
```

- `mode` 语义：任务形态标签，**非状态值**；`single` = 现状单任务（存量行默认值），`team` = 船长自组织团队。
- `team_json` 语义：**平台侧只读快照**，内容 = 插件 `team.json` 持久化记录的原文（全量覆盖写，不做增量合并）。默认 `"{}"`（`"{}"` 与 `""` 区分：`{}` = 团队模式尚无进度或 single 模式恒为 `{}`）。
- 不放 `batch_mode` 列：批次模式是提交参数（`params.batch_mode`），随 `params_json` 落库即可，避免冗余列与 schema 漂移（与 B1「模型最小扩展」一致）。

### 1.2 Alembic 迁移 `20260817_b191_dsh_team_mode`（`backend/alembic/versions/`）

**开工已核实（§7.1）**：`alembic heads` 单头 = `20260816_b182_status_unify`（branch label batch27，仅一个 head）→ `down_revision = "20260816_b182_status_unify"`。

```python
revision = "20260817_b191_dsh_team_mode"
down_revision = "20260816_b182_status_unify"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("dsh_task", sa.Column("mode", sa.String(length=16),
        server_default="single", nullable=False))
    op.add_column("dsh_task", sa.Column("team_json", sa.Text(),
        server_default="{}", nullable=False))
    op.create_index("ix_dsh_task_mode", "dsh_task", ["mode"])

def downgrade() -> None:
    op.drop_index("ix_dsh_task_mode", table_name="dsh_task")
    op.drop_column("dsh_task", "team_json")
    op.drop_column("dsh_task", "mode")
```

要点（SQLite/PG 双兼容）：
- `add_column` 必须带 `server_default`（存量行回填：mode="single"、team_json="{}"）；**不加** Python 侧 default 参与迁移（Python default 由 ORM 管）。
- 命名对齐既有风格：`20260816_b181_task_queue_locks.py`（列名语义直白）；索引名 `ix_dsh_task_mode` 与 SQLAlchemy 默认命名一致（`index=True` 自动建同名索引，迁移不重复建）。
- `nullable=False` + server_default：SQLite `ALTER TABLE ADD COLUMN NOT NULL` 需要默认值，PG 同理，写法兼容。
- 迁移后校验：`alembic upgrade head`、`alembic downgrade -1`（或 `-1` 语义按仓库惯例）可逆；`alembic heads` 仍单头。

### 1.3 模型序列化

`DshTaskOut.model_validate(row)` 需含 `mode`/`team_json`——ORM 存字符串，出参转 dict 的转换规则见 §2.2（field_validator，不依赖 ORM 自定义类型）。

---

## 2. API / Schema 契约（PM T3）

### 2.1 `DshTaskCreate`（`backend/app/schemas/dsh.py`）

```python
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class DshTaskCreate(BaseModel):
    task: str = Field(..., min_length=1, max_length=20000, description="任务文本")
    params: dict = Field(default_factory=dict, description="附加参数（batch_mode 等）")
    mode: Literal["single", "team"] = "single"

    @model_validator(mode="after")
    def _validate_batch_mode(self):
        batch_mode = (self.params or {}).get("batch_mode")
        if self.mode == "team":
            if batch_mode is None:
                raise ValueError("mode=team 时必须提供 params.batch_mode（full|light）")
            if batch_mode not in ("full", "light"):
                raise ValueError(f"params.batch_mode 非法: {batch_mode!r}（仅支持 full|light）")
        else:
            if batch_mode is not None:
                raise ValueError("params.batch_mode 仅团队模式（mode=team）可用")
        return self
```

校验规则（落到 422，走 FastAPI 默认校验错误格式，与既有风格一致）：
1. `mode` 非 `single|team` → Pydantic `Literal` 自动 422。
2. `mode=team` 且缺 `params.batch_mode` → 422「必须提供」（PRD US-1：用户选择批次模式，必填不默认）。
3. `mode=team` 且 `batch_mode` 非 `full|light` → 422「非法值」。
4. `mode=single` 且带了 `batch_mode` → 422「仅团队模式可用」（严格拒绝防误用；现状无任何调用方传 batch_mode，无兼容风险）。

### 2.2 `DshTaskOut` 扩展

```python
class DshTaskOut(BaseModel):
    id: int
    project_id: int
    task: str
    status: str
    mode: str = "single"
    team_json: dict = {}          # 响应为对象；ORM 存字符串，经 before validator 转换
    output_text: str = ""
    session_dir: str = ""
    error: str = ""
    operator_id: int = 0
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @field_validator("team_json", mode="before")
    @classmethod
    def _parse_team_json(cls, v):
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v) if v else {}
            except json.JSONDecodeError:
                return {}          # 损坏快照不阻断详情；前端显示"进度数据不可用"
        return {}

    model_config = {"from_attributes": True}
```

- `team_json` 响应恒为对象（空 = `{}`），前端无需判字符串/对象双态。
- 列表与详情共用 `DshTaskOut`；**不加新端点**（B1 决策，复用 GET `""` / GET `/{id}`）。

### 2.3 API 层透传（`backend/app/api/v1/dsh_tasks.py`）

- `create_dsh_task`：`dsh_task_service.submit_task(db, project_id=..., task=body.task, params=body.params, mode=body.mode, operator_id=...)`；路由只做校验/透传/组装响应（禁 ORM）。
- 503 前置（DSH 不可用）保持现状；`mode=team` 同样受 503 门禁。
- **C86-1 双 404 约定**：详情/取消对「不存在任务」与「跨 project 任务」均返回 404（`get_task`/`cancel_task` 既有 project_id 过滤不变，团队任务无特例）。
- 请求/响应示例：

```json
POST /api/v1/dsh-tasks
{ "task": "为登录模块生成用例并跑回归", "mode": "team", "params": { "batch_mode": "full" } }

200 → { "code": 0, "data": { "id": 42, "task": "...", "status": "pending",
  "mode": "team", "team_json": {}, "params_json 不入出参", ... } }

GET /api/v1/dsh-tasks/42
200 → { "code": 0, "data": { ..., "mode": "team",
  "team_json": { "id": "...", "name": "...", "captainSessionId": "...", "members": [...], "tasks": [...] } } }
```

---

## 3. 执行侧设计（PM T4 / T5）

### 3.1 `run_dsh_task` 双运行时路由（`backend/app/services/dsh/dsh_runner.py`）

签名扩展（向后兼容，single 默认）：

```python
def run_dsh_task(
    task: str,
    *,
    workspace: str | None = None,
    session_root: str | None = None,
    model: str | None = None,
    timeout: float | None = None,
    extra_env: dict[str, str] | None = None,
    mode: str = "single",          # 新增（Batch 191）
) -> DshRunResult:
```

路由规则（`_concurrency_gate` 内、`_workspace_for` 之后分支）：

| mode | node 运行时 | python-sdk 运行时 | 超时 |
|------|-------------|-------------------|------|
| single | `["node", entry, "--profile", "headless", task]`（现状不变） | `dsh_cordis_config` 或内置 `minimal.cordis.yml`（现状不变） | `dsh_timeout_seconds`（600s） |
| team | `["node", entry, "--profile", settings.dsh_team_profile, task]`（默认 profile 名 `agent-team`） | `dsh_team_cordis_config` 或内置 `team.cordis.yml` | `dsh_team_timeout_seconds`（1800s） |

实现要点：
- `profile_name = "headless" if mode == "single" else (settings.dsh_team_profile or "agent-team")`；harness 入口 `_node_entry()` 不变（profile 由 CLI 从 `$DSH_HOME/profiles/` 解析，**平台不传路径**，见 §7.2）。
- python-sdk：`cordis = (settings.dsh_team_cordis_config or "").strip()`，空 → `Path(__file__).parent / "team.cordis.yml"`；存在性检查与 single 相同（缺失 → exit 1 + 可读 error）。
- 超时：`resolved_timeout = (timeout or settings.dsh_team_timeout_seconds if mode == "team" else settings.dsh_timeout_seconds)`——走既有 subprocess timeout / SDK 路径，`DshRunResult(timed_out=True, exit_code=124, error="dsh 执行超时（>1800s）")` 语义不变（R-4）。
- **沙箱不回归（C172-1）**：团队分支在 `_concurrency_gate` 内执行（排队）、经 `_workspace_for` 分配 `ws-{uuid}` 隔离工作区、`DSH_MAX_TASK_CHARS` 文本配额检查在入口统一生效、python-sdk env 锁（C172-2）包住团队分支的 SDK 调用——**一行旁路都不加**。
- `DshRunResult` 增加字段 `workspace: str = ""`（runner 内部 `_workspace_for` 的返回值，执行完成后精确回传，供终态 team.json 读取；single 模式留空不影响既有断言）。**注意**：实时轮询不能等这个字段（执行未结束），用 §4.2 的隔离根扫描方案。

### 3.2 `build_agent_team_persona` 船长提示词（新增 `backend/app/services/dsh/agent_team_persona.py`）

签名：`build_agent_team_persona(task: str, batch_mode: str) -> str`（纯函数，无 IO，单测友好）。

提示词结构（固定步骤，全文字面，两运行时共用；经 `extra_env["DSH_SYSTEM_PROMPT"]` 注入）：

```text
你是测试平台提交的 DSH 船长（AgentTeams 船长模式）。请严格按以下步骤用 agent_teams_* 工具自组织团队完成目标。

【用户目标】{task}
【批次模式】{full|light}

【固定步骤】（逐步执行，每一步用对应工具，不要跳过）
1. agent_teams_create：创建团队（name 用目标主题摘要，description 写用户目标原文）。
2. agent_teams_add_member：按批次模式添加成员——
   - full（完整批次）：product、pm、design、dev、qa 五名成员，role 分别为「产品/项目管理/设计/开发/测试」；
   - light（轻量批次）：product、qa 两名成员，role 分别为「产品/测试」。
3. agent_teams_create_task：把用户目标拆成带依赖关系的子任务（如 PRD→计划→设计→实现→测试/门禁），用 dependencies 参数表达先后依赖。
4. agent_teams_claim_task：按依赖顺序把任务认领派发给对应成员（一次一个任务，等成员完成后派发下一个依赖就绪的任务）。
5. 收集各成员结论：成员完成任务后用 agent_teams_send_message 汇报，你在收件后继续派发后续任务。
6. 全部任务完成后：汇总各成员结论，写一份【最终报告】（含：团队分工、各任务结果、总体结论），作为最终回复输出。

【产出要求】工作产物写入当前工作区 work-logs/ 目录（如无可新建），最终报告同时作为回复文本输出。
【约束】不要创建用户目标之外的额外任务；不要删除团队（保留团队档案供平台复盘）。
```

- full 成员集 `product/pm/design/dev/qa`、light 成员集 `product/qa`（PRD §1.3 / 设计文档 §4.2 固化）。
- 失败不静默：模型自组织失败 → 船长会话异常由 runner 兜底为 `status=failed` + 可读 `error`（R-5），persona 不承诺重试。
- 平台侧不重复移植仓库级 Agent Team 技能（非目标红线）。

### 3.3 `team.cordis.yml`（新增 `backend/app/services/dsh/team.cordis.yml`，python-sdk 团队组合）

= `minimal.cordis.yml` 全部行不变 + 追加插件行（格式照插件自带 `cordis.patch.yml` 的 insert 条目，已核实插件包源码；注意顶层是数组，插件行作为数组元素追加在文件末尾）：

```yaml
# ── Batch 191：AgentTeams 团队模式插件行（追加于 minimal.cordis.yml 之后）──
- id: agent-teams
  name: '@nanmicoder/dsh-agent-teams'
  config:
    stateDir: .agent-teams
    memberProvider: spawn
```

- 插件为 npm bundle（`dsh.bundle` 声明已核实）；SDK bundled runtime 能否解析该包是 **R-2** 风险——冒烟失败 → 登记 C191-1 deferred（node 先交付），**不静默 fallback 到 single**（US-7）。
- YAML 校验：`yaml.safe_load` 可解析且数组元素数 = minimal 行数 + 1（单测断言）。

### 3.4 agent-team profile 模板（新增 `backend/app/services/dsh/agent-team/` 目录）

**开工核实（§7.2）**：CLI `--profile <name>` 解析 `$DSH_HOME/profiles/<name>`；本机 `$DSH_HOME=C:\Users\26029\.dsh`，已有 `profiles/headless`、`profiles/web`；`F:\deepseek-harness\` 下**没有** profiles 目录（PM 计划 T5 的「自动探测 F:\deepseek-harness\profiles\agent-team」假设不成立，见修正记录）。

profile 骨架（照 `profiles/headless` 模板，目录 `$DSH_HOME/profiles/agent-team/`）：

| 文件 | 内容要点 |
|------|---------|
| `package.json` | `name: "dsh-profile-agent-team"`, `private: true`；`dependencies: {"@nanmicoder/dsh-agent-teams": "^0.1.5"}`；`dsh.profile.bundles: ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-headless", "@nanmicoder/dsh-agent-teams"]` |
| `cordis.yml` | `[]`（根空，与 headless 一致） |
| `cordis.patch.yml` | 追加 §3.3 同款插件行（`- insert:` 块或顶层数组元素，照插件自带 patch 格式） |
| `pnpm-workspace.yaml` | `packages: [.]`、`nodeLinker: hoisted`、`autoInstallPeers: false`、`allowBuilds: {node-pty: true}`（照 web/headless） |
| `README.md` | 安装步骤 + `DSH_TEAM_HARNESS_PATH` 覆盖说明（见下） |

安装方式（README 写清两种，推荐 A）：
- **A（推荐）**：`dsh plugin --profile agent-team add @nanmicoder/dsh-agent-teams`（CLI 官方命令：创建 profile 骨架 + pnpm 安装 + 写入 `dsh.profile.bundles`）——仓库内只保留 `agent-team/README.md` + 模板文件（`package.json.template` / `cordis.patch.yml.template`），实际安装位在 `$DSH_HOME/profiles/agent-team`（本机 `C:\Users\26029\.dsh\profiles\agent-team`，不入库）。
- **B（手工）**：复制模板到 `$DSH_HOME/profiles/agent-team/`，`pnpm install` 后验证。
- 安装完成自检（冒烟前置，PM T5 验收）：`dsh --profile agent-team --dump-config` 能输出组合树（含 agent-teams 插件）且无「profile 不存在」错误。

`dsh_team_harness_path` 配置语义（**修正 PM T1**）：空 = 使用 CLI 默认 `$DSH_HOME`（Windows 本地 `%USERPROFILE%\.dsh`，自动探测）；非空 = 作为 `DSH_HOME` 环境变量注入 node 子进程（profile 从 `{dsh_team_harness_path}/profiles/agent-team` 解析）。它不是 bin.js 路径（那是 `dsh_harness_path`）。

### 3.5 配置项（PM T1，`backend/app/core/config.py` + `.env.example` 注释）

```python
dsh_team_timeout_seconds: float = 1800.0   # 团队任务超时（覆盖单任务 600s；R-4）
dsh_team_poll_seconds: float = 3.0         # 进度轮询间隔（PRD 成功指标引用）
dsh_team_profile: str = "agent-team"       # node profile 名
dsh_team_cordis_config: str = ""           # python-sdk 团队 cordis 路径；空 = 内置 team.cordis.yml
dsh_team_harness_path: str = ""            # 团队 profile 的 DSH_HOME 覆盖；空 = 自动探测
```

`.env.example` 追加注释行（不写真实凭据），命名对齐既有 `DSH_*` 风格。

---

## 4. 服务层设计（PM T6）

### 4.1 `submit_task` / `list_tasks` / `get_task` / `cancel_task` 扩展

- `submit_task(..., mode: str = "single")`：落库 `mode` 列；`params_json` 原样（含 batch_mode）；其余不变。
- `list_tasks`：可选加 `mode` 过滤参数（前端列表不需要按 mode 过滤，但参数低成本预留；**不加**则保持签名不变——本规范定：不加，最小改动）。
- `get_task` / `cancel_task`：**零改动**（project_id 过滤、仅 pending 可取消语义不变；running 团队取消延后 = C191-2 登记）。

### 4.2 `execute_task` 团队分支线程模型

现状 single 路径 `execute_task(db, task, runner=None)` 同步执行，零改动。新增 `mode == "team"` 分支：

```
execute_task(db, task, runner=None)  [调用线程，持认领 session]
├─ params = json.loads(task.params_json)；batch_mode = params.get("batch_mode", "full")
├─ persona = build_agent_team_persona(task.task, batch_mode)
├─ result_box = queue.Queue(maxsize=1)              # 执行结果传回（线程安全）
├─ stop_event = threading.Event()                   # 轮询线程终止信号
├─ T_exec = threading.Thread(target=_team_runner, args=(task, persona, result_box), daemon=True)
│    └─ runner(task.task, workspace=params.get("workspace"), mode="team",
│              timeout=settings.dsh_team_timeout_seconds,
│              extra_env={"DSH_SYSTEM_PROMPT": persona}) → result_box.put(result)
├─ T_poll = threading.Thread(target=_team_poller, args=(task.id, stop_event), daemon=True)
│    └─ 循环（stop_event.wait(dsh_team_poll_seconds)）：
│         workdir = 隔离根扫描（§4.3）→ 读到 team.json → 独立短 SessionLocal 全量幂等写 task.team_json
├─ T_exec.start(); T_poll.start()
├─ T_exec.join(timeout=settings.dsh_team_timeout_seconds + 60)   # 防御性兜底
├─ stop_event.set(); T_poll.join(timeout=5)                       # 终止轮询线程（含清理）
├─ result = result_box.get()（若 T_exec 异常/超时未放 → 构造 failed 结果）
├─ 终态：再读一次 team.json（用 result.workspace 精确路径，§4.3）写 team_json
├─ 写 task.status / output_text[:20000] / error[:2000] / session_dir / finished_at（用认领 session commit）
└─ 异常兜底：except → task.status="failed", error=str(exc)[:2000], finished_at 落库（与 single 一致）
```

线程安全铁律（R-3）：
- **执行线程 T_exec 不碰任何 DB session**（run_dsh_task 纯子进程/SDK 调用）。
- **轮询线程 T_poll 每次写库用独立短 `SessionLocal()`**（`with SessionLocal() as s: s.get(DshTask, task_id); s.commit()` 或等价短生命周期），**绝不使用 execute_task 的认领 session、绝不复用任何共享 session**（单测断言：轮询写入路径不引用传入 db）。
- `team_json` **全量幂等覆盖**（`task.team_json = json.dumps(snapshot, ensure_ascii=False)`），无增量合并；写失败（如文件被插件串行写占用瞬间）捕获后下轮重试，不中断轮询。
- 两个线程均 `daemon=True`：worker 退出/进程终止不悬挂。

### 4.3 team.json 发现与读取

- **实时轮询（隔离根扫描）**：隔离根 = `params.workspace` 或 `settings.dsh_workspace` 或 `session_root/workspaces`（与 `_workspace_for` 同规则）。扫描 `{root}/ws-*/` 下所有 `.agent-teams/<teamId>/team.json`；**首次成功解析**的路径记为锁定目标（`_team_json_path` 变量），此后只读该路径（防并发任务串扰；DSH_MAX_CONCURRENT=1 时实际只有一个 ws-*）。解析失败（文件半写/损坏）跳过该轮。
- **终态读取（精确路径）**：`DshRunResult.workspace` 返回本次 `ws-{uuid}` 路径 → 直接读 `{workspace}/.agent-teams/<teamId>/team.json`（无扫描歧义）。
- 快照内容 = 插件 `team.json` **原文**（TeamState：`id/name/description?/captainSessionId/members[{id,name,role?,status}]/tasks[{id,subject,description?,status,assignee?,dependencies[]}]`；任务状态 `pending|claimed|in_progress|completed|failed|cancelled`——已核实插件 lib/state.js）。平台不加工、不重命名；展示派生（成员进度%、依赖深度）放前端计算。
- **数据大小防御**（PRD §5）：`team_json` 写入前截断——上限 `settings.dsh_max_output_chars`（20000）字符，超长截断并在快照内加 `"_truncated": true` 标记（前端显示「进度数据已截断」）；与 output_text 截断口径对齐。

### 4.4 超时 / 错误 / 取消

| 场景 | 行为 |
|------|------|
| 执行超时（>1800s） | `run_dsh_task` 内部 subprocess/SDK timeout → `DshRunResult(exit_code=124, timed_out=True, error="dsh 执行超时（>1800s）")` → `task.status="failed"` + 可读 error + `finished_at` 落库；已有 `team_json` 进度**保留**（US-4） |
| 执行异常（插件不可用/profile 缺失等） | runner 返回 exit≠0 + error（如「DSH 不可用」「profile 不存在」）→ failed + error 落库（R-1/R-2 可追溯） |
| T_exec.join 兜底超时 | 记录 `error="团队执行线程异常终止（未知原因）"`，failed 落库，不悬挂 |
| 轮询线程异常 | `logger.warning` 后继续（单轮失败不退出轮询）；连续失败不阻塞执行线程结果 |
| 取消 | 仅 pending 可取消（现状）；running 团队任务取消延后（**C191-2** 登记，不实现） |
| 终态 `team_json` | 执行结束后读取的最后一版快照（可能含部分进度 + `_truncated`），与 `output_text`（船长最终报告）并存 |

---

## 5. 前端设计（PM T8 / T9）

### 5.1 API 类型与调用（`frontend/src/api/dshTasks.ts`）

```ts
export interface DshTask {
  id: number
  project_id: number
  task: string
  status: string
  mode: string              // 'single' | 'team'（Batch 191）
  team_json: Record<string, any>   // 团队进度快照（空 = {}）
  output_text: string
  session_dir: string
  error: string
  operator_id: number
  created_at: string | null
  started_at: string | null
  finished_at: string | null
}

export async function createDshTask(
  task: string,
  params?: Record<string, any>,
  mode?: 'single' | 'team',
): Promise<DshTaskCreateResult> {
  return api.post('/dsh-tasks', { task, params: params ?? {}, mode: mode ?? 'single' })
}
```

（`fetchDshTasks` / `fetchDshTask` / `cancelDshTask` 签名不变，响应自动带新字段。）

### 5.2 提交面板（`frontend/src/pages/dsh-tasks/index.tsx` Dialog 扩展）

- 模式选择：`RadioGroup`（或 shadcn `Select`）单选项——**标准模式（single）** / **团队模式（team）**，默认标准。加 `aria-label="任务模式"`。
- 团队模式选中时显示**批次模式下拉**：`Select` 选项 完整批次（full）/ 轻量批次（light），默认 full；`aria-label="批次模式"`。切换回标准模式时隐藏下拉。
- 提交：`createDshTask(taskText, { batch_mode }, mode)`；后端 422（非法 mode/batch_mode）→ toast 显示明确错误（sonner，沿用 `handleCreate` 的 catch 分支）。
- Dialog 描述文案更新：团队模式提示「将创建 DSH 船长会话，自组织多成员团队执行」。

### 5.3 列表 mode 徽标

- 表格加「类型」列（`w-16`，置于状态列前或后——**规范：置于「任务」列与「状态」列之间**，避免与状态徽标混淆）：
  - single → `<Badge variant="outline">标准</Badge>`（`bg-muted text-muted-foreground` 亦可，二选一；**规范：outline + 标准**）
  - team → `<Badge className="bg-status-info-muted text-status-info">团队</Badge>`
- 空态文案不变（colSpan 从 5 改 6）。

### 5.4 详情团队进度树（拆子组件 `frontend/src/pages/dsh-tasks/team-progress.tsx`）

渲染条件：`detail.mode === 'team' && Object.keys(detail.team_json).length > 0`。

**轮询刷新**（遵循 AGENTS.md §3.4，强制）：
- 详情 Sheet 打开且 `detail.mode==='team' && detail.status==='running'` 时，`useEffect` 内 `setInterval` 每 3000ms（`DSH_TEAM_POLL_SECONDS` 前端常量）调 `fetchDshTask(detail.id, signal)`；**cleanup 必须 `clearInterval` + AbortController.abort`**（fake timers 单测断言卸载后无残留定时器）。
- 非 running（success/failed/cancelled）不轮询（终态只拉一次）。
- 列表页既有 `hasRunning` 指数退避轮询（Batch 178）不动；详情轮询独立于列表轮询（各自清理，无 N+1——每个 tick 单请求）。

**进度树结构**（自顶向下）：

```
┌ 团队头：团队名（team_json.name）+ 团队 id + 当前阶段（由任务状态推导：pending=等待认领/running=执行中/success=已完成/failed=失败）
├ 成员卡区（team_json.members，grid 自适应）：
│   每卡 = 成员名 + role（text-xs muted）+ 状态徽标（active=在队/removed=已移除，中文映射）
│         + 进度条（done/total 推导 %；h-2 rounded bg-muted，填充 bg-status-info）
│         + 当前任务（推导：首个 in_progress 且 assignee==该成员 的 task.subject，无则「—」）
├ 任务列表区（team_json.tasks，按 depth 排序）：
│   每行 = 状态徽标（pending=等待中/claimed=已认领/in_progress=执行中/completed=已完成/
│           failed=失败/cancelled=已取消，中文映射字典 TEAM_TASK_STATUS_BADGE）+ 标题 subject
│         + assignee（指派成员）+ 依赖（dependencies 显示 `依赖 #<id>` 或空）
├ 团队结论区（team_json.conclusion 若存在；否则取 output_text 尾部）：
│   pre 样式（bg-muted p-3 rounded-md whitespace-pre-wrap，无 Markdown 渲染库）
└ 截断提示：team_json._truncated === true → 提示「进度数据已截断」
```

状态映射字典（新文件或页内常量，中文标签风格对齐 `executionStatus.ts`）：

```ts
const TEAM_TASK_STATUS_BADGE: Record<string, { label: string; color: string }> = {
  pending:     { label: '等待中', color: 'bg-muted text-muted-foreground' },
  claimed:     { label: '已认领', color: 'bg-muted text-muted-foreground' },
  in_progress: { label: '执行中', color: 'bg-status-info-muted text-status-info' },
  completed:   { label: '已完成', color: 'bg-status-success-muted text-status-success' },
  failed:      { label: '失败',   color: 'bg-status-danger-muted text-status-danger' },
  cancelled:   { label: '已取消', color: 'bg-muted text-muted-foreground' },
}
const MEMBER_STATUS_BADGE = { active: '在队', removed: '已移除' }
```

`team_json` 为 `{}`（尚无进度）且 running → 显示「团队进度尚未产生，等待船长建队…」（Empty 态，非错误）。`team_json` 损坏（后端解析兜底已给 `{}`）同 Empty。

### 5.5 组件规格表（DEPARTMENTS.md §3 骨架）

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|----------|--------|
| 模式 RadioGroup | `space-y-2`，选项 h-9 | 语义类默认 | hover 默认 / focus-visible 全局 ring（globals.css 已配，不加） |
| 批次 Select | h-9 | 默认 | 同上 |
| mode 徽标（列表） | `h-5 px-2 text-xs` | team=`bg-status-info-muted text-status-info`；single=`outline` | 无交互 |
| 成员卡 | `Card p-3`，grid `grid-cols-1 sm:grid-cols-2` | `bg-card border` | 无交互 |
| 进度条 | `h-2 rounded bg-muted`，填充 `bg-status-info` | 语义 | 无交互 |
| 任务行 | `py-2 text-sm`，`flex items-center gap-2` | 状态 Badge 色 | 无交互（只读树） |
| 结论区 | `pre p-3 rounded-md text-xs` | `bg-muted` | 无交互 |
| 触控目标 | 列表行 `min-h-[36px]`、行内按钮 `h-8` | — | Red Flag 7 防回归 |

### 5.6 布局与响应式

| 断点 | 布局 | 变化 |
|------|------|------|
| <768px（手机） | 单列；成员卡 1 列；进度树在详情 Sheet（`w-full sm:max-w-lg` 既有）内滚动 | 无并排 |
| 768–1023px（平板） | 成员卡 2 列（`sm:grid-cols-2`）；任务列表单列 | Red Flag 8：不跳 3 列 |
| ≥1024px（桌面） | 成员卡 2–3 列（`lg:grid-cols-3`）；其余不变 | 保持详情 Sheet 宽度内自适应 |

### 5.7 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用(503) |
|------|---------|-------|-------|-------------|
| 提交面板 | 提交按钮 `Loader2 spin` + disabled | 任务文本空 → 提交 disabled | toast（sonner）明确错误 | 页头既有 503 横幅 + 新建按钮 disabled（现状） |
| 详情进度树 | `Skeleton`（详情加载中，既有） | team_json 空 → 「团队进度尚未产生…」 | 详情加载失败 → toast + 可点行重开；team_json 损坏 → 后端兜底 `{}` | 复用页头 503 横幅 |
| 列表 | `Skeleton` 行（既有） | 「暂无 DSH 任务」空态（colSpan 6） | 列表加载失败 toast（既有） | 同上 |

---

## 6. 测试设计（PM T7 / T9 / T11 / T12 映射）

### 6.1 后端单测（PM T7）

| 用例文件 | 覆盖点（对应 PM） |
|----------|-------------------|
| `tests/test_dsh_tasks.py`（扩展） | **T3**：POST mode=team+batch_mode=full 成功返回 mode=team；mode="x"→422；team 缺 batch_mode→422；batch_mode="x"→422；single 带 batch_mode→422；列表/详情含 mode 与 team_json（空 `{}`）；C86-1 双 404 回归（详情/取消：不存在 + 跨项目均 404）；**T6**：execute_task 团队分支（mock runner + 临时目录 team.json）——轮询 ≥2 次快照写入 task.team_json、终态快照、success/failed 与 output_text/error、超时路径（runner 返回 124）→ failed + error 含超时标识 + team_json 保留 |
| `tests/test_dsh_runner.py`（扩展） | **T4**：`run_dsh_task(mode="team")` node 分支 cmd 含 `--profile agent-team`（mock subprocess）；python-sdk 分支 cordis 指向 team.cordis.yml；团队超时 → `DshRunResult(exit_code=124, timed_out=True, error 可读)`；single 行为零变化回归 |
| `tests/test_dsh_sandbox.py`（扩展） | **C172-1（US-6）**：mode=team 仍走 `_workspace_for`（ws-{uuid} 目录创建断言）、`_concurrency_gate`（并发排队断言）、`DSH_MAX_TASK_CHARS` 超限拒绝；C172-2 python-sdk env 锁路径不回归 |
| 新 `tests/test_agent_team_persona.py` | **T5**：`build_agent_team_persona` full→成员集含 product/pm/design/dev/qa；light→product/qa；含用户目标原文与 6 固定步骤关键词；`team.cordis.yml` YAML 可解析且含 `id: agent-teams` 行；`agent-team/` 模板文件存在且 README 含安装步骤与 DSH_TEAM_HARNESS_PATH 说明 |

### 6.2 前端 vitest（PM T9，新建 `frontend/src/pages/dsh-tasks/__tests__/`）

| 用例 | 断言 |
|------|------|
| 模式切换 | 默认标准模式无批次下拉；切团队模式出现批次下拉；切回标准隐藏 |
| 进度树渲染 | mock team_json（2 成员 + 3 任务含依赖 + 结论）渲染成员卡/任务列表/结论；空 team_json 显示 Empty 文案；`_truncated` 显示截断提示 |
| 轮询清理 | fake timers：running 团队详情打开 → setInterval 触发 fetchDshTask；卸载 → `clearInterval` 被调用、无残留定时器（vitest `vi.getTimerCount() === 0`） |
| mode 徽标 | 列表 team/single 行徽标文案「团队/标准」 |

### 6.3 冒烟（PM T11，真实执行）

| 冒烟项 | 判定 | 结果处理 |
|--------|------|----------|
| node mini 团队（`--profile agent-team`） | 建队→加成员→带依赖任务→派发→进度→终态；`team_json` 终态含 members/tasks；`output_text` 含最终报告；两次详情拉取间 team_json 有变化（粒度 ≤3s）；全程在 ws-{uuid} 工作区（沙箱实证） | success 记录为 QA 证据（截图/日志） |
| python-sdk（`team.cordis.yml`） | SDK 可加载 npm bundle 插件并完成团队组合 | 成功 → 记录；失败 → 登记 **C191-1 deferred**（README/ADR 注明 node 先行），不静默 fallback（US-7） |

### 6.4 门禁（PM T12）

- 后端：`ruff check app --select F821`（exit 0）、pytest 全量（记录基线 vs 本分支失败集合、退出码，C78-1）、`alembic heads` 单头。
- 前端：`npm run typecheck`、`npm run build`、相关 vitest。
- 无调试遗留 / 无硬编码密钥（提交前自检）；OpenAPI 同步（DshTaskCreate.mode / DshTaskOut.mode+team_json，gen:api 后前端类型对齐）。

---

## 7. 开工核实记录与事实修正

### 7.1 已核实（开工日，证据为本仓库 + 本机运行时）

| # | 事实 | 证据 |
|---|------|------|
| V1 | `alembic heads` 单头 = `20260816_b182_status_unify`（branch label batch27） | `python -m alembic heads` 实跑 |
| V2 | CLI `--profile <name>` 解析 `$DSH_HOME/profiles/<name>`（官方注释原文） | `F:\deepseek-harness\apps\cli\lib\bin.js:77` |
| V3 | headless profile 组成：package.json（`dsh.profile.bundles`）+ cordis.yml(`[]`) + cordis.patch.yml + pnpm-workspace.yaml | `C:\Users\26029\.dsh\profiles\headless\*` |
| V4 | `@nanmicoder/dsh-agent-teams@0.1.5` 为 bundle 插件，dependencies + `dsh.profile.bundles` 装入 | `C:\Users\26029\.dsh\profiles\web\package.json` |
| V5 | 插件 cordis 行格式：`- insert: - id: agent-teams, name: '@nanmicoder/dsh-agent-teams', config: {stateDir: .agent-teams, memberProvider: spawn}`；团队状态落 `<workspace>/.agent-teams/<teamId>/team.json` | 插件包 `cordis.patch.yml`、`lib/state.js` |
| V6 | team.json 结构（TeamState）：`id/name/description?/captainSessionId/members[{id,name,role?,status}]/tasks[{id,subject,description?,status,assignee?,dependencies[]}]`；任务状态 `pending|claimed|in_progress|completed|failed|cancelled` | 插件 `lib/state.js`、`lib/snapshot.js`、`lib/tools.js` |
| V7 | 九件套工具名（create/add_member/remove_member/create_task/claim_task/update_task/send_message/status/delete） | 插件 `lib/tools.js` |

### 7.2 对 PM 计划的 2 处事实修正（Dev 开工以本规范为准）

1. **agent-team profile 安装位**：PM T5「自动探测 `F:\deepseek-harness\profiles\agent-team`」不成立——harness checkout 下无 profiles 目录，CLI 从 `$DSH_HOME/profiles/<name>` 解析（V2/V3）。**修正**：安装位 = `$DSH_HOME/profiles/agent-team`（本机 `C:\Users\26029\.dsh\profiles\agent-team`）；`dsh_team_harness_path` 语义 = 覆盖 `DSH_HOME`（§3.5），README 同步。
2. **轮询的 team.json 定位**：设计文档 §4.3 写 `{ws}/.agent-teams/{team}/team.json`，但 `run_dsh_task` 返回的 `session_dir` 是 session_root 而非 ws-{uuid} 工作区（现状代码核实）。**修正**：实时轮询用「隔离根扫描 ws-*/ 首次命中锁定」方案（§4.3），终态用新增 `DshRunResult.workspace` 精确路径。

### 7.3 风险对照（设计文档 §7 / PM 风险提示 → 规范落点）

| 风险 | 本规范落点 |
|------|-----------|
| R-1 插件 headless 可用性 | §3.4 安装自检 `--dump-config` + §6.3 node 冒烟兜底 |
| R-2 python-sdk bundle 加载 | §3.3 team.cordis.yml 先行 + C191-1 deferred 路径（US-7） |
| R-3 轮询/执行并发写 DB | §4.2 独立短 SessionLocal + 全量幂等 + 线程不共享 session（单测断言） |
| R-4 团队超时 1800s | §3.1 超时路由 + §4.4 超时表 |
| R-5 persona 不稳定 | §3.2 固定步骤 + failed/error 可追溯 |
| R-6 并发闸门排队 | 沿用（README 说明排队语义，PM T10） |
| team 目录发现 | §4.3 首次命中锁定 + mtime 最新 |
| 进度树数据量 | §4.3 20000 字符截断 + `_truncated` 标记 + 前端 mock 验证 |

---

## 8. 设计走查与签核

### 8.1 走查发现（对照 cameltv-ui-conventions Red Flags 预检，实现后需反向回填锚点）

- **RF-3 状态标签中文映射**：团队任务状态（claimed/in_progress 等）与成员状态（active/removed）必须走中文映射字典（§5.4），禁止裸英文——已入规范 ✅
- **RF-4/5 四态与失败态**：进度树 Empty/Error 态已定义（§5.7）；running（spin）与 failed（红色 AlertCircle 语义）区分——已入规范 ✅
- **RF-6 原始 JSON 不裸展示**：team_json 只经进度树组件派生展示，不直接 `<pre>` 输出整包（除结论区白名单文本）——已入规范 ✅
- **RF-7 触控目标**：列表行 min-h-[36px]、行内按钮 h-8——已入规范 ✅
- **RF-8 响应式**：成员卡 1→2→3 列带 md 过渡（§5.6）——已入规范 ✅
- **P0-1（本批新增）**：`DshTaskOut.team_json` 字符串→dict 转换必须用 `field_validator(mode="before")` 兜底损坏 JSON，否则 `model_validate` 直接 500——已写入 §2.2（实现后反向回填文件:行号）。

### 8.2 设计签核

- 结论：**通过（就绪）**。六节契约完整，PM 13 任务均有可执行落点；对 PM 计划的 2 处事实修正已记录（§7.2），Dev 以本规范为准。
- 实现后需反向回填：UI 组件规格实际类名/行号锚点（DEPARTMENTS.md §3「若前端已实现则反向回填」），由 Dev 或 QA 走查补锚点。
- 遗留（非阻断）：详情轮询粒度前端写死 3000ms 常量（与 `DSH_TEAM_POLL_SECONDS` 对齐，不新增配置接口）；若将来要前端可配，另起小批次。

**技能使用**: `cameltv-ui-conventions`（SKILL.md）→ UI 组件/四态/Red Flags 基线；`cameltv-agent-team`（DEPARTMENTS.md §3）→ Design 工件骨架；文档核查（read/glob/grep + 本机运行时证据 V1–V7）→ 事实核实（非测试证据）。
