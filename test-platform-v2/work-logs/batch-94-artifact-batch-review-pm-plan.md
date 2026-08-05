# Batch 94 — PM Plan（AI 产物批量审核/采纳）

> **PM (🟨)** | Date: 2026-08-05

## 规格摘要

**原始需求**: 批量采纳/驳回/导入（PRD §1–§5）。**目标时间**: 1.5 个工作日。

## 开发任务

### Slice 1: 后端批量端点（TDD）
- schemas：`ArtifactBatchReviewRequest{ids,comment}` / `ArtifactBatchImportRequest{ids}`
- service：`batch_approve` / `batch_reject`（去重+逐条复用）；复用 `import_artifacts_to_test_cases`
- router：`/ai-artifacts/batch-approve|batch-reject|batch-import`（注册于 `{artifact_id}` 之前）
- 测试：`test_ai_artifact_batch.py`（7 项）
- 验收：pytest 7/7

### Slice 2: 前端批量交互
- `api/knowledge.ts`：3 个批量函数
- ArtifactReviewTab：勾选列 + 全选 + 批量按钮 + Dialog（驳回必填原因）+ toast 计数 + 刷新
- 验收：typecheck；E2E 批量采纳+导入通过

### Slice 3: QA 门禁 + C 条件关闭
- typecheck/build/vitest/pytest/scan/audit；C26KB-C3/C91-1/C92-1 关闭

## 质量要求

- [x] 无障碍：全选/行勾选 aria-label；筛选 Select aria-label
- [x] 无 N+1：批量走后端批量端点，前端不发逐条请求
- [x] 治理：批量导入受开关约束（默认 False）
- [x] 单元/E2E 测试
