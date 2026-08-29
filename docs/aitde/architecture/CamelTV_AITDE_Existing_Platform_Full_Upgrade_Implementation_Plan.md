# CamelTV 测试平台 → AITDE 完整升级方案包

> 基线：现有 `cameltv-test-platform/test-platform-v2`  
> 目标：将现有“测试资产/工具型平台”升级为 **Mission-Centered AI Test-Driven Engineering Runtime**。  
> 原则：本方案**不以最小改动为目标**，而以长期最合理、最可维护、最适合测试工程师使用为目标；现有可复用能力通过 Adapter/迁移方式保留，领域模型和主用户路径允许重构。

## 文档清单

1. `01_Overall_Upgrade_Blueprint.md`  
   现有模块逐项判断：保留 / 重构 / 合并 / 降级 / 新增；最终目标架构和迁移原则。

2. `02_Backend_Implementation_Design.md`  
   后端领域模型、数据库、Temporal Workflow、Driver、Worker、Data、Assertion、Evidence、Replay、API、事件、安全和测试策略。

3. `03_Frontend_UX_Implementation_Design.md`  
   测试工程师从需求评审到功能测试、API/UI 自动化、执行审计、回放、RED→GREEN 的完整前端信息架构、页面、交互和状态设计。

4. `04_Version_Roadmap_and_Migration.md`  
   按版本拆解的实施路线、兼容策略、数据迁移、旧模块退出策略和每版验收标准。

## 最终产品中心

```text
Mission
  ↓
Sources
  ↓
Scope / Ambiguity Review
  ↓
Frozen Test Contract
  ↓
Executable Scenario
  ↓
Data + Action + Oracle
  ↓
Hybrid Runtime
  ↓
Evidence / Replay
  ↓
Acceptance
  ↓
New Build → RED → GREEN
```

## 一句话原则

> 不再让“功能用例、接口用例、UI 自动化”成为三个独立中心；让它们成为同一 `TestScenario` 的人类视图和执行 Adapter。

> 不再让 AI 同时负责“出题、执行、判卷”；AI 负责理解与规划，Frozen Oracle + Deterministic Assertion + Evidence 负责裁决。

> 不再把测试平台理解成“测试结束后记录结果的地方”；Mission 从需求评审阶段就创建，并持续存在到版本验收结束。


---

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


---

# 02｜AITDE 后端落地实现设计

## 1. 后端总原则

现有 FastAPI / SQLAlchemy 技术栈可以继续保留。

在不考虑改造成本时，建议进行一次“模块化单体”重构，而不是继续把所有业务堆在：

```text
app/models
app/services
app/api/v1
```

也不建议直接拆微服务。

推荐：

```text
backend/app/
├ domain/
├ modules/
├ intelligence/
├ orchestration/
├ drivers/
├ workers/
├ evidence/
├ integrations/
├ platform/
└ api/
```

原因：

- 领域复杂度会快速超过基础 CRUD；
- TestContract / Scenario / Runtime 有明确一致性边界；
- 微服务过早拆分会制造分布式事务和调试复杂度；
- 模块化单体 + Temporal Worker 已足够隔离执行能力。

---

# 2. 基础设施目标态

```text
FastAPI Control Plane
        │
        ├ PostgreSQL
        ├ MinIO / S3
        ├ Temporal
        ├ OpenTelemetry
        ├ Vault / Secret Store
        └ OPA / Policy Engine
              │
              ▼
        Network Workers
```

## PostgreSQL

建议：

- 所有共享环境统一 PostgreSQL；
- SQLite 只保留给极轻量本地开发，或者彻底去掉；
- JSONB 承载 flexible schema；
- 核心关系仍使用 FK；
- 重要 immutable version 使用 append-only table。

---

# 3. 后端模块边界

```text
modules/
  mission/
  source/
  scope/
  contract/
  scenario/
  data/
  environment/
  execution/
  evidence/
  acceptance/
  defect/
```

```text
intelligence/
  scope_analyst/
  ambiguity_detector/
  contract_builder/
  scenario_designer/
  action_planner/
  failure_triage/
  healing_advisor/
```

```text
drivers/
  requirement/
  openapi/
  api/
  browser/
  database/
  data/
  assertion/
  evidence/
```

---

# 4. Mission 数据模型

## missions

```sql
id                  bigint pk
project_id          bigint not null
mission_key         varchar unique(project_id, mission_key)
mission_type        varchar
title               varchar
version_label       varchar
status              varchar
owner_id            bigint
default_environment_id bigint null
current_contract_version_id bigint null
latest_environment_snapshot_id bigint null
acceptance_status   varchar
created_by          bigint
created_at
updated_at
archived_at
```

不要再把大量业务字段直接放 Mission。

来源、环境、Contract、Plan 全用关系表。

---

# 5. Source 模型

## source_artifacts

```text
id
project_id
mission_id
source_type
provider
name
uri
content_hash
version_label
sensitivity
parse_status
parser_version
metadata jsonb
created_at
```

## source_fragments

```text
id
artifact_id
fragment_key
title
text
location jsonb
embedding optional
content_hash
```

## source_refs

统一引用：

```json
{
  "artifact_id": 10,
  "fragment_id": 333,
  "location": "PRD 3.2.1"
}
```

AI 每一个 Scope/Oracle/Scenario 结论都带 SourceRef。

---

# 6. Scope / Ambiguity

## scope_items

```text
id
mission_id
scope_type
name
decision
test_depth
risk_level
reason
ai_confidence
review_status
reviewed_by
reviewed_at
source_refs jsonb
```

## ambiguities

```text
id
mission_id
title
description
severity
status
candidate_options jsonb
selected_option jsonb
source_refs jsonb
resolution_note
resolved_by
resolved_at
```

冻结 Contract 前可配置：

```text
P0/P1 ambiguity 必须 resolved
```

---

# 7. Intent / Contract

## test_intents

```text
id
mission_id
intent_key
title
business_goal
required_outcomes jsonb
source_refs jsonb
status
```

## test_contracts

