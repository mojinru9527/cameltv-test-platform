---
title: "test-platform-v2/backend — FastAPI 后端"
owner: "backend-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["backend", "fastapi", "sqlalchemy", "python"]
related: ["../frontend/CLAUDE.md", "clean-code-standards.md", "../../docs/adr/0001-use-python-fastapi-monostack.md", "../../docs/adr/0002-sqlite-with-postgresql-upgrade-path.md", "../../docs/adr/0004-jwt-bcrypt-rbac-auth.md"]
---

# test-platform-v2/backend — FastAPI 后端

> FastAPI 0.110+ / SQLAlchemy 2.0 / SQLite (WAL) / JWT + BCrypt / APScheduler

## 目录结构

```
backend/
├── app/
│   ├── main.py              FastAPI 入口 + 生命周期
│   ├── api/v1/              API 路由层 (router.py 聚合)
│   ├── services/            业务服务层
│   ├── models/              SQLAlchemy ORM 模型
│   ├── schemas/             Pydantic 请求/响应 schema
│   ├── core/                核心组件 (config, db, deps, exceptions)
│   └── middleware/          中间件 (CORS, 审计日志)
├── alembic/                 数据库迁移
├── tests/                   pytest 测试
├── requirements.txt
└── Dockerfile
```

## 分层架构约定

```
Router (api/v1/)  →  Service (services/)  →  Model (models/)
       ↓                     ↓
   Deps (core/deps.py)   BaseService (core/base_service.py)
```

- **Router 层**：仅做参数校验、调用 Service、返回响应。**不放业务逻辑**
- **Service 层**：所有业务逻辑。继承 `BaseService`（提供 CRUD 混入）。Service 之间可相互调用
- **Model 层**：SQLAlchemy ORM 模型。使用 `declarative_base()`，表名用 snake_case 复数
- **Schema 层**：Pydantic v2 模型。请求/响应分离，使用 `model_config = ConfigDict(from_attributes=True)`
- **Deps 层**：FastAPI `Depends()` 可复用依赖（get_db、get_current_user、权限检查）

### 路由层禁 ORM（Batch 181 / FIX-173-P2-10，强制）

- `app/api/v1/` 下的路由文件**禁止** `from app.models import ...`、`select(`、`db.query(`（查询一律收敛到 services）。
- 豁免：BackgroundTasks 使用的独立 `SessionLocal()` 会话（test_plan/defect/report 既有模式，仅指开新会话，不含查询）。
- 路由层只保留：参数校验、权限、组装响应、审计、`db.commit()`。
- 守卫测试：`tests/test_route_layer_orm_ban.py` + `tests/test_route_inventory.py`（路径集基线，拆分不得漂移）。

### 删除语义唯一约定（Batch 181 / FIX-173-P2-08，强制）

- **软删除 = `is_deleted` 布尔**（True=已删）：可恢复/默认隐藏的删除一律用该列（test_case/domain/module、knowledge_source/chunk）。
- **硬删除 = 显式审计删除**（需求/缺陷/计划/UI 任务等）：保留审计留痕，不建软删列。
- **禁止第三套删除语义**：不得再用 `status=deprecated` 之类状态值兼作删除标志（status 列仅作展示/生命周期值，过滤一律走 `is_deleted`）。
- 过滤写法统一 `Model.is_deleted.is_(False)`，禁止 `== False`。

### 认领式任务队列统一约定（Batch 181 / FIX-173-P2-06，强制）

- 认领/回收/收尾原语统一走 `app/core/task_queue.py`（`QueueSpec` + `atomic_claim`/`atomic_claim_by_id`/`reap_stale`/`finish_task` + `QueueWorkerLoop`）。
- 新队列禁止自研 SELECT→改→commit 认领（TOCTOU）；锁列统一 `locked_by`/`locked_at`（或按 QueueSpec 配置），失联回收必须有（默认 30 分钟阈值）。

