# Agent Team Automation And Wiki Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把接口自动化、UI 自动化、RAG/LLM-WIKI 从“可用雏形”推进到可支撑日常回归、CI、知识复用和 Agent Team 协作实施的生产化能力。

**Architecture:** 接口自动化优先从请求线程中移出，统一项目隔离、执行治理、快照和生产保护；UI 自动化升级为独立 Playwright runner，按 `run_id` 隔离进程、状态和产物；RAG/LLM-WIKI 基于蓝湖链接进入 Raw Source、知识切片、向量检索、Wiki 编译、差异对比和待审资产闭环。所有写入正式测试资产的路径必须经过项目权限、配置开关、审计日志和人工审核。

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite/PostgreSQL, httpx, Playwright, subprocess/Popen, BackgroundTasks to worker queue migration, React, TypeScript, Ant Design/shadcn-style components, fastembed/vector store, Lanhu MCP.

---

## 0. Scope And Current State

本计划基于 2026-07-13 仓库现状复核，而不是只基于历史问题记录。

已确认的当前状态：

- 接口自动化已经有后端 `httpx` 真实执行、请求/响应快照、生产写接口保护雏形、`BackgroundTasks` 异步触发雏形。
- 接口自动化仍有多个入口直接接收 query `project_id`，需要统一收口到 `current.project_id`。
- 接口批量任务仍依赖 FastAPI `BackgroundTasks`，不是可恢复的持久化 worker；取消、超时、重试、并发限制仍不完整。
- UI 自动化已经能创建 `UiTestRun` 后由后台任务调用 Playwright，并且已有 `storage/ui-runs/{run_id}` 产物目录和下载接口。
- UI 执行器仍使用 `subprocess.run` 阻塞后台线程，`_semaphore` 只定义未使用；取消接口只改数据库状态，没有终止子进程。
- RAG 已有 `KnowledgeVector`、`/knowledge/search`、`/knowledge/reembed`、`hybrid_search` 和向量回填管线，但默认 `rag_enabled=False`，需要按环境完成开关、模型健康检查和验收。
- LLM-WIKI 已有 `wiki.py` 模型、`/wiki/*` API、`LanhuProvider`、Wiki/WikiDiff 前端入口；后续重点是蓝湖链路验收、差异质量、外部连接器、权限与 Agent 记录治理。
- Agent 记录查询当前使用 `agent:list`，历史建议中的 `agent:view / agent:run` 拆分应按 seed 与前端权限统一推进。

蓝湖实施输入：

```text
url: https://lanhuapp.com/web/#/item/project/product?tid=6324825d-1614-4d73-bc4c-f05cdf0734c1&pid=cc8cfbd5-16d2-481f-828e-7eb424a91694&versionId=26af2885-b229-4971-881c-c9bda43492fd&docId=e6b5ce1e-0d25-4e22-a9e9-450283918b3b&docType=axure&image_id=e6b5ce1e-0d25-4e22-a9e9-450283918b3b&pageId=2b4c4235b036420787d3e856b5d133d7&corpId=null
tid: 6324825d-1614-4d73-bc4c-f05cdf0734c1
pid: cc8cfbd5-16d2-481f-828e-7eb424a91694
versionId: 26af2885-b229-4971-881c-c9bda43492fd
docId: e6b5ce1e-0d25-4e22-a9e9-450283918b3b
pageId: 2b4c4235b036420787d3e856b5d133d7
docType: axure
```

蓝湖正文不能通过公开页面稳定读取，必须由 `lanhu-mcp` 在具备合法 Cookie 或账号权限的运行环境中抽取。验收时使用上述 `docId/versionId/pageId` 校验 Raw Source 的 `immutable_version`。

---

## 1. File Structure

### Backend: API Automation

- Modify: `test-platform-v2/backend/app/api/v1/apitest.py`
  - 移除 query `project_id` 信任，统一使用 `current.project_id`。
  - `POST /apitest/tasks` 只创建任务并入队，不直接绑定请求生命周期执行。
  - 增加失败重跑、任务取消和详情项接口的项目隔离校验。
- Modify: `test-platform-v2/backend/app/services/api_execution_service.py`
  - 保持请求快照、响应快照、生产保护和断言结果输出稳定。
  - 增加超时、错误类型、重试语义和可复制 curl 字段。
- Create: `test-platform-v2/backend/app/services/api_task_worker.py`
  - 持久化任务 worker，按项目和全局并发限制拉取 pending 任务。
  - 支持取消、失败重试、运行中任务恢复、执行锁。
- Modify: `test-platform-v2/backend/app/models/api_asset.py`
  - 给 `ApiExecutionTask` 增加 `cancel_requested`、`retry_count`、`max_retries`、`locked_at`、`locked_by`、`timeout_seconds`。
  - 给 `ApiExecutionTaskItem` 增加 `error_type`、`retry_count`、`started_at`、`finished_at`。
- Modify: `test-platform-v2/backend/app/schemas/api_asset.py`
  - 补齐任务创建、重试、详情、快照输出字段。
- Create: `test-platform-v2/backend/alembic/versions/20260713_automation_task_worker.py`
  - 增量迁移上述任务字段。
- Test: `test-platform-v2/backend/tests/test_apitest_project_isolation.py`
- Test: `test-platform-v2/backend/tests/test_api_task_worker.py`
- Test: `test-platform-v2/backend/tests/test_api_execution_snapshots.py`

### Backend: UI Automation

- Modify: `test-platform-v2/backend/app/api/v1/ui_test.py`
  - 触发接口返回 `run_id` 后由 runner 队列执行。
  - 取消接口改为设置取消标记并终止子进程。
  - 所有 run/artifact 读取必须校验 job 所属 `current.project_id`。
- Modify: `test-platform-v2/backend/app/services/ui_test_service.py`
  - `trigger_job` 只负责创建 run、更新 job 状态、入队。
  - 增加脚本资产与 job 的绑定校验。