```text
id
mission_id
name
current_version_no
created_at
```

## test_contract_versions

```text
id
contract_id
version_no
status
content_hash
snapshot jsonb
created_by
created_at
approved_by
approved_at
supersedes_version_id
```

### 不可变设计

`FROZEN` 后版本记录禁止 UPDATE。

修改：

```text
FROZEN v3
  ↓
ChangeProposal
  ↓ approve
DRAFT v4
  ↓ freeze
FROZEN v4
```

建议：

- ORM 层禁止；
- service 层禁止；
- 数据库触发器额外保护 frozen rows。

---

# 8. Contract Change Proposal

## change_proposals

```text
id
mission_id
target_type
target_id
target_version
proposal_type
reason
diff jsonb
source_refs jsonb
created_by_type
created_by
status
reviewed_by
reviewed_at
```

`created_by_type`：

```text
USER
AI
SYSTEM
```

AI 永远只能创建 Proposal。

---

# 9. TestScenario 模型

## test_scenarios

```text
id
project_id
mission_id
contract_version_id
scenario_key
title
business_goal
priority
risk_level
status
given_model jsonb
when_model jsonb
expected_state jsonb
source_refs jsonb
version_no
created_by_type
created_at
updated_at
```

Scenario 本身也做版本化。

对于 Contract 版本变化：

```text
Scenario v2
→ mark stale
→ AI生成 ScenarioChangeProposal
→ tester review
→ Scenario v3
```

---

# 10. Oracle

## test_oracles

```text
id
scenario_id
scenario_version
oracle_key
oracle_type
target jsonb
operator
expected_value jsonb
source_type
source_refs jsonb
required boolean
confidence numeric
review_status
created_at
```

类型：

```text
UI
API
DB
EVENT
LOG
CONTRACT
VISUAL
PERFORMANCE
```

第一期执行支持：

```text
UI / API / DB
```

---

# 11. Functional View

不新建第二份 Expected。

提供：

```text
ScenarioProjectionService
```

输出：

```json
{
  "title": "...",
  "preconditions": [...],
  "steps": [...],
  "expected_results": [...],
  "priority": "P0"
}
```

用户修改 Functional View 时：

- 如果只是文案：更新 projection override；
- 如果改变业务规则：自动创建 Scenario/Contract Change Proposal。

---

# 12. 旧 TestCase 兼容

给旧 TestCase 增加：

```text
scenario_id nullable
scenario_version nullable
projection_type nullable
is_legacy boolean
canonical_source varchar
```

规则：

```text
scenario_id is null
→ Legacy TestCase，可直接编辑

scenario_id is not null
→ Projection，不允许独立修改业务 Expected
```

最终旧 TestCase 表可以保留为 export / integration 层，不再作为核心运行时事实源。

---

# 13. Scenario Adapter

## scenario_adapters

```text
id
scenario_id
scenario_version
adapter_type
adapter_version
status
compiled_plan_id
last_validation_at
metadata jsonb
```

类型：

```text
MANUAL
API
UI
DB
HYBRID
```

---

# 14. Command IR

这是后端改造最重要的实现点之一。

不要让 Runtime 直接吃 LLM 代码。

## command_plans

```text
id
scenario_adapter_id
schema_version
plan_hash
commands jsonb
generated_by
model_ref
prompt_version
created_at
```

示例：

```json
{
  "schema_version": "1.0",
  "commands": [
    {
      "id": "step-1",
      "driver": "data",
      "action": "ensure",
      "input": {"requirement_ref": "expired-member"}
    },
    {
      "id": "step-2",
      "driver": "browser",
      "action": "goto",
      "input": {"route": "/member"}
    },
    {
      "id": "step-3",
      "driver": "browser",
      "action": "click",
      "input": {
        "locator": {
          "strategy": "role",
          "role": "button",
          "name": "立即续费"
        }
      }
    },
    {
      "id": "step-4",
      "driver": "assertion",
      "action": "evaluate",
      "input": {"oracle_key": "membership-status"}
    }
  ]
}
```

---

# 15. IR Schema Registry

所有 command 必须：

```text
Pydantic schema validate
↓
Policy validate
↓
Capability validate
↓
Execute
```

禁止未知 command 直接运行。

例如：

```text
browser.goto@v1
browser.click@v1
browser.fill@v1

api.request@v1
api.wait_for@v1

db.select@v1
db.fixture_insert@v1

data.ensure@v1
data.cleanup@v1

assert.evaluate@v1
```

---

# 16. Driver Protocol

```python
class Driver(Protocol):
    name: str
    capabilities: set[str]

    async def prepare(self, ctx: RuntimeContext) -> DriverPrepareResult:
        ...

    async def execute(
        self,
        command: Command,
        ctx: RuntimeContext,
    ) -> DriverResult:
        ...

    async def collect_evidence(
        self,
        ctx: RuntimeContext,
    ) -> list[EvidenceRef]:
        ...

    async def cleanup(self, ctx: RuntimeContext) -> CleanupResult:
        ...
```

Driver 不知道 LLM。

Driver 只知道：

```text
Command
Policy
Context
```

---

# 17. 当前 Service → Driver 迁移

| 当前 Service | 目标 |
|---|---|
| openapi_import_service | OpenApiSourceDriver |
| api_execution_service | ApiRuntimeDriver |
| case_compiler_service | LegacyCompiler + ActionPlanCompiler |
| playwright_executor | BrowserRuntimeDriver |
| xhr_capture_service | BrowserObserverDriver |
| dataset_service | StaticDatasetAdapter |
| production_operation_guard | PolicyGateway |
| trace_service | Lineage/Evidence Service |
| file_parser_service | RequirementSourceDriver |
| requirement_source_service | RequirementSourceProvider |

---

# 18. Assertion Engine

Assertion 必须独立于 AI。

```python
class AssertionEngine:
    async def evaluate(
        oracle: TestOracle,
        observations: ObservationStore,
        context: RuntimeContext
    ) -> AssertionResult:
        ...
```

## Observation

Driver 执行后统一产生：

```text
Observation
```

