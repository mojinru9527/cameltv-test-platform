# Batch 213 — Design Spec (首页我的待办 / home-todo)
> **Design (🎨)** | Date: 2026-09-02 | Status: 草稿

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind + CVA；Token 走语义类（bg-card / bg-muted / text-foreground / text-muted-foreground / border / variant）。
复用 `PageHeader`、`Card`、`Badge`、`AsyncState`（四态）、`EmptyState`；图标用 Lucide（`size-4`）。

## 1. 页面结构
`/workbench` →「我的待办」页：

```
PageHeader(title=我的待办, desc=今天要审什么、什么在跑、什么失败)
└─ AsyncState(loading/error/empty/data)
   └─ grid grid-cols-1 md:grid-cols-2 gap-4
      ├─ TodoPanel(待审)      Icon=ClipboardCheck count=reviews.count   — 点击直链 /requirement/{id}/review
      ├─ TodoPanel(在跑)      Icon=Loader2/Activity   count=running.count — 直链需求/AI 任务页
      ├─ TodoPanel(失败/需关注) Icon=AlertCircle      count=failures.count — 直链 /defect/{id}、报告
      └─ TodoPanel(待放行)     Icon=Rocket/FileCheck   count=releases.count — 直链 /release-bundles/{id}
```

`TodoPanel` = `Card` 容器：
- `CardHeader`: 图标 + 面板标题 + `Badge`（count，`variant=secondary`，中文语义色）。
- `CardContent`: 条目列表；每条 = `<button>`（整行可点）+ 标题 `truncate` + 副标题 `text-xs text-muted-foreground`；分隔 `divide-y`。
- 空态：`EmptyState`（面板级小文案「暂无待办」）；列表尾部「查看全部」link（`text-sm text-primary`）。
- 四态：Loading（`Skeleton` 行）→ Empty（`EmptyState`）→ Error（`ErrorState` + 重试）→ Data。

## 2. 布局与响应式
| 断点 | 布局 | 变化 |
|------|------|------|
| <768px | 单列 | 四面板纵向堆叠，条目触控 `min-h-[40px]` |
| md 768–1023 | 2 列 | `md:grid-cols-2` |
| lg 1024+ | 2 列 | 面板固定高度 280px，内容滚动 `max-h` |

## 3. 状态设计核对（四态）
| 组件 | Loading | Empty | Error | 未启用(503) |
|------|---------|-------|-------|------------|
| 我的待办 | 整页 `AsyncState` Skeleton | 面板级 `EmptyState` | `ErrorState` + 重试 | 沿用平台统一 503 处理 |
| TodoPanel | 面板内 3 行 Skeleton | 「暂无待办」 | 面板级错误占位 | — |

## 4. 中文映射（状态不裸英文）
- 待审 / 在跑 / 失败(需关注) / 待放行 —— 全部中文标题；
- count 徽标用数字 + 中文单位，不用 `pending/failed/active` 裸枚举；
- 副标题字段：待审=需求标题+用例数；在跑=任务类型+进度；失败=缺陷标题+严重级；待放行=发布包名+版本号。

## 5. 设计 QA 走查对照（Red Flags 自检）
| Red Flag | 本页处理 |
|----------|---------|
| 状态标签裸英文 | 面板标题/徽标全部中文 |
| 缺 Error/四态 | 用 `AsyncState` + `ErrorState` + `EmptyState` |
| 失败态误用加载动画 | 失败面板用 `AlertCircle` 红色语义，非 spin |
| 触控目标<44px | 条目 `min-h-[40px]`；`h-8` 以上 | 
| 响应式断点跨度过大 | `md:grid-cols-2` 中间态，非 1→大屏直跳 |
| 硬编码语义色无深色变体 | 用 `bg-card`/`text-muted`/`border` 语义类，不写裸色阶 |

## 6. 设计签核
结论：交付给 Dev 落地（前端为真实栈，无外部依赖；四态与中文映射为硬性）。
