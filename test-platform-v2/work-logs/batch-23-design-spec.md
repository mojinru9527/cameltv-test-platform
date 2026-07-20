# batch-23 设计规范 — 接口测试模块优化

> 日期：2026-07-20 | 设计部门 | 前端 UI + 后端服务

## 技术约束

- UI 组件库：shadcn/ui (Radix + Tailwind) — 见 `cameltv-ui-conventions` skill
- Collapsible 组件使用 Radix Collapsible 封装（`@/components/ui/collapsible`）
- Tabs 组件使用 Radix Tabs 封装（`@/components/ui/tabs`）
- 后端：Python FastAPI，模板驱动的用例生成器（纯函数，不依赖 LLM）
- 状态管理：React useState（组件级），不引入 Zustand

## Slice 1: 接口资产 Tab 层级重构

### 1.1 AssetTab 数据流变更

**当前数据流：**
```
fetchApiEndpoints → endpoints[] → modulePathGroups (Record<module, Record<pathGroup, ApiEndpoint[]>>)
→ Collapsible(module) → CollapsibleContent → pathGroup header → endpoint rows
```

**目标数据流：**
```
fetchApiEndpoints(filtered by service_id) → endpoints[]
→ serviceModuleGroups (activeTab==='_all' ? grouped by service : flat)
→ Collapsible(module) → endpoint rows (with inline pathGroup labels)
```

### 1.2 关键状态与交互

```
┌─ Service Tabs ──────────────────────────────────────┐
│ [全部服务(200)] [用户服务] [订单服务] [支付服务]       │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌─ 当选中「全部服务」Tab: ───────────────────────┐  │
│  │                                                 │  │
│  │  ▼ 用户服务 (45个接口)                          │  │
│  │    ▼ 用户模块 (23)                              │  │
│  │      /api/user      ← pathGroup inline 标签     │  │
│  │      ┌─ [GET] 获取用户列表  │ 描述 │ 备注       │  │
│  │      └─ [POST] 创建用户    │ 描述 │ 备注       │  │
│  │      /api/user/profile  ← pathGroup inline      │  │
│  │      └─ [PUT] 更新用户资料 │ 描述 │ 备注        │  │
│  │    ▷ 认证模块 (12)          ← 折叠状态          │  │
│  │    ▷ 权限模块 (10)          ← 折叠状态          │  │
│  │                                                 │  │
│  │  ▷ 订单服务 (67个接口)     ← 折叠状态           │  │
│  │  ▷ 支付服务 (32个接口)     ← 折叠状态           │  │
│  │                                                 │  │
│  └─────────────────────────────────────────────────┘  │
│                                                      │
│  ┌─ 当选中单个服务 Tab (如'用户服务'): ──────────┐  │
│  │                                                 │  │
│  │  ▼ 用户模块 (23)                                │  │
│  │    /api/user                                     │  │
│  │    ┌─ [GET] 获取用户列表  │ 描述 │ 备注         │  │
│  │    └─ [POST] 创建用户    │ 描述 │ 备注         │  │
│  │  ▷ 认证模块 (12)          ← 折叠状态            │  │
│  │  ▷ 权限模块 (10)          ← 折叠状态            │  │
│  │                                                 │  │
│  └─────────────────────────────────────────────────┘  │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 1.3 组件变更详情

**AssetTab.tsx** 关键变更：

1. **modulePathGroups 改为 serviceModuleGroups**
   - 全部 Tab：`Record<serviceName, Record<moduleName, Record<pathGroup, ApiEndpoint[]>>>`
   - 单个服务 Tab：`Record<moduleName, Record<pathGroup, ApiEndpoint[]>>`
   - 使用 useMemo 按 activeTab 切换

2. **移除中间折叠层级**
   - 当前：Collapsible(module) → pathGroup header → endpoint rows
   - 改为：Collapsible(module) → pathGroup inline label + endpoint rows
   - pathGroup 不作为独立的 Collapsible，作为 section divider 内联展示

3. **全部 Tab 增加服务名折叠**
   - 用双层 Collapsible：Service → Module
   - 服务名折叠默认 `defaultOpen={false}` (Issue 1)

4. **模块名折叠默认关闭**
   - 保持 `defaultOpen={false}`（已实现）
   - 用 key prop 处理 Tab 切换时的状态重置

### 1.4 数据分组函数

```typescript
// 新增分组函数
function groupEndpointsByService(
  endpoints: ApiEndpoint[], 
  services: ApiService[]
): Record<string, Record<string, Record<string, ApiEndpoint[]>>> {
  const result: Record<string, Record<string, Record<string, ApiEndpoint[]>>> = {}
  for (const ep of endpoints) {
    const svcName = services.find(s => s.id === ep.service_id)?.display_name 
      || services.find(s => s.id === ep.service_id)?.name 
      || '未分类'
    const mod = ep.module || '默认模块'
    const pathParts = (ep.path || '/').split('/').filter(Boolean)
    const pathGroup = pathParts.length > 0 ? `/${pathParts[0]}` : '/'
    
    if (!result[svcName]) result[svcName] = {}
    if (!result[svcName][mod]) result[svcName][mod] = {}
    if (!result[svcName][mod][pathGroup]) result[svcName][mod][pathGroup] = []
    result[svcName][mod][pathGroup].push(ep)
  }
  return result
}
```

## Slice 2: 接口用例 & 快速调试优化

### 2.1 ApiCaseTab 分组增强

**当前 apiCaseGroups.ts:**
- 按 `api_spec_ref` 分组 → 组名从第一个 case 的 title 提取

**目标 apiCaseGroups.ts:**
- 按 `api_endpoint` + `api_method` 组合分组
- 组名格式：`[GET] /api/user/list`
- 如果 api_spec_ref 存在，优先用它确保唯一性

```typescript
// 变更后分组逻辑
export function groupApiCases(cases: any[]): ApiCaseGroup[] {
  const map = new Map<string, any[]>()
  
  for (const c of cases) {
    // 按 api_endpoint 分组，方法+路径组合作为 key
    const method = c.api_method || 'GET'
    const endpoint = c.api_endpoint || '/'
    const key = `${method}:${endpoint}`
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(c)
  }
  
  return Array.from(map.entries()).map(([key, items]) => {
    const [method, endpoint] = key.split(':', 2)
    const name = `[${method}] ${endpoint}`
    return { key, name, api_spec_ref: key, cases: items }
  })
}
```

### 2.2 DebugTab 响应位置确认

**当前状态：** ResponsePanel 已在 DebugTab 最底部（line 425），位于 Card 和 AssertionEditor 之后。

**加固变更：**
- 在 ResponsePanel 上添加 `id="response-panel"` 锚点
- 请求完成后用 `scrollIntoView({ behavior: 'smooth' })` 自动滚动

### 2.3 地址拆分加固

**当前状态：** 已实现 4 字段拆分（baseUrl/ serviceName/ modulePath/ endpointPath）和 composeAssetUrl 拼接。

**加固变更：**
- 确保环境切换时只更新 baseUrl，不影响 serviceName/modulePath/endpointPath
- 从资产跳转时预填更准确的字段（利用 endpoint 的 service_id 反查服务名）
- URL 预览区实时更新

## Slice 3: 用例生成覆盖增强

### 3.1 前端模板启用

**AssetTab.tsx:80** `handleGenerate` 函数：
```typescript
// 当前
templates: ['basic', 'boundary', 'invalid', 'idempotency'],

