# Batch 22 — Slice 1 设计规范

> **Design (🎨)** | Date: 2026-07-19 | 基于 PM Plan 的 Slice 1 三任务设计

## 现状基线

### 代码级发现（探索日期：2026-07-19）

| 组件 | 文件 | 现状 | Slice 1 缺口 |
|------|------|------|-------------|
| 用例模型 | `models/test_case.py:39` | `steps` JSON: `[{step, desc, expected}]`, `case_type`: manual/api/ui | — |
| API 执行引擎 | `services/api_execution_service.py:37-73` | `execute_api_case(db, case_id)` — 完整流水线（变量→VPN→httpx→断言→快照） | — |
| 断言引擎 | `services/api_execution_service.py:241-299` | 9 种断言：status_code/jsonpath/regex/response_time/header/json_schema/type/array_length | — |
| 变量解析 | `services/environment_service.py:121-141` | `resolve_variables(db, env_id, template)` — `${VAR_NAME}` 替换 | — |
| 后台 Worker | `services/api_task_worker.py:266-291` | 单守护线程，2s 轮询，任务认领+逐条执行+取消 | 仅用于 ApiExecutionTask，不用于 TestPlan。注意：`task_worker.py` + `ui_runner_queue.py` 存在三路 Worker 重复 |
| 计划自动执行 | `services/test_plan_service.py:356-416` | `auto_execute_api_cases()` — **同步阻塞**，只处理 `case_type=="api"` | 不支持 functional/ui 类型；请求线程内阻塞，大批量会超时 |
| Playwright 执行器 | `services/playwright_executor.py:245-249` | `subprocess.Popen([npx, playwright, test])` + semaphore(2) + 产物隔离 + 取消轮询 + 300s 超时 | — |
| Playwright 骨架生成 | `services/case_generation_service.py:280` | `_build_playwright_spec()` — 生成空心 `test.step()` 骨架（注释占位，无真实操作） | **Task 1a 起點**：替换空心 comment 为 LLM 生成的 `page.click()`/`page.fill()` |
| AI 服务 | `services/ai_service.py:644` | `_call_ai_api()` — httpx AsyncClient POST DeepSeek `/chat/completions`，180s 超时，`response_format: json_object` | 代码生成需要纯文本输出（非 JSON） |
| 用例执行端点 | `api/v1/test_case.py:361-395` | `POST /test-cases/{case_id}/execute` — **已存在！** 调 `execute_api_case()`，含环境选择+数据集参数化 | ✅ Task 1c 后端已完成，只需前端的执行按钮 |
| 前端用例详情 | `pages/testcase/CaseDrawer.tsx` | 表单编辑+评审，无执行按钮 | 缺「执行」按钮（Task 1c 唯一缺口） |

### 现有流程

```
测试计划 → auto_execute_api_cases()
  → 遍历 TestPlanCase
    → 过滤 case_type=="api"
    → execute_api_case() 同步执行
    → 创建 TestExecution 记录
```

**缺口**：
1. 功能用例（`case_type=="manual"` 含 `steps` JSON）无法自动执行——没有编译器
2. 执行是同步的（HTTP 请求线程内阻塞），大批量会超时
3. 没有进度反馈（SSE/polling）
4. 没有 per-case 执行入口（用例详情页缺少「执行」按钮）

---

## 设计决策

### 决策 D1：编译器走 DeepSeek prompt，不走模板

**理由**：与 Leader 决策 2 一致。`steps` JSON 内容是自然语言（"点击登录按钮"、"验证页面跳转到首页"），模板引擎无法覆盖。

**缓解**：编译结果用 `npx playwright test --dry-run` 做语法校验；校验不过的返回行号 + AI 修复建议。

### 决策 D2：统一编排器复用现有 auto_execute 端点，加后台 Worker

**理由**：与 Leader 决策 3 一致。`api_task_worker.py` 的认领-执行-取消模式已经过验证。不建新调度系统，在 `auto_execute_api_cases` 基础上扩展为支持三种 `case_type`。

