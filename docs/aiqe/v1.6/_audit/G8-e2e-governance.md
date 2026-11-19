# G8 独立审计报告 — V16-017（十个真实 E2E）与 V16-025（工程交付治理）

> 审计类型：只读代码审计（未修改任何业务文件；本文件是本次审计唯一写入）
> 审计对象 worktree：`F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6`
> 审计对象提交：`86a44b2cb`（`release/aiqe-v1-6`，与 `origin/main` 的 `rev-list --left-right --count` = `0 0`）
> 规格来源：`C:\Users\26029\Downloads\CamelTv_AIQE_V1.6_修复与生产化开发实施计划.md`
> 关注范围：`test-platform-v2/backend/tests/e2e/aiqe` 十个 TC / `scripts/aiqe` / CI Gate / CODEOWNERS / PR 模板 / 追踪矩阵
> 审计日期：2026-11-19

## 0. 审计口径与基线声明

1. **判定基线**：所有“已实现/未实现”结论均以 worktree 的**已提交 HEAD `86a44b2cb` + 工作树现状**为对象，用 `git ls-files` 与逐行读码核对，不接受“目录名/类名/文档声明”作为实现证据（规格 §0.2.8 第 146 条）。
2. **工作树漂移（必须知悉）**：审计期间工作树被并发开发持续写入（V16-001/V16-004 第二批补丁），审计开始时为 14 改 + 1 新增，审计结束前扩展为 **20 改 + 3 新增**（新增 `alembic/versions/20261119_v16_001_policy_status.py`、`scripts/aiqe/migrate_workflow_target_policy.py`、`tests/test_aiqe_v16_001_policy_fail_closed.py`；`run_launch.py`、`execution_jobs.py`、`models/workflow.py` 等随后也被改写）。与本报告结论直接相关的处理：
   - 本报告涉及的**判定对象文件**（`test-platform-v2/backend/tests/e2e/aiqe/**`、`.github/**`、`scripts/aiqe/**`（仓库根）、`scripts/git/audit-ai-pr.ps1`、`app/aiqe/services/regression_service.py`、`work-logs/**`）**均不在** `git status --short` 中，即未受在途补丁影响。
   - 少数**被引用但不属于判定对象**的文件（`backend/scripts/aiqe/evidence_*.py`、`tests/test_aiqe_execution_pipeline.py`、`app/aiqe/services/run_launch.py`）现处于在途修改状态；本报告引用的行号（`evidence_camel_test5.py:139/184/211`、`evidence_local_20.py:169/217`、`test_aiqe_execution_pipeline.py:105/107/123`、`run_launch.py:86`）已在**审计结束时对工作树重新逐行复核**，与结论一致。若 V16-001 补丁合入这些文件，需重跑 §5 命令确认。
   - `docs/aiqe/v1.6/` 为未跟踪目录，仅含同批审计产物 `_audit/baseline-audit-G1-G3.txt` 与本报告 `_audit/G8-e2e-governance.md`（无任何 V16 交付物）。
3. **状态判定规则（严格版）**：只有当一个 Issue 的**每一项**“通用要求 / 实施步骤 / 验收标准”都能在代码中找到从**正式入口**可复核的实现与测试时，才允许 `IMPLEMENTED` 及以上。任一子项完全缺失即不臆造 IMPLEMENTED；子项只有“零件”而无主链/无入口时按规格 §0.2.4 记为 `IMPLEMENTED` 以下并在 gaps 中点名。本次两 Issue 均**没有**任何子项达到“正式入口 + 业务断言 + 证据”的 IMPLEMENTED 门槛。
4. **规格-仓库路径差异**：规格把 TC 目录写作 `tests/e2e/aiqe`（相对后端根 `test-platform-v2/backend`），实际位置为 `test-platform-v2/backend/tests/e2e/aiqe`；规格把治理脚本写作 `scripts/aiqe/check_traceability.py`，仓库根 `scripts/aiqe/` 实际只有 3 个文件（见 §3.2）。审计按“仓库根相对路径”书写行号。

## 1. 结论

| Issue | 标题 | 判定 | 一句话依据 |
|---|---|---|---|
| **V16-017** | TC-AIQE-001～010 独立真实验收 | **MISSING** | 被 V1.5 点名的 `test_tc_aiqe_001_010.py`（十个用例同一 `/runs` 页面 + `body.count()==1`）在 HEAD 上**逐字未改**（最后改动 `447b2f6de`/#558）；后续 #571/#574 新增的两个脚本直调 `dag_scheduler`/`node_executor` 伪造执行链，3/10 为 `NotImplementedError`（BLOCKED），`return 0 if failed==0` 把 BLOCKED 当成功；`work-logs/P1-closeout.md:36` 据此写“9/10 PASS”与规格定义冲突；CI 中**没有任何** workflow 运行 AIQE E2E。 |
| **V16-025** | 工程交付治理代码化落地 | **MISSING**（10 项实施步骤：9 项完全缺失，1 项 PR 模板 PARTIAL） | 规格 8.7 的 9 项“必须交付的自动化资产”在 `git ls-files` 中**全部 0 命中**：无 `check_traceability.py`、无 `aiqe-v16-gates.yml`、无 `CODEOWNERS`、无追踪矩阵、无 `requirements.yaml`、无 `evidence-index` 生成器、无 Sprint 差距报告、无 branch protection/ruleset 生效证明；仅 PR 模板有 `Issue: #` 与证据表两处近似字段，且**没有任何 Gate 会拒绝空字段**。 |

两 Issue 都**不得**进入 `VERIFIED/ACCEPTED`；按规格 Gate E/F/G 与 §14“治理：V16-025 Gate G 全部通过”的要求，当前状态连带阻塞 `GA` 判定。

---

## 2. V16-017 详审：TC-AIQE-001～010 独立真实验收

### 2.1 规格要求逐条对照

