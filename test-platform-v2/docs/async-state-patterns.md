# AsyncState & DataTable 集成模式指南

> 版本: 1.0 | 日期: 2026-07-02 | 批次 D (Sprint 0.4) 沉淀

---

## 概述

测试平台 v2 前端通过批次 D 统一了三态（loading / error / empty）处理。页面使用两种模式处理数据加载状态，本文档说明两种模式的适用场景和选择依据。

## 核心基础设施

| 模块 | 路径 | 职责 |
|------|------|------|
| `useApi` | `src/hooks/useApi.ts` | 泛型数据获取 hook，内置 AbortController、isLoading/isRefetching 分离、sonner toast 错误提示 |
| `AsyncState` | `src/components/state/AsyncState.tsx` | 声明式 4 状态容器（loading → error → empty → data），自动决策渲染哪个状态 |
| `LoadingState` | `src/components/state/LoadingState.tsx` | 加载态组件（skeleton / spinner / inline 三种变体） |
| `ErrorState` | `src/components/state/ErrorState.tsx` | 错误态组件（AlertTriangle + retry + 可展开详情） |
| `EmptyState` | `src/components/EmptyState.tsx` | 空数据组件（增强版，支持 size / variant / children） |
| `DataTable` | `src/components/DataTable.tsx` | 通用数据表格（内置 loading skeleton + empty state + pagination） |

---

## 模式 A：AsyncState 全包裹

### 适用场景

- 页面内容为**非 DataTable 组件**（图表、卡片、自定义布局）
- 页面有**单一数据源**
- 需要在 loading/error/empty/data 四态之间**完全切换**，不保留旧内容

### 使用页面

- `workbench/index.tsx` — 工作台看板（Recharts 图表 + 卡片）
- `requirement/index.tsx` — 需求管理（自定义表格 + 分页）
- `defect/index.tsx` — 缺陷管理（DataTable）

### 代码模板

```tsx
import { useApi } from '@/hooks/useApi'
import { AsyncState } from '@/components/state'
import { fetchData } from '@/api/xxx'

export default function MyPage() {
  const { data, isLoading, isError, error, refetch } = useApi(
    () => fetchData({ page }),
    [page]
  )

  return (
    <AsyncState
      isLoading={isLoading}
      isError={isError}
      error={error}
      data={data}
      onRetry={refetch}
      skeletonType="card"       // or "table" | "page" | "form"
      loadingRows={5}
      emptyTitle="暂无数据"
      emptyIcon={Inbox}
      emptyAction={{ label: '创建', onClick: () => openDrawer() }}
    >
      {(items) => (
        <DataTable columns={columns} data={items} />
      )}
    </AsyncState>
  )
}
```

### 优点

- **单一入口**：所有状态逻辑集中在一个组件
- **安全**：loading/error/empty 状态下不会渲染 data 内容，避免 `undefined.map()` 崩溃
- **类型安全**：function-as-children 中的 data 是 `NonNullable<T>`，无需额外 null check

### 注意

- 当 data 是空数组 `[]` 或空对象 `{}` 时，`isDataEmpty()` 会触发 empty 状态
- `AsyncState` 在 loading + data===undefined 时渲染 loading，在 isError + data===undefined 时渲染 error
- **如果 data 已存在（refetch 场景），loading 和 error 不会覆盖已有内容**，而是通过 `isRefetching` 传递给 DataTable 的 `loading` prop

---

## 模式 B：DataTable 内联 ErrorState

### 适用场景

- 页面内容**主要是 DataTable 组件**
- DataTable 自带 loading skeleton（`loading` prop）和 empty state（`emptyState` prop）
- 只想在**首次加载失败**时显示全页 ErrorState，其他状态交给 DataTable 处理

### 使用页面

- `testplan/index.tsx` — 测试计划
- `report/index.tsx` — 报告中心
- `testcase/index.tsx` — 用例管理
- `project/index.tsx` — 项目管理
- `schedule/index.tsx` — 定时任务
- `trace/index.tsx` — 质量追溯
- `system/` — 用户/角色/审计标签页

### 代码模板

