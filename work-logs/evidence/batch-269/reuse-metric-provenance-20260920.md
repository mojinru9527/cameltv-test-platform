# Batch 269 证据 — ⑦ 复用命中率数字的**来源归属**（2026-09-20 只读取证）

> 为什么单独取证：Batch 269 的 3 版本演练报告里，三个版本的 `reuse_suggested/adopted` **完全相同**（16/10）。
> 这说明它不是"每版各产生一份"，但**它是从哪来的**必须说清楚——否则"达成"两个字会被读成"这 3 个版本自己产出了 50% 以上的复用率"，而事实不是。

## 1. 结论（先说结论）

**本次 3 个版本没有产生任何复用建议/采纳事件。** 驱动读到的 `suggested 16 / adopted 10 / hit_rate 0.625` 是**演练开始前平台里已有的读数**（写于 2026-09-20 00:26–00:32 的 Batch 268 端到端验证），被三个版本原样读了三次。

因此 ⑦ 的正确读法是：**判定内核给出 `meets_all=true`，且"复用命中率"是平台埋点的真实读数（≥50%）——但这三个版本没有参与产生该数字**；"每版自产自证"需要驱动改走版本任务流程 → `C269-1`（本批由 P2 上调为 **P1**）。

## 2. 驱动代码：演练根本没走"版本任务"路径

```
$ rg -n 'client\.(post|get|put)' test-platform-v2/backend/scripts/drill_three_versions.py
172:            resp = client.post(            # POST /api/v1/auth/login（取 JWT）
193:        resp = client.get("/api/v1/version-tasks/knowledge/reuse-stats", headers=headers)   # 只读指标
228:                created = client.post(     # POST /api/v1/execution-jobs（登记执行任务）
245:                    job = client.get(f"/api/v1/execution-jobs/{job_id}", …)
249:                verified = client.get(f"/api/v1/execution-jobs/{job_id}/evidence/verify", …)
```

驱动**没有**调用 `POST /api/v1/version-tasks`；而 Batch 268 把 `decision='suggested'` 的埋点写在 `version_task_service.create_task`（建版本任务）里。**没有建版本任务 → 不会写建议事件**。

## 3. 试点库取证（只读 SQL）

```sql
-- A. 演练窗口内（12:50 之后）新增的复用事件数
select count(*) from reuse_suggestion_event where created_at >= '2026-09-20 12:50';
--   → 0

-- B. 全部复用事件的时间跨度
select min(created_at), max(created_at), count(*) from reuse_suggestion_event;
--   → ('2026-09-20 00:26:08.963366', '2026-09-20 00:32:02.030705', 41)

-- C. 演练窗口内新增的版本任务数
select count(*) from version_task where created_at >= '2026-09-20 12:50';
--   → 0

-- D. 事件按决策分组（驱动后来读到的那份数据）
select decision, count(*) from reuse_suggestion_event group by decision;
--   → [('adopted', 19), ('rejected', 6), ('suggested', 16)]

-- E. 演练窗口内登记的执行任务
select id, kind, status, created_at from execution_jobs where id between 46 and 51 order by id;
--   → (46,'api','completed','2026-09-20 13:13:01.279176')
--      (47,'web','failed',   '2026-09-20 13:13:01.288664')
--      (48,'api','completed','2026-09-20 13:18:21.910192')
--      (49,'web','failed',   '2026-09-20 13:18:21.918212')
--      (50,'api','completed','2026-09-20 13:20:37.219775')
--      (51,'web','failed',   '2026-09-20 13:20:37.226784')
```

配套事实：`version_task` 表里 8 行（16.0 / 16.1 / 17.1–17.3 / 18.1–18.3）**全部创建于 00:25–00:32**，没有一行落在演练窗口。

## 4. 这份取证改变了什么

| 项 | 取证前的说法 | 取证后的准确说法 |
|----|-------------|-----------------|
| ⑦ 的复用命中率 | "平台累计口径，不是本次增量" | **"平台既有读数，本次 3 个版本产生 0 条事件"**——不是增量/累计之别，而是**本次没有参与生产** |
| ⑦ 的判定 | 达成 | **判定内核达成**（`meets_all=true`）不变，但"复用率由被验收的版本自产"这一层**未达成** → `C269-1` 由 P2 上调 **P1** |
| 演练覆盖面 | "3 版本 SLO 全绿" | 3 版本的**执行/证据/时长**三项是本次自产；**复用率不是** |

**没有撤回的结论**：接口 50/50 ×3、Web 29/30 ×3、6 个 job 的 `evidence_complete=true` 与 `verified`、`execution_hours` 三项——这些都是本次真实跑出来的，不受本取证影响。

## 5. 追加验证：埋点路径本身是活的（所以 `C269-1` 的修法可行）

为回答"是不是埋点又坏了"，在**本机试点平台**做了一次真实 API 调用（写操作只落在本地试点库）：

```python
before = GET /api/v1/version-tasks/knowledge/reuse-stats
r = POST /api/v1/version-tasks   {"title": "Batch269 proof: version-task 埋点路径", "version": "16.9", "environment_id": 12}
after  = GET /api/v1/version-tasks/knowledge/reuse-stats
```

```
BEFORE: {"suggested": 16, "adopted": 10, "rejected": 3, "hit_rate": 0.625, "meets_50pct": true, "pending": 3}
POST /version-tasks -> 200 {"code": 0, "msg": "ok", "data": {"id": 9, ... "version": "16.9", "status": "draft" ...}}
AFTER : {"suggested": 20, "adopted": 10, "rejected": 3, "hit_rate": 0.5,   "meets_50pct": true, "pending": 7}
```

**读法**：

1. 建版本任务**确实会写 4 条 `suggested` 事件**（16 → 20，正好 4 条复用条目），说明 Batch 268 的接线**是活的**——本次演练拿到 0 增量，纯粹是因为**驱动没有走这条路径**；
2. `hit_rate` 随之重算为 `adopted/suggested = 10/20 = 0.5`，仍然有界、`meets_50pct=true`；
3. 因此 `C269-1` 的修法（驱动逐版本建版本任务 + 操作者对每条建议记采纳/否掉 + 按版本区间取增量）**技术可行、且不需要改平台代码**——只改驱动的编排。

**副作用（如实登记）**：本次验证在**本地试点库**里留下 1 条版本任务（id=9，version 16.9，draft）与 4 条 `suggested` 事件，故此后本机 `reuse-stats` 的基准从 16/10 变为 20/10。生产库不受影响（生产 `reuse_suggestion_event` 仍为 0 行，见本报告 §3-⑧ 同批复核）。
