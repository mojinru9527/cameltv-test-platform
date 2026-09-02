# Batch 209 — 执行链专门批次 — Design Spec
> **Design (🎨)** | Date: 2026-09-02 | Status: 就绪

## 架构决策
| 决策 | 内容 |
|------|------|
| D1 命令分派 | `_execute_commands_hook` 按 `cmd.driver` 分派：`api`→HTTP（现逻辑）；`browser`→有 `browser_runner` 回调执行，否则步骤 BLOCKED(no_browser_runtime)，绝不发 HTTP；`assertion`→跳过（Oracle 阶段）；未知→BLOCKED(unknown_driver)。保持 schema_version v2（commands）解析。 |
| D2 运行时回调 | drivers 模块暴露 `register_browser_runner(fn)` 供未来真实 Playwright worker 注入（本批默认无 → BLOCKED）。 |
| D3 自动 binding | `materialize_bindings_for_plan(db, plan_version)`：对 plan 的 scenario_version 下 `review_status=APPROVED` 的 oracle，匹配命令 observations（observation.key == oracle.oracle_key 或 observation.key.endswith(oracle.oracle_key) 或 command.id==oracle.oracle_key），按 observation.type 推导 binding_type（HTTP_STATUS→API_STATUS；HTTP_RESPONSE→API_JSONPATH(selector=oracle.target.jsonpath?)；UI_TEXT/UI_VISIBLE→同名），source_step_key=command.id，status ACTIVE；幂等 upsert。 |
| D4 接线 | `command/service.approve_version` 与 `activate_version` 成功后调用 materialize（幂等；缺 binding 不阻断审批，run 前 fail-fast 兜底）。 |
| D5 C6b 门控 | `agent._agent_unavailable_reason(db=None, project_id=None)`：db+project 时优先 `ai_client.is_configured`；否则 env（settings.ai_enabled/api_key）。触发端点带 db/project 时传入。 |

## 兼容性
- api driver 命令行为不变（现有 v31-v34 测试保持）；browser 命令从“误跑 HTTP”变“显式 BLOCKED”——属期望语义变更，更新相关断言。
- 无 DB/API 变更。

## 设计签核
结论：通过（真实浏览器运行时接入列为 C1b 后批）。
