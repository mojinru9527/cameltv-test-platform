# G5 独立审计报告 — Mandatory Scope / Assertion Engine / Workflow Validator / Quality Gate / Terminal Handler / Comparison Snapshot

> **STATUS: HISTORICAL** — 本文记录 2026-11-2x 当时的执行事实与结论；其中 PASS/VERIFIED 等表述不代表当前发布判定。当前状态以 `release-verdict.json`、`E2E-Coverage-and-Blockers.md` 与 `governance/production-evidence.json` 为准。


| 项目 | 内容 |
|---|---|
| 审计 Issue | **V16-008**（Mandatory Scope 真正生效）、**V16-009**（Assertion 与 PASS 语义）、**V16-020**（统一终态与 Comparison Snapshot） |
| 审计角色 | 独立代码审计员（只读；未修改任何业务文件；唯一写入是本报告） |
| 审计对象 | `F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6`（分支 `release/aiqe-v1-6`） |
| 基线 | `HEAD = 86a44b2cb`（= `origin/main`）+ 未提交在途 V16-001 改动（审计期间仍在被并发写入，见 §0.2） |
| 规格 | `C:\Users\26029\Downloads\CamelTv_AIQE_V1.6_修复与生产化开发实施计划.md` |
| 审计时间 | 2026-11-19 19:00–19:40 (+08:00) |
| 方法 | 只读走查 `test-platform-v2/backend`、`scripts/`、`.github/workflows/`、alembic 迁移；**未执行 pytest**（只读审计，避免在工作树生成 DB/缓存），全部结论可用 §6 命令复核 |

---

## 0. 结论总表

| Issue | 状态 | 一句话结论 |
|---|---|---|
| **V16-008** | **PARTIAL** | `build_mandatory_scope()` 已从“死代码”变为“被调用并落库”，但仍只是**记录**而非**执行**：强制集合不参与终态/门禁判定；客户端可用 `scope=SELECTED` 把强制集合缩成空；回归 Run 不派发 Job、不复制节点断言、永不到终态。规格 6 条实施要求中只有“40 位 SHA / 部署证明绑定”与“确定性幂等指纹”达到 IMPLEMENTED。 |
| **V16-009** | **PARTIAL** | 断言引擎与 Runtime 的“局部零件”基本齐备（Driver 200 但业务 JSON 错 → FAIL，已从真实 Worker 入口验证），但 **PASS 语义的核心不变量不成立**：无断言节点直接 `PASSED`（`execution_service.py:466-468`），Run 可零业务 Oracle 判 `PASS`；业务节点类别、`required`、`evidence_required`、Quality Gate 与 Run Outcome 同集合四条均缺失。 |
| **V16-020** | **PARTIAL** | 终态处理器/对比快照存在且幂等（`completed_at` 去重）、不自动关缺陷；但 **“仅真实终态 Run 可生成对比结论”被直接违反**：`handle_run_terminal()` 不校验 Run 终态，`GET /comparison` 是读路径写库入口，非终态 Run 会被立刻固化成 `UNKNOWN` 结论并写 `completed_at`；同时存在 4 套终态计算、outbox 消费者零生产调用点。 |

**状态定义**：按规格 §0.2.4 —— `IMPLEMENTED`（代码落地≠验收通过）/`PARTIAL`/`MISSING`。本报告不使用 `VERIFIED`/`ACCEPTED`（无 Runtime E2E 证据）。

---

## 0.1 规格章节定位（含 V16-020 规格缺口）

| Issue | 规格位置 | 说明 |
|---|---|---|
| V16-008 | 正文 §V16-008（规格 L494–L513）+ 总表 L180 | 有独立章节：6 条实施要求 + 4 条验收 |
| V16-009 | 正文 §V16-009（规格 L515–L547）+ 总表 L181 | 有独立章节：节点类别 / 断言结构 / 结果规则 / 4 条验收 |
| V16-020 | **仅**总表 L192、TC-AIQE-008 断言 L839、Gate C L1148–L1155、Sprint 5 L1096 | **规格没有 V16-020 独立章节**；可验收口径必须从以上 4 处推导。本报告据此把验收拆为：(a) 只有真实终态 Run 才能产出对比结论；(b) 终态计算唯一；(c) 对比快照引用真实 Assertion/Artifact；(d) Gate C“Run Outcome、Quality Gate、Regression Outcome 语义一致”。**建议 Lead 在追踪矩阵中补齐 V16-020 的验收口径，否则该项无法被客观判定。** |

---

## 0.2 基线与工作树漂移（复核前提）

1. 审计起点 `git -C <worktree> rev-parse HEAD` = `86a44b2cb…`（= `origin/main`）；审计期间并发提交 `09140401f`（仅 V16-001 相关 + 各审计报告文件），见第 2 条。
2. 审计开始时工作树有 17 个 `M` 文件（V16-001 在途改动）；审计期间又新增：
   - `test-platform-v2/backend/app/aiqe/services/run_launch.py` 被并发修改（新增 `WORKFLOW_NEEDS_POLICY_REVIEW` 抛错，+6 行，位于原 L122 之后）；
   - 新增未跟踪文件 `alembic/versions/20261119_v16_001_policy_status.py`、`scripts/aiqe/migrate_workflow_target_policy.py`、`tests/test_aiqe_v16_001_policy_fail_closed.py`。
   - 19:12 左右这批在途改动被并发提交为 **`09140401f`（feat(aiqe-v16): V16-001 删除 HTTP/DB fail-open…）**；`git diff --name-only 86a44b2cb 09140401f` 显示，本报告引用的核心文件中**只有 `run_launch.py` 变化**，其余行号在 `86a44b2cb` 与 `09140401f` 之间完全一致。
3. **本报告引用的核心文件均未被在途改动触及**（`git status --porcelain -- <files>` 为空，唯一例外 `run_launch.py`）：
   `regression_service.py`、`regression_terminal.py`、`workflow_validator.py`、`result_writer.py`、`dag_scheduler.py`、`quality_gate.py`、`quality_gate_service.py`、`assertion_service.py`、`assertions/engine.py`、`reconciler.py`、`api/v1/aiqe_regressions.py`、`api/v1/aiqe_automation.py`、`api/v1/defect.py`、`models/defect.py`、`models/deployment.py`。
4. `run_launch.py` 行号以 **19:2x 当前工作树**为准（`validate_workflow` L138、`preflight_graph` L204、`TestRun(...)` L212、`apply_transition(QUEUED)` L258、`enqueue_node_run` L266、`dag_scheduler.schedule` L284、`apply_transition(RUNNING)` L292）；其余文件行号与 HEAD 一致。
5. 按 `alembic/versions/*.py` 的 `revision/down_revision` 解析，当前为**单头** `20261119_v16_001_policy_status`（该文件已随 `09140401f` 提交；未执行 `alembic heads` 实测）；`defect_regressions` / `aiqe_deployment_attestations` / `run_comparison_snapshots` 由 `alembic/versions/20261124_aud009_regression_hardening.py` 建立，迁移本身可重复执行（`upgrade()` 先 inspect 再 add/drop，L43–L123），SQLite 下 downgrade 为空操作（L127–L129）。

---

# 1. V16-008：Defect Regression Mandatory Scope 真正执行

## 1.1 规格要求 → 状态对照

