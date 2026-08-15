---
title: "test-platform-v2/backend — FastAPI 后端"
owner: "backend-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["backend", "fastapi", "sqlalchemy", "python"]
related: ["../frontend/CLAUDE.md", "../../docs/adr/0001-use-python-fastapi-monostack.md", "../../docs/adr/0002-sqlite-with-postgresql-upgrade-path.md", "../../docs/adr/0004-jwt-bcrypt-rbac-auth.md"]
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
| trace.py | `/api/v1/trace` | trace_service | 质量追溯 |
| av_check.py | `/api/v1/av-check` | — | 音视频专项 |
| ui_test.py | `/api/v1/ui-test` | — | UI 自动化 |
| open_api.py | `/api/v1/open` | — | 开放 API |
| perf.py | `/api/v1/perf` | perf_service | 性能监控 |
| perf_ws.py | `/ws/perf` | — | WebSocket 实时指标采集 |
| environment.py | `/api/v1/environment` | — | 环境/变量管理 |
| dataset.py | `/api/v1/datasets` | — | 测试数据集 |
| integration.py | `/api/v1/integration` | — | 集成配置 |
| knowledge.py | `/api/v1/knowledge` | — | 知识中心 |
| agent.py | `/api/v1/agent` | — | Agent 工作台 |

## 核心配置

配置文件：[app/core/config.py](app/core/config.py) — 基于 Pydantic Settings，从 `.env` 加载。

关键环境变量：
```bash
DATABASE_URL=sqlite:///./cameltv.db    # 本地开发
AUTO_CREATE_TABLES=true                # 本地开发自动建表
SECRET_KEY=<random>                    # JWT 签名密钥
ELK_BASE_URL=                          # 本地开发留空，生产填 Kibana URL
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
- **AI 调用**：`ai_service.py` 调用 DeepSeek LLM，注意超时和重试
- **DSH 执行（Batch 172 / Batch 184 沙箱加固）**：`services/dsh/` 提供 DeepSeek Harness 执行抽象（`dsh_runner.run_dsh_task`）；
  A 用例生成 harness 模式经 `ai_service._call_ai_api_with_harness`（默认关、失败降级直连）；
  B Agent 工作台 `dsh_execution` 类型走 orchestrator 分发；C DSH 任务模块 `api/v1/dsh_tasks.py` + `models/dsh_task.py`。
  配置走 `DSH_*`（见 `.env.example`），运行时 node/python-sdk 由 `DSH_RUNTIME` 切换
- **DSH 沙箱约定（Batch 184 / C172-1/2，强制）**：
  - 每任务强制隔离工作区 `{根}/ws-{uuid}`（共享 DSH_WORKSPACE 只作隔离根，禁止多任务同目录）；
  - 全局并发闸门 `DSH_MAX_CONCURRENT`（默认 1，安全优先）与任务文本上限 `DSH_MAX_TASK_CHARS`（超限拒绝）；
  - python-sdk 凭据经 `os.environ` 传递必须持 `_python_sdk_env_lock`（env 突变+执行整体锁，禁止裸改）；
  - **生产启用前置**：`DSH_ENABLED=true` 仅在本批加固 + `tests/test_dsh_sandbox.py` 全绿 + 部署人工确认后允许；OS 级沙箱（seccomp/nsjail）为部署层后续（C184-1）
- **APScheduler**：定时任务在 `main.py` 生命周期中启动，开发时 `--reload` 会导致 scheduler 重复启动
- **CORS**：生产环境 CORS 配置在 Nginx，本地开发在 `main.py` 中配置 `allow_origins`

## 多项目隔离

所有请求必须携带 `X-Project-Id` header（int 类型项目 ID）。不传该 header 的请求将返回 `{"code":403,"msg":"缺少当前项目（请求头 X-Project-Id）"}`。前端 Axios 拦截器自动从 `authStore.currentProjectId` 注入该 header。外部调用者（Playwright、curl、CI）须显式添加该 header。
