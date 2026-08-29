# 01｜CamelTV 现有测试平台升级总体蓝图

## 1. 目标

现有平台已经具备大量可复用能力：

- 项目 / 组织 / 权限；
- 需求与知识；
- 测试用例；
- 测试计划；
- API 资产、OpenAPI 导入和真实 HTTP 执行；
- UI 自动化和真实 Playwright 执行；
- Dataset；
- Environment；
- Trace；
- Defect / Report；
- Schedule；
- VersionMission；
- Agent / DSH Task；
- XHR Capture；
- Production Guard；
- 产物、截图、视频、Trace 等执行证据。

升级目标不是继续增加更多并列菜单，而是把这些能力重新组织为：

```text
                    Mission
                       │
              Design / Contract
                       │
                   Scenario
                       │
              Runtime / Drivers
                       │
                 Execution Run
                       │
               Evidence / Replay
                       │
                  Acceptance
```

---

# 2. 为什么“时间成本不受限”以后，改造策略应该变化

如果目标是快速兼容，我会继续直接扩展 `VersionMission`、`TestCase` 等现有表。

但现在假设时间成本不是约束，更合理的做法是：

1. **保留现有业务能力，重建规范领域模型。**
2. 使用迁移层把旧数据导入新领域对象。
3. 使用 Compatibility API 让旧页面在过渡期继续工作。
4. 新功能只写入新模型。
5. 等新 Mission 主流程稳定后，再逐步关闭旧的独立事实源。

原因是现有 `VersionMission.scope`、独立 `TestCase(case_type)`、TestPlan、API/UI Run 等设计本来就是为“模块化测试平台”服务，不适合作为未来十年的统一测试事实模型。

因此最终建议：

```text
Reuse Capability
≠
Reuse Every Data Model
```

复用执行器、解析器、权限、平台基础能力；领域模型允许重建。

---

# 3. 最终平台定位

## 3.1 旧定位

```text
Requirement
TestCase
TestPlan
API Test
UI Test
Dataset
Report
```

用户需要自己在模块之间搬运信息。

## 3.2 新定位

```text
                  Test Mission
                      │
       ┌──────────────┼──────────────┐
       │              │              │
    Sources        Contract       Runtime
       │              │              │
       └──────────────┼──────────────┘
                      ▼
                  Scenario
                      │
            ┌─────────┼─────────┐
            ▼         ▼         ▼
           Data      Action    Oracle
                      │
                      ▼
                 Execution Run
                      │
                 Proof Replay
                      │
                  Acceptance
```

测试工程师绝大多数时间只进入 Mission。

原来 API/UI/Dataset 等页面转变为：

> 专业资产页 / 高级调试页 / 管理页。

---

# 4. 现有模块逐项处理决策

| 现有能力 | 最终处理 | 新定位 |
|---|---|---|
| Project / Org / RBAC | 保留并增强 | 平台基础治理 |
| Workbench | 重构 | Mission 首页 / 我的待办 / 风险 / 最近 Run |
| VersionMission | 迁移到新 Mission Aggregate | 兼容旧 API；新数据进入 `missions` |
| Requirement | 保留增强 | Source Provider |
| Knowledge | 保留增强 | AI Context Provider，不直接成为 Oracle |
| Lanhu Evidence | 保留 | SourceArtifact Provider |
| TestCase | 兼容保留、降级事实地位 | Scenario Projection / Legacy Case |
| TestPlan | 重构 | Execution Campaign / Run Profile |
| API Test | 保留执行能力、重构入口 | API Asset Explorer + API Driver |
| UI Test | 保留执行能力、重构入口 | Browser Adapter Library + Regression Runner |
| Dataset | 大改 | DataSource / DataRequirement / Fixture |
| Environment | 大改 | Environment + EnvironmentSnapshot + Network Zone |
| Trace | 升级 | Evidence Lineage / Scenario Trace |
| Defect | 保留增强 | Evidence-linked Defect |
| Report | 重构 | Acceptance Report |
| Schedule | 重构 | Trigger / Continuous Acceptance |
| DSH Tasks | 降级为内部能力 | Intelligence/Automation 后台，不作为主用户模型 |
| Agent Workbench | 降级 | AI 调试、管理员、专家模式 |
| Playground | 管理/调试 | 不进入正式测试主路径 |
| Release Bundle | 升级 | Acceptance Bundle / Release Evidence Package |
| XHR Capture | 保留并升级 | Browser Observation / Traffic Evidence |
| Production Guard | 保留强化 | 统一 Policy Enforcement |
| API Task Worker | Adapter 化 | 迁移到统一 Runtime / Temporal Activity |
| UI Runner Queue | Adapter 化 | 迁移到统一 Runtime / Temporal Activity |

---

# 5. 必须停止继续强化的旧模式

## 5.1 停止让三个 Case 类型成为三个事实源

现状概念：

```text
manual TestCase
api TestCase
ui TestCase
```

最终：

```text
TestScenario
 ├ FunctionalProjection
 ├ ApiAdapter
 ├ UiAdapter
 ├ DbAdapter
 └ HybridAdapter
```