| # | 规格要求（L498–L506） | 状态 | 关键证据 |
|---|---|---|---|
| 1 | Mandatory Scope 由服务端根据 Defect、修复 commit、Impact Analysis、历史缺陷映射、风险策略计算 | **PARTIAL** | `build_mandatory_scope()` 存在并被调用（`regression_service.py:157-179`、`:263-266`），但输入只有 **source Run 的失败节点/断言** + `selected_case_ids` 中 `P0` 前缀；不读 Defect 严重度、不读 A5 `impact_service`、无历史缺陷映射、无风险策略 |
| 2 | Scope 记录 `scope_id`、规则版本、输入证据 refs、必测 Case/Node、原因、审批人、checksum | **PARTIAL** | 有 `scope`/`scope_hash`/`mandatory_case_ids_json`/`selected_case_ids_json`/`excluded_json`（含 reason）/`reason`（`models/defect.py:134-139`，迁移 `20261124_aud009_regression_hardening.py:24-29`）；**无 `scope_id`、无规则版本、无输入证据 refs、无审批人**（全仓 `scope_id` 0 命中） |
| 3 | Regression Launch 必须接收 scope snapshot；Cloner 只允许排除非 mandatory 节点 | **MISSING** | 回归链路**未接入**唯一 Launch 服务 `run_launch.launch_run()`，而是直接 `TestRun(status="QUEUED")`（`regression_service.py:344-376`）；不存在 `SnapshotCloner`（全仓 0 命中）；克隆由 `_replicate_nodes()` 临时实现（`:204-227`），既不接收 mandatory/excluded 参数，也不存在“排除”逻辑 |
| 4 | 必测节点无法执行时必须 BLOCKED，不能缩小范围后 PASS | **MISSING** | 终态聚合与门禁都不读 `mandatory_*`；无 `MANDATORY_*` 错误码（全仓 0 命中）；`aggregate_regression_status()`（`regression_terminal.py:74-118`）只看 assertion 状态与 `run.outcome` |
| 5 | 支持 `MANDATORY + RELATED + SMOKE` 三类集合，分别报告；门禁要求 Mandatory 全部完成且断言通过 | **MISSING** | `SCOPES` 只有 `DIRECT_FAILURES / DIRECT_FAILURES_PLUS_P0 / DIRECT_FAILURES_PLUS_P0_PLUS_IMPACT / SELECTED`（`regression_service.py:38-45`）；无三集合模型、无分类上报；Quality Gate 完全不读 mandatory（`quality_gate_service.py` 全文） |
| 6 | 修复版本绑定 40 位 SHA、构建产物 digest、部署环境 ID、部署证明、workflow snapshot hash；禁止 SHA 前缀 | **PARTIAL** | 40 位 SHA 强校验 IMPLEMENTED（`regression_service.py:36,58-62`）；部署证明来自 `aiqe_deployment_attestations` 且只读（`:97-108`、`:269-288`）；**digest / evidence_ref 未绑定到回归记录**（`DefectRegression` 无 image_digest/attestation_id 列）；`workflow_checksum` 只存 WorkflowDefinition checksum（`:182-201`），未绑定任何 snapshot hash；**旧 API 仍接受 7 位 SHA**（见 G8-8） |
| 7 | 幂等 key = 确定性 hash（project+defect+full SHA+snapshot+scope+environment+policy version） | **PARTIAL** | `_fingerprint()` 为确定性 sha256（`:65-86`），含 project/defect/SHA/deployed_sha/env/workflow_checksum/scope_hash；`idempotency_fingerprint` 有唯一约束（`models/defect.py:125-127`，迁移 L55–L61）；**缺 policy version**；并发插入无 `IntegrityError` 处理（`:302-339`） |

验收（L508–L513）逐条：

| 验收项 | 结果 | 证据 |
|---|---|---|
| Mandatory 不可删除/skip；模拟 Driver 缺失应 BLOCKED | **不成立** | 强制集合仅在 DB/API 回显；Driver 缺失走 `PREFLIGHT_BLOCKED`/`CAPABILITY_UNAVAILABLE` 的另一条链，回归 Run 根本不调度（G8-4） |
| 同一输入重复请求只创建一个 regression execution | **部分成立** | 串行重复 ✓（`test_aiqe_regression_api.py:194-206`）；并发未覆盖、未处理唯一约束冲突（G8-9） |
| 同一缺陷不同 commit/环境创建不同 Run | **成立（代码层）** | fingerprint 含 `fixed_sha`/`environment_id`（`:75-86`）；但**无对应测试**（只测了不同 scope） |
| 40 位 SHA 不匹配、部署证明过期、snapshot hash 不同均拒绝比较 | **不成立** | SHA/部署不匹配在**创建期**阻断 ✓；**部署证明无过期语义**（`models/deployment.py:17-47` 无 `expires_at`）；对比阶段不校验 snapshot hash（G20-5） |

## 1.2 代码证据（可复核）

| 证据 | 位置 | 说明 |
|---|---|---|
| E1 | `app/aiqe/services/regression_service.py:157-179` | `build_mandatory_scope()`：失败节点/断言 + `P0` 前缀；`SELECTED` 分支把入参原样作为强制集合 |
| E2 | `app/aiqe/services/regression_service.py:263-266` | 唯一调用点：计算 `mandatory/excluded` 与 `scope_hash`，随后写入指纹 |
| E3 | `app/aiqe/services/regression_service.py:328,368,391` | mandatory 只落到 `DefectRegression.mandatory_case_ids_json`、`TestRun.environment_snapshot_json.mandatory_case_ids`、`regression.created` 事件的 payload |
| E4 | `app/api/v1/aiqe_regressions.py:83` | 唯一读取点：API 回显 `mandatory_case_ids`（**只读展示**） |
| E5 | `app/aiqe/services/regression_service.py:204-227` | `_replicate_nodes()`：graph 节点仅含 `key/driver/input/depends_on=[]`，`edges=[]`；**不复制 `assertions`/`outputs`/`capability`** |
| E6 | `app/aiqe/services/dag_scheduler.py:119-130` | `create_node_runs()` 从 graph 节点读取 `assertions`；因 E5 未传 → 回归节点 `assertions_json=[]` |
| E7 | `app/aiqe/services/regression_service.py:344-376` | 直接 `TestRun(status="QUEUED")`，只 `db.add/flush`，无 `launch_run`、无 `preflight_graph`、无 `enqueue_node_run`、无 `dag_scheduler.schedule` |
| E8 | `app/aiqe/services/reconciler.py:150-157` | Reconciler 只扫描 `TestRun.status == "RUNNING"`；QUEUED 回归 Run 不在处理范围 |
| E9 | `app/aiqe/services/run_launch.py:204,212,258,266,284,292` | 唯一正式 Launch：`preflight_graph` → `TestRun` → QUEUED → schedule+dispatch → RUNNING；回归链路完全绕过 |
| E10 | `app/api/v1/defect.py:330-358` + `app/services/defect_service.py:688-711` | 旧 API `POST /api/v1/defects/{id}/regressions`：`len(sha) >= 7` 即通过，`verification_run_id` 任意填，`status="passed"` 直接置成功（G8-8） |
| E11 | `app/services/defect_service.py:714-732` | 第二套对比实现 `compare_runs()`（纯函数），与 `regression_terminal.build_comparison_snapshot()` 并存 |
| E12 | `app/aiqe/models/deployment.py:17-47` | 部署证明无 `expires_at`/无状态、无撤销；`resolve_deployed_sha()` 取最新一条，不判时效（`regression_service.py:100-108`） |

## 1.3 Gaps（每条可验证）

| ID | Gap | 验证方式 |
|---|---|---|
| **G8-1** | Mandatory 只“记录”不“执行”：终态聚合、Quality Gate、对比快照三处都不读 `mandatory_case_ids_json`；不存在“mandatory 未完成 → BLOCKED/FAIL”分支 | `rg -n "mandatory" app/aiqe/services/` 仅命中 `regression_service.py:89,157,263,328,368,391`（计算/落库）与 `aiqe_regressions.py:83`（回显） |
| **G8-2** | 强制集合可由客户端缩成空：`scope=SELECTED` + 空 `selected_case_ids` + 无 `source_run_id` → `mandatory=[]`，且无任何阻断（“必须有强制项”校验不存在） | `regression_service.py:169-171`；`create_regression_request()` L263–L288 只对部署证明加 blocker；API `RegressionRequestIn.scope/selected_case_ids`（`aiqe_regressions.py:46-53`） |
| **G8-3** | 克隆丢失节点断言/输出/capability：回归节点 100% 无业务断言，配合 G9-1 直接 `PASSED` | E5+E6；可在 `tests/test_aiqe_regression_api.py:188-189` 补断言 `nodes[0].assertions_json != []` 即红 |
| **G8-4** | 回归不走统一 Launch：无 ExecutionJob、无 preflight、`workflow_snapshot_json={}`、`workflow_checksum=""`、`preflight_json={}`；Run 永久停在 QUEUED | `rg -n "enqueue_node_run" app/aiqe` 仅 `run_launch.py:266` + `execution_service.py:547`；`regression_service.py` 全文无调用 |
| **G8-5** | Scope 契约字段缺失：无 `scope_id`、规则版本、输入证据 refs、审批人；也无 mandatory/related/smoke 集合语义 | `rg -n "scope_id|rule_version|approved_by" app/aiqe/services/regression_service.py`（0 命中）；`models/defect.py:124-141` |
| **G8-6** | 强制范围未纳入 A5 Impact：`impact_service` 产出的 `mandatory_case_ids`（`impact_service.py:65,272-302`）与回归 scope 完全不关联；回归 API/服务无 `impact_plan_id` 入参 | `rg -n "impact_service" app/aiqe/services/regression_service.py`（0 命中）；`RegressionRequestIn`（`aiqe_regressions.py:46-53`） |
| **G8-7** | 修复版本证据不完整：回归记录不含构建产物 digest、部署证明 ID/evidence_ref；对比也不校验部署证明时效 | E10 表 + E12；`DefectRegression` 字段清单（`models/defect.py:115-150`） |
| **G8-8** | **旧 API 旁路依旧开放**：`POST /api/v1/defects/{id}/regressions` 接受 ≥7 位 SHA、外部自报 `verification_run_id`，并把 `status` 直接写成 `passed` —— 完全跳过 40 位 SHA、部署证明、fingerprint 幂等、mandatory | `app/api/v1/defect.py:330-358`；`app/services/defect_service.py:699-707`；且 `tests/test_aiqe_defect_regression.py:17-29` 仍在断言该行为 |
| **G8-9** | 并发幂等未闭合：`select` 后再 `add`（check-then-act），两个并发同指纹请求会有一个触发唯一约束 `IntegrityError`（500），未捕获/未转成“返回既有记录” | `regression_service.py:302-339`；迁移唯一索引 `20261124_aud009_regression_hardening.py:55-61` |
| **G8-10** | 无“AI 不得删除强制项”的回归链路守卫：该守卫只存在于 `impact_service.merge_candidates()`（`impact_service.py:363-365`），不在回归创建/克隆路径 | `rg -n "removed_mandatory" app/` → 仅 `impact_service.py:363` |

