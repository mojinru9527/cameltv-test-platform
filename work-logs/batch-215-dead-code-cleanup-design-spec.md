# Batch 215 — Design Spec
> **Design (🎨)** | Date: 2026-09-03 | Status: 就绪 | Executor: Codex | 完整批次

## 0. 技术体系确认
真实栈为 shadcn/ui + Radix + Tailwind + CVA；语义 UI 系统入口为 `@/ui`（`src/ui/index.ts`），业务页面禁止直接从 `@/components/ui` 或 `@radix-ui/*` 导入（`src/ui/index.ts` 头部约定）。本批为**删除型清理**，不新增/修改组件，重点核对删除不破坏渲染语义与导航。

## 1. 组件规格表
本批无新增组件。删除清单：
| 组件 | 处置 | 复核点 |
|------|------|--------|
| `pages/testplan/*` | 删除整页 + 自测 | 路由已重定向 /testcase；无菜单/命令面板/访客目录引用（batch-212 C7/C8 已清） |
| `pages/testcase/playground/index.tsx` | 删除 | `?tab=playground` 回落列表（不 404）；后端 /playground API 保留 |
| `components/ui/{accordion,breadcrumb,calendar,combobox,progress,toggle-group,toggle}` | 删除 | 未在 `@/ui` re-export、无代码引用（非 shadcn 语义系统保留件） |
| `components/ListToolbar`/`trust/VerificationLevelBadge`/`hooks/useA11y`/`usePaginatedList`/`pages/apitest/components/{ApiDebugPanel,EnvironmentBar}`/`pages/missions/StagePlaceholder`/`pages/runtime/components/{PolicyDecisionDrawer,RetryHistory}`/`pages/requirement/ExtractionModal` | 删除 | 引用审计零代码引用、无测试耦合 |

保留（非删除）：`components/foolproof/*`（B4 批量空态教学，待接线）、`components/TriagePanel.tsx`（有 eslint suppression 与后续复用）、`knowledge/components/{SphereTab,WikiLintPanel}`/`release-bundles/components/*`（有测试耦合）、`api/playground.ts`（M1 场景执行复用）。

## 2. 布局与响应式
无布局/响应式变化。删除的是不可达页面/组件，不影响现网断点（single/md/lg）。

## 3. 状态设计核对（四态）
无新增交互态。被删除组件的 Loading/Empty/Error 态随组件一并移除；主链路（工作台/版本验收/资产与更多）状态设计不变。

## 4. 设计 QA 走查发现（P0–P3，均附文件:行号）
### ⚪ P3-1 删除 testplan 后触控守护测试仍引用旧文件
`src/__tests__/touchTargetGuard.test.ts:10` 仍列出 `src/pages/testplan/index.tsx`。→ **建议**：随 Task 1 一并移除该条目，否则 vitest 读取失败。

### ⚪ P3-2 `@/components/ui` 语义边界
删除 `@/components/ui/*` 未用原语（accordion/breadcrumb/calendar/combobox/progress/toggle-group/toggle）不会破坏 `@/ui` re-export 链（`src/ui/index.ts` 未 re-export 它们）。→ **建议**：确认 `@/ui` 无 `components/ui` 导入即可安全删除。

## 5. 设计签核
结论：**通过**（删除型清理，无 UI 回归；P3-1 为测试清单联动项，随 Dev 一并处理）。
