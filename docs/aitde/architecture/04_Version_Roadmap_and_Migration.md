# 04｜AITDE 版本路线与现有平台迁移方案

## 1. 版本策略

由于不以时间成本为第一约束，本方案不建议长期维持“旧平台 + 新平台两套事实模型”。

采用：

```text
Strangler
+
Backfill
+
Compatibility Layer
+
Controlled Cutover
```

最终应该真正收敛到 Mission / Contract / Scenario / Run 模型。

---

# 2. 推荐版本线

为了和已有平台区分，建议新一代使用：

```text
Platform 3.x
```

而不是继续给当前模块零散加功能。

---

# V3.0｜Domain Foundation + Mission UX

## 目标

建立新系统的标准答案和新主入口。

## Backend

新增：

```text
missions
source_artifacts
source_fragments
scope_items
ambiguities
test_intents
test_contracts
test_contract_versions
test_scenarios
test_oracles
change_proposals
```

完成：

- VersionMission → Mission Migration；
- Requirement/OpenAPI → SourceArtifact Adapter；
- Contract Freeze；
- Scenario Version；
- Oracle Source；
- AI Schema Output；
- New `/api/v2`.

## Frontend

新增：

```text
/missions
Mission Create
Sources
Scope Review
Ambiguity
Contract
Scenario Matrix
Functional View
```

Workbench 默认改成 Mission-oriented。

## 旧功能

```text
TestCase
API
UI
TestPlan
Dataset
```

仍正常运行。

## 验收

一份需求：

```text
Mission
→ Sources
→ Scope Review
→ Ambiguity Resolve
→ Frozen Contract
→ Scenario
```

打通。

---

# V3.1｜Unified Execution + Proof Replay

## Backend

新增：

```text
execution_runs
execution_steps
assertion_results
evidence_artifacts
replay_manifest
environment_snapshots
```

将：

```text
ApiExecutionTask
UiTestRun
TestExecution
```

统一映射到 ExecutionRun。

引入 Object Storage。

建立 Outcome Classifier。

## Frontend

新增：

```text
Execution Center
Run Detail
Basic Replay
Why PASS
Failure Classification
```

## 核心改造

旧：

```text
pass / fail
```

新：

```text
PASS
BUSINESS_FAIL
AUTOMATION_FAIL
DATA_FAIL
ENV_FAIL
ASSERTION_ERROR
BLOCKED
INCONCLUSIVE
```

## 验收

现有 API/UI Run 都可以：

```text
Scenario → Run → Timeline → Evidence → Outcome
```

---

# V3.2｜Data + DB Runtime

## Backend

新增：

```text
data_sources
data_requirements
data_plans
data_fixtures
fixture_entities
fixture_leases
db_snapshots
```

实现：

```text
Existing Data Finder
API Builder
DB Fixture Builder
Workflow Builder
Cleanup
```

只开放 Test 环境写能力。

旧 Dataset 迁移为 StaticDataSource。

## Frontend

新增：

```text
Data Requirement View
Data Plan Preview
Fixture View
Lease State
Before / After
Cleanup
```

## 验收

测试工程师不再手工找关键测试账号即可执行核心 Scenario。

---

# V3.3｜Browser + Hybrid + Assisted Manual

## Backend

重构：

```text
case_compiler_service
```

引入：

```text
Command IR
Action Planner
Playwright Driver
UI Oracle
Hybrid Runtime
Observe Mode
```

保留 Legacy Spec Compiler 作为兼容。

## Frontend

新增：

```text
Assisted Manual Execution
Observe / Record Mode
Action Plan Review
Hybrid Run
Playwright Trace Replay
Healing Proposal
```

## 验收

```text
自动造数据
→ Tester/AI 操作 UI
→ API 观测
→ DB 校验
→ UI Oracle
→ Cleanup
→ Replay
```

---

# V3.4｜Temporal + Network Worker + Security Plane

## Backend

正式引入：

```text
Temporal
WorkerNode
Capability Routing
Network Zone
SecretRef
Policy Gateway
mTLS
```

迁移：

```text
api_task_worker
ui_runner_queue
DSH queue
```

到 Temporal Activity / Worker Adapter。

## Frontend

新增：

```text
Worker Admin
Network Zone
Capability
Step Retry / Resume
Approval Gate
```

普通测试工程师仅看到：

