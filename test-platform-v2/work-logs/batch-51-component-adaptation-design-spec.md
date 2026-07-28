# Batch 51 — Design Spec

> 🎨 Design | Date: 2026-07-28

## 核心策略：Badge variant→tone 透明兼容

**不替换消费者，只增强组件。** 在 `@/ui` Badge 中新增 `variant` prop 作为 `tone` 的 alias，让所有 shadcn `variant="..."` 自动映射到 `tone`。

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
<Card className="...">  // ← 自动应用 ui-surface + rounded-xl + border
  <CardHeader><CardTitle>...</CardTitle><CardDescription>...</CardDescription></CardHeader>
  <CardContent>...</CardContent>
  <CardFooter>...</CardFooter>
</Card>
```

### Textarea
```tsx
<Textarea className="..." placeholder="..." rows={4} />
// 自动应用 ui-input 样式类
```

### Label
```tsx
<Label htmlFor="id" className="...">字段名</Label>
// text-sm font-medium text-(--_text-secondary)
```

### Select
```tsx
<Select value={v} onValueChange={setV}>
  <SelectTrigger><SelectValue placeholder="..." /></SelectTrigger>
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
├─ subtitle?: string
├─ actions?: ReactNode (工具栏按钮)
└─ children (列表内容)
```

接入页面: testcase, defect, testplan, environment, report
