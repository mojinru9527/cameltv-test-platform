# Batch 347c：外部 Runner 执行 AIQE 设备节点并回写（2026-11-13）

> **结论**：真实 Android 设备通过外部 runner 认领 Test 实例的 AIQE `ExecutionJob`，执行后回写节点状态，
> Run 判定 PASS——AIQE 首次"真机执行 + attempt 证据"闭环。

## 1. 架构

```text
Test backend (dispatch) → ExecutionJob(payload: run_id/node_run_id/driver/input/graph)
        │  (进程内消费者只认领 http，跳过 appium/playwright)
        ▼
本地 runner（aiqe_local_runner.py） --claim--> /execution-jobs/claim
        │  --payload--> /execution-jobs/{id}/payload
        │  execute_node(driver=appium/playwright/http)
        ▼
/execution-jobs/{id}/report  (status=completed|failed)
        ▼
complete_from_report → dag_scheduler.complete_node → NodeRun/TestRun/StepAttempt
```

关键点：
- 外部上报状态只接受 `completed|failed|cancelled`；`completed` 映射 PASSED；
- 进程内消费者只认领 `driver in (http, httpx, api)`，UI/设备任务留给具备依赖的 runner；
- 节点令牌由 `POST /api/v1/ai/agents/register` 签发，能力需包含 `api/web/ui`。

## 2. 端到端证据（Test 实例 + 真机）

runner 输出：

```json
{"claimed": true, "job_id": 8, "driver": "appium", "node_status": "PASSED", "error_class": ""}
```

Test 库查询：

```sql
select j.id, j.status as job, n.status as node, n.error_class, r.status as run, r.outcome,
       (select string_agg(a.status, ',') from step_attempts a where a.node_run_id = n.id) as attempts, r.run_key
from execution_jobs j
join node_runs n on n.id = (j.payload_json::json->>'node_run_id')
join test_runs r on r.id = n.run_id
where j.id = 8;
```

```text
 id |    job    |  node  | error_class |    run    | outcome | attempts |       run_key
----+-----------+--------+-------------+-----------+---------+----------+---------------------
  8 | completed | PASSED |             | COMPLETED | PASS    | PASSED   | M10-DEVICE-e3d5a122
```

- 设备：`9f0564ba` / ONEPLUS A6010 / Android 11 / `com.camelrn`；
- 断言：页面层级包含 `PHONE NUMBER`（登录页）；
- 运输：本地 SSH 端口转发 `18000 → Test 127.0.0.1:18000`。

## 3. 代码与测试

| 文件 | 变更 |
|------|------|
| `aiqe/services/job_consumer.py` | `HTTP_DRIVERS` 过滤 + `complete_from_report` |
| `api/v1/execution_jobs.py` | report 后对 AIQE job 回写节点 |
| `aiqe/services/execution_dispatcher.py` | payload 增加 driver/input |
| `scripts/qa/aiqe_local_runner.py` | 外部 runner（claim/payload/execute/report） |
| `tests/test_aiqe_external_node_report.py` | 4 条：payload、跳过非 http、成功/失败回写 |

质量棘轮 PASS；相关测试 16 条通过。

## 4. 边界

- Test 云主机无 Chromium/Appium/设备，UI/设备节点必须由 runner 执行（本机已验证）；
- runner 需可访问平台 API（生产建议走内网/白名单）；
- 真机用例目前是只读断言；后续可加点击/截图证据包上传（B4 evidence）。
