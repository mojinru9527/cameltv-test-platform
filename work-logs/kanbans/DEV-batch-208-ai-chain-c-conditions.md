# 🗂️ Dev 部门项目看板 — Batch 208 AI 链 C 条件

## 📋 项目信息
| 字段 | 值 |
|------|-----|
| **项目名称** | AI 链 C 条件（C3/C4/C5/C6/C7） |
| **关联 PRD/PM** | work-logs/batch-208-ai-chain-c-conditions-{prd-summary,pm-plan,design-spec}.md |
| **分支** | feature/batch-208-ai-chain-c-conditions（executor=codex） |
| **看板创建** | 2026-09-02 | **最后更新** | 2026-09-02 |

## 🎯 交付切片进度
| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | 部门工件 | ✅ | ✅ | ✅ | ⏳ | ⏳ | docs |
| 1 | 共享 LLM client（C5/C6） | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 2 | 四栈传输收敛（C5） | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 3 | 门控统一 helper（C6） | ✅ | ✅ | ✅ | ⏳ | ⏳ | is_configured + ADR-0023 |
| 4 | PromptEvaluation runner（C3） | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 5 | Smart-Regression store loader（C4） | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 6 | module_extractor AI 边界（C7） | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 7 | QA 硬门禁 + 报告 | ✅ | ✅ | ✅ | ✅ | ✅ | 已合入 #385 |

## 📍 当前位置
Batch 208 — 已合入 main（PR #385, a5b09e7c）。

## ⚠️ 阻塞与风险
| 阻塞项 | 严重度 | 描述 | 需要谁 |
|--------|:------:|------|--------|
| C1/C2 | P2 | IR 方言统一与 binding 自动物化依赖真实运行时 | 后批 |
