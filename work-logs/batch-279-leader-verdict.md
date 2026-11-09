# Batch 279（M1 / TA-005）— Leader Verdict

> **部门**：🎯 Leader · **日期**：2026-11-10

## 判决

# ✅ APPROVED

**理由**：

- TA-005 验收 A1–A8 全绿：状态机单入口 + 非法迁移异常 + 四表 ORM + ExecutionJob 关联；
- 迁移在 SQLite 全链与“预建/遗留/生产”三种场景都有明确处理，且 downgrade 可重跑；
- 全量回归 `1376 passed / 43 skipped`，ratchet `increased_keys=0`；
- 设计决策 D-279-1..5 有据可查，未改任何现有 API/表，风险可控。

## M1 进度

```text
M1-1 batch-279 TA-005 Run 模型 + 状态机        ✅ 本批
M1-2 batch-280 TA-006 Event/Outbox             ⏭ 下一批
M1-3 batch-281 TA-007 Artifact Manager         ⏭
M1-4 batch-282 TA-008 React Run Console MVP    ⏭
```

## 放行条件

1. PR required checks 全绿后 squash 合入 main；
2. batch-280 必须从合并后的 main 切出（AGENTS 2.1.1）；
3. 生产部署留给 M1 整体窗口（本批不改运行路径）。

## 风险提示

- 生产 PG 首次执行本迁移会创建四表；需在部署窗口内跑一次
  `alembic upgrade head` 并确认 `\dt test_runs`；
- 旧 `assertion_results` 仍属 execution_runtime，M2 前不合并（D-279-1）。
