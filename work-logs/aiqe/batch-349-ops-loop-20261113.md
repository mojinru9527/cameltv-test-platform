# Batch 349 运营闭环实测（Test 实例，2026-11-13）

> **环境**：`aiqe-test-backend`（`release-m14-b349`）/ `aiqe_test` PostgreSQL / project 1
> **方式**：真实 HTTP（admin 登录，`menu:aiqe_runs` 门禁）+ 服务层清理

## 1. 结果

```json
{
  "project_id": 1,
  "candidate_id": "b5627575-4f4a-485d-94ba-388351bb4a50",
  "pattern": "batch-349-ops-44c3ba42",
  "after_evaluate": "benchmarked",
  "after_approve": "approved",
  "after_activate": "active",
  "pattern_key": "batch-349-ops-44c3ba42",
  "pattern_visible": true,
  "cleaned": true
}
```

## 2. 结论

- 学习候选运营闭环在隔离 Test 真实跑通：`draft → benchmarked（误报率 2%）→ approved → active`；
- `GET /aiqe/learning/bug-patterns` 能查到激活后的 `BugPattern`；
- 数据已清理，Test 库无残留。

## 3. 备注

- 本批同时登记 **M9-R4**（AIQE ExecutionJob 无消费者），见 `work-logs/aiqe/M9-R4-node-execution-gap.md`；
- M10-346/347/348 仍受外部环境阻塞，详见 `work-logs/M10-status-20261113.md`。