```tsx
import { useApi } from '@/hooks/useApi'
import { ErrorState } from '@/components/state'
import DataTable from '@/components/DataTable'
import { fetchData } from '@/api/xxx'

export default function MyListPage() {
  const { data, isLoading, isRefetching, isError, error, refetch } = useApi(
    () => fetchData({ page, keyword }),
    [page, keyword]
  )

  const items = data?.items || []
  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1

  return (
    <div>
      <PageHeader title="列表页" />

      {/* 仅首次加载失败 (data 为空) 时显示全页 ErrorState */}
      {isError && (!data || data.items?.length === 0) ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : (
        <DataTable
          columns={columns}
          data={items}
          rowKey={(r) => r.id}
          loading={isLoading || isRefetching}    // ← DataTable 内置 skeleton
          loadingRows={4}
          emptyState={{ title: '暂无数据', description: '...' }}
          pagination={{ page, totalPages, total, onChange: setPage }}
          toolbar={/* search + filters */}
        />
      )}
    </div>
  )
}
```

### 优点

- **最小改动**：只需添加 ErrorState import + 三元判断，其余结构不变
- **利用 DataTable 内置能力**：loading skeleton、empty state、pagination 全部内置
- **粒度更细**：`isRefetching` 单独传递给 DataTable，后台刷新时显示 subtle loading

### 注意

- ErrorState 的 guard 条件 `!data || data.items?.length === 0` 确保在 refetch 失败时（data 仍存在旧数据）不会用 ErrorState 替换 DataTable
- 错误 toast 由 useApi 自动弹出，ErrorState 提供 retry 按钮作为二次操作入口

---

## 模式选择决策树

```
页面主要内容是 DataTable 吗？
├── 是 → 使用模式 B（DataTable 内联 ErrorState）
│   └── 除非：页面有多个数据源 / 非表格内容
└── 否 → 使用模式 A（AsyncState 全包裹）
    ├── 图表/卡片 → skeletonType="card"
    ├── 自定义列表 → skeletonType="table"
    └── 全页 → fullPage={true}
```

## 快速决策表

| 特征 | 模式 A (AsyncState) | 模式 B (DataTable inline) |
|------|---------------------|--------------------------|
| 适用组件 | 非 DataTable 或混合内容 | DataTable 为主 |
| Error 显示 | 由 AsyncState 统一渲染 | 手动 `<ErrorState>` guard |
| Loading 显示 | 由 AsyncState 统一渲染 | DataTable `loading` prop |
| Empty 显示 | 由 AsyncState 统一渲染 | DataTable `emptyState` prop |
| 代码量 | 一个包裹组件 | 一个三元 + ErrorState import |
| 类型安全 | function-as-children 自动 narrow | 需要手动 `items || []` |

---

## 迁移指南

### 从旧模式迁移到模式 B（推荐 DataTable 页面）

**迁移前**（批次 D 之前）：
```tsx
const [data, setData] = useState([])
const [loading, setLoading] = useState(false)
const [error, setError] = useState(null)

useEffect(() => {
  setLoading(true)
  fetchData().then(setData).catch(setError).finally(() => setLoading(false))
}, [page])

return <DataTable data={data} loading={loading} />
```

**迁移后**：
```tsx
const { data, isLoading, isError, error, refetch } = useApi(
  () => fetchData({ page }),
  [page]
)

const items = data?.items || []

return (
  <>
    {isError && items.length === 0 ? (
      <ErrorState error={error} onRetry={refetch} />
    ) : (
      <DataTable data={items} loading={isLoading} />
    )}
  </>
)
```

### 从旧模式迁移到模式 A（推荐非 DataTable 页面）

直接包裹 `<AsyncState>` 即可，见上方代码模板。

---

## 相关文件

- [useApi.ts](../frontend/src/hooks/useApi.ts) — 数据获取 hook
- [AsyncState.tsx](../frontend/src/components/state/AsyncState.tsx) — 状态容器
- [LoadingState.tsx](../frontend/src/components/state/LoadingState.tsx) — 加载组件
- [ErrorState.tsx](../frontend/src/components/state/ErrorState.tsx) — 错误组件
- [EmptyState.tsx](../frontend/src/components/EmptyState.tsx) — 空状态组件
- [DataTable.tsx](../frontend/src/components/DataTable.tsx) — 数据表格
