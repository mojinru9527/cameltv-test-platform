# Batch 268 PM 计划

> **PM** | Date: 2026-09-20

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| 1 | 建任务写建议事件（条目粒度） | `version_task_service.create_task` | ✅ |
| 2 | 驱动改读平台指标 + 标注来源 | `drill_three_versions.py` | ✅ |
| 3 | 回归测试 4 例（接线 / 命中率 / 无记录不虚增 / 驱动读数与回退） | `tests/test_batch268_reuse_metric_wiring.py` | ✅ |
| 4 | API 级端到端验证 | `evidence/batch-268/reuse-metric-wired-e2e-20260920.json` | ✅ |
| 5 | C 条件更新（关闭 C267-3 待合入）与看板 | `C-CONDITIONS.md` | ✅ |
