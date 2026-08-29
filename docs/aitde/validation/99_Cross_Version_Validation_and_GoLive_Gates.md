
# AITDE V3.0 → V4.0 跨版本校验、准入与发布总清单

> 用途：控制“当前版本是否真的有资格成为下一版本基线”。  
> 任意阻断项未通过，下一版本可以做技术验证，但当前版本不能标记为 VERIFIED。

---

# 1. 全版本不可破坏不变量

```text
1. Frozen Contract 不可直接修改。
2. ScenarioVersion 精确绑定 ContractVersion。
3. AI_INFERRED 不能静默成为 Required Oracle。
4. PASS 必须来自 Required Oracle + Deterministic Assertion + Evidence。
5. Runtime/Data/Environment 问题不能直接成为 BUSINESS_FAIL。
6. Auto Healing 只能修改 Action，不修改 Oracle/Contract。
7. Production 默认只读，数据库账号本身必须真正只读。
8. Secret 不进入 Prompt / Workflow History / Evidence / 普通日志。
9. 所有跨项目访问都做授权。
10. 所有正式事实可追溯 Source / Version / Audit。
```

---

# 2. 每版发布必须归档

```text
Alembic Head
/api/v2 OpenAPI
Frontend Route Map
Feature Flags
Domain Invariant Test Report
Backend Unit/Integration Report
Frontend Unit/E2E Report
Migration/Backfill Report
Security Report
Quality Metrics Snapshot
Known Limitations
Rollback Procedure
Transition Gate Result
```

---

# 3. V3.0 → V3.1

- [ ] Frozen Contract mutation = 0。
- [ ] ScenarioVersion / Oracle ID 稳定。
- [ ] AI Schema Valid = 100%。
- [ ] Invalid SourceRef acceptance = 0。
- [ ] Legacy v1 Regression 通过。
- [ ] Tester 能完成完整 Design Loop。
- [ ] V3.1 可只新增执行事实，不修改 V3.0 业务事实模型。

不通过时，不允许正式构建统一 PASS/FAIL。

---

# 4. V3.1 → V3.2

- [ ] 至少 100 个 Run 完成 Shadow 对比。
- [ ] PASS 必须有 Required Oracle/Evidence。
- [ ] False Pass/False Fail 有人工审计基线。
- [ ] Locator/Environment Error 不误报 BUSINESS_FAIL。
- [ ] Evidence Sanitizer Secret Leak = 0。
- [ ] Replay 在 Backend 重启后可用。
- [ ] ExecutionRun 可扩展 DATA/DB Step。

不通过时，不允许大规模自动造数据，否则无法分辨判定问题和数据问题。

---

# 5. V3.2 → V3.3

- [ ] Fixture Cleanup 幂等。
- [ ] Lease 并发无冲突。
- [ ] 非 Allowlist DB Mutation 100% 拒绝。
- [ ] DATA_FAIL 不误报 BUSINESS_FAIL。
- [ ] DB Before/After Snapshot 可信。
- [ ] Browser/Runner 异常后 Cleanup 能最终执行。
- [ ] Fixture 与 Environment 严格隔离。

不通过时，不允许大规模 Hybrid UI。

---

# 6. V3.3 → V3.4

- [ ] Command IR Schema 稳定。
- [ ] Action 与 Oracle 完全分离。
- [ ] Healing Oracle Mutation = 0。
- [ ] Hybrid Scenario 连续运行有稳定性基线。
- [ ] 所有长步骤定义 Idempotency/Retry Policy。
- [ ] Observe/Manual Session 有持久状态。
- [ ] Legacy UI Regression 通过。

不通过时，不允许把动作迁入 Durable Retry，因为重试可能放大副作用。

---

# 7. V3.4 → V3.5

- [ ] Worker Crash Recovery 演练。
- [ ] Control Plane Restart Recovery 演练。
- [ ] Secret 不进入 Temporal History。
- [ ] Policy Backend 不可绕过。
- [ ] Worker Capability Routing 正确。
- [ ] Cleanup Activity Retry 安全。
- [ ] Workflow 可以由外部 Trigger 启动。

不通过时，不允许无人值守 Continuous Acceptance。

---

# 8. V3.5 → V3.6

- [ ] 无 Git 权限完整 RED→GREEN 流程成功。
- [ ] Fingerprint Duplicate Trigger 幂等。
- [ ] Zero Execution Gate 永不 PASS。
- [ ] P0 BUSINESS_FAIL Gate 必 FAIL。
- [ ] ContractVersion/Build mismatch 被 Gate 拒绝。
- [ ] Build Timeline 与真实 Run 一致。
- [ ] Override 全审计。

不通过时，生产 Evidence 可试验，但不能反向驱动正式验收。

