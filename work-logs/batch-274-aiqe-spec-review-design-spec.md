# Batch 274 — AIQE Spec Review：Design Spec

> **部门**：🎨 Design
> **日期**：2026-11-09
> **关联 PRD**：[batch-274-aiqe-spec-review-prd-summary.md](batch-274-aiqe-spec-review-prd-summary.md)
> **关联 PM**：[batch-274-aiqe-spec-review-pm-plan.md](batch-274-aiqe-spec-review-pm-plan.md)

---

## 1. 评审方法

本批是**对 docs 的评审**，不是前端/后端设计。因此 Design 的"规范"意义是：

- 规格书的**内部一致性**：定义 vs 引用、章节 vs 章节、术语 vs 术语。
- 规格书与**现有仓库事实**的一致性：§18.5 列的接入点 vs 当前 `test-platform-v2/backend/app/models/` 真实清单。
- 规格书与**现有 ADR**的一致性：ADR-0014 / 0015 / 0019 / 0020 的决策不能被静默推翻。
- 规格书与**11 号方案 + 10-07 评估**的一致性：不恢复已删模块。

Design 的"反向回填"原则：若现有代码已实现某能力（如 version_task_run 执行 run），**回填规范**到 13 号，而不是让 13 号强推新表。

## 2. 术语与命名一致性

抽查 §24 ADR 清单 + 附录 B 术语表 + §4 数据模型 + §5 状态机 四处的术语：

| 术语 | §4 用法 | §5 用法 | 附录 B 定义 | 结论 |
|------|--------|---------|------------|------|
| TestRun | `test_runs` 表 | Run 状态机对象 | "TestRun，一次执行实例" | ✅ 一致 |
| NodeRun | `node_runs` 表 | Node 状态机对象 | "Node：DAG 节点；对应 NodeRun" | ✅ 一致 |
| StepAttempt | `step_attempts` 表 | Attempt 状态机 | "Attempt：StepAttempt，一次步骤尝试，永不被覆盖" | ✅ 一致 |
| WorkflowDefinition | `workflow_definitions` 表 | "approved 后 checksum 不变" | "Workflow：WorkflowDefinition，已批准的 DAG" | ✅ 一致 |
| Scenario | `test_scenarios` 表 | - | - | ⚠️ **术语表附录 B 漏列 Scenario**，M-1 建议补 |
| Oracle Layer | §9.4 引入 | - | 附录 B 有 | ✅ |
| Interference | §4.15 `interference_observations` 表 | - | 附录 B 有 | ✅ |
| Triage | §4.16 `triage_cases` 表 | §11.5 流程 | 附录 B 有 | ✅ |
| Platform Binding | §13.1 概念 | - | 附录 B 有 | ✅ |

**发现**：Scenario 这个核心术语在附录 B 遗漏。记为 **M-1**。

## 3. §4 数据模型对账（T2 评审任务输出）

用 `origin/main` 的真实 `app/models/` 清单（43 个文件）与 13 号 §4 的 22 张目标表做对账。

### 3.1 对账表（22 目标表 × 43 现有表）

