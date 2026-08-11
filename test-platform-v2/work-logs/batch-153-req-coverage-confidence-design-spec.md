# Batch 153 — Design Spec（需求覆盖率 + AI 置信度）

> **Design (🎨)** | Date: 2026-08-11 | Status: 就绪

## 0. 技术体系确认
后端 FastAPI + SQLAlchemy；无 UI 变更（审核台已展示置信度）。

## 1. 覆盖率口径
| 指标 | 口径 |
|------|------|
| 需求文档数 | RequirementDocument.project_id |
| 有用例文档数 | distinct TestCase.source_doc_id（project 内、is_deleted=False） |
| requirement_coverage_rate | 有用例文档数 / 文档数 ×100（上限 100%） |

## 2. 置信度规则
| 来源 | 规则 |
|------|------|
| LLM 显式 confidence | 取输出中的 confidence（0-1 收敛） |
| LLM review_items | items 的 confidence 平均值 |
| 兜底（Agent 产物） | 0.6 |
| 差异补齐（WikiDiffItem） | 按 severity：P0→0.9 / P1→0.85 / P2→0.75 / P3→0.65 |
| Lint 转换（WikiLintIssue） | 同上按 severity |

## 3. 状态核对
| 组件 | 前 | 后 |
|------|----|----|
| 审核台置信度列 | 0% | 0-100% 合理值 |
| 追溯需求覆盖率卡 | 0% | 按实际关联 |

## 4. 设计签核
结论：通过