- Modify: `test-platform-v2/backend/app/services/playwright_executor.py`
  - 从 `subprocess.run` 改为 `subprocess.Popen`。
  - 使用真实并发控制，保存 `process_id`，支持取消和超时 kill。
  - 只从 `storage/ui-runs/{run_id}` 收集产物，不扫描历史目录。
- Modify: `test-platform-v2/backend/app/models/ui_test.py`
  - 确认或补齐 `UiTestScript`、`process_id`、`cancel_requested`、`artifact_dir`、`report_json_path`、`html_report_path`、`stdout`、`stderr`。
- Create: `test-platform-v2/backend/app/services/ui_runner_queue.py`
  - UI runner 队列与并发调度。
- Create: `test-platform-v2/backend/alembic/versions/20260713_ui_runner_hardening.py`
- Test: `test-platform-v2/backend/tests/test_ui_runner_queue.py`
- Test: `test-platform-v2/backend/tests/test_playwright_executor.py`
- Test: `test-platform-v2/backend/tests/test_ui_artifact_isolation.py`

### Backend: RAG / LLM-WIKI

- Modify: `test-platform-v2/backend/app/core/config.py`
  - 保持 `rag_enabled`、`wiki_enabled`、`wiki_diff_enabled` 默认关闭。
  - 增加 `external_llm_wiki_enabled`、`wiki_lint_enabled`、`embedding_health_required`。
- Modify: `test-platform-v2/backend/app/api/v1/knowledge.py`
  - 增加搜索健康检查与 embedding 覆盖率输出。
- Modify: `test-platform-v2/backend/app/api/v1/wiki.py`
  - 补充蓝湖导入验收字段、diff 取消/重试、外部连接器接口。
- Modify: `test-platform-v2/backend/app/services/external/lanhu_provider.py`
  - 确保 `docId/versionId/pageId` 标准化、错误状态稳定、图片型原型提示补充说明。
- Modify: `test-platform-v2/backend/app/services/wiki/import_service.py`
  - 蓝湖 Raw Source 同步进入 `knowledge_source/chunk/vector/wiki_page`。
- Modify: `test-platform-v2/backend/app/services/wiki/compare_service.py`
  - 差异项覆盖需求范围、客户端、业务规则、字段、接口、异常、权限、数据依赖、验收标准、测试覆盖、版本、证据。
- Create: `test-platform-v2/backend/app/services/wiki/external_llm_wiki.py`
  - 只读连接外部 LLM Wiki Desktop/API。
- Create: `test-platform-v2/backend/app/services/wiki/lint_service.py`
  - Wiki 健康体检：孤立页面、无来源结论、过期页面、冲突规则、测试覆盖缺口。
- Modify: `test-platform-v2/backend/app/api/v1/agent.py`
  - 权限拆分为 `agent:view` 读、`agent:run` 写。
- Modify: `test-platform-v2/backend/app/seed.py`
  - 增加 `agent:view`，保留兼容迁移策略，调整角色默认权限。
- Test: `test-platform-v2/backend/tests/test_lanhu_provider.py`
- Test: `test-platform-v2/backend/tests/test_knowledge_search_rag.py`
- Test: `test-platform-v2/backend/tests/test_wiki_import_lanhu_contract.py`
- Test: `test-platform-v2/backend/tests/test_wiki_diff_quality.py`
- Test: `test-platform-v2/backend/tests/test_agent_permissions.py`

### Frontend

- Modify: `test-platform-v2/frontend/src/api/apitest.ts`
  - 移除业务调用里的 `project_id` query 拼接，改由全局 `X-Project-Id`。
  - 增加 retry failed、cancel、task item detail 类型。
- Modify: `test-platform-v2/frontend/src/pages/apitest/components/TaskTab.tsx`
  - 展示 pending/running/cancelled/retrying 状态。
  - 增加失败重跑、取消、复制 curl、请求/响应/断言快照。
- Modify: `test-platform-v2/frontend/src/pages/apitest/components/AssetTab.tsx`
  - 服务和接口列表不再显式传 query `project_id`。
- Modify: `test-platform-v2/frontend/src/api/uitest.ts`
  - 增加 runner 健康检查、artifact 列表、取消状态。
- Modify: `test-platform-v2/frontend/src/pages/uitest/index.tsx`
  - 运行详情轮询、取消按钮、产物下载、脚本资产选择、环境注入展示。
- Modify: `test-platform-v2/frontend/src/api/knowledge.ts`
  - 搜索健康、embedding 覆盖率、reembed 结果展示。
- Modify: `test-platform-v2/frontend/src/api/wiki.ts`
  - 蓝湖导入、diff、外部连接、lint 入口补齐。
- Modify: `test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx`
  - 展示蓝湖 `docId/versionId/pageId`、Raw Source、Wiki 页面、审核状态。
- Modify: `test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx`
  - 增加差异维度、严重级别、证据、生成待审资产。
- Create: `test-platform-v2/frontend/src/pages/knowledge/components/WikiLintPanel.tsx`
- Test: `test-platform-v2/frontend/src/pages/knowledge/components/__tests__/WikiTab.test.tsx`
- Test: `test-platform-v2/frontend/src/pages/knowledge/components/__tests__/WikiDiffTab.test.tsx`
- Test: `test-platform-v2/frontend/src/pages/uitest/__tests__/UiRunDetail.test.tsx`

---

## 2. Phase P0: API Automation Production Hardening

### Task 1: Project Isolation For API Test Routes

**Files:**
- Modify: `test-platform-v2/backend/app/api/v1/apitest.py`
- Modify: `test-platform-v2/frontend/src/api/apitest.ts`
- Modify: `test-platform-v2/frontend/src/pages/apitest/components/AssetTab.tsx`
- Modify: `test-platform-v2/frontend/src/pages/apitest/components/TaskTab.tsx`
- Test: `test-platform-v2/backend/tests/test_apitest_project_isolation.py`

