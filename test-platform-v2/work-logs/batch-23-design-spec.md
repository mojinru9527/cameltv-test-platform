# batch-23 Design Spec — 接口测试模块优化

> 日期：2026-07-20 | Design 部门 | 7 项需求

## Slice 1: 接口资产层级重构

### 组件：AssetTab

**数据流**：`endpoints` + `services` → `hierarchy` useMemo → 渲染

```
hierarchy: Record<serviceName, Record<moduleName, Record<pathGroup, ApiEndpoint[]>>>
```

**渲染结构**：

"全部服务" Tab:
```
TabsContent
├── 服务 A (Collapsible, defaultOpen=false)
│   ├── 模块 users (Collapsible, defaultOpen=false)
│   │   ├── [/users] (inline label)  ← pathGroup
│   │   │   ├── GET /users/list  (endpoint row)
│   │   │   └── POST /users/create
│   │   └── [/admin]
│   │       └── GET /admin/dashboard
│   └── 模块 orders (Collapsible)
│       └── ...
├── 服务 B (Collapsible)
│   └── ...
```

单个服务 Tab:
```
TabsContent  (same structure but only for selected service, no service-level Collapsible header)
├── 模块 users (Collapsible)  ← directly, no service wrapper
│   └── ...
```

**关键交互**：
- 点击 Tab 切换服务 → re-fetch endpoints for that service
- 点击 Collapsible 展开/收起 → Radix Collapsible 原生行为
- 点击 endpoint 行 → 打开 EndpointDetailPanel (Sheet)

**视觉规范**：
- 服务组头：font-medium, hover:bg-muted/50, ChevronDown 旋转动画
- 模块组头：font-medium, hover:bg-muted/50, FolderOpen 图标
- PathGroup 标签：bg-muted/30, text-xs, text-muted-foreground, font-mono, ArrowRight 图标
- Endpoint 行：hover:bg-muted/50, cursor-pointer, 左侧 padding 缩进 (pl-10)
- Method Badge：颜色区分 GET/POST/PUT/DELETE
- 路径 code：text-sm font-medium

## Slice 2: 接口用例 & 快速调试

### ApiCaseGroup 接口更新

```typescript
interface ApiCaseGroup {
  key: string
  name: string         // from title extraction
  method: string       // NEW: HTTP method
  endpoint: string     // NEW: clean endpoint path (no query string)
  api_spec_ref: string
  cases: any[]
}
```

### ApiCaseTab 组头

```
CollapsibleTrigger:
  [ClipboardCheck] [ChevronDown] [POST Badge] /api/c  [3 条用例 Badge] [执行全部 Button]
```

### DebugTab 响应滚动

- ResponsePanel 的 Card 元素添加 `id="response-panel"`
- `useEffect` 监听 `result` 变化 → `scrollIntoView({ behavior: 'smooth', block: 'start' })`
- 100ms 延迟确保 DOM 渲染完成

## Slice 3: 用例生成增强

### 新增函数

| 函数 | 职责 |
|------|------|
| `_get_invalid_value(param)` | 返回参数对应的非法值（null → null, string → '', integer → 0, number → 0.0） |
| `_build_extra_boundary_cases(ep, properties, params)` | 为每个参数生成 null/空/零/负数用例 |
| `_build_combo_param_cases(ep, properties, params)` | 为多参数组合生成覆盖用例（全正常、全边界、混合） |

### 数量下限保护

```python
total_params = len(properties) + len(query_params)
if total_params >= 5 and len(cases) < 40:
    cases.extend(_build_combo_param_cases(...))
elif total_params >= 3 and len(cases) < 25:
    cases.extend(_build_extra_boundary_cases(...))
```

### Query 参数增强

`_build_query_required_cases` 扩展：
- 原有：缺失必填参数
- 新增：null 值、空字符串（仅 string 类型）

### 前端模板扩展

生成模板从 `['basic', 'boundary', 'invalid', 'idempotency']` 扩展为：
`['basic', 'boundary', 'invalid', 'security', 'idempotency', 'extreme']`
