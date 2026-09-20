# Batch 269 — QA 报告

> **QA (🔍)** | Date: 2026-09-20 | Verdict: **PASS**
> 档位：轻量批次（纯证据/纯文档）。门禁按"变更域 = 文档/证据"执行。

## 可执行门禁

| 命令 | 结果 |
|------|------|
| `pwsh scripts/git/scan-common-bugs.ps1` | HARD **0** / WARN 344（= 主干基线；退出码 2 因存在 WARN 且未 `-FailOnWarning`，按门禁规则非阻断） |
| `pwsh scripts/git/audit-cconditions.ps1` | hard errors **0** / warnings **0**；closed rows 197（missing evidence 0） |
| `python -m ruff check app --select S110,S112,B904,RUF012 --statistics` | **11 / 7 / 32 / 18**（app 代码零改动，仅作 S7/S8 复发核对） |
| `python scripts/ci/classify_ci_changes.py work-logs/batch-269-landing-acceptance-report.md C-CONDITIONS.md work-logs/evidence/batch-269/drill-three-versions-platform-reuse.json` | `{"backend": false, "frontend": false, "reasons": ["documentation", "governance"]}` → 前后端重测试跳过（本批无代码变更），三个 required 汇总仍给明确结论 |
| `GET /api/v1/execution-jobs/{46,51}/evidence/verify` | `verdict=verified`，逐文件 sha256 对账通过 |
| `python -m pytest`（B1–B4 引用 10 个测试文件，今日主干） | **154 passed / 1 skipped**，与验收报告 ①–⑥ 引用数字逐项一致（无漂移） |
| 只读 SQL + 驱动调用面取证（⑦ 复用数字来源） | 演练窗口内新增复用事件 **0** 条、新增版本任务 **0** 个 |
| `POST /api/v1/version-tasks`（本机试点平台，写操作仅落本地试点库） | `suggested 16 → 20`（建任务即写 4 条建议事件）、`hit_rate 0.625 → 0.5` → **埋点是活的**，证明 `C269-1` 的修法不需改平台代码 |
| 生产只读复核（`df` / `crontab -l` / `ls -l` / `tail` / `docker ps`） | 见 §A3 |

## 逐条验证（A1–A6）

### A1 3 版本演练全绿 ✅

`work-logs/evidence/batch-269/drill-three-versions-platform-reuse.json`：

```
checks  : database_ok / dataset_meets_target / fingerprint_present / node_online /
          target_reachable / account_slot_configured = **全 true**
dataset : module_prefix=体育, counts={api:50, web:30}, shortfall={api:0, web:0}, meets_target=true
slo     : consecutive_passing=3, overall_reuse_hit_rate=0.625, meets_all=**true**
          versions[0..2].meets = {plan_within_2h:true, execution_within_3h:true,
                                  evidence_complete:true, reuse_hit_rate_50pct:true}
```

**判定内核全绿，但两项口径经取证受限**（`evidence/batch-269/reuse-metric-provenance-20260920.md`）：

1. **没有版本记录**：§5 第 ⑦ 条字面要求"看版本记录"，而驱动只 `POST /execution-jobs`、不 `POST /version-tasks` → 16.1/16.2/16.3 **没有 `version_task` 行**；
2. **复用率非本次自产**：三个版本读数完全相同（16/10）；演练窗口（12:50 后）新增复用事件 **0** 条、新增版本任务 **0** 个，41 条事件全部写于 **00:26–00:32**（Batch 268 端到端验证）。

→ ⑦ 的"执行时长/证据完整/连续 3 版"三项为本次自产，**版本记录与复用率不是**；结论由 **✅ 达成** 下调为 **⚠️ 判定内核达成、口径受限**，`C269-1` 上调 **P1**。

驱动 stdout（`drill-attempt5-driver-stdout.txt`，逐字；原始报告写在 Batch 268 工作区的 `work-logs/evidence/batch-268/drill-three-versions-platform-reuse.json`——268 已合入，故本批把该报告与该 stdout 一并归档到 `evidence/batch-269/`）：

```
[version 16.1] jobs=[46, 47] evidence_complete=True
[version 16.2] jobs=[48, 49] evidence_complete=True
[version 16.3] jobs=[50, 51] evidence_complete=True
报告已写入 …\batch-268\drill-three-versions-platform-reuse.json
{"meets_all": true, "consecutive_passing": 3}
```

### A2 6 个 job 都可取且证据可校验 ✅

| job | 类型 | 结果 | 证据文件 |
|-----|------|------|---------|
| 46 / 48 / 50 | 接口（50 条用例） | **50/50 passed** | 101 |
| 47 / 49 / 51 | Web（30 条用例） | **29/30** | 61 |

**唯一失败项**（三轮一致）：`case:605`「从首页点击联赛入口进入联赛页」，失败步骤 `index 4 expect_visible selector=text=Scores`，`console_errors=[]`。
**判定**：断言锚点在目标页不成立（点进去后页面没有 `Scores` 文案），不是网络/链路问题 → 登记 `C269-4`（P3）。

### A3 ⑧ 生产水位与告警（只读） ✅

```
df -h /            → 74%（< 80% 达标）
crontab -l         → */15 * * * * /opt/cameltv-ops/disk-watermark-check.sh >> /var/log/cameltv-disk-alert.cron.log 2>&1
ls -l /opt/cameltv-ops/ → disk-watermark-check.sh (700) / smtp.env (600, root)
/var/log/cameltv-disk-alert.log  → 13:15:01 / 13:30:01 均 OK used=74% threshold=85%
grep ALERT  → 5 行（人为降阈值 70%/50% 强制触发时确实进 ALERT 分支）
grep MAIL_OK → 1 行（邮件通道实测成功）
docker ps   → 8 个容器全 healthy
```

