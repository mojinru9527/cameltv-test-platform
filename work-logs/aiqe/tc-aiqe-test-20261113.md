# TC-AIQE-001..010 隔离 Test 实例执行记录（2026-11-13）

> **环境**：隔离 Test 实例（`aiqe-test-backend` / `aiqe_test` PostgreSQL / head `20261123`），镜像 `release-m13-20261113`。
> **方式**：在 Test 后端容器内以服务层（与 API 同一套 service）真实执行，真实 PostgreSQL，创建隔离数据后清理；
> 无法由当前服务边界真实覆盖的场景标记 **BLOCKED**，不造假绿。
> **结果**：**7 PASS / 3 BLOCKED / 0 FAIL**。

## 1. 执行命令

```bash
# 服务器
docker cp tc_aiqe_service_acceptance.py aiqe-test-backend:/tmp/
docker exec -e PYTHONPATH=/app -w /app aiqe-test-backend \
  python /tmp/tc_aiqe_service_acceptance.py > /root/tc_aiqe_result.json
```

脚本入库：`test-platform-v2/backend/tests/e2e/aiqe/tc_aiqe_service_acceptance.py`
原始结果：`work-logs/aiqe/evidence/tc-aiqe-test-20261113.json`

## 2. 结果

| 用例 | 场景 | 结果 | 证据/说明 |
|------|------|:----:|-----------|
| TC-AIQE-001 | 需求契约冻结 + 变更影响 | ✅ PASS（定义冻结代理） | Workflow approved 后 `update_graph` 抛 `WorkflowImmutableError`，checksum 不变 |
| TC-AIQE-002 | 统一 Run | ✅ PASS | DAG 两节点（http→playwright）依次完成，Run=`COMPLETED/PASS`，事件时间线可读 |
| TC-AIQE-003 | 首次失败 + 重试成功 | 🚫 BLOCKED | attempt 时间线由 executor/worker 产生；Test 实例 `WORKER_EXECUTION_ENABLED=false`，服务层无 retry API |
| TC-AIQE-004 | 广告浮层交叉干扰 | 🚫 BLOCKED | 需业务 Web Test 目标 + integration profile 注入；Web 端反爬未解除 |
| TC-AIQE-005 | 并发数据污染 | ✅ PASS | 同一 fixture 锁第二次 `acquire` 抛 `LockUnavailable`，释放后可再取 |
| TC-AIQE-006 | 上游第三方故障 | ✅ PASS | `dependency_5xx` 检测命中；节点 `BLOCKED/UPSTREAM_5XX` → Run outcome=`INCOMPLETE`（非 PASS） |
| TC-AIQE-007 | UI Runner 自身故障 | ✅ PASS | `recover_after_worker_kill`：节点 `BLOCKED/WORKER_LOST`，Run=`COMPLETED/INCOMPLETE`（非 PASS） |
| TC-AIQE-008 | 开发修复后一键回归 | 🚫 BLOCKED | 需缺陷草稿→确认→指定 SHA 部署链路；AIQE HTTP 面未暴露 RegressionRequest 创建端点 |
| TC-AIQE-009 | 多端 AC 对照 | ✅ PASS | 注册 web（有 evidence）+ android（无 evidence）节点：web 可用、android 不可用，矩阵真实反映 |
| TC-AIQE-010 | 学习候选发布 | ✅ PASS | `candidate→benchmarked→approved→active`，误报率 5% 允许发布并生成 BugPattern |

## 3. 结论与边界

- 本记录是**平台服务层验收**（真实 Test 实例 + 真实 PostgreSQL），证明 P1 之后 AIQE 的冻结、DAG、锁、干扰检测、worker 恢复、能力矩阵、学习状态机均可运行；
- **未**覆盖业务端 E2E（CamelTv 体育 Test Web/Admin/真机）：TC-003/004/008 因执行引擎关闭、业务账号/反爬、缺少 RegressionRequest HTTP 端点而 BLOCKED；
- 因此**不能**把本记录当作"TC-AIQE 全绿"对外宣称；后续需：开启 Test 执行引擎 + 业务 Test 账号 + 补 RegressionRequest/attempt 查询 API。

## 4. 清理

脚本对创建的 `test_runs`/`node_runs`/`workflow_definitions`/`node_capability_manifests`/`learning_candidates`/`bug_patterns` 逐项删除（`CLEANUP` 无失败记录）。
