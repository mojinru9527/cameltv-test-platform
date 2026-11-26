# AIQE V1.6 监控与告警（V16-024）

> **STATUS: HISTORICAL** — 本文记录 2026-11-2x 当时的执行事实与结论；其中 PASS/VERIFIED 等表述不代表当前发布判定。当前状态以 `release-verdict.json`、`E2E-Coverage-and-Blockers.md` 与 `governance/production-evidence.json` 为准。


> 指标端点：`GET /api/v1/aiqe/metrics`（`X-AIQE-Metrics-Token`；生产未配置 token 时 403 fail-closed）。
> 告警规则事实源：`docs/aiqe/v1.6/observability/aiqe-alerts.yaml`，由 `scripts/aiqe/check_alerts.py` 校验。

## 1. 指标清单（21 项，全部 `aiqe_` 前缀）

### 执行可靠性
- `aiqe_run_queued_age_seconds`
- `aiqe_job_pending_age_seconds`
- `aiqe_job_lease_expired_total`
- `aiqe_job_fencing_rejected_total`
- `aiqe_run_terminal_latency_seconds`（histogram）
- `aiqe_run_without_job_total`
- `aiqe_node_without_assertion_total`
- `aiqe_reconciler_repair_total`

### 安全
- `aiqe_target_policy_denied_total`
- `aiqe_target_policy_unavailable_total`
- `aiqe_ssrf_blocked_total`
- `aiqe_secret_canary_detected_total`（**必须为 0**）
- `aiqe_secret_handle_resolve_denied_total`
- `aiqe_cross_project_access_denied_total`
- `aiqe_db_query_policy_denied_total`

### Agent / Learning
- `aiqe_agent_task_failure_total`
- `aiqe_agent_tool_unavailable_total`
- `aiqe_agent_invalid_evidence_total`
- `aiqe_benchmark_gate_rejected_total`
- `aiqe_learning_publish_total`
- `aiqe_learning_rollback_total`

低基数约束：label 仅允许 `project_id / status / driver / outcome / reason / tool / agent / platform / env`；
URL、SQL、Token、用户输入全文不得进入 label（registry 会丢弃/替换为 `redacted`）。

## 2. 告警分级

| 级别 | 场景 | 动作 |
|---|---|---|
| **P0** | `aiqe_secret_canary_detected_total > 0` | 立即停止相关 Worker、隔离数据、启动密钥轮换；按安全事件升级 |
| **P0** | `aiqe_target_policy_unavailable_total` 上升 | 阻断新执行，不降级旧路径 |
| **P0** | `aiqe_cross_project_access_denied_total` 出现 | 按安全事件调查；若出现成功访问则立即回滚 |
| P1 | lease expired / fencing rejected / run without job / node without assertion | 暂停自动回归与 Noise，检查 Worker/Reconciler |
| P1 | Agent task failure / invalid evidence / Benchmark 未过 gate 却发布 | 撤回发布、重新审批 |
| P2 | terminal latency、reconciler repair、tool unavailable、gate rejected | 观察并排期修复 |

Secret Canary 命中时禁止继续灰度；告警必须带 runbook 链接与负责人。

## 3. 抓取与保留

- Prometheus 每 15s 抓取，保留 ≥ 30 天（release gate 要求覆盖一个完整业务周期）。
- 指标端点只读、无写副作用；不得在抓取路径触发数据库重查询。
- 生产 token 存于 Secret Manager，轮换周期 ≤ 90 天。