- [ ] **Step 1: Write failing backend tests**

Create tests that prove query `project_id` cannot override `X-Project-Id`.

```python
def test_services_ignore_query_project_id(client, auth_headers, db):
    headers = {**auth_headers, "X-Project-Id": "1"}
    resp = client.get("/api/v1/apitest/services?project_id=999", headers=headers)
    assert resp.status_code == 200
    assert all(item["project_id"] == 1 for item in resp.json()["data"])


def test_tasks_detail_enforces_current_project(client, auth_headers, api_task_factory):
    task = api_task_factory(project_id=999)
    headers = {**auth_headers, "X-Project-Id": "1"}
    resp = client.get(f"/api/v1/apitest/tasks/{task.id}", headers=headers)
    assert resp.status_code in (403, 404)
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_apitest_project_isolation.py -q
```

Expected: at least one test fails because routes still accept or read query `project_id`.

- [ ] **Step 3: Replace query project_id with current.project_id**

Apply this rule to every route in `apitest.py`: derive `pid = current.project_id or 0`, reject missing project, and filter by `pid`.

```python
def _current_project_id(current: CurrentUser) -> int:
    if not current.project_id:
        raise HTTPException(400, "缺少当前项目上下文")
    return current.project_id
```

Example replacement:

```python
@router.get("/services", response_model=R[list[ApiServiceOut]], summary="服务列表")
def list_services(
    current: CurrentUser = Depends(require_permission("apitest:view")),
    db: Session = Depends(get_db),
):
    pid = _current_project_id(current)
    rows = db.query(ApiService).filter_by(project_id=pid).order_by(ApiService.name).all()
    return R.ok([ApiServiceOut.model_validate(r) for r in rows])
```

Endpoints to update in this pass:

```text
GET  /apitest/services
POST /apitest/services
GET  /apitest/endpoints
POST /apitest/endpoints
POST /apitest/import/preview
POST /apitest/import/confirm
POST /apitest/cases/generate
POST /apitest/cases/batch-generate
POST /apitest/tasks
GET  /apitest/tasks
GET  /apitest/tasks/{task_id}
POST /apitest/tasks/{task_id}/cancel
```

- [ ] **Step 4: Remove frontend query project_id**

In `frontend/src/api/apitest.ts`, remove `project_id` from request params. The platform already carries project scope through `X-Project-Id`.

```ts
export async function fetchApiServices(): Promise<ApiService[]> {
  return api.get('/apitest/services')
}

export async function fetchApiEndpoints(params: ApiEndpointQuery): Promise<PageResult<ApiEndpoint>> {
  const { project_id: _ignored, ...rest } = params
  return api.get('/apitest/endpoints', { params: rest })
}
```

- [ ] **Step 5: Run tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_apitest_project_isolation.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add test-platform-v2/backend/app/api/v1/apitest.py test-platform-v2/frontend/src/api/apitest.ts test-platform-v2/frontend/src/pages/apitest/components/AssetTab.tsx test-platform-v2/frontend/src/pages/apitest/components/TaskTab.tsx test-platform-v2/backend/tests/test_apitest_project_isolation.py
git commit -m "fix: enforce project isolation in api test routes"
```

### Task 2: Persistent API Task Worker

**Files:**
- Create: `test-platform-v2/backend/app/services/api_task_worker.py`
- Modify: `test-platform-v2/backend/app/api/v1/apitest.py`
- Modify: `test-platform-v2/backend/app/models/api_asset.py`
- Modify: `test-platform-v2/backend/app/schemas/api_asset.py`
- Create: `test-platform-v2/backend/alembic/versions/20260713_automation_task_worker.py`
- Test: `test-platform-v2/backend/tests/test_api_task_worker.py`

- [ ] **Step 1: Write failing worker tests**

```python
def test_worker_claims_only_pending_tasks(db, api_task_factory):
    pending = api_task_factory(project_id=1, status="pending")
    api_task_factory(project_id=1, status="running")
    from app.services.api_task_worker import claim_next_task
    claimed = claim_next_task(db, worker_id="test-worker", project_id=1)
    assert claimed.id == pending.id
    assert claimed.status == "running"
    assert claimed.locked_by == "test-worker"


def test_worker_marks_remaining_items_skipped_after_cancel(db, api_task_with_items):
    task = api_task_with_items(project_id=1, total=3)
    task.cancel_requested = True
    from app.services.api_task_worker import execute_task
    execute_task(task.id, project_id=1, worker_id="test-worker")
    db.refresh(task)
    assert task.status == "cancelled"
    assert task.skipped == 3