---

# 9. V3.6 → V3.7

- [ ] Production DB 真实只读账号写测试全部失败。
- [ ] Production Browser 高风险动作默认阻断。
- [ ] Prod Query Audit Coverage = 100%。
- [ ] Secret/PII Leakage = 0。
- [ ] Mask/Token 后关系完整。
- [ ] Prod Template 只写 Test。
- [ ] Production Behavior 不自动改 Contract。
- [ ] Journey/Entity/API 有稳定 SourceRef。

不通过时，不允许用生产 Evidence 大规模自动扩展 Scope/Scenario。

---

# 10. V3.7 → V3.8

- [ ] Golden ChangeSet Impact Recall 有基线。
- [ ] P0/P1 False Negative = 0（Golden Set）。
- [ ] Unknown Change 有 Fallback。
- [ ] Smart Selection 可解释。
- [ ] Selection 固化后不可静默改变。
- [ ] Full Regression Fallback 一键可用。
- [ ] 基础 Impact Path 不依赖 AI 才能计算。

不通过时，AI Gap/Learning 只能做实验。

---

# 11. V3.8 → V4.0

- [ ] Failure Triage Benchmark 达团队阈值。
- [ ] AI 修改 Frozen Oracle 的拒绝率 = 100%。
- [ ] Healing 只产生新 ActionPlanVersion。
- [ ] BUSINESS_FAIL 不被 Flaky 自动吞掉。
- [ ] Suggestion/Gap 正式应用均经过 Review。
- [ ] Prompt/Model 更新有 Golden Evaluation。
- [ ] 所有 AI 自动能力有 Kill Switch。
- [ ] Cutover 所需质量指标已有连续历史数据。

---

# 12. V4.0 Cutover Gate

建议最低目标：

```text
P0 False Pass Rate              < 1%
False Fail Rate                 < 3%
P0 Evidence Completeness        > 99%
Replay Audit Consistency        > 99%
Fixture Cleanup Success         > 99%
Production Unauthorized Write   = 0
Secret Leakage                  = 0
PII Leakage                     = 0
Contract Unauthorized Mutation  = 0
Mission Workflow Adoption       > 80%
```

同时：

- [ ] SSO/RBAC 安全测试 PASS。
- [ ] PostgreSQL Backup/Restore Drill PASS。
- [ ] Object Storage Restore Drill PASS。
- [ ] Temporal Recovery Drill PASS。
- [ ] Legacy Active Consumer Inventory 清零或有正式兼容计划。
- [ ] Legacy Write Cutoff 有 Rollback Window。
- [ ] Platform Readiness Gate PASS。

---

# 13. 全版本回归层级

每次升级至少跑四层：

## A. 当前版本新增能力

当前版本专项。

## B. AITDE Invariants Regression

V3.0 开始累加，不能只跑当前版本测试。

## C. Legacy Regression

V4.0 Cutover 前持续覆盖：

```text
TestCase
TestPlan
API Test
UI Test
Requirement
Environment
RBAC
VersionMission
```

## D. Real Tester Journey

至少用一个真实 Mission 走完整链：

```text
Mission
→ Contract
→ Scenario
→ Data（V3.2+）
→ Browser/Hybrid（V3.3+）
→ Durable Runtime（V3.4+）
→ Build Acceptance（V3.5+）
→ Production Evidence（V3.6+）
→ Smart Regression（V3.7+）
→ AI Closed Loop（V3.8+）
```

---

# 14. 必须长期维护的 Golden Benchmark

```text
Golden Requirements
Golden Scope/Contract
Golden Scenarios/Oracles
Golden Execution Runs
Golden False Pass/False Fail Cases
Golden Data Fixtures
Golden UI Flake Cases
Golden Production Safety Cases
Golden ChangeSets
Golden Failure Triage Cases
```

它们是防止 Prompt/Model/Driver 改动导致质量暗降的核心。

---

# 15. 推荐版本发布流程

```text
Development Complete
→ Automated CI
→ Migration Test
→ Security Test
→ Shadow/Pilot
→ Real Tester Acceptance
→ Transition Gate
→ VERIFIED Baseline
```

建议每版至少：

```text
RC1 Functional
RC2 Migration/Security
RC3 Real Tester Pilot
Verified
```

---

# 16. 总判断原则

始终遵循：

```text
测对
→ 能执行
→ 能证明
→ 能造数据
→ 能 Hybrid
→ 能可靠恢复
→ 能持续验收
→ 能安全看生产
→ 能精准回归
→ 能 AI 闭环
→ 能企业级 Cutover
```

后一个版本暴露前一层基础不稳定时，优先回去修基础，不用更多 AI 自动化掩盖问题。
