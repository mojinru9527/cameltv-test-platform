# API Testing Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready API testing module with service-based API assets, Swagger/OpenAPI import, generated boundary/idempotency cases, enhanced debug execution, and batch execution tasks.

**Architecture:** Extend the current FastAPI + SQLAlchemy API execution engine instead of replacing it. Add explicit API asset and execution task models, reuse existing `TestCase` API fields for generated cases, and refactor the React page into focused tabs for assets, debug, cases, and tasks.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, React 18, TypeScript, shadcn/ui, axios, Vitest/Pytest.

---

## File Structure

- Create `test-platform-v2/backend/app/models/api_asset.py`: API service, endpoint, import batch, execution task, execution task item models.
- Create `test-platform-v2/backend/app/schemas/api_asset.py`: request/response schemas for services, endpoints, imports, generation, and tasks.
- Create `test-platform-v2/backend/app/services/openapi_import_service.py`: parse Swagger/OpenAPI, preview import, confirm import.
- Create `test-platform-v2/backend/app/services/api_case_generation_service.py`: generate positive, validation, boundary, auth, and idempotency cases.
- Create `test-platform-v2/backend/app/services/api_task_service.py`: create and execute batch tasks.
- Modify `test-platform-v2/backend/app/services/api_execution_service.py`: support base_url path resolution, headers/body format normalization, extra assertion types.
- Modify `test-platform-v2/backend/app/api/v1/apitest.py`: add service/endpoint/import/generate/task routes.
- Modify `test-platform-v2/backend/app/api/v1/router.py`: ensure new routes are included through existing `apitest.router`.
- Create Alembic migration under `test-platform-v2/backend/alembic/versions/`.
- Modify `test-platform-v2/backend/app/models/__init__.py`: export new models.
- Modify `test-platform-v2/backend/app/seed.py`: add permissions for import/generate/task/prod execution.
- Modify `test-platform-v2/frontend/src/api/apitest.ts`: add API client functions and types.
- Modify `test-platform-v2/frontend/src/types/index.ts`: add API asset/task/import/generation types.
- Replace/split `test-platform-v2/frontend/src/pages/apitest/index.tsx`: compose new tabs from focused components.
- Create `test-platform-v2/frontend/src/pages/apitest/components/ImportDialog.tsx`.
- Create `test-platform-v2/frontend/src/pages/apitest/components/AssetTab.tsx`.
- Create `test-platform-v2/frontend/src/pages/apitest/components/DebugTab.tsx`.
- Create `test-platform-v2/frontend/src/pages/apitest/components/ApiCaseTab.tsx`.
- Create `test-platform-v2/frontend/src/pages/apitest/components/TaskTab.tsx`.
- Create backend tests in `test-platform-v2/backend/tests/test_apitest_assets.py`, `test_apitest_generation.py`, `test_apitest_tasks.py`.
- Create frontend tests in `test-platform-v2/frontend/src/pages/apitest/__tests__/`.

## Task 1: Add API Asset Data Model

**Files:**
- Create: `test-platform-v2/backend/app/models/api_asset.py`
- Modify: `test-platform-v2/backend/app/models/__init__.py`
- Create: `test-platform-v2/backend/alembic/versions/20260707_0012_api_testing_assets.py`

- [ ] **Step 1: Write model tests**

Create `test-platform-v2/backend/tests/test_apitest_assets.py`:

```python
from app.models.api_asset import ApiEndpoint, ApiService


def test_api_service_endpoint_unique_shape():
    service = ApiService(project_id=1, name="account-service", display_name="账号服务")
    endpoint = ApiEndpoint(
        project_id=1,
        service_id=1,
        module="Auth",
        method="POST",
        path="/api/v1/login",
        summary="登录",
    )

    assert service.name == "account-service"
    assert endpoint.method == "POST"
    assert endpoint.path == "/api/v1/login"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_apitest_assets.py -q
```

Expected: FAIL because `app.models.api_asset` does not exist.

- [ ] **Step 3: Implement models**

Create `app/models/api_asset.py`:

```python
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class ApiService(Base, TimestampMixin):
    __tablename__ = "api_service"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_api_service_project_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(index=True)
    display_name: Mapped[str] = mapped_column(default="")
    description: Mapped[str] = mapped_column(default="")
    default_base_path: Mapped[str] = mapped_column(default="")
    owner: Mapped[str] = mapped_column(default="")
    status: Mapped[str] = mapped_column(default="active")


class ApiImportBatch(Base, TimestampMixin):
    __tablename__ = "api_import_batch"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    service_id: Mapped[int] = mapped_column(index=True)
    source_type: Mapped[str] = mapped_column(default="openapi")
    source_ref: Mapped[str] = mapped_column(default="")
    version: Mapped[str] = mapped_column(default="")
    status: Mapped[str] = mapped_column(default="pending")
    total_count: Mapped[int] = mapped_column(default=0)
    created_count: Mapped[int] = mapped_column(default=0)
    updated_count: Mapped[int] = mapped_column(default=0)
    skipped_count: Mapped[int] = mapped_column(default=0)
    error_detail: Mapped[str] = mapped_column(Text, default="")


class ApiEndpoint(Base, TimestampMixin):
    __tablename__ = "api_endpoint"
    __table_args__ = (UniqueConstraint("project_id", "service_id", "method", "path", name="uq_api_endpoint_identity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    service_id: Mapped[int] = mapped_column(index=True)
    module: Mapped[str] = mapped_column(default="", index=True)
    method: Mapped[str] = mapped_column(default="GET", index=True)
    path: Mapped[str] = mapped_column(default="", index=True)
    summary: Mapped[str] = mapped_column(default="")
    description: Mapped[str] = mapped_column(Text, default="")
    request_schema: Mapped[str] = mapped_column(Text, default="{}")
    response_schema: Mapped[str] = mapped_column(Text, default="{}")
    auth_required: Mapped[bool] = mapped_column(default=False)
    deprecated: Mapped[bool] = mapped_column(default=False)
    source: Mapped[str] = mapped_column(default="manual")
    import_batch_id: Mapped[int | None] = mapped_column(default=None, index=True)
    version: Mapped[str] = mapped_column(default="")


class ApiExecutionTask(Base, TimestampMixin):
    __tablename__ = "api_execution_task"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    task_id: Mapped[str] = mapped_column(default="", index=True)
    name: Mapped[str] = mapped_column(default="")
    environment_id: Mapped[int | None] = mapped_column(default=None, index=True)
    service_id: Mapped[int | None] = mapped_column(default=None, index=True)
    status: Mapped[str] = mapped_column(default="pending", index=True)
    total: Mapped[int] = mapped_column(default=0)
    passed: Mapped[int] = mapped_column(default=0)
    failed: Mapped[int] = mapped_column(default=0)
    skipped: Mapped[int] = mapped_column(default=0)
    trigger_type: Mapped[str] = mapped_column(default="manual")
    creator_id: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)


class ApiExecutionTaskItem(Base, TimestampMixin):
    __tablename__ = "api_execution_task_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(index=True)
    case_id: Mapped[int] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(default="pending", index=True)
    duration_ms: Mapped[float] = mapped_column(default=0)
    request_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    response_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    assertion_results: Mapped[str] = mapped_column(Text, default="[]")
    error_message: Mapped[str] = mapped_column(Text, default="")
```

- [ ] **Step 4: Export models**

Add to `app/models/__init__.py`:

```python
from app.models.api_asset import ApiEndpoint, ApiExecutionTask, ApiExecutionTaskItem, ApiImportBatch, ApiService
```

- [ ] **Step 5: Add migration**

Create migration with equivalent tables and unique constraints. Run:

```bash
cd test-platform-v2/backend
alembic upgrade head
pytest tests/test_apitest_assets.py -q
```

Expected: PASS.

## Task 2: Add OpenAPI Import Preview and Confirm

**Files:**
- Create: `test-platform-v2/backend/app/schemas/api_asset.py`
- Create: `test-platform-v2/backend/app/services/openapi_import_service.py`
- Modify: `test-platform-v2/backend/app/api/v1/apitest.py`
- Test: `test-platform-v2/backend/tests/test_apitest_assets.py`

- [ ] **Step 1: Add parser tests**

Append:

```python
from app.services.openapi_import_service import preview_openapi_import


def test_preview_openapi_import_extracts_service_modules_and_endpoints(db_session):
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Account API", "version": "1.2.0"},
        "paths": {
            "/api/v1/login": {
                "post": {
                    "summary": "登录",
                    "tags": ["Auth"],
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }

    preview = preview_openapi_import(db_session, project_id=1, service_name="account-service", spec=spec)

    assert preview["total_count"] == 1
    assert preview["endpoints"][0]["module"] == "Auth"
    assert preview["endpoints"][0]["method"] == "POST"
```

- [ ] **Step 2: Implement schemas**

Define `OpenApiImportPreviewRequest`, `OpenApiImportConfirmRequest`, `ApiServiceOut`, `ApiEndpointOut`, `ApiImportPreviewOut`.

- [ ] **Step 3: Implement parser service**

Implement:

```python
def preview_openapi_import(db: Session, *, project_id: int, service_name: str, spec: dict) -> dict:
    ...

def confirm_openapi_import(db: Session, *, project_id: int, service_name: str, spec: dict, source_ref: str = "") -> dict:
    ...
```