```

- [ ] **Step 2: Add migration fields**

Migration must add these columns:

```python
op.add_column("api_execution_task", sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()))
op.add_column("api_execution_task", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
op.add_column("api_execution_task", sa.Column("max_retries", sa.Integer(), nullable=False, server_default="1"))
op.add_column("api_execution_task", sa.Column("locked_at", sa.DateTime(), nullable=True))
op.add_column("api_execution_task", sa.Column("locked_by", sa.String(), nullable=False, server_default=""))
op.add_column("api_execution_task", sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="1800"))
op.add_column("api_execution_task_item", sa.Column("error_type", sa.String(), nullable=False, server_default=""))
op.add_column("api_execution_task_item", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
op.add_column("api_execution_task_item", sa.Column("started_at", sa.DateTime(), nullable=True))
op.add_column("api_execution_task_item", sa.Column("finished_at", sa.DateTime(), nullable=True))
```

- [ ] **Step 3: Implement worker claim logic**

```python
def claim_next_task(db: Session, *, worker_id: str, project_id: int | None = None) -> ApiExecutionTask | None:
    q = db.query(ApiExecutionTask).filter(ApiExecutionTask.status == "pending")
    if project_id is not None:
        q = q.filter(ApiExecutionTask.project_id == project_id)
    task = q.order_by(ApiExecutionTask.created_at.asc()).with_for_update(skip_locked=True).first()
    if not task:
        return None
    task.status = "running"
    task.locked_by = worker_id
    task.locked_at = datetime.now(timezone.utc)
    task.started_at = task.started_at or datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return task
```

For SQLite test mode, if `with_for_update(skip_locked=True)` is unsupported, branch by dialect and use deterministic single-process claim.

- [ ] **Step 4: Change create task to enqueue only**

In `POST /apitest/tasks`, remove direct `_execute_task_async` invocation. Set `task.status="pending"` and call `api_task_worker.kick()` if the in-process worker is enabled.

```python
task = ApiExecutionTask(..., status="pending")
db.add(task)
db.commit()
api_task_worker.ensure_processor_running()
return R.ok(ApiTaskOut.model_validate(task))
```

- [ ] **Step 5: Implement cancellation**

`POST /apitest/tasks/{task_id}/cancel` must set `cancel_requested=True`. Worker checks before every item and after every request.

```python
if task.cancel_requested:
    mark_unstarted_items_skipped(db, task.id, "任务已取消")
    finish_task(db, task, status="cancelled")
    return
```

- [ ] **Step 6: Implement retry failed**

Add endpoint:

```http
POST /api/v1/apitest/tasks/{task_id}/retry-failed
```

Behavior:

```text
1. Verify task.project_id == current.project_id.
2. Create a new ApiExecutionTask with trigger_type="retry_failed".
3. Copy only failed item case_id values into new pending items.
4. Return new task id immediately.
```

- [ ] **Step 7: Run tests**

```bash
cd test-platform-v2/backend
pytest tests/test_api_task_worker.py tests/test_api_execution_snapshots.py -q
```

Expected: worker tests pass and request/response snapshots remain stable.

- [ ] **Step 8: Commit**

```bash
git add test-platform-v2/backend/app/services/api_task_worker.py test-platform-v2/backend/app/api/v1/apitest.py test-platform-v2/backend/app/models/api_asset.py test-platform-v2/backend/app/schemas/api_asset.py test-platform-v2/backend/alembic/versions/20260713_automation_task_worker.py test-platform-v2/backend/tests/test_api_task_worker.py
git commit -m "feat: run api execution tasks through persistent worker"
```

### Task 3: API Execution Evidence And Production Guardrails

**Files:**
- Modify: `test-platform-v2/backend/app/services/api_execution_service.py`
- Modify: `test-platform-v2/backend/app/api/v1/apitest.py`
- Modify: `test-platform-v2/frontend/src/pages/apitest/components/TaskTab.tsx`
- Test: `test-platform-v2/backend/tests/test_api_execution_snapshots.py`

- [ ] **Step 1: Ensure request snapshot contains reproducible fields**

Required JSON shape:

```json
{
  "method": "POST",
  "original_url": "/ee/test/matchpush",
  "resolved_url": "https://example.test/ee/test/matchpush",
  "headers": {"authorization": "***"},
  "body": "{\"matchId\":\"1\"}",
  "environment_id": 1,
  "dataset_row_index": null,
  "curl": "curl -X POST 'https://example.test/ee/test/matchpush' ..."
}
```

- [ ] **Step 2: Ensure response snapshot contains truncation metadata**

Required JSON shape:

```json
{
  "status_code": 200,
  "headers": {"content-type": "application/json"},
  "body_preview": "{\"code\":0}",
  "body_size_bytes": 1048576,
  "truncated": true,
  "content_type": "application/json"
}
```

- [ ] **Step 3: Enforce production write protection**

Rules:

```text
GET/HEAD/OPTIONS in prod: allowed with apitest:execute.
POST/PUT/PATCH/DELETE in prod: require apitest:execute_prod and confirm_prod=true.
Batch tasks in prod: require all write cases to pass the same guard.
```

- [ ] **Step 4: Run tests**

```bash
cd test-platform-v2/backend
pytest tests/test_api_execution_snapshots.py -q
```

Expected: snapshot and production guard tests pass.

- [ ] **Step 5: Commit**

```bash
git add test-platform-v2/backend/app/services/api_execution_service.py test-platform-v2/backend/app/api/v1/apitest.py test-platform-v2/frontend/src/pages/apitest/components/TaskTab.tsx test-platform-v2/backend/tests/test_api_execution_snapshots.py
git commit -m "feat: harden api execution snapshots and production guards"
```

---

## 3. Phase P1: UI Automation Runner Hardening

### Task 4: Replace Blocking Playwright Run With Managed Process

**Files:**
- Modify: `test-platform-v2/backend/app/services/playwright_executor.py`
- Modify: `test-platform-v2/backend/app/services/ui_test_service.py`
- Create: `test-platform-v2/backend/app/services/ui_runner_queue.py`
- Modify: `test-platform-v2/backend/app/models/ui_test.py`
- Create: `test-platform-v2/backend/alembic/versions/20260713_ui_runner_hardening.py`
- Test: `test-platform-v2/backend/tests/test_playwright_executor.py`

- [ ] **Step 1: Write failing process tests**

```python
def test_playwright_executor_records_pid_and_output_dir(db, ui_run_factory, ui_job_factory, monkeypatch):
    run = ui_run_factory(status="pending")
    job = ui_job_factory(id=run.job_id, test_spec="specs/example.spec.ts", browser="chromium")
    from app.services.playwright_executor import run_playwright_test
    result = run_playwright_test(db, run.id, job.id, project_id=job.project_id)
    db.refresh(run)
    assert run.artifact_dir.endswith(f"/ui-runs/{run.id}")
    assert run.report_json_path.endswith("report.json")


def test_cancel_kills_running_process(db, ui_run_factory, monkeypatch):
    run = ui_run_factory(status="running", process_id=12345, cancel_requested=True)
    from app.services.playwright_executor import cancel_process_if_needed
    killed = cancel_process_if_needed(db, run)
    assert killed is True
```

- [ ] **Step 2: Add model and migration fields**

Fields:

```text
UiTestRun.process_id
UiTestRun.cancel_requested
UiTestRun.artifact_dir
UiTestRun.report_json_path
UiTestRun.html_report_path
UiTestRun.stdout
UiTestRun.stderr
UiTestRun.error_message
```

- [ ] **Step 3: Use Popen**

Replace `subprocess.run` with:

```python
proc = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    cwd=str(PLAYWRIGHT_DIR),
    env=env,
)
run.process_id = proc.pid
db.commit()
stdout_text, stderr_text = proc.communicate(timeout=timeout_seconds)
```

On timeout:

```python
proc.kill()
stdout_text, stderr_text = proc.communicate()
return _fail_run(db, run, f"测试执行超时 ({timeout_seconds}s)", job)
```

- [ ] **Step 4: Check cancellation during execution**

Polling loop:

```python
while proc.poll() is None:
    db.refresh(run)
    if run.cancel_requested or run.status == "cancelled":
        proc.kill()
        run.status = "cancelled"
        run.finished_at = datetime.now(timezone.utc)
        run.error_message = "用户手动取消"
        db.commit()
        return {"status": "cancelled"}
    time.sleep(1)