| 13 号目标表 | 现有同义表 | 重叠度 | 建议策略 | 优先级 |
|------------|----------|:-----:|---------|:-----:|
| `requirement_contracts` | `requirement.py`（有 `Requirement`） | 字段级 | **扩字段**：加 version/checksum/approval；不新建 | P0 |
| `acceptance_criteria` | 无 | 0 | 新建 | P1 |
| `test_scenarios` | `test_case_category.py` 部分 | 低 | 新建（category 保留做分类） | P1 |
| `test_cases` | `test_case.py` + `test_case_version.py` + `test_case_review.py` | **完全重叠** | **扩字段**：加 assertions_json/platform_bindings_json/data_plan_json/source_json；version 走现有 test_case_version | P0 |
| `workflow_definitions` | 无（**新概念**） | 0 | 新建 | P1 |
| `test_runs` | `version_task_run.py` | **高度重叠** | ⚠️ **M-2**：13 号默认新建 `test_runs`，但现有 `version_task_run` 已承接"一次执行实例"；需显式说明"扩 version_task_run 而非新建"或"迁移废旧建新 + 数据转移脚本" | **P0** |
| `node_runs` | `execution_job.py` + `plan_execution_job.py` | **中度重叠** | ⚠️ **M-3**：execution_job 是派发工作单元（§1.3 已说"ExecutionJob 不是测试场景定义"），node_run 是 DAG 节点运行事实。需在 §4.8 显式说明"node_run 关联 execution_job_id 一对一" | P0 |
| `step_attempts` | 无 | 0 | 新建 | P1 |
| `assertion_results` | 无（现有 `test_case.steps_json` 内嵌断言） | 低 | 新建 + 迁移 | P1 |
| `run_events` + `event_outbox` | 无 | 0 | 新建 | P1 |
| `run_artifacts` | `lanhu_evidence.py` + `runner_execution.py` 部分 | 低 | 新建（lanhu_evidence 继续承担蓝湖专项） | P1 |
| `execution_profiles` | `environment.py` 部分 | 中 | **扩字段 or 新表**：profile 是对 env 的用法封装；建议新表但关联 env | P1 |
| `target_environments` | `environment.py` | **完全重叠** | ⚠️ **M-4**：13 号 §4.14 新建 `target_environments` 与现有 `environment` 重复。改为"扩 environment 字段"或"新表并明示 environment 废弃路径" | **P0** |
| `interference_observations` | 无 | 0 | 新建 | P1 |
| `triage_cases` / `triage_hypotheses` | 无 | 0 | 新建 | P1 |
| `defects` | `defect.py` | **已承认扩字段**（§4.17） | **扩字段**：加 `steps_to_reproduce_json/expected/actual/env_snapshot_json/linked_execution_id/triage_case_id/fixed_commit_sha` | ✅ 已对 |
| `regression_requests` | 无 | 0 | 新建 | P1 |
| `agent_executions` | `ai_task.py` + `ai_job.py` + `ai_shadow_run.py` | **中度重叠** | ⚠️ **M-5**：§0 P0-5 要删 `ai_gateway/`，但 `ai_job.py`/`ai_shadow_run.py` 仍在 models 树里。规格需明示这两个 model 是否一并删除；若删除，agent_executions 单独承载审计；若保留，agent_executions 与 ai_task 字段必须去重 | **P0** |
| `learning_candidates` + `bug_patterns` | `knowledge.py` + `.claude/skills/bug-pattern-curator/` | 中 | **分离**：knowledge 继续保 项目知识；13 号这两张表承接 Learning + BugPattern 的结构化部分 | P1 |
| `noise_suppression_rules` | 无 | 0 | 新建 | P1 |
| `project_adapters` | 无（当前走 `docs/standards/project-adapters/*.yaml` 外部文件） | 0 | **新建"轻量表 + 引用 yaml"**：避免双事实源，表只存 adapter_yaml_ref | P1 |
| `node_capability_manifests` | 无（当前走 `scripts/node/capabilities.yaml`） | 0 | **新建"轻量表"**：同上 | P1 |

### 3.2 发现汇总

| 问题 | 条目 | 严重度 |
|------|------|:-----:|
| 现有 `version_task_run.py` 未在规格里对账 → 可能重复建 | **M-2** | P0 |
| 现有 `execution_job.py / plan_execution_job.py` 与 node_runs 关系不清 | **M-3** | P0 |
| `target_environments` 与 `environment.py` 完全重复 | **M-4** | P0 |
| `ai_job / ai_shadow_run` 的删除/保留未定，影响 agent_executions 设计 | **M-5** | P0 |
| 附录 B 术语表漏 Scenario | **M-1** | P2 |

### 3.3 project_id 隔离审计

抽查 22 张表的 project_id 字段：

