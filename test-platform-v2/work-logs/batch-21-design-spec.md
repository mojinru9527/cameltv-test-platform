# batch-21 设计规范

> 日期：2026-07-20 | 设计部门 | 反向回填式 — UI 已存在，本文档规范改动点

## 1. 用例列表页 — 列结构变更

### 当前列布局 (`index.tsx:430-437`)

```
☐ | 编号 | 标题 | 模块 | 状态 | 评审 | API | 操作
```

### 目标列布局

```
☐ | 模块名称 | 用例标题 | 用例等级 | 前置条件 | 操作步骤 | 预期结果 | 状态 | 评审 | 操作
```

### 变更明细

| 操作 | 列名 | 宽度 | 内容 |
|------|------|------|------|
| ➕ 前移 | 模块名称 | `min-w-[100px] max-w-[140px]` | `{r.module \|\| '-'}` |
| ✏️ 调整 | 用例标题 | `min-w-[160px]` | `{r.title}`（不再含 Badge） |
| ➕ 新增 | 用例等级 | `w-[70px]` | `<Badge>` P0/P1/P2/P3（从标题 cell 移出） |
| ➕ 新增 | 前置条件 | `max-w-[140px] truncate` | `formatNumberedText(r.preconditions)` |
| ➕ 新增 | 操作步骤 | `max-w-[160px] truncate` | `formatStepActions(r.steps)` |
| ➕ 新增 | 预期结果 | `max-w-[160px] truncate` | `formatStepExpectations(r.steps, r.expected_result)` |
| ❌ 删除 | API | — | 整列删除（`<TableHead>API</TableHead>` + 数据 cell） |

### 工具栏变更

| 操作 | 元素 | 说明 |
|------|------|------|
| ❌ 删除 | Export Excel 按钮 | `handleExport('excel')` |
| ❌ 删除 | Export Xmind 按钮 | `handleExport('xmind')` |
| ❌ 删除 | 隐藏 `<input type="file">` | `handleImportClick` |
| ✏️ 修改 | 搜索框 placeholder | `"搜索标题/编号/接口"` → `"搜索标题/关键字"` |
| ➕ 新增 | 域下拉 | 加 `<SelectItem value="">全部</SelectItem>` |
| ➕ 新增 | 模块下拉 | 加 `<SelectItem value="">全部</SelectItem>` |
| ➕ 新增 | 优先级下拉 | 加 `<SelectItem value="">全部</SelectItem>` |

---

## 2. 新建/编辑用例弹窗 — 字段变更

### 当前字段列表 (CaseDrawer.tsx)

```
title, case_id, case_type, priority, status,
domain, module, api_method, api_endpoint, tags,
preconditions, steps, expected_result, api_spec_ref
```

### 目标字段列表

```
title, case_id, case_type, priority, status,
domain*, module*, tags,
preconditions, steps*, expected_result*,
api_method, api_endpoint
```

`*` = 必填（新增 Zod `.min(1, ...)`）

### Schema 变更 (Zod)

```typescript
// Before
domain: z.string().optional().or(z.literal('')),
module: z.string().optional().or(z.literal('')),
steps: z.string().optional().or(z.literal('')),
expected_result: z.string().optional().or(z.literal('')),
api_spec_ref: z.string().optional().or(z.literal('')),

// After
domain: z.string().min(1, '请选择域'),
module: z.string().min(1, '请选择模块'),
steps: z.string().min(1, '请填写操作步骤'),
expected_result: z.string().min(1, '请填写预期结果'),
// api_spec_ref: REMOVED
```

---

## 3. 接口测试页 — 行为变更

### 默认 Tab

```typescript
// Before: index.tsx:15
const [activeTab, setActiveTab] = useState('quick')

// After
const [activeTab, setActiveTab] = useState('assets')
```

### DebugTab 接线

```typescript
// Before: index.tsx:68
<DebugTab />

// After
<DebugTab endpoint={debugEndpoint} />
```

### 默认环境 (DebugTab.tsx)

```typescript
// 环境列表加载完成后 (useEffect 中)
const defaultEnv = envs.find(e => e.name === '测试5')
if (defaultEnv && envId === undefined) {
  setEnvId(defaultEnv.id)
  setBaseUrl(defaultEnv.base_url)
}
```

### AssetTab 路径 + 备注

```typescript
// 路径显示: ep.path.replace(/\//g, '-')
<code>{ep.path.replace(/\//g, '-')}</code>

// 新增备注列 (从 ep.remark 读取)
<span className="text-xs text-muted-foreground truncate">{ep.remark || '-'}</span>
```

---

## 4. 后端 API 变更

### 软删除行为

| 端点 | Before | After |
|------|--------|-------|
| `DELETE /test-cases/{id}` | `db.delete(row)` 物理删除 | `row.is_deleted = True` 软删除 |
| `DELETE /test-cases/batch` | `db.delete(r)` 循环物理删除 | `r.is_deleted = True` 循环软删除 |
| `GET /test-cases` | 返回全部（含未映射的 is_deleted 列） | 加 `filter(TestCase.is_deleted == False)` |
| `DELETE /test-cases/domains/{id}` | 软删域+模块 | 新增：级联 `UPDATE test_case SET is_deleted=1 WHERE domain=...` |
| `DELETE /test-cases/domains/{id}/modules/{mid}` | 软删模块 | 新增：级联 `UPDATE test_case SET is_deleted=1 WHERE module=... AND domain=...` |

### 搜索扩展

**`list_cases` keyword：**
```python
# Before: service:112-123 — 3 fields
or_(
    TestCase.title.ilike(like),
    TestCase.case_id.ilike(like),
    TestCase.api_endpoint.ilike(like),
)

# After: 8 fields
or_(
    TestCase.title.ilike(like),
    TestCase.case_id.ilike(like),
    TestCase.api_endpoint.ilike(like),
    TestCase.domain.ilike(like),
    TestCase.module.ilike(like),
    TestCase.preconditions.ilike(like),
    TestCase.steps.ilike(like),
    TestCase.expected_result.ilike(like),
)
```

**`apitest.py` keyword：**
```python
# Before: apitest.py:252-253 — 2 fields
(ApiEndpoint.path.ilike(like)) | (ApiEndpoint.summary.ilike(like))

# After: 4 fields + join
(ApiEndpoint.path.ilike(like)) |
(ApiEndpoint.summary.ilike(like)) |
(ApiEndpoint.module.ilike(like)) |
(ApiEndpoint.service.has(ApiService.name.ilike(like)))
```

---

## 5. 组件树不变

```
MainLayout
└── TestCasePage (testcase/index.tsx)
    ├── 工具栏（筛选+搜索+新建按钮）← 改
    ├── 用例表格 ← 改
    ├── Pagination
    ├── CaseDrawer ← 改
    └── CategoryManagerDialog ← 不改

ApiTestPage (apitest/index.tsx)
├── Tabs ← 改默认值
├── AssetTab ← 改
└── DebugTab ← 改
```

## 关联

- `cameltv-ui-conventions` skill — 组件/样式规范
- `cameltv-bug-guard` skill — 编码前避坑
- [[react-effect-hygiene-rules]]
- PRD: batch-21-prd-summary.md
- PM: batch-21-pm-plan.md
