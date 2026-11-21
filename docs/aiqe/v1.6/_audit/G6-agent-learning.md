# G6 独立审计报告 — Benchmark Gate / Project Scope / A4 Evidence / A0 Plan / A5 Impact / Tool Registry

| 项目 | 内容 |
|---|---|
| 审计 Issue | **V16-010**（Benchmark Gate 强制审批和发布）、**V16-011**（全资源 Project Scope）、**V16-012**（A4 Evidence Resolver 强制校验）、**V16-013**（A0 Draft→审批→run_plan 执行）、**V16-014**（A5 Change Impact 纳入 Plan/Scope）、**V16-019**（Tool Registry 真实绑定/权限/审计） |
| 审计角色 | 独立代码审计员（只读；未修改任何业务文件；唯一写入是本报告） |
| 审计对象 | `F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6`（分支 `release/aiqe-v1-6`，后端根 `test-platform-v2/backend`） |
| 基线 | `HEAD = 09140401f`（`feat(aiqe-v16): V16-001 删除 HTTP/DB fail-open…`） |
| 规格 | `C:\Users\26029\Downloads\CamelTv_AIQE_V1.6_修复与生产化开发实施计划.md`（下称“规格”） |
| 审计时间 | 2026-11-19 19:55–21:10 (+08:00) |
| 方法 | 只读走查 `test-platform-v2/backend/app/aiqe/**`、`app/api/v1/**`、`tests/**`、`scripts/qa/**`、`work-logs/**`；**未执行 pytest**（只读审计，避免在工作树生成 DB/缓存），全部结论均给出可复核行号与复核命令（各节末） |

---

## 0. 结论总表

| Issue | 状态 | 一句话结论 |
|---|---|---|
| **V16-010** | **PARTIAL（存在 gate fail-open）** | 指标确由后端 `BenchmarkRun` 计算、API 已拒绝自报指标（这两点 IMPLEMENTED）；但**唯一批准条件只实现了“误报率 ≤ 20%”**：`evaluate_candidate()` 无条件把候选置 `benchmarked`，`approve_candidate()` 不校验 `result_status==PASS_GATE`、`gate_eligible`、样本数 ≥30、Precision/Recall/F1、baseline、dataset checksum、版本一致性；`approved_by/approved_at/benchmark_run_id/dataset_checksum/baseline_version/gate_policy_version/approval_reason` 全部缺失；publish/revoke/shadow/rollback 不存在。**一个 100% UNKNOWN（precision=recall=f1=0、`BELOW_THRESHOLD`）的 Run 也能被批准并激活**（`false_positive_rate=0`）。 |
| **V16-011** | **PARTIAL** | 只有 `LearningCandidate` 的 create/get/list 与 `run_llm_benchmark` 做了 project 校验；`get_dataset/list_samples/add_sample/freeze_dataset/get_run/metrics_of` **全部无 project_id**，对应 API `add_sample/freeze/get_run` 也不传 project；`BugPattern` 表**根本没有 project_id**（全局唯一 `pattern_key`）。规格 7 条实施要求里只有“建议”被部分满足，验收要求的跨项目 GET/POST/Freeze/Evaluate/Publish 全拒绝不成立。 |
| **V16-012** | **PARTIAL（核心不变量 fail-open）** | `evidence_service.resolve_evidence_refs()` 实现质量不错（存在性 + 跨项目 + 跨 Run），但**完全没有接入 Agent 链路**：`BaseAgent.validate()` 无 context/resolver 参数，`BaseAgentAdapter.execute()` 调 `agent.run(request)` 时不传 resolver，`FailureTriageAgent.validate(..., evidence_resolver=None)` 默认 None 且 `if evidence_resolver is not None` 才校验、返回值被丢弃、空结果不拒绝；**A4 在生产代码中零调用点**（既无 Agent Adapter 入口，也无 API/Job 入口）。规格明令禁止的“resolver 缺失降级通过”正是当前默认行为。 |
| **V16-013** | **PARTIAL（闭环 MISSING）** | 有 `AgentExecution` 可追溯落库与 `run_plan()`（DAG/依赖取消/幂等/WAITING_HUMAN/超时后置判定）；但**没有持久化 `AgentTask`/`AgentStepExecution`**，`POST /agent-tasks` 只返回内存 plan（不落库、无 plan hash），**没有 `/approve`、没有 `/run`、无 409/403 审批门禁**，`run_plan()` **零生产调用点**（全仓仅 tests 调用），A1–A6 从未真实执行；ToolRegistry 在 `run_plan` 中默认空实现。 |
| **V16-014** | **PARTIAL** | `impact_service` 有真实 git diff + Python AST/TS 导出/route/migration/component 解析（AUD-017 基础，IMPLEMENTED 的部分）；但 **A5 Agent 本身仍是“文件名关键词 → suite 名”**（`AREA_RULES`），无 base/head SHA、无 diff hash、无 OpenAPI/migration 证据、无 `DIRECT/TRANSITIVE/CONTRACT/DATA/UI/RISK` 分类；且**经 Adapter 调用时 `_expected` 为空导致“不得漏选强制 suite/影响域”校验整体失效**；`impact_service` 从未进入 `run_plan`/回归 Scope，`persist_edges` 在生产代码中零调用，`diff_digest` 从不落库。 |
| **V16-019** | **MISSING（仅保留拒绝路径）** | `ToolRegistry` 只有 `allowlist + tools dict` 两个字段：**没有任何注册元数据**（version/input_schema/output_schema/permission_scope/project_scope/side_effect_level/idempotent/timeout/rate_limit/requires_human_approval/secret_access_policy）、无启动期实现校验、无 `UNAVAILABLE` 状态、无按工具的参数 schema 校验、无 ToolExecution 模型/事件/审计；`build_tool_registry()` 默认 `{}`（审计来源所述“默认实现字典为空”**至今成立**）；Agent 自身从不调用工具（`tool_calls` 恒空）。 |

**状态定义**：按规格 §0.2.4 —— `IMPLEMENTED`（代码落地≠验收通过）/`PARTIAL`/`MISSING`。本报告不使用 `VERIFIED`/`ACCEPTED`（无 Runtime E2E 证据，且本组 6 个 Issue 均无任何真实入口纵向切片证据）。

---

## 0.1 规格章节定位

| Issue | 规格位置 | 关闭条件（总表） |
|---|---|---|
| V16-010 | 正文 §V16-010（规格 L553–L589）+ 总表 L182 + Gate D L1162 | 非 PASS_GATE 候选不可批准/发布 |
| V16-011 | 正文 §V16-011（L591–L607）+ 总表 L183 + 角色分工 L1101 | 跨项目读写全拒绝 |
| V16-012 | 正文 §V16-012（L609–L638）+ 总表 L184 + Gate D L1160 + §0 原则 L24 | 无效/跨 Run/跨 Project evidence 拒绝 |
| V16-013 | 正文 §V16-013（L640–L667）+ 总表 L185 + Gate D L1158/L1163 + §9.6 L1077–L1081 | 审批后真实执行 A1–A6 并持久化状态 |
| V16-014 | 正文 §V16-014（L669–L684）+ 总表 L186 + Gate D L1161 | 变更范围有证据、影响用例可追踪 |
| V16-019 | 正文 §V16-019（L686–L701）+ 总表 L191 + Gate D L1159/L1163 | 工具权限、执行证据、人工审批可审计 |
| 共同约束 | §0.2.2 不得造第二套执行/终态逻辑（L76）；§0.2.3 测试分层（L79–L90）；§0.2.8 禁止“只调 helper/手工改状态/Mock 替代核心组件”（L135–L146）；L156 Agent 阶段出口“Agent 只能 Draft，不得影响业务决策”；L1207 “禁止 Agent 证据 resolver 缺失时降级通过” | — |

---

## 0.2 基线与工作树漂移（复核前提）

1. 审计起点 `git rev-parse HEAD` = `09140401f`；`git log --oneline -3` 显示其上一条为 `86a44b2cb`（`origin/main`）。
2. 工作树存在**其他审计员/实现者的在途改动**：`M test-platform-v2/backend/app/aiqe/drivers/playwright_driver.py`、`M test-platform-v2/backend/app/aiqe/services/execution_service.py`、`M docs/aiqe/v1.6/_audit/G5-scope-assert.md`，以及未跟踪 `G4-exec-state.md`、`G7-driver-artifact-ops.md`、`scripts/aiqe/check_traceability.py`。
3. **本报告引用的全部文件由 `git status --porcelain -- <files>` 验证为干净**（空输出）：`app/aiqe/services/{benchmark,learning,impact,evidence}_service.py`、`app/aiqe/agents/**`、`app/aiqe/models/{agent,learning,benchmark}.py`、`app/api/v1/{aiqe_automation,aiqe_learning,aiqe_insights}.py`、`app/core/deps.py`、`tests/**`。因此行号与 `09140401f` 一致。
4. 未执行 `pytest` / 未运行任何脚本；本报告所有“会/不会成功”的判断均由代码路径与算术推导，并附复核命令。

---

# 1. V16-010：A6 Benchmark Gate 强制审批和发布

## 1.1 规格“唯一批准条件”8 条 → 状态对照

| # | 规格条件（L559–L568） | 状态 | 关键证据 |
|---|---|---|---|
| 1 | BenchmarkRun 状态为终态 `PASS_GATE` | **MISSING** | `evaluate_candidate()` 只调 `benchmark_service.metrics_of()`，后者仅要求 `run.status == "COMPLETED"` 且 `metrics_json` 非空（`benchmark_service.py:352-356`）；`run.result_status` 只被抄进 `benchmark_json`（`learning_service.py:92`），**从不参与判定**；`approve_candidate()` 完全不读 `result_status`（`:100-119`） |
| 2 | `gate_eligible == true` | **MISSING** | `gate_eligible` 仅写入 `benchmark_json["gate_eligible"]`（`learning_service.py:90`），`approve_candidate()` 不读（`:108-114` 只有 3 个判断） |
| 3 | `sample_count >= configured_min_samples`（≥30，项目可提高不可降低） | **MISSING** | `evaluate_candidate()` 只拒绝 `samples <= 0`（`:74-75`）；`GATING_MIN_SAMPLES=30` 仅用于计算 `gate_eligible`（`benchmark_service.py:26,125`），无项目级可配置项（全仓无 `min_samples` 配置读取） |
| 4 | Precision/Recall/F1/FPR/Unknown Rate 等**所有**强制阈值达标 | **PARTIAL（仅 FPR）** | `DEFAULT_THRESHOLDS` 只有 precision/recall/f1（`benchmark_service.py:27-31`），`meets` 不校验 FPR/unknown（`:126-131`）；`learning_service.approve_candidate()` 只校验 `false_positive_rate <= 0.2`（`:110-112`，常量 `:18`）；`precision/recall/f1/meets_thresholds` 只回显不判定 |
| 5 | 相对已发布 baseline 无退化 | **MISSING** | `compare_with_baseline()` 存在（`benchmark_service.py:359-368`）但**未被任何生产代码调用**（全仓仅 `tests/test_aiqe_aud018_benchmark.py:19,181-188` 引用）；无 `baseline_version`，无容忍阈值，无“已发布 baseline”概念 |
| 6 | dataset 已冻结且 checksum 与 BenchmarkRun 完全匹配 | **MISSING** | `BenchmarkRun` **没有 dataset checksum 快照列**（`models/benchmark.py:83-109`：只有 `dataset_id`，无 `content_hash`）；`evaluate_candidate()` 不查 dataset 状态/`content_hash` |
| 7 | Candidate version / prompt / model / rule version 与 Run 一致 | **MISSING** | `LearningCandidate` 无版本字段（`models/learning.py:14-32`）；`evaluate_candidate()` 不比较 `run.agent_key/agent_version/prompt_hash` 与候选；`dataset_revision` 字段被误写成 `run.dataset_id`（`learning_service.py:83`，明显笔误） |
| 8 | 审批人具备项目权限且不能是发起候选的同一自动化身份 | **MISSING** | `LearningCandidate` **没有 created_by/requested_by**（`models/learning.py:14-32`）→ 无法比较；`approve_candidate()` 无 `actor_id` 参数、不写 `approved_by/approved_at`；API 只校验权限码 `aiqe:learning:approve`（`api/v1/aiqe_learning.py:113`） |

## 1.2 实施步骤 6 条 → 状态对照