## 1.4 测试现状与入口质量

| 测试 | 入口 | 真实性 | 能证明 | 不能证明 |
|---|---|---|---|---|
| `tests/test_aiqe_regression_api.py::test_short_sha_rejected`（L123） | **API** `POST /api/v1/aiqe/defects/{id}/regressions` | 真实 Service+DB，无 Mock | 7 位 SHA → 400 | — |
| `…::test_missing_attestation_blocks` / `test_deployed_sha_mismatch_blocks`（L132/L144） | API | 真实 | 部署证明缺失/不匹配 → BLOCKED | 部署证明过期（无该字段） |
| `…::test_create_regression_creates_verification_run`（L156） | API | 真实 | mandatory 列表含 `node:ui`/`assertion:live.entry`/`P0-login`，P2 有 excluded reason；旧 Run 不变 | **未断言回归节点是否继承断言**；未断言 Job 派发；未断言终态 |
| `…::test_fingerprint_idempotent` / `test_different_scope_creates_new_regression`（L194/L208） | API（串行两次调用） | 真实 | 串行幂等、不同 scope 新建 | 并发幂等；不同 SHA/环境 |
| `…::test_terminal_sync_pass_and_comparison` / `…fail…` / `…without_assertions_is_unknown`（L252/L290/L307） | **直调 helper** `handle_run_terminal`，且用 ORM 手工设置 `run.status/outcome`（L246-249） | 绕过 Worker/Outbox/API，**手工造终态** | 聚合规则分支：PASS→READY_FOR_HUMAN_CLOSE、FAIL→NEEDS_MORE_FIX、无断言→UNKNOWN、不自动关缺陷 | 终态是否真实、非终态调用行为、outbox 消费、`GET /comparison` 的读路径副作用 |
| `tests/test_aiqe_defect_regression.py`（全部 7 条） | 直调 `defect_service.create_regression/compare_runs` | 旧实现 | 旧语义（≥7 位 SHA、`status="passed"`） | 与 V16 要求相反的契约，却被 `scripts/aiqe/run_dogfood.ps1:24`（M4 组）当作回归证据 |
| `tests/e2e/aiqe/tc_aiqe_unblocked_verify.py::tc008`（L101-153） | HTTP（**compat 入口** `/api/v1/aiqe/regressions`） | 真实 HTTP + 服务层 | 只断言 `run.status == "QUEUED"`、`commit_sha == "abc1234def"`、`retest_of` | **反而是规格禁止的证据形态**：7 位 SHA + QUEUED 当成功；按当前代码 `normalize_sha` 会 400，该脚本已不是有效/可绿证据 |
| `tests/e2e/aiqe/tc_aiqe_service_acceptance.py::tc008`（L225-229） | 直接 `raise NotImplementedError` | — | — | 说明 TC-AIQE-008 从未 E2E 通过 |
| `tests/e2e/aiqe/test_tc_aiqe_001_010.py`（L58-63） | Playwright 打开 `/runs`，断言 `body.count()==1` | 页面打开 | 仅页面可加载 | 全部 10 个 TC 共用同一条 body 断言（0.2.8 明令禁止） |

**入口质量结论**：V16-008 的**创建期**契约有真实 API 入口测试；**执行期**（Job/Worker/终态/mandatory 覆盖）与**对比期**没有任何正式入口测试，唯一的 E2E 证据脚本自相矛盾且当前应为失败。

## 1.5 最小整改建议（不含补丁）

1. **`app/aiqe/services/regression_service.py`**
   - `build_mandatory_scope()`：改为服务端唯一计算入口（输入 Defect 严重度/commit diff/`impact_service` 计划/历史缺陷），返回结构化对象（`scope_id`、`rule_version`、`evidence_refs`、`mandatory/related/smoke` 三集合、`approved_by`、`checksum`）；**禁止客户端直接决定 scope 集合**，`SELECTED` 只能“扩大”，且必须与计算集合做包含校验。
   - 增加“强制集合非空”与“每类集合至少一个可执行映射（case→node）”阻断码（如 `MANDATORY_SCOPE_EMPTY` / `MANDATORY_UNMAPPED`）。
   - `create_regression_request()`：必须调用 `run_launch.launch_run()`（`graph_override` + `expected_checksum` + `source_type="regression"` + `priority/scope snapshot` 入参），禁止自建 `TestRun`；删除本地 `_replicate_nodes()`，改用 SnapshotCloner（V16-007）。
   - 并发幂等：捕获唯一约束冲突并返回既有记录。
2. **`app/aiqe/services/regression_terminal.py`**
   - 新增 `mandatory_coverage(run, regression)`：按 `mandatory_case_ids_json` 校验“已执行 + required 断言 PASS”，缺项 → `BLOCKED`/`FAIL`（不可 PASS），并写 `error_code=MANDATORY_NOT_VERIFIED`。
3. **`app/api/v1/defect.py` + `app/services/defect_service.py`**
   - 旧 `POST /defects/{id}/regressions` 改为 410/转发到 AIQE 回归入口；`create_regression()` 与 `compare_runs()` 删除或标记 legacy（不得可写）。
4. **`app/aiqe/models/defect.py` + 新迁移**
   - `DefectRegression` 补 `scope_id / scope_rule_version / scope_evidence_refs_json / approved_by / attestation_id / image_digest`；`aiqe_deployment_attestations` 补 `expires_at / revoked_at`，`resolve_deployed_sha()` 拒绝过期。
5. **必须新增的负向测试（正式入口）**
   - `tests/aiqe/test_v16_008_mandatory.py`
     - (a) API 创建回归（完整 40 位 SHA + 部署证明）→ 断言回归 Run 有 `ExecutionJob`（`ExecutionJob.run_id` 可查）且节点 `assertions_json` 与 source 节点一致（覆盖 G8-3/G8-4）。
     - (b) 客户端传 `scope=SELECTED` + 空 `selected_case_ids` + 有 source run → 仍包含全部失败节点；无 source run → 拒绝（覆盖 G8-2）。
     - (c) 强制节点对应 Driver 不可用（不 `register_manifest`）→ 经 `job_consumer.run_job()` 后节点 `BLOCKED`，回归 `status=BLOCKED`，**不得 PASS**（覆盖 G8-1/G8-4）。
     - (d) 强制节点断言 `NOT_EVALUATED`/证据缺失 → 回归不得 `PASS`（覆盖 G8-1）。
     - (e) 旧 API `POST /api/v1/defects/{id}/regressions` 传 7 位 SHA → 非 2xx（覆盖 G8-8）。
     - (f) 并发 2 个相同输入（线程/事务）→ 只 1 条 `DefectRegression`、1 个 Run，无 500（覆盖 G8-9）。
     - (g) 部署证明 `expires_at` 过期 → 创建/对比拒绝（覆盖 G8-7）。
   - 修改 `tests/test_aiqe_defect_regression.py`：删除/改写 7 位 SHA + `status="passed"` 断言（否则整改必红）。

## 1.6 复核命令

```powershell
$B = "F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6\test-platform-v2\backend"
# E1-E4 mandatory 只记录不执行
rg -n "mandatory" "$B\app\aiqe\services" "$B\app\api\v1\aiqe_regressions.py"
# E5-E6 克隆丢断言
rg -n -A14 "def _replicate_nodes" "$B\app\aiqe\services\regression_service.py"
rg -n -A14 "def create_node_runs" "$B\app\aiqe\services\dag_scheduler.py"
# E7/E9/E10 无统一 Launch / 无 Job
rg -n "launch_run\(|enqueue_node_run\(|dag_scheduler.schedule\(" "$B\app\aiqe\services\regression_service.py"
rg -n "status=\"QUEUED\"" "$B\app\aiqe\services\regression_service.py"
# E10/G8-8 旧 API 旁路
rg -n "def create_regression" "$B\app\api\v1\defect.py" "$B\app\services\defect_service.py"
rg -n "len\(sha\) < 7|status=\"pending\" if verification_run_id" "$B\app\services\defect_service.py"
# G8-1/G8-5/G8-6
rg -n "MANDATORY_" "$B\app"
rg -n "scope_id|impact_plan_id" "$B\app"
# 测试覆盖事实
rg -n "build_mandatory_scope" "$B\tests"
```

---

# 2. V16-009：Assertion Engine 与 Run PASS 语义重构

## 2.1 规格要求 → 状态对照