- ✅ 带 project_id：`requirement_contracts / test_scenarios / test_runs / defects / execution_profiles / target_environments / project_adapters` 7 张；
- ✅ 明示全局：`agent_executions`（§4.19 说明 nullable）；
- ⚠️ **未明示**：`run_events / run_artifacts / interference_observations / triage_cases / noise_suppression_rules / node_capability_manifests` → 这些是 Run 子表继承 run.project_id 还是独立带 project_id？建议显式写明。记为 **M-6**。

## 4. §5 状态机完备性审计（T3）

### 4.1 Run 状态转换邻接表

```
DRAFT      → VALIDATING
VALIDATING → QUEUED | BLOCKED | ERROR
QUEUED     → RUNNING | CANCELED
RUNNING    → WAITING_HUMAN | TRIAGING | COMPLETED | BLOCKED | CANCELED | ERROR
WAITING_HUMAN → RUNNING | CANCELED
TRIAGING   → RUNNING | COMPLETED | CANCELED
COMPLETED  → (terminal)
BLOCKED    → (terminal)
CANCELED   → (terminal)
ERROR      → (terminal)
```

**发现**：
- ✅ 合法转换完整；
- ✅ `COMPLETED` 的入边 ∈ {RUNNING, TRIAGING}；WAITING_HUMAN 必须先回 RUNNING 才能 COMPLETED → 符合 §5.1 "status=COMPLETED 必须有 outcome" 规则；
- ✅ `BLOCKED / CANCELED / ERROR` 无 outcome；
- ⚠️ **遗漏边**：`DRAFT → CANCELED` 是否允许？用户创建 Run 后在 VALIDATING 之前取消。未明示。记为 **M-7**。
- ⚠️ **遗漏边**：`WAITING_HUMAN → ERROR`（人工审批超时）未明示。记为 **M-8**。

### 4.2 Node 状态

10 状态：`PENDING / READY / QUEUED / RUNNING / WAITING / PASSED / FAILED / BLOCKED / SKIPPED / CANCELED / ERROR`。

等等——**数一下是 11 个，不是 10 个**。§5.2 文字说 10 状态但列了 11 个。记为 **M-9**（技术性 typo）。

- ✅ `SKIPPED` 入边：§5.2 明示"上游失败且策略要求跳过"；
- ✅ `WAITING` 与 `RUNNING` 的区别：WAITING 是"等待资源锁/依赖/审批"，RUNNING 是"真正在执行"——这块 §4.8 字段表里应补 `waiting_reason` 字段。记为 **M-10**。

### 4.3 Attempt 状态

7 状态：`QUEUED / RUNNING / PASSED / FAILED / TIMED_OUT / CANCELED / ERROR`。

- ✅ TIMED_OUT vs ERROR 边界：TIMED_OUT 是超过 `timeout_ms`；ERROR 是基础设施错误（Worker 崩溃 / 网络中断）；
- ✅ "首次失败在 UI 时间线必须可见" 规则清晰。

### 4.4 Defect 状态

6 状态：`open / confirmed / fixing / pending_review / closed / rejected`。

- ✅ 与现有 `defect.py` 兼容，§4.17 已标明"现有基础上扩展"；
- ⚠️ `pending_review → fixing`（回归失败回打）这条边清晰；但 `closed → ?` 终态是否允许 reopen？规格未说明。记为 **M-11**。

## 5. §6 + ADR-AIQE-008 WorkflowDefinition 护栏审计（T4）

### 5.1 WorkflowDefinition vs AITDE 四层建模对比

| 层 | AITDE（已删） | 13 号 | 评估 |
|----|-------------|------|------|
| L0 需求 | `Scope` | `requirement_contracts` | ✅ 用现有 requirement 扩字段，不新表 |
| L1 契约 | `Contract`（冻结 + checksum） | `requirement_contracts`（冻结 + checksum） | ⚠️ 概念同构，命名同构 |
| L2 场景 | `Scenario` | `test_scenarios` | ⚠️ 概念同构 |
| L3 预期 | `Oracle` + `OracleBinding` | `assertion_results`（含 `oracle_layer` 字段） | ✅ **区别**：13 号不建 Oracle 独立表，只做字段标签 |
| L4 执行计划 | `ScenarioExecutionWorkflow`（Temporal） | `workflow_definitions`（DAG） | ⚠️ 概念同构，但**不用 Temporal** |

