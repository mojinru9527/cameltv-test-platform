# Batch 153 — 需求覆盖率口径 + AI 产物置信度（PRD Summary）

> **Product (🟦)** | Date: 2026-08-11 | Status: Approved | Mode: full

mode: full
理由: 引入新行为（AI 产物置信度计算）+ 覆盖率口径重构，按 SKILL.md 判定完整批次。
非目标: 数据集参数化（C147-8）、知识图谱治理（C147-9）、UI 映射回写（C151-1）、孤儿文件/env 统一入口（C152-1）不在本批。

## 0. 背景与来源
- 来源：Batch 126 遗留 C126-2/C126-3（2026-08-09 登记），落地文档 Batch 152 原计划「覆盖率/置信度」部分。
- 现状：4 文档 / 476 AI 用例但覆盖率 0%；85 条待审 AI 产物置信度全 0%。

## 1. 问题陈述
1. **覆盖率 0%**：项目级需求覆盖率 `req_with_cases` 依赖 `RequirementDocument.imported_count>0`；AI 生成用例（case_generation_service 路径）只写 `source_doc_id` 不更新计数器 → 覆盖率恒 0。
2. **置信度 0%**：`AiArtifact.confidence` 三处创建均未计算：agent_orchestrator（缺省 0）、compare_service（写死 0.0）、lint_service（缺省 0）→ 审核台全部 0%。

## 2. 成功指标
| 指标 | 基线 | 目标 |
|------|------|------|
| 需求覆盖率（有 AI 用例文档） | 0% | 按实际 source_doc_id 关联 >0% |
| 待审 AI 产物置信度 | 全 0% | 按 AI 输出/严重度计算 0-1 |
| 口径一致性 | imported_count 双轨 | 覆盖率以实际用例关联为锚 |

## 3. 用户故事 + 验收标准
- As 测试经理, I want 需求覆盖率反映真实用例关联, so that 不再被 0% 误导。
  - Given 文档有 AI 生成用例（source_doc_id 已关联） / When 查看追溯/需求覆盖率 / Then 覆盖率 >0%。
- As 审核人, I want 待审 AI 产物带可信度, so that 按置信度排序审核。
  - Given 生成 AI 产物 / When 查看审核台 / Then confidence ∈ (0,1]，随来源（LLM 显式/平均/严重度）合理赋值。

## 4. 技术考量
- 覆盖率口径：`req_with_cases = distinct source_doc_id（is_deleted=False）∩ 项目文档数`；与单文档覆盖率（已按实际关联）对齐。
- 置信度模块：新增 `services/knowledge/artifact_confidence.py`：`severity_confidence()`（P0→0.9/P1→0.85/P2→0.75/P3→0.65）与 `artifact_confidence_from_output()`（优先 LLM 显式 confidence，其次 review_items 平均，兜底 0.6）。
- 三处创建接入：agent_orchestrator（LLM 输出）、compare_service（差异项 severity）、lint_service（lint severity）。
- 无 schema/迁移；仅后端计算逻辑 + 测试。
- 风险：LLM 输出 confidence 需类型校验与 0-1 收敛。

## 5. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全部 | checks 全绿 |
| 部署回归 | 测试经理/审核人 | 覆盖率 >0%、置信度非 0 |

## 6. 技能使用
- cameltv-bug-guard（口径一致性、类型校验）
