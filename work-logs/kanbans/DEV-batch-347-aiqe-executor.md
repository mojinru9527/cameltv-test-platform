# 🗂️ 看板：Batch 347（AIQE 进程内执行器）

| 字段 | 值 |
|------|-----|
| 批次 | batch-347（full，M10-347 代码部分） |
| 分支 | feature/batch-347-aiqe-executor |
| 基线 | origin/main `84b378bd9` |

| # | 项 | 状态 |
|---|----|:----:|
| 1 | node_executor（http driver） | ✅ |
| 2 | ExecutionJob 消费者 + 原子认领 | ✅ |
| 3 | lifespan 开关（默认关） | ✅ |
| 4 | 测试 5 条 | ✅ |
| 5 | PR / checks / 合入 | 🔄 |
| 6 | Test 真实 DAG 执行验证 | ⏳ |

## 下一步

- Test 开启 `AIQE_INPROCESS_EXECUTOR_ENABLED=true`，跑真实 http DAG（200 PASS / 404 FAIL）；
- 剩余：UI/真机 runner 节点（设备到位后）。
