# Batch 270 — QA 报告

> **QA (🔍)** | Date: 2026-09-20 | Verdict: **PASS**
> 档位：轻量批次（验收驱动 + 证据；平台零改动）

## 可执行门禁

| 命令 | 结果 |
|------|------|
| `python -m pytest tests/test_batch270_drill_version_task_flow.py -q` | **10 passed**（本批新增） |
| `python -m pytest`（本批相关 9 个套件：270 / 261_slo / 261_pilot_dataset / 265 / 268 / 260_reuse / 266 / 261_evidence / 258_job_protocol） | **95 passed**，无回归 |
| `python -m ruff check scripts/drill_three_versions.py tests/test_batch270_*.py tests/test_batch265_*.py tests/test_batch268_*.py` | All checks passed |
| **真实 3 版本演练**（本批核心证据，`--reuse-mode version-task`） | `meets_all=true`、`consecutive_passing=3`，三版各 `reuse=2/4`（**本版本自产**） |
| `pwsh scripts/git/scan-common-bugs.ps1` | HARD **0** |
| `pwsh scripts/git/audit-cconditions.ps1 -RequireLatestBatch` | hard errors **0** / warnings **0** |
| `pwsh scripts/git/dev-gate.ps1 -RepositoryPath (Get-Location).Path`（G0–G2 一键门禁） | **`GATE_RESULT=PASS_WITH_WARN`**（机械项通过，WARN 需人工复核）：`scan-common-bugs` HARD 0 · `ruff F821` All checks passed · `QUALITY_RATCHET=PASS` · backend dependency audit 过 · `npm run typecheck` 过 · `npm run lint` 过 · `NPM_AUDIT_RATCHET=PASS`（baseline 16 / current 16 / new 0）· `found 0 vulnerabilities` · 路由层守卫 4 passed。**首次运行因新检出无 `node_modules` 报 `'tsc'/'eslint' is not recognized`，执行 `npm ci`（850 包）后通过**——该失败是环境缺依赖，不是本批代码问题（本批零前端改动） |

## 逐条验证（A1–A6）

### A1 每版都有版本记录，且复用数字按本版本增量 ✅

驱动 stdout（`evidence/batch-270/drill-driver-stdout.txt`，逐字）：

```
[version 20.1] task=10 jobs=[52, 53] evidence_complete=True reuse=2/4 (platform:version-task-delta)
[version 20.2] task=11 jobs=[54, 55] evidence_complete=True reuse=2/4 (platform:version-task-delta)
[version 20.3] task=12 jobs=[56, 57] evidence_complete=True reuse=2/4 (platform:version-task-delta)
{"meets_all": true, "consecutive_passing": 3}
```

报告（`evidence/batch-270/drill-three-versions-version-task-20260920.json`）：

| 版本 | 版本任务 | 执行任务 | 自产 建议/采纳/否掉 | 本版命中率 | 累计读数（对照） | 证据 | 执行时长 |
|------|:--------:|----------|:-------------------:|:----------:|:----------------:|:----:|:--------:|
| 20.1 | **10** | 52(api 50/50) · 53(web 29/30) | **4 / 2 / 2** | **0.5** | 24/12 (0.5) | ✅ | 0.043h |
| 20.2 | **11** | 54(api 50/50) · 55(web 29/30) | **4 / 2 / 2** | **0.5** | 28/14 (0.5) | ✅ | 0.038h |
| 20.3 | **12** | 56(api 50/50) · 57(web 29/30) | **4 / 2 / 2** | **0.5** | 32/16 (0.5) | ✅ | 0.042h |

平台侧可独立复核（试点库）：`select id,version from version_task where version like '20.%'` → **10/11/12** 三行；
`reuse_suggestion_event` 在演练窗口内新增 **12 条**（3 版 × 4 条建议）与 **12 条决策**（3 版 × 2 采纳 + 3 版 × 2 否掉）。

> 与 Batch 269 的对照：上一批驱动在该窗口新增 **0** 条事件、**0** 个版本任务——本批修好了这个口径缺口。

### A2 决策落在本版本的建议 ref 上 ✅

每版 `decisions.missing = []`（即 4 条建议标题全部匹配到本版本的 `suggestion_ref`），
`adopted=[赛事列表, 直播入口]`、`rejected=[登录冒烟, 结算流程]`；判定规则与理由写在
`evidence/batch-270/reuse-decisions-20260920.json`（操作者口径，**用户可覆盖后复跑**）。

**如实标注**：`adopted/rejected` 是**人工判断**（本批由 Codex 代执行，依据"本版本执行范围是否覆盖该建议条目"）。
驱动不会自动判定"是否复用"；平台侧 `record_decision` 的守卫也会拒绝"没被带出过"的建议（本批 `missing=[]` 即证明 ref 对得上）。

### A3 SLO 由本版本数字算出 ✅

