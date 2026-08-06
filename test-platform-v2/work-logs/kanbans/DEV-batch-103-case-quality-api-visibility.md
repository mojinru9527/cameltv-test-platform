# 🗂️ Dev 部门项目看板 — Batch 103（用例质量与接口可视优化）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 体育平台用例质量（规范对齐/覆盖度）+ 接口用例参数/断言/结果可视 |
| **关联 PRD** | [batch-103-case-quality-api-visibility-prd-summary.md](../batch-103-case-quality-api-visibility-prd-summary.md) |
| **看板创建** | 2026-08-06 |
| **执行器** | codex（用户确认未来 10 版本沿用） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-103-case-quality-api-visibility |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 批次工件 + 需求登记 | ✅ | 🔄 | ⏳ | ⏳ | ⏳ | **当前位置**：PRD/PM/Design + C 条件 + backlog |
| 2 | 用例规范对齐：AI 生成注入 tests/test-case-standards 方法与正负向/边界要求 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | backend ai_service 提示词 |
| 3 | 覆盖度提升：用户端 92 FP → 目标 ≥2-3 条/FP（正/负/边界） | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 生产库补生成 + 重导入 |
| 4 | 接口用例可视：请求参数/断言/实际结果回填展示 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | api case schema + 前端 |
| 5 | QA + Leader + 一次总确认 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | push → Draft PR → checks → 合入 |

## 📍 当前位置

```
Batch 103 — 用例质量与接口可视优化（启动）
├── ✅ Batch 102 已合入 main（PR #140）
├── ✅ 用户反馈已确认：用例规范/覆盖度 + 接口用例可视
└── 🔄 批次工件 + 需求登记
```
