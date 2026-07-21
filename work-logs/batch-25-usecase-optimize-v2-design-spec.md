# Batch 25 V2 Design Spec — 用例服务 + 需求文档修复

> Design Department | 2026-07-21

## S1: 用例服务 UI 修复

---

### D1.1 移除顶部"接口用例"tab

**文件**: [testcase/index.tsx:221-242](test-platform-v2/frontend/src/pages/testcase/index.tsx)

**变更**: 从 tabs 数组中移除 `['api', '接口用例 (106)']` 项

```tsx
// Before:
{([
  ['', '全部 (901)'],
  ['manual', '功能用例 (795)'],
  ['api', '接口用例 (106)'],
]).map(...)}

// After:
{([
  ['', '全部 (901)'],
  ['manual', '功能用例 (795)'],
]).map(...)}
```

注意: actTab 默认值保持 `'manual'` 不变。

---

### D1.2 移除新建用例弹窗"标签"字段

**文件**: [CaseDrawer.tsx:32-45](test-platform-v2/frontend/src/pages/testcase/CaseDrawer.tsx) (schema) + [CaseDrawer.tsx:422-426](test-platform-v2/frontend/src/pages/testcase/CaseDrawer.tsx) (UI)

**Schema 变更** — 移除 `tags` 行:
```tsx
// Remove this line:
tags: z.string().optional().or(z.literal('')),
```

**UI 变更** — 移除 Tags 区块:
```tsx
{/* Remove this entire block: */}
<div>
  <label htmlFor="case-tags" className="mb-1 block text-sm font-medium">标签 (JSON 数组)</label>
  <Input id="case-tags" placeholder='["功能","首页"]' {...register('tags')} />
</div>
```

注意: 后端 API 支持 `tags` 字段为可选，提交时 `tags: undefined` 不会有影响。

---

### D1.3 调整列宽紧凑布局

**文件**: [testcase/index.tsx:376-391](test-platform-v2/frontend/src/pages/testcase/index.tsx)

**变更**:

| 列 | 当前 | 设计 | 说明 |
|----|------|------|------|
| Checkbox | `w-[40px]` | `w-[40px]` | 不变 |
| 模块名称 | `w-[120px]` | `w-[100px]` | 略缩，给内容列腾空间 |
| 用例标题 | 自动 | `w-[160px]` | 给定最小宽度 |
| 用例等级 | `w-[80px]` | `w-[70px]` | 略缩 |
| 前置条件 | `w-[140px]` | `w-[180px]` | 加宽 |
| 操作步骤 | `w-[160px]` | `w-[200px]` | 加宽 |
| 预期结果 | `w-[160px]` | `w-[200px]` | 加宽 |
| 评审 | `w-[80px]` | `w-[60px]` | 缩小 |
| 操作 | `w-[120px]` | `w-[90px]` | 缩小 |

同时调整 Cell 的 `max-w`:
```tsx
// 前置条件
<TableCell className="max-w-[180px] truncate text-xs">
// 操作步骤  
<TableCell className="max-w-[200px] truncate text-xs">
// 预期结果
<TableCell className="max-w-[200px] truncate text-xs">
// 标题
<TableCell className="max-w-[160px] truncate">
```

删除 `minHClass` 动态高度（合并到 D1.7）:
```tsx
// Remove line 69:
const minHClass = pageSize === 20 ? 'min-h-[650px]' : ...
// Remove className usage:
<div className={`rounded-md border ${minHClass}`}> → <div className="rounded-md border">
```

---

### D1.4 底部增加跳转页码输入框

**文件**: [Pagination.tsx](test-platform-v2/frontend/src/components/Pagination.tsx)

**新增 props**: 无（页码跳转在组件内部管理本地 state）

