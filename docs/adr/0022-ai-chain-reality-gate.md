# ADR-0022 — AI 全链路 Reality Gate（Batch 207）

> Status: Accepted (2026-09-02) | Owner: qa-team | Tags: aitde, ai, intelligence, trust

## 背景

代码审计（main@34225781）确认 AITDE 评审链的 ``LegacyAIServiceProvider`` 5 个方法全部
回退到确定性基线，``ai_enabled`` 无生产入口；确定性占位产物被标成 AI 溯源且不可执行；
``ActionPlanner`` 无调用方；Oracle binding 无生产者；AI 治理/闭环为空转表面。

## 决策

- **D1 提供者分型**：`DeterministicScopeProvider`（规则基线）+ `AiIntelligenceProvider`（真实同步 LLM）。
- **D2 工厂**：`build_intelligence_provider(db, project_id)` 依项目 AI 配置选择；未配置/禁用走确定性。
- **D3 同步客户端**：`intelligence/llm_sync.py`（resolve → sync httpx chat/completions → JSON 解析；
  超时先于 HTTPError 分类；契约破损 raise 不静默降级）。
- **D4 提示词接线**：主链 4 模板（scope/ambiguity/contract/scenario）由 AI provider 读取并映射到既有 Pydantic schema。
- **D5 溯源诚实**：`created_by_type` = AI 或 DETERMINISTIC；oracle `source_type` = `AI_INFERRED`（required=False）
  或 `RULE_BASELINE`（required=False）；不再伪造 AI 归属。
- **D6 歧义触发**：确定性只对 EXCLUDE/低置信/缺 reason 产出歧义，消除“每项必歧义”。
- **D7 服务端 planner**：`command.plan_from_scenario` 用 ActionPlanner 生成 DRAFT；
  `/action-plans/generate` 缺 plan 时服务端生成（向后兼容客户端）。
- **D8 Oracle 信任升级**：`review_oracle(promote=True)` 将 AI_INFERRED 显式升级为 TESTER_APPROVED + APPROVED；
  缺省保持 V3.9 不变量（AI 永不静默成为 Required）。
- **D9 Binding 生产者**：oracle-binding create/list API（幂等 upsert，ACTIVE）。
- **D10 fail-fast**：run 创建时，受信（REQUIRED+APPROVED）oracle 无 plan/binding 直接 400，不再静默 NOT_EVALUATED。
- **D11 闭环诚实化**：run 完成后自动规则 triage（幂等）；hypothesis CONFIRMED → TRIAGE suggestion；
  移除“real LLM runs first”等误导表述。
- **D12 降级语义**：AI 配置存在但调用瞬时失败 → ai_ops 记 FAILED 并用 DETERMINISTIC 基线降级（溯源诚实）。

## 移交的 Leader 条件（非本批实现）

- C1：Command IR 方言统一（browser ActionPlanner / HTTP 执行 / oracle observations）与执行器路由。
- C2：从真实 DOM/API/DB 观测自动物化 oracle binding。
- C3：PromptEvaluation 黄金回归 runner（LLM 调用注入）。
- C4：Smart Regression 生产快照 store-backed loader（OPENAPI/DB_SCHEMA/PRD/UI_DISCOVERY）。
- C5：统一既有 4 套 LLM 调用栈（ai_service/llm_json_client/legacy_cutover/api_generalization）。
- C6：AI 可用性门控统一（项目级 resolve vs 环境级 settings）。
- C7：knowledge.module_extractor AI 辅助模块边界检测实现。

## 关联

- provider/llm_sync/runner: `app/modules/aitde/intelligence/`
- 工件: `work-logs/batch-207-ai-chain-reality-gate-*`