### 5.2 护栏核查

| 护栏 | 规格位置 | 是否足够 |
|------|---------|:-------:|
| 禁止平行建模实体 | §2 不做清单 #1 | ✅ 明示 |
| 禁止 Temporal / 自研 Durable Runtime | §2 不做清单 #2 | ✅ 明示 |
| 禁止 planner stub + executor echo | §2 不做清单 #3 | ✅ 明示 |
| 禁止 AI 临场改已批准 Workflow | §2 不做清单 #11 | ✅ 明示 |
| WorkflowDefinition 必须绑 scenario_id + contract_version | §24 ADR-AIQE-008 | ✅ 明示 |
| 已批准 Workflow checksum 固定 | §4.6 字段级规则 + §6.2 规则 7 | ✅ 明示 |

### 5.3 剩余风险

- ⚠️ ADR-AIQE-008 的护栏是"不建平行建模实体"，但 13 号自己建的 `workflow_definitions` 本质就是"冻结 DAG + checksum + approval" ——与 AITDE 的 `ScenarioExecutionWorkflow` 结构相似度仍 ≥ 70%。**真正的区别只有 "不用 Temporal"**。
- 建议 **M-12**：§24 ADR-AIQE-008 需补一条判据——"任何 PR 新建带 `checksum + approval_status` 的实体，必须显式说明它不是 AITDE Scenario 的翻版"。即加一道**PR 模板强制问答**。

## 6. §11 噪音治理项目无关性审计（T5）

### 6.1 11 类对多项目适用性

| 分类 | 体育 | 电商 | SaaS | IoT | 通用性评估 |
|------|:---:|:---:|:---:|:---:|-----------|
| ENVIRONMENT | ✅ | ✅ | ✅ | ✅ | 100% |
| TEST_DATA | ✅ | ✅ | ✅ | ✅ | 100% |
| CONCURRENCY | ✅ | ✅ | ✅ | ✅ | 100% |
| THIRD_PARTY | ✅ | ✅ | ✅ | ✅ | 100% |
| NETWORK | ✅ | ✅ | ✅ | ✅ | 100% |
| TIME | ✅ | ✅ | ✅ | ✅ | 100% |
| CROSS_FEATURE | ✅ | ✅ | ✅ | ✅ | 100% |
| UI_OVERLAY | ✅ | ✅ | ⚠️ | ❌ | **IoT 无 UI 时不适用**；SaaS 部分（有管理台时适用） |
| AUTOMATION | ✅ | ✅ | ✅ | ✅ | 100% |
| REQUIREMENT_AMBIGUITY | ✅ | ✅ | ✅ | ✅ | 100% |
| UNKNOWN | ✅ | ✅ | ✅ | ✅ | 100% |

**发现**：UI_OVERLAY 对无 UI 的 IoT 项目不适用；建议改为 "UI_OVERLAY（仅对有 UI 端的测试适用）" 并在适配器 capability 层声明是否启用此分类。记为 **M-13**。

### 6.2 6 对照实验 vs 非体育项目

| 实验 | 电商退款 | SaaS 租户隔离 | IoT 设备影子 |
|------|:--------:|:-----------:|:-----------:|
| E1 同 Build 重跑 | ✅ | ✅ | ✅ |
| E2 数据隔离重跑 | ✅ | ⚠️ 租户隔离本身就是数据隔离 → 可用但语义重叠 | ✅ |
| E3 外部依赖回放 | ✅ 退款走第三方支付 | ✅ 走 SSO/License server | ✅ 走云平台 API |
| E4 跨功能 Profile 对照 | ✅ 优惠券 vs 退款 | ✅ 不同模块 feature flag | ✅ 不同固件版本 |
| E5 Worker 对照 | ✅ | ✅ | ⚠️ IoT 的 Worker 可能是物理网关，更换成本高 |
| E6 网络 Profile 对照 | ✅ | ✅ | ✅ 弱网对 IoT 尤其重要 |