| # | 规格要求（§V16-017 通用要求 / TC 验收门槛） | 现状 | 证据 |
|---|---|---|---|
| 1 | 每个 TC 有独立文件或独立测试函数、**独立 fixture**、数据隔离、清理逻辑、业务断言和证据清单 | ❌ 未满足 | `tests/e2e/aiqe/test_tc_aiqe_001_010.py:45-55` 为 **session 级单 browser/page**（十个 case 共用一个登录页）；`:58-63` 是**同一个** `test_tc_aiqe_case` 参数化函数；无 `conftest.py`（该目录只有 3 个 `.py` + `__pycache__`）；服务脚本有清理（`tc_aiqe_service_acceptance.py:305-324`）与一份脚本级 JSON，但**无 per-TC 独立 fixture/数据隔离**，且该 JSON 缺 job/assertion/artifact ID |
| 2 | 必须通过**真实 API/Worker/Driver**；禁止用 Mock 代替本次要验收的关键链路 | ❌ 未满足（两条路径都不合格） | ①页面路径不触达执行链（仅 `goto /runs`）；②`tests/e2e/aiqe/tc_aiqe_service_acceptance.py:7-8` 文档自述“直接调用 AIQE 服务层”，`:73-83` 用 ORM 直接 `TestRun(...)`，`:124-128` 手工 `dag_scheduler.create_node_runs/schedule/mark_running/complete_node`；③`tc_aiqe_unblocked_verify.py:55-76` 同样 ORM 建 Run + 手工推进 |
| 3 | 测试结束输出 `run_id`、`project_id`、`workflow_snapshot_hash`、`job_ids`、`assertion_ids`、`artifact_refs`、最终 outcome | ❌ 未满足 | 页面路径**什么都不输出**；服务脚本输出里只有 `workflow/checksum`、`run/status/outcome/events`、`mutex/key`、`signal/outcome`、`candidate/status`（`tc_aiqe_service_acceptance.py:117,142,172,198,222,262-266,288`），**无 `project_id`/`job_ids`/`assertion_ids`/`artifact_refs`**；已入库的证据 JSON `work-logs/aiqe/evidence/tc-aiqe-test-20261113.json`（由 #571 手工提交，属“把脚本 stdout 粘进仓库”，非 CI 生成）同样缺这些字段；`workflow_snapshot_hash` 在后端全仓 **0 命中**（`rg workflow_snapshot_hash test-platform-v2/backend` 无结果） |
| 4 | 失败时保存截图、Trace、HAR、请求/响应脱敏副本、DB 断言和事件日志 | ❌ 未满足 | `test_tc_aiqe_001_010.py:45-55` 只 `browser.new_page()`，**无 `tracing.start`/`har`/`screenshot`**；两个服务脚本仅在 `run_case` 里记录 `traceback.format_exc(limit=4)`（`:66`），无任何 TIP 产物、无 DB 断言快照 |
| 5 | 环境不具备前置条件时结果为 **BLOCKED，不得 SKIP 后计入 PASS** | ❌ 明确违反 | `test_tc_aiqe_001_010.py:21` `pytestmark = pytest.mark.skipif(not BASE_URL, ...)`；`:15` 模块级 `pytest.importorskip("playwright.sync_api")`。CI 跑 `python -m pytest -q`（`.github/workflows/main-quality-gate.yml:181-187`，`test-platform-v2/backend/pytest.ini:2-3` 的 `testpaths=tests`）时这 10 条以 **skipped** 记入结果 |
| 6 | 10/10 必须是独立业务场景，**不得共用单一页面加载断言** | ❌ 明确违反 | `test_tc_aiqe_001_010.py:61-62`：`goto(f"{BASE_URL}/runs")` + `assert locator("body").count() == 1`。`body` 元素在任何已加载页面（含登录页）恒为 1，该断言**没有业务含义**，且 `_login`（`:37-42`）的 `wait_for_url(f"{BASE_URL}/**")` 与当前登录 URL 自匹配，登录成功与否不影响结果 |
| 7 | 所有用例都从正式 **Launch/API/Worker** 入口运行 | ❌ 未满足 | 正式入口确实存在：`app/api/v1/aiqe_runs.py:57-89`（`POST /api/v1/aiqe/runs` → `launch_run`，`app/aiqe/services/run_launch.py:86`），Worker 侧为 `job_consumer.claim_aiqe_jobs/run_job`。但**十个 TC 一条都没走它**（无 `launch_run`、无 `ExecutionJob`、无 claim） |
| 8 | 每个 TC 至少一个 negative assertion；安全类 TC 必须有“目标未抵达”的外部证据 | ❌ 未满足 | 页面路径无任何负向断言；服务脚本中 tc001/tc005/tc006/tc007 有负向语义（`:109-115`、`:163-168`、`:197`、`:217-221`）但全部是**与自身伪造状态比较**，不存在“危险目标服务器没有收到请求”的外部计数器/目标端日志 |
| 9 | TC 报告必须机器可读，CI 能解析 PASS/FAIL/BLOCKED；BLOCKED 不计入通过率 | ⚠️ 形式有、语义 fail-open | 服务脚本打印 JSON（`:342`），由人工贴入 `work-logs/aiqe/evidence/tc-aiqe-test-20261113.json`（#571）与 `tc-aiqe-unblocked-20261113.json`（#574），**CI 不生成也不解析**；`main()` 退出码 `return 0 if summary["failed"] == 0 else 1`（`:343`）——3 条 BLOCKED 时仍 **exit 0 = 通过**；“BLOCKED 不计入通过率”无实现；且 `work-logs/P1-closeout.md:36` 据此得出 **“9/10 PASS、1 BLOCKED”** 结论（与规格定义冲突，见 G8-017-14） |

### 2.2 规格场景 vs 仓库实际场景（ID 语义冲突）

规格 §V16-017 定义的十个场景与仓库里挂着同一批 ID 的三套内容**互不对应**：

| TC | 规格要求的场景 | `tc_aiqe_service_acceptance.py:291-302` | `test_tc_aiqe_001_010.py:23-34` | 其它占用者 |
|---|---|---|---|---|
| 001 | 跨系统混合 Workflow（API→后台 UI→DB→前台 UI） | 契约/定义冻结 | 需求契约冻结 + 变更影响 | — |
| 002 | HTTP 200 但业务断言失败 | DAG 两节点 + 事件时间线 | 用例生成与评审 | — |
| 003 | Playwright 真实交互 + 安全拦截 | 首次失败 + 重试（**NotImplementedError**） | DAG 执行与证据 | sports adapter `DAG 执行与证据` |
| 004 | DB 只读/Query Registry/租户隔离 | 广告浮层交叉干扰（**NotImplementedError**） | 失败归因 | `scripts/qa/check_business_web_reachability.py:1` 自称 TC-AIQE-004 前置检查 |
| 005 | SSRF/Redirect/DNS Rebinding | 并发数据污染（fixture 锁） | 反事实重放 | — |
| 006 | Secret 全链路保护 | 上游第三方 5xx → BLOCKED | 缺陷草稿与一键回归 | — |
| 007 | Worker 崩溃/重复消息/Lease/Fencing | UI Runner worker lost | 噪音抑制规则 | `app/aiqe/adapters/cameltv_sports.py:27` “断流重连”；`tests/test_aiqe_sports_vertical.py:6` |
| 008 | 缺陷一键回归（Job 派发/Mandatory 覆盖/Run terminal） | 一键回归（**NotImplementedError**） | 版本质量门禁 | — |
| 009 | Noise 因果分析 E1–E6 | 多端 AC 平台矩阵 | MCP 查询与写审批 | — |
| 010 | A0–A6 Agent/Benchmark/学习发布 | 学习候选状态机 | 平台矩阵 | — |