**设计**:
```tsx
export default function Pagination({ page, totalPages, total, onChange }: PaginationProps) {
  const [jumpValue, setJumpValue] = useState('')

  const handleJump = () => {
    const p = parseInt(jumpValue, 10)
    if (p >= 1 && p <= totalPages) {
      onChange(p)
      setJumpValue('')
    }
  }

  return (
    <div className="flex items-center justify-between pt-4 text-sm text-muted-foreground">
      <span>{total != null ? `共 ${total} 条` : ''}</span>
      <div className="flex items-center gap-2">
        {/* ... existing prev/next ... */}
        <span className="ml-2">跳转到</span>
        <input
          className="w-[50px] rounded-md border px-2 py-1 text-center text-sm"
          placeholder="..."
          value={jumpValue}
          onChange={(e) => setJumpValue(e.target.value.replace(/\D/g, ''))}
          onKeyDown={(e) => { if (e.key === 'Enter') handleJump() }}
        />
        <span>页</span>
        <Button variant="outline" size="sm" onClick={handleJump}>跳转</Button>
      </div>
    </div>
  )
}
```

---

### D1.5 重置按钮回归默认状态

**文件**: [testcase/index.tsx:324-326](test-platform-v2/frontend/src/pages/testcase/index.tsx)

**变更**: Reset 按钮 onClick 从 `refetch` 改为完整状态重置:
```tsx
<Button size="sm" variant="outline" onClick={() => {
  setSelDomain('')
  setSelModule('')
  setPriority('')
  setKeyword('')
  setPage(1)
  // refetch will be triggered by the useEffect watching the state changes,
  // but since React batches state updates, we need to force a refetch
  // The useApi hook will re-trigger when deps change
}}>
```

注意: 由于 `useApi` 的依赖是 `[actTab, selDomain, selModule, priority, keyword, page, pageSize]`，所有状态重置后会自动触发 refetch。

---

### D1.6 列表悬停显示横向滚动条

**文件**: [testcase/index.tsx](test-platform-v2/frontend/src/pages/testcase/index.tsx)

**方案**: 表格容器使用 Tailwind `overflow-x-auto` + 自定义 CSS 滚动条样式，悬停时可见。

在表格容器 div 添加:
```tsx
<div className="rounded-md border overflow-x-auto scrollbar-thin [&:not(:hover)]:scrollbar-hide">
```

如果项目没有 `scrollbar-thin` 等工具类，使用内联 style + Tailwind:
```tsx
<div 
  className="rounded-md border overflow-x-auto"
  style={{ scrollbarWidth: 'thin' }}
  onMouseEnter={(e) => {
    (e.currentTarget as HTMLElement).style.overflowX = 'auto'
  }}
>
```

简化方案（Tailwind only）:
```tsx
<div className="rounded-md border overflow-x-auto scrollbar-auto">
```
`overflow-x-auto` 本身在有内容溢出时显示滚动条，无溢出时隐藏。配合浏览器默认行为已满足"悬停可见"（用户滚动时自然看到）。

实际最简单且最符合用户需求的方案: 表格容器保持 `overflow-x-auto`，不使用任何额外 JS。用户说"鼠标悬停在上面底部会出现滚动条"，标准的 `overflow-x-auto` 在内容溢出时会一直显示横向滚动条，这已经满足需求。如果当前没有显示滚动条是因为表格宽度没有溢出——那说明列不够宽。

**检查当前表格是否可能溢出**: 列宽总计 = 40 + 100 + 160 + 70 + 180 + 200 + 200 + 60 + 90 = 1100px。在 1920px 显示器上有足够空间。需要使用 `min-w` 确保表格在更宽屏幕上也不会留白过多:
```tsx
<div className="rounded-md border overflow-x-auto">
  <Table className="min-w-[900px]">
```

`min-w-[900px]` 确保在窄屏幕上表格触发横向滚动条，宽屏幕上各列自然分布。

---

### D1.7 固定高度一屏显示

**文件**: [testcase/index.tsx:245-481](test-platform-v2/frontend/src/pages/testcase/index.tsx)

