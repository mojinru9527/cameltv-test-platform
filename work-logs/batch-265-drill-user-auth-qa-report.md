# Batch 265 — QA 报告

> **QA (🔍)** | Date: 2026-09-19 | Verdict: **PASS**
> 档位：轻量批次（QA 驱动脚本修复）

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 4（A1–A4） | 4 | 0 | 0 |

## 可执行门禁

| 命令 | 退出码 | 摘要 |
|------|:------:|------|
| `python -m pytest tests/test_batch265_drill_user_auth.py -q` | 0 | **3 passed** |
| `python -m ruff check app --select F821` | 0 | 无 F821 |
| `pwsh scripts/git/scan-common-bugs.ps1` | 2 | **HARD 0** / WARN 344（=主干基线，非阻断） |
| `pwsh scripts/git/audit-cconditions.ps1` | 0 | hard errors 0 / warnings 0 |

## 修复验证（实跑，不是单测代替）

```
# 修复前（Batch 264 记录）
drill_three_versions.py … --node-token <节点令牌>
  → 预检 6/6 通过 → 401 Unauthorized (POST /api/v1/execution-jobs)

# 修复后（本批）
drill_three_versions.py … --username drill-admin --password *** --versions 3 --module-prefix 体育
  → [version 16.1] jobs=[4,5] evidence_complete=True
  → [version 16.2] jobs=[6,7] evidence_complete=True
  → [version 16.3] jobs=[8,9] evidence_complete=True
  → {"meets_all": false, "consecutive_passing": 0}

SLO 明细（报告 evidence/batch-265/drill-three-versions.json）：
  16.1/16.2/16.3：plan_within_2h=true(1.5h) · execution_within_3h=true(0.006~0.007h)
                  · evidence_complete=true · reuse_hit_rate_50pct=false（--reuse-suggested/adopted 未提供 → null）
```

**结论**：401 缺陷已消除，3 个版本可连续跑完且证据完整；**唯一未达标项是复用命中率**，它是 B3-4 的"复用建议→采纳"人工/特性指标，本机这次演练没有走版本任务流程，故无真实数字，**我没有编数字填进去**（详见 `C265-1`）。

## 逐条验证（A1–A4）

### A1 回归测试 ✅
`tests/test_batch265_drill_user_auth.py`：① `--user-token` → Bearer + X-Project-Id 且不含 agent 头；② 只给节点令牌 → `SystemExit` 且提示含 `--user-token`/`node-token`；③ 源码调用点必须是 `headers = _auth_headers(args)`，且不得再出现 `headers = {"X-AI-Agent-Token"`。

### A2 实跑 ✅
见上（1 版探路 + 3 版验收本体）。

### A3 边界 ✅
未改 `app/api/v1/execution_jobs.py` 的权限模型；仓库内未写入任何 Test5 凭据（命令里的密码只用于本机临时环境，且是脚本参数而非落盘）。

### A4 门禁 ✅
见上表。

## 缺陷列表

| # | 严重级 | 描述 | 状态 |
|---|:------:|------|------|
| D1 | **P1** | 驱动用节点令牌调用户端点 → 401，⑦ 条按文档命令无法跑通（C264-3） | ✅ 本批修复并实跑验证 |
| D2 | P3 | `--out` 指向不存在目录时崩溃（实跑命中） | ✅ 本批修复（`parent.mkdir(parents=True, exist_ok=True)`） |
| D3 | P2 | 复用命中率无法由驱动自动观测，需版本任务流程产生真实建议/采纳数 | ⏳ 登记 `C265-1` |
| D4 | **P1** | 试点集执行 payload 不带可执行细节：API 侧 50/50 裸 `GET <base>/`→404；Web 侧 `steps=[]` 且 30 张截图逐字节相同（空白页）→ **30/30 是空过**，不能作为通过证据 | ⏳ 登记 `C265-3`；证据 `evidence/batch-265/pilot-payload-vacuous-execution-20260919.json` |

> **勘误**：本批早期曾把「Web 30/30 在真实 Test5 上通过」当作结论，经证据复核（截图 SHA256 相同、steps 为空）**该结论作废**。

## 追加验证：用**正确的可执行 payload** 重跑 8 条试点用例（§5 第 ③ 条）

为区分"驱动缺陷"与"链路缺陷"，用同一平台+同一节点、按 `drill_b1_e2e.py` 证明过的 payload 结构重投任务：

| 任务 | 结果 | 证据 |
|------|------|------|
| API job **12**（5 条真实体育业务端点） | **completed，passed 5 / failed 0**，evidence_files 11 | `/ee/version/version`（$.data 含『打包时间』）· `/ee/stream_stats/quality` · `/ee/sports_live/list_faceoff` · `/ee/sports_live/living_group_match` · `/ee/sports_live/player/hot-players` |
| Web job **11**（3 条真实页面） | **completed，passed 3 / failed 0**，evidence_files 7 | 截图 `sp-web-1.png` 967912B / `sp-web-2.png` 1089762B / `sp-web-3.png` 451633B，**SHA256 互不相同**（真实渲染） |

对照：job **10** 用随机 GET 端点只过 3/5，失败两条是 **HTTP 200 但信封码 `$.status=400`**（缺参数）——按仓库"envelope 码 vs HTTP 码"约定，这是**正确判定**，换成信封 200 的端点后 5/5。

**结论**：执行链路（平台登记 → 节点认领 → 真打 Test5 → 上传证据 → 完整性校验）**可用**；缺口只在 driver 的 payload 构造（`C265-3`）。证据文件：`evidence/batch-265/pilot-8cases-real-test5-20260919.json`。

## bug-guard「未关闭已知风险」表核对（三问）

**1) 本批是否新增清单中任一项？** 否——只改 QA 驱动的鉴权参数与输出路径。
**2) 本批是否修复/关闭任一项？** 关闭 `C264-3`（验收链路 401）。
**3) 新增路径是否过铁律？** 驱动新增了"账号密码登录"这一步：**凭据只作参数**，不写文件、不入日志、不入仓库；测试用假令牌断言，不接触真实平台凭据。

## 发布建议

状态：**READY**　必修复：0　建议修复：0

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 2h / ~1h | 0/1/1/1 | 1 | 需求（驱动凭据口径未与端点权限对齐）+ 健壮性（输出目录） | 写调用平台的脚本前，先读目标端点的 `Depends(require_permission(...))`，确认是用户态还是节点态 |
