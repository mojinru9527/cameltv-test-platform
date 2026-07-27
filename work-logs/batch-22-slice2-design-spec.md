# Batch 22 — Slice 2 设计规范

> **Design (🎨)** | Date: 2026-07-19 | 基于 PM Plan 的 Slice 2 三任务设计

## 现状基线

### 代码级发现

| 组件 | 文件 | 现状 | 缺口 |
|------|------|------|------|
| AiResultModal | `pages/requirement/AiResultModal.tsx` (930行) | 一次性 Dialog：表格展示 AI 用例 → 选择 → 导入。关闭后状态丢失，无持久化 | 不能分批复审、不能离开后回来 |
| 需求管理页 | `pages/requirement/index.tsx` (~450行) | 文件拖拽上传 + 蓝湖链接。有「生成」「查看」按钮触发 AiResultModal | 无「快速创建」入口，必须上传文件 |
| 计划详情 | `pages/testplan/PlanDetail.tsx` | 表格展示执行结果：pass/fail/skip/block + 手动执行 | 无 AI 分诊、无分类展示、无「一键提缺陷」 |
| 缺陷管理 | `pages/defect/` | 6 状态机 + 评论 + 附件 CRUD | 无预填入口（从失败用例创建） |
| 后端审核 | `services/review_service.py` | 已存在 review 接口 | 仅 test_case 级别评审，无 requirement 级别审核队列 |
| AI 服务 | `services/ai_service.py` | DeepSeek，两段式生成 | 无 triage/分诊 prompt |

### 关键发现

1. **AiResultModal 930 行单文件**：混合了需求分析面板、功能点审核、用例表格、内联编辑、导入——所有功能塞在一个 Dialog 里。改为页面可显著降低复杂度。
2. **前端未调用 auto-execute**：搜索 `auto-execute` 在前端代码中 0 结果——计划自动执行功能（Slice 1 已完善）尚未被前端使用。
3. **无 AI 分诊逻辑**：执行失败后无任何自动分析，用户需手工排查。

---

## 设计决策

### D1：审查队列走新页面，不复用 Dialog

**理由**：Persistent state + URL 可访问 + 更大的屏幕空间。在 `pages/requirement/ReviewPage.tsx` 新建独立页面，路由 `/requirement/{id}/review`。

**与旧 AiResultModal 的关系**：保留 AiResultModal 作为快速预览（生成后立即弹出查看），但添加「在审查页打开」按钮跳转到完整页面。

### D2：审查状态持久化到后端

**理由**：刷新不丢失、多人可协作（未来）。新建轻量模型 `RequirementReview` 存储每个生成用例的审核状态。

```python
class RequirementReview(Base):
    __tablename__ = "requirement_review"
    id: int (PK)
    requirement_id: int (FK → requirement_document)
    case_index: int            # AI 生成用例的 index
    status: str                # pending / approved / rejected / edited
    edited_data: str           # JSON: 编辑后的用例数据（仅 edited 状态）
    reviewer_id: int
    reviewed_at: datetime
```

### D3：AI 分诊走 LLM one-shot，不建复杂规则引擎

**理由**：失败模式多变（超时/断言失败/网络错误/环境问题），规则引擎不可穷举。LLM 直接分析执行结果给出分类。

---

## Task 2a: 审查队列（替代 AiResultModal）

### 后端

#### 新模型：`models/requirement_review.py`

```python
class RequirementReview(Base):
    __tablename__ = "requirement_review"
    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirement_document.id"), index=True)
    case_index: Mapped[int]           # AI 生成用例的 index（唯一标识）
    status: Mapped[str] = mapped_column(default="pending")  # pending/approved/rejected/edited
    edited_data: Mapped[str] = mapped_column(default="{}")  # JSON: 编辑后的用例字段
    reviewer_id: Mapped[int] = mapped_column(default=0)
    reviewed_at: Mapped[datetime] = mapped_column(default=datetime.now)
```