兼容期仍允许打开旧 Case，但所有新 AI 生成都先生成 Scenario。

---

## 5.2 停止让 TestPlan 承担核心编排

`TestPlan` 适合：

- 人工测试批次；
- 业务测试集合；
- 报告维度。

它不适合：

- 长任务恢复；
- Worker 调度；
- Data Fixture；
- 多 Driver 编排；
- Human Approval Wait；
- Continuous Acceptance。

这些由 `MissionWorkflow / ExecutionWorkflow` 负责。

---

## 5.3 停止让 LLM 直接生成最终 Oracle

当前“用例 steps + expected_result → LLM → Playwright expect”适合作为原型，但最终必须拆成：

```text
Frozen Oracle
        │
        ├────→ Assertion Compiler
        │
Action Plan
        │
        └────→ Browser/API Command Compiler
```

LLM 可以修 Action，不得自动修改 Frozen Oracle。

---

## 5.4 停止把 PASS/FAIL 当一个简单字段

必须拆：

```text
runtime_status
+
outcome
+
evidence_completeness
+
oracle_results
```

---

# 6. 新平台分层

```text
┌─────────────────────────────────────────────┐
│                  UX Layer                   │
│ Mission / Review / Run / Replay / Assets   │
├─────────────────────────────────────────────┤
│                Domain Layer                 │
│ Scope Contract Scenario Oracle DataReq      │
├─────────────────────────────────────────────┤
│             Intelligence Layer              │
│ ScopeAI ContractAI ScenarioAI TriageAI      │
├─────────────────────────────────────────────┤
│             Orchestration Layer             │
│ Temporal Workflow / Policy / Scheduling     │
├─────────────────────────────────────────────┤
│                Runtime Layer                │
│ Data API Browser DB Assertion Evidence      │
├─────────────────────────────────────────────┤
│                 Worker Layer                │
│ Office / Test / Prod-RO                     │
├─────────────────────────────────────────────┤
│                Storage Layer                │
│ PostgreSQL / Object Storage / OTEL          │
└─────────────────────────────────────────────┘
```

---

# 7. 新的主领域 Aggregate

如果长期架构优先，建议新建：

```text
Mission
```

而不是继续无限扩展旧 `VersionMission`。

## Mission 支持

```text
mission_type:
VERSION
FEATURE
HOTFIX
REGRESSION
EXPLORATORY

lifecycle:
DRAFT
SOURCE_READY
SCOPE_REVIEW
CONTRACT_REVIEW
CONTRACT_FROZEN
SCENARIO_READY
RUNNING
ACCEPTANCE_REVIEW
ACCEPTED
REJECTED
PARTIAL
ARCHIVED
```

旧 `VersionMission`：

```text
VersionMission
   ↓ Migration
Mission(type=VERSION)
```

过渡期保留 `/version-mission` 兼容 API。

---

# 8. 新旧实体映射

```text
旧 RequirementDocument
        │
        └────→ SourceArtifact(type=REQUIREMENT)

旧 OpenAPI Import
        │
        └────→ SourceArtifact(type=OPENAPI)
              + ApiService/Endpoint

旧 VersionMission
        └────→ Mission

旧 TestCase
        ├────→ LegacyScenario (迁移)
        └────→ FunctionalProjection / Adapter

旧 TestPlan
        └────→ ExecutionCampaign

旧 Dataset
        └────→ StaticDataSource

旧 Environment
        └────→ Environment
              └ EnvironmentSnapshot

旧 API Execution
        └────→ ExecutionRun / ExecutionStep / Evidence

旧 UI Run
        └────→ ExecutionRun / ExecutionStep / Evidence

旧 Trace
        └────→ LineageEdge

旧 GeneratedArtifact
        └────→ ArtifactMetadata / EvidenceArtifact

旧 AgentWorkLog
        └────→ AiDecisionRecord / AuditEvent
```

---

# 9. 新增的核心领域对象

```text
Mission

SourceArtifact

ScopeItem
Ambiguity
TestIntent

TestContract
TestContractVersion

TestScenario
ScenarioAdapter
ScenarioActionPlan

TestOracle

DataRequirement
DataSource
DataFixture
FixtureLease

Environment
EnvironmentSnapshot

ExecutionCampaign
ExecutionRun
ExecutionStep
AssertionResult

EvidenceArtifact
ReplayManifest

WorkerNode
WorkerCapability
MissionStep

ContractChangeProposal
ScenarioChangeProposal
ReviewFeedback

QualityGatePolicy
QualityGateResult
```

---

# 10. 新平台三条“主链”

## 10.1 设计链

```text
Source
→ Scope
→ Ambiguity
→ Intent
→ Contract
→ Scenario
```

## 10.2 执行链

```text
Scenario
→ Data Plan
→ Action Plan
→ Oracle Plan
→ Run
→ Evidence
→ Outcome
```

## 10.3 持续验收链

```text
Environment Fingerprint Changed
→ Impact Analysis
→ Regression Selection
→ Run
→ Acceptance
→ RED / GREEN Trend
```

---

# 11. 现有平台已有能力最值得直接复用的部分