**结论**：`TC-AIQE-001..010` 在仓库内至少有 4 套互不相同的语义（`test_tc_aiqe_001_010.py`、`tc_aiqe_service_acceptance.py`、`app/aiqe/adapters/cameltv_sports.py:21-30`、`tc_aiqe_unblocked_verify.py`）。规格要求的 10 个场景里，**跨系统 UI 链路、HTTP200+业务失败、SSRF/DNS Rebinding、Secret 全链路、Noise E1–E6、A0–A6** 在 TC 编号下**零覆盖**（这些主题的单元/集成测试存在，但不在 TC 语义下，见 §2.4）。这是 V16-025 追踪链无法建立的**前置硬伤**。

### 2.3 V16-017 gaps（可逐条复核）

- **G8-017-01（P0）十个 TC 仍共用一个页面加载断言**：`test-platform-v2/backend/tests/e2e/aiqe/test_tc_aiqe_001_010.py:58-63`。V1.5 审计指出的缺陷在 HEAD 上**逐字存在**：该文件最后一次改动是 `447b2f6de`（#558），此后 #571（新增 `tc_aiqe_service_acceptance.py`）与 #574（新增 `tc_aiqe_unblocked_verify.py`）都**没有修改**这个伪 E2E 文件（`git log --oneline -- <path>` 仅 1 条）。
- **G8-017-02（P0）无独立 fixture / 数据隔离 / 清理 / 业务断言**：同文件 `:45-55` 为 `scope="session"` 单 page；无 `conftest.py`；无 cleanup。
- **G8-017-03（P0）未从正式入口进入**：`tests/e2e/aiqe/tc_aiqe_service_acceptance.py:73-83` 用 ORM `TestRun(...)`；`:124-128`、`tc_aiqe_unblocked_verify.py:64-76` 手工 `dag_scheduler.*` 推状态；`backend/scripts/aiqe/evidence_camel_test5.py:127-164,184` 与 `evidence_local_20.py:156-195,217` 是同一模式（`node_executor.execute_node(...)` 直调 + 手工 `finalize_run`）。规格 §0.2.3/§0.2.8 明令禁止。
- **G8-017-04（P0）证据字段缺失**：已入库证据 JSON（`work-logs/aiqe/evidence/tc-aiqe-test-20261113.json`、`tc-aiqe-unblocked-20261113.json`）无 `project_id`/`job_ids`/`assertion_ids`/`artifact_refs`；`workflow_snapshot_hash` 字段在 `test-platform-v2/backend` 中 0 命中（依赖 V16-005 WorkflowSnapshot，尚未落地）。
- **G8-017-05（P1）失败无证据留档**：无 Trace/HAR/screenshot/请求响应脱敏副本/DB 断言（`test_tc_aiqe_001_010.py:45-55`）。
- **G8-017-06（P0）BLOCKED 被 SKIP 替代**：`test_tc_aiqe_001_010.py:15,21`；CI 中计为 skipped。
- **G8-017-07（P0）CI 完全不跑 AIQE E2E**：`.github/workflows` 下 9 个 workflow 对 `tests/e2e` / `aiqe` **0 命中**（`rg -n "tests/e2e|aiqe" .github/workflows` 空）。
- **G8-017-08（P0）服务脚本把 BLOCKED 当成功（fail-open）**：`tc_aiqe_service_acceptance.py:343` `return 0 if summary["failed"] == 0 else 1`，`blocked` 计数（`:338`）不参与退出码。
- **G8-017-09（P0）3/10 场景直接 `NotImplementedError`**：`:146-149`（TC-003）、`:152-156`（TC-004）、`:225-229`（TC-008）。
- **G8-017-10（P0）场景与规格不对应**：见 §2.2 表；规格 6 个关键场景在 TC 编号下零覆盖。
- **G8-017-11（P0）TC-008 “回归验收”是伪造 PASS，且回归通道本身违反 §12#5**：
  - `tc_aiqe_unblocked_verify.py:146` `assert data["run"]["status"] == "QUEUED"` —— 把 QUEUED 断言成 PASS（规格 §0.2.8 第 138 条明令禁止）。
  - 证据链真实状态：`app/api/v1/aiqe_regressions.py:131-154` 的 `POST /api/v1/aiqe/regressions` 只调 `create_regression_request`，**不调用 `launch_run`、不派发 ExecutionJob**；`app/aiqe/services/regression_service.py:344-376` 直接 `TestRun(status="QUEUED")` → 无 Job 可被 claim；`:204-227` `_replicate_nodes` 用 `"depends_on": []` + `"edges": []` 复制节点，**清空 DAG 依赖**（规格 §12 第 5 条禁止）；`/regressions/{id}/sync`（`app/api/v1/aiqe_automation.py:72-93`）只做终态同步，不启动执行。
- **G8-017-12（P1）无“目标未抵达”的外部证据**：安全类场景（SSRF/浏览器 egress）均无受控目标端请求计数器。
- **G8-017-13（P0）TC ID 语义冲突**：见 §2.2；同 ID 四套语义使 V16-025 的 Requirement↔Test 映射不可判定。
- **G8-017-14（P0）“9/10 PASS”结论已写入收口报告，与规格定义冲突**：`work-logs/P1-closeout.md:36` 记录“真实 TC-AIQE-001..010 ⚠️ 9/10 PASS、1 BLOCKED”，依据是 #571/#574 的两个脚本 + `work-logs/aiqe/evidence/*.json`，并把 `tc-aiqe-unblocked-20261113.md` 作为解除证据。但这些“PASS”来自：① 手工 `dag_scheduler` 推进的 attempt 时间线（TC-003）；② 断言 `run.status == "QUEUED"` 的回归创建（TC-008，`tc_aiqe_unblocked_verify.py:146`）；③ 与规格场景不对应的自定场景（§2.2）。按规格 §0.2.8 第 138/139 条与 Gate E“不存在只访问 `/runs` 页面即 PASS 的验收测试”，该结论**不成立**，必须在审计结论中撤回并以真实 E2E 重新计算通过率。

### 2.4 已存在测试及其入口质量

