---
title: "AITDE V3.1 Unified Execution + Proof Replay — QA Report"
status: "active"
tags: ["aitde", "v3.1", "qa-report"]
---

# AITDE V3.1 — QA Report（Unified Execution + Proof Replay）

> 文档版本：1.0
> 日期：2026-08-29
> 分支：`feature/aitde-v31-unified-execution`（独立 worktree）
> 基准：`origin/main`（含 V3.0，HEAD `118f5d51`）

## 1. 交付范围

### 后端（PR31-01..07 / 10）
- **ScenarioAdapter**：把 ScenarioVersion 绑定到已有 API/UI 资产或未来 Runtime Adapter（UNIQUE 稳定语义）
- **EnvironmentSnapshot**：Run 前环境指纹；无 build_label 允许 tester 登记但始终生成 `fingerprint_hash`
- **ExecutionRun / Step / Assertion**：`runtime_status` 与 `outcome` 分离；父子 retry；Run 必绑定 `scenario_version_id + contract_version_id + environment_snapshot_id`
- **ObjectStorage** 抽象：Local + S3/MinIO provider
- **EvidenceArtifact**：元数据 + hash（原始字节只进对象存储，DB 只存 URI/hash/type/size）
- **EvidenceSanitizer**：Authorization/Cookie/token/password/secret 清洗；`REJECTED` 不可成为正式 Replay
- **AssertionEngine**：确定性求值，**不调用 LLM**；`NOT_EVALUATED` 绝不判 PASS
- **OutcomeClassifier**：确定性决策表；**无 HTTP-200→PASS、Toast→PASS、脚本异常→BUSINESS_FAIL**
- **Legacy API/UI Bridge**：幂等关联，不改旧记录
- **ReplayManifest**：append-only proof replay（成功 Run 也可回放）
- **Shadow Audit**：CONFIRMED/FALSE_PASS/FALSE_FAIL 反馈，**不改历史 outcome**
- 4 个 Alembic Migration：`M31-1`(adapter/environment)、`M31-2`(run/step/assertion)、`M31-3`(evidence/replay/legacy-link)、`M31-4`(shadow_audit_feedback)

### 前端（PR31-08/09/10）
- **Execution Center**、**Run Detail（+Why PASS / Failure Classification）**、**Replay 三栏**、**Mission Executions**
- 组件：OutcomeBadge / RuntimeStatusBadge / ExecutionTimeline / AssertionSummary / RequiredOracleList / EvidenceList / WhyPassPanel / FailureClassificationPanel / EnvironmentSnapshotCard / LegacyExecutionBadge / ReplayEvidenceViewer / **ShadowAuditPanel**
- 路由：`/executions`、`/executions/:runId`、`/executions/:runId/replay`、`/missions/:missionId/executions`（受 `AITDE_V3_ENABLED` 门控）；MissionLayout 增「执行」tab

## 2. 自检证据（本地）

| 项 | 结果 |
|---|---|
| `ruff check app/ --select F821`（硬门禁） | ✅ 全绿 |
| 新增文件默认 ruff（F/E/W） | ✅ 已清理（无 E501/F401 新增；config.py 既有债务未触碰） |
| 后端 pytest `tests/aitde/**` | ✅ **70 passed**（V3.0 既有 29 + V3.1 41） |
| 前端 `npm run typecheck` | ✅ 通过 |
| 前端 `npm run build` | ✅ 通过（9s） |
| 前端 `npm test`（vitest 全量） | ✅ **541 passed / 1 fixed**（含 batch54 治理测试） |
| Alembic `alembic heads` | ✅ 单头 = `20260829_aitde_v31_m31_4` |
| OpenAPI 路由 | ✅ 15 个 V3.1 路由已挂载 |

### 关键不变量验证（单元测试断言）
- 所有 Required Oracle PASS **且** Required Evidence 完整 → PASS
- 缺证据 / Required Oracle NOT_EVALUATED → INCONCLUSIVE
- HTTP 200 / Toast 单独 → 不判 PASS（`test_http_200_alone_is_not_pass`）
- locator timeout / 脚本异常 → 不判 BUSINESS_FAIL（决策表 AUTOMATION_FAIL/ASSERTION_ERROR 分支）
- Shadow Audit 反馈 → 不改历史 outcom，列表按项目隔离

## 3. 无回归
- 后端 V3.0 既有 AITDE 测试（mission/scenario/contract/scope/source/ambiguity/ai_ops）全绿
- 前端全量 vitest 除一处新引入治理违规（`⚠`→`AlertTriangle`）已修复，其余 540 项基线全绿

## 4. 待上线前（计划 §93 需真实环境）
- [ ] 抽取 ≥100 个历史/真实 API/UI Run 做新旧 Shadow 对比
- [ ] 人工审计 ≥30 PASS（证据不足 PASS=0）、≥30 失败分类
- [ ] 删除 Required Evidence 后 PASS 必须降级（真实环境实测）
- [ ] 对象存储 hash 与 DB 一致、跨 Project Evidence 拒绝（联调环境）
- 上述需 test/生产同构实例 + 真实数据，无法在纯单元/本地完成，已作为已知限制记录。

## 5. 结论
V3.1 开发与本地验证完成：Unified Execution + Proof Replay 全链路（后端核心 + 前端）已实现，本地 `ruff/pytest/typecheck/build/vitest` 全部通过，Alembic 迁移链正确（单头 m31_4）。进入 PR 合入流程。