| 规格项（L519–L547） | 状态 | 关键证据 |
|---|---|---|
| **节点类别** BUSINESS / SETUP / CLEANUP / OBSERVE；BUSINESS 缺断言在 Validate/Preflight 拒绝 | **MISSING** | 不存在节点类别模型；只有 `node.get("type") == "cleanup"` 特例（`workflow_validator.py:66-68`、`dag_scheduler.py:156`）；`validate_workflow()` 不断言“业务节点至少一条断言”（`:169-184` 只查 `expected` 是否存在）；`preflight.py` 只查 driver/capability/secret/env，不查断言 |
| **断言结构**（assertion_id/kind/subject/operator/expected/actual_source/severity/required/timeout_ms/evidence_required/version） | **PARTIAL** | `AssertionSpec`（`schemas/contracts.py:67-100`）有 `assertion_key/oracle_layer/oracle_ref/type/operator/expected/expected_ref/actual_source/path/selector/schema/timeout_ms/severity/message`；**无 `assertion_id` / `kind` / `subject` / `required` / `evidence_required`**（在 `AssertionSpec` / Worker 链路中 `required` 只能落 `model_extra` 且无人读取；只有 `assertions/engine.py` 直接读原始 dict 的 `required`）；validator 不校验 type/operator/actual_source/timeout；`expected: null` 可通过 validate（只判键存在，`workflow_validator.py:179`） |
| 不允许空表达式/未知变量/无类型比较/空 expected/静默忽略 evaluator error | **PARTIAL** | 未知变量/悬空引用 IMPLEMENTED（`workflow_validator.py:209-244`）；evaluator 异常 → ERROR IMPLEMENTED（`assertion_service.py:388-391`）；但未知 `operator`/未知 `type` 要到运行期才 ERROR（`assertion_service.py:202,387`）、空 `expected` 不拒绝、`exploratory` 断言在 validate 被放行（`workflow_validator.py:177-178`）并在 Runtime 被**静默丢弃**（`assertion_service.py:127-128`） |
| **结果规则** PASS/FAIL/BLOCKED/ERROR/UNKNOWN/NOT_EVALUATED 语义 | **PARTIAL** | `assertion_service` 有 PASS/FAIL/ERROR/NOT_EVALUATED/BLOCKED（`:47-53`）；**UNKNOWN 在 Worker 链路永不产生**（仅在 `assertions/engine.py:215` 的非 required 分支）；Run 级 outcome 只有 PASS/FAIL/INCOMPLETE/UNKNOWN（`run_state.py:34`），`dag_scheduler`/`reconciler` 均不产生 `UNKNOWN` |
| **Run PASSED 条件**：所有 mandatory business 节点 terminal、所有 required assertion PASS、至少一个有效业务 Oracle、无 FAIL/BLOCKED/ERROR/UNKNOWN、required evidence 存在；Setup/Cleanup/Observe 不得使 Run PASS | **MISSING** | `dag_scheduler._finalize()`（`:196-228`）：FAIL 有 → FAIL；BLOCKED 有 → INCOMPLETE；否则 **PASS**；证据只查“已存在但上传未完成”的 Artifact（`:207-214` → `artifact_service.incompleteness_reasons()` `:261-279`）。**无“至少一个业务 Oracle”、无 required 集合、无 mandatory 节点、无 setup/cleanup 排除** |
| 验收①：空 assertions 的 BUSINESS node 在 Validate 阶段拒绝 | **MISSING** | 同上；`test_aiqe_execution_pipeline.py:249` 甚至把“login 无业务断言允许 PASS”写成契约 |
| 验收②：Driver 200 但业务 JSON 状态错误 → Assertion FAIL | **IMPLEMENTED** | `assertion_service.py:293-305`（jsonpath → FAIL）；**真实 Worker 入口测试** `test_aiqe_aud007_assertion_engine.py:325-377`（`job_consumer.claim_aiqe_jobs` + `run_job`，真实本地 HTTP stub） |
| 验收③：Driver 成功但无 Oracle，Run 必须 BLOCKED/ERROR，不得 PASS | **MISSING（fail-open）** | `execution_service.py:466-468`：`elif not declarations: node_status = "PASSED"`；`result_writer.py:136-138`：无断言返回 `(None,None,[])` 让调用方沿用 Driver 结论；`dogfood.py:493` 同样 `mapped_status or result.status` |
| 验收④：required assertion 未执行 / evidence 缺失 / actual source 不存在 → 不得 PASS | **PARTIAL** | Driver 失败时节点仍 ERROR（`execution_service.py:458-459`），断言记 `NOT_EVALUATED`（`assertion_service.py:502-516`）；`summarize()` 把 `NOT_EVALUATED` 归为 `BLOCKED`（`assertion_service.py:406-418`）；另一引擎把 `NOT_EVALUATED` 映射 `ERROR`（`assertions/engine.py:270`，仅 dogfood 路径）。但 `required` 语义在真实链路丢失（G9-5）、`evidence_required` 不存在（G9-8）、`actual_source` 只落库不校验（`assertion_service.py:457`） |
| 验收⑤：Quality Gate 与 Run Outcome 使用同一 required assertion 集合与证据规则 | **MISSING** | Gate 只统计 `severity == "P0"`（`quality_gate_service.py:136-147`），不读 `required`、不校验证据、不校验 Run 终态（`_runs_for_scope` `:57-80`）；与 Run Outcome 的聚合口径不同（G9-7） |

## 2.2 代码证据（可复核）

| 证据 | 位置 | 说明 |
|---|---|---|
| A1 | `app/aiqe/services/execution_service.py:455-470` | 节点终态判定；**无断言（或只有被过滤的 exploratory）→ `PASSED`**（`:466-468`） |
| A2 | `app/aiqe/services/result_writer.py:121-138` | 旧 Assertion Runtime：无 specs → `(None,None,[])`，由调用方沿用 Driver 结论（fail-open 接口约定） |
| A3 | `app/aiqe/services/assertion_service.py:64-119` | `normalize_assertion()`：`type` 必填、`oracle_layer` 枚举、`severity` 默认 **P1**；`required` 落 extra，未被读取 |
| A4 | `app/aiqe/services/assertion_service.py:267-270` | 所有断言都要求 `oracle_ref`，否则 ERROR（比规格更严，但只覆盖“有断言”的节点） |
| A5 | `app/aiqe/services/assertion_service.py:406-418` | `summarize()` 对全部断言聚合（非 required-only） |
| A6 | `app/aiqe/services/assertion_service.py:421-467` | `persist_outcomes()` 未写 `required` → `RunAssertionResult.required` 恒为默认 `True`（`models/run.py:212`） |
| A7 | `app/aiqe/services/dag_scheduler.py:196-228` | `_finalize()`：无断言/证据规则的 Run PASS 推导 |
| A8 | `app/aiqe/services/reconciler.py:78-98` | 第二套 Run 终态推导：无证据检查、BLOCKED→INCOMPLETE、无 UNKNOWN |
| A9 | `app/aiqe/services/quality_gate_service.py:132-175` | Gate 只看 `severity=P0`、取每个节点最新 attempt、不校验 Run 终态/required/证据 |
| A10 | `app/aiqe/assertions/engine.py:177-217,250-272` | 另一套断言引擎（severity P0/P1 无 oracle → BLOCKED；required-only 聚合；UNKNOWN 语义）；仅被 `result_writer` 使用，而 `result_writer` 仅被 `dogfood.py:485-493` 使用 |
| A11 | `app/aiqe/services/workflow_validator.py:66-68,169-184` | validator 只有 cleanup 特例与 `expected` 存在性检查；`exploratory` 直接跳过 |
| A12 | `scripts/ci/check-oracle-layer.ps1:27,60-95,101-103` | 唯一静态守卫只扫变更的 JSON/Markdown 里的 `oracle_layer`，不扫 Python 种子图/DB 图，也不检查“业务节点至少一条断言” |

## 2.3 Gaps（每条可验证）

| ID | Gap | 验证方式 |
|---|---|---|
| **G9-1** | **无断言业务节点直接 `PASSED`，Run 可零业务 Oracle 判 PASS** —— 规格最核心的禁止项 | A1；`rg -n "elif not declarations" -A3 app/aiqe/services/execution_service.py` |
| **G9-2** | 无 BUSINESS/SETUP/CLEANUP/OBSERVE 类别：validator/launch/preflight 都不拒绝“业务节点无断言” | A11；`rg -n "OBSERVE|BUSINESS" app/aiqe` 只命中 `playwright_driver.py:49`（动作类型）与 `testcase_service.py:80`（用例质量） |
| **G9-3** | Run PASSED 条件缺 3 个不变量：至少一个有效业务 Oracle、required assertion 全通过、required evidence 存在 | A7；`rg -n "incompleteness_reasons" app/aiqe` 仅 `dag_scheduler.py:212` |
| **G9-4** | 两套断言引擎并存且语义不同（oracle 触发条件、UNKNOWN、required）；Worker 用 `assertion_service`，带 Oracle 语义的 `assertions/engine.py` 只被 dogfood 使用 → 规格 §断言结构/结果规则的 Oracle 语义在正式链路上不存在 | `rg -n "from app.aiqe.services import assertion_service" app/aiqe/services/execution_service.py`（L27）；`rg -n "result_writer" app/aiqe` 仅 `dogfood.py` |
| **G9-5** | `required` 在真实链路被丢弃：`AssertionSpec` 无该字段 → `persist_outcomes` 恒写 `required=True`（模型默认）→ `regression_terminal` 的 `bool(assertion.required)` 过滤失去意义 | A3+A6；`rg -n "required" app/aiqe/services/assertion_service.py`（0 命中） |
| **G9-6** | 断言结构字段不全 + 校验不足：缺 `assertion_id/kind/subject/evidence_required/version`；`expected: null`、未知 operator/type、`exploratory` 均可过 Validate | A11+A3；`test_aiqe_workflow_validator.py:160-163` 把 exploratory 放行固化为契约 |
| **G9-7** | Quality Gate 与 Run Outcome 集合/证据不一致：Gate 用 `severity=P0`，Run 用节点状态；会出现“Run PASS 但 Gate BLOCKED（无 P0 事实）”或“Gate 对非终态 Run 出 PASS” | A7 vs A9；`quality_gate_service.py:165-167`（无 P0 → BLOCKED）；`:57-80`（无 status 过滤） |
| **G9-8** | 无逐断言 `evidence_required`；`actual_source` 只持久化不校验；缺失 evidence 不会阻断 PASS（只有“上传未完成”的 Artifact 会） | A9+A7；`models/run.py:198`（actual_source 仅列） |
| **G9-9** | 无静态/CI 守卫阻止“业务节点无断言”“无断言节点 PASSED”回归 | A12；`rg -n "no_assertion|assertion_required" scripts/ci`（0 命中） |