```text
正在等待 TEST 网络 Worker
```

## 验收

Worker 掉线后可以恢复，不产生重复脏数据。

---

# V3.5｜Continuous Acceptance

## Backend

新增：

```text
Build Observer
Environment Fingerprint
Impact Planner v1
Continuous Acceptance Workflow
Quality Gate v2
```

## Frontend

新增：

```text
Build Timeline
RED → GREEN Dashboard
Acceptance Gate
Build Diff
```

## 旧模块调整

Schedule 迁移为：

```text
Trigger
```

TestPlan 迁移为：

```text
ExecutionCampaign / RunProfile
```

## 验收

没有 Git 权限也能通过测试环境 Build 变化持续自动回归。

---

# V3.6｜Production Evidence

## Backend

新增：

```text
Prod-RO Worker
Browser Observer
Prod DB ReadOnly
XHR Evidence
PII Mask
Entity Graph Extractor
Prod Template Builder
```

所有生产写默认 DENY。

## Frontend

新增：

```text
Production Evidence
Observed Journeys
Real State Discovery
Prod Template Preview
Mask Preview
```

## 验收

生产只作为 Evidence Source，能反向补充：

```text
Scope
Ambiguity
Scenario
Data Template
```

---

# V3.7｜Impact Analysis + Smart Regression

## Backend

构建完整 Lineage：

```text
Source
→ Scope
→ Intent
→ Contract
→ Scenario
→ API/Page/Data/Oracle
→ Run
```

变化来源：

```text
PRD Diff
OpenAPI Diff
DB Schema Diff
Environment Fingerprint
UI Discovery
Historical Failure
```

## Frontend

新增：

```text
Impact Preview
Affected Scenario
Regression Selection Explanation
```

## 验收

每次变化默认只跑受影响 Scenario，同时允许 Full Regression。

---

# V3.8｜AI QA Closed Loop

## Backend

新增：

```text
Failure Triage
Action Healing Proposal
Flaky Detection
Data Strategy Learning
Scenario Gap Detection
Human Feedback Learning
```

AI 仍禁止直接修改 Frozen Oracle。

## Frontend

新增：

```text
Healing Review
Flaky Trend
AI Suggestion Inbox
Correction Metrics
```

---

# V4.0｜Legacy Cutover + Enterprise Stable

## 目标

新模型成为唯一事实源。

## 处理

### TestCase

```text
scenario-bound:
只读 Projection

legacy:
迁移或归档
```

### TestPlan

只保留：

```text
ExecutionCampaign
```

### Agent Workbench / DSH

移入：

```text
Admin / Advanced
```

### 旧 VersionMission

停止写入。

### 旧 API v1

进入：

```text
Deprecated
→ Read-only
→ Remove
```

## 企业补齐

```text
SSO
RBAC
Audit
Retention
Encryption
HA
Backup
Secret Rotation
Model Governance
Cost Governance
Release Gate
```

---

# 3. 模块迁移顺序依赖

```text
Mission
  ↓
Contract
  ↓
Scenario
  ↓
Oracle
  ↓
Execution / Evidence
  ↓
Data
  ↓
Hybrid UI
  ↓
Worker
  ↓
Continuous Acceptance
  ↓
Production Evidence
  ↓
Impact / Closed Loop
```

不能先做：

```text
Production Autonomous Agent
```

再回来补 Contract。

---

# 4. 数据迁移策略

## VersionMission

```text
1 old VersionMission
→ 1 Mission
```

关联：

```text
requirement_doc_id
environment_id
test_plan_id
```

变关系。

---

## TestCase

迁移分三种。

### A. AI Generated / Structured

AI 尝试反向提取：

```text
Given / When / Then / Oracle
```

生成 Draft Scenario，需要 Tester Review。

### B. 高价值历史 P0/P1

人工辅助迁移。

### C. 低价值历史 Case

保留 Legacy，不强制迁移。

不要让 AI 一次把所有历史 Case 转成正式 Scenario。

---

# 5. API Asset

API Service / Endpoint 保留原 ID。

新增关联：

```text
ScenarioApiBinding
```

不用迁移 OpenAPI 本身。

---

# 6. UI Asset

现有 UI Script：

```text
standalone asset
```

可以：

```text
link to ScenarioAdapter
```

验证成功后成为：

```text
Regression Adapter
```

---

# 7. Execution History

