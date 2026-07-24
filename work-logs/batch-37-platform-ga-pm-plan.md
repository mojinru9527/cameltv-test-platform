# Batch 37 — 测试平台 GA 补缺 + 工程债务清理 PM Plan

> **PM 部门** | 2026-07-23 | 版本 2.0（精简版）

## 总览

| 字段 | 值 |
|------|-----|
| 关联 PRD | [batch-37-platform-ga-prd-summary.md](batch-37-platform-ga-prd-summary.md) |
| 总 Slice | 3 |
| 总 Task | 12 |
| 预估工时 | 3–4h |

---

## Slice 1: TestPlan 批量执行 + 执行指派 🎯 P0

> 执行闭环两个最关键的缺口。纯后端改动，模型 → 服务 → API → Schema。

### Task 1.1 — TestPlan 模型添加 assignee_id + due_date

| 字段 | 值 |
|------|-----|
| 描述 | `test_plan` 表新增 `assignee_id` (FK→user, nullable) 和 `due_date` (datetime, nullable) |
| 验收标准 | 模型字段添加 + Alembic 迁移脚本生成 + `PlanOut.plan_case_to_dict` 返回新字段 |
| 涉及文件 | `backend/app/models/test_plan.py`, Alembic 迁移 |
| 参考 | `TestPlanCase.executor_id` 已有类似模式 |

### Task 1.2 — Schema + Service 更新计划指派

| 字段 | 值 |
|------|-----|
| 描述 | `PlanCreate`/`PlanUpdate`/`PlanOut` 添加 `assignee_id` + `due_date`；`_plan_to_dict` 返回新字段；列表/详情 API 内联 `assignee_name` |
| 验收标准 | 创建/更新计划可传 assignee_id + due_date；查询返回 assignee_name |
| 涉及文件 | `backend/app/schemas/test_plan.py`, `backend/app/services/test_plan_service.py` |
| 参考 | `batch_user_names` 已有批量用户查询工具 |

### Task 1.3 — 批量执行 Service + API 端点

| 字段 | 值 |
|------|-----|
| 描述 | `test_plan_service.py` 新增 `execute_all_cases()` 函数；API 新增 `POST /{plan_id}/execute-all` |
| 验收标准 | API 用例自动执行；人工/UI 用例标记 skip；返回汇总 JSON |
| 涉及文件 | `backend/app/services/test_plan_service.py`, `backend/app/api/v1/test_plan.py` |
| 参考 | `auto_execute_api_cases()` (已有) 的逻辑可直接复用 |

### Task 1.4 — 前端：计划表单 + 详情增加指派字段

| 字段 | 值 |
|------|-----|
| 描述 | 计划创建/编辑表单增加「负责人」选择器和「截止日期」日期选择器；计划详情显示负责人 |
| 验收标准 | 可保存/编辑指派信息；详情页正确显示 |
| 涉及文件 | `frontend/src/pages/testplan/` |
| 参考 | 用例的 executor 字段模式 |

---

## Slice 2: 追溯增强 + 自动建计划 🎯 P1/P2

> 增强用例可追溯性 + 导入体验优化。后端为主，前端一个复选框。

### Task 2.1 — TestCase 模型添加 source_req_id

| 字段 | 值 |
|------|-----|
| 描述 | `test_case` 表新增 `source_req_id: str` 字段（存储 REQ-xxx 标识） + Alembic 迁移 |
| 验收标准 | 字段添加 + 迁移可执行 |
| 涉及文件 | `backend/app/models/test_case.py`, Alembic 迁移 |

### Task 2.2 — 导入用例时写入 source_req_id + Schema 露出

| 字段 | 值 |
|------|-----|
| 描述 | `import_cases()` 从 AI 生成的用例数据中提取 `req_id` 写入 `source_req_id`；`PlanCaseOut` 返回 `source_req_id` |
| 验收标准 | 从需求导入的用例 `source_req_id` 非空；API 返回值包含此字段 |
| 涉及文件 | `backend/app/services/requirement_service.py`, `backend/app/schemas/test_plan.py`, `backend/app/services/test_case_service.py` |
| 参考 | `source_doc_id` 的写入模式 |

### Task 2.3 — 导入后自动创建测试计划