```

- [ ] **Step 5: Enforce artifact isolation**

Only collect files from `artifact_dir`. Remove scanning from `PLAYWRIGHT_DIR` and shared `test-results` unless files are copied into the run directory by Playwright config for this run.

```python
screenshots = _collect_artifacts(artifact_dir, "*.png")
videos = _collect_artifacts(artifact_dir, "*.webm")
traces = _collect_artifacts(artifact_dir, "*.zip")
```

- [ ] **Step 6: Run tests**

```bash
cd test-platform-v2/backend
pytest tests/test_playwright_executor.py tests/test_ui_artifact_isolation.py -q
```

Expected: process, cancel, and artifact isolation tests pass.

- [ ] **Step 7: Commit**

```bash
git add test-platform-v2/backend/app/services/playwright_executor.py test-platform-v2/backend/app/services/ui_test_service.py test-platform-v2/backend/app/services/ui_runner_queue.py test-platform-v2/backend/app/models/ui_test.py test-platform-v2/backend/alembic/versions/20260713_ui_runner_hardening.py test-platform-v2/backend/tests/test_playwright_executor.py
git commit -m "feat: manage playwright runs with isolated runner processes"
```

### Task 5: UI Runner Queue, Health Check, And Frontend Run Detail

**Files:**
- Modify: `test-platform-v2/backend/app/api/v1/ui_test.py`
- Modify: `test-platform-v2/frontend/src/api/uitest.ts`
- Modify: `test-platform-v2/frontend/src/pages/uitest/index.tsx`
- Test: `test-platform-v2/backend/tests/test_ui_runner_queue.py`
- Test: `test-platform-v2/frontend/src/pages/uitest/__tests__/UiRunDetail.test.tsx`

- [ ] **Step 1: Add runner health endpoint**

```http
GET /api/v1/ui-tests/runner/health
```

Response:

```json
{
  "npx": true,
  "playwright": true,
  "version": "Version 1.x",
  "browsers_installed": true,
  "max_concurrent": 2,
  "running": 1
}
```

- [ ] **Step 2: Create queue service**

`ui_runner_queue.py` must expose:

```python
def ensure_processor_running() -> None: ...
def enqueue_run(run_id: int, job_id: int, project_id: int) -> None: ...
def running_count() -> int: ...
```

Use a process-local thread for development and leave a clear adapter boundary for RQ/Celery/Arq in production deployment.

- [ ] **Step 3: Update trigger endpoint**

`POST /ui-tests/{job_id}/trigger` behavior:

```text
1. Validate job belongs to current.project_id.
2. Create run with status=pending.
3. Enqueue run.
4. Return run immediately.
```

- [ ] **Step 4: Frontend run detail**

UI must show:

```text
run status
base_url
browser
duration
stdout/stderr summary
screenshots
videos
trace zip
HTML report
cancel button when pending/running
```

- [ ] **Step 5: Run checks**

```bash
cd test-platform-v2/backend
pytest tests/test_ui_runner_queue.py -q

cd ../frontend
npm test -- UiRunDetail
npm run typecheck
```

Expected: backend queue tests pass; frontend typecheck passes.

- [ ] **Step 6: Commit**

```bash
git add test-platform-v2/backend/app/api/v1/ui_test.py test-platform-v2/frontend/src/api/uitest.ts test-platform-v2/frontend/src/pages/uitest/index.tsx test-platform-v2/backend/tests/test_ui_runner_queue.py test-platform-v2/frontend/src/pages/uitest/__tests__/UiRunDetail.test.tsx
git commit -m "feat: expose ui runner health and run detail workflow"
```

---

## 4. Phase P2: RAG And LLM-WIKI For Agent Team Memory

### Task 6: RAG Enablement And Search Acceptance

**Files:**
- Modify: `test-platform-v2/backend/app/api/v1/knowledge.py`
- Modify: `test-platform-v2/backend/app/services/knowledge/vectorize.py`
- Modify: `test-platform-v2/backend/app/services/knowledge/search_service.py`
- Modify: `test-platform-v2/frontend/src/pages/knowledge/components/SearchTab.tsx`
- Test: `test-platform-v2/backend/tests/test_knowledge_search_rag.py`

- [ ] **Step 1: Write RAG acceptance tests**

```python
def test_reembed_updates_embedding_id(client, auth_headers, knowledge_chunk_factory, monkeypatch):
    chunk = knowledge_chunk_factory(project_id=1, embedding_id="")
    monkeypatch.setattr("app.core.config.settings.rag_enabled", True)
    resp = client.post("/api/v1/knowledge/reembed", headers={**auth_headers, "X-Project-Id": "1"})
    assert resp.status_code == 200
    assert resp.json()["data"]["embedded"] >= 1


