# TC-004 UI 执行链路验证（本地 fixture，2026-11-14）

> **结论**：TC-004 的 Core / Integration 两条 UI Run 已通过真实 AIQE 链路跑通
> （Test 实例建 Run → 外部 runner Playwright 执行 → 回写 attempt）。
> 真实站点 camel1.tv 仍被 WAF 拦截，白名单后仅需替换 URL。

## 1. 链路

```text
Test 建 Run（playwright 节点）
  → ExecutionJob(payload driver/input/graph)
  → 外部 runner claim（进程内消费者只认 http，跳过 playwright）
  → Playwright 执行（本地 fixture http://127.0.0.1:8765/）
      Core：点击 LIVE（trial）→ 可点击 → PASSED
      Integration：注入 #aiqe-injected-overlay 后点击 LIVE → 被拦截 → OVERLAY_INTERCEPTED
  → report(status=completed|failed)
  → complete_from_report → NodeRun/TestRun/StepAttempt
```

## 2. 结果（Test 实例）

```sql
select j.id, j.status as job, n.status as node, n.error_class, r.status as run, r.outcome,
       (select string_agg(a.status, ',') from step_attempts a where a.node_run_id = n.id) as attempts, r.run_key
from execution_jobs j
join node_runs n on n.id = (j.payload_json::json->>'node_run_id')
join test_runs r on r.id = n.run_id
where j.id in (9, 10) order by j.id;
```

```text
 id |    job    |  node  |     error_class     |    run    | outcome | attempts |         run_key
----+-----------+--------+---------------------+-----------+---------+----------+--------------------------
  9 | completed | PASSED |                     | COMPLETED | PASS    | PASSED   | TC004-core-95731b
 10 | failed    | FAILED | OVERLAY_INTERCEPTED | COMPLETED | FAIL    | FAILED   | TC004-integration-bd7832
```

- Core：无浮层，目标可点击、文案匹配 → PASS；
- Integration：注入全屏浮层后目标不可点击 → FAIL（预期），error_class 精确为 `OVERLAY_INTERCEPTED`；
- 两条 Run 均产生 attempt 记录（PASSED / FAILED）。

## 3. 复跑方式

```bash
# 1) 本地起 fixture
python -m http.server 8765 --bind 127.0.0.1 --directory <repo>/scripts/qa/fixtures
# 2) Test 实例建两条 Run（playwright 节点，含/不含 inject_overlay）
# 3) 本地 runner 认领并执行
python scripts/qa/aiqe_local_runner.py --base-url http://127.0.0.1:18000 \
  --project-id 1 --node-id local-device-runner --agent-token <token> --once
```

## 4. 边界与下一步

| 项 | 状态 |
|----|------|
| 链路机制（Run→Job→runner→回写） | ✅ |
| Core PASS / Integration FAIL 判定 | ✅ |
| 真实 camel1.tv | 🚫 WAF 拦截脚本（403/reset），需白名单或内部 Test 入口 |
| 证据包上传（截图） | ⏳ 后续可接 B4 evidence |

WAF 放行后，把节点 input.url 换成 `https://www.camel1.tv/`、`click_text` 换成真实入口文案即可复用本链路。
