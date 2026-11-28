## AIQE V1.6.2 Hardening 整改（FIX-001～FIX-015，单一大版本）

- Issue / Requirement ID: V16-001 / V16-002 / V16-003 / V16-004 / V16-005 / V16-006 / V16-007 / V16-008 / V16-009 / V16-010 / V16-011 / V16-012 / V16-013 / V16-014 / V16-017 / V16-018 / V16-019 / V16-021 / V16-022 / V16-023 / V16-024 / V16-025
- base_sha: `2d2f508d5d1fd452972e7af49d9b4f3bde2e7b01`
- head_sha: `HEAD_SHA_PLACEHOLDER`
- 业务结果: 旧静态 10/10 PASS 撤销，当前 10/10 BLOCKED；Gate E/F 非 PASS；GA_NOT_READY，release_status=RELEASE_CANDIDATE_BLOCKED；审计台账 0 CLOSED/19 EXTERNAL；凭据扫描当前 SHA CLEAN。
- 正式入口: `python scripts/aiqe/release_verdict.py --require-ga`；`python scripts/aiqe/run_product_tc.py --check-config|--plan|--run|--verify-results`；`POST /api/v1/aiqe/agent-tasks` → `/submit` → `/approve` → `/run` → Worker `claim_agent_task_jobs` + `run_job`。
- 调用链: AgentTask API → Project Scope → AgentTask → ExecutionJob → Worker Claim/Lease → A0→A1..A6 → ToolRegistry/ToolExecutor → ToolExecutionAudit → AgentExecution；产品 TC config → Runner → execution → Assertion/Artifact → verify → Gate E。
- 真实组件与 Mock 边界: 真实 FastAPI 路由/SQLAlchemy/ExecutionJob/Worker/ToolRegistry/Benchmark/Learning/GitHub API；Agent LLM 用 deterministic stub（`controlled_llm_test`），不代表生产模型质量；产品 TC 无隔离 Test 环境，全部 BLOCKED。
- Reviewer 角色域: qa
- 证据: commit:HEAD_SHA_PLACEHOLDER；pytest:tests/test_aiqe_v162_release_verdict.py（13 passed）；artifact:docs/aiqe/v1.6/V1.6.2-Hardening-Final-Acceptance.md、docs/aiqe/v1.6/release-verdict.json、docs/aiqe/v1.6/e2e/product-results.json、docs/aiqe/v1.6/evidence/credential-scan.json、docs/aiqe/v1.6/governance/production-evidence.json、docs/aiqe/v1.6/V1.6.1-Audit-Closure-Report.md
- 整改依据：`CamelTv_AIQE_V1.6.2_整改开发落地实施手册.md`（FIX-001～015）
- 范围：AIQE 发布门禁/证据语义、产品 TC 基线与 Runner 框架、AgentTask/Benchmark、多端/Regression、凭据扫描、生产阶段、provenance、审计关闭、Ruleset、Reviewer 身份、最终验收。
- 非目标：不伪造产品 PASS/生产证据/Reviewer；不执行生产发布；不轮换外部账号密码（owner 操作）。

## 1. 整改任务

- FIX-001：Gate E 严格化，runtime `ga_ready=false` 时不得签 GA；RV-001～012。
- FIX-002/003：产品 TC schema 2.0、`--plan/--run/--verify-results`、ADR 0032 基线映射、V16-017-R3～R6 登记。
- FIX-004～008：产品场景执行结构、AgentTask API→Worker E2E、Benchmark 复算/双人审批、多端最弱聚合、Defect 回归守卫。
- FIX-009/010：明文凭据移除/Scanner 重写/CI Secret；生产阶段跳过标 NOT_RUN/NOT_PROVEN。
- FIX-011～014：provenance 不覆盖 tested SHA、语义审计关闭、AIQE Aggregate required check、GitHub Reviewer 身份。
- FIX-015：Evidence Manifest + Final Acceptance，结论 `RELEASE_CANDIDATE_BLOCKED`。

## 2. 业务结果

- 旧 `product-results.json` 静态 10/10 PASS 已撤销；当前 10/10 为机器生成 `BLOCKED`，Gate E 不再 PASS。
- 生产阶段 stage3/4、rollback drill 不再标 PASS；Gate F 按原始事实判定。
- 审计台账 0 CLOSED / 19 EXTERNAL，不再用“文件存在”关闭。
- 凭据扫描当前 SHA `CLEAN`（potential=0 / weak=0），CI PG 密码改 Secret。
- GA 状态 `GA_NOT_READY`，release_status `RELEASE_CANDIDATE_BLOCKED`；不宣称 GA/10-10/PRODUCTION_DEPLOYED。

## 3. 正式入口

