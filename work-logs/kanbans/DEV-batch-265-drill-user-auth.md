# Dev Kanban — Batch 265 演练驱动用户凭据修复

> Batch: 265 | 模式: 轻量 | Scope: `test-platform-v2/backend/scripts,test-platform-v2/backend/tests,work-logs,C-CONDITIONS.md`

| # | 任务 | Product | PM | Dev | QA | Leader |
|---|------|:-------:|:--:|:---:|:--:|:------:|
| 1 | 复现并定位 401（驱动发 agent 头调用户端点） | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 | 驱动加 `--user-token` / `--username/--password`，调用点改用户态 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 3 | 回归测试 3 例 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4 | 真跑 1 版 + 3 版（Test5 真实入口） | ✅ | ✅ | ✅ | ✅ | ✅ |
| 5 | 顺带修 `--out` 目录崩溃；登记 C265-1 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 6 | 勘误空过结论 + 用正确 payload 重跑 8 条（③ 条本机端到端达成） | ✅ | ✅ | ✅ | ✅ | ✅ |

## 关键事实（供后续批次直接引用）

- `POST /api/v1/execution-jobs` = **用户端点**（`execution:manage`）；`X-AI-Agent-Token` 只用于 `ai_agent.py` 的认领/心跳/上报。
- 修复后实跑：`--versions 3` → 16.1/16.2/16.3 全部 `evidence_complete=True`；SLO 仅"复用命中率"未达标（未提供真实复用数）。
- 报告：`work-logs/evidence/batch-265/drill-three-versions.json`。