def test_search_returns_project_scoped_hits(client, auth_headers, knowledge_chunk_factory, monkeypatch):
    knowledge_chunk_factory(project_id=1, title="比赛推送", content="matchId 必填")
    knowledge_chunk_factory(project_id=999, title="越权内容", content="不应返回")
    monkeypatch.setattr("app.core.config.settings.rag_enabled", True)
    resp = client.get("/api/v1/knowledge/search?q=比赛推送", headers={**auth_headers, "X-Project-Id": "1"})
    titles = [x["title"] for x in resp.json()["data"]["items"]]
    assert "比赛推送" in titles
    assert "越权内容" not in titles
```

- [ ] **Step 2: Add embedding health output**

`GET /knowledge/overview` should include:

```json
{
  "rag_enabled": true,
  "embedding_model": "BAAI/bge-small-zh-v1.5",
  "active_chunks": 100,
  "embedded_chunks": 93,
  "embedding_coverage": 0.93
}
```

- [ ] **Step 3: Run tests**

```bash
cd test-platform-v2/backend
pytest tests/test_knowledge_search_rag.py -q
```

Expected: search and reembed tests pass with `rag_enabled=True` test override.

- [ ] **Step 4: Commit**

```bash
git add test-platform-v2/backend/app/api/v1/knowledge.py test-platform-v2/backend/app/services/knowledge/vectorize.py test-platform-v2/backend/app/services/knowledge/search_service.py test-platform-v2/frontend/src/pages/knowledge/components/SearchTab.tsx test-platform-v2/backend/tests/test_knowledge_search_rag.py
git commit -m "feat: add rag search health and acceptance coverage"
```

### Task 7: Blue Lake To Raw Source To Wiki Contract

**Files:**
- Modify: `test-platform-v2/backend/app/services/external/lanhu_provider.py`
- Modify: `test-platform-v2/backend/app/services/wiki/import_service.py`
- Modify: `test-platform-v2/backend/app/services/wiki/ingest_service.py`
- Modify: `test-platform-v2/frontend/src/pages/knowledge/components/WikiImportDialog.tsx`
- Modify: `test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx`
- Test: `test-platform-v2/backend/tests/test_wiki_import_lanhu_contract.py`

- [ ] **Step 1: Add contract test for the provided Lanhu URL**

```python
LANHU_URL = "https://lanhuapp.com/web/#/item/project/product?tid=6324825d-1614-4d73-bc4c-f05cdf0734c1&pid=cc8cfbd5-16d2-481f-828e-7eb424a91694&versionId=26af2885-b229-4971-881c-c9bda43492fd&docId=e6b5ce1e-0d25-4e22-a9e9-450283918b3b&docType=axure&image_id=e6b5ce1e-0d25-4e22-a9e9-450283918b3b&pageId=2b4c4235b036420787d3e856b5d133d7&corpId=null"


def test_lanhu_url_ids_are_preserved():
    from app.services.external.lanhu_provider import parse_lanhu_ids
    doc_id, version_id, page_id = parse_lanhu_ids(LANHU_URL)
    assert doc_id == "e6b5ce1e-0d25-4e22-a9e9-450283918b3b"
    assert version_id == "26af2885-b229-4971-881c-c9bda43492fd"
    assert page_id == "2b4c4235b036420787d3e856b5d133d7"
```

- [ ] **Step 2: Standardize immutable_version**

Use:

```text
lanhu:{docId}:{versionId}:{pageId}
```

Expected value for this project:

```text
lanhu:e6b5ce1e-0d25-4e22-a9e9-450283918b3b:26af2885-b229-4971-881c-c9bda43492fd:2b4c4235b036420787d3e856b5d133d7
```

- [ ] **Step 3: Ensure one import can write three layers**

When `target.ingest_knowledge=true`, write:

```text
knowledge_source
knowledge_chunk
KnowledgeVector if rag_enabled=true
```

When `target.build_wiki=true`, write:

```text
wiki_raw_source
wiki_ingest_job
wiki_page
wiki_link
```

When `target.extract_graph=true`, write or enqueue:

```text
knowledge_entity
knowledge_relation
```

- [ ] **Step 4: Frontend displays extraction status**

`WikiImportDialog` must show:

```text
success
partial
image_only
auth_failed
permission_denied
invalid_url
failed
```

For `image_only`, require `description` before allowing Wiki compilation.

- [ ] **Step 5: Run tests**

```bash
cd test-platform-v2/backend
pytest tests/test_wiki_import_lanhu_contract.py -q
```

Expected: URL parsing and Raw Source contract tests pass without external network. A separate manual smoke with real Cookie validates extraction.

- [ ] **Step 6: Commit**

```bash
git add test-platform-v2/backend/app/services/external/lanhu_provider.py test-platform-v2/backend/app/services/wiki/import_service.py test-platform-v2/backend/app/services/wiki/ingest_service.py test-platform-v2/frontend/src/pages/knowledge/components/WikiImportDialog.tsx test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx test-platform-v2/backend/tests/test_wiki_import_lanhu_contract.py
git commit -m "feat: standardize lanhu wiki import contract"
```

### Task 8: Wiki Diff Quality And Artifact Review

**Files:**
- Modify: `test-platform-v2/backend/app/services/wiki/contract_extractor.py`
- Modify: `test-platform-v2/backend/app/services/wiki/diff_classifier.py`
- Modify: `test-platform-v2/backend/app/services/wiki/compare_service.py`
- Modify: `test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx`
- Modify: `test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffDetailDrawer.tsx`
- Test: `test-platform-v2/backend/tests/test_wiki_diff_quality.py`

- [ ] **Step 1: Write diff classifier tests**

```python
def test_diff_classifier_detects_field_and_coverage_gap():
    from app.services.wiki.diff_classifier import classify
    left = {
        "title": "比赛推送",
        "fields": [{"name": "matchId", "required": True, "type": "string"}],
        "test_cases": []
    }
    right = {
        "title": "比赛推送",
        "fields": [{"name": "matchId", "required": True, "type": "string"}, {"name": "minutes", "required": True, "type": "integer"}],
        "test_cases": ["matchId 必填校验"]
    }
    items = classify(left, right)
    assert any(i["diff_type"] == "missing_in_left" and i["dimension"] == "字段" for i in items)
    assert any(i["diff_type"] == "coverage_gap" for i in items)