#### 新 API 端点（加到 `api/v1/requirement.py`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/requirements/{id}/review` | 获取审查状态（所有 cases + 审核标记） |
| PUT | `/requirements/{id}/review/{case_index}` | 审核单条 case (action: approve/reject/edit) |
| POST | `/requirements/{id}/review/import` | 批量导入已批准的 cases 到用例库 |

### 前端

#### `pages/requirement/ReviewPage.tsx`（新建）

```
┌─────────────────────────────────────────────────┐
│ ← 返回需求列表    需求标题    [批量导入选中]    │
├──────────────────┬──────────────────────────────┤
│  筛选：[P0▾]    │  用例详情                     │
│  [仅新增] [仅API]│                              │
│                  │  标题: xxx                    │
│  ┌────────────┐  │  优先级: P1                  │
│  │ ☑ TC-001   │  │  模块: 登录模块              │
│  │   登录验证  │  │  前置条件: ...               │
│  │   P0  [✓]  │  │  步骤:                       │
│  │            │  │   1. 打开登录页 → 页面显示    │
│  │ ☐ TC-002   │  │   2. 输入账号密码 → 接受输入  │
│  │   注册流程  │  │   3. 点击登录 → 跳转首页      │
│  │   P1       │  │                              │
│  │            │  │  [通过] [驳回] [编辑后导入]   │
│  │ ☑ TC-003   │  │                              │
│  │   密码找回  │  │                              │
│  │   P0  [✗]  │  │                              │
│  └────────────┘  │                              │
│  已选 2 条        │                              │
├──────────────────┴──────────────────────────────┤
│ 状态栏: 12 total · 5 approved · 3 rejected · 4 pending │
└─────────────────────────────────────────────────┘
```

#### 路由注册

```typescript
// router/index.tsx
{ path: '/requirement/:id/review', element: <ReviewPage /> }
```

### Task 2a 涉及文件

| 文件 | 操作 | 预估行数 |
|------|------|---------|
| `models/requirement_review.py` | 新建 | ~25 |
| `models/__init__.py` | 编辑 | +2 |
| `api/v1/requirement.py` | 编辑 | +80 (3 端点) |
| `services/requirement_service.py` | 编辑 | +60 |
| `frontend/src/pages/requirement/ReviewPage.tsx` | 新建 | ~300 |
| `frontend/src/api/requirement.ts` | 编辑 | +40 |
| `frontend/src/router/index.tsx` | 编辑 | +5 |
| `requirements.txt` | 编辑 | +1 (如有新依赖) |
| `alembic/versions/xxx_review.py` | 新建 | 迁移 |

---

## Task 2b: AI 智能分诊

### 后端

#### 新 Service：`services/triage_service.py`

```python
def triage_failed_cases(
    db: Session,
    plan_id: int,
    *,
    project_id: int = 0,
) -> dict:
    """分析计划中所有失败用例，返回分类结果。

    流程：
    1. 收集所有 status=fail 的 TestExecution 记录
    2. 提取每个失败用例的关键信息（assertion errors, error messages）
    3. 调用 LLM 分类：bug / flaky_env / case_defect / known_issue
    4. 返回结构化分类结果

    Returns:
        {
            "plan_id": 123,
            "total_failures": 5,
            "classified": [
                {
                    "execution_id": 456,
                    "case_title": "登录验证",
                    "category": "bug",        // bug | flaky_env | case_defect | known_issue
                    "confidence": 0.85,
                    "explanation": "断言 status_code 期望 200 实际 500，服务端内部错误",
                    "suggested_action": "检查后端 /api/login 接口日志",
                },
                ...
            ],
            "summary": {"bug": 2, "flaky_env": 1, "case_defect": 1, "known_issue": 1},
        }
    """
```

#### LLM Prompt 设计