### 执行状态统一词表（Batch 182 / FIX-173-P1-06，强制）

- **DB 规范值唯一词表**：`pending | running | passed | failed | skipped | cancelled | blocked`（test_execution / test_plan_case.last_status / api_execution_task / api_execution_task_item / ui_test_run / ui_test_job / test_schedule_run）。
- 新代码**只写规范值**；历史/外部值经 `app/core/execution_status.canonical_exec_status(v)` 规范化后落库（open_api 回写等外部入口必须过该函数）。
- 统计/报告/趋势**响应键**（pass_/fail/skip/block/pending）是外部契约，读取侧用映射表（`_STATS_RESPONSE_KEY`/`_REPORT_STATS_KEY`）把 DB 规范值映射为响应键；禁止直接在响应层用 DB 值当键。
- 前端展示统一走 `frontend/src/utils/executionStatus.ts`（新旧双值中文标签）。

## API 设计约定

- **URL 风格**：`/api/v1/{resource}`，RESTful
- **响应 envelope**：
  ```json
  { "code": 0, "message": "success", "data": { ... } }
  ```
  - `code=0` 成功，非零为业务错误码
- **分页**：`/api/v1/{resource}?page=1&page_size=20`
  - 响应：`{ "items": [...], "total": 100, "page": 1, "page_size": 20 }`
- **认证**：`Authorization: Bearer <jwt_token>`
- **错误处理**：统一异常类在 `core/exceptions.py`，全局异常处理器在 `main.py`

## 关键模块速查

| API 文件 | 路由前缀 | Service | 职责 |
|----------|---------|---------|------|
| auth.py | `/api/v1/auth` | — | 登录/登出/刷新 token |
| token.py | `/api/v1/token` | — | Token 校验 |
| project.py | `/api/v1/projects` | project_service | 项目 CRUD + 成员 |
| system.py | `/api/v1/system` | — | 用户/角色/权限管理 |
| test_case.py | `/api/v1/test-cases` | test_case_service | 用例 CRUD + 域树 |
| test_plan.py | `/api/v1/test-plans` | test_plan_service | 计划 + 执行闭环 |
| requirement.py | `/api/v1/requirements` | requirement_service | 需求 + AI 生成 |
| defect.py | `/api/v1/defects` | defect_service | 缺陷 6 状态机 |
| report.py | `/api/v1/reports` | report_service | 报告中心 |
| dashboard.py | `/api/v1/dashboard` | — | 工作台看板 |
| schedule.py | `/api/v1/schedules` | schedule_service | 定时任务 |
| notify.py | `/api/v1/notify` | notify_service | Webhook 通知 |
| trace.py | `/api/v1/trace` | trace_service | 质量追溯（P2c 起前端并入报告中心 Tab，本 API 保留） |
| ui_test.py | `/api/v1/ui-test` | — | UI 自动化 |
| open_api.py | `/api/v1/open` | — | 开放 API |
| environment.py | `/api/v1/environment` | — | 环境/变量管理 |
| dataset.py | `/api/v1/datasets` | — | 测试数据集 |
| integration.py | `/api/v1/integration` | — | 集成配置 |
| knowledge.py | `/api/v1/knowledge` | — | 知识中心 |
| agent.py | `/api/v1/agent` | — | Agent 执行记录 API（P1b 起前端入口收敛进 DSH 任务，本 API 保留供知识/排障链路与调试调用） |
| ai_config.py | `/api/v1/ai-config` | ai_config_service | AI 模型配置中心（项目级提供方池） |

## 核心配置

配置文件：[app/core/config.py](app/core/config.py) — 基于 Pydantic Settings，从 `.env` 加载。

