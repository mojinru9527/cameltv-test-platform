# ADR-0023 — AI 链 C 条件收敛（C3/C4/C5/C6/C7，Batch 208）

> Status: Accepted (2026-09-02) | Owner: qa-team | Tags: ai, llm-client, evaluation, loader

## 决策
- **C5 共享 LLM client**：新增 `app/services/ai_client.py`（`resolve_config`/`is_configured`、
  `chat_completions`/`chat_completions_full` 与 async 对应、`parse_json_object`，统一 settings 全局开关 +
  项目 resolve、重试与错误分类）。四栈收敛：`intelligence/llm_sync`、`knowledge/llm_json_client`、
  `legacy_cutover.extract_ai_draft`、`ai_service._call_ai_api`（传输段）。各调用方保留自身
  sanitize/prompt/health/salvage 逻辑。
- **C6 门控统一**：`is_configured(db, project_id)` 成为项目级门控事实源（全局 settings.ai_enabled 仅作
  kill-switch）。无 DB 环境（agent.py 等）仍用 env 门控并注释分歧——彻底统一需这些端点先获得 DB 上下文，
  记录为后续优化，不属本批阻断。
- **C3 PromptEvaluation golden runner**：`PromptEvaluationService.run_golden` 用共享 client 逐样例调用模型并
  评分，成功才写 `_trusted=True` 的 ModelEvaluationRun；未配置/调用失败 → BLOCKED 且不写 trusted。
- **C4 Smart-Regression store loader**：默认 loader 支持 `inline:`、`env_snapshot:<id>`（EnvironmentSnapshot
  服务版本 → ENVIRONMENT diff 形状）、`data_source:<id>:<kind>`（DataSource.config_json，kind 白名单）。
- **C7 module_extractor AI 边界**：`ai_boundary_suggestions_sync`（共享 client，失败/未配置返回 []）+
  `extract_module_tree(boundary_suggestions=...)` opt-in 应用；确定性默认行为不变。

## 移交（后续）
- C1 Command IR 方言统一、C2 binding 自动物化：仍依赖真实 UI/API 运行时，留待专门批次。
- C6 无 DB 端点的 env→project 门控迁移（需端点改造）。

## 关联
- 工件: work-logs/batch-208-ai-chain-c-conditions-*
