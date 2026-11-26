# V1.6 Stage 1–5 发布窗口计划（建议）

> 需产品/运维/QA 共同确认后执行；每个窗口都必须产出可校验 artifact，否则阶段保持 NOT_PROVEN。

| 阶段 | 建议窗口 | 动作 | 验收证据 |
|---|---|---|---|
| Stage 1 Shadow | 2026-11-28 10:00–12:00 | 生产旁路 shadow，不对外生效 | Run/Job/Assertion artifact + 与线上结果对比 |
| Stage 2 Dogfood | 2026-11-29 14:00–18:00 | 内部账号 dogfood | 内部账号 Run 清单 + 缺陷记录 |
| Stage 3 小流量 | 2026-12-01 10:00–12:00 | 5% 流量 | 流量比例、错误率、回滚演练记录 |
| Stage 4 扩量 | 2026-12-03 10:00–16:00 | 50% 流量 | 监控/告警、P95、错误率 |
| Stage 5 GA | 2026-12-05 10:00 | 100% + 发布公告 | 发布 commit、镜像 digest、独立验收签署 |

## 每阶段前置
- CI required checks 全绿、PR 已 squash 合并；
- 生产 PG 只读 role 硬化（`default_transaction_read_only=on`、`statement_timeout=5s`）；
- 回滚脚本与值班人确认；
- 证据写入 `governance/production-evidence.json` 对应 stage 并置 PASS。
