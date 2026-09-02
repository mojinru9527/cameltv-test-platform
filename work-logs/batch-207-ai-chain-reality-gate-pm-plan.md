# Batch 207 — AI 全链路 Reality Gate — PM Plan
> **PM (🟨)** | Date: 2026-09-02

## 规格摘要
**原始需求**: PRD §1 六类问题（provider 空壳/占位不可执行/无服务端 planner/假溯源/治理空转/loader 缺失）。
**目标时间**: 单批次内完成；切片粒度 30–60 分钟。**范围**: test-platform-v2/backend + work-logs 文档。**分支**: feature/ai-chain-reality-gate。

## 开发任务（Dev Slice，按序提交；每片先测后码）
### [x] S0: 部门工件（PRD/PM/Design + 看板） — docs
### [ ] S1: 统一同步 LLM client + AI provider 真实现 + 工厂
**描述**: 新增 `intelligence/llm_sync.py`（resolve→sync httpx chat/completions→json 解析，含 timeout/HTTP/JSON 分类错误与 `AIProviderUnconfiguredError` 透传）；`provider.py` 增加 `AiIntelligenceProvider`（5 方法各读对应提示词模板→LLM→`model_validate` 到既有输出 schema），`build_intelligence_provider(db, project_id)`（resolve 成功→AI，否则 deterministic）；两个 provider 暴露 `mode`/`label`。
**验收**: mock LLM 下 5 方法产出通过 schema 校验；无配置时返回 deterministic；错误分类正确（超时先于 HTTPError）。
**涉及文件**: app/modules/aitde/intelligence/llm_sync.py(新) / provider.py / prompts/*.txt(读取)
### [ ] S2: 4 service 接线工厂 + ai_ops 生产者 + operation_id 回传
**描述**: scope/ambiguity/contract/scenario service 默认 `build_intelligence_provider(db, project_id)`；AI 模式包 `ai_ops create_operation→mark_*`；API 返回 operation_id；确定性模式不写 ai_ops、`created_by_type=DETERMINISTIC`。
**验收**: AI(mock) 路径落 operation 记录并返回 id；deterministic 不落；既有 service 测试保持（语义断言更新见 QA）。
**涉及文件**: scope/service.py、scope/ambiguity_service.py、contract/service.py、scenario/service.py、scope/repository.py、ambiguity_repository.py、contract/repository.py、scenario/repository.py、api/v2/mission_scope.py、mission_ambiguities.py、mission_contracts.py、mission_scenarios.py
### [ ] S3: 确定性占位诚实化（provenance + 歧义 + oracle 形状）
**描述**: deterministic analyze_scope confidence=0.95；detect_ambiguities 仅在 EXCLUDE 或低置信触发（消除“每项都歧义”）；design_intents/contract/scenario 真实 source_refs 尽量回填；deterministic oracle `source_type=RULE_BASELINE`、`required=False`、review_status PROPOSED；AI 路径 oracle `AI_INFERRED/required=False`（符合 golden 不变量）。
**验收**: 无配置默认流 ambiguity_count=0/intent_count≥1；oracle 不再 required=True；golden AI schema 不变量测试保持。
**涉及文件**: intelligence/provider.py、tests/test_aitde_ambiguity_service.py(语义更新)
### [ ] S4: 服务端 ActionPlanner 生成 + plan 校验 fail-fast + binding/promote API
**描述**: command/service 增加 `plan_from_scenario(db, scenario_version_id, route)`（读 when_model+oracles→ActionPlanner.plan_and_validate→create_version DRAFT）；`/action-plans/generate` 缺 plan 时服务端生成；scenario/repository `review_oracle(promote=True)`→`TESTER_APPROVED+APPROVED`（默认保持 guard）；新增 binding 创建/列表 API（oracle→binding_type/source_step_key/observation_selector）；execution create_run 校验 plan/binding 存在否则 400。
**验收**: 单测覆盖 generate-from-scenario、promote、binding、fail-fast。
**涉及文件**: command/service.py、api/v2/action_plans.py、scenario/repository.py、scenario/schemas.py、api/v2/oracle_bindings.py(新)、execution/service.py
### [ ] S5: V38 闭环诚实化 + 自动 triage + suggestion 生产者
**描述**: run 完成后自动 FailureTriageAgent.triage（确定性规则、诚实标注 no-LLM）；hypothesis confirm→自动建 suggestion；修正「real LLM first」等误导 docstring；PromptEvaluation 标注 harness=C 条件。
**验收**: 单测：失败 run 自动产 hypothesis；confirm 后 suggestion 出现。
**涉及文件**: execution/service.py(完成钩子)、ai_closed_loop/service.py、repository.py、api/v2/ai_closed_loop.py(如需)
### [ ] S6: Smart Regression loader + 门控/调用栈文档化 + 过期注释清理
**描述**: providers 增加 env/data-source 快照 loader（source_ref 解析 + 明确错误）；version_differ「stub」过期注释修正；P2-1/P2-2 决策写 ADR/CLAUDE.md 备注（不重构既有栈）。
**验收**: loader 单测；docs 更新。
**涉及文件**: smart_regression/providers.py、services/knowledge/version_differ.py、docs/adr/0xxx-ai-chain-reality-gate.md(新)、CLAUDE.md
### [ ] S7: QA 门禁全绿 + 报告
**描述**: ruff F821 + 受影响 pytest + 全量 backend pytest（记录基线失败集合）；必要时 frontend typecheck 不动。
**验收**: 无新增失败。

## 质量要求
- [ ] 后端：ruff F821 / 相关 pytest / 全量 pytest 记录
- [ ] 每切片 git commit（总确认前不 push）
- [ ] 语义变更（S3/S4）逐条在 QA 报告列明新旧行为与测试更新
- [ ] 新增 API 同步 OpenAPI（FastAPI 自动）+ 文档
- [ ] 无 console/print/debugger、无密钥、无 .db/.bak 提交
