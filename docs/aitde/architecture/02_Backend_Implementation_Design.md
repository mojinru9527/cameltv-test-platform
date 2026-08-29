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
