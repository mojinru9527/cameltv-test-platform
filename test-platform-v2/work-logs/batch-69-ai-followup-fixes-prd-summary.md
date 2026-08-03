# Batch 69 — PRD Summary（AI 验收跟进修复：C68-2/C68-3/C68-4）

> **Product (🟦)** | Date: 2026-08-03 | Status: Approved（用户已确认执行器 Codex 并授权启动）

## 1. 问题陈述

Batch 68 验收中 Leader 判定「有条件通过」，遗留三项代码/登记跟进（C68-2/C68-3/C68-4）：

1. **C68-2（P2）**：`TestCaseUpdate` 不暴露 `source_doc_id`，需求-用例关联只能以 DB 种子方式完成；
   需要 API 层支持，替换种子方式并可在前端/脚本直接建立关联。
2. **C68-3（P2）**：`POST /requirements/{doc}/generate`（AI 用例生成）对大型需求文档单次调用，输出超过
   `AI_MAX_TOKENS` 截断 → 400 拒绝（batch-68 实测 147 功能点文档连续两次截断）。需要分批/分模块生成并合并。
3. **C68-4（P1）**：正式域名发布演练已 200（Vercel/Railway），但发布决策未登记（是否启用自定义域名等）。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| C68-2 | API 不支持 source_doc_id | `TestCaseUpdate.source_doc_id` 可写；用 API 为 50 条用例建立需求关联（替换 DB 种子） | 本批 QA |
| C68-3 | 147 功能点文档生成截断失败 | 同一文档 AI 生成成功（分批合并），0 条假数据；小文档行为不变 | 本批 QA |
| C68-4 | 演练 200 未登记决策 | 交付清单登记演练结论与待决策项 | 本批 |

## 3. 非目标（本次不做）

- **C68-1 / J15 外部页 / J16 媒体**：需用户提供授权/样本，保持 DEFERRED。
- **C58-01/03/04、C63-1、C64-1/2**：外部或独立批次，维持原状态。
- **不改数据库结构**：`source_doc_id` 列已存在（TestCase.source_doc_id），仅补 API 字段与校验。
- **不引入新依赖**：分批策略用现有 `_call_ai_api` 复用。

## 4. 用户故事 + 验收标准

- As a 测试人员，I want 通过 API 为用例关联来源需求文档，so that 追溯矩阵不再依赖手工 DB 种子。
  - 验收：Given 用例与文档存在 / When PUT /test-cases/{id} 提交 source_doc_id / Then 用例关联生效且 `/trace/requirement/{doc_id}` 计数更新。
- As a 产品，I want 大型需求也能一次生成完整用例，so that 253 功能点级文档不再因输出截断返工。
  - 验收：Given 147 功能点文档 / When 调 generate / Then 返回成功且 functional_cases 非空；N：单块截断重试后仍失败仅告警该块，不产出假用例。
- As a 发布负责人，I want 演练结论与决策项登记，so that 正式域名发布可继续推进。
  - 验收：Given 演练 200 / When 登记 / Then 交付清单含结论 + 待用户决策项。

## 5. 技术考量

- C68-3 分批策略：按模块拆分，单次调用功能点上限（如 25 个）控制输出体积；每块独立调用 `_call_ai_api`，合并
  functional_cases；块级截断重试 1 次，仍失败记 warning 且不整体失败（无假数据）。
- C68-2：`TestCaseUpdate` 增加 `source_doc_id: Optional[int]`，沿用现有 update_case（setattr 路径），补校验
  （文档存在且属于同项目）。
- 测试：ai_service 分批合并单测（mock LLM 截断场景）+ test_case update schema 单测 + 运行中平台端到端验证。

## 6. 上线计划

| 阶段 | 成功门槛 |
|------|---------|
| Slice 1 C68-2 | 单测 + API 实测（50 用例关联替换种子） |
| Slice 2 C68-3 | 单测（分批/截断/合并）+ 大文档端到端生成成功 |
| Slice 3 C68-4 | 交付清单登记 |
| 收口 | QA PASS + Leader APPROVED + PR 合入 |

## 7. 条件对账（C-CONDITIONS.md）

- **纳入**：C68-2、C68-3、C68-4；C63-2（禁止假证据）；C63-3（引用 C 条件）。
- **豁免/延后**：C68-1（授权缺失，DEFERRED）、C58-01/03/04、C63-1、C64-1/2。