Rules:

- Support OpenAPI 3.x and Swagger 2.0 `paths`.
- Use first tag as module; fallback to path segment.
- Persist `request_schema` and `response_schema` as JSON strings.
- Upsert by `project_id + service_id + method + path`.

- [ ] **Step 4: Add routes**

In `apitest.py`, add:

```python
@router.post("/import/preview", response_model=R[dict])
def import_preview(...):
    ...

@router.post("/import/confirm", response_model=R[dict])
def import_confirm(...):
    ...
```

- [ ] **Step 5: Run tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_apitest_assets.py -q
```

Expected: PASS.

## Task 3: Generate Boundary and Idempotency API Cases

**Files:**
- Create: `test-platform-v2/backend/app/services/api_case_generation_service.py`
- Modify: `test-platform-v2/backend/app/api/v1/apitest.py`
- Test: `test-platform-v2/backend/tests/test_apitest_generation.py`

- [ ] **Step 1: Add generation tests**

Create:

```python
from app.services.api_case_generation_service import generate_cases_from_endpoint


def test_generate_cases_includes_required_boundary_and_idempotency():
    endpoint = {
        "service_name": "account-service",
        "module": "Auth",
        "method": "POST",
        "path": "/api/v1/users",
        "summary": "创建用户",
        "request_schema": {
            "body": {
                "type": "object",
                "required": ["username", "age"],
                "properties": {
                    "username": {"type": "string", "minLength": 3, "maxLength": 20},
                    "age": {"type": "integer", "minimum": 0, "maximum": 120},
                    "role": {"type": "string", "enum": ["user", "admin"]},
                },
            }
        },
    }

    cases = generate_cases_from_endpoint(endpoint, templates=["basic", "boundary", "invalid", "idempotency"])
    titles = [c["title"] for c in cases]

    assert any("正常请求" in t for t in titles)
    assert any("username 必填缺失" in t for t in titles)
    assert any("username 最大长度越界" in t for t in titles)
    assert any("role 枚举非法" in t for t in titles)
    assert any("幂等" in t for t in titles)
```

- [ ] **Step 2: Implement generator**

Implement pure functions:

- `generate_cases_from_endpoint(endpoint, templates)`.
- `build_positive_case`.
- `build_required_cases`.
- `build_boundary_cases`.
- `build_enum_cases`.
- `build_type_cases`.
- `build_idempotency_cases`.

Each generated case must include `title`, `domain`, `module`, `case_type`, `priority`, `steps`, `expected_result`, `api_method`, `api_endpoint`, `api_headers`, `api_body`, `api_assertions`, `source`, `tags`.

- [ ] **Step 3: Add route**

Add `POST /apitest/cases/generate` with body:

```json
{
  "endpoint_id": 1,
  "templates": ["basic", "boundary", "invalid", "idempotency"],
  "import_to_case_library": true
}
```

If `import_to_case_library=true`, create `TestCase` rows with `source="api_generated"`.

- [ ] **Step 4: Run tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_apitest_generation.py -q
```

Expected: PASS.

## Task 4: Enhance Execution Engine

**Files:**
- Modify: `test-platform-v2/backend/app/services/api_execution_service.py`
- Test: `test-platform-v2/backend/tests/test_apitest_generation.py`

- [ ] **Step 1: Add tests for base_url and assertions**

Add tests for:

- environment `base_url` + endpoint path resolution.
- response header assertion.
- JSON Schema assertion.
- array length assertion.

- [ ] **Step 2: Implement request normalization**

Add helper:

```python
def _resolve_url(db: Session, environment_id: int | None, url: str) -> str:
    if url.startswith(("http://", "https://")):
        return url
    if environment_id:
        env = ...
        return env.base_url.rstrip("/") + "/" + url.lstrip("/")
    return url if url.startswith("http") else f"http://{url}"
```

- [ ] **Step 3: Add assertion types**

Support:

- `header`
- `json_schema`
- `type`
- `array_length`

- [ ] **Step 4: Run API execution tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_apitest_generation.py tests/test_testcase.py -q
```

Expected: PASS.

## Task 5: Add Batch Execution Tasks

**Files:**
- Create: `test-platform-v2/backend/app/services/api_task_service.py`
- Modify: `test-platform-v2/backend/app/api/v1/apitest.py`
- Test: `test-platform-v2/backend/tests/test_apitest_tasks.py`

- [ ] **Step 1: Add task tests**

Create tests that create two API `TestCase` rows, create a task, execute them, and assert task totals.

- [ ] **Step 2: Implement task service**

Functions:

- `create_task(db, project_id, creator_id, environment_id, case_ids, name)`.
- `run_task(db, task_id, project_id)`.
- `list_tasks(db, project_id, page, page_size)`.
- `get_task(db, task_id, project_id)`.

Store each item request/response snapshot.

- [ ] **Step 3: Add routes**

Routes:

- `POST /apitest/tasks`
- `GET /apitest/tasks`
- `GET /apitest/tasks/{task_id}`
- `POST /apitest/tasks/{task_id}/cancel`

- [ ] **Step 4: Run tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_apitest_tasks.py -q
```