| # | 规格步骤（L572–L579） | 状态 | 关键证据 |
|---|---|---|---|
| 1 | `evaluate_candidate()` 只接受 `benchmark_run_id`，服务端读取 Run，不接受自报指标 | **IMPLEMENTED（API 层）/ PARTIAL（服务层）** | API `EvaluateIn` 只有 `benchmark_run_id`（`api/v1/aiqe_learning.py:38-40`），自报字段 → 422（测试 `tests/test_aiqe_aud018_benchmark.py:236-240`）；但服务层仍保留**旧位置参数 `benchmark: dict \| None = None` 并被静默忽略**（`learning_service.py:62`）——旧调用方（如 `scripts/qa/aiqe_m3_m5_gate.py:233-238`）继续传自报指标既不会报错也不生效 |
| 2 | 保存 immutable evaluation snapshot + gate decision，不得无条件置 `benchmarked` | **MISSING** | `row.status = "benchmarked"` 无条件（`learning_service.py:94`）；`benchmark_json` 是普通 JSON 列，可被二次 evaluate 覆盖（`:80-93`），无 snapshot 表、无 hash、无 gate decision 记录 |
| 3 | `approve_candidate()` 事务内重读 Run/Candidate/Dataset 并重算 eligibility | **MISSING** | `approve_candidate()` 只 `get_candidate()` + 读 `benchmark_json` 快照的两个字段（`:107-112`），**不重读 Run、不重读 Dataset、不重算指标** |
| 4 | 增加 `approved_by/approved_at/benchmark_run_id/dataset_checksum/baseline_version/gate_policy_version/approval_reason` | **MISSING** | 7 个字段在 `models/learning.py` 中**全部不存在**；迁移 `alembic/versions/20261122_ta030_learning.py:22-46` 也只建原 9 列（无上述任何列，`bug_patterns` 亦无 `project_id`/`version` `:50-74`） |
| 5 | 发布时再次验证 Run 未撤销、数据集未变、Candidate version 未变 | **MISSING** | `activate_candidate()` 只校验 `status == "approved"`（`learning_service.py:126-127`），随后**直接写 `BugPattern(status="active")`**（`:142-147`）；无 revoke 语义、无 checksum/version 复核 |
| 6 | shadow evaluation、逐步 rollout、一键回滚 | **MISSING** | 全仓无 shadow/rollout/rollback 相关实现；`BugPattern` 无版本、无 `previous` 指针、无 `revoked_at`（`models/learning.py:35-45`） |

## 1.3 代码证据（可复核）

| 证据 | 位置 | 说明 |
|---|---|---|
| B1 | `app/aiqe/services/benchmark_service.py:92-144` | `compute_metrics()`：UNKNOWN 预测计入 unknown+漏报、**不计误报**（`:105-109`）→ 全 UNKNOWN 时 `false_positives=0` |
| B2 | `benchmark_service.py:125-131` | `gate_eligible = samples>=30`；`meets` 只含 precision/recall/f1 |
| B3 | `benchmark_service.py:334-338` | `result_status ∈ {PASS_GATE, REFERENCE_ONLY, BELOW_THRESHOLD}` 由后端计算（正确） |
| B4 | `benchmark_service.py:267-296` | `run_benchmark()` 无 project 校验（`:272-296`）；未把 dataset `content_hash` 快照到 Run（`:284-294` 只写 dataset_id/agent/model） |
| B5 | `learning_service.py:59-97` | `evaluate_candidate()`：读 Run → 读 metrics → 只判 `samples>0` → 无条件 `status="benchmarked"` |
| B6 | `learning_service.py:100-119` | `approve_candidate()`：唯一数值门禁 `false_positive_rate > 0.2`；`row.acknowledged = True` 无条件（`:115`，**伪造人工确认位**） |
| B7 | `learning_service.py:122-152` | `activate_candidate()`：无 benchmark 复核、无审批人、`BugPattern.status="active"` 直写（`:145`） |
| B8 | `app/aiqe/models/learning.py:14-32` | `LearningCandidate` 字段清单：无 created_by / approved_by / approved_at / benchmark_run_id / dataset_checksum / baseline_version / gate_policy_version / approval_reason |
| B9 | `scripts/qa/aiqe_m3_m5_gate.py:233-240` | 仓库自有 M3–M5 Gate 脚本仍以 `evaluate_candidate(db, id, {"false_positive_rate":0.1,"sample_size":50})` 形式调用 → 当前实现下 `str(None)` → `get_run("None")` **必然抛 BenchmarkError**（B5 `:71-73`），即该“官方 Gate 脚本”已不可能通过 |
| B10 | `work-logs/aiqe/v1.4-m3-m6-gates-20261115.md:19-20,60` | 历史证据声称“A6 Benchmark/审批/激活 PASS（FPR 0.1 / 50 样本）” —— 该证据正是自报指标路径，**在 V1.6 口径下不可采信**（规格 L1075：审批前必须从 BenchmarkRun/冻结 Dataset 重新核验，不信任客户端 metrics） |

## 1.4 Gaps（每条可验证）

| ID | Gap | 验证方式 |
|---|---|---|
| **G10-1** | **非 PASS_GATE 可批准/发布（核心 fail-open）**：40 样本全 UNKNOWN → `precision=recall=f1=0`、`unknown_rate=1.0`、`result_status=BELOW_THRESHOLD`、`meets_thresholds=False`，但 `false_positives=0` → `false_positive_rate=0.0` ≤ 0.2 → `approve_candidate()` 通过 → `activate_candidate()` 写入 ACTIVE 规则 | B1+B5+B6+B7；复核：读 `:105-109`（UNKNOWN 不造 FP）与 `:110-112`（仅 FPR 门禁）即可推导 |
| **G10-2** | 10 样本 REFERENCE_ONLY 候选可批准（规格“必测”第 1 条要求拒绝） | `test_aiqe_learning_curator.py:132-135` 只断言 `run.result_status == "REFERENCE_ONLY"`，**从未尝试 approve**；`approve_candidate()` 无 `gate_eligible` 判定 |
| **G10-3** | 无 gate decision 快照：`benchmark_json` 可被二次 evaluate 覆盖，候选 status 只增不减，无法证明“批准时依据的是哪一版 Run/数据集” | `learning_service.py:80-94`（每次 evaluate 覆盖写） |
| **G10-4** | 审批不可归因：没有 `approved_by`，API 只要权限码即可批准；`acknowledged=True` 由代码直接写 | B6+B8；`api/v1/aiqe_learning.py:110-123` |
| **G10-5** | 阈值集合与规格不符：FPR/Unknown Rate 不是 gate 阈值；`thresholds` 可由调用方经 `run_benchmark(thresholds=...)` 传入且**不记录 gate_policy_version** | `benchmark_service.py:96-99,277,330,446,469` |
| **G10-6** | 自报指标接口未删除：服务层保留 `benchmark` 位置参数且静默忽略，制造“已生效”错觉（已实际污染 B9/B10 证据） | `learning_service.py:62`；`scripts/qa/aiqe_m3_m5_gate.py:233-238` |
| **G10-7** | 无 dataset checksum 绑定：`BenchmarkRun` 无 content_hash 快照，冻结数据集被 RETIRED/重建后无法发现“审批用的数据集已变” | `models/benchmark.py:83-109`；`benchmark_service.py:248-264`（`freeze_dataset` 只写 dataset 自身） |
| **G10-8** | “发布”没有独立对象/版本：ACTIVE 直接体现在 `BugPattern.status`，无 publish 记录、无 rollback | `learning_service.py:142-147`；`models/learning.py:35-45` |

## 1.5 测试现状与入口质量

| 测试 | 入口 | 真实性 | 能证明 | 不能证明 |
|---|---|---|---|---|
| `tests/test_aiqe_aud018_benchmark.py::test_api_rejects_self_reported_metrics`（L192-242） | **正式 API** `POST /aiqe/learning/candidates/{id}/evaluate`（仅 override 认证依赖） | 真实 Router+Schema | 自报字段 → 422（G10-6 的 API 半边） | 服务层仍接受静默忽略的同名位置参数 |
| `tests/test_aiqe_learning_api.py::test_evaluate_and_approve_and_activate`（L117-139） | 正式 API | 真实 Service+DB | PASS_GATE（60 样本、FPR 5%）happy path | 非 PASS_GATE、样本不足、baseline、checksum、审批人 |
| `tests/test_aiqe_learning_api.py::test_high_false_positive_rate_rejected`（L142-153） | 正式 API | 真实 | 仅 FPR 门禁 | 其余 7 条批准条件 |
| `tests/test_aiqe_learning_api.py::test_approve_requires_dedicated_permission`（L156-164） | 正式 API | 真实 | 权限码分离（`aiqe:learning:approve`） | 审批人身份/双人审批/发起人回避 |
| `tests/test_aiqe_learning_curator.py`（L60-135，9 条） | **直调 service** | 真实 DB | evaluate 只取后端指标、FPR 超限拒绝、duplicate ack、激活合并 | G10-1（全 UNKNOWN 可批）、G10-2（REFERENCE_ONLY 可批）、G10-3/4/7 |
| `tests/test_aiqe_tenant_scope.py:31-36` | 直调 service | 真实 | 候选跨项目被拒 | 该调用仍在使用已废弃的自报 dict 形态，**间接固化旧接口** |
| `scripts/qa/aiqe_m3_m5_gate.py`（L233-240） | 直调 service + 自报指标 | **伪造指标** | — | 无 BenchmarkRun，无 gate，**该脚本当前必然抛错**（B9） |

**入口质量结论**：V16-010 的“后端算指标 + API 拒绝自报”有真实入口证据；**批准/发布侧的 7 条硬条件零测试**，且仓库既有的 A6 证据（B9/B10）来自自报指标路径，属于规格 §0.2.8 明令禁止的“只凭开发报告/伪造状态宣称能力已实现”。

## 1.6 最小整改建议（不含补丁）

1. `app/aiqe/services/learning_service.py`
   - 删除 `evaluate_candidate()` 的 `benchmark` 位置参数（或改为抛 `LearningError("CLIENT_METRICS_NOT_ACCEPTED")`），杜绝“静默忽略”。
   - `evaluate_candidate()`：`run.result_status == "PASS_GATE"` 且 `metrics["gate_eligible"] is True` 才允许 `status="benchmarked"`；否则保持 `draft` 并落 `gate_decision="REJECTED:<reason>"`；写入 `benchmark_snapshot_hash`（Run 指标 + dataset content_hash 的 sha256）。
   - `approve_candidate()`：新增 `actor_id` 必填；重读 Run/Dataset/Candidate；校验 `PASS_GATE`、`gate_eligible`、`samples >= max(30, project.min_samples)`、precision/recall/f1/fpr/unknown 全部阈值、`dataset.content_hash == run.dataset_snapshot_hash`、`run.agent_key/agent_version/prompt_hash` 与候选一致、`actor != candidate.created_by`；写 `approved_by/approved_at/benchmark_run_id/dataset_checksum/baseline_version/gate_policy_version/approval_reason`。
   - `activate_candidate()`：发布前重复第 5 条校验；新增 `publish_candidate()/revoke_rule()`，`BugPattern` 增 `project_id/version/previous_version_id/revoked_at`。
2. `app/aiqe/models/learning.py` + 新 Alembic 迁移：补 §1.2#4 七列、`created_by`、`benchmark_snapshot_hash`、`gate_decision`；`BugPattern` 补 `project_id/version/revoked_at`，`pattern_key` 唯一约束改 `(project_id, pattern_key)`。
3. `app/aiqe/services/benchmark_service.py`：`BenchmarkRun` 增 `dataset_content_hash` 快照列；`evaluate/approve` 依赖它；`DEFAULT_THRESHOLDS` 增 `false_positive_rate/unknown_rate`。
4. 新增 `scripts/qa` 的 A6 gate：删除自报指标调用，改为“创建 FROZEN ≥30 数据集 → `run_llm_benchmark` → evaluate → approve”，并输出 `benchmark_run_id` 作为证据。
5. **必须新增的负向测试**（`tests/aiqe/test_v16_010_benchmark_gate.py`，全部走正式 API）：
   - (a) 10 样本 REFERENCE_ONLY + FPR=0 → `approve` 400/409，候选仍 `benchmarked`；
   - (b) 40 样本全 UNKNOWN（`BELOW_THRESHOLD`，FPR=0）→ `approve` 拒绝（覆盖 G10-1）；
   - (c) 40 样本 Recall 低但 FPR=0 → 拒绝；
   - (d) `PASS_GATE` 但 evaluate 后数据集被替换/Run 指标被改 → approve 拒绝（覆盖 G10-7）；
   - (e) 用项目 B 的 `benchmark_run_id` → 404/403（与 V16-011 联动）；
   - (f) 同一用户既创建又批准 → 拒绝（覆盖 #8）；
   - (g) 全部达标 + `aiqe:learning:approve` → 批准成功且响应含 `benchmark_run_id/dataset_checksum/approved_by`。