| 资产 | 层级 | 入口 | Mock/替身边界 | 能否作为 V16-017 证据 | 证据行 |
|---|---|---|---|---|---|
| `tests/e2e/aiqe/test_tc_aiqe_001_010.py` | 伪 UI | 浏览器 `goto /runs` | 无业务系统，无执行链 | ❌ 反例：正是规格要删除的形态 | `:58-63` |
| `tests/e2e/aiqe/tc_aiqe_service_acceptance.py` | L2（直调 Service） | ORM + `dag_scheduler` + `node_executor`（**绕过 API/Worker/Driver**） | 全部内部 helper；代码路径上 7 条 PASS、3 条 BLOCKED（本次审计未执行，仅静态判定） | ❌ 不可（§0.2.3 第 90 条） | `:7-8,73-83,124-128,146-149,291-343` |
| `tests/e2e/aiqe/tc_aiqe_unblocked_verify.py` | L2（真实 HTTP + ORM 混用） | `POST /defects`、`POST /aiqe/regressions` 真实 API；**Run 由 ORM 建、状态由 scheduler 手推** | 断言 `QUEUED` 即 PASS | ❌ 不可（假 PASS） | `:22,37,51-98,101-153,146` |
| `backend/scripts/aiqe/evidence_camel_test5.py` | L2（直调） | ORM `TestRun` + `execute_node` + 手工 `finalize_run` | 真实外部 HTTP 目标，但执行链伪造 | ❌ 不可作为 Runtime E2E（产出物 `docs/aiqe/evidence/camel-test5-20.json` 有 `run_id`/`status=COMPLETED`，但**无 ExecutionJob**） | `:127-164,184,211` |
| `backend/scripts/aiqe/evidence_local_20.py` | L2（直调） | 同上 + 登记查询 | 同上 | ❌ 不可 | `:156-195,217` |
| `tests/test_aiqe_execution_pipeline.py` | L2（Launch→Job→Consumer 真实基座） | `launch_run` + `job_consumer.claim_aiqe_jobs/run_job` ✅ | `monkeypatch.setattr(execution_service, "execute_node", fake_execute)`（Mock 掉 Driver） | ⚠️ 只能证明调度骨架，不能证明真实 Driver | `:1,85-105,107-123` |
| `tests/test_aiqe_run_api_v14.py` | L2（真实 API 入口） | `TestClient` + `POST /api/v1/aiqe/runs`，断言 `ExecutionJob` 存在 | 无 Worker 消费 | ⚠️ 只到“Job 已创建” | `:8,25,106-124` |
| `tests/test_aiqe_sports_vertical.py` | L1 | 纯 Python `executor` 闭包（**假执行器**） | 全 Mock | ❌ 且占用 `TC-AIQE-001..010` ID | `:6,19` |
| `tests/test_aiqe_v16_001_policy_fail_closed.py`（在途未提交） | L2（`job_consumer.run_job` 入口） | Worker 消费入口 ✅ | 受控 HTTP 目标 | ⚠️ 仅 V16-001 用；未被 TC 套件复用 | `:133,159,190,221,275,303,348` |

**基线事实**：后端 `tests/` 下 `test_aiqe*.py` 共 **88 个文件**，覆盖了安全/断言/状态机等 L1–L2；但**“正式 API→Job→Worker→Driver→Assertion→Artifact→Finalize”的 L3 运行时 E2E 对十个 TC 的覆盖为 0**。

**已入库的 TC “证据”文件（必须按上面口径重新定性）**：

| 文件 | 来源 | 内容问题 |
|---|---|---|
| `work-logs/aiqe/evidence/tc-aiqe-test-20261113.json` | #571 手工提交（脚本 stdout 粘贴） | `passed=7/blocked=3/failed=0`；无 `project_id`/`job_ids`/`assertion_ids`/`artifact_refs`；BLOCKED 未参与通过率；场景与规格不对应 |
| `work-logs/aiqe/evidence/tc-aiqe-unblocked-20261113.json` | #574 手工提交 | TC-003 的 `attempts:[FAILED,PASSED]` 由 `dag_scheduler.complete_node` 手推；TC-008 的 `verification_run` 是 `QUEUED` 且无 ExecutionJob |
| `work-logs/aiqe/tc-aiqe-test-20261113.md`、`tc-aiqe-unblocked-20261113.md`、`work-logs/P1-closeout.md:36` | 同上 | 人类可读结论页，已出现“9/10 PASS”“TC-003/008 由 BLOCKED → PASS”的**假完成表述**（G8-017-14） |

### 2.5 最小整改建议（不含补丁代码）

1. **重建 TC 套件骨架**：`test-platform-v2/backend/tests/e2e/aiqe/conftest.py` 新增 `tenant`/`project`/`workflow`/`run_ctx`/`api_client` 五个 per-test fixture（function scope），每个 TC 一个文件 `test_tc_aiqe_001.py … test_tc_aiqe_010.py`；删除现 `test_tc_aiqe_001_010.py` 的参数化单页断言。
2. **统一正式入口**：所有 TC 走 `POST /api/v1/aiqe/runs`（`app/api/v1/aiqe_runs.py:57-89`）→ `job_consumer.claim_aiqe_jobs`/`run_job`（Worker 入口）→ 轮询 `GET /api/v1/aiqe/runs/{id}/nodes`、`/assertions`、`/artifacts` 直到终态；禁止 `monkeypatch execution_service.execute_node`、禁止 ORM 建 `TestRun`、禁止手工 `dag_scheduler.mark_running/complete_node/finalize_run`。
3. **证据输出器**：新增 `tests/e2e/aiqe/evidence.py::build_tc_evidence(...)`，每条 TC 输出 `run_id/project_id/workflow_checksum/（待 V16-005 的 snapshot hash）/job_ids/node_run_ids/assertion_ids/artifact_refs/outcome` 到 `docs/aiqe/v1.6/traceability/evidence/TC-AIQE-00X.json`；缺失任一关键 ID 时**判 FAIL**（对应 V16-025 §7）。
4. **TC-008 修正**：改为断言 `ExecutionJob` 数 > 0、mandatory case 全覆盖、DAG `edges`/`depends_on` **保留**（同时修 `regression_service.py:204-227`）、Run 终态 + comparison 引用真实 Assertion/Artifact；删除 `assert run.status == "QUEUED"`。
5. **BLOCKED 语义**：把 `skipif` 改为“生成 BLOCKED JSON + 非零退出（或 CI 标记 blocked 且不计通过率）”；`tc_aiqe_service_acceptance.py:343` 退出码必须把 `blocked` 计入非通过。
6. **降级与改名**：`tc_aiqe_service_acceptance.py`/`tc_aiqe_unblocked_verify.py`/`evidence_*.py` 保留为 **L2 集成证据**并改名为 `l2_*`，**不得**再以 `TC-AIQE-*` 编号冒充 E2E（解决 G8-017-13）。
7. **撤回假完成结论**：修订 `work-logs/P1-closeout.md:36` 与 `work-logs/aiqe/tc-aiqe-unblocked-20261113.md`，把“9/10 PASS / BLOCKED→PASS”改为“V16-017 未验收（0/10 真实 E2E）”，并在 `tc-aiqe-*.json` 中把无 ExecutionJob 的条目标 `UNVERIFIED`；否则后续追踪矩阵会以假数据起步。
8. **必须新增的负向测试（从正式入口）**：
   - TC-002 类：HTTP 200 + `success=false` → Run 终态必须 FAIL/BLOCKED，Assertion FAIL，且 `GET /runs/{id}` 可读到失败证据；
   - TC-004 类：inline SQL / 写 SQL / 跨租户 `query_key` → 拒绝 + 目标 DB `INSERT` 计数为 0（用只读账号 + 行数快照双向断言）；
   - TC-005 类：302 → `127.0.0.1` / `169.254.169.254` / IPv6-mapped → 受控目标端 fixture **收到请求数 = 0**，事件含拒绝原因；
   - TC-006 类：Canary 明文在 DB/event/artifact/日志 命中数 = 0，越权 Handle 解析失败；
   - TC-007 类：重复投递 + 迟到 fencing token → 仅 1 个有效终态，旧 token 被拒；
   - 元测试（防回归）：静态守卫断言 `tests/e2e/aiqe/**` 内 `locator("body")`、`pytest.mark.skipif`、`TestRun(` 直建、`dag_scheduler.mark_running(` 命中为 0。