## 2.4 测试现状与入口质量

| 测试 | 入口 | 真实性 | 能证明 | 不能证明 |
|---|---|---|---|---|
| `test_aiqe_aud007_assertion_engine.py::test_http_200_business_error_fails_and_persists`（L325-377） | **Worker 正式入口**：`dag_scheduler.schedule`→`enqueue_node_run`→`job_consumer.claim_aiqe_jobs()`→`run_job()` | 真实 HTTP 本地 stub server、真实 Driver/断言/落库；仅预置 `upsert_target_policy`（V16-001 要求的前置） | HTTP 200 + 业务码错 → `biz.code=FAIL`、node FAILED、run outcome FAIL、断言落库含 expected/actual/oracle_ref | 无断言节点行为；required/evidence；Gate 一致性 |
| `…::test_all_assertions_pass_marks_node_passed`（L379-401） | 同上 Worker 入口 | 真实 | 全 PASS → 节点 PASSED | Run 级 PASS 条件 |
| `test_aiqe_assertion_runtime.py`（L39-206） | 直调 `evaluate_and_persist/normalize_assertions`（Service 层，非入口） | 真实（无网络） | 算子/类型/`eventually`/`oracle_ref` 缺失 → ERROR、probe 不产生 PASS | 不经过 Job/Worker/Driver |
| `test_aiqe_execution_pipeline.py::test_pipeline_variable_assertion_outputs_and_evidence`（L81） | `launch_run` + `job_consumer.run_job` | **Mock Driver**（monkeypatch `execution_service.execute_node`） | DAG/输出/证据/断言落库 | 真实 Driver 行为（可接受，本条不验证 Driver） |
| `…::test_probe_only_execution_never_passes`（L223-254） | 同上 + Mock Driver | Mock | probe 不产生 PASS | **反而把“无断言 login → PASS”写成注释契约（L249）** |
| `test_aiqe_quality_gate.py`（全 7 条） | **直调 helper** `evaluate_cases/evaluate_stats` | 纯函数 | 简单 P0 计数规则 | 真实 Gate（`evaluate_from_facts`）完全不覆盖 |
| `test_aiqe_console_admin_api.py::test_quality_gate_status`（L66-101） | **API** `/api/v1/aiqe/admin/quality-gate` | 真实 Service+DB（断言行由 ORM 直接 seed，Run 直接标 COMPLETED） | P0 PASS/FAIL/NOT_EVALUATED/ERROR/BLOCKED 映射、无 P0 → BLOCKED、跨项目 404 | required/证据规则；**非终态 Run**；Run Outcome 与 Gate 一致性 |
| `test_aiqe_workflow_validator.py:152-164` | helper `validate_workflow` | 纯函数 | `expected` 缺失拒绝、exploratory 放行 | “业务节点必须至少一条断言”不存在 |
| 全仓 | — | — | 无任何“无断言 → Run 不得 PASS”的负向用例（`rg -n "无断言\|without_assertion" tests` 仅命中 dogfood 的 `no_assertion_reason` 与 execution_pipeline 的注释） | 规格验收③④⑤ 全部无测试 |

**入口质量结论**：V16-009 的“Driver 200 + 业务错 → FAIL”（验收②）有**真实 Worker 入口**证据，这部分 IMPLEMENTED；但验收①③⑤ 与 Gate 一致性零覆盖，且验收③ 的 fail-open 被现有测试/注释固化为期望行为。

## 2.5 最小整改建议（不含补丁）

1. **`app/aiqe/services/execution_service.py::finalize_node()`**
   - 删除 `elif not declarations: node_status="PASSED"`（L466-468）；改为：无 `assertions` 且节点类别≠SETUP/CLEANUP → 节点 `BLOCKED`（`ASSERTION_MISSING`），SETUP/CLEANUP 只允许“技术性条件断言”，OBSERVE 不得贡献 PASS。节点类别需从 graph 节点 `type/category` 读取并落入 `NodeRun`（补列/迁移）。
2. **`app/aiqe/services/result_writer.py::evaluate_node_assertions()`**
   - 取消 `(None,None,[])` 的“沿用 Driver 结论”约定；无断言必须返回明确的 `BLOCKED/ERROR` 语义，调用方（`dogfood.py:493`）不得再用 `mapped_status or result.status`。
3. **`app/aiqe/services/workflow_validator.py::validate_workflow()`**
   - 新增节点类别校验：BUSINESS 必须 ≥1 条断言；断言 schema 校验（type ∈ `ASSERTION_TYPES`、operator ∈ 注册表、非 `exists/not_exists` 时 `expected` 非 None、`required` 必填、`evidence_required` 必填）；禁止 `exploratory` 单独构成业务节点。
4. **同集合口径**：抽出唯一 `evaluate_run_outcome()` 服务（供 dag_scheduler/reconciler/regression_terminal/quality_gate 共用），输入 required 断言集合 + evidence 结果，输出 `PASS/FAIL/BLOCKED/ERROR/UNKNOWN`；`quality_gate_service.evaluate_from_facts()` 改为调用同一函数并使用 `required=True`（而非 severity），且拒绝非终态 Run。
5. **断言模型**：`schemas/contracts.py::AssertionSpec` 增加 `assertion_id/kind/subject/required/evidence_required/version`；`assertion_service.persist_outcomes()` 落 `required`；`summarize()` 改 required-only 并显式产生 `UNKNOWN`。
6. **删除双引擎**：保留一个判定入口（建议 `assertions/engine.py` 的 Oracle 语义合并进 `assertion_service`），`result_writer`/`dogfood` 走同一入口。
7. **CI 守卫**：新增 `scripts/ci/check-business-assertions.py`（AST 扫描 graph 种子/模板 + `execution_service` 禁止 `not declarations → PASSED`），并在 `main-quality-gate.yml` 后端步骤中强制执行。
8. **必须新增的负向测试**
   - `tests/aiqe/test_v16_009_pass_semantics.py`
     - (a) `POST /aiqe/workflows` 创建 BUSINESS 节点无 `assertions` → 400（Validate 拒绝）。
     - (b) BUSINESS 节点 `assertions: [{type:"exploratory"}]` → 400。
     - (c) 断言 `required: false` 且 FAIL → 节点/ Run 结论不因该条失败（证明 required 集合生效且非 required 不阻断）。
     - (d) 节点无断言：从 `launch_run`+`job_consumer.run_job` 进入（真实入口）→ 节点 `BLOCKED`、Run outcome ≠ PASS、`assertion.evaluated`/`node.blocked` 事件存在（覆盖 G9-1）。
     - (e) `evidence_required=true` 但 `RunArtifact` 缺失/不可用 → Run 不得 PASS。
     - (f) 同一 run 同时跑 Gate 与 Run Outcome：断言集合完全一致（P0+P1+required 混合），断言两者结论一致（覆盖 G9-7）。
     - (g) Run 处于 RUNNING（有 P0 PASS 断言）→ Gate 必须 `BLOCKED`（非终态）。
   - 修改 `tests/test_aiqe_execution_pipeline.py:249` 注释与期望（整改后 login 无断言不得 PASS）。

## 2.6 复核命令

