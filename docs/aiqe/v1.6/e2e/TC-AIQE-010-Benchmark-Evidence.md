# TC-AIQE-010 证据口径说明：产品级与 local_service_test 分离

**文档类型：** 证据口径说明（不是产品级 PASS 记录）
**基线：** `origin/main` = `2d2f508d5d1fd452972e7af49d9b4f3bde2e7b01`
**整改任务：** FIX-006（Benchmark / Learning Candidate 接入正式业务链）、FIX-005（A0–A6 正式 AgentTask 生命周期）
**Owner：** qa-automation
**状态：** 产品级 `NOT_PROVEN`（未取得产品级证据）；本地 Service 测试 `PASS`；平台级 AgentTask 链 `PASS`（TC-PLATFORM-009）

---

## 1. 为什么需要本文件

V1.6.1 的 TC-AIQE-010 证据存在两个口径问题：

1. `scripts/aiqe/per_tc/futurewayu_learning_benchmark.py` 把 `DATABASE_URL` 强制指向
   `work-logs/evidence/aiqe-v16/local-test/platform.db`，直接调用 `benchmark_service` /
   `learning_service`，属于**本地 Service 测试**，却以产品级 PASS 记入追踪矩阵；
2. 数据集样本数写成 43 条、结论文字写成 37 条（26 + 11），但没有 6 条样本的剔除记录。

本文件的作用是**把两类证据分开命名、分开存放、分开统计**，并明确本地 Service 测试
`PASS` 不得折算为 TC-AIQE-010 的产品级通过。

---

## 2. 三层证据与可用边界

| 层级 | 证据载体 | 证明什么 | 能否支撑产品级 PASS |
|---|---|---|---|
| 本地 Service 测试 | `work-logs/evidence/aiqe-v162/local-service-test/TC-AIQE-010/learning-benchmark.local-service-test.json`（脚本 `scripts/aiqe/per_tc/futurewayu_learning_benchmark.py` 生成，`evidence_kind=local_service_test`） | Dataset 冻结、逐样本指标复算、gate 判定、双人审批与发布的服务层行为 | 不能（脚本未经过正式 API/Worker） |
| 平台级 AgentTask 链 | `tests/e2e/aiqe/test_v16_017_platform_chain.py::test_tc_010_agent_task_platform_chain`（TC-PLATFORM-009）、`tests/e2e/aiqe/test_v16_018_agent_task_api_e2e.py` | AgentTask API→审批→入队→Worker claim→A0–A6→工具审计（含 A5 `read_git_diff`） | 不能（平台链路命名空间，非产品业务链） |
| 产品级 | **尚无**已归档机器产物 | 正式 API + 真实项目数据 + 真实模型 + 双人审批 | 当前不成立；产品级状态为 `NOT_PROVEN` |

产品级结论固定输出 `product_status = BLOCKED`：
`本地 Service 测试 PASS 不能折算为 TC-AIQE-010 产品级 PASS`。

### 2.1 历史产物处理

`docs/aiqe/v1.6/evidence/product/TC-AIQE-010/learning-benchmark.json` 是旧脚本生成的
**本地 Service 口径**产物（`DATABASE_URL` 指向 `local-test/platform.db`，非正式 API），
不得继续作为产品级证据引用。追踪矩阵
（`docs/aiqe/v1.6/traceability/requirements.yaml`）中 TC-AIQE-010 的
`e2e.product.status` 与 `runtime_evidence.note` 需要由 traceability owner（FIX-003 负责人）
按本文件口径复核更正；该文件不在 FIX-005/FIX-006 的可改范围内。

---

## 3. 样本口径（69 / 42 / 26 / 16 的构成）

`local_service_test` 对权威用例/问题表做显式口径拆分，并逐条记录剔除原因：

| 项 | 数值 | 说明 |
|---|---:|---|
| 原始行数（`total_raw_rows`） | 69 | `03-待复测（26条）` + `02-问题登记表` 的全部数据行（含表内表头行） |
| 有效样本（`effective_samples`） | 42 | 去重后可用于 Benchmark 的样本 |
| 重复剔除（`duplicates_removed`） | 26 | 同一 `WWY-*` 编号同时出现在两张表；逐条记录 `sample_id` / `first_source` / `duplicate_source` |
| 非法剔除（`invalid_rows_removed`） | 1 | 表内表头「问题编号」行，`reason=INVALID_SAMPLE_ID` |
| 口径校验（`accounting_ok`） | true | `69 = 42 + 26 + 1` |

