# Batch 244 — PM Plan

> **PM (🟨)** | Date: 2026-09-14

## 规格摘要

**原始需求**：执行 C243-2，让 OpenAPI 生成类型成为前端契约来源，减少核心 API `any`，修复 OpenAPI 导入/计划执行/dashboard 的 N+1，并统一缓存失效。  
**目标时间**：一个完整 Agent Team 批次。

## 开发任务

### [ ] Task 1: OpenAPI contract 类型入口
**描述**：新增 `src/api/contract.ts`，统一导出生成 schema、请求/响应和领域类型；核心 API 模块改用生成类型，不再重复手写同名字段。
**验收标准**：
- `api.d.ts` 被实际 import。
- 至少 auth、testcase、testplan、defect、report 的核心返回类型来自生成 schema 或该入口。
- typecheck 通过。
**涉及文件**：
- `test-platform-v2/frontend/src/api/contract.ts`（新增）
- `test-platform-v2/frontend/src/api/*.ts`

### [ ] Task 2: 清除生产 API 层 `any`
**描述**：将生产 `src/api/**/*.ts` 中的 `any` 改为 `unknown`、`Record<string, unknown>` 或明确 DTO；为 API 目录增加 ESLint override。
**验收标准**：
- 生产 API 目录 `rg '\bany\b'` 为 0。
- `npm run lint` 通过。
- 不使用 `as any` 掩盖类型错误。
**涉及文件**：
- `test-platform-v2/frontend/src/api/*.ts`
- `test-platform-v2/frontend/eslint.config.js`

### [ ] Task 3: 去除核心 N+1
**描述**：
- OpenAPI confirm：按 `(method,path)` 预取现有 endpoint，循环内只做内存 upsert。
- 计划执行准备/自动执行：批量 `IN` 查 TestCase，构建 map。
- Dashboard：批量取 execution/defect 聚合，去掉项目×日循环查询。
**验收标准**：
- 新增查询计数测试证明查询数不随条数线性增长。
- 导入、计划、dashboard 相关既有测试通过。
**涉及文件**：
- `test-platform-v2/backend/app/services/openapi_import_service.py`
- `test-platform-v2/backend/app/services/test_plan_service.py`
- `test-platform-v2/backend/app/services/dashboard_service.py`
- 对应 pytest

### [ ] Task 4: 缓存失效和 query key 收敛
**描述**：为 `cachedGet` 建立统一 key/prefix invalidation helper，所有 environment/domain/stats/menu 写路径在成功 mutation 后失效相关缓存；补测试。
**验收标准**：
- mutation 后读取触发新请求。
- 项目切换仍按 projectId 隔离。
- 现有 client-cache 测试不回归。
**涉及文件**：
- `test-platform-v2/frontend/src/api/client.ts`
- `test-platform-v2/frontend/src/api/environment.ts`
- `test-platform-v2/frontend/src/api/testcase.ts`
- `test-platform-v2/frontend/src/api/__tests__/*`

## 质量要求

- [ ] 前端 typecheck/lint/build
- [ ] 前端 Vitest
- [ ] 后端 ruff F821 / 相关 pytest
- [ ] 查询计数断言
- [ ] 不改变 UI 视觉和业务 API
