# Batch 208 — AI 链 C 条件 — Design Spec
> **Design (🎨)** | Date: 2026-09-02 | Status: 就绪

## 1. 架构决策
| 决策 | 内容 |
|------|------|
| D1 共享 client | `app/services/ai_client.py`：`resolve_config`（settings.ai_enabled 全局 kill-switch + 项目 resolve；未配置返回 None 语义由调用方处理）→ `request_completions/arequest_completions`（messages 数组、json_mode、max_tokens、重试=settings.ai_retry_attempts、timeout=settings.ai_timeout_seconds）→ `parse_json_object`。异常：`AiClientUnavailableError`（传输/HTTP 瞬时后）、`AiClientResponseError`（JSON/信封契约）。`httpx.TimeoutException` except 先于 HTTPError。 |
| D2 收敛 | llm_sync.call_llm_json → sync client+parse（异常重映射 Intelligence*）；llm_json_client.call_json_model → async client（sanitize 保留在调用方，异常重映射 LLMUnavailable/LLMResponse）；legacy_cutover.extract_ai_draft → sync client（json_mode）；ai_service._call_ai_api → 仅传输段换 arequest_completions(raw 返回 content 字符串)，health/salvage/error_kind 保留在 ai_service。 |
| D3 门控 | `is_configured(db, project_id)`：settings.ai_enabled False → False；resolve 成功 → True；AIProviderUnconfiguredError → False。调用方（runner/llm_sync/legacy）统一用它或依赖 client 内 resolve。agent.py（无 db）保留 env 门控 + 注释说明分歧。 |
| D4 C3 runner | `PromptEvaluationService.run_golden(db, project_id, suite, cases, model_ref=None)`：逐条 system+user 调 async client(json_mode)，比对 `expected`（== / 包含）算 accuracy；写 ModelEvaluationRun(metrics={accuracy,_trusted:True,...})；无配置/失败 → 返回 BLOCKED 且不写 trusted。阈值沿用 REGRESSION_THRESHOLD。 |
| D5 C4 loader | store loader 支持 `inline:`、`env_snapshot:{id}`（→EnvironmentSnapshot→服务版本/指纹 dict）、`data_source:{id}:{kind}`（→DataSource.config_json/url 快照 dict，kind 白名单）。解析失败 raise ValueError 且消息列支持格式与 C 条件引用。 |
| D6 C7 | `module_extractor.ai_boundary_suggestions(db, project_id, pages, model_ref=None)` async；`extract_module_tree(..., ai_boundary=False)`：True 且建议可用时合并 (folder→module) 并标记 meta；未配置/失败 → 返回空建议，不改变默认确定性输出。 |

## 2. 兼容性
- 新 client 对既有函数签名零破坏（包装层保持原签名）；ai_service 返回值 dict 契约不变。
- 无 DB/API 变更。

## 3. 设计签核
结论：通过（C1/C2 移交后批）。