// 改为
templates: ['basic', 'boundary', 'invalid', 'idempotency', 'security', 'extreme'],
```

### 3.2 后端 Query 参数空值覆盖

在 `api_case_generation_service.py` 中扩展 `_build_query_required_cases`:

```python
# 为必填 query 参数增加：缺失、null、空字符串 三种用例
def _build_query_required_cases(ep: dict, query_params: list) -> list[dict]:
    cases = []
    required = [q for q in query_params if q.get("required")]
    for q in required:
        name = q.get("name", "")
        ptype = q.get("type", "string")
        
        # 1. 缺失
        cases.append(...)  # 已有
        
        # 2. 空值
        cases.append(...)  # 新增
        
        # 3. null (如果是可null类型)
        cases.append(...)  # 新增
    
    # 为非必填参数增加可选值用例
    optional = [q for q in query_params if not q.get("required")]
    for q in optional[:3]:
        # 正常值 + 空值 + 特殊字符每种生成一条
        ...
    
    return cases
```

### 3.3 边界值增强

为每个参数的 null 和空值增加专用断言：
- `null` → 期望 4xx 或 200（根据 `nullable`）
- `""` → 期望 4xx（非 nullable string）或 200（nullable）
- `0` → 期望 200（integer 有 default=0）或 4xx
- 负数 → 期望 4xx（无负值业务含义时）

### 3.4 生成数量下限

```python
# 在 generate_cases_from_endpoint 末尾
# 如果参数≥3个但生成<25条，追加组合覆盖
if len(properties) >= 3 and len(cases) < 25:
    cases.extend(_build_combo_cases(endpoint, properties))

# 如果参数≥5个但生成<40条，追加更多组合
if len(properties) >= 5 and len(cases) < 40:
    cases.extend(_build_extra_boundary_cases(endpoint, properties))
```
