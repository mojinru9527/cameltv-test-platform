# Dev Kanban — Batch 268 复用命中率埋点接线

> Batch: 268 | 模式: **完整** | Scope: `test-platform-v2/backend/app,test-platform-v2/backend/scripts,test-platform-v2/backend/tests,work-logs,C-CONDITIONS.md`

| # | 任务 | Product | PM | Design | Dev | QA | Leader |
|---|------|:-------:|:--:|:------:|:---:|:--:|:------:|
| 1 | 排查接线缺口（代码 + 生产双证） | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 | 建任务写建议事件（条目粒度，不吞异常） | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 3 | 驱动读平台指标（人工输入降级为回退） | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4 | 回归测试 4 例 + 既有 69 例不回归 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 5 | API 级端到端（建任务 → suggested>0 → adopted → hit_rate 可算） | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 6 | 发现并修复「命中率可 >1」（C268-2）+ 对历史数据免疫 + 补齐 QA/Leader 工件 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## 关键事实

- 接线前：`suggested` 恒 0（生产 0 行）→ ⑦ 的复用率不可测。
- 接线后（API 实测）：建任务 → `suggested=4`（4 条建议条目）；记 1 条 adopted → `hit_rate=0.25`、`meets_50pct=false`（数字真实，不美化）。
- 修 C268-2 后（API 实测）：新任务 6/7/8 = suggested 4 / adopted 3 / rejected 1（75%）；聚合 `hit_rate 0.625`（≤1）、`meets_50pct true`；守卫前写入的历史脏数据已不影响聚合（生产该表 0 行）。