```

- [ ] **Step 2: Cover all required dimensions**

Classifier must emit dimensions from this closed list:

```text
需求范围
客户端
业务规则
字段
接口
异常路径
权限角色
数据依赖
验收标准
测试覆盖
版本
证据
```

- [ ] **Step 3: Ensure every diff item has evidence**

Every `WikiDiffItem.evidence_json` must include:

```json
[
  {"source_type": "wiki_page", "id": 1, "title": "比赛推送"},
  {"source_type": "knowledge_chunk", "id": 2, "title": "字段规则"}
]
```

- [ ] **Step 4: Generate pending AI artifact**

Accepted diff items create `AiArtifact` with `review_status="pending"` only. No direct import into formal cases.

- [ ] **Step 5: Run tests**

```bash
cd test-platform-v2/backend
pytest tests/test_wiki_diff_quality.py -q
```

Expected: diff classification, evidence, and artifact conversion tests pass.

- [ ] **Step 6: Commit**

```bash
git add test-platform-v2/backend/app/services/wiki/contract_extractor.py test-platform-v2/backend/app/services/wiki/diff_classifier.py test-platform-v2/backend/app/services/wiki/compare_service.py test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffDetailDrawer.tsx test-platform-v2/backend/tests/test_wiki_diff_quality.py
git commit -m "feat: improve wiki diff quality and review handoff"
```

### Task 9: Agent Permission Split

**Files:**
- Modify: `test-platform-v2/backend/app/api/v1/agent.py`
- Modify: `test-platform-v2/backend/app/seed.py`
- Modify: `test-platform-v2/frontend/src/pages/workbench/index.tsx`
- Test: `test-platform-v2/backend/tests/test_agent_permissions.py`

- [ ] **Step 1: Write permission tests**

```python
def test_agent_view_can_read_but_not_run(client, user_headers):
    headers = {**user_headers(["agent:view"]), "X-Project-Id": "1"}
    assert client.get("/api/v1/agents/runs", headers=headers).status_code == 200
    assert client.post("/api/v1/agents/run/case_generation", headers=headers, json={"query": "x"}).status_code == 403


def test_agent_run_can_trigger(client, user_headers):
    headers = {**user_headers(["agent:view", "agent:run"]), "X-Project-Id": "1"}
    resp = client.post("/api/v1/agents/run/case_generation", headers=headers, json={"query": "生成用例"})
    assert resp.status_code == 200
```

- [ ] **Step 2: Change read endpoints**

Use:

```python
current: CurrentUser = Depends(require_permission("agent:view"))
```

For:

```text
GET /agents/runs
GET /agents/runs/{run_id}
GET /agents/types
GET /agents/queue
GET /agents/queue/stats
```

- [ ] **Step 3: Keep write endpoints on agent:run**

Use:

```python
current: CurrentUser = Depends(require_permission("agent:run"))
```

For:

```text
POST /agents/run/{agent_type}
POST /agents/queue/{item_id}/cancel
```

- [ ] **Step 4: Seed permissions**

Add:

```python
("agent:view", "查看 Agent 执行记录", "button")
```

Keep `agent:list` during one release as compatibility alias if existing roles already reference it. New UI checks should use `agent:view`.

- [ ] **Step 5: Run tests**

```bash
cd test-platform-v2/backend
pytest tests/test_agent_permissions.py -q
```

Expected: read-only and run permissions are separated.

- [ ] **Step 6: Commit**

```bash
git add test-platform-v2/backend/app/api/v1/agent.py test-platform-v2/backend/app/seed.py test-platform-v2/frontend/src/pages/workbench/index.tsx test-platform-v2/backend/tests/test_agent_permissions.py
git commit -m "fix: split agent view and run permissions"
```

---

## 5. Phase P3: External LLM-WIKI And Wiki Health

### Task 10: External LLM Wiki Connector

**Files:**
- Create: `test-platform-v2/backend/app/services/wiki/external_llm_wiki.py`
- Modify: `test-platform-v2/backend/app/models/wiki.py`
- Modify: `test-platform-v2/backend/app/schemas/wiki.py`
- Modify: `test-platform-v2/backend/app/api/v1/wiki.py`
- Create: `test-platform-v2/backend/alembic/versions/20260713_external_llm_wiki.py`
- Test: `test-platform-v2/backend/tests/test_external_llm_wiki_connector.py`

- [ ] **Step 1: Add connection model**

Fields:

```text
id
project_id
name
provider
base_url
token_encrypted
external_project_id
enabled
created_at
updated_at
```

- [ ] **Step 2: Implement read-only client**

Methods:

```python
def health_check(connection) -> dict: ...
def search(connection, query: str, limit: int = 10) -> list[dict]: ...
def read_page(connection, path: str) -> dict: ...
def graph(connection, node: str) -> dict: ...
```

- [ ] **Step 3: Add APIs**

```http
POST /api/v1/wiki/external-connections
GET  /api/v1/wiki/external-connections
POST /api/v1/wiki/external-connections/{id}/health-check
POST /api/v1/wiki/external-connections/{id}/search
GET  /api/v1/wiki/external-connections/{id}/files/content
GET  /api/v1/wiki/external-connections/{id}/graph
```

- [ ] **Step 4: Enforce switch and permission**

Use `external_llm_wiki_enabled=False` by default and require `wiki:external`.

- [ ] **Step 5: Run tests**

```bash
cd test-platform-v2/backend
pytest tests/test_external_llm_wiki_connector.py -q
```

Expected: 401, 503, timeout, success, and project isolation cases pass.

- [ ] **Step 6: Commit**

```bash
git add test-platform-v2/backend/app/services/wiki/external_llm_wiki.py test-platform-v2/backend/app/models/wiki.py test-platform-v2/backend/app/schemas/wiki.py test-platform-v2/backend/app/api/v1/wiki.py test-platform-v2/backend/alembic/versions/20260713_external_llm_wiki.py test-platform-v2/backend/tests/test_external_llm_wiki_connector.py
git commit -m "feat: add read-only external llm wiki connector"
```

### Task 11: Wiki Lint And Iteration Health Report

**Files:**
- Create: `test-platform-v2/backend/app/services/wiki/lint_service.py`
- Modify: `test-platform-v2/backend/app/api/v1/wiki.py`
- Create: `test-platform-v2/frontend/src/pages/knowledge/components/WikiLintPanel.tsx`
- Modify: `test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx`
- Test: `test-platform-v2/backend/tests/test_wiki_lint.py`

- [ ] **Step 1: Implement lint rules**

Rules:

```text
orphan_page: Wiki page has no inbound/outbound links.
no_source: Wiki page conclusion has no source_refs_json.
stale_page: Raw source is superseded but page is still approved.
conflict_rule: Two approved rule pages conflict on same stable key.
coverage_gap: Approved requirement page has no test case or api case coverage.
```

- [ ] **Step 2: Add API**

```http
POST /api/v1/wiki/lint
GET  /api/v1/wiki/lint/reports/{report_id}
```

- [ ] **Step 3: Convert lint results to review items**

Each lint issue should be convertible to `AiArtifact` with `review_status="pending"`.

- [ ] **Step 4: Run tests**

```bash
cd test-platform-v2/backend
pytest tests/test_wiki_lint.py -q
```

Expected: each lint rule has at least one deterministic test.

- [ ] **Step 5: Commit**

```bash
git add test-platform-v2/backend/app/services/wiki/lint_service.py test-platform-v2/backend/app/api/v1/wiki.py test-platform-v2/frontend/src/pages/knowledge/components/WikiLintPanel.tsx test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx test-platform-v2/backend/tests/test_wiki_lint.py
git commit -m "feat: add wiki health lint workflow"
```

---

## 6. Release Gates

### Backend Gate

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_apitest_project_isolation.py tests/test_api_task_worker.py tests/test_api_execution_snapshots.py tests/test_ui_runner_queue.py tests/test_playwright_executor.py tests/test_ui_artifact_isolation.py tests/test_knowledge_search_rag.py tests/test_wiki_import_lanhu_contract.py tests/test_wiki_diff_quality.py tests/test_agent_permissions.py -q
```

