# Batch 329 — Design / QA / Leader

## 交付

| 文件 | 说明 |
|------|------|
| `aiqe/services/execution_dispatcher.py` | NodeRun → ExecutionJob（幂等，link execution_job_id） |
| `aiqe/services/dag_scheduler.py` | 条件边 success/failure/always |
| `aiqe/services/artifact_gc.py` | 30 天 GC；失败保留记录 |
| `artifact_storage*.py` | 新增 `delete()`（Local/MinIO） |
| `scripts/aiqe/run_dogfood.ps1` | Dogfood 执行器 |
| `tests/e2e/aiqe/test_tc_aiqe_001_010.py` | 真实 E2E 入口（env-gated） |

## QA

| # | 结果 | 证据 |
|---|:----:|------|
| A1–A6 | ✅ | 7 单测（dispatch 2 + 条件边 2 + GC 3） |
| A7 | ✅ | Dogfood：M1 64 / M2 75 / M3 44 / M4 30 / M5 78 / M6 17 / M8 24 / P0 7，全 PASS |
| A8 | ✅ | E2E 文件 skip 逻辑（无环境不伪造） |
| A9 | ✅ | 全量 + ratchet PASS |

## Leader Verdict

# ✅ APPROVED

- P0 代码闭环：真实 Worker 队列桥接、条件边、GC、Dogfood 留档；
- E2E 入口已固化，但**真实 Test 环境执行仍待环境/账号**；
- 放行合入 + 部署 release-m9。