---

## 3. V16-025 详审：工程交付治理的代码化落地

### 3.1 规格 8.7 十项实施步骤逐项判定

| # | 实施步骤 | 判定 | 证据 |
|---|---|---|---|
| 1 | 建立 `docs/aiqe/v1.6/V1.6-Requirement-Code-Test-Evidence-Matrix.md`（稳定 ID + 12 字段） | **MISSING** | 文件不存在；`docs/aiqe/v1.6/` 仅有审计目录 `_audit/`（`baseline-audit-G1-G3.txt` + 本报告），无任何交付物；`git ls-files \| rg "V1.6\|Requirement-Code-Test"` **0 命中** |
| 2 | 机器可读 `docs/aiqe/v1.6/traceability/requirements.yaml` + CI 校验 P0/P1 覆盖率 | **MISSING** | 目录/文件不存在（同上，0 命中） |
| 3 | `scripts/aiqe/check_traceability.py`（PR 描述/变更文件/矩阵映射/状态流转校验，缺失非零退出） | **MISSING** | `scripts/aiqe/` 仅 `run_dogfood.ps1`、`skill-clients.json`、`verify-skill-compat.ps1`（`git ls-files scripts/aiqe` 全量 3 行）；仓内 `rg check_traceability` 0 命中 |
| 4 | `.github/workflows/aiqe-v16-gates.yml`，拆 8 个 Job（traceability/lint-type/unit/integration/runtime-e2e/security-negative/migration/evidence-index），P0/P1 不得被路径过滤跳过 | **MISSING** | `.github/workflows/` 仅 9 个既有 workflow（`git ls-files .github`）；`backend-clean-checkout` 只有 `pytest -q`（`main-quality-gate.yml:181-187`）与 Alembic 单头（`:150-161`），**无 runtime-e2e / security-negative / evidence-index / traceability job**；`ai-delivery-policy.yml` 无任何追踪校验（`:24-32` 为 CI 分类契约测试，`:100-142` 为分支/凭据扫描） |
| 5 | Branch Protection/Ruleset：禁直推、必需 check、≥1 名非作者 Reviewer、CODEOWNERS 领域批准、禁管理员绕过（或审计日志披露） | **MISSING** | 无 ruleset 导出文件（`Get-ChildItem -Recurse -Include *ruleset*,*branch-protection*` 0 命中）；仓内文档自述**未启用** branch protection：`work-logs/batch-242-runner-lock-and-image-gate-leader-verdict.md:43`（“仓库未启用 GitHub branch protection，required 语义由 `audit-ai-pr.ps1` 固定三角色名承载”）、`:51`（记入 ADR-0031 决策 10） |
| 6 | `.github/CODEOWNERS` 映射 security / execution runtime / agent-learning / driver-device / migration-CI | **MISSING** | `git ls-files .github` 10 个文件，**无 CODEOWNERS**；全仓 `rg -l CODEOWNERS` 0 命中 |
| 7 | 每个 Runtime E2E 生成机器可读 `evidence-index.json`（commit SHA/CI Run/环境/TestRun/ExecutionJob/NodeRun/Assertion/Artifact/结果），缺关键 ID 不计通过 | **MISSING** | 无生成器、无示例（`rg "evidence-index\|evidence_index"` 0 命中）。最接近物是 `work-logs/p0-evidence/*.json` + `scripts/ci/check-p0-ready.ps1:4-17`（P0-1..5 证据 + 过期即失败），但**不含** TestRun/ExecutionJob/NodeRun/Assertion/Artifact 任何 ID |
| 8 | PR 模板强制：Issue/Requirement ID、业务结果、正式入口、调用链、真实组件与 Mock 边界、成功/失败/异常测试、风险、安全影响、迁移影响、证据链接、Reviewer；空字段由 Traceability Gate 拒绝 | **PARTIAL** | `.github/pull_request_template.md:34-39` 有“Issue: #”，`:62-71` 有“命令/退出码/CI 链接”证据表，`:93-96` 有安全三项，`:58` 有“相关测试…通过”；**缺** 业务结果、正式入口、调用链、真实组件与 Mock 边界、风险、独立 Reviewer 身份；且**无任何 Gate 解析 PR 正文**（步骤 8 后半句 MISSING） |
| 9 | 每 Sprint 工程交付差距报告（计划数/IMPLEMENTED/VERIFIED/ACCEPTED/BLOCKED/未覆盖测试/未关联证据/Gate 失败项） | **MISSING** | 仓内无 V1.6 Sprint 差距报告；`work-logs/` 的 batch QA 报告只报用例通过数，不含矩阵状态分布与未关联证据清单 |
| 10 | 版本末由**非原开发团队**对 **release tag 精确 commit** 做独立验收，逐条引用矩阵与 CI/E2E 证据 | **MISSING** | 无 release tag 对应验收记录；本审计为基础审计（G8）之一，V1.6 尚未形成 release commit；V16-001 仍在途（见 §0.2） |

### 3.2 规格“必须交付的自动化资产”清单核对

| 交付物 | 存在 | 证据 |
|---|---|---|
| `scripts/aiqe/check_traceability.py` | ❌ | 目录仅 3 个文件 |
| `.github/workflows/aiqe-v16-gates.yml` | ❌ | workflows 仅 9 个既有文件 |
| `.github/pull_request_template.md`（等价更新） | ⚠️ 部分 | 存在但缺 6 类字段（§3.1 #8） |
| `.github/CODEOWNERS` | ❌ | 0 命中 |
| Branch Protection / Ruleset 导出或生效证明 | ❌ | 0 命中；文档自述未启用 |
| `docs/aiqe/v1.6/V1.6-Requirement-Code-Test-Evidence-Matrix.md` | ❌ | 0 命中 |
| `docs/aiqe/v1.6/traceability/requirements.yaml` | ❌ | 0 命中 |
| `evidence-index.json` 生成器与示例 | ❌ | 0 命中 |
| 每 Sprint 工程交付差距报告 | ❌ | 0 命中 |

### 3.3 验收标准对照（§8.7 验收标准 6 条）