Expected: PASS.

## Task 6: Add Permissions

**Files:**
- Modify: `test-platform-v2/backend/app/seed.py`

- [ ] **Step 1: Add permission rows**

Add:

- `apitest:view`
- `apitest:import`
- `apitest:generate`
- `apitest:task`
- `apitest:asset_manage`
- `apitest:execute_prod`

- [ ] **Step 2: Verify seed idempotency**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_p1_security_regression.py -q
```

Expected: PASS.

## Task 7: Frontend API Client and Types

**Files:**
- Modify: `test-platform-v2/frontend/src/types/index.ts`
- Modify: `test-platform-v2/frontend/src/api/apitest.ts`

- [ ] **Step 1: Add TypeScript interfaces**

Add interfaces for `ApiService`, `ApiEndpoint`, `ApiImportPreview`, `ApiExecutionTask`, `ApiExecutionTaskItem`, `GenerateApiCasesRequest`.

- [ ] **Step 2: Add API functions**

Implement:

- `fetchApiServices`
- `createApiService`
- `fetchApiEndpoints`
- `previewOpenApiImport`
- `confirmOpenApiImport`
- `generateApiCases`
- `createApiExecutionTask`
- `fetchApiExecutionTasks`
- `fetchApiExecutionTask`

- [ ] **Step 3: Typecheck**

Run:

```bash
cd test-platform-v2/frontend
npm run typecheck
```

Expected: PASS.

## Task 8: Refactor API Test Page

**Files:**
- Modify: `test-platform-v2/frontend/src/pages/apitest/index.tsx`
- Create: `test-platform-v2/frontend/src/pages/apitest/components/ImportDialog.tsx`
- Create: `test-platform-v2/frontend/src/pages/apitest/components/AssetTab.tsx`
- Create: `test-platform-v2/frontend/src/pages/apitest/components/DebugTab.tsx`
- Create: `test-platform-v2/frontend/src/pages/apitest/components/ApiCaseTab.tsx`
- Create: `test-platform-v2/frontend/src/pages/apitest/components/TaskTab.tsx`

- [ ] **Step 1: Build tab shell**

Tabs:

- 接口资产
- 快速调试
- 接口用例
- 执行任务

- [ ] **Step 2: Build import dialog**

Support URL, file, and text import. Show preview counts before confirmation.

- [ ] **Step 3: Build asset tab**

Left service/module tree; right endpoint table; row actions: 调试, 生成用例.

- [ ] **Step 4: Build debug tab**

Support method/url/env, Params, Headers table/JSON/text, Body type selector, assertions editor, response detail, save/generate actions.

- [ ] **Step 5: Build case tab**

List API test cases with service/module filters, checkbox selection, single execute, batch execute.

- [ ] **Step 6: Build task tab**

Show task list and task detail with per-case assertion results.

- [ ] **Step 7: Run frontend verification**

Run:

```bash
cd test-platform-v2/frontend
npm run typecheck
npm run test
```

Expected: PASS.

## Task 9: End-to-End Verification

**Files:**
- Add or update Playwright smoke test under `test-platform-v2/backend/tests/playwright/specs/` if local app test harness is available.

- [ ] **Step 1: Start backend and frontend**

Run the existing project commands from `COMMANDS.md` or package scripts.

- [ ] **Step 2: Verify core flow manually**

Flow:

1. Open `/apitest`.
2. Import sample OpenAPI.
3. Confirm assets appear by service.
4. Generate cases for one endpoint.
5. Open API 用例 tab and select generated cases.
6. Execute selected cases against test environment.
7. Open task detail and confirm assertion results.

- [ ] **Step 3: Capture final checks**

Record:

- imported endpoint count.
- generated case count.
- task pass/fail count.
- any failed assertion details.

## Self-Review

- Spec coverage: covers Swagger/OpenAPI import, any-interface case generation, boundary/idempotency templates, JMeter-like debug, service grouping, environment selection, multi-select execution, and task tracking.
- Placeholder scan: no implementation step relies on TBD/TODO; each task names files and concrete behavior.
- Type consistency: service/endpoint/task names match between model, schema, API, and frontend sections.