## 1.7 复核命令

```powershell
$B = "F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6\test-platform-v2\backend"
rg -n -A6 "def evaluate_candidate|def approve_candidate|def activate_candidate" "$B\app\aiqe\services\learning_service.py"
rg -n "result_status|gate_eligible|meets_thresholds" "$B\app\aiqe\services\learning_service.py"
rg -n "GATING_MIN_SAMPLES|DEFAULT_THRESHOLDS|meets = " "$B\app\aiqe\services\benchmark_service.py"
rg -n "approved_by|approved_at|benchmark_run_id|dataset_checksum|baseline_version|gate_policy_version" "$B\app\aiqe\models\learning.py"
rg -n "false_positive_rate\", 0.1" "F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6\scripts\qa\aiqe_m3_m5_gate.py"
rg -n "A6" "F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6\work-logs\aiqe\v1.4-m3-m6-gates-20261115.md"
```

---

# 2. V16-011：Benchmark / Learning / Insights 全资源 Project Scope

## 2.1 实施要求 7 条 → 状态对照

| # | 规格要求（L597–L603） | 状态 | 关键证据 |
|---|---|---|---|
| 1 | 所有 service 方法 `project_id` 为**必填**（get/list/create/add_sample/freeze/evaluate/approve/publish/revoke） | **MISSING** | benchmark：`get_dataset(dataset_id)`、`list_samples(dataset_id)`、`add_sample(db,dataset_id,...)`、`freeze_dataset(db,dataset_id,...)`、`get_run(run_id)`、`metrics_of(run_id)` **全部无 project 参数**（`benchmark_service.py:191,198,238,248,345,352`）；learning：`get_candidate/evaluate_candidate/approve_candidate/activate_candidate` 的 `project_id` **默认 None**（`learning_service.py:49,65,105,123`）；无 publish/revoke |
| 2 | SQL 同时含 `resource_id` + `project_id`，禁止裸 UUID 查询 | **MISSING（多数路径）** | `db.get(BenchmarkDataset, dataset_id)`（`:192`）、`db.get(BenchmarkRun, run_id)`（`:346`）、`db.get(LearningCandidate, candidate_id)`（`:51`）均为裸 UUID；`list_samples` 只按 `dataset_id` 过滤（`:240-244`）；`BugPattern` 查询只按 `pattern_key`（`:134`） |
| 3 | Dataset/Run/Candidate/Evidence/LearningRule 之间同 project 校验 | **PARTIAL（仅 1 处）** | `run_llm_benchmark()` 校验 `dataset.project_id != project_id`（`benchmark_service.py:450-451`，且 `project_id is None` 时放行）；`evaluate_candidate()` **不比较 Run 与 Candidate 的 project**；`BugPattern` 无 project 列可比较；Evidence 侧 `resolve_evidence_refs()` 有 project 校验（`evidence_service.py:210-238`，但未用于 Agent） |
| 4 | API 层从认证上下文取 project，禁止 body/query 覆盖 | **IMPLEMENTED（认证侧）/ PARTIAL（透传侧）** | `CurrentUser.project_id` 来自 `X-Project-Id` 头并经 `require_project()` 成员校验（`app/core/deps.py:42,83,88-102`，`require_permission` 自动叠加 `:105-117`）；但多个 AIQE 端点**根本不把 `current.project_id` 传给 service**：`add_sample_api`（`aiqe_insights.py:84-93`）、`freeze_dataset_api`（`:110-112`）、`get_benchmark_run_api`（`:172`）、`post_evaluate`（`aiqe_learning.py:96-98`）、`get_bug_patterns`（`:165`） |
| 5 | 组织级跨项目权限必须显式，而不是绕过 project filter | **MISSING** | 无组织 scope 概念；`is_super`（`deps.py:30-36`）只影响 `require_project` 成员校验，service 层无对应开关 |
| 6 | 复合 FK 或 Service 事务内强校验 | **MISSING** | `aiqe_benchmark_runs.project_id` 可空且**无 FK**（`models/benchmark.py:87`）；`aiqe_benchmark_datasets.project_id` 可空（`:31-33`）；`BugPattern` 无 project 列；无任何复合唯一约束（`(project_id, dataset_key, revision)` 不存在） |
| 7 | 统一 404/403 语义 | **PARTIAL** | learning 用“不存在”字符串匹配映射 404（`aiqe_learning.py:100-101,121`），语义脆弱；benchmark 侧 `add_sample/freeze` 对不存在资源返回 **400**（`aiqe_insights.py:94-96,113-115`），`get_run` 返回 404（`:173-174`）——不一致 |

## 2.2 代码证据（可复核）

| 证据 | 位置 | 说明 |
|---|---|---|
| S1 | `benchmark_service.py:191-195,198-235,238-245,248-264,345-356` | 6 个公开函数无 project 参数 / 无 project 过滤 |
| S2 | `api/v1/aiqe_insights.py:74-98,101-125,165-185` | 3 个 API 端点不传 project（追加样本、冻结、读 Run） |
| S3 | `api/v1/aiqe_learning.py:87-102` | `evaluate` 端点只传 `benchmark_run_id`，不传 `project_id` → `get_candidate()` 以 `project_id=None` 执行（`learning_service.py:65,70`）→ **任意项目候选可被本项目 token 评估** |
| S4 | `learning_service.py:134` + `models/learning.py:35-45` | `activate_candidate()` 按全局 `pattern_key` 查 `BugPattern`；`list_bug_patterns()` 无 project 过滤（`:164-171`）→ A 项目激活的规则全局可见（`api/v1/aiqe_learning.py:157-177` 直接回显） |
| S5 | `models/benchmark.py:87` | `BenchmarkRun.project_id` 可空且无 FK；`benchmark_service.run_benchmark()` 从 dataset 复制（`:285`）→ dataset.project_id 为 NULL 时 Run 无租户 |
| S6 | `benchmark_service.py:450-451` | `if dataset.project_id is not None and ...` → **project_id 为 NULL 的数据集对任意项目放行**（fail-open 分支） |
| S7 | `tests/test_aiqe_benchmark_llm.py:88-92` | 唯一的 benchmark 跨项目测试只覆盖 `run_llm_benchmark()` 一个函数（服务层，无 API） |

## 2.3 Gaps（每条可验证）

| ID | Gap | 验证方式 |
|---|---|---|
| **G11-1** | 跨项目**写**样本：项目 A token 对项目 B 的 DRAFT 数据集 `POST /aiqe/benchmarks/datasets/{B_id}/samples` 成功（无任何 project 校验链） | S1+S2；`add_sample()` 只查 `status == "DRAFT"`（`benchmark_service.py:213-214`） |
| **G11-2** | 跨项目**冻结**：`POST .../freeze` 可为 B 项目数据集冻结并写 `approved_by`（A 的用户 id） | S2；`freeze_dataset()` 无 project（`:248-264`） |
| **G11-3** | 跨项目**读 Run**：`GET /aiqe/benchmarks/runs/{B_run_id}` 返回 B 项目指标与逐样本结果 | S2；`get_run()` 裸 id（`:345-349`） |
| **G11-4** | 跨项目**评估候选**：`POST /aiqe/learning/candidates/{B_candidate}/evaluate` 成功（`get_candidate(project_id=None)`），可用 A 项目 Run 给 B 项目候选打标 | S3；`learning_service.py:70-73` |
| **G11-5** | 跨项目规则泄漏/串写：`BugPattern` 全局，`/bug-patterns` 无 project；A 项目激活 `pattern_key` 会命中 B 项目同名规则并复用 | S4 |
| **G11-6** | `evaluate_candidate()` 不校验 run 与 candidate 同 project（即使调用方传了 `project_id` 也只校验候选） | `learning_service.py:65-73`；对照规格 L599 |
| **G11-7** | 服务层“裸 UUID → 只靠 API 过滤”的模式未消除（规格明确禁止） | S1 全部路径；可写 5 行 pytest 演示 service 直调跨项目成功 |
| **G11-8** | 数据模型层无租户硬约束：可空 project_id、无 FK、无 `(project_id, …)` 唯一键 | S5；`models/benchmark.py:31-33,87`；`models/learning.py:18-20` |

## 2.4 测试现状与入口质量

| 测试 | 入口 | 真实性 | 能证明 | 不能证明 |
|---|---|---|---|---|
| `tests/test_aiqe_tenant_scope.py::test_learning_candidate_cross_project_blocked`（L24-40） | 直调 service | 真实 | 候选 create/get/evaluate/approve/activate 带 `project_id=2` 被拒 | 未传 `project_id` 时（真实 API 路径）跨项目成功；`benchmark_run` 跨项目 |
| `tests/test_aiqe_benchmark_llm.py::test_run_llm_benchmark_rejects_cross_project_dataset`（L88-92） | 直调 service | 真实（predictor 被 monkeypatch） | `run_llm_benchmark` 单一函数拒绝跨项目 dataset | `run_benchmark/add_sample/freeze/get_run/metrics_of`；所有 API 端点 |
| `tests/test_aiqe_learning_api.py`（全部） | 正式 API | 真实 | 单项目 happy path + 权限 | **无任何跨项目 API 用例** |
| `tests/test_aiqe_aud018_benchmark.py`（全部） | 直调 service + 1 条 API | 真实 | 冻结/指标/自报拒绝 | project scope |
| 全仓 | — | — | `rg -n "benchmarks/runs" tests` 仅 `test_aiqe_capabilities_api.py:272`（`unknown-run` → 404） | 跨项目 Run 读取、跨项目冻结/加样本 |

**入口质量结论**：V16-011 的验收（规格 L607“直接调用 Service 层也必须拒绝”）**没有被任何测试覆盖**：现有 2 条跨项目测试恰好只测了**已带 project 参数**的函数，绕开了“参数缺失”这一真实缺口；且无一条测试从 API + 两套 Token 进入。

## 2.5 最小整改建议（不含补丁）

1. `app/aiqe/services/benchmark_service.py`：给 `get_dataset/list_samples/add_sample/freeze_dataset/get_run/metrics_of/run_benchmark` 增加**关键字必填** `project_id`，所有查询同时带 `resource_id` 与 `project_id`；`run_benchmark()` 拒绝 `dataset.status != FROZEN`、`dataset.project_id != project_id`（含 NULL → 拒绝）。
2. `app/aiqe/services/learning_service.py`：`get_candidate/evaluate_candidate/approve_candidate/activate_candidate` 的 `project_id` 改为必填；`evaluate_candidate()` 校验 `candidate.project_id == run.project_id`；`activate_candidate()` 按 `(project_id, pattern_key)` 查重；`list_bug_patterns(project_id=...)`。
3. `app/api/v1/aiqe_insights.py` / `aiqe_learning.py`：`add_sample/freeze/get_run/evaluate/bug-patterns` 全部透传 `current.project_id or 0`；错误统一 404（无权限/不存在同码）。
4. 模型 + 迁移：`aiqe_benchmark_runs.project_id` 改为非空 + FK；`aiqe_benchmark_datasets` 唯一键 `(project_id, dataset_key, revision)`；`bug_patterns` 增 `project_id` 非空 + `(project_id, pattern_key)` 唯一。
5. **必须新增的负向测试**（`tests/aiqe/test_v16_011_project_scope.py`，两项目两 Token、全部走正式 API，并在每个用例后**再直调 service 复核**）：
   - (a) A token `POST datasets/{B}/samples` → 404；DB 中样本数不变；
   - (b) A token `POST datasets/{B}/freeze` → 404；dataset 仍 DRAFT、`approved_by` 未变；
   - (c) A token `GET benchmarks/runs/{B_run}` → 404；
   - (d) A token `POST candidates/{B_candidate}/evaluate` → 404；
   - (e) A token 用 B 项目 `benchmark_run_id` 评估 A 候选 → 404（覆盖 G11-6）；
   - (f) A 项目激活规则后，B token `GET /bug-patterns` 不含该规则（覆盖 G11-5）；
   - (g) 直调 `add_sample/get_dataset/get_run` 不传 project → `TypeError`（证明必填）。

## 2.6 复核命令