例如：

```json
{
  "type": "DB_ROW",
  "target": "membership:123",
  "data": {"status": "EXPIRED"}
}
```

Assertion Engine：

```text
Oracle:
membership.status == ACTIVE

Observation:
EXPIRED

Result:
FAIL
```

---

# 19. Outcome Classifier

不是 AI 分类。

用确定性决策表：

```text
if env_error:
  ENV_FAIL

elif data_prepare_error:
  DATA_FAIL

elif automation_error before required oracle point:
  AUTOMATION_FAIL

elif assertion_engine_error:
  ASSERTION_ERROR

elif required_oracle_failed:
  BUSINESS_FAIL

elif required_oracle_not_evaluated:
  INCONCLUSIVE

elif all_required_oracles_pass and evidence_complete:
  PASS

else:
  INCONCLUSIVE
```

AI Failure Triage 在 Outcome 之后运行。

---

# 20. Data Domain

当前 Dataset 作为静态数据继续支持。

新增：

## data_sources

```text
id
project_id
environment_id
source_type
name
network_zone
secret_ref
access_mode
policy_ref
config jsonb
status
```

source_type：

```text
STATIC
MYSQL
POSTGRES
API
WORKFLOW
PROD_TEMPLATE
```

---

# 21. DataRequirement

```text
id
scenario_id
requirement_key
entity_type
constraints jsonb
required
sharing_policy
cleanup_policy
```

例：

```json
{
  "entity_type": "member",
  "constraints": {
    "status": {"eq": "EXPIRED"},
    "wallet.balance": {"gte": 100}
  }
}
```

---

# 22. Data Planner

```text
ExistingFinder
→ ApiBuilder
→ DbFixtureBuilder
→ WorkflowBuilder
→ ProdTemplateBuilder
```

Planner 返回：

```text
DataPlan
```

而不是直接执行。

测试工程师可以在高风险数据策略前审核。

---

# 23. Fixture

## data_fixtures

```text
id
project_id
scenario_id
run_id
strategy
status
manifest jsonb
namespace
created_at
expires_at
cleanup_status
```

## fixture_leases

避免不同并发 Run 抢同一个用户。

```text
fixture_id
run_id
lease_token
leased_at
expires_at
released_at
```

---

# 24. DB Driver

生产与测试必须是两个权限模型。

## TEST

可以：

```text
SELECT
受控 INSERT
受控 UPDATE
受控 DELETE/CLEANUP
```

仅允许：

- allowlisted schema/table；
- fixture namespace；
- transaction boundary；
- statement timeout。

## PROD_RO

必须：

```text
DB account = READ ONLY
Policy = SELECT only
row limit
statement timeout
schema allowlist
PII sanitizer
```

AI 看不到 connection string。

---

# 25. Environment

## environments

保存：

```text
环境逻辑定义
base URLs
auth profile refs
data source refs
network zone
policy profile
```

## environment_snapshots

每个 Run 必须有：

```text
build_label
frontend_version
service_versions
openapi_hash
db_schema_version
config_hash
static_asset_hash
manual_note
captured_at
```

没有 Git 也可以识别 Build。

---

# 26. Execution Domain

## execution_runs

```text
id
mission_id
scenario_id
scenario_version
contract_version_id
adapter_id
environment_id
environment_snapshot_id
runtime_status
outcome
evidence_status
worker_group
started_at
finished_at
duration_ms
parent_run_id
retry_no
```

---

# 27. Execution Step

```text
id
run_id
sequence
command_id
driver
action
status
outcome
started_at
finished_at
input_snapshot_ref
output_snapshot_ref
error_type
error_message
trace_id
span_id
```

Timeline 必须 append-only。

---

# 28. Evidence

## evidence_artifacts

```text
id
run_id
step_id
evidence_type
storage_uri
content_hash
content_type
size_bytes
sanitization_status
sensitivity
retention_class
created_at
```

类型：

```text
SCREENSHOT
VIDEO
PW_TRACE
DOM
HAR
REQUEST
RESPONSE
DB_BEFORE
DB_AFTER
CONSOLE
LOG
ASSERTION
FIXTURE_MANIFEST
ENV_SNAPSHOT
```

---

# 29. Object Storage

不要再把大产物塞数据库。

推荐：

```text
S3 / MinIO

/project/{project_id}
/mission/{mission_id}
/run/{run_id}/...
```

数据库只存 metadata + hash。

---

# 30. Replay Manifest

```json
{
  "run_id": 812,
  "contract_version": 3,
  "scenario_version": 4,
  "environment_snapshot": "envsnap-19",
  "timeline": [...],
  "assertions": [...],
  "evidence_refs": [...]
}
```

Replay API 不需要重新拼多个旧表。

---

# 31. Temporal 作为正式编排核心

既然不考虑时间成本，建议直接把 Temporal 纳入目标架构，而不是继续扩建 DB Poll Worker。

## Workflow 1：MissionDesignWorkflow

```text
ingest_sources
→ analyze_scope
→ WAIT tester_scope_review
→ detect_ambiguity
→ WAIT ambiguity_resolution
→ build_contract
→ WAIT contract_freeze
→ build_scenarios
→ WAIT scenario_review(optional)
→ ready
```

Human review 用 Signal。

---

# 32. Workflow 2：ScenarioExecutionWorkflow

```text
capture_environment_snapshot
→ plan_data
→ ensure_fixture
→ compile_action_plan
→ policy_check
→ execute_commands
→ evaluate_oracles
→ collect_evidence
→ classify_outcome
→ cleanup_fixture
→ build_replay
→ triage_if_needed
```

---

# 33. Workflow 3：ContinuousAcceptanceWorkflow

```text
observe_environment
→ fingerprint_changed?
→ compute_impact
→ select_scenarios
→ fan_out ScenarioExecutionWorkflow
→ aggregate_acceptance
→ publish_gate
→ wait_next_change
```

---

# 34. Worker 架构

不建议自己重新设计一整套 poll/lock 协议。

Temporal Worker 本身可以 Pull Task Queue。

部署：

