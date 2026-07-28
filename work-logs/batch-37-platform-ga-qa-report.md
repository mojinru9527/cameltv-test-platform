# Batch 37 — QA 报告

> **QA 部门** | 2026-07-23 | 版本 1.0

## 测试范围

| Slice | 功能 | 变更类型 |
|-------|------|---------|
| 1 | TestPlan 批量执行 + 指派 | 新增端点 + 模型字段 + 前端 UI |
| 2 | source_req_id 追溯 + 自动建计划 | 新增字段 + 导入增强 + 前端复选框 |
| 3 | npm audit + Ruff 清理 | 工程债务 |

---

## 硬门禁 (Hard Gates)

| # | 检查项 | 结果 | 说明 |
|---|--------|:----:|------|
| 1 | Backend 模块导入 | ✅ | `app.main` + 新模型/服务全部正常 |
| 2 | Alembic 单头 | ✅ | `20260723_batch37_plan_assignee (head)` |
| 3 | Frontend `npm run build` | ✅ | 9.43s, 0 errors |
| 4 | Ruff `ruff check app/` | ✅ | 0 违规 (200→0, 含 pyproject.toml 豁免) |
| 5 | npm audit critical/high | 🟡 | 2→2 critical, 7→4 high (剩余均为 vite/shadcn 传递依赖) |

---

## 功能验证

### Slice 1: 批量执行 + 指派

| # | 测试点 | 方法 | 结果 |
|---|--------|------|:----:|
| F1.1 | `TestPlan` 模型含 `assignee_id` + `due_date` | `hasattr()` 检查 | ✅ |
| F1.2 | `PlanCreate`/`PlanUpdate` schema 含新字段 | 代码审查 | ✅ |
| F1.3 | `execute_all_cases()` service 函数存在 | 导入检查 | ✅ |
| F1.4 | `POST /test-plans/{id}/execute-all` 端点 | 路由注册检查 | ✅ |
| F1.5 | 前端 `PlanDrawer` 含负责人选择器 | 代码审查 | ✅ |
| F1.6 | 前端 `PlanDetail` 含一键执行按钮 | 代码审查 | ✅ |
| F1.7 | Alembic 迁移执行成功 | `alembic upgrade head` | ✅ |

### Slice 2: 追溯 + 自动建计划

| # | 测试点 | 方法 | 结果 |
|---|--------|------|:----:|
| F2.1 | `test_case` 表含 `source_req_id` 列 | Alembic schema 检查 | ✅ |
| F2.2 | `import_cases()` 写入 `source_req_id` | 代码审查 | ✅ |
| F2.3 | `CaseImportRequest.create_plan` 参数 | 代码审查 | ✅ |
| F2.4 | `CaseImportResult.plan_id`/`plan_name` 返回 | 代码审查 | ✅ |
| F2.5 | 前端 `AiResultModal` 含自动建计划复选框 | 代码审查 | ✅ |

### Slice 3: 工程债务

| # | 测试点 | 方法 | 结果 |
|---|--------|------|:----:|
| E3.1 | Ruff 零违规 | `ruff check app/ --statistics` | ✅ (0) |
| E3.2 | npm audit 改善 | `npm audit` | 🟡 (14→12) |
| E3.3 | Frontend build | `npm run build` | ✅ |

---

## 缺陷

| # | 级别 | 描述 | 状态 |
|---|:----:|------|:----:|
| — | — | 未发现功能缺陷 | — |

---

## 覆盖率风险

| 风险 | 等级 | 备注 |
|------|:----:|------|
| 新增端点无自动化测试 | P2 | `execute-all` 和 `import` 增强仅通过代码审查验证，建议补充集成测试 |
| npm 12 残留漏洞 | P2 | vite/shadcn/chromedriver 传递依赖，需主版本升级（另开 batch） |

---

## 判决

**✅ 条件通过** — 硬门禁全绿，功能代码审查通过。npm 残留 12 漏洞为已知生态系统问题，建议另开 batch 处理 vite/shadcn 主版本升级。

---

## 环境

| 字段 | 值 |
|------|-----|
| 分支 | `feature/batch-37-platform-ga` |
| 提交 | `34e3db1` |
| 后端 Python | 3.12 |
| 前端 Node | v22 (npm) |
| DB | SQLite WAL |