关键环境变量：
```bash
DATABASE_URL=sqlite:///./cameltv.db    # 本地开发
AUTO_CREATE_TABLES=true                # 本地开发自动建表
SECRET_KEY=<random>                    # JWT 签名密钥
ELK_BASE_URL=                          # 本地开发留空，生产填 Kibana URL
DISABLED_MENUS=menu:notify,menu:integration  # 模块可见性开关（P1a）：逗号分隔菜单 code，
                                             # 软下线侧边栏/访客目录/命令面板入口；
                                             # 页面路由保留可直达，置空即恢复全部入口
```

## 数据库迁移

```bash
# 本地开发：AUTO_CREATE_TABLES=true 自动建表，无需手动迁移
# 生产/共享环境：
alembic upgrade head                   # 执行迁移
alembic revision --autogenerate -m "描述"  # 模型变更后生成迁移文件
```

## 测试

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v --tb=short
```

测试文件位于 `backend/tests/`，使用 pytest + httpx (AsyncClient) 测试 API。

## 常见陷阱

- **不要在 Router 中写业务逻辑**——Router 只做参数校验和调用 Service
- **大文件上传**：需求文档解析（Word/Excel）走 `file_parser_service.py`，注意内存控制
- **AI 调用（Batch A 起按项目解析）**：所有 AI 消费点统一经 `ai_config_service.resolve(db, project_id)` 获取
  运行时配置（项目级提供方池），禁止再直接读 `settings.ai_api_key / ai_api_base_url / ai_model`；
  未配置提供方的项目抛 `AIProviderUnconfiguredError`（AI 功能按项目禁用）。见下方「AI 模型配置中心」。
- **AI 模型配置中心（Batch A）**：
  - 数据：`ai_provider` 表（项目级多提供方池）；Key 用 Fernet 加密（`SECRET_KEY` 派生），列表只回掩码；
  - 解析：`ai_config_service.resolve(db, project_id) -> EffectiveAiConfig`（provider_id/provider_name/
    provider_type/api_base_url/api_key/model）；消费点入口签名带 `db + project_id` 透传；
  - API：`api/v1/ai_config.py`（`/api/v1/ai-config/*`，权限 `ai_config:view/manage`）+ `/resolve` 供前端状态条；
  - DSH 凭据：`dsh_runner.run_dsh_task(provider=...)` 注入 `DEEPSEEK_API_KEY/DEEPSEEK_BASE_URL/DSH_MODEL`，
    provider 为空回退 settings（仅测试兼容）；任务提交时快照 `provider_id` 到 params，worker 执行时重建；
  - 退役 env：`AI_API_KEY/AI_API_BASE_URL/AI_MODEL/DSH_API_KEY/DSH_BASE_URL/DSH_MODEL/DSH_MODEL_POOL`
    （见 `.env.example` 退役标注）；`DSH_ENABLED/DSH_RUNTIME` 等部署基础设施保留；
  - 迁移幂等：新增迁移必须带「表/列存在检查」守卫（stamp 回退重跑 upgrade 自愈，对齐 b191 惯例）。
  - 轮换注意：轮换 `SECRET_KEY` 会使存量 Fernet 加密 API Key 全部失效（解密失败已转业务错误
    `AIProviderUnconfiguredError`，提示重新录入）；轮换后须各项目在「AI 配置」页重新录入 API Key。
- **DSH 执行（Batch 172 / Batch 184 沙箱加固）**：`services/dsh/` 提供 DeepSeek Harness 执行抽象（`dsh_runner.run_dsh_task`）；
  A 用例生成 harness 模式经 `ai_service._call_ai_api_with_harness`（默认关、失败降级直连）；
  B Agent 工作台 `dsh_execution` 类型走 orchestrator 分发；C DSH 任务模块 `api/v1/dsh_tasks.py` + `models/dsh_task.py`。
  配置走 `DSH_*`（见 `.env.example`），运行时 node/python-sdk 由 `DSH_RUNTIME` 切换
- **DSH 沙箱约定（Batch 184 / C172-1/2，强制）**：
  - 每任务强制隔离工作区 `{根}/ws-{uuid}`（共享 DSH_WORKSPACE 只作隔离根，禁止多任务同目录）；
  - 全局并发闸门 `DSH_MAX_CONCURRENT`（默认 1，安全优先）与任务文本上限 `DSH_MAX_TASK_CHARS`（超限拒绝）；
  - python-sdk 凭据经 `os.environ` 传递必须持 `_python_sdk_env_lock`（env 突变+执行整体锁，禁止裸改）；
  - **生产启用前置**：`DSH_ENABLED=true` 仅在本批加固 + `tests/test_dsh_sandbox.py` 全绿 + 部署人工确认后允许；OS 级沙箱（seccomp/nsjail）为部署层后续（C184-1）
- **DSH 团队模式（Batch 191，AgentTeams）**：
  - 资产：`services/dsh/agent_team_persona.py`（船长提示词纯函数，full 五成员/light 两成员）、
    `services/dsh/team.cordis.yml`（= minimal + subagent/subagent-spawn-in-process/agent-teams，
    python-sdk 用；**C191-1 修复：agent-teams 依赖 subagents 服务，minimal 不含提供者**）、
    `services/dsh/agent-team/`（profile 模板 + 安装 README，**实际安装位 `$DSH_HOME/profiles/agent-team`，不入库**）；
  - 路由：`run_dsh_task(mode="team")` → node `--profile agent-team` / python-sdk `team.cordis.yml`；
    `DSH_TEAM_HARNESS_PATH` 语义 = **DSH_HOME 覆盖**（非 bin.js 路径）；
  - 心跳（R-1 冒烟修复）：团队执行期间 `_team_heartbeat` 线程按 `DSH_TEAM_HEARTBEAT_SECONDS`
    （默认 60s）续期 `locked_at`，防 `reap_stale`（300s）误回收 1800s 级长任务；
    进程崩溃 → 心跳停 → 5 分钟后照常回收（失联语义不回归）；
  - 船长纪律（真实业务任务修复）：`agent_team_persona.py` 步骤明确「认领后必须
    `agent_teams_send_message` 唤醒成员、必须轮询到全部任务 completed 才可结束」；
    agent-team profile 的 patch 层**禁用 generic subagent 派活工具**
    （tool-subagent/subagent-fork/control/list-agents，模板已同步）——防止模型混用
    subagent 工具绕过团队协议（成员 idle、任务 in_progress 挂起）；
  - 线程铁律（R-3）：`dsh_task_service._team_poller` 每次写库用**独立短 `SessionLocal`**，
    禁止复用 `execute_task` 的认领 session；`team_json` 全量幂等覆盖，超长截断加 `_truncated`；
    快照扫描**递归 glob（`**/team.json`，覆盖船长删除团队后的 `archive/` 归档路径）且每轮
    按 mtime 最新重选**（船长同任务重建团队时跟随最新，不永久锁定首个命中；并发串扰由
    `DSH_MAX_CONCURRENT` 默认 1 兜底，调高并发需按任务 workspace 隔离扫描）；
  - 状态词表：`dsh_task.status` 仍用队列词表（pending/running/success/failed/cancelled）；
    团队内部任务状态（claimed/in_progress 等）是插件 `team.json` 字段，前端单独映射；
  - 冒烟（C191-1 已关闭）：node 需先安装 agent-team profile
    （`dsh plugin --profile agent-team add @nanmicoder/dsh-agent-teams`），**安装后必须校验
    `package.json` 的 `dsh.profile.bundles` 含 `@deepseek-ai/dsh-headless`**（CLI 方式 A 生成的
    bundles 缺 headless → 任务挂起，见 agent-team/README.md）；python-sdk 走 `team.cordis.yml`
    实测通过（SDK node carrier 45s 团队组合 completed），生产 Linux exe carrier 需把
    agent-teams 打进闭包 → C191-3，**不静默 fallback 到 single**
- **DSH 测试 Agent 框架（Batch 202，tester 视角）**：
  - `services/dsh/tester_team_persona.py`：测试船长 persona（analyst/case-designer/api-tester/
    ui-tester/reviewer；用例必须遵守 test-case-design skill 自检清单、执行必须走平台 Runner、
    reviewer 独立审查）；`params.team_kind` 分派——`tester` 用测试 persona，缺省 `dev` 沿用开发
    persona（不回归）；`params.model` 透传 runner（single/team 均支持，模型池按任务指定）；
  - `api/v1/open_knowledge.py`：Agent 查询面（知识源/检索/模块拓扑/需求/用例读+写/计划/执行
    记录/UI 任务），API Token 鉴权 + project 隔离——knowledge-mcp 只经此通道访问，不直连库；
  - 模型池（阶段 3）：`DSH_MODEL_POOL`（逗号分隔）+ `dsh_model_allowed` 准入（`/dsh-tasks`
    提交时校验）+ `/dsh-tasks/model-pool` 端点（前端下拉渲染）；空池 = 不限；
  - 使用入口：`docs/DSH测试Agent-测试工程师使用手册.md`；架构：`docs/DSH测试Agent框架设计.md`
- **AI 配置模型发现（Batch fix）**：`POST /ai-config/providers/discover-models` 调用提供方
  `GET /models`（OpenAI 兼容）返回模型清单，前端「获取模型列表」按钮免手填；401/无 /models
  转可读错误，仍可手动填写。
- **DSH 任务图片附件（Batch fix）**：`POST /dsh-tasks/upload-image`（PNG/JPEG/WebP/GIF，魔数
  校验，≤10MB）→ file_id 经 `params.image_files` 提交（32 位 hex 校验）→ 执行时
  `dsh_attachment_service.resolve_images` 复制到工作区 `attachments/`，runner 在任务文本
  末尾追加 read_image 提示；视觉模型（如官方 deepseek-v4-flash-vision-exp）可查看附件。
- **DSH node 模式多提供方路由（Batch fix，生产事故）**：`@deepseek-ai/dsh-base` 固定
  `agent-default-model=deepseek-v4-flash`，node 模式**不读 `DSH_MODEL` env** → 任务所选 AI
  提供方模型失效（生产实测 `HTTP_422 Model Not Exist`）。Dockerfile 构建期向
  `headless`/`agent-team` 两个 profile 的 `cordis.patch.yml` 注入 **llm-pi-ai `platform` 路由**
  （api=openai-completions，apiKeyEnv=DEEPSEEK_API_KEY，baseURL 读 DEEPSEEK_BASE_URL env，
  models 读 DSH_MODEL env）→ 任意 OpenAI 兼容端点按项目接入不同模型（DeepSeek 官方/SCNET/
  Kimi/GLM…）；runner 每任务注入 provider 密钥/端点/模型，生产实测路由生效。
- **存储保留期清理（`services/storage_retention.py`）**：每日定时（默认 02:30，
  `STORAGE_RETENTION_ENABLED` 开关）按 mtime 清理超保留期（默认 7 天）的
  `ui-runs/<纯数字id>/`、`dsh-sessions/workspaces/ws-*`、会话 `*.jsonl`；
  `plan-sync/` 与蓝湖证据默认不清理；根目录 `STORAGE_RETENTION_ROOT`（空 = dsh-sessions 父目录）。
- **APScheduler**：定时任务在 `main.py` 生命周期中启动，开发时 `--reload` 会导致 scheduler 重复启动
- **CORS**：生产环境 CORS 配置在 Nginx，本地开发在 `main.py` 中配置 `allow_origins`

## 多项目隔离

所有请求必须携带 `X-Project-Id` header（int 类型项目 ID）。不传该 header 的请求将返回 `{"code":403,"msg":"缺少当前项目（请求头 X-Project-Id）"}`。前端 Axios 拦截器自动从 `authStore.currentProjectId` 注入该 header。外部调用者（Playwright、curl、CI）须显式添加该 header。
