# Test Case Service Follow-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成用例列表字段顺序、分步内容、独立筛选、分类层级管理与本地分类接口可用性修复。

**Architecture:** 列表展示逻辑抽到纯格式化函数，把前置条件、步骤描述和逐步预期统一转换为中文序号列表。分类管理继续使用域/模块 API，但前端增加运行时 ID 防护并改为可展开树；后端隐藏保留域“接口测试”，搜索补齐域字段，本地数据库升级后重启旧 API 进程。

**Tech Stack:** FastAPI、SQLAlchemy、Alembic、pytest、React 18、TypeScript、Radix/shadcn UI、Vitest、Playwright

---

### Task 1: 列表格式与字段顺序

**Files:**
- Create: `frontend/src/pages/testcase/caseListFormatters.ts`
- Create: `frontend/src/pages/testcase/__tests__/caseListFormatters.test.ts`
- Modify: `frontend/src/pages/testcase/index.tsx`

- [x] **Step 1: 编写失败的格式化测试**

覆盖纯文本换行、JSON 数组、`steps=[{desc, expected}]`，期望返回：

```ts
['1、打开登录页', '2、输入账号密码']
['1、页面打开成功', '2、登录成功']
```

- [x] **Step 2: 实现格式化函数**

新增 `formatNumberedText`、`formatStepActions`、`formatStepExpectations` 和 `sortCasesNewestFirst`；无法解析的单行文本仍显示为 `1、原内容`。

- [x] **Step 3: 调整表头与单元格**

隐藏编号列，字段顺序改为“模块名称、用例标题、前置条件、操作步骤、预期结果”；前置条件和步骤列渲染多行编号，预期结果优先取 `steps[].expected`。页面数据按 `created_at DESC, id DESC` 再做一次稳定排序。

### Task 2: 独立筛选与模糊搜索

**Files:**
- Modify: `frontend/src/pages/testcase/index.tsx`
- Modify: `backend/app/services/test_case_service.py`
- Modify: `backend/tests/test_testcase.py`

- [x] **Step 1: 补充域关键字测试**

调用：

```python
client.get('/api/v1/test-cases', params={'keyword': '运营后台'}, headers=auth_headers)
```

断言只返回域名称包含“运营后台”的有效用例。

- [x] **Step 2: 后端补齐搜索字段**

关键字条件包含 `title/domain/module/preconditions/steps/expected_result`，保留编号兼容搜索但不再展示编号。

- [x] **Step 3: 前端允许模块单独筛选**

域为 `all` 时模块选项为全部域模块名称的去重集合，模块下拉不禁用；指定域时只显示该域模块。域、模块、优先级默认值保持 `all`，任意一项均可独立发起查询。

- [x] **Step 4: 修正文案**

搜索框 placeholder 改为 `搜索标题/关键字`。

### Task 3: 分类树与保留域隐藏

**Files:**
- Modify: `frontend/src/pages/testcase/CategoryManagerDialog.tsx`
- Modify: `frontend/src/api/testcase.ts`
- Modify: `backend/app/services/test_case_service.py`
- Modify: `backend/alembic/versions/20260715_test_case_categories.py`
- Modify: `backend/tests/test_testcase.py`

- [x] **Step 1: 增加分类 ID 防护**

分类类型允许运行时兼容旧接口的缺失 ID；`createModule/deleteDomain/deleteModule` 调用前检查 `Number.isInteger(id)`，无 ID 时提示“分类接口尚未更新”，不得发出含 `undefined` 的请求。

- [x] **Step 2: 分类管理改为两级树**

每个域为第一级，点击展开其模块；域行可直接删除，展开后的模块行可删除模块。新增域和模块区保留。

- [x] **Step 3: 隐藏接口测试域**

域树查询排除 `接口测试`，禁止在用例分类中重新新增该域；迁移回填时将该分类标记为逻辑删除，但不删除已有接口用例数据。

- [x] **Step 4: 验证分类级联删除**

后端测试断言域/模块删除仍只修改 `is_deleted`，接口测试域不会出现在 `/test-cases/domains`。

### Task 4: 本地接口升级与完整回归

**Files:**
- Test: `backend/tests/test_testcase.py`
- Test: `frontend/src/pages/testcase/__tests__/caseListFormatters.test.ts`

- [x] **Step 1: 运行目标测试**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_testcase.py -q`

Expected: PASS。

Run: `cd frontend && npm test -- --run src/pages/testcase/__tests__`

Expected: PASS。

- [x] **Step 2: 运行类型检查与构建**

Run: `cd frontend && npm run typecheck && npm run build`

Expected: PASS。

- [x] **Step 3: 升级并重启本地后端**

Run: `cd backend && .venv/Scripts/alembic.exe upgrade head`

Expected: 当前数据库升级到 `20260715_test_case_categories`。

重启 8000 服务后，`/openapi.json` 必须包含 POST/DELETE 分类路由，`POST /api/v1/test-cases/domains` 不再返回 405。

- [x] **Step 4: 真实浏览器验收**

验证列表无编号列、模块列在标题前、三组分步内容、模块可独立筛选、分类两级展开删除、搜索提示正确，并保存验收截图。

- [x] **Step 5: 最终检查**

Run: `git diff --check`

Expected: 无空白错误，且原有无关工作区改动保持不变。