```
per-version meets = {plan_within_2h: True, execution_within_3h: True,
                     evidence_complete: True, reuse_hit_rate_50pct: True}   ×3
consecutive_passing = 3 / consecutive_required = 3
overall_reuse_hit_rate = 0.5      meets_all = true
```

### A4 重试语义 ✅

| 用例 | 断言 |
|------|------|
| `test_retry_recovers_from_transient_transport_error` | `ReadError` ×2 后第 3 次成功 → 返回 200（瞬时错误必须重试） |
| `test_retry_does_not_mask_http_4xx` | HTTP 400 → **只调 1 次**（真问题不重试） |
| `test_retry_retries_get_5xx_but_not_post_5xx` | GET 503 → 3 次；**POST 503 → 1 次**（避免重复登记任务） |
| `test_retry_raises_after_exhausting_attempts` | 重试用尽后仍抛 `httpx.TransportError`（不吞错） |

### A5 增量落盘与冲突提示 ✅

- `test_run_versions_uses_version_task_delta` 断言跑完一版即落盘且 `partial=true`；
- `test_version_task_conflict_gives_actionable_error` 断言版本号冲突时给出含 `--version-prefix` 的可操作提示；
- `test_batch265_drill_user_auth.test_report_path_parent_is_created` 由"匹配源码字符串"改为**验行为**（`_write_report` 建父目录）——见缺陷 D3 说明。

### A6 无回归 ✅

相关 9 个套件 **95 passed**；其中 2 个既有用例因实现细节变化而更新（D3/D4），语义不变。

## 缺陷列表

| # | 严重级 | 描述 | 状态 |
|---|:------:|------|------|
| D1 | P1 | 驱动不建版本任务 → 被验收版本无版本记录、复用数字来自别处（`C269-1`） | ✅ 本批修复（逐版本建任务 + 增量取数 + 记录决策） |
| D2 | P1→P2 | 驱动无瞬断容错、崩溃不落盘（一次 `ReadError` 白跑 20 分钟）（`C269-2`） | ✅ 本批修复（有界重试 + 每版落盘）+ 4 例单测 |
| D3 | P3 | **实跑命中**：`version_task` 的 `(project_id, version)` 唯一约束冲突时平台返回 **500**（裸 `IntegrityError` 栈），不是 409/业务码 | ⚠️ 驱动侧已给可操作提示；**平台侧登记 `C270-1`（P2）**，证据 `evidence/batch-270/dup-version-500-finding-20260920.md` |
| D4 | P3 | 两个既有测试编码了旧实现细节（`Path(args.out).parent.mkdir(...)` 源码字符串、`client.get` 而非 `client.request`） | ✅ 按"测试陈旧 vs 真 bug"判定为**测试陈旧**并更新：前者改验行为，后者补 `request` 入口；语义断言未放松 |
| D5 | P3 | Web `case:605` 断言锚点不成立（本批仍 29/30，唯一失败项） | ⏳ 保持 Open（`C269-4`，P3），本批范围外 |

## bug-guard「未关闭已知风险」表核对（三问）

1. **本批是否新增清单中任一项？** 否——本批只改驱动脚本与其单测，未新增"用户输入 → 出网/落盘/执行代码"面（新增调用都是既有平台端点）。
2. **本批是否修复/关闭任一项？** `C269-1`（复用口径）与 `C269-2`（驱动容错）本批关闭；`C269-3`（节点遇 4xx/5xx 退出）**仍 Open**——本批实测中该节点在演练前再次消失（与 Batch 269 的根因一致），修复属下一批。
3. **新增路径是否过铁律？** 驱动的新增请求都带守卫语义：`adopted/rejected` 由平台校验（没带出过的建议会被拒 400）；版本号冲突本批已实测并给出可读失败。**不吞异常**：重试用尽仍抛错。

## CI 分层核对

本批改动 `test-platform-v2/backend/scripts/**` + `tests/**` + `work-logs/**` + `C-CONDITIONS.md` → 属后端域，按规则跑后端 required 汇总；前端域不涉及。不把 required 名称存在当作重测试已跑——本批的本地后端证据是上表 95 passed 与本批新增 10 例。

## 发布建议

状态：**READY**　必修复：0　建议修复：0（`C270-1`/`C269-3`/`C269-4` 已登记，不阻断本批）

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 3h / ~2.5h | 0/1/1/3 | 2（演练各重跑 1 次：版本号冲突、节点掉线） | 需求（验收条目的字面口径"版本记录"未在驱动里落地）+ 环境（本机试点实例的节点/连接稳定性） | ① 验收驱动要**先对齐验收条目字面要求**（"看版本记录"就必须建版本记录）；② 复用类指标必须问"分子分母谁产生"；③ 长跑驱动要支持换版本系列（唯一约束）与断点续跑 |

**技能使用**: `cameltv-bug-guard`（三问）。
