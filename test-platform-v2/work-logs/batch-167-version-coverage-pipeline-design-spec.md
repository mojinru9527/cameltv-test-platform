# Batch 167 — Design Spec
> **Design (🎨)** | Date: 2026-08-13 | Status: 就绪

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind + CVA。Token 走语义类（bg-muted / text-muted-foreground / border / variant）。徽标用状态语义 tone，不用自造颜色。

## 1. 组件规格表
| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|----------|--------|
| 版本覆盖矩阵（BundleDetail） | 表格行高 44px，gap-2 | 已覆盖=success，缺口=danger，部分=muted | 行 hover bg-muted；P0/P1 模块加 priority badge |
| 覆盖门禁卡片 | Card + 进度条 | ≥60%=success，<60%=warning | 加载态 skeleton，空态 EmptyState |
| 接入配置表单 | Input/Select 栅格 2 列（<1024 单列） | 必填=normal，URL 校验失败=destructive | Select 空值用 sentinel |
| 提取质量徽标 | Badge 12px | chunked=info，fallback=warning，truncated=danger | — |
| 计划 auto_ui 开关 | Switch | — | 默认开，disabled 态可读 |

## 2. 布局与响应式
| 断点 | 布局 |
| <768px 单列 / 768–1023 两列 / ≥1024 矩阵全宽 |
覆盖矩阵在窄屏转卡片列表；接入配置在 <1024 单列。

## 3. 状态设计核对（四态）
| 组件 | Loading | Empty | Error | 未启用(503) |
|------|---------|-------|-------|-------------|
| 覆盖矩阵 | Skeleton | 「尚无模块树，先确认版本差异」 | 重试按钮 + 错误文案 | — |
| 提取质量 | — | 无 meta 时不显示 | 接口失败 toast | — |
| auto_ui | — | — | — | 无 UI 编译能力时提示 |

## 4. 设计 QA 走查发现
无历史页面改动冲突；新增面板遵循 cameltv-ui-conventions（状态徽标/间距/深色模式/加载空态）。

## 5. 设计签核
结论：通过（实现阶段由 Dev 按本规范落地，QA 附截图证据）。