**发现**：E5 在 IoT 场景下 Worker 更换成本很高（物理网关），应在规格里标注"IoT 场景 E5 需走设备池借还机制"。记为 **M-14**。

### 6.3 噪音规则库 90 天强制复核

§11.9 规定 `effective_until` ≤ 90 天。对高频抖动（广告系统/第三方）合理；对**长期已知外部依赖**（如 Oracle Cloud 的 DNS 失败窗口）可能过短。建议补一条：规则可被 Owner 显式续期（需重新审批），而非一刀切 90 天过期。记为 **M-15**。

## 7. §14 OSS 准入审计（T6）

### 7.1 TestZeus AGPL-3.0 处理

13 号 §14 处理方案："仅在完全隔离的独立服务中使用，不深度合并"。

**验证**：
- CamelTv 本身是否闭源商业分发？用户是面向内部/合作伙伴的测试工具平台，**不对外销售**→ AGPL 的网络服务义务**可能不触发**；
- 但一旦未来有 SaaS 化计划（13 号 §19 预留 TA-040 多租户）→ AGPL 义务会触发；
- 建议 **M-16**：§14 加一条"**采用 TestZeus 前必须经法务书面评估**"硬门禁，不仅是"PoC 后决定"。

### 7.2 版本锁事实证据

| 组件 | 13 号声明 | 事实核查 | 评估 |
|------|---------|---------|------|
| Playwright 1.56 Agents | "从 1.56 起支持" | ✅ Microsoft 2025-10 发布 Playwright Agents（Planner/Generator/Healer） | ✅ |
| Midscene.js iOS/Android/HarmonyOS/桌面 | "2026-04 起支持" | ✅ 字节 Web Infra 2026-04 核心更新 | ✅ |
| Appium MCP 官方 | "appium/appium-mcp" | ✅ 官方维护 | ✅ |
| Keploy eBPF | 承认需权限审计 | ✅ Keploy 依赖 eBPF 做协议捕获 | ✅ |
| ReportPortal 26.0.3 Agentic | §14.1 声明 | ✅ 26.0.3 版本开始接收 Agentic Test Results | ✅ |

**结论**：版本锁依据合理。

### 7.3 低采用度警戒（WarrDoge/Test-Agent 1⭐ 0 fork）

13 号 §14.1 已标明"提高准入门槛"。✅

### 7.4 剩余建议

- **M-17**：附录 A 版本锁表加一列"**预期年度升级窗口**"（如 Playwright 每季度主版本，年度大升级 1 次）。便于规划升级演练。
- **M-18**：PoC 矩阵 §14.4 加一列"**失败回退方案**"，避免 PoC 不通过时堵塞 V1 交付。

## 8. §19 工期估算审计（T7）

### 8.1 Phase 工时核算

| Phase | 周数 | TA 数量 | 粗估人日 | 并行度 | 人数需求 |
|-------|:---:|:------:|:-------:|:-----:|:-------:|
| Phase 0 | 2 | 6 | 18 pd | 3 条 | 2-3 人 |
| Phase 1 | 2 | 4 | 32 pd | 4 条（相对独立） | **4 人** |
| Phase 2 | 3 | 7 | 60 pd | 5 条（Driver 可并行） | 5 人 |
| Phase 3 | 4 | 7 | 80 pd | 6 条（PoC + Agent 并行） | **6 人** |
| Phase 4 | 3 | 6 | 50 pd | 4 条 | 5 人 |
| Phase 5 | 4 | 6 | 50 pd | 4 条 | 4 人 |
| Phase 6 | 3 | 4 | 30 pd | 2 条 | 2-3 人 |

**粗算**：Phase 2-3 峰值需要 **5-6 人**，与规格假设一致。✅

### 8.2 2-3 人团队放大倍数

若实际只有 2-3 人：
- Phase 0：× 1.5（因为 OSS 准入+ 代码审计是串行做法时间不省）；
- Phase 1-3：× 2.0 ~ 2.5（并行度不足）；
- Phase 4-6：× 2.0；
- **V1 周数预估：16 × 2.0 = 32 周（8 个月）**。

