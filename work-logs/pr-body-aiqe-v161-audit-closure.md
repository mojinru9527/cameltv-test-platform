# PR 提交包：AIQE V1.6.1 审计整改（`fix/aiqe-v161-audit-closure`）

> 本文件是推送前的 PR 描述草稿。按 AGENTS.md §2.4，**推送前需要用户在聊天中逐字确认**
> 「当前待推送范围如下。是否还有其他变动需要合并？」并明确授权本次 push；
> 本 Agent 未获得授权，因此 17 个提交仍在本地。

## 变更类型

- [x] 🐛 Bug 修复（A3 无法运行、AgentTask 永久 pending、镜像缺 sqlglot）
- [x] 🔒 安全（Agent 工具授权、TargetPolicy 负向证据、PG 只读验证器）
- [x] 🧪 测试（54+ 新增/强化测试）
- [x] 📝 文档（GA/Production/E2E 真值重写、审计台账）
- [x] 🚀 CI/CD（strict 门禁、evidence index、release gate、product TC 校验）

## 变更说明

针对 `CamelTv_AIQE_V1.6_Main_9bbbdbb_Code_Audit.md`（2026-11-24）的 P0/P1/P2 逐项整改：
18 项审计发现 → 12 项 CLOSED（代码/测试/证据），7 项 EXTERNAL（已登记 owner 与
解除动作），1 项为环境复现（已用本机全量回归替代）。

## AIQE V1.6 需求追踪（V16-025 强制）

- Issue / Requirement ID：V16-013, V16-014, V16-017, V16-019, V16-022, V16-023, V16-024, V16-025
- 业务结果（用户可观察）：发布判定从“文档声明”变为机器可校验证据；Agent 全链路可运行；
  E2E 负向/崩溃/归因场景可复现；GA 状态真实显示 `GA_NOT_READY` 及阻塞项。
- 正式入口（API / Worker / Job / CLI）：
  - `POST /api/v1/aiqe/runs`（launch）→ `job_consumer.claim_aiqe_jobs` → `execute_inprocess_job`
  - `POST /api/v1/aiqe/agent-tasks/{id}/run` → `enqueue_task_job` → `job_consumer` → `execute_task_job` → `run_plan`
  - `POST /api/v1/aiqe/defects/{id}/regressions`（`impact_base_sha` 服务端重算）
  - CLI：`scripts/aiqe/check_traceability.py`、`release_verdict.py`、`check_release_audit.py`、
    `check_audit_closure.py`、`run_product_tc.py`、`check_pg_readonly_role.py`、`check_branch_protection.py`
- 调用链（入口到 Driver/Assertion/Finalize）：
  - Run：API → launch_run → ExecutionJob → job_consumer → node_executor → driver → assertion → finalize
  - Agent：API → AgentTask(Draft→APPROVED→QUEUED) → Outbox/ExecutionJob → consumer → run_plan →
    AgentContext(tool_executor) → Agent Adapter → ToolRegistry(授权/审计) → AgentExecution
- 真实组件与 Mock 边界：
  - 真实：SQLite/PostgreSQL 模型、Worker claim/lease/fencing、reconciler、BoundToolRegistry、
    Evidence Resolver、Agent 状态机、Playwright（node_executor 层）。
  - Mock/Stub：LLM 用确定性 stub（模型供应商是可替换边界）；本地 SUT HTTP 服务；
    产品级 TC 的 Test 环境尚未接入（`run_product_tc.py` 缺 env 时输出 NOT_PROVEN）。
- 成功路径测试：`tests/e2e/aiqe/test_v16_017_platform_chain.py::test_tc_010_agent_task_platform_chain`
  等（见 `docs/aiqe/v1.6/traceability/requirements.yaml` 各条 `tests.success`）
- 拒绝/失败路径测试：`test_tc_005_metadata_endpoint_never_reached`、
  `test_write_tools_remain_unavailable`、`test_rejects_runtime_proven_without_ids` 等
- 异常/依赖缺失测试：`test_run_without_env_is_not_proven`、`test_unreachable_dsn_reports_fail`、
  `test_get_agent_accepts_model_for_every_agent`
- 并发/重试/竞态测试：`test_tc_007_worker_crash_recovery_and_duplicate_delivery`、
  `test_duplicate_delivery_is_idempotent`、`test_stale_worker_result_rejected`
- 安全影响（权限/Secret/网络/租户/外部副作用）：
  - 工具：写工具仍 UNAVAILABLE；`create_regression_plan` 只读提案（无副作用）；
    read_git_diff 仓库路径服务端固定、SHA 严格 40 位；project_id 不可覆盖。
  - Secret：TC-006 明文零落库断言保留；Handle 越权解析拒绝。
  - 网络：TargetPolicy 负向场景增加受控目标 0 请求断言。
- 迁移影响（迁移文件、回滚/前滚方案）：**无新增迁移**；基线 head 仍为
  `20261122_v16_catalog_post_merge`，`--check-baseline` 强制单头。
- 证据（commit SHA / CI Run / 测试报告 / Run ID / Job ID / Artifact ID）：
  - `docs/aiqe/v1.6/e2e/platform-results.json`（TC-PLATFORM-001..010 机器结果）
  - `docs/aiqe/v1.6/evidence/evidence-index.json`（build_evidence_index.py 生成）
  - `docs/aiqe/v1.6/release-verdict.json` / `V1.6-Release-Verdict.md`
  - `docs/aiqe/v1.6/V1.6.1-Audit-Closure-Report.md`（19 项台账）
  - `docs/aiqe/v1.6/governance/branch-protection.json`（GitHub API 实采）
  - 本机全量：`2553 passed / 43 skipped`（work-log 记录）
- Reviewer（非原实现者）：**待指定**（P0/P1 合入前必须由非作者签署）
- Reviewer 角色域（须与 owner 不同）：**待指定**（见 `governance/review-roles.yaml`）
- 独立验收记录（如本 PR 触发 REVIEWED）：待 Reviewer 用
  `python scripts/aiqe/record_acceptance.py` 生成后随 PR 提交

## 自检结果（本地）

| 检查 | 命令 | 结果 |
|---|---|---|
| 追踪矩阵 strict | `check_traceability.py --strict-warnings --check-baseline` | 0 error / 0 warning |
| 发布审计 | `check_release_audit.py` | 0 error |
| 审计台账 | `check_audit_closure.py --check` | 12 CLOSED / 7 EXTERNAL，0 error |
| 质量棘轮 | `scripts/ci/quality_ratchet.py` | PASS（ruff 395 / mypy 89，increased=0） |
| AIQE 子集 | `pytest -k "aiqe_v16 or …"` | 372 passed |
| 全量后端 | `pytest tests` | 2553 passed / 43 skipped |
| 仓库守卫 | oracle-layer / aiqe-skills / CI 分类器 | 全部 PASS |

## 风险

- 中：`GA_NOT_READY` 保持不变——独立验收（0/70）、产品级 TC（0/10）、
  生产证据与 ruleset 非作者审批仍未完成（见审计台账 EXTERNAL）。
- 低：新增脚本只读/门禁类，不改业务数据；无迁移。
- 已知：`test_tc_006_secret_chain_no_plaintext` 曾在整套运行时偶发失败（旧 GA 报告已记录为
  flaky）；已消除顺序依赖，若复现需按 work-log 抓取证据定位。