```powershell
$B = "F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6\test-platform-v2\backend"
rg -n "^def (get_dataset|add_sample|list_samples|freeze_dataset|get_run|metrics_of|run_benchmark)" "$B\app\aiqe\services\benchmark_service.py"
rg -n "^def (get_candidate|evaluate_candidate|approve_candidate|activate_candidate|list_bug_patterns)" "$B\app\aiqe\services\learning_service.py"
rg -n "benchmark_service\.(add_sample|freeze_dataset|get_run)\(" "$B\app\api\v1\aiqe_insights.py"
rg -n "evaluate_candidate\(" "$B\app\api\v1\aiqe_learning.py"
rg -n "project_id" "$B\app\aiqe\models\learning.py"
rg -n "project_id: Mapped" "$B\app\aiqe\models\benchmark.py"
```

---

# 3. V16-012：A4 Failure Triage Evidence Resolver 强制校验

## 3.1 实施步骤 7 条 → 状态对照

| # | 规格步骤（L628–L634） | 状态 | 关键证据 |
|---|---|---|---|
| 1 | 修改 Agent Protocol：`validate(parsed, context)` 或 `validate(parsed, evidence_resolver=...)`，保证 Adapter 把 `AgentContext.evidence_resolver` 传入 | **MISSING** | `BaseAgent.validate(self, data)` 无 context/resolver（`agents/base.py:53-54`）；`BaseAgent.run()` 调 `self.validate(self.parse_json(...))`（`:56-57`）；`BaseAgentAdapter.execute()` 调 `self._agent.run(request)`（`agents/protocol.py:180`）——**Adapter 根本不读 `context`** |
| 2 | 禁止 A4 validate 默认 `evidence_resolver=None`；构造 A4 时 resolver 必填 | **MISSING（被违反）** | `FailureTriageAgent.validate(self, data, *, evidence_resolver=None)`（`failure_triage_agent.py:112`）默认 None；`if evidence_resolver is not None:`（`:150`）→ 缺省时**整段证据校验被跳过**；`FailureTriageAgent.__init__` 无 resolver 依赖（继承 `BaseAgent.__init__(llm)`，`base.py:21-29`） |
| 3 | A4 schema 规定每条判断至少引用一条证据；UNKNOWN 可注明缺证据但不得伪造 ref | **PARTIAL** | `Hypothesis.supporting_evidence/contradicting_evidence` 默认空列表（`:50-51`），**不校验非空**；仅 `CROSS_FEATURE_DEFECT` 强制至少一条（`:135-138`）；UNKNOWN 允许空证据（符合规格），但“非 UNKNOWN 至少一条证据”未实现 |
| 4 | Resolver 批量解析 refs，返回 canonical metadata，不返回 Secret 原文 | **IMPLEMENTED（独立服务）/ 未接入** | `evidence_service.resolve_evidence_refs()` 返回 `ResolvedEvidenceRef`（`evidence_service.py:210-238`，metadata 只含 status/required/source_ref）——但 **A4 路径未调用** |
| 5 | 保存 evidence snapshot/hash，防止验证后引用被替换 | **MISSING** | `AgentExecution` 只存 `source_refs_json`（`models/agent.py:42`），无 snapshot/hash；A4 输出被整体存 `output_json`，ref 内容不冻结 |
| 6 | 无效 refs、跨项目、跨 Run、tombstone、checksum mismatch 全部拒绝 | **PARTIAL（服务级有，Agent 级无）** | Resolver 覆盖存在性/跨项目/跨 Run（`evidence_service.py:79-101,133-167`，测试 `test_aiqe_aud012_evidence_and_draft.py:165-190`）；**checksum mismatch 无从校验**（引用不带期望 checksum，`artifact` 分支只回显库内 `sha256` `:97`）、**不检查 `upload_status=PENDING`/tombstone**、`signal` 仅格式校验（`:199-207`）；且 A4 不调用 → 全部不生效 |
| 7 | 保留分类置信度、证据支持/反证、缺失证据、人工复核；低置信度 UNKNOWN | **PARTIAL** | `compute_confidence_band()` 确定性（`failure_triage_agent.py:67-90`）且 `confidence` 强制 null（`:54`）；`human_review_required=true`/`auto_close_defect=false` 强制（`:118-121`）；但**低置信度不会自动降级为 UNKNOWN**（`confidence_band=LOW` 仍保留具体分类，`:153-157`） |

## 3.2 代码证据（可复核）

| 证据 | 位置 | 说明 |
|---|---|---|
| A4-1 | `agents/protocol.py:75-83` | `AgentContext.evidence_resolver` 是**可选字段**（默认 None），无“必填”约束 |
| A4-2 | `agents/protocol.py:177-215` | `BaseAgentAdapter.execute()` 只用 `request`；`context` 形参被完全忽略（`output = self._agent.run(request)` `:180`） |
| A4-3 | `agents/base.py:53-57` | 旧协议 `validate(data)` / `run(input_text)` 无证据上下文 |
| A4-4 | `agents/failure_triage_agent.py:112,150-152` | resolver 默认 None + `if ... is not None` 守卫 + **返回值被丢弃**（`evidence_resolver(refs)` 无赋值/无空值判断） |
| A4-5 | `agents/failure_triage_agent.py:147-152` | refs 只取 `supporting+contradicting`（符合规格口径），但**逐个 hypothesis 串行调用 resolver**，不是规格要求的“批量解析” |
| A4-6 | `agents/orchestrator.py:256-292` | `run_plan()` 有 `evidence_resolver` 透传参数（`:266,286,340`），但仅 A6 使用它（`learning_curator_agent.py:105-106`）；A4 经 Adapter 丢失 |
| A4-7 | `agents/registry.py:129-133` | A4 通过 `BaseAgentAdapter(agent_class(llm, model=model), version="1.1.0")` 构造 —— 无 resolver 注入点 |
| A4-8 | `app/aiqe/services/evidence_service.py:210-248` | 现成 resolver（含 `assert_valid_evidence_refs`），生产代码中**仅 `defect_draft_service` 调用**（`grep -rn "assert_valid_evidence_refs\|resolve_evidence_refs" app/` → `defect_draft_service.py:28,178,188,262` + 定义） |
| A4-9 | `grep -n "FailureTriageAgent" app/` | 仅 `registry.py:17,76`（注册表）→ **app/ 内无任何 API/Job/Worker 构造 A4**；A4 的实际构造只出现在 `tests/test_aiqe_failure_triage_agent.py:9` 与 `scripts/qa/aiqe_m3_m5_gate.py:17,158`（离线 Gate 脚本，直调 `.triage()`，无 resolver） |

## 3.3 Gaps（每条可验证）

| ID | Gap | 验证方式 |
|---|---|---|
| **G12-1** | **resolver 缺失即降级通过（规格 L1207 明文禁止）**：默认 None 且分支跳过，A4 输出照常 `COMPLETED` 并进入 `AgentResult.output` | A4-4；复现：`FailureTriageAgent(llm).triage({...})` 传任意不存在的 `supporting_evidence=["artifact:fake"]` → 不抛错 |
| **G12-2** | 正常 Agent Adapter 路径**永远**不校验证据：`run_plan()` → `get_agent("A4")` → Adapter → `BaseAgent.run()`，`context.evidence_resolver` 被丢弃 | A4-1/A4-2/A4-3；`orchestrator.py:291` + `base.py:56-57` |
| **G12-3** | resolver 返回值被忽略：即使注入 resolver，也不校验“解析数量 == refs 数量”、不拒绝空结果、不落 canonical metadata / snapshot hash | A4-4；`failure_triage_agent.py:150-152` 中 `evidence_resolver(refs)` 无赋值、无长度/空值判定 |
| **G12-4** | checksum mismatch / 未完成上传 / tombstone 未覆盖：`artifact` 分支只查存在 + project + run，把库内 `sha256` 原样回显（引用中无期望值可比对），不校验 `upload_status`；`signal` 仅格式校验 | `evidence_service.py:79-101,199-207` |
| **G12-5** | 无 `INVALID_EVIDENCE`/`BLOCKED` 语义：A4 的 `status` 只可能是 COMPLETED/FAILED（Adapter 层），`AgentResult.error_code` 无 `INVALID_EVIDENCE`（全仓 0 命中） | `rg -n "INVALID_EVIDENCE" app/` 0 命中；`agents/protocol.py:19-30` |
| **G12-6** | A4 无生产入口：无 API、无 Job、`run_plan` 无调用方（见 V16-013），故规格验收“通过正常 Agent Adapter 执行 A4”**无法被执行** | A4-9 + `rg -n "run_plan\(" app/` 仅定义 |
| **G12-7** | 低置信度不降级 UNKNOWN；`confidence_band` 只是回显字段，不影响 `attribution_status`/是否可用 | `failure_triage_agent.py:153-157` |

## 3.4 测试现状与入口质量

| 测试 | 入口 | 真实性 | 能证明 | 不能证明 |
|---|---|---|---|---|
| `tests/test_aiqe_failure_triage_agent.py`（9 条，L41-108） | **直调 `FailureTriageAgent.triage()`**（`llm` 为 lambda，等于把模型替换成固定 JSON） | 局部协议 | auto_close 拒绝、confidence null、human_review 强制、UNKNOWN 一致性、CROSS_FEATURE 需证据 | **resolver 相关全部未覆盖**；Adapter 路径；证据存在性/跨项目/跨 Run |
| `tests/test_aiqe_aud012_evidence_and_draft.py`（L133-190） | **直调 `resolve_evidence_refs()`** | 真实 DB | resolver 本身的正/负向（不存在、跨项目、跨 Run、signal 仅格式） | resolver 是否被 Agent 调用、返回值是否被消费 |
| `tests/test_aiqe_aud012_evidence_and_draft.py::test_api_rejects_invalid_evidence_and_cross_project`（L352-372） | 正式 API，但对象是**缺陷草稿** | 真实 | 草稿链路拒绝非法 evidence | 与 A4/Agent 无关 |
| `tests/test_aiqe_aud013_agent_protocol.py::test_learning_curator_*`（L321-344） | 直调 A6 `execute` | 真实 | A6 在**无 resolver** 时降级为 PARTIAL + `EVIDENCE_NOT_RESOLVED` | A4；且反向证明“resolver 缺失”在其它 Agent 上已有可接受的降级先例 |

**入口质量结论**：V16-012 的验收句要求“通过正常 Agent Adapter 执行 A4（不能直接调用 Agent.validate）”，而**现有测试全部是直接调用 `.triage()`（内部就是 `validate`）**，恰好规避了本 Issue 的核心；且不存在任何 Adapter→A4 的可执行路径，Spec 验收无法被执行。

## 3.5 最小整改建议（不含补丁）

1. `app/aiqe/agents/base.py` + `app/aiqe/agents/protocol.py`：
   - `BaseAgent.validate(self, data: dict, *, context: AgentContext | None = None)`；`BaseAgent.run(input_text, *, context=None)` 透传；`BaseAgentAdapter.execute()` 改为 `self._agent.run(request, context=context)`（**这是修复 G12-1/G12-2 的唯一入口**）。
   - `AgentContext.evidence_resolver` 改为构造期必填（或在 `AgentContext.__post_init__` 对 A4/A6 断言非 None）。
2. `app/aiqe/agents/failure_triage_agent.py`：
   - `validate()` 的 `evidence_resolver` 改为**位置必填**（无默认值）；`resolved = evidence_resolver(refs)`；`len(resolved) != len(set(refs))` → `AgentSchemaError("INVALID_EVIDENCE")`；resolver 抛异常/返回空 → `AgentResult(status="FAILED", error_code="INVALID_EVIDENCE")`，不得 COMPLETED。
   - 非 UNKNOWN 假设强制 `supporting_evidence` 非空；`confidence_band in {LOW, UNKNOWN}` → 强制 `attribution_status="UNKNOWN"` 或标记 `needs_human`。
   - 把 `resolved` 的 canonical metadata 与 `checksum` 写入 `AgentResult.output["evidence_manifest"]`。
