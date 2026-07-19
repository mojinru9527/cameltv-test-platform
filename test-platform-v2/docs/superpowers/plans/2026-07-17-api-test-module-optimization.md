# API Test Module Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将接口资产、快速调试和接口用例调整为稳定的一一对应层级，并让自动生成覆盖每个请求参数的空值、类型、边界和异常场景。

**Architecture:** 前端继续使用项目现有的 React、Radix Tabs/Collapsible 和 Tailwind 组件：服务作为 Tab，模块和接口用例组作为默认关闭的 Collapsible。快速调试把环境服务器地址与服务/模块/接口路径分离，只在发送时调用 `composeAssetUrl` 组装完整地址。后端生成器以参数为最小覆盖单元，实际写入 Query、Path、Header 和 Body 的异常值，并把安全上限提高到足以覆盖常见多参数接口。

**Tech Stack:** React 18、TypeScript、Radix UI、Tailwind CSS、Vitest、Testing Library、FastAPI、Python、pytest

**Status:** Complete — 2026-07-17 已通过前端组件测试、生产构建、后端 66 项回归和 Playwright 页面验收。

---

### Task 1: 接口资产改为服务 Tab 与默认收起模块

**Files:**
- Modify: `frontend/src/pages/apitest/components/AssetTab.tsx`
- Create: `frontend/src/pages/apitest/components/AssetTab.test.tsx`

- [ ] **Step 1: 写失败测试**

```tsx
render(<AssetTab onOpenImport={vi.fn()} refreshKey={0} />)
await screen.findByRole('tab', { name: /service-a/i })
expect(screen.queryByText('/users/list')).not.toBeInTheDocument()
await user.click(screen.getByRole('button', { name: /用户模块/ }))
expect(screen.getByText('/users/list')).toBeInTheDocument()
```

- [ ] **Step 2: 验证测试先失败**

Run: `npm test -- --run src/pages/apitest/components/AssetTab.test.tsx`
Expected: FAIL，因为现有服务是折叠项且模块默认展开。

- [ ] **Step 3: 实现服务 Tab 与模块集合**

```tsx
<Tabs value={String(selectedService)} onValueChange={(value) => setSelectedService(Number(value))}>
  <TabsList className="h-auto max-w-full justify-start overflow-x-auto">
    {services.map((service) => (
      <TabsTrigger key={service.id} value={String(service.id)}>
        {service.display_name || service.name}
      </TabsTrigger>
    ))}
  </TabsList>
  {services.map((service) => (
    <TabsContent key={service.id} value={String(service.id)}>
      {modules.map((module) => <Collapsible key={module.modulePath}>{/* 接口集合 */}</Collapsible>)}
    </TabsContent>
  ))}
</Tabs>
```

- [ ] **Step 4: 验证服务、模块、接口一一对应**

Run: `npm test -- --run src/pages/apitest/components/AssetTab.test.tsx`
Expected: PASS，切换服务只显示该服务模块，模块初始关闭。

### Task 2: 快速调试拆分地址并把响应移到底部

**Files:**
- Modify: `frontend/src/pages/apitest/components/DebugTab.tsx`
- Modify: `frontend/src/pages/apitest/components/DebugTab.test.tsx`
- Test: `frontend/src/pages/apitest/components/assetRoute.test.ts`

- [ ] **Step 1: 写失败测试**

```tsx
expect(screen.getByLabelText('服务器地址')).toHaveValue('http://camel-api-gateway05.svc.elelive.cn/')
expect(screen.getByLabelText('服务名')).toHaveValue('camel-service')
expect(screen.getByLabelText('模块名')).toHaveValue('/ee/search')
expect(screen.getByLabelText('接口路径')).toHaveValue('/synonyms/cou')
expect(screen.getByText('响应结果')).toBeInTheDocument()
```

- [ ] **Step 2: 验证测试先失败**

Run: `npm test -- --run src/pages/apitest/components/DebugTab.test.tsx`
Expected: FAIL，因为当前只有完整 URL 输入框且响应位于右栏。

- [ ] **Step 3: 拆分状态并在发送时组装**

```tsx
const requestUrl = composeAssetUrl(baseUrl, serviceName, modulePath, endpointPath)
const payload = {
  method,
  url: applyPathAndQueryParams(requestUrl, paramRows),
  headers: buildHeaders(),
  body,
  assertions,
  environment_id: envId,
}
```

- [ ] **Step 4: 让环境只替换服务器地址**

```tsx
const changeEnvironment = (value: string) => {
  const environment = envs.find((item) => item.id === Number(value))
  setEnvId(environment?.id)
  if (environment) setBaseUrl(environment.base_url)
}
```

- [ ] **Step 5: 验证测试 5 默认值、环境切换和响应布局**