**边界（如实写）**：没有把生产盘撑到 85%。因此"85% 能触发告警"的证据 = 阈值分支实测走到 `ALERT` + 邮件通道 `MAIL_OK` + 用户确认收到自检邮件，三段合成，不等于"盘真的到过 85%"。

### A4 送达确认 ✅

用户 2026-09-20 回复「QQ 邮箱有收到 cameltv 邮件自检」。**如实标注**：日志中的收件人（`DISK_ALERT_TO`）是 Gmail 地址（脱敏后仅核对前 4 字符），发信账号是 QQ 邮箱；用户在 QQ 侧看到该邮件。若要求投递地址本身就是 QQ 地址，改一行配置即可——本批不改生产配置。

### A5 C 条件收口与新增 ✅

- **关闭 12 条**（`C261-1` / `C262-1` / `C262-3` / `C264-1` / `C264-2` / `C266-1` / `C266-2` / `C266-4` / `C267-1` / `C267-3` / `C268-1` / `C268-2`），每条带 PR/commit/证据；
- **保持 Open 1 条**：`C265-1`——其解除条件要求「通过**版本任务流程**跑 ≥3 个版本」，本轮演练只登记执行任务，未满足；实现转 `C269-1`（P1）；
- **新增 4 条**（`C269-1`~`C269-4`），每条带解除条件；
- `audit-cconditions.ps1` 复核 hard errors 0 / warnings 0（无孤儿 ID、无缺证据）。

**三处必须一起读的口径**（已同时写进验收报告）：① **⑦ 的复用率不是这 3 个版本产生的**（取证：窗口内新增事件 0 条、新增版本任务 0 个；数字来自演练前的平台读数 → `C269-1` 上调 P1）；② **人日 = 执行者输入**（`--person-hours-per-version 1.5`，文档明确该值不可自动测量）；③ 控制面 = 本机试点实例（被测系统是真实 Test5）。

### A6 报告如实列出缺口 ✅

验收报告附录 C 列了 5 条"没做到/没验证"：真机未跑、⑦ 口径限制、未在生产/测试环境跑 3 版本、`C269-2~4` 未修、⑧ 未把盘撑到 85%。

## 缺陷列表

| # | 严重级 | 描述 | 状态 |
|---|:------:|------|------|
| D1 | **P1** | **演练的 3 个版本没有产生复用数据**：驱动不调 `POST /version-tasks`，窗口内新增复用事件 0 条 / 新增版本任务 0 个；三版读到的 `0.625` 是演练前平台已有读数（Batch 268 端到端验证写入）→ 取证见 `evidence/batch-269/reuse-metric-provenance-20260920.md` | 🆕 登记 `C269-1`（P1） |
| D2 | P2 | 驱动无瞬断容错、崩溃不落盘 → 本批 4 次尝试全部白跑（每次约 20 分钟） | 🆕 登记 `C269-2` |
| D3 | **P1** | 节点在平台返回 4xx/5xx 时**一次性退出**（`call()` 抛 `SystemExit(2)`，`_loop` 只捕获 `TransportDown`）→ 进程无声消失、任务滞留 pending | 🆕 登记 `C269-3`（P1，根因已复现：`evidence/batch-269/node-exit-root-cause-20260920.md`） |
| D4 | P3 | Web `case:605` 断言 `text=Scores` 与目标页不符（3 轮唯一失败项） | 🆕 登记 `C269-4` |

> 说明：D1–D4 均**不是**本轮引入的回归——D1/D2/D3 是本轮"真跑"才暴露的既有能力缺口，D4 是 Batch 264 建集时的断言选取问题。

## bug-guard「未关闭已知风险」表核对（三问）

1. **本批是否新增清单中任一项？** 否——本批**零代码改动**，无新增"用户输入→出网/落盘/执行代码"路径。
2. **本批是否修复/关闭任一项？** 清单相关项 `C267-3`（埋点未接线）由 Batch 268 修复（PR #487 / `27c11e80`），本批记录；S1–S6 状态不变（S6 部分关闭，内核级隔离属 `C259-2`）。
3. **新增路径是否过铁律？** 不适用。**S7/S8 复发核对**：`S110/S112/B904/RUF012` = 11/7/32/18，与 2026-09-18 基线与 09-19 复核逐项一致 → 未复发；`S110/S112` 仍在棘轮覆盖范围外（`C262-4`）。

## CI 分层核对

本批只改 `work-logs/**` 与 `C-CONDITIONS.md` → 属"文档/证据"域，前后端重测试按规则跳过，三个 required 汇总仍会给出明确成功结论。**不把 required 名称存在当作重测试已跑**；本批的正确说法是"没有代码变更需要重测试"。

## 发布建议

状态：**READY**　必修复：0　建议修复：0（4 条新缺口已登记为 C 条件，不阻断本批）

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 5h / ~4h | 0/0/3/1 | 4（演练重跑） | 环境（本机试点实例的连接稳定性）+ 设计（验收驱动缺容错与增量落盘） | ① 长跑驱动必须先做"崩溃可恢复"再谈数字；② 平台单进程 + SQLite 的试点实例要配 `--timeout-keep-alive`，节点侧要有自愈；③ 给每版落盘，别把 20 分钟押在最后一次写文件上 |

**技能使用**: `cameltv-bug-guard`（三问 + S7/S8 复发核对）。
