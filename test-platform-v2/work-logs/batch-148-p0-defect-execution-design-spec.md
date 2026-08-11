# Batch 148 — Design Spec（P0 缺陷契约 + 执行根因可见/环境预检）

> **Design (🎨)** | Date: 2026-08-11 | Status: 就绪

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind + CVA；Token 走语义类（bg-muted / text-muted-foreground / border / variant）。真实栈不是 Ant Design。

## 1. 组件规格表

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|----------|---------|--------|
| 执行历史表（3 新列） | 列宽：失败原因 max-w-[220px] truncate + title；HTTP 状态 w-[90px]；失败阶段 w-[110px] | 状态码 ≥400 用 text-destructive；error_type 用 Badge tone | 悬浮 title 显示完整错误 |
| 执行环境 Select | 与执行按钮同排，w-[180px] | SelectTrigger 默认样式 | 空值 sentinel「请选择环境」；选中显示 env.name |
| 缺陷表单错误提示 | 位于 DialogFooter 上方，text-sm | text-destructive | 仅保存失败时显示 |

## 2. 布局与响应式
- 计划详情头部：环境 Select 插入「批量执行」与「一键执行」之前，≤1024px 时换行到第二行（flex-wrap）。
- 执行历史 Tab：表格容器保持横向滚动（现有 overflow-x），新增列不破坏移动端。

## 3. 状态设计核对（四态）
| 组件 | Loading | Empty | Error | 未启用(503) |
|------|---------|-------|-------|------------|
| 执行环境 Select | 禁用 + skeleton 由父级 loading 覆盖 | 仅「请选择环境」 | toast 提示加载失败，可重试 | 计划无 API 用例时不展示（纯人工计划无需环境） |
| 执行历史 3 新列 | SkeletonText 覆盖 | 空态文案不变 | 失败原因列显示 error_message | '-' 占位 |
| 缺陷保存按钮 | saving 禁用 + Loader2 | - | 弹窗内错误文本 + 保持打开 | - |

## 4. 错误阶段（error_type）中文映射
| error_type | 展示 |
|-----------|------|
| INVALID_CASE | 用例校验 |
| TARGET_POLICY | 目标策略/URL |
| POLICY_DENIED | 策略拦截 |
| TIMEOUT | 请求超时 |
| NETWORK_ERROR | 网络连接 |
| ASSERTION_FAILED | 断言失败 |
| EXECUTION_ERROR | 执行异常 |
| 其他/空 | 执行失败 / - |

## 5. 设计 QA 走查发现（P0–P3）
### 🔴 P0-1 422 对象渲染崩溃
`client.ts` 将数组 detail 直接给 toast → **建议**：错误提取链把数组转可读字符串（本批修复）。
### 🟠 P1-2 执行历史根因不可见
执行表仅 5 列 → **建议**：新增失败原因/HTTP 状态/失败阶段三列，历史 JSON 回填解析。

## 6. 设计签核
结论：通过（P0/P1 项已纳入本批 Dev 任务）
