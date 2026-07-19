# API Asset Hierarchy And Debug Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将接口测试默认入口改为接口资产，提供服务→模块→路径三级资产、跨字段模糊搜索、Swagger 文档导入和可切换环境的完整 URL 快速调试。

**Architecture:** 接口资产继续保留现有 `ApiService + ApiEndpoint` 模型；前端用确定性路由拆分函数把完整路径分为模块路径和接口路径，不做破坏性表结构迁移。接口查询联表服务支持三字段搜索；快速调试接收带服务名的资产快照，使用环境 base URL 拼接服务、模块、路径，环境切换只重算 base URL 部分。Swagger 导入在直接 JSON/YAML 失败后发现 Knife4j/Swagger UI 的规范地址。

**Tech Stack:** FastAPI、httpx、SQLAlchemy、pytest、React、TypeScript、Radix Collapsible、Vitest、Playwright

**Status:** Complete — full test suites, production build, migration audit, and browser acceptance passed on 2026-07-16.

---

### Task 1: 资产路由拆分与 URL 拼接

**Files:**
- Create: `frontend/src/pages/apitest/components/assetRoute.ts`
- Create: `frontend/src/pages/apitest/components/__tests__/assetRoute.test.ts`
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: 编写失败测试**

示例断言：

```ts
expect(splitAssetRoute('camel-service', '', '/ee/search/synonyms/cou')).toEqual({
  modulePath: '/ee/search', endpointPath: '/synonyms/cou',
})
expect(composeAssetUrl('http://camel-api-gateway05.svc.elelive.cn/', 'camel-service', '/ee/search', '/synonyms/cou'))
  .toBe('http://camel-api-gateway05.svc.elelive.cn/camel-service/ee/search/synonyms/cou')
```

- [ ] **Step 2: 实现纯函数**

实现 `splitAssetRoute`、`composeAssetUrl`、`displayAssetSegment`，去除重复服务前缀、规范斜杠，并将外显名称中的 `/` 替换为 `-`。

### Task 2: 服务/模块/路径模糊搜索

**Files:**
- Modify: `backend/app/api/v1/apitest.py`
- Modify: `backend/tests/test_apitest_assets.py`

- [ ] **Step 1: 编写失败 API 测试**

分别用服务名子串、模块名子串和路径子串请求 `/api/v1/apitest/endpoints?keyword=...`，每次只返回命中的资产。

- [ ] **Step 2: 联表搜索**

查询 `join(ApiService, ApiService.id == ApiEndpoint.service_id)`，keyword 条件 OR 覆盖 `ApiService.name/display_name`、`ApiEndpoint.module`、`ApiEndpoint.path`。

- [ ] **Step 3: 运行后端资产测试**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_apitest_assets.py -q`

Expected: PASS。

### Task 3: 接口资产三级展示

**Files:**
- Modify: `frontend/src/pages/apitest/components/AssetTab.tsx`

- [ ] **Step 1: 搜索改为显式触发**

区分输入值和已提交 keyword，增加“搜索”按钮及 Enter 搜索；placeholder 为“搜索服务名/模块名/路径”。

- [ ] **Step 2: 构造三级树**

按服务 ID 分组为一级、按 `modulePath` 分组为二级、接口为三级；服务和模块支持展开，模块和路径外显通过 `displayAssetSegment` 转成连字符名称。

- [ ] **Step 3: 接口备注单独显示**

路径行使用固定列布局：方法、接口路径名、接口备注、操作；备注取 `summary || description || '-'`，不再与路径混排。

### Task 4: 默认资产页和快速调试预填

**Files:**
- Modify: `frontend/src/pages/apitest/index.tsx`
- Modify: `frontend/src/pages/apitest/components/DebugTab.tsx`

- [ ] **Step 1: 默认资产 Tab**

`activeTab` 默认值改成 `assets`；直接点击快速调试时清空资产快照，从资产调试按钮进入时传入 endpoint 并切换到 quick。

- [ ] **Step 2: 默认测试5环境和完整 URL**

资产进入时优先匹配 `base_url` 含 `camel-api-gateway05.svc.elelive.cn` 或名称含“测试5”的环境，并用 `composeAssetUrl` 生成完整 URL；切换环境只替换 base URL。

- [ ] **Step 3: 预填请求参数格式**

解析 `request_schema.query/path/header/body`：query/path 参数全部生成表格行，header 生成 Header 行，body properties 用 `buildSampleBody` 生成示例 JSON。直接进入 quick 时 URL、参数、body、环境保持空。

### Task 5: Swagger/Knife4j 文档链接识别

**Files:**
- Modify: `backend/app/services/openapi_import_service.py`
- Modify: `backend/app/api/v1/apitest.py`
- Modify: `backend/tests/test_openapi_import_knife4j.py`
- Modify: `frontend/src/pages/apitest/components/ImportDialog.tsx`

- [ ] **Step 1: 编写文档发现失败测试**

模拟 `doc.html` 返回 HTML、`swagger-resources` 返回规范 location、location 返回 Swagger JSON，断言最终解析成功。

- [ ] **Step 2: 实现规范发现**

新增 `load_openapi_spec(url)`：先尝试当前 URL；若不是 OpenAPI，则访问同目录 `swagger-resources` 并跟随 location，同时回退 `v3/api-docs`、`v2/api-docs`。

- [ ] **Step 3: 简化导入 UI**

默认展示“服务名称”和“Swagger 文档链接”，保留文本导入作为高级方式；链接可以是 JSON/YAML 地址或 `doc.html` 页面。

### Task 6: 全量验收

- [ ] **Step 1: 运行后端全量测试**

Run: `cd backend && .venv/Scripts/python.exe -m pytest -q`

- [ ] **Step 2: 运行前端全量测试和构建**

Run: `cd frontend && npm test && npm run build`

- [ ] **Step 3: Playwright 验收**

验证默认资产 Tab、三级树、备注列、服务/模块/路径搜索、资产跳转快速调试、测试5默认环境、环境切换 URL 仅替换 host，以及直接进入快速调试为空。