```powershell
$B = "F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6\test-platform-v2\backend"
# G9-1 核心 fail-open
rg -n -B6 -A4 "elif not declarations" "$B\app\aiqe\services\execution_service.py"
rg -n -A6 "if not specs" "$B\app\aiqe\services\result_writer.py"
# Run PASS 推导（无断言/证据规则）
rg -n -A30 "def _finalize\(" "$B\app\aiqe\services\dag_scheduler.py"
rg -n -A20 "def _finalize_run" "$B\app\aiqe\services\reconciler.py"
# required 丢失 / 双引擎
rg -n "required" "$B\app\aiqe\services\assertion_service.py" "$B\app\aiqe\schemas\contracts.py"
rg -n "result_writer|assertions.engine" "$B\app\aiqe"
# Gate 口径
rg -n -A12 "severity == \"P0\"" "$B\app\aiqe\services\quality_gate_service.py"
rg -n -A8 "def _runs_for_scope" "$B\app\aiqe\services\quality_gate_service.py"
# validator 缺口
rg -n -A18 "assertions = node.get" "$B\app\aiqe\services\workflow_validator.py"
# 静态守卫
rg -n "oracle_layer|Invoke-Scan" "F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6\scripts\ci\check-oracle-layer.ps1"
```

---

# 3. V16-020：统一终态与 Comparison Snapshot

> 规格无独立章节，验收口径取自：总表 L192（terminal handler / regression compare｜仅真实终态 Run 可生成对比结论）、TC-AIQE-008 L839（Comparison Snapshot 引用真实 Assertion/Artifact）、Gate C L1148–L1155（QUEUED 必须有 Job；Run Outcome / Quality Gate / Regression Outcome 语义一致）、§0.2.2 L76（不得创建第二套终态计算逻辑）、Sprint 5 L1096。

## 3.1 验收口径 → 状态对照

| 口径 | 状态 | 关键证据 |
|---|---|---|
| **仅真实终态 Run 可生成对比结论** | **MISSING（被违反）** | `handle_run_terminal()` 只用 `regression.completed_at` 去重（`regression_terminal.py:212-220`），**不校验 `run.status ∈ {COMPLETED,BLOCKED,CANCELED,ERROR}`**；`aggregate_regression_status()` 对非终态 Run 直接落 `UNKNOWN`（`:102-118`）；`GET /comparison` → `load_comparison()` → `handle_run_terminal()` + `db.commit()`（`regression_service.py:487-494`） |
| 统一终态（不得有第二套终态计算） | **MISSING** | 4 处终态/outcome 推导：`dag_scheduler._finalize`（L196-228）、`reconciler._finalize_run`（L78-98）、`hardening_service.recover_after_worker_kill`（L28-58）、`regression_terminal.aggregate_regression_status`（L74-118），规则互不一致 |
| 终态不可回退 | **MISSING（存在改写路径）** | `cancel_regression()` 只写 `status=CANCELLED`+`cancelled_at`，**不写 `completed_at`**（`:401-419`）→ 之后 `GET /comparison`/`POST /sync` 进入 `handle_run_terminal()`（`completed_at is None`）→ 把 `CANCELLED` 改写为 `UNKNOWN` 并覆盖 `terminal_summary_json`（`:235-249`，丢 `cancel_reason`） |
| 终态由真实事件驱动（outbox/worker） | **MISSING** | `consume_terminal_events()`（`:285-309`）**无任何生产调用点**；`event_service.dispatch_outbox()`（`:123-139`）也无生产调用点；`run.completed` 事件写 outbox（`event_service.py:101`）但无人消费 |
| Comparison Snapshot 引用真实 Assertion/Artifact | **PARTIAL** | `evidence_refs_json` 只有 `artifact:{id}`（`:156-159`）；`assertion_diff_json` 的键是 `"node_key:assertion_key"` 字符串（`:130-151`），**无 `RunAssertionResult.id` / `StepAttempt.id` / `NodeRun.id`**；`blocked_json` 同 |
| 对比前提校验（40 位 SHA、部署证明时效、snapshot hash 一致） | **MISSING** | `build_comparison_snapshot()`（`:121-190`）只拷贝 `regression.fixed_sha/deployed_sha/workflow_checksum`，不校验：Run 终态、`deployed_sha == fixed_sha`、部署证明未过期、source run 与 regression run 的 workflow checksum 一致；且回归 Run 的 `workflow_checksum` 列为空（`regression_service.py:344-376` 未设置），快照里的 checksum 并非“被执行图”的 hash |
| 幂等 | **PARTIAL** | `completed_at` 单点去重（`:212-220`）+ `RunComparisonSnapshot` 无 `regression_id` 唯一约束（`models/defect.py:153-174`；迁移 L96–L123）；`with_for_update()` 在 SQLite 无效（`:205-209`），并发下可各写一条 |
| 不自动关缺陷 | **IMPLEMENTED** | `SUGGESTIONS` 只给建议（`:33-39`）；`handle_run_terminal()` 不 touch `Defect.status`；测试 `test_aiqe_regression_api.py:279-280` 断言缺陷仍 open |

## 3.2 代码证据（可复核）

| 证据 | 位置 | 说明 |
|---|---|---|
| T1 | `app/aiqe/services/regression_terminal.py:198-233` | 终态处理器：按 `verification_run_id` 查回归 → `completed_at` 去重 → 聚合 → 建快照 → 写状态；**无终态校验** |
| T2 | `app/aiqe/services/regression_terminal.py:74-118` | 聚合规则：CANCELED→CANCELLED、ERROR→UNKNOWN、无断言且 outcome PASS→UNKNOWN、FAIL 优先、outcome PASS→PASS、INCOMPLETE/BLOCKED→BLOCKED；**没有任何“run 是否终态”的判断** |
| T3 | `app/aiqe/services/regression_service.py:477-495` | `load_comparison()`：读路径内触发 `handle_run_terminal()` 并 `db.commit()`（GET 产生写副作用） |
| T4 | `app/api/v1/aiqe_regressions.py:184-236` | `GET /aiqe/regressions/{id}/comparison`：直接调用 T3；当 snapshot 为 None 时返回 `available=False, reason=VERIFICATION_RUN_NOT_TERMINAL`（**说明作者知道该语义，但代码没有真正阻断**） |
| T5 | `app/api/v1/aiqe_automation.py:72-93` | `POST /aiqe/automation/regressions/{id}/sync`：同样直接调用 `handle_run_terminal()`，无终态校验 |
| T6 | `app/aiqe/services/regression_terminal.py:285-309` | `consume_terminal_events()`：从 outbox 捞 `run.completed/run.failed/run.blocked` 驱动终态；**无调用方** |
| T7 | `app/aiqe/services/event_service.py:101,123-139` | 事件写 `EventOutbox`；`dispatch_outbox()` 仅被测试调用 → outbox 无 relay |
| T8 | `app/aiqe/services/dag_scheduler.py:196-228` / `reconciler.py:78-98` / `hardening_service.py:28-58` | 三套 Run 终态实现（规则不同：证据检查只在 dag_scheduler；UNKNOWN outcome 全无） |
| T9 | `app/aiqe/services/regression_terminal.py:121-190` | 快照构建：无前提校验、evidence 只有 artifact id、assertion 键为合成字符串 |
| T10 | `app/aiqe/services/regression_service.py:401-419` | 取消不写 `completed_at` → 给 T1/T2 留下“终态被改写”窗口 |
| T11 | `app/aiqe/models/defect.py:105-174` + `alembic/versions/20261124_aud009_regression_hardening.py:96-123` | `DefectRegression`/`RunComparisonSnapshot` 字段与索引；无终态机、无 snapshot 唯一约束 |

## 3.3 Gaps（每条可验证）

| ID | Gap | 验证方式 |
|---|---|---|
| **G20-1** | 非终态 Run 可生成对比结论，并被固化为“不可再改”的终态：`GET /comparison`（读路径）会把刚创建/仍在 QUEUED 的回归写成 `UNKNOWN`+`completed_at`，此后真实终态到达时返回 `ALREADY_HANDLED`，永久错误 | T1+T2+T3+T4；复现：创建回归（不执行）→ 调用 `GET /comparison` → 查 `DefectRegression.status/completed_at` |
| **G20-2** | 终态可回退/被改写：`cancel` → `GET /comparison`/`POST /sync` 使 `CANCELLED → UNKNOWN`，`terminal_summary_json` 的 `cancel_reason` 丢失 | T10+T1；复现：`POST /cancel` → `GET /comparison` → 查 status |
| **G20-3** | 无自动终态驱动：outbox 无人消费、`consume_terminal_events`/`dispatch_outbox` 零生产调用点；终态只能靠人工 `POST /sync` 或 GET 懒收敛 | `rg -n "consume_terminal_events|dispatch_outbox" app/`（仅定义） |
| **G20-4** | 多套终态计算并存且语义不一致（违反 §0.2.2 L76 与 Gate C 一致性） | T8；`rg -n "apply_transition\(run, \"COMPLETED\"" app/aiqe` |
| **G20-5** | 对比前提全缺：不校验 Run 终态、SHA 一致、部署证明时效、snapshot hash 一致；快照 `workflow_checksum` 取自 `DefectRegression`（创建时从 WorkflowDefinition 拿），而回归 Run 的 `workflow_checksum` 列为 `""`、`workflow_snapshot_json` 为 `{}` → 快照不能证明“对比的是哪张图” | T9；`regression_service.py:344-376`（未设置 workflow_checksum/workflow_snapshot_json）；`models/run.py:58-59` |
| **G20-6** | 证据不可追溯到断言实体：`evidence_refs_json` 只有 artifact id；assertion diff 用 `"node:key"` 字符串，缺 `RunAssertionResult.id`/`StepAttempt.id` | T9；`rg -n "evidence_refs" app/aiqe/services/regression_terminal.py` |
| **G20-7** | 幂等/并发不足：`completed_at` 无事件 ID 绑定；`RunComparisonSnapshot` 无 `(regression_id)` 唯一约束；SQLite 下 `with_for_update` 无效 | T1+T11；迁移 L96–L123 索引清单 |
| **G20-8** | 终态入口不是执行主链：两个 HTTP 读写入口 + dogfood 自算 outcome；没有 Worker/Outbox/CLI 的终态收口 | T3+T5；`rg -n "handle_run_terminal" app/`（仅 `aiqe_regressions.py`、`aiqe_automation.py`、`regression_service.py`） |