历史文本中的「43 条」「37（26 + 11）条」均**不再作为口径依据**：旧脚本用字典去重后未
记录被剔除的样本，导致数据集行数与结论文字不一致。服务层同时强制
`Dataset.sample_count == 实际样本行数`、`total = valid + excluded`（剔除原因逐条落库），
Run 记录该口径快照。

---

## 4. 指标与数据集绑定（服务端唯一计算）

- `benchmark_service.metrics_of()` **从逐样本 prediction/ground truth 复算**
  precision/recall/f1 与 TP/FP/FN，以及样本级 2×2 混淆矩阵
  （`sample_true_positives` / `sample_false_positives` /
  `sample_false_negatives` / `sample_true_negatives`）；
- 存储的 `metrics_json` 只用于**对账**：人工改 summary（而逐样本预测未变）会被
  `METRICS_TAMPERED` 拒绝；结果状态被改写会被 `RESULT_STATUS_MISMATCH` 拒绝；
- 每个 Run 记录 `dataset_snapshot`（dataset_id / content_hash / 当前样本 hash / 样本数）。
  数据集样本或 hash 在 Run 之后变化 → `DATASET_BINDING_STALE`，旧 Run 不可冒充新 Dataset；
  没有快照的历史 Run → `DATASET_SNAPSHOT_MISSING`，不得作为当前数据集证据；
- 样本导入拒绝重复 `sample_id`（`DUPLICATE_SAMPLE_ID`）与非法标签（`INVALID_LABEL`，
  词表 `[A-Z][A-Z0-9_]{0,63}`）。

本文件所附 `local_service_test` 产物中的指标来自**确定性 stub 预测器**
（`controlled_predictor=true`，故意翻转 2 条样本），只证明服务端复算与 gate 链路，
**不是**真实模型质量结论。

---

## 5. 审批 / 发布身份（双人审批）

- 审批与发布都必须提供**真实用户 id**（拒绝 `"QA-Lead"` 这类角色字符串、拒绝布尔/非正数）；
- 默认要求 `Owner(created_by) != Approver(approved_by)`（按 user id 比较），
  自动化服务身份（`automation/agent/auto/service/system`）永远不得自审；
- 单操作员本地部署可用 `AIQE_LEARNING_REQUIRE_TWO_PERSON_APPROVAL=false` 显式豁免
  （属于有记录的降级，不得用于产品级证据）；
- 审批/发布事件写入 `LearningCandidate.benchmark_json["approval"]`
  （`approved_by_user_id` / `owner_user_id` / `published_by_user_id` / 时间戳），可回查；
- 未审批（`approved_by/approved_at` 缺失）不得发布；重复发布、状态错误（draft/rejected/
  revoked）、候选已评估后数据集 hash 或规则 hash 变化一律拒绝。

### 5.1 已知回归（跨文件）

`tests/test_aiqe_learning_api.py::test_evaluate_and_approve_and_activate` 用**同一个用户 id**
创建并审批候选（历史单操作员语义），在双人审批默认开启后按预期返回 400。
该文件不在本任务的可改范围，需由其 owner 把 fixture 改为「创建用户 1 / 审批用户 2」
（或在该进程显式设置 `AIQE_LEARNING_REQUIRE_TWO_PERSON_APPROVAL=false` 表示接受降级）。

---

## 6. A0–A6 能力矩阵（本批可验证范围）

| Agent | 读工具（已真实可用） | 写能力 | 本批判定 |
|---|---|---|---|
| A0 Orchestrator | plan / 子 Agent 调度 | 无 | VERIFIED（平台链路） |
| A1 Requirement | `read_requirements` / `read_project_context` | 无 | VERIFIED（平台链路） |
| A2 Test Design | `read_requirements` / `read_openapi` | `create_draft` = `UNAVAILABLE` | PARTIAL（写能力未开放） |
| A3 Workflow Planner | `read_openapi` | `create_draft` = `UNAVAILABLE` | PARTIAL（只产出待审批计划） |
| A4 Failure Triage | `read_defects` / `read_run_evidence` | 无（仅草稿+人工确认） | VERIFIED（平台链路） |
| A5 Change Impact | `read_git_diff` / `create_regression_plan`（无副作用） | 无 | VERIFIED（需真实 base/head SHA） |
| A6 Learning Curator | `read_defects` / `read_benchmark_dataset` | `create_learning_candidate` = `UNAVAILABLE` | PARTIAL（候选发布只经人工 API/Service） |

