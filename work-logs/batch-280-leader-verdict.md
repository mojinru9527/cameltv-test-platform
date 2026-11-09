# Batch 280（M1 / TA-006）— Leader Verdict

> **部门**：🎯 Leader · **日期**：2026-11-10

## 判决

# ✅ APPROVED

**理由**：

- TA-006 验收 A1–A6 全绿：1000 事件 seq 连续、幂等、同事务投影、outbox 标记；
- 迁移与 279 同策略兼容预建/遗留，downgrade 可重跑；
- 全量 1386 passed / 43 skipped，ratchet PASS；
- 只新增表与服务，不改现有执行路径，风险低。

## M1 进度

```text
batch-279 TA-005 Run 模型      ✅
batch-280 TA-006 Event/Outbox  ✅ 本批
batch-281 TA-007 Artifact      ⏭
batch-282 TA-008 Run Console   ⏭
```

## 放行条件

1. PR checks 全绿后 squash 合入 main；
2. batch-281 从最新 main 切出；
3. SSE 端点/前端联调放 batch-282（本批只提供 list/dispatch 原语）。
