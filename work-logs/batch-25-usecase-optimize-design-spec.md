# Batch 25 Design Spec — 用例服务 + 接口测试优化

> Design Department | 2026-07-21

## 设计范围

本次改动涉及前端 7 个文件 + 验证后端 1 个文件，无新增组件，无 API 契约变更。

---

## 1. 用例列表列重构 (`testcase/index.tsx`)

### 1.1 列定义变更

**当前** (line 372-386):
```
复选框 → 模块名称 → 用例标题 → 用例等级 → 前置条件 → 操作步骤 → 预期结果 → 评审 → 操作
```

**目标**:
```
复选框 → 模块名称 → 用例标题 → 用例等级(Badge独立) → 前置条件 → 操作步骤 → 预期结果 → 评审 → 操作
```

变更点：
- **隐藏 `case_id` 列**：当前不显示 case_id 列（已不存在于 TableHead 中），无需改动
- **优先级 Badge**：确保 `PRIORITY_COLORS` 映射正确，P0→red/destructive, P1→orange, P2→blue/default, P3→muted
- **单行截断**：所有 TableCell 添加 `max-w-[XXXpx] truncate` class（已部分实现）

### 1.2 列表渲染截断

每个 TableCell 使用：
```tsx
<TableCell className="max-w-[XXXpx] truncate">
  <span className="line-clamp-1">{content || '......'}</span>
</TableCell>
```

`line-clamp-1` 确保单行 + 超出 "......"

### 1.3 时间倒序

在 `items` 使用前调用已有函数：
```ts
import { sortCasesNewestFirst } from './caseListFormatters'
const sortedItems = useMemo(() => sortCasesNewestFirst(items), [items])
```

### 1.4 编号格式化确认

`formatNumberedText` / `formatStepActions` / `formatStepExpectations` 已正确返回 `string[]`，渲染为：
```tsx
{formatNumberedText(r.preconditions).map((line, i) => (
  <div key={i}>{line}</div>
))}
```
或单行模式用 `join(' ')` 拼接。

---

## 2. 筛选器增强 (`testcase/index.tsx`)

### 2.1 Select 全部选项

域/模块/优先级 Select 均已包含 `<SelectItem value="">全部</SelectItem>`，保留不变。

### 2.2 搜索优化

- Placeholder: `"搜索标题/关键字、域、模块"`
- 后端已在 `test_case_service.py:112-133` 实现多字段模糊搜索（title, case_id, api_endpoint, domain, module, preconditions, steps, expected_result），前端无需改动

---

## 3. 模块分类管理 (`CategoryManagerDialog.tsx`)

### 3.1 过滤"接口测试"域

在 `CategoryManagerDialog` 接收 `domains` prop 前过滤：
```ts
const filteredDomains = domains.filter((d: any) => d.domain !== '接口测试')
```

同时索引页的 domain tree 也需过滤。

### 3.2 修复 `undefined` ID 问题

`categoryId` 函数已处理 undefined → null 返回。需确保有 `id` 的域才能进行删除操作。当前逻辑已在 `DomainNode` 中用 `disabled={!domainId}` 处理。

实际报错可能来自 index.tsx 中 domain tree 的 `onSelect` 回调，当点击没有 `id` 的旧域节点时 key 仍是字符串。现有逻辑用 `key.includes('::')` 判断，应该不会传 `undefined`。

---

## 4. 新建用例弹窗 (`CaseDrawer.tsx`)

### 4.1 下拉框遮挡修复

为 Dialog 内的 Select 添加 `modal={false}` 或增加 Portal z-index：
```tsx
<SelectContent position="popper" sideOffset={4} className="z-[9999]">
```

### 4.2 模块必填

Zod schema 已有 `module: z.string().min(1, '请选择模块')`。在表单中确保 `errors.module` 提示信息被正确渲染。

### 4.3 移除字段

- 移除 `case_id` Input 字段（line 298-302）
- Zod schema 中移除 `case_id` 字段
- 移除 `api_spec_ref`（当前不在 form schema 中，确认创建时 body 不包含该字段）

### 4.4 保存后排序

onSaved 回调中 refetch 后无需额外操作（Slice 1 的 `sortCasesNewestFirst` 已处理排序）。

---

## 5. 逻辑删除 (`test_case_service.py` + 前端)

### 5.1 后端确认

`delete_domain` (line 306) 和 `delete_module` (line 377) 已实现级联 is_deleted=true：
- 域删除 → 模块 is_deleted=true + 用例 is_deleted=true
- 模块删除 → 用例 is_deleted=true

前端调用正确 → 无需后端改动。

### 5.2 接口用例过滤

用例列表 tab 切换 `case_type` filter 已生效（line 95）：
- "全部" → `actTab=''` → 不传 `case_type`
- "功能用例" → `actTab='manual'`
- "接口用例" → `actTab='api'`

需确认 `actTab` 默认值为 `''`（全部）或 `'manual'`（功能用例）。

---

## 6. 移除 Excel/Xmind 按钮 (`mindmap/index.tsx`)

### 6.1 脑图页

移除 lines 162-170 的 Xmind 导出按钮。

### 6.2 用例列表页

当前无 Excel/Xmind 按钮（line 84 仅是空注释），不需要改。

---

## 7. 接口测试默认 Tab (`apitest/index.tsx`)

```tsx
const [activeTab, setActiveTab] = useState('assets')  // 从第一个 tab 改为 'assets'
```

---

## 8. 接口资产三级层级 (`AssetTab.tsx`)

### 8.1 显示名称转换

模块名和路径名中的 `/` 替换为 `-`：
```ts
function displayName(segment: string): string {
  return segment.replace(/\//g, '-').replace(/^-|-$/g, '')
}
```

应用场景：
- `ee/search` → `ee-search`
- `synonyms/cou` → `synonyms-cou`
- `/ee/search/` → `ee-search`

### 8.2 搜索增强

现有搜索已将 keyword 传到后端。添加客户端搜索提示：搜索框 placeholder 改为 "搜索服务名、模块名、路径"。

### 8.3 备注字段

当前 `ep.remark` 已在 endpoint row 第二行显示（line 157-159）。确保 remark 有独立的样式区分（如 italic 或 muted）。

---

## 9. 调试 URL 拼接 (`DebugTab.tsx`)

### 9.1 从资产跳入

当前逻辑（line 114-158）：解析 endpoint path → serviceName/modulePath/endpointPath。需确认：
- 默认环境自动选中 "测试5"（line 102 已实现）
- URL 预览正确显示 `${baseUrl}/${serviceName}${modulePath}${endpointPath}`

### 9.2 直接进入调试

当 `endpoint` prop 为 null 时，所有字段为空（当前逻辑已处理）。

### 9.3 环境切换

切换环境时仅更新 `baseUrl`，不影响 `serviceName`/`modulePath`/`endpointPath`（line 257 已实现）。

---

## 10. Swagger 导入 (`ImportDialog.tsx`)

现有实现已完整：服务名 + URL/文本导入 + 预览 + 确认。确认以下几点：
- 导入后 AssetTab 正确刷新（`importRefreshKey` 已处理）
- 导入后生成的接口有正确的 `module` 和 `path` 字段
- `service_name` 对应 ApiService 的 `name` 或 `display_name`