Expected:

```text
all selected tests pass
no route accepts query project_id where current.project_id is available
no API/UI runner task remains running after cancellation
no UI artifact list contains files outside storage/ui-runs/{run_id}
```

### Frontend Gate

Run:

```bash
cd test-platform-v2/frontend
npm run typecheck
npm test -- WikiTab WikiDiffTab UiRunDetail
npm run build
```

Expected:

```text
typecheck passes
component tests pass
production build succeeds
```

### Manual Smoke Gate

Use an environment with valid `LANHU_COOKIE` or `LANHU_USERNAME/LANHU_PASSWORD`.

```bash
cd lanhu-mcp
python lanhu_mcp_server.py
```

Then import the provided Lanhu URL from Knowledge Center:

```text
Knowledge Center -> Wiki 知识库 -> 导入蓝湖
target.ingest_knowledge=true
target.build_wiki=true
target.extract_graph=true
```

Expected:

```text
Raw Source immutable_version equals lanhu:e6b5ce1e-0d25-4e22-a9e9-450283918b3b:26af2885-b229-4971-881c-c9bda43492fd:2b4c4235b036420787d3e856b5d133d7
knowledge_source is created
knowledge_chunk is created
embedding_id is filled after reembed when rag_enabled=true
Wiki pages are created with source references
RAG vs Wiki diff task can run and produce evidence-backed items
accepted diff creates pending AiArtifact only
```

---

## 7. Rollout Order

1. P0 API project isolation and persistent worker.
2. P0 API snapshots, retry, cancellation, production guardrails.
3. P1 UI managed Playwright runner, cancellation, artifact isolation.
4. P1 UI script assets, runner health, frontend run detail.
5. P2 RAG enablement and embedding coverage acceptance.
6. P2 Lanhu Raw Source to Wiki contract using the provided Blue Lake URL.
7. P2 Wiki diff quality and artifact review.
8. P2 Agent permission split.
9. P3 external LLM-WIKI connector.
10. P3 Wiki lint and iteration health report.

---

## 8. Definition Of Done

- API 批量任务创建接口响应不等待用例执行完成。
- API 执行任务可取消、可重试失败项、可恢复 running/pending 状态、可限制并发。
- API 所有项目级路由使用 `current.project_id`，不信任 query `project_id`。
- API 失败结果可通过 request snapshot、response snapshot、assertion results、curl 复现。
- 生产环境写接口执行必须具备权限和二次确认。
- UI 触发接口响应不等待 Playwright 完成。
- UI runner 使用独立 `run_id` 目录，只展示当前 run 产物。
- UI 取消能终止 Playwright 子进程并落库 `cancelled`。
- RAG 搜索在 `rag_enabled=true` 时能完成向量回填和项目内混合检索。
- 蓝湖链接能形成可追溯 Raw Source，并绑定 `docId/versionId/pageId`。
- Wiki 页面有来源引用、审核状态和页面链接。
- 知识差异对比输出有维度、类型、严重级别、左右值、证据和建议。
- 差异生成的测试资产必须先进入 AI 审核台。
- Agent 查询权限与运行权限分离。
- 所有新增能力受配置开关、RBAC、审计日志和项目隔离保护。
