# 落地方案最终验收报告 v3（Batch 270 更新）

> **交付方**: Codex（Agent Team 流水线） ｜ **验收方**: 用户 ｜ **日期**: 2026-09-20
> **清单来源**: `docs/platform-refactor/10-landing-plan-task-backlog.md` §5 的 9 条
> **前版**: `work-logs/batch-269-landing-acceptance-report.md`（v2，Batch 269 合入 `8e4b5550`）——**本版只更新变化项**，未变部分以 v2 为准

## 1. 本版只改一件事：§5 第 ⑦ 条从"口径受限"变成"达成"

| 项 | v2（Batch 269） | v3（Batch 270） |
|----|-----------------|-----------------|
| 版本记录 | ❌ 驱动只登记执行任务，3 个版本**没有 `version_task` 记录** | ✅ 驱动逐版本建版本任务：`version_task` **10 / 11 / 12**（20.1 / 20.2 / 20.3） |
| 复用命中率的来源 | ⚠️ `0.625` 是**演练前平台既有读数**（窗口内新增事件 **0** 条） | ✅ **本版本自产**：每版 `suggested 4 / adopted 2 / rejected 2` → 本版命中率 **0.5**（窗口内新增建议事件 12 条 + 决策 12 条） |
| ⑦ 判定 | ⚠️ 判定内核达成、口径受限 | ✅ **达成**（`meets_all=true`、`consecutive_passing=3`，且分子分母可追溯到被验收的 3 个版本） |
| `C265-1` | Open（解除条件要求走版本任务流程） | ✅ **Closed**（本版满足其字面解除条件） |
| `C269-1` / `C269-2` | Open（本版新增的两条 P1/P2） | ✅ **Closed**（本版修复并回归） |

## 2. §5 九条现状（v3）

| # | 验收项 | 结论 | 说明 |
|---|--------|------|------|
| 1 | 菜单只剩 4 个入口 + 专家区 | ✅ 达成 | 同 v2（模型层断言 + a11y 28 passed；无浏览器级"数导航项"E2E） |
| 2 | 本地节点一条命令可用 | ✅ 达成 | 同 v2；本批演练再次由 `cameltv-node up` 认领并跑完 6 个 job（52–57）。**但节点自愈仍缺** → `C269-3`（P1） |
| 3 | 试点用例真实跑通且证据可查 | ✅ 达成（真机外） | 本批复现同一结论：接口 **50/50 ×3**、Web **29/30 ×3**、每版 `evidence_complete=true` |
| 4 | 断线不丢任务 | ✅ 达成 | 同 v2（租约回收 + attempt 递增，18 例） |
| 5 | 恶意 URL / spec 全被拒 | ✅ 达成 | 同 v2（17+10+12+20 例；B1–B4 引用测试已在 269 复跑逐项一致） |
| 6 | 「改了 X 要跑哪些」可用 | ✅ 达成 | 同 v2（13 例 + 前端视图；中位 4.0ms） |
| 7 | 体育连续 3 个版本达成 SLO | ✅ **达成** | 见 §3；数字来自被验收版本自身 |
| 8 | 生产盘水位可控 | ✅ 达成 | 同 v2（`df -h /` 74%；85% 告警固化 + 自检邮件已确认送达） |
| 9 | 备份可恢复 | ✅ 达成 | 同 v2（手册 + 两次演练逐项一致） |

**九条全部达成**（③ 限定"真机外"）。仍保留的口径说明见 §4。

## 3. 第 ⑦ 条：本版证据

驱动 stdout（`evidence/batch-270/drill-driver-stdout.txt`）：

```
[version 20.1] task=10 jobs=[52, 53] evidence_complete=True reuse=2/4 (platform:version-task-delta)
[version 20.2] task=11 jobs=[54, 55] evidence_complete=True reuse=2/4 (platform:version-task-delta)
[version 20.3] task=12 jobs=[56, 57] evidence_complete=True reuse=2/4 (platform:version-task-delta)
{"meets_all": true, "consecutive_passing": 3}
```

