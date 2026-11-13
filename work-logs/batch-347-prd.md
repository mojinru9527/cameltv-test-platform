# Batch 347（M10-347 代码部分：AIQE 进程内执行器）— PRD / Design / Dev

> mode: **full**（执行链路变更）· 分支：`feature/batch-347-aiqe-executor` · 基线：`origin/main 84b378bd9`
> 背景：M9-R4——AIQE `ExecutionJob` 无消费者，`cameltv_node` 也不识别 `node_run_id`，导致 TC-003 仅服务层证据。

## 1. 目标

1. 新增 AIQE NodeRun 进程内执行器（`http` driver），把 `ExecutionJob(payload.node_run_id)` 真正执行并回写；
2. 新增消费者线程：原子认领（pending→running+租约）、执行、回写 job/节点、失败落库；
3. 开关默认关闭（`AIQE_INPROCESS_EXECUTOR_ENABLED=false`），Test 显式开启；
4. 保留边界：UI/设备节点不在本批（`UNSUPPORTED_DRIVER` → 节点 BLOCKED，不假绿）。

## 2. 设计

| 点 | 实现 |
|----|------|
| 执行器 | `aiqe/services/node_executor.py`：读取 NodeRun.input_ref（url/method/headers/params/json/expected_status），`HttpDriver.execute` |
| 消费者 | `aiqe/services/job_consumer.py`：claim（SQL `UPDATE ... WHERE status='pending'` 原子）+ run_job + 租约 300s |
| 图谱 | dispatcher 新增 `graph=` 写入 payload；缺失时按 NodeRun 合成最小图（兼容旧 job） |
| 调度回写 | `mark_running` → 执行 → `complete_node`（attempt 由 batch-340 持久化） |
| 生命周期 | `lifespan` 在开关开启时启动守护线程，关闭时 join |
| 失败语义 | driver 异常 → FAILED/DRIVER_ERROR；状态不符 → FAILED/STATUS_MISMATCH；缺 url → INPUT_INVALID；未知 driver → BLOCKED/UNSUPPORTED_DRIVER |

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | http 节点真实执行 → 节点 PASSED、Run PASS、attempt PASSED | `test_consumer_executes_http_node` |
| A2 | 500 → FAILED/STATUS_MISMATCH、Run FAIL、job failed | `test_consumer_failure_marks_node_and_job` |
| A3 | 认领幂等（第二次为空） | `test_claim_is_idempotent` |
| A4 | 非 AIQE job 不被认领 | `test_non_aiqe_job_not_claimed` |
| A5 | 不支持的 driver → BLOCKED，不假绿 | `test_blocked_driver_marks_node_blocked` |
| A6 | Test 实例真实 DAG 执行（health 200 / 404 失败） | 部署验证记录（PR 评论/证据） |

## 4. 非目标 / 风险

- 非目标：UI/Playwright 节点、设备节点（需 runner 节点/真机，M10-347 剩余部分）；
- 风险：进程内执行受控制面资源限制 → 默认关闭，仅 Test 开启；后续由独立 runner 节点承接。