```text
worker-office
worker-test-a
worker-test-b
worker-prod-ro
```

每个 Worker：

```text
mTLS
machine identity
capability manifest
secret access scope
network zone
```

---

# 35. Capability Routing

Worker 注册：

```json
{
  "worker_id": "test-a-01",
  "zone": "TEST",
  "capabilities": [
    "HTTP",
    "BROWSER",
    "MYSQL"
  ],
  "tags": ["member", "payment"]
}
```

Workflow 根据 Step 要求选择 Task Queue。

---

# 36. Secret 管理

业务数据库、Session、Token：

```text
secret_ref
```

Worker 运行时：

```text
resolve secret
→ inject process memory
→ execute
→ destroy reference
```

不写：

- Prompt；
- DB；
- Timeline；
- Evidence；
- stdout。

---

# 37. Policy Gateway

所有危险 Command 执行前调用：

```text
PolicyDecision
```

输入：

```text
actor
project
mission
environment
network_zone
driver
action
target
command_metadata
```

输出：

```text
ALLOW
DENY
REQUIRE_APPROVAL
```

生产策略在 Policy 层，而不是 Prompt。

---

# 38. IntelligenceProvider

业务服务不能直接依赖 DeepSeek/OpenAI/LangGraph。

```python
class IntelligenceProvider(Protocol):
    async def analyze_scope(...): ...
    async def detect_ambiguities(...): ...
    async def build_contract(...): ...
    async def design_scenarios(...): ...
    async def plan_actions(...): ...
    async def triage_failure(...): ...
    async def propose_healing(...): ...
```

Provider 可以实现：

```text
LangGraphProvider
DirectLLMProvider
InternalModelProvider
```

---

# 39. AI Output Contract

所有正式 AI 输出：

```text
JSON Schema / Pydantic
```

禁止把自由 Markdown 直接保存为业务事实。

每次调用保存：

```text
model
model_config_hash
prompt_template_version
input_hash
output_hash
schema_version
source_refs
duration
token_usage
```

不保存隐藏思维链。

---

# 40. AgentWorkLog 的最终处理

现有 AgentWorkLog 可以迁移为：

```text
ai_operation_records
```

保留：

- action；
- model；
- input/output reference；
- duration；
- structured summary。

不要再用“department”作为质量门禁核心。

---

# 41. Event / Outbox

建议所有重要领域变化发 Domain Event：

```text
ScopeApproved
ContractFrozen
ScenarioApproved
RunStarted
RunFinished
BusinessFailureDetected
EnvironmentFingerprintChanged
QualityGateChanged
```

使用 Transactional Outbox 保证 DB 状态与事件一致。

用途：

- SSE；
- 通知；
- report；
- webhook；
- analytics。

---

# 42. 前端实时更新接口

建议：

```text
GET /missions/{id}/events/stream
GET /runs/{id}/events/stream
```

使用 SSE 足够。

需要双向控制时：

- REST Command；
- SSE Event。

不必为了实时状态全部改 WebSocket。

---

# 43. API 分组

## Mission

```text
POST   /api/v2/missions
GET    /api/v2/missions
GET    /api/v2/missions/{id}
PATCH  /api/v2/missions/{id}
```

## Source

```text
POST /missions/{id}/sources
GET  /missions/{id}/sources
POST /sources/{id}/parse
GET  /sources/{id}/fragments
```

## Scope

```text
POST /missions/{id}/scope/analyze
GET  /missions/{id}/scope
POST /missions/{id}/scope/reviews
```

## Ambiguity

```text
GET  /missions/{id}/ambiguities
POST /ambiguities/{id}/resolve
```

## Contract

```text
POST /missions/{id}/contracts/generate
GET  /missions/{id}/contracts
GET  /contracts/{id}/versions/{version}
POST /contracts/{id}/freeze
POST /contracts/{id}/change-proposals
```

## Scenario

```text
POST /contracts/{version_id}/scenarios/generate
GET  /missions/{id}/scenarios
GET  /scenarios/{id}
POST /scenarios/{id}/reviews
POST /scenarios/{id}/adapters/compile
```

## Data

```text
POST /scenarios/{id}/data/plan
GET  /data-sources
POST /fixtures/ensure
GET  /fixtures/{id}
POST /fixtures/{id}/cleanup
```

## Run

```text
POST /scenarios/{id}/runs
POST /missions/{id}/runs
GET  /runs/{id}
POST /runs/{id}/cancel
POST /runs/{id}/retry
```

## Replay

```text
GET /runs/{id}/timeline
GET /runs/{id}/assertions
GET /runs/{id}/evidence
GET /runs/{id}/replay
```

## Acceptance

```text
GET  /missions/{id}/acceptance
POST /missions/{id}/quality-gate/evaluate
GET  /missions/{id}/builds
```

---

# 44. Compatibility API

旧前端过渡期继续：

```text
/api/v1/testcase
/api/v1/apitest
/api/v1/uitest
/api/v1/testplan
/api/v1/version-mission
```

但新核心只写：

```text
/api/v2/...
```

旧 API 的新建请求可以在后期改为创建 Scenario Projection。

---

# 45. OpenAPI 类型生成

现有前端已经有 OpenAPI TS 类型生成习惯，应继续强化：

```text
backend OpenAPI
→ generated frontend client/types
```

不手写重复 DTO。

---

# 46. Backend Error Model

统一错误：

```json
{
  "code": "CONTRACT_FROZEN",
  "message": "Frozen contract cannot be mutated.",
  "details": {},
  "trace_id": "..."
}
```

前端不要通过中文字符串判断业务错误。

---

# 47. 可观测性

所有 Run / Step / Driver：

```text
mission_id
scenario_id
run_id
step_id
worker_id
trace_id
```

写入 OTEL Attributes。

指标：

```text
run_duration
driver_error_rate
worker_queue_latency
fixture_prepare_latency
assertion_latency
evidence_upload_latency
```

---

# 48. 测试策略

## Domain Unit Test

必须覆盖：

