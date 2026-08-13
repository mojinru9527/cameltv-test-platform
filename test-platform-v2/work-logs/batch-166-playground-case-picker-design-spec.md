# Batch batch-166-playground-case-picker — Design Spec
> **Design (🎨)** | Date: 2026-08-13 | Status: 就绪

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind + CVA；语义类（bg-muted / text-muted-foreground / border / variant）。

## 1. 组件规格表
| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|----------|---------|--------|
| 用例选择表 | 表格行 p-2，sticky 表头 | 标题 font-medium，次级 text-muted-foreground | hover bg-muted/50 |
| 筛选 Select | w-[180px]/[130px] | 默认中性 | focus ring |
| 批量按钮 | size 默认 | primary/secondary | loading 时 Loader2 |
| 结果卡 | border rounded-md p-3 | 成功 status-success / 失败 status-danger / TODO warning | - |

## 2. 布局与响应式
| 断点 | 布局 |
| <1024px | 筛选区 flex-wrap 纵向堆叠 |
| ≥1024px | 筛选区单行，结果列表单列 |

## 3. 状态设计核对
| 组件 | Loading | Empty | Error |
|------|---------|-------|-------|
| 用例列表 | 加载中文本 | 当前筛选无功能用例 | toast 错误 |
| 批量编译 | 按钮 loading | 无可选项禁用 | toast 错误 |
| 批量执行 | 按钮 loading | 无可选项禁用 | toast 错误 |

## 4. 设计 QA 走查发现
- 无 P0-P2；已核对 `cameltv-ui-conventions` Red Flags。

## 5. 设计签核
结论：通过