3. `app/aiqe/services/evidence_service.py`：`_resolve_one()` 补 artifact checksum/过期/tombstone 校验；新增 `to_manifest()`（ref → {kind, project_id, run_id, checksum}）。
4. 打通 A4 正式入口：新增 `POST /aiqe/agent-tasks/{id}/run`（见 V16-013），A4 任务必须携带 `run_id` 与已构造的 resolver（`lambda refs: resolve_evidence_refs(db, project_id=..., run_id=..., refs=refs)`）。
5. **必须新增的负向测试**（`tests/aiqe/test_v16_012_a4_resolver.py`，全部经 **Adapter / run_plan / API** 进入）：
   - (a) `get_agent("A4").execute(context_without_resolver, ...)` → `FAILED` + `INVALID_EVIDENCE`（覆盖 G12-1）；
   - (b) `BuildContext(resolver=None)` 构造即抛错；
   - (c) resolver 返回 `[]` → FAILED（空结果不得通过）；
   - (d) resolver 抛 `EvidenceRefError` → FAILED（不是 500，也不是 COMPLETED）；
   - (e) 有效 refs（node/attempt/assertion，同 project 同 run）→ COMPLETED 且 `evidence_manifest` 含 checksum；
   - (f) 跨项目 / 跨 Run / 不存在 / artifact 已 tombstone / checksum 不匹配 → 全部 FAILED；
   - (g) 端到端：`POST /agent-tasks`（A4 计划）→ approve → run（真实 Run 证据）→ `AgentExecution.output_json.evidence_manifest` 非空。

## 3.6 复核命令

```powershell
$B = "F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6\test-platform-v2\backend"
rg -n "def validate|evidence_resolver" "$B\app\aiqe\agents\failure_triage_agent.py" "$B\app\aiqe\agents\base.py" "$B\app\aiqe\agents\protocol.py"
rg -n -A3 "output = self\._agent\.run" "$B\app\aiqe\agents\protocol.py"
rg -n "FailureTriageAgent|get_agent\(\"A4\"|get_agent\('A4'" "$B\app"
rg -n "resolve_evidence_refs|assert_valid_evidence_refs" "$B\app"
rg -n "INVALID_EVIDENCE" "$B\app"
rg -n "def triage|\.triage\(" "$B\tests\test_aiqe_failure_triage_agent.py"
```

---

# 4. V16-013：A0 Agent Task Draft → Human Approval → run_plan 真正执行

## 4.1 目标状态机与 9 条实施步骤 → 状态对照

**目标状态机**：`DRAFT → PENDING_APPROVAL → APPROVED → QUEUED → RUNNING → {COMPLETED, FAILED, BLOCKED, CANCELLED}`（+`WAITING_HUMAN`）→ **MISSING**（不存在任何 `AgentTask` 状态列；`PLAN_STATUSES`（`orchestrator.py:43-51`）只是内存 `PlanRunResult.status` 的取值域，且缺 `DRAFT/PENDING_APPROVAL/APPROVED`、多出 `PARTIAL`）。

| # | 规格步骤（L650–L658） | 状态 | 关键证据 |
|---|---|---|---|
| 1 | 新增持久化 `AgentTask`、`AgentExecution`、`AgentStepExecution`（字段：project_id、task_type、input refs、plan JSON/hash、agent registry version、prompt version、toolset version、requested_by、approved_by、status、started_at、finished_at、result refs、error code） | **PARTIAL** | `AgentExecution` 存在且已扩展（`models/agent.py:18-55`：agent_version/prompt_version/model_provider/input_hash/output_hash/token_usage/source_refs/tool_calls/warnings/needs_human/task_id/parent_task_id/idempotency_key）；**但 `AgentTask`/`AgentStepExecution` 不存在**（`app/aiqe/models/` 无该表，全仓 `agent_tasks` 0 命中）；`AgentExecution.task_id` 只是字符串（`:46`），无 FK、无 plan_hash、无 approved_by、无 requested_by、无 toolset_version |
| 2 | `POST /agent-tasks` 创建 Draft，必须持久化计划与输入证据 refs，返回 task ID、plan hash、审批要求 | **MISSING** | 端点存在（`api/v1/aiqe_automation.py:37-69`）但：不写任何表；返回 `plan_id`（`plan-uuid[:12]`，内存生成 `orchestrator.py:179`）**无 plan hash**、**无审批要求**、**无 input refs**；且**在 HTTP 请求线程内直接执行 A0**（`:52`） |
| 3 | `POST /agent-tasks/{id}/approve`：校验权限、计划未变、证据有效、工具权限、预算，记录审批人 | **MISSING** | 路由不存在（`aiqe_automation.py` 仅 2 个路由：`:37`、`:72`） |
| 4 | `POST /agent-tasks/{id}/run` 或审批后自动排队，经统一 Job/Outbox 调 `run_plan()`，不得在 HTTP 线程同步执行长任务 | **MISSING** | 路由不存在；`run_plan` 无调用方（`rg -n "run_plan\(" app/` 仅定义 `orchestrator.py:256`）；无 `ExecutionJob`/Outbox 关联 |
| 5 | `run_plan()` 逐 Agent 记录输入/输出 schema、prompt/model version、tool calls、证据 refs、tokens/cost、耗时、重试、审批点、状态 | **PARTIAL** | `_persist_execution()` 写 prompt_version/model/input_hash/output_hash/token_usage/source_refs/tool_calls/warnings（`orchestrator.py:202-244`）；**缺：输入/输出 JSON schema、cost、耗时（`started` 只有 `time.monotonic` 用于超时判断，未落库）、重试次数、审批点** |
| 6 | ToolRegistry 必须绑定真实实现；注册时校验 permission scope/项目范围/参数 schema/超时/幂等/审计 | **MISSING** | `run_plan()` 默认 `build_tool_registry()` → `ToolRegistry(allowlist, {})`（`orchestrator.py:273` + `registry.py:104-110`）→ **所有工具 resolve 均抛 `ToolNotAllowed`**；无上述任何注册期校验 |
| 7 | 每次工具调用前授权、调用后写 ToolExecution Event + Artifact；敏感工具需人类确认 | **MISSING** | 无 ToolExecution 模型/事件（`rg -n "ToolExecution" app/` 0 命中）；Agent 自身从不调用 `context.tools.resolve()`（全仓 `resolve(` 只在 `protocol.py:66` 定义与测试中） |
| 8 | A1–A6 失败策略明确（A1 WAITING_HUMAN、A2 不合格不能继续、A3 需冻结审批、A4 evidence validated、A5 需 diff 证据、A6 不可自行发布） | **PARTIAL** | A4/A5/A6 的精神在各自 Agent 内有局部实现（A4 human_review 强制、A6 `REQUIRES_BENCHMARK_AND_HUMAN_APPROVAL`、A5 forced suite），但**A4 evidence validated 未实现（V16-012）、A5 diff 证据未实现（V16-014）**；`run_plan` 只做“依赖未 COMPLETED → CANCELLED”（`:294-303`），无按 Agent 类型的失败策略 |
| 9 | 取消/超时/重试/重复请求/审批撤销必须有状态规则 | **PARTIAL** | 幂等：`idempotency_key` 命中复用（`:304-331`，测试 `test_aiqe_aud013_agent_protocol.py:247-266`）；超时：**事后判定**（执行完才发现 `elapsed > timeout`，`:393-397`，不能中断）；**取消/审批撤销：不存在**；`max_attempts` 定义但从未使用（`AgentTask.max_attempts` `:63`，`run_plan` 无重试循环） |

## 4.2 代码证据（可复核）

| 证据 | 位置 | 说明 |
|---|---|---|
| T1 | `app/api/v1/aiqe_automation.py:37-69` | 唯一 agent 端点：`build_plan()` + `get_agent("A0").execute(...)` 在本请求线程内执行；响应只有 plan_id/tasks/a0_status/a0_output；**无持久化、无 plan hash、无审批字段** |
| T2 | `app/aiqe/agents/orchestrator_agent.py:29-69` | A0 纯规则、无副作用，但 `output["a0_state"]="QUEUED"`（`:57`）与 `AgentResult.status="COMPLETED"`（`:63`）**自相矛盾**（状态语义伪造/不一致） |
| T3 | `app/aiqe/agents/orchestrator.py:58-81` | `AgentTask` 是 `@dataclass(frozen=True)` **内存对象**，非 ORM |
| T4 | `app/aiqe/agents/orchestrator.py:256-456` | `run_plan()`：完整 DAG 执行器；**全仓唯一调用方是 tests**（`tests/test_aiqe_aud013_agent_protocol.py:201,238,261-262,286,301`） |
| T5 | `app/aiqe/agents/orchestrator.py:419-440` | 落库状态用 `"succeeded"`（`:427`）或 `status.lower()`，与 `AGENT_STATUSES`/`PLAN_STATUSES` 的大写枚举混用；`_existing_execution()` 用 `IN ("succeeded","COMPLETED")` 兼容（`:247-253`）——**状态词表三套并存** |
| T6 | `app/aiqe/models/agent.py:18-55` + 迁移 `alembic/versions/20261116_ta019_agent_executions.py`、`20261124_aud013_agent_protocol.py` | 只有 `agent_executions`（及其 AUD-013 扩列）；无 `agent_tasks`/`tool_executions` 表（`Select-String alembic/versions "agent_task\|tool_execution"` 0 命中）；无 task 级状态/审批/plan hash；`task_id` 无 FK |
| T7 | `app/aiqe/agents/orchestrator.py:119-153` | `DEFAULT_PLAN_TEMPLATE` 含 A1/A2/A3/A5/A4/A6 与依赖（A5 无依赖、A6 依赖 A4）——**Plan 结构存在**，但由于 T4 永不执行 |
| T8 | `app/aiqe/agents/registry.py:104-110` + `orchestrator.py:273` | `run_plan` 默认注入空工具表 |
| T9 | `scripts/qa/aiqe_m3_m5_gate.py:45-58` | 该 Gate 脚本用手写 `AgentExecution(status="succeeded")` 记录 A5（`_persist`），绕过 `run_plan`/协议校验 —— **伪造执行状态**的既有先例 |
| T10 | `app/api/v1/aiqe_automation.py:72-93` | 同文件的 `regressions/{id}/sync` 表明作者会在本文件加路由；仍无 agent approve/run |

## 4.3 Gaps（每条可验证）

| ID | Gap | 验证方式 |
|---|---|---|
| **G13-1** | 无 AgentTask 持久化：Draft 不落库、无 plan hash、无 `requested_by`，服务重启即丢；无法审计“谁在何时批准了哪份计划” | T1+T6 |
| **G13-2** | 无审批门禁：不存在 approve/run 端点，因此“未审批调用 run 返回 409/403”无法成立（没有可调用的 run）；`run_plan()` 可被任意内部调用方无审批直接执行 | T4；`rg -n "agent-tasks" app/` 仅 1 处 |
| **G13-3** | `run_plan()` 是死代码：A1–A6 从未真实执行（唯一真实 Agent 调用是 `POST /agent-tasks` 里的 A0 规则引擎） | T1+T4；`rg -n "run_plan\(" app/` |
| **G13-4** | 工具链为空且 Agent 不调工具：`tool_calls` 恒空，`tool_calls_json` 只是“回填”；`ToolNotAllowed` 一旦真调用就会拒绝 | T8；`rg -n "\.resolve\(" app/aiqe` 0 命中 |
| **G13-5** | 超时不可中断、`max_attempts` 未实现、无取消/审批撤销状态 | T4（`:393-397`）；`AgentTask.max_attempts` `:63` |
| **G13-6** | 状态词表不一致（`QUEUED/COMPLETED` vs `succeeded/failed`），且 A0 自报 `a0_state=QUEUED` 却返回 COMPLETED | T2+T5 |
| **G13-7** | 无执行证据链：`AgentExecution` 无 cost/耗时/重试/审批点/输入输出 schema；无 ToolExecution | T6；规格 §9.6 L1081 的 ToolExecution 字段全缺 |
| **G13-8** | `POST /agent-tasks` 在 HTTP 线程执行 Agent（虽然 A0 廉价），违反“不得在请求线程跑长任务”的设计取向；且响应把 A0 `output.task_plan` 与 `build_plan()` 结果重复返回，两份 plan 可能不一致（A0 内部重新 `build_plan(goal)`，忽略 `include`） | T1（`:48` vs `:52`）；`orchestrator_agent.py:41` |

## 4.4 测试现状与入口质量