Run: `npm test -- --run src/pages/apitest/components/DebugTab.test.tsx src/pages/apitest/components/assetRoute.test.ts`
Expected: PASS。

### Task 3: 接口用例按接口分组

**Files:**
- Create: `frontend/src/pages/apitest/components/apiCaseGroups.ts`
- Create: `frontend/src/pages/apitest/components/apiCaseGroups.test.ts`
- Modify: `frontend/src/pages/apitest/components/ApiCaseTab.tsx`

- [ ] **Step 1: 写失败测试**

```ts
const groups = groupApiCases([
  { id: 1, api_spec_ref: 'api_endpoint:9', title: '【正向】接口C - 正常请求' },
  { id: 2, api_spec_ref: 'api_endpoint:9', title: '【类型校验】接口C - age - 类型错误' },
])
expect(groups).toHaveLength(1)
expect(groups[0].name).toBe('接口C')
expect(groups[0].cases.map((item) => item.id)).toEqual([1, 2])
```

- [ ] **Step 2: 验证测试先失败**

Run: `npm test -- --run src/pages/apitest/components/apiCaseGroups.test.ts`
Expected: FAIL，因为分组函数尚不存在。

- [ ] **Step 3: 以稳定接口引用分组并默认关闭**

```tsx
{groups.map((group) => (
  <Collapsible key={group.key}>
    <CollapsibleTrigger>{group.name}<Badge>{group.cases.length}</Badge></CollapsibleTrigger>
    <CollapsibleContent>{group.cases.map(renderCaseRow)}</CollapsibleContent>
  </Collapsible>
))}
```

- [ ] **Step 4: 保留单条、接口组和全量选择执行**

Run: `npm test -- --run src/pages/apitest/components/apiCaseGroups.test.ts`
Expected: PASS，具有同一 `api_spec_ref` 的用例只进入同一接口集合。

### Task 4: 自动生成覆盖所有参数

**Files:**
- Modify: `backend/app/services/api_case_generation_service.py`
- Modify: `backend/tests/test_apitest_generation.py`
- Modify: `backend/tests/test_openapi_import_knife4j.py`

- [ ] **Step 1: 写多参数失败测试**

```python
cases = generate_cases_from_endpoint(endpoint, templates=["invalid"])
for field in ("name", "age", "enabled"):
    assert any(field in case["title"] and "类型" in case["title"] for case in cases)
assert any("keyword" in case["title"] and "空值" in case["title"] for case in cases)
assert any("page" in case["title"] and "类型" in case["title"] for case in cases)
```

- [ ] **Step 2: 验证测试先失败**

Run: `pytest tests/test_apitest_generation.py -q`
Expected: FAIL，因为 Query 只覆盖前三个且生成结果没有写入目标异常值。

- [ ] **Step 3: 生成实际的参数变体**

```python
def _with_query_params(case, params, *, overrides=None, omitted=None):
    values = {p["name"]: _sample_value_for_param(p) for p in params if p["name"] != omitted}
    values.update(overrides or {})
    case["api_endpoint"] = f"{base_path}?{urlencode(values)}"
    return case
```

- [ ] **Step 4: 覆盖 Body、Query、Path、Header 的空值和类型错误**

```python
for field, prop in properties.items():
    cases.extend(_body_empty_and_type_cases(endpoint, field, prop))
for param in query_params:
    cases.extend(_query_empty_and_type_cases(endpoint, query_params, param))
for param in path_params:
    cases.extend(_path_empty_and_type_cases(endpoint, path_params, param))
for param in header_params:
    cases.extend(_header_empty_and_type_cases(endpoint, header_params, param))
```

- [ ] **Step 5: 调整安全上限并验证不会截断常见多参数覆盖**

Run: `pytest tests/test_apitest_generation.py tests/test_openapi_import_knife4j.py -q`
Expected: PASS，每个参数至少有一条空值或类型异常覆盖，且总数不超过 200。

### Task 5: 全量回归与构建

**Files:**
- Verify: `frontend/src/pages/apitest/components/*.tsx`
- Verify: `backend/app/services/api_case_generation_service.py`

- [ ] **Step 1: 运行前端测试与类型构建**

Run: `npm test -- --run src/pages/apitest && npm run build`
Expected: PASS，TypeScript 无错误且 Vite 产物生成成功。

- [ ] **Step 2: 运行后端接口测试回归**

Run: `pytest tests/test_apitest_generation.py tests/test_apitest_assets.py tests/test_openapi_import_knife4j.py tests/test_apitest_project_isolation.py -q`
Expected: PASS。

- [ ] **Step 3: 浏览器验收**

Run: `npm run dev -- --host 127.0.0.1`
Expected: `/apitest` 中服务 Tab 可切换、模块默认关闭、快速调试地址分段且响应位于请求配置下方、接口用例按接口关闭分组。