| 验收标准 | 判定 | 说明 |
|---|---|---|
| V16-001～025、TC-AIQE-001～010 每条 P0/P1 要求唯一追踪记录；覆盖率 100% | ❌ | 无矩阵、无 Requirement ID；TC ID 还存在 §2.2 的四义冲突 |
| 对缺 Requirement ID / 测试路径 / 证据声明 / 非作者 Reviewer 的模拟 PR，CI 必须失败 | ❌ | 无 Check 解析 PR 正文；`audit-ai-pr.ps1:17-21,129-141` 只校验三个 required check 名，`:106-113` 拉取的 PR JSON 无 `reviews`/`author` 字段，全文无 reviewer 校验 |
| 故意删 Runtime Gate / 用 helper 直调替代 Worker / 把 QUEUED 当 PASS / 把 E2E 改为 body 断言 → Gate 必须失败或被独立验收拒绝 | ❌（且反例已被写成结论） | 上述四种“作弊”在 HEAD 上**全部实际存在**：无 Runtime Gate（§3.1 #4）、`tc_aiqe_service_acceptance.py:73-83` helper 直调、`tc_aiqe_unblocked_verify.py:146` QUEUED=PASS、`test_tc_aiqe_001_010.py:62` body 断言——**没有一个 Gate 会失败**，且 `work-logs/P1-closeout.md:36` 已把它记成“9/10 PASS” |
| P0/P1 不得仅凭开发者自测 ACCEPTED；须显示独立验收人 | ❌ | 无 reviewer 字段/无审批记录载体 |
| release tag / CI Run / commit SHA / Run/Job/Assertion/Artifact 可互相追溯；抽 10 条 100% | ❌ | 无 evidence-index；`main-quality-gate.yml:181-187` 只 `pytest -q`，**不上传任何测试报告/JUnit/覆盖率 artifact**（`upload-artifact` 仅出现在非 required 的 `pr-check.yml:89,218,270`、`api-regression.yml:86`、`responsive-e2e.yml:86` 等） |
| BLOCKED/SKIP/UNKNOWN/无证据不计通过率并披露 | ❌ | 无通过率计算器；E2E 以 skipped 记入 CI |

### 3.4 已存在的“近似治理资产”（可复用，不等价于本 Issue 交付物）

| 资产 | 覆盖能力 | 与 V16-025 的差距 |
|---|---|---|
| `C-CONDITIONS.md` + `scripts/git/audit-cconditions.ps1` | 条件台账（Open/In-Progress/Closed/Deferred，关闭必须带 PR/commit，一致性校验脚本只读检查孤儿/重复/缺证据） | 面向批次 C 条件，非 `Requirement ID ↔ 代码 ↔ 入口 ↔ 测试 ↔ 证据`；无机器可读 YAML；无覆盖率口径 |
| `work-logs/p0-evidence/*.json` + `scripts/ci/check-p0-ready.ps1:4-17` | 机器可读证据 + **fail-closed**（缺失/过期/不通过 → 退出码 1）+ `-SelfTest` | 仅 P0-1..5 五条；无 TestRun/ExecutionJob/NodeRun/Assertion/Artifact ID；未接入 required 汇总 |
| `scripts/ci/test_batch59_quality_contracts.py:25-46,49+`（由 `ai-delivery-policy.yml:24-32` 执行） | 现成的 **workflow gate 契约测试 harness**（断言 job/step 存在且命令 fail-closed） | 只断言既有 3 个 required job 的步骤，**没有任何 AIQE V16 gate 契约** |
| `.github/pull_request_template.md:41-48` 架构护栏 | 条件触发式必答项（“不适用请勾选”） | 仅限 AITDE 翻版问题，不是追踪字段 |

### 3.5 V16-025 gaps（可逐条复核）

- **G8-025-01（P0）追踪矩阵与机器可读清单完全缺失**（步骤 1/2，交付物 6/7）。
- **G8-025-02（P0）`check_traceability.py` 完全缺失**（步骤 3，交付物 1）；仓库无任何脚本解析 PR 正文中的 Issue/Requirement ID。
- **G8-025-03（P0）AIQE V16 CI Gate 完全缺失**（步骤 4，交付物 2）：无 `aiqe-v16-gates.yml`；required 工作流无 `runtime-e2e`/`security-negative`/`evidence-index`/`traceability` job；无 JUnit/覆盖率/证据 artifact 上传。
- **G8-025-04（P0）无 branch protection/ruleset 生效证明，且文档自述未启用**（步骤 5，交付物 5）：required 语义仅由本地手工 `scripts/git/audit-ai-pr.ps1:17-21` 承载，需人工执行，可跳过。
- **G8-025-05（P0）无“非作者 Reviewer”与 CODEOWNERS 双重校验**（步骤 5/6，交付物 4）：无 CODEOWNERS；`audit-ai-pr.ps1` 不读取 `reviewDecision`/`reviews`。
- **G8-025-06（P0）PR 模板字段不全且**无 Gate 拒绝空字段**（步骤 8）：缺业务结果/正式入口/调用链/真实组件与 Mock 边界/风险/Reviewer。
- **G8-025-07（P0）无 `evidence-index.json` 生成器与示例**（步骤 7，交付物 8）。
- **G8-025-08（P0）无 Sprint 差距报告与统计口径**（步骤 9，交付物 9）；现有 batch QA 报告不满足“未覆盖测试/未关联证据/Gate 失败项”字段。
- **G8-025-09（P0）无版本末独立验收对 release tag 精确 commit 的记录**（步骤 10）。
- **G8-025-10（P0）追踪链的 ID 基座不成立**：无 Requirement ID 体系；`TC-AIQE-001..010` 四义冲突（§2.2）。
- **G8-025-11（P0）反例未被拦截**：规格验收标准第 3 条列出的 4 种作弊在当前代码中**全部真实存在**且无 Gate 失败（见 §3.3 第 3 行）；更严重的是这些反例已被写成正式收口结论——`work-logs/P1-closeout.md:36` “9/10 PASS”、`work-logs/aiqe/tc-aiqe-unblocked-20261113.md` “TC-003/008 由 BLOCKED → PASS”。即“独立验收检查必须拒绝”这一条在流程上**已经失败过一次**，而没有任何机制阻止其入库。
- **G8-025-12（P1）无“缺失关键 ID 不计通过”的执行点**：现有 E2E/服务脚本即使无 Job/Assertion/Artifact 也判 PASS（`tc_aiqe_service_acceptance.py:52` 默认 PASS）。
- **G8-025-13（P1）仓库治理声明与可执行事实不一致**：`AGENTS.md:210-231`（§4.1 当前状态表 + §4.3 已知差距）把 required checks 描述为阻断层，而 `work-logs/batch-242...:43` 自述未启用 branch protection —— 治理文档本身需要按“证据可用”重述，否则 V16-025 的“生效证明”永远无法达成。

### 3.6 最小整改建议（不含补丁代码）

