# Batch 347 真实 DAG 执行验证（Test 实例，2026-11-13）

> **环境**：`aiqe-test-backend` 镜像 `release-m14-b347`，`AIQE_INPROCESS_EXECUTOR_ENABLED=true`（poll 2s）
> **结论**：AIQE `ExecutionJob` 首次被真实消费并回写——PASS/FAIL 两条 DAG 均按预期收口，M9-R4（http 节点）解除。

## 1. 验证方式

容器内脚本创建 Run + `http` 节点 → `schedule(dispatch=enqueue_node_run)` 生成 ExecutionJob →
进程内消费者认领执行 → 回写 `complete_node`。脚本：`/tmp/tc_b347_real_dag.py`（一次性验证用）。

## 2. 结果

```json
{
  "results": [
    {
      "tag": "ok",
      "run": "B347-ok-447ed97b",
      "status": "COMPLETED",
      "outcome": "PASS",
      "node_status": "PASSED",
      "attempts": ["PASSED"],
      "job_status": "success"
    },
    {
      "tag": "fail",
      "run": "B347-fail-892fac43",
      "status": "COMPLETED",
      "outcome": "FAIL",
      "node_status": "FAILED",
      "attempts": ["FAILED"],
      "job_status": "failed",
      "job_error": "STATUS_MISMATCH"
    }
  ]
}
```

- PASS：`GET /api/v1/open/health`（expected 200）→ 节点 PASSED、Run PASS、attempt PASSED、job success；
- FAIL：`GET /api/v1/not-exists`（expected 200）→ 节点 FAILED、Run FAIL、job failed/STATUS_MISMATCH；
- 执行后清理：Run/Node/StepAttempt 删除（Job 记录保留为审计行，状态 success/failed）。

## 3. 覆盖与边界

| 项 | 状态 |
|----|------|
| http/API 节点进程内执行 | ✅ |
| attempt 时间线（batch-340） | ✅ |
| 失败不假绿 | ✅ |
| UI/Playwright 节点 | ⏳ 仍需 runner 节点（真机/内网） |
| 设备节点（Android/iOS） | ⏳ 需设备 |

## 4. 结论

M9-R4 的 http 部分闭环；M10-347 剩余部分（UI/真机 runner）继续等待设备环境。