- Frozen Contract 不可变；
- Outcome Classification；
- Required Oracle；
- Gate；
- Fixture state machine；
- Proposal versioning。

## Driver Integration Test

针对真实：

```text
HTTP test server
Postgres/MySQL container
Playwright sample site
MinIO
Temporal test environment
```

## Golden Scenario Benchmark

维护一批人工确认的：

```text
PRD
Scope
Contract
Scenario
Oracle
Outcome
```

用于评估 AI 版本变化。

## Security Test

特别覆盖：

```text
secret redaction
prod write denial
SQL bypass
artifact leakage
cross-project access
worker capability escalation
```

---

# 49. 后端关键验收条件

在进入正式默认流程前，后端至少做到：

```text
1. Frozen Contract 无法直接修改。
2. Required Oracle 未执行不能 PASS。
3. ENV/DATA/AUTOMATION error 不会被分类为 BUSINESS_FAIL。
4. Evidence 不完整不能可信 PASS。
5. Worker 重试不会重复制造不可清理数据。
6. Run 永远绑定 EnvironmentSnapshot。
7. 所有 Artifact 有 checksum。
8. Prod Worker 默认无写权限。
9. Secret 不进入 Prompt/Evidence。
10. 所有 AI 输出 schema validated。
```

---

# 50. 后端最终完成标准

后端完成后，前端只需要表达：

```text
用户意图
↓
API Command
↓
Workflow
↓
Driver
↓
Evidence
↓
Domain State
↓
SSE Event
```

前端不应自己承担：

- 质量判定；
- Scope 计算；
- PASS/FAIL 计算；
- Contract 版本逻辑；
- Fixture 调度；
- Worker 路由。


---

# 03｜AITDE 前端与测试工程师使用方案

## 1. 前端设计目标

测试工程师不应该学习“AI Agent 怎么工作”。

他需要解决的是：

```text
我要测哪个版本？
AI认为要测什么？
有没有理解歧义？
什么才算正确？
有哪些 Scenario？
数据准备好了没有？
哪些已经能跑？
为什么 PASS？
为什么 FAIL？
这个 Build 比上一个 Build 好了多少？
```

因此前端核心不是 Chat，而是：

> **Review + Run + Replay。**

Chat 可以存在，但只是辅助入口。

---

# 2. 技术栈建议

现有 React 19 + TypeScript + React Router + shadcn/Radix/Tailwind 可以继续使用。

没有必要为了新架构切 Next.js。

建议新增：

```text
TanStack Query
```

用于 Server State。

职责：

```text
Zustand
→ auth / project / local UI state

TanStack Query
→ mission / scope / contract / scenario / run / replay

SSE
→ live execution / workflow events
```

不要把新的 Mission 数据全部塞 Zustand。

---

# 3. 新信息架构

## 主导航

```text
工作台
测试任务
执行中心
回放与证据
缺陷与验收

──────────

测试资产
  需求与资料
  场景库
  API 资产
  UI 自动化
  测试数据
  环境
  知识

──────────

系统治理
  Worker
  集成
  通知
  AI 配置
  策略
  审计
```

---

# 4. Workbench 重构

旧 Workbench 不再主要展示：

```text
case count
plan count
defect count
```

而展示“我今天需要处理什么”。

```text
┌─────────────────────────────────────────────┐
│ 我的测试任务                                │
│                                             │
│ 会员中心 V3.6   Contract 待确认      [进入] │
│ 支付 V2.9       3 个 P0 FAIL         [进入] │
│ 赛事 V4.1       Build #18 正在执行    [进入] │
├─────────────────────────────────────────────┤
│ 待我确认                                    │
│ Scope 12 项 | Ambiguity 4 | Contract 2      │
├─────────────────────────────────────────────┤
│ 真实业务失败                                │
│ BUSINESS_FAIL 8                              │
├─────────────────────────────────────────────┤
│ 自动化问题                                  │
│ AUTOMATION_FAIL 3 | DATA_FAIL 2             │
└─────────────────────────────────────────────┘
```

---

# 5. 创建 Mission：不要做复杂表单

建议 3 步向导。

## Step 1 基本信息

```text
任务名称
版本标签
测试负责人
默认测试环境
Mission Type
```

类型：

```text
版本测试
功能测试
Hotfix
回归
探索
```

---

## Step 2 导入 Sources

同一页面支持：

```text
拖 PRD
粘需求链接
选择已有需求
OpenAPI URL
OpenAPI File
选择 Test DB
关联历史缺陷
```

每个 Source 显示：

```text
已读取
解析中
解析失败
敏感等级
版本 / hash
```

---

## Step 3 AI 分析

用户点击：

```text
开始分析测试范围
```

不是：

```text
直接生成所有用例
```

---

# 6. Mission Detail

路由：

```text
/missions/:missionId
```

子页：

```text
/overview
/sources
/scope
/contract
/scenarios
/data
/executions
/replay
/trace
```

顶部固定 Mission Header：

```text
会员中心 V3.6
Contract v3 FROZEN
Build #18
Acceptance: NOT READY

[运行回归] [导出] [...]
```

---

# 7. Overview

测试工程师第一眼需要：

```text
当前最重要的问题
```

而不是一堆统计图。

建议：

```text
┌ Scope ──────┐ ┌ Contract ────┐ ┌ Acceptance ──┐
│ 24/24 已确认│ │ v3 FROZEN    │ │ NOT READY    │
└─────────────┘ └───────────────┘ └──────────────┘

阻塞：
🔴 2 个 P0 BUSINESS_FAIL
🟠 1 个 P0 INCONCLUSIVE
🟡 3 个 Automation Fail

最新 Build：
#18

Scenario:
PASS 52
BUSINESS_FAIL 3
AUTOMATION_FAIL 2
DATA_FAIL 1
BLOCKED 4
```

---

# 8. Sources 页面

左侧 Source List：

```text
PRD v3
OpenAPI 2026-08-28
Test DB Schema
Historical Defects
Production Observation
```

中间内容阅读器。

右侧：

```text
AI 提取实体
关联 Scope
引用位置
```