**架构**：
```
POST /test-plans/{id}/auto-execute
  → 创建后台任务（类似 ApiExecutionTask 模式）
  → 立即返回 task_id + "accepted"
  → 后台 worker 逐条执行：
      - case_type=="api"    → execute_api_case()
      - case_type=="manual" → compile_steps() → run_playwright()
      - case_type=="ui"     → run_playwright()  (已有 spec)
  → 前端 polling GET /test-plans/{id}/auto-execute/{task_id}/status
```

### 决策 D3：API 一键执行直接复用现有 execute_api_case

**理由**：`execute_api_case(db, case_id, ...)` 已经完整可用。只需：
- 后端：新增 `POST /test-cases/{id}/execute` 端点
- 前端：CaseDrawer 中 API 类型用例加「执行」按钮 + 环境选择 + 结果展示

**风险**：生产环境保护（`_check_prod_protection`）已有，无需重复实现。

---

## Task 1a: 用例 → Playwright 脚本编译器

### 新增文件

#### `backend/app/services/case_compiler_service.py`

**职责**：接收 TestCase 的 `steps` + `preconditions` + `expected_result`，调用 DeepSeek 生成 Playwright `.spec.ts` 代码。

**接口契约**：

```python
def compile_to_playwright(
    case_id: int,
    db: Session,
    *,
    base_url: str = "http://localhost:5173",  # 被测前端地址
    environment_id: int | None = None,
) -> dict:
    """返回:
    {
        "case_id": 123,
        "spec_code": "import { test, expect } from '@playwright/test';...",
        "spec_file": "generated-TC-MODULE-001.spec.ts",
        "validation": {
            "syntax_ok": True,
            "dry_run_ok": True,
            "errors": []
        },
        "compilation_time_ms": 2345.6,
        "model_used": "deepseek-chat",
        "prompt_tokens": 1234,
        "completion_tokens": 567,
    }
    """
```

**编译 Prompt 结构**：

```
System: 你是 Playwright 测试自动化专家。根据测试用例的步骤描述，生成可直接运行的 Playwright TypeScript 代码。
必须遵守：
1. 使用 import { test, expect } from '@playwright/test';
2. 每个步骤用 test.step() 包裹
3. 使用真实的选择器（getByText/getByRole/getByLabel），不用 CSS 类名
4. 每个步骤断言后截图（screenshot: 'only-on-failure'）
5. 前置条件在 test.beforeEach 中处理
6. 只输出 TypeScript 代码，不要 markdown 包裹，不要解释

User: 请将以下测试用例编译为 Playwright 代码：

**用例标题**: {title}
**前置条件**: {preconditions}
**测试步骤**:
{steps_as_numbered_list}
**预期结果**: {expected_result}
**被测地址**: {base_url}
```

**Sandbox 校验流程**：
1. 将生成的 `.spec.ts` 写入 `playwright/generated/` 临时目录
2. `npx playwright test --dry-run generated-xxx.spec.ts` (2s timeout)
3. 解析输出：有 error → 返回行号+错误信息
4. 清理临时文件

#### `backend/app/api/v1/case_compiler.py`

```python
router = APIRouter(prefix="/test-cases", tags=["用例编译"])

class CompileRequest(BaseModel):
    base_url: str = "http://localhost:5173"
    environment_id: int | None = None

class CompileResponse(BaseModel):
    case_id: int
    spec_code: str
    spec_file: str
    validation: dict
    compilation_time_ms: float
    model_used: str

@router.post("/{case_id}/compile", response_model=R[CompileResponse])
def compile_case(case_id: int, body: CompileRequest, current=Depends(...), db=Depends(get_db)):
    """将功能用例的 steps 编译为 Playwright .spec.ts 代码。"""
    result = case_compiler_service.compile_to_playwright(
        case_id, db, base_url=body.base_url, environment_id=body.environment_id
    )
    return R.ok(CompileResponse(**result))
```