| 测试 | 入口 | 真实性 | 能证明 | 不能证明 |
|---|---|---|---|---|
| `tests/test_aiqe_capabilities_api.py::test_agent_task_plan`（L339-346） | **正式 API** `POST /aiqe/agent-tasks` | 真实 Router（A0 规则引擎，无 LLM） | 返回 A1<A2<A3 顺序、`a0_status=COMPLETED` | 未断言持久化、plan hash、审批、不执行（该测试**默认接受“创建即执行 A0”**，与验收“Draft 创建后不执行 Agent”冲突） |
| `tests/test_aiqe_aud013_agent_protocol.py`（L180-307，5 条 run_plan） | 直调 `run_plan(..., executor=_fake_executor)` | **注入假 executor**（A1–A6 全部被替换） | DAG 串行、WAITING_HUMAN 取消下游、幂等、失败/异常终止与落库 | 真实 Agent、工具、审批、API 入口；且 fake executor 使“执行记录可追溯”只证明 `_persist_execution` 格式化正确 |
| `tests/test_aiqe_aud013_agent_protocol.py:119-128` | 直调 `build_tool_registry/assert_child_allowed` | 真实 | allowlist 拒绝、未注册实现拒绝 | Tool 元数据/审计 |
| `tests/test_aiqe_requirement_agent.py`（L31-73） | 直调 `run_agent()`（单 Agent 兼容入口） | 真实 | A1 单次执行落 `AgentExecution` | 不经过 task 状态机/审批 |
| 全仓 | — | — | `rg -n "approve.*agent\|agent.*approve"` 0 命中；无 409/403 未审批测试 | 验收 5 条全部无覆盖 |

**入口质量结论**：V16-013 只有“Draft 端点”有真实 API 测试（且该测试把“创建即执行 A0”当作正确行为）；**执行闭环的唯一测试全部注入 fake executor**，恰好绕过本 Issue 要证明的“审批后真实执行 A1–A6”。

## 4.5 最小整改建议（不含补丁）

1. `app/aiqe/models/agent.py`（优先扩展，避免重复建模）+ 新迁移：
   - 新增 `AgentTask`：`id/project_id/task_type/goal/input_refs_json/plan_json/plan_hash/agent_registry_version/prompt_version/toolset_version/requested_by/approved_by/approved_at/status/error_code/started_at/finished_at/cancel_reason`；`(project_id, plan_hash)` 唯一（防重复提交）。
   - 新增 `ToolExecution`：按规格 §9.6 L1081 九列；`AgentExecution` 增 `cost_usd/duration_ms/attempt_no/approval_point`。
2. `app/api/v1/aiqe_automation.py`：
   - `POST /agent-tasks`：只 `build_plan` + 计算 `plan_hash` + 落 `AgentTask(status="PENDING_APPROVAL")`；**不再执行 A0**；返回 `task_id/plan_hash/approval_required`。
   - `POST /agent-tasks/{id}/approve`：校验 `status=="PENDING_APPROVAL"`、`plan_hash` 未变、证据 refs 经 resolver、每个工具 `resolve()!=UNAVAILABLE`、预算；写 `approved_by/approved_at → APPROVED`。
   - `POST /agent-tasks/{id}/run`：仅 `APPROVED` 可执行，否则 409；改为 `enqueue ExecutionJob(kind="agent_plan")`，由 `job_consumer` 调 `run_plan`；返回 202。
   - `POST /agent-tasks/{id}/cancel`、`POST /agent-tasks/{id}/retry`：状态规则。
3. `app/aiqe/agents/orchestrator.py`：`run_plan` 增 `task_id` 入参，落 `AgentTask.status` 迁移；`max_attempts` 真正重试；超时前置（`signal`/子进程/心跳）或至少把超时任务标 `BLOCKED` 而非事后改 FAILED；状态词表统一为 `AGENT_STATUSES`。
4. **必须新增的负向测试**（`tests/aiqe/test_v16_013_agent_task.py`）：
   - (a) `POST /agent-tasks` → 只 1 条 `AgentTask(PENDING_APPROVAL)`，`AgentExecution` 计数为 0（覆盖 G13-1/“Draft 后不执行 Agent”）；
   - (b) 未审批 `POST /run` → 409；无 `menu:aiqe_runs` → 403；
   - (c) 审批后 `POST /run` → 产生 Job；`job_consumer.run_job()` 后每个 plan 节点都有 `AgentExecution`（真实 A1/A2/A3；LLM 可用受控 stub）；
   - (d) 让 A2 抛错 → Task=`FAILED`（不得 COMPLETED），A3 记录 `CANCELLED/DEPENDENCY_NOT_COMPLETED`；
   - (e) 修改 plan 后 approve → 409（plan_hash 不一致）；
   - (f) 计划节点引用未注册工具 → approve 拒绝（`UNAVAILABLE`）；
   - (g) approve 与 cancel 事件在 `agent_tasks`/事件表可查（含操作人、时间）。

## 4.6 复核命令

```powershell
$B = "F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6\test-platform-v2\backend"
rg -n "agent-tasks|approve|/run" "$B\app\api\v1\aiqe_automation.py"
rg -n "run_plan\(" "$B\app" "$B\tests"
rg -n "class AgentExecution|class AgentTask|tool_calls_json|idempotency_key" "$B\app\aiqe\models\agent.py"
rg -n "PLAN_STATUSES|max_attempts|elapsed > task.timeout_seconds" "$B\app\aiqe\agents\orchestrator.py"
rg -n "a0_state|status=\"COMPLETED\"" "$B\app\aiqe\agents\orchestrator_agent.py"
rg -n "_fake_executor|executor=executor" "$B\tests\test_aiqe_aud013_agent_protocol.py"
```

---

# 5. V16-014：A5 Change Impact 纳入 Agent Plan 和回归 Scope

## 5.1 实施要求 6 条 → 状态对照

| # | 规格要求（L675–L680） | 状态 | 关键证据 |
|---|---|---|---|
| 1 | 输入含 base/head 完整 SHA、repo/project mapping、变更文件、diff hash、路由/API/schema/migration 影响证据 | **PARTIAL（但不在 A5 上）** | `impact_service.load_git_diff()` 接受 base/head 并校验十六进制（`impact_service.py:100-129`，允许 7–40 位，短 SHA 未拒绝）；`collect_changes()` 产出 files/symbols/routes/migrations/components（`:186-216`）；**A5 Agent 的输入只有 `files: list[str]`**（`change_impact_agent.py:76-80`），无 SHA、无 diff hash、无 route/migration 证据 |
| 2 | 结果按 `DIRECT/TRANSITIVE/CONTRACT/DATA/UI/RISK` 分类，关联 Case/Workflow/Assertion/Defect refs | **MISSING** | 全仓无该 6 类常量；A5 输出是 `impacted_areas`(auth/payment/live/admin/api) + `candidate_suites`(suite 名)（`change_impact_agent.py:16-28,50-53`）；`impact_service` 的 component kind 是 `module/api/model/service/ui/migration`（`:171-183`），edge kind 是 `changed/covers/depends`（`:323-346`）——都不是规格分类；`candidates` 只关联 Case（`case_id`），无 Workflow/Assertion/Defect refs |
| 3 | 每条影响关系给出证据来源（AST symbol/route/OpenAPI operation/migration table/column/dependency graph），不得只凭文件名关键词 | **MISSING（A5 侧被明确禁止）** | A5 判定逻辑就是**路径子串匹配**：`any(needle in path for path in paths for needle in needles)`（`:41`）——规格 L677 点名禁止；`impact_service` 虽有 AST/route/migration，但 `candidates[].reason` 只有 3 个固定值（`:319,376,387`），`trace_path` 全部使用 `components[0]`（`:299`、`:376`、`:387`）——**所有候选共享同一个首个组件**，不是逐关系的符号级证据 |
| 4 | A5 输出进入 V16-008 Mandatory/Related Scope；人工可扩大不可无审批缩小 | **MISSING** | `impact_service` 与 `regression_service` 零关联（无 import、回归 API 无 `impact_plan_id` 入参）——与 G5 报告 G8-6 一致；A5 的 `candidate_suites` 是 suite 名，与回归 Case/Node scope 无映射；`merge_ai_plan()` 有“AI 不可删强制”守卫（`:363-365`）但只在 `impact_service`、且 `persist_edges`/`merge` 在 API 路径上未被调用 |
| 5 | 无法分析的类型/生成代码/动态路由/缺 baseline → UNKNOWN + 更广回归，不得返回“无影响” | **MISSING（返回“仅 smoke”）** | A5：无命中 → `impacted_areas=["unknown"]` + **只给 smoke-suite**（`change_impact_agent.py:46-48`，测试 `test_aiqe_change_impact_agent.py:42-43` 将“README.md → 仅 smoke”固化为契约）；`impact_service`：读文件失败 `continue`（`:199-200`），空 diff → `mandatory=[]`、`candidates=[]` → API 直接返回“无影响”（且 `test_aiqe_capabilities_api.py:285-304` 断言该行为） |
| 6 | 记录影响算法版本、规则版本、diff hash、结果 checksum | **MISSING** | `ImpactPlan.payload()` 无 hash/version 字段（`impact_service.py:69-83`）；`diff_digest()` 存在但**无生产调用**（仅测试 `:208`）；`persist_edges(version=...)` 的 version 由调用方给，API 不调用 `persist_edges`（`aiqe_insights.py:207-216`）→ ImpactEdge **生产环境从不落库** |

## 5.2 代码证据（可复核）

| 证据 | 位置 | 说明 |
|---|---|---|
| I1 | `agents/change_impact_agent.py:16-28` | `AREA_RULES`：`("auth", ("auth","login",...), ("auth-suite","smoke-suite"))` 等 5 条**文件名规则** |
| I2 | `agents/change_impact_agent.py:35-53` | `compute_impact()`：纯字符串包含匹配；无命中 → `unknown` + `DEFAULT_SUITES` |
| I3 | `agents/change_impact_agent.py:76-96` | `analyze()` 设置 `self._expected` 后 `run()`；`validate()` 依赖 `self._expected` 做“强制 suite/影响域不可漏”校验 |
| I4 | `agents/protocol.py:177-215` + `agents/base.py:56-57` | Adapter 路径**不会调用 `analyze()`** → `_expected` 为 None → `validate()` 中 `expected = {}` → `forced=set()` → 所有包含关系判定恒真（**强制校验失效**） |
| I5 | `agents/registry.py:132` + `agents/orchestrator.py:291` | A5 经 `BaseAgentAdapter` 构造与执行（`run_plan` 路径），即 I4 必然发生 |
| I6 | `services/impact_service.py:100-129,186-216` | 真实 git diff + AST/TS 导出 + FastAPI route 正则 + migration 识别（AUD-017 基础实现） |
| I7 | `services/impact_service.py:254-350` | 强制集合来自**调用方入参** `failed_case_ids/changed_contract_ids`（`:261-278`），不是从 A5/回归/缺陷推导 |
| I8 | `api/v1/aiqe_insights.py:197-220` | 影响 API 只 `build_impact_plan` 并 `return payload()`：**不 `persist_edges`、不记 version、不返回 diff_digest** |
| I9 | `services/impact_service.py:393-423,426-428` | `persist_edges()`/`diff_digest()` 在生产代码中零调用（仅测试） |
| I10 | `scripts/qa/aiqe_m3_m5_gate.py:218-225` | 所谓 A5 证据：硬编码 3 个文件路径调用 `analyze(files)`，无 commit、无 diff、无 route/migration 证据 |

## 5.3 Gaps（每条可验证）

| ID | Gap | 验证方式 |
|---|---|---|
| **G14-1** | A5 结论仍由文件名关键词产生（规格明令禁止），无 SHA/diff/AST 参与 | I1+I2；`rg -n "ast\.\|git \|openapi" app/aiqe/agents/change_impact_agent.py` 0 命中 |
| **G14-2** | **经 Adapter 时 A5 的强制集合守卫失效**：`_expected=None` → 任何输出（含漏选 auth-suite / 漏选 auth 域）都通过 | I3+I4+I5；与 `tests/test_aiqe_change_impact_agent.py:54-63`（直调 `analyze` 才有守卫）形成对照 |
| **G14-3** | A5 不在任何真实执行链：`run_plan` 死代码（V16-013），`analyze()` 只在 Gate 脚本里用硬编码文件列表调用 | I10；`rg -n "ChangeImpactAgent\|compute_impact" app/` 仅 registry/定义 |
| **G14-4** | `impact_service` 与 A5/AgentPlan/回归 Scope 三者互不连接：无 `impact_plan_id`、无 `candidate_suites→case` 映射、无 mandatory 传递 | I7；`rg -n "impact_service" app/aiqe/agents app/aiqe/services/regression_service.py` 0 命中 |
| **G14-5** | 证据粒度造假感：所有候选 `trace_path` 用 `components[0]`，reason 固定 3 值；无法回溯“这条 relation 由哪个 symbol/route/migration 导致” | `impact_service.py:299,319,376,387` |
| **G14-6** | 未知类型/空 diff 返回“无影响”（只 smoke / 空 mandatory），且被测试固化为期望；违反“无 baseline 不得声称无影响” | I2；`test_aiqe_capabilities_api.py:303-304`；`test_aiqe_change_impact_agent.py:42-43` |
| **G14-7** | 无算法/规则版本、无 diff hash、无结果 checksum 落库；ImpactEdge 生产不落库 → “影响结果可追溯”不成立 | I8+I9；`ImpactEdge` 仅测试写入 |
| **G14-8** | `load_git_diff()` 接受 7 位短 SHA（规格 V16-014#1 要求“完整 SHA”） | `impact_service.py:104-105`（`{7,40}`） |

