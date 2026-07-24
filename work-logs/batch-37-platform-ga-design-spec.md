# Batch 37 — 测试平台 GA 补缺 + 工程债务清理 Design Spec

> **Design 部门** | 2026-07-23 | 版本 2.0（精简版）

## 架构决策

### AD-1: 批量执行不分派异步任务（同步阻塞）

**决策**：`execute-all` 端点同步执行所有用例，不通过 BackgroundTasks 或消息队列异步化。
**理由**：
- 计划内用例数通常 ≤50 条，总执行时间在可接受范围内（<30s）
- 与现有 `auto-execute` 模式保持一致（同步返回结果）
- 避免引入任务队列复杂度
**替代方案**：异步任务 + 轮询状态 — 对当前规模过度设计。

### AD-2: assignee_id 使用 FK 而非纯 int

**决策**：`assignee_id` 使用 `ForeignKey("user.id")` + index。
**理由**：
- 与现有 `User` 模型建立关系约束
- `batch_user_names` 已有批量查询模式可复用
- 避免孤儿引用

### AD-3: source_req_id 使用自由格式 string 而非 FK

**决策**：`source_req_id` 使用 `str` 类型，存储 `REQ-{编号}` 格式的标识符。
**理由**：
- 功能点 ID 来自 AI 提取的 modules→function_points，不存储在独立表中
- 灵活性：未来可兼容不同 ID 方案
- 加 index 满足查询性能
**替代方案**：创建 `FunctionPoint` 表 → 过度设计，功能点仅作为 AI 提取物存在。

### AD-4: 自动建计划与导入用例保持同一事务

**决策**：自动创建计划的逻辑在 `import_cases()` 同一 DB 事务内完成。
**理由**：
- 导入失败时不留孤儿计划
- 已使用 `transaction()` 上下文管理器（见 `import_cases` 现有实现）

---

## 数据模型变更

### 变更 1: TestPlan 新增字段

**文件**：[test_plan.py](../../test-platform-v2/backend/app/models/test_plan.py)

```python
# TestPlan 类新增（在 due_date 行之后）:
assignee_id: Mapped[int | None] = mapped_column(
    ForeignKey("user.id"), default=None, index=True,
    comment="指派执行人"
)
due_date: Mapped[datetime | None] = mapped_column(
    default=None, comment="截止日期"
)
```

**Alembic 迁移**：
```sql
ALTER TABLE test_plan ADD COLUMN assignee_id INTEGER NULL REFERENCES user(id);
ALTER TABLE test_plan ADD COLUMN due_date DATETIME NULL;
CREATE INDEX IF NOT EXISTS ix_test_plan_assignee_id ON test_plan(assignee_id);
```

### 变更 2: TestCase 新增字段

**文件**：[test_case.py](../../test-platform-v2/backend/app/models/test_case.py)

```python
# TestCase 类新增（在 source_doc_id 行之后）:
source_req_id: Mapped[str] = mapped_column(
    default="", index=True,
    comment="来源需求功能点 ID (REQ-xxx)"
)
```

**Alembic 迁移**：
```sql
ALTER TABLE test_case ADD COLUMN source_req_id VARCHAR NOT NULL DEFAULT '';
CREATE INDEX IF NOT EXISTS ix_test_case_source_req_id ON test_case(source_req_id);
```

---

## API 设计

### 端点 1: `POST /api/v1/test-plans/{plan_id}/execute-all`

**权限**：`testplan:execute`

**Request** (可选):
```json
{
  "environment_id": null
}
```

**Response** (`R[dict]`):
```json
{
  "code": 0,
  "data": {
    "total": 10,
    "executed": 8,
    "passed": 6,
    "failed": 2,
    "skipped": 2,
    "details": [
      {
        "plan_case_id": 101,
        "case_id": 42,
        "case_title": "TC-ADMIN-NEWS-001 - 验证新闻列表",
        "case_type": "api",
        "status": "pass"
      },
      {
        "plan_case_id": 102,
        "case_id": 43,
        "case_title": "TC-ADMIN-NEWS-002 - 手动验证",
        "case_type": "manual",
        "status": "skip",
        "error": "人工用例，需手动执行"
      }
    ]
  }
}
```

**Service 逻辑** (`execute_all_cases`):
```
For each plan_case:
  if case_type == "api" → execute_api_case() → record pass/fail
  else → create TestExecution with status="skip", notes="需人工执行"
Update plan_case.last_status for all
Return summary
```

### 端点 2: 更新 `POST /api/v1/requirements/{doc_id}/import`

**Schema 变更** — [requirement.py](../../test-platform-v2/backend/app/schemas/requirement.py):

```python
class CaseImportRequest(BaseModel):
    indices: list[int]
    create_plan: bool = False   # ← 新增

class CaseImportResult(BaseModel):
    imported: int
    skipped: int
    total: int
    plan_id: int | None = None   # ← 新增
    plan_name: str = ""          # ← 新增
```

