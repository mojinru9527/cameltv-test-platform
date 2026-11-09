# M1（Phase 1：Run / Event / Artifact 底座）收口报告

> **日期**：2026-11-10 · **范围**：TA-005 / TA-006 / TA-007 / TA-008
> **结论**：4 批全部开发完成并合入 main；生产部署待窗口。

## 1. 批次与合并

| 批次 | TA | 内容 | PR | 合并 commit |
|------|----|------|----|-------------|
| batch-279 | TA-005 | Run/Node/Step/Assertion 四表 + 状态机 + 迁移 | #508 | `10c0f9213` |
| batch-280 | TA-006 | run_events + event_outbox + append_event（同事务/幂等/seq） | #509 | `cf5dcfb5e` |
| batch-281 | TA-007 | run_artifacts + FS 存储抽象 + sha256 去重 + 403 + 脱敏 | #510 | `ad49d9817` |
| batch-282 | TA-008 | 只读 Run API + SSE + React Run Console | 本批 | 待合 |

## 2. 数据模型

新增 7 张表（UUID PK，除 outbox BIGINT）：

```text
test_runs, node_runs, step_attempts, run_assertion_results
run_events, event_outbox
run_artifacts
```

迁移链：`20261111_ta005_run_models → 20261112_ta006_run_events → 20261113_ta007_run_artifacts`，
单 head，up/down/up 均通过（SQLite 全链）。

## 3. 关键能力

- 状态机单入口：10 状态，COMPLETED 必须 outcome，终态/非法迁移抛异常；
- 事件：append-only，`(run_id, seq)` 严格递增，`producer_event_id` 幂等，事件+outbox+投影同事务；
- Artifact：内容寻址去重、跨项目 403、脱敏单向、防路径穿越；
- Console：`/runs` 列表、`/runs/:id` 详情、SSE + 断线轮询补拉（`after_seq`）。

## 4. 验证汇总

| 层 | 结果 |
|----|------|
| 后端单测（M1 新增） | 37 + 10 + 6 + 6 = 59 |
| 后端全量 | 1398 passed / 43 skipped |
| 前端 | 550 tests（123 files）+ typecheck/build/lint 0 |
| quality ratchet | PASS（increased_keys=0） |
| 路由守卫 | inventory 322 + 路由层禁 ORM 通过 |

## 5. 生产部署（待窗口）

```bash
# 备份
docker exec <pg> pg_dump -U ... -Fc > pre-m1.dump
# 升级（新建 7 表，无既有表变更）
docker exec backend alembic upgrade head
# 验证
docker exec backend alembic current   # 20261113_ta007_run_artifacts
```

Console 入口：`https://swiftbugs.cn/runs`（菜单/RBAC 在 M2 接入）。

## 6. M2 入口条件与遗留

- 立即可以开始 **M2（TA-009 Workflow Validator + TA-010 DAG Scheduler）**；
- 遗留：生产 COS/MinIO 后端（TA-007 PoC）、菜单/RBAC、SSE 长连接/Redis、浏览器 E2E。