| 字段 | 值 |
|------|-----|
| 描述 | `POST /requirements/{doc_id}/import` 新增 `create_plan: bool` 参数；为 True 时自动创建 TestPlan 并关联导入的用例 |
| 验收标准 | 导入+建计划原子操作；返回 plan_id + plan_name |
| 涉及文件 | `backend/app/api/v1/requirement.py`, `backend/app/services/requirement_service.py`, `backend/app/schemas/requirement.py` |

### Task 2.4 — 前端：导入弹窗 + 追溯矩阵展示

| 字段 | 值 |
|------|-----|
| 描述 | 导入弹窗增加「同时创建测试计划」复选框；用例详情显示 `source_req_id` 标签 |
| 验收标准 | 勾选后导入返回计划链接；用例详情可看到关联的功能点 ID |
| 涉及文件 | `frontend/src/pages/requirement/`, `frontend/src/pages/testcase/` |

---

## Slice 3: 工程债务清理 🎯 P1/P2

> npm 安全漏洞 + Python Ruff 违规。纯工具执行，无业务代码改动。

### Task 3.1 — npm audit 修复

| 字段 | 值 |
|------|-----|
| 描述 | 执行 `npm audit fix` 修复可自动修复的漏洞；手动升级剩余包 |
| 验收标准 | `npm audit` 0 critical + 0 high；`npm run typecheck && npm run build` 通过 |
| 涉及文件 | `frontend/package.json`, `frontend/package-lock.json` |

### Task 3.2 — Ruff 违规清理

| 字段 | 值 |
|------|-----|
| 描述 | `ruff check app/ --fix` 自动修复；手动处理剩余语义违规 |
| 验收标准 | `ruff check app/` 0 违规 |
| 涉及文件 | `backend/app/**/*.py` |

### Task 3.3 — CI 硬门禁验证

| 字段 | 值 |
|------|-----|
| 描述 | 运行前后端硬门禁：`npm run typecheck && npm run build` + `ruff check app/` + 模块测试 |
| 验收标准 | 所有检查通过 |
| 涉及文件 | 无 |

### Task 3.4 — 完整功能回归

| 字段 | 值 |
|------|-----|
| 描述 | 验证所有 4 个新功能端到端可用 |
| 验收标准 | 批量执行返回正确结果、指派信息正确保存/读取、source_req_id 正确写入、自动建计划正常 |
| 涉及文件 | 测试脚本 |

---

## 依赖关系

```
Slice 1 (Task 1.1 → 1.2 → 1.3, Task 1.4)  并行于 Slice 2
Slice 2 (Task 2.1 → 2.2 → 2.3, Task 2.4)  并行于 Slice 1
Slice 3 (Task 3.1 + 3.2 → 3.3 → 3.4)      依赖 Slice 1+2 完成后执行
```

---

## 涉及文件汇总

### Backend (12 文件)
| 文件 | Slice | 变更类型 |
|------|-------|---------|
| `app/models/test_plan.py` | 1 | 模型 +2 字段 |
| `app/models/test_case.py` | 2 | 模型 +1 字段 |
| `app/schemas/test_plan.py` | 1 | Schema 更新 |
| `app/schemas/requirement.py` | 2 | Schema 更新 |
| `app/services/test_plan_service.py` | 1 | 新增函数 + 更新返回值 |
| `app/services/requirement_service.py` | 2 | import_cases 增强 |
| `app/services/test_case_service.py` | 2 | create_case 增强 |
| `app/api/v1/test_plan.py` | 1 | 新增端点 |
| `app/api/v1/requirement.py` | 2 | import 端点增强 |
| Alembic migration | 1+2 | 两份迁移脚本 |

### Frontend (3 模块)
| 路径 | Slice | 变更类型 |
|------|-------|---------|
| `pages/testplan/` | 1 | 指派字段 |
| `pages/requirement/` | 2 | 导入复选框 |
| `pages/testcase/` | 2 | source_req_id 展示 |
| `package.json` | 3 | 依赖升级 |

### 工程债务
| 范围 | Slice | 操作 |
|------|-------|------|
| `frontend/` npm | 3 | audit fix |
| `backend/app/` Ruff | 3 | lint fix |