**A5 硬约束：** 未提供真实 `base_sha`/`head_sha`、或 `ToolExecutionAudit` 中没有
`ALLOW` 的 `read_git_diff`（含 SHA 不匹配）时，AgentTask 必须 `BLOCKED`
（`error_code=A5_NOT_PROVEN`），A5 的 `AgentExecution` 记为 `BLOCKED` 并带
`A5_NOT_PROVEN` 警告——**不得输出“无影响 PASS”**。

默认计划模板包含 `a5_impact`，因此**包含 A5 的任务必须携带真实 SHA**（或在不需要变更
影响分析时显式裁剪 `include`，不传 `a5_impact`）。这是有意的 fail-closed：不得为“跑通”
而传入伪造/占位 SHA。

---

## 7. 复现命令

```powershell
# 1) 本地 Service 测试（不得作为产品级证据；产品级固定 BLOCKED）
cd <repo>
python scripts/aiqe/per_tc/futurewayu_learning_benchmark.py
#   -> evidence_kind=local_service_test, product_status=BLOCKED, 退出码 2
#   产物：work-logs/evidence/aiqe-v162/local-service-test/TC-AIQE-010/learning-benchmark.local-service-test.json

# 2) 服务层指标/口径/身份测试
cd test-platform-v2/backend
$env:PYTHONIOENCODING="utf-8"
python -m pytest tests/test_aiqe_v162_agent_benchmark.py tests/test_aiqe_v16_010_benchmark_gate.py -q -p no:cacheprovider

# 3) 平台级 AgentTask 链（TC-PLATFORM-009）
python -m pytest tests/e2e/aiqe/test_v16_017_platform_chain.py::test_tc_010_agent_task_platform_chain `
  tests/e2e/aiqe/test_v16_018_agent_task_api_e2e.py -q -p no:cacheprovider
```

---

## 8. 未完成项（BLOCKED / PARTIAL 及解除条件）

| 项 | 状态 | 原因 | Owner | 解除条件 |
|---|---|---|---|---|
| TC-AIQE-010 产品级 Benchmark/审批/发布 | BLOCKED | 产品级入口需要隔离 Test 项目 + 已配置 AI Provider + 真实历史缺陷数据 + 两个不同真实用户；本批只能在本地 Service 与平台级验证 | qa-automation | 在 Test 项目配置 Provider 后，经 `POST /api/v1/aiqe/benchmarks/datasets|freeze|runs`、`POST /api/v1/aiqe/learning/candidates|evaluate|approve|activate` 执行并归档机器产物到 `docs/aiqe/v1.6/evidence/product/TC-AIQE-010/` |
| 真实模型质量结论 | BLOCKED | 无可用真实 Provider/配额；stub 结果不得作为模型质量结论 | ai-platform | 使用项目批准的真实模型配置，单独记录模型版本/参数/provider 与响应 hash |
| A2/A3/A6 写工具 | PARTIAL | `create_draft` / `create_learning_candidate` 仍是 `UNAVAILABLE`（无真实实现），Agent 只能产出草稿/计划，业务写入必须人工经 API 完成 | agent-owner | 实现写工具时必读：审批 token 不能是 Agent 可读的任务 id；需独立审批 token + 双人审批 |
| 追踪矩阵产品级状态 | NOT_PROVEN | `requirements.yaml` 中 TC-AIQE-010 仍引用旧的本地 Service 产物作为产品级证据 | FIX-003 owner | 按本文件口径把 `e2e.product.status` 改为 `NOT_PROVEN`/`BLOCKED` 并更新 `runtime_evidence.note` |
| `tests/test_aiqe_learning_api.py` 单用户审批 fixture | PARTIAL | 与双人审批默认策略冲突（同一 user id 创建+审批） | test owner | 改为两个不同 user id（见 §5.1） |

---

## 9. 不得据此宣称的结论

- 不得宣称 TC-AIQE-010 产品级通过，或把 `local_service_test` 产物计入产品级 PASS 计数；
- 不得把 `controlled_predictor`/`controlled_llm_test` 的指标当作模型质量或线上效果；
- 不得在缺少真实 SHA 时用 A5 输出“无影响”结论；
- 不得把 A2/A3/A6 的 `UNAVAILABLE` 写工具描述为“已完整可用”。