建议 **M-19**：§23 里程碑表加一行 "**2-3 人团队放大线**"，避免小团队承诺 20 周。

### 8.3 可推迟到 V1.1/V1.2 的 TA

抽查：
- TA-016 Playwright MCP PoC → 可延 V1.1（MVP 用确定性脚本即可）；
- TA-017 TesterArmy e2e PoC → 可延（同上）；
- TA-018 Keploy PoC → 可延（上下游 mock 可手写）；
- TA-021 A3 Workflow Planner Agent → ⚠️ **不能延**，否则 §6 WorkflowDefinition 没人生成；
- TA-029 A5 Change Impact → 可延 V1.1（人工手选回归用例可接受）；
- TA-030 A6 Learning Curator → 可延 V1.2；
- TA-039 ~ TA-045 → 已明示 V1.1/V1.2/专项。

建议 **M-20**：§19 加一个"MVP 核心 vs V1 扩展 vs V1.1+"的**优先级三档标注**，便于资源不足时裁。

## 9. 本 Design spec 的 M 条目汇总

| M-ID | 位置 | 内容 | 严重度 |
|------|------|------|:-----:|
| M-1 | 附录 B | 术语表漏 Scenario | P2 |
| M-2 | §4.7 | `test_runs` vs `version_task_run.py` 未对账 | **P0** |
| M-3 | §4.8 | `node_runs` 与 `execution_job.py/plan_execution_job.py` 关系不清 | **P0** |
| M-4 | §4.14 | `target_environments` 与 `environment.py` 完全重复 | **P0** |
| M-5 | §4.19 + §0 P0-5 | `ai_job / ai_shadow_run` 的删除/保留未定 | **P0** |
| M-6 | §4 各 Run 子表 | project_id 隔离未明示 | P1 |
| M-7 | §5.1 | `DRAFT → CANCELED` 边缺 | P2 |
| M-8 | §5.1 | `WAITING_HUMAN → ERROR` 边缺 | P2 |
| M-9 | §5.2 | Node 文字说 10 状态但列了 11 个 | P2 |
| M-10 | §4.8 | NodeRun 的 WAITING 需 `waiting_reason` 字段 | P2 |
| M-11 | §4.17 | Defect `closed` 终态是否允许 reopen 未说 | P2 |
| M-12 | §24 ADR-AIQE-008 | 需加 PR 模板强制问答"不是 AITDE Scenario 翻版" | P1 |
| M-13 | §11.2 | UI_OVERLAY 对无 UI 项目不适用，需 adapter capability 开关 | P1 |
| M-14 | §11.4 E5 | IoT 场景 Worker 更换成本高，需设备池借还机制 | P2 |
| M-15 | §11.9 | 噪音规则 90 天强制过期过严，需显式续期机制 | P1 |
| M-16 | §14 | TestZeus AGPL 需加"法务书面评估"硬门禁 | **P0** |
| M-17 | 附录 A | 版本锁表加"预期年度升级窗口"列 | P2 |
| M-18 | §14.4 | PoC 矩阵加"失败回退方案"列 | P1 |
| M-19 | §23 | 加 2-3 人团队放大线 | P1 |
| M-20 | §19 | 加 MVP / V1 / V1.1+ 优先级三档标注 | P1 |

**P0 条目 5 个（M-2, M-3, M-4, M-5, M-16）**，必须进入 Leader verdict 的"修改后合入"清单。

## 10. Design 结论

- 规格书**结构完整、术语基本一致、与 AITDE 教训对账清晰**；
- **真实阻塞问题** 集中在 §4 数据模型与现有 `app/models/` 的重复（M-2/3/4/5）——这是"规格看起来漂亮但落地时会和现有代码撞车"的典型风险；
- **法务风险** M-16 必须立即处理，否则 TestZeus PoC 启动时才踩到 AGPL 坑；
- 其余 M-1 ~ M-15 / M-17 ~ M-20 多为"可读性/边缘场景/工程细节"，可在"修改后合入"批次里一并处理。
