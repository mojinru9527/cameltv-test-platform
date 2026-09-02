# Batch 219 — Design Spec
> **Design (🎨)** | Date: 2026-09-05 | Status: 就绪 | Executor: Codex | 完整批次

## 0. 技术体系确认
`@/ui` 语义组件；Badge variant（default/destructive/outline/secondary/ghost）或 tone（success/warning/danger/info/neutral）。语义 token（batch54）禁止固定色板。

## 1. 组件规格表
| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|----------|--------|
| 放行卡片 | Card mt-4 | — | hover |
| 放行按钮 | md | primary(放行)/secondary(有条件)/danger(打回) | loading disabled |
| 结论 Badge | sm | outline/destructive | — |
| 发布包 ID Input | w-32 | — | focus ring |

## 2. 状态设计核对（四态）
| 场景 | Loading | Empty | Error | 未启用 |
|------|---------|-------|-------|--------|
| 放行 | toast + disabled | 未执行/无覆盖时预览为空 | toast.error（verdict/status 非法） | 未到 executed 拒放行 |

## 3. 设计 QA 走查发现（P0–P3）
### ⚪ P3-1 Badge success 无效
`variant="success"` 不存在（success 是 tone）。→ 改为 `variant="outline"`。

## 4. 设计签核
结论：**通过**（放行证据包 + 绑定发布包 + 通知；无固定色板）。