测试工程师点击任何 AI 结论，都可以：

```text
查看来源
```

---

# 9. Scope Review 是第一个核心 UX

建议三栏。

```text
┌──────────────┬────────────────────────┬───────────────┐
│ 需求章节     │ AI Scope Proposal      │ Review        │
│              │                        │               │
│ PRD 3.2      │ 会员续费 P0 FULL       │ ✓ Include     │
│              │ Reason: ...            │ ○ Exclude     │
│              │ API: /renew            │ Depth: Full   │
│              │ DB: membership         │ Risk: P0      │
└──────────────┴────────────────────────┴───────────────┘
```

支持批量：

```text
批准全部低风险建议
仅查看 P0/P1
仅查看 AI confidence < 0.8
```

---

# 10. Scope 必须显示“为什么”

每个 Scope Item：

```text
会员续费
P0 / FULL

为什么纳入：
- PRD 3.2 有修改
- POST /member/renew Schema 变化
- 历史上该模块 3 次线上缺陷

来源：
[PRD 3.2] [OpenAPI diff] [DEFECT-822]
```

不要只显示：

```text
AI建议：Full
```

---

# 11. Ambiguity 页面

测试工程师不需要审 1000 条 Case，优先审：

> AI 不确定的地方。

```text
⚠ Grace Period 是否允许续费？

PRD：
仅说明 EXPIRED

API：
renewable = true

DB：
存在 GRACE_PERIOD

[允许]
[不允许]
[本版本不测]
[需要产品确认]
```

点击选项后直接记录为 Contract 输入。

---

# 12. Contract 页面

Contract 页面不是大段 JSON。

按业务规则展示。

```text
会员续费

成功标准
✓ Order = SUCCESS
✓ Membership = ACTIVE
✓ Privilege usable = true
✓ UI 显示新有效期

禁止条件
✓ SUSPENDED 不允许续费

待确认
0

来源可信度
Requirement Explicit  3
Tester Approved       2
AI Inferred           0
```

---

# 13. Freeze Interaction

点击：

```text
冻结 Contract v3
```

弹窗明确：

```text
冻结后：
- AI 不能修改业务预期
- 已生成 Scenario 将绑定 v3
- 后续修改将创建 v4 Proposal

未解决 P0/P1 Ambiguity：0

[确认冻结]
```

这是非常重要的信任操作。

---

# 14. Contract Diff

后续 v4：

```text
v3                 v4

EXPIRED 可续费       EXPIRED 可续费
GRACE 未定义     →  GRACE 可续费
```

高亮：

```text
哪些 Scenario 受影响
哪些 Oracle stale
哪些 Run 需要重跑
```

---

# 15. Scenario Matrix 是测试工程师主工作区

```text
Scenario            Risk  Data  Manual API UI DB Hybrid  Last

过期会员续费          P0    ✓     ✓    ✓  ✓  ✓    ✓     PASS
余额不足              P0    ✓     ✓    ✓  -  ✓    ✓     PASS
重复点击              P1    ✓     ✓    ✓  ✓  ✓    ✓     FAIL
Amount 边界           P1    -     ✓    ✓  -  -    -     PASS
UI 有效期展示         P1    ✓     ✓    -  ✓  -    -     PASS
```

支持：

```text
按风险
按模块
按功能点
按状态
按 Build
按 Adapter
```

---

# 16. Scenario Detail

布局：

```text
┌─────────────────────────────────────────────────────┐
│ MEMBER-RENEW-001 | P0 | Contract v3                │
├─────────────────────────────────────────────────────┤
│ Business Goal                                       │
│ 过期会员续费后立即恢复权益                           │
├────────────────┬────────────────────────────────────┤
│ Given          │ user normal                       │
│                │ membership expired                │
│                │ balance >= 100                    │
├────────────────┼────────────────────────────────────┤
│ When           │ renew monthly                     │
├────────────────┼────────────────────────────────────┤
│ Then / Oracle  │ DB membership = ACTIVE            │
│                │ API privilege usable = true       │
│                │ UI shows active                   │
├────────────────┴────────────────────────────────────┤
│ Sources: PRD 3.2.1 | API /renew | Tester approved  │
└─────────────────────────────────────────────────────┘
```

---

# 17. Functional View

测试工程师仍然可以点击：

```text
[功能用例视图]
```

看到传统：

```text
前置条件
步骤
预期
```

并可以：

```text
开始人工执行
```

这是功能测试阶段特别重要的能力。

---

# 18. Assisted Manual Execution

最终平台不应该逼所有功能测试都立即自动化。

人工执行也使用同一个 Scenario。

用户点击：

```text
开始人工执行
```

系统先：

```text
自动准备 Data Fixture
```

然后进入：

```text
步骤 1 / 5
登录用户

[已完成]
[失败]
[阻塞]
[添加截图]
```

与此同时平台可以后台：

- 记录 Browser Session（如果在受控浏览器中）；
- 抓 XHR；
- 采集 Screenshot；
- 自动执行 DB/API Oracle；
- 保存人工备注。

这样：

> 功能测试阶段已经进入 Runtime，而不是等 UI 自动化写完以后才享受平台能力。

---

# 19. Record / Observe Mode

功能测试工程师第一次手工走业务时：

```text
[开始观察模式]
```

平台打开 Browser Session：

```text
Tester 操作
     ↓
Browser Observer
     ├ DOM semantic event
     ├ click/input
     ├ navigation
     ├ XHR/fetch
     ├ screenshot
     └ timing
```

结束后：

```text
AI 建议生成 UI Action Plan
```

测试工程师 Review 后形成 Regression Adapter。

这比让 AI 自己一开始盲点生产/测试页面更可靠。

---

# 20. Data Workspace

不要让测试工程师首先看到 SQL。

看到：

```text
Scenario 需要的数据

Member
  status = EXPIRED

Wallet
  balance >= 100
```

系统给策略：

```text
✓ Test DB 已找到符合数据
  User #T-8892

或者：

需要创建
  Strategy: API Builder
  预计 3 个实体

[预览数据计划]
[准备]
```