不必把所有历史执行完全重建 Proof Bundle。

策略：

```text
新 Run → Full Evidence Model

旧 Run → LegacyRunReference
```

重要历史缺陷可以增量转 Evidence。

---

# 8. Feature Flag

迁移期建议：

```text
MISSION_V2
SCENARIO_RUNTIME
UNIFIED_EXECUTION
DATA_RUNTIME
HYBRID_RUNTIME
CONTINUOUS_ACCEPTANCE
PROD_EVIDENCE
```

按项目逐个打开。

---

# 9. Shadow Mode

V3.1~V3.3 期间：

```text
旧流程仍是正式结果
新 Runtime 同时执行
```

抽查：

```text
AI PASS 是否真 PASS
AI FAIL 是否真 FAIL
Scope 是否遗漏
Oracle 是否准确
```

统计：

```text
False Pass
False Fail
Human Correction
Replay Audit Consistency
```

达到阈值后再成为正式 Gate。

---

# 10. Gate 升级路线

```text
Informational
      ↓
Soft Gate
      ↓
Hard Gate
```

## Informational

只提示。

## Soft

阻止 AI 自动标记 Acceptance，但 Tester 可以 override。

## Hard

P0 Gate 不通过即：

```text
NOT READY
```

---

# 11. 每个版本都必须监控的指标

```text
False Pass Rate
False Fail Rate
Scope Correction Rate
Oracle Correction Rate
Scenario Correction Rate
Automation Fail Rate
Data Prepare Success Rate
Fixture Cleanup Success Rate
Evidence Completeness
Tester Review Time
Failure Diagnosis Time
```

---

# 12. 回滚策略

每个版本要保证：

```text
新领域写入失败
≠
破坏旧平台
```

迁移期间：

- 数据库 migration 可前向修复；
- Compatibility API 保留；
- 新 Workflow 可关 Feature Flag；
- 旧 Run 能继续查看；
- Contract/Scenario 数据永不因为关闭 feature 被删除。

---

# 13. 推荐实施 Epic

```text
EPIC-01 Mission Domain
EPIC-02 Source Normalization
EPIC-03 Scope & Ambiguity
EPIC-04 Contract Versioning
EPIC-05 Scenario & Oracle
EPIC-06 Scenario Projection
EPIC-07 Unified Execution
EPIC-08 Evidence Store
EPIC-09 Replay
EPIC-10 Data Runtime
EPIC-11 DB Driver
EPIC-12 Browser Command IR
EPIC-13 Hybrid Runtime
EPIC-14 Assisted Manual
EPIC-15 Temporal Workflow
EPIC-16 Network Worker
EPIC-17 Policy & Secrets
EPIC-18 Environment Fingerprint
EPIC-19 Continuous Acceptance
EPIC-20 Prod Evidence
EPIC-21 Impact Analysis
EPIC-22 AI Closed Loop
EPIC-23 Legacy Migration
EPIC-24 Enterprise Hardening
```

---

# 14. 哪些 Epic 可以并行

基础：

```text
EPIC-01 → 03/04/05
```

并行：

```text
Evidence / Replay
Data Runtime
Browser IR
Frontend Mission UX
```

但都依赖：

```text
Scenario / Oracle
```

成为统一语义。

---

# 15. 最终 Cutover 判定

只有满足以下条件才建议让新平台成为唯一正式路径：

```text
P0 False Pass < 1%
Replay Audit > 99%
Required Evidence > 99%
Fixture Cleanup > 99%
Contract unauthorized mutation = 0
Production unauthorized writes = 0
Tester Mission workflow adoption > 80%
```

---

# 16. 最终状态

V4.0 后，现有平台不是“被推翻”。

它的成熟能力被重新归位：

```text
Requirement → Source Driver
API Test → API Driver / Asset
UI Test → Browser Driver / Asset
Dataset → Data Runtime
Environment → Runtime Environment
Trace → Evidence Lineage
TestCase → Scenario Projection
TestPlan → Execution Campaign
Report → Acceptance Report
VersionMission → Mission
Agent → Intelligence Layer
```

最终从一个：

> 多模块测试管理平台

演进为：

> **以 Mission 为入口、以 Contract 为标准答案、以 Scenario 为唯一测试事实源、以 Runtime 自动执行、以 Replay 证明结果的 AI Test-Driven Engineering Platform。**