## 3.4 测试现状与入口质量

| 测试 | 入口 | 真实性 | 能证明 | 不能证明 |
|---|---|---|---|---|
| `test_aiqe_regression_api.py::test_terminal_sync_pass_and_comparison`（L252-287） | 直调 `handle_run_terminal()`；`_complete_run()` 用 ORM 手工改 `run.status/outcome`（L223-249） | 绕过 Worker/outbox/API | PASS 分支、`ALREADY_HANDLED` 幂等、缺陷不被自动关闭、`GET /comparison` 返回快照 | 终态是否真实；非终态调用；并发 |
| `…::test_terminal_sync_fail_needs_more_fix`（L290） | 同上 | 手工终态 | FAIL 分支 | 同上 |
| `…::test_terminal_sync_without_assertions_is_unknown`（L307-320） | 同上（`run.status="COMPLETED"`, `outcome="PASS"`） | 手工终态 | 无断言 → UNKNOWN | 非终态/部分执行时的行为（真实场景恰好会先触发 G20-1） |
| `test_aiqe_triage_experiments.py:242-254`（`test_sync_keeps_queued_while_run_not_terminal`） | 直调 `sync_experiment_result` | 真实 Run 行（未执行） | **噪声实验侧有终态守卫**（`triage_service.py:340-343`） | 回归侧没有对应守卫 → 说明是遗漏而非统一设计 |
| `test_aiqe_console_admin_api.py::test_quality_gate_status` | API（gate） | 真实 Service+DB | Gate 基本映射 | Gate 与 Run Outcome/回归一致 |
| 全仓 | — | — | `consume_terminal_events`、`build_comparison_snapshot`、`aggregate_regression_status` 均 **0 测试引用** | 终态链路的真实驱动 |
| `tests/e2e/aiqe/*` | Playwright/HTTP | — | 无 | TC-AIQE-008 无有效 E2E（`tc008` NotImplementedError；`unblocked_verify` 断言 QUEUED） |

**入口质量结论**：V16-020 的所有“终态”测试都是**手工造终态 + 直调 helper**，恰好绕开了本 Issue 要验证的两点（Run 必须真实终态、终态由执行链驱动）。这是规格 §0.2.3 L90 与 §0.2.8 明令禁止的验收方式。

## 3.5 最小整改建议（不含补丁）

1. **`app/aiqe/services/regression_terminal.py::handle_run_terminal()`**
   - 入口第一步强校验：`run.status ∈ TERMINAL_STATUSES`（引用 `run_state.TERMINAL_STATUSES`）且 `run.outcome` 与 status 自洽（COMPLETED 必须有 outcome），否则返回 `skipped=True, reason="RUN_NOT_TERMINAL"` 且**不写任何回归字段、不建快照**。
   - 增加回归自身终态守卫：`if regression.completed_at or regression.status in {"PASS","FAIL","BLOCKED","UNKNOWN","CANCELLED"}: return ALREADY_HANDLED`（禁止 CANCELLED→UNKNOWN 改写）。
2. **`app/aiqe/services/regression_service.py::load_comparison()`**
   - 读路径不得触发终态收敛；改为“只读 + 明确 `available=false, reason=RUN_NOT_TERMINAL`”；终态收敛只允许由 Worker/Outbox（或显式 maintenance CLI）执行。
3. **统一终态**：新建 `app/aiqe/services/run_outcome.py::finalize_run_outcome(db, run_id)`（唯一实现），`dag_scheduler._finalize`/`reconciler._finalize_run`/`hardening_service` 全部委托；回归/噪声/Gate 使用同一输入（required 断言集合 + 证据完整性 + mandatory 覆盖）。
4. **Outbox 消费者**：把 `consume_terminal_events()` 接入 `job_consumer`/独立 worker 轮询（或在 `dispatch_outbox` 后回调），并落 `dispatched_at`/重试计数；回归终态必须由 `run.completed` 事件驱动一次，`GET` 只读。
5. **`build_comparison_snapshot()`**
   - 前置校验：`len(fixed_sha)==40`、`deployed_sha==fixed_sha`、部署证明未过期、`source_run.workflow_checksum == regression_run.workflow_checksum`（后者需由 SnapshotCloner 写入）。
   - 证据字段改为真实 ID：`assertion_refs`（`RunAssertionResult.id`）、`step_attempt_ids`、`node_run_ids`、`artifact_ids`，并保留人类可读 key。
   - `RunComparisonSnapshot` 增加 `(regression_id, regression_run_id)` 唯一约束 + `source_event_id`。
6. **必须新增的负向测试**
   - `tests/aiqe/test_v16_020_terminal_comparison.py`
     - (a) 回归 Run 仍 `QUEUED`（无 Job）→ `GET /comparison` 返回 `available=false`，且 DB 中 `regression.completed_at is None`、`comparison_snapshot_id is None`（覆盖 G20-1）。
     - (b) 回归 Run `RUNNING` 且有一条 PASS 断言 → 同上（覆盖 G20-1）。
     - (c) `POST /cancel` 后 `GET /comparison`/`POST /sync` → `status` 仍为 `CANCELLED`，`terminal_summary_json.cancel_reason` 保留（覆盖 G20-2）。
     - (d) 真实链路：`launch_run`（regression source_type）+ `job_consumer.run_job` 使 Run 到 COMPLETED 后，`consume_terminal_events(db)` 一次即生成快照；再次运行幂等（覆盖 G20-3/G20-7）。
     - (e) `fixed_sha` 与 `deployed_sha` 不一致的回归（构造）→ 快照生成被拒绝（覆盖 G20-5）。
     - (f) 断言快照必须含真实 `RunAssertionResult.id`，且能反查（覆盖 G20-6）。
     - (g) Run outcome 与 Gate 对同一 Run 结论一致（覆盖 Gate C 一致性）。
7. **旧入口收口**：`POST /aiqe/automation/regressions/{id}/sync` 仅保留给运维并加审计/权限；不得作为常规终态驱动。

## 3.6 复核命令

```powershell
$B = "F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6\test-platform-v2\backend"
# G20-1/G20-2 无终态守卫 + 取消可被改写
rg -n -A26 "def handle_run_terminal" "$B\app\aiqe\services\regression_terminal.py"
rg -n -A22 "def aggregate_regression_status" "$B\app\aiqe\services\regression_terminal.py"
rg -n -A20 "def cancel_regression" "$B\app\aiqe\services\regression_service.py"
# G20-1 读路径写库
rg -n -A18 "def load_comparison" "$B\app\aiqe\services\regression_service.py"
# G20-3 outbox 无消费者
rg -n "consume_terminal_events|dispatch_outbox" "$B\app"
# G20-4 多套终态
rg -n "apply_transition\(run, \"COMPLETED\"" "$B\app\aiqe"
# G20-5 快照无前提校验
rg -n -A40 "def build_comparison_snapshot" "$B\app\aiqe\services\regression_terminal.py"
rg -n "workflow_checksum" "$B\app\aiqe\services\regression_service.py" "$B\app\aiqe\models\run.py"
# G20-6 证据字段
rg -n "evidence_refs_json|assertion_diff_json|blocked_json" "$B\app\aiqe\services\regression_terminal.py"
# 测试覆盖事实
rg -n "handle_run_terminal|consume_terminal_events|build_comparison_snapshot" "$B\tests"
```

---

# 4. 跨 Issue 交叉风险（fail-open 组合链）

