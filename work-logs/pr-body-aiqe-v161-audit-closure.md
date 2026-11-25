# PR 提交包：AIQE V1.6.1 审计整改（`fix/aiqe-v161-audit-closure`）

> Draft PR #635。推送已获用户授权；**合入前仍需非作者 Reviewer 签署**（见文末）。

## 变更类型

- [x] 🐛 Bug 修复（A3 无法运行、AgentTask 永久 pending、镜像缺 sqlglot）
- [x] 🔒 安全（Agent 工具授权、TargetPolicy 负向证据、PG 只读验证器）
- [x] 🧪 测试（60+ 新增/强化测试）
- [x] 📝 文档（GA/Production/E2E 真值重写、审计台账）
- [x] 🚀 CI/CD（strict 门禁、evidence index、release gate、product TC 校验）

## 变更说明

针对 `CamelTv_AIQE_V1.6_Main_9bbbdbb_Code_Audit.md`（2026-11-24）的 P0/P1/P2 逐项整改：
19 项审计发现 → 14 项 CLOSED（代码/测试/证据），5 项 EXTERNAL（已登记 owner 与解除动作）。
补充材料：镜像 digest + CycloneDX SBOM + 运行态冒烟（production `/health` 200、Alembic 单头）、
真实 PostgreSQL 16 只读 role 验证 PASS、未来娃屿生产只读实测 PROBED。

---

## AIQE V1.6 需求追踪（V16-025 强制，AIQE 相关 PR 必须完整填写）

> 由 `.github/workflows/aiqe-v16-gates.yml` 的 Traceability Gate 校验；空字段直接拒绝。
> 追踪矩阵：`docs/aiqe/v1.6/traceability/requirements.yaml`。

- Issue / Requirement ID：V16-013, V16-014, V16-017, V16-019, V16-022, V16-023, V16-024, V16-025
- 业务结果（用户可观察）：发布判定从文档声明变为机器可校验证据；Agent A1–A6 全链路可运行；E2E 负向/崩溃/归因场景可复现；GA 状态真实显示 GA_NOT_READY 及阻塞项。
- 正式入口（API / Worker / Job / CLI）：POST /api/v1/aiqe/runs -> job_consumer.claim_aiqe_jobs -> execute_inprocess_job；POST /api/v1/aiqe/agent-tasks/{id}/run -> job_consumer -> execute_task_job -> run_plan；POST /api/v1/aiqe/defects/{id}/regressions（impact_base_sha 服务端重算）；CLI：check_traceability.py / release_verdict.py / check_release_audit.py / check_audit_closure.py / run_product_tc.py / check_pg_readonly_role.py / check_branch_protection.py。
- 调用链（入口到 Driver/Assertion/Finalize）：Run：API -> launch_run -> ExecutionJob -> job_consumer -> node_executor -> driver -> assertion -> finalize；Agent：API -> AgentTask(Draft->APPROVED->QUEUED) -> Outbox/ExecutionJob -> consumer -> run_plan -> AgentContext(tool_executor) -> Agent Adapter -> ToolRegistry(授权/审计) -> AgentExecution。
- 真实组件与 Mock 边界：真实=SQLite/PostgreSQL 模型、Worker claim/lease/fencing、reconciler、BoundToolRegistry、Evidence Resolver、Agent 状态机、Playwright（node_executor 层）；Mock/Stub=LLM 确定性 stub（模型供应商可替换边界）、本地 SUT HTTP 服务；产品级 TC 的 Test 业务环境尚未接入（run_product_tc.py 缺 env 时输出 NOT_PROVEN）。
- 成功路径测试：tests/e2e/aiqe/test_v16_017_platform_chain.py::test_tc_010_agent_task_platform_chain, tests/test_aiqe_v16_019_agent_tool_loop.py::test_a1_agent_invokes_tools_through_executor, tests/test_aiqe_v16_019_agent_task_consumer.py::test_run_job_dispatches_agent_task_to_executor
- 拒绝/失败路径测试：tests/e2e/aiqe/test_v16_017_platform_chain.py::test_tc_005_metadata_endpoint_never_reached, tests/test_aiqe_v16_019_agent_tool_loop.py::test_write_tools_remain_unavailable, tests/test_aiqe_v16_025_traceability_gate.py::test_rejects_runtime_proven_without_ids
- 异常/依赖缺失测试：tests/test_aiqe_v16_017_product_runner.py::test_run_without_env_is_not_proven, tests/test_aiqe_v16_004_pg_readonly.py::test_unreachable_dsn_reports_fail, tests/test_aiqe_v16_019_agent_tool_loop.py::test_get_agent_accepts_model_for_every_agent
- 并发/重试/竞态测试：tests/e2e/aiqe/test_v16_017_platform_chain.py::test_tc_007_worker_crash_recovery_and_duplicate_delivery, tests/test_aiqe_v16_005_lease_fencing.py::test_duplicate_delivery_is_idempotent, tests/test_aiqe_v16_005_lease_fencing.py::test_stale_worker_result_rejected
- 安全影响（权限/Secret/网络/租户/外部副作用）：写工具保持 UNAVAILABLE；create_regression_plan 只读提案（side_effects=NONE）；read_git_diff 仓库路径服务端固定、SHA 严格 40 位；project_id 不可覆盖；TC-006 明文零落库断言保留；TargetPolicy 负向场景增加受控目标 0 请求断言。
- 迁移影响（迁移文件、回滚/前滚方案）：无新增迁移；基线 head 仍为 20261122_v16_catalog_post_merge，--check-baseline 强制单头。
- 证据（commit SHA / CI Run / 测试报告 / Run ID / Job ID / Artifact ID）：commit:9bbbdbb2026bada5c016d663780e03d62fca940d, artifact:docs/aiqe/v1.6/e2e/platform-results.json, artifact:docs/aiqe/v1.6/evidence/evidence-index.json, artifact:docs/aiqe/v1.6/release-verdict.json, artifact:docs/aiqe/v1.6/V1.6.1-Audit-Closure-Report.md, artifact:docs/aiqe/v1.6/governance/branch-protection.json, pytest:tests/test_aiqe_release_audit.py (11 passed)
- Reviewer（非原实现者）：MoojinR（qa；邀请待接受）
- Reviewer 角色域（须与 owner 不同）：qa
- 独立验收记录（如本 PR 触发 REVIEWED）：待 Reviewer 用 python scripts/aiqe/record_acceptance.py 生成后随 PR 提交

