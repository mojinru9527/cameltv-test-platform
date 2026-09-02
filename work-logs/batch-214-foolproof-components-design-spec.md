# Batch 214 — Design Spec (foolproof-components)
> **Design (🎨)** | Date: 2026-09-03 | Status: 草稿

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind + CVA；语义类（bg-card/bg-muted/text-muted-foreground/border/variant）；复用 `ui/tooltip`、`ui/dialog`、`ui/button`、`Badge`、`EmptyState`。

## 1. 组件规格
| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|----------|---------|--------|
| PageIntro | 标题下 `text-sm text-muted-foreground`，`space-y-1`，可带 link | 无特殊色 | 纯展示 |
| TermTip | 词包 `TermTip`，`size-4` 问号图标 + tooltip `text-xs` | 无 | hover/focus 显示 tooltip |
| EmptyStateGuide | `Card` + `p-5`，三步行 `space-y-2`，主按钮 | 主按钮 `variant=default` | 每步可带 `action` 按钮 |
| StepWizard | 顶部步骤指示（已过/当前/未来），内容区 `min-h-[280px]`，底部 `Prev/Next/Finish` | 当前步骤 primary | 键盘可达 |
| AskAiButton | `size-4` 问号图标按钮，`aria-label`；Dialog `max-w-md` | `variant=ghost` | 打开弹层 |

## 2. 布局与响应式
| 断点 | 布局 | 变化 |
| <768px | 单列 | StepWizard 内容单列 |
| md+ | 多列内容（向导内容保持一列） | — |

## 3. 四态
页面保持 `AsyncState` 四态；`EmptyStateGuide` 为数据为空的「教学态」；不破坏原 `EmptyState` 兜底。

## 4. 中文映射 / TermTip 词表
`src/lib/terminology.ts` 复制 `docs/platform-refactor/03-terminology-map.md` 核心词（Mission/Contract/Oracle/Run/Evidence/Execution → 业务语言解释），禁止裸引擎词。

## 5. 设计 QA 走查（Red Flags 自检）
| Red Flag | 处理 |
|----------|------|
| 裸英文状态/术语 | TermTip 全中文业务解释 |
| 缺四态 | 复用 `AsyncState` |
| 触控<44px | StepWizard 按钮 `h-9`+；AskAi `size-4`（图标按钮加 aria-label，触控区 `p-2`） |
| 硬编码色 | 语义类，不写裸色 |

## 6. 设计签核
结论：交付 Dev（组件为真实栈；TermTip 词表内容由 03 术语映射；AskAi MVP 为前端内容表）。
