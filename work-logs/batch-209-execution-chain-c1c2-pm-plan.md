# Batch 209 — 执行链专门批次 — PM Plan
> **PM (🟨)** | Date: 2026-09-02

## 规格摘要
PRD §1（C1/C2/C6b）。范围: test-platform-v2/backend + docs/adr + work-logs。分支: feature/batch-209-execution-chain-c1c2。

## 开发任务
### [x] S0: 部门工件
### [ ] S1: execute_commands 按 driver 分派（C1）
- workflow/drivers._execute_commands_hook：`driver=="api"` 走现有 HTTP；`driver=="browser"` 无运行时 → 步骤 BLOCKED(no_browser_runtime)（有运行时回调则执行）；`driver=="assertion"` 跳过（oracle 阶段负责）；其它未知 driver → BLOCKED(unknown_driver)。
- 涉及: workflow/drivers.py；测试 tests/aitde/v34/test_api_driver.py 扩展 + 新 test_execute_dispatch.py
### [ ] S2: plan 审批时自动物化 binding（C2）
- 新增 scenario/repository.materialize_bindings_for_plan(db, plan_version_id)：对 plan 的 scenario_version 中 review_status=APPROVED 的 oracle，按其 oracle_key 匹配命令 observations（observation key 含 oracle_key 或命令 id==oracle_key），自动 upsert ACTIVE binding（类型由 observation.type 推导：HTTP_STATUS→API_STATUS、HTTP_RESPONSE→API_JSONPATH、UI_*→UI_TEXT/VISIBLE）。
- 接入 command/service.approve_version 或 activate_version（幂等）。
- 涉及: scenario/repository.py、command/service.py；测试 test_batch209_materialize.py
### [ ] S3: C6b 项目级门控（agent 等无 DB 端点）
- agent._agent_unavailable_reason 增加可选 db/project；有 DB 时走 ai_client.is_configured，无 DB 回退 env；主触发端点接线。
- 涉及: api/v1/agent.py、services/ai_client 已有；测试 test_ai_gate_project_context.py
### [ ] S4: QA 硬门禁 + 报告 + ADR-0024

## 质量要求
- ruff F821 / 受影响 pytest / 全量 backend pytest；语义变更逐条记录；无迁移/API 路由变更。