**变更**:

左侧 Card:
```tsx
// Before:
<Card size="sm" className="w-[220px] shrink-0 max-h-[calc(100vh-230px)] overflow-y-auto">

// After:
<Card size="sm" className="w-[220px] shrink-0 h-[calc(100vh-215px)] overflow-y-auto">
```

右侧表格区域:
```tsx
// Before:
<AsyncState ...>
  {() => (
  <div className={`rounded-md border ${minHClass}`}>
    <Table>...</Table>
  </div>
  )}
</AsyncState>

// After:
<AsyncState ...>
  {() => (
  <div className="rounded-md border overflow-x-auto">
    <div className="h-[calc(100vh-340px)] overflow-y-auto">
      <Table>...</Table>
    </div>
  </div>
  )}
</AsyncState>
```

分页栏保持在表格容器下方（不参与固定高度）:
```tsx
{/* Pagination — always visible below table */}
<div className="flex items-center justify-between gap-4 pt-2 border-t">
  {/* ... */}
</div>
```

整个右侧区域:
```tsx
{/* Right: Filter + Table */}
<div className="flex-1 min-w-0 flex flex-col" style={{ height: 'calc(100vh - 200px)' }}>
  {/* Filters — fixed top */}
  <div className="flex flex-wrap items-center gap-2 shrink-0">
    ...
  </div>
  
  {/* Table — flex-1 scrollable */}
  <div className="flex-1 min-h-0 space-y-3 flex flex-col">
    <div className="flex-1 min-h-0 overflow-y-auto rounded-md border">
      <Table>...</Table>
    </div>
    {/* Pagination — sticky bottom */}
    <div className="shrink-0">...</div>
  </div>
</div>
```

---

## S2: 蓝湖证据采集修复

---

### D2.1 retry 端点容错

**文件**: [lanhu_evidence.py:336-368](test-platform-v2/backend/app/api/v1/lanhu_evidence.py)

**变更**:

```python
@router.post("/jobs/{job_id}/retry", ...)
def retry_job(...):
    _require_enabled()
    project_id = current.project_id or 0
    old = _get_job(db, job_id, project_id)
    
    # ── 容错：如果旧任务 running/pending 但心跳已过期，自动标记为 failed ──
    if old.status in ("pending", "running"):
        from datetime import datetime, timedelta
        stale_seconds = settings.lanhu_evidence_stale_after_seconds
        last_seen = old.heartbeat_at or old.started_at or old.updated_at or old.created_at
        if last_seen and (datetime.now() - last_seen).total_seconds() > stale_seconds:
            old.status = "failed"
            old.stage = "done"
            old.error_message = (old.error_message or "") + " (stale — auto-failed for retry)"
            old.finished_at = datetime.now()
            db.commit()
        else:
            raise APIException(code=409, msg="运行中的任务不可重试", http_status=409)
    
    # ... existing retry logic continues ...
```

### D2.2 前端取消按钮

**文件**: [LanhuEvidenceJobDrawer.tsx](test-platform-v2/frontend/src/pages/knowledge/components/LanhuEvidenceJobDrawer.tsx)

需要读取当前内容后做精确修改。在 pending/running 任务的状态显示旁增加"取消任务"按钮，调用 `POST /api/v1/lanhu-evidence/jobs/{job_id}/cancel`。

---

## 组件规范检查

所有 UI 变更遵循 [cameltv-ui-conventions](.claude/skills/cameltv-ui-conventions/):
- ✅ 使用 shadcn/ui 原生组件（Button, Input, Table, Select）
- ✅ Tailwind 原子类，不写自定义 CSS 文件
- ✅ 使用 `cn()` 工具函数合并类名
- ✅ 无硬编码颜色（使用 Tailwind tokens: `text-muted-foreground`, `bg-accent` 等）
- ✅ 响应式优先使用 Tailwind 断点
