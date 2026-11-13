# M9-R4：AIQE 节点执行消费者缺口（2026-11-13 发现）

> **结论**：Test 实例开启 `WORKER_EXECUTION_ENABLED=true` 只启动了平台任务消费者（scheduler/ai_tasks），
> **没有 AIQE NodeRun 的消费者**；AIQE DAG 派生的 `ExecutionJob(kind=api)` 无人认领（Test 库现有 3 条 pending）。
> 因此 M9-R3"执行引擎浸泡"对 AIQE 链路不成立，TC-003 的真实执行仍未闭环（当前证据为服务层 + HTTP API）。

## 1. 证据

```bash
# Test 库
select status, count(*) from execution_jobs group by status;  -- pending|3
docker exec aiqe-test-backend ls /tmp/platform-worker.heartbeat  -- 不存在（未走 run_worker）
```

- `app/aiqe/services/execution_dispatcher.enqueue_node_run` 只创建 `ExecutionJob(payload={run_id,node_run_id,node_key})`；
- 平台消费者（`app/worker.py`）只消费 `ai_tasks`/scheduler，不处理 AIQE payload；
- `scripts/node/cameltv_node/executor.py` 的 `SUPPORTED_KINDS=("api","web","ui")` 按用例执行，
  **没有 `node_run_id` 分支**，无法把结果回写 `complete_node`。

## 2. 影响

| 项 | 影响 |
|----|------|
| M9-R3 引擎浸泡 | 对 AIQE 无意义（队列无消费者） |
| TC-003 真实执行 | 仅服务层模拟通过；真实 driver→attempt 链路未闭环 |
| Test 实例 | 3 条 pending job 长期滞留，需清理或补消费者 |

## 3. 建议（M10-347 一并实施）

1. **node 侧**：`cameltv_node` 增加 `aiqe_node` 执行分支：按 `node_run_id` 拉取节点规格 → 调 driver → 回写完成；
2. **或控制面侧**：`WORKER_EXECUTION_ENABLED=true` 时启动 AIQE 专用消费者（claim `payload.node_run_id` 的 job，
   执行 http driver，调用 `dag_scheduler.complete_node`）；
3. 清理 Test 现存的 3 条 pending job（确认无引用后置 `cancelled`）；
4. 完成后再重跑 TC-003 真实 driver 版本，替换 M9-R3 口径。

## 4. 与规划的关系

该缺口不阻塞 batch-349（学习 API）与本轮 M10 文档工作；列入 M10-347（真机/Runner 节点）范围。