## 5.4 测试现状与入口质量

| 测试 | 入口 | 真实性 | 能证明 | 不能证明 |
|---|---|---|---|---|
| `tests/test_aiqe_change_impact_agent.py`（7 条） | 直调 `compute_impact()` / `analyze()`（LLM 用 lambda 固定 JSON） | 纯文件名规则 | auth 强制 suite、区域并集、unknown→smoke、漏选被拒 | Agent Adapter 路径（G14-2）；真实 diff/SHA/AST |
| `tests/test_aiqe_aud017_impact_graph.py`（L76-256） | 直调 `build_impact_plan/collect_changes/merge_ai_plan/persist_edges`，**真实临时 git repo** | 真实（唯一质量较高的测试集） | diff/symbol/route/component 解析、强制集合、AI 不可删、edges 幂等 | **不经过 API、不经过 A5、不进入回归 Scope**；无 rename/删 API/鉴权中间件等负向场景 |
| `tests/test_aiqe_capabilities_api.py::test_impact_plan_with_real_commit_range`（L285-304） | 正式 API | 真实 | `base=head` 时空 diff 返回 200 | 真实变更集；且**断言“空变更=无影响”** 正是规格禁止的语义 |
| `tests/test_aiqe_capabilities_api.py::test_impact_plan_with_identical_shas`（L276-282） | 正式 API | 真实 | `"HEAD"` 非十六进制 → 422 | 7 位短 SHA 未被拒 |
| `scripts/qa/aiqe_m3_m5_gate.py:218-225` | 直调 `analyze()` + 硬编码文件 | 无 diff | — | 任何真实影响证据 |

**入口质量结论**：V16-014 的“真实 diff → 影响 → 回归范围”链条**三段全部断开**：A5 不接 diff、`impact_service` 不接 API 持久化、回归 scope 不读影响结果；测试最好的一层（AUD-017）全部是 helper 直调，且没有一条负向场景（纯重命名、删除 API、改鉴权中间件、无 baseline）。

## 5.5 最小整改建议（不含补丁）

1. `app/aiqe/agents/change_impact_agent.py`：删除 `AREA_RULES` 关键词判定作为**结论来源**；`analyze()` 改为接收 `ImpactPlan`（由 `impact_service.build_impact_plan()` 产出）作为唯一事实输入，LLM 只能在 mandatory 之外**追加**候选（沿用 `merge_ai_plan` 守卫）；把 `_expected` 改为显式入参（`validate(data, *, expected_impact)`），**禁止依赖实例可变状态**，从根上修 G14-2。
2. `app/aiqe/services/impact_service.py`：
   - `load_git_diff()` 强制 40 位 SHA；`ImpactPlan` 增 `algorithm_version/rule_version/diff_hash/result_checksum` 并在 `payload()` 返回；`build_impact_plan()` 落 `diff_digest()`。
   - 分类改为规格 6 类（`DIRECT/TRANSITIVE/CONTRACT/DATA/UI/RISK`），每条 relation 携带 `evidence_kind`（`AST_SYMBOL/ROUTE/OPENAPI_OP/MIGRATION_TABLE/DEP_GRAPH`）与**逐条** `trace_path`（不得复用 `components[0]`）。
   - 未知扩展名/生成代码/动态路由/空 diff → `impact_status="UNKNOWN"` + 强制 `mandatory` 扩大（如全 P0 + 全 auth/smoke），**不得**返回空集。
3. `app/api/v1/aiqe_insights.py`：`/impact/plan` 改为**创建持久化影响计划**（`impact_plans` 表 + `persist_edges` + version），返回 `impact_plan_id`。
4. `regression_service.create_regression_request()`：接收 `impact_plan_id`，把 `mandatory_case_ids` 并入强制集合；人工只能追加，缩小需审批记录（与 V16-008 联动）。
5. **必须新增的负向测试**（`tests/aiqe/test_v16_014_change_impact.py`）：
   - (a) API 传 7 位 SHA → 422；base/head 非 SHA → 422；
   - (b) 变更集含 `alembic/versions/*` + `app/api/v1/*` + 共享 `app/services/*`（真实临时 repo）→ 断言 `DIRECT/CONTRACT/DATA` 分类、每条 relation 有 `evidence_kind` 与独立 trace_path；
   - (c) 纯重命名（文件改名、内容不变）→ 不得产出“新增影响域”误导结论（或标 UNKNOWN）；
   - (d) 删除 API 路由 → `CONTRACT` 影响 + 相关 Case 进入 mandatory；
   - (e) 修改鉴权中间件 → `RISK/DIRECT` + forced auth-suite；
   - (f) 未知扩展名（`.proto`/生成文件）→ `UNKNOWN` 且 mandatory 扩大，**不得** 空集；
   - (g) 经 Agent Adapter 执行 A5 并漏选 forced suite → 必须报错（覆盖 G14-2）；
   - (h) 回归 API 传 `impact_plan_id` → 影响 Case 出现在回归 mandatory；无审批的缩小请求 → 拒绝。

## 5.6 复核命令

```powershell
$B = "F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6\test-platform-v2\backend"
rg -n "AREA_RULES|def compute_impact|self\._expected|def validate" "$B\app\aiqe\agents\change_impact_agent.py"
rg -n "def collect_changes|def build_impact_plan|diff_digest|persist_edges|trace_component" "$B\app\aiqe\services\impact_service.py"
rg -n "impact_service|persist_edges|diff_digest" "$B\app\api\v1\aiqe_insights.py" "$B\app\aiqe\services\regression_service.py"
rg -n "TRANSITIVE|RISK|EVIDENCE" "$B\app\aiqe"
rg -n "base_sha|head_sha" "$B\app\aiqe\agents"
```

---

# 6. V16-019：Agent Tool Registry 真实绑定、权限和审计

## 6.1 实施要求 6 条 → 状态对照

| # | 规格要求（L692–L697） | 状态 | 关键证据 |
|---|---|---|---|
| 1 | 注册项含 tool_name/version/implementation_ref/input_schema/output_schema/permission_scope/project_scope/side_effect_level/idempotent/timeout/rate_limit/requires_human_approval/secret_access_policy | **MISSING** | `ToolRegistry.__init__(allowlist, tools: Mapping[str, Callable])` 只有两个字段（`agents/protocol.py:52-61`）；`tools` 值是**裸 callable**，无任何元数据类/表/常量（`rg -n "side_effect\|permission_scope\|requires_human_approval\|secret_access" app/aiqe/agents` 0 命中） |
| 2 | 启动时校验 allowlist 每个可用工具都有实现；缺失标 `UNAVAILABLE`，Plan 不得当作可用 | **MISSING** | 无启动校验；`resolve()` 只在**运行时**抛 `ToolNotAllowed("... 未注册实现")`（`:69-72`）；无 `UNAVAILABLE` 概念（`:19-30` 只有 Agent 状态）；`build_tool_registry()` 默认空（`registry.py:104-110`）→ 所有工具均“可用名字、无实现” |
| 3 | 按只读/可写/外部副作用分级；生产默认只开只读，写需审批 | **MISSING** | 只有 `FORBIDDEN_TOOLS` 黑名单（`registry.py:60-70`）+ 名字级 allowlist（`:45-57`）；无分级、无环境开关、无写审批 |
| 4 | 工具参数 schema validate，拒绝额外字段和隐式扩权字段 | **MISSING** | `resolve()` 直接返回 callable（`protocol.py:66-72`），**无参数校验、无调用包装**；全仓无 `jsonschema` 校验接入 Agent |
| 5 | 工具结果经 SecretSanitizer + Evidence Artifact 管道 | **MISSING** | 无工具调用 → 无结果管道；`evidence_redactor`/`artifact_service` 未被任何 Agent 路径引用（`rg -n "evidence_redactor\|artifact_service" app/aiqe/agents` 0 命中） |
| 6 | 记录调用人、Agent、task、tool version、参数摘要、授权 decision、结果摘要、耗时、成本、evidence refs | **MISSING** | 无 `ToolExecution` 模型/表/事件（`rg -n "ToolExecution" app/` 0 命中）；`AgentExecution.tool_calls_json` 只是**回填**（`orchestrator.py:230`），来源是 `AgentResult.tool_calls`，而所有 Agent 都不产生该字段（全仓 Agent 实现中 `tool_calls` 0 赋值） |

## 6.2 代码证据（可复核）

| 证据 | 位置 | 说明 |
|---|---|---|
| R1 | `agents/protocol.py:52-72` | 完整 `ToolRegistry` 实现（19 行）：allowlist 查询 + tools dict 查询 + 2 类拒绝 |
| R2 | `agents/registry.py:104-110` | `build_tool_registry(tools=None)` → `ToolRegistry(allowlist, tools or {})` → **默认空实现表**（规格审计来源所述问题原样保留） |
| R3 | `agents/orchestrator.py:273` | `run_plan()` 默认 `tools or build_tool_registry()` → 空表；只在 test `test_aiqe_aud013_agent_protocol.py:120` 传入 1 个 lambda |
| R4 | `agents/registry.py:45-57` | `DEFAULT_TOOL_ALLOWLIST` 12 个名字（read_*/create_*），**全部无实现**；仅作为 Plan 的 `allowed_tools` 文本 |
| R5 | `agents/registry.py:60-70,95-101` | `FORBIDDEN_TOOLS` 只在 `assert_child_allowed()` 中被检查（且是把**子 Agent 名**与工具名比较，语义错位） |
| R6 | `agents/orchestrator.py:230` | `tool_calls_json=(list(result.tool_calls) if result else [])` —— 恒空列表 |
| R7 | `agents/protocol.py:104-116` | `AgentResult.validate()` 不校验 `tool_calls` 与 allowlist 的一致性（可伪造 tool_calls 而不被发现） |
| R8 | `tests/test_aiqe_aud013_agent_protocol.py:119-128` | 唯一 tool 测试：断言“允许但未注册实现 → 仍 fail closed”（**恰好证明 R1/R2 的现状被当作正确行为**） |

## 6.3 Gaps（每条可验证）

| ID | Gap | 验证方式 |
|---|---|---|
| **G19-1** | 工具实现表默认为空：`build_tool_registry()` 无参调用即得“0 实现”，与规格“allowlist 名称不等于实现存在”的要求**方向相反**地停留在 v1.5 状态 | R2+R3 |
| **G19-2** | 注册元数据 12 项全缺（无数据结构、无校验、无版本） | R1；`rg` 证据见 6.1#1 |
| **G19-3** | 无启动期/计划期校验：`UNAVAILABLE` 不存在，Plan 仍把 `read_git_diff` 等列入 `allowed_tools` 并视为可用 | R4；`AgentTask.validate()` 只校验名字是否在 allowlist（`orchestrator.py:78-81`） |
| **G19-4** | 无参数 schema 校验与“额外字段/隐式扩权”拒绝 | `protocol.py:66-72` 直接返回 callable |
| **G19-5** | 无 ToolExecution 审计（调用人/Agent/task/tool_version/授权决策/参数摘要/结果摘要/耗时/成本/evidence refs） | R6+R7；规格 §9.6 L1081 |
| **G19-6** | 无副作用分级/生产只读默认/写审批；`FORBIDDEN_TOOLS` 的语义被误用为“子 Agent 名黑名单” | R5（`registry.py:100` 比较的是 `child`） |
| **G19-7** | 工具结果无 SecretSanitizer/Artifact 管道；`AgentResult.tool_calls` 可被任意伪造且不被校验 | R7 |
| **G19-8** | Agent 实际不调工具：`context.tools` 只是透传对象，全仓无 `context.tools.resolve(...)` 调用点 | `rg -n "\.resolve\(" app/aiqe` 0 命中（除定义） |

## 6.4 测试现状与入口质量