```
System: 你是测试结果分析专家。根据执行失败的测试用例信息，将其归类为以下四类之一：
1. bug — 代码缺陷（如 500 错误、返回数据不正确）
2. flaky_env — 环境抖动（如超时、网络错误、服务暂时不可用）
3. case_defect — 用例本身有问题（如断言写错、期待值不合理）
4. known_issue — 已知缺陷（如错误信息匹配已有缺陷记录）

返回 JSON: {"classified": [{"execution_id": ..., "category": "...", "confidence": 0.0-1.0, "explanation": "...", "suggested_action": "..."}]}

User: 请分析以下 {N} 个失败用例:
1. 用例: {title} | 断言结果: {assertions} | 错误: {error} | HTTP状态: {status_code} | 响应: {body_preview}
...
```

#### 新端点（加到 `api/v1/test_plan.py`）

```python
@router.post("/{plan_id}/triage", response_model=R[dict])
def triage_plan_failures(plan_id, current, db):
    result = triage_service.triage_failed_cases(db, plan_id, project_id=current.project_id)
    return R.ok(result)
```

### 前端

#### 修改 `pages/testplan/PlanDetail.tsx`

添加「AI 分诊」Tab 或按钮：

```
执行结果页 → 新增 Tab: "AI 分诊"
  ┌────────────────────────────────────────────┐
  │ 🔴 Bug (2)                                 │
  │ ├─ TC-001 登录验证 → 500 错误               │
  │ │  置信度 85% · 建议检查 /api/login 日志     │
  │ │  [一键提缺陷]  [查看执行详情]              │
  │ └─ TC-005 支付回调 → 签名验证失败            │
  │    置信度 92% · 建议检查签名算法配置          │
  │    [一键提缺陷]  [查看执行详情]              │
  │                                             │
  │ 🟡 环境抖动 (1)                             │
  │ └─ TC-003 超时 → 网络超时                     │
  │    置信度 78% · 建议重试或检查网络             │
  │    [重试]                                    │
  │                                             │
  │ 🔵 用例缺陷 (1)                              │
  │ └─ TC-008 期待值不合理                        │
  │    置信度 90% · 建议修正断言                   │
  │    [编辑用例]                                 │
  └────────────────────────────────────────────┘
```

**「一键提缺陷」流程**：
1. 点击 → 弹出 `DefectDialog`（预填：标题=用例标题+"失败"，步骤=用例步骤，实际结果=执行结果）
2. 用户确认/修改 → 调用 `createDefect()` → 跳转缺陷详情

### Task 2b 涉及文件

| 文件 | 操作 | 预估行数 |
|------|------|---------|
| `services/triage_service.py` | 新建 | ~180 |
| `api/v1/test_plan.py` | 编辑 | +20 |
| `frontend/src/pages/testplan/PlanDetail.tsx` | 编辑 | +100 (新 Tab) |
| `frontend/src/components/TriagePanel.tsx` | 新建 | ~150 |
| `frontend/src/api/testplan.ts` | 编辑 | +10 |

---

## Task 2c: 需求输入简化

### 后端

#### 新端点：`POST /requirements/quick-create`

```python
class QuickCreateBody(BaseModel):
    description: str = Field(..., min_length=5, max_length=2000)  # 一句话/一段话
    template: str = "functional"   # functional / api / regression
    title: str = ""                # 可选，空则由 AI 生成

@router.post("/quick-create", response_model=R[dict])
def quick_create_requirement(body: QuickCreateBody, ...):
    """一句话创建需求 → AI 展开为结构化需求文档 → 返回文档 ID。

    流程：
    1. 根据 template 选择 prompt（功能/接口/回归）
    2. 调用 LLM 展开 description 为结构化 JSON（含模块、功能点、验收标准）
    3. 创建 RequirementDocument（file_type="ai_quick"）
    4. 返回文档 ID（前端可立即进入生成用例）
    """
```

#### Prompt 模板（按 template 类型）

```
# functional 模板
你是产品需求分析专家。根据一句话需求描述，生成结构化的功能需求文档。
输出 JSON: {"title": "需求标题", "modules": [{"name": "模块名", "function_points": ["功能点1", ...]}], "acceptance_criteria": ["验收标准1", ...], "scope": "影响范围描述"}

# api 模板
你是接口测试专家。根据描述，定义需要测试的 API 端点列表。
输出 JSON: {"title": "...", "apis": [{"method": "GET", "path": "/api/...", "description": "...", "expected_response": "..."}]}

# regression 模板
你是回归测试专家。根据新功能描述，生成回归测试范围。
输出 JSON: {"title": "...", "affected_modules": [...], "regression_scope": "...", "risk_areas": [...]}
```

