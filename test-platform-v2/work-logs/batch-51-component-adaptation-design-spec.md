# Batch 51 — Design Spec

> 🎨 Design | Date: 2026-07-28

## 核心策略：兼容层兜底 + 消费者显式迁移

在 `@/ui` Badge 中保留 `variant` 兼容别名，同时把生产消费者显式迁移到 `tone`。兼容别名只用于过渡和回归测试，避免后续代码继续混用两套语义。

### variant → tone 映射表

| shadcn variant | @/ui tone |
|---------------|-----------|
| `default` | `neutral` |
| `destructive` | `danger` |
| `outline` | `neutral` |
| `secondary` | `neutral` |
| `ghost` | `neutral` |

## 新增基元 API

### Card
```tsx
<Card className="...">  // ← 保留成熟 Card API，可按页面添加 ui-surface
  <CardHeader><CardTitle>...</CardTitle><CardDescription>...</CardDescription></CardHeader>
  <CardContent>...</CardContent>
  <CardFooter>...</CardFooter>
</Card>
```

### Textarea
```tsx
<Textarea className="..." placeholder="..." rows={4} />
// 保留成熟输入组件的焦点、禁用和无障碍行为
```

### Label
```tsx
<Label htmlFor="id" className="...">字段名</Label>
// 保留 Radix Label 与 htmlFor 关联能力
```

### Select
```tsx
<Select value={v} onValueChange={setV}>
  <SelectTrigger aria-label="选择项"><SelectValue placeholder="..." /></SelectTrigger>
  <SelectContent>
    <SelectItem value="x">X</SelectItem>
  </SelectContent>
</Select>
```

### Skeleton
```tsx
<Skeleton className="h-4 w-32" />
// bg-_surface-elevated + animate-pulse
```

## PageShell 接入

```
PageShell
├─ title: string | ReactNode
├─ description?: string
├─ actions?: ReactNode (工具栏按钮)
└─ children (列表内容)
```

接入页面: testcase, defect, testplan, environment, report, trace, requirement
