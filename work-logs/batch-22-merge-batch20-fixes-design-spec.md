# Batch 22 — 合并 Batch-20 七个缺陷修复 — 设计规范

> 方案源自 batch-20 已审批设计，此处重新锚定到当前分支文件:行号。

## G1: `prefers-reduced-transparency`

### theme-provider.tsx — `applyTheme()` 末尾追加

在 `applyTheme()` 函数末尾、设置 `data-reduced-motion` 之后：

```tsx
// 检测 reduced-transparency 偏好
if (window.matchMedia("(prefers-reduced-transparency: reduce)").matches) {
  root.dataset.reducedTransparency = "true"
} else {
  delete root.dataset.reducedTransparency
}
```

### theme-provider.tsx — 新增 useEffect 监听变化

在现有 `prefers-reduced-motion` 监听 useEffect 之后新增：

```tsx
// 监听 reduced-transparency 偏好变化
useEffect(() => {
  const mq = window.matchMedia("(prefers-reduced-transparency: reduce)")
  const handler = () => applyTheme(mode, colorTheme)
  mq.addEventListener("change", handler)
  return () => mq.removeEventListener("change", handler)
}, [mode, colorTheme])
```

### globals.css — `[data-reduced-transparency="true"]` 降级块

在 `@media (prefers-reduced-motion: reduce)` 块后面追加，覆盖液境主题 10 个玻璃态组件：

```css
[data-reduced-transparency="true"] [data-theme="liquid"] [data-slot="card-lift"],
[data-reduced-transparency="true"] [data-theme="liquid"] [data-sidebar="..."] ... {
  background: var(--card);
  backdrop-filter: none;
}
```

## G2: `prefers-reduced-motion` CSS 块

### globals.css — 在文件末尾 `@layer base` 之前

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
  .shimmer { animation: none !important; background-image: none !important; }
  [data-sidebar="menu-item"] { transition: none !important; }
}
```

## G3: Sonner toast per-theme 覆盖

### globals.css — `[data-theme] [data-sonner-toaster]` 块

```css
[data-theme] [data-sonner-toaster] {
  --normal-bg: var(--popover);
  --normal-border: var(--border);
  --normal-text: var(--popover-foreground);
  --success-bg: hsl(142 76% 90%);
  --success-border: hsl(142 76% 36%);
  --error-bg: hsl(0 76% 90%);
  --error-border: hsl(0 76% 36%);
}

[data-theme="liquid"] [data-sonner-toaster] {
  --normal-bg: var(--glass-bg);
  --normal-border: var(--glass-border);
}
.dark[data-theme="liquid"] [data-sonner-toaster] {
  --normal-bg: var(--glass-bg);
}
```

## G4: AssetTab 无障碍 + 测试修正

### AssetTab.tsx — 左箭头按钮: line ~156

```tsx
<Button variant="ghost" size="icon-sm" className="shrink-0"
  onClick={() => scrollTabs('left')}
  aria-label="向左查看更多服务">
```

### AssetTab.tsx — 滚动容器 div: line ~163

```tsx
<div ref={tabsScrollRef} className="overflow-x-auto scrollbar-none flex-1"
  onScroll={checkScroll} data-testid="service-tabs-viewport">
```

### AssetTab.tsx — 右箭头按钮: line ~180

```tsx
<Button variant="ghost" size="icon-sm" className="shrink-0"
  onClick={() => scrollTabs('right')}
  aria-label="向右查看更多服务">
```

### AssetTab.test.tsx — line 115

`left: 240` → `left: 200`（匹配源码 `scrollTabs` 函数）

## G5: CaseDrawer label-id

### CaseDrawer.tsx — line 463

```tsx
<pre id="case-steps" className="text-sm leading-relaxed bg-muted/30 rounded-md p-3 min-h-[120px] whitespace-pre-wrap font-sans">
```

## G6: ApiCaseTab 错误 Modal

### ApiCaseTab.tsx — lines 73-76

```tsx
} catch (e: any) {
  toast.error(e?.message || '执行失败')
  setResult({ error: true, message: e?.message || '网络请求失败，请检查后端服务是否启动' })
  setResponseModalOpen(true)
}
```

## G7: testcase/index.tsx 动态高度

### testcase/index.tsx — line 365

```tsx
// 替换: min-h-[600px]
// 改为:
min-h-[${pageSize === 20 ? '650px' : pageSize === 50 ? '1550px' : '3050px'}]
```
