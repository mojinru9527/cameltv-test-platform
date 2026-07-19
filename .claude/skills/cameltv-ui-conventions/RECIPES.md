# UI 配方（可复制代码 + 设计 Token 速查）

> 对应 SKILL.md 的 8 类 Red Flags，给出直接能抄的实现。命名/类名与真实代码对齐（`pages/knowledge/components/*`、`src/globals.css`）。

---

## §1 严重级四级可辨色梯度（P0/P1/P2/P3）

问题：曾把 P0 与 P1 都映射为 `destructive`（同红），差异对比按严重级分诊失效。做法——抽一个共享助手，所有用到严重级的组件复用（`WikiDiffTab` / `WikiDiffDetailDrawer` 都用它）：

```ts
// pages/knowledge/components/wikiSeverity.ts
import type { VariantProps } from 'class-variance-authority'
import type { badgeVariants } from '@/components/ui/badge'

type BadgeVariant = VariantProps<typeof badgeVariants>['variant']

export function severityBadge(sev: 'P0' | 'P1' | 'P2' | 'P3'): {
  variant: BadgeVariant
  className?: string
} {
  switch (sev) {
    case 'P0': return { variant: 'destructive' }
    case 'P1': return { variant: 'outline',
      className: 'border-orange-400 text-orange-600 dark:border-orange-500 dark:text-orange-400' }
    case 'P2': return { variant: 'secondary' }
    case 'P3': return { variant: 'outline' }
  }
}
```

关键：**P0 与 P1 必须不同视觉**（红 vs 橙），别再都给 `destructive`。

---

## §2 硬编码语义色 → 补深色变体

反例：`border-blue-200 bg-blue-50 text-blue-700`。

改法 A - 就地补 `dark:` 变体：

```tsx
className="border-blue-200 bg-blue-50 text-blue-700
  dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-300"
className="border-emerald-200 bg-emerald-50 text-emerald-700
  dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
className="border-amber-200 bg-amber-50 text-amber-700
  dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
```

规则：**任何 `-50/-100` 浅底 + `-600/-700` 深字的组合，必须成对提供 `dark:` 变体**。

---

## §3 状态枚举中文映射

```ts
export const REVIEW_STATUS_LABEL: Record<string, string> = {
  approved: '已通过', pending: '待审核', rejected: '已驳回', draft: '草稿',
}
export const TASK_STATUS_LABEL: Record<string, string> = {
  running: '进行中', success: '已完成', failed: '失败', pending: '排队中',
}
// 渲染：{TASK_STATUS_LABEL[status] ?? status}
```

---

## §4 列表页四态 —— 用 AsyncState / DataTable

```tsx
const { data, isLoading, isError, error, refetch } = useApi(
  (signal) => fetchItems({ signal }), [deps])

<AsyncState
  isLoading={isLoading} isError={isError} error={error} data={data}
  onRetry={refetch} emptyTitle="暂无数据"
  emptyAction={{ label: '新建', onClick: openCreate }}
>
  {(items) => <List items={items} />}
</AsyncState>
```

- 主内容是表格 → 用 `DataTable`（自带 loading/error/select 内联态）。
- 决策树见 `test-platform-v2/docs/async-state-patterns.md`。

失败态 ≠ 加载态：

```tsx
{status === 'running' && <><Loader2 className="size-4 animate-spin" /> 对比中…</>}
{status === 'failed'  && <div className="flex items-center gap-2 text-destructive">
  <AlertCircle className="size-4" /> 对比失败
  <Button size="sm" variant="outline" onClick={retry}>重试</Button>
</div>}
```

---

## §5 JSON 结构化展示

```tsx
function prettyJson(raw: string): string {
  try { return JSON.stringify(JSON.parse(raw), null, 2) }
  catch { return raw }
}
<pre className="whitespace-pre-wrap text-xs bg-muted/40 p-3 max-h-[420px] overflow-auto font-mono">
  {prettyJson(evidenceJson)}
</pre>
```

---

## §6 响应式 & 触控目标

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-[1fr_1.4fr_1fr] gap-3">…</div>
<button className="w-full min-h-[36px] px-2 rounded hover:bg-muted">…</button>
```

多 Tab 溢出：给 `TabsList` 加横向滚动容器或图标态收缩。

---

## §7 设计 Token 速查（`src/globals.css`）

| 用途 | CSS 变量 / Tailwind 类 |
|------|------------------------|
| 页面/卡片/弹层底 | `--background` `--card` `--popover` → `bg-background` `bg-card` |
| 主色 | `--primary` / `--primary-foreground` |
| 次要/静音/强调 | `--secondary` `--muted` `--accent`（各带 `-foreground`） |
| 危险 | `--destructive` → `text-destructive` |
| 边框/输入/焦点 | `--border` `--input` `--ring` |
| 高对比 a11y | `--text-muted-high-contrast` → `text-muted-hc` |
| 主题 | `data-theme-id`（crystal/xlab/column/clay/liquid）|

---

## §8 无障碍补全片段

```tsx
<button aria-label={`${sev} ${dimension}差异：${title}`} title={title}
        className="w-full rounded-md border p-2 hover:bg-muted">…</button>
<SelectTrigger aria-label="按严重级筛选" className="h-7 w-[90px]">…</SelectTrigger>
```
