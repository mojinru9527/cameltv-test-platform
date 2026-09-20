# Batch 268 PRD — 复用命中率埋点接线（修 C267-3）

> **Product** | Date: 2026-09-20 | 档位：**完整批次**
> 触发器：平台行为变更（建任务新增埋点写入）+ 测量链路变更（驱动改读平台指标）。

## 1. 问题（Batch 267 发现，已登记 C267-3 / P1）

```
B3-4 定义了 reuse_metrics_service.record_suggestion（写 decision='suggested'），但**全仓无调用点**；
带出建议的 GET /version-tasks/knowledge/reuse 不写埋点；决策接口只接受 adopted|rejected。
⇒ hit_rate = adopted / suggested 的 suggested 恒为 0 ⇒ 命中率恒 0。
生产实证：reuse_suggestion_event 0 行，而同期已有 6 个版本任务、1 条版本知识记录。
影响：§5 第 ⑦ 条「复用命中率 ≥50%」无法被测量。
```

## 2. 本批行为

1. **建任务时写建议事件**：`version_task_service.create_task` 在创建任务后，把"上版知识记录带出的**每一条**复用建议"写成 `decision='suggested'` 事件（`suggestion_ref=knowledge:<记录id>:<条目标题>`）。不吞异常——埋点失败即暴露。
2. **驱动改读平台指标**：`drill_three_versions.py` 未显式给 `--reuse-suggested/--reuse-adopted` 时，调用 `GET /version-tasks/knowledge/reuse-stats` 取真实数字，并在报告里标注 `reuse_source`（platform/operator）。

## 3. 非目标

- ❌ 不改 `get_reuse_suggestions` / `GET knowledge/reuse` 的既有返回契约（Batch 260 的约束仍守）；
- ❌ 不改 `reuse_suggestion_event` 的表结构（无 Schema 变更）；
- ❌ 不替用户做"采纳/否掉"的判断（决策仍由人工/前端写入）。

## 4. 验收判据

| # | 判据 |
|---|------|
| A1 | 建任务 → 产生 `decision='suggested'` 事件（每条建议 1 条），`reuse_stats.suggested > 0` |
| A2 | 记录 adopted 后 `hit_rate = adopted/suggested` 与 `meets_50pct` 可判定 |
| A3 | 无上版知识记录时**不产生**建议事件（不虚增分母） |
| A4 | 驱动在无人工输入时读平台指标；平台不可用时回退 (0,0) 并标注来源 |
