# Batch 94 — PRD Summary（AI 产物批量审核/采纳工作流 UI）

> **Product (🟦)** | Date: 2026-08-05 | Status: Review

## 0. 批次模式判定（C75-1 强制）

```markdown
mode: full
判定理由: 新增后端批量端点（新接口）+ 前端批量交互（新行为）→ 完整批次（六部门）。
```

## 1. 问题陈述

AI 审核台（ArtifactReviewTab）只有单条采纳/驳回/导入，25 条 AI 用例要逐条点 3 次——批量场景（AI 一次生成 25 条）操作成本高，且 C26KB-C3 的 C7 三个检查点（批量采纳/批量驳回/批量导入）因此长期未达标（batch-91 复核 25/28）。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| 批量采纳/驳回/导入 | 无（仅单条） | 勾选/全选 → 批量操作，toast 计数，状态即时刷新 |
| 后端接口 | 仅单条 | 3 个批量端点（approve/reject/import），静态路径优先注册 |
| 治理 | 批量导入默认关 | `ai_artifact_allow_batch_import` 开关保持（默认 False，批量导入仍需显式开启） |
| C26KB-C3 | 25/28（89.3%） | 补齐 C7 后 28/28（100%）关闭 |
| 门禁 | — | typecheck/build/vitest/pytest/E2E 全绿 |

## 3. 非目标（本次不做）

- **不改单条审核流程**：单条采纳/驳回/导入保持现有行为。
- **不放开治理门**：批量导入的 `ai_artifact_allow_batch_import` 默认仍 False（生产逐条导入），仅环境显式开启。
- **不做跨页选择**：勾选仅当前页（分页内），不跨页记忆。

### C 条件纳入/豁免

| C 条件 | 处理 |
|--------|------|
| C26KB-C3 | **纳入**：补齐 C7 批量操作后复测 28/28 关闭 |
| C91-1 / C92-1 | **纳入**：统一「人工审核」交互范式（复用 Dialog 模式） |
| C75-1/2/3、C76-2、C78-1、C86-1 | 本批遵守 |

## 4. 用户故事 + 验收标准

- As a **测试人员**, I want 勾选多条 AI 产物批量采纳/驳回/导入，so that AI 生成 25 条用例不再逐条点击。
  - Given 审核台有 5 条产物（3 pending + 2 approved），When 全选 → 批量采纳，Then 全部转已采纳且 toast「已采纳 N 条」。
  - Given 已采纳产物，When 勾选 → 批量导入，Then 转已导入且生成对应用例。
  - Given 未开启批量导入开关，When 批量导入 >1 条，Then 403 提示逐条导入（治理不放松）。

## 5. 技术考量

- 后端：`ArtifactBatchReviewRequest/ArtifactBatchImportRequest` schema + `artifact_service.batch_approve/batch_reject`（去重、逐条复用单条逻辑）+ 复用 `import_artifacts_to_test_cases`（含治理门）；路由注册在 `{artifact_id}` 之前（静态路径优先，避坑清单）。
- 前端：ArtifactReviewTab 增加勾选列 + 全选（当前页可操作）+ 批量按钮 + 批量 Dialog；`api/knowledge.ts` 增加 3 个批量函数。
- 测试：后端 `test_ai_artifact_batch.py`（7 项：批量/去重/missing/隔离/治理门/路由顺序）；前端 E2E `batch94-artifact-batch-review.spec.ts`（批量采纳+导入）。