## 11.1 OpenAPI / HTTP

复用：

```text
openapi_import_service
api_execution_service
api_change_impact_service
api_generalization_service
api_task_worker（迁移期）
```

升级为：

```text
ContractSourceProvider
ApiDriver
ApiEvidenceCollector
```

---

## 11.2 Playwright

复用：

```text
playwright_executor
ui_test_service
ui_runner_queue
case_compiler_service 中的 locator 经验
```

但重构：

```text
LLM → 完整 spec.ts
```

为：

```text
AI → Command IR / Action Plan
Oracle → Deterministic Assertion Compiler
Runtime → Playwright Driver
```

---

## 11.3 Production Safety

复用并统一：

```text
production_operation_guard
session_credentials_service
audit_service
```

所有 Driver 必须经过同一个 Policy Gateway。

---

## 11.4 Requirement / Knowledge

复用：

```text
requirement_source_service
file_parser_service
requirement_* services
knowledge*
lanhu*
```

统一输出 `SourceArtifact + SourceFragment + SourceRef`。

---

## 11.5 Trace / Artifacts

复用：

```text
trace_service
GeneratedArtifact
InteractionEdge
UI Trace
API request/response snapshot
```

但新系统建立统一：

```text
EvidenceArtifact
ExecutionTimeline
LineageEdge
ReplayManifest
```

---

# 12. 当前必须重点修正的三个技术债

## 12.1 Quality Gate

旧质量门禁偏“资产数量 / 部门留痕 / 总通过率”。

新 Gate 必须以 Contract 为中心：

```text
Scope approved
Contract frozen
P0/P1 Scenario coverage
Required Oracle coverage
Required Scenario executed
Required Evidence complete
P0 BUSINESS_FAIL = 0
P0 INCONCLUSIVE = 0
Contract version matches
Environment snapshot valid
```

绝对禁止：

```text
0 条执行 → Gate PASS
```

---

## 12.2 Dataset

当前静态 CSV/JSON Dataset 可以继续存在，但只能作为：

```text
StaticDataSource
```

真正的数据系统新增：

```text
DataRequirement
DataPlanner
DatabaseDataSource
ApiDataBuilder
WorkflowDataBuilder
Fixture
Lease
Snapshot
Cleanup
Mask
```

---

## 12.3 UI Compiler

当前 LLM 编译整个 Playwright spec 的能力继续保留在：

```text
LegacyCompiler
```

新模式改成：

```text
Scenario
   │
   ├ Data Requirement
   ├ Frozen Oracles
   └ Action Intent
           ↓
    AI Action Planner
           ↓
      Command IR
           ↓
   Playwright Compiler
           ↓
Deterministic Assertions
```

---

# 13. 最终导航结构

建议从当前“模块菜单”升级为两层导航。

## 一级：工作主线

```text
工作台
测试任务 Mission
执行中心
回放与证据
缺陷与验收
```

## 一级：测试资产

```text
需求与资料
场景库
API 资产
UI 自动化资产
测试数据
环境
知识
```

## 一级：治理

```text
Worker
集成
通知
权限
AI 配置
安全策略
审计
```

原有功能没有消失，但测试工程师不再需要在十几个菜单之间完成一次版本测试。

---

# 14. 为什么不建议把所有旧页面删除

成熟测试团队仍然需要：

- 单独调 API；
- 单独调 Playwright；
- 管理环境；
- 查看所有 Dataset；
- 管理历史 Case；
- 调试 AI；
- 查 Audit。

因此采用：

```text
Mission-first
+
Asset Workspaces
+
Admin Workspaces
```

而不是：

```text
Mission-only
```

---

# 15. 迁移原则

## 15.1 Strangler Migration

```text
旧平台照常运行
       │
       ├───────────────┐
       ▼               ▼
Compatibility       New Domain
API / Adapter       Mission Runtime
       │               │
       └─────双读───────┘
              ↓
          数据回填验证
              ↓
          新流程默认
              ↓
          旧写入口关闭
              ↓
          旧页面只读
              ↓
            删除
```

---

## 15.2 新旧事实源规则

迁移中最重要：

```text
同一个业务对象，只能有一个 canonical source of truth。
```

例如 Scenario 已建立后：

- Scenario-bound TestCase 的 Expected 不允许独立改；
- UI Adapter 的 Oracle 不允许独立改；
- API Adapter 的 Expected 不允许独立改。

修改必须回到：

```text
Contract / Scenario Change Proposal
```

---

# 16. 最终产品价值

升级完成后，测试工程师的主流程从：

```text
读需求
→ 写 Case
→ 找 API
→ 找账号
→ 查 DB
→ 写自动化
→ 跑
→ 失败后重新复现
→ 截图
→ 报 Bug
```

变成：

```text
创建 Mission
→ Review AI Scope / Ambiguity
→ Freeze Contract
→ Review Scenario
→ 选择/确认数据策略
→ Run
→ Replay 审计
→ 处理真正的 BUSINESS_FAIL
→ 新 Build 自动回归
```

平台真正替代的是测试工程师的**重复操作和信息搬运**，而不是测试判断本身。
