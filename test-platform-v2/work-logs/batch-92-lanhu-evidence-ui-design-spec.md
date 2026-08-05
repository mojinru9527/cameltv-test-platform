# Batch 92 — Design Spec（蓝湖证据包审核 UI）

> **Design (🎨)** | Date: 2026-08-05 | Status: 就绪

## 0. 技术体系确认

shadcn/ui（Radix）+ Tailwind 语义类 + CVA；组件走 `@/ui`（Badge/StatusBadge/PageHeader/AsyncState/Table/Dialog/Select/AlertDialog）。
主题由 data-theme-id + globals.css 驱动，不写死颜色。

## 1. 组件规格表

| 组件 | 规格 | 交互态 |
|------|------|--------|
| 任务状态 Badge | tone 映射：pending=neutral / running=info / success=success / success_with_warnings=warning / failed=danger / cancelled=neutral | 静态 |
| 阶段 Badge | queued=排队中 / discovering=发现页面 / capturing=截图中 / exporting=导出中 / done=已完成（neutral/info 交替） | 静态 |
| 页面审核 Badge | pending=待审核(neutral) / approved=已通过(success) / rejected=已驳回(danger) | 静态 |
| 列表行操作 | 图标按钮 `size-8`（触控目标≥32px，行高 min-h-11 主按钮） | hover 高亮；危险操作 AlertDialog |
| 详情弹窗 | `sm:max-w-5xl w-[95vw]` 内容区 + `<pre whitespace-pre-wrap>` 文本 + 截图 `<img>` | 滚动 |
| 审核弹窗 | `sm:max-w-md`：通过/驳回 + 原因 textarea | 提交 loading |

## 2. 布局与响应式

- 列表页：PageHeader（标题+操作）→ 表格（桌面）/ 卡片折叠（<768px 依赖现有 Table 滚动，不加分栏重构）
- 详情页：顶部摘要卡（grid md:grid-cols-4）→ 页面表格 → 分页
- 弹窗在 390px 视口：`w-[95vw]` + 内部滚动

## 3. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用/无权限 |
|------|---------|-------|-------|--------------|
| 任务列表 | Skeleton 表格 | EmptyState + 新建引导 | ErrorState + 重试 | view 权限缺失 → 菜单不可见 |
| 页面表 | Skeleton 行 | EmptyState（无页面） | ErrorState + 重试 | — |

## 4. 设计 QA 走查发现

### ⚪ P3-01 截图加载
证据包截图体积大（设计稿长图）→ 详情弹窗图片 `max-h-[70vh] object-contain`，避免撑爆视口。

### ⚪ P3-02 长 OCR 文本
merged_text 可能数千字符 → `<pre className="max-h-[50vh] overflow-y-auto whitespace-pre-wrap text-xs">`。

## 5. 设计签核

结论：**通过**。