---

# 21. 数据 Plan 详情

高级模式：

```text
Data Plan

1. Create user
2. Create member
3. Set membership expired
4. Set balance 100
5. Lease for Run
6. Cleanup after run

Affected:
member_test.user
member_test.membership
member_test.wallet
```

测试工程师可以知道 AI 要造什么，而不是让它偷偷改数据库。

---

# 22. Execution Launch

点击：

```text
运行
```

弹出：

```text
Environment:
TEST-5

Build:
2026-08-28.18

Scope:
○ 当前 Scenario
○ 当前模块
● 受影响 Scenario
○ 全量

Data:
● Auto Prepare

Browser:
Chromium

Evidence:
✓ Screenshot
✓ Trace
✓ Network
✓ DB Snapshot

[执行]
```

---

# 23. Preflight Check

真正执行前系统自动：

```text
Environment reachable      ✓
Worker available            ✓
DataSource reachable        ✓
Required Secret available   ✓
Contract Frozen             ✓
Scenario compiled           ✓
Required Oracle supported   ✓
```

有问题：

```text
禁止开始
```

这能减少很多“跑了半天才发现环境/数据不对”。

---

# 24. Live Execution

```text
RUN #812

PREPARING_DATA  ✓
EXECUTING       ●
ASSERTING
COLLECTING
CLASSIFYING

Timeline
09:31:02 DATA  ensure expired member     ✓
09:31:05 UI    login                     ✓
09:31:08 API   GET /membership           200
09:31:12 UI    click 立即续费             ●
```

前端通过 SSE 实时更新。

---

# 25. Outcome UI 必须避免所有错误都显示红色 FAIL

建议：

```text
PASS                 ✓
BUSINESS_FAIL         ✕ 业务失败
AUTOMATION_FAIL       ⚙ 自动化问题
DATA_FAIL             ◇ 数据问题
ENV_FAIL              ◇ 环境问题
ASSERTION_ERROR       ! 断言配置
BLOCKED               ⊘ 尚不可测
INCONCLUSIVE          ? 无法裁决
```

同时始终显示文字，不只依赖颜色。

---

# 26. Replay 是第二个核心 UX

三栏：

```text
┌───────────────┬───────────────────────┬─────────────────┐
│ Timeline      │ Visual / Browser      │ Evidence Detail │
│               │                       │                 │
│ DATA ✓        │ Screenshot / DOM      │ Request         │
│ LOGIN ✓       │                       │ Response        │
│ POST 200 ✓    │                       │ DB Before       │
│ DB ✕          │                       │ DB After        │
│ ASSERT ✕      │                       │ Oracle          │
└───────────────┴───────────────────────┴─────────────────┘
```

---

# 27. PASS Replay

即使 PASS：

```text
Why PASS?

Required Oracle

✓ Membership DB = ACTIVE
✓ Privilege API = true
✓ UI = active

Evidence completeness: 100%

[查看时间线]
```

用于防止假成功。

---

# 28. BUSINESS_FAIL Replay

显示：

```text
业务失败

Expected:
membership.status = ACTIVE

Actual:
EXPIRED

Oracle Source:
PRD 3.2.1
Contract v3

Related Evidence:
POST /renew → 200
DB after → EXPIRED
```

---

# 29. AUTOMATION_FAIL Replay

例如：

```text
自动化失败，不等于业务失败

原因：
Locator not found

业务 Oracle：
NOT EVALUATED

AI 建议：
按钮文本由“续费”变为“立即续费”

[查看 Healing Proposal]
[批准修复并重跑]
```

---

# 30. Healing UX

显示明确 diff：

```text
Before
getByRole('button', {name: '续费'})

After
getByRole('button', {name: '立即续费'})

Reason
当前 DOM 仅存在“立即续费”

Scope
Action only

Oracle changed?
NO
```

只有 Oracle 不变时才允许“一键批准”。

---

# 31. Failure Triage

AI 分析放在结果之后：

```text
AI 分析（不是最终判定）

高概率问题：
续费接口返回成功，但会员状态未更新。

证据：
API 200
DB EXPIRED
UI EXPIRED

建议开发检查：
1. 事务提交
2. membership update
3. async event consumer
```

测试工程师可以：

```text
[创建缺陷]
```

---

# 32. Defect Create

自动带：

```text
Scenario
Contract version
Build
Expected
Actual
Replay URL
Evidence refs
Environment
Fixture
```

测试工程师只补：

```text
标题
严重等级
负责人
```

---

# 33. Continuous Acceptance Dashboard

不是代码进度。

```text
Build           P0 GREEN     P1 GREEN    Gate

#15             8/12         17/28       FAIL
#16             10/12        21/28       FAIL
#17             11/12        26/28       FAIL
#18             12/12        28/28       PASS
```

点击任意 Build：

```text
从 #17 → #18
变绿 Scenario: 3
新增失败: 0
仍阻塞: 0
```

---

# 34. “开发修好了吗”的体验

测试工程师不再：

```text
收到开发一句“修好了”
→ 找数据
→ 重新手测
```

而是：

```text
Build #19 被检测
→ 受影响 Scenario 自动执行
→ BUSINESS_FAIL → PASS
→ 测试收到通知
```

---

# 35. Trace 页面

新的 Trace 从：

```text
Requirement → TestCase → Execution
```

升级：

```text
Source
→ Scope
→ Intent
→ Contract
→ Scenario
→ Oracle
→ Adapter
→ Run
→ Assertion
→ Evidence
→ Defect
```

任何节点可点击。

---

# 36. 专业资产页面如何保留

## API Test

仍然允许：

- OpenAPI 浏览；
- 单接口调试；
- Request Builder；
- Schema；
- 手工执行；
- 生成 API Adapter。

额外显示：

```text
Referenced by 18 Scenarios
```

---

## UI Test

仍然允许：

- Browser Script；
- locator；
- trace；
- video；
- standalone run。

额外显示：

```text
Generated from Scenario / Action Plan
```

---

## Dataset

改名：

```text
测试数据
```