---

## 自检结果（本地）

| 检查 | 命令 | 结果 |
|---|---|---|
| 追踪矩阵 strict | check_traceability.py --strict-warnings --check-baseline | 0 error / 0 warning |
| 发布审计 | check_release_audit.py | 0 error |
| 审计台账 | check_audit_closure.py --check | 14 CLOSED / 5 EXTERNAL，0 error |
| 质量棘轮 | scripts/ci/quality_ratchet.py | PASS（ruff 395 / mypy 89，increased=0） |
| AIQE 子集 | pytest -k "aiqe_v16 or …" | 376 passed |
| 全量后端 | pytest tests | 2572 passed / 43 skipped |
| 仓库守卫 | oracle-layer / aiqe-skills / CI 分类器 | 全部 PASS |
| 本地 rehearsal | local_test_env + run_product_tc（local config） | 10 BLOCKED（TC-001 Contract API、TC-002 Run 实测通过，产品验收仍需业务环境） |

## 风险

- 中：GA_NOT_READY 保持不变——独立验收（0/70）、产品级 TC（0/10）、生产证据、
  ruleset 非作者审批仍未完成（见审计台账 EXTERNAL）。
- 低：新增脚本为只读/门禁类，不改业务数据；无迁移。
- 已知：test_tc_006_secret_chain_no_plaintext 曾在整套运行时偶发失败（旧 GA 报告已记录为
  flaky）；已消除顺序依赖，若复现需按 work-log 抓取证据定位。

## 合入前必须完成

1. 指定非作者 Reviewer（GitHub 账号 + 角色域，如 `qa` / `security`），
   由其对 70 条需求逐条生成 `acceptance/records/*.json`；
2. 仓库邀请该独立账号，并在 ruleset `protect-main` 启用
   `require_code_owner_review=true` 或 `required_approving_review_count>=1`
   （当前单账号仓库直接启用会锁死合并）。