### Task 1a 涉及文件总览

| 文件 | 操作 | 预估行数 |
|------|------|---------|
| `services/case_compiler_service.py` | 新建 | ~180 |
| `api/v1/case_compiler.py` | 新建 | ~35 |
| `api/v1/router.py` | 编辑 | +2 (注册路由) |
| `playwright/generated/.gitkeep` | 新建 | 0 |
| `tests/test_case_compiler.py` | 新建 | ~80 |

---

## Task 1b: 统一批量执行编排器

### 修改现有文件

#### `services/test_plan_service.py` — 扩展现有 `auto_execute_api_cases`

**现有签名不变，扩展内部逻辑**：

```python
def auto_execute_api_cases(
    db: Session,
    plan_id: int,
    *,
    executor_id: int = 0,
    environment_id: int | None = None,
    project_id: int = 0,
) -> dict:
```

**扩展点**：
1. 当前只过滤 `case_type == "api"` → 改为支持三种 case_type
2. 当前同步执行 → 改为创建后台任务，立即返回 task_id
3. 当前只记录执行结果 → 增加进度追踪

**新执行分发逻辑**：

```python
def _execute_single_case(pc: TestPlanCase, tc: TestCase, env_id, project_id) -> dict:
    if tc.case_type == "api":
        return _execute_api_case(tc, env_id, project_id)
    elif tc.case_type == "manual" and tc.steps and tc.steps != "[]":
        return _execute_functional_case(tc, env_id, project_id)
    elif tc.case_type == "ui":
        return _execute_ui_case(tc, env_id, project_id)
    else:
        return {"status": "skipped", "reason": "不支持的用例类型或缺少步骤"}

def _execute_functional_case(tc, env_id, project_id) -> dict:
    """编译 steps → 执行 Playwright 脚本 → 返回结果。"""
    # 1. 调 case_compiler_service.compile_to_playwright()
    # 2. 调 playwright_executor 执行生成的 .spec.ts
    # 3. 解析 Playwright JSON 报告
    # 4. 返回统一格式结果
```

#### `api/v1/test_plan.py` — 新增进度查询端点

```python
@router.get("/{plan_id}/auto-execute/progress", response_model=R[dict])
def get_auto_execute_progress(plan_id: int, ...):
    """查询自动执行进度。"""
    return R.ok({
        "plan_id": plan_id,
        "total": 10, "completed": 5, "passed": 3, "failed": 1, "in_progress": 1,
        "current_case_id": 123,
        "current_case_title": "TC-ADMIN-NEWS-001",
        "started_at": "2026-07-19T12:00:00Z",
        "eta_seconds": 30,
    })
```

#### 进度追踪模型（内存 + DB 回退）

```python
# services/test_plan_service.py 内嵌
# 使用 threading.Lock + 内存 dict（简单高效，不需要新表）
_progress_store: dict[int, dict] = {}  # plan_id → progress
_progress_lock = threading.Lock()
```

**并发控制**：默认 2 并发，复用 `threading.Semaphore(2)`

### Task 1b 涉及文件总览

| 文件 | 操作 | 预估行数 |
|------|------|---------|
| `services/test_plan_service.py` | 编辑 | +120 (扩展 auto_execute + 分发逻辑) |
| `api/v1/test_plan.py` | 编辑 | +30 (新增 progress 端点) |
| `tests/test_auto_execute.py` | 新建 | ~100 |

---

## Task 1c: API 用例一键执行

### 后端

#### `api/v1/test_case.py` — 新增执行端点