包含：

```text
Static Dataset
Data Source
Fixture
Lease
Template
```

---

# 37. 用户权限体验

权限不要让普通 Tester 处理复杂 Policy。

按钮层体现：

```text
生产数据：只读
生产浏览：观察模式
测试环境：允许造数
```

高风险动作：

```text
需要审批
```

并说明原因。

---

# 38. AI 交互原则

## 不推荐

每个页面一个：

```text
Ask AI...
```

让用户自己想 Prompt。

## 推荐

上下文动作：

```text
[分析测试范围]
[发现需求歧义]
[生成 Scenario]
[生成 UI Action Plan]
[分析失败]
[建议修复]
```

Prompt 被产品能力吸收。

---

# 39. AI 建议必须有三个东西

每条建议：

```text
建议
依据
置信度 / 不确定性
```

例如：

```text
建议：
Grace Period 纳入 FULL

依据：
DB 状态存在
API renewable=true
历史缺陷 DEF-31

Confidence:
0.72

[批准] [拒绝] [需要确认]
```

---

# 40. Reviewer Efficiency

Review 页面默认优先展示：

```text
AI confidence 低
P0/P1
Oracle = AI_INFERRED
新出现状态
Contract Diff
```

测试工程师不需要逐条审所有 AI 正确的机械边界 Case。

---

# 41. Frontend Route 设计

```text
/workbench

/missions
/missions/new
/missions/:id/overview
/missions/:id/sources
/missions/:id/scope
/missions/:id/contract
/missions/:id/scenarios
/missions/:id/data
/missions/:id/executions
/missions/:id/replay
/missions/:id/trace

/executions
/executions/:runId
/executions/:runId/replay

/assets/requirements
/assets/scenarios
/assets/apis
/assets/ui
/assets/data
/assets/environments
/assets/knowledge

/defects
/acceptance

/admin/workers
/admin/ai
/admin/policies
/admin/audit
```

旧路由保留 redirect/legacy。

---

# 42. 前端代码结构

```text
src/
├ app/
│  ├ router/
│  └ providers/
│
├ features/
│  ├ missions/
│  ├ sources/
│  ├ scope/
│  ├ contracts/
│  ├ scenarios/
│  ├ data/
│  ├ executions/
│  ├ replay/
│  ├ acceptance/
│  └ assets/
│
├ entities/
│  ├ mission/
│  ├ scenario/
│  ├ oracle/
│  ├ run/
│  └ evidence/
│
├ shared/
│  ├ api/
│  ├ ui/
│  ├ hooks/
│  ├ events/
│  └ utils/
│
└ legacy/
```

---

# 43. Query Key

例：

```text
mission.detail(id)
mission.scope(id)
mission.contract(id)
mission.scenarios(id, filters)
run.detail(runId)
run.timeline(runId)
run.evidence(runId)
```

SSE event 到达后：

```text
invalidate / patch query cache
```

---

# 44. 大列表

Scenario / Evidence / Timeline 必须：

- server-side filter；
- pagination；
- virtual list；
- URL 保存 filter；
- 可复制 share link。

---

# 45. Empty State

新系统会有很多阶段状态。

不要只写：

```text
暂无数据
```

例如 Contract 为空：

```text
尚未生成 Test Contract

需要先：
1. 确认 Scope
2. 解决 P0/P1 Ambiguity

[前往 Scope]
```

---

# 46. Error Recovery UX

如果 AI 分析失败：

```text
Scope analysis failed

已完成：
Source parse ✓

未执行：
Scope generation

[重试 Scope 分析]
```

不要从头创建 Mission。

这是后端 Durable Workflow 在 UX 上的重要体现。

---

# 47. 前端最重要的几个“保护型交互”

## Freeze

显式确认。

## Production

显示环境徽标：

```text
PRODUCTION / READ ONLY
```

## DB Fixture

显示影响实体预览。

## Retry

告诉用户：

```text
是否复用 Fixture
是否重新创建 Browser Context
```

## Contract Change

必须显示影响 Scenario。

---

# 48. 测试工程师 5 条真实使用旅程

## Journey A：需求评审当天

```text
创建 Mission
→ 导 PRD/OpenAPI
→ AI Scope
→ Review
→ 解决 Ambiguity
→ Freeze Contract
→ 场景生成
```

结果：

> 开发前已经知道“做到什么才算正确”。

---

## Journey B：功能测试阶段

```text
Scenario
→ 系统自动准备测试数据
→ Assisted Manual Execution
→ Tester 手工操作
→ 系统后台抓 API/DB/截图
→ Oracle 自动校验
→ Replay
```

价值：

> 就算 UI 自动化尚未生成，功能测试阶段已经享受 Data / Oracle / Evidence 能力。

---

## Journey C：将手工路径转 UI 自动化

```text
Observe Mode
→ Tester 正常操作
→ 系统捕获 DOM/XHR
→ AI 生成 Action Plan
→ Tester Review
→ Regression Adapter
→ 执行
```

---

## Journey D：审查 AI 是否假成功/假失败

```text
点击 PASS/FAIL
→ Replay
→ Oracle
→ Evidence
→ 时间线
→ 确认 / 标记误判
```

该反馈进入质量指标。

---

## Journey E：新 Build 到达

```text
Environment Fingerprint changed
→ Impact Analysis
→ 自动回归
→ Dashboard 更新
→ 测试只处理真正失败
```

---

# 49. 用户无需知道的东西

普通 Tester 默认不需要看到：

```text
Temporal Workflow ID
LangGraph 节点
模型 Prompt
Worker Task Queue
SQL connection string
Object Storage URI
```

这些只在 Advanced / Admin 模式。

---

# 50. 前端最终成功标准

一个测试工程师从需求评审到验收：

> 80% 以上操作应该在一个 Mission 内完成。

测试工程师不应该为了完成一个 Scenario 来回跳：

```text
需求 → Dataset → API → UI → TestPlan → Report → Trace
```

这些旧工作区可以存在，但 Mission 应该把它们以“业务上下文”聚合起来。


---

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
