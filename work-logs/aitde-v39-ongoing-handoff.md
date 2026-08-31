# AITDE V3.9 Reality Gate — 交接/续做清单（handoff）

> 供新会话直接续做。目标：在 `feature/aitde-v39-reality-gate` 分支上，按
> 《V3.9_Reality_Gate_Correction_and_Certification_Plan.md》+《V3.9_Reality_Gate_Issue_Checklist.md》
> 修复 V3.0–V3.9 全部 P0/P1/P2/P3，全部完成后建 PR → main（需用户确认后合入）。
> 计划文档：`C:\Users\26029\Desktop\CamelTv重构\落地实施方案\V3.0-V3.9校准方案\`（两个文件）。

## 1. 当前分支与基线
- 分支：`feature/aitde-v39-reality-gate`（基于 `origin/main` = beb297c2 创建）。
- 工作区有**未提交改动**（git status 可见，未 push）。`main` 被另一 worktree `F:/CamelTv-safe-backup/wt-main` 占用，故在本分支开发。
- 本地验证基线：
  - 后端：`cd test-platform-v2/backend` → `\.venv\Scripts\python.exe -m pytest tests/aitde/ -q` → **420+ passed, 1 xfailed**。
  - 前端：`cd test-platform-v2/frontend` → `npm run typecheck` 与 `npm run build` 均 0 错误；vitest 12/12。
- 备注：为跑通后端测试，已 `pip install temporalio`（TEMP-001：temporalio 已同步进 `requirements.lock`）。

## 2. 已完成（均经测试/构建验证）
**后端**（`test-platform-v2/backend/app/modules/aitde/**` 等）：
- R1 信任链：`workflow/oracle_engine.py`（Oracle 单一来源：真实 TestOracle + OracleBinding +
  CommandPlan v2 只声明观察、v1 标 LEGACY）、`scenario/models.py` 新增 `ScenarioOracleBinding`、
  `evidence/snapshot_sanitizer.py`（Snapshot 清洗）、`evidence/service.py`（`integrity_status=VERIFIED`）、
  `assertion/completeness.py`（`artifact_usable`/`is_complete_artifacts`）、`workflow/drivers.py`
  （Secret-Ref-only + TLS verify + 证据走 EvidenceService）、`execution/outcome_classifier.py` 新增
  `compute_run_trust`、`execution/mapper.py` 序列化 `trust_status/oracle_source_type/integrity_status/object_exists...`。
- HYBRID-001：`hybrid/coordinator.py`（无 runner 不假 executed，`RuntimeCapabilityError` + `preflight()`）。
- AI-001/002/004：`ai_closed_loop/service.py`（真实 FailureEvidencePack、`FailureTriageRuleEngine`、
  真实 evidence_refs、样本不足→BLOCKED）。
- CONT-002：`continuous/service.py`（G1/G3/G4/G9 真算，去除硬编码/vacuous pass）。
- CONT-001：`continuous/service.py fire_trigger` 真正执行 Campaign——`start_campaign_execution` 冻结选择并给每个
  CampaignScenario 创建真实 ExecutionRun 并绑定 `run_id`，`finalize_campaign` 仅在全部 run 到达 terminal 时置
  COMPLETED/PARTIAL，`evaluate_gate` 仅在 Campaign 完成（COMPLETED/PARTIAL）才给出最终 Gate，否则
  INCONCLUSIVE + `CAMPAIGN_NOT_FINISHED`（plan §50/§51/§52）。
- FINGER-001：`EnvironmentFingerprint`/`EnvironmentSnapshot` 新增 `confidence` 列（迁移 `M39R3-002`
  `20260903_aitde_v39_reality_r3_fingerprint`，已在真实 SQLite `alembic upgrade head` 验证，单 head 保持），
  `capture_fingerprint`/`capture_snapshot` 经 `confidence_from_components` 落库，`evaluate_gate` G9 要求目标 Build
  fingerprint confidence 为 MEDIUM/HIGH（否则 G9 不通过）（plan §57）。
- TEMP-002：`workflow/service.py` 接通死代码仓库函数 `create_approval` 为服务层入口（持久化 REQUIRE_APPROVAL，
  `temporal_workflow_id` 存入 request_json）；`_signal_approval` 增加 `_is_workflow_already_completed` 守卫，
  已完成的 workflow 信号按良性跳过而非当失败吞掉。
- REG-002：`smart_regression/service.py` + `api/v2/smart_regression.py`（真实 unknown_changes→CoverageGuard）。
- REG-001：`smart_regression/providers.py`（ChangeProvider Registry + 真实 `SnapshotDiffProvider`：
  OPENAPI/DB_SCHEMA/PRD/ENVIRONMENT/UI_DISCOVERY，每个 provider 自带 `load`(从 source_ref 取快照)+`diff`）；
  `ChangeSetService.detect` 增加 `source_type`/`trusted`——`PROVIDER` 经 registry 自行加载快照（绝不 trust 调用方 payload，
  不可解析 source_ref 抛 ValueError fail-closed），`MANUAL` 保留 debug payload（契约层）；
  `api/v2/smart_regression.py detect_changes` 透传 source_type/trusted。生产 store/URL backed loader 为注入缝（R6 接线）。
- REG-001 契约层：`smart_regression/schemas.py`（DetectIn `source_type=MANUAL`/`trusted=false`）。
- PG Drill（§77/78）：`tests/aitde/v39/test_migration_drill_reversible.py` 实现 previous-head↔current-head 可逆演练
  （upgrade 前头→upgrade head→downgrade 前头→upgrade head+单头校验），DB-agnostic——本地 SQLite 已通过，CI 走 PostgreSQL。
  迁移 M39R3-002 改为显式 `op.create_index`/`op.drop_index`（弃用 `op.add_column(..., index=True)`）以保可逆
  （此前 batched drop_column 会留孤儿索引破坏 re-upgrade，已由该 drill 暴露并修复）。
  CI：`.github/workflows/main-quality-gate.yml` 新增 job `aitde-migration-postgres`（PG service + 该 drill）。
- AI-003：`ai_closed_loop/service.py` `PromptEvaluationService` 增加 `run_suite`（Golden Runner：逐 sample 经可注入 evaluator 评分
  must_include/must_not_include/expected，聚合 accuracy，落库并标记 `_trusted=true`）、`score_suite`、`compare_baseline`、
  `release_decision`（仅 TRUSTED run_suite 得分可 PASS，不足→BLOCKED，低于阈值→FAIL）、`import_external_evaluation`
  （`evaluate` 标记外部未信任）；`tests/aitde/golden/{scope,contract,scenario,triage,healing,impact}/golden.json` 样本集。
- DATA-001：`drivers/database/base.py`（真实 `execute_select`/`execute_dml` + allowlist + row cap）。
- DATA-003：`data/cleanup_service.py`（真实清理+验证，绝不假 CLEANED）；`data/models.py` FixtureEntity 物理事实列；
  迁移 `M39R2-001`（20260903_aitde_v39_reality_r2_fixture）。
- DATA-004：`data/run_data_integration.py`（`store_data_evidence` 走 EvidenceService，拒绝假证据行）。
- DATA-002：`data/executors/db_executor.py`（真实 INSERT + SELECT VERIFY）+ `data/executors/existing_executor.py`
  （真实 SELECT → `FixtureEntity.created_by_fixture=False`，无匹配 → `NOT_FOUND`）、
  `data/executors/api_executor.py`（HTTP POST → 提取 physical id → GET VERIFY，Create 200 但资源不存在 → `VERIFY_MISMATCH`）、
  `data/executors/data_plan_executor.py`（DataPlanExecutor 编排：逐 entity 真实执行 + 物理验证，写 `physical_status`/
  `verification_status`/`verified_at`，step SUCCEEDED/FAILED，fixture 仅全部验证通过才 READY，否则 FAILED）、
  `drivers/http/data_api_driver.py`（DataApiDriver：POST/GET/DELETE，SecretRef-only，凭据安全分类）、
  `fixture_service.provision_fixture` 已接线 DataPlanExecutor（真实效果 + 验证）。
- FINGER-001：`environment/fingerprint.py`（FingerprintProbe 探针 + confidence）。
- TEMP-001：`requirements.lock` 补 temporalio/nexus-rpc/types-protobuf。
- 迁移：`20260903_aitde_v39_reality_r1.py`（oracle binding + assertion trust + evidence integrity + step evidence_refs）已在真实 SQLite 上 `alembic upgrade head` 验证，单 head 保持。
- Ruff：`app/modules/aitde` 等目录已清 E402/F401/F841 语义错误。

**前端**（`test-platform-v2/frontend/src/`）：
- `components/trust/`（12 文件）：`VerificationLevelBadge`、`TrustLevelBadge`、`EvidenceIntegrityBadge`、
  `OracleSourceBadge`、`CampaignProgress`、`SuccessStageBadge`、`runTrust.ts` 等。
- 接线：`pages/executions/run/[runId].tsx`、`EvidenceList.tsx`、`ReplayEvidenceViewer.tsx`、
  `RequiredOracleList.tsx`、`pages/campaigns/CampaignDetail.tsx`、`DataPlanPreview.tsx`、`api/executions.ts`。

**CI**：`.github/workflows/main-quality-gate.yml` 后端 job 新增「AITDE Domain Invariants + Reality Gate」
步骤（`pytest tests/aitde/v39 tests/aitde/reality`），已验证可执行（84 passed, 1 xfailed）。

**测试**：`test-platform-v2/backend/tests/aitde/reality/`（22 个文件：db_driver/db_executor/existing_executor/
api_executor/data_plan_executor/campaign_execution/fingerprint_confidence/approval_workflow/source_diff_registry/
evidence_integrity/fingerprint_probes/fixture_physical_facts/hybrid_capability/oracle_single_source/run_trust/
ai_rule_engine/mapper_trust/reg_source_manual 等）。此外 v32/v33 陈旧测试已改为
真实 sqlite 数据源驱动（`conftest.py` 加 `patched_db_driver`）以适配真实 provisioning。

## 3. 剩余（未完成，体量大）
- TEMP-003：**已闭环 + 更正早前误判**。先前“本地 Temporal 环境坏（activity 不执行）”是我**极简测试漏传 `start_to_close_timeout`** 导致的误判（temporalio 1.32 强制要求该 timeout，否则 `ValueError: Activity must have start_to_close_timeout or schedule_to_close_timeout`，worker 日志证实）。真实 AITDE `ScenarioExecutionWorkflow` 对每个 activity 都传了 timeout，实际**完全正常**。已用真实 workflow + `run_worker` + 真实 activity 在本机 Temporal（`aitde-temporal`，7233）跑通完整演练：**BEFORE-approve status 1（在 approval 门等待，15s 不 approve 不完成）、kill worker 后 status 1（durable）、重启 worker + signal approve 后 status 2（COMPLETED）**，无重复副作用。
- R6：已用 `admin/admin123` **实认证业务链**——login✅ → list projects✅ → GET test-cases(200) → POST create(200, id=3644) → read-back(200) → **故障注入**缺 `X-Project-Id`→**403**（多项目隔离守卫生效，已删冒烟用例）。后端 `/health`=200、`/openapi.json` 481 路由、前端 `vite preview`=200。
- R6 scenario **RED→GREEN + Replay 审计 + 版本认证**：✅ 已用**真实运行时 driver hooks**（`execute_commands`/`evaluate_oracles`/`classify_outcome`）+ 本地 mock target 跑通——RED→**BUSINESS_FAIL**；GREEN→**PASS**；每次运行 Replay：ExecutionSteps=1（`renew`/SUCCEEDED）+ EvidenceArtifacts=2（REQUEST+RESPONSE）；run 已绑定 contract_version_id + environment_snapshot_id。
- CERT-001 Full Test Chain（端到端经 Temporal）：✅ 用真实 `ScenarioExecutionWorkflow` + `run_worker` 把完整 scenario 端到端跑通——workflow **COMPLETED**（status 2），execute_commands 真实 HTTP 调用（step=`renew`/SUCCEEDED）+ evidence=REQUEST/RESPONSE，run 绑定契约+快照。
- CERT-002 五类故障注入：✅ `tests/aitde/reality/test_outcome_categories.py` 用真实 `outcome_classifier.classify` 判定表确定性验证 5 类——ENV_FAIL/DATA_FAIL/AUTOMATION_FAIL/BUSINESS_FAIL/INCONCLUSIVE/ASSERTION_ERROR/PASS 各就其位（9 passed）。
- CERT-005 Prod RO：✅ 已本地闭环——本地 PG 角色 `p_ro` 实证明 SELECT 通过、INSERT/UPDATE/DELETE/DDL/CTE 写全 `permission denied`；固化 `tests/aitde/reality/test_prod_ro_write_denial.py`。**§74 XHR red-team / §75 Prod→Test 数据流向**仍属外部/人工项。
- CI 其余 job：`aitde-data-integration`/`aitde-security-redteam`/`aitde-migration-postgres` 已加入并本地 104/34/8 通过（需 PG/RO 变量在 CI 提供以启用）。
- Ruff/mypy 余项（E501 等 line-length；**mypy 实测未安装**，venv 与系统 Python 均无；且非 CI 硬门禁）。
- **建 PR → main**（需用户按 AGENTS.md 确认；当前分支未 push）。

### 人工闭环交接（需用户从生产库导入测试环境 + 重跑 + 人工标/审计）
用户方案：从**生产数据库导入数据到测试环境**，在**测试环境重跑一遍流程**，再**人工标记/审计**。本会话无法替代的真实/外部项：
1. **CERT-004 PASS/FAIL Replay 人工审计**：本地已自动产出 Replay（steps+evidence+assertions）；需**人工**核对 replay 能否证明 PASS/FAIL 后定稿。
2. **CERT-006 Smart Regression Golden**：需 30+ **历史 ChangeSet golden 数据集**+ 人工标“每个变更应跑哪些 scenario”。本地已备 ChangeProvider/ImpactAnalyzer/RegressionSelector 骨架；数据集+人工标需你导入生产历史变更后填充。
3. **CERT-005 的 §74 XHR red-team / §75 Prod→Test**：真实 XHR 注入红队 + 生产→测试数据流向认证，需生产/测试环境与账号。
4. **CI 三 job 真在 GitHub Actions 跑** + **真实 PostgreSQL 迁移 drill 实测**：需 push 到分支触发 CI（授权后）+ PG service。
5. **R6 全量版本认证**：测试环境导入生产数据后，对真实业务形态重跑 RED→GREEN/Replay/版本比对。

## 4. 推荐续做顺序（不跳级）
R1(已完成) → R2 数据运行时（DATA-002 其余执行器 + 编排）→ R3（CONT-001 → TEMP-002/003 → FINGER-001 落库）→
R4（REG-001 真实 Provider + Prod RO）→ R5（AI-003 Golden）→ 前端收尾 → CI 其余 job + PG Drill →
R6 真实环境认证 → 全量回归 → 建 PR。

## 5. 关键命令
```bash
# 后端测试
cd test-platform-v2/backend
.\.venv\Scripts\python.exe -m pytest tests/aitde/ -q
# 迁移检查（单 head）
.\.venv\Scripts\python.exe -m pytest tests/aitde/v39/test_migration_single_head.py -q
# 前端
cd test-platform-v2/frontend
npm run typecheck && npm run build
```