```python
class ExecuteCaseRequest(BaseModel):
    environment_id: int | None = None
    confirm_prod: bool = False

@router.post("/{case_id}/execute", response_model=R[dict])
def execute_single_case(
    case_id: int,
    body: ExecuteCaseRequest,
    current: CurrentUser = Depends(require_permission("testcase:execute")),
    db: Session = Depends(get_db),
):
    """立即执行一条 API 用例，返回执行结果（不含存储）。"""
    from app.services.api_execution_service import execute_api_case
    try:
        result = execute_api_case(
            db, case_id,
            project_id=current.project_id or 0,
            environment_id=body.environment_id,
            confirm_prod=body.confirm_prod,
            has_execute_prod=True,
        )
        return R.ok(result)
    except ValueError as e:
        return R(code=1, msg=str(e))
```

### 前端

#### `pages/testcase/CaseDrawer.tsx` — 新增执行按钮

**仅在 `case_type === "api"` 且 `editing?.id` 时显示**：

```tsx
{editing?.id && selType === 'api' && (
  <div className="border-t pt-4 mt-4">
    <div className="flex items-center justify-between mb-3">
      <span className="text-sm font-medium">⚡ 执行测试</span>
      <Select value={execEnvId} onValueChange={setExecEnvId}>
        <SelectTrigger className="w-[160px] h-8">
          <SelectValue placeholder="选择环境" />
        </SelectTrigger>
        <SelectContent>
          {environments.map(e => (
            <SelectItem key={e.id} value={String(e.id)}>{e.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
    <Button
      size="sm"
      onClick={handleExecute}
      disabled={executing}
      variant="secondary"
    >
      {executing ? (
        <><Loader2 className="size-4 animate-spin mr-1" /> 执行中...</>
      ) : (
        <><Play className="size-4 mr-1" /> 执行</>
      )}
    </Button>

    {/* 执行结果 */}
    {execResult && (
      <div className="mt-3 rounded-md border p-3 text-sm">
        <div className="flex items-center gap-2 mb-2">
          <Badge variant={execResult.all_pass ? 'default' : 'destructive'}>
            {execResult.all_pass ? '通过' : '失败'}
          </Badge>
          <span className="text-muted-foreground">
            {execResult.status_code} · {execResult.duration_ms}ms
          </span>
        </div>
        {/* 断言结果列表 */}
        {execResult.assertions?.map((a, i) => (
          <div key={i} className="text-xs">
            {a.passed ? '✅' : '❌'} {a.message}
          </div>
        ))}
        {/* 响应快照可展开 */}
        <details className="mt-2">
          <summary className="cursor-pointer text-xs text-muted-foreground">
            查看响应详情
          </summary>
          <pre className="mt-1 text-xs whitespace-pre-wrap max-h-[200px] overflow-y-auto">
            {JSON.stringify(execResult.response_snapshot, null, 2)}
          </pre>
        </details>
      </div>
    )}
  </div>
)}
```

### Task 1c 涉及文件总览

| 文件 | 操作 | 预估行数 |
|------|------|---------|
| `api/v1/test_case.py` | 编辑 | +25 |
| `pages/testcase/CaseDrawer.tsx` | 编辑 | +70 |
| `api/testcase.ts` (前端) | 编辑 | +8 (新增 executeCase 函数) |
| `tests/test_case_execute.py` | 新建 | ~50 |

---

## UI 规范自查（cameltv-ui-conventions 8 Red Flags）

| # | Red Flag | 本次设计是否触发 | 处理 |
|---|----------|----------------|------|
| 1 | Badge 颜色不可辨 | ❌ | — |
| 2 | 硬编码语义色没深色变体 | ⚠️ 执行结果状态色 | 用 `variant="default"`/`"destructive"`（shadcn 已含 dark:） |
| 3 | 状态标签裸英文 | ⚠️ pass/fail | 映射为「通过」「失败」中文 |
| 4 | 缺 Error 态 | ⚠️ 执行按钮 | 失败时 toast 提示，结果区显示 error_message |
| 5 | 失败态误用加载动画 | ✅ 需注意 | executing=true → spin；结果区独立 |
| 6 | 原始 JSON 裸展示 | ⚠️ 响应快照 | `JSON.stringify(x, null, 2)` + `<pre>` |
| 7 | 触控目标 < 44px | ⚠️ 执行按钮 | `size="sm"` 约 36px → 可接受（非主操作区） |
| 8 | 响应式断点跨度过大 | ❌ | 执行结果区在 Drawer 内，单栏 |