| 测试 | 入口 | 真实性 | 能证明 | 不能证明 |
|---|---|---|---|---|
| `tests/test_aiqe_aud013_agent_protocol.py::test_tool_allowlist_denies_unlisted_tools`（L119-128） | 直调 `build_tool_registry`/`resolve` | 真实（纯内存） | 未列工具/受保护工具/未注册实现 → `ToolNotAllowed` | 注册元数据、UNAVAILABLE、参数校验、审计、真实工具 |
| `tests/test_aiqe_aud013_agent_protocol.py::test_run_plan_serial_execution_persists_traceability`（L180-217） | 直调 `run_plan`（fake executor，**手工塞 `tool_calls=[{"tool":"read_requirements"}]`**） | **伪造 tool_calls** | 证明 `tool_calls_json` 字段能存 | 工具是否真实执行/是否授权；反而固化了“可伪造 tool_calls” |
| 全仓 | — | — | 无 ToolExecution、无参数 schema、无 UNAVAILABLE 测试 | 规格验收 6 条全部无覆盖 |

**入口质量结论**：V16-019 **没有任何真实入口测试**；唯一相关测试把“未注册实现 fail closed”当作正确行为，而规格要求的是“启动时发现缺失 → 标 UNAVAILABLE 且 Plan 不可用”，两者结论相反（前者静默运行时拒绝，后者要求计划期可见）。

## 6.5 最小整改建议（不含补丁）

1. 新增 `app/aiqe/agents/tools.py`（或 `app/aiqe/models/tool.py` + 迁移）：
   - `ToolSpec` dataclass/表：`tool_name/version/implementation_ref/input_schema/output_schema/permission_scope/project_scope/side_effect_level(idempotent,timeout,rate_limit)/requires_human_approval/secret_access_policy/status(REGISTERED|AVAILABLE|UNAVAILABLE)`。
   - 启动函数 `assert_tools_available()`：对每个 allowlist 名字解析实现（`importlib` from `implementation_ref`），缺失 → `UNAVAILABLE` 并写进程日志/健康端点；`AgentPlan` 构建时过滤掉 `UNAVAILABLE`（`AgentTask.validate()` 增加该判定）。
2. `app/aiqe/agents/protocol.py`：`ToolRegistry.resolve()` 返回**包装器** `invoke(agent_key, context, params, *, approval_token=None)`：
   - `jsonschema.validate(params, spec.input_schema, additionalProperties=False)`；
   - 校验 `project_scope`（必须包含 `context.project_id`）与 `permission_scope`（按 `actor_id` 的 RBAC）；
   - 只读/可写/外部副作用分级：非只读且 `requires_human_approval` 时必须有 `approval_token`（否则 `ToolNotAllowed("HUMAN_APPROVAL_REQUIRED")`）；
   - 超时（per-spec）、幂等键（`context.idempotency_key + tool_name + params_hash`）与 rate limit；
   - 结果过 `evidence_redactor`/`SecretSanitizer`，落 `ToolExecution` + Artifact。
3. `app/aiqe/models/agent.py`：新增 `ToolExecution`（规格 §9.6 L1081 九列）+ `AgentExecution.tool_calls_json` 改为由 `ToolExecution` 派生（禁止 Agent 自报）。
4. `app/aiqe/agents/orchestrator.py`：`run_plan()` 传入**已注册**的 registry（从启动单例注入），禁止 `tools or build_tool_registry()` 的空表兜底（应 fail-closed 抛 `TOOLSET_UNAVAILABLE`）。
5. **必须新增的负向测试**（`tests/aiqe/test_v16_019_tool_registry.py`）：
   - (a) allowlist 中某工具无实现 → `assert_tools_available()` 标 `UNAVAILABLE`，构建含该工具的 Plan → 400/`TOOLSET_UNAVAILABLE`；
   - (b) 工具不存在 → 拒绝；跨项目调用（`context.project_id` 不在 `project_scope`）→ 拒绝；
   - (c) 参数多传字段/漏必填 → `SchemaError`，且**未产生** ToolExecution；
   - (d) 写工具无 `approval_token` → `HUMAN_APPROVAL_REQUIRED`；带无效 token → 拒绝；
   - (e) 超时工具 → `TOOL_TIMEOUT`，不产生成功 ToolExecution；
   - (f) 同一幂等键重复调用只产生 1 条 ToolExecution + 1 个 Artifact；
   - (g) 成功调用后 `ToolExecution` 含 tool_version/agent_key/task_id/authorization_decision/input_summary/output_ref/duration_ms/evidence_refs；
   - (h) 回归守卫：`AgentResult.tool_calls` 与 `ToolExecution` 不一致 → 落库校验失败。

## 6.6 复核命令

```powershell
$B = "F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6\test-platform-v2\backend"
rg -n -A20 "class ToolRegistry" "$B\app\aiqe\agents\protocol.py"
rg -n "def build_tool_registry|return ToolRegistry|DEFAULT_TOOL_ALLOWLIST|FORBIDDEN_TOOLS" "$B\app\aiqe\agents\registry.py"
rg -n "tool_calls" "$B\app\aiqe\agents" "$B\app\aiqe\models\agent.py"
rg -n "ToolExecution|UNAVAILABLE|side_effect|permission_scope|requires_human_approval" "$B\app\aiqe"
rg -n "\.resolve\(" "$B\app\aiqe"
```

---

# 7. 横切结论（跨 Issue）

## 7.1 发现的三类“伪造/降级”行为（规格 §0.2.8、L1207 明令禁止）

| 类型 | 位置 | 具体表现 |
|---|---|---|
| **伪造状态跃迁** | `learning_service.py:94`、`:115`、`:145` | `evaluate` 无条件 `status="benchmarked"`；`approve` 无条件 `acknowledged=True`（无审批人）；`activate` 直写 `BugPattern.status="active"`（无发布记录/版本） |
| **证据校验降级通过** | `failure_triage_agent.py:112,150-152` + `protocol.py:180` + `base.py:56-57` | resolver 默认 None 时**整段校验跳过**；Adapter 从不传 resolver；resolver 返回值被丢弃 |
| **执行状态自报** | `scripts/qa/aiqe_m3_m5_gate.py:45-58`；`orchestrator_agent.py:57` vs `:63` | Gate 脚本手写 `AgentExecution(status="succeeded")`；A0 输出 `a0_state="QUEUED"` 但协议 status=`COMPLETED` |

## 7.2 结构性缺口（比单点 bug 更关键）

1. **Agent 协议与执行器之间存在“最后一公里”断裂**：`BaseAgentAdapter.execute()` 丢弃 `AgentContext`（tools/resolver/run_id），导致 `run_plan()` 精心透传的 resolver/tool_registry 对 A1–A5 **完全无效**（仅 A6 自行实现 `execute` 才用到 resolver）。→ 修 V16-012/013/019 必须先修这一处（`protocol.py:177-215`）。
2. **Plan/Draft 全是内存对象**：`AgentTask`/`AgentPlan`/`PlanRunResult` 均为 dataclass（`orchestrator.py:58-116,182-199`），无持久化，因此审批、恢复、审计、重试全部无从谈起。
3. **凡是“Agent 输出”都在绕过校验**：A5 的 `_expected`（`change_impact_agent.py:88`）依赖实例状态，Adapter 路径必为空；A4 的 resolver（`:150`）依赖可选参数，Adapter 路径必为 None。**同一模式出现两次**，根因是 `BaseAgent.run(input_text)` 无上下文。
4. **证据链依赖“调用方自觉”**：`run_llm_benchmark(project_id=...)` 是唯一做了 project 校验的 benchmark 入口，其余入口是否安全取决于调用方是否记得传参；`persist_edges()`/`diff_digest()`/`compare_with_baseline()` 三个关键治理函数**全部只有测试调用**（死代码）。
5. **历史证据不可采信**：`work-logs/aiqe/v1.4-m3-m6-gates-20261115.md:19-20,60` 的 A6 PASS 来自自报指标脚本（`scripts/qa/aiqe_m3_m5_gate.py:233-238`），该脚本在当前代码下会直接抛 `BenchmarkError`；`docs/aiqe/aud-baseline-v15.md:191` 亦自认“剩余：把 `run_plan` 暴露为 REST/MCP 工具”。

## 7.3 与其他审计组的分工交叉

- **V16-008/V16-020（G5）**：本报告的 G14-4（A5 不进回归 Scope）与 G5 的 G8-6 同一根因；建议在追踪矩阵中合并为一个整改项（`impact_plan_id` → `regression.mandatory`）。
- **V16-007/V16-009（G5）**：A5/A6 的“证据”最终要落 Assertion/Artifact，本组任何修复都不得新建第二套证据管道（规格 L76）。
- **V16-025（治理）**：本组 6 个 Issue 在 `docs/aiqe/v1.6/` 下**没有追踪矩阵文件**（`docs/aiqe/v1.6/V1.6-Requirement-Code-Test-Evidence-Matrix.md` 不存在），违反规格 L63“矩阵必须随 PR 增量更新”。

---

# 8. 逐 Issue 摘要（可直接进追踪矩阵）

| Issue | 状态 | 已 IMPLEMENTED 的子项 | 必须补齐的阻断项 |
|---|---|---|---|
| V16-010 | PARTIAL | 后端算指标（`benchmark_service.py:92-144,334-338`）；API 拒绝自报（`aiqe_learning.py:38-40` + 测试） | PASS_GATE/gate_eligible/样本数/全阈值/baseline/checksum/版本/审批人 8 条批准条件；`approved_*` 字段；publish/revoke/rollback |
| V16-011 | PARTIAL | 认证上下文 project（`deps.py:42,83,88-117`）；`run_llm_benchmark` project 校验（`benchmark_service.py:450-451`）；候选 create/get/list 过滤 | 6 个 benchmark 服务函数 + 4 个 API + `BugPattern`/`evaluate` 的 project 强制；模型非空 FK 与复合唯一键 |
| V16-012 | PARTIAL | 现成 resolver（`evidence_service.py:210-248`）；A4 安全字段（human_review/auto_close/confidence null）；A6 的 resolver 用法可参考（`learning_curator_agent.py:104-119`） | Protocol/Adapter 传 context；A4 resolver 必填 + 返回值消费 + 空/异常拒绝；`INVALID_EVIDENCE`；A4 正式入口 |
| V16-013 | PARTIAL | `AgentExecution` 可追溯（`models/agent.py:18-55` + `_persist_execution`）；`run_plan` DAG/幂等/依赖取消/WAITING_HUMAN | `AgentTask`/`AgentStepExecution`/`ToolExecution`；approve/run/cancel/retry 端点；`run_plan` 接 Job；超时/重试/审批点 |
| V16-014 | PARTIAL | `impact_service` 真实 diff/AST/route/migration（`impact_service.py:100-216`）；AI 不可删强制（`:363-368`） | A5 去掉关键词、接 `ImpactPlan`；6 类分类 + 逐条证据；`impact_plan_id` 入回归 Scope；diff_hash/version/checksum 落库；UNKNOWN 扩大回归 |
| V16-019 | MISSING | allowlist + 未注册实现 fail-closed（`protocol.py:63-72`，测试 `:119-128`） | ToolSpec 12 项元数据；启动校验 + UNAVAILABLE；参数 schema；分级/审批；ToolExecution 审计；结果脱敏/Artifact |

---

# 9. 附：可直接复用的既有资产（整改加速）

| 资产 | 位置 | 可复用点 |
|---|---|---|
| 证据解析器 | `app/aiqe/services/evidence_service.py:210-248` | A4 的 resolver 直接 `lambda refs: resolve_evidence_refs(db, project_id=..., run_id=..., refs=refs)` |
| Agent 结果协议 | `app/aiqe/agents/protocol.py:86-136` | `AgentResult.validate()` 已强制 COMPLETED 非空输出/needs_human 一致性，可作为 V16-013 执行记录校验基础 |
| 事件/Outbox | `app/aiqe/services/event_service.py:44,101,123-139` | Agent approval/run/tool 事件可复用 outbox（注意 G5 报告已指出 outbox 无 relay，需先补消费者） |
| Artifact 脱敏管道 | `app/aiqe/services/artifact_service.py`、`evidence_redactor.py` | V16-019 工具结果脱敏 |
| 变更影响服务 | `app/aiqe/services/impact_service.py` | V16-014 的唯一应保留的“事实来源” |
| 基准服务 | `app/aiqe/services/benchmark_service.py` | V16-010 的指标与 `result_status` 计算已正确，只需把 gate 判定搬进 approve |

---

*本报告为只读审计结论；除本文件外未修改工作树任何文件，未执行 pytest/迁移/脚本。所有行号基于 `HEAD = 09140401f` 且对应文件经 `git status` 验证无在途改动。*