1. **`scripts/aiqe/check_traceability.py`（新）**：入参 `--pr-body`、`--base/--head`、`--matrix docs/aiqe/v1.6/traceability/requirements.yaml`；校验（a）PR 正文含 V16 Issue + Requirement ID；（b）每个 ID 在 YAML 存在且 `code[]` 路径真实存在、`test.command` 与路径存在、`evidence` 非空、`owner != reviewer`、`status ∈ {IMPLEMENTED,VERIFIED,BLOCKED,ACCEPTED}`；（c）变更文件必须落在某个 ID 的 `code[]` 前缀内。任一缺失 `exit 1`。**只做映射，不得据文件名推断实现**（写入脚本 docstring 与自测用例）。
2. **矩阵双份**：`docs/aiqe/v1.6/traceability/requirements.yaml`（机器可读，按规格 8.7 的 12 字段）+ `docs/aiqe/v1.6/V1.6-Requirement-Code-Test-Evidence-Matrix.md`（人类视图，由 YAML 生成，禁止手改双份漂移）。V16-001..025 + TC-AIQE-001..010 每行必须写 `production_entry` 与 `mock_boundary`。
3. **`.github/workflows/aiqe-v16-gates.yml`**：8 个 job；`traceability` 调步骤 1 脚本；`runtime-e2e` 起 Postgres + 后端，用 `tests/e2e/aiqe/conftest.py` 的正式入口跑 TC 成功/失败路径；`evidence-index` 收集 `*.json` 并 `actions/upload-artifact`；P0/P1 用 tag/label 强制运行（禁止 paths 过滤）。`migration` job 复用现有 `alembic heads` + `upgrade/downgrade/upgrade` 演练。
4. **`.github/CODEOWNERS`**：`test-platform-v2/backend/app/aiqe/security/**`、`.../services/{execution_service,node_executor,job_consumer,lease,dag_scheduler}.py`、`.../agents/**`、`.../drivers/**`、`alembic/**`、`.github/**` 分别映射到责任团队。
5. **`.github/pull_request_template.md`**：按规格 8.7 第 8 条补齐字段（业务结果/正式入口/调用链/真实组件与 Mock 边界/成功-失败-异常测试/风险/安全影响/迁移影响/证据链接/独立 Reviewer），并在 `check_traceability.py` 中对空字段非零退出。
6. **`scripts/git/audit-ai-pr.ps1`**：`gh pr view --json` 增加 `author,reviews,reviewDecision`；新增“至少 1 条非作者 APPROVED”与“PR 正文追踪字段齐全”校验；P0/P1 分支强制。同步在 `scripts/ci/test_batch59_quality_contracts.py` 增加 `aiqe-v16-gates.yml` 的 gate 契约断言（复用现成 harness）。
7. **ruleset 生效证明**：导出 ruleset JSON 到 `deploy/github/ruleset-main.json` + 生效截图/`gh api repos/.../rulesets` 输出；若平台侧确认未启用，必须在 `docs/adr/` 记录“管理员不可绕过限制 + 替代控制（required checks 由 CI 汇总名强制）”并按规格 8.7 第 5 条披露。
8. **`scripts/aiqe/build_evidence_index.py`（新）**：扫描 TC 证据 JSON → 汇总 `evidence-index.json`（commit SHA、CI Run ID、环境、TestRun/ExecutionJob/NodeRun/Assertion/Artifact ID、结果）；缺任一关键 ID 时该 TC 记 `UNVERIFIED` 并使脚本非零退出（复用 `check-p0-ready.ps1` 的 fail-closed 形状与 `-SelfTest` 习惯）。
9. **每 Sprint 差距报告**：`docs/aiqe/v1.6/sprints/sprint-N-gap.md`，字段固定为 计划/IMPLEMENTED/VERIFIED/ACCEPTED/BLOCKED/未覆盖测试/未关联证据/Gate 失败项，由步骤 8 的统计输出生成。
10. **必须新增的负向测试（针对治理 Gate 本身）**：
    - `scripts/aiqe/test_check_traceability.py`（新）：缺 Requirement ID、缺 test 路径、缺 evidence、`reviewer == owner`、`status=garbage`、PR 正文为空 → 全部必须 `exit != 0`；**再加**一条“变更文件不在任何 code[] 前缀内”用例；
    - gate 契约测试（加入 `test_batch59_quality_contracts.py`）：删除 `runtime-e2e` job、把 runtime 步骤替换为 `pytest -k unit`、移除 `--junitxml` → 必须失败；
    - 反作弊静态测试：`tests/e2e/aiqe/**` 中出现 `locator("body").count()`、`pytest.mark.skipif`、`TestRun(`、`dag_scheduler.mark_running(`、`execute_node(` → 必须失败（对照 G8-017-01/03/06/11）；
    - “BLOCKED 不计通过”用例：构造一条 BLOCKED 证据，断言汇总脚本非零退出且报告中 `passed` 不增加。

---

## 4. 交叉发现（两 Issue 共同根因）

1. **执行链证据普遍是“手工拼装”**：`evidence_camel_test5.py`/`evidence_local_20.py`/`tc_aiqe_service_acceptance.py` 三个“证据生成器”都采用 `ORM 建 TestRun → 手工 create_node_runs → mark_running → execute_node → complete_node → finalize_run`。这条链**绕过了 ExecutionJob/Worker claim/lease/fencing/Assertion Gate/Finalize 的正式实现**，产出的 `docs/aiqe/evidence/*.json`（含 `run_id`、`status=COMPLETED`、`assertions: 7`）在“有 Run/Node/Assertion”这一层看起来完整，却**没有任何 ExecutionJob 与 Worker 消费证据** —— 规格 §0.2.8 第 139 条、§0.2.3 第 90 条明确把这种形态列为不可作为验收证据。
2. **“跳过/阻塞 = 通过”在多处系统化存在**：E2E 的 `skipif`（`test_tc_aiqe_001_010.py:21`）、服务脚本的 `exit 0 when blocked>0`（`tc_aiqe_service_acceptance.py:343`）、required 工作流无报告产物（`main-quality-gate.yml:181-187`）。三者叠加使 CI 绿灯无法区分“执行成功”和“根本没执行”。
3. **治理层“声明式”而非“可执行式”**：`AGENTS.md` §4.1/§4.2 把 required checks 描述为不可绕过层，但仓库自述未启用 branch protection（`work-logs/batch-242...:43`），required 判定实际依赖本地手工脚本。V16-025 的核心正是把这种“模板提醒”升级为“自动 Gate”，当前完全未开始。
4. **可复用资产被闲置**：`C-CONDITIONS.md` + `audit-cconditions.ps1`、`work-logs/p0-evidence/*.json` + `check-p0-ready.ps1`、`test_batch59_quality_contracts.py` 三套机制已经具备“状态机 + 证据 + fail-closed + 契约测试”的全部要素，V16-025 应在其上扩展（新增 AIQE 目录与 ID 命名空间），避免再造第四套。

---

## 5. 可复核命令

