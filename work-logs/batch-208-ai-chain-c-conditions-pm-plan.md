# Batch 208 — AI 链 C 条件 — PM Plan
> **PM (🟨)** | Date: 2026-09-02

## 规格摘要
原始需求: PRD §1（C3/C4/C5/C6/C7）。范围: test-platform-v2/backend + docs/adr + work-logs。分支: feature/batch-208-ai-chain-c-conditions。

## 开发任务
### [x] S0: 部门工件（PRD/PM/Design + 看板）
### [ ] S1: 共享 LLM client（C5/C6 基础）
- 新增 `app/services/ai_client.py`：`resolve_config(db, project_id)`（settings.ai_enabled 全局开关 + 项目 resolve）、`request_completions`(sync) / `arequest_completions`(async)、`parse_json_object`；统一超时/重试/错误分类（Timeout 先于 HTTPError）；`is_configured(db, project_id)`。
- 验收: 单测覆盖 sync/async 成功、重试、超时分类、JSON 错误、门控。
- 涉及: app/services/ai_client.py(新)
### [ ] S2: 四栈传输收敛（C5）
- `intelligence/llm_sync.call_llm_json` → 包装 sync client；`knowledge/llm_json_client.call_json_model` → 包装 async client（保留 sanitize/异常映射）；`legacy_cutover.extract_ai_draft` → sync client；`ai_service._call_ai_api` HTTP 段 → `arequest_completions`（保留 health/salvage/解析逻辑）。
- 验收: 相关既有测试全绿（llm_sync/llm_json_client/legacy_cutover/ai service/knowledge_ai_closure）。
- 涉及: 上述 4 文件
### [ ] S3: 门控统一 helper（C6）
- ai_client.is_configured 供 llm_json_client/legacy_cutover/intelligence runner 统一判定；agent.py 无 db 场景保留 env 判定并注明；ADR 增补。
- 验收: 单测 is_configured 在 resolve 失败/成功/settings off 三分支。
- 涉及: ai_client、llm_json_client、legacy_cutover、docs/adr
### [ ] S4: PromptEvaluation golden runner（C3）
- ai_closed_loop PromptEvaluationService.run_golden(db, project_id, suite, items)：调 async client 逐条评分 → accuracy → 写 ModelEvaluationRun(metrics._trusted) → 返回 check_regression 兼容 dict；失败/无配置返回 BLOCKED。
- 验收: mock LLM 单测产出 trusted run；insufficient/未配置 → BLOCKED。
- 涉及: ai_closed_loop/service.py、prompts(可内联)、schemas(如需)
### [ ] S5: Smart-Regression store loader（C4）
- providers: 默认 loader 增加 `env_snapshot:{id}`（EnvironmentSnapshot）与 `data_source:{id}:{kind}`（DataSource.config 解析，kind∈OPENAPI/DB_SCHEMA/PRD/UI_DISCOVERY）；未解析仍 raise 且消息含支持列表；registry 保持可注入。
- 验收: 单测 env_snapshot/data_source 装载 + 未解析 raise。
- 涉及: smart_regression/providers.py
### [ ] S6: module_extractor AI 边界建议（C7）
- 新增 `async ai_boundary_suggestions(db, project_id, pages)`：调 async client 返回 {suggested_merges:[...]}；未配置/失败返回 []；`extract_module_tree` 增加 `ai_boundary: bool = False` 参数，True 时合并建议（mock 单测）。
- 验收: mock LLM 产出 merge 建议并应用；未配置不改变默认结果。
- 涉及: services/knowledge/module_extractor.py
### [ ] S7: QA 硬门禁 + 报告

## 质量要求
- ruff F821、相关 pytest、全量 backend pytest 记录；语义变更逐条记录；无新迁移；API 无破坏。
