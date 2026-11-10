# Batch 287（M2 / TA-012）— HTTP Driver Adapter：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-287-m2-http-driver · **基线**：origin/main `9e5ebfd03`

## 1. 问题

DAG 的 `http` 节点还没有真实执行器：没有统一请求/响应证据（脱敏、截断），
多接口链失败行为与"首次失败不被 retry 覆盖"没有落点。

## 2. 目标

1. `HttpDriver.execute(spec)`：httpx 真实请求，返回 request/response 证据；
2. 证据脱敏（Authorization/Cookie/API-Key）+ body 截断；
3. `execute_chain(specs)`：顺序执行，首个失败即停，结果只追加不覆盖；
4. 超时/网络错误映射为 `TIMEOUT` / 异常类名；
5. 请求 content 记录 sha256 + 字节数（供 Artifact 关联）。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 多接口链成功 + 证据 | `test_chain_success_records_evidence` |
| A2 | 首失败即停 + 历史保留 | `test_chain_stops_at_first_failure_and_preserves_result` |
| A3 | 敏感头脱敏 | `test_sensitive_headers_redacted` |
| A4 | 超时映射 | `test_timeout_maps_to_error` |
| A5 | body 截断 | `test_body_truncated` |
| A6 | content 哈希证据 | `test_content_evidence_has_hash` |
| A7 | 全量 + ratchet | CI |

## 4. 非目标

- retry 编排（由调度层 StepAttempt 表达，driver 不覆盖历史）；
- 请求录制/回放（Keploy TA-018）；
- 断言执行（TA-009 workflow + assertion 层）。