**Service 逻辑** — 在 `import_cases()` 成功后：
```
if create_plan:
    plan = create_plan(db, {
        "name": f"{requirement.title} - 测试计划",
        "status": "draft",
    }, creator_id, project_id)
    add_cases(db, plan.id, [newly_imported_case_ids], project_id)
    return {..., "plan_id": plan.id, "plan_name": plan.name}
```

### 端点 3: 更新 `PlanCreate` / `PlanUpdate` / `PlanOut`

**文件**：[test_plan.py schemas](../../test-platform-v2/backend/app/schemas/test_plan.py)

```python
class PlanCreate(BaseModel):
    # ... 现有字段 ...
    assignee_id: int | None = None   # ← 新增
    due_date: datetime | None = None # ← 新增

class PlanUpdate(BaseModel):
    # ... 现有字段 ...
    assignee_id: int | None = None
    due_date: datetime | None = None

class PlanOut(BaseModel):
    # ... 现有字段 ...
    assignee_id: int = 0             # ← 新增
    due_date: datetime | None = None # ← 新增
    assignee_name: str = ""          # ← 新增

class PlanCaseOut(BaseModel):
    # ... 现有字段 ...
    source_req_id: str = ""          # ← 新增
```

### Service 更新 — `_plan_to_dict`

```python
def _plan_to_dict(r: TestPlan) -> dict:
    return {
        # ... 现有字段 ...
        "assignee_id": r.assignee_id,
        "due_date": r.due_date.isoformat() if r.due_date else None,
    }
```

### Service 更新 — `_plan_case_to_dict`

```python
def _plan_case_to_dict(pc: TestPlanCase, case: TestCase | None) -> dict:
    return {
        # ... 现有字段 ...
        "source_req_id": case.source_req_id if case else "",
    }
```

### Service 更新 — `create_case`

`test_case_service.create_case()` 已接受 `dict` 参数，只需在调用处传入 `source_req_id`。

---

## 前端组件设计

### 1. 计划表单 — 指派选择器

**位置**：[testplan/](../../test-platform-v2/frontend/src/pages/testplan/) 创建/编辑表单

**组件**：
- `AssigneeSelect` — 复用现有用户选择组件或简单 `<select>` 下拉
- `DatePicker` — 使用 shadcn/ui 的 Calendar + Popover 组合

**改动点**：
- 表单增加两行：负责人（下拉选择） + 截止日期（日期选择器）
- 计划详情页显示指派信息（头像 + 姓名 + 剩余天数）

### 2. 导入弹窗 — 自动建计划复选框

**位置**：[AiResultModal.tsx](../../test-platform-v2/frontend/src/pages/requirement/AiResultModal.tsx) 的导入操作区

**组件**：shadcn/ui `<Checkbox>`

**改动点**：
- 导入按钮旁增加 `<Checkbox>` "同时创建测试计划"
- 勾选后 API 调用传入 `create_plan: true`
- 导入成功后如有 `plan_id`，显示跳转链接 toast

### 3. 用例详情 — source_req_id 标签

**位置**：[testcase/](../../test-platform-v2/frontend/src/pages/testcase/) 详情/列表

**改动点**：
- 列表增加可选的「需求功能点」列（显示 `REQ-xxx`）
- 详情页元数据区显示 source_req_id badge

---

## 工程债务执行方案

### npm audit

```bash
cd frontend
npm audit                          # 查看漏洞清单
npm audit fix                      # 自动修复兼容的
# 手动升级剩余 critical/high 包
npm run typecheck && npm run build # 验证
```

### Ruff

```bash
cd backend
ruff check app/ --fix              # 自动修复
ruff check app/                    # 检查残余，手动处理
```

---

## 文件变更清单（确定版）

| 文件 | 变更 |
|------|------|
| `backend/app/models/test_plan.py` | +2 字段 (assignee_id, due_date) |
| `backend/app/models/test_case.py` | +1 字段 (source_req_id) |
| `backend/app/schemas/test_plan.py` | PlanCreate/Update/Out + PlanCaseOut 新增字段 |
| `backend/app/schemas/requirement.py` | CaseImportRequest + CaseImportResult 新增字段 |
| `backend/app/services/test_plan_service.py` | +execute_all_cases, _plan_to_dict 更新, _plan_case_to_dict 更新, list_plans batch assignee_name |
| `backend/app/services/requirement_service.py` | import_cases 增强 (source_req_id + create_plan) |
| `backend/app/api/v1/test_plan.py` | +execute_all 端点, assignee 字段透传 |
| `backend/app/api/v1/requirement.py` | import 端点 create_plan 参数 |
| `backend/alembic/versions/` | 2 份迁移脚本 |
| `frontend/src/pages/testplan/` | 指派表单 + 详情展示 |
| `frontend/src/pages/requirement/AiResultModal.tsx` | 自动建计划复选框 |
| `frontend/src/pages/testcase/` | source_req_id 展示 |
| `frontend/src/api/` | API 类型更新 |
| `frontend/src/types/` | 类型定义更新 |