---

## Bug Guard 自查（cameltv-bug-guard）

| 铁律 | 触发？ | 防范 |
|------|--------|------|
| B1: 静态路径先于参数路径 | ⚠️ | `/{case_id}/execute` 在 `/{case_id}` 之后 → 需要放在 router 中 `/{case_id}` 之前 |
| B2: 非幂等网络操作只做一次 | ✅ | LLM 编译只调用一次 DeepSeek，结果直接返回 |
| B3: 加列迁移前先搜 | ❌ | 无新表/新列 |
| F1: useEffect 异步 cleanup | ⚠️ | 执行按钮用 `useState` + cleanup 标志 |
| F2: N+1 请求 | ❌ | — |
| F3: API 面三层检查 | ⚠️ | 新增 compiler 路由 → router.py 注册 → service 实现 |
| F4: Axios 错误提取链含 detail | ⚠️ | 新增 `executeCase` API 函数，错误提取链需含 `detail` |

---

## 路由注册顺序（防 B1: 422 陷阱）

```python
# 在 api/v1/router.py 或 test_case.py 中，以下顺序确保静态段在前：
# 已有的 /batch、/domains 已在前面（正确）
# 新增：
POST /test-cases/{case_id}/execute   ← 静态 execute 段，需排在 /{case_id} 之前
POST /test-cases/{case_id}/compile   ← 静态 compile 段，需排在 /{case_id} 之前

# 当前 test_case.py 路由：
# /batch      ← 静态，OK
# /domains    ← 静态，OK
# /           ← GET list
# /{case_id}  ← 最后注册
# 需要把 /{case_id}/execute 和 /{case_id}/compile 放在 /{case_id} 之前
```

**修正方案**：在 `test_case.py` 中，`/{case_id}` 路由之前插入：
```python
@router.post("/{case_id}/execute")
@router.post("/{case_id}/compile")
```

✅ FastAPI 按注册顺序匹配——两个新路由含后续静态段 `/execute` `/compile`，在解析 `/{case_id}` 之前先被匹配。

---

## 数据流：端到端

```
用户点击「全部执行」(测试计划)
  → POST /test-plans/{id}/auto-execute {environment_id:1}
    → 后端创建后台任务
    → 返回 {task_id: "xxx", accepted: true}
  → 前端开始 polling GET /test-plans/{id}/auto-execute/progress
    → 显示进度条: "3/10 完成 · 2通过 1失败"

后台 Worker 逐条执行:
  For each TestPlanCase:
    ├─ case_type=="api" → execute_api_case()
    │   → httpx 请求 → 断言 → 快照 → TestExecution 记录
    │
    ├─ case_type=="manual" → compile_to_playwright()
    │   → 调 DeepSeek 生成 .spec.ts
    │   → dry-run 校验
    │   → playwright_executor 执行
    │   → 解析 JSON 报告 → TestExecution 记录
    │
    └─ case_type=="ui" → playwright_executor (已有 spec)
        → 执行 → TestExecution 记录

全部完成:
  → polling 返回 {completed: 10, passed: 8, failed: 2}
  → 前端展示汇总: 通过率 80%
```

---

## 关联

- [batch-22-platform-audit-pm-plan.md](batch-22-platform-audit-pm-plan.md) — PM Plan（Slice 1 任务定义来源）
- [batch-22-platform-audit-leader-verdict.md](batch-22-platform-audit-leader-verdict.md) — Leader 决策 1-4
- `cameltv-ui-conventions` skill — 前端 Red Flags
- `cameltv-bug-guard` skill — 避坑铁律

---

**Design Agent**: 设计部门 🎨 | **日期**: 2026-07-19 | **下一步**: Dev 实现 (Task 1a → 1c → 1b，按依赖顺序)