1. **回归链路完全绕过断言**：`_replicate_nodes()` 不复制 `assertions`（regression_service.py:204-227）→ 回归节点 `assertions_json=[]` → `finalize_node()` 判 `PASSED`（execution_service.py:466-468）→ `dag_scheduler._finalize()` 判 Run `PASS`。**即使后续把回归 Run 接上 Job，业务断言也不会执行**。这是 V16-008 + V16-009 的组合缺口，比单点更严重：修复其中一个不会自动关闭。
2. **对比结论可先于执行产生**：回归 Run 无 Job（V16-008 G8-4）→ 永远 QUEUED → `GET /comparison` 立刻写 `UNKNOWN` 并 `completed_at`（V16-020 G20-1）→ 后续任何真实执行结果都无法写回。因此 “Regression Outcome” 在真实部署下**不可信**。
3. **Quality Gate 不能被用于反向兜底**：Gate 只统计 `severity=P0` 且不校验 `required`/证据/Run 终态（quality_gate_service.py:57-80,132-175），因此无法发现“Run PASS 但无 Oracle”的假 PASS；这与 Gate C L1153–L1155 直接冲突。
4. **证据形态被旧/伪 E2E 固化**：`tc_aiqe_unblocked_verify.py:146-147` 与 `test_aiqe_defect_regression.py:17-29` 把“7 位 SHA / QUEUED 即成功 / 立即 passed”写成期望；`test_aiqe_execution_pipeline.py:249` 把“无断言 PASS”写成注释。整改这些 Issue 必然触发上述测试变红，属于**必须同步修改的契约**，不能作为“回归失败”处理。
5. **文档/追踪缺口**：规格无 V16-020 章节；审计时 `docs/aiqe/v1.6/` 下只有 `_audit/` 审计输出（`baseline-audit-G1-G3.txt` 及并行的 G2/G5/G8 报告），**不存在** `V1.6-Requirement-Code-Test-Evidence-Matrix.md` / `traceability/requirements.yaml` / `.github/workflows/aiqe-v16-gates.yml`（V16-025 交付物），因此本报告三条 Issue 目前**没有追踪矩阵映射**，按 V16-025 口径无法进入 `VERIFIED/ACCEPTED`。

---

# 5. 审计边界与未能证明项

1. **未执行测试**：本次为只读审计，未运行 pytest/alembic（避免在工作树写 DB/缓存）。所有“测试是否会红/是否会绿”的判断均基于代码阅读，并在 §1.5/§2.5/§3.5 给出可执行命令。
2. **E2E 未运行**：`tests/e2e/aiqe/*` 需要隔离 Test 环境（`AIQE_E2E_BASE_URL`），本次未触发；本报告只评估其入口与断言质量。
3. **工作树仍在漂移**：审计期间 `run_launch.py` 与新增迁移被并发写入（§0.2）；若 V16-001 补丁继续扩展到 `execution_service.py` 的 `finalize_node()` 区域，需重新核对本报告行号（G9-1 位于当前 L466-468，位于 V16-001 已改区 `L573+` 之前，本次审计时未受影响）。
4. **前端未审**：本次范围不含前端；对照 API 回显字段（`aiqe_regressions.py:70-91`）未发现前端可绕过服务端强制集合的入口，但“前端是否把 `scope/selected_case_ids` 当作用户可随意收缩的控件”未验证。
5. **Runner 侧**：外部 Runner 上报路径（`execution_service.complete_from_external_report`）未在本报告展开（属 V16-001/002 范围），但它同样不会让回归 Run 产生 Job，故不影响 G8-4 结论。

---

# 6. 复核命令汇总（快速判定）

```powershell
$R = "F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6"
$B = "$R\test-platform-v2\backend"

# 0) 基线与漂移
git -C $R rev-parse HEAD; git -C $R status --porcelain=v1

# 1) V16-008 状态
rg -n "def build_mandatory_scope|def _replicate_nodes|def create_regression_request|status=\"QUEUED\"" "$B\app\aiqe\services\regression_service.py"
rg -n "mandatory" "$B\app\aiqe\services" "$B\app\api\v1\aiqe_regressions.py"
rg -n "def create_regression" "$B\app\services\defect_service.py" "$B\app\api\v1\defect.py"
rg -n "SnapshotCloner|scope_id" "$B\app"

# 2) V16-009 状态
rg -n -B3 -A5 "elif not declarations" "$B\app\aiqe\services\execution_service.py"
rg -n -B2 -A4 "if not specs" "$B\app\aiqe\services\result_writer.py"
rg -n -A32 "def _finalize\(" "$B\app\aiqe\services\dag_scheduler.py"
rg -n "severity == \"P0\"|def _runs_for_scope" "$B\app\aiqe\services\quality_gate_service.py"
rg -n "assertions = node.get" -A16 "$B\app\aiqe\services\workflow_validator.py"
rg -n "required" "$B\app\aiqe\services\assertion_service.py" "$B\app\aiqe\schemas\contracts.py"

# 3) V16-020 状态
rg -n -A26 "def handle_run_terminal" "$B\app\aiqe\services\regression_terminal.py"
rg -n "consume_terminal_events|dispatch_outbox" "$B\app"
rg -n "apply_transition\(run, \"COMPLETED\"" "$B\app\aiqe"
rg -n "def load_comparison" -A18 "$B\app\aiqe\services\regression_service.py"

# 4) 测试入口质量
rg -n "handle_run_terminal" "$B\tests"
rg -n "build_mandatory_scope|consume_terminal_events|build_comparison_snapshot" "$B\tests"
rg -n "abc1234def|QUEUED" "$B\tests\e2e\aiqe\tc_aiqe_unblocked_verify.py"
rg -n "NotImplementedError" "$B\tests\e2e\aiqe\tc_aiqe_service_acceptance.py"

# 5) 迁移
rg -n "mandatory_case_ids_json|run_comparison_snapshots|aiqe_deployment_attestations" "$B\alembic\versions\20261124_aud009_regression_hardening.py"
```

---

## 附录 A：证据索引（file:line → 结论）

| # | 位置 | 归属 | 结论 |
|---|---|---|---|
| 1 | `app/aiqe/services/regression_service.py:157-179,263-266,328` | V16-008 | 强制集合已计算并落库，但仅记录 |
| 2 | `app/aiqe/services/regression_service.py:204-227` | V16-008/009 | 克隆丢 edges/depends_on/assertions/outputs/capability |
| 3 | `app/aiqe/services/regression_service.py:344-376` | V16-008/020 | 自建 QUEUED Run，无 Launch/Preflight/Job |
| 4 | `app/aiqe/services/regression_service.py:401-419,477-495` | V16-020 | 取消不写 completed_at；读路径触发终态收敛 |
| 5 | `app/aiqe/services/regression_terminal.py:74-118,198-233` | V16-020 | 无终态校验、无 mandatory 校验 |
| 6 | `app/aiqe/services/regression_terminal.py:121-190` | V16-020 | 快照无前提校验、证据非实体 ID |
| 7 | `app/aiqe/services/regression_terminal.py:285-309` | V16-020 | outbox 消费者零生产调用 |
| 8 | `app/aiqe/services/execution_service.py:455-470` | V16-009 | 无断言 → PASSED（核心 fail-open） |
| 9 | `app/aiqe/services/result_writer.py:121-138` | V16-009 | 无断言沿用 Driver 结论 |
| 10 | `app/aiqe/services/dag_scheduler.py:196-228` | V16-009/020 | Run PASS 无 Oracle/required/证据规则 |
| 11 | `app/aiqe/services/reconciler.py:78-98,150-157` | V16-009/020 | 第二套终态；只扫 RUNNING |
| 12 | `app/aiqe/services/quality_gate_service.py:57-80,132-175` | V16-009 | Gate 只按 severity=P0，无 required/证据/终态 |
| 13 | `app/aiqe/services/assertion_service.py:64-119,267-270,406-467` | V16-009 | required 丢弃、全量聚合、oracle_ref 强制 |
| 14 | `app/aiqe/assertions/engine.py:177-217,250-272` | V16-009 | 第二套断言引擎（仅 dogfood 使用） |
| 15 | `app/aiqe/services/workflow_validator.py:66-68,169-184` | V16-009 | 无节点类别/无“必须断言”校验 |
| 16 | `app/api/v1/defect.py:330-358` + `app/services/defect_service.py:688-711,714-732` | V16-008/020 | 旧 API 旁路（7 位 SHA + 直接 passed）；第二套对比实现 |
| 17 | `app/aiqe/models/deployment.py:17-47` | V16-008 | 部署证明无过期 |
| 18 | `tests/test_aiqe_regression_api.py:223-320` | V16-008/020 | 手工造终态 + 直调 helper |
| 19 | `tests/test_aiqe_aud007_assertion_engine.py:325-401` | V16-009 | 唯一真实 Worker 入口断言测试 |
| 20 | `tests/test_aiqe_execution_pipeline.py:249` | V16-009 | “无断言 PASS” 被固化为期望 |
| 21 | `tests/e2e/aiqe/tc_aiqe_unblocked_verify.py:101-153` | V16-008 | 以 QUEUED + 7 位 SHA 作为 TC-008 成功 |
| 22 | `tests/e2e/aiqe/tc_aiqe_service_acceptance.py:225-229` | V16-008 | TC-008 NotImplementedError |
| 23 | `scripts/aiqe/run_dogfood.ps1:24` | V16-008 | dogfood M4 组使用旧回归测试作为证据 |
| 24 | `scripts/ci/check-oracle-layer.ps1:27,60-95` | V16-009 | 唯一断言静态守卫，覆盖不到业务节点断言 |
| 25 | `alembic/versions/20261124_aud009_regression_hardening.py:16-123` | V16-008/020 | 表/列/唯一索引存在；无终态机、无 snapshot 唯一约束 |

---

*报告结束。本报告仅为审计结论与整改建议，未包含任何代码补丁，也未修改任何业务文件。*