| 版本 | 版本记录 | 执行任务（接口 / Web） | 本版自产 建议/采纳/否掉 | 本版命中率 | 证据完整 |
|------|:--------:|------------------------|:-----------------------:|:----------:|:--------:|
| 20.1 | `version_task` **10** | 52 → 50/50 ｜ 53 → 29/30 | **4 / 2 / 2** | **0.5** | ✅ |
| 20.2 | `version_task` **11** | 54 → 50/50 ｜ 55 → 29/30 | **4 / 2 / 2** | **0.5** | ✅ |
| 20.3 | `version_task` **12** | 56 → 50/50 ｜ 57 → 29/30 | **4 / 2 / 2** | **0.5** | ✅ |

四条 DoD：`plan_within_2h`（人日 1.5，执行者口径）/ `execution_within_3h`（0.043/0.038/0.042 h）/ `evidence_complete`（3/3 真实）/ `reuse_hit_rate ≥50%`（**0.5，自产**）→ **三版全绿**，`consecutive_passing=3`。

**怎么复现**：

```bash
cd test-platform-v2/backend
python scripts/drill_three_versions.py --project-id 1 --environment-id 12 \
  --account-slot sports-tester-01 --base-url http://127.0.0.1:8124 \
  --target-url http://camel-api-gateway05.svc.elelive.cn/camel-service \
  --web-target-url https://camelive-g3-test5.elelive.cn/ \
  --username <账号> --password <口令> --versions 3 --version-prefix 20. \
  --module-prefix 体育 --reuse-mode version-task \
  --decisions-json work-logs/evidence/batch-270/reuse-decisions-20260920.json \
  --person-hours-per-version 1.5 --out drill.json
```

## 4. 仍然成立的口径说明（不因"达成"而消失）

1. **复用决策是人工判断**：`adopted=[赛事列表, 直播入口]`、`rejected=[登录冒烟, 结算流程]`，理由是"本版本实际执行的 50 接口 + 30 Web 是否覆盖该建议条目"（试点集不含登录/结算用例）。规则与理由写在 `evidence/batch-270/reuse-decisions-20260920.json`，**你可以覆盖该文件后复跑**；驱动不会自动判定。
2. **人日仍是执行者输入**（`--person-hours-per-version 1.5`），平台无法自动测量（文档明确）。
3. **控制面仍是本机试点实例**（`127.0.0.1:8124` + 试点 SQLite），节点是本机 `cameltv-node`，**被测系统是真实 Test5**。
4. **Web 仍 29/30**：唯一失败项 `case:605`（断言 `text=Scores`）三轮一致 → `C269-4`（P3）仍在 Open，不因本批"达成"而消失。
5. **前端全量与 a11y 本批未复跑**（无 `node_modules`，且本批零前端改动）——沿用 2026-09-19 主干复跑记录。

## 5. 未决条件（v3）

**本批关闭**：`C269-1`（复用口径自产）、`C269-2`（驱动容错/增量落盘）、`C265-1`（字面解除条件已满足）。
**本批新增**：`C270-1`（P2：版本号冲突时平台返回 500，应为业务码）。
**仍 Open 且与本结论相关**：`C269-3`（P1 节点遇 4xx/5xx 退进程——本批演练前再次现场复现）、`C269-4`（P3 Web `case:605`）、`C258-1`（P1 真机）、`C259-2`（P1 内核沙箱）、`C260-1`/`C262-2`/`C262-4`/`C263-1`/`C266-3`/`C267-2` 等（见 v2 §4.3 与 `C-CONDITIONS.md`）。

## 6. 需要你验收的结论

1. §5 九条**全部达成**（③ 真机外）；⑦ 的复用数字**由被验收的 3 个版本自己产生**（0.5 ≥ 50%），不再依赖别的流程留下的读数；
2. 达成伴随 §4 的 5 条口径限制，尤其第 1 条（人工决策）与第 3 条（本机试点控制面）；
3. 仍有 3 条与本主题直接相关的 Open：`C269-3`（P1）、`C270-1`（P2）、`C269-4`（P3）。
