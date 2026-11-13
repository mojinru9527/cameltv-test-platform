# TC-AIQE-003 / 008 阻塞项解除验证（隔离 Test，2026-11-13）

> **环境**：`aiqe-test-backend`（镜像 `release-m13-b341`，`WORKER_EXECUTION_ENABLED=true`）/ `aiqe_test` PostgreSQL。
> **结论**：TC-003、TC-008 由 BLOCKED → **PASS**；TC-004（业务 Web 反爬）仍是唯一环境阻塞。

## 1. 前置（本批已交付）

| 能力 | 批次 | 说明 |
|------|------|------|
| 执行引擎 | batch-340 | Test 打开 `WORKER_EXECUTION_ENABLED=true`；`step_attempts` 持久化 + `retry.max_attempts` |
| attempt 时间线 API | batch-340 | `GET /api/v1/aiqe/runs/{run_id}/attempts` |
| 回归请求 API | batch-341 | `POST/GET /api/v1/aiqe/regressions`，创建 verification TestRun |

## 2. 执行方式

```bash
# Test 容器内（真实 HTTP + 服务层，真实 PostgreSQL）
docker exec -e PYTHONPATH=/app -w /app aiqe-test-backend python /tmp/tc_aiqe_unblocked_verify.py
```

脚本入库：`test-platform-v2/backend/tests/e2e/aiqe/tc_aiqe_unblocked_verify.py`

## 3. 结果

| 用例 | 场景 | 结果 | 证据 |
|------|------|:----:|------|
| TC-AIQE-003 | 首次失败 + 重试成功 | ✅ PASS | Run `TC003-…`：attempt1 `FAILED`（HTTP_503）保留、Run 未收口；重试 attempt2 `PASSED`；Run=`PASS`；API `/attempts` 返回 `[FAILED, PASSED]` |
| TC-AIQE-008 | 缺陷修复后一键回归 | ✅ PASS | 创建缺陷 → `POST /aiqe/regressions`：verification Run `REG-abc1234-…`（QUEUED、commit_sha=abc1234def、retest_of=旧 Run）；旧 Run 仍 `COMPLETED/FAIL` 未被修改 |

原始结果：`work-logs/aiqe/evidence/tc-aiqe-unblocked-20261113.json`

## 4. 剩余阻塞

| 用例 | 原因 | 解除条件 |
|------|------|----------|
| TC-AIQE-004 广告浮层交叉干扰 | 业务 Web Test 入口反爬未放行，无法注入浮层 | 业务 Test Web 白名单/专用测试入口，或改用 Admin/API 入口并记录豁免 |

## 5. 清理

脚本创建的 `test_runs`/`node_runs`/`step_attempts`/`defect`/`defect_regressions` 已删除；Test 实例 health 200。
