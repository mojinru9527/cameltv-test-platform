# Test Case Cleanup And Row Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用例服务只展示有效功能用例，并以独立等级列和单行省略布局呈现，同时移除新建弹窗中的关联引用。

**Architecture:** 新迁移负责一次性补齐历史数据：删除分类下仍存活的用例和旧接口用例全部标记 `is_deleted=true`。查询层在未指定 `case_type` 时排除 API 用例，显式 `case_type=api` 仍供接口测试模块使用；前端只改变展示和表单字段，不改变已有步骤数据结构。

**Tech Stack:** FastAPI、SQLAlchemy、Alembic、pytest、React、TypeScript、Vitest

**Status:** Complete — migration applied, backend/frontend tests passed, and Playwright acceptance passed on 2026-07-16.

---

### Task 1: 历史逻辑删除补偿

**Files:**
- Create: `backend/alembic/versions/20260716_reconcile_deleted_test_cases.py`
- Modify: `backend/app/services/test_case_service.py`
- Modify: `backend/tests/test_testcase.py`

- [ ] **Step 1: 编写失败测试**

新增测试覆盖：默认用例列表排除 `case_type=api`；显式 `case_type=api` 仍能返回未删除的新接口用例；域和模块删除后数据库中的关联用例 `is_deleted` 为真且列表不可见。

- [ ] **Step 2: 收紧默认查询**

在 `list_cases` 中加入：

```python
if case_type:
    stmt = stmt.where(TestCase.case_type == case_type)
else:
    stmt = stmt.where(TestCase.case_type != "api")
```

计数查询保持相同条件。

- [ ] **Step 3: 新增数据补偿迁移**

迁移执行一条幂等 `UPDATE test_case`，将以下数据逻辑删除：旧 `case_type='api'`/`domain='接口测试'` 用例、已删除域关联用例、已删除模块关联用例。

- [ ] **Step 4: 运行目标测试**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_testcase.py -q`

Expected: PASS。

### Task 2: 列表和新建弹窗精简

**Files:**
- Modify: `frontend/src/pages/testcase/index.tsx`
- Modify: `frontend/src/pages/testcase/CaseDrawer.tsx`
- Modify: `frontend/src/pages/testcase/__tests__/CaseDrawer.test.tsx`

- [ ] **Step 1: 增加弹窗失败测试**

断言新建用例弹窗不存在“关联引用”。

- [ ] **Step 2: 独立展示用例等级**

表头在“模块名称”和“用例标题”之间新增“用例等级”，P0/P1/P2/P3 Badge 从标题单元格移入独立单元格。

- [ ] **Step 3: 每条用例只占一行**

前置条件、操作步骤、预期结果把编号数组用空格连接，单元格统一 `truncate whitespace-nowrap`，完整内容放入 `title`。

- [ ] **Step 4: 移除关联引用**

从表单 schema、默认值和 JSX 中删除 `api_spec_ref`，后端兼容字段保留。

- [ ] **Step 5: 运行前端测试和构建**

Run: `cd frontend && npm test && npm run build`

Expected: PASS。