### 前端

#### 修改 `pages/requirement/index.tsx`

上传区域上方添加「快速创建」卡片：

```
┌─────────────────────────────────────────────┐
│ ⚡ 快速创建                                  │
│                                             │
│ [模板选择: 功能需求 ▾ 接口需求 回归需求]     │
│                                             │
│ [                                            │
│  请输入需求描述，AI 将自动展开为结构化文档...  │
│  例：「用户登录功能需要支持手机号+验证码登录」 │
│ ]                                            │
│                                             │
│ [允许 AI 自动生成用例] [创建并生成]           │
└─────────────────────────────────────────────┘
```

**流程**：输入 → AI 展开 → 生成 RequirementDocument → 自动跳转生成用例 → 进入审查队列。

### 可配置蓝湖路径

在 `config.py` 中已存在 `lanhu_mcp_dir` 设置。本次添加 `lanhu_skills_dir`（与已有 `skill_dir` 区分）：

```python
# config.py 已有：
skill_dir: str = ""           # test-case-design skill 目录
lanhu_mcp_dir: str = ""       # lanhu-mcp module 目录

# 本次确认无需新增——lanhu 相关路径已通过 lanhu_mcp_dir 和 skill_dir 覆盖。
# 蓝湖输入不再硬编码路径，前端通过环境变量 LANHU_MCP_ENABLED 控制是否显示。
```

### Task 2c 涉及文件

| 文件 | 操作 | 预估行数 |
|------|------|---------|
| `services/requirement_service.py` | 编辑 | +50 (quick_create) |
| `api/v1/requirement.py` | 编辑 | +30 |
| `frontend/src/pages/requirement/index.tsx` | 编辑 | +80 (QuickCreateCard) |
| `frontend/src/components/QuickCreateCard.tsx` | 新建 | ~100 |

---

## UI 规范自查

| # | Red Flag | 处理 |
|---|----------|------|
| 1 | Badge 颜色 | 复用 AiResultModal 已有的四级梯度 |
| 2 | 深色模式 | 新组件全部使用 Tailwind 语义类 + `dark:` 变体 |
| 3 | 状态标签中文 | ✅ 全部已映射 |
| 4 | Error 态 | ReviewPage: AsyncState 四态; TriagePanel: 加载/空/错误 |
| 5 | 失败态≠加载动画 | ✅ triage 结果独立展示 |
| 6 | JSON 裸展示 | Triage 的 LLM 返回用 `JSON.stringify(x, null, 2)` + `<pre>` |
| 7 | 触控目标 | 操作按钮 ≥ `size="sm"` (36px) |
| 8 | 响应式 | ReviewPage: `grid-cols-1 lg:grid-cols-[280px_1fr]` + md 过渡 |

## Bug Guard 自查

| 铁律 | 处理 |
|------|------|
| B1(路由顺序) | 新路由 `/review` 是静态段，在 `/{id}` 之前注册: `/{id}/review` 在 `/{id}` 之后但 FastAPI 匹配更具体路径优先 ✅ |
| B3(迁移) | 新表 `requirement_review` → 先搜 `alembic/versions/` 确认无重复 |
| F2(N+1) | ReviewPage 一次性加载所有 cases + review states，不分页 |
| F4(error提取链) | 新增 API 函数含 `detail` 提取 |

---

## 关联

- [batch-22-platform-audit-pm-plan.md](batch-22-platform-audit-pm-plan.md) — PM Plan Slice 2 定义
- [batch-22-slice1-design-spec.md](batch-22-slice1-design-spec.md) — Slice 1 设计（依赖）
- `cameltv-ui-conventions` skill — 前端规范
- `cameltv-bug-guard` skill — 避坑铁律
