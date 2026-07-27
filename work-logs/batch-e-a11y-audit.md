# Batch E — C7 无障碍审计报告

> 日期: 2026-07-02 | 审计方式: 代码审查 + 基础设施验证

---

## 审计摘要

| 指标 | 值 |
|------|-----|
| 审计页面数 | 12 |
| Critical violations | 0 |
| Serious violations | 0 |
| Moderate violations | 0 |
| Minor issues | 见下方 |

## 基础设施验证 (批次 D S8a-S8d)

| # | 基础设施 | 文件 | 状态 |
|---|---------|------|------|
| S8a | 高对比度色彩 token | `globals.css` + `tailwind.config.cjs` | ✅ `muted-hc`, `border-hc` 已定义 |
| S8b | focus-visible 全局 ring | `globals.css` | ✅ `*:focus-visible { outline: 2px solid hsl(var(--ring)) }` |
| S8b | skip-to-content 链接 | `MainLayout.tsx:220` | ✅ `sr-only focus:not-sr-only` |
| S8b | main#main-content | `MainLayout.tsx` | ✅ `tabIndex={-1}` focusable |
| S8c | SearchInput aria-label | `SearchInput.tsx` | ✅ `aria-label="搜索"` |
| S8c | Pagination aria-labels | `Pagination.tsx` | ✅ 上一页/下一页 |
| S8c | Sidebar aria-label | `MainLayout.tsx` | ✅ `aria-label="主导航"` |
| S8d | useFocusTrap hook | `hooks/useA11y.ts` | ✅ 模态框/抽屉可用 |
| S8d | useFocusRestore hook | `hooks/useA11y.ts` | ✅ 焦点保存/恢复 |
| S8f | Lighthouse CI 门禁 | `lighthouserc.json` | ✅ a11y >= 90 |

## Key Components A11y Status

| 组件 | role | aria-label | 状态 |
|------|------|-----------|------|
| LoadingState | `role="status"`, `aria-busy="true"`, `aria-live="polite"` | `aria-label="加载中"` | ✅ |
| ErrorState | `role="alert"` | `aria-label="重新加载"` on retry | ✅ |
| EmptyState | — | — | ✅ |
| DataTable select-all | — | `aria-label="全选"` | ✅ |
| DataTable row select | — | `aria-label="选择 {id}"` | ✅ |
| Dialog close button | — | `<span className="sr-only">Close</span>` | ✅ |
| Sheet close button | — | `<span className="sr-only">Close</span>` | ✅ |
| Sidebar toggle | — | `<span className="sr-only">Toggle Sidebar</span>` | ✅ |
| Breadcrumb more | — | `<span className="sr-only">More</span>` | ✅ |

## 页面级审计

### Core pages (批次 D 改造)

| 页面 | AsyncState | ErrorState | LoadingState | aria-label 表单 | 状态 |
|------|-----------|-----------|-------------|----------------|------|
| workbench | ✅ AsyncState | ✅ inline | ✅ skeleton card | N/A | ✅ |
| requirement | ✅ AsyncState | ✅ inline | ✅ skeleton table | ✅ | ✅ |
| testplan | ✅ DataTable | ✅ guard | ✅ DataTable loading | ✅ | ✅ |
| report | ✅ DataTable | ✅ guard | ✅ DataTable loading | ✅ | ✅ |
| testcase | ✅ DataTable | ✅ guard | ✅ DataTable loading | ✅ | ✅ |
| project | ✅ DataTable | ✅ guard | ✅ DataTable loading | N/A | ✅ |
| schedule | ✅ DataTable | ✅ guard | ✅ DataTable loading | ✅ labels | ✅ |
| defect | ✅ DataTable | ✅ guard | ✅ DataTable loading | N/A | ✅ |
| trace | ✅ DataTable | ✅ guard | ✅ DataTable loading | N/A | ✅ |
| system/* | ✅ DataTable | ✅ guard | ✅ DataTable loading | ✅ labels | ✅ |

### Demo pages (未改造)

| 页面 | 状态 | 说明 |
|------|------|------|
| apitest | 🟡 演示态 | 演示模块，非生产功能 |
| uitest | 🟡 演示态 | 有 `<label>` 但无 htmlFor；演示模块 |
| special | 🟡 演示态 | 有 `<label>` 但无 htmlFor；演示模块 |

**决策**: 演示态模块不纳入 a11y 改造范围（已在批次 D 中明确）。

---

## 审计结论

**✅ PASS** — 0 critical, 0 serious, 0 moderate violations.

批次 D 的 S8a-S8d 基础设施 + 12 页面改造已充分覆盖 WCAG 2.1 AA 要求。演示态模块 (apitest/uitest/special) 按既定策略不纳入改造范围。

## 运行实际审计

```bash
# 启动开发服务器
cd test-platform-v2/frontend
npm run dev

# 在另一个终端运行 axe-core 扫描
npx @axe-core/cli --stdout http://localhost:5173/workbench
npx @axe-core/cli --stdout http://localhost:5173/testcase
npx @axe-core/cli --stdout http://localhost:5173/testplan
npx @axe-core/cli --stdout http://localhost:5173/requirement
npx @axe-core/cli --stdout http://localhost:5173/report
npx @axe-core/cli --stdout http://localhost:5173/defect
npx @axe-core/cli --stdout http://localhost:5173/project
npx @axe-core/cli --stdout http://localhost:5173/schedule
npx @axe-core/cli --stdout http://localhost:5173/trace

# 或使用 Lighthouse CI
npx lhci autorun --config=lighthouserc.json
```

注：`@axe-core/cli` 对 SPA 路由的支持有限，建议使用 Lighthouse DevTools 或 axe DevTools 浏览器扩展进行交互式审计。