```powershell
$R = "F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6"
$B = Join-Path $R "test-platform-v2\backend"

# 基线
git -C $R rev-parse HEAD
git -C $R rev-list --left-right --count origin/main...HEAD      # 期望 0 0
git -C $R status --short                                        # 本报告范围内无条目

# V16-017：伪 E2E 仍然存在
Select-String -Path "$B\tests\e2e\aiqe\test_tc_aiqe_001_010.py" -Pattern 'goto\(|locator\("body"\)|skipif|importorskip|scope="session"'
# 期望命中 :21 :45 :61 :62

# V16-017：服务脚本直调 + BLOCKED 当成功
Select-String -Path "$B\tests\e2e\aiqe\tc_aiqe_service_acceptance.py" -Pattern 'NotImplementedError|return 0 if summary|dag_scheduler\.|TestRun\('
Select-String -Path "$R\test-platform-v2\backend\scripts\aiqe\evidence_camel_test5.py","$R\test-platform-v2\backend\scripts\aiqe\evidence_local_20.py" -Pattern 'node_executor\.execute_node|run = TestRun\(|finalize_run'

# V16-017：QUEUED 即 PASS 与回归通道无 Job
Select-String -Path "$B\tests\e2e\aiqe\tc_aiqe_unblocked_verify.py" -Pattern '== "QUEUED"'
Select-String -Path "$B\app\aiqe\services\regression_service.py" -Pattern 'edges|depends_on|status="QUEUED"|ExecutionJob'
Select-String -Path "$B\app\api\v1\aiqe_regressions.py" -Pattern 'launch_run|create_regression_request'

# V16-017：“9/10 PASS” 结论与其证据文件
Select-String -Path "$R\work-logs\P1-closeout.md" -Pattern '9/10|TC-AIQE'
Get-Content "$R\work-logs\aiqe\evidence\tc-aiqe-test-20261113.json" -Encoding UTF8
Get-Content "$R\work-logs\aiqe\evidence\tc-aiqe-unblocked-20261113.json" -Encoding UTF8
git -C $R log --oneline -- "$B/tests/e2e/aiqe/test_tc_aiqe_001_010.py"   # 期望仅 1 条：447b2f6de

# V16-017：CI 完全不跑 AIQE E2E
Select-String -Path "$R\.github\workflows\*.yml" -Pattern 'tests/e2e|aiqe' | Measure-Object   # 期望 Count=0

# V16-025：交付物全部缺失
git -C $R ls-files ".github"                       # 期望 10 行，无 CODEOWNERS
git -C $R ls-files "scripts/aiqe"                  # 期望 3 行，无 check_traceability.py
git -C $R ls-files | Select-String -Pattern 'CODEOWNERS|aiqe-v16|check_traceability|requirements\.yaml|evidence-index|V1\.6|Requirement-Code-Test'   # 期望 0 命中
Get-ChildItem "$R\docs\aiqe\v1.6" -Recurse -Force   # 期望仅 _audit\baseline-audit-G1-G3.txt

# V16-025：required 语义只在本地手工脚本，且不校验 reviewer / PR 正文
Select-String -Path "$R\scripts\git\audit-ai-pr.ps1" -Pattern 'requiredChecks|statusCheckRollup|review|author'   # 期望无 review/author 命中
Select-String -Path "$R\work-logs\batch-242-runner-lock-and-image-gate-leader-verdict.md" -Pattern 'branch protection'  # 期望 :43 :51

# V16-025：required 工作流无报告/证据产物
Select-String -Path "$R\.github\workflows\main-quality-gate.yml" -Pattern 'pytest -q|junitxml|upload-artifact'   # 期望仅 pytest -q
```

---

## 6. 附录：本报告引用文件清单（仓库根相对路径）

| 文件 | 用途 |
|---|---|
| `test-platform-v2/backend/tests/e2e/aiqe/test_tc_aiqe_001_010.py` | V1.5 被点名的伪 E2E（未修） |
| `test-platform-v2/backend/tests/e2e/aiqe/tc_aiqe_service_acceptance.py` | L2 直调服务层“验收”（3 BLOCKED，exit 0 fail-open） |
| `test-platform-v2/backend/tests/e2e/aiqe/tc_aiqe_unblocked_verify.py` | L2 API+ORM 混合（QUEUED 即 PASS） |
| `test-platform-v2/backend/scripts/aiqe/evidence_camel_test5.py` | 直调 `node_executor` 伪执行链证据 |
| `test-platform-v2/backend/scripts/aiqe/evidence_local_20.py` | 同上 + 登记查询 |
| `test-platform-v2/backend/app/api/v1/aiqe_runs.py` | 正式 Launch 入口（TC 套件应使用） |
| `test-platform-v2/backend/app/aiqe/services/run_launch.py` | `launch_run` |
| `test-platform-v2/backend/app/aiqe/services/regression_service.py` | 回归 Run 无 Job + DAG 依赖被清空 |
| `test-platform-v2/backend/app/api/v1/aiqe_regressions.py` | 回归创建端点（不 launch） |
| `test-platform-v2/backend/app/api/v1/aiqe_automation.py` | 回归终态同步（不启动） |
| `test-platform-v2/backend/tests/test_aiqe_execution_pipeline.py` | 现有唯一 Launch→Job→Consumer 基座（Mock Driver） |
| `test-platform-v2/backend/tests/test_aiqe_run_api_v14.py` | 真实 API 入口 + ExecutionJob 断言 |
| `test-platform-v2/backend/tests/test_aiqe_sports_vertical.py` | 假执行器测试，占用 TC ID |
| `test-platform-v2/backend/pytest.ini` | `testpaths=tests` → e2e 文件被收集并 skip |
| `.github/pull_request_template.md` | 追踪字段缺口 |
| `.github/workflows/main-quality-gate.yml` | required 工作流：无 AIQE gate、无报告产物 |
| `.github/workflows/ai-delivery-policy.yml` | 交付策略门禁：无 traceability |
| `scripts/git/audit-ai-pr.ps1` | required 语义仅在本地手工脚本 |
| `scripts/ci/test_batch59_quality_contracts.py` | 可复用的 gate 契约测试 harness |
| `work-logs/P1-closeout.md` | “9/10 PASS” 假完成结论（`:36`） |
| `work-logs/aiqe/evidence/tc-aiqe-test-20261113.json`、`tc-aiqe-unblocked-20261113.json` | 已入库 TC 证据（缺 job/assertion/artifact ID，含 QUEUED 假 PASS） |
| `work-logs/aiqe/tc-aiqe-test-20261113.md`、`tc-aiqe-unblocked-20261113.md` | TC 结论页（“BLOCKED → PASS”表述） |
| `scripts/ci/check-p0-ready.ps1` + `work-logs/p0-evidence/*.json` | 可复用的 fail-closed 证据机制 |
| `C-CONDITIONS.md` + `scripts/git/audit-cconditions.ps1` | 可复用的状态机台账 |
| `work-logs/batch-242-runner-lock-and-image-gate-leader-verdict.md` | “未启用 branch protection”自述 |
| `docs/aiqe/v1.6/_audit/baseline-audit-G1-G3.txt` | 同批审计基线（工作树漂移说明） |
