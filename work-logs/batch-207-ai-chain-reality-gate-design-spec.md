# Batch 207 — AI 全链路 Reality Gate — Design Spec
> **Design (🎨)** | Date: 2026-09-02 | Status: 就绪

## 0. 技术体系确认
后端 FastAPI + SQLAlchemy（本批不改前端，无 shadcn/Radix 面）。同步 LLM 调用对齐既有 `legacy_cutover` 先例。

## 1. 架构决策（后端）
| 决策 | 内容 |
|------|------|
| D1 Provider 分型 | `DeterministicScopeProvider`（mode=deterministic，纯规则降级）；`AiIntelligenceProvider`（mode=ai，真实 LLM）；协议 `IntelligenceProvider` 不变。 |
| D2 工厂 | `build_intelligence_provider(db, project_id)`：`settings.ai_enabled=False` → deterministic；`ai_config_service.resolve` 成功 → ai，`AIProviderUnconfiguredError`/异常 → deterministic。服务默认经工厂构造（显式注入仍优先）。 |
| D3 同步 LLM client | 新 `intelligence/llm_sync.py`：`resolve→httpx.post(chat/completions, timeout=60)→json 解析`；异常分类（`httpx.TimeoutException` 先于 `HTTPError`）；JSON 解析失败抛 `IntelligenceLLMError`。复用 `ai_config_service` 掩码/模型字段。 |
| D4 提示词接线 | 主链 4 模板（scope_analysis_v1 / ambiguity_intent_v1 / contract_builder_v1 / scenario_design_v1）由 AI provider 按方法读取；LLM 输出经 `json.loads` + `model_validate` 映射到既有输出 schema（ScopeAnalysisOutput/AmbiguityDetectionOutput/IntentDetectionOutput/ContractSnapshot/ScenarioDesignOutput）。 |
| D5 溯源诚实 | 落库 `created_by_type`：ai → `"AI"`，deterministic → `"DETERMINISTIC"`。Oracle `source_type`：ai → `AI_INFERRED`(required=False)，deterministic → `RULE_BASELINE`(required=False)。scope 保留真实 source_refs；ambiguity/intent/contract/scenario 能回填 scope/契约 refs 则回填，否则空数组（不再伪造 `artifact_id=0`）。 |
| D6 歧义触发 | deterministic `analyze_scope` confidence=0.95（规则置信）；`detect_ambiguities` 仅当 `decision==EXCLUDE` 或 `confidence<0.5` 或 reason 为空时产出。消除“每项必歧义”。 |
| D7 服务端 planner | `command/service.plan_from_scenario()`：读 scenario 版本 when_model+oracles+route → `ActionPlanner.plan_and_validate` → `create_version(... generated_by_type="PLANNER")` DRAFT。`/action-plans/generate` payload.plan 缺省时调用它（向后兼容）。 |
| D8 Oracle 信任升级 | `review_oracle` 增加显式 `promote: bool`：`promote=True` 时（human 明确动作）`source_type→TESTER_APPROVED` + `APPROVED` + 审计字段；缺省 False 保持 V3.9 不变量（AI_INFERRED 永不静默 APPROVED）。不变量测试不改。 |
| D9 Binding 生产者 | 新增 oracle-binding 创建/列表 API：`oracle_id + scenario_adapter_id + binding_type + source_step_key + observation_selector_json + status=ACTIVE`；唯一约束 (scenario_adapter_id, scenario_version_id, oracle_id)。 |
| D10 fail-fast | `execution/service.create_run`：scenario 版本存在 required+APPROVED oracle 时，校验存在 ACTIVE binding，否则 400 明示 `ORACLE_NOT_BOUND:{oracle_key}`；无 CommandPlanVersion 时 400 `PLAN_MISSING`。杜绝静默 NOT_EVALUATED。 |
| D11 闭环诚实化 | run 完成后自动 `FailureTriageAgent.triage`（确定性规则；模型字段仍可带 model_ref/prompt_version=null）；hypothesis CONFIRMED → SuggestionInbox 自动建 suggestion；修正“real LLM agent runs first”类 docstring；PromptEvaluation/Prompt 评估 runner 列为 C 条件不假装实现。 |
| D12 Smart Regression loader | registry 支持 `env_snapshot:{id}` / `data_source:{id}:{kind}` refs（loader 由 registry 注入 store-backed loader），未解析 ref 显式 raise（保持现语义）并给出可操作消息。 |

## 2. Command IR 方言（权威化 v2）
- **生成面（本批）**：`ActionPlanner` 仍是 browser/assertion 方言（V33 registry 校验）；服务端生成只做“DRAFT 候选”，不做运行时承诺。
- **运行面（现有）**：v2 plan 若含 browser 命令由 `browser/driver.BrowserDriver`（Playwright）执行；`workflow/drivers._execute_commands_hook` 的 HTTP 方言仅用于 `api/request` 命令 —— 本批在 registry 增加“命令 driver 与执行 hook 匹配”的**生成时 lint**（`browser` 命令在无观察源时拒绝进入 ACTIVE），把运行时歧义提前到生成期；执行器路由的完整统一列 C1。

## 3. 状态设计核对
| 对象 | 生成后 | 人类动作 | 可执行 |
|------|--------|----------|--------|
| ScopeItem | PROPOSED (DETERMINISTIC/AI) | approve/reject | — |
| Ambiguity | 仅真实信号 | resolve | — |
| ScenarioVersion | PROPOSED | approve | plan 前需 approve |
| Oracle | PROPOSED required=False | approve(+promote)=TESTER_APPROVED/APPROVED | 需 ACTIVE binding |
| CommandPlanVersion | DRAFT | approve→VALIDATED→ACTIVE | ACTIVE 后 run |

## 4. 设计走查（本批无 UI 变更）
- 无前端组件变更；API 契约向后兼容（generate 多一条缺省分支、新增 promote 字段/binding 端点）。
- 新端点全部置于既有 `require_aitde_v3` 权限路由组内。

## 5. 设计签核
结论：通过（含 C1–C7 移交下一批的显式边界，见 PM S6/PRD §3）。
