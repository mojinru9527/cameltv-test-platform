# Test Case Service Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化用例服务的分类管理、逻辑删除、搜索排序、列表字段、分页与新增用例体验，并确保新增用例只能选择已维护的域和模块。

**Architecture:** 新增项目级 `TestCaseDomain` 和 `TestCaseModule` 分类表，保留 `TestCase.domain/module` 文本字段以兼容现有调用；分类删除和用例删除统一写入 `is_deleted` 标记。`/test-cases/domains` 返回分类及有效用例数，分类写接口负责新增、恢复和级联逻辑删除；前端以独立分类管理弹窗维护分类，列表树只展示有用例的模块，表单下拉仍展示全部有效模块。

**Tech Stack:** FastAPI、Pydantic v2、SQLAlchemy 2.0、Alembic、pytest、React 18、TypeScript、Radix/shadcn UI、React Hook Form、Zod、Vitest

---

### Task 1: 分类与逻辑删除数据模型

**Files:**
- Create: `backend/app/models/test_case_category.py`
- Modify: `backend/app/models/test_case.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/20260715_test_case_categories.py`

- [x] **Step 1: 编写迁移结构检查测试**

在 `backend/tests/test_testcase.py` 中新增断言，确认 `TestCase`、域和模块对象均有 `is_deleted` 字段，并且分类名称受项目范围约束。

- [x] **Step 2: 运行测试并确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_testcase.py -q`

Expected: FAIL，提示分类模型或 `is_deleted` 不存在。

- [x] **Step 3: 实现模型与迁移**

新增 `TestCaseDomain(project_id, name, is_deleted)`、`TestCaseModule(project_id, domain_id, name, is_deleted)`，并为 `TestCase` 增加：

```python
is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
```

迁移创建两张分类表，为 `test_case` 增加逻辑删除列，并通过 `SELECT DISTINCT project_id, domain, module FROM test_case` 回填已有分类。

- [x] **Step 4: 运行模型和迁移测试**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_testcase.py -q`

Expected: 新增模型测试 PASS。

### Task 2: 分类 API、级联逻辑删除与列表查询

**Files:**
- Modify: `backend/app/schemas/test_case.py`
- Modify: `backend/app/services/test_case_service.py`
- Modify: `backend/app/api/v1/test_case.py`
- Modify: `backend/tests/test_testcase.py`

- [x] **Step 1: 编写失败的 API 测试**

覆盖以下行为：新增域、域内新增模块、重复新增返回业务错误；删除模块后模块和关联用例不可见但数据库记录仍存在；删除域后其模块和全部关联用例均被标记；无效模块不能通过手工新增接口创建用例；列表按 `created_at DESC, id DESC` 返回；关键字可匹配标题、编号、模块、前置条件、步骤和预期结果。

- [x] **Step 2: 运行用例并确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_testcase.py -q`

Expected: FAIL，分类写接口返回 404/405，逻辑删除和新搜索断言不满足。

- [x] **Step 3: 实现分类服务与接口**

提供以下接口：

```text
GET    /api/v1/test-cases/domains
POST   /api/v1/test-cases/domains
DELETE /api/v1/test-cases/domains/{domain_id}
POST   /api/v1/test-cases/domains/{domain_id}/modules
DELETE /api/v1/test-cases/domains/{domain_id}/modules/{module_id}
```

分类新增在同项目内恢复已删除同名记录；模块/域删除使用单事务更新分类和关联 `TestCase.is_deleted`。所有用例读取、统计、域树和删除操作过滤 `is_deleted=False`，单条和批量删除改为更新标记。

- [x] **Step 4: 实现查询与创建约束**

列表排序使用：

```python
stmt.order_by(TestCase.created_at.desc(), TestCase.id.desc())
```

关键字条件覆盖 `title/case_id/module/preconditions/steps/expected_result`；手工创建时校验域和模块属于当前项目且均有效；`module`、`steps`、`expected_result` 在创建 Schema 中必填，状态默认 `draft`。

- [x] **Step 5: 运行后端目标测试**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_testcase.py -q`

Expected: PASS。

### Task 3: 分类管理界面与筛选体验

**Files:**
- Create: `frontend/src/pages/testcase/CategoryManagerDialog.tsx`
- Modify: `frontend/src/pages/testcase/index.tsx`
- Modify: `frontend/src/api/testcase.ts`

- [x] **Step 1: 增加分类 API 客户端**

新增 `createDomain`、`deleteDomain`、`createModule`、`deleteModule`，并定义包含 `id/domain/modules/count` 的分类类型。

- [x] **Step 2: 实现分类管理弹窗**

弹窗提供“新增域”和“新增模块”输入区；模块必须选择已有域。分类列表展示全部有效模块，删除前明确提示将同时逻辑删除关联用例，成功后刷新分类与列表。

- [x] **Step 3: 调整左侧树和筛选**

左侧树过滤 `count === 0` 的模块；域、模块、优先级均使用显式值 `all` 的“全部”选项，并在请求时把 `all` 转为空筛选；域变化时清空不再有效的模块筛选，搜索按钮始终从第 1 页查询。

- [x] **Step 4: 移除下载入口并更新表格**

移除用例服务页 Excel/Xmind 下载按钮和相关处理函数，保留 Excel 导入；移除 API 列，新增前置条件、操作步骤、预期结果列，模块列标题使用“模块名称”。

### Task 4: 新增用例弹窗与分页

**Files:**
- Modify: `frontend/src/pages/testcase/CaseDrawer.tsx`
- Modify: `frontend/src/pages/testcase/index.tsx`
- Modify: `frontend/src/components/Pagination.tsx`

- [x] **Step 1: 调整新增表单字段与校验**

移除用例编号和标签输入；状态默认 `draft`；域、模块、测试步骤和预期结果必填。域变化时清空模块，模块选项只来自分类接口。

- [x] **Step 2: 修复弹窗下拉定位和遮挡**

弹窗内所有 `SelectContent` 使用 `position="popper"`、`align="start"` 和高层级样式，触发器使用 `w-full`，避免下拉与字段错位或被滚动区域遮挡。

- [x] **Step 3: 增强分页**

为 `Pagination` 增加可选 `pageSize/pageSizeOptions/onPageSizeChange` 和页码输入跳转；用例页开放 20、50、100 条每页，改变条数时返回第 1 页。

- [x] **Step 4: 保证新增后最新用例置顶**

保存回调区分新增与编辑；新增成功后切换至第 1 页并刷新，配合后端倒序让新用例显示在首行。

### Task 5: 回归验证

**Files:**
- Test: `backend/tests/test_testcase.py`
- Test: `frontend/src/pages/testcase/__tests__/CaseDrawer.test.tsx`

- [x] **Step 1: 补充前端表单测试**

验证默认草稿、模块/步骤/预期结果必填，以及编号/标签输入不再渲染。

- [x] **Step 2: 运行后端测试**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_testcase.py -q`

Expected: PASS。

- [x] **Step 3: 运行前端测试和类型检查**

Run: `cd frontend && npm test -- --run`

Expected: PASS。

Run: `cd frontend && npm run typecheck`

Expected: PASS。

- [x] **Step 4: 构建前端**

Run: `cd frontend && npm run build`

Expected: PASS，并生成生产构建。

- [x] **Step 5: 检查迁移单头和变更范围**

Run: `cd backend && .venv/Scripts/alembic.exe heads`

Expected: 仅 `20260715_test_case_categories (head)`。

Run: `git diff --check`

Expected: 无空白错误。