- 发布判定：`python scripts/aiqe/release_verdict.py --require-ga`
- 产品 TC：`python scripts/aiqe/run_product_tc.py --check-config|--plan|--run|--verify-results`
- AgentTask：`POST /api/v1/aiqe/agent-tasks` → `/submit` → `/approve` → `/run`，Worker `claim_agent_task_jobs` + `run_job`
- 审计/证据：`check_audit_closure.py --check`、`build_evidence_index.py`、`build_evidence_manifest.py`
- 产品级 Benchmark：`/api/v1/aiqe/benchmarks/*` 与 `/api/v1/aiqe/learning/candidates/*`（当前产品级执行 BLOCKED）

## 4. 调用链

- AgentTask：API → Authorization/Project Scope → AgentTask Record → ExecutionJob → Worker Claim/Lease → A0→A1..A6 → BoundToolRegistry/ToolExecutor → ToolExecutionAudit → AgentExecution/Result。
- 产品 TC：config → Runner 合同 → 本次 execution → Assertion/Artifact → verify → Gate E。
- 发布：traceability → audit closure → branch protection → product runtime → production stages → Gate A–G → release-verdict。

## 5. 真实组件与 Mock 边界

- 真实：FastAPI 路由、SQLAlchemy/SQLite、ExecutionJob/Worker consumer、ToolRegistry/ToolExecutor、AgentTask 状态机、Benchmark/Learning 服务、Ruleset GitHub API、credential scanner（本地文件）。
- 受控边界：Agent LLM 使用 deterministic stub（测试标注 `controlled_llm_test`），不代表生产模型质量；产品 TC 无隔离 Test 环境，全部 `BLOCKED`，不以外部生产站点脚本替代。

## 6. 测试

- 成功路径测试: tests/test_aiqe_v162_release_verdict.py::test_rv_012_complete_fixture_passes, tests/e2e/aiqe/test_v16_018_agent_task_api_e2e.py::test_agent_task_api_full_chain, tests/test_aiqe_v162_agent_benchmark.py::test_metrics_fixed_fixture_manually_recomputable, tests/test_aiqe_v162_governance.py::test_check_requires_exact_aiqe_context
- 拒绝/失败路径测试: tests/test_aiqe_v162_release_verdict.py::test_rv_001_runtime_ga_ready_false_blocks_even_with_10_of_10, tests/test_aiqe_v162_product_tc.py::test_verify_rejects_forged_blocked_to_pass, tests/test_aiqe_v162_provenance_closure.py::test_scenario_2_null_runner_cannot_close, tests/test_aiqe_v162_agent_benchmark.py::test_same_user_approval_rejected
- 命令与结果：`pytest tests -q -k aiqe` → 1516 passed；后端全量 → 2854 passed / 43 skipped（修复 1 个顺序依赖后复跑，见 QA 报告）；`ruff F821` / `quality_ratchet` / `alembic heads` 通过。

## 7. 证据

- 证据: commit:`HEAD_SHA_PLACEHOLDER`；pytest:1516 passed；artifact:`docs/aiqe/v1.6/V1.6.2-Hardening-Final-Acceptance.md`、`docs/aiqe/v1.6/release-verdict.json`、`docs/aiqe/v1.6/e2e/product-results.json`、`docs/aiqe/v1.6/evidence/credential-scan.json`、`docs/aiqe/v1.6/governance/production-evidence.json`、`docs/aiqe/v1.6/V1.6.1-Audit-Closure-Report.md`
- run: 本地 2026-11-28；CI run 由本 PR checks 生成（workflow `AIQE V1.6 交付门禁`）
- environment: local-windows / ci（CI 证据以 artifact 为准）
- 产品结果：10/10 BLOCKED（`product-results.json`，baseline `v1.6.2-hardening`）
- 扫描：`scan_commit_sha=HEAD_SHA_PLACEHOLDER`，potential=0 / weak=0

## 8. 安全检查

- Secret 扫描：当前工作树 `CLEAN`；Kibana 早期文档明文已移除；测试/外部脚本改环境变量注入。
- 明文敏感数据：仓库新增文件未包含密码/token；`credential-scan.json` 仅含脱敏模式。
- TargetPolicy / tenant isolation：未修改策略实现；AgentTask/Benchmark 新增校验均为 fail-closed。

## 9. 验收与关闭

- closure_rule_id: `PRODUCT_TC_EXECUTED`（P1-4）、`BRANCH_RULESET_REQUIRED_CHECKS`（P0-2）、`SECRET_SCAN_CURRENT`（P2-3）等；台账 0 CLOSED / 19 EXTERNAL。
- 自动化验证器结果：Traceability 0 error / Release Audit 0 error / Audit Closure 0 error / Credential Scan CLEAN。
- 非作者 Reviewer login / Review ID: `MoojinR` / 待本 PR APPROVED review 回填（V1.6.1 review 6089615481 不对应本 SHA，不继承）。
- Reviewer 批准的 commit SHA: `HEAD_SHA_PLACEHOLDER`（待 review）
- 仍未完成：产品 TC 隔离 Test 执行、生产阶段/rollback drill、真实 Reviewer 身份、Ruleset apply+capture；GA 结论 `RELEASE_CANDIDATE_BLOCKED`。
